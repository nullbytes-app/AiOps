"""
Operations UI Helper Functions.

This module provides UI-specific helper functions for the Operations page:
- Confirmation result handling for operations
- Worker health display fragment with auto-refresh
- Status formatting utilities

Part of Story 6.5 Code Review refactoring to reduce 4_Operations.py file size.
Extracted from 4_Operations.py to comply with CLAUDE.md 500-line constraint.
"""

from datetime import datetime

import pandas as pd
import streamlit as st

from admin.utils.operations_helper import format_uptime, get_worker_stats


# ============================================================================
# CONFIRMATION RESULT HANDLERS
# ============================================================================


def handle_operation_confirmation(
    operation_name: str,
    operation_func: callable,
    success_key: str = None,
    **operation_kwargs
) -> None:
    """
    Handle confirmation result and execute operation if confirmed.

    Generic handler for operation confirmations. Executes operation function
    if user confirmed, displays result message, and resets session state.

    Args:
        operation_name: Name of operation to check for confirmation
        operation_func: Function to call if confirmed (must return tuple with success flag and message)
        success_key: Optional key for extracting success value from operation result
        **operation_kwargs: Additional kwargs to pass to operation function

    Session State:
        Reads 'operation_confirmed' and 'confirmed_operation'
        Resets both after handling

    Examples:
        >>> handle_operation_confirmation("pause_processing", pause_processing)
        >>> handle_operation_confirmation("clear_queue", clear_celery_queue, queue_name="celery")
    """
    if not st.session_state.get("operation_confirmed"):
        return

    confirmed_op = st.session_state.get("confirmed_operation")

    if confirmed_op != operation_name:
        return

    # Execute operation
    result = operation_func(**operation_kwargs)

    # Extract success and message from result tuple
    if len(result) == 2:
        success, message = result
    elif len(result) == 3:
        # For operations that return (success, data, message)
        success, _data, message = result
    else:
        success, message = False, "Unexpected operation result format"

    # Display result
    if success:
        st.success(message)
    else:
        st.error(message)

    # Reset confirmation state
    st.session_state["operation_confirmed"] = False
    st.session_state["confirmed_operation"] = None
    st.rerun()


# ============================================================================
# WORKER HEALTH DISPLAY FRAGMENT
# ============================================================================


@st.fragment(run_every="30s")
def display_worker_health() -> None:
    """
    Display worker health with auto-refresh every 30 seconds.

    Uses @st.fragment for selective rerun (Streamlit 1.44.0+ feature).
    Only this section refreshes, not the entire page.

    AC#6: "View Worker Health" section displays active workers.
    """
    st.subheader("💓 Worker Health")

    # Get worker stats
    workers = get_worker_stats()

    if not workers:
        st.error("❌ No active Celery workers detected. Check worker deployment.")
        st.write("")
        st.info(
            "**Troubleshooting:**\n"
            "1. Verify workers are running: `kubectl get pods -l app=celery-worker`\n"
            "2. Check worker logs: `kubectl logs -l app=celery-worker`\n"
            "3. Test Redis connection: redis-cli ping\n"
            "4. Verify Celery broker URL in environment"
        )
    else:
        # Convert to DataFrame
        df_workers = pd.DataFrame(workers)

        # Format uptime to human-readable
        if "uptime_seconds" in df_workers.columns:
            df_workers["uptime_formatted"] = df_workers["uptime_seconds"].apply(format_uptime)

        # Rename columns for display
        df_workers = df_workers.rename(
            columns={
                "hostname": "Worker",
                "total_tasks": "Total Tasks Processed",
                "uptime_formatted": "Uptime",
            }
        )

        # Select display columns
        display_cols = ["Worker", "Total Tasks Processed"]
        if "Uptime" in df_workers.columns:
            display_cols.insert(1, "Uptime")

        # Display DataFrame
        st.dataframe(
            df_workers[display_cols],
            use_container_width=True,
            hide_index=True,
        )

        # Display last updated timestamp
        st.caption(f"📅 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    st.write("")


# ============================================================================
# STATUS FORMATTING UTILITIES
# ============================================================================


def format_operation_status(status: str) -> str:
    """
    Format operation status with emoji indicators.

    Args:
        status: Status string ("success", "failure", "in_progress", etc.)

    Returns:
        str: Formatted status with emoji (e.g., "✅ Success")

    Examples:
        >>> format_operation_status("success")
        "✅ Success"

        >>> format_operation_status("failure")
        "❌ Failure"
    """
    status_map = {
        "success": "✅ Success",
        "failure": "❌ Failure",
        "in_progress": "⏳ In Progress",
        "partial_failure": "⚠️ Partial Success",
    }

    return status_map.get(status, status)
