# Epic Technical Specification: Foundation & Infrastructure Setup

Date: 2025-11-01
Author: Ravi
Epic ID: 1
Status: Draft

---

## Overview

Epic 1 establishes the foundational infrastructure for the AI enhancement platform, delivering a complete local development environment and production-ready deployment configuration. This epic builds the technical foundation upon which all subsequent features will be constructed, including project structure, containerization, database layer, message queuing infrastructure, worker processes, Kubernetes deployment manifests, and CI/CD automation.

By the end of this epic, developers will have a fully functional development environment where they can run the entire stack locally using Docker Compose, and DevOps teams will have production-ready Kubernetes manifests that can deploy the platform to any managed Kubernetes cluster (EKS, GKE, AKS). The system will be capable of receiving and storing basic data through its API layer, even though the enhancement logic will be implemented in Epic 2.

---

## Objectives and Scope

**In Scope:**

- Complete Python project structure with dependencies managed via pyproject.toml
- Docker containers for FastAPI application, PostgreSQL, Redis, and Celery workers
- PostgreSQL database with initial schema (tenant_configs, enhancement_history) and row-level security
- Redis message queue configured for job processing with persistence
- Celery worker setup with retry logic and concurrency configuration
- Kubernetes deployment manifests for all components (API, workers, database, Redis)
- GitHub Actions CI/CD pipeline for automated testing, linting, and Docker image builds
- Comprehensive documentation for local development and Kubernetes deployment

**Out of Scope:**

- Enhancement workflow logic (Epic 2)
- ServiceDesk Plus webhook integration (Epic 2)
- LangGraph AI orchestration (Epic 2)
- Multi-tenant security implementation (Epic 3)
- Monitoring and observability stack (Epic 4)
- Production deployment to cloud providers (Epic 5)

---

## System Architecture Alignment

This epic implements the foundational layer of the architecture defined in architecture.md:

**Core Technologies Initialized:**
- Python 3.12 with FastAPI 0.104+ for the API layer
- PostgreSQL 17 with SQLAlchemy 2.0+ ORM and Alembic migrations
- Redis 7.x as message broker and caching layer
- Celery 5.x for distributed task processing
- Docker and Docker Compose for containerization
- Kubernetes 1.28+ manifests for production deployment

**Architecture Patterns Established:**
- Async-first approach using FastAPI and asyncio
- Message queue pattern for decoupling webhook receipt from processing
- Container-based deployment for consistency across environments
- Infrastructure-as-code for reproducible deployments

**Key Constraints Adhered To:**
- All services must be containerized (Docker requirement)
- Database must support row-level security for multi-tenancy (PostgreSQL requirement)
- Worker processes must scale horizontally (Celery + Kubernetes HPA requirement)
- Development environment must match production closely (Docker Compose mirrors K8s structure)

---

## Detailed Design

### Services and Modules

| Service/Module | Responsibility | Inputs | Outputs | Owner/Location |
|---------------|----------------|--------|---------|----------------|
| **FastAPI Application** | HTTP API server with health checks and basic endpoints | HTTP requests | JSON responses | src/main.py, src/api/ |
| **PostgreSQL Database** | Persistent storage for tenant configs and enhancement history | SQL queries via SQLAlchemy | Query results | Docker container, src/database/ |
| **Redis Queue** | Message broker for job queuing and caching | Job payloads, cache keys | Job data, cached values | Docker container, src/cache/ |
| **Celery Workers** | Asynchronous task processing (placeholder tasks for Epic 1) | Jobs from Redis queue | Task results, logs | Docker container, src/workers/ |
| **Alembic Migrations** | Database schema version control | Migration scripts | Applied schema changes | alembic/, alembic.ini |
| **Docker Compose** | Local development orchestration | docker-compose.yml | Running stack | docker-compose.yml |
| **Kubernetes Manifests** | Production deployment configuration | YAML manifests | Deployed resources | k8s/ |
| **GitHub Actions** | CI/CD automation | Code commits, PRs | Test results, Docker images | .github/workflows/ |

