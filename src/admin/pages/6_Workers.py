"""
Worker Health & Resource Monitoring Page.

This page provides comprehensive monitoring of Celery worker health and
resource utilization, including:
    - Worker list with status indicators
    - Resource metrics (CPU%, Memory%, throughput)
    - Worker restart controls
    - Logs viewer with filtering
    - Historical performance charts
    - Auto-refresh every 30 seconds

Story: 6.7 - Add Worker Health and Resource Monitoring
"""

from datetime import datetime

import pandas as pd
import streamlit as st
from loguru import logger

from admin.utils.worker_helper import (
    create_worker_performance_chart,
    fetch_celery_workers,
    fetch_worker_logs,
    fetch_worker_resources,
    fetch_worker_throughput_history,
    format_uptime,
    get_cpu_alert_icon,
    get_status_icon,
    restart_worker_k8s,
)

# Page configuration
st.set_page_config(
    page_title="Worker Health & Resource Monitoring",
    page_icon="🔧",
    layout="wide",
)


@st.fragment(run_every="30s")
def display_workers_page():
    """
    Display workers page with auto-refresh every 30 seconds.

    Uses Streamlit fragment decorator for selective page refresh without
    full reload. All page content is wrapped in this function to enable
    30-second auto-refresh of worker data.
    """
    st.title("🔧 Worker Health & Resource Monitoring")
    st.caption(
        "Monitor Celery worker health, resource utilization, and performance metrics"
    )

    # Fetch worker data
    workers = fetch_celery_workers()

    if not workers:
        st.warning(
            "⚠️ No active Celery workers found. Check that workers are running "
            "and connected to the broker."
        )
        st.info(
            "**Troubleshooting:**\n"
            "- Verify Celery workers are running: `kubectl get pods -l app=celery-worker`\n"
            "- Check worker logs: `kubectl logs <pod-name>`\n"
            "- Verify broker connection: Check Redis connectivity"
        )
        return

    # Fetch resource metrics
    worker_hostnames = [w["hostname"] for w in workers]
    resources = fetch_worker_resources(worker_hostnames)

    # Merge worker metadata with resource metrics
    merged_workers = []
    for worker in workers:
        hostname = worker["hostname"]
        worker_resources = resources.get(
            hostname,
            {
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "throughput_tasks_per_min": 0.0,
                "data_available": False,
            },
        )
        merged_workers.append({**worker, **worker_resources})

    # Display metrics summary
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Active Workers", len(workers))

    with col2:
        total_active_tasks = sum(w["active_tasks"] for w in workers)
        st.metric("Active Tasks", total_active_tasks)

    with col3:
        total_completed = sum(w["completed_tasks"] for w in workers)
        st.metric("Completed Tasks", f"{total_completed:,}")

    with col4:
        avg_throughput = (
            sum(w.get("throughput_tasks_per_min", 0) for w in merged_workers)
            / len(merged_workers)
            if merged_workers
            else 0
        )
        st.metric("Avg Throughput", f"{avg_throughput:.1f} tasks/min")

    st.divider()

    # Worker List Table Section
    st.subheader("📋 Worker Status")

    # Status filter
    status_filter = st.multiselect(
        "Filter by Status",
        ["active", "idle", "unresponsive"],
        default=["active", "idle"],
        key="worker_status_filter",
    )

    # Prepare DataFrame
    df_data = []
    for worker in merged_workers:
        # Apply status filter
        if worker["status"] not in status_filter:
            continue

        df_data.append(
            {
                "Status": get_status_icon(worker["status"]),
                "Hostname": worker["hostname"],
                "Uptime": format_uptime(worker["uptime_seconds"]),
                "Active Tasks": worker["active_tasks"],
                "Completed Tasks": f"{worker['completed_tasks']:,}",
                "CPU %": f"{worker['cpu_percent']:.1f}%",
                "CPU Alert": get_cpu_alert_icon(worker["cpu_percent"]),
                "Memory %": f"{worker['memory_percent']:.1f}%",
                "Throughput": f"{worker['throughput_tasks_per_min']:.1f} tasks/min",
            }
        )

    if not df_data:
        st.info("No workers match the selected filters")
        return

    df = pd.DataFrame(df_data)

    # Display table with custom column configuration
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Hostname": st.column_config.TextColumn("Hostname", width="medium"),
            "Uptime": st.column_config.TextColumn("Uptime", width="small"),
            "Active Tasks": st.column_config.NumberColumn(
                "Active Tasks", width="small"
            ),
            "Completed Tasks": st.column_config.TextColumn(
                "Completed Tasks", width="medium"
            ),
            "CPU %": st.column_config.TextColumn("CPU %", width="small"),
            "CPU Alert": st.column_config.TextColumn("Alert", width="small"),
            "Memory %": st.column_config.TextColumn("Memory %", width="small"),
            "Throughput": st.column_config.TextColumn("Throughput", width="medium"),
        },
    )

    st.caption(
        f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} • "
        f"Auto-refresh: 30s"
    )

    # Manual refresh button
    if st.button("🔄 Refresh Now", key="refresh_workers"):
        st.rerun()

    st.divider()

    # Worker Operations Section
    st.subheader("⚙️ Worker Operations")

    col1, col2 = st.columns([1, 3])

    with col1:
        st.markdown("**Restart Worker**")
        st.caption("⚠️ Restarts ALL worker pods (rolling restart)")

        selected_worker_restart = st.selectbox(
            "Select Worker to Restart",
            options=worker_hostnames,
            key="restart_worker_select",
        )

        if st.button(
            f"🔄 Restart {selected_worker_restart}",
            key="restart_worker_button",
            type="primary",
        ):
            st.warning(
                f"**Are you sure?** This will restart the worker deployment "
                f"(affects all worker pods, not just {selected_worker_restart}). "
                f"Currently executing tasks will complete before restart."
            )

            # Confirmation in session state
            if st.button(
                "✅ Confirm Restart",
                key="confirm_restart_button",
                type="secondary",
            ):
                with st.spinner(f"Restarting worker {selected_worker_restart}..."):
                    success, message = restart_worker_k8s(selected_worker_restart)

                if success:
                    st.success(f"✅ {message}")
                    logger.info(
                        f"Admin UI: Worker restart initiated for {selected_worker_restart}"
                    )
                else:
                    st.error(f"❌ {message}")
                    logger.error(
                        f"Admin UI: Worker restart failed for {selected_worker_restart}: {message}"
                    )

    with col2:
        st.markdown("**Worker Logs Viewer**")

        selected_worker_logs = st.selectbox(
            "Select Worker",
            options=worker_hostnames,
            key="logs_worker_select",
        )

        col_filter1, col_filter2 = st.columns(2)

        with col_filter1:
            log_level = st.selectbox(
                "Log Level",
                ["all", "ERROR", "WARNING", "INFO", "DEBUG"],
                key="log_level_filter",
            )

        with col_filter2:
            log_lines = st.slider(
                "Lines to show",
                min_value=10,
                max_value=500,
                value=100,
                step=10,
                key="log_lines_slider",
            )

        if st.button("📜 Fetch Logs", key="fetch_logs_button"):
            with st.spinner(f"Fetching logs from {selected_worker_logs}..."):
                logs = fetch_worker_logs(selected_worker_logs, log_lines, log_level)

            st.code("\n".join(logs), language="log", line_numbers=False)

            # Download button
            st.download_button(
                label="💾 Download Logs",
                data="\n".join(logs),
                file_name=f"{selected_worker_logs}_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                key="download_logs_button",
            )

    st.divider()

    # Historical Performance Charts Section
    st.subheader("📊 Historical Performance (7 Days)")
    st.caption("Task throughput over the past 7 days with average reference line")

    # Create tabs for each worker
    tabs = st.tabs([w["hostname"] for w in workers])

    for tab, worker in zip(tabs, workers):
        with tab:
            with st.spinner(f"Loading historical data for {worker['hostname']}..."):
                historical_data = fetch_worker_throughput_history(
                    worker["hostname"], days=7
                )

            if historical_data:
                fig = create_worker_performance_chart(
                    historical_data, worker["hostname"]
                )
                st.plotly_chart(fig, use_container_width=True)

                # Summary statistics
                col1, col2, col3 = st.columns(3)

                throughputs = [d["value"] for d in historical_data]
                avg_throughput = sum(throughputs) / len(throughputs)
                max_throughput = max(throughputs)
                min_throughput = min(throughputs)

                with col1:
                    st.metric("Average Throughput", f"{avg_throughput:.2f} tasks/min")

                with col2:
                    st.metric("Peak Throughput", f"{max_throughput:.2f} tasks/min")

                with col3:
                    st.metric("Minimum Throughput", f"{min_throughput:.2f} tasks/min")

            else:
                st.info(
                    f"No historical data available for {worker['hostname']}. "
                    "This may indicate Prometheus is unavailable or worker metrics are not instrumented."
                )


# Call the display function to render the page
display_workers_page()
