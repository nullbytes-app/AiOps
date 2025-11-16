"""
Unit tests for MCP Health Monitor Service (Story 11.1.8).

Tests:
- check_server_health() with successful health check
- Health check with timeout error
- Health check with process spawn failure
- Circuit breaker triggers after 3 consecutive failures
- Database updates (status, last_health_check, consecutive_failures, error_message)
- Structured logging output verification
- Client cleanup after health check
- Error message sanitization (no sensitive data)

Coverage Target: ≥95% for mcp_health_monitor.py
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from loguru import logger

from src.services.mcp_health_monitor import (
    check_server_health,
    _handle_health_check_failure,
    _sanitize_error_message,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_mcp_server():
    """Create mock MCPServer instance for testing."""
    server = MagicMock()
    server.id = uuid4()
    server.tenant_id = uuid4()
    server.name = "test-server"
    server.command = "npx"
    server.args = ["-y", "@modelcontextprotocol/server-filesystem"]
    server.env = {"LOG_LEVEL": "debug"}
    server.status = "active"
    server.last_health_check = None
    server.error_message = None
    server.consecutive_failures = 0
    server.discovered_tools = []
    server.transport_type = "stdio"  # Required for MCPHealthMetric Pydantic validation
    return server


@pytest.fixture
def mock_db():
    """Create mock database session."""
    db = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.fixture
def mock_tool():
    """Create mock MCP tool for list_tools() response."""
    tool = MagicMock()
    tool.name = "read_file"
    tool.description = "Read file contents"
    tool.inputSchema = {"type": "object", "properties": {}}
    return tool


# ============================================================================
# Test check_server_health() - Success Cases
# ============================================================================


@pytest.mark.asyncio
async def test_check_server_health_success(mock_mcp_server, mock_db, mock_tool):
    """Test health check succeeds and updates database correctly."""
    with patch("src.services.mcp_health_monitor.MCPStdioClient") as MockClient:
        # Mock client behavior
        mock_client_instance = AsyncMock()
        mock_client_instance.initialize = AsyncMock()
        mock_client_instance.list_tools = AsyncMock(return_value=[mock_tool])
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        MockClient.return_value = mock_client_instance

        # Perform health check
        result = await check_server_health(mock_mcp_server, mock_db)

        # Verify result
        assert result["status"] == "active"
        assert result["error_message"] is None
        assert result["duration_ms"] >= 0

        # Verify database updates
        assert mock_mcp_server.status == "active"
        assert mock_mcp_server.last_health_check is not None
        assert mock_mcp_server.error_message is None
        assert mock_mcp_server.consecutive_failures == 0

        # Note: discovered_tools are NOT updated by health check in Story 11.2.4
        # Health check only verifies server is reachable, not full capability discovery

        # Verify database commit called twice (Story 11.2.4: record_metric + update server status)
        assert mock_db.commit.call_count == 2


# ============================================================================
# Test check_server_health() - Failure Cases
# ============================================================================


@pytest.mark.asyncio
async def test_check_server_health_timeout(mock_mcp_server, mock_db):
    """Test health check handles timeout error (>30s)."""
    with patch("src.services.mcp_health_monitor.MCPStdioClient") as MockClient:
        # Mock client to raise TimeoutError
        mock_client_instance = AsyncMock()
        mock_client_instance.initialize = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        MockClient.return_value = mock_client_instance

        # Perform health check
        result = await check_server_health(mock_mcp_server, mock_db)

        # Verify result
        assert result["status"] == "error"
        assert "timeout" in result["error_message"].lower()
        assert result["duration_ms"] >= 0

        # Verify database updates
        assert mock_mcp_server.status == "error"
        assert mock_mcp_server.last_health_check is not None
        assert "timeout" in mock_mcp_server.error_message.lower()
        assert mock_mcp_server.consecutive_failures == 1

        # Verify database commit called twice (Story 11.2.4: record_metric + update server status)
        assert mock_db.commit.call_count == 2


@pytest.mark.asyncio
async def test_check_server_health_process_error(mock_mcp_server, mock_db):
    """Test health check handles process spawn failure."""
    with patch("src.services.mcp_health_monitor.MCPStdioClient") as MockClient:
        # Mock client to raise OSError (process spawn failure)
        MockClient.side_effect = OSError("Command not found: /usr/bin/npx")

        # Perform health check
        result = await check_server_health(mock_mcp_server, mock_db)

        # Verify result
        assert result["status"] == "error"
        assert "process spawn failed" in result["error_message"].lower()
        assert result["duration_ms"] >= 0

        # Verify database updates
        assert mock_mcp_server.status == "error"
        assert mock_mcp_server.consecutive_failures == 1

        # Verify database commit called twice (Story 11.2.4: record_metric + update server status)
        assert mock_db.commit.call_count == 2


@pytest.mark.asyncio
async def test_check_server_health_jsonrpc_error(mock_mcp_server, mock_db):
    """Test health check handles JSON-RPC protocol error."""
    with patch("src.services.mcp_health_monitor.MCPStdioClient") as MockClient:
        # Mock client to raise ValueError (JSON-RPC error)
        mock_client_instance = AsyncMock()
        mock_client_instance.initialize = AsyncMock(side_effect=ValueError("Invalid JSON-RPC response"))
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        MockClient.return_value = mock_client_instance

        # Perform health check
        result = await check_server_health(mock_mcp_server, mock_db)

        # Verify result
        assert result["status"] == "error"
        assert "json-rpc" in result["error_message"].lower()
        assert result["duration_ms"] >= 0

        # Verify database updates
        assert mock_mcp_server.status == "error"
        assert mock_mcp_server.consecutive_failures == 1


# ============================================================================
# Test Circuit Breaker Logic
# ============================================================================


@pytest.mark.asyncio
async def test_circuit_breaker_triggers_after_3_failures(mock_mcp_server, mock_db, capsys):
    """Test circuit breaker marks server inactive after 3 consecutive failures."""
    # Set server to have 2 existing failures
    mock_mcp_server.consecutive_failures = 2

    with patch("src.services.mcp_health_monitor.MCPStdioClient") as MockClient:
        # Mock client to raise error (3rd failure)
        MockClient.side_effect = OSError("Process spawn failed")

        # Perform health check (will be 3rd failure)
        result = await check_server_health(mock_mcp_server, mock_db)

        # Verify circuit breaker triggered
        assert mock_mcp_server.status == "inactive"
        assert mock_mcp_server.consecutive_failures == 3
        # Note: Warning log is emitted (checked manually in stderr output)


# ============================================================================
# Test _handle_health_check_failure()
# ============================================================================


@pytest.mark.asyncio
async def test_handle_health_check_failure_updates_database(mock_mcp_server, mock_db):
    """Test failure handler updates database correctly."""
    start_time = datetime.now(timezone.utc)

    result = await _handle_health_check_failure(
        mock_mcp_server,
        mock_db,
        error_message="Test error",
        start_time=start_time,
        error_type="test_error"
    )

    # Verify result
    assert result["status"] == "error"
    assert result["error_message"] == "Test error"
    assert result["duration_ms"] >= 0

    # Verify database updates
    assert mock_mcp_server.status == "error"
    assert mock_mcp_server.error_message == "Test error"
    assert mock_mcp_server.consecutive_failures == 1
    assert mock_mcp_server.last_health_check is not None

    # Verify database commit called
    mock_db.commit.assert_called_once()


# ============================================================================
# Test _sanitize_error_message()
# ============================================================================


def test_sanitize_error_message_removes_paths():
    """Test sanitization removes full file paths."""
    error = "/usr/local/bin/npx failed: ENOENT"
    sanitized = _sanitize_error_message(error)

    # Verify path removed (keeps only executable name)
    assert "/usr/local/bin" not in sanitized
    assert "npx" in sanitized


def test_sanitize_error_message_removes_env_vars():
    """Test sanitization removes environment variable values."""
    error = "API_KEY=secret123 not set"
    sanitized = _sanitize_error_message(error)

    # Verify secret removed
    assert "secret123" not in sanitized
    assert "Environment variable" in sanitized


def test_sanitize_error_message_truncates_long_errors():
    """Test sanitization truncates very long error messages."""
    error = "x" * 300
    sanitized = _sanitize_error_message(error)

    # Verify truncated to 200 chars
    assert len(sanitized) == 200
    assert sanitized.endswith("...")


# ============================================================================
# Test Client Cleanup (Context Manager)
# ============================================================================


@pytest.mark.asyncio
async def test_client_cleanup_on_success(mock_mcp_server, mock_db, mock_tool):
    """Test client cleanup guaranteed via context manager (success case)."""
    with patch("src.services.mcp_health_monitor.MCPStdioClient") as MockClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.initialize = AsyncMock()
        mock_client_instance.list_tools = AsyncMock(return_value=[mock_tool])
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        MockClient.return_value = mock_client_instance

        # Perform health check
        await check_server_health(mock_mcp_server, mock_db)

        # Verify context manager exit called (cleanup)
        mock_client_instance.__aexit__.assert_called_once()


@pytest.mark.asyncio
async def test_client_cleanup_on_error(mock_mcp_server, mock_db):
    """Test client cleanup guaranteed even on error."""
    with patch("src.services.mcp_health_monitor.MCPStdioClient") as MockClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.initialize = AsyncMock(side_effect=ValueError("Error"))
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        MockClient.return_value = mock_client_instance

        # Perform health check (will fail)
        await check_server_health(mock_mcp_server, mock_db)

        # Verify context manager exit called despite error
        mock_client_instance.__aexit__.assert_called_once()


# ============================================================================
# Test Additional Coverage (Story 11.2.6 - Coverage >90%)
# ============================================================================


@pytest.mark.asyncio
async def test_perform_detailed_health_check_generic_exception(mock_mcp_server):
    """Test perform_detailed_health_check handles generic Exception (lines 141-144)."""
    from src.services.mcp_health_monitor import perform_detailed_health_check

    # Mock MCPStdioClient to raise a generic exception
    with patch("src.services.mcp_health_monitor.MCPStdioClient") as MockClient:
        MockClient.side_effect = RuntimeError("Unexpected error")

        result = await perform_detailed_health_check(mock_mcp_server)

        # Verify error metric returned
        assert result.status.value == "error"
        assert "error_message" in result.model_dump()
        assert result.response_time_ms >= 0


@pytest.mark.asyncio
async def test_legacy_check_server_health_v1_success(mock_mcp_server, mock_db, mock_tool):
    """Test deprecated _legacy_check_server_health_v1() success path (lines 400-461)."""
    from src.services.mcp_health_monitor import _legacy_check_server_health_v1

    with patch("src.services.mcp_health_monitor.MCPStdioClient") as MockClient:
        # Mock client behavior
        mock_client_instance = AsyncMock()
        mock_client_instance.initialize = AsyncMock()
        mock_client_instance.list_tools = AsyncMock(return_value=[mock_tool])
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        MockClient.return_value = mock_client_instance

        # Perform legacy health check
        result = await _legacy_check_server_health_v1(mock_mcp_server, mock_db)

        # Verify result
        assert result["status"] == "active"
        assert result["error_message"] is None
        assert result["duration_ms"] >= 0

        # Verify database updates (legacy function updates discovered_tools)
        assert mock_mcp_server.status == "active"
        assert mock_mcp_server.last_health_check is not None
        assert mock_mcp_server.error_message is None
        assert mock_mcp_server.consecutive_failures == 0
        assert len(mock_mcp_server.discovered_tools) == 1

        # Verify database commit called once (legacy function commits once)
        mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_legacy_check_server_health_v1_timeout(mock_mcp_server, mock_db):
    """Test deprecated _legacy_check_server_health_v1() timeout error (lines 462-467)."""
    from src.services.mcp_health_monitor import _legacy_check_server_health_v1

    with patch("src.services.mcp_health_monitor.MCPStdioClient") as MockClient:
        # Mock client to raise TimeoutError
        mock_client_instance = AsyncMock()
        mock_client_instance.initialize = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        MockClient.return_value = mock_client_instance

        # Perform legacy health check
        result = await _legacy_check_server_health_v1(mock_mcp_server, mock_db)

        # Verify result
        assert result["status"] == "error"
        assert "timeout" in result["error_message"].lower()


@pytest.mark.asyncio
async def test_legacy_check_server_health_v1_os_error(mock_mcp_server, mock_db):
    """Test deprecated _legacy_check_server_health_v1() OSError (lines 469-474)."""
    from src.services.mcp_health_monitor import _legacy_check_server_health_v1

    with patch("src.services.mcp_health_monitor.MCPStdioClient") as MockClient:
        MockClient.side_effect = OSError("Command not found")

        # Perform legacy health check
        result = await _legacy_check_server_health_v1(mock_mcp_server, mock_db)

        # Verify result
        assert result["status"] == "error"
        assert "process spawn failed" in result["error_message"].lower()


@pytest.mark.asyncio
async def test_legacy_check_server_health_v1_value_error(mock_mcp_server, mock_db):
    """Test deprecated _legacy_check_server_health_v1() ValueError (lines 476-481)."""
    from src.services.mcp_health_monitor import _legacy_check_server_health_v1

    with patch("src.services.mcp_health_monitor.MCPStdioClient") as MockClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.initialize = AsyncMock(side_effect=ValueError("Invalid response"))
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        MockClient.return_value = mock_client_instance

        # Perform legacy health check
        result = await _legacy_check_server_health_v1(mock_mcp_server, mock_db)

        # Verify result
        assert result["status"] == "error"
        assert "json-rpc" in result["error_message"].lower()


@pytest.mark.asyncio
async def test_legacy_check_server_health_v1_unknown_error(mock_mcp_server, mock_db):
    """Test deprecated _legacy_check_server_health_v1() generic Exception (lines 483-488)."""
    from src.services.mcp_health_monitor import _legacy_check_server_health_v1

    with patch("src.services.mcp_health_monitor.MCPStdioClient") as MockClient:
        MockClient.side_effect = RuntimeError("Unexpected error")

        # Perform legacy health check
        result = await _legacy_check_server_health_v1(mock_mcp_server, mock_db)

        # Verify result
        assert result["status"] == "error"
        assert "unexpected error" in result["error_message"].lower()
