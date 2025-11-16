"""
Enhancement History Viewer Page.

Displays historical enhancement processing data with comprehensive filtering,
search, pagination, expandable row details, and CSV export.

Features (Story 6.4):
- Filter by tenant, status, date range
- Search by ticket ID (case-insensitive partial match)
- Pagination (25/50/100/250 rows per page)
- Color-coded status badges (green=completed, red=failed, blue=pending)
- Expandable row details (context_gathered JSON, llm_output, error_message)
- CSV export with flattened JSON fields
- Performance optimized for 10K+ records (< 5 seconds query time)
"""

from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st
from loguru import logger

from admin.utils import show_connection_status
from admin.utils.history_helper import (
    convert_to_csv,
    format_status_badge,
    get_all_tenant_ids,
    get_enhancement_history,
)


def show() -> None:
    """
    Render the Enhancement History page.

    Implements full history viewer with filters, pagination, search,
    expandable details, and CSV export (Story 6.4).
    """
    st.title("📜 Enhancement History")
    st.markdown("---")

    # Database connection check
    with st.sidebar:
        st.subheader("Connection Status")
        show_connection_status()

    # Initialize session state for pagination
    if "current_page" not in st.session_state:
        st.session_state.current_page = 1
    if "page_size" not in st.session_state:
        st.session_state.page_size = 50

    # Filters section (AC #2, #3)
    st.subheader("🔍 Filters")

    col1, col2, col3, col4 = st.columns([2, 2, 3, 3])

    with col1:
        # Tenant filter (AC #2)
        try:
            tenant_list = get_all_tenant_ids()
            selected_tenant = st.selectbox("Tenant", ["All"] + tenant_list)
        except Exception as e:
            logger.error(f"Failed to load tenant list: {e}")
            selected_tenant = st.selectbox("Tenant", ["All"])
            st.error("Failed to load tenant list")

    with col2:
        # Status filter (AC #2)
        selected_status = st.selectbox("Status", ["All", "pending", "completed", "failed"])

    with col3:
        # Date range filter (AC #2)
        # Default: last 30 days
        default_from_date = date.today() - timedelta(days=30)
        from_date = st.date_input("From Date", value=default_from_date)
        to_date = st.date_input("To Date", value=date.today())

    with col4:
        # Search box (AC #3)
        search_query = st.text_input("Search Ticket ID", placeholder="Enter ticket ID...")

    st.markdown("---")

    # Page size selector
    col_a, col_b, col_c = st.columns([2, 2, 6])
    with col_a:
        page_size = st.selectbox("Rows per page", [25, 50, 100, 250], index=1)
        if page_size != st.session_state.page_size:
            st.session_state.page_size = page_size
            st.session_state.current_page = 1  # Reset to first page
            st.rerun()

    # Query enhancement history (AC #1, #7)
    try:
        records, total_count = get_enhancement_history(
            tenant_id=selected_tenant if selected_tenant != "All" else None,
            status=selected_status if selected_status != "All" else None,
            date_from=from_date,
            date_to=to_date,
            search_query=search_query if search_query else None,
            page=st.session_state.current_page,
            page_size=st.session_state.page_size,
        )

        # Calculate pagination metrics
        total_pages = (total_count + st.session_state.page_size - 1) // st.session_state.page_size
        start_record = (st.session_state.current_page - 1) * st.session_state.page_size + 1
        end_record = min(start_record + len(records) - 1, total_count)

        # Display record count (AC #1)
        st.caption(f"Showing {start_record}-{end_record} of {total_count} records")

        if total_count > 0:
            # Convert to DataFrame for display (AC #4)
            df = pd.DataFrame(records)

            # Format status badges (AC #8)
            df["Status"] = df["status"].apply(format_status_badge)

            # Format timestamps (AC #4)
            df["Created"] = pd.to_datetime(df["created_at"]).dt.strftime("%Y-%m-%d %H:%M:%S")
            df["Completed"] = pd.to_datetime(df["completed_at"]).dt.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            df["Completed"] = df["Completed"].fillna("N/A")

            # Format processing time (AC #4)
            df["Duration"] = df["processing_time_ms"].apply(
                lambda x: f"{x}ms" if pd.notna(x) else "N/A"
            )

            # Select and rename columns for display (AC #4)
            display_df = df[
                ["ticket_id", "tenant_id", "Status", "Duration", "Created", "Completed"]
            ].rename(
                columns={
                    "ticket_id": "Ticket ID",
                    "tenant_id": "Tenant",
                    "Duration": "Processing Time",
                    "Created": "Created At",
                    "Completed": "Completed At",
                }
            )

            # Display table (AC #4)
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            # Pagination controls
            col_prev, col_page, col_next = st.columns([1, 3, 1])

            with col_prev:
                if st.button("⬅️ Previous", disabled=(st.session_state.current_page == 1)):
                    st.session_state.current_page -= 1
                    st.rerun()

            with col_page:
                st.write(f"Page {st.session_state.current_page} of {total_pages}")

            with col_next:
                if st.button(
                    "Next ➡️", disabled=(st.session_state.current_page >= total_pages)
                ):
                    st.session_state.current_page += 1
                    st.rerun()

            st.markdown("---")

            # CSV Export button (AC #6)
            st.subheader("📥 Export Data")
            if st.button("Export to CSV"):
                try:
                    # Create DataFrame for export (all visible records)
                    export_df = df[
                        [
                            "ticket_id",
                            "tenant_id",
                            "status",
                            "processing_time_ms",
                            "created_at",
                            "completed_at",
                            "context_gathered",
                            "llm_output",
                            "error_message",
                        ]
                    ]

                    csv_data = convert_to_csv(export_df)
                    filename = f"enhancement_history_{date.today()}.csv"

                    st.download_button(
                        label="📥 Download CSV",
                        data=csv_data,
                        file_name=filename,
                        mime="text/csv",
                    )
                    st.success(f"CSV ready for download: {filename}")

                except Exception as e:
                    logger.error(f"CSV export failed: {e}")
                    st.error(f"Failed to generate CSV: {e}")

            st.markdown("---")

            # Expandable row details (AC #5)
            st.subheader("🔍 Enhancement Details")
            st.caption("Click on an expander to view detailed information")

            for idx, record in enumerate(records):
                # Create expander for each record (AC #5)
                with st.expander(
                    f"🔍 {record['ticket_id']} - {record['status'].upper()}",
                    expanded=False,
                ):
                    # Header info
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"**Ticket ID:** `{record['ticket_id']}`")
                        st.markdown(f"**Tenant:** `{record['tenant_id']}`")
                    with col2:
                        st.markdown(f"**Status:** {format_status_badge(record['status'])}")
                        st.markdown(
                            f"**Processing Time:** {record['processing_time_ms']}ms"
                            if record["processing_time_ms"]
                            else "**Processing Time:** N/A"
                        )
                    with col3:
                        st.markdown(
                            f"**Created:** {record['created_at'].strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        st.markdown(
                            f"**Completed:** {record['completed_at'].strftime('%Y-%m-%d %H:%M:%S') if record['completed_at'] else 'N/A'}"
                        )

                    st.markdown("---")

                    # Context Gathered (AC #5)
                    if record["context_gathered"]:
                        st.write("**Context Gathered:**")
                        st.json(record["context_gathered"])
                    else:
                        st.info("No context data available")

                    # LLM Output (AC #5)
                    if record["llm_output"]:
                        st.write("**LLM Enhancement Output:**")
                        st.text_area(
                            "Output",
                            value=record["llm_output"],
                            height=200,
                            disabled=True,
                            key=f"llm_output_{idx}",
                        )

                    # Error Message (AC #5)
                    if record["error_message"]:
                        st.error("**Error:**")
                        st.code(record["error_message"], language="text")

        else:
            st.info(
                "No records found matching your filters.\n\n"
                "Try adjusting the filters or date range."
            )

    except Exception as e:
        logger.error(f"Failed to load enhancement history: {e}")
        st.error(f"Failed to load enhancement history: {e}")
        st.warning(
            "**Troubleshooting:**\n\n"
            "1. Verify database connection is active\n"
            "2. Check filter values are valid\n"
            "3. Try reducing the date range\n"
            "4. Contact support if issue persists"
        )


if __name__ == "__main__":
    show()
