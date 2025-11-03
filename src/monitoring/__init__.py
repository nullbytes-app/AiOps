"""Monitoring module for Prometheus metrics and OpenTelemetry distributed tracing.

Exports:
- Prometheus metrics for real-time monitoring
- OpenTelemetry tracing functions for distributed trace collection
"""

from src.monitoring.metrics import (
    enhancement_duration_seconds,
    enhancement_requests_total,
    enhancement_success_rate,
    queue_depth,
    worker_active_count,
)
from src.monitoring.tracing import get_tracer, init_tracer_provider

__all__ = [
    # Prometheus metrics
    "enhancement_requests_total",
    "enhancement_duration_seconds",
    "enhancement_success_rate",
    "queue_depth",
    "worker_active_count",
    # OpenTelemetry tracing
    "init_tracer_provider",
    "get_tracer",
]
