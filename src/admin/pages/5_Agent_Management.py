"""
Agent Management Page - Comprehensive AI Agent CRUD Interface.

Implements full agent management for AI Agents admin UI:
- View all agents with search/filter/pagination
- Create agents with multi-tab form (Basic Info, LLM Config, System Prompt, Triggers, Tools)
- Edit existing agents with form validation
- Delete agents with soft delete confirmation
- Manage agent status (draft→active, active→suspended)
- Display webhook URLs with copy functionality
- Form validation with helpful error messages
- MCP Tool Discovery UI with tabs, badges, health status (Story 11.2.5)

Story: 8.4 - Agent Management UI (Basic)
Story: 11.2.5 - MCP Tool Discovery in Agent Tools UI
Depends on Story 8.3 (Agent CRUD API Endpoints) for REST endpoints

Helper modules:
- src/admin/utils/agent_helpers.py: API calls and form validation
- src/admin/components/agent_forms.py: Dialog forms (create, edit, delete, detail)
- src/admin/utils/tool_assignment_ui_helpers.py: MCP tool discovery helpers (Story 11.2.5)
- src/admin/utils/tool_tab_renderers.py: Tool tab rendering (Story 11.2.5)
"""

import pandas as pd
import streamlit as st

from admin.components.agent_forms import (
    agent_detail_view,
    create_agent_form,
    delete_agent_confirm,
    edit_agent_form,
)
from admin.utils.agent_helpers import (
    AVAILABLE_TOOLS,
    activate_agent_async,
    async_to_sync,
    fetch_agent_detail_async,
    fetch_agents_async,
    fetch_available_tenants,
    format_datetime,
    format_status_badge,
)
from admin.utils.tool_assignment_ui_helpers import (
    fetch_mcp_server_health,
    fetch_unified_tools,
)
from admin.utils.tool_tab_renderers import (
    render_assigned_tools_summary,
    render_tool_tab,
)


# ============================================================================
# Session State Initialization
# ============================================================================


def initialize_session_state():
    """Initialize all session state variables."""
    if "agents_list" not in st.session_state:
        st.session_state.agents_list = []
    if "selected_agent_id" not in st.session_state:
        st.session_state.selected_agent_id = None
    if "selected_agent" not in st.session_state:
        st.session_state.selected_agent = None
    if "show_create_form" not in st.session_state:
        st.session_state.show_create_form = False
    if "show_edit_form" not in st.session_state:
        st.session_state.show_edit_form = False
    if "show_delete_form" not in st.session_state:
        st.session_state.show_delete_form = False
    if "show_detail_view" not in st.session_state:
        st.session_state.show_detail_view = False
    if "refresh_trigger" not in st.session_state:
        st.session_state.refresh_trigger = 0

    # Story 11.2.5: MCP Tool Discovery session state (AC6)
    if "selected_tools" not in st.session_state:
        st.session_state.selected_tools = {
            "openapi": set(),  # Set of OpenAPI tool IDs
            "mcp": set(),  # Set of MCP tool keys (server_id_tool_name format)
        }
    if "tools_tab" not in st.session_state:
        st.session_state.tools_tab = 0  # AC1: Tab state persistence (0=All, 1=OpenAPI, 2=MCP)
    if "mcp_server_filter" not in st.session_state:
        st.session_state.mcp_server_filter = []  # AC4: Server filter state
    if "tool_search" not in st.session_state:
        st.session_state.tool_search = ""  # AC5: Search query state


# ============================================================================
# Cached Data Fetching
# ============================================================================


@st.cache_data(ttl=60, show_spinner=False)
def fetch_agents_cached(refresh_trigger: int, search: str, status: str, tenant_id: str = None):
    """
    Fetch agents with caching and refresh mechanism.

    Args:
        refresh_trigger: Cache key (increment to invalidate)
        search: Search query
        status: Status filter
        tenant_id: Tenant identifier to filter agents

    Returns:
        list: Agent list or empty list on error
    """
    agents_data = async_to_sync(fetch_agents_async)(search, status, tenant_id=tenant_id)
    if agents_data and "items" in agents_data:
        return agents_data.get("items", [])
    return []


# ============================================================================
# Main Page (AC#1: Streamlit page with wide layout)
# ============================================================================


