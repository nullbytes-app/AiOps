"""Unit tests for MCP UI helper functions."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from src.admin.utils.mcp_ui_helpers import (
    create_mcp_server,
    delete_mcp_server,
    fetch_mcp_server_details,
    fetch_mcp_servers,
    format_timestamp,
    rediscover_server,
    render_status_badge,
    render_transport_badge,
    update_mcp_server,
)


# ============================================================================
# Test fetch_mcp_servers
# ============================================================================


@patch("src.admin.utils.mcp_ui_helpers.asyncio.run")
def test_fetch_mcp_servers_success(mock_run: Mock) -> None:
    """Test fetch_mcp_servers returns list of servers."""
    mock_servers = [
        {"id": "server1", "name": "Test Server 1", "status": "active"},
        {"id": "server2", "name": "Test Server 2", "status": "error"},
    ]
    mock_run.return_value = mock_servers

    result = fetch_mcp_servers("tenant-123")

    assert result == mock_servers
    mock_run.assert_called_once()


@patch("src.admin.utils.mcp_ui_helpers.asyncio.run")
def test_fetch_mcp_servers_empty_list(mock_run: Mock) -> None:
    """Test fetch_mcp_servers handles empty list."""
    mock_run.return_value = []

    result = fetch_mcp_servers("tenant-123")

    assert result == []


@patch("src.admin.utils.mcp_ui_helpers.asyncio.run")
def test_fetch_mcp_servers_with_filters(mock_run: Mock) -> None:
    """Test fetch_mcp_servers with status and transport_type filters."""
    mock_servers = [{"id": "server1", "name": "Test Server", "status": "active"}]
    mock_run.return_value = mock_servers

    result = fetch_mcp_servers("tenant-123", status="active", transport_type="stdio")

    assert result == mock_servers


@patch("src.admin.utils.mcp_ui_helpers.asyncio.run")
def test_fetch_mcp_servers_http_error(mock_run: Mock) -> None:
    """Test fetch_mcp_servers handles HTTP errors."""
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_run.side_effect = httpx.HTTPStatusError(
        "Server error", request=Mock(), response=mock_response
    )

    with pytest.raises(Exception, match="API request failed: 500"):
        fetch_mcp_servers("tenant-123")


# ============================================================================
# Test fetch_mcp_server_details
# ============================================================================


@patch("src.admin.utils.mcp_ui_helpers.asyncio.run")
def test_fetch_mcp_server_details_success(mock_run: Mock) -> None:
    """Test fetch_mcp_server_details returns server data."""
    mock_server = {
        "id": "server1",
        "name": "Test Server",
        "status": "active",
        "discovered_tools": [],
    }
    mock_run.return_value = mock_server

    result = fetch_mcp_server_details("server1", "tenant-123")

    assert result == mock_server


@patch("src.admin.utils.mcp_ui_helpers.asyncio.run")
def test_fetch_mcp_server_details_not_found(mock_run: Mock) -> None:
    """Test fetch_mcp_server_details handles 404 error."""
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"
    mock_run.side_effect = httpx.HTTPStatusError(
        "Not found", request=Mock(), response=mock_response
    )

    with pytest.raises(Exception, match="Server not found: server1"):
        fetch_mcp_server_details("server1", "tenant-123")


# ============================================================================
# Test create_mcp_server
# ============================================================================


@patch("src.admin.utils.mcp_ui_helpers.asyncio.run")
def test_create_mcp_server_success(mock_run: Mock) -> None:
    """Test create_mcp_server creates server successfully."""
    payload = {
        "name": "New Server",
        "transport_type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem"],
    }
    mock_server = {"id": "server1", **payload, "status": "active"}
    mock_run.return_value = mock_server

    result = create_mcp_server(payload, "tenant-123")

    assert result == mock_server


@patch("src.admin.utils.mcp_ui_helpers.asyncio.run")
def test_create_mcp_server_validation_error(mock_run: Mock) -> None:
    """Test create_mcp_server handles validation errors."""
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.text = '{"detail":"Name already exists"}'
    mock_run.side_effect = httpx.HTTPStatusError(
        "Validation error", request=Mock(), response=mock_response
    )

    payload = {"name": "Duplicate Server"}
    with pytest.raises(Exception, match="Validation error"):
        create_mcp_server(payload, "tenant-123")


# ============================================================================
# Test update_mcp_server
# ============================================================================


@patch("src.admin.utils.mcp_ui_helpers.asyncio.run")
def test_update_mcp_server_success(mock_run: Mock) -> None:
    """Test update_mcp_server updates server successfully."""
    payload = {"name": "Updated Server", "description": "Updated description"}
    mock_server = {"id": "server1", **payload, "status": "active"}
    mock_run.return_value = mock_server

    result = update_mcp_server("server1", payload, "tenant-123")

    assert result == mock_server


@patch("src.admin.utils.mcp_ui_helpers.asyncio.run")
def test_update_mcp_server_not_found(mock_run: Mock) -> None:
    """Test update_mcp_server handles 404 error."""
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"
    mock_run.side_effect = httpx.HTTPStatusError(
        "Not found", request=Mock(), response=mock_response
    )

    with pytest.raises(Exception, match="Server not found: server1"):
        update_mcp_server("server1", {"name": "Updated"}, "tenant-123")


# ============================================================================
# Test delete_mcp_server
# ============================================================================


@patch("src.admin.utils.mcp_ui_helpers.asyncio.run")
def test_delete_mcp_server_success(mock_run: Mock) -> None:
    """Test delete_mcp_server deletes successfully."""
    mock_run.return_value = True

    result = delete_mcp_server("server1", "tenant-123")

    assert result is True


@patch("src.admin.utils.mcp_ui_helpers.asyncio.run")
def test_delete_mcp_server_not_found(mock_run: Mock) -> None:
    """Test delete_mcp_server handles 404 error."""
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"
    mock_run.side_effect = httpx.HTTPStatusError(
        "Not found", request=Mock(), response=mock_response
    )

    with pytest.raises(Exception, match="Server not found: server1"):
        delete_mcp_server("server1", "tenant-123")


# ============================================================================
# Test rediscover_server
# ============================================================================


@patch("src.admin.utils.mcp_ui_helpers.asyncio.run")
def test_rediscover_server_success(mock_run: Mock) -> None:
    """Test rediscover_server triggers rediscovery."""
    mock_server = {
        "id": "server1",
        "name": "Test Server",
        "discovered_tools": [{"name": "tool1"}],
        "discovered_resources": [{"uri": "resource1"}],
        "discovered_prompts": [{"name": "prompt1"}],
    }
    mock_run.return_value = mock_server

    result = rediscover_server("server1", "tenant-123")

    assert result == mock_server
    assert len(result["discovered_tools"]) == 1


@patch("src.admin.utils.mcp_ui_helpers.asyncio.run")
def test_rediscover_server_failure(mock_run: Mock) -> None:
    """Test rediscover_server handles errors."""
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Discovery failed"
    mock_run.side_effect = httpx.HTTPStatusError(
        "Server error", request=Mock(), response=mock_response
    )

    with pytest.raises(Exception, match="API request failed: 500"):
        rediscover_server("server1", "tenant-123")


# ============================================================================
# Test format_timestamp
# ============================================================================


def test_format_timestamp_none() -> None:
    """Test format_timestamp with None returns 'Never'."""
    result = format_timestamp(None)
    assert result == "Never"


def test_format_timestamp_just_now() -> None:
    """Test format_timestamp for timestamps <60 seconds ago."""
    now = datetime.now(timezone.utc)
    ts = now - timedelta(seconds=30)
    result = format_timestamp(ts)
    assert result == "Just now"


def test_format_timestamp_minutes() -> None:
    """Test format_timestamp for timestamps in minutes."""
    now = datetime.now(timezone.utc)
    ts = now - timedelta(minutes=5)
    result = format_timestamp(ts)
    assert result == "5 minutes ago"


def test_format_timestamp_single_minute() -> None:
    """Test format_timestamp for 1 minute (singular)."""
    now = datetime.now(timezone.utc)
    ts = now - timedelta(minutes=1)
    result = format_timestamp(ts)
    assert result == "1 minute ago"


def test_format_timestamp_hours() -> None:
    """Test format_timestamp for timestamps in hours."""
    now = datetime.now(timezone.utc)
    ts = now - timedelta(hours=3)
    result = format_timestamp(ts)
    assert result == "3 hours ago"


def test_format_timestamp_days() -> None:
    """Test format_timestamp for timestamps in days."""
    now = datetime.now(timezone.utc)
    ts = now - timedelta(days=2)
    result = format_timestamp(ts)
    assert result == "2 days ago"


def test_format_timestamp_naive_datetime() -> None:
    """Test format_timestamp handles naive datetime (converts to UTC)."""
    now = datetime.now()  # Naive datetime
    ts = now - timedelta(minutes=10)
    result = format_timestamp(ts)
    assert "ago" in result or result == "Just now"


# ============================================================================
# Test render_status_badge
# ============================================================================


@patch("src.admin.utils.mcp_ui_helpers.st")
def test_render_status_badge_active(mock_st: Mock) -> None:
    """Test render_status_badge for active status."""
    render_status_badge("active")
    mock_st.markdown.assert_called_once_with("🟢 **Active**")


@patch("src.admin.utils.mcp_ui_helpers.st")
def test_render_status_badge_error(mock_st: Mock) -> None:
    """Test render_status_badge for error status."""
    render_status_badge("error")
    mock_st.markdown.assert_called_once_with("🔴 **Error**")


@patch("src.admin.utils.mcp_ui_helpers.st")
def test_render_status_badge_inactive(mock_st: Mock) -> None:
    """Test render_status_badge for inactive status."""
    render_status_badge("inactive")
    mock_st.markdown.assert_called_once_with("⚪ **Inactive**")


@patch("src.admin.utils.mcp_ui_helpers.st")
def test_render_status_badge_unknown(mock_st: Mock) -> None:
    """Test render_status_badge for unknown status (defaults to inactive icon)."""
    render_status_badge("unknown")
    mock_st.markdown.assert_called_once_with("⚪ **Unknown**")


# ============================================================================
# Test render_transport_badge
# ============================================================================


@patch("src.admin.utils.mcp_ui_helpers.st")
def test_render_transport_badge_stdio(mock_st: Mock) -> None:
    """Test render_transport_badge for stdio transport."""
    render_transport_badge("stdio")
    mock_st.markdown.assert_called_once_with("🔌 **STDIO**")


@patch("src.admin.utils.mcp_ui_helpers.st")
def test_render_transport_badge_http_sse(mock_st: Mock) -> None:
    """Test render_transport_badge for http_sse transport."""
    render_transport_badge("http_sse")
    mock_st.markdown.assert_called_once_with("🌐 **HTTP_SSE**")


@patch("src.admin.utils.mcp_ui_helpers.st")
def test_render_transport_badge_unknown(mock_st: Mock) -> None:
    """Test render_transport_badge for unknown transport."""
    render_transport_badge("unknown")
    mock_st.markdown.assert_called_once_with("❓ **UNKNOWN**")


# ============================================================================
# Test Network Timeout Handling
# ============================================================================


@patch("src.admin.utils.mcp_ui_helpers.asyncio.run")
def test_fetch_mcp_servers_network_timeout(mock_run: Mock) -> None:
    """Test fetch_mcp_servers handles network timeouts gracefully."""
    mock_run.side_effect = httpx.TimeoutException("Network timeout")

    with pytest.raises(Exception, match="Failed to fetch MCP servers"):
        fetch_mcp_servers("tenant-123")


# ============================================================================
# Test HTTP Status Error Handling
# ============================================================================


@patch("src.admin.utils.mcp_ui_helpers.asyncio.run")
def test_create_mcp_server_401_unauthorized(mock_run: Mock) -> None:
    """Test create_mcp_server handles 401 unauthorized."""
    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    mock_run.side_effect = httpx.HTTPStatusError(
        "Unauthorized", request=Mock(), response=mock_response
    )

    with pytest.raises(Exception, match="API request failed: 401"):
        create_mcp_server({"name": "Test"}, "tenant-123")


@patch("src.admin.utils.mcp_ui_helpers.asyncio.run")
def test_update_mcp_server_403_forbidden(mock_run: Mock) -> None:
    """Test update_mcp_server handles 403 forbidden."""
    mock_response = Mock()
    mock_response.status_code = 403
    mock_response.text = "Forbidden"
    mock_run.side_effect = httpx.HTTPStatusError(
        "Forbidden", request=Mock(), response=mock_response
    )

    with pytest.raises(Exception, match="API request failed: 403"):
        update_mcp_server("server1", {"name": "Test"}, "tenant-123")


# =============================================================================
# Story 11.2.2 - Task 4.6: Security Tests for Sensitive Header Detection
# =============================================================================


def test_is_sensitive_header_authorization() -> None:
    """Test 'Authorization' header is detected as sensitive (case insensitive)."""
    from src.admin.utils.mcp_ui_helpers import is_sensitive_header

    assert is_sensitive_header("Authorization") is True
    assert is_sensitive_header("authorization") is True
    assert is_sensitive_header("AUTHORIZATION") is True


def test_is_sensitive_header_api_key() -> None:
    """Test headers with 'key' or 'api' are detected as sensitive."""
    from src.admin.utils.mcp_ui_helpers import is_sensitive_header

    assert is_sensitive_header("X-API-Key") is True
    assert is_sensitive_header("api-key") is True
    assert is_sensitive_header("API_KEY") is True
    assert is_sensitive_header("X-Secret-Key") is True


def test_is_sensitive_header_token() -> None:
    """Test headers with 'token' or 'bearer' are detected as sensitive."""
    from src.admin.utils.mcp_ui_helpers import is_sensitive_header

    assert is_sensitive_header("X-Auth-Token") is True
    assert is_sensitive_header("Bearer-Token") is True
    assert is_sensitive_header("access_token") is True
    assert is_sensitive_header("bearer") is True


def test_is_sensitive_header_non_sensitive() -> None:
    """Test normal headers are NOT detected as sensitive."""
    from src.admin.utils.mcp_ui_helpers import is_sensitive_header

    assert is_sensitive_header("Content-Type") is False
    assert is_sensitive_header("Accept") is False
    assert is_sensitive_header("User-Agent") is False
    assert is_sensitive_header("X-Request-ID") is False
    assert is_sensitive_header("Cache-Control") is False


# =============================================================================
# Story 11.2.2 - Task 3.6: Test Connection UI Tests
# =============================================================================


@patch("src.admin.utils.mcp_ui_helpers.asyncio.run")
def test_mcp_connection_success(mock_run: Mock) -> None:
    """Test test_mcp_connection returns result on success."""
    from src.admin.utils.mcp_ui_helpers import test_mcp_connection

    mock_result = {
        "success": True,
        "server_info": {
            "protocol_version": "2024-11-05",
            "server_name": "Test MCP Server",
            "capabilities": ["tools", "resources"],
        },
        "tools_discovered": 5,
        "resources_discovered": 2,
        "prompts_discovered": 1,
    }
    mock_run.return_value = mock_result

    payload = {
        "name": "Test Server",
        "transport_type": "http_sse",
        "url": "https://test-server.com/mcp",
    }

    result = test_mcp_connection(payload)

    assert result["success"] is True
    assert result["tools_discovered"] == 5
    assert result["server_info"]["server_name"] == "Test MCP Server"


@patch("src.admin.utils.mcp_ui_helpers.asyncio.run")
def test_mcp_connection_failure(mock_run: Mock) -> None:
    """Test test_mcp_connection handles connection failures."""
    from src.admin.utils.mcp_ui_helpers import test_mcp_connection

    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Server timeout"
    mock_run.side_effect = httpx.HTTPStatusError(
        "Connection failed", request=Mock(), response=mock_response
    )

    payload = {
        "name": "Test Server",
        "transport_type": "http_sse",
        "url": "https://unreachable-server.com/mcp",
    }

    with pytest.raises(Exception, match="API request failed: 500"):
        test_mcp_connection(payload)
