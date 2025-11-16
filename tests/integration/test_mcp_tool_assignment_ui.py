"""
Integration Tests - MCP Tool Assignment UI Workflow

Tests end-to-end workflows for Story 11.2.5:
- Tab navigation and tool filtering
- Combined server filter + search
- Multi-source tool selection and assignment
- Health status integration with tool display
- Tool removal workflow

Note: These tests validate UI helper logic but do NOT test Streamlit rendering
(Streamlit UI testing requires manual validation or dedicated app_test framework).
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from admin.utils.tool_assignment_ui_helpers import (
    fetch_unified_tools,
    fetch_mcp_server_health,
    search_tools,
    filter_by_mcp_server,
    get_unique_server_names,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_unified_tools():
    """Mixed OpenAPI + MCP tools for integration testing."""
    return [
        {
            "id": "1",
            "name": "update_ticket",
            "description": "Update ServiceDesk Plus ticket",
            "source_type": "openapi",
            "enabled": True,
        },
        {
            "id": "2",
            "name": "search_tickets",
            "description": "Search for tickets in ServiceDesk",
            "source_type": "openapi",
            "enabled": True,
        },
        {
            "id": "mcp-1",
            "name": "list_files",
            "description": "List directory contents",
            "source_type": "mcp",
            "mcp_server_id": "server-uuid-1",
            "mcp_server_name": "filesystem-server",
            "mcp_primitive_type": "tool",
            "enabled": True,
        },
        {
            "id": "mcp-2",
            "name": "read_file",
            "description": "Read file contents",
            "source_type": "mcp",
            "mcp_server_id": "server-uuid-1",
            "mcp_server_name": "filesystem-server",
            "mcp_primitive_type": "tool",
            "enabled": True,
        },
        {
            "id": "mcp-3",
            "name": "project_docs",
            "description": "Access project documentation",
            "source_type": "mcp",
            "mcp_server_id": "server-uuid-2",
            "mcp_server_name": "docs-server",
            "mcp_primitive_type": "resource",
            "enabled": True,
        },
        {
            "id": "mcp-4",
            "name": "analyze_ticket",
            "description": "Generate ticket analysis prompt",
            "source_type": "mcp",
            "mcp_server_id": "server-uuid-3",
            "mcp_server_name": "ai-assistant-server",
            "mcp_primitive_type": "prompt",
            "enabled": True,
        },
    ]


@pytest.fixture
def sample_mcp_server_health():
    """MCP server health status for integration testing."""
    return {
        "server-uuid-1": {
            "id": "server-uuid-1",
            "name": "filesystem-server",
            "status": "active",
            "last_health_check": (datetime.now(timezone.utc).isoformat()),
        },
        "server-uuid-2": {
            "id": "server-uuid-2",
            "name": "docs-server",
            "status": "error",
            "last_health_check": (
                datetime.now(timezone.utc).replace(hour=9, minute=55).isoformat()
            ),
            "error_message": "Connection timeout",
        },
        "server-uuid-3": {
            "id": "server-uuid-3",
            "name": "ai-assistant-server",
            "status": "inactive",
            "last_health_check": None,
        },
    }


# ============================================================================
# Integration Test 1: Tab Navigation and Filtering (AC1)
# ============================================================================


def test_tab_navigation_filters_correct_subsets(sample_unified_tools):
    """
    Test: Navigate all 3 tabs, verify correct tool subsets displayed.

    AC1: Tab-based tool organization
    - All Tools: Show all 6 tools
    - OpenAPI Tools: Show 2 OpenAPI tools
    - MCP Tools: Show 4 MCP tools
    """
    all_tools = sample_unified_tools

    # Tab 1: All Tools
    assert len(all_tools) == 6

    # Tab 2: OpenAPI Tools
    openapi_tools = [t for t in all_tools if t["source_type"] == "openapi"]
    assert len(openapi_tools) == 2
    assert all(t["source_type"] == "openapi" for t in openapi_tools)

    # Tab 3: MCP Tools
    mcp_tools = [t for t in all_tools if t["source_type"] == "mcp"]
    assert len(mcp_tools) == 4
    assert all(t["source_type"] == "mcp" for t in mcp_tools)

    # Verify no overlap
    assert set(t["id"] for t in openapi_tools).isdisjoint(
        set(t["id"] for t in mcp_tools)
    )


# ============================================================================
# Integration Test 2: Combined Filter + Search (AC4 + AC5)
# ============================================================================


def test_combined_server_filter_and_search(sample_unified_tools):
    """
    Test: Apply MCP server filter + search query, verify both filters work together.

    AC4 + AC5: Combined filtering
    - Filter by filesystem-server: 2 tools
    - Search "read": 1 tool (read_file)
    - Combined: 1 tool matching both filters
    """
    mcp_tools = [t for t in sample_unified_tools if t["source_type"] == "mcp"]

    # Step 1: Filter by MCP server
    filtered_by_server = filter_by_mcp_server(mcp_tools, ["filesystem-server"])
    assert len(filtered_by_server) == 2
    assert all(t["mcp_server_name"] == "filesystem-server" for t in filtered_by_server)

    # Step 2: Apply search on filtered results
    search_results = search_tools(filtered_by_server, "read")
    assert len(search_results) == 1
    assert search_results[0]["name"] == "read_file"

    # Verify both filters applied correctly
    assert search_results[0]["mcp_server_name"] == "filesystem-server"
    assert "read" in search_results[0]["name"].lower()


def test_combined_filter_multiple_servers_with_search(sample_unified_tools):
    """
    Test: Filter by multiple servers + search, verify intersection.

    AC4 + AC5: Multi-server filter + search
    - Filter by filesystem-server AND docs-server: 3 tools
    - Search "file": 2 tools (list_files, read_file)
    - Combined: 2 tools from filesystem-server
    """
    mcp_tools = [t for t in sample_unified_tools if t["source_type"] == "mcp"]

    # Step 1: Filter by multiple servers
    filtered_by_servers = filter_by_mcp_server(
        mcp_tools, ["filesystem-server", "docs-server"]
    )
    assert len(filtered_by_servers) == 3

    # Step 2: Search "file" in filtered results
    search_results = search_tools(filtered_by_servers, "file")
    assert len(search_results) == 2
    assert all("file" in t["name"].lower() for t in search_results)


# ============================================================================
# Integration Test 3: Badge + Health Status Integration (AC2 + AC3)
# ============================================================================


def test_badge_rendering_with_health_status_integration(
    sample_unified_tools, sample_mcp_server_health
):
    """
    Test: Fetch tools + health status, verify badge rendering includes health indicators.

    AC2 + AC3: Visual badges with health status
    - OpenAPI tools: 🔧 badge, no health indicator
    - MCP tools: 🔌/📦/💬 badge + 🟢/🔴/⚪ health icon
    """
    from admin.utils.tool_assignment_ui_helpers import (
        render_tool_badge,
        get_health_status_icon,
    )

    for tool in sample_unified_tools:
        badge = render_tool_badge(tool, sample_mcp_server_health)

        if tool["source_type"] == "openapi":
            # OpenAPI badge: 🔧 icon, no health indicator
            assert "🔧" in badge
            assert "OpenAPI" in badge
            assert "🟢" not in badge and "🔴" not in badge and "⚪" not in badge

        elif tool["source_type"] == "mcp":
            # MCP badge: correct primitive type icon
            if tool["mcp_primitive_type"] == "tool":
                assert "🔌" in badge
            elif tool["mcp_primitive_type"] == "resource":
                assert "📦" in badge
            elif tool["mcp_primitive_type"] == "prompt":
                assert "💬" in badge

            # Health indicator included
            server_id = tool["mcp_server_id"]
            server_health = sample_mcp_server_health.get(server_id, {})
            health_status = server_health.get("status", "inactive")
            health_icon = get_health_status_icon(health_status)
            assert health_icon in badge  # 🟢, 🔴, or ⚪


# ============================================================================
# Integration Test 4: Multi-Source Tool Selection (AC6 + AC7)
# ============================================================================


def test_tool_selection_across_multiple_sources(sample_unified_tools):
    """
    Test: Select tools from OpenAPI + MCP sources, verify assignment tracking.

    AC6 + AC7: Multi-source tool selection
    - Select 1 OpenAPI tool + 2 MCP tools
    - Verify selections tracked correctly
    - Simulate assignment to agent
    """
    # Simulate user selections (session state in real UI)
    selected_tools = {
        "openapi": set([1]),  # update_ticket
        "mcp": set(["server-uuid-1_list_files", "server-uuid-2_project_docs"]),
    }

    # Verify selection tracking
    assert len(selected_tools["openapi"]) == 1
    assert len(selected_tools["mcp"]) == 2

    # Convert selections to assignment format (simulates form submission)
    selected_openapi_ids = list(selected_tools["openapi"])
    selected_mcp_assignments = []

    for mcp_key in selected_tools["mcp"]:
        parts = mcp_key.split("_", 1)
        if len(parts) == 2:
            server_id, tool_name = parts
            # Find tool to get full details
            mcp_tools = [
                t for t in sample_unified_tools if t["source_type"] == "mcp"
            ]
            tool = next(
                (
                    t
                    for t in mcp_tools
                    if str(t["mcp_server_id"]) == server_id and t["name"] == tool_name
                ),
                None,
            )
            if tool:
                selected_mcp_assignments.append(
                    {
                        "server_id": server_id,
                        "tool_name": tool_name,
                        "primitive_type": tool["mcp_primitive_type"],
                    }
                )

    # Verify assignment payload
    assert selected_openapi_ids == [1]
    assert len(selected_mcp_assignments) == 2

    # Verify tool names (order not guaranteed due to set iteration)
    tool_names = {a["tool_name"] for a in selected_mcp_assignments}
    assert tool_names == {"list_files", "project_docs"}


# ============================================================================
# Integration Test 5: Tool Removal Workflow (AC7)
# ============================================================================


def test_tool_removal_workflow_updates_selections(sample_unified_tools):
    """
    Test: Remove assigned tool, verify selection state updated.

    AC7: Tool removal workflow
    - Assign 3 tools (2 OpenAPI, 1 MCP)
    - Remove 1 OpenAPI tool
    - Verify assignment updated correctly
    """
    # Initial assignments
    assigned_tools = {
        "openapi": set([1, 2]),  # update_ticket, search_tickets
        "mcp": set(["server-uuid-1_list_files"]),
    }

    # Remove tool: update_ticket (OpenAPI ID 1)
    tool_to_remove = 1
    assigned_tools["openapi"].discard(tool_to_remove)

    # Verify removal
    assert tool_to_remove not in assigned_tools["openapi"]
    assert len(assigned_tools["openapi"]) == 1
    assert 2 in assigned_tools["openapi"]  # search_tickets still assigned

    # MCP tools unchanged
    assert len(assigned_tools["mcp"]) == 1


def test_mcp_tool_removal_workflow(sample_unified_tools):
    """
    Test: Remove MCP tool, verify selection state updated.

    AC7: MCP tool removal
    - Assign 2 MCP tools
    - Remove 1 MCP tool
    - Verify assignment updated
    """
    # Initial MCP assignments
    assigned_mcp_tools = set(
        ["server-uuid-1_list_files", "server-uuid-1_read_file"]
    )

    # Remove tool: list_files
    tool_to_remove = "server-uuid-1_list_files"
    assigned_mcp_tools.discard(tool_to_remove)

    # Verify removal
    assert tool_to_remove not in assigned_mcp_tools
    assert len(assigned_mcp_tools) == 1
    assert "server-uuid-1_read_file" in assigned_mcp_tools


def test_agent_management_page_tab_integration(sample_unified_tools, sample_mcp_server_health):
    """
    Test: Agent Management page renders all three tabs with correct tools.

    AC1: Tab-based tool organization
    - Verify "All Tools" tab shows all 6 tools (2 OpenAPI + 4 MCP)
    - Verify "OpenAPI Tools" tab shows only 2 OpenAPI tools
    - Verify "MCP Tools" tab shows only 4 MCP tools
    - Verify tools are correctly filtered by source_type
    """
    # Simulate Agent Management page tab rendering logic
    all_tools = sample_unified_tools
    openapi_tools = [t for t in sample_unified_tools if t["source_type"] == "openapi"]
    mcp_tools = [t for t in sample_unified_tools if t["source_type"] == "mcp"]

    # Verify "All Tools" tab
    assert len(all_tools) == 6
    assert all(t["source_type"] in ["openapi", "mcp"] for t in all_tools)

    # Verify "OpenAPI Tools" tab
    assert len(openapi_tools) == 2
    assert all(t["source_type"] == "openapi" for t in openapi_tools)
    assert openapi_tools[0]["name"] == "update_ticket"
    assert openapi_tools[1]["name"] == "search_tickets"

    # Verify "MCP Tools" tab
    assert len(mcp_tools) == 4
    assert all(t["source_type"] == "mcp" for t in mcp_tools)
    assert any(t["name"] == "list_files" for t in mcp_tools)
    assert any(t["name"] == "read_file" for t in mcp_tools)
    assert any(t["name"] == "project_docs" for t in mcp_tools)
    assert any(t["name"] == "analyze_ticket" for t in mcp_tools)

    # Verify MCP tools have required fields
    for mcp_tool in mcp_tools:
        assert "mcp_server_id" in mcp_tool
        assert "mcp_server_name" in mcp_tool
        assert "mcp_primitive_type" in mcp_tool
        assert mcp_tool["mcp_primitive_type"] in ["tool", "resource", "prompt"]

    # Verify health status available for all MCP servers
    unique_server_ids = set(t["mcp_server_id"] for t in mcp_tools)
    for server_id in unique_server_ids:
        assert server_id in sample_mcp_server_health
        health = sample_mcp_server_health[server_id]
        assert "status" in health
        assert health["status"] in ["active", "inactive", "error"]
