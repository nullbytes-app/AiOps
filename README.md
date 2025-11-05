# AI Agents

[![CI/CD Pipeline](https://github.com/nullBytes/AI-Ops/actions/workflows/ci.yml/badge.svg)](https://github.com/nullBytes/AI-Ops/actions/workflows/ci.yml)

Multi-tenant AI enhancement platform for MSP technicians. This system receives webhook requests from ServiceDesk Plus, enriches tickets with context gathered from multiple sources, and returns enhanced ticket information for improved support workflows.

## Table of Contents

- **Getting Started**
  - [Prerequisites](#prerequisites)
  - [Local Development Setup](#local-development-setup)
  - [Docker Setup (Recommended)](#docker-setup-recommended)
  - [Quick Links](#quick-links)

- **Core Features**
  - [Webhook Integration](#webhook-integration)
  - [Redis Queue Setup and Monitoring](#redis-queue-setup-and-monitoring)
  - [Celery Worker Setup](#celery-worker-setup)
  - [Database Setup and Migrations](#database-setup-and-migrations)
  - [LiteLLM Proxy Integration](#litellm-proxy-integration)

- **Running the Application**
  - [Running Tests in Docker](#running-tests-in-docker)
  - [Development Tools](#development-tools)
  - [CI/CD Pipeline](#cicd-pipeline)

- **Deployment & Operations**
  - [Kubernetes Deployment](#kubernetes-deployment)
  - [Troubleshooting](#troubleshooting)

- **Project Information**
  - [Project Structure](#project-structure)
  - [Documentation](#documentation)
  - [Contributing](#contributing)

## Quick Links

**Documentation:**
- 📘 [Architecture Decision Document](docs/architecture.md) - System design, technology stack, and technical decisions
- 🚀 [Kubernetes Deployment Guide](docs/deployment.md) - Production deployment and scaling
- 📋 [Tech Specification](docs/tech-spec-epic-1.md) - Detailed technical requirements and specifications
- 🖥️ [Admin UI Guide](docs/admin-ui-guide.md) - Comprehensive Streamlit admin interface documentation (setup, deployment, features, troubleshooting)

**Development:**
- 💻 [Contributing Guidelines](#contributing) - Development workflow and code standards
- ✅ [CI/CD Pipeline Details](#cicd-pipeline) - Automated testing and deployment

**Helpful Commands:**
```bash
# Local development with Docker (recommended)
docker-compose up -d

# Run Streamlit Admin UI locally
streamlit run src/admin/app.py

# View application documentation
curl http://localhost:8000/docs

# Run tests locally
pytest tests/ --cov=src --cov-report=html

# Deploy to Kubernetes
./k8s/test-deployment.sh
```

## Prerequisites

- **Python 3.12+** (required for all dependencies)
- **Docker Desktop** (for running PostgreSQL and Redis locally)
- **Git** (for version control)

## Local Development Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd "AI Ops"
```

### 2. Create Virtual Environment

```bash
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip setuptools wheel
pip install -e ".[dev]"
```

This installs:
- Core dependencies (FastAPI, SQLAlchemy, Celery, Redis, prometheus-client, etc.)
- Development tools (pytest, black, ruff, mypy)

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and configure the following variables:
- `AI_AGENTS_DATABASE_URL` - PostgreSQL connection string
- `AI_AGENTS_REDIS_URL` - Redis connection string
- `AI_AGENTS_CELERY_BROKER_URL` - Celery broker URL (Redis)
- `AI_AGENTS_ENVIRONMENT` - Environment name (development/staging/production)
- `AI_AGENTS_LOG_LEVEL` - Logging level (DEBUG/INFO/WARNING/ERROR)

**Note:** When using Docker (recommended), the default values in `.env.example` are already configured for Docker service names (`postgres`, `redis`). For local development without Docker, change `postgres` to `localhost` and `redis` to `localhost` in the connection strings.

## Docker Setup (Recommended)

The project includes Docker configuration for running the complete stack locally without manual service installation.

### Prerequisites

- **Docker Desktop** installed and running
- Minimum: Docker Engine 20.10+, Docker Compose 2.0+
- Allocate at least 4GB RAM to Docker Desktop

### Quick Start with Docker

1. **Copy environment configuration:**
   ```bash
   cp .env.example .env
   ```

2. **Start all services:**
   ```bash
   docker-compose up -d
   ```

3. **Wait for health checks to pass** (about 30 seconds):
   ```bash
   docker-compose ps
   ```
   All services should show status `(healthy)`.

4. **Access the application:**
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

5. **View logs:**
   ```bash
   # All services
   docker-compose logs -f

   # Specific service
   docker-compose logs -f api
   ```

6. **Stop services:**
   ```bash
   # Stop and keep data
   docker-compose down

   # Stop and remove all data
   docker-compose down -v
   ```

### Docker Services

The `docker-compose.yml` orchestrates three services:

- **postgres** - PostgreSQL 17 database (port 5433 → 5432)
- **redis** - Redis 7 cache and message broker (port 6379)
- **api** - FastAPI application with hot-reload (port 8000)

### Accessing Services

| Service | Container Name | Host Access | Container Access |
|---------|---------------|-------------|------------------|
| PostgreSQL | ai-agents-postgres | localhost:5433 | postgres:5432 |
| Redis | ai-agents-redis | localhost:6379 | redis:6379 |
| FastAPI | ai-agents-api | localhost:8000 | api:8000 |

**Note:** Port 5433 is used for PostgreSQL host mapping to avoid conflicts with local PostgreSQL installations. Inside containers, use service names (`postgres`, `redis`) and standard ports.

### Hot-Reload Development

Code changes are automatically detected and the API reloads:

1. **Edit source code** in `src/` directory
2. **Save the file** - uvicorn detects changes
3. **API reloads automatically** - no restart needed

Volume mounts:
- `./src:/app/src` - Application code
- `./tests:/app/tests` - Test files
- `./alembic:/app/alembic` - Database migrations

### Data Persistence

PostgreSQL and Redis data are stored in local volumes:
- `./data/postgres/` - Database files
- `./data/redis/` - Redis AOF persistence

These directories are git-ignored and persist across container restarts.

### Redis Queue Setup and Monitoring

Redis is configured as both a caching layer and message broker for asynchronous job processing.

#### Configuration

Redis is initialized with the following settings (see `docker-compose.yml`):

- **Version:** Redis 7-alpine
- **Port:** 6379 (standard Redis port)
- **Persistence:** AOF (Append-Only File) enabled for durability
- **Max Memory:** 2GB (local development), 8GB (production)
- **Connection Pool:** 10 max connections per service (configurable via `AI_AGENTS_REDIS_MAX_CONNECTIONS`)
- **Connection Timeout:** 5 seconds for all operations

#### Queue Naming Convention

Jobs are organized by queue name using the pattern: `module:purpose`

- **Main Enhancement Queue:** `enhancement:queue`
  - Stores webhook enhancement requests for asynchronous processing
  - Used by FastAPI to push jobs, Celery workers to pop jobs
  - Message format: JSON serialized job objects

#### Queue Operations

The application provides queue operations via `src/services/queue_service.py`:

```python
# Push a job to the queue
await push_to_queue("enhancement:queue", {
    "job_id": "uuid",
    "tenant_id": "tenant-abc",
    "ticket_id": "TKT-12345",
    "description": "Server running slow",
    "priority": "high"
})

# Pop a job from the queue (blocking, 1-second timeout)
job = await pop_from_queue("enhancement:queue")

# Peek at jobs without removing them
jobs = await peek_queue("enhancement:queue", count=10)

# Get queue depth (for monitoring/autoscaling)
depth = await get_queue_depth("enhancement:queue")
```

#### Health Check Integration

The health check endpoint validates Redis connectivity:

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "service": "AI Agents",
  "dependencies": {
    "database": "healthy",
    "redis": "healthy"
  }
}
```

#### Redis CLI Monitoring

Access Redis CLI to inspect and monitor queues:

```bash
# Enter Redis CLI
docker-compose exec redis redis-cli

# Get queue depth
LLEN enhancement:queue

# View next 10 jobs in queue (FIFO order)
LRANGE enhancement:queue 0 9

# View all jobs in queue
LRANGE enhancement:queue 0 -1

# View specific job
LINDEX enhancement:queue 0

# Monitor Redis server stats
INFO

# Check memory usage
INFO memory

# Check connected clients
INFO clients
CLIENT LIST

# Check slow commands
SLOWLOG GET 10
```

#### Queue Depth for Autoscaling

The queue depth metric is used for autoscaling worker pods:

```bash
# Get current queue depth (number of pending jobs)
LLEN enhancement:queue

# Scale up if: depth > 50 jobs
# Scale down if: depth < 10 jobs
```

#### Persistence Strategy

Redis uses AOF (Append-Only File) persistence for durability:

- **Fsync Policy:** `everysec` (default) - Syncs to disk every second
- **Data Loss Window:** Maximum 1 second of jobs if Redis crashes
- **Persistence File:** `./data/redis/appendonlydir/`
- **RDB Snapshot:** `./data/redis/dump.rdb` (periodic backup)

To verify persistence:

```bash
# Check persistence files
docker-compose exec redis ls -la /data

# View persistence status
docker-compose exec redis redis-cli CONFIG GET appendonly
docker-compose exec redis redis-cli INFO persistence
```

#### Testing Queue Operations

Run integration tests to verify queue functionality:

```bash
# Run all Redis queue tests
docker-compose exec api pytest tests/integration/test_redis_queue.py -v

# Run specific test
docker-compose exec api pytest tests/integration/test_redis_queue.py::TestQueueOperations::test_push_to_queue -v
```

Test coverage includes:
- Redis client initialization and connection pooling
- Queue push/pop operations
- Message serialization and durability
- Queue depth monitoring
- Persistence across container restarts
- Error handling for connection failures

#### Troubleshooting

**Queue not processing:**

```bash
# Check queue depth
docker-compose exec redis redis-cli LLEN enhancement:queue

# Verify worker is running
docker-compose ps  # Check for celery worker service

# View Redis logs
docker-compose logs redis
```

**Persistence not working:**

```bash
# Verify AOF is enabled
docker-compose exec redis redis-cli CONFIG GET appendonly

# Check persistence file exists
docker-compose exec redis ls -la /data

# Force AOF rewrite (if file too large)
docker-compose exec redis redis-cli BGREWRITEAOF
```

**Connection errors:**

```bash
# Test Redis connectivity
docker-compose exec redis redis-cli ping

# Check connection pool status
docker-compose exec redis redis-cli INFO clients

# Verify container is healthy
docker-compose ps redis
```

**Clear queue (development only):**

```bash
# Delete all jobs in enhancement queue
docker-compose exec redis redis-cli DEL enhancement:queue

# Flush entire Redis database (clears cache too)
docker-compose exec redis redis-cli FLUSHDB
```

### Celery Worker Setup

The application uses **Celery 5.x** with **Redis** as the message broker for asynchronous task processing. Celery workers handle long-running operations like AI enhancement workflows, allowing the API to respond quickly to webhook requests.

#### Worker Configuration

Celery workers are configured with the following settings (per tech spec):

- **Concurrency:** 4 worker threads per pod (processes 4 tasks in parallel)
- **Prefetch Multiplier:** 1 (fetch one task at a time for memory efficiency)
- **Time Limits:** 120 seconds hard limit, 100 seconds soft limit
- **Acknowledgement:** Late (acknowledge after task completes to prevent message loss)
- **Retry Logic:** Max 3 retries with exponential backoff (2s, 4s, 8s) and jitter
- **Serialization:** JSON for task payloads and results
- **Redis Broker:** Database 1 (separate from cache on DB 0)

#### Starting the Worker

**With Docker (recommended):**

```bash
# Start worker service
docker-compose up -d worker

# View worker logs
docker-compose logs -f worker

# Check worker status
docker-compose ps worker
```

**Manual start (local development):**

```bash
# Activate virtual environment
source .venv/bin/activate

# Load environment variables
set -a && source .env && set +a

# Start worker
celery -A src.workers.celery_app worker --loglevel=info --concurrency=4
```

#### Worker Health Monitoring

Celery provides several commands for monitoring worker health and task execution:

**Check worker is alive:**

```bash
# Ping worker (should respond with 'pong')
docker-compose exec worker celery -A src.workers.celery_app inspect ping

# Or from host (requires celery installed locally)
celery -A src.workers.celery_app inspect ping
```

**View active tasks:**

```bash
# List currently executing tasks
docker-compose exec worker celery -A src.workers.celery_app inspect active

# Example output:
# -> celery@worker: OK
#     * {'id': '...', 'name': 'tasks.enhance_ticket', 'args': [...], ...}
```

**View registered tasks:**

```bash
# List all tasks registered with the worker
docker-compose exec worker celery -A src.workers.celery_app inspect registered

# Example output:
# -> celery@worker: OK
#     * tasks.add_numbers
#     * tasks.enhance_ticket
```

**View worker statistics:**

```bash
# Get comprehensive worker stats (processed tasks, pool info, etc.)
docker-compose exec worker celery -A src.workers.celery_app inspect stats
```

**Monitor queue depth:**

```bash
# Check how many jobs are waiting in the queue
docker-compose exec redis redis-cli LLEN celery

# View pending jobs (first 10)
docker-compose exec redis redis-cli LRANGE celery 0 9
```

#### Creating and Executing Celery Tasks

**Task Definition (example from `src/workers/tasks.py`):**

```python
from src.workers.celery_app import celery_app

@celery_app.task(
    bind=True,
    name="tasks.add_numbers",
    track_started=True,
)
def add_numbers(self, x: int, y: int) -> int:
    """Add two numbers (test task)."""
    return x + y
```

**Calling Tasks from Python:**

```python
from src.workers.tasks import add_numbers

# Async execution (returns immediately with task ID)
result = add_numbers.delay(2, 3)

# Get task ID
print(result.id)  # e.g., '550e8400-e29b-41d4-a716-446655440000'

# Wait for result (blocking)
final_result = result.get(timeout=10)  # Returns: 5

# Check task status
print(result.status)  # 'SUCCESS', 'PENDING', 'STARTED', 'FAILURE'

# Advanced: Call with options
result = add_numbers.apply_async(
    args=[10, 20],
    countdown=5,  # Delay execution by 5 seconds
    expires=60,   # Task expires after 60 seconds
    retry=True,   # Enable retries
)
```

**Task Result Retrieval:**

```python
from celery.result import AsyncResult
from src.workers.celery_app import celery_app

# Retrieve result using task ID
task_id = "550e8400-e29b-41d4-a716-446655440000"
result = AsyncResult(task_id, app=celery_app)

# Check if task completed
if result.ready():
    print(result.result)  # Get result value
else:
    print(f"Task status: {result.status}")
```

#### Worker Configuration Reference

**Environment Variables:**

```bash
# Celery broker URL (Redis DB 1)
AI_AGENTS_CELERY_BROKER_URL=redis://redis:6379/1

# Celery result backend (Redis DB 1)
AI_AGENTS_CELERY_RESULT_BACKEND=redis://redis:6379/1

# Worker concurrency (number of concurrent tasks)
AI_AGENTS_CELERY_WORKER_CONCURRENCY=4

# Log level
AI_AGENTS_LOG_LEVEL=INFO
```

**Worker Command Line Options:**

```bash
# Basic worker start
celery -A src.workers.celery_app worker

# With log level
celery -A src.workers.celery_app worker --loglevel=info

# With specific concurrency
celery -A src.workers.celery_app worker --concurrency=8

# With autoscale (min 2, max 10 workers)
celery -A src.workers.celery_app worker --autoscale=10,2

# With specific queue
celery -A src.workers.celery_app worker -Q celery,high_priority

# With beat scheduler (for periodic tasks)
celery -A src.workers.celery_app worker --beat
```

#### Structured Logging

Workers output structured logs with task context:

**Development (colorized console):**

```
2025-11-01 14:30:15 | INFO     | tasks:add_numbers:45 | Task add_numbers started {'task_id': '...', 'worker_id': 'celery@worker', 'args': {'x': 2, 'y': 3}}
2025-11-01 14:30:15 | INFO     | tasks:add_numbers:62 | Task add_numbers completed successfully {'task_id': '...', 'result': 5}
```

**Production (JSON serialization):**

```json
{
  "timestamp": "2025-11-01T14:30:15.123Z",
  "level": "INFO",
  "message": "Task add_numbers started",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "task_name": "tasks.add_numbers",
  "worker_id": "celery@worker-1",
  "args": {"x": 2, "y": 3}
}
```

#### Testing Celery Tasks

Run integration tests to verify worker and task functionality:

```bash
# Run all Celery integration tests
docker-compose exec api pytest tests/integration/test_celery_tasks.py -v

# Run specific test class
docker-compose exec api pytest tests/integration/test_celery_tasks.py::TestCeleryTaskExecution -v

# Run specific test
docker-compose exec api pytest tests/integration/test_celery_tasks.py::TestCeleryTaskExecution::test_basic_task_execution_async -v

# Run with coverage
docker-compose exec api pytest tests/integration/test_celery_tasks.py --cov=src/workers
```

Test coverage includes:
- Worker connection to Redis broker
- Task execution (synchronous and asynchronous)
- Task retry logic with exponential backoff
- Task timeout enforcement (soft and hard limits)
- Task result persistence in Redis backend
- Task monitoring and inspection

#### Troubleshooting

**Worker not starting:**

```bash
# Check worker logs for errors
docker-compose logs worker

# Verify Redis is running
docker-compose ps redis
docker-compose exec redis redis-cli ping

# Verify worker container is running
docker-compose ps worker

# Restart worker
docker-compose restart worker
```

**Tasks not executing:**

```bash
# Check if worker is registered and alive
docker-compose exec worker celery -A src.workers.celery_app inspect ping

# Check if tasks are registered
docker-compose exec worker celery -A src.workers.celery_app inspect registered

# Check active tasks
docker-compose exec worker celery -A src.workers.celery_app inspect active

# Check queue depth (tasks waiting)
docker-compose exec redis redis-cli LLEN celery

# Verify broker connection
docker-compose exec redis redis-cli INFO clients
```

**Connection errors:**

```bash
# Test Redis connectivity from worker container
docker-compose exec worker redis-cli -h redis ping

# Check environment variables
docker-compose exec worker env | grep CELERY

# Verify .env file has correct values
cat .env | grep CELERY
```

**Task timeouts:**

```bash
# Check if task is exceeding soft time limit (100s)
docker-compose logs worker | grep "SoftTimeLimitExceeded"

# Increase time limits (if needed, edit src/workers/celery_app.py):
# task_time_limit=240  # 4 minutes hard limit
# task_soft_time_limit=200  # 3:20 soft limit
```

**Memory issues:**

```bash
# Check worker memory usage
docker stats ai-agents-worker

# Reduce concurrency if memory-constrained
docker-compose down
# Edit docker-compose.yml: --concurrency=2
docker-compose up -d worker

# Or set via environment variable
export AI_AGENTS_CELERY_WORKER_CONCURRENCY=2
docker-compose up -d worker
```

**Purge all tasks (development only):**

```bash
# WARNING: This deletes all pending tasks in the queue
docker-compose exec worker celery -A src.workers.celery_app purge

# Or manually via Redis CLI
docker-compose exec redis redis-cli DEL celery
```

#### Future Enhancements (Epic 3-4)

Planned worker enhancements for future epics:

- **Celery Flower:** Web-based monitoring dashboard (http://localhost:5555)
- **Prometheus Metrics:** Task success/failure rates, execution time, queue depth
- **Distributed Tracing:** OpenTelemetry integration for end-to-end request tracing
- **Priority Queues:** High/normal/low priority task routing
- **Tenant Isolation:** Separate worker pools per tenant for resource isolation
- **Rate Limiting:** Max N tasks per tenant per minute
- **Horizontal Autoscaling:** Kubernetes HPA based on queue depth (scale 1-10 pods)

### Database Setup and Migrations

The application uses **PostgreSQL 17** with **Alembic** for schema management and **Row-Level Security (RLS)** for multi-tenant data isolation.

#### Initial Database Setup

When the Docker containers start, the database is automatically initialized with migrations. The complete database schema is created on first startup, including:

- **Schema Migration:** Initial table creation (tenant_configs, enhancement_history) with proper constraints and indexes
- **RLS Migration:** Row-level security policies and database roles for tenant isolation
- **Timestamp Defaults:** Server-side timestamp defaults for auditability

No manual setup is required—migrations run automatically when the Docker stack starts.

#### Database Migrations Applied

**Migration 1: Initial Schema (63a573401118)**
- Creates `tenant_configs` table with encryption fields and tenant isolation
- Creates `enhancement_history` table for audit trail and analytics
- Establishes indexes on frequently-queried columns
- Ensures data consistency with primary keys and constraints

**Migration 2: Row-Level Security (2075b4285d2b)**
- Enables RLS on both tables for automatic tenant isolation
- Creates database roles: `app_user` (limited) and `admin` (full access)
- Implements `tenant_isolation_policy` for enforcement
- Grants appropriate permissions to each role

**Migration 3: Server-Side Timestamp Defaults (15577cf2a847)**
- Adds `now()` defaults to `created_at` columns in both tables
- Adds `now()` defaults to `updated_at` column in tenant_configs
- Ensures database-side timestamp accuracy for all records
- Improves audit trail reliability

#### Running Database Migrations

**From the project root (local development):**

```bash
# Activate virtual environment
source .venv/bin/activate

# Load environment variables
set -a && source .env && set +a

# Check current migration status
alembic current

# Apply all pending migrations
alembic upgrade head

# Rollback one migration (testing only)
alembic downgrade -1

# Re-apply a migration
alembic upgrade head
```

**From within Docker container:**

```bash
# Apply migrations
docker-compose exec api alembic upgrade head

# Check status
docker-compose exec api alembic current

# View migration history
docker-compose exec api alembic history
```

#### Creating New Migrations

When you modify database models in `src/database/models.py`:

1. **Auto-generate migration:**
   ```bash
   alembic revision --autogenerate -m "Add new_column to users table"
   ```

2. **Review the generated migration** in `alembic/versions/`:
   - Verify all columns, indexes, and constraints are correct
   - Add any custom SQL if needed

3. **Test the migration:**
   ```bash
   alembic upgrade head     # Apply migration
   alembic downgrade -1     # Rollback (verify reverse works)
   alembic upgrade head     # Re-apply
   ```

4. **Commit the migration file** to version control

#### Database Schema

The initial schema includes:

- **tenant_configs** - Multi-tenant configuration storage
  - Stores ServiceDesk Plus credentials, webhook secrets
  - Encrypted fields for sensitive data (API keys, secrets)
  - JSON field for tenant-specific enhancement preferences
  - Indexed by tenant_id for fast lookups

- **enhancement_history** - Audit trail of enhancement operations
  - Records status of each enhancement (pending, completed, failed)
  - Stores gathered context, LLM output, processing time
  - Indexed by (tenant_id, ticket_id) composite for efficient queries
  - Supports analytics and debugging

#### Row-Level Security (RLS)

The database implements RLS policies for multi-tenant isolation:

- **Policy:** `tenant_isolation_policy` on enhancement_history table
- **Policy:** `tenant_config_isolation_policy` on tenant_configs table
- **Mechanism:** Uses PostgreSQL `current_setting('app.current_tenant_id')` session variable

**Setting tenant context in application code:**

```python
from sqlalchemy import text
from src.database.session import async_session_maker

async def process_request(tenant_id: str):
    async with async_session_maker() as session:
        # Set tenant context before queries
        await session.execute(
            text("SET app.current_tenant_id = :tenant_id"),
            {"tenant_id": tenant_id}
        )

        # All queries automatically filtered by tenant_id
        result = await session.execute(
            select(EnhancementHistory).where(...)
        )
```

**Database roles:**

- **app_user** - Limited permissions (SELECT, INSERT, UPDATE on data tables)
- **admin** - Full permissions (bypasses RLS for administrative tasks)

#### Connection Pooling Configuration

The application uses async SQLAlchemy with connection pooling:

- **Pool Size:** 20 connections per service (configurable via `AI_AGENTS_DATABASE_POOL_SIZE`)
- **Pool Pre-Ping:** Enabled - detects and removes stale connections
- **Pool Recycle:** 3600 seconds - recycles old connections

Configuration in `src/database/session.py` and `src/database/connection.py`.

#### Troubleshooting

**Connection refused errors:**

```bash
# Check if PostgreSQL container is running
docker-compose ps postgres

# Verify database is accepting connections
docker-compose exec postgres pg_isready -U aiagents

# View PostgreSQL logs
docker-compose logs postgres
```

**Migration conflicts:**

```bash
# View migration history
alembic history

# Check if any migrations are pending
alembic current
```

**Data persistence issues:**

```bash
# Backup data before stopping containers
docker-compose down  # Keeps data

# Remove all data (fresh start)
docker-compose down -v

# Inspect stored data
ls -la data/postgres/
```

#### Database Testing

Run comprehensive integration tests to verify database functionality:

```bash
# Run all database tests (14 tests)
docker-compose exec api pytest tests/integration/test_database.py -v

# Run specific test class
docker-compose exec api pytest tests/integration/test_database.py::TestTenantConfigModel -v

# Run specific test
docker-compose exec api pytest tests/integration/test_database.py::TestTenantConfigModel::test_insert_tenant_config -v

# Run with coverage report
docker-compose exec api pytest tests/integration/test_database.py --cov=src/database --cov-report=html

# Run from host (requires local Alembic installation)
pytest tests/integration/test_database.py -v
```

**Test Coverage (14 tests, all passing):**

**DatabaseConnection Tests:**
- ✅ Database health check endpoint connectivity
- ✅ Connection pool configuration and pre-ping verification

**TenantConfig Model Tests:**
- ✅ Insert and retrieve tenant configuration records
- ✅ Query by tenant_id index
- ✅ Unique constraint enforcement on tenant_id

**EnhancementHistory Model Tests:**
- ✅ Insert and retrieve enhancement history records
- ✅ Composite query (tenant_id + ticket_id)
- ✅ Multiple status values (pending, completed, failed)

**Row-Level Security Tests:**
- ✅ RLS enabled on enhancement_history table
- ✅ RLS enabled on tenant_configs table
- ✅ RLS policy enforces tenant isolation

**Migration Tests:**
- ✅ All required tables exist after migration
- ✅ All required indexes created correctly
- ✅ Migration rollback and re-apply compatibility

**Testing Scenarios:**
- ✅ Server-side timestamp defaults work correctly
- ✅ Multi-tenant isolation via RLS policies
- ✅ Index performance on composite keys
- ✅ Null constraint violations caught properly
- ✅ Connection pooling stability under load

### LiteLLM Proxy Integration

The AI Agents Platform uses **LiteLLM Proxy** as a unified LLM gateway, providing multi-provider support, automatic fallbacks, cost tracking, and virtual keys for multi-tenant deployments. LiteLLM abstracts away provider-specific implementations behind an OpenAI-compatible API.

#### What is LiteLLM?

LiteLLM is an open-source proxy that:
- **Unifies 100+ LLM providers** behind a single OpenAI-compatible API
- **Automatic fallback chain** between providers (OpenAI → Azure → Anthropic)
- **Cost tracking** and spend limits per tenant (virtual keys)
- **Retry logic** with exponential backoff (3 attempts, 2s/4s/8s delays)
- **Database persistence** for virtual keys and budget management
- **Load balancing** across multiple provider instances

#### Architecture

```
FastAPI → LiteLLM Proxy → [OpenAI (primary) → Azure (fallback) → Anthropic (fallback)]
   ↓              ↓
PostgreSQL   PostgreSQL (shared database)
```

#### Configuration Files

**docker-compose.yml** (lines 240-269):
```yaml
litellm:
  image: ghcr.io/berriai/litellm-database:main-stable
  container_name: litellm-proxy
  depends_on:
    postgres:
      condition: service_healthy
  environment:
    DATABASE_URL: postgresql://aiagents:password@postgres:5432/ai_agents
    LITELLM_MASTER_KEY: ${LITELLM_MASTER_KEY}
    LITELLM_SALT_KEY: ${LITELLM_SALT_KEY}
  volumes:
    - ./config/litellm-config.yaml:/app/config.yaml:ro
  ports:
    - "4000:4000"
  command: ["--config", "/app/config.yaml", "--detailed_debug"]
```

**config/litellm-config.yaml**:
Defines model fallback chain, retry logic, and routing strategy. All providers use `model_name: "gpt-4"` to enable automatic fallback.

#### Environment Variables

Add these to your `.env` file (already in `.env.example` lines 100-138):

```bash
# LiteLLM Master Key (admin access, changeable)
# Generate with: openssl rand -hex 16 | awk '{print "sk-" $0}'
LITELLM_MASTER_KEY=sk-25cbfca9df5c7566308044a84c541ead

# LiteLLM Salt Key (encryption key, IMMUTABLE after first use)
# Generate with: openssl rand -base64 32
# CRITICAL: Back up this key securely - loss means complete re-setup
LITELLM_SALT_KEY=your-base64-salt-key-here

# OpenAI API Key (primary provider)
OPENAI_API_KEY=sk-proj-your-openai-api-key-here

# Anthropic API Key (fallback provider, optional)
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here

# Azure OpenAI (fallback provider, optional)
AZURE_API_KEY=your-azure-api-key-here
AZURE_API_BASE=https://your-resource.openai.azure.com/
```

#### Initial Setup

**1. Generate secure keys using the setup script:**

```bash
./scripts/setup-litellm-env.sh
```

This script:
- Generates `LITELLM_MASTER_KEY` (sk-* format, changeable)
- Generates `LITELLM_SALT_KEY` (base64, IMMUTABLE, encrypts API keys in database)
- Updates `.env` file automatically
- Warns about backup requirements for LITELLM_SALT_KEY

**⚠️ CRITICAL: Back up LITELLM_SALT_KEY immediately after generation. This key encrypts provider API credentials in the database and CANNOT be changed after first use.**

**2. Configure provider API keys:**

Edit `.env` and add your provider API keys:
- `OPENAI_API_KEY` (required for primary provider)
- `ANTHROPIC_API_KEY` (optional, enables Claude fallback)
- `AZURE_API_KEY` and `AZURE_API_BASE` (optional, enables Azure fallback)

**3. Start services:**

```bash
# Start all services including LiteLLM
docker-compose up -d

# Or start LiteLLM only
docker-compose up -d litellm
```

**4. Verify health:**

```bash
# Check service is running
docker-compose ps litellm

# Check health endpoint (requires authentication)
curl -H "Authorization: Bearer $LITELLM_MASTER_KEY" http://localhost:4000/health

# View logs
docker-compose logs -f litellm
```

#### Fallback Chain Configuration

The fallback chain is automatically enabled when multiple providers share the same `model_name`:

1. **Primary: OpenAI GPT-4** (model: `openai/gpt-4`)
   - 3 retries with exponential backoff (2s, 4s, 8s)
   - 30 second timeout per request
   - Fails over to Azure after 3 consecutive failures

2. **Fallback 1: Azure OpenAI GPT-4** (model: `azure/gpt-4`)
   - Same retry configuration
   - Requires `AZURE_API_KEY` and `AZURE_API_BASE` configured
   - Fails over to Anthropic after 3 consecutive failures

3. **Fallback 2: Anthropic Claude 3.5 Sonnet** (model: `anthropic/claude-3-5-sonnet-20241022`)
   - Same retry configuration
   - Requires `ANTHROPIC_API_KEY` configured
   - Last resort provider

**Router settings:**
- `routing_strategy: simple-shuffle` - Load balances between healthy providers
- `num_retries: 2` - Router-level retries before provider fallback
- `context_window_fallbacks: true` - Switches to larger context models if needed

#### Virtual Keys (Multi-Tenant Support)

Create tenant-specific API keys with spend limits:

```bash
# Create virtual key with budget limit
curl -X POST http://localhost:4000/key/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -d '{
    "models": ["gpt-4"],
    "max_budget": 10.0,
    "duration": "30d",
    "metadata": {"tenant_id": "acme-corp"}
  }'

# Response:
{
  "key": "sk-RO8eHY9HhtQvi-uEx2w40A",
  "expires": "2025-12-05T00:00:00Z",
  "max_budget": 10.0,
  ...
}
```

**Use virtual key in application:**

```python
import openai

client = openai.OpenAI(
    api_key="sk-RO8eHY9HhtQvi-uEx2w40A",  # Virtual key from LiteLLM
    base_url="http://litellm:4000"  # LiteLLM proxy endpoint
)

response = client.chat.completions.create(
    model="gpt-4",  # Routes through fallback chain automatically
    messages=[{"role": "user", "content": "Hello!"}]
)
```

#### Database Tables

LiteLLM automatically creates 31 tables in your PostgreSQL database for managing virtual keys, budgets, users, and audit logs:

**Key tables:**
- `LiteLLM_VerificationToken` - Virtual API keys
- `LiteLLM_BudgetTable` - Spend tracking and limits
- `LiteLLM_UserTable` - User management
- `LiteLLM_SpendLogs` - Cost tracking per request
- `LiteLLM_AuditLog` - Audit trail for all operations

**Verify tables:**

```bash
docker-compose exec postgres psql -U aiagents -d ai_agents \
  -c "SELECT tablename FROM pg_tables WHERE tablename LIKE '%LiteLLM%' ORDER BY tablename;"
```

#### Testing

**Test scripts provided:**

1. **Fallback chain testing:**
   ```bash
   ./scripts/test-litellm-fallback.sh
   ```
   Tests primary provider, virtual key creation, and simulates fallback scenarios.

2. **Retry logic testing:**
   ```bash
   ./scripts/test-litellm-retry.sh
   ```
   Tests exponential backoff, timeout configuration, concurrent requests, and health checks.

**Manual testing examples:**

```bash
# Test health endpoint
curl -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  http://localhost:4000/health

# Test chat completion
curl -X POST http://localhost:4000/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 50
  }'

# Check virtual key spend
curl http://localhost:4000/key/info \
  -H "Authorization: Bearer sk-RO8eHY9HhtQvi-uEx2w40A"
```

#### Monitoring

**View LiteLLM logs:**

```bash
# Real-time logs
docker-compose logs -f litellm

# Last 100 lines
docker-compose logs --tail=100 litellm

# Search for errors
docker-compose logs litellm | grep -i error
```

**Prometheus metrics** (available at `http://localhost:4000/metrics`):

- `litellm_requests_total` - Total requests by model and status
- `litellm_request_duration_seconds` - Request latency histogram
- `litellm_spend_usd` - Cost tracking per tenant
- `litellm_deployment_state` - Provider health status

#### Troubleshooting

**LiteLLM service won't start:**

```bash
# Check if postgres is healthy (LiteLLM depends on it)
docker-compose ps postgres

# Check environment variables
docker-compose config | grep -A 10 litellm

# Check config file syntax
cat config/litellm-config.yaml

# View startup logs
docker-compose logs litellm
```

**Health endpoint returns 401 (expected):**

LiteLLM health endpoint requires authentication. This is correct behavior:

```bash
# Without auth: 401 Unauthorized
curl http://localhost:4000/health

# With auth: 200 OK with provider health status
curl -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  http://localhost:4000/health
```

**All providers show as unhealthy:**

This means API keys are invalid or not configured:

```bash
# Check if API keys are set in .env
cat .env | grep -E "OPENAI_API_KEY|ANTHROPIC_API_KEY|AZURE_API_KEY"

# Verify keys are not placeholders
# Bad: OPENAI_API_KEY=your-openai-api-key-here
# Good: OPENAI_API_KEY=sk-proj-abc123...

# Restart LiteLLM after updating keys
docker-compose restart litellm
```

**Virtual key creation fails:**

```bash
# Check database connectivity
docker-compose exec litellm curl http://localhost:4000/health

# Verify LITELLM_SALT_KEY is set (required for encryption)
docker-compose exec litellm env | grep LITELLM_SALT_KEY

# Check database tables exist
docker-compose exec postgres psql -U aiagents -d ai_agents \
  -c "SELECT COUNT(*) FROM \"LiteLLM_VerificationToken\";"
```

**Requests failing with timeout:**

```bash
# Check timeout configuration (default: 30s)
cat config/litellm-config.yaml | grep timeout

# View recent timeout errors
docker-compose logs litellm | grep -i timeout

# Test with longer timeout (if provider is slow)
# Edit config/litellm-config.yaml: timeout: 60
docker-compose restart litellm
```

**Database migration issues:**

```bash
# Check LiteLLM table count (should be 31 tables)
docker-compose exec postgres psql -U aiagents -d ai_agents \
  -c "SELECT COUNT(*) FROM pg_tables WHERE tablename LIKE '%LiteLLM%';"

# If tables missing, LiteLLM auto-creates them on startup
# Check logs for migration errors
docker-compose logs litellm | grep -i migration
```

#### API Reference

**Base URL:** `http://localhost:4000` (local) or `http://litellm:4000` (container)

**Key Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check (requires auth) |
| `/chat/completions` | POST | OpenAI-compatible chat endpoint |
| `/key/generate` | POST | Create virtual key |
| `/key/info` | GET | Get key info and spend |
| `/key/update` | POST | Update key budget/limits |
| `/key/delete` | POST | Delete virtual key |
| `/metrics` | GET | Prometheus metrics |
| `/model/info` | GET | List available models |

**Authentication:**
All endpoints require `Authorization: Bearer {key}` header:
- Admin operations: Use `LITELLM_MASTER_KEY`
- Chat completions: Use virtual key or master key

#### Production Considerations

**Security:**
- Store `LITELLM_SALT_KEY` in secure vault (AWS Secrets Manager, 1Password)
- Rotate `LITELLM_MASTER_KEY` regularly (changeable)
- Use HTTPS/TLS in production (configure Ingress)
- Restrict `/key/generate` endpoint to admin users only

**Performance:**
- Enable Redis for multi-instance deployments (cache + session state)
- Use connection pooling for database (configured by default)
- Scale horizontally with multiple LiteLLM instances behind load balancer
- Monitor queue depth and response times via Prometheus

**Cost Management:**
- Set `max_budget` on all virtual keys
- Monitor spend via `/key/info` endpoint
- Set up budget alerts in Prometheus
- Use `duration` parameter to auto-expire keys

**Disaster Recovery:**
- Back up PostgreSQL database regularly (includes virtual keys)
- Store `LITELLM_SALT_KEY` backup in multiple secure locations
- Document provider API key rotation procedures
- Test failover scenarios (provider outages)

#### Additional Resources

- **LiteLLM Documentation:** https://docs.litellm.ai/
- **Config File:** `config/litellm-config.yaml`
- **Setup Script:** `scripts/setup-litellm-env.sh`
- **Test Scripts:** `scripts/test-litellm-fallback.sh`, `scripts/test-litellm-retry.sh`
- **Docker Compose:** `docker-compose.yml` (lines 240-269)

### Running Tests in Docker

```bash
# Run all tests inside the API container
docker-compose exec api pytest

# Run with coverage
docker-compose exec api pytest --cov=src --cov-report=html

# Run specific test file
docker-compose exec api pytest tests/unit/test_config.py -v
```

## Environment Variables Reference

All environment variables must be prefixed with `AI_AGENTS_` for consistency. Copy `.env.example` to `.env` and configure as needed.

### Database Configuration

| Variable | Required | Default | Example | Description |
|----------|----------|---------|---------|-------------|
| `AI_AGENTS_DATABASE_URL` | ✅ Yes | None | `postgresql+asyncpg://aiagents:password@postgres:5432/ai_agents` | PostgreSQL async connection string. Use `postgres` for Docker, `localhost` for local dev |
| `AI_AGENTS_DATABASE_POOL_SIZE` | ❌ No | `20` | `20` | Connection pool size (1-100). Default balances throughput and memory |

### Redis Configuration

| Variable | Required | Default | Example | Description |
|----------|----------|---------|---------|-------------|
| `AI_AGENTS_REDIS_URL` | ✅ Yes | None | `redis://redis:6379/0` | Redis URL for caching. Use `redis` for Docker, `localhost` for local dev |
| `AI_AGENTS_REDIS_MAX_CONNECTIONS` | ❌ No | `10` | `10` | Maximum concurrent Redis connections (1-50) |

### Celery Configuration

| Variable | Required | Default | Example | Description |
|----------|----------|---------|---------|-------------|
| `AI_AGENTS_CELERY_BROKER_URL` | ✅ Yes | None | `redis://redis:6379/1` | Celery message broker URL. Uses Redis DB 1 to separate from cache |
| `AI_AGENTS_CELERY_RESULT_BACKEND` | ✅ Yes | None | `redis://redis:6379/1` | Celery result backend (same as broker for simplicity) |
| `AI_AGENTS_CELERY_WORKER_CONCURRENCY` | ❌ No | `4` | `4` | Number of concurrent workers per pod (1-16). Recommended: 4 for balanced throughput/memory |

### Application Configuration

| Variable | Required | Default | Example | Description |
|----------|----------|---------|---------|-------------|
| `AI_AGENTS_ENVIRONMENT` | ❌ No | `development` | `development`, `staging`, `production` | Deployment environment affects logging and behavior |
| `AI_AGENTS_LOG_LEVEL` | ❌ No | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | Application logging verbosity level |

### Optional Configuration (Future Epics)

| Variable | Required | Default | Example | Description |
|----------|----------|---------|---------|-------------|
| `AI_AGENTS_API_HOST` | ❌ No | `0.0.0.0` | `0.0.0.0` | API server bind address (Story 1.1) |
| `AI_AGENTS_API_PORT` | ❌ No | `8000` | `8000` | API server port (Story 1.1) |
| `AI_AGENTS_SERVICEDESK_API_URL` | ❌ No | None | `https://your-servicedesk.com/api/v3` | ServiceDesk Plus API endpoint (Epic 2) |
| `AI_AGENTS_SERVICEDESK_API_KEY` | ❌ No | None | `your-api-key` | ServiceDesk Plus API authentication key (Epic 2) |
| `AI_AGENTS_OPENAI_API_KEY` | ❌ No | None | `sk-...` | OpenAI API key for GPT-4 access (Epic 2) |
| `AI_AGENTS_OPENAI_MODEL` | ❌ No | `gpt-4o-mini` | `gpt-4`, `gpt-4o` | OpenAI model to use (Epic 2) |
| `AI_AGENTS_METRICS_PORT` | ❌ No | `9090` | `9090` | Prometheus metrics port (Epic 4) |

### Environment Examples

**Local Development (with Docker):**
```bash
# Database: Use service name 'postgres' instead of localhost
AI_AGENTS_DATABASE_URL=postgresql+asyncpg://aiagents:password@postgres:5432/ai_agents

# Redis: Use service name 'redis' instead of localhost
AI_AGENTS_REDIS_URL=redis://redis:6379/0
AI_AGENTS_CELERY_BROKER_URL=redis://redis:6379/1

# Application settings
AI_AGENTS_ENVIRONMENT=development
AI_AGENTS_LOG_LEVEL=DEBUG  # Verbose logging for development
```

**Local Development (without Docker):**
```bash
# Database: Use localhost instead of service name
AI_AGENTS_DATABASE_URL=postgresql+asyncpg://aiagents:password@localhost:5432/ai_agents

# Redis: Use localhost instead of service name
AI_AGENTS_REDIS_URL=redis://localhost:6379/0
AI_AGENTS_CELERY_BROKER_URL=redis://localhost:6379/1

# Ensure PostgreSQL and Redis are running locally
```

**Production (Kubernetes):**
```bash
# Use full DNS names with namespace
AI_AGENTS_DATABASE_URL=postgresql+asyncpg://aiagents:password@postgresql.ai-agents.svc.cluster.local:5432/ai_agents
AI_AGENTS_REDIS_URL=redis://redis.ai-agents.svc.cluster.local:6379/0

# Production settings
AI_AGENTS_ENVIRONMENT=production
AI_AGENTS_LOG_LEVEL=WARNING  # Reduce verbosity in production
```

### Troubleshooting

**Port already in use:**
```bash
# Check what's using the port
lsof -i :8000  # or :5433, :6379

# Update docker-compose.yml port mappings if needed
# Example: "8001:8000" instead of "8000:8000"
```

**Services not healthy:**
```bash
# Check logs for errors
docker-compose logs postgres
docker-compose logs redis
docker-compose logs api

# Restart specific service
docker-compose restart api
```

**Volume permission issues (Linux):**
```bash
# Ensure data directories have correct permissions
sudo chown -R $USER:$USER ./data
```

**Clean rebuild:**
```bash
# Remove containers, volumes, and rebuild
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Webhook Integration

The platform supports webhook integration with ServiceDesk Plus for automatic ticket ingestion. Two webhook endpoints are available:

#### 1. Enhancement Webhook (Story 2.1)
**Endpoint:** `POST /webhook/servicedesk`

Receives ticket creation/update events from ServiceDesk Plus and queues them for enhancement processing.

**Payload:**
```json
{
    "event": "ticket_created",
    "ticket_id": "TKT-001",
    "tenant_id": "acme-corp",
    "description": "Server issue",
    "priority": "high",
    "created_at": "2025-11-01T12:00:00Z"
}
```

**Response:** `202 Accepted`

#### 2. Resolved Ticket Webhook (Story 2.5B)
**Endpoint:** `POST /webhook/servicedesk/resolved-ticket`

Receives ticket resolved/closed events and stores them in `ticket_history` for context gathering.

**Payload:**
```json
{
    "tenant_id": "acme-corp",
    "ticket_id": "TKT-12345",
    "subject": "Issue title",
    "description": "Problem description",
    "resolution": "Solution applied",
    "resolved_date": "2025-11-01T14:30:00Z",
    "priority": "high",
    "tags": ["database", "performance"]
}
```

**Response:** `202 Accepted`

#### Webhook Security
All webhooks validate **HMAC-SHA256 signatures** via the `X-ServiceDesk-Signature` header.

**Configuration:**
- Set `AI_AGENTS_WEBHOOK_SECRET` environment variable (min 32 chars)
- ServiceDesk Plus must compute signature with same secret
- Invalid signatures return `401 Unauthorized`

**Setup Guide:** See [docs/webhooks/resolved-ticket-webhook-setup.md](docs/webhooks/resolved-ticket-webhook-setup.md) for detailed ServiceDesk Plus configuration.

## Plugin Architecture

The AI Agents Platform uses a plugin architecture to support multiple ticketing tools (ITSM systems) without modifying core enhancement logic. This enables seamless integration with ServiceDesk Plus, Jira Service Management, and future tools.

### Overview

**Benefits:**
- **Extensibility:** Add new ticketing tools by implementing a standard interface
- **Separation of Concerns:** Tool-specific logic isolated in plugins
- **Testability:** Independent plugin testing with mock implementations
- **Vendor Flexibility:** Switch tools or support multiple tools per tenant

### Supported Ticketing Tools

| Tool | Status | Documentation |
|------|--------|---------------|
| ServiceDesk Plus | ✅ Production | [Example](docs/plugins/plugin-examples-servicedesk.md) |
| Jira Service Management | ✅ Production | [Example](docs/plugins/plugin-examples-jira.md) |
| Zendesk | 🔄 Planned Q1 2026 | [Roadmap](docs/plugins/plugin-roadmap.md) |
| ServiceNow | 🔄 Planned Q1 2026 | [Roadmap](docs/plugins/plugin-roadmap.md) |
| Freshservice | 📋 Backlog Q2 2026 | [Roadmap](docs/plugins/plugin-roadmap.md) |
| Freshdesk | 📋 Backlog Q2 2026 | [Roadmap](docs/plugins/plugin-roadmap.md) |

### Plugin Interface

All plugins implement `TicketingToolPlugin` abstract base class with 4 methods:

```python
class TicketingToolPlugin(ABC):
    @abstractmethod
    async def validate_webhook(self, payload: Dict, signature: str) -> bool:
        """Authenticate webhook requests"""

    @abstractmethod
    async def get_ticket(self, tenant_id: str, ticket_id: str) -> Optional[Dict]:
        """Retrieve ticket from API"""

    @abstractmethod
    async def update_ticket(self, tenant_id: str, ticket_id: str, content: str) -> bool:
        """Post enhancement content"""

    @abstractmethod
    def extract_metadata(self, payload: Dict) -> TicketMetadata:
        """Normalize ticket data"""
```

### Plugin Developer Quick Start

1. **Understand the Architecture:** Read [Plugin Architecture Overview](docs/plugins/plugin-architecture-overview.md) (15 min)
2. **Follow Tutorial:** Build your first plugin with [Plugin Development Guide](docs/plugin-development-guide.md) (2-3 hours)
3. **Reference Examples:** Study [ServiceDesk Plus](docs/plugins/plugin-examples-servicedesk.md) or [Jira](docs/plugins/plugin-examples-jira.md) implementations
4. **Submit for Review:** Follow [Plugin Submission Guidelines](docs/plugins/plugin-submission-guidelines.md)

### Plugin Documentation

**Core Documentation:**
- [Plugin Architecture Overview](docs/plugins/plugin-architecture-overview.md) - Architecture patterns, benefits, design
- [Plugin Interface Reference](docs/plugins/plugin-interface-reference.md) - TicketingToolPlugin ABC, method specifications
- [Plugin Manager Guide](docs/plugins/plugin-manager-guide.md) - Dynamic loading, routing, registration

**How-To Guides:**
- [Plugin Development Guide](docs/plugin-development-guide.md) - Step-by-step Zendesk plugin tutorial
- [Plugin Type Safety Guide](docs/plugins/plugin-type-safety.md) - Type hints, mypy validation
- [Plugin Error Handling Guide](docs/plugins/plugin-error-handling.md) - Exception hierarchy, retry patterns
- [Plugin Performance Guide](docs/plugins/plugin-performance.md) - Connection pooling, caching, optimization

**Examples & Support:**
- [ServiceDesk Plus Example](docs/plugins/plugin-examples-servicedesk.md) - Complete implementation reference
- [Jira Service Management Example](docs/plugins/plugin-examples-jira.md) - Complete implementation reference
- [Plugin Testing Guide](docs/plugins/plugin-testing-guide.md) - Test strategy, coverage requirements
- [Plugin Troubleshooting Guide](docs/plugins/plugin-troubleshooting.md) - Common errors, debugging

**Planning & Contributing:**
- [Plugin Roadmap](docs/plugins/plugin-roadmap.md) - Planned features, versioning strategy
- [Plugin Submission Guidelines](docs/plugins/plugin-submission-guidelines.md) - Code review checklist, PR process
- [Plugin Documentation Index](docs/plugins/index.md) - Complete documentation navigation

### Contributing Plugins

We welcome plugin contributions for new ticketing tools! See [Plugin Submission Guidelines](docs/plugins/plugin-submission-guidelines.md) for:
- Code review checklist (10 items)
- Testing requirements (15+ unit tests, 5+ integration tests, 80%+ coverage)
- Performance standards (NFR001 compliance)
- Documentation requirements
- PR submission process

### 5. Run Database Migrations

Database migrations are automatically applied when Docker containers start. To manually apply migrations:

```bash
# If using Docker (recommended)
docker-compose exec api alembic upgrade head

# If running locally
alembic upgrade head
```

See **[Database Setup and Migrations](#database-setup-and-migrations)** section for detailed information.

### 6. Run the Application (Non-Docker)

If not using Docker, start the application directly:

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Note:** This requires PostgreSQL and Redis to be running locally on your machine.

## Kubernetes Deployment

For production deployment and running the platform on Kubernetes clusters (local development with minikube/kind or cloud platforms like EKS/GKE/AKS), see the complete deployment guide:

**[Kubernetes Deployment Guide](docs/deployment.md)**

Quick start:
```bash
# Deploy with automated validation
./k8s/test-deployment.sh

# Verify all pods are running
kubectl get pods -n ai-agents

# Access the API
kubectl port-forward -n ai-agents svc/api 8000:8000
curl http://localhost:8000/api/v1/health
```

The deployment guide includes:
- Prerequisites and cluster setup (minikube, kind, EKS/GKE/AKS)
- Step-by-step deployment instructions
- Secret management and configuration
- Scaling and performance tuning
- Monitoring and troubleshooting
- Production readiness checklist

## Admin UI (Streamlit)

The AI Agents platform includes a web-based admin interface built with Streamlit for operations teams to manage the system without kubectl access.

### Features

**Current (Story 6.1 - Foundation):**
- ✅ Multi-page navigation (Dashboard, Tenants, History)
- ✅ Basic authentication (session-based for local dev, Ingress basic auth for production)
- ✅ Database connectivity with synchronous SQLAlchemy sessions
- ✅ Kubernetes deployment manifests

**Coming Soon (Stories 6.2-6.8):**
- 📊 Real-time system metrics dashboard
- 🏢 Tenant CRUD operations
- 📜 Enhancement history viewer with filters
- ⚙️ System operations controls
- 📈 Prometheus metrics integration
- 🔍 Worker health monitoring

### Local Development

**Prerequisites:**
- Python 3.12+ with virtual environment activated
- PostgreSQL running (Docker or local)
- Environment variable `AI_AGENTS_DATABASE_URL` configured

**Run Admin UI:**

```bash
# Install dependencies (includes Streamlit)
pip install -e ".[dev]"

# Set database connection
export AI_AGENTS_DATABASE_URL="postgresql://aiagents:password@localhost:5432/ai_agents"

# Run Streamlit app
streamlit run src/admin/app.py
```

The app will be available at: **http://localhost:8501**

**Default Login:**
- Username: `admin`
- Password: `admin`

**Configure Authentication (Optional):**

Create `.streamlit/secrets.toml` from template:

```bash
cp .streamlit/secrets.toml.template .streamlit/secrets.toml
```

Edit passwords in `secrets.toml` for production-grade authentication.

### Kubernetes Deployment

**Build Docker Image:**

```bash
docker build -f docker/streamlit.dockerfile -t ai-agents-streamlit:1.0.0 .
```

**Setup Authentication:**

```bash
# Create htpasswd secret for Ingress basic auth
./scripts/setup-streamlit-auth.sh admin your-secure-password
```

**Deploy to Kubernetes:**

```bash
kubectl apply -f k8s/streamlit-admin-configmap.yaml
kubectl apply -f k8s/streamlit-admin-deployment.yaml
kubectl apply -f k8s/streamlit-admin-service.yaml
kubectl apply -f k8s/streamlit-admin-ingress.yaml
```

**Configure Local Access:**

Add to `/etc/hosts`:

```
127.0.0.1  admin.ai-agents.local
```

**Access Admin UI:**

Open browser: **http://admin.ai-agents.local**

You'll be prompted for basic authentication credentials.

### Troubleshooting

**Database Connection Issues:**

```bash
# Verify environment variable
echo $AI_AGENTS_DATABASE_URL

# Test PostgreSQL connectivity
psql $AI_AGENTS_DATABASE_URL -c "SELECT 1"
```

**Authentication Not Working (Kubernetes):**

```bash
# Verify secret exists
kubectl get secret streamlit-basic-auth -n ai-agents

# Recreate if needed
./scripts/setup-streamlit-auth.sh admin newpassword
```

**Detailed Documentation:**

See complete setup guide: **[docs/admin-ui-setup.md](docs/admin-ui-setup.md)**

## Monitoring & Metrics

The AI Agents Platform includes comprehensive Prometheus metrics for operational observability.

### Prometheus Metrics

**Local Development (Docker Compose):**
```bash
# Access Prometheus UI
http://localhost:9090

# Access raw metrics endpoint
http://localhost:8000/metrics
```

**Kubernetes Production:**
```bash
# Port-forward to Prometheus service
kubectl port-forward svc/prometheus 9090:9090

# Access Prometheus UI
http://localhost:9090

# Get metrics from FastAPI pods
kubectl exec deployment/deployment-api -- curl http://localhost:8000/metrics
```

### Available Metrics

The platform exposes the following Prometheus metrics:

- **enhancement_requests_total** - Counter of enhancement requests by tenant and status
- **enhancement_duration_seconds** - Histogram of processing latency (p50/p95/p99)
- **enhancement_success_rate** - Gauge of current success rate percentage
- **queue_depth** - Gauge of pending Redis queue jobs
- **worker_active_count** - Gauge of active Celery workers

### Documentation

For detailed metrics documentation, PromQL queries, and alerting recommendations, see:
- [Metrics Guide](docs/operations/metrics-guide.md) - Available metrics and sample PromQL queries
- [Prometheus Setup Guide](docs/operations/prometheus-setup.md) - Deployment and configuration instructions

### Grafana Dashboards

Real-time visual dashboards for monitoring platform health and performance.

**Local Development (Docker Compose):**
```bash
# Access Grafana UI
http://localhost:3000

# Default credentials
Username: admin
Password: admin
```

**Kubernetes Production:**
```bash
# Port-forward to Grafana service
kubectl port-forward svc/grafana 3000:3000

# Access Grafana UI
http://localhost:3000
```

**Default Dashboard:** "AI Agents - System Health & Performance"
- Success Rate (gauge, ≥95% = healthy)
- Queue Depth (time series, shows pending jobs)
- p95 Latency (time series, target ≤120 seconds)
- Error Rate by Tenant (table, ≥5% = critical)
- Active Celery Workers (stat, ≥1 = healthy)

**Dashboard Configuration:**
- Auto-refresh: 30 seconds
- Time range selector: 1h, 6h, 24h, 7d lookback
- Datasource: Prometheus (http://prometheus:9090)

**Documentation:** See [Grafana Setup Guide](docs/operations/grafana-setup.md) for deployment, configuration, and troubleshooting.

### Prometheus Alerting

Automated alerts for critical system failures and performance degradation.

**Alert Rules Configured:**
- **EnhancementSuccessRateLow** - Warning alert when success rate <95% for 10 minutes
- **QueueDepthHigh** - Warning alert when pending jobs >100 for 5 minutes
- **WorkerDown** - Critical alert when no active Celery workers for 2 minutes
- **HighLatency** - Warning alert when p95 latency >120 seconds for 5 minutes

**Accessing Alerts:**

Local Development:
```bash
# View alert rules and current states
http://localhost:9090/alerts
```

Kubernetes Production:
```bash
# Port-forward to Prometheus
kubectl port-forward svc/prometheus 9090:9090

# View alert rules
http://localhost:9090/alerts
```

**Alert Documentation:**
- [Alert Configuration Guide](docs/operations/prometheus-alerting.md) - Complete alerting configuration and testing procedures
- [Alert Runbooks](docs/operations/alert-runbooks.md) - Troubleshooting guides for each alert with root cause analysis and resolution steps

**Current Status:**
⚠️ Alerts currently fire in Prometheus UI only. Story 4.5 will add Alertmanager for Slack/email/PagerDuty notifications.

### Sample Queries

```promql
# p95 latency over last 5 minutes
histogram_quantile(0.95, rate(enhancement_duration_seconds_bucket[5m]))

# Error rate percentage
rate(enhancement_requests_total{status="failure"}[5m]) / rate(enhancement_requests_total[5m]) * 100

# Current queue depth
queue_depth{queue_name="enhancement:queue"}

# Success rate for specific tenant
enhancement_success_rate{tenant_id="acme"}
```

## Troubleshooting

This section covers common issues and solutions for local development and deployment.

### Docker Service Won't Start

**Symptoms:** `docker-compose up` fails or services won't start

**Possible Causes:**
- Docker Desktop not running
- Insufficient disk space
- Port conflicts with existing services
- Resource constraints (CPU/memory)

**Solutions:**

```bash
# Ensure Docker Desktop is running
docker --version

# Check available disk space
df -h

# Check for port conflicts
lsof -i :8000  # API
lsof -i :5433  # PostgreSQL
lsof -i :6379  # Redis

# Clean up unused Docker resources
docker system prune -a

# Start services with verbose logging
docker-compose up  # Remove -d flag to see logs

# Allocate more resources to Docker Desktop
# Go to Docker > Preferences > Resources
# Increase CPUs and Memory
```

**Alternative:** If ports are already in use, modify `docker-compose.yml`:
```yaml
ports:
  - "8001:8000"  # Use 8001 instead of 8000
  - "5434:5432"  # Use 5434 instead of 5433
```

### Database Connection Failures

**Symptoms:**
- `psycopg.OperationalError: connection to server at "postgres"... failed`
- `FATAL: database "ai_agents" does not exist`
- Connection timeout errors

**Solutions:**

```bash
# Check if PostgreSQL container is running
docker-compose ps postgres

# Verify PostgreSQL is accepting connections
docker-compose exec postgres pg_isready -U aiagents
# Expected: accepting connections

# Check PostgreSQL logs for errors
docker-compose logs postgres

# Verify database exists
docker-compose exec postgres psql -U aiagents -l

# Verify connection string in .env
cat .env | grep DATABASE_URL

# For local development (no Docker):
# Ensure PostgreSQL is running on localhost:5432
# Update DATABASE_URL to use localhost
export AI_AGENTS_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/ai_agents

# Test connection locally
python -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect('postgresql://user:password@localhost/ai_agents'))"
```

### Redis Connection Errors

**Symptoms:**
- `ConnectionError: Error 111 connecting to redis:6379. Connection refused.`
- Queue operations timing out
- Worker can't connect to broker

**Possible Causes:**
- Redis container not running
- Port conflicts (port 6379 already in use)
- Memory exhausted on Redis container
- Incorrect connection URL

**Solutions:**

```bash
# Check Redis container status
docker-compose ps redis

# Verify Redis is responding
docker-compose exec redis redis-cli ping
# Expected: PONG

# Check Redis logs
docker-compose logs redis

# Check Redis memory usage (in MB)
docker-compose exec redis redis-cli INFO memory | grep used_memory_human

# Clear Redis if memory is full (development only)
docker-compose exec redis redis-cli FLUSHDB

# Verify connection URL in .env
cat .env | grep REDIS_URL

# For local development without Docker:
# Ensure Redis is running on localhost:6379
redis-server --port 6379

# Test connection
redis-cli -p 6379 ping
```

### Celery Worker Not Processing Jobs

**Symptoms:**
- Jobs queued but not executing
- Worker appears offline
- Task status stays PENDING

**Solutions:**

```bash
# Check if worker container is running
docker-compose ps worker

# View worker logs
docker-compose logs -f worker

# Ping worker to verify it's alive
docker-compose exec worker celery -A src.workers.celery_app inspect ping

# List registered tasks
docker-compose exec worker celery -A src.workers.celery_app inspect registered

# Check active tasks
docker-compose exec worker celery -A src.workers.celery_app inspect active

# Check queue depth (pending jobs)
docker-compose exec redis redis-cli LLEN celery

# Restart worker if stuck
docker-compose restart worker

# Check Celery broker connection
docker-compose exec worker celery -A src.workers.celery_app inspect stats
```

### Port Conflicts on Local Machine

**Symptoms:**
- `Address already in use` when starting docker-compose
- Cannot bind to port X

**Solutions:**

```bash
# Identify which process is using the port
lsof -i :8000  # API port
lsof -i :5433  # PostgreSQL port
lsof -i :6379  # Redis port

# Kill the process (use PID from above)
kill -9 <PID>

# Or change ports in docker-compose.yml
# API: "8001:8000"
# PostgreSQL: "5434:5432"
# Redis: "6380:6379"

# Then update .env accordingly
AI_AGENTS_DATABASE_URL=postgresql+asyncpg://aiagents:password@postgres:5432/ai_agents
AI_AGENTS_REDIS_URL=redis://redis:6379/0
```

### Alembic Migration Failures

**Symptoms:**
- `FAILED: Can't locate revision identified by...`
- Migration script doesn't run
- Database schema mismatch

**Solutions:**

```bash
# Check current migration status
docker-compose exec api alembic current

# View migration history
docker-compose exec api alembic history

# Check for pending migrations
docker-compose exec api alembic upgrade --sql head

# If migration is stuck, check database directly
docker-compose exec postgres psql -U aiagents -d ai_agents \
  -c "SELECT version_num, description FROM alembic_version;"

# Rollback last migration (testing only)
docker-compose exec api alembic downgrade -1

# Re-apply migrations
docker-compose exec api alembic upgrade head

# For local development:
alembic current
alembic upgrade head
```

### Unit Tests Failing

**Symptoms:**
- Test collection errors
- Tests fail locally but pass in CI
- ImportError or module not found

**Solutions:**

```bash
# Run tests with verbose output
docker-compose exec api pytest tests/ -v --tb=short

# Run specific test file
docker-compose exec api pytest tests/unit/test_config.py -v

# Run with coverage to identify gaps
docker-compose exec api pytest --cov=src --cov-report=html

# Check for import issues
docker-compose exec api python -c "import src; print(src.__file__)"

# Verify all dependencies installed
docker-compose exec api pip list | grep -E "pytest|asyncio"

# For local development:
# Ensure virtual environment is activated
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run with asyncio support
pytest tests/ -v --asyncio-mode=auto
```

### CI/CD Pipeline Failures

**Symptoms:**
- GitHub Actions workflow failing
- Black formatting check fails
- Ruff linting finds issues
- Pytest coverage below threshold

**Solutions:**

```bash
# Format code with Black (auto-fix)
black src/ tests/

# Check linting issues
ruff check src/ tests/

# Auto-fix common linting issues
ruff check --fix src/ tests/

# Run type checking
mypy src/ --ignore-missing-imports

# Run tests with coverage threshold
pytest tests/ --cov=src --cov-fail-under=80

# Or run all checks at once
docker-compose exec api bash -c \
  "black src/ tests/ && \
   ruff check --fix src/ tests/ && \
   mypy src/ && \
   pytest tests/ --cov=src --cov-fail-under=80"

# View workflow logs in GitHub Actions
# Go to: https://github.com/nullBytes/AI-Ops/actions
```

### Kubernetes Deployment Issues

**Symptoms:**
- Pods stuck in Pending
- ImagePullBackOff errors
- CrashLoopBackOff status
- Services not accessible

**Solutions:**

See the comprehensive **[Kubernetes Deployment Guide](docs/deployment.md#monitoring-and-troubleshooting)** for detailed K8s troubleshooting including:
- Common issues and solutions
- Pod debugging commands
- Log analysis
- Network diagnostics

## Project Structure

```
AI Ops/
├── src/                    # Application source code
│   ├── api/               # FastAPI endpoints and middleware
│   ├── database/          # SQLAlchemy models and session management
│   ├── cache/             # Redis client and caching utilities
│   ├── services/          # Business logic and service layer
│   ├── workers/           # Celery tasks and worker configuration
│   ├── enhancement/       # LangGraph workflow and context gatherers
│   ├── monitoring/        # Prometheus metrics instrumentation
│   ├── utils/             # Cross-cutting concerns (logging, exceptions)
│   └── schemas/           # Pydantic models for validation
├── tests/                 # Test suite
│   ├── unit/             # Fast, isolated unit tests
│   ├── integration/      # Multi-component integration tests
│   └── conftest.py       # Shared pytest fixtures
├── docs/                  # Documentation
│   ├── architecture.md   # Architecture decisions and patterns
│   ├── PRD.md           # Product requirements document
│   └── epics.md         # Epic and story breakdown
├── docker/               # Dockerfiles for containerization
├── k8s/                  # Kubernetes manifests for deployment
├── alembic/              # Database migration scripts
├── pyproject.toml        # Project dependencies and configuration
├── .env.example          # Environment variable template
└── README.md            # This file
```

## Development Tools

### Code Formatting

```bash
black src/ tests/
```

### Linting

```bash
ruff check src/ tests/
```

### Type Checking

```bash
mypy src/
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_config.py -v
```

## CI/CD Pipeline

This project uses GitHub Actions for automated testing, linting, type checking, and Docker image builds.

### Workflow Overview

The CI/CD pipeline is defined in `.github/workflows/ci.yml` and runs automatically on:
- **Pull Requests to `main` branch** - Runs code quality checks and tests (no Docker push)
- **Commits to `main` branch** - Runs all checks and pushes Docker images to registry

### Automated Checks

The pipeline performs the following checks on every PR and commit:

1. **Code Formatting (Black)**
   - Enforces consistent Python code formatting per PEP8
   - All code must be formatted with `black` (line-length=100)

2. **Linting (Ruff)**
   - Fast linter checking for code quality issues and security patterns
   - Detects unused imports, undefined variables, and common mistakes
   - Configuration: `E`, `F`, `I`, `N`, `W` rule sets enabled

3. **Type Checking (Mypy)**
   - Static type checking with strict mode enabled
   - Catches type errors before runtime
   - Validates all function signatures and variable types

4. **Unit Tests (Pytest)**
   - Runs all tests in `tests/` directory
   - Generates coverage report (HTML and XML formats)
   - **Must maintain 80%+ code coverage** (CI fails if below threshold)

5. **Docker Image Build**
   - Builds API and Worker Docker images using existing Dockerfiles
   - Tags images with commit SHA for traceability
   - **Only pushes to registry on `main` branch** (not on PRs)

### Running Checks Locally Before Pushing

To avoid CI failures, run these commands before committing:

```bash
# Auto-format code
black src/ tests/

# Check for linting issues
ruff check src/ tests/

# Run type checking
mypy src/ --ignore-missing-imports

# Run all tests with coverage check
pytest tests/ --cov=src --cov-fail-under=80

# Alternative: Run everything at once
docker-compose exec api bash -c "black src/ tests/ && ruff check src/ tests/ && mypy src/ && pytest tests/ --cov=src --cov-fail-under=80"
```

### Troubleshooting CI Failures

**Black formatting check fails:**
```bash
# Auto-fix formatting issues
black src/ tests/
```

**Ruff linting fails:**
```bash
# Auto-fix common issues
ruff check --fix src/ tests/

# View detailed error messages
ruff check src/ tests/ --show-settings
```

**Mypy type checking fails:**
- Add type hints to function parameters and return values
- Use proper type annotations for variables
- See [mypy docs](https://mypy.readthedocs.io/) for guidance

**Pytest fails or coverage is too low:**
```bash
# Run tests locally with detailed output
pytest tests/ -v --cov=src --cov-report=html

# Open coverage report in browser
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
```

**Docker build fails:**
```bash
# Test Docker builds locally
docker build -f docker/backend.dockerfile -t ai-agents-api:test .
docker build -f docker/celeryworker.dockerfile -t ai-agents-worker:test .
```

### Docker Image Registry

Docker images are pushed to **GitHub Container Registry (ghcr.io)**:

- **Advantages:**
  - Integrated GitHub authentication (uses GITHUB_TOKEN)
  - Free for public repositories
  - Images linked directly to GitHub repository
  - No rate limits

- **Image Naming Convention:**
  ```
  ghcr.io/{repository}/ai-agents-api:latest
  ghcr.io/{repository}/ai-agents-api:{commit_sha}
  ghcr.io/{repository}/ai-agents-worker:latest
  ghcr.io/{repository}/ai-agents-worker:{commit_sha}
  ```

- **Pulling Images Locally:**
  ```bash
  docker pull ghcr.io/nullBytes/AI-Ops/ai-agents-api:latest
  ```

### Workflow Performance

**Expected Runtime:**
- PR workflow (no Docker push): ~5 minutes
  - Setup: 1m
  - Linting: 30s
  - Tests: 1m
  - Docker build: 2.5m

- Main branch workflow (with push): ~7 minutes
  - All above plus 2m for registry push

**Performance Optimizations:**
- Dependencies cached based on `pyproject.toml` hash (saves ~30s)
- Docker layer caching via Buildx (saves ~60s)
- Concurrent job execution where possible
- 15-minute timeout per job prevents hung workflows

### Workflow Security Best Practices

1. **Minimal Permissions:**
   - `contents: read` - Required to checkout code
   - `packages: write` - Required to push Docker images

2. **Secrets Management:**
   - Uses `secrets.GITHUB_TOKEN` (automatically provided by GitHub)
   - Never hardcodes credentials in workflow file

3. **Action Versions:**
   - All actions pinned to specific versions (e.g., `@v4`, `@v5`)
   - Prevents unexpected behavior from action updates

### Monitoring and Badges

The CI/CD status badge at the top of this README shows the current pipeline status:

- ✅ **Passing** - All checks passed on latest main branch commit
- ❌ **Failing** - One or more checks failed
- 🔄 **In Progress** - Workflow currently running

Click the badge to view detailed workflow results and logs in GitHub Actions.

### Future Enhancements

Potential improvements for later phases:
- Add security scanning (Trivy for Docker images, CodeQL for code)
- Add dependency vulnerability scanning (Dependabot)
- Add performance benchmarks and trend analysis
- Integrate with SonarQube for advanced code quality metrics
- Add staging environment deployment
- Multi-Python version testing (3.12, 3.13)

## Documentation

- [Architecture Decision Document](docs/architecture.md) - System design, technology choices, and patterns
- [Product Requirements Document](docs/PRD.md) - Product vision, goals, and user stories
- [Epic Breakdown](docs/epics.md) - Detailed epic and story planning

## Contributing

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for comprehensive guidelines on:

- **Development Workflow** - Fork, branch, commit, and PR process
- **Code Style** - PEP8, Black formatting, Ruff linting, Mypy type checking
- **Testing Requirements** - Pytest framework, 80% coverage minimum
- **Pre-commit Hooks** - Optional automated checks before committing
- **Branch Naming** - Consistent naming conventions for features, bugfixes, etc.
- **Commit Messages** - Clear, descriptive commit message format
- **Pull Request Process** - PR guidelines and code review expectations
- **Adding Dependencies** - How to safely add new packages
- **Development Methodology** - Story-based development with BMAD workflow

**Quick Summary:**
1. Follow PEP 8 style guide with Black auto-formatting
2. Use type hints for all functions (Mypy strict mode)
3. Write unit and integration tests (80% coverage minimum)
4. Run quality checks before committing:
   ```bash
   black src/ tests/
   ruff check --fix src/ tests/
   mypy src/
   pytest tests/ --cov=src --cov-fail-under=80
   ```
5. All tests must pass in CI/CD pipeline

## Current Status

**Epic 1: Foundation & Infrastructure Setup** - In Progress

This is an early-stage project. Core infrastructure and development patterns are being established in Epic 1 before implementing the enhancement workflow in Epic 2.

## License

**Note:** License information to be added.
