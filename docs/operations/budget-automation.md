# Budget Automation - Operational Guide

**Story:** 8.10C - Budget Enforcement Operational Features
**Generated:** 2025-11-06
**Status:** Production-Ready

## Overview

This guide covers the operational setup and management of automated budget reset and override expiry features for the AI Agents platform.

## Architecture

### Components

1. **Celery Beat Scheduler** - Triggers periodic tasks
2. **Celery Workers** - Execute budget automation tasks
3. **LiteLLM Proxy** - Manages virtual key budgets and webhooks
4. **Budget Service** - Handles reset logic and API interactions
5. **Notification Service** - Sends alerts to tenant admins

### Periodic Tasks

```yaml
Task: reset_tenant_budgets
Schedule: Daily at 00:00 UTC (crontab(hour=0, minute=0))
Purpose: Reset budgets for tenants whose budget_reset_at <= NOW()
Timeout: 10 minutes (soft), 11 minutes (hard)
Retry: Max 3 attempts, 5-minute countdown

Task: expire_budget_overrides
Schedule: Hourly at :00 (crontab(minute=0))
Purpose: Remove expired budget overrides and reset virtual keys
Timeout: 5 minutes (soft), 5.5 minutes (hard)
Retry: Max 3 attempts, 3-minute countdown
```

## Setup Instructions

### 1. Environment Configuration

Add to `.env`:

```bash
# LiteLLM Webhook Secret (HMAC signature validation)
AI_AGENTS_LITELLM_WEBHOOK_SECRET=<generate with: openssl rand -hex 32>
```

### 2. Celery Beat Configuration

**File:** `src/workers/celery_app.py`

```python
celery_app.conf.beat_schedule = {
    'reset-tenant-budgets-daily': {
        'task': 'tasks.reset_tenant_budgets',
        'schedule': crontab(hour=0, minute=0),
        'options': {'expires': 3600},
    },
    'expire-budget-overrides-hourly': {
        'task': 'tasks.expire_budget_overrides',
        'schedule': crontab(minute=0),
        'options': {'expires': 1800},
    },
}
```

### 3. LiteLLM Configuration

**File:** `config/litellm-config.yaml`

```yaml
general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
  database_url: os.environ/DATABASE_URL
  alerting: ["webhook"]  # Enable webhook alerts
```

**File:** `docker-compose.yml`

```yaml
litellm:
  environment:
    WEBHOOK_URL: http://api:8000/api/v1/budget-alerts
```

### 4. Starting Celery Beat

**Production (separate process):**
```bash
celery -A src.workers.celery_app beat --loglevel=info
```

**Development (embedded in worker):**
```bash
celery -A src.workers.celery_app worker --beat --loglevel=info
```

**Docker Compose:**
```bash
docker-compose up worker  # Beat schedule auto-configured
```

## Monitoring

### Check Task Status

```bash
# List active beat schedule
celery -A src.workers.celery_app inspect scheduled

# Check worker stats
celery -A src.workers.celery_app inspect stats

# View task history
celery -A src.workers.celery_app events
```

### Logs

```bash
# Worker logs
docker logs ai-agents-worker -f --tail=100

# Filter budget tasks
docker logs ai-agents-worker 2>&1 | grep "budget"

# Check task results
redis-cli KEYS "celery-task-meta-*" | xargs redis-cli MGET
```

### Metrics

**Prometheus Queries:**

```promql
# Budget reset task duration
celery_task_duration_seconds{task_name="tasks.reset_tenant_budgets"}

# Override expiry success rate
rate(celery_task_success_total{task_name="tasks.expire_budget_overrides"}[5m])

# Failed reset count
celery_task_failure_total{task_name="tasks.reset_tenant_budgets"}
```

## Operational Procedures

### Manual Budget Reset

```bash
# Trigger reset task manually
celery -A src.workers.celery_app call tasks.reset_tenant_budgets

# Reset specific tenant (Python shell)
python
>>> from src.services.budget_service import BudgetService
>>> import asyncio
>>> service = BudgetService()
>>> asyncio.run(service.reset_tenant_budget("tenant-123"))
```

### Manual Override Expiry

```bash
# Trigger expiry task manually
celery -A src.workers.celery_app call tasks.expire_budget_overrides

# Expire specific override (API call)
curl -X DELETE http://localhost:8000/admin/tenants/tenant-123/budget-override \
  -H "Authorization: Bearer $ADMIN_API_KEY"
```

### Grant Budget Override

```bash
# Grant 7-day $100 override
curl -X POST http://localhost:8000/admin/tenants/tenant-123/budget-override \
  -H "Authorization: Bearer $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "override_amount": 100.0,
    "duration": "7d",
    "reason": "Emergency deployment support"
  }'
```

## Troubleshooting

### Reset Task Failures

**Symptom:** Budget reset task fails with "LiteLLM API timeout"

