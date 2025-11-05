"""
Operations Utility Functions.

This module provides utility functions for system operations:
- Worker health monitoring via Celery inspect
- Confirmation dialogs with typed "YES" confirmation
- Uptime formatting utilities

Dependencies:
- celery: Celery control API for worker health monitoring
- streamlit: Dialog and caching decorators

Part of Story 6.5 refactoring to comply with CLAUDE.md 500-line constraint.
"""

import streamlit as st
from loguru import logger

from src.workers.celery_app import celery_app


# ============================================================================
# WORKER HEALTH MONITORING (AC#6)
# ============================================================================


@st.cache_data(ttl=10)
def get_worker_stats() -> list[dict]:
    """
    Get Celery worker statistics for health monitoring.

    Uses celery_app.control.inspect().stats() to query worker info.
    Returns list of worker stats including hostname, uptime, and task counts.

    AC#6: "View Worker Health" section displays active workers.

    Returns:
        list[dict]: List of worker stat dicts, or empty list if unavailable
            Each dict contains: hostname, uptime_seconds, total_tasks

    Examples:
        >>> get_worker_stats()
        [
            {"hostname": "celery@worker-1", "uptime_seconds": 3600, "total_tasks": 1234},
            {"hostname": "celery@worker-2", "uptime_seconds": 7200, "total_tasks": 5678}
        ]

        >>> get_worker_stats()  # No workers
        []
    """
    try:
        # Use Celery inspect to get worker stats
        inspect = celery_app.control.inspect()
        stats_data = inspect.stats()

        if not stats_data:
            logger.warning("No active Celery workers detected")
            return []

        workers = []

        for hostname, stats in stats_data.items():
            # Extract task counts (sum all task types)
            total_tasks = 0
            if "total" in stats:
                for task_name, count in stats["total"].items():
                    total_tasks += count

            # Extract uptime (rusage field may not always be available)
            uptime_seconds = 0
            # Note: Celery stats doesn't directly provide uptime
            # This is a placeholder - actual implementation may vary

            workers.append(
                {
                    "hostname": hostname,
                    "uptime_seconds": uptime_seconds,
                    "total_tasks": total_tasks,
                }
            )

        return workers

    except Exception as e:
        logger.error(f"Failed to get worker stats: {e}")
        return []


@st.cache_data(ttl=10)
def get_active_workers() -> list[str]:
    """
    Get list of active Celery worker hostnames.

    Returns:
        list[str]: List of active worker hostnames, or empty list if none active

    Examples:
        >>> get_active_workers()
        ["celery@worker-1", "celery@worker-2"]

        >>> get_active_workers()  # No workers
        []
    """
    try:
        inspect = celery_app.control.inspect()
        stats_data = inspect.stats()

        if not stats_data:
            return []

        return list(stats_data.keys())

    except Exception as e:
        logger.error(f"Failed to get active workers: {e}")
        return []


# ============================================================================
# CONFIRMATION DIALOG (AC#8)
# ============================================================================


@st.dialog("Confirm Operation")
def confirm_operation(operation_name: str, warning_message: str) -> None:
    """
    Display confirmation dialog with typed "YES" confirmation.

    Uses Streamlit @st.dialog decorator for modal dialog. Requires user to
    type exactly "YES" (case-sensitive) before confirming destructive operations.

    AC#8: All operations require confirmation dialog with typed confirmation.

    Args:
        operation_name: Name of operation being confirmed
        warning_message: Warning message to display in dialog

    Session State:
        Sets 'operation_confirmed' to True/False based on user action
        Sets 'confirmed_operation' to operation_name if confirmed

    Examples:
        Usage pattern:
        >>> if st.button("Pause Processing"):
        ...     confirm_operation("pause_processing", "This will stop workers...")
        ...
        >>> if st.session_state.get('operation_confirmed'):
        ...     if st.session_state.get('confirmed_operation') == 'pause_processing':
        ...         result = pause_processing()

    Note:
        This function uses @st.dialog which requires Streamlit 1.44.0+.
        Dialog closes automatically when st.rerun() is called.
    """
    st.warning(f"⚠️ {warning_message}")
    st.write("")
    st.write(f"**Operation:** {operation_name}")
    st.write("")

    # Text input for "YES" confirmation (case-sensitive)
    confirmation = st.text_input(
        "Type **YES** to confirm (case-sensitive):",
        key=f"confirm_input_{operation_name}",
        max_chars=3,
    )

    st.write("")

    # Two-column layout for Cancel and Confirm buttons
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Cancel", use_container_width=True, key=f"cancel_{operation_name}"):
            st.session_state["operation_confirmed"] = False
            st.session_state["confirmed_operation"] = None
            st.rerun()

    with col2:
        # Confirm button disabled until user types "YES"
        confirm_disabled = confirmation != "YES"

        if st.button(
            "Confirm",
            use_container_width=True,
            disabled=confirm_disabled,
            key=f"confirm_{operation_name}",
            type="primary",
        ):
            st.session_state["operation_confirmed"] = True
            st.session_state["confirmed_operation"] = operation_name
            st.rerun()


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def format_uptime(seconds: int) -> str:
    """
    Format uptime seconds to human-readable string.

    Args:
        seconds: Uptime in seconds

    Returns:
        str: Formatted uptime (e.g., "2h 34m 12s")

    Examples:
        >>> format_uptime(3600)
        "1h 0m 0s"

        >>> format_uptime(9123)
        "2h 32m 3s"
    """
    if seconds < 0:
        return "0s"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"
