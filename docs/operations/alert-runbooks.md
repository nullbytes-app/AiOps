# Alert Runbooks - AI Agents Platform

**Story Reference:** Story 4.4 - Configure Alerting Rules in Prometheus
**Last Updated:** 2025-11-03
**Author:** Development Agent (Amelia)

---

## Overview

This document provides troubleshooting runbooks for Prometheus alerts configured in Story 4.4. Each alert has a dedicated section with symptom description, common root causes, step-by-step troubleshooting commands, resolution guidance, and escalation procedures.

**Alert Rules Implemented:**
1. **EnhancementSuccessRateLow** - Success rate <95% for 10 minutes (warning)
2. **QueueDepthHigh** - Queue depth >100 jobs for 5 minutes (warning)
3. **WorkerDown** - No active Celery workers for 2 minutes (critical)
4. **HighLatency** - p95 latency >120 seconds for 5 minutes (warning)

---

## EnhancementSuccessRateLow

**Severity:** Warning
**Affected Component:** Enhancement Pipeline
**SLA Impact:** Exceeds NFR003 (99% success rate target)

### Symptom

Enhancement success rate metric (`enhancement_success_rate`) drops below 95% and persists for 10+ minutes. This indicates that less than 95% of enhancement requests are completing successfully.

### Common Root Causes

1. **External API Failures**
   - ServiceDesk Plus API unreachable or returning errors
   - OpenAI API returning rate limit (HTTP 429) or service error (HTTP 5xx)
   - Invalid credentials or expired API tokens

2. **Worker Process Failures**
   - Celery worker crashes or OOM kills
   - Python exception during enhancement processing
   - Missing dependencies or import errors

3. **Database Connectivity Issues**
   - PostgreSQL connection timeout or failure
   - Row-level security (RLS) blocking updates
   - Transaction lock causing deadlock

4. **Invalid Tenant Configuration**
   - Missing or incorrect ServiceDesk Plus API credentials in ConfigMap
   - Disabled tenant in tenant configuration management

5. **Rate Limiting or Quota Issues**
   - OpenAI API rate limit exceeded
   - ServiceDesk Plus API request throttling

### Troubleshooting Steps

1. **Check Recent Failure Rate**
   ```bash
   # Query Prometheus for recent enhancement request failures
   # Navigate to Prometheus UI: http://localhost:9090
   # Graph tab → Query: rate(enhancement_requests_total{status="failure"}[5m])

   # Or using curl (if Prometheus API available):
   curl 'http://localhost:9090/api/v1/query?query=rate(enhancement_requests_total{status="failure"}[5m])'
   ```

2. **Review Worker Logs**
   ```bash
   # Local Docker environment
   docker-compose logs -f worker | tail -100

   # Kubernetes environment
   kubectl logs -l app=celery-worker --tail=100 -f

   # Look for Python exceptions, traceback, or "ERROR" level messages
   ```

3. **Check External API Connectivity**
   ```bash
   # Verify ServiceDesk Plus API health
   curl -i https://your-servicedesk-plus-instance/api/v3/tickets \
     -H "Authorization: Bearer YOUR_API_TOKEN"

   # Expected response: 200 OK or 401 if auth issues
   # 500+ status codes indicate ServiceDesk Plus service failure

   # Check OpenAI API status
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY" \
     -H "User-Agent: curl" | head -20
   ```

4. **Verify Tenant Credentials**
   ```bash
   # Local Docker
   docker-compose exec api cat /run/secrets/tenant_config.json | jq '.clients[0]'

   # Kubernetes
   kubectl get secret tenant-config -o jsonpath='{.data.config\.json}' | base64 -d | jq '.clients[0]'

   # Verify fields: service_desk_plus_url, api_key, api_secret are present and not empty
   ```

5. **Check Database Connectivity**
   ```bash
   # Local Docker
   docker-compose exec db psql -U aiagents -d ai_agents \
     -c "SELECT COUNT(*) FROM enhancement_requests WHERE created_at > NOW() - INTERVAL '1 hour';"

   # Kubernetes
   kubectl exec -it deployment/postgres -- psql -U aiagents -d ai_agents \
     -c "SELECT COUNT(*) FROM enhancement_requests WHERE status='failed' AND created_at > NOW() - INTERVAL '10 minutes';"
   ```

