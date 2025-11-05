"""
Unit tests for operations_core module.

Tests core system operation functions including pause/resume processing,
queue management, and tenant config synchronization.

Story 6.5 Code Review Follow-up: Split from test_operations_helper.py (545 lines)
into test_operations_core.py and test_operations_audit.py to comply with
CLAUDE.md 500-line constraint (C1).

Test Coverage (CLAUDE.md requirement):
- 1 expected use case per function
- 1 edge case per function
- 1 failure case per function

Fixtures:
- Mocks for Redis, Celery, database operations
- Streamlit cache clearing for test isolation
"""

import pytest
from unittest.mock import MagicMock, patch

from src.admin.utils.operations_helper import (
    pause_processing,
    resume_processing,
    is_processing_paused,
    clear_celery_queue,
    get_queue_length,
    sync_tenant_configs,
)


@pytest.fixture(autouse=True)
def clear_streamlit_cache():
    """Clear Streamlit cache before each test for isolation."""
    import streamlit as st

    st.cache_data.clear()
    st.cache_resource.clear()


# ============================================================================
# PAUSE/RESUME PROCESSING TESTS (AC#2, AC#3)
# ============================================================================


def test_pause_processing_success():
    """Test pause_processing sets Redis key with TTL (expected case)."""
    with patch("src.admin.utils.operations_core.get_sync_redis_client") as mock_redis_fn:
        mock_client = MagicMock()
        mock_redis_fn.return_value = mock_client

        success, message = pause_processing()

        assert success is True
        assert "paused" in message.lower()
        mock_client.setex.assert_called_once_with("system:pause_processing", 86400, "true")


def test_pause_processing_redis_unavailable():
    """Test pause_processing handles Redis unavailable (failure case)."""
    with patch("src.admin.utils.operations_core.get_sync_redis_client") as mock_redis_fn:
        mock_redis_fn.return_value = None

        success, message = pause_processing()

        assert success is False
        assert "unavailable" in message.lower()


def test_pause_processing_redis_error():
    """Test pause_processing handles Redis connection error (edge case)."""
    with patch("src.admin.utils.operations_core.get_sync_redis_client") as mock_redis_fn:
        mock_client = MagicMock()
        mock_client.setex.side_effect = Exception("Connection refused")
        mock_redis_fn.return_value = mock_client

        success, message = pause_processing()

        assert success is False
        assert "failed" in message.lower()


def test_resume_processing_success():
    """Test resume_processing deletes Redis key (expected case)."""
    with patch("src.admin.utils.operations_core.get_sync_redis_client") as mock_redis_fn:
        mock_client = MagicMock()
        mock_client.exists.return_value = 1  # Flag exists
        mock_redis_fn.return_value = mock_client

        success, message = resume_processing()

        assert success is True
        assert "resumed" in message.lower()
        mock_client.delete.assert_called_once_with("system:pause_processing")


def test_resume_processing_no_flag_set():
    """Test resume_processing when no pause flag exists (edge case)."""
    with patch("src.admin.utils.operations_core.get_sync_redis_client") as mock_redis_fn:
        mock_client = MagicMock()
        mock_client.exists.return_value = 0  # No flag
        mock_redis_fn.return_value = mock_client

        success, message = resume_processing()

        assert success is True
        assert "not paused" in message.lower()
        mock_client.delete.assert_not_called()


def test_resume_processing_redis_unavailable():
    """Test resume_processing handles Redis unavailable (failure case)."""
    with patch("src.admin.utils.operations_core.get_sync_redis_client") as mock_redis_fn:
        mock_redis_fn.return_value = None

        success, message = resume_processing()

        assert success is False
        assert "unavailable" in message.lower()


def test_is_processing_paused_true():
    """Test is_processing_paused returns True when flag exists (expected case)."""
    with patch("src.admin.utils.operations_core.get_sync_redis_client") as mock_redis_fn:
        mock_client = MagicMock()
        mock_client.exists.return_value = 1
        mock_redis_fn.return_value = mock_client

        result = is_processing_paused()

        assert result is True


def test_is_processing_paused_false():
    """Test is_processing_paused returns False when no flag (expected case)."""
    with patch("src.admin.utils.operations_core.get_sync_redis_client") as mock_redis_fn:
        mock_client = MagicMock()
        mock_client.exists.return_value = 0
        mock_redis_fn.return_value = mock_client

        result = is_processing_paused()

        assert result is False


def test_is_processing_paused_redis_error():
    """Test is_processing_paused handles Redis error gracefully (failure case)."""
    with patch("src.admin.utils.operations_core.get_sync_redis_client") as mock_redis_fn:
        mock_client = MagicMock()
        mock_client.exists.side_effect = Exception("Connection error")
        mock_redis_fn.return_value = mock_client

        result = is_processing_paused()

        # Should return False on error (fail safe)
        assert result is False


