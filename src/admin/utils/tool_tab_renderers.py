"""
Tool Tab Renderers - MCP Tool Discovery Tab Rendering Logic.

Provides tab-specific rendering functions for tool assignment UI:
- Render individual tool tabs with search, filter, selection controls
- Render tool checkboxes with badges and health indicators
- Handle tool selection state management

Story: 11.2.5 - MCP Tool Discovery in Agent Tools UI
Split from tool_assignment_ui_helpers.py for file size compliance (C1)
"""

from typing import Any

import streamlit as st

from admin.utils.tool_assignment_ui_helpers import (
    count_tools_by_server,
    filter_by_mcp_server,
    get_unique_server_names,
    render_health_tooltip,
    render_tool_badge,
    search_tools,
)


# ============================================================================
# Tab Rendering Functions
# ============================================================================


def render_tool_tab(
    tools: list[dict[str, Any]],
    health_status: dict[str, dict[str, Any]],
    show_mcp_filter: bool,
    tab_name: str,
    in_form_context: bool = False,
    key_prefix: str = "",
) -> None:
    """
    Render a single tool tab with search, filter, and selection controls.

    Args:
        tools: List of tools to display in this tab
        health_status: MCP server health status dict
        show_mcp_filter: Whether to show MCP server filter (AC4)
        tab_name: Tab identifier (prefixed with key_prefix)
        in_form_context: If True, skip rendering buttons (Streamlit forms don't allow st.button)
        key_prefix: Unique prefix for widget keys (e.g., "edit_" for dialog)
    """
    # Namespace session state keys
    tool_search_key = f"{key_prefix}tool_search"
    mcp_filter_key = f"{key_prefix}mcp_server_filter"
    selected_tools_key = f"{key_prefix}selected_tools"

    # AC5: Search functionality
    search_query = st.text_input(
        "🔍 Search tools",
        value=st.session_state.get(tool_search_key, ""),
        placeholder="Search by name or description...",
        key=f"search_{tab_name}",
        help="Case-insensitive search across tool names and descriptions",
    )
    st.session_state[tool_search_key] = search_query

    # AC4: MCP Server filter (only in MCP Tools tab)
    filtered_tools = tools
    if show_mcp_filter and tools:
        unique_servers = get_unique_server_names(tools)
        tool_counts = count_tools_by_server(tools)

        # Format server options with counts
        server_options_with_counts = [
            f"{server} ({tool_counts.get(server, 0)} tools)" for server in unique_servers
        ]

        # Show helpful tip when multiple servers with many tools
        if len(unique_servers) > 0 and any(count > 10 for count in tool_counts.values()):
            st.info(
                "💡 **Tip:** To quickly select all tools from a server, "
                "use the filter below to show only that server's tools, "
                "then click '✅ Select All'."
            )

        selected_servers_with_counts = st.multiselect(
            "Filter by MCP Server",
            options=server_options_with_counts,
            default=[],
            key=f"server_filter_{tab_name}",
            help="Select one or more MCP servers to filter tools",
        )

        # Extract server names from formatted options
        selected_servers = [opt.split(" (")[0] for opt in selected_servers_with_counts]

        if selected_servers:
            filtered_tools = filter_by_mcp_server(tools, selected_servers)
            st.session_state[mcp_filter_key] = selected_servers

            # Show helpful message when filtering by a specific server
            if len(selected_servers) == 1:
                server_name = selected_servers[0]
                tool_count = tool_counts.get(server_name, 0)
                st.success(
                    f"📋 Filtered to **{tool_count} tools** from **{server_name}**. "
                    f"Use '✅ Select All' below to select all these tools at once."
                )

    # Apply search filter
    if search_query:
        filtered_tools = search_tools(filtered_tools, search_query)

    # Display tool count
    st.caption(f"Showing {len(filtered_tools)} of {len(tools)} tools")

    # AC6: Select All / Deselect All buttons (skip in form context - forms don't allow st.button)
    if not in_form_context:
        col1, col2, col3 = st.columns([1, 1, 3])

        # Determine button labels based on filter context
        select_label = "✅ Select All"
        if show_mcp_filter and mcp_filter_key in st.session_state and st.session_state[mcp_filter_key]:
            server_count = len(st.session_state[mcp_filter_key])
            if server_count == 1:
                server_name = st.session_state[mcp_filter_key][0]
                select_label = f"✅ Select All from {server_name}"

        with col1:
            if st.button(select_label, key=f"select_all_{tab_name}", use_container_width=True, type="primary"):
                select_all_tools(filtered_tools, key_prefix)
                st.rerun()

        with col2:
            if st.button("⬜ Deselect All", key=f"deselect_all_{tab_name}", use_container_width=True):
                deselect_all_tools(filtered_tools, key_prefix)
                st.rerun()

        with col3:
            # AC6: Show selected count
            selected_count = count_selected_tools(key_prefix)
            st.info(f"📋 {selected_count} tools selected")
    else:
        # In form context, just show the selected count without buttons
        selected_count = count_selected_tools(key_prefix)
        st.info(f"📋 {selected_count} tools selected")

    # Render tool list with checkboxes (AC2, AC3, AC6)
    if not filtered_tools:
        st.info("No tools found matching your criteria.")
        return

    st.markdown("---")
    for tool in filtered_tools:
        render_tool_checkbox(tool, health_status, tab_name, key_prefix)