6. **Check Worker Health**
   ```bash
   # Local Docker - verify workers are running
   docker-compose ps | grep worker

   # Check for crashes
   docker-compose logs worker | grep -i "exit\|crash\|oom"

   # Kubernetes
   kubectl get pods -l app=celery-worker
   kubectl describe pod -l app=celery-worker | grep -A 5 "Last State"
   ```

### Resolution

**Quick Fixes (try in order):**

1. **Verify API credentials are correct**
   - Check ServiceDesk Plus credentials in tenant configuration
   - Re-authenticate if tokens have expired
   - Test API connection manually (steps 3 above)

2. **Restart workers to clear potential stuck processes**
   ```bash
   # Local Docker
   docker-compose restart worker

   # Kubernetes
   kubectl rollout restart deployment/celery-worker
   ```

3. **Check for rate limiting**
   - Review OpenAI API usage dashboard for rate limit status
   - Check ServiceDesk Plus API request logs for throttling
   - Implement exponential backoff or rate limiting on client side

4. **Scale workers if overloaded**
   ```bash
   # Local Docker
   docker-compose up -d --scale worker=3

   # Kubernetes
   kubectl scale deployment celery-worker --replicas=3
   ```

5. **Monitor success rate recovery**
   ```bash
   # Wait 10 minutes and check if alert resolves
   # Prometheus UI → Graph → enhancement_success_rate
   # Should see metric climbing back above 95%
   ```

### Escalation

- **1 hour without resolution:** Escalate to on-call engineer
- **3+ hours with success rate <90%:** Page engineering team (production incident)
- **24+ hours:** Review system architecture for capacity constraints

**On-Call Actions:**
- Check infrastructure health (CPU, memory, disk)
- Review recent deployments that may have introduced bugs
- Check for upstream API provider incidents (OpenAI status page, etc.)

---

## QueueDepthHigh

**Severity:** Warning
**Affected Component:** Redis Queue
**SLA Impact:** May cause user-facing delays if not addressed

### Symptom

Redis queue depth metric (`queue_depth`) exceeds 100 pending jobs and persists for 5+ minutes. This indicates that enhancement jobs are being queued faster than workers can process them.

### Common Root Causes

1. **Insufficient Worker Capacity**
   - Workers running slower than ingestion rate
   - Workers crashed or restarting repeatedly
   - Worker process stuck or deadlocked

2. **Webhook Flood or Spike**
   - Unexpected surge in webhook requests
   - Misconfigured external system sending duplicate webhooks
   - Bot or automated script sending excessive requests

3. **Slow Enhancement Processing**
   - Complex tickets requiring long LLM processing
   - External API calls timing out
   - Database queries performing slowly

4. **Redis Issues**
   - Redis connection pool exhausted
   - Redis memory pressure or eviction
   - Network latency to Redis instance

5. **Configuration Issues**
   - Celery worker concurrency set too low
   - Prefetch multiplier limiting parallel task execution
   - Task timeout causing retries

### Troubleshooting Steps

1. **Check Current Queue Depth**
   ```bash
   # Prometheus Graph
   # Query: queue_depth
   # Should see the current and historical values

   # Or directly query Redis
   docker-compose exec redis redis-cli LLEN enhancement_queue
   # Kubernetes
   kubectl exec -it deployment/redis -- redis-cli LLEN enhancement_queue
   ```

2. **Verify Worker Count and Health**
   ```bash
   # Check worker_active_count metric
   # Prometheus Graph → worker_active_count

   # Direct check - Local Docker
   docker-compose exec worker celery -A tasks inspect active

   # Kubernetes
   kubectl exec -it deployment/celery-worker -- celery -A tasks inspect active
   ```

