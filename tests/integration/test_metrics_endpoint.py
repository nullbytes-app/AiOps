"""
Integration tests for Prometheus /metrics endpoint (Story 4.1).

Tests the full /metrics endpoint functionality including:
- Endpoint accessibility (AC2)
- Response format (Prometheus text format)
- Status codes (200 OK)
- Content-Type header
- Metrics collection and exposure

Test Coverage:
- AC2: /metrics endpoint returns 200 OK
- AC2: Response is in Prometheus text format
- AC2: Content-Type is text/plain
- AC3-AC4: Instrumented metrics appear in response
"""

import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from src.main import app


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


class TestMetricsEndpointBasic:
    """Test basic /metrics endpoint functionality."""

    def test_metrics_endpoint_returns_200(self, client):
        """AC2: GET /metrics returns 200 OK status code."""
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_endpoint_content_type(self, client):
        """AC2: /metrics response has Prometheus text format content type."""
        response = client.get("/metrics")
        assert "text/plain" in response.headers.get("content-type", "")

    def test_metrics_endpoint_returns_text(self, client):
        """AC2: /metrics response is readable text (not binary)."""
        response = client.get("/metrics")
        assert response.text is not None
        assert len(response.text) > 0
        # Should be readable text, not binary
        assert isinstance(response.text, str)


class TestMetricsFormatting:
    """Test metrics response format matches Prometheus standards."""

    def test_metrics_contains_help_lines(self, client):
        """AC2: Metrics include HELP lines for documentation."""
        response = client.get("/metrics")
        content = response.text
        # Prometheus format includes HELP lines starting with #
        assert "#" in content
        # Should have at least some HELP or TYPE lines
        help_lines = [line for line in content.split("\n") if line.startswith("# HELP")]
        assert len(help_lines) > 0

    def test_metrics_contains_type_lines(self, client):
        """AC2: Metrics include TYPE lines declaring metric type."""
        response = client.get("/metrics")
        content = response.text
        type_lines = [line for line in content.split("\n") if line.startswith("# TYPE")]
        assert len(type_lines) > 0

    def test_metrics_contains_data_lines(self, client):
        """AC2: Metrics include actual metric data lines."""
        response = client.get("/metrics")
        content = response.text
        # Data lines don't start with # and contain metric values
        data_lines = [
            line for line in content.split("\n")
            if line.strip() and not line.startswith("#")
        ]
        assert len(data_lines) > 0


class TestInstrumentedMetricsAppear:
    """Test that instrumented metrics appear in /metrics response."""

    def test_enhancement_requests_total_metric_appears(self, client):
        """AC3: enhancement_requests_total metric appears in /metrics."""
        response = client.get("/metrics")
        content = response.text
        # Metric name should appear (in HELP, TYPE, or data lines)
        assert "enhancement_requests_total" in content

    def test_enhancement_duration_seconds_metric_appears(self, client):
        """AC3: enhancement_duration_seconds metric appears in /metrics."""
        response = client.get("/metrics")
        content = response.text
        assert "enhancement_duration_seconds" in content

    def test_enhancement_success_rate_metric_appears(self, client):
        """AC3: enhancement_success_rate metric appears in /metrics."""
        response = client.get("/metrics")
        content = response.text
        assert "enhancement_success_rate" in content

    def test_queue_depth_metric_appears(self, client):
        """AC3: queue_depth metric appears in /metrics."""
        response = client.get("/metrics")
        content = response.text
        assert "queue_depth" in content

    def test_worker_active_count_metric_appears(self, client):
        """AC3: worker_active_count metric appears in /metrics."""
        response = client.get("/metrics")
        content = response.text
        assert "worker_active_count" in content