def render_tool_checkbox(
    tool: dict[str, Any], health_status: dict[str, dict[str, Any]], tab_name: str, key_prefix: str = ""
) -> None:
    """
    Render a single tool checkbox with badge, description, and health indicator.

    Args:
        tool: UnifiedTool dict
        health_status: MCP server health status dict
        tab_name: Tab identifier for unique keys
        key_prefix: Unique prefix for session state keys
    """
    selected_tools_key = f"{key_prefix}selected_tools"

    tool_id = tool.get("id")
    tool_name = tool.get("name", "Unknown")
    tool_desc = tool.get("description", "No description")
    source_type = tool.get("source_type", "openapi")

    # Determine if tool is selected (using namespaced session state)
    if source_type == "openapi":
        is_selected = tool_id in st.session_state[selected_tools_key]["openapi"]
    else:
        server_id = str(tool.get("mcp_server_id", ""))
        mcp_key = f"{server_id}_{tool_name}"
        is_selected = mcp_key in st.session_state[selected_tools_key]["mcp"]

    # Render checkbox with badge (AC2, AC3)
    col1, col2 = st.columns([0.1, 0.9])

    with col1:
        checkbox_key = f"tool_checkbox_{tab_name}_{tool_id}"

        # CRITICAL FIX: Force widget state to match our selection state
        # Streamlit's checkbox 'value' only sets default, actual state is in st.session_state[key]
        st.session_state[checkbox_key] = is_selected

        # Use on_change callback to only toggle when user clicks, not during render sync
        st.checkbox(
            label="",
            key=checkbox_key,
            label_visibility="collapsed",
            on_change=toggle_tool_selection,
            args=(tool, key_prefix),
        )

    with col2:
        # AC2: Render tool badge with icon, type, server name
        badge = render_tool_badge(tool, health_status, show_health=True)
        st.markdown(f"**{badge}**")

        # Show description
        st.caption(tool_desc)

        # AC3: Show health tooltip for MCP tools
        if source_type == "mcp":
            server_id = str(tool.get("mcp_server_id", ""))
            if server_id and server_id in health_status:
                tooltip = render_health_tooltip(server_id, health_status)
                with st.expander("🔍 Server Health Details", expanded=False):
                    st.caption(tooltip)

    st.markdown("---")


def render_assigned_tools_summary(
    openapi_tools: list[dict[str, Any]],
    mcp_tools: list[dict[str, Any]],
    health_status: dict[str, dict[str, Any]],
    in_form_context: bool = False,
    key_prefix: str = "",
) -> None:
    """
    Render summary of assigned tools with source type badges (AC7).

    Args:
        openapi_tools: List of OpenAPI tools
        mcp_tools: List of MCP tools
        health_status: MCP server health status dict
        in_form_context: If True, skip rendering remove buttons (forms don't allow st.button)
        key_prefix: Unique prefix for widget keys (e.g., "edit_" for dialog)
    """
    selected_tools_key = f"{key_prefix}selected_tools"

    st.markdown("---")
    st.subheader("📌 Assigned Tools Summary")

    total_selected = count_selected_tools(key_prefix)

    if total_selected == 0:
        st.info("ℹ️ No tools selected. Select tools from the tabs above.")
        return

    st.success(f"✅ {total_selected} tools assigned")

    # Show OpenAPI tools
    selected_openapi = [
        t for t in openapi_tools if t.get("id") in st.session_state[selected_tools_key]["openapi"]
    ]

    if selected_openapi:
        st.markdown("**🔧 OpenAPI Tools:**")
        for tool in selected_openapi:
            badge = render_tool_badge(tool, health_status, show_health=False)
            if in_form_context:
                # In form context, just show the badge without remove button
                st.markdown(f"- {badge}")
            else:
                # Outside form, show badge with remove button
                col1, col2 = st.columns([0.9, 0.1])
                with col1:
                    st.markdown(f"- {badge}")
                with col2:
                    if st.button("✕", key=f"{key_prefix}remove_openapi_{tool.get('id')}", help="Remove tool"):
                        st.session_state[selected_tools_key]["openapi"].remove(tool.get("id"))
                        st.rerun()

    # Show MCP tools
    selected_mcp: list[dict[str, Any]] = []
    for mcp_key in st.session_state[selected_tools_key]["mcp"]:
        parts = mcp_key.split("_", 1)
        if len(parts) == 2:
            server_id, tool_name = parts
            mcp_tool: dict[str, Any] | None = next(
                (
                    t
                    for t in mcp_tools
                    if str(t.get("mcp_server_id")) == server_id and t.get("name") == tool_name
                ),
                None,
            )
            if mcp_tool is not None:
                selected_mcp.append(mcp_tool)

    if selected_mcp:
        st.markdown("**🔌 MCP Tools:**")
        for mcp_tool_item in selected_mcp:
            badge = render_tool_badge(mcp_tool_item, health_status, show_health=True)
            server_id = str(mcp_tool_item.get("mcp_server_id", ""))
            tool_name = mcp_tool_item.get("name", "")
            mcp_key = f"{server_id}_{tool_name}"

            if in_form_context:
                # In form context, just show the badge without remove button
                st.markdown(f"- {badge}")
            else:
                # Outside form, show badge with remove button
                col1, col2 = st.columns([0.9, 0.1])
                with col1:
                    st.markdown(f"- {badge}")
                with col2:
                    if st.button("✕", key=f"{key_prefix}remove_mcp_{mcp_key}", help="Remove tool"):
                        st.session_state[selected_tools_key]["mcp"].remove(mcp_key)
                        st.success(f"✅ Tool '{tool_name}' removed from agent")
                        st.rerun()