3. **Monitor Queue Drain Rate**
   ```bash
   # Prometheus Graph
   # Query: rate(queue_depth[5m])
   # If negative, queue is draining; if flat or positive, queue growing

   # Watch queue in real-time
   while true; do
     depth=$(docker-compose exec redis redis-cli LLEN enhancement_queue)
     echo "Queue depth: $depth at $(date)"
     sleep 10
   done
   ```

4. **Check for Webhook Flood**
   ```bash
   # Review FastAPI logs for webhook request rate
   docker-compose logs api | grep "POST /webhook" | wc -l

   # Kubernetes
   kubectl logs -l app=api | grep "POST /webhook" | wc -l

   # Check request rate in last 5 minutes
   # If >50 requests/min unusual, investigate source
   ```

5. **Verify Worker Performance**
   ```bash
   # Check average processing time
   docker-compose logs worker | grep "enhancement completed in"

   # Kubernetes
   kubectl logs -l app=celery-worker | grep "enhancement completed in"

   # If individual tasks taking 30+s, likely slow API calls or large tickets
   ```

### Resolution

**Immediate Actions:**

1. **Scale workers horizontally**
   ```bash
   # Local Docker - increase worker replicas
   docker-compose up -d --scale worker=3

   # Kubernetes - scale deployment
   kubectl scale deployment celery-worker --replicas=3

   # Monitor queue draining
   # Queue depth should start decreasing within 1-2 minutes
   ```

2. **Monitor queue drain progress**
   ```bash
   # Set up monitoring of queue depth over time
   watch -n 5 "docker-compose exec redis redis-cli LLEN enhancement_queue"

   # Kubernetes
   watch -n 5 "kubectl exec -it deployment/redis -- redis-cli LLEN enhancement_queue"

   # Queue should reach <100 within 5-10 minutes if workers scaled properly
   ```

3. **If queue doesn't drain after scaling:**
   - Check if scaled workers are actually processing (logs show activity)
   - Verify Redis connection is healthy
   - Check for worker crashes or exceptions

4. **Investigate root cause once queue is drained**
   - Was it a webhook flood? Implement rate limiting
   - Were workers crashing? Fix the crash condition
   - Is processing inherently slow? Optimize enhancement logic or add caching

### Escalation

- **Queue depth exceeds 500 jobs:** Page on-call immediately (production incident)
- **Queue depth remains high after scaling to 5+ workers:** Infrastructure bottleneck, escalate to DevOps
- **Repeated incidents:** Review SLA targets and capacity planning

**On-Call Actions:**
- Scale workers aggressively (e.g., to 5-10 replicas)
- Check for webhook flood source and potentially throttle/block
- Review Redis metrics for memory pressure or connection pool exhaustion
- Consider temporarily stopping non-critical feature processing

---

## WorkerDown

**Severity:** Critical
**Affected Component:** Celery Workers
**SLA Impact:** Enhancement processing is halted - immediate impact on users

### Symptom

Worker active count metric (`worker_active_count`) drops to 0 and persists for 2+ minutes. This means all Celery worker processes are down and no enhancement jobs are being processed.

### Common Root Causes

1. **Worker Process Crash**
   - Unhandled Python exception in worker code
   - Segmentation fault from native library
   - Memory exhaustion (OOM kill)

2. **Resource Exhaustion**
   - Container/Pod memory limit exceeded (OOM kill)
   - Disk space exhausted (logging or temporary files)
   - CPU throttling causing process hang

3. **Redis Connection Failure**
   - Redis service down or unreachable
   - Network partition between worker and Redis
   - Redis authentication failure

4. **Configuration Error**
   - Invalid Celery configuration in environment variables
   - Incorrect broker URL or credentials
   - Missing required dependencies

5. **Kubernetes Pod Issues** (if K8s environment)
   - Pod evicted due to resource pressure on node
   - Pod restart loop (CrashLoopBackOff)
   - Node failure or node drain

### Troubleshooting Steps

1. **Verify Worker Status**
   ```bash
   # Local Docker
   docker-compose ps | grep worker
   # Look for "Up" or "Exited" status

   # Kubernetes
   kubectl get pods -l app=celery-worker
   # Look for Running, Pending, CrashLoopBackOff, Evicted status
   ```

