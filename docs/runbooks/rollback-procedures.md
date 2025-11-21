# Rollback Procedures

**Document Version:** 1.0
**Last Updated:** November 20, 2025
**Story:** 4-8 Testing, Deployment, and Rollout - AC-4
**Status:** ✅ ACTIVE

## Table of Contents

1. [Overview](#overview)
2. [Rollback Decision Matrix](#rollback-decision-matrix)
3. [Pre-Rollback Checklist](#pre-rollback-checklist)
4. [Rollback Procedures](#rollback-procedures)
5. [Database Rollback Strategies](#database-rollback-strategies)
6. [Verification and Validation](#verification-and-validation)
7. [Post-Rollback Analysis](#post-rollback-analysis)
8. [Appendix](#appendix)

---

## Overview

### Purpose

This document provides comprehensive procedures for rolling back deployments of the AI Agents Platform when issues are detected in production. It covers decision criteria, execution steps, and validation procedures.

### Scope

- **In Scope**: Application code rollback, database migrations, configuration changes, service restarts
- **Out of Scope**: Infrastructure-level rollbacks (cloud provider migrations, hardware changes)
- **Related Documents**: [Production Deployment Runbook](./production-deployment.md), [Post-Deployment Monitoring](./post-deployment-monitoring.md)

### Rollback Philosophy

**Goal**: Restore service to last known good state with minimal downtime and zero data loss.

**Principles**:
1. **Safety First**: Always preserve data integrity
2. **Speed Second**: Execute rollback as quickly as safe practices allow
3. **Communication Throughout**: Keep stakeholders informed at each step
4. **Learn from Every Rollback**: Conduct post-mortems to prevent recurrence

### Rollback Authority Matrix

| Severity | Approval Required | Response Time |
|----------|-------------------|---------------|
| **P0 - Critical** (Service down, data loss risk) | On-call engineer | Immediate (0-5 min) |
| **P1 - High** (Major feature broken, >10% error rate) | Engineering lead | 15 minutes |
| **P2 - Medium** (Minor feature issues, <5% error rate) | Team consensus | 1 hour |
| **P3 - Low** (Cosmetic issues, no user impact) | Next scheduled deployment | N/A |

---

## Rollback Decision Matrix

### Automatic Rollback Triggers

These conditions trigger **immediate automated rollback** (if monitoring/alerting configured):

| Trigger | Threshold | Duration | Action |
|---------|-----------|----------|--------|
| **API Health Check Failure** | `/health` returns 5xx | 5 minutes consecutive | Auto-rollback |
| **Error Rate Spike** | HTTP 5xx > 5% of requests | 3 minutes | Auto-rollback |
| **Database Connection Failures** | Connection timeouts > 50% | 2 minutes | Auto-rollback |
| **Worker Queue Stalled** | No task processing for | 10 minutes | Auto-rollback |
| **Memory Leak** | Container OOM kills | 2 occurrences | Auto-rollback |

### Manual Rollback Criteria

Consider rollback if **any** of these conditions occur:

#### Severity P0 (Critical - Immediate Rollback)
- [ ] Complete service outage (API unreachable)
- [ ] Data corruption detected (RLS violations, constraint errors)
- [ ] Security vulnerability actively exploited
- [ ] Authentication system failure (users locked out)
- [ ] Database migrations failed with schema corruption

#### Severity P1 (High - Rollback within 15 minutes)
- [ ] Core functionality broken (agent execution, webhook processing)
- [ ] Error rate >10% sustained for >5 minutes
- [ ] Performance degradation >3x baseline (p95 latency)
- [ ] Memory leak causing frequent restarts (>5/hour)
- [ ] Critical integration failures (LiteLLM, Redis, PostgreSQL)

#### Severity P2 (Medium - Rollback within 1 hour)
- [ ] Non-critical feature broken (UI dashboard, reports)
- [ ] Error rate 5-10% sustained for >15 minutes
- [ ] Performance degradation 2-3x baseline
- [ ] Elevated but manageable resource usage (>80% CPU sustained)

#### Severity P3 (Low - Fix Forward)
- [ ] Cosmetic UI issues
- [ ] Non-critical logging errors
- [ ] Minor documentation issues
- [ ] Performance degradation <2x baseline

### Rollback vs. Hotfix Decision

| Scenario | Recommended Action | Rationale |
|----------|-------------------|-----------|
| Simple config change needed | **Hotfix** | Faster than full rollback |
| Database migration involved | **Rollback** | Safer to revert than forward |
| Single file code change | **Hotfix** | Low risk, quick fix |
| Multiple interrelated changes | **Rollback** | Too risky to isolate issue |
| Unknown root cause | **Rollback** | Investigate offline, then redeploy |
| Known fix available in <30 min | **Hotfix** | Faster recovery |

---

## Pre-Rollback Checklist

### 1. Situation Assessment

- [ ] **Identify Root Cause** (if possible)
  - Check logs for error patterns
  - Review recent changes (git log)
  - Consult monitoring dashboards (Grafana)

- [ ] **Determine Rollback Scope**
  - [ ] Application code only
  - [ ] Database migrations
  - [ ] Configuration changes
  - [ ] Multiple services

- [ ] **Estimate Impact**
  - Number of affected users
  - Data loss risk (if any)
  - Expected downtime during rollback

### 2. Communication

- [ ] **Notify Stakeholders**
  ```
  🔴 ROLLBACK INITIATED

  Issue: [Brief description]
  Severity: P0/P1/P2
  Affected: [API/Worker/Database]
  ETA: [15-30] minutes
  Status updates: #engineering channel
  ```

- [ ] **Update Status Page** (if customer-facing)
  - Mark service as "Degraded" or "Major Outage"
  - Provide ETA for resolution

### 3. Backup Current State

- [ ] **Capture Current Deployment Info**
  ```bash
  # Git commit hash
  git rev-parse HEAD > /tmp/rollback-from-commit.txt

  # Docker image tags
  docker images | grep ai-agents > /tmp/rollback-from-images.txt

  # Environment variables (Render)
  render env list ai-ops-api > /tmp/rollback-from-env.txt
  ```

- [ ] **Database Snapshot** (if migration rollback needed)
  ```bash
  # PostgreSQL backup
  docker-compose exec postgres pg_dump -U aiagents ai_agents | gzip > /tmp/rollback-backup-$(date +%Y%m%d-%H%M%S).sql.gz

  # Or Render backup
  render pg-backup ai-ops-postgres
  ```

- [ ] **Export Logs for Analysis**
  ```bash
  # API logs (last 1000 lines)
  docker-compose logs --tail=1000 api > /tmp/rollback-api-logs-$(date +%Y%m%d-%H%M%S).txt

  # Worker logs
  docker-compose logs --tail=1000 worker > /tmp/rollback-worker-logs-$(date +%Y%m%d-%H%M%S).txt
  ```

### 4. Identify Rollback Target

- [ ] **Determine Last Known Good Version**
  ```bash
  # View recent deployments (git tags)
  git tag --sort=-creatordate | head -10

  # View recent commits
  git log --oneline -10

  # Identify stable release (usually previous tag)
  ROLLBACK_TARGET=$(git tag --sort=-creatordate | head -2 | tail -1)
  echo "Rolling back to: $ROLLBACK_TARGET"
  ```

- [ ] **Verify Rollback Target**
  - Confirm version was stable (check monitoring history)
  - Ensure database schema compatible
  - Verify no data migration issues

---

## Rollback Procedures

### Procedure 1: Application Code Rollback (No Database Changes)

**Use Case**: Code-only deployment with no database migrations

**Duration**: 5-10 minutes

**Prerequisites**: No database schema changes in rolled-back commits

#### Steps

##### Render.com Deployment

1. **Identify Previous Working Commit**
   ```bash
   # Locally, find the last stable commit
   git log --oneline -10
   # Example: abc123f was the last working deployment
   ```

2. **Revert to Previous Commit**
   ```bash
   # Option A: Hard reset to previous commit (WARNING: Destructive)
   git reset --hard abc123f

   # Option B: Create revert commit (Safer, preserves history)
   git revert --no-commit HEAD
   git commit -m "Rollback: Revert deployment to abc123f"
   ```

3. **Force Push to Trigger Rebuild**
   ```bash
   # Push to main branch
   git push origin main --force-with-lease

   # Render automatically rebuilds and redeploys
   ```

4. **Monitor Deployment**
   - Watch Render dashboard for build progress (5-8 minutes)
   - Check logs for startup errors
   - Verify health check passes

##### Docker Compose Deployment

1. **Checkout Previous Commit**
   ```bash
   cd /path/to/ai-agents-platform
   git fetch origin
   git checkout abc123f  # Last working commit
   ```

2. **Rebuild and Restart Services**
   ```bash
   # Stop current services
   docker-compose stop api worker

   # Rebuild images
   docker-compose build api worker

   # Start services
   docker-compose up -d api worker

   # Monitor startup
   docker-compose logs -f api worker
   ```

3. **Verify Health**
   ```bash
   # API health check
   curl http://localhost:8000/health

   # Worker status
   docker-compose exec worker celery -A src.workers.celery_app inspect ping
   ```

---

### Procedure 2: Database Migration Rollback

**Use Case**: Deployment included Alembic migrations that caused issues

**Duration**: 15-30 minutes

**Risk**: HIGH - Data loss possible if not careful

#### Prerequisites

- [ ] Database backup exists (taken during deployment)
- [ ] Migration files reviewed for reversibility
- [ ] Downgrade scripts tested on staging

#### Steps

1. **Assess Migration Reversibility**
   ```bash
   # Check current migration version
   docker-compose exec api alembic current

   # Review migration history
   docker-compose exec api alembic history

   # Inspect downgrade logic in migration file
   cat alembic/versions/016_add_cognitive_architecture_to_agents.py | grep "def downgrade"
   ```

2. **Test Downgrade on Staging** (if available)
   ```bash
   # On staging environment
   alembic downgrade -1  # Downgrade one version

   # Verify data integrity
   psql $STAGING_DATABASE_URL -c "SELECT count(*) FROM agents;"

   # Re-upgrade to test forward compatibility
   alembic upgrade +1
   ```

3. **Execute Production Downgrade**

   **Option A: Safe Reversible Migration**
   ```bash
   # Downgrade one migration
   docker-compose exec api alembic downgrade -1

   # Verify schema state
   docker-compose exec postgres psql -U aiagents -c "\d agents"

   # Check application still works
   curl http://localhost:8000/health
   ```

   **Option B: Non-Reversible Migration (Restore from Backup)**
   ```bash
   # STOP ALL SERVICES FIRST
   docker-compose stop api worker streamlit

   # Drop current database (WARNING: DATA LOSS)
   docker-compose exec postgres psql -U aiagents -c "DROP DATABASE ai_agents;"
   docker-compose exec postgres psql -U aiagents -c "CREATE DATABASE ai_agents;"

   # Restore from backup
   gunzip < /tmp/rollback-backup-20251120-120000.sql.gz | \
     docker-compose exec -T postgres psql -U aiagents ai_agents

   # Verify restoration
   docker-compose exec postgres psql -U aiagents -c "SELECT count(*) FROM agents;"

   # Restart services
   docker-compose up -d api worker streamlit
   ```

4. **Rollback Application Code**
   ```bash
   # Checkout code compatible with rolled-back schema
   git checkout abc123f  # Commit before migration

   # Rebuild and restart
   docker-compose build api worker
   docker-compose restart api worker
   ```

---

### Procedure 3: Configuration Rollback

**Use Case**: Environment variable change caused issues

**Duration**: 2-5 minutes

**Risk**: LOW - No code or database changes

#### Steps

##### Render.com

1. **Restore Previous Environment Variables**
   ```bash
   # Compare current vs. backup
   diff <(render env list ai-ops-api) /tmp/rollback-from-env.txt

   # Identify changed variables
   # Example: OPENAI_API_KEY was changed
   ```

2. **Revert via Render Dashboard**
   - Navigate to Service → Environment
   - Locate changed variable (e.g., `OPENAI_API_KEY`)
   - Update to previous value
   - Click "Save Changes"
   - Wait for auto-restart (1-2 minutes)

##### Docker Compose

1. **Restore .env File**
   ```bash
   # Restore from backup
   cp .env.backup-20251120-100000 .env

   # Verify critical variables
   grep -E '^(AI_AGENTS_DATABASE_URL|OPENAI_API_KEY)=' .env
   ```

2. **Restart Services**
   ```bash
   # Restart to reload environment variables
   docker-compose restart api worker streamlit

   # Verify new config loaded
   docker-compose logs api | grep "Environment loaded"
   ```

---

### Procedure 4: Partial Rollback (Feature Flag)

**Use Case**: New feature causing issues, but rest of deployment stable

**Duration**: <1 minute

**Risk**: VERY LOW - No service restart needed

#### Prerequisites

- Feature must be behind feature flag or configuration toggle

#### Steps

1. **Disable Feature via Admin UI**
   - Login to Streamlit Admin: http://localhost:8501
   - Navigate to "Feature Flags" page
   - Locate feature causing issues
   - Toggle "Enabled" to OFF
   - Click "Save"

2. **Or Disable via API**
   ```bash
   # Update feature flag via API
   curl -X PATCH http://localhost:8000/api/v1/features/new-feature \
     -H "Authorization: Bearer $ADMIN_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"enabled": false}'
   ```

3. **Or Disable via Environment Variable**
   ```bash
   # Add feature flag to .env
   echo "FEATURE_NEW_FEATURE_ENABLED=false" >> .env

   # Restart services
   docker-compose restart api worker
   ```

4. **Verify Feature Disabled**
   ```bash
   # Test feature endpoint returns 404 or "feature disabled" message
   curl http://localhost:8000/api/v1/new-feature
   # Expected: {"detail": "Feature disabled"}
   ```

---

### Procedure 5: Emergency Full Rollback

**Use Case**: Critical production outage, unknown root cause

**Duration**: 10-15 minutes

**Risk**: MEDIUM - Fast recovery prioritized over analysis

#### Steps

1. **Execute Rapid Rollback**
   ```bash
   # Get last stable tag
   STABLE_TAG=$(git tag --sort=-creatordate | sed -n '2p')
   echo "Emergency rollback to: $STABLE_TAG"

   # Hard reset to stable tag
   git fetch --tags
   git checkout $STABLE_TAG

   # Stop all services
   docker-compose down

   # Rebuild from stable code
   docker-compose build

   # Start services
   docker-compose up -d

   # Wait 30 seconds for startup
   sleep 30
   ```

2. **Verify Core Functionality**
   ```bash
   # Health check
   curl http://localhost:8000/health

   # Auth working
   curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "$ADMIN_PASSWORD"}'

   # Database accessible
   docker-compose exec postgres pg_isready -U aiagents
   ```

3. **Announce Recovery**
   ```
   🟢 SERVICE RESTORED

   Rollback completed to stable version: $STABLE_TAG
   Services operational: API, Worker, Database
   Issue under investigation
   Post-mortem scheduled: [Date/Time]
   ```

---

## Database Rollback Strategies

### Strategy 1: Backward-Compatible Migrations (Preferred)

**Design Principle**: New schema supports both old and new application code

**Example**: Adding a new column
```python
# Migration UP: Add column with default value
def upgrade():
    op.add_column('agents', sa.Column('cognitive_arch', sa.String(), nullable=True))

# Migration DOWN: Drop column (safe, no data loss)
def downgrade():
    op.drop_column('agents', 'cognitive_arch')
```

**Rollback**: Simple `alembic downgrade -1` with zero risk

---

### Strategy 2: Blue-Green Database Deployment

**Use Case**: Complex schema changes with data transformation

**Steps**:
1. Create new database with new schema
2. Dual-write to both databases during transition
3. Migrate data in background
4. Switch application to new database
5. Keep old database as rollback option for 7 days

**Rollback**: Switch connection string back to old database

---

### Strategy 3: Point-in-Time Recovery

**Use Case**: Data corruption or accidental deletion

**Prerequisites**: Continuous database backups (WAL archiving)

**Rollback**:
```bash
# Restore PostgreSQL to specific timestamp
pg_restore --clean --if-exists \
  --dbname=ai_agents \
  --jobs=4 \
  backup-before-deployment.dump

# Or use point-in-time recovery (PITR)
# Requires WAL archiving enabled
```

---

## Verification and Validation

### Post-Rollback Validation Checklist

- [ ] **Services Running**
  ```bash
  docker-compose ps
  # Expected: All services show "Up" and "healthy"
  ```

- [ ] **Health Checks Passing**
  ```bash
  # API
  curl http://localhost:8000/health
  # Expected: {"status": "healthy"}

  # Prometheus metrics
  curl http://localhost:8000/metrics/ | head -20

  # Worker
  docker-compose exec worker celery -A src.workers.celery_app status
  ```

- [ ] **Database Connectivity**
  ```bash
  docker-compose exec postgres psql -U aiagents -c "SELECT count(*) FROM agents;"
  # Expected: Valid count returned
  ```

- [ ] **Error Rate Normal**
  ```bash
  # Check API logs for errors (last 100 lines)
  docker-compose logs --tail=100 api | grep -c ERROR
  # Expected: 0 or minimal (<5)
  ```

- [ ] **Performance Baseline Restored**
  ```bash
  # Test API response time
  time curl -s http://localhost:8000/health
  # Expected: <200ms
  ```

- [ ] **Critical Functionality Working**
  - [ ] Authentication: Login succeeds
  - [ ] Agent execution: Test agent runs successfully
  - [ ] Webhooks: Test webhook accepted (HTTP 202)
  - [ ] Background tasks: Celery tasks processing

### Monitoring Post-Rollback

**Duration**: Monitor for 1 hour post-rollback

**Metrics to Watch**:
- [ ] Error rate: Should return to <1%
- [ ] Response time: p95 < 500ms, p99 < 1000ms
- [ ] Memory usage: Stable, no leaks
- [ ] Database connections: Not exhausted
- [ ] Celery queue depth: Decreasing (tasks being processed)

**Alerting**:
- Configure Prometheus alerts to fire if issues recur
- Escalate to engineering lead if problems persist

---

## Post-Rollback Analysis

### Immediate Actions (Within 1 Hour)

1. **Preserve Evidence**
   ```bash
   # Collect all logs from failed deployment
   mkdir -p /tmp/rollback-analysis-$(date +%Y%m%d-%H%M%S)
   docker-compose logs > /tmp/rollback-analysis-*/all-logs.txt
   cp /tmp/rollback-*.txt /tmp/rollback-analysis-*/
   ```

2. **Document Timeline**
   - Deployment start time
   - Issue detected time
   - Rollback initiated time
   - Rollback completed time
   - Total downtime duration

3. **Identify Root Cause**
   - Code changes that caused issue
   - Configuration changes
   - Migration issues
   - External dependency failures

### Post-Mortem (Within 24 Hours)

**Required Attendees**: Engineering team, on-call engineer, engineering lead

**Agenda**:
1. **Timeline Review**: What happened and when?
2. **Root Cause Analysis**: Why did it happen?
3. **Detection Discussion**: How was it discovered?
4. **Response Evaluation**: How did rollback go?
5. **Prevention Planning**: How to prevent recurrence?

**Deliverable**: Post-mortem document with:
- Incident summary
- Root cause
- Action items with owners and deadlines
- Process improvements

### Long-Term Improvements

**Consider implementing**:
- [ ] **Automated rollback triggers** (if not already in place)
- [ ] **Enhanced smoke tests** to catch issues earlier
- [ ] **Canary deployments** for gradual rollout
- [ ] **Feature flags** for instant disable without rollback
- [ ] **Blue-green deployment** for zero-downtime rollbacks

---

## Appendix

### A. Rollback Commands Quick Reference

```bash
# Application code rollback (Docker Compose)
git checkout <stable-commit>
docker-compose build api worker
docker-compose restart api worker

# Database migration rollback
docker-compose exec api alembic downgrade -1

# Configuration rollback
cp .env.backup .env
docker-compose restart api worker

# Full emergency rollback
docker-compose down
git checkout <stable-tag>
docker-compose build
docker-compose up -d

# Verification
curl http://localhost:8000/health
docker-compose ps
docker-compose logs --tail=50 api
```

### B. Common Rollback Issues

**Issue**: Downgrade migration fails with constraint violation

**Solution**:
```bash
# Check for data that violates old schema
docker-compose exec postgres psql -U aiagents -c \
  "SELECT * FROM table WHERE new_column IS NOT NULL;"

# Options:
# 1. Manually update data to be compatible
# 2. Restore from pre-deployment backup
```

**Issue**: Services won't start after rollback

**Solution**:
```bash
# Check logs for specific error
docker-compose logs api

# Common fixes:
# - Verify .env file has all required variables
# - Check database connection string
# - Ensure ports not in use: netstat -tlnp | grep <port>
```

**Issue**: Database restore fails

**Solution**:
```bash
# Verify backup file integrity
gunzip -t backup.sql.gz

# Check database exists
docker-compose exec postgres psql -U aiagents -l

# Restore to new database name (avoid DROP)
docker-compose exec postgres psql -U aiagents -c \
  "CREATE DATABASE ai_agents_restored;"
gunzip < backup.sql.gz | docker-compose exec -T postgres \
  psql -U aiagents ai_agents_restored
```

### C. Rollback Decision Flowchart

```
┌─────────────────────────────┐
│   Issue Detected            │
└──────────┬──────────────────┘
           │
           ▼
    ┌──────────────┐    No
    │ Severity P0? ├─────────┐
    └──┬───────────┘         │
       │ Yes                 │
       │                     ▼
       │              ┌──────────────┐    No
       │              │ Severity P1? ├─────────┐
       │              └──┬───────────┘         │
       │                 │ Yes                 │
       │                 │                     ▼
       │                 │              ┌──────────────┐
       │                 │              │ Severity P2? │
       │                 │              └──┬───────────┘
       │                 │                 │
       │                 │                 │
       ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ IMMEDIATE    │  │ ROLLBACK     │  │ HOTFIX or    │
│ ROLLBACK     │  │ WITHIN 15min │  │ NEXT DEPLOY  │
│ (0-5 min)    │  │              │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
       │                 │                 │
       └─────────────────┴─────────────────┘
                         │
                         ▼
              ┌──────────────────┐
              │ Execute Rollback │
              │ Procedure        │
              └──────┬───────────┘
                     │
                     ▼
              ┌──────────────────┐
              │ Verify Service   │
              │ Restored         │
              └──────┬───────────┘
                     │
                     ▼
              ┌──────────────────┐
              │ Post-Mortem      │
              │ Analysis         │
              └──────────────────┘
```

### D. Related Documents

- [Production Deployment Runbook](./production-deployment.md)
- [Post-Deployment Monitoring Checklist](./post-deployment-monitoring.md)
- [Database Connection Issues Runbook](./database-connection-issues.md)
- [Worker Failures Runbook](./worker-failures.md)

### E. Contact Information

| Role | Contact | Availability |
|------|---------|--------------|
| On-Call Engineer | Slack: #engineering @oncall | 24/7 |
| Engineering Lead | Slack: @engineering-lead | Business hours |
| Database Admin | Slack: @dba | Business hours |
| Security Team | Slack: #security | Business hours |

### F. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-20 | AI Agents Platform Team | Initial rollback procedures |

---

**Document Status**: ✅ ACTIVE
**Next Review**: 2025-12-20
**Owner**: Engineering Team
**Contact**: #engineering on Slack
