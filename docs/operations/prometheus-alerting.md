# Prometheus Alerting Configuration Guide

**Story Reference:** Story 4.4 - Configure Alerting Rules in Prometheus
**Last Updated:** 2025-11-03
**Author:** Development Agent (Amelia)

---

## Overview

This guide documents the Prometheus alerting system for the AI Agents platform, including architecture, configuration, testing, and operational procedures.

### Alerting Architecture

```
Metrics Collection (Story 4.1)
       ↓
Prometheus Server (Story 4.2)
       ↓
Alert Rule Evaluation (15s interval)
       ↓
Alert State Management
       ├─ Inactive: Condition not met
       ├─ Pending: Condition met, waiting for 'for' duration
       └─ Firing: Condition persisted for full duration
       ↓
Prometheus UI Display (Story 4.4)
       ↓
Alertmanager (Future - Story 4.5)
       └─ Slack/Email/PagerDuty Notifications
```

### Prerequisites

- **Story 4.1 Metrics Instrumentation:** `/metrics` endpoint exposed with core metrics
- **Story 4.2 Prometheus Deployment:** Prometheus server deployed and scraping metrics
- **Story 4.3 Grafana Dashboards:** Establishes threshold baselines for alerts

### Core Metrics Available for Alerting

| Metric | Type | Labels | Example Values |
|--------|------|--------|-----------------|
| `enhancement_success_rate` | Gauge | tenant_id | 98.5 (percentage) |
| `queue_depth` | Gauge | (none) | 42 (number of jobs) |
| `worker_active_count` | Gauge | (none) | 3 (number of workers) |
| `enhancement_duration_seconds` | Histogram | tenant_id, bucket | 0.5s to 300s+ buckets |
| `enhancement_requests_total` | Counter | status, tenant_id | success/failure counts |

---

## Alert Rules Configuration

### Local Docker Setup

**Configuration File:** `alert-rules.yml` (project root)

**Referenced in:** `prometheus.yml` under `rule_files:`

```yaml
global:
  evaluation_interval: 15s  # How often to evaluate alert rules

rule_files:
  - "alert-rules.yml"  # Load alert rules from file
```

**Alert Rules Structure:**

```yaml
groups:
  - name: enhancement_pipeline_alerts
    interval: 15s
    rules:
      - alert: AlertName
        expr: <PromQL_expression>
        for: 10m                    # Wait duration before firing
        keep_firing_for: 5m         # Keep firing after resolution
        labels:
          severity: warning/critical
          component: <component>
          tenant_id: "{{ $labels.tenant_id }}"
        annotations:
          summary: "Brief {{ $value }} alert"
          description: "Detailed context about {{ $labels.tenant_id }}"
          runbook_url: "docs/operations/alert-runbooks.md#anchor"
```

### Kubernetes Production Setup

**Configuration:**
1. **ConfigMap:** `k8s/prometheus-alert-rules.yaml`
   - Contains alert rules as ConfigMap data field
   - Mounted in Prometheus pod at `/etc/prometheus/alert-rules.yml`

2. **Prometheus Config:** `k8s/prometheus-config.yaml`
   - References mounted file: `rule_files: ["/etc/prometheus/alert-rules.yml"]`

3. **Deployment:** `k8s/prometheus-deployment.yaml`
   - Volume mount for ConfigMap: `volumeMounts.name: alert-rules`
   - Volume definition: `volumes.configMap.name: prometheus-alert-rules`

**Deployment Steps:**

```bash
# 1. Create/update ConfigMap
kubectl apply -f k8s/prometheus-alert-rules.yaml

# 2. Update Prometheus config (already included in prometheus-config.yaml)
kubectl apply -f k8s/prometheus-config.yaml

# 3. Restart Prometheus to load rules
kubectl rollout restart deployment/prometheus

# 4. Wait for pod restart
kubectl rollout status deployment/prometheus

# 5. Verify rules loaded (no errors in logs)
kubectl logs -l app=prometheus | grep -i "rule\|alert"
```

### Template Variables in Annotations

Prometheus supports dynamic values in alert annotations using templates:

| Variable | Description | Example |
|----------|-------------|---------|
| `{{ $value }}` | Current metric value | 92.5 (for success rate alert) |
| `{{ $labels.label_name }}` | Extract label value | tenant_id "client1" |
| `{{ $labels.instance }}` | Scrape target instance | api:8000 |
| `{{ $externalLabels.key }}` | Global external label | cluster "ai-agents-prod" |

**Example Annotations:**

```yaml
annotations:
  summary: "Enhancement success rate {{ $value }}% (target: >95%)"
  description: "Alert for tenant {{ $labels.tenant_id }}: current rate {{ $value }}%"
```

When alert fires:
- `{{ $value }}` renders to actual metric value: `Enhancement success rate 92.3% (target: >95%)`
- `{{ $labels.tenant_id }}` renders to: `Alert for tenant client1: current rate 92.3%`

---

## Viewing Alerts

### Accessing Prometheus Alerts UI

**Local Development:**
```bash
# Navigate to Prometheus
open http://localhost:9090/alerts
```

**Kubernetes Production:**
```bash
# Port-forward to Prometheus service
kubectl port-forward svc/prometheus 9090:9090

# In browser
open http://localhost:9090/alerts
```

### Alert States on Alerts Page

The Alerts page shows all alert rules and their current states:

**Inactive (Green):**
- Condition not currently met
- Alert rule exists and is valid
- Normal, expected state

**Pending (Yellow):**
- Condition met but waiting for `for:` duration
- Example: Success rate <95% but only for 2 minutes of 10-minute requirement
- Alert will transition to Firing if condition persists

**Firing (Red):**
- Condition met for full `for:` duration
- Alert is actively alerting
- Requires investigation and remediation

**Error (Gray):**
- Alert rule has syntax error or missing metric
- Requires immediate attention to fix rule definition

### Viewing Alert Details

Click on an alert to expand details:

```
Alert Name:        EnhancementSuccessRateLow
State:             Firing (red)
Since:             2025-11-03 14:23:15 UTC (was pending for 10 minutes)

Expression:        enhancement_success_rate < 95
Labels:
  - severity: warning
  - component: enhancement-pipeline
  - tenant_id: client1

Annotations:
  Summary: "Enhancement success rate below 95% (current: 92.3%)"
  Description: "Enhancement pipeline success rate has been below 95%..."
  Runbook URL: "docs/operations/alert-runbooks.md#enhancementsuccessratelow"

Value:             92.3
Graphs:            [Graph] [Console] [Logs]
```

### Understanding Thresholds and Duration Clauses

**`for:` Clause:**
- Prevents false positives from brief spikes
- Alert only fires if condition sustained for full duration
- Example: `for: 10m` means 10 consecutive minutes below 95%

**`keep_firing_for:` Clause:**
- Prevents alert flapping during brief recoveries
- Alert remains firing even after condition resolves
- Example: `keep_firing_for: 5m` means alert stays red for 5 minutes after recovery

**Alert Durations by Type:**

| Alert | For Duration | Keep Firing | Rationale |
|-------|--------------|-------------|-----------|
| EnhancementSuccessRateLow | 10m | 5m | Non-critical, allow brief fluctuations |
| QueueDepthHigh | 5m | 3m | Warning level, medium duration |
| WorkerDown | 2m | 5m | Critical, fast detection, stability for brief restarts |
| HighLatency | 5m | 3m | Warning level, allows legitimate spikes |

---

## Testing Alerts

### Pre-Production Testing in Local Docker

**Setup:**
```bash
# Ensure Prometheus is running and alert rules loaded
docker-compose ps | grep prometheus

# Verify rules visible in UI
curl http://localhost:9090/api/v1/rules | jq '.data.groups[0].rules'

# Should show 4 alert rules: EnhancementSuccessRateLow, QueueDepthHigh, WorkerDown, HighLatency
```

### Testing Each Alert

#### 1. WorkerDown Alert (Fastest Test - 2 minutes)