### Data Models and Contracts

**Tenant Configuration Model:**
```python
# src/database/models.py
from sqlalchemy import Column, String, Text, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
import uuid

class TenantConfig(Base):
    __tablename__ = "tenant_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    servicedesk_url = Column(String(500), nullable=False)
    servicedesk_api_key_encrypted = Column(Text, nullable=False)
    webhook_signing_secret_encrypted = Column(Text, nullable=False)
    enhancement_preferences = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

**Enhancement History Model:**
```python
class EnhancementHistory(Base):
    __tablename__ = "enhancement_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(100), nullable=False, index=True)
    ticket_id = Column(String(100), nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True)  # pending, completed, failed
    context_gathered = Column(JSON)
    llm_output = Column(Text)
    error_message = Column(Text)
    processing_time_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
```

**Pydantic Configuration Model:**
```python
# src/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str
    database_pool_size: int = 20

    # Redis
    redis_url: str
    redis_max_connections: int = 10

    # Celery
    celery_broker_url: str
    celery_result_backend: str

    # Application
    environment: str = "development"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_prefix = "AI_AGENTS_"

settings = Settings()
```

### APIs and Interfaces

**Health Check Endpoints (Story 1.1):**

```python
# src/api/health.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0"
    }

@router.get("/health/ready")
async def readiness_check():
    """Readiness check including dependency validation."""
    db_status = await check_database_connection()
    redis_status = await check_redis_connection()

    return {
        "status": "ready" if all([db_status, redis_status]) else "not_ready",
        "dependencies": {
            "database": "connected" if db_status else "disconnected",
            "redis": "connected" if redis_status else "disconnected"
        }
    }
```

**Database Session Management:**

```python
# src/database/session.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    pool_pre_ping=True,
    echo=settings.environment == "development"
)

async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_async_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session
```

**Redis Connection:**

```python
# src/cache/redis_client.py
import redis.asyncio as redis

redis_client = redis.from_url(
    settings.redis_url,
    max_connections=settings.redis_max_connections,
    decode_responses=True
)

async def get_redis():
    return redis_client
```

**Celery Application Configuration:**

```python
# src/workers/celery_app.py
from celery import Celery

