"""
Execution History Viewer Page (Story 10.2).

Displays agent test execution history with comprehensive filtering,
pagination, and expandable detail view placeholder for Story 10.3.

Features:
- Filter by agent, tenant, status, date range (AC2)
- Pagination (50 per page) (AC4)
- Color-coded status badges (AC1)
- Expandable row details placeholder (AC3)
- Empty state handling (AC6)
- Default sorting by created_at DESC (AC5)
"""

from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st
from loguru import logger

from admin.utils import show_connection_status
from admin.utils.execution_detail_rendering import (
    fetch_execution_detail,
    render_error_section,
    render_input_section,
    render_llm_conversation,
    render_metadata_section,
)
from admin.utils.execution_history_helpers import (
    format_execution_table,
    get_agent_list,
    get_execution_history,
    get_tenant_list,
)


def show() -> None:
    """
    Render the Execution History page.

    Implements full execution history viewer with filters, pagination,
    and detail view placeholder (Story 10.2).
    """
    st.title("📊 Execution History")
    st.markdown("---")

    # Database connection check
    with st.sidebar:
        st.subheader("Connection Status")
        show_connection_status()

    # Initialize session state for pagination (Constraint 2)
    if "exec_current_page" not in st.session_state:
        st.session_state.exec_current_page = 1
    if "exec_page_size" not in st.session_state:
        st.session_state.exec_page_size = 50

    # Filters section (AC2)
    st.subheader("🔍 Filters")

    col1, col2, col3 = st.columns(3)

    with col1:
        # Agent filter (AC2)
        try:
            agent_list = get_agent_list()
            agent_options = ["All"] + [f"{agent['name']}" for agent in agent_list]
            agent_display = st.selectbox("Agent", agent_options)

            # Map display name back to agent_id
            if agent_display == "All":
                selected_agent = "All"
            else:
                selected_agent = next(
                    (agent["id"] for agent in agent_list if agent["name"] == agent_display),
                    "All",
                )
        except Exception as e:
            logger.error(f"Failed to load agent list: {e}")
            selected_agent = st.selectbox("Agent", ["All"])
            st.error("Failed to load agent list")
            selected_agent = "All"

    with col2:
        # Tenant filter (AC2)
        try:
            tenant_list = get_tenant_list()
            tenant_options = ["All"] + [f"{tenant['name']}" for tenant in tenant_list]
            tenant_display = st.selectbox("Tenant", tenant_options)

            # Map display name back to tenant_id
            if tenant_display == "All":
                selected_tenant = "All"
            else:
                selected_tenant = next(
                    (tenant["id"] for tenant in tenant_list if tenant["name"] == tenant_display),
                    "All",
                )
        except Exception as e:
            logger.error(f"Failed to load tenant list: {e}")
            selected_tenant = st.selectbox("Tenant", ["All"])
            st.error("Failed to load tenant list")
            selected_tenant = "All"

    with col3:
        # Status filter (AC2)
        selected_status = st.selectbox("Status", ["All", "Completed", "Failed"])

    # Date range filter (AC2)
    col4, col5 = st.columns(2)
    with col4:
        # Default: last 30 days
        default_from_date = date.today() - timedelta(days=30)
        from_date = st.date_input("From Date", value=default_from_date)

    with col5:
        to_date = st.date_input("To Date", value=date.today())

    st.markdown("---")

    # Apply Filters button
    apply_filters = st.button("🔍 Apply Filters", use_container_width=True)

    # Reset to page 1 when filters change (Constraint 8)
    if apply_filters:
        st.session_state.exec_current_page = 1

    st.markdown("---")

    # Query execution history (AC1, AC5)
    try:
        records, total_count = get_execution_history(
            agent_id=selected_agent if selected_agent != "All" else None,
            tenant_id=selected_tenant if selected_tenant != "All" else None,
            status=selected_status if selected_status != "All" else None,
            date_from=from_date,
            date_to=to_date,
            page=st.session_state.exec_current_page,
            page_size=st.session_state.exec_page_size,
        )

        # Calculate pagination metrics (AC4)
        total_pages = (
            total_count + st.session_state.exec_page_size - 1
        ) // st.session_state.exec_page_size
        start_record = (
            st.session_state.exec_current_page - 1
        ) * st.session_state.exec_page_size + 1
        end_record = min(start_record + len(records) - 1, total_count)

        # Display record count (AC1, Constraint 8)
        if total_count > 0:
            st.caption(f"Showing {start_record}-{end_record} of {total_count} records")
        else:
            st.caption("Showing 0 records")

        if total_count > 0:
            # Convert to DataFrame for display (AC1)
            df = format_execution_table(records)

            # Display table (AC1)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Pagination controls (AC4, Constraint 2)
            col_prev, col_page, col_next = st.columns([1, 3, 1])

            with col_prev:
                if st.button("⬅️ Previous", disabled=(st.session_state.exec_current_page == 1)):
                    st.session_state.exec_current_page -= 1
                    st.rerun()

            with col_page:
                st.write(f"Page {st.session_state.exec_current_page} of {total_pages}")

            with col_next:
                if st.button(
                    "Next ➡️",
                    disabled=(st.session_state.exec_current_page >= total_pages),
                ):
                    st.session_state.exec_current_page += 1
                    st.rerun()

            st.markdown("---")

            # Expandable row details with full detail view (Story 1.3 implementation)
            st.subheader("🔍 Execution Details")
            st.caption("Click on an expander to view detailed LLM conversation and execution trace")

            for idx, record in enumerate(records):
                # Create expander for each record
                status_icon = "🟢" if record["status"] == "success" else "🔴"
                status_text = "Completed" if record["status"] == "success" else "Failed"

                with st.expander(
                    f"{status_icon} {record['agent_name']} - {record['id'][:8]}... - {status_text}",
                    expanded=False,
                ):
                    # Fetch full execution details from API (Task 1)
                    # FIX: Pass tenant_id from record for proper tenant isolation
                    execution_detail = fetch_execution_detail(record["id"], record["tenant_id"])

                    if execution_detail:
                        # Render all detail sections (Tasks 2-5)
                        render_metadata_section(execution_detail)
                        st.markdown("---")

                        render_input_section(execution_detail)
                        st.markdown("---")

                        render_llm_conversation(execution_detail)
                        st.markdown("---")

                        render_error_section(execution_detail)
                    else:
                        # Fallback if API call fails
                        st.error(
                            f"❌ Failed to load execution details for ID: {record['id']}\n\n"
                            "This may be due to:\n"
                            "- Network connectivity issues\n"
                            "- API endpoint unavailable\n"
                            "- Insufficient permissions\n\n"
                            "Try refreshing the page or contact support if the issue persists."
                        )

        else:
            # Empty state handling (AC6, Constraint 9)
            st.info(
                "📭 **No executions found**\n\n"
                "No executions match your current filters.\n\n"
                "**Suggestions:**\n"
                "- Adjust the date range to include more data\n"
                "- Change the agent or tenant filter\n"
                "- Select 'All' for status filter\n"
                "- Try removing some filters to see more results"
            )

    except Exception as e:
        logger.error(f"Failed to load execution history: {e}")
        st.error(f"❌ Failed to load execution history: {e}")
        st.warning(
            "**Troubleshooting:**\n\n"
            "1. Verify database connection is active\n"
            "2. Check filter values are valid\n"
            "3. Try reducing the date range\n"
            "4. Contact support if issue persists"
        )


if __name__ == "__main__":
    show()