```bash
# Step 1: Verify baseline - workers running, metric > 0
curl http://localhost:9090/api/v1/query?query=worker_active_count

# Step 2: Stop workers
docker-compose stop worker

# Step 3: Wait 2 minutes (for: 2m duration)
sleep 120

# Step 4: Check alert state
curl http://localhost:9090/api/v1/rules | jq '.data.groups[0].rules[] | select(.name=="WorkerDown")'

# Expected: state: "firing", value: 0

# Step 5: Restart workers
docker-compose start worker

# Step 6: Verify alert stays firing for 5 minutes (keep_firing_for: 5m)
sleep 300

# Step 7: Check alert resolved
curl http://localhost:9090/api/v1/rules | jq '.data.groups[0].rules[] | select(.name=="WorkerDown")'

# Expected: state: "inactive" (after keep_firing_for duration)
```

#### 2. QueueDepthHigh Alert (5 minute test)

```bash
# Step 1: Stop workers temporarily
docker-compose stop worker

# Step 2: Enqueue test jobs
for i in {1..150}; do
  docker-compose exec redis redis-cli LPUSH enhancement_queue "{\"ticket_id\": \"TEST-$i\"}"
done

# Step 3: Verify queue depth > 100
docker-compose exec redis redis-cli LLEN enhancement_queue

# Step 4: Wait 5 minutes
sleep 300

# Step 5: Check alert firing
curl http://localhost:9090/api/v1/rules | jq '.data.groups[0].rules[] | select(.name=="QueueDepthHigh")'

# Step 6: Start workers and monitor drainage
docker-compose start worker

# Step 7: Monitor queue until <100
watch -n 5 'docker-compose exec redis redis-cli LLEN enhancement_queue'
```

#### 3. EnhancementSuccessRateLow Alert (10 minute test)

```bash
# Step 1: Temporarily break ServiceDesk Plus API
# Edit tenant config - set invalid API credentials
docker-compose exec api bash -c 'export SDP_API_KEY=invalid && celery -A tasks call enhance_ticket[{\"ticket_id\": \"TEST-001\"}]'

# Step 2: Send webhook requests to trigger enhancements
for i in {1..20}; do
  curl -X POST http://localhost:8000/webhook \
    -H "Content-Type: application/json" \
    -d '{"ticket_id": "TEST-'"$i"'"}'
done

# Step 3: Wait 10 minutes
sleep 600

# Step 4: Check alert firing
curl http://localhost:9090/api/v1/rules | jq '.data.groups[0].rules[] | select(.name=="EnhancementSuccessRateLow")'

# Step 5: Fix API credentials
# Restore valid credentials and restart workers

# Step 6: Monitor success rate recovery
watch -n 10 'curl -s http://localhost:9090/api/v1/query?query=enhancement_success_rate | jq .data.result'
```

#### 4. HighLatency Alert (5 minute test)

```bash
# Step 1: Add artificial delay to worker code (temporary)
# In src/workers/tasks.py, add:
# import time
# time.sleep(150)  # 150 seconds in process_enhancement function

# Step 2: Send enhancement requests
for i in {1..5}; do
  curl -X POST http://localhost:8000/webhook \
    -H "Content-Type: application/json" \
    -d '{"ticket_id": "PERF-'"$i"'"}'
done

# Step 3: Monitor latency in Prometheus
curl 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,rate(enhancement_duration_seconds_bucket[5m]))'

# Step 4: Wait 5 minutes
sleep 300

# Step 5: Check alert firing
curl http://localhost:9090/api/v1/rules | jq '.data.groups[0].rules[] | select(.name=="HighLatency")'

# Step 6: Remove artificial delay from code

# Step 7: Monitor latency decreasing below 120s
watch -n 10 'curl -s http://localhost:9090/api/v1/query?query=histogram_quantile\(0.95,rate\(enhancement_duration_seconds_bucket\[5m\]\)\) | jq .data.result'
```

### Production Testing in Kubernetes

```bash
# Access Prometheus via port-forward
kubectl port-forward svc/prometheus 9090:9090

# Same test procedures as Docker, but using kubectl exec for pod operations:
# kubectl exec -it deployment/celery-worker -- stop  (simulating WorkerDown)
# kubectl logs -l app=celery-worker  (for debugging)
# kubectl describe pod -l app=celery-worker  (for resource/status info)
```