celery_app = Celery(
    "ai_agents",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=120,
    task_soft_time_limit=100
)
```

### Workflows and Sequencing

**Local Development Workflow:**
1. Developer clones repository
2. Copies `.env.example` to `.env` and configures local values
3. Runs `docker-compose up` to start all services
4. Services start in order: PostgreSQL → Redis → API → Workers
5. Alembic migrations run automatically on API startup
6. Developer accesses API at http://localhost:8000
7. Developer runs tests: `docker-compose exec api pytest`
8. Code changes trigger hot-reload in API container

**Database Migration Workflow:**
1. Developer modifies SQLAlchemy models in `src/database/models.py`
2. Generates migration: `alembic revision --autogenerate -m "description"`
3. Reviews generated migration in `alembic/versions/`
4. Tests migration: `alembic upgrade head`
5. Tests rollback: `alembic downgrade -1`
6. Commits migration file to git
7. CI pipeline validates migration on pull request

**CI/CD Pipeline Workflow:**
1. Developer pushes code or creates pull request
2. GitHub Actions triggers workflow
3. Linting runs: Black (formatting check), Ruff (code quality)
4. Type checking runs: Mypy validates type hints
5. Unit tests run: Pytest with coverage report
6. Docker image builds and tags
7. On main branch merge: Image pushed to container registry
8. Workflow status badge updates in README

---

## Non-Functional Requirements

### Performance

**Database Connection Pooling:**
- Min pool size: 5 connections
- Max pool size: 20 connections per service
- Connection timeout: 30 seconds
- Pool pre-ping enabled for stale connection detection

**Redis Performance:**
- Max connections: 10 per service
- Connection pool timeout: 5 seconds
- Persistence: AOF (Append-Only File) for durability
- Max memory: 2GB (local), 8GB (production)
- Eviction policy: allkeys-lru

**Celery Worker Configuration:**
- Concurrency: 4 workers per pod (configurable via env var)
- Prefetch multiplier: 1 (process one task at a time for memory efficiency)
- Task time limit: 120 seconds hard limit
- Soft time limit: 100 seconds (allows graceful cleanup)

**Startup Time Targets:**
- API container: <30 seconds from start to ready
- Worker container: <15 seconds from start to ready
- Database migrations: <10 seconds for typical schema changes

### Security

**Environment Variables:**
- All sensitive values (passwords, API keys) stored in .env (local) or K8s Secrets (production)
- .env file git-ignored to prevent credential leakage
- .env.example provides template with placeholder values

**Database Security:**
- PostgreSQL user with limited privileges (no superuser)
- SSL mode required in production
- Row-level security policies defined (enforced in Epic 3)
- Password stored in environment variables, never hardcoded

**Docker Security:**
- Non-root user in containers (USER directive)
- Multi-stage builds to minimize image size and attack surface
- Official base images only (python:3.12-slim)
- Regular security scanning in CI pipeline (future enhancement)

**Code Quality:**
- Black enforces consistent formatting
- Ruff catches common security issues (SQL injection patterns, hardcoded secrets)
- Mypy ensures type safety
- .gitignore prevents accidental commits of .env, __pycache__, etc.

### Reliability/Availability

**Health Checks:**
- Liveness probe: `/health` endpoint (checks API is responding)
- Readiness probe: `/health/ready` endpoint (checks API + dependencies)
- Kubernetes uses probes to restart unhealthy pods

**Database Resilience:**
- Connection pool with automatic retry on transient failures
- Pool pre-ping detects stale connections before use
- Alembic migrations are idempotent (safe to re-run)

**Worker Resilience:**
- Celery retry logic: Max 3 attempts with exponential backoff (2s, 4s, 8s)
- Task acknowledgement after processing (prevents message loss)
- Dead letter queue for permanently failed tasks (future enhancement)

**Container Restart Policies:**
- Docker Compose: restart: unless-stopped
- Kubernetes: restartPolicy: Always

### Observability

**Logging Configuration:**
- Loguru with structured JSON output
- Log levels: DEBUG (dev only), INFO, WARNING, ERROR, CRITICAL
- All logs include timestamp, service name, environment
- Container logs sent to stdout/stderr (12-factor app pattern)

**Monitoring Readiness:**
- Health check endpoints for monitoring integration
- Database connection metrics available via SQLAlchemy instrumentation
- Redis metrics available via redis-py
- Celery task metrics exported (future Prometheus integration in Epic 4)

**Development Debugging:**
- SQLAlchemy echo mode in development (logs all SQL queries)
- Loguru colorized console output for readability
- Docker Compose logs aggregated and color-coded by service
- Hot-reload enabled for rapid iteration

---

## Dependencies and Integrations

**Python Dependencies (pyproject.toml):**

```toml
[project]
name = "ai-agents"
version = "1.0.0"
requires-python = ">=3.12"

dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "sqlalchemy[asyncio]>=2.0.23",
    "alembic>=1.12.1",
    "asyncpg>=0.29.0",
    "redis>=5.0.1",
    "celery[redis]>=5.3.4",
    "httpx>=0.25.2",
    "loguru>=0.7.2",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.3",
    "pytest-asyncio>=0.21.1",
    "black>=23.11.0",
    "ruff>=0.1.6",
    "mypy>=1.7.1",
]
```

**Docker Base Images:**
- `python:3.12-slim` - Debian-based Python runtime (API and workers)
- `postgres:17-alpine` - PostgreSQL database
- `redis:7-alpine` - Redis message broker and cache

**External Services:**
- None in Epic 1 (ServiceDesk Plus and OpenAI integrated in Epic 2)

**Internal Service Dependencies:**
- API depends on: PostgreSQL, Redis
- Workers depend on: PostgreSQL, Redis (via Celery broker)
- All services depend on: .env configuration

**Development Tools:**
- Docker Desktop or Docker Engine 24+
- Docker Compose v2+
- Git 2.30+
- Python 3.12+ (for local development without Docker)

---

## Acceptance Criteria (Authoritative)

**AC1: Project Structure and Dependencies**
- Project directory structure matches architecture.md specification
- pyproject.toml defines all core dependencies with correct versions
- Virtual environment can be created and dependencies installed successfully
- .gitignore configured to exclude .env, __pycache__, venv/, *.pyc
- README.md includes setup instructions for local development

**AC2: Docker Development Environment**
- docker-compose.yml defines services: postgres, redis, api, worker
- All services start successfully with `docker-compose up`
- API accessible at http://localhost:8000
- API health check returns 200 OK at /health endpoint
- Volume mounts configured for hot-reload (src/ directory)
- Environment variables loaded from .env file

**AC3: Database Setup and Migrations**
- PostgreSQL container runs with version 17
- Database initialized with name "ai_agents"
- Alembic configured with initial migration
- tenant_configs table created with correct schema
- enhancement_history table created with correct schema
- Database migrations can be applied: `alembic upgrade head`
- Database migrations can be rolled back: `alembic downgrade -1`
- SQLAlchemy models defined for both tables

**AC4: Redis Queue Configuration**
- Redis container runs with version 7.x
- Redis accessible from API and worker containers
- AOF persistence configured (data survives container restart)
- Redis health check command succeeds: `redis-cli ping` returns PONG
- Basic queue operations work: push, pop, peek

**AC5: Celery Worker Setup**
- Celery worker container starts successfully
- Worker connects to Redis broker
- Basic test task executes and returns result
- Worker logs visible via `docker-compose logs worker`
- Worker auto-restarts on code changes (development mode)
- Concurrency set to 4 workers
- Retry logic configured with exponential backoff

**AC6: Kubernetes Manifests**
- Namespace manifest created: ai-agents.yaml
- Deployment manifests for: api, worker, postgres, redis
- Service manifests for: api, postgres, redis
- ConfigMap manifest for non-sensitive configuration
- Secret manifest template created (secrets.yaml.example)
- Resource requests and limits defined for all deployments
- All manifests apply successfully to local K8s cluster (minikube/kind)
- Pods start and pass readiness checks

**AC7: CI/CD Pipeline**
- GitHub Actions workflow file created: .github/workflows/ci.yml
- Workflow triggers on pull requests and main branch commits
- Linting step runs: Black format check, Ruff linting
- Type checking step runs: Mypy validation
- Unit test step runs: Pytest with coverage report
- Docker build step completes successfully
- Workflow status badge added to README
- Pipeline passes for test commit

**AC8: Documentation**
- README.md includes: prerequisites, local setup steps, running tests
- docs/deployment.md created with Kubernetes deployment instructions
- Environment variable documentation with .env.example
- Troubleshooting section for common issues (port conflicts, permission errors)
- New developer can follow docs and run system in <30 minutes

---

## Traceability Mapping

| Acceptance Criteria | Spec Section | Components/APIs | Test Strategy |
|---------------------|--------------|-----------------|---------------|
| AC1: Project Structure | Detailed Design > Services and Modules | src/, tests/, docker/, k8s/ directories | Manual verification + CI validation |
| AC2: Docker Environment | Detailed Design > Workflows and Sequencing | docker-compose.yml, Dockerfiles | Integration test: `docker-compose up` succeeds |
| AC3: Database Setup | Detailed Design > Data Models | models.py, alembic/, PostgreSQL container | Unit tests for models, migration smoke test |
| AC4: Redis Queue | Detailed Design > APIs and Interfaces | redis_client.py, Redis container | Unit tests for queue operations |
| AC5: Celery Workers | Detailed Design > APIs and Interfaces | celery_app.py, workers/tasks.py | Integration test: task execution |
| AC6: Kubernetes Manifests | System Architecture Alignment | k8s/*.yaml manifests | Manual: apply to minikube, verify pods ready |
| AC7: CI/CD Pipeline | NFR > Observability | .github/workflows/ci.yml | Pipeline execution on test PR |
| AC8: Documentation | All sections | README.md, docs/*.md | New developer onboarding test |

---

## Risks, Assumptions, Open Questions

**Risks:**

1. **Risk:** Database migrations may fail in production if schema changes are complex
   - **Mitigation:** Test all migrations on staging data, implement rollback procedures, include migration dry-run in CI

2. **Risk:** Docker Compose performance may be slow on older developer machines
   - **Mitigation:** Provide resource limit recommendations, document minimum system requirements (8GB RAM, 4 cores)

3. **Risk:** Kubernetes manifest versions may drift from local Docker Compose configuration
   - **Mitigation:** Use same container images for both environments, document parity requirements in deployment.md

4. **Risk:** CI/CD pipeline may have insufficient test coverage to catch regressions
   - **Mitigation:** Establish 80% coverage requirement, expand tests in Epic 2

**Assumptions:**

1. **Assumption:** Developers have Docker Desktop installed and running
   - **Validation:** Document installation as prerequisite in README

2. **Assumption:** Production Kubernetes cluster will be managed service (EKS/GKE/AKS)
   - **Validation:** Confirm with stakeholders before Epic 5

3. **Assumption:** .env file approach sufficient for local development secrets management
   - **Validation:** Acceptable for Epic 1, migrate to more robust solution if needed

4. **Assumption:** PostgreSQL and Redis persistence requirements met by default Docker volumes
   - **Validation:** Test container restart scenarios, document backup procedures

**Open Questions:**

1. **Question:** Should we use multi-arch Docker builds (amd64 + arm64) for M1/M2 Mac compatibility?
   - **Next Step:** Test on M1 Mac, add multi-arch build if issues found

2. **Question:** What is the preferred container registry (Docker Hub, GitHub Container Registry, ECR)?
   - **Next Step:** Decide in Story 1.7 based on CI/CD requirements

3. **Question:** Should Alembic migrations run automatically on container startup or manually triggered?
   - **Next Step:** Auto-run in development (Story 1.3), manual in production (Epic 5)

---

## Test Strategy Summary

**Unit Testing (Pytest):**
- **Coverage Target:** 80% for all Python modules
- **Frameworks:** pytest, pytest-asyncio for async tests
- **Mocking:** Use pytest fixtures for database, Redis, external dependencies
- **Scope:** Individual functions, classes, and modules

**Integration Testing:**
- **Database Tests:** Verify SQLAlchemy models, migrations, and queries
- **API Tests:** FastAPI TestClient for endpoint validation
- **Worker Tests:** Celery task execution with test broker
- **Scope:** Multi-component interactions within the system

**System Testing:**
- **Docker Compose Smoke Test:** `docker-compose up` completes, all services healthy
- **Kubernetes Smoke Test:** Manifests apply, pods reach ready state
- **Health Check Validation:** `/health` and `/health/ready` return expected responses
- **Scope:** Full stack validation

**Manual Testing:**
- **Documentation Validation:** New developer follows README to set up environment
- **Performance Baseline:** Measure startup times, connection pool behavior
- **Failure Scenarios:** Test container restarts, network interruptions

**CI Pipeline Tests:**
- **Linting:** Black, Ruff on all code changes
- **Type Checking:** Mypy validates type hints
- **Automated Tests:** All pytest tests run on every PR
- **Docker Build:** Verify images build successfully

**Test Data:**
- Sample tenant configurations
- Mock job payloads for queue testing
- Test migration scripts with sample data

**Success Criteria:**
- All unit tests pass with >80% coverage
- Integration tests demonstrate working database, Redis, and API
- Smoke tests validate full stack functionality
- Documentation enables new developer setup in <30 minutes
- CI pipeline green for at least 3 consecutive runs
