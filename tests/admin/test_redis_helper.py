"""
Unit tests for redis_helper.py - Redis connection and queue operations.

Tests cover:
- AC#4: Redis connection status testing
- Queue depth queries for dashboard metrics
- Error handling and timeouts
"""

import time
from unittest.mock import MagicMock, Mock, patch
import pytest
import redis

from admin.utils.redis_helper import (
    get_sync_redis_client,
    test_redis_connection,
    get_redis_queue_depth,
    get_redis_info,
    clear_redis_cache,
)


@pytest.fixture(autouse=True)
def clear_streamlit_cache():
    """Clear Streamlit cache before and after each test."""
    import streamlit as st

    st.cache_resource.clear()
    st.cache_data.clear()
    yield
    st.cache_resource.clear()
    st.cache_data.clear()


class TestGetSyncRedisClient:
    """Test suite for get_sync_redis_client function."""

    @patch("admin.utils.redis_helper.redis.Redis.from_url")
    @patch.dict("os.environ", {"AI_AGENTS_REDIS_URL": "redis://localhost:6379/1"})
    def test_creates_redis_client_successfully(self, mock_from_url):
        """Test creating Redis client with valid configuration."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_from_url.return_value = mock_client

        result = get_sync_redis_client()

        assert result is not None
        mock_from_url.assert_called_once()
        mock_client.ping.assert_called_once()

    @patch("admin.utils.redis_helper.redis.Redis.from_url")
    @patch.dict("os.environ", {"AI_AGENTS_REDIS_URL": "redis://localhost:6379/1"})
    def test_returns_none_on_connection_error(self, mock_from_url):
        """Test returning None when Redis connection fails."""
        mock_from_url.side_effect = redis.ConnectionError("Connection refused")

        result = get_sync_redis_client()

        assert result is None

    @patch("admin.utils.redis_helper.redis.Redis.from_url")
    @patch.dict("os.environ", {"AI_AGENTS_REDIS_URL": "redis://localhost:6379/1"})
    def test_uses_correct_timeout_settings(self, mock_from_url):
        """Test Redis client created with correct timeout settings."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_from_url.return_value = mock_client

        get_sync_redis_client()

        # Verify timeout settings in call
        call_kwargs = mock_from_url.call_args[1]
        assert call_kwargs["socket_connect_timeout"] == 2
        assert call_kwargs["socket_timeout"] == 2
        assert call_kwargs["decode_responses"] is True


