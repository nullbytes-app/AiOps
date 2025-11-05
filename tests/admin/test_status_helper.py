"""
Unit tests for status_helper.py - System health status calculation.

Tests cover:
- AC#1: System status indicator logic (Healthy/Degraded/Down)
- AC#7: Status emoji icons (✅/⚠️/❌)
- Edge cases: connection failures, threshold boundaries
"""

import pytest
from unittest.mock import MagicMock, patch

from admin.utils.status_helper import get_system_status, get_cached_system_status


class TestGetSystemStatus:
    """Test suite for get_system_status function."""

    def test_healthy_status_all_checks_pass(self):
        """Test healthy status when all checks pass."""
        status, emoji, message = get_system_status(
            db_connected=True, redis_connected=True, success_rate=95.0, queue_depth=50
        )

        assert status == "Healthy"
        assert emoji == "✅"
        assert message == "All systems operational"

    def test_degraded_status_low_success_rate(self):
        """Test degraded status when success rate below 80% threshold."""
        status, emoji, message = get_system_status(
            db_connected=True, redis_connected=True, success_rate=75.0, queue_depth=50
        )

        assert status == "Degraded"
        assert emoji == "⚠️"
        assert "Success rate below threshold (75.0% < 80%)" in message

    def test_degraded_status_high_queue_depth(self):
        """Test degraded status when queue depth exceeds 100."""
        status, emoji, message = get_system_status(
            db_connected=True, redis_connected=True, success_rate=95.0, queue_depth=150
        )

        assert status == "Degraded"
        assert emoji == "⚠️"
        assert "Queue depth exceeds limit (150 > 100)" in message

    def test_degraded_status_multiple_issues(self):
        """Test degraded status with multiple degradation reasons."""
        status, emoji, message = get_system_status(
            db_connected=True, redis_connected=True, success_rate=70.0, queue_depth=120
        )

        assert status == "Degraded"
        assert emoji == "⚠️"
        # Both reasons should be in message
        assert "Success rate below threshold" in message
        assert "Queue depth exceeds limit" in message

    def test_down_status_database_disconnected(self):
        """Test down status when database connection fails."""
        status, emoji, message = get_system_status(
            db_connected=False, redis_connected=True, success_rate=95.0, queue_depth=50
        )

        assert status == "Down"
        assert emoji == "❌"
        assert message == "Database connection failed"

    def test_down_status_redis_disconnected(self):
        """Test down status when Redis connection fails."""
        status, emoji, message = get_system_status(
            db_connected=True, redis_connected=False, success_rate=95.0, queue_depth=50
        )

        assert status == "Down"
        assert emoji == "❌"
        assert message == "Redis connection failed"

    def test_down_status_takes_precedence_over_degraded(self):
        """Test that down status takes precedence over degraded conditions."""
        status, emoji, message = get_system_status(
            db_connected=False, redis_connected=True, success_rate=70.0, queue_depth=150
        )

        # Should be Down (not Degraded), even though metrics are degraded
        assert status == "Down"
        assert emoji == "❌"

    def test_success_rate_exactly_80_percent_is_healthy(self):
        """Test boundary condition: 80% success rate is healthy (not degraded)."""
        status, emoji, message = get_system_status(
            db_connected=True, redis_connected=True, success_rate=80.0, queue_depth=50
        )

        assert status == "Healthy"
        assert emoji == "✅"

    def test_queue_depth_exactly_100_is_healthy(self):
        """Test boundary condition: 100 queue depth is healthy (not degraded)."""
        status, emoji, message = get_system_status(
            db_connected=True, redis_connected=True, success_rate=95.0, queue_depth=100
        )

        assert status == "Healthy"
        assert emoji == "✅"

    def test_none_metrics_ignored(self):
        """Test that None metrics are skipped in health checks."""
        status, emoji, message = get_system_status(
            db_connected=True, redis_connected=True, success_rate=None, queue_depth=None
        )

        # Should be healthy when connections are up and metrics are None
        assert status == "Healthy"
        assert emoji == "✅"

    @patch("admin.utils.status_helper.test_database_connection")
    def test_auto_check_database_connection(self, mock_db_test):
        """Test auto-checking database connection when not provided."""
        mock_db_test.return_value = (True, "Connected")

        status, emoji, message = get_system_status(
            db_connected=None,  # Auto-check
            redis_connected=True,
            success_rate=95.0,
            queue_depth=50,
        )

        mock_db_test.assert_called_once()
        assert status == "Healthy"

    @patch("admin.utils.redis_helper.test_redis_connection")
    @patch("admin.utils.status_helper.test_database_connection")
    def test_auto_check_redis_connection(self, mock_db_test, mock_redis_test):
        """Test auto-checking Redis connection when not provided."""
        mock_db_test.return_value = (True, "DB Connected")
        mock_redis_test.return_value = (True, "Redis Connected")

        status, emoji, message = get_system_status(
            db_connected=None,  # Auto-check
            redis_connected=None,  # Auto-check
            success_rate=95.0,
            queue_depth=50,
        )

        mock_redis_test.assert_called_once()
        assert status == "Healthy"


class TestGetCachedSystemStatus:
    """Test suite for cached version of get_system_status."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear Streamlit cache before each test."""
        import streamlit as st

        st.cache_data.clear()
        yield
        st.cache_data.clear()

    def test_cached_function_returns_same_result(self):
        """Test that cached function returns same result as uncached."""
        cached_result = get_cached_system_status(
            db_connected=True, redis_connected=True, success_rate=95.0, queue_depth=50
        )

        uncached_result = get_system_status(
            db_connected=True, redis_connected=True, success_rate=95.0, queue_depth=50
        )

        assert cached_result == uncached_result

    def test_cache_works_across_calls(self):
        """Test that cache persists result across multiple calls."""
        # First call
        result1 = get_cached_system_status(
            db_connected=True, redis_connected=True, success_rate=95.0, queue_depth=50
        )

        # Second call (should use cache)
        result2 = get_cached_system_status(
            db_connected=True, redis_connected=True, success_rate=95.0, queue_depth=50
        )

        # Results should be identical (from cache)
        assert result1 == result2
        assert result1[0] == "Healthy"
