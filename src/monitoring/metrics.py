"""Prometheus metrics instrumentation for AI Agents enhancement pipeline.

This module defines all Prometheus metrics for real-time monitoring of the
enhancement pipeline, queue health, and worker activity. Metrics are exposed
via the /metrics endpoint for scraping by Prometheus server.

Metrics Coverage:
- enhancement_requests_total: Counter for webhook requests received
- enhancement_duration_seconds: Histogram for processing latency (p50, p95, p99)
- enhancement_success_rate: Gauge for current success rate percentage
- queue_depth: Gauge for Redis queue pending job count
- worker_active_count: Gauge for active Celery worker count

All metrics include tenant_id labels for multi-tenant observability and follow
Prometheus naming conventions (snake_case, _total suffix for counters,
_seconds for durations).
"""

from prometheus_client import Counter, Gauge, Histogram

# ============================================================================
# COUNTER: enhancement_requests_total
# ============================================================================
# Description: Total number of enhancement requests received via webhook
# Labels: tenant_id, status (received/queued/rejected)
# Use: Track request volume and rejection rates
# ============================================================================

enhancement_requests_total: Counter = Counter(
    name="enhancement_requests_total",
    documentation="Total number of enhancement requests received via webhook",
    labelnames=["tenant_id", "status"],
)

# ============================================================================
# HISTOGRAM: enhancement_duration_seconds
# ============================================================================
# Description: Time taken to complete ticket enhancement (webhook to ticket update)
# Labels: tenant_id, status (success/failure)
# Buckets: Default Prometheus buckets for latency distribution
# Use: Calculate p50, p95, p99 latency via PromQL
# ============================================================================

enhancement_duration_seconds: Histogram = Histogram(
    name="enhancement_duration_seconds",
    documentation="Time taken to complete ticket enhancement (webhook to ticket update)",
    labelnames=["tenant_id", "status"],
    buckets=(
        0.005,
        0.01,
        0.025,
        0.05,
        0.075,
        0.1,
        0.25,
        0.5,
        0.75,
        1.0,
        2.5,
        5.0,
        7.5,
        10.0,
    ),
)

# ============================================================================
# GAUGE: enhancement_success_rate
# ============================================================================
# Description: Current enhancement success rate percentage (rolling 5-minute window)
# Labels: tenant_id
# Calculation: (successful_enhancements / total_enhancements) * 100
# Use: Monitor success rate trends and alert on failures
# ============================================================================

enhancement_success_rate: Gauge = Gauge(
    name="enhancement_success_rate",
    documentation="Current enhancement success rate percentage (rolling 5-minute window)",
    labelnames=["tenant_id"],
)

# ============================================================================
# GAUGE: queue_depth
# ============================================================================
# Description: Current number of pending enhancement jobs in Redis queue
# Labels: queue_name (e.g., "enhancement:queue")
# Update: On queue operations (enqueue, dequeue) or via periodic background task
# Use: Monitor queue health, trigger alerts when queue depth exceeds threshold
# ============================================================================

queue_depth: Gauge = Gauge(
    name="queue_depth",
    documentation="Current number of pending enhancement jobs in Redis queue",
    labelnames=["queue_name"],
)

# ============================================================================
# GAUGE: worker_active_count
# ============================================================================
# Description: Number of currently active Celery workers processing enhancements
# Labels: worker_type (e.g., "celery_enhancement")
# Update: Via Celery inspect() API or custom worker heartbeat mechanism
# Use: Monitor worker availability and scale workers based on demand
# ============================================================================

worker_active_count: Gauge = Gauge(
    name="worker_active_count",
    documentation="Number of currently active Celery workers processing enhancements",
    labelnames=["worker_type"],
)

# ============================================================================
# MCP BRIDGE POOLING METRICS (Story 11.2.3)
# ============================================================================
# NOTE: These metrics are defined but NOT yet instrumented in the bridge pooling code.
# Story 11.2.3 implements simplified bridge pooling (per-execution context lifecycle)
# without the full MCPConnectionPool class that would use these metrics.
# These are marked as FUTURE ENHANCEMENT for potential instrumentation if monitoring
# requirements emerge or if full connection pool manager is implemented later.
# ============================================================================

