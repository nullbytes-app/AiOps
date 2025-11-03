# Worker Failures

**Last Updated:** 2025-11-03
**Author:** Amelia (Developer Agent)
**Related Alerts:** WorkerDown (no active workers)
**Severity:** High (all workers down) / Medium (partial degradation, restarts)

## Quick Links

- [Symptoms](#symptoms)
- [Diagnosis](#diagnosis)
- [Resolution](#resolution)
- [Escalation](#escalation)
- [Using Distributed Tracing](#using-distributed-tracing-for-diagnosis)

---

## Overview

**When to Use This Runbook:**
- Worker pods showing CrashLoopBackOff or frequent restarts
- One or more workers crashing repeatedly
- Worker process errors in logs (Python exceptions, OOMKilled, segfaults)
- Enhancement processing stopped or degraded after worker changes
- Post-mortem analysis of worker crash incident

**Scope:** Investigation and remediation of worker process failures (not queue issues)

**Prerequisites:**
- Docker and docker-compose (local) or kubectl (Kubernetes)
- Access to worker logs and pod details
- Optional: Python memory profiler if investigating OOM issues

---

## Symptoms

### Observable Indicators

- ✓ Worker container/pod status is CrashLoopBackOff or Unhealthy
- ✓ Worker restart count increasing (kubectl describe pod shows high restart count)
- ✓ Worker logs showing Python exceptions or error stack traces
- ✓ Worker logs showing "Killed" or "OOMKilled" messages
- ✓ Enhancement success rate declining, workers processing zero jobs
- ✓ Worker active count = 0 (no workers accepting jobs)

### When This Runbook Does NOT Apply

- Workers running but queue high → Use [High Queue Depth Runbook](./high-queue-depth.md)
- Enhancement failures with database errors → Use [Database Connection Issues Runbook](./database-connection-issues.md)
- Individual jobs failing but workers healthy → Job-level issue, check logs for error context

---

## Diagnosis

### Step 1: Check Worker Pod/Container Status

**Docker:**
```bash
# Check worker container status
docker-compose ps worker

# Expected Output:
# NAME      COMMAND       SERVICE STATUS     PORTS
# ai-agents-worker-1  python... worker Up (healthy)
```

**Kubernetes:**
```bash
# Check worker pod status
kubectl get pods -l app=celery-worker

# Expected Output showing pod name, ready status, restarts, age
# NAME                    READY   STATUS    RESTARTS   AGE
# celery-worker-0         1/1     Running   0          5d
# celery-worker-1         0/1     CrashLoopBackOff 127  2h
```

**What to Look For:**
- Status = "Running" (healthy)
- Status = "CrashLoopBackOff" (bad - investigate immediately)
- RESTARTS column: If > 5 in last hour, repeated crashes occurring

### Step 2: Review Worker Restart History

**Kubernetes:**
```bash
# Get detailed pod info including restart reason
kubectl describe pod -l app=celery-worker

# Look for "Last State" and "Reason" sections
# Example:
# Last State:     Terminated
#   Reason:       OOMKilled
#   Exit Code:    137
#   Started:      Mon, 03 Nov 2025 10:00:00 +0000
#   Finished:     Mon, 03 Nov 2025 10:05:00 +0000
```

**Docker:**
```bash
# View worker logs (shows all output + errors)
docker-compose logs worker --tail=100

# View logs from previous container restart (if available)
docker-compose logs --previous worker  # May not be available in Docker
```

### Step 3: Analyze Worker Crash Logs

**Docker:**
```bash
# Get worker logs filtered for errors
docker-compose logs worker --tail=500 | grep -i "error\|exception\|killed\|fatal"

# Example output:
# MemoryError: Unable to allocate 2.4 GiB for an array...
# worker exited with code 137
```

**Kubernetes:**
```bash
# Get logs from crashing pod
kubectl logs -l app=celery-worker --tail=200

# If pod crashed, try previous log
kubectl logs -l app=celery-worker --previous --tail=200

# Find error pattern across all worker pods
kubectl logs -l app=celery-worker --all-containers=true | grep -i error
```

**What to Look For:**
- **MemoryError / OOMKilled:** Memory leak or insufficient allocation
- **Segmentation Fault:** Native library issue (PostgreSQL driver, OpenTelemetry)
- **Python Exception:** Code bug, review stack trace
- **Connection errors:** Database or Redis unreachable
- **Signal 15 (SIGTERM):** Normal shutdown (check if intentional)

### Step 4: Check Resource Usage Trends

**Kubernetes:**
```bash
# Check resource requests and limits
kubectl describe deployment/celery-worker | grep -A 10 "Limits\|Requests"

# Example output:
# Limits:
#   memory:  2Gi
#   cpu:     1000m
# Requests:
#   memory:  512Mi
#   cpu:     250m
```

**Prometheus Query (View in Grafana):**

```promql
# Memory usage of worker pods (last 1 hour)
container_memory_usage_bytes{pod=~"celery-worker.*"}

# CPU usage
rate(container_cpu_usage_seconds_total{pod=~"celery-worker.*"}[5m])
```

**What to Look For:**
- Memory steadily increasing toward limit → Memory leak
- Memory spike then OOMKilled → Out of memory event
- CPU stuck at 100% → Infinite loop or expensive operation

### Step 5: Check Health Check Configuration

**Kubernetes:**
```bash
# View health check settings
kubectl get deployment celery-worker -o yaml | grep -A 10 "livenessProbe\|readinessProbe"

# Example:
# livenessProbe:
#   httpGet:
#     path: /health
#     port: 8000
#   initialDelaySeconds: 30
#   periodSeconds: 10
```

**What to Look For:**
- initialDelaySeconds: If workers need more time to start, increase value
- periodSeconds: If health checks happening too frequently, may cause false negatives

---

## Resolution

### If: OOMKilled (Memory Exhaustion)

**Cause:** Worker memory limit exceeded or memory leak

**Option 1 - Increase Memory Limit (Short Term):**

**Kubernetes:**
```bash
# Edit deployment
kubectl set resources deployment/celery-worker --limits=memory=4Gi,cpu=2000m

# Verify change
kubectl rollout status deployment/celery-worker
kubectl get deployment celery-worker -o yaml | grep -A 5 "limits:"
```

**Docker:**
```bash
# Stop current workers
docker-compose down

# Edit docker-compose.yml to increase memory limit
# services:
#   worker:
#     mem_limit: 2g  # Increase from current
#     memswap_limit: 2g

# Restart
docker-compose up -d worker
```

**Option 2 - Identify Memory Leak (Long Term):**

Enable Python memory profiler:
```bash
# Install memory_profiler in worker container
docker-compose exec worker pip install memory-profiler

# Run memory profiler on next crash
# (Requires code instrumentation or profiling container)
```

**Next Steps:**
- After scaling up, monitor memory trend (should stabilize)
- If memory continues growing, escalate to engineering for memory leak fix

### If: Python Exception in Logs

**Cause:** Code bug or unhandled error condition

**Step 1: Extract Full Stack Trace**
```bash
# Get full error context
docker-compose logs worker --tail=1000 | grep -A 20 "Traceback"

# Example output:
# Traceback (most recent call last):
#   File "/app/src/worker/tasks.py", line 42, in enhance_ticket
#     result = llm_client.call(context)
#   File "/app/src/llm/client.py", line 100, in call
#     response = self.client.chat.completions.create(...)
# ValueError: Invalid API key format
```

**Step 2: Identify Issue Category**
- **API Key Issue:** Update credentials in Kubernetes secret or .env
- **Import Error:** Check if dependencies installed correctly
- **Logic Error:** Requires code fix, escalate to engineering

**Step 3: Deploy Fix or Workaround**

If configuration issue:
```bash
# Update secret
kubectl create secret generic worker-config --from-literal=api_key=new_key --dry-run=client -o yaml | kubectl apply -f -

# Restart workers to pick up new config
kubectl rollout restart deployment/celery-worker
```

If code issue:
- Wait for engineering team to fix and deploy new image
- Rollback to previous image if recent deployment caused issue:
  ```bash
  kubectl rollout undo deployment/celery-worker
  ```

### If: Worker Won't Start (CrashLoopBackOff Immediately)

**Cause:** Configuration missing, dependency issue, or port conflict

**Step 1: Check Startup Logs**
```bash
# Get logs from first startup attempt
docker-compose logs worker --tail=50 | head -30

# Or Kubernetes:
kubectl logs -l app=celery-worker --previous --tail=50
```

**Step 2: Verify Configuration**
```bash
# Check environment variables are set
docker-compose config worker | grep "environment:"

# Kubernetes:
kubectl get deployment celery-worker -o yaml | grep -A 20 "env:"
```

**Step 3: Test Connectivity**
```bash
# Verify Redis is reachable
docker-compose exec worker redis-cli -h redis ping

# Verify PostgreSQL is reachable
docker-compose exec worker psql -h postgres -U aiagents -d ai_agents -c "SELECT 1;"
```

**Step 4: Restart Services**
```bash
# Restart dependencies first
docker-compose restart redis postgres

# Then restart workers
docker-compose restart worker

# Wait 30 seconds
sleep 30

# Check status
docker-compose ps worker
```

### If: Segmentation Fault (Rare)

**Cause:** Native library issue (PostgreSQL driver, OpenTelemetry native extensions)

**Diagnosis:**
```bash
# Check for segfault pattern
docker-compose logs worker | grep -i "segmentation\|segfault\|sig 11"

# Get detailed error
docker-compose logs worker --tail=100 | grep -B 5 -A 5 "Segmentation"
```

**Resolution:**
- Escalate to engineering with:
  - Exact segfault message and logs
  - Python version, dependencies, OS
  - Kubernetes/Docker version
- Workaround: Update native dependencies to latest patch version
  ```bash
  pip install --upgrade psycopg2-binary opentelemetry-sdk
  ```

### If: Repeated Crashes with Pattern

**Cause:** Specific job/tenant causing all workers to crash

**Diagnosis:**
```bash
# Check if crashes happen at specific times
docker-compose logs worker --tail=500 | grep -E "Traceback|start" | tail -20

# Check if specific tenant_id appears before crashes
docker-compose logs worker | grep tenant_id | tail -20
```

**Resolution - Quarantine Bad Job:**

```bash
# If specific job in queue causing crash:
# 1. Pause webhook receiver (if possible)
# 2. Remove crashing job from queue
docker-compose exec redis redis-cli LPOP enhancement_queue

# 3. Restart workers
docker-compose restart worker

# 4. If crashes stop, investigate job in detail
# 5. Re-enable webhook after fix
```

### Performing Rolling Restart (Zero-Downtime)

**Kubernetes:**
```bash
# Graceful rolling restart with timeout
kubectl rollout restart deployment/celery-worker --timeout=5m

# Monitor restart progress
kubectl get pods -l app=celery-worker -w  # Press Ctrl+C to exit
```

**Docker:**
```bash
# Graceful restart (waits for jobs to complete)
docker-compose stop worker
sleep 5
docker-compose up -d worker

# Or with health check:
docker-compose restart worker
sleep 10
docker-compose ps worker  # Verify healthy
```

---

## Escalation

### All Workers Down (count = 0)

- **Severity:** Critical
- **Action:** Immediate
- **Timeline:** Page on-call engineer NOW
- **Context:** No jobs being processed, platform unavailable
- **Steps Before Escalating:** Verify with `worker_active_count` metric and kubectl/docker-compose status

### Repeated Crashes (3+ in 1 Hour)

- **Severity:** High
- **Action:** Immediate
- **Timeline:** Page on-call engineer
- **Context:** Workers crashing repeatedly, likely permanent issue
- **Provide:** Last 5 crash logs, restart timestamps, any recent deployments

### Unknown Root Cause After 30 Minutes Investigation

- **Severity:** High
- **Action:** Escalate to engineering team
- **Provide:**
  - Worker logs (last 100 lines showing error)
  - Pod/container status and restart count
  - Kubernetes node status (if applicable)
  - Prometheus metrics showing resource usage
  - Recent deployments or configuration changes

---

## Using Distributed Tracing for Diagnosis

### When to Use Distributed Tracing

If worker is crashing sporadically (not continuously):

1. Open Jaeger UI: http://localhost:16686
2. Search for traces from crashing time window
3. Look for traces that end abruptly (missing final spans)

### Jaeger Search Examples

**Find traces in time window when worker crashed:**
```
start_time > 2025-11-03T10:00:00Z
duration > 30s  # Jobs taking long before crash
```

**Find incomplete traces (missing final span):**
```
# Search for traces without "ticket_update" span
# (Jaeger UI doesn't support negative filtering, so inspect manually)
```

### Interpreting Trace Patterns

- **Traces stopping at context_gathering span:** Database operation causing crash
- **Traces stopping at llm_synthesis span:** LLM API call causing crash
- **Multiple traces crashing at same span:** Consistent reproducible issue

**Next Steps:**
- If database related: See [Database Connection Issues Runbook](./database-connection-issues.md)
- If API related: See [API Timeout Runbook](./api-timeout.md)
- If pattern unclear: Escalate with trace details to engineering

---

## Related Documentation

- **[WorkerDown Alert Runbook](../operations/alert-runbooks.md#workerdown)** - Alert-triggered procedures (no workers running)
- **[High Queue Depth Runbook](./high-queue-depth.md)** - If queue backing up after worker restart
- **[Database Connection Issues Runbook](./database-connection-issues.md)** - If crashes related to database
- **[API Timeout Runbook](./api-timeout.md)** - If crashes related to external APIs
- **[Distributed Tracing Setup](../operations/distributed-tracing-setup.md)** - Jaeger UI guide and trace analysis
- **[Docker Compose Reference](../../docker-compose.yml)** - Worker service definition

---

**Status:** ✅ Complete with memory profiling and distributed tracing guidance
**Test Status:** Awaiting team member validation (Task 10)
**Last Review:** 2025-11-03
