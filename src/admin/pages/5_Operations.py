"""
System Operations Page for Streamlit Admin UI.

This page provides manual controls for critical system operations including
pause/resume worker processing, queue management, tenant config sync, worker
health monitoring, and audit logging.

Key Features (Story 6.5):
- AC#1: Warning banner for operations page
- AC#2: Pause Processing button with Redis flag control
- AC#3: Resume Processing button
- AC#4: Clear Queue button with confirmation
- AC#5: Sync Tenant Configs button
- AC#6: Worker Health display with stats
- AC#7: Operation logs display (last 20 operations)
- AC#8: Typed "YES" confirmation dialogs for all operations
- AC#9: Audit logging for compliance

Typical Usage:
  streamlit run src/admin/app.py
  # Navigate to "Operations" page from sidebar

Dependencies:
  - streamlit>=1.44.0 (for @st.dialog and @st.fragment)
  - pandas for DataFrame display
  - operations_helper for all system operations

Safety:
  All destructive operations require confirmation dialog with typed "YES".
  Audit logs created for every operation for compliance tracking.
"""

import os
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
from loguru import logger

from admin.utils.operations_helper import (
    clear_celery_queue,
    confirm_operation,
    get_active_workers,
    get_queue_length,
    get_recent_operations,
    is_processing_paused,
    log_operation,
    pause_processing,
    resume_processing,
    sync_tenant_configs,
)
from admin.utils.operations_ui_helpers import (
    display_worker_health,
    format_operation_status,
)

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="System Operations - AI Agents",
    page_icon="⚙️",
    layout="wide",
)

# ============================================================================
# AUTHENTICATION CHECK
# ============================================================================

# Check authentication (dual-mode: session state for local dev, K8s ingress for prod)
if "authenticated" not in st.session_state:
    # Check if running behind K8s ingress with authentication headers
    auth_header = st.context.headers.get("X-Auth-Request-User") if hasattr(st, "context") else None

    if auth_header:
        # Authenticated via K8s ingress
        st.session_state["authenticated"] = True
        st.session_state["user"] = auth_header
    elif os.getenv("STREAMLIT_LOCAL_DEV", "false").lower() == "true":
        # Local development mode - bypass authentication
        st.session_state["authenticated"] = True
        st.session_state["user"] = "admin@localhost"
    else:
        # Not authenticated
        st.session_state["authenticated"] = False

if not st.session_state.get("authenticated", False):
    st.error("🔒 Authentication required. Please access via Kubernetes ingress.")
    st.stop()

# Get current user for audit logging
current_user = st.session_state.get("user", "unknown")

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

# Initialize operation confirmation states
if "operation_confirmed" not in st.session_state:
    st.session_state["operation_confirmed"] = False

if "confirmed_operation" not in st.session_state:
    st.session_state["confirmed_operation"] = None

if "last_operation_result" not in st.session_state:
    st.session_state["last_operation_result"] = None

# ============================================================================
# PAGE HEADER
# ============================================================================

st.title("⚙️ System Operations")

# AC#1: Warning banner
st.warning(
    "⚠️ **Caution:** Manual operations can affect system behavior. "
    "Use these controls carefully and ensure you understand the impact."
)

st.write("")

# Display current processing status
paused = is_processing_paused()
if paused:
    st.error("🔴 **Processing Status:** PAUSED - Workers are not picking up new tasks")
else:
    st.success("🟢 **Processing Status:** RUNNING - Workers are active")

st.write("")
st.divider()

# ============================================================================
# WORKER CONTROL SECTION (AC#2, AC#3)
# ============================================================================

st.subheader("🔧 Worker Control")

col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    # Pause Processing button (AC#2)
    pause_disabled = paused  # Disable if already paused

    if st.button(
        "⏸️ Pause Processing",
        disabled=pause_disabled,
        use_container_width=True,
        help="Stop workers from picking up new tasks (sets Redis pause flag)",
    ):
        confirm_operation(
            operation_name="pause_processing",
            warning_message="This will prevent Celery workers from picking up new tasks. "
            "Currently executing tasks will complete. The pause will auto-expire in 24 hours.",
        )

with col2:
    # Resume Processing button (AC#3)
    resume_disabled = not paused  # Disable if not paused

    if st.button(
        "▶️ Resume Processing",
        disabled=resume_disabled,
        use_container_width=True,
        help="Clear pause flag and allow workers to process tasks",
    ):
        confirm_operation(
            operation_name="resume_processing",
            warning_message="This will allow Celery workers to resume picking up tasks from the queue.",
        )

with col3:
    # Display pause status with timestamp
    if paused:
        st.info("⏸️ Workers are currently paused (flag active)")
    else:
        st.info("▶️ Workers are actively processing tasks")

# Handle confirmation results for pause/resume
if st.session_state.get("operation_confirmed"):
    confirmed_op = st.session_state.get("confirmed_operation")

    if confirmed_op == "pause_processing":
        # Execute pause operation
        success, message = pause_processing()

        # Log operation
        log_operation(
            user=current_user,
            operation="pause_processing",
            details={"timestamp": datetime.now(timezone.utc).isoformat()},
            status="success" if success else "failure",
        )

        # Display result
        if success:
            st.success(message)
        else:
            st.error(message)

        # Reset state
        st.session_state["operation_confirmed"] = False
        st.session_state["confirmed_operation"] = None
        st.rerun()

    elif confirmed_op == "resume_processing":
        # Execute resume operation
        success, message = resume_processing()

        # Log operation
        log_operation(
            user=current_user,
            operation="resume_processing",
            details={"timestamp": datetime.now(timezone.utc).isoformat()},
            status="success" if success else "failure",
        )

        # Display result
        if success:
            st.success(message)
        else:
            st.error(message)

        # Reset state
        st.session_state["operation_confirmed"] = False
        st.session_state["confirmed_operation"] = None
        st.rerun()

