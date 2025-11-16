"""
MCP Server Detail View

Renders detailed view of an MCP server with configuration and capabilities.
Extracted from 12_MCP_Servers.py for maintainability (Story 12.7).

Features:
- Server information panel (transport, status, timestamps)
- Configuration display (stdio command/args/env, HTTP+SSE URL/headers)
- Health metrics dashboard (Story 11.2.4)
- Discovered capabilities tabs (tools, resources, prompts)
- Action buttons: Edit, Rediscover, Back
- Raw JSON view for debugging

References:
- Story 12.7: File Size Refactoring and Code Quality
- Story 11.1.9: Admin UI for MCP Server Management
- Story 11.2.4: Enhanced MCP Health Monitoring

Usage:
    from src.admin.utils.mcp_admin_ui import render_server_details

    render_server_details()  # Call from page main routing
"""

from datetime import datetime
from typing import Optional

import streamlit as st

from src.admin.utils.mcp_ui_helpers import (
    fetch_mcp_server_details,
    format_timestamp,
    is_sensitive_header,
    rediscover_server,
    render_status_badge,
    render_transport_badge,
)


def switch_view(view: str, server_id: Optional[str] = None) -> None:
    """
    Switch between MCP admin views.

    Updates session state to trigger view transition. Clears form state
    when switching to "add" view to ensure clean form.

    Args:
        view: Target view name ("list", "add", "edit", "details")
        server_id: Optional server UUID for "edit" or "details" views
    """
    st.session_state.mcp_view = view
    st.session_state.selected_server_id = server_id
    if view == "add":
        st.session_state.env_vars = []
        st.session_state.http_headers = []
        st.session_state.test_results = None


