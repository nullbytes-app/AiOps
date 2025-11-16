# MCP Server Health Monitoring Guide

**Story:** 11.2.4 - Enhanced MCP Health Monitoring
**Last Updated:** 2025-11-10

## Overview

This guide explains how to monitor MCP server health using the enhanced health monitoring system implemented in Story 11.2.4. The system provides:

- **Time-series metrics collection** with 7-day retention
- **Prometheus metrics** for real-time monitoring and alerting
- **SQL-based aggregations** with percentile calculations (P50/P95/P99)
- **Streamlit health dashboard** with charts and auto-refresh
- **REST API endpoint** for programmatic access

## Architecture

### Components

1. **Health Check Task** (`mcp_health_check_task`)
   - Runs every 30 seconds via Celery Beat
   - Calls `perform_detailed_health_check()` for each server
   - Records metrics to `mcp_server_metrics` table
   - Updates Prometheus metrics

2. **Metrics Database** (`mcp_server_metrics`)
   - Stores time-series health check results
   - Columns: `response_time_ms`, `status`, `error_type`, `check_timestamp`
   - Indexed on `check_timestamp` for fast queries
   - 7-day retention enforced by daily cleanup task

3. **Metrics Aggregation Service** (`mcp_metrics_aggregator.py`)
   - `get_server_metrics()`: Aggregates metrics over time period
   - `calculate_trend()`: Compares 24h periods for trend analysis
   - Uses PostgreSQL `PERCENTILE_CONT()` for efficient percentiles

4. **API Endpoint** (`GET /api/v1/mcp-servers/{id}/metrics`)
   - Query params: `period_hours` (1-168, default 24)
   - Returns JSON with success rates, percentiles, error distribution
   - Enforces tenant isolation

5. **Streamlit Dashboard** (`12_MCP_Servers.py`)
   - Embedded in server details view
   - Auto-refreshes every 30 seconds
   - Charts: percentiles, success/error pie, error distribution bar

6. **Cleanup Task** (`cleanup_old_mcp_metrics_task`)
   - Runs daily at 02:00 UTC
   - Deletes metrics older than 7 days
   - Retries up to 3 times on failure

## Prometheus Metrics

### Available Metrics

#### 1. `mcp_server_health_status` (Gauge)
Current health status (1=active, 0=inactive)

**Labels:**
- `server_id`: MCP server UUID
- `server_name`: Server name
- `transport_type`: stdio | http_sse
- `tenant_id`: Tenant UUID

**Example Query:**
```promql
# Active servers count
sum(mcp_server_health_status{transport_type="stdio"})

# Servers down (inactive)
mcp_server_health_status{server_name=~".*"} == 0
```

#### 2. `mcp_server_last_check_timestamp` (Gauge)
Unix timestamp of last health check

**Labels:**
- `server_id`: MCP server UUID
- `server_name`: Server name

**Example Query:**
```promql
# Time since last check (seconds)
time() - mcp_server_last_check_timestamp

# Stale health checks (no check in 2 minutes)
time() - mcp_server_last_check_timestamp > 120
```

#### 3. `mcp_health_checks_total` (Counter)
Total health checks performed

**Labels:**
- `server_id`: MCP server UUID
- `server_name`: Server name
- `transport_type`: stdio | http_sse
- `status`: success | timeout | error | connection_failed

**Example Query:**
```promql
# Check rate (checks/sec)
rate(mcp_health_checks_total[5m])

# Success rate (percentage)
sum(rate(mcp_health_checks_total{status="success"}[5m])) / sum(rate(mcp_health_checks_total[5m])) * 100

# Error rate by server
rate(mcp_health_checks_total{status!="success"}[5m])
```

#### 4. `mcp_health_check_errors_total` (Counter)
Total health check errors

**Labels:**
- `server_id`: MCP server UUID
- `server_name`: Server name
- `error_type`: TimeoutError | ProcessCrashed | InvalidJSON | etc.