st.write("")
st.divider()

# ============================================================================
# QUEUE MANAGEMENT SECTION (AC#4)
# ============================================================================

st.subheader("📋 Queue Management")

col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    # Display current queue length
    queue_depth = get_queue_length()
    st.metric("Pending Tasks", f"{queue_depth:,}")

with col2:
    # Clear Queue button (AC#4)
    if st.button(
        "🗑️ Clear Queue",
        use_container_width=True,
        help="Remove all pending tasks from Celery queue (destructive operation)",
        type="secondary",
    ):
        confirm_operation(
            operation_name="clear_queue",
            warning_message=f"This will DELETE ALL {queue_depth:,} pending tasks from the queue. "
            "This operation CANNOT be undone. Tasks will be permanently lost.",
        )

with col3:
    st.info(f"💡 Queue: 'celery' (default Celery queue)")

# Handle confirmation for clear queue
if st.session_state.get("operation_confirmed"):
    if st.session_state.get("confirmed_operation") == "clear_queue":
        # Execute clear queue operation
        success, count, message = clear_celery_queue()

        # Log operation
        log_operation(
            user=current_user,
            operation="clear_queue",
            details={"tasks_deleted": count, "timestamp": datetime.now(timezone.utc).isoformat()},
            status="success" if success else "failure",
        )

        # Display result
        if success:
            st.success(message)
        else:
            st.error(message)

        # Reset state
        st.session_state["operation_confirmed"] = False
        st.session_state["confirmed_operation"] = None
        st.rerun()

st.write("")
st.divider()

# ============================================================================
# CONFIGURATION MANAGEMENT SECTION (AC#5)
# ============================================================================

st.subheader("🔄 Configuration Management")

col1, col2 = st.columns([1, 3])

with col1:
    # Sync Tenant Configs button (AC#5)
    if st.button(
        "🔄 Sync Tenant Configs",
        use_container_width=True,
        help="Reload tenant configurations from database to Redis cache",
    ):
        confirm_operation(
            operation_name="sync_configs",
            warning_message="This will reload all active tenant configurations from the database "
            "to Redis cache, overwriting any cached values. Existing cache entries will be replaced.",
        )

with col2:
    st.info(
        "💡 Syncs tenant configurations from PostgreSQL to Redis cache "
        "(tenant_config:{tenant_id} keys with 1-hour TTL)"
    )

# Handle confirmation for sync configs
if st.session_state.get("operation_confirmed"):
    if st.session_state.get("confirmed_operation") == "sync_configs":
        # Execute sync operation
        success, sync_results, message = sync_tenant_configs()

        # Log operation
        log_operation(
            user=current_user,
            operation="sync_tenant_configs",
            details={
                "sync_results": sync_results,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            status="success" if success else "partial_failure",
        )

        # Display result
        if success:
            st.success(message)
        else:
            st.warning(message)

        # Show detailed results if available
        if sync_results:
            with st.expander("📊 Detailed Sync Results", expanded=False):
                df = pd.DataFrame(
                    [{"Tenant ID": k, "Status": v} for k, v in sync_results.items()]
                )
                st.dataframe(df, use_container_width=True, hide_index=True)

        # Reset state
        st.session_state["operation_confirmed"] = False
        st.session_state["confirmed_operation"] = None
        st.rerun()

st.write("")
st.divider()

# ============================================================================
# WORKER HEALTH SECTION (AC#6)
# ============================================================================

# Display worker health with auto-refresh (extracted to operations_ui_helpers)
display_worker_health()

st.divider()

# ============================================================================
# OPERATION LOGS SECTION (AC#7, AC#9)
# ============================================================================

st.subheader("📜 Operation Logs")

# Get recent operations
operations = get_recent_operations(limit=20)

if not operations:
    st.info("ℹ️ No operations logged yet. Operations will appear here after execution.")
else:
    # Convert to DataFrame
    df_logs = pd.DataFrame(operations)

    # Format timestamp
    df_logs["timestamp"] = pd.to_datetime(df_logs["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")

    # Format details (truncate long JSON)
    if "details" in df_logs.columns:
        df_logs["details_preview"] = df_logs["details"].apply(
            lambda x: str(x)[:100] + "..." if len(str(x)) > 100 else str(x)
        )

    # Color-code status (using helper function)
    df_logs["status_formatted"] = df_logs["status"].apply(format_operation_status)

    # Rename columns for display
    df_display = df_logs.rename(
        columns={
            "timestamp": "Timestamp",
            "user": "User",
            "operation": "Operation",
            "status_formatted": "Status",
            "details_preview": "Details",
        }
    )

    # Select display columns
    display_cols = ["Timestamp", "User", "Operation", "Status", "Details"]

    # Display DataFrame
    st.dataframe(
        df_display[display_cols],
        use_container_width=True,
        hide_index=True,
    )

    # Export logs button
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        # Convert to CSV for download
        csv_data = df_logs.to_csv(index=False)

        st.download_button(
            label="📥 Export Logs (CSV)",
            data=csv_data,
            file_name=f"operation_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col2:
        # Refresh button (clears cache)
        if st.button("🔄 Refresh Logs", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

st.write("")
st.divider()

# ============================================================================
# FOOTER
# ============================================================================

st.caption(
    f"👤 Logged in as: **{current_user}** | "
    f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
    "⚙️ System Operations v1.0"
)
