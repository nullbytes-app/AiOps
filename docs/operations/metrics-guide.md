# Metrics Guide - AI Agents Platform

## Overview

This guide documents the Prometheus metrics exposed by the AI Agents Platform for operational monitoring and observability. The platform exposes metrics at the `/metrics` endpoint following Prometheus exposition format.

## Available Metrics

### enhancement_requests_total (Counter)

Tracks total number of enhancement requests processed by the system.

**Labels:**
- `tenant_id`: Identifier for the tenant making the request
- `status`: Request status (`queued`, `processing`, `success`, `failure`)

**Use Cases:**
- Request rate monitoring
- Success/failure ratio analysis
- Per-tenant usage tracking

### enhancement_duration_seconds (Histogram)

Measures the duration of enhancement processing operations.

**Labels:**
- `tenant_id`: Identifier for the tenant
- `operation`: Type of operation performed

**Buckets:** 0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, +Inf (seconds)

**Use Cases:**
- Latency analysis (p50, p95, p99 percentiles)
- SLA compliance monitoring
- Performance regression detection

### enhancement_success_rate (Gauge)

Current success rate percentage for enhancement operations.

**Labels:**
- `tenant_id`: Identifier for the tenant

**Value Range:** 0-100 (percentage)

**Use Cases:**
- Real-time reliability monitoring
- Tenant-specific success tracking
- Alert triggers for degraded performance

### queue_depth (Gauge)

Number of pending jobs in the Redis queue.

**Labels:**
- `queue_name`: Name of the queue (e.g., `enhancement:queue`)

**Use Cases:**
- Capacity planning
- Backlog monitoring
- Worker scaling decisions

### worker_active_count (Gauge)

Number of active Celery workers processing jobs.

**Labels:**
- `worker_type`: Type of worker (e.g., `enhancement`)

**Use Cases:**
- Worker health monitoring
- Scaling decisions
- Resource utilization tracking

---

## Sample PromQL Queries

### p95 Latency

Calculates the 95th percentile of enhancement processing time over the last 5 minutes.

```promql
histogram_quantile(0.95, rate(enhancement_duration_seconds_bucket[5m]))
```

**Expected Result:** Float value in seconds (e.g., `12.5` = 12.5 seconds)

**Use Case:** SLA monitoring, performance baseline tracking

---

### Error Rate

Percentage of failed enhancements in the last 5 minutes.

```promql
rate(enhancement_requests_total{status="failure"}[5m]) / rate(enhancement_requests_total[5m]) * 100
```

**Expected Result:** Float percentage (e.g., `2.5` = 2.5% error rate)

**Use Case:** Reliability monitoring, alert triggers

---

### Queue Depth

Current number of pending enhancement jobs.

```promql
queue_depth{queue_name="enhancement:queue"}
```

**Expected Result:** Integer (e.g., `42` = 42 pending jobs)

**Use Case:** Capacity planning, worker scaling

---

### Success Rate by Tenant

Success rate for a specific tenant.

```promql
enhancement_success_rate{tenant_id="acme"}
```

**Expected Result:** Float percentage (e.g., `98.5` = 98.5% success rate)

**Use Case:** Per-tenant SLA monitoring, customer success tracking

---

### Request Rate

Enhancement requests per second.

```promql
rate(enhancement_requests_total[1m])
```

**Expected Result:** Float (e.g., `0.25` = 0.25 requests/second = 15 requests/minute)

**Use Case:** Load monitoring, traffic analysis

---

### p99 Latency by Tenant

99th percentile processing time for a specific tenant over the last 10 minutes.

```promql
histogram_quantile(0.99, rate(enhancement_duration_seconds_bucket{tenant_id="acme"}[10m]))
```

**Expected Result:** Float value in seconds

**Use Case:** Tenant-specific performance monitoring

---

### Active Workers

Number of currently active Celery workers.

```promql
worker_active_count{worker_type="enhancement"}
```

**Expected Result:** Integer (e.g., `4` = 4 active workers)

**Use Case:** Worker health monitoring, capacity tracking

---

## Testing Queries in Prometheus UI

1. **Access Prometheus UI:**
   - Local: http://localhost:9090
   - Kubernetes: `kubectl port-forward svc/prometheus 9090:9090`

2. **Navigate to Graph Tab:**
   - Click "Graph" in the top navigation bar

3. **Enter Query:**
   - Type or paste a PromQL query into the expression box
   - Click "Execute" or press Enter

4. **View Results:**
   - **Graph View:** Time-series visualization of metrics over time
   - **Console View:** Instant values and table format

5. **Adjust Time Range:**
   - Use the time picker to adjust the query time range
   - Default is last 1 hour

---

## Multi-Tenant Filtering

All metrics include `tenant_id` labels for per-tenant observability. Use label matchers to filter by tenant:

**Example: Requests for specific tenant**
```promql
enhancement_requests_total{tenant_id="acme"}
```

**Example: Error rate for multiple tenants**
```promql
rate(enhancement_requests_total{status="failure", tenant_id=~"acme|globex"}[5m])
```

**Example: Top 5 tenants by request rate**
```promql
topk(5, sum by (tenant_id) (rate(enhancement_requests_total[5m])))
```

---

## Alerting Recommendations

### High Error Rate Alert

```yaml
alert: HighErrorRate
expr: rate(enhancement_requests_total{status="failure"}[5m]) / rate(enhancement_requests_total[5m]) > 0.05
for: 10m
annotations:
  summary: "High error rate detected: {{ $value | humanizePercentage }}"
```

### High Queue Depth Alert

```yaml
alert: HighQueueDepth
expr: queue_depth{queue_name="enhancement:queue"} > 100
for: 5m
annotations:
  summary: "Queue depth exceeds threshold: {{ $value }} pending jobs"
```

### Slow Processing Alert

```yaml
alert: SlowProcessing
expr: histogram_quantile(0.95, rate(enhancement_duration_seconds_bucket[10m])) > 60
for: 15m
annotations:
  summary: "p95 latency exceeds 60 seconds: {{ $value }}s"
```

---

## Next Steps

- **Story 4.3:** Set up Grafana dashboards for visualization
- **Story 4.4:** Configure alerting rules in Prometheus
- **Story 4.5:** Integrate Alertmanager for alert routing

---

**Related Documentation:**
- [Prometheus Setup Guide](prometheus-setup.md)
- [Architecture - Observability](../architecture.md#observability)
- [PRD - NFR005 (Observability Requirements)](../PRD.md#nfr005-observability)