**Diagnosis:**
```bash
# Check LiteLLM proxy health
curl http://localhost:4000/health

# Check virtual key
curl http://localhost:4000/key/info \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -d '{"keys": ["sk-..."]}'
```

**Resolution:**
1. Verify LiteLLM proxy is running: `docker ps | grep litellm`
2. Check network connectivity: `docker exec ai-agents-worker ping litellm`
3. Increase timeout in `tasks.py` if needed (current: 30s)
4. Retry manually: `celery -A src.workers.celery_app call tasks.reset_tenant_budgets`

### Override Expiry Not Running

**Symptom:** Expired overrides not being removed

**Diagnosis:**
```bash
# Check beat scheduler status
celery -A src.workers.celery_app inspect scheduled

# Check last run time (database)
psql -d ai_agents -c "SELECT * FROM audit_logs WHERE operation='budget_override_expired' ORDER BY timestamp DESC LIMIT 5;"
```

**Resolution:**
1. Verify Beat scheduler is running: `ps aux | grep "celery.*beat"`
2. Check beat schedule file permissions: `ls -la celerybeat-schedule`
3. Restart Beat scheduler: `docker-compose restart worker`
4. Check worker logs: `docker logs ai-agents-worker --tail=50`

### Webhook Not Received

**Symptom:** LiteLLM budget alerts not triggering webhook

**Diagnosis:**
```bash
# Check LiteLLM webhook config
docker exec litellm-proxy cat /app/config.yaml | grep -A 5 "alerting"

# Check webhook URL environment variable
docker exec litellm-proxy env | grep WEBHOOK_URL

# Test webhook endpoint directly
curl -X POST http://localhost:8000/api/v1/budget-alerts \
  -H "Content-Type: application/json" \
  -d '{"event": "budget_crossed", "user_id": "test", "max_budget": 100, "current_spend": 101}'
```

**Resolution:**
1. Verify webhook URL in `docker-compose.yml`: `WEBHOOK_URL=http://api:8000/api/v1/budget-alerts`
2. Check API service is running: `docker ps | grep ai-agents-api`
3. Verify webhook endpoint exists: `curl http://localhost:8000/docs` (check /api/v1/budget-alerts)
4. Test inter-container network: `docker exec litellm-proxy curl http://api:8000/health`

### Task Stuck in Queue

**Symptom:** Budget tasks not executing despite being queued

**Diagnosis:**
```bash
# Check queued tasks
celery -A src.workers.celery_app inspect reserved

# Check active tasks
celery -A src.workers.celery_app inspect active

# Check worker availability
celery -A src.workers.celery_app inspect ping
```

**Resolution:**
1. Check worker concurrency: `celery -A src.workers.celery_app inspect stats | grep concurrency`
2. Purge stuck tasks: `celery -A src.workers.celery_app purge`
3. Restart worker: `docker-compose restart worker`
4. Check Redis health: `redis-cli ping`

## Runbooks

### Runbook: Budget Reset Failure Recovery

**Trigger:** Budget reset task fails for multiple tenants

**Steps:**

1. **Identify Failed Tenants**
   ```bash
   # Check task result
   celery -A src.workers.celery_app result <task-id>

   # Query audit logs
   psql -d ai_agents -c "SELECT tenant_id, details FROM audit_logs WHERE operation='budget_reset' AND timestamp > NOW() - INTERVAL '1 day' ORDER BY timestamp DESC;"
   ```

2. **Diagnose Root Cause**
   - LiteLLM API timeout → Increase timeout or check proxy health
   - Virtual key not found → Verify tenant configuration
   - Database connection error → Check PostgreSQL health
   - Rate limiting → Add delay between batch processing

3. **Manual Recovery**
   ```python
   # Reset failed tenants individually
   from src.services.budget_service import BudgetService
   import asyncio

   failed_tenants = ["tenant-1", "tenant-2", "tenant-3"]
   service = BudgetService()

   for tenant_id in failed_tenants:
       try:
           result = asyncio.run(service.reset_tenant_budget(tenant_id))
           print(f"{tenant_id}: {'success' if result else 'failed'}")
       except Exception as e:
           print(f"{tenant_id}: error - {e}")
   ```

4. **Prevent Recurrence**
   - Update task retry logic if needed
   - Add monitoring alerts for reset failures
   - Consider batch size reduction if rate limiting occurs

### Runbook: Emergency Budget Override

**Trigger:** Tenant requires immediate budget increase for urgent work

**Steps:**

1. **Verify Tenant Status**
   ```bash
   # Check current budget status
   curl http://localhost:8000/admin/tenants/tenant-123 \
     -H "Authorization: Bearer $ADMIN_API_KEY" | jq '.budget_status'
   ```

2. **Calculate Override Amount**
   - Review tenant's current spend vs. max budget
   - Estimate additional capacity needed
   - Determine appropriate duration (24h, 7d, 30d)

