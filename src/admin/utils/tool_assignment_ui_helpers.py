"""
Tool Assignment UI Helpers - MCP Tool Discovery and Badge Rendering.

Provides UI components for displaying and filtering tools in Agent Management:
- Fetch unified tools (OpenAPI + MCP) with caching
- Fetch MCP server health status with caching
- Render visual badges for tool types (OpenAPI, MCP Tool, Resource, Prompt)
- Search and filter tools by name/description and MCP server
- Health status indicators with tooltips

Story: 11.2.5 - MCP Tool Discovery in Agent Tools UI
Follows 2025 Streamlit best practices (Context7 MCP validated)
"""

import os
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
import streamlit as st

# ============================================================================
# Configuration
# ============================================================================

API_BASE_URL: str = os.getenv("API_BASE_URL", "http://api:8000")


# ============================================================================
# Cached API Fetching (AC8: Performance and Caching)
# ============================================================================


@st.cache_data(ttl=60, show_spinner=False)
def fetch_unified_tools(tenant_id: str) -> list[dict[str, Any]]:
    """
    Fetch all tools (OpenAPI + MCP) for tenant. Cached 60s.

    Calls GET /api/v1/unified-tools endpoint and returns combined tool list
    with source_type, mcp_server_id, mcp_server_name, mcp_primitive_type fields.

    Args:
        tenant_id: Tenant UUID for filtering tools

    Returns:
        list[dict]: List of UnifiedTool dicts or empty list on error

    Performance:
        - First call: <500ms (database query)
        - Cached calls: <10ms (in-memory cache hit)
        - Cache TTL: 60 seconds

    Example:
        tools = fetch_unified_tools("test-tenant-id")
        openapi_tools = [t for t in tools if t["source_type"] == "openapi"]
        mcp_tools = [t for t in tools if t["source_type"] == "mcp"]
    """
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{API_BASE_URL}/api/v1/unified-tools/",
                headers={"X-Tenant-ID": tenant_id},
            )
            response.raise_for_status()
            tools = response.json()
            return tools if isinstance(tools, list) else []
    except httpx.HTTPError as e:
        st.warning(f"⚠️ Could not load tools: {str(e)}")
        return []


@st.cache_data(ttl=60, show_spinner=False)
def fetch_mcp_server_health(tenant_id: str) -> dict[str, dict[str, Any]]:
    """
    Fetch MCP server health status. Cached 60s. Returns dict keyed by server_id.

    Calls GET /api/v1/mcp-servers endpoint to retrieve server health status
    (active/inactive/error), last_health_check timestamp, and error messages.

    Args:
        tenant_id: Tenant UUID for filtering servers

    Returns:
        dict: Mapping of server_id -> {id, name, status, last_health_check, error_message}
        Empty dict on error

    Performance:
        - Cache TTL: 60 seconds (aligns with 30s health check interval)

    Example:
        health_status = fetch_mcp_server_health("test-tenant-id")
        server_status = health_status.get("server-uuid-1", {}).get("status")
        # Returns: "active", "inactive", or "error"
    """
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{API_BASE_URL}/api/v1/mcp-servers/",
                headers={"X-Tenant-ID": tenant_id},
            )
            response.raise_for_status()
            data = response.json()
            # Endpoint returns list of servers directly (not wrapped in {"servers": [...]})
            servers = data if isinstance(data, list) else []
            # Return dict keyed by server_id for O(1) lookup
            return {str(s["id"]): s for s in servers}
    except httpx.HTTPError as e:
        st.warning(f"⚠️ Could not load MCP server health: {str(e)}")
        return {}


# ============================================================================
# Badge Rendering (AC2: Visual Tool Type Indicators)
# ============================================================================


