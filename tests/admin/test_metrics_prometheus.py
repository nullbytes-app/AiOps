"""
Unit tests for Prometheus integration in metrics_helper.py (Story 6.6).

Tests cover:
- fetch_prometheus_range_query() with mocked httpx.get()
- Time-series query functions (queue, success rate, latency)
- Chart creation with Plotly
- Error handling and fallback to cached data
- Data downsampling for performance
- Time range conversion logic
"""

import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import httpx
import pandas as pd
import plotly.graph_objects as go
import pytest
import streamlit as st

from admin.utils.metrics_helper import (
    _get_time_range_params,
    create_timeseries_chart,
    downsample_timeseries,
    fetch_latency_timeseries,
    fetch_prometheus_range_query,
    fetch_queue_depth_timeseries,
    fetch_success_rate_timeseries,
)


# Pytest fixture to clear Streamlit cache before each test
@pytest.fixture(autouse=True)
def clear_streamlit_cache():
    """Clear Streamlit cache before each test to ensure isolation."""
    st.cache_data.clear()
    st.cache_resource.clear()
    # Clear session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    yield
    # Clear after test
    st.cache_data.clear()
    st.cache_resource.clear()


class TestFetchPrometheusRangeQuery:
    """Test fetch_prometheus_range_query() function."""

    def test_successful_query(self):
        """Test successful Prometheus query with valid response."""
        # Mock response data
        mock_response = {
            "status": "success",
            "data": {
                "result": [
                    {
                        "metric": {"__name__": "ai_agents_queue_depth"},
                        "values": [
                            [1730678400, "12"],  # Unix timestamp, value as string
                            [1730679300, "15"],
                            [1730680200, "18"],
                        ],
                    }
                ]
            },
        }

        # Mock httpx.Client.get()
        with patch("admin.utils.metrics_helper.httpx.Client") as mock_client:
            mock_get = MagicMock()
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.raise_for_status = MagicMock()
            mock_client.return_value.__enter__.return_value.get = mock_get

            start_time = datetime.utcnow() - timedelta(hours=1)
            end_time = datetime.utcnow()

            data, unavailable = fetch_prometheus_range_query(
                query="ai_agents_queue_depth",
                start_time=start_time,
                end_time=end_time,
                step="1m",
            )

            # Verify results
            assert unavailable is False
            assert len(data) == 3
            assert data[0]["value"] == 12.0
            assert data[1]["value"] == 15.0
            assert data[2]["value"] == 18.0
            assert isinstance(data[0]["timestamp"], datetime)

            # Verify request parameters
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "params" in call_args.kwargs
            params = call_args.kwargs["params"]
            assert params["query"] == "ai_agents_queue_depth"
            assert params["step"] == "1m"

    def test_connection_error_with_cached_data(self):
        """Test connection error falls back to cached data."""
        # Pre-populate cache
        cached_data = [
            {"timestamp": datetime.utcnow(), "value": 42.0},
        ]
        cache_key = "cached_prom_test_query_2025-11-04T00:00:00_2025-11-04T01:00:00"
        st.session_state[cache_key] = cached_data

        # Mock connection error
        with patch("admin.utils.metrics_helper.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = (
                httpx.ConnectError("Connection refused")
            )

            start_time = datetime(2025, 11, 4, 0, 0, 0)
            end_time = datetime(2025, 11, 4, 1, 0, 0)

            data, unavailable = fetch_prometheus_range_query(
                query="test_query",
                start_time=start_time,
                end_time=end_time,
                step="1m",
            )

            # Verify fallback to cached data
            assert unavailable is True
            assert len(data) == 1
            assert data[0]["value"] == 42.0

    def test_timeout_exception(self):
        """Test timeout exception handled gracefully."""
        with patch("admin.utils.metrics_helper.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = (
                httpx.TimeoutException("Request timeout")
            )

            start_time = datetime.utcnow() - timedelta(hours=1)
            end_time = datetime.utcnow()

            data, unavailable = fetch_prometheus_range_query(
                query="test_query",
                start_time=start_time,
                end_time=end_time,
                step="1m",
            )

            # Verify graceful handling (returns empty list, unavailable=True)
            assert unavailable is True
            assert data == []

    def test_empty_result_from_prometheus(self):
        """Test empty result array from Prometheus query."""
        mock_response = {"status": "success", "data": {"result": []}}

        with patch("admin.utils.metrics_helper.httpx.Client") as mock_client:
            mock_get = MagicMock()
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.raise_for_status = MagicMock()
            mock_client.return_value.__enter__.return_value.get = mock_get

            start_time = datetime.utcnow() - timedelta(hours=1)
            end_time = datetime.utcnow()

            data, unavailable = fetch_prometheus_range_query(
                query="missing_metric",
                start_time=start_time,
                end_time=end_time,
                step="1m",
            )

            # Verify empty result handled
            assert unavailable is False
            assert data == []

    def test_prometheus_error_status(self):
        """Test Prometheus API returns error status."""
        mock_response = {"status": "error", "errorType": "bad_data"}

        with patch("admin.utils.metrics_helper.httpx.Client") as mock_client:
            mock_get = MagicMock()
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.raise_for_status = MagicMock()
            mock_client.return_value.__enter__.return_value.get = mock_get

            start_time = datetime.utcnow() - timedelta(hours=1)
            end_time = datetime.utcnow()

            data, unavailable = fetch_prometheus_range_query(
                query="invalid_query",
                start_time=start_time,
                end_time=end_time,
                step="1m",
            )

            # Verify error handled (caught by generic Exception handler)
            # unavailable will be False if no cached data exists
            assert data == []
            # Check unavailable is boolean
            assert isinstance(unavailable, bool)