def show() -> None:
    """Render the Agent Management page."""
    st.title("🤖 Agent Management")
    st.markdown("---")

    # Initialize session state
    initialize_session_state()

    # BUG FIX: Use elif to ensure only ONE dialog is opened at a time
    # Streamlit raises StreamlitAPIException if multiple dialogs are called in same script run
    # Handle dialogs with priority: delete > edit > detail > create
    if st.session_state.get("show_delete_form"):
        delete_agent_confirm(st.session_state.selected_agent_id)
    elif st.session_state.get("show_edit_form"):
        edit_agent_form(st.session_state.selected_agent_id)
    elif st.session_state.get("show_detail_view") and st.session_state.get("selected_agent"):
        agent_detail_view(st.session_state.selected_agent)
    elif st.session_state.show_create_form:
        create_agent_form()

    # Page controls (AC#2: Search + filter + refresh + create button)
    col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1])
    with col1:
        search_term = st.text_input(
            "🔍 Search agents", placeholder="Search by name...", key="agent_search"
        )
    with col2:
        status_filter = st.selectbox(
            "Filter by status",
            ["All", "draft", "active", "suspended", "inactive"],
            key="agent_status_filter",
        )
    with col3:
        # Tenant selector (required - API enforces tenant isolation)
        available_tenants = fetch_available_tenants()

        if not available_tenants:
            # Don't return early - show the error but allow the page to continue
            # This helps with debugging and lets users navigate to create tenants
            st.selectbox(
                "Select tenant *",
                options=[],
                disabled=True,
                help="⚠️ No tenants configured. Please create a tenant first in the Tenant Management page.",
            )
            selected_tenant = None
        else:
            tenant_options = [t["tenant_id"] for t in available_tenants]
            tenant_display = {
                t["tenant_id"]: f"{t['name']} ({t['tenant_id']})" for t in available_tenants
            }

            selected_tenant = st.selectbox(
                "Select tenant *",
                tenant_options,
                format_func=lambda x: tenant_display.get(x, x),
                key="agent_tenant_filter",
                help="Agents are tenant-specific. Select a tenant to view its agents.",
            )
    with col4:
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with col5:
        if st.button("+ Create Agent", use_container_width=True):
            # Clear create dialog session state to start fresh
            if "create_selected_tools" in st.session_state:
                del st.session_state["create_selected_tools"]
            st.session_state.show_create_form = True
            st.rerun()

    # Fetch agents with caching (AC#8: Auto-refresh via refresh_trigger)
    # Always pass the selected tenant_id (required by API)
    # If no tenant selected, show empty list
    if selected_tenant:
        agents = fetch_agents_cached(
            st.session_state.refresh_trigger, search_term, status_filter, selected_tenant
        )
    else:
        agents = []

    # Display agent list
    st.subheader(f"📋 Agents ({len(agents)} found)")

    if not agents:
        if not selected_tenant:
            st.warning("⚠️ No tenant selected. Please create a tenant first in the Tenant Management page.")
        else:
            st.info("No agents found. Click '+ Create Agent' to create your first agent.")
    else:
        # Display as table (AC#2: name, status, tools count, last execution)
        agent_data = []
        for agent in agents:
            # Count both OpenAPI tools and MCP tools
            openapi_count = len(agent.get("tool_ids", []))
            mcp_count = len(agent.get("mcp_tool_assignments", []))
            total_tools = openapi_count + mcp_count

            agent_data.append(
                {
                    "Name": agent.get("name", ""),
                    "Status": format_status_badge(agent.get("status", "draft")),
                    "Tools": total_tools,
                    "Last Updated": format_datetime(agent.get("updated_at")),
                }
            )

        df = pd.DataFrame(agent_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Agent detail view
        st.markdown("### Agent Details & Actions")
        agent_names = [a.get("name", "") for a in agents]
        selected_name = st.selectbox(
            "Select agent to manage:",
            options=agent_names,
            key="agent_selector",
            index=0 if agent_names else None,
        )

        if selected_name and agent_names:
            agent = next((a for a in agents if a.get("name") == selected_name), None)
            if agent:
                agent_id = agent.get("id")
                tenant_id = agent.get("tenant_id")

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if st.button("🔍 View Details", use_container_width=True):
                        st.session_state.selected_agent_id = agent_id
                        st.session_state.selected_agent = agent
                        st.session_state.show_detail_view = True
                        st.rerun()

                with col2:
                    if st.button("✏️ Edit", use_container_width=True):
                        st.session_state.selected_agent_id = agent_id
                        st.session_state.selected_agent_tenant_id = tenant_id
                        # Clear edit dialog session state to reload agent's current data from DB
                        if "edit_selected_tools" in st.session_state:
                            del st.session_state["edit_selected_tools"]
                        if "edit_form_data" in st.session_state:
                            del st.session_state["edit_form_data"]
                        st.session_state.show_edit_form = True
                        st.rerun()

                with col3:
                    if st.button("🗑️ Delete", use_container_width=True):
                        st.session_state.selected_agent_id = agent_id
                        st.session_state.selected_agent_tenant_id = tenant_id
                        st.session_state.show_delete_form = True
                        st.rerun()

                with col4:
                    # AC#5: Status toggle buttons
                    status = agent.get("status")
                    if status == "draft":
                        if st.button("▶️ Activate", use_container_width=True):
                            with st.spinner("Activating agent..."):
                                result = async_to_sync(activate_agent_async)(agent_id, tenant_id)
                                if result:
                                    st.success("✅ Agent activated!")
                                    st.session_state.refresh_trigger += 1
                                    st.rerun()

                # Story 11.2.5: MCP Tool Discovery UI
                st.markdown("---")
                st.subheader("🛠️ Tool Assignment & Discovery")

                # Render MCP tool discovery tabs (only if tenant is selected)
                if selected_tenant:
                    render_mcp_tool_discovery_ui(selected_tenant)
                else:
                    st.warning("⚠️ Please select a tenant to view available tools.")


def render_mcp_tool_discovery_ui(tenant_id: str) -> None:
    """
    Render MCP Tool Discovery UI with tabs, badges, and health status (Story 11.2.5).

    Args:
        tenant_id: Tenant UUID for filtering tools and health status
    """
    # Initialize session state for main page (key_prefix="")
    if "selected_tools" not in st.session_state:
        st.session_state["selected_tools"] = {
            "openapi": set(),
            "mcp": set(),
        }

    # AC8: Fetch unified tools and MCP health status with caching
    with st.spinner("Loading tools and MCP server health..."):
        unified_tools = fetch_unified_tools(tenant_id)
        health_status = fetch_mcp_server_health(tenant_id)

    # DEBUG: Show session state
    if st.checkbox("Show Debug Info", value=False, key="show_debug_mcp"):
        st.json({
            "openapi_count": len(st.session_state.get("selected_tools", {}).get("openapi", set())),
            "mcp_count": len(st.session_state.get("selected_tools", {}).get("mcp", set())),
            "mcp_keys_sample": list(st.session_state.get("selected_tools", {}).get("mcp", set()))[:5]
        })

    if not unified_tools:
        st.warning("⚠️ No tools available. Configure OpenAPI tools or MCP servers first.")
        return

    # Separate tools by source type
    all_tools = unified_tools
    openapi_tools = [t for t in unified_tools if t.get("source_type") == "openapi"]
    mcp_tools = [t for t in unified_tools if t.get("source_type") == "mcp"]

    # AC1: Tab-based tool organization with st.tabs()
    tab_all, tab_openapi, tab_mcp = st.tabs(["📋 All Tools", "🔧 OpenAPI Tools", "🔌 MCP Tools"])

    # Render "All Tools" tab (key_prefix="" for main page)
    with tab_all:
        render_tool_tab(
            tools=all_tools,
            health_status=health_status,
            show_mcp_filter=False,  # Don't show MCP filter in "All Tools"
            tab_name="all",
            key_prefix="",  # Main page uses empty prefix
        )

    # Render "OpenAPI Tools" tab
    with tab_openapi:
        render_tool_tab(
            tools=openapi_tools,
            health_status=health_status,
            show_mcp_filter=False,  # No MCP filter for OpenAPI-only tab
            tab_name="openapi",
            key_prefix="",  # Main page uses empty prefix
        )

    # Render "MCP Tools" tab
    with tab_mcp:
        render_tool_tab(
            tools=mcp_tools,
            health_status=health_status,
            show_mcp_filter=True,  # AC4: Show MCP server filter in this tab
            tab_name="mcp",
            key_prefix="",  # Main page uses empty prefix
        )

    # AC7: Render assigned tools summary
    render_assigned_tools_summary(openapi_tools, mcp_tools, health_status, key_prefix="")


if __name__ == "__main__":
    show()
