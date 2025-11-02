# Enhancement Failure Runbook

**Purpose:** Troubleshoot and resolve failed ticket enhancement jobs
**Audience:** On-call engineers, DevOps, support team
**Last Updated:** 2025-11-02

---

## Quick Diagnostics

### Step 1: Identify the Failure

**Location:** Check logs with correlation ID

```bash
# Using ELK Stack or CloudWatch
grep -r "correlation_id=550e8400-e29b-41d4-a716-446655440000" /var/log/

# Or via Docker (local dev)
docker logs ai-ops-celery-worker | grep "correlation_id"
```

**Or check database:**

```sql
-- PostgreSQL
SELECT * FROM enhancement_history WHERE status = 'failed' ORDER BY created_at DESC LIMIT 10;

-- View specific failure
SELECT * FROM enhancement_history WHERE correlation_id = '550e8400-e29b-41d4-a716-446655440000';
```

### Step 2: Identify Failure Type

Check the `error_message` field in `enhancement_history` table:

| Error Pattern | Phase | Action |
|---------------|-------|--------|
| `Timeout after 30s` | Context Gathering (2.8) | [See: Context Gathering Timeout] |
| `ServiceDesk API returned 401` | API Update (2.10) | [See: Authentication Failure] |
| `ServiceDesk API returned 429` | API Update (2.10) | [See: Rate Limit Exceeded] |
| `OpenRouter API error: 500` | LLM Synthesis (2.9) | [See: LLM Provider Outage] |
| `Connection refused: redis` | Queue/Initialization | [See: Redis Connection] |
| `Database connection lost` | History Recording | [See: Database Connection] |

---

## Failure Scenarios & Resolution

### 1. Context Gathering Timeout

**Symptom:**
```
error_message: "Timeout after 30s"
context_nodes_success: 0
context_nodes_failed: 0
```

**Cause:** One or more context gathering nodes (similar tickets, KB search, IP lookup) took >30 seconds

**Investigation:**
```bash
# Check individual node timing in logs
grep "correlation_id=550e8400..." logs/ | grep "node_name"

# Output should show:
# - ticket_search_time_ms: 450
# - kb_search_time_ms: 320
# - ip_lookup_time_ms: 280
# Total > 30000ms = TIMEOUT
```

**Resolution:**

**Option A: Increase timeout (if nodes are genuinely slow)**
```python
# src/workers/tasks.py
timeout = 45  # Increase from 30 to 45 seconds
context = await asyncio.wait_for(
    execute_context_gathering(...),
    timeout=timeout
)
```

**Option B: Optimize slow node (if persistent)**

If `kb_search_time_ms` > 15s consistently:
```bash
# 1. Check knowledge base search performance
SELECT * FROM kb_articles LIMIT 1000;  # Verify indexes

# 2. Monitor database query performance
EXPLAIN ANALYZE SELECT ... FROM kb_articles WHERE full_text_search(...);

# 3. Add index if missing
CREATE INDEX idx_kb_full_text ON kb_articles USING gin(search_vector);
```

**Option C: Parallel node execution**
- Ensure context gathering nodes run in parallel (already implemented in LangGraph)
- Check for lock contention on database

**Manual Retry:**
```bash
# Re-queue the job manually (if original job was lost)
python -c "
from src.workers.tasks import enhance_ticket
enhance_ticket.apply_async(
    args=[{
        'job_id': '550e8400...',
        'ticket_id': 'TKT-12345',
        'tenant_id': 'test-tenant',
        # ... other fields
    }],
    queue='default'
)
"
```

---

### 2. LLM Provider Outage (OpenRouter)

**Symptom:**
```
error_message: "OpenRouter API error: 503 Service Unavailable"
status: 'failed'
```

**Cause:** OpenRouter API is down or rate limited

**Investigation:**
```bash
# Check OpenRouter status page
curl https://status.openrouter.io/api/v2/status.json

# Check recent API calls in logs
grep "openrouter" logs/ | grep -i error | tail -20

# Monitor rate limit headers
curl -H "Authorization: Bearer $OPENROUTER_API_KEY" \
     https://openrouter.ai/api/v1/models | jq '.data[0].pricing'
```