---

## Alert Management

### Monitoring Alert Performance

**Key Metrics to Track:**

```bash
# Alert firing rate
# How many alerts are currently firing
curl http://localhost:9090/api/v1/rules | jq '[.data.groups[].rules[] | select(.state=="firing")] | length'

# Alert noise (flapping)
# If same alert transitions frequently, may need to adjust for/keep_firing_for durations

# MTTR (Mean Time To Resolution)
# How long alerts stay firing before remediation
# Track in documentation or monitoring dashboard
```

### Adjusting Alert Thresholds

If alerts are too aggressive or too lenient:

```bash
# Edit alert-rules.yml
vim alert-rules.yml

# Adjust thresholds
# Example: EnhancementSuccessRateLow
# Original: enhancement_success_rate < 95
# Adjusted: enhancement_success_rate < 90  (less aggressive)

# Validate syntax
python3 -c "import yaml; yaml.safe_load(open('alert-rules.yml')); print('Valid')"

# Reload Prometheus
docker-compose restart prometheus

# Wait for rules to load and monitor impact
curl http://localhost:9090/api/v1/rules | jq '.data.groups[0].rules'
```

### Adjusting Alert Duration Clauses

If `for:` duration causing delayed detection or `keep_firing_for` too long:

```yaml
# Too aggressive (frequent false positives)
- alert: EnhancementSuccessRateLow
  expr: enhancement_success_rate < 95
  for: 5m          # Changed from 10m - faster detection
  keep_firing_for: 3m  # Changed from 5m - resolves sooner

# Too lenient (missing real issues)
- alert: EnhancementSuccessRateLow
  expr: enhancement_success_rate < 95
  for: 15m         # Changed from 10m - waits longer
  keep_firing_for: 7m   # Changed from 5m - stability period

# Reload after editing
docker-compose restart prometheus
```

### Alert Silencing Procedure

**Current Workaround** (before Story 4.5 Alertmanager):

```bash
# 1. Edit alert-rules.yml
vim alert-rules.yml

# 2. Comment out the alert(s) to silence
# Example: silence QueueDepthHigh for maintenance
#   # - alert: QueueDepthHigh   ← Comment out this line
#   #   expr: queue_depth > 100
#   #   ...

# 3. Reload Prometheus config
docker-compose restart prometheus
# OR
curl -X POST http://localhost:9090/-/reload

# 4. Verify alert is silenced
# Prometheus UI: Alerts page should no longer show QueueDepthHigh

# 5. Document silence
# Add comment with reason and date:
# SILENCED until 2025-11-04 for database maintenance
# - alert: QueueDepthHigh

# 6. Set reminder to re-enable
# After maintenance window, uncomment and reload

# 7. Re-enable alert
# Uncomment the alert rules
vim alert-rules.yml

# 8. Reload again
docker-compose restart prometheus
```

**Best Practices for Silencing:**

✅ **DO:**
- Document reason and end date for silence
- Use for planned maintenance only
- Set calendar reminder to re-enable
- Test that alert re-fires after re-enabling

❌ **DO NOT:**
- Silence critical alerts indefinitely
- Forget to re-enable after maintenance
- Use silencing as substitute for fixing root cause
- Silence without documenting reason

**Future: Native Silencing (Story 4.5)**

When Alertmanager is integrated:
- Web UI for creating temporary silences
- Silence expiration times
- Silence history and audit trail
- Per-alert and label-based silencing

---

## Troubleshooting

### Alert Not Firing When Expected

**Symptoms:** Condition met but alert remains inactive

**Debug Steps:**

```bash
# 1. Verify metric exists and has expected value
curl 'http://localhost:9090/api/v1/query?query=enhancement_success_rate'
# Should return non-empty result with value

# 2. Test PromQL expression in Prometheus Graph
# Navigate to http://localhost:9090/graph
# Paste expression: enhancement_success_rate < 95
# Check if it returns results

# 3. Check evaluation_interval
# Default: 15s, means alert rule evaluated every 15 seconds

# 4. Verify 'for:' duration requirement
# Alert requires condition to persist for full 'for' duration
# If condition only met for 5 minutes but for: 10m, won't fire yet

# 5. Check Prometheus logs for configuration errors
docker-compose logs prometheus | grep -i "alert\|error"
```