def render_tool_badge(
    tool: dict[str, Any], health_status: dict[str, dict[str, Any]], show_health: bool = True
) -> str:
    """
    Render visual badge for tool with icon, type, server name, health indicator.

    Creates formatted string with emoji icon, tool type badge, and optional
    MCP server name + health status indicator. Uses consistent color coding:
    - OpenAPI: 🔧 (blue)
    - MCP Tool: 🔌 (green)
    - MCP Resource: 📦 (purple)
    - MCP Prompt: 💬 (orange)

    Args:
        tool: UnifiedTool dict with source_type, mcp_server_name, mcp_primitive_type
        health_status: Dict mapping server_id -> server health metadata
        show_health: Whether to display health status indicator (default: True)

    Returns:
        str: Formatted badge string for display

    Example:
        badge = render_tool_badge(tool, health_status)
        # Returns: "🔧 OpenAPI | update_ticket"
        # Or: "🔌 MCP Tool | list_files | [filesystem-server] 🟢"
    """
    source_type = tool.get("source_type", "openapi")
    name = tool.get("name", "Unknown")

    # Base icon and type badge
    if source_type == "openapi":
        icon = "🔧"
        type_badge = "OpenAPI"
    else:  # source_type == "mcp"
        primitive_type = tool.get("mcp_primitive_type", "tool")
        if primitive_type == "tool":
            icon = "🔌"
            type_badge = "MCP Tool"
        elif primitive_type == "resource":
            icon = "📦"
            type_badge = "MCP Resource"
        elif primitive_type == "prompt":
            icon = "💬"
            type_badge = "MCP Prompt"
        else:
            icon = "🔌"
            type_badge = "MCP Tool"

    # Build badge string
    badge_parts = [icon, type_badge, "|", name]

    # Add MCP server name and health status if applicable
    if source_type == "mcp":
        server_name = tool.get("mcp_server_name")
        server_id = tool.get("mcp_server_id")

        if server_name:
            badge_parts.append(f"| [{server_name}]")

        # Add health status indicator
        if show_health and server_id:
            server_health = health_status.get(str(server_id), {})
            status = server_health.get("status", "inactive")
            health_icon = get_health_status_icon(status)
            badge_parts.append(health_icon)

    return " ".join(badge_parts)


def get_health_status_icon(status: str) -> str:
    """
    Get health status emoji icon.

    Args:
        status: Health status ("active", "inactive", "error")

    Returns:
        str: Emoji icon (🟢 active, 🔴 error, ⚪ inactive)
    """
    status_icons = {
        "active": "🟢",
        "error": "🔴",
        "inactive": "⚪",
    }
    return status_icons.get(status, "⚪")


def render_health_tooltip(server_id: str, health_status: dict[str, dict[str, Any]]) -> str:
    """
    Render health status tooltip text.

    Creates human-readable tooltip showing server name, status, last health
    check timestamp (relative), and error message if applicable.

    Args:
        server_id: MCP server UUID (as string)
        health_status: Dict mapping server_id -> server health metadata

    Returns:
        str: Formatted tooltip text

    Example:
        tooltip = render_health_tooltip(server_id, health_status)
        # Returns: "filesystem-server | Active | Last checked: 2 minutes ago"
    """
    server = health_status.get(str(server_id), {})
    if not server:
        return "Status unknown"

    server_name = server.get("name", "Unknown")
    status = server.get("status", "inactive")
    last_check = server.get("last_health_check")
    error_msg = server.get("error_message")

    # Format status text
    status_text = status.capitalize()

    # Format relative time
    time_text = format_relative_time(last_check) if last_check else "Never"

    # Build tooltip
    tooltip_parts = [
        f"{server_name}",
        f"{status_text}",
        f"Last checked: {time_text}",
    ]

    if error_msg and status == "error":
        tooltip_parts.append(f"Error: {error_msg}")

    return " | ".join(tooltip_parts)