**Resolution:**

**Option A: Wait for recovery**
- OpenRouter outages typically resolve within 5-15 minutes
- Celery will automatically retry task (configurable retry count)
- Check: `src/workers/tasks.py` for retry configuration

**Option B: Switch to fallback formatting immediately**
```python
# In src/services/llm_synthesis.py
try:
    enhancement = await synthesize_enhancement(context, correlation_id)
except OpenRouterError as exc:
    logger.warning(f"LLM synthesis unavailable: {exc}")
    enhancement = _format_context_fallback(context)  # Fallback mode
    # Task continues successfully
```

**Option C: Check API key and quota**
```bash
# Test OpenRouter API connectivity
curl -X POST https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "test"}]
  }' | jq '.error'

# If error: check OpenRouter dashboard for:
# - Quota remaining
# - Account status
# - API key validity
```

**Option D: Temporarily disable LLM (emergency mode)**
```python
# In src/config.py
DISABLE_LLM_SYNTHESIS = True  # Forces fallback for all jobs

# Then fix and re-enable
DISABLE_LLM_SYNTHESIS = False
```

**Manual Retry:**
```bash
# Celery will auto-retry, but force immediate retry if needed
celery -A src.workers.celery_app inspect revoked  # Check revoked tasks
celery -A src.workers.celery_app purge  # Clear queue (CAREFUL!)
```

---

### 3. ServiceDesk Plus API Authentication Failure

**Symptom:**
```
error_message: "ServiceDesk API returned 401 Unauthorized"
status: 'failed'
```

**Cause:** API key expired, revoked, or incorrect permissions

**Investigation:**
```bash
# Test ServiceDesk API directly
curl -X GET \
  "https://api.servicedesk-plus.local/api/v3/tickets/TKT-12345" \
  -H "Authorization: apikey ${SERVICEDESK_API_KEY}"

# Check response
# 401 = auth failure
# 403 = permission denied
# 404 = ticket not found
```

**Resolution:**

**Option A: Verify API key in database**
```sql
-- Check tenant config
SELECT tenant_id, api_key, base_url FROM tenant_configs WHERE tenant_id = 'test-tenant';

-- Verify key is not NULL/empty
SELECT LENGTH(api_key) as key_length FROM tenant_configs WHERE tenant_id = 'test-tenant';
```

**Option B: Regenerate API key**
1. Login to ServiceDesk Plus admin panel
2. Navigate to: Settings → API → API Keys
3. Revoke old key
4. Generate new key
5. Update database:
```sql
UPDATE tenant_configs
SET api_key = 'new-api-key-xyz'
WHERE tenant_id = 'test-tenant';
```

**Option C: Verify API endpoint permissions**
In ServiceDesk Plus:
1. Settings → API → Scopes
2. Ensure API key has permission for: `TICKETS_UPDATE`

**Manual Retry:**
```bash
# After fixing API key, re-run enhancement
python -c "
from src.services.servicedesk_client import update_ticket_with_enhancement
import asyncio

asyncio.run(update_ticket_with_enhancement(
    base_url='https://api.servicedesk-plus.local',
    api_key='new-api-key-xyz',
    ticket_id='TKT-12345',
    enhancement='## Enhancement...',
    correlation_id='550e8400-e29b-41d4-a716-446655440000'
))
"
```

---

### 4. ServiceDesk Plus Rate Limit Exceeded

**Symptom:**
```
error_message: "ServiceDesk API returned 429 Too Many Requests"
status: 'failed'
```

**Cause:** Too many API requests to ServiceDesk Plus

**Investigation:**
```bash
# Check rate limit headers
curl -i -X GET \
  "https://api.servicedesk-plus.local/api/v3/tickets/TKT-12345" \
  -H "Authorization: apikey ${SERVICEDESK_API_KEY}" | grep -i "rate-limit"

# Check recent API calls
SELECT COUNT(*) as count FROM logs WHERE level='INFO'
  AND message LIKE '%ServiceDesk API%'
  AND created_at > NOW() - INTERVAL '1 minute';
```