class TestTimeRangeParams:
    """Test _get_time_range_params() helper function."""

    def test_1h_time_range(self):
        """Test 1 hour time range conversion."""
        start, end, step = _get_time_range_params("1h")

        assert step == "1m"
        assert (end - start).total_seconds() == 3600  # 1 hour

    def test_6h_time_range(self):
        """Test 6 hour time range conversion."""
        start, end, step = _get_time_range_params("6h")

        assert step == "5m"
        assert (end - start).total_seconds() == 21600  # 6 hours

    def test_24h_time_range(self):
        """Test 24 hour time range conversion (default)."""
        start, end, step = _get_time_range_params("24h")

        assert step == "15m"
        assert (end - start).total_seconds() == 86400  # 24 hours

    def test_7d_time_range(self):
        """Test 7 day time range conversion."""
        start, end, step = _get_time_range_params("7d")

        assert step == "1h"
        assert (end - start).total_seconds() == 604800  # 7 days

    def test_unknown_time_range_defaults_to_24h(self):
        """Test unknown time range defaults to 24h."""
        start, end, step = _get_time_range_params("invalid")

        assert step == "15m"  # Same as 24h
        assert (end - start).total_seconds() == 86400  # 24 hours


class TestTimeseriesQueryFunctions:
    """Test metric-specific timeseries query functions."""

    @patch("admin.utils.metrics_helper.fetch_prometheus_range_query")
    def test_fetch_queue_depth_timeseries(self, mock_fetch):
        """Test queue depth timeseries query."""
        mock_fetch.return_value = (
            [{"timestamp": datetime.utcnow(), "value": 42.0}],
            False,
        )

        data, unavailable = fetch_queue_depth_timeseries("24h")

        # Verify correct query sent
        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args[0]
        assert call_args[0] == "ai_agents_queue_depth"
        assert call_args[3] == "15m"  # 24h step

        assert len(data) == 1
        assert data[0]["value"] == 42.0
        assert unavailable is False

    @patch("admin.utils.metrics_helper.fetch_prometheus_range_query")
    def test_fetch_success_rate_timeseries(self, mock_fetch):
        """Test success rate timeseries query."""
        mock_fetch.return_value = (
            [{"timestamp": datetime.utcnow(), "value": 95.5}],
            False,
        )

        data, unavailable = fetch_success_rate_timeseries("6h")

        # Verify correct query sent
        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args[0]
        assert call_args[0] == "ai_agents_enhancement_success_rate"
        assert call_args[3] == "5m"  # 6h step

        assert data[0]["value"] == 95.5
        assert unavailable is False

    @patch("admin.utils.metrics_helper.fetch_prometheus_range_query")
    def test_fetch_latency_timeseries_p50(self, mock_fetch):
        """Test P50 latency timeseries query."""
        # Mock returns latency in seconds
        mock_fetch.return_value = (
            [{"timestamp": datetime.utcnow(), "value": 1.250}],  # 1.25 seconds
            False,
        )

        data, unavailable = fetch_latency_timeseries("1h", "p50")

        # Verify histogram_quantile query
        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args[0]
        query = call_args[0]
        assert "histogram_quantile(0.50" in query
        assert "rate(ai_agents_enhancement_latency_seconds_bucket[5m])" in query
        assert call_args[3] == "1m"  # 1h step

        # Verify latency converted from seconds to milliseconds
        assert data[0]["value"] == 1250.0  # 1.25s * 1000 = 1250ms

    @patch("admin.utils.metrics_helper.fetch_prometheus_range_query")
    def test_fetch_latency_timeseries_p95(self, mock_fetch):
        """Test P95 latency timeseries query."""
        mock_fetch.return_value = (
            [{"timestamp": datetime.utcnow(), "value": 2.500}],  # 2.5 seconds
            False,
        )

        data, unavailable = fetch_latency_timeseries("24h", "p95")

        # Verify histogram_quantile query with 0.95
        call_args = mock_fetch.call_args[0]
        query = call_args[0]
        assert "histogram_quantile(0.95" in query

        # Verify conversion to milliseconds
        assert data[0]["value"] == 2500.0  # 2.5s * 1000

    @patch("admin.utils.metrics_helper.fetch_prometheus_range_query")
    def test_fetch_latency_timeseries_p99(self, mock_fetch):
        """Test P99 latency timeseries query."""
        mock_fetch.return_value = (
            [{"timestamp": datetime.utcnow(), "value": 3.750}],  # 3.75 seconds
            False,
        )

        data, unavailable = fetch_latency_timeseries("7d", "p99")

        # Verify histogram_quantile query with 0.99
        call_args = mock_fetch.call_args[0]
        query = call_args[0]
        assert "histogram_quantile(0.99" in query

        # Verify conversion to milliseconds
        assert data[0]["value"] == 3750.0  # 3.75s * 1000