**Example Query:**
```promql
# Error rate by type
sum(rate(mcp_health_check_errors_total[5m])) by (error_type)

# Top 5 servers by error count
topk(5, sum(increase(mcp_health_check_errors_total[24h])) by (server_name))
```

#### 5. `mcp_health_check_duration_seconds` (Histogram)
Health check response time distribution

**Labels:**
- `server_id`: MCP server UUID
- `server_name`: Server name
- `transport_type`: stdio | http_sse

**Buckets:** 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, +Inf

**Example Query:**
```promql
# P50 (median) response time
histogram_quantile(0.5, rate(mcp_health_check_duration_seconds_bucket[5m]))

# P95 response time
histogram_quantile(0.95, rate(mcp_health_check_duration_seconds_bucket[5m]))

# P99 response time
histogram_quantile(0.99, rate(mcp_health_check_duration_seconds_bucket[5m]))

# Average response time
rate(mcp_health_check_duration_seconds_sum[5m]) / rate(mcp_health_check_duration_seconds_count[5m])
```

## Prometheus Alert Rules

### Critical Alerts

#### MCP Server Down
```yaml
- alert: MCPServerDown
  expr: mcp_server_health_status == 0
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "MCP server {{ $labels.server_name }} is down"
    description: "Server {{ $labels.server_name }} ({{ $labels.server_id }}) has been inactive for 5 minutes. Check server logs and restart if needed."
```

#### High Error Rate
```yaml
- alert: MCPServerHighErrorRate
  expr: |
    sum(rate(mcp_health_checks_total{status!="success"}[5m])) by (server_name)
    /
    sum(rate(mcp_health_checks_total[5m])) by (server_name)
    > 0.2
  for: 10m
  labels:
    severity: critical
  annotations:
    summary: "MCP server {{ $labels.server_name }} has high error rate"
    description: "Server {{ $labels.server_name }} error rate > 20% for 10 minutes. Current rate: {{ $value | humanizePercentage }}"
```

### Warning Alerts

#### Degraded Performance
```yaml
- alert: MCPServerDegradedPerformance
  expr: |
    histogram_quantile(0.95, rate(mcp_health_check_duration_seconds_bucket[5m])) > 5
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: "MCP server {{ $labels.server_name }} has degraded performance"
    description: "Server {{ $labels.server_name }} P95 response time > 5s for 15 minutes. Current P95: {{ $value }}s"
```

#### Stale Health Checks
```yaml
- alert: MCPServerStaleHealthCheck
  expr: time() - mcp_server_last_check_timestamp > 120
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "MCP server {{ $labels.server_name }} health check is stale"
    description: "No health check recorded for server {{ $labels.server_name }} in last 2 minutes. Health check task may be stuck."
```

#### Frequent Timeouts
```yaml
- alert: MCPServerFrequentTimeouts
  expr: |
    sum(rate(mcp_health_check_errors_total{error_type="TimeoutError"}[5m])) by (server_name)
    > 0.1
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "MCP server {{ $labels.server_name }} experiencing frequent timeouts"
    description: "Server {{ $labels.server_name }} timeout rate > 0.1/sec for 10 minutes. Check server responsiveness."
```

### Informational Alerts

#### Circuit Breaker Triggered
```yaml
- alert: MCPServerCircuitBreakerTriggered
  expr: |
    mcp_server_health_status == 0
    and
    changes(mcp_server_health_status[5m]) > 0
  labels:
    severity: info
  annotations:
    summary: "MCP server {{ $labels.server_name }} circuit breaker triggered"
    description: "Server {{ $labels.server_name }} marked inactive after 3 consecutive failures. Manual intervention required to reactivate."
```

## Grafana Dashboard

### Example Panels

#### 1. Server Health Status Overview
```promql
# Panel type: Stat
# Query:
sum(mcp_server_health_status)

# Display: Show total active servers
# Thresholds:
#   - Red: < 5 (critical - most servers down)
#   - Yellow: 5-10 (warning)
#   - Green: > 10 (healthy)
```