2. **Check Worker Logs for Crash**
   ```bash
   # Local Docker - view last 200 lines
   docker-compose logs worker --tail=200

   # Kubernetes
   kubectl logs -l app=celery-worker --tail=200

   # Look for:
   # - Python exceptions/tracebacks
   # - "Killed" or "OOMKilled" messages
   # - Connection refused errors to Redis
   ```

3. **Verify Redis Connectivity**
   ```bash
   # From worker container - test Redis connection
   docker-compose exec worker redis-cli -h redis ping
   # Expected response: PONG

   # Kubernetes
   kubectl exec -it deployment/celery-worker -- redis-cli -h redis ping

   # If connection fails, Redis is down or unreachable
   ```

4. **Check Container/Pod Resource Usage**
   ```bash
   # Docker - check memory and CPU
   docker stats --no-stream | grep worker

   # Kubernetes - check resource requests vs actual usage
   kubectl describe pod -l app=celery-worker | grep -A 5 "Limits\|Requests"
   kubectl top pods -l app=celery-worker
   ```

5. **Check Node Health** (Kubernetes only)
   ```bash
   # If workers are on a specific node, check node status
   kubectl describe node <node-name>

   # Look for conditions: NotReady, MemoryPressure, DiskPressure
   # Check for eviction messages in events
   ```

### Resolution

**Immediate Actions (Critical Priority):**

1. **Restart Workers**
   ```bash
   # Local Docker
   docker-compose restart worker

   # Kubernetes
   kubectl rollout restart deployment/celery-worker

   # Wait for workers to come online (verify worker_active_count > 0)
   watch -n 2 "docker-compose logs worker | tail -5"
   ```

2. **If Restart Fails - Check Logs Immediately**
   ```bash
   # Docker - stream logs while restarting
   docker-compose logs -f worker

   # Kubernetes - watch logs during restart
   kubectl logs -f -l app=celery-worker

   # Identify the root cause (exception, connectivity, resource issue)
   ```

3. **If Redis is Down**
   ```bash
   # Local Docker
   docker-compose restart redis

   # Kubernetes
   kubectl rollout restart deployment/redis

   # Then restart workers
   ```

4. **If Memory Issue (OOMKilled)**
   ```bash
   # Increase worker memory limits
   # Kubernetes - edit deployment
   kubectl edit deployment celery-worker
   # Increase resources.limits.memory to 1Gi or 2Gi

   # Local Docker - adjust docker-compose.yml or container memory limits
   ```

5. **If Configuration Error**
   ```bash
   # Verify Celery environment variables
   docker-compose config | grep -A 10 "worker:"

   # Kubernetes
   kubectl describe deployment celery-worker | grep -A 20 "Environment"

   # Check for:
   # - CELERY_BROKER_URL (should be redis://)
   # - CELERY_RESULT_BACKEND (should be redis://)
   # - Correct hostnames and credentials
   ```

### Post-Resolution

1. **Verify Workers are Processing Tasks**
   ```bash
   # Should see active tasks
   docker-compose exec worker celery -A tasks inspect active

   # Check worker_active_count metric in Prometheus - should be > 0
   ```

2. **Monitor Recovery**
   ```bash
   # Check if queue is being drained
   docker-compose exec redis redis-cli LLEN enhancement_queue

   # Watch success rate recovering
   # Prometheus Graph → enhancement_success_rate (should climb toward 100%)
   ```

3. **Investigate Root Cause**
   - Review what caused the crash
   - Apply fixes (upgrade library, increase memory, fix config)
   - Deploy updated version if needed

### Escalation

- **Immediate:** Page on-call engineer (critical incident - no processing)
- **Workers restart successfully:** Monitor for recurrence (if crash repeats, escalate to engineering)
- **Workers fail to start:** Critical infrastructure incident - escalate to DevOps/Platform team

**On-Call Actions:**
- Restart workers immediately
- Verify Redis is healthy
- Check infrastructure capacity
- If recurrence, prepare rollback of recent deployments
- Consider manual processing if customer SLA at risk

---

## HighLatency