# ============================================================================
# QUEUE MANAGEMENT TESTS (AC#4)
# ============================================================================


def test_clear_celery_queue_success():
    """Test clear_celery_queue purges queue (expected case)."""
    with patch("src.admin.utils.operations_core.celery_app") as mock_celery:
        mock_celery.control.purge.return_value = 42

        success, count, message = clear_celery_queue()

        assert success is True
        assert count == 42
        assert "42" in message


def test_clear_celery_queue_empty():
    """Test clear_celery_queue on empty queue (edge case)."""
    with patch("src.admin.utils.operations_core.celery_app") as mock_celery:
        mock_celery.control.purge.return_value = 0

        success, count, message = clear_celery_queue()

        assert success is True
        assert count == 0
        assert "empty" in message.lower()


def test_clear_celery_queue_error():
    """Test clear_celery_queue handles purge error (failure case)."""
    with patch("src.admin.utils.operations_core.celery_app") as mock_celery:
        mock_celery.control.purge.side_effect = Exception("Broker unavailable")

        success, count, message = clear_celery_queue()

        assert success is False
        assert count == 0
        assert "failed" in message.lower()


def test_get_queue_length_success():
    """Test get_queue_length returns correct depth (expected case)."""
    with patch("src.admin.utils.operations_core.get_sync_redis_client") as mock_redis_fn:
        mock_client = MagicMock()
        mock_client.llen.return_value = 123
        mock_redis_fn.return_value = mock_client

        depth = get_queue_length()

        assert depth == 123
        mock_client.llen.assert_called_once_with("celery")


def test_get_queue_length_redis_unavailable():
    """Test get_queue_length returns 0 when Redis unavailable (failure case)."""
    with patch("src.admin.utils.operations_core.get_sync_redis_client") as mock_redis_fn:
        mock_redis_fn.return_value = None

        depth = get_queue_length()

        assert depth == 0


def test_get_queue_length_custom_queue():
    """Test get_queue_length with custom queue name (edge case)."""
    with patch("src.admin.utils.operations_core.get_sync_redis_client") as mock_redis_fn:
        mock_client = MagicMock()
        mock_client.llen.return_value = 5
        mock_redis_fn.return_value = mock_client

        depth = get_queue_length(queue_name="custom_queue")

        assert depth == 5
        mock_client.llen.assert_called_once_with("custom_queue")


# ============================================================================
# TENANT CONFIG SYNC TESTS (AC#5)
# ============================================================================


def test_sync_tenant_configs_success():
    """Test sync_tenant_configs syncs all configs (expected case)."""
    with patch("src.admin.utils.operations_core.get_sync_redis_client") as mock_redis_fn, \
         patch("src.admin.utils.operations_core.get_db_session") as mock_db_session:

        # Mock Redis
        mock_redis_client = MagicMock()
        mock_redis_fn.return_value = mock_redis_client

        # Mock database session
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session

        # Mock tenant configs
        from src.database.models import TenantConfig

        mock_config1 = MagicMock(spec=TenantConfig)
        mock_config1.tenant_id = "tenant-1"
        mock_config1.webhook_url = "https://example.com/webhook"
        mock_config1.api_key = "secret123"
        mock_config1.is_active = True

        mock_config2 = MagicMock(spec=TenantConfig)
        mock_config2.tenant_id = "tenant-2"
        mock_config2.webhook_url = "https://example2.com/webhook"
        mock_config2.api_key = "secret456"
        mock_config2.is_active = True

        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.all.return_value = [mock_config1, mock_config2]

        success, sync_results, message = sync_tenant_configs()

        assert success is True
        assert len(sync_results) == 2
        assert "tenant-1" in sync_results
        assert "tenant-2" in sync_results
        assert "2" in message


def test_sync_tenant_configs_no_tenants():
    """Test sync_tenant_configs with no active tenants (edge case)."""
    with patch("src.admin.utils.operations_core.get_sync_redis_client") as mock_redis_fn, \
         patch("src.admin.utils.operations_core.get_db_session") as mock_db_session:

        mock_redis_client = MagicMock()
        mock_redis_fn.return_value = mock_redis_client

        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session

        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.all.return_value = []

        success, sync_results, message = sync_tenant_configs()

        assert success is True
        assert len(sync_results) == 0
        assert "no active" in message.lower()


def test_sync_tenant_configs_redis_unavailable():
    """Test sync_tenant_configs handles Redis unavailable (failure case)."""
    with patch("src.admin.utils.operations_core.get_sync_redis_client") as mock_redis_fn:
        mock_redis_fn.return_value = None

        success, sync_results, message = sync_tenant_configs()

        assert success is False
        assert "unavailable" in message.lower()