#### 2. Success Rate by Server
```promql
# Panel type: Time series
# Query:
sum(rate(mcp_health_checks_total{status="success"}[5m])) by (server_name)
/
sum(rate(mcp_health_checks_total[5m])) by (server_name)
* 100

# Y-axis: Percentage (0-100)
# Legend: {{ server_name }}
```

#### 3. Response Time Percentiles
```promql
# Panel type: Time series
# Queries:
# P50:
histogram_quantile(0.5, rate(mcp_health_check_duration_seconds_bucket[5m]))

# P95:
histogram_quantile(0.95, rate(mcp_health_check_duration_seconds_bucket[5m]))

# P99:
histogram_quantile(0.99, rate(mcp_health_check_duration_seconds_bucket[5m]))

# Y-axis: Seconds
# Legend: P50, P95, P99
```

#### 4. Error Distribution Heatmap
```promql
# Panel type: Heatmap
# Query:
sum(increase(mcp_health_check_errors_total[1h])) by (error_type, server_name)

# X-axis: Time
# Y-axis: Error type
# Color: Count
```

## API Usage Examples

### Fetch Metrics for Last 24 Hours
```bash
curl -X GET "http://localhost:8000/api/v1/mcp-servers/{server_id}/metrics?period_hours=24" \
  -H "X-Tenant-ID: {tenant_id}"
```

### Fetch Metrics for Last 7 Days
```bash
curl -X GET "http://localhost:8000/api/v1/mcp-servers/{server_id}/metrics?period_hours=168" \
  -H "X-Tenant-ID: {tenant_id}"
```

### Example Response
```json
{
  "server_id": "550e8400-e29b-41d4-a716-446655440000",
  "server_name": "filesystem-server",
  "period_hours": 24,
  "metrics": {
    "total_checks": 2880,
    "success_rate": 0.985,
    "error_rate": 0.015,
    "avg_response_time_ms": 125,
    "p50_response_time_ms": 95,
    "p95_response_time_ms": 280,
    "p99_response_time_ms": 450,
    "max_response_time_ms": 1200,
    "errors_by_type": {
      "TimeoutError": 28,
      "ProcessCrashed": 5,
      "InvalidJSON": 10
    },
    "uptime_percentage": 98.5,
    "last_24h_trend": "stable"
  }
}
```

## Streamlit Dashboard Usage

### Accessing the Dashboard

1. Navigate to **MCP Servers** page in Streamlit Admin UI
2. Click on a server from the list
3. Scroll to **📊 Health Metrics Dashboard** section

### Dashboard Features

- **Period Selector:** Choose time period (1h, 6h, 12h, 24h, 48h, 72h, 168h)
- **Key Metrics Grid:**
  - Success Rate (percentage)
  - Uptime (percentage)
  - Avg Response Time (ms)
  - Total Checks (count)

- **Charts:**
  - Response Time Distribution (P50/P95/P99/Max)
  - Success vs Error Rate (pie chart)
  - Error Distribution by Type (bar chart)

- **Performance Trend:**
  - 📈 Improving: Response time decreased > 10%
  - ➡️ Stable: Change within ±10%
  - 📉 Degrading: Response time increased > 10%

- **Auto-Refresh:** Dashboard refreshes every 30 seconds

### Interpreting Metrics

#### Success Rate
- **> 99%:** Excellent - server is highly reliable
- **95-99%:** Good - occasional failures acceptable
- **< 95%:** Poor - investigate error_type distribution

#### Response Time Percentiles
- **P50 (Median):** Typical user experience
- **P95:** 95% of requests faster than this
- **P99:** Slowest 1% of requests
- **Max:** Worst-case latency

#### Performance Trend
- **Improving:** Recent optimizations effective
- **Stable:** Consistent performance
- **Degrading:** Investigate resource constraints, network issues

## Troubleshooting