**Resolution:**

**Option A: Celery will auto-retry with exponential backoff**
- Default retry delay: 60 seconds
- Max retries: 3
- Already implemented in `src/services/servicedesk_client.py`

**Option B: Reduce concurrent Celery workers**
```yaml
# docker-compose.yml or Kubernetes deployment
celery:
  environment:
    CELERY_CONCURRENCY: 2  # Reduce from 4 to 2
```

**Option C: Implement request queuing**
```python
# In src/services/servicedesk_client.py
import asyncio

_semaphore = asyncio.Semaphore(1)  # Limit concurrent API calls to 1

async def update_ticket_with_enhancement(...):
    async with _semaphore:  # Queue requests
        response = await client.post(...)
```

**Option D: Contact ServiceDesk Plus support**
- Check if account has rate limit increase available
- Request: increase limits from default (usually 100 req/min) to 500 req/min

**Manual Retry:**
```bash
# Wait 2 minutes, then retry
sleep 120

python -c "
from src.workers.tasks import enhance_ticket
enhance_ticket.apply_async(
    args=[...],
    countdown=60  # Delay before execution
)
"
```

---

### 5. Redis Connection Failure

**Symptom:**
```
error_message: "Connection refused: redis://redis:6379"
status: 'failed'
```

**Cause:** Redis server is down or unreachable

**Investigation:**
```bash
# Test Redis connectivity
redis-cli -h redis -p 6379 ping
# Should return: PONG

# Check Redis logs
docker logs ai-ops-redis | tail -50

# Check Redis memory usage
redis-cli -h redis info memory | grep used_memory

# Check Redis key count
redis-cli -h redis dbsize
```

**Resolution:**

**Option A: Restart Redis**
```bash
# Docker
docker restart ai-ops-redis

# Kubernetes
kubectl rollout restart deployment/redis -n default

# Wait for startup (~5 seconds)
sleep 5
redis-cli -h redis ping
```

**Option B: Check Redis configuration**
```bash
# View Redis config
docker exec ai-ops-redis redis-cli CONFIG GET "*"

# Common issues:
# - maxmemory exceeded
# - append-only file corruption
```

**Option C: Increase Redis memory allocation**
```yaml
# docker-compose.yml
redis:
  command: redis-server --maxmemory 1gb --maxmemory-policy allkeys-lru
```

**Option D: Check network connectivity**
```bash
# From Celery worker pod
kubectl exec -it celery-worker-xyz -c worker -- /bin/bash
nc -zv redis 6379  # Should succeed
```

**Manual Retry:**
```bash
# After Redis is online, re-queue job
python -c "
from src.queue.redis_queue import push_to_queue
push_to_queue({
    'job_id': '550e8400...',
    'ticket_id': 'TKT-12345',
    # ... other fields
})
"
```

---

### 6. Database Connection Failure

**Symptom:**
```
error_message: "Database connection lost during enhancement_history update"
status: 'pending'  # Still pending, never completed
```

**Cause:** PostgreSQL connection lost or database unavailable

**Investigation:**
```bash
# Test PostgreSQL connectivity
psql -h postgres -U postgres -d ai_agents_db -c "SELECT 1"

# Check PostgreSQL logs
docker logs ai-ops-postgres | tail -50

# Check connection pool status
SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;
```

**Resolution:**

**Option A: Restart PostgreSQL**
```bash
# Docker
docker restart ai-ops-postgres

# Kubernetes
kubectl rollout restart statefulset/postgres -n default

# Wait for startup (~10 seconds)
sleep 10
psql -h postgres -c "SELECT 1"
```

**Option B: Check database disk space**
```bash
# Inside PostgreSQL
SELECT pg_database.datname, pg_size_pretty(pg_database_size(pg_database.datname))
FROM pg_database ORDER BY pg_database_size DESC;

# If full, expand volume
kubectl patch pvc postgres-data -p '{"spec":{"resources":{"requests":{"storage":"100Gi"}}}}'
```

