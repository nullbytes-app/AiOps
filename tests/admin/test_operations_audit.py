"""
Unit tests for operations_audit and operations_utils modules.

Tests worker health monitoring, audit logging functions, and utility helpers.

Story 6.5 Code Review Follow-up: Split from test_operations_helper.py (545 lines)
into test_operations_core.py and test_operations_audit.py to comply with
CLAUDE.md 500-line constraint (C1).

Test Coverage (CLAUDE.md requirement):
- 1 expected use case per function
- 1 edge case per function
- 1 failure case per function

Fixtures:
- Mocks for Celery, database operations
- Streamlit cache clearing for test isolation
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from src.admin.utils.operations_helper import (
    get_worker_stats,
    get_active_workers,
    log_operation,
    get_recent_operations,
    format_uptime,
)


@pytest.fixture(autouse=True)
def clear_streamlit_cache():
    """Clear Streamlit cache before each test for isolation."""
    import streamlit as st

    st.cache_data.clear()
    st.cache_resource.clear()


# ============================================================================
# WORKER HEALTH TESTS (AC#6)
# ============================================================================


def test_get_worker_stats_success():
    """Test get_worker_stats returns worker info (expected case)."""
    with patch("admin.utils.operations_utils.celery_app") as mock_celery:
        mock_inspect = MagicMock()
        mock_celery.control.inspect.return_value = mock_inspect

        mock_inspect.stats.return_value = {
            "celery@worker-1": {
                "total": {
                    "tasks.process_ticket_enhancement": 1234,
                    "tasks.another_task": 567,
                }
            },
            "celery@worker-2": {
                "total": {
                    "tasks.process_ticket_enhancement": 890,
                }
            },
        }

        workers = get_worker_stats()

        assert len(workers) == 2
        assert workers[0]["hostname"] == "celery@worker-1"
        assert workers[0]["total_tasks"] == 1801  # 1234 + 567
        assert workers[1]["hostname"] == "celery@worker-2"
        assert workers[1]["total_tasks"] == 890


def test_get_worker_stats_no_workers():
    """Test get_worker_stats returns empty list when no workers (edge case)."""
    with patch("admin.utils.operations_utils.celery_app") as mock_celery:
        mock_inspect = MagicMock()
        mock_celery.control.inspect.return_value = mock_inspect
        mock_inspect.stats.return_value = None

        workers = get_worker_stats()

        assert workers == []


def test_get_worker_stats_error():
    """Test get_worker_stats handles inspect error (failure case)."""
    with patch("admin.utils.operations_utils.celery_app") as mock_celery:
        mock_inspect = MagicMock()
        mock_celery.control.inspect.return_value = mock_inspect
        mock_inspect.stats.side_effect = Exception("Broker unavailable")

        workers = get_worker_stats()

        assert workers == []


def test_get_active_workers_success():
    """Test get_active_workers returns worker hostnames (expected case)."""
    with patch("admin.utils.operations_utils.celery_app") as mock_celery:
        mock_inspect = MagicMock()
        mock_celery.control.inspect.return_value = mock_inspect
        mock_inspect.stats.return_value = {
            "celery@worker-1": {},
            "celery@worker-2": {},
        }

        workers = get_active_workers()

        assert len(workers) == 2
        assert "celery@worker-1" in workers
        assert "celery@worker-2" in workers


def test_get_active_workers_no_workers():
    """Test get_active_workers returns empty list (edge case)."""
    with patch("admin.utils.operations_utils.celery_app") as mock_celery:
        mock_inspect = MagicMock()
        mock_celery.control.inspect.return_value = mock_inspect
        mock_inspect.stats.return_value = None

        workers = get_active_workers()

        assert workers == []


# ============================================================================
# AUDIT LOGGING TESTS (AC#7, AC#9)
# ============================================================================


def test_log_operation_success():
    """Test log_operation creates audit log entry (expected case)."""
    with patch("admin.utils.operations_audit.get_db_session") as mock_db_session:
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session

        result = log_operation(
            user="admin@example.com",
            operation="pause_processing",
            details={"queue": "celery"},
            status="success",
        )

        assert result is True
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


def test_log_operation_database_error():
    """Test log_operation handles database error gracefully (failure case)."""
    with patch("admin.utils.operations_audit.get_db_session") as mock_db_session:
        mock_session = MagicMock()
        mock_session.add.side_effect = Exception("Database unavailable")
        mock_db_session.return_value.__enter__.return_value = mock_session

        result = log_operation(
            user="admin@example.com",
            operation="pause_processing",
            details={},
            status="success",
        )

        # Should return False but not raise exception (non-blocking)
        assert result is False


def test_get_recent_operations_success():
    """Test get_recent_operations returns operation list (expected case)."""
    with patch("admin.utils.operations_audit.get_db_session") as mock_db_session:
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session

        # Mock operation records
        from src.database.models import AuditLog

        mock_op1 = MagicMock(spec=AuditLog)
        mock_op1.id = uuid4()
        mock_op1.timestamp = datetime(2025, 11, 4, 10, 30)
        mock_op1.user = "admin"
        mock_op1.operation = "pause_processing"
        mock_op1.details = {"queue": "celery"}
        mock_op1.status = "success"

        mock_op2 = MagicMock(spec=AuditLog)
        mock_op2.id = uuid4()
        mock_op2.timestamp = datetime(2025, 11, 4, 10, 31)
        mock_op2.user = "admin"
        mock_op2.operation = "resume_processing"
        mock_op2.details = {}
        mock_op2.status = "success"

        mock_query = mock_session.query.return_value
        mock_query.order_by.return_value.limit.return_value.all.return_value = [mock_op1, mock_op2]

        operations = get_recent_operations(limit=20)

        assert len(operations) == 2
        assert operations[0]["operation"] == "pause_processing"
        assert operations[1]["operation"] == "resume_processing"


def test_get_recent_operations_no_operations():
    """Test get_recent_operations returns empty list (edge case)."""
    with patch("admin.utils.operations_audit.get_db_session") as mock_db_session:
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session

        mock_query = mock_session.query.return_value
        mock_query.order_by.return_value.limit.return_value.all.return_value = []

        operations = get_recent_operations()

        assert operations == []


def test_get_recent_operations_database_error():
    """Test get_recent_operations handles database error (failure case)."""
    with patch("admin.utils.operations_audit.get_db_session") as mock_db_session:
        mock_session = MagicMock()
        mock_session.query.side_effect = Exception("Database unavailable")
        mock_db_session.return_value.__enter__.return_value = mock_session

        operations = get_recent_operations()

        assert operations == []


# ============================================================================
# UTILITY FUNCTION TESTS
# ============================================================================


def test_format_uptime_hours():
    """Test format_uptime with hours (expected case)."""
    result = format_uptime(3661)  # 1h 1m 1s
    assert result == "1h 1m 1s"


def test_format_uptime_minutes():
    """Test format_uptime with minutes only (edge case)."""
    result = format_uptime(125)  # 2m 5s
    assert result == "2m 5s"


def test_format_uptime_seconds():
    """Test format_uptime with seconds only (edge case)."""
    result = format_uptime(42)
    assert result == "42s"


def test_format_uptime_zero():
    """Test format_uptime with zero seconds (edge case)."""
    result = format_uptime(0)
    assert result == "0s"


def test_format_uptime_negative():
    """Test format_uptime with negative value (failure case)."""
    result = format_uptime(-10)
    assert result == "0s"  # Should return 0s for negative