### No Metrics Available
**Symptom:** Dashboard shows "No metrics available for this period"

**Causes:**
1. Server was recently created (< 30s ago)
2. Health check task not running
3. Database connectivity issues

**Resolution:**
```bash
# Check Celery Beat is running
docker-compose ps celery-beat

# Check Celery worker is running
docker-compose ps celery-worker

# View health check task logs
docker-compose logs celery-worker | grep mcp_health_check

# Manually trigger health check via API
curl -X POST "http://localhost:8000/api/v1/mcp-servers/{server_id}/health-check" \
  -H "X-Tenant-ID: {tenant_id}"
```

### Stale Metrics (> 2 minutes old)
**Symptom:** Prometheus alert `MCPServerStaleHealthCheck` firing

**Causes:**
1. Celery Beat schedule misconfigured
2. Health check task timing out (> 30s)
3. Database connection pool exhausted

**Resolution:**
```bash
# Restart Celery Beat
docker-compose restart celery-beat

# Check Celery Beat schedule
docker-compose exec celery-beat celery -A src.workers.celery_app inspect scheduled

# Check database connection pool
docker-compose logs postgres | grep "connection"
```

### High P99 Response Time (> 5s)
**Symptom:** Slow health checks, degraded user experience

**Causes:**
1. stdio process startup overhead
2. Network latency (HTTP+SSE servers)
3. Resource contention on worker host

**Resolution:**
```bash
# Check server resource usage
docker stats

# Check network latency (HTTP+SSE)
curl -w "@curl-format.txt" -o /dev/null -s {server_url}

# Review server logs for slow operations
docker-compose logs -f --tail=100 | grep {server_name}
```

### Circuit Breaker Triggered (status=inactive)
**Symptom:** Server marked inactive after 3 consecutive failures

**Causes:**
1. Server process crashed
2. Configuration error (wrong command/URL)
3. Network connectivity issues

**Resolution:**
```bash
# Check server error_message in database
psql -U aiagents -c "SELECT name, status, error_message, consecutive_failures FROM mcp_servers WHERE id='{server_id}';"

# Review recent error logs
docker-compose logs -f --tail=50 | grep {server_id}

# Fix configuration and rediscover
# Via Streamlit: Click "Rediscover" button on server details page
# Via API:
curl -X POST "http://localhost:8000/api/v1/mcp-servers/{server_id}/discover" \
  -H "X-Tenant-ID: {tenant_id}"
```

## Data Retention

### Metrics Retention Policy
- **Duration:** 7 days
- **Cleanup Schedule:** Daily at 02:00 UTC
- **Cleanup Task:** `cleanup_old_mcp_metrics_task`

### Manual Cleanup
```sql
-- Delete metrics older than 7 days
DELETE FROM mcp_server_metrics
WHERE check_timestamp < NOW() - INTERVAL '7 days';
```

### Extending Retention
To extend retention beyond 7 days, update the cleanup task:

```python
# src/workers/tasks.py
# Line ~1651: Change retention_days
retention_days = 30  # Extend to 30 days
```

**Storage Impact:**
- Default: ~2880 checks/day/server @ 30s interval
- 1 server x 7 days = ~20,160 rows
- 10 servers x 7 days = ~201,600 rows
- Est. storage: 100 bytes/row = ~20MB/7days/10servers

## References

- **Story:** `docs/stories/11-2-4-enhanced-mcp-health-monitoring.md`
- **API Endpoint:** `src/api/mcp_servers.py:get_mcp_server_metrics()`
- **Aggregation Service:** `src/services/mcp_metrics_aggregator.py`
- **Health Monitor:** `src/services/mcp_health_monitor.py`
- **Prometheus Metrics:** `src/monitoring/metrics.py` (lines 193-231)
- **Cleanup Task:** `src/workers/tasks.py:cleanup_old_mcp_metrics_task()`
- **Database Schema:** `alembic/versions/012_add_mcp_server_metrics_table.py`