**Severity:** Warning
**Affected Component:** Enhancement Pipeline
**SLA Impact:** Exceeds 120-second SLA threshold for processing time

### Symptom

p95 (95th percentile) enhancement processing latency metric exceeds 120 seconds and persists for 5+ minutes. This means 5% of enhancement requests are taking longer than 120 seconds to complete.

### Common Root Causes

1. **Slow External API Calls**
   - ServiceDesk Plus API responding slowly (>30s per request)
   - OpenAI API generating responses slowly or queued (>60s)
   - Network latency to external services
   - External service under load

2. **LLM Processing Delays**
   - Token limit reached requiring multiple requests
   - Model responding slowly due to complexity
   - Temperature/parameters causing longer generation
   - OpenAI rate limit causing queuing

3. **Database Performance Issues**
   - Slow ticket history search on large PostgreSQL tables
   - Missing indexes on frequently queried columns
   - Inefficient SQL query fetching context
   - Row-level security (RLS) check slowness

4. **Large Ticket Context**
   - Very long ticket descriptions (100k+ characters)
   - Large attachment processing
   - Extensive ticket history (1000+ historical updates)
   - Complex related tickets graph

5. **Infrastructure Resource Constraints**
   - CPU throttling on worker containers
   - Memory swap causing slowdown
   - Network bandwidth saturation
   - Shared resource contention

### Troubleshooting Steps

1. **Confirm High Latency**
   ```bash
   # Prometheus Graph
   # Query: histogram_quantile(0.95, rate(enhancement_duration_seconds_bucket[5m]))
   # Should show current p95 latency in seconds

   # Also check other percentiles
   # Query: histogram_quantile(0.50, ...) for p50 (median)
   # Query: histogram_quantile(0.99, ...) for p99 (tail)
   ```

2. **Check Grafana Dashboard p95 Latency Panel**
   ```bash
   # Local: http://localhost:3000
   # Kubernetes: kubectl port-forward svc/grafana 3000:3000
   # then http://localhost:3000

   # Navigate to AI Agents Dashboard → find "p95 Latency" panel
   # Look for trend - is it sustained high latency or spike?
   ```

3. **Analyze Recent Enhancements**
   ```bash
   # Find slow enhancement requests
   # Kubernetes
   kubectl logs -l app=celery-worker | grep "enhancement completed in" | sort -t' ' -k4 -rn | head -10

   # Look for entries with >120s duration
   # Example: "enhancement completed in 156.42 seconds for ticket TICKET-001"
   ```

4. **Check ServiceDesk Plus API Latency**
   ```bash
   # Test API response time
   time curl -s https://your-sdp/api/v3/tickets/search \
     -H "Authorization: Bearer $TOKEN" \
     -d "query=..." | wc -l

   # If response time > 10s consistently, issue is external
   ```

5. **Check OpenAI API Latency**
   ```bash
   # Monitor worker logs for OpenAI call times
   docker-compose logs worker | grep -i "openai\|gpt\|completion" | head -20

   # Kubernetes
   kubectl logs -l app=celery-worker | grep -i "openai" | head -20

   # Check if individual LLM requests taking >60s
   ```

6. **Analyze Slow Tickets**
   ```bash
   # Look at database query performance
   docker-compose exec db psql -U aiagents -d ai_agents \
     -c "\timing on" \
     -c "SELECT count(*) FROM tickets WHERE created_at > NOW() - INTERVAL '1 hour' AND description LIKE '%large%';"

   # Check for slow table scans
   -c "EXPLAIN ANALYZE SELECT * FROM ticket_history WHERE ticket_id = 'SLOW-TICKET' LIMIT 100;"
   ```

7. **Check Worker Resource Constraints**
   ```bash
   # CPU and memory usage
   docker stats worker | head -5

   # Kubernetes
   kubectl top pods -l app=celery-worker

   # If CPU near limit (e.g., 450m of 500m limit), worker is CPU-constrained
   ```

### Resolution

**Quick Wins (try in order):**

1. **Check External API Status Pages**
   - OpenAI status page: https://status.openai.com
   - ServiceDesk Plus service health
   - Network connectivity to external services