# GAUGE: mcp_pool_total_clients
mcp_pool_total_clients: Gauge = Gauge(
    name="mcp_pool_total_clients",
    documentation="Total number of MCP clients in pool",
    labelnames=["transport_type"],
)

# GAUGE: mcp_pool_active_clients
mcp_pool_active_clients: Gauge = Gauge(
    name="mcp_pool_active_clients",
    documentation="Number of MCP clients currently in use",
    labelnames=["transport_type"],
)

# GAUGE: mcp_pool_idle_clients
mcp_pool_idle_clients: Gauge = Gauge(
    name="mcp_pool_idle_clients",
    documentation="Number of MCP clients available for reuse",
    labelnames=["transport_type"],
)

# COUNTER: mcp_pool_client_acquisitions_total
mcp_pool_client_acquisitions_total: Counter = Counter(
    name="mcp_pool_client_acquisitions_total",
    documentation="Total number of MCP client acquisitions from pool",
    labelnames=["server_id", "transport_type", "tenant_id"],
)

# COUNTER: mcp_pool_client_reuses_total
mcp_pool_client_reuses_total: Counter = Counter(
    name="mcp_pool_client_reuses_total",
    documentation="Total number of MCP client reuses (cache hits)",
    labelnames=["server_id", "transport_type", "tenant_id"],
)

# COUNTER: mcp_pool_client_creations_total
mcp_pool_client_creations_total: Counter = Counter(
    name="mcp_pool_client_creations_total",
    documentation="Total number of new MCP client creations (cache misses)",
    labelnames=["server_id", "transport_type", "tenant_id"],
)

# COUNTER: mcp_pool_client_evictions_total
mcp_pool_client_evictions_total: Counter = Counter(
    name="mcp_pool_client_evictions_total",
    documentation="Total number of MCP client evictions from pool",
    labelnames=["transport_type"],
)

# COUNTER: mcp_pool_client_health_check_failures_total
mcp_pool_client_health_check_failures_total: Counter = Counter(
    name="mcp_pool_client_health_check_failures_total",
    documentation="Total number of failed MCP client health checks",
    labelnames=["server_id", "transport_type"],
)

# HISTOGRAM: mcp_pool_acquisition_duration_seconds
mcp_pool_acquisition_duration_seconds: Histogram = Histogram(
    name="mcp_pool_acquisition_duration_seconds",
    documentation="Time to acquire MCP client from pool (seconds)",
    labelnames=["server_id", "transport_type", "tenant_id"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

# HISTOGRAM: mcp_pool_wait_time_seconds
mcp_pool_wait_time_seconds: Histogram = Histogram(
    name="mcp_pool_wait_time_seconds",
    documentation="Time waiting for available MCP client (seconds)",
    labelnames=["server_id", "transport_type"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# ===== MCP Server Health Monitoring Metrics (Story 11.2.4) =====
# These metrics track detailed health check results for MCP servers,
# enabling performance analysis, failure detection, and trend monitoring.

# GAUGE: mcp_server_health_status
mcp_server_health_status: Gauge = Gauge(
    name="mcp_server_health_status",
    documentation="MCP server health status (1=active, 0=inactive)",
    labelnames=["server_id", "server_name", "transport_type", "tenant_id"],
)

# GAUGE: mcp_server_last_check_timestamp
mcp_server_last_check_timestamp: Gauge = Gauge(
    name="mcp_server_last_check_timestamp",
    documentation="Timestamp of last health check (Unix seconds)",
    labelnames=["server_id", "server_name"],
)

# COUNTER: mcp_health_checks_total
mcp_health_checks_total: Counter = Counter(
    name="mcp_health_checks_total",
    documentation="Total health checks performed",
    labelnames=["server_id", "server_name", "transport_type", "status"],
)

# COUNTER: mcp_health_check_errors_total
mcp_health_check_errors_total: Counter = Counter(
    name="mcp_health_check_errors_total",
    documentation="Total health check errors",
    labelnames=["server_id", "server_name", "error_type"],
)

# HISTOGRAM: mcp_health_check_duration_seconds
mcp_health_check_duration_seconds: Histogram = Histogram(
    name="mcp_health_check_duration_seconds",
    documentation="Health check response time distribution",
    labelnames=["server_id", "server_name", "transport_type"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, float("inf")),
)