# ============================================================================
# Selection State Management Functions
# ============================================================================


def toggle_tool_selection(tool: dict[str, Any], key_prefix: str = "") -> None:
    """
    Toggle tool selection state.

    Args:
        tool: UnifiedTool dict
        key_prefix: Unique prefix for session state keys
    """
    selected_tools_key = f"{key_prefix}selected_tools"
    source_type = tool.get("source_type")

    if source_type == "openapi":
        tool_id = tool.get("id")
        if tool_id in st.session_state[selected_tools_key]["openapi"]:
            st.session_state[selected_tools_key]["openapi"].remove(tool_id)
        else:
            st.session_state[selected_tools_key]["openapi"].add(tool_id)
    else:
        server_id = str(tool.get("mcp_server_id", ""))
        tool_name = tool.get("name", "")
        mcp_key = f"{server_id}_{tool_name}"

        if mcp_key in st.session_state[selected_tools_key]["mcp"]:
            st.session_state[selected_tools_key]["mcp"].remove(mcp_key)
        else:
            st.session_state[selected_tools_key]["mcp"].add(mcp_key)


def select_all_tools(tools: list[dict[str, Any]], key_prefix: str = "") -> None:
    """Select all tools in the filtered list.

    Args:
        tools: List of tools to select
        key_prefix: Unique prefix for session state keys
    """
    selected_tools_key = f"{key_prefix}selected_tools"

    for tool in tools:
        source_type = tool.get("source_type")
        if source_type == "openapi":
            tool_id = tool.get("id")
            st.session_state[selected_tools_key]["openapi"].add(tool_id)
        else:
            server_id = str(tool.get("mcp_server_id", ""))
            tool_name = tool.get("name", "")
            mcp_key = f"{server_id}_{tool_name}"
            st.session_state[selected_tools_key]["mcp"].add(mcp_key)


def deselect_all_tools(tools: list[dict[str, Any]], key_prefix: str = "") -> None:
    """Deselect all tools in the filtered list.

    Args:
        tools: List of tools to deselect
        key_prefix: Unique prefix for session state keys
    """
    selected_tools_key = f"{key_prefix}selected_tools"

    for tool in tools:
        source_type = tool.get("source_type")
        if source_type == "openapi":
            tool_id = tool.get("id")
            st.session_state[selected_tools_key]["openapi"].discard(tool_id)
        else:
            server_id = str(tool.get("mcp_server_id", ""))
            tool_name = tool.get("name", "")
            mcp_key = f"{server_id}_{tool_name}"
            st.session_state[selected_tools_key]["mcp"].discard(mcp_key)


def count_selected_tools(key_prefix: str = "") -> int:
    """Count total selected tools across all source types.

    Args:
        key_prefix: Unique prefix for session state keys

    Returns:
        Total count of selected tools
    """
    selected_tools_key = f"{key_prefix}selected_tools"

    openapi_count = len(st.session_state[selected_tools_key]["openapi"])
    mcp_count = len(st.session_state[selected_tools_key]["mcp"])
    return openapi_count + mcp_count