2. **Scale Worker Resources**
   ```bash
   # Increase CPU allocation
   # Kubernetes - edit deployment
   kubectl edit deployment celery-worker
   # Increase resources.limits.cpu to 1000m (1 CPU core)

   # Increase memory
   # Increase resources.limits.memory to 2Gi

   # Apply changes
   kubectl apply -f k8s/celery-worker-deployment.yaml
   ```

3. **Optimize Enhancement Processing**
   ```bash
   # Check for obvious inefficiencies in logs
   docker-compose logs worker | grep -E "query|search|context gathering" | head -20

   # If ticket context gathering is slow:
   # - Implement pagination for ticket history (only fetch last 50 updates instead of all)
   # - Add database indexes on frequently queried columns (ticket_id, created_at)
   # - Consider caching context for duplicate tickets
   ```

4. **Implement Request Timeout**
   ```bash
   # If external API calls are slow, add timeout
   # Example (in worker code):
   # requests.get(url, timeout=30)  # 30 second timeout instead of infinite

   # Prevents hanging requests from blocking worker
   ```

5. **Reduce Ticket Context Size**
   ```bash
   # Limit historical context fetched
   # Instead of fetching entire ticket history, fetch only last N updates
   # Example: SELECT * FROM ticket_history WHERE ticket_id=X ORDER BY created_at DESC LIMIT 50

   # Only include recent context in LLM prompt
   ```

### Monitoring Recovery

```bash
# Monitor latency after optimization
watch -n 10 "curl -s http://localhost:9090/api/v1/query?query=histogram_quantile\\(0.95\\,rate\\(enhancement_duration_seconds_bucket\\[5m\\]\\)\\) | jq '.data.result[0].value[1]'"

# Should see p95 latency dropping back below 120s within 5-10 minutes
```

### Escalation

- **p95 > 120s for 30+ minutes:** Page on-call engineer (SLA breach)
- **p95 > 300s:** Critical incident - impacts user experience significantly
- **p99 > 600s:** Investigate for specific failing ticket patterns

**On-Call Actions:**
- Identify the slow tickets (use logs + database query)
- Check if specific ticket types or tenants affected
- Review recent deployment changes that might have regressed performance
- Consider manual processing for customers if SLA critical
- Escalate to engineering for permanent optimization

---

## General Alert Management

### Accessing Prometheus Alerts

**Local Docker:**
```bash
# Access Prometheus UI
open http://localhost:9090
# or
curl http://localhost:9090/alerts
```

**Kubernetes:**
```bash
# Port-forward to Prometheus service
kubectl port-forward svc/prometheus 9090:9090

# Then access
open http://localhost:9090/alerts
```

### Understanding Alert States

| State | Color | Meaning |
|-------|-------|---------|
| **Inactive** | Green | Alert rule exists but condition not met (normal state) |
| **Pending** | Yellow | Condition met but waiting for `for:` duration to elapse |
| **Firing** | Red | Condition met for full `for:` duration - alert is active |
| **Resolved** | Green (with history) | Condition resolved after `keep_firing_for` duration |

### Reading Alert Details

When an alert is firing, click expand to see:

- **Expression:** The PromQL query being evaluated (e.g., `enhancement_success_rate < 95`)
- **Labels:** Categorization (severity, component, tenant_id)
- **Annotations:** Human-readable context (summary, description, runbook URL)
- **Active Since:** When the alert transitioned to Firing state
- **Value:** Current metric value (e.g., 92.5% if success rate dropped)

### Alert State Transitions

```
Normal Condition → Inactive (green)
                   ↓
Condition Met → Pending (yellow) → [wait for 'for:' duration]
                                    ↓
                              Firing (red) ← Sustained condition
                                    ↓
Condition Resolves → [keeps firing for 'keep_firing_for:' duration]
                     ↓
                  Resolved (green)
```

### Testing Alerts

For testing and debugging alert rules:

```bash
# Access Prometheus Graph tab
# Test PromQL expressions before they trigger alerts
# Examples:
#   - enhancement_success_rate   (current value, should be around 98-100%)
#   - queue_depth                (should be near 0 during normal operation)
#   - worker_active_count        (should be > 0 if workers running)
#   - histogram_quantile(0.95, rate(enhancement_duration_seconds_bucket[5m]))  (p95 latency)
```

### Future: Alert Silencing (Story 4.5)

**Current State:** No native silencing UI in Prometheus. Temporary workaround via config edit.

**Temporary Silencing Procedure:**

```bash
# 1. Edit alert-rules.yml and comment out the alert(s)
# 2. Reload Prometheus config

# Local Docker
docker-compose restart prometheus

# Kubernetes
kubectl rollout restart deployment/prometheus

# 3. Alert disappears from UI until config reload completes
# 4. Re-enable alert by uncommenting and reloading
```

⚠️ **Warning:** Never silence critical alerts indefinitely. Silencing is only for:
- Planned maintenance windows
- Known issues with documented resolution timeline
- Testing (always re-enable after testing)

**Better Approach (Coming in Story 4.5):**
- Alertmanager will provide native silence UI
- Can create temporary silences with expiration time
- Silences visible in Prometheus → Silences page

---

## Troubleshooting Common Patterns

### Alert Not Firing When Expected

**Symptoms:** Condition met but alert not firing

**Causes & Solutions:**
1. **Metric not available:** Check that metric is exposed at /metrics endpoint
2. **PromQL expression syntax error:** Validate expression in Prometheus Graph tab
3. **`for:` duration not elapsed:** Alert requires condition to persist for full duration (e.g., 10 minutes)
4. **Metric value matches incorrectly:** Check if thresholds are correct (e.g., `< 95` vs `<= 95`)

**Resolution:**
- Query metric directly in Prometheus Graph: `enhancement_success_rate`
- Check expression evaluates correctly: `enhancement_success_rate < 95` should return empty or values
- Verify metrics have expected labels (tenant_id, etc.)

### Alert Always Firing

**Symptoms:** Alert permanently red (firing)

**Causes & Solutions:**
1. **Threshold too aggressive:** Lower threshold may be too close to normal value
2. **Transient spike:** `for:` duration might be too short for the alert type
3. **Metric calculation error:** PromQL expression might have typo or logical error
4. **Insufficient metric data:** Recent metrics insufficient for time-windowed aggregation

**Resolution:**
- Adjust `for:` duration to be more appropriate for the metric
- Review threshold vs historical metric data ranges
- Check PromQL expression for syntax issues
- Provide more historical data if using time-windowed queries

### Prometheus Config Load Error

**Symptoms:** Alert rules not loading, "error" state in UI

**Causes & Solutions:**
1. **YAML syntax error:** Check prometheus.yml and alert-rules.yml for invalid YAML
2. **Alert rule syntax error:** Missing required field (alert name, expr, for)
3. **PromQL expression invalid:** Syntax error in alert condition expression
4. **File not found:** rule_files path incorrect or file missing

**Resolution:**
```bash
# Validate YAML syntax
python3 -c "import yaml; yaml.safe_load(open('prometheus.yml')); print('Valid')"

# Check Prometheus logs for specific error
docker-compose logs prometheus | grep -i error

# Kubernetes
kubectl logs -l app=prometheus | grep -i error

# Verify rule files section in prometheus.yml
grep -A 2 "rule_files:" prometheus.yml
```

---

## References

- **Prometheus Alerting Docs:** https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/
- **PromQL Guide:** https://prometheus.io/docs/prometheus/latest/querying/basics/
- **Story 4.1 - Metrics Instrumentation:** docs/stories/4-1-implement-prometheus-metrics-instrumentation.md
- **Story 4.2 - Prometheus Deployment:** docs/stories/4-2-deploy-prometheus-server-and-configure-scraping.md
- **Story 4.3 - Grafana Dashboards:** docs/stories/4-3-create-grafana-dashboards-for-real-time-monitoring.md
- **Story 4.5 - Alertmanager Integration:** (In Backlog) - Will add Slack/email notifications
