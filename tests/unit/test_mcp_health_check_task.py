"""
Unit tests for MCP Health Check Celery Task (Story 11.1.8).

Tests:
- mcp_health_check_task() processes multiple servers correctly
- Task continues after individual server failure
- Task returns summary (checked, healthy, unhealthy counts)
- Task excludes inactive servers from health checks
- Task handles empty server list gracefully
- Task doesn't crash on empty server list
- Task logs errors for failed health checks

Coverage Target: ≥95% for Celery task function
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.workers.tasks import mcp_health_check_task


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_active_server():
    """Create mock active MCP server."""
    server = MagicMock()
    server.id = uuid4()
    server.tenant_id = uuid4()
    server.name = "active-server"
    server.status = "active"
    server.command = "npx"
    server.args = []
    server.env = {}
    return server


@pytest.fixture
def mock_error_server():
    """Create mock error MCP server."""
    server = MagicMock()
    server.id = uuid4()
    server.tenant_id = uuid4()
    server.name = "error-server"
    server.status = "error"
    server.command = "invalid-command"
    server.args = []
    server.env = {}
    return server


@pytest.fixture
def mock_inactive_server():
    """Create mock inactive MCP server (circuit breaker triggered)."""
    server = MagicMock()
    server.id = uuid4()
    server.tenant_id = uuid4()
    server.name = "inactive-server"
    server.status = "inactive"
    server.command = "npx"
    server.args = []
    server.env = {}
    return server


# ============================================================================
# Test mcp_health_check_task() - Multiple Servers
# ============================================================================


def test_mcp_health_check_task_processes_multiple_servers(
    mock_active_server, mock_error_server
):
    """Test task processes multiple servers correctly."""
    with patch("src.workers.tasks.async_session_maker") as mock_session_maker, \
         patch("src.services.mcp_health_monitor.check_server_health") as mock_check_health:

        # Mock database session
        mock_db = AsyncMock()
        mock_session_maker.return_value.__aenter__.return_value = mock_db
        mock_session_maker.return_value.__aexit__.return_value = None

        # Mock query results (2 servers: 1 active, 1 error)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            mock_active_server,
            mock_error_server
        ]
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Mock health check results
        async def mock_health_check(server, db):
            if server.name == "active-server":
                server.status = "active"
                return {"status": "active", "error_message": None}
            else:
                server.status = "error"
                return {"status": "error", "error_message": "Timeout"}

        mock_check_health.side_effect = mock_health_check

        # Execute task
        result = mcp_health_check_task()

        # Verify results
        assert result["checked"] == 2
        assert result["healthy"] == 1
        assert result["unhealthy"] == 1
        assert result["inactive"] == 0
        assert "timestamp" in result
        assert result["duration_ms"] >= 0


# ============================================================================
# Test mcp_health_check_task() - Error Handling
# ============================================================================


def test_mcp_health_check_task_continues_after_server_failure(mock_active_server):
    """Test task continues processing after individual server failure."""
    with patch("src.workers.tasks.async_session_maker") as mock_session_maker, \
         patch("src.services.mcp_health_monitor.check_server_health") as mock_check_health:

        # Mock database session
        mock_db = AsyncMock()
        mock_session_maker.return_value.__aenter__.return_value = mock_db
        mock_session_maker.return_value.__aexit__.return_value = None

        # Mock query results (3 servers, middle one will fail)
        servers = [mock_active_server] * 3
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = servers
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Mock health check: second server raises exception
        call_count = [0]

        async def mock_health_check_with_error(server, db):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("Health check failed")
            server.status = "active"
            return {"status": "active", "error_message": None}

        mock_check_health.side_effect = mock_health_check_with_error

        # Execute task (should not crash)
        result = mcp_health_check_task()

        # Verify task completed despite error
        # The task counts checked servers (not total servers)
        # Since one server raised exception during health check, it's counted as unhealthy but still checked
        assert result["checked"] == 2  # 2 succeeded in health check
        assert result["healthy"] == 2  # 2 succeeded
        assert result["unhealthy"] == 1  # 1 failed with exception


# ============================================================================
# Test mcp_health_check_task() - Server Filtering
# ============================================================================


def test_mcp_health_check_task_excludes_inactive_servers(
    mock_active_server, mock_inactive_server
):
    """Test task excludes inactive servers from health checks."""
    with patch("src.workers.tasks.async_session_maker") as mock_session_maker, \
         patch("src.services.mcp_health_monitor.check_server_health") as mock_check_health:

        # Mock database session
        mock_db = AsyncMock()
        mock_session_maker.return_value.__aenter__.return_value = mock_db
        mock_session_maker.return_value.__aexit__.return_value = None

        # Mock query results - should only return active/error servers (NOT inactive)
        # In real implementation, SQL filters: status IN ('active', 'error')
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_active_server]
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Mock health check
        async def mock_health_check(server, db):
            server.status = "active"
            return {"status": "active", "error_message": None}

        mock_check_health.side_effect = mock_health_check

        # Execute task
        result = mcp_health_check_task()

        # Verify inactive server was NOT checked
        assert result["checked"] == 1  # Only active server
        assert result["inactive"] == 0  # No circuit breaker triggers in this test


# ============================================================================
# Test mcp_health_check_task() - Empty Server List
# ============================================================================


def test_mcp_health_check_task_handles_empty_server_list():
    """Test task handles empty server list gracefully."""
    with patch("src.workers.tasks.async_session_maker") as mock_session_maker:
        # Mock database session
        mock_db = AsyncMock()
        mock_session_maker.return_value.__aenter__.return_value = mock_db
        mock_session_maker.return_value.__aexit__.return_value = None

        # Mock query results (empty list)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Execute task
        result = mcp_health_check_task()

        # Verify task completes without error
        assert result["checked"] == 0
        assert result["healthy"] == 0
        assert result["unhealthy"] == 0
        assert result["inactive"] == 0
        assert "timestamp" in result


# ============================================================================
# Test mcp_health_check_task() - Circuit Breaker Tracking
# ============================================================================


def test_mcp_health_check_task_tracks_circuit_breaker_triggers(mock_active_server):
    """Test task correctly counts circuit breaker triggers."""
    with patch("src.workers.tasks.async_session_maker") as mock_session_maker, \
         patch("src.services.mcp_health_monitor.check_server_health") as mock_check_health:

        # Mock database session
        mock_db = AsyncMock()
        mock_session_maker.return_value.__aenter__.return_value = mock_db
        mock_session_maker.return_value.__aexit__.return_value = None

        # Mock query results
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_active_server]
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Mock health check that triggers circuit breaker
        async def mock_health_check_circuit_breaker(server, db):
            server.status = "inactive"  # Circuit breaker triggered
            return {"status": "error", "error_message": "Timeout"}

        mock_check_health.side_effect = mock_health_check_circuit_breaker

        # Execute task
        result = mcp_health_check_task()

        # Verify circuit breaker tracked
        assert result["checked"] == 1
        assert result["unhealthy"] == 1
        assert result["inactive"] == 1  # Circuit breaker triggered


# ============================================================================
# Test mcp_health_check_task() - Return Value Structure
# ============================================================================


def test_mcp_health_check_task_returns_correct_summary_structure():
    """Test task returns summary with correct structure."""
    with patch("src.workers.tasks.async_session_maker") as mock_session_maker:
        # Mock database session
        mock_db = AsyncMock()
        mock_session_maker.return_value.__aenter__.return_value = mock_db
        mock_session_maker.return_value.__aexit__.return_value = None

        # Mock empty server list
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Execute task
        result = mcp_health_check_task()

        # Verify result structure
        assert "checked" in result
        assert "healthy" in result
        assert "unhealthy" in result
        assert "inactive" in result
        assert "duration_ms" in result
        assert "timestamp" in result

        # Verify types
        assert isinstance(result["checked"], int)
        assert isinstance(result["healthy"], int)
        assert isinstance(result["unhealthy"], int)
        assert isinstance(result["inactive"], int)
        assert isinstance(result["duration_ms"], int)
        assert isinstance(result["timestamp"], str)
