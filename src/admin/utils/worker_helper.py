"""
Worker health and resource monitoring helper functions.

This module provides functions for monitoring Celery worker health, resource
utilization, and operational controls (restart, logs viewing). It integrates
with Celery inspect API, Prometheus metrics, and Kubernetes API.

Key Features:
    - Worker discovery via Celery inspect (ping, stats, active)
    - Resource metrics from Prometheus (CPU%, Memory%, throughput)
    - Worker restart via Kubernetes deployment patch
    - Worker logs viewing from Kubernetes pod logs
    - Historical performance charts (7-day throughput)

Dependencies:
    - celery: Worker discovery and monitoring
    - kubernetes: K8s API for restart and logs
    - httpx: Prometheus HTTP API queries
    - plotly: Interactive performance charts
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import plotly.graph_objects as go
import streamlit as st
from celery import Celery
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from loguru import logger

from admin.utils.metrics_helper import (
    create_timeseries_chart,
    fetch_prometheus_range_query,
)
from src.config import settings


@st.cache_resource
def get_celery_app() -> Celery:
    """
    Get or create Celery application instance for worker monitoring.

    Uses Streamlit cache_resource to maintain a single Celery app instance
    across page refreshes. The app is configured with broker URL from settings.

    Returns:
        Celery: Configured Celery application instance

    Examples:
        >>> app = get_celery_app()
        >>> inspector = app.control.inspect()
        >>> workers = inspector.ping()
    """
    app = Celery(
        settings.celery_app_name,
        broker=settings.celery_broker_url,
    )
    logger.info(f"Celery app initialized for monitoring: {settings.celery_app_name}")
    return app


@st.cache_data(ttl=30)
def fetch_celery_workers() -> list[dict[str, Any]]:
    """
    Fetch active Celery workers with metadata via inspect API.

    Uses Celery's control.inspect() to discover active workers and fetch
    statistics including hostname, uptime, task counts, and status.

    Worker status determination:
        - "active": Worker has active tasks currently executing
        - "idle": Worker is responsive but has no active tasks
        - "unresponsive": Worker did not respond to ping

    Returns:
        list[dict]: List of worker metadata dictionaries with keys:
            - hostname (str): Worker hostname (after @ in worker name)
            - uptime_seconds (int): Worker uptime in seconds
            - active_tasks (int): Number of currently executing tasks
            - completed_tasks (int): Total completed tasks (approximate)
            - status (str): Worker status (active/idle/unresponsive)

    Raises:
        None: Returns empty list on connection errors with logged warning

    Examples:
        >>> workers = fetch_celery_workers()
        >>> for worker in workers:
        ...     print(f"{worker['hostname']}: {worker['status']}")
        worker-1: active
        worker-2: idle
    """
    try:
        app = get_celery_app()
        inspector = app.control.inspect()

        # Discover active workers via ping
        ping_result = inspector.ping()
        if not ping_result:
            logger.warning("No active Celery workers found (ping returned empty)")
            return []

        # Get worker statistics for all workers
        stats_result = inspector.stats() or {}
        active_result = inspector.active() or {}

        workers = []
        for worker_name in ping_result.keys():
            # Extract hostname from worker name (format: celery@hostname)
            hostname = worker_name.split("@")[1] if "@" in worker_name else worker_name

            # Get worker statistics
            worker_stats = stats_result.get(worker_name, {})

            # Parse uptime from clock field (seconds since worker started)
            uptime_seconds = int(worker_stats.get("clock", 0) or 0)

            # Get total completed tasks (sum of all task type counts)
            total_stats = worker_stats.get("total", {})
            if isinstance(total_stats, dict):
                completed_tasks = sum(
                    v for v in total_stats.values() if isinstance(v, int)
                )
            else:
                completed_tasks = 0

            # Get active task count
            active_tasks = len(active_result.get(worker_name, []))

            # Determine worker status
            status = "active" if active_tasks > 0 else "idle"

            workers.append(
                {
                    "hostname": hostname,
                    "uptime_seconds": uptime_seconds,
                    "active_tasks": active_tasks,
                    "completed_tasks": completed_tasks,
                    "status": status,
                }
            )

        logger.info(f"Fetched {len(workers)} active Celery workers")
        return workers

    except Exception as e:
        logger.error(f"Failed to fetch Celery workers: {e}", exc_info=True)
        return []


@st.cache_data(ttl=30)
def fetch_worker_resources(worker_hostnames: list[str]) -> dict[str, dict[str, float]]:
    """
    Fetch worker resource utilization metrics from Prometheus.

    Queries Prometheus for worker-level CPU%, Memory%, and task throughput
    (tasks/min) metrics. Returns placeholder values (0.0) if Prometheus
    is unavailable or metrics don't exist.

    Args:
        worker_hostnames: List of worker hostnames to query

    Returns:
        dict: Mapping of hostname to resource metrics dict with keys:
            - cpu_percent (float): CPU usage percentage (0-100)
            - memory_percent (float): Memory usage percentage (0-100)
            - throughput_tasks_per_min (float): Task completion rate
            - data_available (bool): Whether metrics were fetched successfully

    Examples:
        >>> resources = fetch_worker_resources(["worker-1", "worker-2"])
        >>> print(resources["worker-1"])
        {'cpu_percent': 45.2, 'memory_percent': 62.8, 'throughput_tasks_per_min': 12.5}
    """
    resources = {}

    for hostname in worker_hostnames:
        try:
            # Query current CPU percentage
            cpu_query = f'celery_worker_cpu_percent{{worker="{hostname}"}}'
            cpu_data, cpu_unavailable = fetch_prometheus_range_query(
                query=cpu_query,
                start_time=datetime.now(timezone.utc) - timedelta(minutes=1),
                end_time=datetime.now(timezone.utc),
                step="1m",
            )

            # Query current memory percentage
            memory_query = f'celery_worker_memory_percent{{worker="{hostname}"}}'
            memory_data, memory_unavailable = fetch_prometheus_range_query(
                query=memory_query,
                start_time=datetime.now(timezone.utc) - timedelta(minutes=1),
                end_time=datetime.now(timezone.utc),
                step="1m",
            )

            # Calculate throughput from task success rate
            # rate() gives tasks/sec, multiply by 60 for tasks/min
            throughput_query = (
                f'rate(celery_task_succeeded_total{{worker="{hostname}"}}[5m]) * 60'
            )
            throughput_data, throughput_unavailable = fetch_prometheus_range_query(
                query=throughput_query,
                start_time=datetime.now(timezone.utc) - timedelta(minutes=5),
                end_time=datetime.now(timezone.utc),
                step="1m",
            )

            # Extract latest values or use 0.0 as fallback
            cpu_percent = float(cpu_data[-1]["value"]) if cpu_data else 0.0
            memory_percent = float(memory_data[-1]["value"]) if memory_data else 0.0
            throughput = float(throughput_data[-1]["value"]) if throughput_data else 0.0

            data_available = not (
                cpu_unavailable and memory_unavailable and throughput_unavailable
            )

            resources[hostname] = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "throughput_tasks_per_min": throughput,
                "data_available": data_available,
            }

        except Exception as e:
            logger.warning(
                f"Failed to fetch resources for worker {hostname}: {e}",
                exc_info=True,
            )
            resources[hostname] = {
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "throughput_tasks_per_min": 0.0,
                "data_available": False,
            }

    return resources


def restart_worker_k8s(worker_hostname: str) -> tuple[bool, str]:
    """
    Restart Celery worker via Kubernetes deployment patch (graceful rolling restart).

    Patches the Celery worker deployment with a restart annotation, triggering
    a Kubernetes rolling restart. This is graceful: currently executing tasks
    complete before the pod is terminated.

    WARNING: This restarts ALL worker pods in the deployment, not just the
    specific worker hostname. Use with caution in production.

    Args:
        worker_hostname: Worker hostname to restart (used for logging only)

    Returns:
        tuple: (success: bool, message: str)
            - success: True if restart initiated successfully
            - message: Success message or error description

    Raises:
        None: All exceptions are caught and returned as error messages

    Examples:
        >>> success, message = restart_worker_k8s("worker-1")
        >>> if success:
        ...     print(f"Restart initiated: {message}")
        ... else:
        ...     print(f"Restart failed: {message}")
    """
    try:
        # Load Kubernetes configuration
        if settings.kubernetes_in_cluster:
            config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes config")
        else:
            config.load_kube_config()
            logger.info("Loaded Kubernetes config from kubeconfig file")

        apps_v1 = client.AppsV1Api()

        # Deployment name pattern (assumes deployment is named "celery-worker")
        deployment_name = "celery-worker"

        # Patch deployment to trigger rolling restart
        # This updates the restart annotation, which Kubernetes detects as a change
        body = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "kubectl.kubernetes.io/restartedAt": datetime.now(
                                timezone.utc
                            ).isoformat()
                        }
                    }
                }
            }
        }

        apps_v1.patch_namespaced_deployment(
            name=deployment_name,
            namespace=settings.kubernetes_namespace,
            body=body,
        )

        success_msg = (
            f"Worker restart initiated for {worker_hostname} "
            f"(deployment: {deployment_name}, namespace: {settings.kubernetes_namespace})"
        )
        logger.info(success_msg)
        return True, success_msg

    except ApiException as e:
        if e.status == 403:
            error_msg = (
                f"Permission denied: Streamlit pod lacks RBAC permissions to patch deployments. "
                f"Check ServiceAccount and RoleBinding configuration."
            )
        elif e.status == 404:
            error_msg = (
                f"Deployment '{deployment_name}' not found in namespace '{settings.kubernetes_namespace}'. "
                f"Verify deployment exists and namespace is correct."
            )
        else:
            error_msg = f"Kubernetes API error (status {e.status}): {e.reason}"

        logger.error(f"Failed to restart worker {worker_hostname}: {error_msg}")
        return False, error_msg

    except Exception as e:
        error_msg = f"Unexpected error restarting worker: {str(e)}"
        logger.error(f"Failed to restart worker {worker_hostname}: {e}", exc_info=True)
        return False, error_msg


def fetch_worker_logs(
    worker_hostname: str, lines: int = 100, log_level: str = "all"
) -> list[str]:
    """
    Fetch worker logs from Kubernetes pod.

    Retrieves the last N lines of logs from the worker pod matching the hostname.
    Logs can be filtered by log level (ERROR, WARNING, INFO, DEBUG).

    Args:
        worker_hostname: Worker hostname to fetch logs for
        lines: Number of log lines to retrieve (default: 100)
        log_level: Filter logs by level ("all", "ERROR", "WARNING", "INFO", "DEBUG")

    Returns:
        list[str]: List of log lines (may be filtered by level)

    Raises:
        None: Returns error message in list on failure

    Examples:
        >>> logs = fetch_worker_logs("worker-1", lines=50, log_level="ERROR")
        >>> print("\\n".join(logs))
        2025-11-04 10:30:15 ERROR Task failed: division by zero
        2025-11-04 10:31:22 ERROR Connection timeout to database
    """
    try:
        # Load Kubernetes configuration
        if settings.kubernetes_in_cluster:
            config.load_incluster_config()
        else:
            config.load_kube_config()

        v1 = client.CoreV1Api()

        # Find pod for worker (assumes label: app=celery-worker)
        # Note: This finds ANY celery-worker pod, not necessarily the specific hostname
        # For hostname-specific lookup, workers need pod labels like worker-name=hostname
        pods = v1.list_namespaced_pod(
            namespace=settings.kubernetes_namespace,
            label_selector="app=celery-worker",
        )

        if not pods.items:
            error_msg = (
                f"No pods found with label 'app=celery-worker' in namespace "
                f"'{settings.kubernetes_namespace}'"
            )
            logger.warning(error_msg)
            return [error_msg]

        # Use first pod (in production, should match by hostname label)
        pod_name = pods.items[0].metadata.name
        logger.info(
            f"Fetching logs from pod {pod_name} for worker {worker_hostname} "
            f"({lines} lines, level: {log_level})"
        )

        # Fetch logs with timestamp
        logs = v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=settings.kubernetes_namespace,
            tail_lines=lines,
            timestamps=True,
        )

        log_lines = logs.split("\n")

        # Filter by log level if specified
        if log_level != "all":
            log_lines = [
                line for line in log_lines if log_level.upper() in line.upper()
            ]

        logger.info(
            f"Retrieved {len(log_lines)} log lines from worker {worker_hostname}"
        )
        return log_lines if log_lines else ["No logs found"]

    except ApiException as e:
        if e.status == 403:
            error_msg = (
                "Permission denied: Streamlit pod lacks RBAC permissions to read pod logs. "
                "Check ServiceAccount and RoleBinding configuration."
            )
        elif e.status == 404:
            error_msg = f"Pod not found in namespace '{settings.kubernetes_namespace}'"
        else:
            error_msg = f"Kubernetes API error (status {e.status}): {e.reason}"

        logger.error(f"Failed to fetch logs for worker {worker_hostname}: {error_msg}")
        return [f"Error: {error_msg}"]

    except Exception as e:
        error_msg = f"Unexpected error fetching logs: {str(e)}"
        logger.error(
            f"Failed to fetch logs for worker {worker_hostname}: {e}", exc_info=True
        )
        return [f"Error: {error_msg}"]


@st.cache_data(ttl=300)
def fetch_worker_throughput_history(
    worker_hostname: str, days: int = 7
) -> list[dict[str, Any]]:
    """
    Fetch 7-day historical throughput data for worker from Prometheus.

    Queries Prometheus for task completion rate over the past N days,
    returning time-series data suitable for charting.

    Args:
        worker_hostname: Worker hostname to fetch history for
        days: Number of days of history to fetch (default: 7)

    Returns:
        list[dict]: Time-series data with keys:
            - timestamp (datetime): Data point timestamp
            - value (float): Throughput in tasks/min

    Examples:
        >>> data = fetch_worker_throughput_history("worker-1", days=7)
        >>> print(f"Data points: {len(data)}")
        Data points: 168
    """
    try:
        # Query Prometheus for 7-day throughput history
        # rate() calculates per-second rate, multiply by 60 for tasks/min
        query = f'rate(celery_task_succeeded_total{{worker="{worker_hostname}"}}[5m]) * 60'

        data, unavailable = fetch_prometheus_range_query(
            query=query,
            start_time=datetime.now(timezone.utc) - timedelta(days=days),
            end_time=datetime.now(timezone.utc),
            step="1h",  # 1-hour steps for 7 days = 168 data points
        )

        if unavailable:
            logger.warning(
                f"Prometheus unavailable for worker {worker_hostname} history"
            )

        logger.info(
            f"Fetched {len(data)} historical throughput data points for worker {worker_hostname}"
        )
        return data

    except Exception as e:
        logger.error(
            f"Failed to fetch throughput history for worker {worker_hostname}: {e}",
            exc_info=True,
        )
        return []


def create_worker_performance_chart(
    data: list[dict[str, Any]], worker_name: str
) -> go.Figure:
    """
    Create historical worker performance chart with average line.

    Generates a Plotly time-series chart showing worker throughput over time,
    with a horizontal average line for reference.

    Args:
        data: Time-series data from fetch_worker_throughput_history()
        worker_name: Worker name for chart title

    Returns:
        go.Figure: Plotly figure object ready for display

    Examples:
        >>> data = fetch_worker_throughput_history("worker-1")
        >>> fig = create_worker_performance_chart(data, "worker-1")
        >>> st.plotly_chart(fig, use_container_width=True)
    """
    # Use base chart creation from Story 6.6
    fig = create_timeseries_chart(
        data=data,
        title=f"{worker_name} - 7-Day Average Throughput",
        y_label="Tasks/Min",
        color="#1f77b4",
    )

    # Add average line annotation
    if data:
        avg_throughput = sum(d["value"] for d in data) / len(data)
        fig.add_hline(
            y=avg_throughput,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Avg: {avg_throughput:.1f} tasks/min",
            annotation_position="bottom right",
        )
        logger.debug(f"Added average line to chart: {avg_throughput:.1f} tasks/min")

    return fig


def format_uptime(uptime_seconds: int) -> str:
    """
    Format uptime seconds as human-readable string.

    Args:
        uptime_seconds: Uptime in seconds

    Returns:
        str: Formatted uptime (e.g., "2d 5h 30m")

    Examples:
        >>> format_uptime(186000)
        '2d 3h 40m'
        >>> format_uptime(3661)
        '1h 1m'
    """
    days = uptime_seconds // 86400
    hours = (uptime_seconds % 86400) // 3600
    minutes = (uptime_seconds % 3600) // 60

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")

    return " ".join(parts) if parts else "0m"


def get_status_icon(status: str) -> str:
    """
    Get emoji icon for worker status.

    Args:
        status: Worker status ("active", "idle", "unresponsive")

    Returns:
        str: Emoji icon

    Examples:
        >>> get_status_icon("active")
        '🟢'
        >>> get_status_icon("unresponsive")
        '🔴'
    """
    status_icons = {
        "active": "🟢",
        "idle": "🟡",
        "unresponsive": "🔴",
    }
    return status_icons.get(status, "⚪")


def get_cpu_alert_icon(cpu_percent: float) -> str:
    """
    Get alert icon for CPU utilization threshold.

    Thresholds:
        - <80%: Green (normal)
        - 80-95%: Yellow (warning)
        - >95%: Red (critical)

    Args:
        cpu_percent: CPU usage percentage

    Returns:
        str: Alert emoji icon

    Examples:
        >>> get_cpu_alert_icon(45.0)
        '🟢'
        >>> get_cpu_alert_icon(85.0)
        '🟡'
        >>> get_cpu_alert_icon(98.0)
        '🔴'
    """
    if cpu_percent < 80:
        return "🟢"
    elif cpu_percent < 95:
        return "🟡"
    else:
        return "🔴"
