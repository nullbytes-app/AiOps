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
