"""
MCP Server List Display

Renders the main MCP server list view with tenant selector and action buttons.
Extracted from 12_MCP_Servers.py for maintainability (Story 12.7).

Features:
- Tenant selection with UUID → name mapping
- Server cards with status badges and transport indicators
- Action buttons: Details, Edit, Rediscover, Delete
- Capability counts (tools, resources, prompts)
- Last health check timestamps

References:
- Story 12.7: File Size Refactoring and Code Quality
- Story 11.1.9: Admin UI for MCP Server Management
- Story 11.2.4: Enhanced MCP Health Monitoring

Usage:
    from src.admin.utils.mcp_admin_ui import render_server_list

    render_server_list()  # Call from page main routing
"""

from datetime import datetime
from typing import Optional

import streamlit as st

from src.admin.utils.agent_helpers import fetch_available_tenants_with_ids
from src.admin.utils.mcp_ui_helpers import (
    delete_mcp_server,
    fetch_mcp_servers,
    format_timestamp,
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

    Example:
        >>> switch_view("add")  # Go to add server form
        >>> switch_view("details", server_uuid)  # Go to server details
    """
    st.session_state.mcp_view = view
    st.session_state.selected_server_id = server_id
    if view == "add":
        st.session_state.env_vars = []
        st.session_state.http_headers = []
        st.session_state.test_results = None


def render_server_list() -> None:
    """
    Render MCP server list view with actions.

    Main list view showing all MCP servers for selected tenant.
    Displays server cards with status, transport type, capabilities,
    and action buttons (details, edit, rediscover, delete).

    Session State:
        - tenant_id: Current tenant VARCHAR identifier (NOT UUID!)
        - confirm_delete_{server_id}: Delete confirmation state

    UI Elements:
        - Tenant selector dropdown (shows name + tenant_id)
        - Add Server button (primary action)
        - Server cards with:
          * Name, description, URL (for HTTP+SSE)
          * Transport and status badges
          * Tool/resource/prompt counts
          * Last health check timestamp
          * Action buttons (4 per server)
          * Delete confirmation warning

    Example:
        >>> # From page main routing:
        >>> if st.session_state.mcp_view == "list":
        >>>     render_server_list()
    """
    # Tenant selector row
    tenants = fetch_available_tenants_with_ids()
    if not tenants:
        st.info("No active tenants found. Create a tenant in 'Tenants' page.")
        return

    # Build mapping to display tenant name with identifier
    # IMPORTANT: Use tenant_id (VARCHAR) for API calls, not id (UUID)
    tenant_display = {t["tenant_id"]: f"{t['name']} ({t['tenant_id']})" for t in tenants}

    col_tenant, col_actions = st.columns([3, 1])
    with col_tenant:
        option_tenant_ids = [t["tenant_id"] for t in tenants]
        default_index = 0
        if st.session_state.tenant_id in option_tenant_ids:
            default_index = option_tenant_ids.index(st.session_state.tenant_id)
        selected_tenant_id = st.selectbox(
            "Select tenant",
            options=option_tenant_ids,
            index=default_index,
            format_func=lambda x: tenant_display.get(x, x),
            help=("Select tenant context. MCP API requires VARCHAR tenant_id."),
            key="mcp_tenant_selector",
        )
        # Store VARCHAR tenant_id for X-Tenant-ID header expected by MCP APIs
        st.session_state.tenant_id = selected_tenant_id

    col1, col2 = st.columns([3, 1])
    col1.subheader("Configured Servers")
    if col2.button("➕ Add MCP Server", use_container_width=True, type="primary"):
        switch_view("add")
        st.rerun()

    try:
        servers = fetch_mcp_servers(st.session_state.tenant_id)
        if not servers:
            st.info(
                "No MCP servers configured. Add your first server to enable MCP tool integration."
            )
            return

        for server in servers:
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 2, 2])

                with col1:
                    st.markdown(f"### {server['name']}")
                    if server.get("description"):
                        st.caption(server["description"])
                    # Show URL for HTTP+SSE servers
                    if server["transport_type"] == "http_sse" and server.get("url"):
                        st.caption(f"🌐 [{server['url']}]({server['url']})")

                with col2:
                    render_transport_badge(server["transport_type"])

                with col3:
                    render_status_badge(server["status"])

                with col4:
                    tools_count = len(server.get("discovered_tools", []))
                    resources_count = len(server.get("discovered_resources", []))
                    prompts_count = len(server.get("discovered_prompts", []))
                    st.markdown(
                        f"**{tools_count}** tools, **{resources_count}** resources, "
                        f"**{prompts_count}** prompts"
                    )
                    last_check = server.get("last_health_check")
                    if last_check:
                        ts = datetime.fromisoformat(last_check.replace("Z", "+00:00"))
                        st.caption(f"Last check: {format_timestamp(ts)}")

                with col5:
                    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
                    with btn_col1:
                        if st.button("📋", key=f"details_{server['id']}", help="View Details"):
                            switch_view("details", server["id"])
                            st.rerun()
                    with btn_col2:
                        if st.button("✏️", key=f"edit_{server['id']}", help="Edit"):
                            switch_view("edit", server["id"])
                            st.rerun()
                    with btn_col3:
                        if st.button("🔄", key=f"rediscover_{server['id']}", help="Rediscover"):
                            with st.spinner("Rediscovering capabilities..."):
                                try:
                                    updated = rediscover_server(
                                        server["id"], st.session_state.tenant_id
                                    )
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
                    with btn_col4:
                        if st.button("🗑️", key=f"delete_{server['id']}", help="Delete"):
                            if st.session_state.get(f"confirm_delete_{server['id']}"):
                                try:
                                    delete_mcp_server(server["id"], st.session_state.tenant_id)
                                    st.success(f"MCP server '{server['name']}' deleted")
                                    st.session_state[f"confirm_delete_{server['id']}"] = False
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Deletion failed: {str(e)}")
                            else:
                                st.session_state[f"confirm_delete_{server['id']}"] = True
                                st.rerun()

                if st.session_state.get(f"confirm_delete_{server['id']}"):
                    st.warning(
                        f"⚠️ **Confirm deletion of '{server['name']}'?** "
                        "This will remove the server configuration and all "
                        "discovered capabilities. Agents using tools from this server "
                        "will no longer function. Click Delete again to confirm, or "
                        "click another button to cancel."
                    )

                st.divider()

    except Exception as e:
        st.error(f"Failed to load MCP servers: {str(e)}")
