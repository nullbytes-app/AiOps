# High Queue Depth

**Last Updated:** 2025-11-03
**Author:** Amelia (Developer Agent)
**Related Alerts:** QueueDepthHigh (triggers at >100 jobs)
**Severity:** Medium (if trending upward) / Low (if stable)

## Quick Links

- [Symptoms](#symptoms)
- [Diagnosis](#diagnosis)
- [Resolution](#resolution)
- [Escalation](#escalation)
- [Using Distributed Tracing](#using-distributed-tracing-for-diagnosis)

---

## Overview

**When to Use This Runbook:**
- Queue depth elevated (50-100 jobs) but below alert threshold (100 triggers alert)
- Proactive investigation before alert fires
- Gradual queue growth observed over time
- User reports of delayed ticket updates

**Scope:** Investigation and remediation of queue backlog scenarios (excluding full system failures)

**Prerequisites:**
- Access to Prometheus metrics (http://localhost:9090 or production equivalent)
- Access to Redis CLI or docker-compose/kubectl
- Access to Grafana dashboards (http://localhost:3000)

---

## Symptoms

### Observable Indicators

- ✓ Queue depth metric (`queue_depth`) shows value between 50-100 jobs
- ✓ Enhancement processing latency gradually increasing (p95 latency 30-60 seconds)
- ✓ User reports of "ticket updates are slow" or "not processing enhancements"
- ✓ Queue depth stable or slowly trending upward (not sudden spike)
- ✓ Worker count appears normal (>1 active workers)
- ✓ No alerts firing yet (if >100, use QueueDepthHigh alert runbook instead)

### When This Runbook Does NOT Apply

- Queue depth > 100 → Use [Alert Runbooks - QueueDepthHigh](../operations/alert-runbooks.md#queuedepthhigh)
- Workers all down → Use [Worker Failures Runbook](./worker-failures.md)
- Database errors in worker logs → Use [Database Connection Issues Runbook](./database-connection-issues.md)

---

## Diagnosis

### Step 1: Verify Current Queue Depth and Trend

**Docker:**
```bash
# Check current queue depth
docker-compose exec redis redis-cli LLEN enhancement_queue

# Expected Output: 75 (example - number of jobs in queue)
```

**Kubernetes:**
```bash
# Check current queue depth
kubectl exec -it redis-0 -- redis-cli LLEN enhancement_queue

# Expected Output: 75 (example)
```

**Expected Output Range:** 50-100

### Step 2: Check Queue Depth Trend (Last 15 Minutes)

**Prometheus Query (use http://localhost:3000 or Prometheus UI):**

```
queue_depth
```

**What to Look For:**
- Steady increase → Workers can't keep up with incoming jobs
- Stable/plateau → Queue depth manageable, monitoring sufficient
- Jagged pattern → Spiky workload, normal variance

### Step 3: Analyze Queue Age Distribution

**Docker:**
```bash
# Get oldest job (first in queue)
docker-compose exec redis redis-cli LINDEX enhancement_queue 0

# Get newest job (last in queue)
docker-compose exec redis redis-cli LINDEX enhancement_queue -1

# View first 5 jobs to inspect format
docker-compose exec redis redis-cli LRANGE enhancement_queue 0 4
```

**Kubernetes:**
```bash
# Get oldest job
kubectl exec -it redis-0 -- redis-cli LINDEX enhancement_queue 0

# Get newest job
kubectl exec -it redis-0 -- redis-cli LINDEX enhancement_queue -1

# View first 5 jobs
kubectl exec -it redis-0 -- redis-cli LRANGE enhancement_queue 0 4
```

**Expected Output:** JSON objects with ticket_id, tenant_id, created_at timestamp

**What to Look For:**
- Oldest job timestamp: If > 30 minutes old → Investigate stuck jobs in Step 4
- Recent jobs: Normal if created in last 2 minutes

### Step 4: Verify Worker Capacity

**Prometheus Queries:**

```promql
# Current active workers
worker_active_count

# Expected: ≥ 2 workers running
```

```promql
# Recent job success rate (last 5 minutes)
rate(enhancement_requests_total{status="success"}[5m])

# Expected: Should see successful jobs being processed (metric value > 0)
```

**Docker Command:**
```bash
# List running worker containers
docker-compose ps worker

# Expected: RUNNING status, no restart count or low count
```

**Kubernetes Command:**
```bash
# Check worker pod status
kubectl get pods -l app=celery-worker

# Expected: Running status, 1/1 Ready
```

**What to Look For:**
- Worker count = 0 → Escalate immediately (workers down)
- Worker count ≥ 2, but success rate low → Possible worker degradation (see Step 5)
- Worker count ≥ 2, success rate normal → Queue backed up due to high demand

### Step 5: Check Worker Processing Rate

**Prometheus Query:**

```promql
# Enhancement success rate (jobs processed per second)
rate(enhancement_requests_total{status="success"}[5m])

# Enhancement failure rate
rate(enhancement_requests_total{status="failure"}[5m])
```

**What to Look For:**
- Success rate > 2 jobs/sec: Workers healthy, queue backed up due to demand
- Success rate < 1 job/sec: Possible slow jobs or workers struggling
- Failure rate increasing: Workers may be erroring out (investigate logs)

### Step 6: Inspect Sample Jobs in Queue (If Age High)

**Docker:**
```bash
# View first 10 jobs in queue
docker-compose exec redis redis-cli LRANGE enhancement_queue 0 9

# Count jobs by tenant (if supported by queue format)
docker-compose exec redis redis-cli LRANGE enhancement_queue 0 -1 | \
  grep -o '"tenant_id":"[^"]*"' | sort | uniq -c | sort -rn
```

**Kubernetes:**
```bash
# View first 10 jobs
kubectl exec -it redis-0 -- redis-cli LRANGE enhancement_queue 0 9
```

**What to Look For:**
- All jobs from one tenant → Possible rate limiting or tenant-specific issue
- Stuck job repeating → Possible infinite loop in processing (escalate to engineering)
- Jobs with very old created_at → See Step 7

---

## Resolution

### If: Workers Underutilized (Low Success Rate Despite Queue Depth)

**Possible Cause:** Worker capacity not scaled to demand

**Docker - Scale Workers:**
```bash
# Scale to 4 workers
docker-compose up -d --scale worker=4

# Verify new workers started
docker-compose ps worker
```

**Kubernetes - Scale Workers:**
```bash
# Scale to 4 workers (check current replicas first)
kubectl get deployment celery-worker
kubectl scale deployment/celery-worker --replicas=4

# Verify scaling in progress
kubectl get pods -l app=celery-worker -w  # Watch mode, press Ctrl+C to exit
```

**Validation:**
- Wait 30 seconds for new workers to start processing
- Check queue depth metric → Should start decreasing
- Verify no new errors in worker logs

### If: Specific Tenant Flooding Queue

**Possible Cause:** One tenant sending unusually high enhancement volume

**Investigation:**
```bash
# Identify tenant(s) causing queue buildup
# (requires access to job payload structure - may vary by implementation)

# Example: If queue stores JSON with tenant_id field
docker-compose exec redis redis-cli LRANGE enhancement_queue 0 99 | \
  grep -o '"tenant_id":"[^"]*"' | cut -d'"' -f4 | sort | uniq -c | sort -rn
```

**Docker - Rate Limiting (if needed):**
- Contact engineering team to implement per-tenant rate limiting
- Temporary workaround: Pause webhook processing for high-volume tenant

**Kubernetes - Rate Limiting:**
- Update tenant configuration to reduce allowed concurrent jobs
- Update celery task rate limit configuration

### If: Jobs Stuck in Queue (Old Age)

**Possible Cause:** Job processing failure or infinite retry loop

**Inspect Stuck Job:**
```bash
# Get the oldest job details
docker-compose exec redis redis-cli LINDEX enhancement_queue 0

# Example output:
# {"ticket_id":"TICKET-12345", "tenant_id":"acme-corp", "created_at":"2025-11-03T12:00:00Z"}
```

**Check Worker Logs for this Job:**
```bash
# Docker: Search logs for ticket ID from stuck job
docker-compose logs worker --tail=200 | grep "TICKET-12345"

# Kubernetes: Search logs
kubectl logs -l app=celery-worker --tail=200 | grep "TICKET-12345"
```

**What to Look For:**
- Repeated error messages → Job will never succeed (remove from queue)
- No log entries → Job never reached worker (may be stuck in webhook processing)

**Remove Stuck Job (Last Resort):**
```bash
# WARNING: Only remove if job won't process and causing backlog

# Docker: Remove oldest job
docker-compose exec redis redis-cli LPOP enhancement_queue

# Kubernetes: Remove oldest job
kubectl exec -it redis-0 -- redis-cli LPOP enhancement_queue

# Verify removal
docker-compose exec redis redis-cli LLEN enhancement_queue
```

### If: Slow Processing (Normal Demand, But Slow Job Execution)

**Possible Cause:** Database queries slow, external API latency, or LLM processing slow

**Step 1: Review Distributed Traces** (see "Using Distributed Tracing" section below)

**Step 2: Check Database Performance:**
```bash
# Confirm database connectivity
docker-compose exec worker psql -h db -U aiagents -d ai_agents -c "SELECT 1;"

# Expected output: 1 (success)

# Check for long-running queries
docker-compose exec postgres psql -U aiagents -d ai_agents -c \
  "SELECT pid, now() - query_start as duration, query FROM pg_stat_activity
   WHERE state = 'active' ORDER BY duration DESC LIMIT 5;"
```

**Step 3: Check External API Latency:**
```bash
# Test ServiceDesk Plus API response time
time curl -i https://your-sdp-instance/api/v3/tickets \
  -H "Authorization: Bearer $SDP_TOKEN" | head -1

# Look for response time (printed by 'time' command)
# If > 10 seconds, ServiceDesk Plus may be slow
```

**Resolution:**
- Database slow → Contact DBA or platform team for query optimization
- API slow → See [API Timeout Runbook](./api-timeout.md)

---

## Escalation

### Queue Depth Exceeds 100 Jobs

- **Severity:** High
- **Action:** Follow [QueueDepthHigh Alert Runbook](../operations/alert-runbooks.md#queuedepthhigh)
- **Timeline:** Immediate (1 minute)

### Queue Age > 30 Minutes

- **Severity:** High
- **Action:** Page on-call engineer immediately
- **Context:** Oldest job in queue has been waiting 30+ minutes to process
- **Likely Cause:** All workers down or crashed

### Recurring Pattern (Queue Depth > 75 Every Day)

- **Severity:** Medium
- **Action:** Escalate to engineering for capacity planning
- **Context:** System consistently under capacity for current demand
- **Resolution:** Add worker instances or optimize job processing time

### Unknown Root Cause After Investigation

- **Severity:** Medium
- **Action:** Page on-call engineer, provide:
  - Current queue depth and age
  - Worker count and recent logs
  - Distributed trace showing slow jobs (if applicable)
  - Screenshots of Prometheus/Grafana

---

## Using Distributed Tracing for Diagnosis

### When to Use Distributed Tracing

If queue depth is elevated but you can't identify root cause from metrics:

1. Open Jaeger UI: http://localhost:16686 or production equivalent
2. Search for recent traces with `slow_trace=true` tag
3. Identify slowest enhancement jobs (ones taking 30+ seconds)
4. Review trace timeline to find bottleneck

### Jaeger Search Examples

**Find slow traces in the last hour:**
```
slow_trace=true
start_time > now-1h
```

**Find traces for specific tenant (if backed up):**
```
tenant_id=acme-corp
start_time > now-30m
```

**Find traces for specific ticket:**
```
ticket_id=TICKET-12345
```

### Interpreting Trace Timeline

The distributed trace shows enhancement processing stages:

1. **webhook_receipt** - Time to receive webhook from ServiceDesk Plus
2. **context_gathering** - Time to gather ticket history and knowledge base (longest stage)
3. **llm_synthesis** - Time for OpenAI to generate enhancement
4. **ticket_update** - Time to update ticket in ServiceDesk Plus

**If context_gathering is slow:** Database queries slow or many historical records

**If llm_synthesis is slow:** OpenAI API slow or complex prompt taking long

**If ticket_update is slow:** ServiceDesk Plus API slow

**If no ticket_update span:** Worker crashed before completing update

### Next Steps After Identifying Bottleneck

- **Slow context_gathering:** See [Database Connection Issues Runbook](./database-connection-issues.md)
- **Slow llm_synthesis:** See [API Timeout Runbook](./api-timeout.md)
- **Missing ticket_update:** See [Worker Failures Runbook](./worker-failures.md)

---

## Related Documentation

- **[QueueDepthHigh Alert Runbook](../operations/alert-runbooks.md#queuedepthhigh)** - Alert-triggered procedures (queue > 100 jobs)
- **[Worker Failures Runbook](./worker-failures.md)** - Diagnosis if workers degraded
- **[Database Connection Issues Runbook](./database-connection-issues.md)** - If slow queries causing queue backup
- **[API Timeout Runbook](./api-timeout.md)** - If external APIs causing slowdown
- **[Distributed Tracing Setup](../operations/distributed-tracing-setup.md)** - Jaeger UI guide and trace queries
- **[Prometheus Setup](../operations/prometheus-setup.md)** - Metric queries and PromQL reference
- **[Grafana Dashboards](../operations/grafana-setup.md)** - Visual monitoring

---

**Status:** ✅ Complete with integrated distributed tracing guidance
**Test Status:** Awaiting team member validation (Task 10)
**Last Review:** 2025-11-03
