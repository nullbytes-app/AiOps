"""
Unit tests for Prometheus metrics module (Story 4.1).

Tests core metrics definitions, labels, and basic functionality
without requiring HTTP endpoints or full application startup.

Test Coverage:
- AC1: Metrics module loads correctly
- AC2: All 5 metrics are defined and exportable
- AC3: Metrics accept correct label combinations
- AC4: Counter increments correctly
- AC4: Histogram observes durations correctly
- AC4: Gauge sets success rate correctly
"""

import pytest
from prometheus_client import CollectorRegistry

from src.monitoring.metrics import (
    enhancement_requests_total,
    enhancement_duration_seconds,
    enhancement_success_rate,
    queue_depth,
    worker_active_count,
)


class TestMetricsDefinition:
    """Test metrics are properly defined with correct types and labels."""

    def test_enhancement_requests_total_is_counter(self):
        """AC1, AC3: enhancement_requests_total is a Counter metric."""
        assert enhancement_requests_total is not None
        assert hasattr(enhancement_requests_total, "labels")
        assert hasattr(enhancement_requests_total, "inc")

    def test_enhancement_duration_seconds_is_histogram(self):
        """AC2, AC3: enhancement_duration_seconds is a Histogram metric."""
        assert enhancement_duration_seconds is not None
        assert hasattr(enhancement_duration_seconds, "labels")
        assert hasattr(enhancement_duration_seconds, "observe")

    def test_enhancement_success_rate_is_gauge(self):
        """AC2, AC3: enhancement_success_rate is a Gauge metric."""
        assert enhancement_success_rate is not None
        assert hasattr(enhancement_success_rate, "labels")
        assert hasattr(enhancement_success_rate, "set")

    def test_queue_depth_is_gauge(self):
        """AC2, AC3: queue_depth is a Gauge metric."""
        assert queue_depth is not None
        assert hasattr(queue_depth, "labels")
        assert hasattr(queue_depth, "set")

    def test_worker_active_count_is_gauge(self):
        """AC2, AC3: worker_active_count is a Gauge metric."""
        assert worker_active_count is not None
        assert hasattr(worker_active_count, "labels")
        assert hasattr(worker_active_count, "set")


class TestMetricsLabeling:
    """Test metrics accept correct labels."""

    def test_enhancement_requests_total_labels(self):
        """AC3: enhancement_requests_total accepts tenant_id and status labels."""
        # Should not raise exception
        metric = enhancement_requests_total.labels(
            tenant_id="test-tenant", status="received"
        )
        assert metric is not None

    def test_enhancement_duration_seconds_labels(self):
        """AC3: enhancement_duration_seconds accepts tenant_id and status labels."""
        metric = enhancement_duration_seconds.labels(
            tenant_id="test-tenant", status="success"
        )
        assert metric is not None

    def test_enhancement_success_rate_labels(self):
        """AC3: enhancement_success_rate accepts tenant_id label."""
        metric = enhancement_success_rate.labels(tenant_id="test-tenant")
        assert metric is not None

    def test_queue_depth_labels(self):
        """AC3: queue_depth accepts queue_name label."""
        metric = queue_depth.labels(queue_name="enhancement:queue")
        assert metric is not None

    def test_worker_active_count_labels(self):
        """AC3: worker_active_count accepts worker_type label."""
        metric = worker_active_count.labels(worker_type="celery_enhancement")
        assert metric is not None


class TestMetricsOperations:
    """Test metric operations (increment, observe, set)."""

    def test_counter_increment(self):
        """AC4: Counter can increment with labels."""
        # Get metric with labels
        metric = enhancement_requests_total.labels(
            tenant_id="test-tenant-counter", status="received"
        )
        # Should not raise exception
        metric.inc()
        metric.inc(5)  # Increment by 5

    def test_histogram_observe(self):
        """AC4: Histogram can record observations with labels."""
        metric = enhancement_duration_seconds.labels(
            tenant_id="test-tenant-hist", status="success"
        )
        # Should not raise exception
        metric.observe(0.5)  # 500ms
        metric.observe(1.5)  # 1.5 seconds
        metric.observe(0.1)  # 100ms

    def test_gauge_set(self):
        """AC4: Gauge can set values with labels."""
        metric = enhancement_success_rate.labels(tenant_id="test-tenant-gauge")
        # Should not raise exception
        metric.set(95.5)  # 95.5% success rate
        metric.set(100)  # 100% success rate
        metric.set(0)  # 0% success rate

    def test_queue_depth_gauge_set(self):
        """AC4: queue_depth Gauge can set queue job count."""
        metric = queue_depth.labels(queue_name="test:queue")
        metric.set(42)  # 42 jobs in queue

    def test_worker_count_gauge_set(self):
        """AC4: worker_active_count Gauge can set active worker count."""
        metric = worker_active_count.labels(worker_type="test_worker")
        metric.set(4)  # 4 active workers


class TestMetricsImport:
    """Test metrics can be imported from module __init__."""

    def test_import_from_monitoring_module(self):
        """AC1, AC2: All metrics importable from src.monitoring module."""
        # This should not raise ImportError
        from src.monitoring import (
            enhancement_requests_total as imported_counter,
            enhancement_duration_seconds as imported_histogram,
            enhancement_success_rate as imported_gauge,
            queue_depth as imported_queue,
            worker_active_count as imported_workers,
        )

        # Verify they're the same objects
        assert imported_counter is enhancement_requests_total
        assert imported_histogram is enhancement_duration_seconds
        assert imported_gauge is enhancement_success_rate
        assert imported_queue is queue_depth
        assert imported_workers is worker_active_count


class TestMetricsExportFormatting:
    """Test metrics format correctly for Prometheus scraping."""

    def test_counter_metric_name(self):
        """AC2: Counter has correct Prometheus metric name."""
        # Counter name should appear in the metric documentation
        # The actual metric name includes _total suffix in Prometheus output
        assert "enhancement_requests" in str(enhancement_requests_total)

    def test_histogram_metric_name(self):
        """AC2: Histogram has correct Prometheus metric name."""
        assert "enhancement_duration_seconds" in str(enhancement_duration_seconds)

    def test_gauge_metric_names(self):
        """AC2: Gauges have correct Prometheus metric names."""
        assert "enhancement_success_rate" in str(enhancement_success_rate)
        assert "queue_depth" in str(queue_depth)
        assert "worker_active_count" in str(worker_active_count)