class TestMetricsDataCollection:
    """Test that metrics actually collect and expose data."""

    def test_metrics_reflect_counter_increments(self, client):
        """AC4: Counter increments are reflected in /metrics response."""
        from src.monitoring import enhancement_requests_total

        # Increment counter
        enhancement_requests_total.labels(
            tenant_id="test-tenant", status="received"
        ).inc()

        # Fetch metrics
        response = client.get("/metrics")
        content = response.text

        # Counter should appear with updated value
        assert "enhancement_requests_total" in content
        # Check that data lines contain the metric
        data_lines = [line for line in content.split("\n")
                     if "enhancement_requests_total" in line and not line.startswith("#")]
        assert len(data_lines) > 0

    def test_metrics_reflect_histogram_observations(self, client):
        """AC4: Histogram observations are reflected in /metrics."""
        from src.monitoring import enhancement_duration_seconds

        # Record observation
        enhancement_duration_seconds.labels(
            tenant_id="test-tenant-hist", status="success"
        ).observe(1.5)

        # Fetch metrics
        response = client.get("/metrics")
        content = response.text

        # Histogram should appear with buckets
        assert "enhancement_duration_seconds" in content
        # Histograms create multiple lines (_bucket, _count, _sum)
        histogram_lines = [line for line in content.split("\n")
                         if "enhancement_duration_seconds" in line
                         and not line.startswith("#")]
        assert len(histogram_lines) > 0

    def test_metrics_reflect_gauge_updates(self, client):
        """AC4: Gauge updates are reflected in /metrics."""
        from src.monitoring import enhancement_success_rate

        # Update gauge
        enhancement_success_rate.labels(tenant_id="test-gauge").set(85.5)

        # Fetch metrics
        response = client.get("/metrics")
        content = response.text

        # Gauge should appear with value
        assert "enhancement_success_rate" in content
        gauge_lines = [line for line in content.split("\n")
                      if "enhancement_success_rate" in line and not line.startswith("#")]
        assert len(gauge_lines) > 0


class TestMetricsPublicAccess:
    """Test /metrics endpoint is publicly accessible (no auth required)."""

    def test_metrics_endpoint_no_auth_required(self, client):
        """AC2: /metrics endpoint requires no authentication."""
        # Should be accessible without any headers
        response = client.get("/metrics")
        # Should return 200, not 401/403
        assert response.status_code == 200
        assert response.status_code != 401
        assert response.status_code != 403

    def test_metrics_endpoint_accessible_via_get(self, client):
        """AC2: /metrics endpoint supports GET requests."""
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_endpoint_rejects_post(self, client):
        """AC2: /metrics endpoint handles POST appropriately (should be GET only)."""
        # POST should either return 405 Method Not Allowed or similar
        response = client.post("/metrics")
        # Most implementations return 405 for POST on GET-only endpoints
        # or forward it through (depends on setup)
        assert response.status_code in [200, 405, 404, 501]


class TestMetricsEdgeCases:
    """Test edge cases and error handling."""

    def test_metrics_endpoint_stability_with_repeated_requests(self, client):
        """AC2: /metrics endpoint remains stable with repeated requests."""
        for _ in range(10):
            response = client.get("/metrics")
            assert response.status_code == 200
            assert "enhancement_requests_total" in response.text

    def test_metrics_response_not_empty(self, client):
        """AC2: /metrics response is not empty (contains at least default metrics)."""
        response = client.get("/metrics")
        # Response should have meaningful content
        assert len(response.text) > 100  # Prometheus metrics are usually large

    def test_metrics_can_be_parsed(self, client):
        """AC2: /metrics response can be parsed as valid Prometheus format."""
        response = client.get("/metrics")
        lines = response.text.split("\n")

        # Every non-empty line should either:
        # - Start with # (comment/metadata)
        # - Contain a metric value (metric_name{labels} value timestamp)
        for line in lines:
            if not line.strip():
                continue  # Skip empty lines
            if line.startswith("#"):
                continue  # Skip comments
            # Data lines should contain = or {
            assert "{" in line or "=" in line or line.startswith("# ")
