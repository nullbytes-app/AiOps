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

Story: 8.4 - Agent Management UI (Basic)
Depends on Story 8.3 (Agent CRUD API Endpoints) for REST endpoints

Helper modules:
- src/admin/utils/agent_helpers.py: API calls and form validation
- src/admin/components/agent_forms.py: Dialog forms (create, edit, delete, detail)
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
    format_datetime,
    format_status_badge,
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
    if "show_create_form" not in st.session_state:
        st.session_state.show_create_form = False
    if "show_edit_form" not in st.session_state:
        st.session_state.show_edit_form = False
    if "show_delete_form" not in st.session_state:
        st.session_state.show_delete_form = False
    if "refresh_trigger" not in st.session_state:
        st.session_state.refresh_trigger = 0


# ============================================================================
# Cached Data Fetching
# ============================================================================


@st.cache_data(ttl=60, show_spinner=False)
def fetch_agents_cached(refresh_trigger: int, search: str, status: str):
    """
    Fetch agents with caching and refresh mechanism.

    Args:
        refresh_trigger: Cache key (increment to invalidate)
        search: Search query
        status: Status filter

    Returns:
        list: Agent list or empty list on error
    """
    agents_data = async_to_sync(fetch_agents_async)(search, status)
    if agents_data and "items" in agents_data:
        return agents_data.get("items", [])
    return []


# ============================================================================
# Main Page (AC#1: Streamlit page with wide layout)
# ============================================================================


def show() -> None:
    """Render the Agent Management page."""
    st.set_page_config(
        page_title="Agent Management - AI Agents Admin",
        page_icon="🤖",
        layout="wide",
    )

    st.title("🤖 Agent Management")
    st.markdown("---")

    # Initialize session state
    initialize_session_state()

    # Handle dialogs
    if st.session_state.show_create_form:
        create_agent_form()
    if st.session_state.get("show_edit_form"):
        edit_agent_form(st.session_state.selected_agent_id)
    if st.session_state.get("show_delete_form"):
        delete_agent_confirm(st.session_state.selected_agent_id)

    # Page controls (AC#2: Search + filter + refresh + create button)
    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
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
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with col4:
        if st.button("+ Create Agent", use_container_width=True):
            st.session_state.show_create_form = True
            st.rerun()

    # Fetch agents with caching (AC#8: Auto-refresh via refresh_trigger)
    agents = fetch_agents_cached(st.session_state.refresh_trigger, search_term, status_filter)

    # Display agent list
    st.subheader(f"📋 Agents ({len(agents)} found)")

    if not agents:
        st.info("No agents found. Click '+ Create Agent' to create your first agent.")
    else:
        # Display as table (AC#2: name, status, tools count, last execution)
        agent_data = []
        for agent in agents:
            agent_data.append(
                {
                    "Name": agent.get("name", ""),
                    "Status": format_status_badge(agent.get("status", "draft")),
                    "Tools": len(agent.get("tool_ids", [])),
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

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if st.button("🔍 View Details", use_container_width=True):
                        st.session_state.selected_agent_id = agent_id
                        agent_detail_view(agent_id)

                with col2:
                    if st.button("✏️ Edit", use_container_width=True):
                        st.session_state.selected_agent_id = agent_id
                        st.session_state.show_edit_form = True
                        st.rerun()

                with col3:
                    if st.button("🗑️ Delete", use_container_width=True):
                        st.session_state.selected_agent_id = agent_id
                        st.session_state.show_delete_form = True
                        st.rerun()

                with col4:
                    # AC#5: Status toggle buttons
                    status = agent.get("status")
                    if status == "draft":
                        if st.button("▶️ Activate", use_container_width=True):
                            with st.spinner("Activating agent..."):
                                result = async_to_sync(activate_agent_async)(agent_id)
                                if result:
                                    st.success("✅ Agent activated!")
                                    st.session_state.refresh_trigger += 1
                                    st.rerun()


if __name__ == "__main__":
    show()