class TestTestRedisConnection:
    """Test suite for test_redis_connection function."""

    @patch("admin.utils.redis_helper.get_sync_redis_client")
    def test_returns_success_with_response_time(self, mock_get_client):
        """Test returning success with connection response time."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_get_client.return_value = mock_client

        success, message = test_redis_connection()

        assert success is True
        assert "✅ Connected" in message
        assert "ms)" in message  # Response time included

    @patch("admin.utils.redis_helper.get_sync_redis_client")
    def test_returns_failure_when_client_unavailable(self, mock_get_client):
        """Test returning failure when Redis client creation fails."""
        mock_get_client.return_value = None

        success, message = test_redis_connection()

        assert success is False
        assert "❌" in message
        assert "client creation failed" in message.lower()

    @patch("admin.utils.redis_helper.get_sync_redis_client")
    def test_handles_connection_error(self, mock_get_client):
        """Test handling Redis connection error."""
        mock_client = Mock()
        mock_client.ping.side_effect = redis.ConnectionError("Connection refused")
        mock_get_client.return_value = mock_client

        success, message = test_redis_connection()

        assert success is False
        assert "❌" in message
        assert "Connection failed" in message

    @patch("admin.utils.redis_helper.get_sync_redis_client")
    def test_handles_timeout_error(self, mock_get_client):
        """Test handling Redis timeout error."""
        mock_client = Mock()
        mock_client.ping.side_effect = redis.TimeoutError("Timeout after 2s")
        mock_get_client.return_value = mock_client

        success, message = test_redis_connection()

        assert success is False
        assert "❌" in message
        assert "timeout" in message.lower()


class TestGetRedisQueueDepth:
    """Test suite for get_redis_queue_depth function."""

    @patch("admin.utils.redis_helper.get_sync_redis_client")
    def test_returns_queue_depth_from_llen(self, mock_get_client):
        """Test getting queue depth using llen() command."""
        mock_client = Mock()
        mock_client.llen.return_value = 42
        mock_get_client.return_value = mock_client

        result = get_redis_queue_depth("celery")

        assert result == 42
        mock_client.llen.assert_called_once_with("celery")

    @patch("admin.utils.redis_helper.get_sync_redis_client")
    def test_uses_default_celery_queue(self, mock_get_client):
        """Test using 'celery' as default queue name."""
        mock_client = Mock()
        mock_client.llen.return_value = 10
        mock_get_client.return_value = mock_client

        result = get_redis_queue_depth()  # No queue_name arg

        mock_client.llen.assert_called_once_with("celery")

    @patch("admin.utils.redis_helper.get_sync_redis_client")
    def test_returns_zero_when_client_unavailable(self, mock_get_client):
        """Test returning 0 when Redis client unavailable."""
        mock_get_client.return_value = None

        result = get_redis_queue_depth()

        assert result == 0

    @patch("admin.utils.redis_helper.get_sync_redis_client")
    def test_returns_zero_on_error(self, mock_get_client):
        """Test returning 0 when llen() fails."""
        mock_client = Mock()
        mock_client.llen.side_effect = redis.ConnectionError("Error")
        mock_get_client.return_value = mock_client

        result = get_redis_queue_depth()

        assert result == 0


class TestGetRedisInfo:
    """Test suite for get_redis_info function."""

    @patch("admin.utils.redis_helper.get_sync_redis_client")
    def test_returns_redis_server_info(self, mock_get_client):
        """Test getting Redis server information."""
        mock_client = Mock()
        mock_client.info.return_value = {
            "redis_version": "7.0.0",
            "used_memory_human": "2.50M",
            "connected_clients": 5,
            "total_commands_processed": 12345,
            "uptime_in_days": 10,
        }
        mock_get_client.return_value = mock_client

        result = get_redis_info()

        assert result["redis_version"] == "7.0.0"
        assert result["used_memory_human"] == "2.50M"
        assert result["connected_clients"] == 5

    @patch("admin.utils.redis_helper.get_sync_redis_client")
    def test_returns_empty_dict_when_client_unavailable(self, mock_get_client):
        """Test returning empty dict when Redis client unavailable."""
        mock_get_client.return_value = None

        result = get_redis_info()

        assert result == {}

    @patch("admin.utils.redis_helper.get_sync_redis_client")
    def test_returns_empty_dict_on_error(self, mock_get_client):
        """Test returning empty dict when info() fails."""
        mock_client = Mock()
        mock_client.info.side_effect = Exception("Error")
        mock_get_client.return_value = mock_client

        result = get_redis_info()

        assert result == {}


class TestClearRedisCache:
    """Test suite for clear_redis_cache function."""

    @patch("admin.utils.redis_helper.get_sync_redis_client")
    def test_clears_redis_cache_successfully(self, mock_get_client):
        """Test clearing Redis cache successfully."""
        mock_client = Mock()
        mock_client.dbsize.return_value = 1234
        mock_client.flushdb.return_value = True
        mock_get_client.return_value = mock_client

        success, message = clear_redis_cache()

        assert success is True
        assert "✅" in message
        assert "1,234 keys deleted" in message
        mock_client.flushdb.assert_called_once()

    @patch("admin.utils.redis_helper.get_sync_redis_client")
    def test_returns_failure_when_client_unavailable(self, mock_get_client):
        """Test returning failure when Redis client unavailable."""
        mock_get_client.return_value = None

        success, message = clear_redis_cache()

        assert success is False
        assert "❌" in message
        assert "unavailable" in message.lower()

    @patch("admin.utils.redis_helper.get_sync_redis_client")
    def test_handles_flush_error(self, mock_get_client):
        """Test handling error during cache flush."""
        mock_client = Mock()
        mock_client.dbsize.return_value = 100
        mock_client.flushdb.side_effect = redis.RedisError("Flush failed")
        mock_get_client.return_value = mock_client

        success, message = clear_redis_cache()

        assert success is False
        assert "❌" in message
