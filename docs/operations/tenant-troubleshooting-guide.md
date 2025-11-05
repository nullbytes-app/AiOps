# Tenant Troubleshooting Guide

**Version:** 1.0
**Last Updated:** 2025-11-03
**Owner:** Operations & Support Team
**Status:** Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Diagnostics](#quick-diagnostics)
3. [Common Issues](#common-issues)
4. [Escalation Procedures](#escalation-procedures)
5. [Debugging Tools](#debugging-tools)
6. [References](#references)

---

## Overview

### Purpose

This guide provides troubleshooting procedures for tenant-specific issues in the AI Agents Ticket Enhancement Platform. It covers common problems reported by MSP clients and their support teams.

### When to Use This Guide

- Client reports tickets not receiving enhancements
- Webhook delivery failures
- Enhancement quality issues
- Performance degradation for specific tenant
- Data isolation concerns

### Severity Levels

| Level | Description | Response Time | Escalation |
|-------|-------------|---------------|------------|
| **P0 - Critical** | Data leak, complete outage, security breach | Immediate | Security + Eng Lead |
| **P1 - High** | Partial outage, all tickets failing | < 30 min | Engineering Lead |
| **P2 - Medium** | Intermittent failures, degraded performance | < 2 hours | On-call engineer |
| **P3 - Low** | Enhancement quality issues, minor bugs | < 24 hours | Support team |

---

## Quick Diagnostics

### Step 1: Identify Tenant

Obtain tenant identifier from client:

```bash
# Query by company name
psql -h <RDS_ENDPOINT> -U aiagents -d ai_agents -c "
SELECT tenant_id, name, servicedesk_url, created_at
FROM tenant_configs
WHERE name ILIKE '%<CLIENT_NAME>%';"

# Example: WHERE name ILIKE '%Acme%'
```

**Save tenant_id for subsequent commands.**

### Step 2: Check Tenant Health

```bash
# Set tenant ID variable
TENANT_ID="550e8400-e29b-41d4-a716-446655440000"

# Check recent enhancement requests (last 24 hours)
psql -h <RDS_ENDPOINT> -U aiagents -d ai_agents -c "
SELECT COUNT(*) as total_requests,
       SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
       SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
       AVG(EXTRACT(EPOCH FROM (completed_at - created_at))) as avg_duration_seconds
FROM enhancement_history
WHERE tenant_id = '$TENANT_ID'
  AND created_at > NOW() - INTERVAL '24 hours';"

# Healthy tenant metrics:
# - completed rate > 95%
# - avg_duration_seconds < 15s
```

### Step 3: Review Recent Errors

```bash
# Check FastAPI logs for tenant errors (last 1000 lines)
kubectl logs -n production deployment/ai-agents-api --tail=1000 | grep "tenant_id=$TENANT_ID" | grep "ERROR"

# Check Celery worker logs
kubectl logs -n production deployment/ai-agents-worker --tail=1000 | grep "tenant_id=$TENANT_ID" | grep "ERROR"
```

### Step 4: Verify Configuration

```bash
# Query tenant configuration
psql -h <RDS_ENDPOINT> -U aiagents -d ai_agents -c "
SELECT tenant_id,
       name,
       servicedesk_url,
       enhancement_preferences->>'llm_model' as model,
       enhancement_preferences->>'max_tokens' as max_tokens,
       created_at,
       updated_at
FROM tenant_configs
WHERE tenant_id = '$TENANT_ID';"

# Verify:
# - servicedesk_url is correct and reachable
# - enhancement_preferences valid JSON
# - updated_at recent (if recent config changes expected)
```

---

## Common Issues

### Issue 1: Tickets Not Receiving Enhancements

#### Symptoms
- Client reports tickets submitted but no enhancement appears
- No enhancement_history records for tenant
- Webhook test successful but production tickets fail

#### Diagnostic Steps

**1. Verify Webhook Delivery**

```bash
# Check if webhooks reaching API (last 100 requests)
kubectl logs -n production deployment/ai-agents-api --tail=100 | grep "webhook_received.*tenant_id=$TENANT_ID"

# Expected: Entries showing webhook_received events
# If no entries: Webhook not reaching API (see Resolution A)
```

**2. Check Signature Validation**

```bash
# Look for signature validation errors
kubectl logs -n production deployment/ai-agents-api --tail=100 | grep "tenant_id=$TENANT_ID" | grep -i "signature"

# Expected: "signature_valid"
# If "signature_invalid" or "signature_mismatch": See Resolution B
```

**3. Check Redis Queue**

```bash
# Verify jobs queued
redis-cli -h <ELASTICACHE_ENDPOINT> LLEN enhancement_queue

# If queue depth > 100: Workers not processing (see Resolution C)
# If queue depth = 0: Jobs being processed, check worker logs
```

**4. Check Worker Processing**

```bash
# Monitor worker activity
kubectl logs -n production deployment/ai-agents-worker --tail=50 | grep "tenant_id=$TENANT_ID"

# Expected: Task processing logs (task_received, task_processing, task_completed)
# If no logs: Workers not picking up tenant jobs (see Resolution D)
```

#### Resolution A: Webhook Not Reaching API

**Possible Causes:**
1. ServiceDesk Plus webhook disabled or misconfigured
2. Network connectivity issue (firewall blocking)
3. Ingress controller routing problem
4. API pods crashed or not running

**Steps:**

```bash
# 1. Verify API pods running
kubectl get pods -n production -l app=api
# Expected: All pods Running (not CrashLoopBackOff)

# 2. Check ingress configuration
kubectl get ingress -n production ai-agents-ingress -o yaml | grep -A 5 "host:"
# Verify: host matches webhook URL domain

# 3. Test API endpoint accessibility
curl -i https://api.ai-agents.production/health
# Expected: 200 OK {"status": "healthy"}

# 4. Ask client to re-test webhook from ServiceDesk Plus admin
# Admin → Automation → Webhooks → Test Webhook button
```

**If API inaccessible:**
- Check ingress controller logs: `kubectl logs -n ingress-nginx deployment/ingress-nginx-controller`
- Verify TLS certificate valid: `kubectl get certificate -n production`
- Test from inside cluster: `kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- curl http://ai-agents-api.production.svc.cluster.local:8000/health`

#### Resolution B: Signature Validation Fails

**Possible Causes:**
1. Signing secret mismatch (database vs ServiceDesk Plus)
2. ServiceDesk Plus not sending X-ServiceDesk-Signature header
3. Incorrect HMAC algorithm (must be HMAC-SHA256)

**Steps:**

```bash
# 1. Retrieve signing secret from database
psql -h <RDS_ENDPOINT> -U aiagents -d ai_agents -c "
SELECT webhook_signing_secret_encrypted
FROM tenant_configs
WHERE tenant_id = '$TENANT_ID';"

# 2. Decrypt secret (if using Fernet)
python3 <<EOF
from cryptography.fernet import Fernet
import os
cipher = Fernet(os.getenv('TENANT_ENCRYPTION_KEY').encode())
encrypted = b'<ENCRYPTED_SECRET_FROM_DB>'
decrypted = cipher.decrypt(encrypted).decode()
print(f'Decrypted secret: {decrypted}')
EOF

# 3. Compare with ServiceDesk Plus configuration
# - Login to client's ServiceDesk Plus admin
# - Navigate to Webhooks → AI Agents webhook
# - Verify signing secret matches exactly

# 4. Test signature computation manually
echo -n '{"ticket_id":"TKT-123"}' | openssl dgst -sha256 -hmac "<SECRET_FROM_DB>"
# Compare output with X-ServiceDesk-Signature header value from failed request

# 5. If mismatch found, update ServiceDesk Plus webhook configuration
# or regenerate secret and update both locations
```

#### Resolution C: Workers Not Processing (Queue Backup)

**Possible Causes:**
1. Celery workers crashed or stuck
2. Database connection pool exhausted
3. ServiceDesk Plus API slow/unresponsive
4. LLM API rate limiting

**Steps:**

```bash
# 1. Check worker pod status
kubectl get pods -n production -l app=worker
# Expected: All pods Running (not Pending, Error, CrashLoopBackOff)

# 2. Check worker resource usage
kubectl top pods -n production -l app=worker
# If CPU > 90% or Memory near limit: Workers overloaded, scale up

# 3. Scale workers horizontally
kubectl scale deployment ai-agents-worker --replicas=5 -n production
# Monitor queue depth decrease: redis-cli -h <ENDPOINT> LLEN enhancement_queue

# 4. Check database connection pool
psql -h <RDS_ENDPOINT> -U aiagents -d ai_agents -c "
SELECT COUNT(*) as active_connections
FROM pg_stat_activity
WHERE datname = 'ai_agents';"
# If near max_connections limit (e.g., 95/100), restart workers to reset pool

# 5. Restart workers if stuck
kubectl rollout restart deployment/ai-agents-worker -n production
kubectl rollout status deployment/ai-agents-worker -n production
```

#### Resolution D: Workers Not Picking Up Tenant Jobs

**Possible Causes:**
1. RLS context not set (worker fails to query tenant_configs)
2. Tenant credentials invalid (ServiceDesk Plus API auth fails)
3. LLM API key expired or rate limited

**Steps:**

```bash
# 1. Check worker logs for RLS errors
kubectl logs -n production deployment/ai-agents-worker --tail=100 | grep "tenant_context"
# Expected: "Setting tenant context: tenant_id=..."
# If error: RLS policy or helper function issue

# 2. Test RLS context setting manually
psql -h <RDS_ENDPOINT> -U aiagents -d ai_agents -c "
SELECT set_tenant_context('$TENANT_ID');
SELECT * FROM tenant_configs WHERE tenant_id = '$TENANT_ID';"
# If error: RLS helper function broken (escalate to engineering)

# 3. Verify ServiceDesk Plus credentials
kubectl exec -n production deployment/ai-agents-worker -- python3 <<EOF
import os
import requests
api_key = "<DECRYPTED_API_KEY>"  # From tenant_configs
url = "<SERVICEDESK_URL>/api/v3/tickets/1"
headers = {"Authorization": f"Bearer {api_key}"}
r = requests.get(url, headers=headers)
print(f"Status: {r.status_code}")
EOF
# Expected: 200 or 404 (ticket not found)
# If 401: Credentials invalid, update tenant_configs

# 4. Check LLM API key
kubectl get secret ai-agents-secrets -n production -o jsonpath='{.data.OPENAI_API_KEY}' | base64 -d
# Test key validity: curl -H "Authorization: Bearer <KEY>" https://api.openai.com/v1/models
```

---

### Issue 2: Enhancement Quality Poor

#### Symptoms
- Client reports irrelevant or unhelpful enhancements
- Enhancement suggestions don't address ticket issue
- Low client satisfaction ratings (< 3 stars)

#### Diagnostic Steps

**1. Review Enhancement Content**

```sql
-- Query recent enhancements for tenant
SELECT ticket_id,
       LEFT(enhancement_text, 200) as preview,
       confidence_score,
       duration_seconds,
       created_at
FROM enhancement_history
WHERE tenant_id = '$TENANT_ID'
ORDER BY created_at DESC
LIMIT 10;
```

**2. Check Context Data Availability**

```sql
-- Check ticket history volume
SELECT COUNT(*) as ticket_count,
       MIN(created_at) as oldest_ticket,
       MAX(created_at) as newest_ticket
FROM ticket_history
WHERE tenant_id = '$TENANT_ID';

-- Healthy: 100+ tickets spanning 30+ days
-- If < 50 tickets: Insufficient context for quality enhancements
```

**3. Review Enhancement Preferences**

```sql
-- Query current preferences
SELECT enhancement_preferences
FROM tenant_configs
WHERE tenant_id = '$TENANT_ID';

-- Check:
-- - context_sources includes ["ticket_history", "kb", "monitoring"]
-- - llm_model appropriate (gpt-4o-mini vs gpt-4o)
-- - max_tokens sufficient (500+ for detailed enhancements)
```

#### Resolution

**Option 1: Populate Ticket History (if insufficient data)**

```bash
# Run historical ticket import (if available)
# See Story 2.5A for populate-ticket-history.py script

python3 scripts/populate-ticket-history.py \
  --tenant-id "$TENANT_ID" \
  --days-back 90 \
  --only-resolved

# Verify import
psql -h <RDS_ENDPOINT> -U aiagents -d ai_agents -c "
SELECT COUNT(*) FROM ticket_history WHERE tenant_id = '$TENANT_ID';"
```

**Option 2: Adjust Enhancement Preferences**

```sql
-- Add more context sources
UPDATE tenant_configs
SET enhancement_preferences = jsonb_set(
    enhancement_preferences,
    '{context_sources}',
    '["ticket_history", "kb", "monitoring", "recent_alerts", "system_inventory"]'::jsonb
)
WHERE tenant_id = '$TENANT_ID';

-- Increase max_tokens for more detailed enhancements
UPDATE tenant_configs
SET enhancement_preferences = jsonb_set(
    enhancement_preferences,
    '{max_tokens}',
    '750'::jsonb
)
WHERE tenant_id = '$TENANT_ID';

-- Upgrade LLM model (if client willing to pay higher cost)
UPDATE tenant_configs
SET enhancement_preferences = jsonb_set(
    enhancement_preferences,
    '{llm_model}',
    '"openai/gpt-4o"'::jsonb  -- More capable but 10x cost
)
WHERE tenant_id = '$TENANT_ID';
```

**Option 3: Tune LLM Prompt (Engineering Task)**

If consistent quality issues across multiple tenants, consider prompt engineering improvements:
- Review `src/enhancement/prompts.py`
- Adjust system prompt, few-shot examples, or temperature
- A/B test changes with subset of clients

---

### Issue 3: Performance Degradation

#### Symptoms
- Enhancement latency > 30 seconds (normal < 15s)
- Client reports slow ticket updates
- Grafana dashboard shows high p95 latency for tenant

#### Diagnostic Steps

**1. Check Recent Latency**

```sql
-- Query enhancement latency (last 24 hours)
SELECT MIN(duration_seconds) as min_latency,
       AVG(duration_seconds) as avg_latency,
       MAX(duration_seconds) as max_latency,
       PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_seconds) as p95_latency
FROM enhancement_history
WHERE tenant_id = '$TENANT_ID'
  AND created_at > NOW() - INTERVAL '24 hours';

-- Thresholds:
-- - avg_latency < 10s: Excellent
-- - avg_latency 10-20s: Acceptable
-- - avg_latency > 20s: Investigate
```

**2. Identify Bottleneck**

```bash
# Use Jaeger distributed tracing to identify slow spans
kubectl port-forward -n production svc/jaeger-query 16686:16686

# Open http://localhost:16686
# Search: service=ai-agents-worker, tag: tenant_id=$TENANT_ID
# Look for longest spans (e.g., llm_synthesis, servicedesk_api_call)
```

**3. Check Resource Utilization**

```bash
# Worker CPU/memory usage
kubectl top pods -n production -l app=worker

# Database query performance
psql -h <RDS_ENDPOINT> -U aiagents -d ai_agents -c "
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE query LIKE '%$TENANT_ID%'
ORDER BY mean_exec_time DESC
LIMIT 10;"
```

#### Resolution

**If LLM API slow:**
- Check OpenRouter status: https://openrouter.ai/status
- Consider switching to faster model (gpt-4o-mini faster than gpt-4o)
- Reduce max_tokens to decrease generation time

**If ServiceDesk Plus API slow:**
- Coordinate with client IT to investigate their API performance
- Check if ServiceDesk Plus instance overloaded or undergoing maintenance
- Consider caching ticket metadata to reduce API calls

**If database slow:**
- Review slow queries in pg_stat_statements
- Add indexes if full table scans detected
- Scale up RDS instance if CPU > 80%

**If workers overloaded:**
```bash
# Scale workers horizontally
kubectl scale deployment ai-agents-worker --replicas=5 -n production

# Or configure HorizontalPodAutoscaler
kubectl autoscale deployment ai-agents-worker \
  --min=3 --max=10 \
  --cpu-percent=70 \
  -n production
```

---

### Issue 4: Data Isolation Concern (Security)

#### Symptoms
- Client reports seeing data from another client (CRITICAL)
- Cross-tenant ticket IDs visible
- Enhancement references tickets from different MSP

#### Severity: **P0 - CRITICAL**

#### Immediate Response

```bash
# 1. IMMEDIATELY disable all webhook processing
kubectl scale deployment ai-agents-worker --replicas=0 -n production

# 2. Verify RLS enabled
psql -h <RDS_ENDPOINT> -U aiagents -d ai_agents -c "
SELECT tablename, rowsecurity
FROM pg_tables
WHERE tablename IN ('tenant_configs', 'enhancement_history', 'ticket_history', 'system_inventory');"

# Expected: rowsecurity = true for ALL tables
# If ANY table shows false: CRITICAL RLS NOT ENABLED

# 3. Check RLS policies exist
psql -h <RDS_ENDPOINT> -U aiagents -d ai_agents -c "
SELECT tablename, policyname, cmd, qual
FROM pg_policies
WHERE tablename IN ('tenant_configs', 'enhancement_history', 'ticket_history', 'system_inventory')
ORDER BY tablename, policyname;"

# Expected: 3+ policies with qual containing "current_setting('app.current_tenant_id')"
```

#### Root Cause Analysis

```sql
-- Test RLS enforcement manually
SET app.current_tenant_id = '$TENANT_ID';

-- This query should return 0 rows (RLS filters out other tenants)
SELECT COUNT(*)
FROM enhancement_history
WHERE tenant_id != '$TENANT_ID';

-- If returns rows > 0: RLS NOT ENFORCING (CRITICAL BUG)
```

#### Resolution (After Root Cause Identified)

**If RLS not enabled:**
```sql
-- Enable RLS on all tenant tables
ALTER TABLE tenant_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE enhancement_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE ticket_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_inventory ENABLE ROW LEVEL SECURITY;

-- Verify enabled
SELECT tablename, rowsecurity FROM pg_tables
WHERE tablename IN ('tenant_configs', 'enhancement_history', 'ticket_history', 'system_inventory');
```

**If RLS policies missing:**
```sql
-- Re-apply RLS migration
-- Run Alembic migration: 168c9b67e6ca_add_row_level_security_policies.py

cd /path/to/project
alembic upgrade 168c9b67e6ca
```

**Post-Resolution:**
1. Re-enable workers: `kubectl scale deployment ai-agents-worker --replicas=3 -n production`
2. Run tenant isolation validation script: `./scripts/tenant-isolation-validation.sh`
3. Monitor for 24 hours before considering resolved
4. Conduct security audit with incident report
5. Notify affected clients and provide transparency on remediation

#### Escalation

**Immediately escalate to:**
- Security Team Lead
- Engineering Director
- CEO/CTO (if data confirmed leaked)

**External notifications (if confirmed breach):**
- Affected clients (within 72 hours per GDPR)
- Legal counsel
- Regulatory bodies (if applicable)

---

### Issue 5: Rate Limiting or Throttling

#### Symptoms
- 429 Too Many Requests errors in logs
- Client reports intermittent enhancement failures
- Grafana shows request spikes

#### Diagnostic Steps

```bash
# 1. Check request volume (last 24 hours)
psql -h <RDS_ENDPOINT> -U aiagents -d ai_agents -c "
SELECT DATE_TRUNC('hour', created_at) as hour,
       COUNT(*) as requests
FROM enhancement_history
WHERE tenant_id = '$TENANT_ID'
  AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour DESC;"

# 2. Check tenant rate limits
psql -h <RDS_ENDPOINT> -U aiagents -d ai_agents -c "
SELECT rate_limits
FROM tenant_configs
WHERE tenant_id = '$TENANT_ID';"

# 3. Review rate limit violations
kubectl logs -n production deployment/ai-agents-api --tail=100 | grep "rate_limit_exceeded.*tenant_id=$TENANT_ID"
```

#### Resolution

**If tenant legitimately exceeding limits:**
```sql
-- Increase rate limits (requires approval from product/sales)
UPDATE tenant_configs
SET rate_limits = jsonb_set(
    rate_limits,
    '{requests_per_minute}',
    '200'::jsonb  -- Increase from 100 to 200
)
WHERE tenant_id = '$TENANT_ID';
```

**If rate limiting too aggressive:**
- Review rate limiting algorithm (token bucket vs sliding window)
- Consider implementing per-client tiered limits (Basic: 100/min, Premium: 500/min)
- Add burst tolerance for short spikes

**If LLM API rate limiting:**
- Check OpenRouter account limits
- Upgrade OpenRouter tier if needed
- Implement request queuing with exponential backoff

---

## Escalation Procedures

### When to Escalate

| Condition | Escalate To | Response Time |
|-----------|-------------|---------------|
| Data isolation breach | Security Lead + Engineering Director | Immediate |
| All enhancements failing for tenant > 1 hour | Engineering Lead | 30 minutes |
| RLS policies not enforcing | Engineering Director | Immediate |
| Database connection exhausted | Database Admin + On-call Engineer | 15 minutes |
| Client escalation (C-level complaint) | Customer Success Manager + VP Engineering | 1 hour |

### Escalation Contacts

**Engineering:**
- On-call Engineer: PagerDuty escalation policy `ai-agents-oncall`
- Engineering Lead: John Doe (john.doe@company.com, +1-555-0100)
- Engineering Director: Jane Smith (jane.smith@company.com, +1-555-0101)

**Security:**
- Security Lead: Bob Johnson (bob.johnson@company.com, +1-555-0200)
- Security On-call: PagerDuty escalation policy `security-oncall`

**Customer Success:**
- CSM Team Lead: Alice Williams (alice.williams@company.com, +1-555-0300)

### Incident Management

**For P0/P1 incidents:**

1. **Create incident ticket:** `incident-YYYYMMDD-HHMM-description`
2. **Start incident Slack channel:** `#incident-<ticket-number>`
3. **Page on-call engineer:** Via PagerDuty
4. **Initiate incident bridge:** Zoom link in Slack channel
5. **Assign incident commander:** First responder or on-call lead
6. **Document timeline:** Incident commander logs key events in Slack
7. **Post-incident review:** Within 48 hours of resolution

---

## Debugging Tools

### Database Queries

```sql
-- Get tenant overview
SELECT t.tenant_id,
       t.name,
       t.created_at,
       COUNT(DISTINCT eh.ticket_id) as total_tickets_enhanced,
       COUNT(DISTINCT th.ticket_id) as total_ticket_history,
       AVG(eh.duration_seconds) as avg_enhancement_duration
FROM tenant_configs t
LEFT JOIN enhancement_history eh ON t.tenant_id = eh.tenant_id
LEFT JOIN ticket_history th ON t.tenant_id = th.tenant_id
WHERE t.tenant_id = '$TENANT_ID'
GROUP BY t.tenant_id, t.name, t.created_at;

-- Find failed enhancements
SELECT ticket_id,
       error_message,
       duration_seconds,
       created_at
FROM enhancement_history
WHERE tenant_id = '$TENANT_ID'
  AND status = 'failed'
ORDER BY created_at DESC
LIMIT 10;

-- Check RLS helper function
SELECT set_tenant_context('$TENANT_ID');
SELECT current_setting('app.current_tenant_id', true);
```

### Kubernetes Commands

```bash
# Get all tenant resources (Premium tier)
kubectl get all -n tenant-<name> --show-labels

# Check pod logs with tenant filter
kubectl logs -n production deployment/ai-agents-worker --tail=100 | grep "tenant_id=$TENANT_ID"

# Execute command in worker pod (debugging)
kubectl exec -it -n production deployment/ai-agents-worker -- /bin/bash

# Port-forward to Grafana
kubectl port-forward -n production svc/grafana 3000:3000

# Port-forward to Jaeger
kubectl port-forward -n production svc/jaeger-query 16686:16686
```

### Monitoring Queries

**Prometheus:**
```promql
# Enhancement success rate (last 1 hour)
rate(enhancement_requests_total{tenant_id="$TENANT_ID",status="success"}[1h])
/
rate(enhancement_requests_total{tenant_id="$TENANT_ID"}[1h])

# Enhancement latency (p95, last 5 minutes)
histogram_quantile(0.95,
  rate(enhancement_request_duration_seconds_bucket{tenant_id="$TENANT_ID"}[5m])
)

# Worker queue depth
redis_queue_depth{queue="enhancement_queue"}
```

**Grafana Dashboards:**
- **System Overview:** `http://localhost:3000/d/system-overview`
- **Per-Tenant Metrics:** `http://localhost:3000/d/tenant-metrics?var-tenant_id=$TENANT_ID`
- **Enhancement Pipeline:** `http://localhost:3000/d/enhancement-pipeline`

---

## References

### Internal Documentation

- [Client Onboarding Runbook](client-onboarding-runbook.md) - Onboarding procedures
- [Production Deployment Runbook](production-deployment-runbook.md) - Infrastructure operations
- [Architecture Documentation](../architecture.md) - System design and RLS
- [PRD](../PRD.md) - Product requirements

### Code References

- `src/services/tenant_service.py` - Tenant CRUD operations
- `src/database/tenant_context.py` - RLS context management
- `src/api/webhooks.py` - Webhook receiver endpoint
- `src/services/webhook_validator.py` - Signature validation
- `src/workers/tasks.py` - Celery enhancement task
- `alembic/versions/168c9b67e6ca_add_row_level_security_policies.py` - RLS migration

### External Resources

- [PostgreSQL Row-Level Security Documentation](https://www.postgresql.org/docs/17/ddl-rowsecurity.html)
- [Kubernetes Troubleshooting Guide](https://kubernetes.io/docs/tasks/debug/)
- [Celery Debugging Guide](https://docs.celeryq.dev/en/stable/userguide/debugging.html)
- [OpenRouter Status Page](https://openrouter.ai/status)

---

**Document Version History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-03 | Operations Team | Initial release (Story 5.3) |

**Review Schedule:** Quarterly review, next due 2026-02-03
