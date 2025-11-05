"""
Unit tests for metrics_helper.py - Dashboard metrics query functions.

Tests cover:
- AC#2: Key metrics queries (queue depth, success rate, P95 latency, active workers)
- AC#3: Recent failures query
- Caching behavior and performance optimization
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch
import pytest

from admin.utils.metrics_helper import (
    get_queue_depth,
    get_success_rate_24h,
    get_p95_latency,
    get_active_workers,
    get_recent_failures,
    get_metric_delta,
)


@pytest.fixture(autouse=True)
def clear_streamlit_cache():
    """Clear Streamlit cache before and after each test."""
    import streamlit as st

    st.cache_data.clear()
    yield
    st.cache_data.clear()


class TestGetQueueDepth:
    """Test suite for get_queue_depth function."""

    @patch("admin.utils.redis_helper.get_redis_queue_depth")
    def test_returns_queue_depth_from_redis(self, mock_redis_depth):
        """Test getting queue depth from Redis."""
        mock_redis_depth.return_value = 42

        result = get_queue_depth()

        assert result == 42
        mock_redis_depth.assert_called_once()

    @patch("admin.utils.redis_helper.get_redis_queue_depth")
    def test_returns_zero_on_error(self, mock_redis_depth):
        """Test returning 0 when Redis query fails."""
        mock_redis_depth.side_effect = Exception("Redis connection error")

        result = get_queue_depth()

        assert result == 0


class TestGetSuccessRate24h:
    """Test suite for get_success_rate_24h function."""

    @patch("admin.utils.metrics_helper.get_db_session")
    def test_calculates_success_rate_correctly(self, mock_session):
        """Test success rate calculation: completed / total * 100."""
        # Mock database session and query results
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        # Mock query chain: completed count = 95, total count = 100
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.scalar.side_effect = [95, 100]  # First call: completed, second: total

        mock_db.query.return_value = mock_query

        result = get_success_rate_24h()

        assert result == 95.0  # 95/100 * 100 = 95.0%

    @patch("admin.utils.metrics_helper.get_db_session")
    def test_returns_zero_when_no_data(self, mock_session):
        """Test returning 0% when no data available."""
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.scalar.side_effect = [0, 0]  # No completed, no total

        mock_db.query.return_value = mock_query

        result = get_success_rate_24h()

        assert result == 0.0

    @patch("admin.utils.metrics_helper.get_db_session")
    def test_handles_database_error(self, mock_session):
        """Test error handling when database query fails."""
        mock_session.side_effect = Exception("Database connection error")

        result = get_success_rate_24h()

        assert result == 0.0


class TestGetP95Latency:
    """Test suite for get_p95_latency function."""

    @patch("admin.utils.metrics_helper.get_db_session")
    def test_returns_p95_latency_in_milliseconds(self, mock_session):
        """Test P95 latency calculation returns milliseconds."""
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        # Mock percentile query result: 2340.5 ms
        mock_result = Mock()
        mock_result.scalar.return_value = 2340.5

        mock_db.execute.return_value = mock_result

        result = get_p95_latency()

        assert result == 2340  # Rounded to integer (Python rounds 0.5 down to even number)

    @patch("admin.utils.metrics_helper.get_db_session")
    def test_returns_zero_when_no_data(self, mock_session):
        """Test returning 0 when no latency data available."""
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        mock_result = Mock()
        mock_result.scalar.return_value = None  # No data

        mock_db.execute.return_value = mock_result

        result = get_p95_latency()

        assert result == 0

    @patch("admin.utils.metrics_helper.get_db_session")
    def test_handles_database_error(self, mock_session):
        """Test error handling when database query fails."""
        mock_session.side_effect = Exception("Database error")

        result = get_p95_latency()

        assert result == 0


class TestGetActiveWorkers:
    """Test suite for get_active_workers function."""

    @patch("admin.utils.metrics_helper.get_db_session")
    def test_returns_active_worker_count(self, mock_session):
        """Test getting active worker count from pending jobs."""
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = 4  # 4 pending jobs

        mock_db.query.return_value = mock_query

        result = get_active_workers()

        assert result == 4

    @patch("admin.utils.metrics_helper.get_db_session")
    def test_caps_worker_count_at_10(self, mock_session):
        """Test capping worker count at 10 for display purposes."""
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = 25  # More than 10 pending

        mock_db.query.return_value = mock_query

        result = get_active_workers()

        assert result == 10  # Capped at 10

    @patch("admin.utils.metrics_helper.get_db_session")
    def test_handles_database_error(self, mock_session):
        """Test error handling when database query fails."""
        mock_session.side_effect = Exception("Database error")

        result = get_active_workers()

        assert result == 0


class TestGetRecentFailures:
    """Test suite for get_recent_failures function."""

    @patch("admin.utils.metrics_helper.get_db_session")
    def test_returns_recent_failures_list(self, mock_session):
        """Test getting list of recent failed enhancements."""
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        # Mock failure records
        mock_failure = Mock()
        mock_failure.ticket_id = "SD-12345"
        mock_failure.tenant_id = "tenant-a"
        mock_failure.error_message = "Connection timeout"
        mock_failure.created_at = datetime.utcnow() - timedelta(minutes=5)

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_failure]

        mock_db.query.return_value = mock_query

        result = get_recent_failures(limit=10)

        assert len(result) == 1
        assert result[0]["ticket_id"] == "SD-12345"
        assert result[0]["tenant_id"] == "tenant-a"
        assert "Connection timeout" in result[0]["error_message"]
        assert result[0]["time_ago"].endswith("m ago")

    @patch("admin.utils.metrics_helper.get_db_session")
    def test_truncates_long_error_messages(self, mock_session):
        """Test truncating error messages longer than 100 characters."""
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        # Mock failure with long error
        long_error = "A" * 150  # 150 characters
        mock_failure = Mock()
        mock_failure.ticket_id = "SD-12345"
        mock_failure.tenant_id = "tenant-a"
        mock_failure.error_message = long_error
        mock_failure.created_at = datetime.utcnow()

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_failure]

        mock_db.query.return_value = mock_query

        result = get_recent_failures(limit=10)

        # Error message should be truncated with "..."
        assert len(result[0]["error_message"]) == 103  # 100 chars + "..."
        assert result[0]["error_message"].endswith("...")
        # Full error should be preserved
        assert len(result[0]["error_full"]) == 150

    @patch("admin.utils.metrics_helper.get_db_session")
    def test_returns_empty_list_when_no_failures(self, mock_session):
        """Test returning empty list when no failures found."""
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        mock_db.query.return_value = mock_query

        result = get_recent_failures(limit=10)

        assert result == []

    @patch("admin.utils.metrics_helper.get_db_session")
    def test_handles_database_error(self, mock_session):
        """Test error handling when database query fails."""
        mock_session.side_effect = Exception("Database error")

        result = get_recent_failures(limit=10)

        assert result == []


class TestGetMetricDelta:
    """Test suite for get_metric_delta function."""

    def test_returns_none_for_mvp_placeholder(self):
        """Test that delta returns None in MVP implementation."""
        result = get_metric_delta("success_rate", 95.0)

        # MVP implementation returns None (placeholder)
        assert result is None

    def test_handles_errors_gracefully(self):
        """Test error handling in delta calculation."""
        # Should not raise exceptions
        result = get_metric_delta("invalid_metric", 0.0)

        assert result is None