def format_relative_time(iso_timestamp: Optional[str]) -> str:
    """
    Format ISO timestamp as relative time (e.g., "2 minutes ago").

    Args:
        iso_timestamp: ISO 8601 formatted timestamp string

    Returns:
        str: Human-readable relative time string

    Example:
        time_str = format_relative_time("2025-11-10T10:00:00Z")
        # Returns: "2 minutes ago" (if current time is 10:02)
    """
    if not iso_timestamp:
        return "Never"

    try:
        # Parse ISO timestamp
        timestamp = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)

        # Calculate time difference
        delta = now - timestamp
        seconds = delta.total_seconds()

        # Format as relative time
        if seconds < 60:
            return f"{int(seconds)} seconds ago"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = int(seconds / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"
    except (ValueError, AttributeError):
        return "Unknown"


# ============================================================================
# Search and Filter Functions (AC4, AC5)
# ============================================================================


def search_tools(tools: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    """
    Case-insensitive partial match on tool name or description.

    Args:
        tools: List of UnifiedTool dicts
        query: Search query string

    Returns:
        list[dict]: Filtered list of tools matching query

    Example:
        filtered = search_tools(all_tools, "ticket")
        # Returns all tools with "ticket" in name or description
    """
    if not query:
        return tools

    query_lower = query.lower()
    return [
        t
        for t in tools
        if query_lower in t.get("name", "").lower()
        or query_lower in t.get("description", "").lower()
    ]


def filter_by_mcp_server(
    tools: list[dict[str, Any]], server_names: list[str]
) -> list[dict[str, Any]]:
    """
    Filter MCP tools by server name.

    Args:
        tools: List of UnifiedTool dicts
        server_names: List of MCP server names to include

    Returns:
        list[dict]: Filtered list of tools from selected servers

    Example:
        filtered = filter_by_mcp_server(mcp_tools, ["filesystem-server", "docs-server"])
    """
    if not server_names:
        return tools

    return [t for t in tools if t.get("mcp_server_name") in server_names]


def get_unique_server_names(tools: list[dict[str, Any]]) -> list[str]:
    """
    Extract unique MCP server names from tool list.

    Args:
        tools: List of UnifiedTool dicts

    Returns:
        list[str]: Sorted list of unique server names

    Example:
        servers = get_unique_server_names(mcp_tools)
        # Returns: ["docs-server", "filesystem-server"]
    """
    server_names = set()
    for tool in tools:
        server_name = tool.get("mcp_server_name")
        if server_name:
            server_names.add(server_name)

    return sorted(list(server_names))


def count_tools_by_server(tools: list[dict[str, Any]]) -> dict[str, int]:
    """
    Count tools per MCP server.

    Args:
        tools: List of UnifiedTool dicts

    Returns:
        dict: Mapping of server_name -> tool_count

    Example:
        counts = count_tools_by_server(mcp_tools)
        # Returns: {"filesystem-server": 5, "docs-server": 3}
    """
    counts: dict[str, int] = {}
    for tool in tools:
        server_name = tool.get("mcp_server_name")
        if server_name:
            counts[server_name] = counts.get(server_name, 0) + 1

    return counts


# ============================================================================
# Main Tool Assignment UI Component (AC1-AC7)
# ============================================================================


def render_unified_tool_list(
    tenant_id: str,
    selected_tool_ids: list[int] | None = None,
    selected_mcp_tools: list[dict[str, Any]] | None = None,
    in_form_context: bool = False,
    key_prefix: str = "",
) -> tuple[list[int], list[dict[str, Any]]]:
    """
    Render comprehensive tool assignment UI with tabs, filters, badges, and health indicators.

    Implements AC1-AC7 from Story 11.2.5:
    - AC1: Tab-based organization (All Tools, OpenAPI Tools, MCP Tools)
    - AC2: Visual tool type indicators (🔧 OpenAPI, 🔌 MCP Tool, 📦 Resource, 💬 Prompt)
    - AC3: MCP server health status display (🟢 active, 🔴 error, ⚪ inactive)
    - AC4: Filter by MCP server name (multiselect)
    - AC5: Search across all tool sources
    - AC6: Multi-select tool assignment with checkboxes
    - AC7: Assigned tools display with source type badges

    Args:
        tenant_id: Tenant UUID for filtering tools and servers
        selected_tool_ids: List of pre-selected OpenAPI tool IDs (integers)
        selected_mcp_tools: List of pre-selected MCP tool assignments (dicts)
        in_form_context: If True, skip rendering buttons (Streamlit forms don't allow st.button)
        key_prefix: Unique prefix for widget keys (e.g., "edit_" for dialog, "" for main page)

    Returns:
        tuple: (openapi_tool_ids, mcp_tool_assignments)
            - openapi_tool_ids: List of selected OpenAPI tool IDs (integers)
            - mcp_tool_assignments: List of MCP tool assignment dicts

    Example:
        openapi_ids, mcp_assignments = render_unified_tool_list(
            tenant_id="test-tenant-id",
            selected_tool_ids=[1, 2, 3],
            selected_mcp_tools=[{"server_id": "...", "tool_name": "list_files"}],
            key_prefix="edit_"
        )
    """
    # Import tab renderers (split for C1 file size compliance)
    from admin.utils.tool_tab_renderers import (
        render_tool_tab,
        render_assigned_tools_summary,
    )

    # Initialize return values
    selected_tool_ids = selected_tool_ids or []
    selected_mcp_tools = selected_mcp_tools or []

    # CRITICAL FIX: Namespace session state keys with key_prefix to avoid conflicts
    # Main page uses "" prefix, edit dialog uses "edit_" prefix
    tools_tab_key = f"{key_prefix}tools_tab"
    mcp_filter_key = f"{key_prefix}mcp_server_filter"
    tool_search_key = f"{key_prefix}tool_search"
    selected_tools_key = f"{key_prefix}selected_tools"

    # Initialize session state for UI controls (AC1, AC4, AC5, AC6)
    if tools_tab_key not in st.session_state:
        st.session_state[tools_tab_key] = 0  # Default to "All Tools" tab

    if mcp_filter_key not in st.session_state:
        st.session_state[mcp_filter_key] = []

    if tool_search_key not in st.session_state:
        st.session_state[tool_search_key] = ""

    # Initialize selected_tools only once per key_prefix namespace
    if selected_tools_key not in st.session_state:
        st.session_state[selected_tools_key] = {
            "openapi": set(selected_tool_ids),
            "mcp": {f"{t.get('mcp_server_id')}_{t.get('name')}" for t in selected_mcp_tools},
        }

    # Fetch data with caching (AC8: Performance)
    with st.spinner("Loading tools..."):
        tools = fetch_unified_tools(tenant_id)
        health_status = fetch_mcp_server_health(tenant_id)

    # Separate tools by source type (even if empty, render UI structure)
    all_tools = tools or []
    openapi_tools = [t for t in all_tools if t.get("source_type") == "openapi"]
    mcp_tools = [t for t in all_tools if t.get("source_type") == "mcp"]

    # AC1: Tab-based organization
    st.subheader("🛠️ Tool Assignment")

    # Show warning if no tools available, but still render UI
    if not tools:
        st.info("ℹ️ No tools available for this tenant. Configure OpenAPI tools or MCP servers first to assign them to this agent.")
    tab1, tab2, tab3 = st.tabs(["All Tools", "OpenAPI Tools", "MCP Tools"])

    # Track which tab is active (for styling/logic purposes)
    with tab1:
        render_tool_tab(
            tools=all_tools,
            health_status=health_status,
            show_mcp_filter=False,
            tab_name=f"{key_prefix}all",
            in_form_context=in_form_context,
            key_prefix=key_prefix,
        )

    with tab2:
        render_tool_tab(
            tools=openapi_tools,
            health_status=health_status,
            show_mcp_filter=False,
            tab_name=f"{key_prefix}openapi",
            in_form_context=in_form_context,
            key_prefix=key_prefix,
        )

    with tab3:
        render_tool_tab(
            tools=mcp_tools,
            health_status=health_status,
            show_mcp_filter=True,
            tab_name=f"{key_prefix}mcp",
            in_form_context=in_form_context,
            key_prefix=key_prefix,
        )

    # AC7: Display assigned tools with source type badges
    render_assigned_tools_summary(
        openapi_tools=openapi_tools,
        mcp_tools=mcp_tools,
        health_status=health_status,
        in_form_context=in_form_context,
        key_prefix=key_prefix,
    )

    # Convert session state selections back to return format (using namespaced key)
    selected_openapi_ids = list(st.session_state[selected_tools_key]["openapi"])
    selected_mcp_assignments = []

    for mcp_key in st.session_state[selected_tools_key]["mcp"]:
        parts = mcp_key.split("_", 1)
        if len(parts) == 2:
            server_id, tool_name = parts
            # Find the tool to get full details
            tool = next(
                (
                    t
                    for t in mcp_tools
                    if str(t.get("mcp_server_id")) == server_id and t.get("name") == tool_name
                ),
                None,
            )
            if tool:
                # Return dict with correct MCPToolAssignment schema field names
                selected_mcp_assignments.append(
                    {
                        "id": tool.get("id"),
                        "name": tool.get("name"),
                        "source_type": "mcp",
                        "mcp_server_id": tool.get("mcp_server_id"),
                        "mcp_server_name": tool.get("mcp_server_name"),
                        "mcp_primitive_type": tool.get("mcp_primitive_type", "tool"),
                    }
                )

    return selected_openapi_ids, selected_mcp_assignments
