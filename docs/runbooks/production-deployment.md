# Production Deployment Runbook

**Document Version:** 1.0
**Last Updated:** November 20, 2025
**Story:** 4-8 Testing, Deployment, and Rollout - AC-4
**Status:** ✅ ACTIVE

## Table of Contents

1. [Overview](#overview)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Deployment Targets](#deployment-targets)
4. [Deployment Procedures](#deployment-procedures)
5. [Post-Deployment Validation](#post-deployment-validation)
6. [Rollback Triggers](#rollback-triggers)
7. [Communication Protocols](#communication-protocols)
8. [Appendix](#appendix)

---

## Overview

### Purpose

This runbook provides step-by-step procedures for deploying the AI Agents Platform to production environments. It covers both Render.com cloud deployments and self-hosted Docker deployments.

### Scope

- **In Scope**: FastAPI API, Celery workers, database migrations, secrets management, health checks
- **Out of Scope**: Infrastructure provisioning (Kubernetes clusters, cloud accounts), DNS configuration
- **Related Documents**: [Rollback Procedures](./rollback-procedures.md), [OWASP Security Testing Report](../security/owasp-security-testing-report.md)

### Architecture Overview

**Services Deployed:**
- **FastAPI API** (port 8000): REST API with OpenTelemetry tracing
- **Celery Worker**: Background task processing (4 workers default)
- **PostgreSQL 17**: Primary database with Row-Level Security (RLS)
- **Redis 7**: Cache and message broker
- **HMAC Proxy** (port 3000): Webhook signature validation proxy
- **LiteLLM Proxy** (port 4000): Unified LLM gateway
- **Streamlit Admin** (port 8501): Operations dashboard
- **Prometheus** (port 9091): Metrics collection
- **Grafana** (port 3002): Monitoring dashboards
- **Jaeger** (port 16686): Distributed tracing
- **Alertmanager** (port 9093): Alert routing

### Deployment Frequency

- **Hotfixes**: As needed (critical security/stability issues)
- **Regular Releases**: Weekly (Tuesdays 10:00 UTC)
- **Major Versions**: Monthly (First Tuesday of month)

### Required Access

- GitHub repository write access
- Render.com account with project access (for cloud deployment)
- Docker Hub account (for self-hosted)
- PostgreSQL admin credentials
- Secrets management access (environment variables)

---

## Pre-Deployment Checklist

### 1. Code Readiness

- [ ] **All Tests Pass**
  ```bash
  # Run full test suite with coverage
  pytest tests/ --cov=src --cov-report=term-missing --cov-report=html -v
  ```
  - **Required**: >80% coverage, 0 test failures
  - **Location**: `htmlcov/index.html` for detailed report

- [ ] **Security Scan Clean**
  ```bash
  # Run Bandit SAST scan
  bandit -r src/ -f json -o bandit-report.json
  python parse_bandit_report.py
  ```
  - **Required**: 0 HIGH severity issues
  - **Acceptable**: MEDIUM/LOW issues reviewed and documented

- [ ] **Type Checking Passes**
  ```bash
  # Run mypy strict type checking
  mypy src/ --strict --ignore-missing-imports
  ```
  - **Required**: 0 type errors

- [ ] **Code Formatting**
  ```bash
  # Verify code formatted with Black
  black src/ tests/ --check
  ```
  - **Required**: All files compliant

- [ ] **Integration Tests Pass**
  ```bash
  # Run integration test suite (<5 min)
  pytest tests/integration/ -v --tb=short
  ```
  - **Required**: All integration scenarios pass

### 2. Database Readiness

- [ ] **Migration Scripts Validated**
  ```bash
  # Check pending migrations
  alembic current
  alembic history

  # Dry-run migration on staging database
  alembic upgrade head --sql > migration-preview.sql
  ```
  - **Review**: Inspect `migration-preview.sql` for destructive operations
  - **Backup**: Create database backup before migration (see step 3)

- [ ] **Backward Compatibility**
  - [ ] New migrations are additive (no column drops)
  - [ ] Old code can run against new schema for rollback safety
  - [ ] Foreign key constraints validated

- [ ] **RLS Policies Validated**
  ```sql
  -- Verify RLS enabled on tenant-scoped tables
  SELECT schemaname, tablename, rowsecurity
  FROM pg_tables
  WHERE schemaname = 'public' AND rowsecurity = true;

  -- Test RLS with sample tenant
  SET app.current_tenant_id = 'test-tenant';
  SELECT count(*) FROM agents WHERE tenant_id = 'test-tenant';
  ```

### 3. Backup Strategy

- [ ] **Database Backup**
  ```bash
  # Local development backup
  docker-compose exec postgres pg_dump -U aiagents ai_agents > backup-$(date +%Y%m%d-%H%M%S).sql

  # Render.com production backup (via dashboard or CLI)
  render pg-backup ai-ops-postgres
  ```
  - **Retention**: 7 days for development, 30 days for production
  - **Verification**: Test restore on separate instance

- [ ] **Redis Snapshot**
  ```bash
  # Trigger Redis BGSAVE
  docker-compose exec redis redis-cli BGSAVE

  # Copy RDB file
  docker cp ai-agents-redis:/data/dump.rdb ./backup-redis-$(date +%Y%m%d-%H%M%S).rdb
  ```

- [ ] **Configuration Backup**
  ```bash
  # Backup environment variables (encrypted secrets excluded)
  cp .env .env.backup-$(date +%Y%m%d-%H%M%S)

  # Export Render environment variables
  render env list ai-ops-api > render-env-backup-$(date +%Y%m%d-%H%M%S).txt
  ```

### 4. Secrets and Environment Variables

- [ ] **Secrets Validated**
  - [ ] `AI_AGENTS_ENCRYPTION_KEY` (Fernet symmetric key, 44 chars base64)
  - [ ] `AI_AGENTS_ADMIN_API_KEY` (UUID or 32-char random string)
  - [ ] `AI_AGENTS_WEBHOOK_SECRET` (HMAC secret, min 25 chars)
  - [ ] `OPENAI_API_KEY` or `AI_AGENTS_OPENAI_API_KEY`
  - [ ] `ANTHROPIC_API_KEY` (optional, for Claude models)
  - [ ] `LITELLM_MASTER_KEY` (LiteLLM proxy authentication)
  - [ ] `SECRET_KEY` (FastAPI session secret, 32+ chars)

- [ ] **Database Connection Strings**
  ```bash
  # Verify format (asyncpg driver for SQLAlchemy async)
  # postgresql+asyncpg://user:password@host:port/database
  echo $AI_AGENTS_DATABASE_URL | grep -E '^postgresql\+asyncpg://'
  ```

- [ ] **Redis Connection Strings**
  ```bash
  # Verify format
  # redis://host:port/db_number
  echo $AI_AGENTS_REDIS_URL | grep -E '^redis://'
  ```

- [ ] **Tenant Configuration**
  - [ ] `DEFAULT_TENANT_ID` set to valid UUID
  - [ ] Admin tenant exists in database with active status

### 5. Infrastructure Readiness

- [ ] **Docker Images Built**
  ```bash
  # Build and tag production images
  docker build -f docker/backend.dockerfile -t ai-agents-api:$(git rev-parse --short HEAD) .
  docker build -f docker/streamlit.dockerfile -t ai-agents-streamlit:$(git rev-parse --short HEAD) .

  # Verify image size (<500MB recommended)
  docker images | grep ai-agents
  ```

- [ ] **Health Checks Configured**
  - [ ] API: `GET /health` returns 200 OK
  - [ ] Worker: Celery inspect ping succeeds
  - [ ] Redis: `redis-cli PING` returns PONG
  - [ ] PostgreSQL: `pg_isready` succeeds

- [ ] **Resource Limits Verified**
  - [ ] API container: 1GB RAM, 1 CPU (minimum)
  - [ ] Worker container: 2GB RAM, 2 CPU (recommended for 4 workers)
  - [ ] PostgreSQL: 2GB RAM, disk I/O provisioned
  - [ ] Redis: 512MB RAM (25MB for Render free tier)

### 6. Monitoring and Observability

- [ ] **Prometheus Configured**
  - [ ] Metrics endpoint `/metrics/` accessible
  - [ ] Alert rules loaded: `alert-rules.yml`
  - [ ] Scrape targets healthy in Prometheus UI

- [ ] **Grafana Dashboards Provisioned**
  - [ ] Datasource configured: `k8s/grafana-datasource-provision.yaml`
  - [ ] Dashboards loaded: `dashboards/*.json`
  - [ ] Admin credentials secured (change default `admin/admin`)

- [ ] **Jaeger Tracing Enabled**
  - [ ] `OTEL_EXPORTER_OTLP_ENDPOINT` set to Jaeger gRPC endpoint (port 4317)
  - [ ] Traces visible in Jaeger UI (http://localhost:16686)

- [ ] **Alertmanager Configured**
  - [ ] Slack webhook configured (if applicable)
  - [ ] PagerDuty integration configured (if applicable)
  - [ ] Email SMTP settings validated

### 7. Deployment Window

- [ ] **Maintenance Window Scheduled**
  - **Preferred**: Tuesday 10:00-12:00 UTC (low traffic period)
  - **Duration**: 30 minutes (standard), 60 minutes (with migrations)
  - **Notification**: 24 hours advance notice to stakeholders

- [ ] **Stakeholders Notified**
  - [ ] Engineering team (Slack #engineering)
  - [ ] Product team (email)
  - [ ] Support team (Slack #support)
  - [ ] Customers (status page update, if public)

---

## Deployment Targets

### Target 1: Render.com Cloud Deployment

**Use Case**: Production environment for cloud-hosted deployment

#### Prerequisites
- Render.com account with billing configured
- GitHub repository connected to Render
- `render.yaml` blueprint file committed

#### Services Deployed
- **Web Service**: `ai-ops-api` (FastAPI)
- **Worker Service**: `ai-ops-worker` (Celery)
- **Redis Service**: `ai-ops-redis` (25MB free tier)
- **PostgreSQL Database**: `ai-ops-postgres` (1GB free tier, 90-day expiration)

#### Deployment Steps

See [Deployment Procedures - Render.com](#render-cloud-deployment) for detailed steps.

---

### Target 2: Self-Hosted Docker Deployment

**Use Case**: On-premises deployment, private cloud, or custom infrastructure

#### Prerequisites
- Docker Engine 24+ and Docker Compose 2.20+
- Linux host (Ubuntu 22.04 LTS recommended)
- Minimum resources: 4GB RAM, 2 CPUs, 20GB disk
- Ports available: 8000 (API), 8501 (Streamlit), 3000 (HMAC proxy), 6379 (Redis), 5432 (PostgreSQL)

#### Services Deployed
Full stack from `docker-compose.yml` (11 services)

#### Deployment Steps

See [Deployment Procedures - Docker Compose](#docker-compose-deployment) for detailed steps.

---

## Deployment Procedures

### Render Cloud Deployment

#### Phase 1: Pre-Deployment Setup

1. **Connect GitHub Repository** (first-time only)
   - Navigate to Render.com dashboard
   - Click "New" → "Blueprint"
   - Connect GitHub account and authorize Render app
   - Select repository: `Ai_Agents/AI Ops`

2. **Review Blueprint Configuration**
   ```bash
   # Validate render.yaml syntax locally
   cat render.yaml | grep -E '(type:|name:|runtime:)'

   # Expected output:
   # - type: web
   #   name: ai-ops-api
   #   runtime: docker
   # - type: worker
   #   name: ai-ops-worker
   #   runtime: docker
   ```

3. **Configure Environment Variables**
   - Navigate to "Environment" tab in Render dashboard
   - Add secrets (not in `render.yaml`):
     - `OPENAI_API_KEY`
     - `AI_AGENTS_OPENAI_API_KEY`
     - `SERVICEDESK_PLUS_WEBHOOK_SECRET`
     - `AI_AGENTS_OPENROUTER_API_KEY`
   - Auto-generated values (already in `render.yaml`):
     - `SECRET_KEY`, `AI_AGENTS_WEBHOOK_SECRET`, `AI_AGENTS_ADMIN_API_KEY`, `LITELLM_MASTER_KEY`

#### Phase 2: Database Migration

4. **Run Database Migrations**
   ```bash
   # SSH into web service (Render dashboard → Shell)
   cd /app
   alembic current  # Check current version
   alembic upgrade head  # Apply migrations

   # Verify migration success
   alembic current
   # Expected: Latest revision (e.g., 016_add_cognitive_architecture_to_agents)
   ```

5. **Verify RLS Policies**
   ```bash
   # Connect to Render PostgreSQL via external connection string
   psql "$RENDER_POSTGRES_CONNECTION_STRING"

   # Check RLS enabled
   SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';

   # Exit psql
   \q
   ```

#### Phase 3: Service Deployment

6. **Deploy Web Service**
   - Render automatically builds on git push to `main` branch
   - Monitor build logs in Render dashboard
   - Wait for status: "Live" (green indicator)
   - **Expected duration**: 5-8 minutes

7. **Deploy Worker Service**
   - Worker deploys automatically after web service succeeds
   - Monitor logs for Celery startup: `[INFO/MainProcess] Connected to redis://...`
   - Verify worker count: `celery -A src.workers.celery_app inspect active` (4 workers expected)

8. **Verify Health Checks**
   ```bash
   # API health check
   curl https://ai-ops-api.onrender.com/health
   # Expected: {"status": "healthy", "database": "connected", "redis": "connected"}

   # Metrics endpoint
   curl https://ai-ops-api.onrender.com/metrics/
   # Expected: Prometheus metrics (http_requests_total, etc.)
   ```

#### Phase 4: Post-Deployment Validation

9. **Run Smoke Tests**
   ```bash
   # Execute smoke test suite (see AC-5)
   bash tests/smoke/production_smoke_tests.sh https://ai-ops-api.onrender.com
   ```

10. **Monitor Initial Traffic**
    - Watch Render logs for 15 minutes
    - Check for errors: `grep ERROR` in logs
    - Verify request latency: p95 < 500ms

11. **Verify Celery Task Execution**
    ```bash
    # Trigger test task via API
    curl -X POST https://ai-ops-api.onrender.com/api/v1/agents/execute \
      -H "Authorization: Bearer $ADMIN_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{"agent_id": "test-agent-id", "input": "test"}'

    # Check worker logs for task pickup
    # Expected: [INFO/ForkPoolWorker-1] Task src.workers.tasks.execute_agent[...] succeeded
    ```

---

### Docker Compose Deployment

#### Phase 1: Host Preparation

1. **Verify System Requirements**
   ```bash
   # Check Docker version (24.0+ required)
   docker --version

   # Check Docker Compose version (2.20+ required)
   docker-compose --version

   # Check available resources
   free -h  # Memory (4GB+ required)
   df -h    # Disk space (20GB+ required)
   lscpu | grep "CPU(s)"  # CPUs (2+ recommended)
   ```

2. **Install Dependencies** (if needed)
   ```bash
   # Ubuntu/Debian
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER

   # Install Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

3. **Configure Firewall**
   ```bash
   # Open required ports (adjust for your firewall tool)
   sudo ufw allow 8000/tcp  # API
   sudo ufw allow 8501/tcp  # Streamlit
   sudo ufw allow 3000/tcp  # HMAC Proxy
   sudo ufw reload
   ```

#### Phase 2: Application Setup

4. **Clone Repository**
   ```bash
   git clone https://github.com/your-org/ai-agents-platform.git
   cd ai-agents-platform
   git checkout main  # Or specific release tag
   ```

5. **Configure Environment**
   ```bash
   # Copy example environment file
   cp .env.example .env

   # Edit .env with production values
   nano .env

   # Required variables (minimum):
   # - AI_AGENTS_DATABASE_URL
   # - AI_AGENTS_REDIS_URL
   # - AI_AGENTS_ENCRYPTION_KEY
   # - AI_AGENTS_ADMIN_API_KEY
   # - AI_AGENTS_WEBHOOK_SECRET
   # - OPENAI_API_KEY
   # - DEFAULT_TENANT_ID
   ```

6. **Validate Configuration**
   ```bash
   # Check for missing required variables
   grep -E '^(AI_AGENTS_DATABASE_URL|AI_AGENTS_ENCRYPTION_KEY|OPENAI_API_KEY)=' .env

   # Verify no placeholder values
   grep -E '(REPLACE_ME|CHANGEME|TODO)' .env
   ```

#### Phase 3: Database Initialization

7. **Start Database Services**
   ```bash
   # Start PostgreSQL and Redis only
   docker-compose up -d postgres redis

   # Wait for health checks (30 seconds)
   sleep 30
   docker-compose ps  # Verify both services show "healthy"
   ```

8. **Run Database Migrations**
   ```bash
   # Run migrations via temporary container
   docker-compose run --rm api alembic upgrade head

   # Verify migration success
   docker-compose run --rm api alembic current
   ```

#### Phase 4: Full Stack Deployment

9. **Build Application Images**
   ```bash
   # Build all services (takes 5-10 minutes)
   docker-compose build

   # Verify image sizes
   docker images | grep ai-agents
   # Expected: api ~600MB, streamlit ~700MB
   ```

10. **Start All Services**
    ```bash
    # Start full stack
    docker-compose up -d

    # Monitor startup logs
    docker-compose logs -f --tail=100

    # Verify all services healthy (Ctrl+C to exit logs)
    docker-compose ps
    ```

11. **Verify Service Health**
    ```bash
    # API health check
    curl http://localhost:8000/health

    # Streamlit health check
    curl http://localhost:8501/_stcore/health

    # Redis connection
    docker-compose exec redis redis-cli PING

    # PostgreSQL connection
    docker-compose exec postgres pg_isready -U aiagents

    # Celery worker status
    docker-compose exec worker celery -A src.workers.celery_app inspect ping
    ```

#### Phase 5: Post-Deployment Validation

12. **Run Smoke Tests**
    ```bash
    # Execute smoke test suite
    bash tests/smoke/production_smoke_tests.sh http://localhost:8000
    ```

13. **Access Admin Interface**
    - Open browser: http://localhost:8501
    - Login with admin credentials
    - Verify dashboards load correctly

14. **Monitor Service Metrics**
    - Prometheus: http://localhost:9091
    - Grafana: http://localhost:3002 (admin/admin)
    - Jaeger: http://localhost:16686

---

## Post-Deployment Validation

### Automated Validation

Run the complete smoke test suite (AC-5):

```bash
# Production smoke tests
bash tests/smoke/production_smoke_tests.sh $API_BASE_URL

# Expected output:
# ✅ API health check passed
# ✅ Database connectivity verified
# ✅ Redis connectivity verified
# ✅ Authentication working
# ✅ Agent execution successful
# ✅ Webhook processing functional
# ⏱️ Average response time: 245ms
```

### Manual Validation Checklist

- [ ] **API Endpoints Responding**
  - [ ] `GET /health` returns 200 OK
  - [ ] `GET /docs` (OpenAPI docs) loads
  - [ ] `GET /metrics/` returns Prometheus metrics

- [ ] **Authentication Working**
  ```bash
  # Test JWT authentication
  curl -X POST $API_BASE_URL/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "$ADMIN_PASSWORD"}'
  # Expected: JWT token returned
  ```

- [ ] **Database Connectivity**
  ```bash
  # Verify tenant table accessible
  curl -X GET $API_BASE_URL/api/v1/tenants \
    -H "Authorization: Bearer $JWT_TOKEN"
  # Expected: List of tenants returned
  ```

- [ ] **Background Tasks Working**
  ```bash
  # Trigger agent execution
  curl -X POST $API_BASE_URL/api/v1/agents/execute \
    -H "Authorization: Bearer $JWT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"agent_id": "$TEST_AGENT_ID", "input": "test deployment"}'

  # Check task status (job_id from response)
  curl -X GET $API_BASE_URL/api/v1/jobs/$JOB_ID \
    -H "Authorization: Bearer $JWT_TOKEN"
  # Expected: status = "completed" within 30 seconds
  ```

- [ ] **Webhook Endpoint Functional**
  ```bash
  # Test ServiceDesk Plus webhook (with valid signature)
  python test_webhook_flat_format.py
  # Expected: HTTP 202 Accepted
  ```

- [ ] **Monitoring Stack Operational**
  - [ ] Prometheus targets all UP: http://localhost:9091/targets
  - [ ] Grafana dashboards rendering: http://localhost:3002
  - [ ] Jaeger receiving traces: http://localhost:16686

- [ ] **Logs Clean (No Critical Errors)**
  ```bash
  # Check API logs for errors (last 100 lines)
  docker-compose logs --tail=100 api | grep -E '(ERROR|CRITICAL)'

  # Check worker logs
  docker-compose logs --tail=100 worker | grep -E '(ERROR|CRITICAL)'

  # Expected: No unexpected errors (ignore startup warnings)
  ```

### Performance Validation

- [ ] **Response Time Acceptable**
  ```bash
  # Measure API latency (100 requests)
  ab -n 100 -c 10 $API_BASE_URL/health
  # Expected: p95 latency < 500ms, p99 < 1000ms
  ```

- [ ] **Database Query Performance**
  ```sql
  -- Connect to PostgreSQL and check slow queries
  SELECT query, mean_exec_time, calls
  FROM pg_stat_statements
  WHERE mean_exec_time > 100
  ORDER BY mean_exec_time DESC
  LIMIT 10;

  -- Expected: No queries > 500ms average
  ```

- [ ] **Redis Memory Usage**
  ```bash
  docker-compose exec redis redis-cli INFO memory | grep used_memory_human
  # Expected: < 400MB for 25MB Render tier, < 200MB for self-hosted
  ```

### Security Validation

- [ ] **HTTPS Enabled** (production only)
  - [ ] Certificate valid and not expired
  - [ ] TLS 1.2+ enforced
  - [ ] HSTS header present

- [ ] **Security Headers Present**
  ```bash
  curl -I $API_BASE_URL/health
  # Expected headers:
  # - Content-Security-Policy
  # - X-Content-Type-Options: nosniff
  # - X-Frame-Options: DENY
  # - Strict-Transport-Security (if HTTPS)
  ```

- [ ] **Secrets Not Exposed**
  ```bash
  # Verify no secrets in logs
  docker-compose logs | grep -iE '(api_key|password|secret|token)' | grep -vE '(masked|***)'
  # Expected: No plaintext secrets found
  ```

---

## Rollback Triggers

### Automatic Rollback Conditions

Rollback is **mandatory** if any of the following occur within 30 minutes of deployment:

1. **Health Check Failure**
   - API `/health` endpoint returns 5xx errors for >5 minutes
   - Database connection failures persist for >3 minutes

2. **Error Rate Spike**
   - HTTP 5xx error rate >5% of total requests
   - Celery task failure rate >10%

3. **Performance Degradation**
   - API p95 response time >2000ms (2x baseline)
   - Database query latency >1000ms average

4. **Data Corruption Detected**
   - RLS policy violations logged
   - Foreign key constraint violations
   - Unexpected NULL values in required columns

### Manual Rollback Decision Criteria

Consider rollback if:

- [ ] New features causing user-reported issues
- [ ] Memory leaks detected (OOM kills)
- [ ] Webhook validation failures >20%
- [ ] Critical functionality broken (auth, agent execution)

### Rollback Authority

- **Automatic**: Monitoring alerts trigger automated rollback (if configured)
- **Manual**: Engineering lead or on-call engineer
- **Escalation**: CTO approval required for rollback with data loss risk

---

## Communication Protocols

### Pre-Deployment Communication

**Timing**: 24 hours before deployment

**Channels**:
- Slack: #engineering, #support
- Email: Product team, stakeholders
- Status page: Public notice (if customer-facing)

**Template**:
```
🚀 DEPLOYMENT NOTICE

Deployment Window: [Date] [Time UTC]
Duration: [30-60] minutes
Impact: [None/Partial downtime/Full downtime]

Changes:
- [Feature 1]: Brief description
- [Feature 2]: Brief description
- [Database migrations]: Yes/No

Rollback Plan: Available if needed
Contact: [Engineering lead] on Slack #engineering
```

### During Deployment Communication

**Timing**: Start, midpoint, completion

**Slack Channel**: #engineering

**Messages**:
- **Start**: "🟡 Deployment started - monitoring progress"
- **Midpoint**: "🟡 Database migrations complete - services starting"
- **Success**: "🟢 Deployment complete - all health checks passing"
- **Failure**: "🔴 Deployment failed - initiating rollback"

### Post-Deployment Communication

**Timing**: 30 minutes after deployment

**Slack Message**:
```
✅ DEPLOYMENT COMPLETE

Deployment: [Version/Tag]
Status: Successful
Duration: [Actual time]
Services Deployed: API, Worker, Streamlit

Validation Results:
✅ All smoke tests passed
✅ Health checks green
✅ Error rate normal (<1%)
✅ Response time: p95 = [XXX]ms

No rollback required.
```

---

## Appendix

### A. Deployment Commands Quick Reference

```bash
# Render.com deployment
git push origin main  # Triggers automatic build

# Docker Compose deployment
docker-compose build
docker-compose up -d
docker-compose ps
docker-compose logs -f

# Database migrations
alembic upgrade head
alembic current
alembic history

# Health checks
curl http://localhost:8000/health
docker-compose exec redis redis-cli PING
docker-compose exec postgres pg_isready -U aiagents

# Smoke tests
bash tests/smoke/production_smoke_tests.sh http://localhost:8000
```

### B. Common Troubleshooting

**Issue**: Database migrations fail

**Solution**:
```bash
# Check current version
alembic current

# Rollback one migration
alembic downgrade -1

# Check database connectivity
docker-compose exec postgres psql -U aiagents -c "SELECT version();"
```

**Issue**: Worker not picking up tasks

**Solution**:
```bash
# Check worker logs
docker-compose logs worker --tail=100

# Verify Redis connection
docker-compose exec redis redis-cli PING

# Restart worker
docker-compose restart worker
```

**Issue**: High memory usage

**Solution**:
```bash
# Check container resource usage
docker stats

# Restart specific service
docker-compose restart api

# Check for memory leaks
docker-compose exec api python -c "import psutil; print(psutil.virtual_memory())"
```

### C. Related Documents

- [Rollback Procedures](./rollback-procedures.md)
- [OWASP Security Testing Report](../security/owasp-security-testing-report.md)
- [Post-Deployment Monitoring Checklist](./post-deployment-monitoring.md)
- [Webhook Troubleshooting Runbook](./WEBHOOK_TROUBLESHOOTING_RUNBOOK.md)
- [Tenant Onboarding Runbook](./tenant-onboarding.md)

### D. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-20 | AI Agents Platform Team | Initial production runbook |

---

**Document Status**: ✅ ACTIVE
**Next Review**: 2025-12-20
**Owner**: Engineering Team
**Contact**: #engineering on Slack