3. **Grant Override**
   ```bash
   curl -X POST http://localhost:8000/admin/tenants/tenant-123/budget-override \
     -H "Authorization: Bearer $ADMIN_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "override_amount": 200.0,
       "duration": "24h",
       "reason": "Critical production incident - requires additional capacity for diagnostics"
     }'
   ```

4. **Verify Application**
   ```bash
   # Check LiteLLM virtual key updated
   curl http://localhost:4000/key/info \
     -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
     -d '{"keys": ["<tenant-virtual-key>"]}'
   ```

5. **Document and Follow-up**
   - Log override details in incident tracking system
   - Schedule review before expiration
   - Evaluate if base budget adjustment needed

### Runbook: Override Expiry Audit

**Trigger:** Periodic review of expired overrides (weekly/monthly)

**Steps:**

1. **Query Expired Overrides**
   ```sql
   SELECT
     tenant_id,
     operation,
     details->>'override_amount' as amount,
     details->>'reason' as reason,
     timestamp
   FROM audit_logs
   WHERE operation = 'budget_override_expired'
     AND timestamp > NOW() - INTERVAL '30 days'
   ORDER BY timestamp DESC;
   ```

2. **Analyze Trends**
   - Identify tenants with frequent overrides
   - Review common override reasons
   - Calculate total override amounts per tenant

3. **Recommend Budget Adjustments**
   - Tenants with >3 overrides/month → Consider base budget increase
   - Seasonal patterns → Plan for temporary increases
   - Growth trends → Proactive budget scaling

4. **Update Budgets**
   ```bash
   # Update tenant base budget
   curl -X PATCH http://localhost:8000/admin/tenants/tenant-123 \
     -H "Authorization: Bearer $ADMIN_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"max_budget": 500.0, "budget_duration": "30d"}'
   ```

## Security Considerations

### Webhook Signature Validation

The budget alert webhook endpoint validates HMAC signatures using `AI_AGENTS_LITELLM_WEBHOOK_SECRET`:

```python
# Webhook request includes signature
headers = {
    "X-Webhook-Signature": "sha256=<hmac-signature>"
}

# Validation performed by src/api/budget.py
def validate_webhook_signature(payload: bytes, signature: str) -> bool:
    expected = hmac.new(
        settings.litellm_webhook_secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

### Admin API Authorization

Budget override endpoints require platform admin authorization:

```python
@router.post("/admin/tenants/{tenant_id}/budget-override")
async def grant_budget_override(
    admin_key: str = Depends(verify_admin_key)  # Admin role required
):
    ...
```

### Audit Logging

All budget operations are logged to `audit_logs` table:

```python
audit_entry = AuditLog(
    tenant_id=tenant_id,
    operation="budget_reset",  # or "budget_override_granted" / "budget_override_expired"
    user="system",  # or admin identifier
    timestamp=datetime.now(timezone.utc),
    details={
        "old_spend": 45.67,
        "new_budget": 100.0,
        "reset_date": "2025-11-06T00:00:00Z"
    }
)
```

## Performance Considerations

### Batch Processing

Reset task processes 100 tenants per batch with 1-second delay:

```python
batch_size = 100
for i in range(0, len(tenants), batch_size):
    batch = tenants[i:i + batch_size]
    for tenant in batch:
        await reset_tenant_budget(tenant.tenant_id)
    if i + batch_size < len(tenants):
        time.sleep(1)  # Prevent API rate limiting
```

### Task Expiry

Tasks expire if not executed within time limit:

- Reset task: 3600 seconds (1 hour)
- Expiry task: 1800 seconds (30 minutes)

Prevents zombie tasks from accumulating in queue.

### Database Indexing

Ensure indexes exist for efficient queries:

```sql
-- Budget reset queries
CREATE INDEX IF NOT EXISTS idx_tenant_budget_reset_at ON tenant_configs(budget_reset_at) WHERE is_active = true;

-- Override expiry queries
CREATE INDEX IF NOT EXISTS idx_budget_override_expires_at ON budget_overrides(expires_at);
```

## References

- **Parent Story:** [docs/stories/8-10-budget-enforcement-with-grace-period.md](../stories/8-10-budget-enforcement-with-grace-period.md)
- **Context File:** [docs/stories/8-10C-budget-operational-features.context.xml](../stories/8-10C-budget-operational-features.context.xml)
- **Budget Service:** [src/services/budget_service.py](../../src/services/budget_service.py)
- **Celery Tasks:** [src/workers/tasks.py](../../src/workers/tasks.py)
- **Celery Config:** [src/workers/celery_app.py](../../src/workers/celery_app.py)
- **Admin API:** [src/api/admin/tenants.py](../../src/api/admin/tenants.py)

## Change Log

### 2025-11-06 - Initial Version
- Created operational guide for budget automation
- Documented setup, monitoring, and troubleshooting procedures
- Added runbooks for common scenarios
- Included security and performance considerations