**Option C: Check connection pool exhaustion**
```python
# In src/database/session.py
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,          # Increase from 10
    max_overflow=10,       # Increase from 5
    pool_recycle=3600,     # Recycle connections hourly
    pool_pre_ping=True     # Validate connections
)
```

**Option D: Verify table exists**
```sql
-- Check enhancement_history table
\dt+ enhancement_history

-- If missing, run migrations
alembic upgrade head
```

**Manual Retry:**
```bash
# After database is online
python -c "
from src.workers.tasks import enhance_ticket
enhance_ticket.apply_async(args=[...])
"
```

---

## Monitoring & Alerting Setup

### Prometheus Metrics (Story 4.1)

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'celery'
    static_configs:
      - targets: ['localhost:5555']  # Celery Flower metrics

  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:6379']
```

### Grafana Dashboard Alerts

**Create Alert:** Enhancement Failure Rate > 5%

```sql
-- Query
SELECT COUNT(*) FILTER (WHERE status='failed') * 100.0 / COUNT(*)
FROM enhancement_history
WHERE created_at > NOW() - INTERVAL '1 hour';
```

**Create Alert:** Correlation ID Tracing

```bash
# Check correlation ID consistency
SELECT COUNT(DISTINCT correlation_id)
FROM enhancement_history
WHERE created_at > NOW() - INTERVAL '1 day'
  AND status = 'failed';
```

---

## Quick Reference Commands

```bash
# View recent failures
docker exec ai-ops-postgres psql -U postgres -d ai_agents_db -c \
  "SELECT correlation_id, ticket_id, error_message FROM enhancement_history WHERE status='failed' ORDER BY created_at DESC LIMIT 10;"

# Check Celery task queue
celery -A src.workers.celery_app inspect active

# Monitor worker health
celery -A src.workers.celery_app inspect stats

# View logs for specific correlation ID
grep -r "correlation_id=550e8400-e29b-41d4-a716-446655440000" /var/log/

# Retry failed task
python -c "from src.workers.tasks import enhance_ticket; enhance_ticket.apply_async(args=[...])"

# Clear stuck tasks
celery -A src.workers.celery_app purge
```

---

## Escalation Path

1. **First Response** (5 min): Identify failure type using this runbook
2. **Mitigation** (15 min): Apply relevant resolution
3. **Validation** (10 min): Verify enhancement now succeeds
4. **Post-Mortem** (next day): Root cause analysis and prevention

**Contacts:**
- **DevOps Lead:** DevOps team Slack channel
- **Database Admin:** Database team for schema/connection issues
- **API Team:** OpenRouter/ServiceDesk Plus integrations
- **On-Call Engineer:** On-call rotation schedule

---

## Prevention Measures

### 1. Circuit Breaker for LLM
```python
# src/services/llm_synthesis.py
@circuitbreaker(failure_threshold=5, recovery_timeout=60)
async def synthesize_enhancement(...):
    # Auto-fallback if OpenRouter fails 5+ times
```

### 2. Health Check Endpoint
```python
# src/api/health.py
@router.get("/health/enhancement")
async def check_enhancement_health():
    checks = {
        "redis": await check_redis(),
        "postgres": await check_postgres(),
        "openrouter": await check_openrouter(),
        "servicedesk": await check_servicedesk(),
    }
    return {
        "status": "healthy" if all(checks.values()) else "degraded",
        "checks": checks
    }
```

### 3. Automated Retries with Exponential Backoff
```python
# Already implemented in:
# - src/services/servicedesk_client.py (retry on 429/5xx)
# - src/workers/tasks.py (Celery retry configuration)
```

### 4. Observability
- All phases log with correlation_id ✓
- Processing time tracked in enhancement_history ✓
- Error messages captured for debugging ✓
- Context node timing recorded ✓

---

## Related Documentation

- **End-to-End Workflow:** `docs/end-to-end-enhancement-workflow.md`
- **Architecture:** `docs/architecture.md`
- **Tech Spec:** `docs/tech-spec-epic-2.md`
- **Deployment:** `docs/deployment.md`
