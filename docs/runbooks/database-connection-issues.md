# Database Connection Issues

**Last Updated:** 2025-11-03
**Author:** Amelia (Developer Agent)
**Related Alerts:** None (not alert-triggered, but manifests in enhancement failures)
**Severity:** High (if connection pool exhausted) / Medium (slow queries, RLS issues)

## Quick Links

- [Symptoms](#symptoms)
- [Diagnosis](#diagnosis)
- [Resolution](#resolution)
- [Escalation](#escalation)
- [Using Distributed Tracing](#using-distributed-tracing-for-diagnosis)

---

## Overview

**When to Use This Runbook:**
- Enhancement failures with "connection refused" or "connection timeout" errors
- Database slow query warnings in logs
- SQLAlchemy connection pool exhaustion errors
- Row-level security (RLS) blocking access errors
- Worker logs showing repeated database operation retries

**Scope:** PostgreSQL connectivity, connection pooling, row-level security, and query performance

**Prerequisites:**
- Access to PostgreSQL client (psql) via Docker or Kubernetes
- Access to worker logs and error messages
- Database admin credentials (for long-running query termination)

---

## Symptoms

### Observable Indicators

- ✓ Enhancement failures with error messages containing "connection refused", "timeout", or "pool exhausted"
- ✓ Worker logs showing repeated "sqlalchemy.pool.QueuePool" warnings
- ✓ Slow query performance: p95 latency elevated (>60 seconds)
- ✓ Database pod resource usage high (CPU or memory)
- ✓ Enhancement success rate dropping with database-related errors
- ✓ Error: "permission denied" or "new row violates row-level security policy"

### When This Runbook Does NOT Apply

- Worker crashing (see [Worker Failures Runbook](./worker-failures.md))
- Queue backing up without database errors (see [High Queue Depth Runbook](./high-queue-depth.md))
- External API timeouts (see [API Timeout Runbook](./api-timeout.md))

---

## Diagnosis

### Step 1: Verify Database Pod/Container Health

**Docker:**
```bash
# Check database container status
docker-compose ps postgres

# Expected Output: postgres service showing "Up (healthy)"
```

**Kubernetes:**
```bash
# Check database pod status
kubectl get pods -l app=postgres

# Expected Output: Running status, 1/1 Ready
# If status is CrashLoopBackOff, database is down (escalate immediately)
```

### Step 2: Test Basic Connectivity

**Docker:**
```bash
# Test connection from worker container
docker-compose exec worker psql -h postgres -U aiagents -d ai_agents -c "SELECT 1;"

# Expected Output: 1 (success) or connection error
```

**Kubernetes:**
```bash
# Test from worker pod
kubectl exec -it deployment/celery-worker -- psql -h postgres -U aiagents -d ai_agents -c "SELECT 1;"

# Expected Output: 1 (success)
```

**What to Look For:**
- Success (output "1"): Database responsive
- "connection refused": Database unavailable or wrong host/port
- "password authentication failed": Wrong credentials

### Step 3: Check Active Connections

**Docker:**
```bash
# Connect to database and check connections
docker-compose exec postgres psql -U aiagents -d ai_agents -c \
  "SELECT count(*) as total_connections FROM pg_stat_activity;"

# Expected Output: 10-30 connections (varies by load)
```

**Kubernetes:**
```bash
# Check active connections
kubectl exec -it postgres-0 -- psql -U aiagents -d ai_agents -c \
  "SELECT count(*) as total_connections FROM pg_stat_activity;"
```

**What to Look For:**
- Count close to max_connections (default 100): Connection pool may be exhausted
- Steadily increasing: Possible connection leak in application

### Step 4: Identify Long-Running Queries

**Docker:**
```bash
# Find queries running longer than 5 minutes
docker-compose exec postgres psql -U aiagents -d ai_agents -c \
  "SELECT pid, now() - query_start as duration, query FROM pg_stat_activity
   WHERE state = 'active' AND query_start < now() - interval '5 minutes'
   ORDER BY duration DESC;"

# Expected Output: Empty (no long queries) or list of slow queries
```

**Kubernetes:**
```bash
# Same query on production
kubectl exec -it postgres-0 -- psql -U aiagents -d ai_agents -c \
  "SELECT pid, now() - query_start as duration, query FROM pg_stat_activity
   WHERE state = 'active' AND query_start < now() - interval '5 minutes'
   ORDER BY duration DESC;"
```

**What to Look For:**
- Context gathering queries on large ticket histories (>10,000 records)
- Missing indexes causing sequential scans
- Cartesian joins returning excessive rows

### Step 5: Check Connection Pool Configuration

**Docker:**
```bash
# Find SQLAlchemy pool settings in application code
docker-compose exec worker python -c \
  "from src.database import get_session; print(get_session().get_bind().pool)"

# Or check environment:
docker-compose exec worker printenv | grep SQL
```

**Expected Values:**
- pool_size: 5-10
- max_overflow: 10-20
- pool_timeout: 30 (seconds)

### Step 6: Test Row-Level Security (RLS)

**Docker:**
```bash
# Connect as tenant user and verify RLS is enforced
docker-compose exec postgres psql -U aiagents -d ai_agents -c \
  "SET ROLE tenant_acme_corp;
   SELECT count(*) FROM tickets;"

# Expected Output: Only tickets visible to this tenant, or error if role doesn't exist
```

**Check RLS Policies:**
```bash
# View RLS policies on tickets table
docker-compose exec postgres psql -U aiagents -d ai_agents -c \
  "\d+ tickets"

# Look for "Policies:" section showing RLS rules
```

**What to Look For:**
- Row count = 0: RLS too restrictive (no data visible to tenant)
- Permission denied error: Role doesn't have table access
- Policies missing: RLS disabled, security issue

---

## Resolution

### If: Connection Pool Exhausted

**Symptom:** "QueuePool limit exceeded" in logs, connection_timeout errors

**Step 1: Verify Issue**
```bash
# Check current connections from workers
docker-compose logs worker --tail=200 | grep -i "pool\|exhausted"

# Check connection count
docker-compose exec postgres psql -U aiagents -d ai_agents -c \
  "SELECT count(*) FROM pg_stat_activity WHERE usename = 'aiagents';"

# If > 15 (close to pool_size), pool is exhausted
```

**Step 2: Increase Pool Size**

**Docker - Temporary Fix:**
```bash
# Update docker-compose.yml environment variable
# environment:
#   DATABASE_POOL_SIZE: 20
#   DATABASE_MAX_OVERFLOW: 30

docker-compose restart worker
```

**Kubernetes - Update Deployment:**
```bash
# Edit deployment environment
kubectl set env deployment/celery-worker \
  DATABASE_POOL_SIZE=20 \
  DATABASE_MAX_OVERFLOW=30

# Verify rollout
kubectl rollout status deployment/celery-worker
```

**Step 3: Investigate Connection Leak**

If issue recurs after scaling:
```bash
# Check for connections in IDLE or other non-active states
docker-compose exec postgres psql -U aiagents -d ai_agents -c \
  "SELECT usename, state, count(*) FROM pg_stat_activity
   GROUP BY usename, state ORDER BY count DESC;"

# Look for many IDLE connections (indicates leak)
```

**Resolution:** Escalate to engineering for application-level connection leak fix

### If: Long-Running Queries Blocking

**Symptom:** p95 latency high, some queries taking >30 seconds

**Step 1: Identify Blocking Query**
```bash
# Find query holding locks
docker-compose exec postgres psql -U aiagents -d ai_agents -c \
  "SELECT pid, usename, query, state FROM pg_stat_activity
   WHERE wait_event is NOT NULL
   ORDER BY query_start ASC;"
```

**Step 2: Analyze Query Plan**

```bash
# Get query plan for slow query (replace with actual query)
docker-compose exec postgres psql -U aiagents -d ai_agents -c \
  "EXPLAIN ANALYZE SELECT * FROM tickets WHERE created_at > now() - interval '1 month';"

# Look for "Sequential Scan" (bad, should use index)
# Look for high row counts compared to output rows (inefficient filtering)
```

**Step 3: Terminate Long-Running Query (If Necessary)**

```bash
# WARNING: Only terminate if query is truly stuck
# Get PID of slow query from Step 1

# Terminate query
docker-compose exec postgres psql -U aiagents -d ai_agents -c \
  "SELECT pg_terminate_backend(PID_FROM_STEP_1);"

# Expected output: true (killed) or false (already terminated)
```

**Step 4: Add Missing Indexes (Long-Term)**

Common indexes needed:
```bash
# Context gathering often filters by:
# - created_at (for recent tickets)
# - tenant_id (for RLS)
# - ticket_status (for open tickets)

# Check if indexes exist
docker-compose exec postgres psql -U aiagents -d ai_agents -c \
  "\d tickets"

# If missing, escalate to DBA/engineering for index creation
```

### If: Row-Level Security (RLS) Blocking Access

**Symptom:** "new row violates row-level security policy" or "permission denied"

**Step 1: Verify RLS Policy**
```bash
# Check which role connection is using
docker-compose exec postgres psql -U aiagents -d ai_agents -c \
  "SELECT current_user, current_role;"

# Expected: Both should be a tenant-specific role or 'aiagents' admin
```

**Step 2: Check Tenant ID Context**
```bash
# Verify tenant_id is set in session (application-level)
docker-compose logs worker | grep -i "tenant_id\|set role" | head -20

# If no tenant_id set, RLS can't filter properly
```

**Step 3: Fix RLS Context**

**If tenant_id not set:**
```bash
# Application code must set tenant context before queries
# Example (in application code):
# SELECT set_config('app.current_tenant_id', 'acme-corp', false);

# Escalate to engineering to verify application sets context correctly
```

**If RLS policy too restrictive:**
```bash
# Review RLS policies
docker-compose exec postgres psql -U aiagents -d ai_agents -c \
  "SELECT schemaname, tablename, policyname, permissive, roles, qual
   FROM pg_policies
   WHERE tablename = 'tickets';"

# If policy uses wrong column or constant, escalate for policy fix
```

### If: Database Pod Down or Unresponsive

**Symptom:** Connection refused, database unreachable

**Step 1: Check Pod Status**
```bash
# Kubernetes
kubectl describe pod postgres-0

# Look for "Events:" section showing why pod crashed/stopped
# Look for "Liveness probe failed" or resource issues
```

**Step 2: Check Resource Limits**
```bash
# Verify database has sufficient resources
kubectl get pod postgres-0 -o yaml | grep -A 10 "resources:"

# If memory limit hit: OOMKilled (check Events)
# If CPU throttled: Performance degraded
```

**Step 3: Restart Database**

```bash
# Kubernetes - Rolling restart
kubectl rollout restart statefulset/postgres
kubectl rollout status statefulset/postgres

# Wait for pod to be ready
kubectl wait --for=condition=Ready pod/postgres-0 --timeout=300s
```

**Docker:**
```bash
# Restart database
docker-compose restart postgres

# Verify health
docker-compose ps postgres
sleep 10

# Test connectivity
docker-compose exec worker psql -h postgres -U aiagents -d ai_agents -c "SELECT 1;"
```

**Step 4: Verify Workers Reconnect**
```bash
# Check worker logs for successful reconnection
docker-compose logs worker --tail=50 | grep -i "connected\|connection"

# If workers not reconnecting, restart workers
docker-compose restart worker
```

---

## Escalation

### Database Unresponsive for 5+ Minutes

- **Severity:** Critical
- **Action:** Immediate
- **Timeline:** Page DBA and on-call engineer NOW
- **Context:** Platform unavailable, no enhancements processing
- **Steps:** Verify pod status, check node resources, initiate failover if applicable

### Data Corruption Suspected

- **Severity:** Critical
- **Action:** Immediate halt of writes, escalate to DBA
- **Timeline:** STOP all writes immediately
- **Steps:**
  1. Pause webhook receiver (if possible)
  2. Stop all workers to prevent further writes
  3. Page DBA immediately
  4. Prepare for potential data restore from backup

### Persistent Connection Issues (30+ Minutes)

- **Severity:** High
- **Action:** Escalate to DBA or platform team
- **Context:** Issue not resolved by standard troubleshooting
- **Provide:**
  - Connection error logs
  - Active connection count from pg_stat_activity
  - RLS policy definitions
  - Recent changes (deployments, data migrations, schema changes)

---

## Using Distributed Tracing for Diagnosis

### When to Use Distributed Tracing

If database queries are slow but not obviously blocked:

1. Open Jaeger UI: http://localhost:16686
2. Search for slow traces (slow_trace=true)
3. Look at "context_gathering" span duration (usually longest)

### Jaeger Search Examples

**Find slow traces (database heavy):**
```
slow_trace=true
duration > 30s
```

**Find traces for specific tenant:**
```
tenant_id=acme-corp
duration > 10s
```

### Interpreting Trace Details

- **context_gathering span:** Shows breakdown of database queries
  - Multiple small queries that should be batched
  - Single large query scanning too many rows
  - Repeated queries that should be cached

**Optimizations to suggest:**
- Batch historical queries instead of individual SELECT calls
- Add database indexes on frequently filtered columns
- Implement query result caching

---

## Related Documentation

- **[High Queue Depth Runbook](./high-queue-depth.md)** - If queue backing up due to slow queries
- **[Worker Failures Runbook](./worker-failures.md)** - If workers crashing from connection errors
- **[API Timeout Runbook](./api-timeout.md)** - If external API slow (separate from database)
- **[Distributed Tracing Setup](../operations/distributed-tracing-setup.md)** - Jaeger UI guide
- **[Database Schema Documentation](../../docs/database-schema.md)** - Table structure and RLS policies
- **[PostgreSQL Documentation](https://www.postgresql.org/docs/14/app-psql.html)** - SQL reference

---

**Status:** ✅ Complete with RLS troubleshooting and query optimization guidance
**Test Status:** Awaiting team member validation (Task 10)
**Last Review:** 2025-11-03