class TestDownsamplingAndPerformance:
    """Test data downsampling for performance (AC#8)."""

    def test_downsample_no_change_under_threshold(self):
        """Test downsampling doesn't change data under 1000 points."""
        data = [
            {"timestamp": datetime.utcnow() - timedelta(minutes=i), "value": float(i)}
            for i in range(500)
        ]

        downsampled = downsample_timeseries(data, max_points=1000)

        # Should return original data unchanged
        assert len(downsampled) == 500
        assert downsampled[0]["value"] == 0.0

    def test_downsample_reduces_points_over_threshold(self):
        """Test downsampling reduces data points over 1000."""
        # Create 2000 data points
        data = [
            {"timestamp": datetime.utcnow() - timedelta(minutes=i), "value": float(i)}
            for i in range(2000)
        ]

        downsampled = downsample_timeseries(data, max_points=1000)

        # Should reduce to approximately 1000 points (allow small tolerance)
        assert len(downsampled) < 2000
        assert len(downsampled) <= 1001  # Allow 1001 due to rounding in resample

    def test_chart_performance_with_1000_points(self):
        """Test chart render time < 2 seconds for 1000 points (AC#8)."""
        # Generate 1000 data points
        data = [
            {"timestamp": datetime.utcnow() - timedelta(seconds=i), "value": float(i)}
            for i in range(1000)
        ]

        # Measure chart creation time
        start_time = time.time()
        fig = create_timeseries_chart(data, "Test Chart", "Value", "#1f77b4")
        render_time = time.time() - start_time

        # Verify render time < 2 seconds (AC#8 requirement)
        assert render_time < 2.0, f"Chart render time {render_time:.2f}s exceeded 2s limit"
        assert isinstance(fig, go.Figure)


class TestCreateTimeseriesChart:
    """Test create_timeseries_chart() Plotly function."""

    def test_chart_creation_basic(self):
        """Test basic chart creation with valid data."""
        data = [
            {"timestamp": datetime(2025, 11, 4, 10, 0, 0), "value": 42.0},
            {"timestamp": datetime(2025, 11, 4, 10, 15, 0), "value": 45.0},
            {"timestamp": datetime(2025, 11, 4, 10, 30, 0), "value": 40.0},
        ]

        fig = create_timeseries_chart(data, "Queue Depth", "Jobs", "#1f77b4")

        # Verify figure properties
        assert isinstance(fig, go.Figure)
        assert fig.layout.title.text == "Queue Depth"
        assert fig.layout.xaxis.title.text == "Time"
        assert fig.layout.yaxis.title.text == "Jobs"
        assert fig.layout.height == 300
        assert fig.layout.showlegend is False  # Single-line chart

        # Verify trace configuration
        assert len(fig.data) == 1
        assert fig.data[0].mode == "lines"
        assert fig.data[0].line.color == "#1f77b4"
        assert fig.data[0].hovertemplate == "%{y:.1f}<extra></extra>"

    def test_chart_empty_data_handling(self):
        """Test chart handles empty data gracefully."""
        data = []

        fig = create_timeseries_chart(data, "Empty Chart", "Value", "#ff0000")

        # Should create chart with placeholder data
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1

    def test_chart_interactivity_settings(self):
        """Test chart has correct interactivity settings (AC#4)."""
        data = [{"timestamp": datetime.utcnow(), "value": 10.0}]

        fig = create_timeseries_chart(data, "Test", "Value", "#000000")

        # Verify interactivity features
        assert fig.layout.xaxis.rangeslider.visible is False  # Cleaner x-axis
        # Hover, zoom, pan enabled by default in plotly

    def test_chart_downsampling_applied(self):
        """Test chart applies downsampling to large datasets."""
        # Create 2000 data points
        data = [
            {"timestamp": datetime.utcnow() - timedelta(seconds=i), "value": float(i)}
            for i in range(2000)
        ]

        fig = create_timeseries_chart(data, "Large Dataset", "Value", "#00ff00")

        # Chart should be created successfully
        assert isinstance(fig, go.Figure)
        # Downsampling should keep data under 1000 points
        assert len(fig.data[0].x) <= 1000
