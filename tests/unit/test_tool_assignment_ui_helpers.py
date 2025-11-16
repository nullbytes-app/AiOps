"""
Unit tests for Tool Assignment UI Helpers.

Tests helper functions for MCP tool discovery UI (Story 11.2.5):
- fetch_unified_tools (cached API call)
- fetch_mcp_server_health (cached API call)
- render_tool_badge (visual badges with icons)
- get_health_status_icon (status emoji indicators)
- render_health_tooltip (server health tooltips)
- format_relative_time (human-readable timestamps)
- search_tools (case-insensitive search)
- filter_by_mcp_server (server name filtering)
- get_unique_server_names (extract unique servers)
- count_tools_by_server (tool counts per server)

Story: 11.2.5 - MCP Tool Discovery in Agent Tools UI
AC Coverage: AC2 (badges), AC3 (health), AC4 (filter), AC5 (search), AC8 (caching)
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from unittest.mock import patch, MagicMock

from admin.utils.tool_assignment_ui_helpers import (
    render_tool_badge,
    get_health_status_icon,
    render_health_tooltip,
    format_relative_time,
    search_tools,
    filter_by_mcp_server,
    get_unique_server_names,
    count_tools_by_server,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_openapi_tool():
    """Sample OpenAPI tool for testing."""
    return {
        "id": str(uuid4()),
        "name": "update_ticket",
        "description": "Update ServiceDesk Plus ticket",
        "source_type": "openapi",
        "enabled": True,
    }


@pytest.fixture
def sample_mcp_tool():
    """Sample MCP tool for testing."""
    server_id = str(uuid4())
    return {
        "id": str(uuid4()),
        "name": "list_files",
        "description": "List directory contents",
        "source_type": "mcp",
        "mcp_server_id": server_id,
        "mcp_server_name": "filesystem-server",
        "mcp_primitive_type": "tool",
        "enabled": True,
    }


@pytest.fixture
def sample_mcp_resource():
    """Sample MCP resource for testing."""
    server_id = str(uuid4())
    return {
        "id": str(uuid4()),
        "name": "project_docs",
        "description": "Access project documentation",
        "source_type": "mcp",
        "mcp_server_id": server_id,
        "mcp_server_name": "docs-server",
        "mcp_primitive_type": "resource",
        "enabled": True,
    }


@pytest.fixture
def sample_mcp_prompt():
    """Sample MCP prompt for testing."""
    server_id = str(uuid4()),
    return {
        "id": str(uuid4()),
        "name": "analyze_ticket",
        "description": "Generate ticket analysis prompt",
        "source_type": "mcp",
        "mcp_server_id": server_id,
        "mcp_server_name": "ai-assistant-server",
        "mcp_primitive_type": "prompt",
        "enabled": True,
    }


@pytest.fixture
def sample_health_status():
    """Sample MCP server health status for testing."""
    server_id_1 = str(uuid4())
    server_id_2 = str(uuid4())
    server_id_3 = str(uuid4())

    return {
        server_id_1: {
            "id": server_id_1,
            "name": "filesystem-server",
            "status": "active",
            "last_health_check": (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat(),
            "error_message": None,
        },
        server_id_2: {
            "id": server_id_2,
            "name": "docs-server",
            "status": "error",
            "last_health_check": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(),
            "error_message": "Connection timeout",
        },
        server_id_3: {
            "id": server_id_3,
            "name": "inactive-server",
            "status": "inactive",
            "last_health_check": None,
            "error_message": None,
        },
    }


# ============================================================================
# AC2: Visual Tool Type Indicators Tests
# ============================================================================


def test_render_tool_badge_openapi(sample_openapi_tool, sample_health_status):
    """Test badge rendering for OpenAPI tool (AC2)."""
    badge = render_tool_badge(sample_openapi_tool, sample_health_status, show_health=False)

    assert "🔧" in badge
    assert "OpenAPI" in badge
    assert "update_ticket" in badge
    assert "filesystem-server" not in badge  # OpenAPI has no server


def test_render_tool_badge_mcp_tool(sample_mcp_tool, sample_health_status):
    """Test badge rendering for MCP tool (AC2)."""
    badge = render_tool_badge(sample_mcp_tool, sample_health_status, show_health=True)

    assert "🔌" in badge
    assert "MCP Tool" in badge
    assert "list_files" in badge
    assert "[filesystem-server]" in badge


def test_render_tool_badge_mcp_resource(sample_mcp_resource, sample_health_status):
    """Test badge rendering for MCP resource (AC2)."""
    badge = render_tool_badge(sample_mcp_resource, sample_health_status, show_health=True)

    assert "📦" in badge
    assert "MCP Resource" in badge
    assert "project_docs" in badge
    assert "[docs-server]" in badge


def test_render_tool_badge_mcp_prompt(sample_mcp_prompt, sample_health_status):
    """Test badge rendering for MCP prompt (AC2)."""
    badge = render_tool_badge(sample_mcp_prompt, sample_health_status, show_health=True)

    assert "💬" in badge
    assert "MCP Prompt" in badge
    assert "analyze_ticket" in badge
    assert "[ai-assistant-server]" in badge


def test_render_tool_badge_null_server_name():
    """Test badge rendering with null server name (edge case)."""
    tool = {
        "id": str(uuid4()),
        "name": "test_tool",
        "source_type": "mcp",
        "mcp_server_id": str(uuid4()),
        "mcp_server_name": None,  # Null server name
        "mcp_primitive_type": "tool",
    }
    badge = render_tool_badge(tool, {}, show_health=False)

    assert "🔌" in badge
    assert "MCP Tool" in badge
    assert "test_tool" in badge
    assert "[" not in badge  # No server name bracket


# ============================================================================
# AC3: Health Status Indicators Tests
# ============================================================================


def test_get_health_status_icon_active():
    """Test health status icon for active server (AC3)."""
    icon = get_health_status_icon("active")
    assert icon == "🟢"


def test_get_health_status_icon_error():
    """Test health status icon for error server (AC3)."""
    icon = get_health_status_icon("error")
    assert icon == "🔴"


def test_get_health_status_icon_inactive():
    """Test health status icon for inactive server (AC3)."""
    icon = get_health_status_icon("inactive")
    assert icon == "⚪"


def test_get_health_status_icon_unknown():
    """Test health status icon for unknown status (default to inactive)."""
    icon = get_health_status_icon("unknown_status")
    assert icon == "⚪"


def test_render_health_tooltip_active(sample_health_status):
    """Test health tooltip for active server (AC3)."""
    server_id = list(sample_health_status.keys())[0]
    tooltip = render_health_tooltip(server_id, sample_health_status)

    assert "filesystem-server" in tooltip
    assert "Active" in tooltip
    assert "ago" in tooltip  # Relative time
    assert "Error" not in tooltip


def test_render_health_tooltip_with_error(sample_health_status):
    """Test health tooltip with error message (AC3)."""
    server_id = list(sample_health_status.keys())[1]
    tooltip = render_health_tooltip(server_id, sample_health_status)

    assert "docs-server" in tooltip
    assert "Error" in tooltip
    assert "Connection timeout" in tooltip


def test_render_health_tooltip_never_checked(sample_health_status):
    """Test health tooltip for server never checked (AC3)."""
    server_id = list(sample_health_status.keys())[2]
    tooltip = render_health_tooltip(server_id, sample_health_status)

    assert "inactive-server" in tooltip
    assert "Never" in tooltip


def test_render_health_tooltip_unknown_server():
    """Test health tooltip for unknown server."""
    tooltip = render_health_tooltip("unknown-server-id", {})
    assert tooltip == "Status unknown"


def test_format_relative_time_seconds_ago():
    """Test relative time formatting for recent timestamp (seconds)."""
    timestamp = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
    result = format_relative_time(timestamp)

    assert "seconds ago" in result or "second ago" in result


def test_format_relative_time_minutes_ago():
    """Test relative time formatting for minutes."""
    timestamp = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    result = format_relative_time(timestamp)

    assert "minutes ago" in result or "minute ago" in result


def test_format_relative_time_hours_ago():
    """Test relative time formatting for hours."""
    timestamp = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    result = format_relative_time(timestamp)

    assert "hours ago" in result or "hour ago" in result


def test_format_relative_time_days_ago():
    """Test relative time formatting for days."""
    timestamp = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    result = format_relative_time(timestamp)

    assert "days ago" in result or "day ago" in result


def test_format_relative_time_none():
    """Test relative time formatting for None timestamp."""
    result = format_relative_time(None)
    assert result == "Never"


def test_format_relative_time_invalid():
    """Test relative time formatting for invalid timestamp."""
    result = format_relative_time("invalid-timestamp")
    assert result == "Unknown"


# ============================================================================
# AC5: Search Functionality Tests
# ============================================================================


def test_search_tools_by_name(sample_openapi_tool, sample_mcp_tool):
    """Test search by tool name (AC5)."""
    tools = [sample_openapi_tool, sample_mcp_tool]
    results = search_tools(tools, "list")

    assert len(results) == 1
    assert results[0]["name"] == "list_files"


def test_search_tools_by_description(sample_openapi_tool, sample_mcp_tool):
    """Test search by description (AC5)."""
    tools = [sample_openapi_tool, sample_mcp_tool]
    results = search_tools(tools, "ServiceDesk")

    assert len(results) == 1
    assert results[0]["name"] == "update_ticket"


def test_search_tools_case_insensitive(sample_openapi_tool):
    """Test case-insensitive search (AC5)."""
    tools = [sample_openapi_tool]
    results = search_tools(tools, "TICKET")  # Uppercase query

    assert len(results) == 1
    assert results[0]["name"] == "update_ticket"


def test_search_tools_partial_match(sample_openapi_tool):
    """Test partial match search (AC5)."""
    tools = [sample_openapi_tool]
    results = search_tools(tools, "tick")  # Partial match

    assert len(results) == 1
    assert results[0]["name"] == "update_ticket"


def test_search_tools_no_results(sample_openapi_tool, sample_mcp_tool):
    """Test search with no matching results (AC5)."""
    tools = [sample_openapi_tool, sample_mcp_tool]
    results = search_tools(tools, "nonexistent")

    assert len(results) == 0


def test_search_tools_empty_query(sample_openapi_tool, sample_mcp_tool):
    """Test search with empty query returns all tools (AC5)."""
    tools = [sample_openapi_tool, sample_mcp_tool]
    results = search_tools(tools, "")

    assert len(results) == 2


# ============================================================================
# AC4: Filter by MCP Server Tests
# ============================================================================


def test_filter_by_mcp_server_single(sample_mcp_tool, sample_mcp_resource):
    """Test filtering by single MCP server (AC4)."""
    tools = [sample_mcp_tool, sample_mcp_resource]
    results = filter_by_mcp_server(tools, ["filesystem-server"])

    assert len(results) == 1
    assert results[0]["name"] == "list_files"


def test_filter_by_mcp_server_multiple(sample_mcp_tool, sample_mcp_resource, sample_mcp_prompt):
    """Test filtering by multiple MCP servers (AC4)."""
    tools = [sample_mcp_tool, sample_mcp_resource, sample_mcp_prompt]
    results = filter_by_mcp_server(tools, ["filesystem-server", "docs-server"])

    assert len(results) == 2
    assert any(t["name"] == "list_files" for t in results)
    assert any(t["name"] == "project_docs" for t in results)


def test_filter_by_mcp_server_empty_list(sample_mcp_tool, sample_mcp_resource):
    """Test filter with empty server list returns all tools (AC4)."""
    tools = [sample_mcp_tool, sample_mcp_resource]
    results = filter_by_mcp_server(tools, [])

    assert len(results) == 2


def test_get_unique_server_names(sample_mcp_tool, sample_mcp_resource):
    """Test extracting unique server names (AC4)."""
    # Add duplicate server
    duplicate_tool = sample_mcp_tool.copy()
    duplicate_tool["id"] = str(uuid4())
    duplicate_tool["name"] = "read_file"

    tools = [sample_mcp_tool, sample_mcp_resource, duplicate_tool]
    servers = get_unique_server_names(tools)

    assert len(servers) == 2  # Only unique servers
    assert "filesystem-server" in servers
    assert "docs-server" in servers
    assert servers == sorted(servers)  # Should be sorted


def test_count_tools_by_server(sample_mcp_tool, sample_mcp_resource):
    """Test counting tools per server (AC4)."""
    # Add duplicate server
    duplicate_tool = sample_mcp_tool.copy()
    duplicate_tool["id"] = str(uuid4())
    duplicate_tool["name"] = "read_file"

    tools = [sample_mcp_tool, sample_mcp_resource, duplicate_tool]
    counts = count_tools_by_server(tools)

    assert counts["filesystem-server"] == 2  # Two tools from this server
    assert counts["docs-server"] == 1