### Alert Always Firing (Won't Resolve)

**Symptoms:** Alert stuck in firing state after condition resolved

**Debug Steps:**

```bash
# 1. Verify condition has actually resolved
curl 'http://localhost:9090/api/v1/query?query=enhancement_success_rate'
# Value should now be > 95

# 2. Check keep_firing_for duration hasn't expired yet
# Alert will stay firing for keep_firing_for duration even after resolution
# Example: keep_firing_for: 5m means alert stays red for 5 more minutes

# 3. Wait for keep_firing_for to elapse
# Then alert should transition to resolved/inactive

# 4. If alert still firing after long duration:
# - Check if condition actually re-triggered (false positive resolution)
# - Review Prometheus expression for logic errors
# - Check metric labels are as expected
```

### Prometheus Config Won't Load

**Symptoms:** Alert rules show error in UI, or rules not appearing

**Debug Steps:**

```bash
# 1. Check Prometheus logs for specific error
docker-compose logs prometheus | tail -50 | grep -i error

# 2. Validate YAML syntax
python3 -c "import yaml; yaml.safe_load(open('prometheus.yml'))"
python3 -c "import yaml; yaml.safe_load(open('alert-rules.yml'))"

# 3. Verify rule_files path is correct
grep -A 2 "rule_files:" prometheus.yml
# Should show: rule_files: - "alert-rules.yml"

# 4. Check file permissions (Docker)
ls -la alert-rules.yml
# Should be readable by Prometheus container

# 5. Restart Prometheus with fresh config
docker-compose down
docker-compose up -d prometheus
docker-compose logs prometheus | head -30
```

### Metrics Not Available for Alerting

**Symptoms:** Alert expression returns no data, metric not found

**Debug Steps:**

```bash
# 1. Verify /metrics endpoint is exposed
curl http://localhost:8000/metrics | head -20

# 2. Check that Prometheus is scraping
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[]'
# Should show fastapi-app target in "up" state (value: 1)

# 3. Query for specific metric
curl 'http://localhost:9090/api/v1/query?query=enhancement_success_rate'

# 4. Check metric name spelling matches exactly
# Common mistakes: enhancement_success_rate vs enhancement_success_ratio

# 5. Verify metrics are being collected
# May need to process some enhancements to generate data points
```

---

## Next Steps

### Story 4.5: Alertmanager Integration (In Backlog)

**What will be added:**
- AlertManager deployment for alert routing
- Slack channel notifications for alerts
- Email notifications for critical alerts
- PagerDuty integration for on-call paging
- Alert silencing UI (replace temporary workaround)
- Alert grouping and aggregation

### Story 4.6: Distributed Tracing (In Backlog)

**Helps debug high latency alerts:**
- OpenTelemetry integration
- Trace visualization for enhancement requests
- Latency breakdown by component (API calls, LLM, database)
- Performance profiling

### Monitoring Roadmap

1. **Current (Stories 4.1-4.4):** Metrics collection, Prometheus, Grafana dashboards, basic alerting
2. **Next (Story 4.5):** Alert routing and notifications
3. **Future (Story 4.6):** Distributed tracing for debugging
4. **Long-term:** ML-based anomaly detection, predictive alerting

---

## References

**Official Documentation:**
- Prometheus Alerting: https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/
- PromQL Guide: https://prometheus.io/docs/prometheus/latest/querying/basics/
- Alert Annotations & Templates: https://prometheus.io/docs/prometheus/latest/configuration/template_examples/

**Related Stories:**
- Story 4.1: Metrics Instrumentation
- Story 4.2: Prometheus Deployment
- Story 4.3: Grafana Dashboards
- Story 4.5: Alertmanager Integration (Future)

**Runbooks:**
- Alert Troubleshooting: docs/operations/alert-runbooks.md

**Architecture:**
- docs/architecture.md - Technology Stack & Monitoring Design
- docs/PRD.md - FR025 (Critical Failure Alerting), NFR005 (Observability)