def render_server_details() -> None:
    """
    Render detailed view of an MCP server.

    Displays comprehensive server information including configuration,
    health metrics, and discovered capabilities (tools, resources, prompts).

    Session State:
        - selected_server_id: UUID of server to display
        - tenant_id: Current tenant context
        - metrics_period: Hours for health metrics (default: 24)

    UI Sections:
        1. Header with action buttons (Edit, Rediscover, Back)
        2. Server Information (transport, status, timestamps, errors)
        3. Configuration (transport-specific fields with masking)
        4. Health Metrics Dashboard (expandable, Story 11.2.4)
        5. Discovered Capabilities (tabs: Tools, Resources, Prompts)
        6. Raw JSON (expandable, for debugging)

    Configuration Display:
        - Stdio: command, args, environment variables (masked values)
        - HTTP+SSE: URL (clickable), headers (sensitive headers masked)

    Capabilities Display:
        - Tools: Name, description, input schema (JSON)
        - Resources: URI list with descriptions
        - Prompts: Name, description, arguments (JSON)

    Example:
        >>> # From page main routing:
        >>> if st.session_state.mcp_view == "details":
        >>>     render_server_details()
    """
    if not st.session_state.selected_server_id:
        st.error("No server selected")
        if st.button("← Back to List"):
            switch_view("list")
            st.rerun()
        return

    try:
        server = fetch_mcp_server_details(
            st.session_state.selected_server_id, st.session_state.tenant_id
        )

        # Header with actions
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        with col1:
            st.subheader(server["name"])
        with col2:
            if st.button("✏️ Edit", use_container_width=True):
                switch_view("edit", server["id"])
                st.rerun()
        with col3:
            if st.button("🔄 Rediscover", use_container_width=True):
                with st.spinner("Rediscovering capabilities..."):
                    try:
                        updated = rediscover_server(server["id"], st.session_state.tenant_id)
                        tools = len(updated.get("discovered_tools", []))
                        resources = len(updated.get("discovered_resources", []))
                        prompts = len(updated.get("discovered_prompts", []))
                        st.success(
                            f"Capabilities rediscovered. Found {tools} tools, "
                            f"{resources} resources, {prompts} prompts"
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"Rediscovery failed: {str(e)}")
        with col4:
            if st.button("← Back", use_container_width=True):
                switch_view("list")
                st.rerun()

        st.divider()

        # Server Information
        st.markdown("### Server Information")
        info_col1, info_col2, info_col3 = st.columns(3)

        with info_col1:
            st.markdown("**Transport Type:**")
            render_transport_badge(server["transport_type"])
            st.markdown("**Status:**")
            render_status_badge(server["status"])

        with info_col2:
            created = datetime.fromisoformat(server["created_at"].replace("Z", "+00:00"))
            st.markdown(f"**Created:** {created.strftime('%Y-%m-%d %H:%M')}")
            if server.get("last_health_check"):
                last_check = datetime.fromisoformat(
                    server["last_health_check"].replace("Z", "+00:00")
                )
                st.markdown(f"**Last Health Check:** {format_timestamp(last_check)}")

        with info_col3:
            if server.get("consecutive_failures", 0) > 0:
                st.markdown(f"**Consecutive Failures:** {server['consecutive_failures']}")
            if server.get("error_message"):
                st.markdown(f"**Error:** {server['error_message']}")

        if server.get("description"):
            st.markdown(f"**Description:** {server['description']}")

        st.divider()

        # Configuration
        st.markdown("### Configuration")
        if server["transport_type"] == "stdio":
            st.markdown(f"**Command:** `{server.get('command', 'N/A')}`")
            if server.get("args"):
                st.markdown("**Arguments:**")
                for arg in server["args"]:
                    st.markdown(f"- `{arg}`")
            if server.get("env"):
                st.markdown("**Environment Variables:**")
                for key in server["env"].keys():
                    st.markdown(f"- **{key}:** `*****` (masked)")
        elif server["transport_type"] == "http_sse":
            url = server.get("url", "N/A")
            st.markdown(f"**URL:** [{url}]({url})")
            if server.get("headers"):
                st.markdown("**HTTP Headers:**")
                for key, value in server["headers"].items():
                    # Mask sensitive headers
                    display_value = "***" if is_sensitive_header(key) else value
                    st.markdown(f"- **{key}:** `{display_value}`")

        st.divider()

        # Health Metrics Dashboard (Story 11.2.4)
        from src.admin.utils.mcp_ui_helpers import render_health_metrics_dashboard

        with st.expander("📊 Health Metrics Dashboard", expanded=True):
            render_health_metrics_dashboard(
                server_id=server["id"],
                tenant_id=st.session_state.tenant_id,
                period_hours=st.session_state.get("metrics_period", 24),
            )

        st.divider()

        # Discovered Capabilities
        st.markdown("### Discovered Capabilities")

        tab1, tab2, tab3 = st.tabs(["🔧 Tools", "📁 Resources", "💬 Prompts"])

        with tab1:
            tools = server.get("discovered_tools", [])
            if tools:
                for tool in tools:
                    with st.expander(f"**{tool.get('name', 'Unnamed Tool')}**"):
                        if tool.get("description"):
                            st.markdown(f"*{tool['description']}*")
                        if tool.get("input_schema"):
                            st.json(tool["input_schema"])
            else:
                st.info("No tools discovered")

        with tab2:
            resources = server.get("discovered_resources", [])
            if resources:
                for resource in resources:
                    st.markdown(f"- **{resource.get('uri', 'N/A')}**")
                    if resource.get("description"):
                        st.caption(resource["description"])
            else:
                st.info("No resources discovered")

        with tab3:
            prompts = server.get("discovered_prompts", [])
            if prompts:
                for prompt in prompts:
                    with st.expander(f"**{prompt.get('name', 'Unnamed Prompt')}**"):
                        if prompt.get("description"):
                            st.markdown(f"*{prompt['description']}*")
                        if prompt.get("arguments"):
                            st.json(prompt["arguments"])
            else:
                st.info("No prompts discovered")

        # Raw JSON
        with st.expander("🔍 Raw JSON"):
            st.json(server)

    except Exception as e:
        st.error(f"Failed to load server details: {str(e)}")
        if st.button("← Back to List"):
            switch_view("list")
            st.rerun()
