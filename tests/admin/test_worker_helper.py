"""
Unit tests for worker_helper.py - Worker health and resource monitoring functions.

Tests cover:
    - Celery worker discovery and status determination
    - Resource metrics fetching from Prometheus
    - Worker restart via Kubernetes API
    - Worker logs viewing from Kubernetes
    - Historical performance data and charting
    - Utility functions (format_uptime, get_status_icon, get_cpu_alert_icon)

Story: 6.7 - Add Worker Health and Resource Monitoring
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, patch

import plotly.graph_objects as go
import pytest

from src.admin.utils.worker_helper import (
    create_worker_performance_chart,
    fetch_celery_workers,
    fetch_worker_logs,
    fetch_worker_resources,
    fetch_worker_throughput_history,
    format_uptime,
    get_celery_app,
    get_cpu_alert_icon,
    get_status_icon,
    restart_worker_k8s,
)


@pytest.fixture(autouse=True)
def clear_streamlit_cache():
    """Clear Streamlit cache before each test."""
    import streamlit as st

    st.cache_data.clear()
    st.cache_resource.clear()


class TestGetCeleryApp:
    """Test Celery app initialization and caching."""

    @patch("src.admin.utils.worker_helper.Celery")
    def test_get_celery_app_creates_instance(self, mock_celery):
        """Test get_celery_app creates Celery instance with correct config."""
        mock_app = Mock()
        mock_celery.return_value = mock_app

        app = get_celery_app()

        assert app == mock_app
        mock_celery.assert_called_once()

    @patch("src.admin.utils.worker_helper.Celery")
    def test_get_celery_app_uses_cache(self, mock_celery):
        """Test get_celery_app uses cache on subsequent calls."""
        mock_app = Mock()
        mock_celery.return_value = mock_app

        # First call creates instance
        app1 = get_celery_app()
        # Second call should use cached instance
        app2 = get_celery_app()

        assert app1 == app2
        # Celery() should only be called once due to caching
        assert mock_celery.call_count == 1


class TestFetchCeleryWorkers:
    """Test Celery worker discovery and metadata fetching."""

    @patch("src.admin.utils.worker_helper.get_celery_app")
    def test_fetch_celery_workers_success(self, mock_get_app):
        """Test successful worker discovery with active and idle workers."""
        # Mock Celery app and inspector
        mock_inspector = Mock()
        mock_inspector.ping.return_value = {
            "celery@worker-1": {"ok": "pong"},
            "celery@worker-2": {"ok": "pong"},
        }
        mock_inspector.stats.return_value = {
            "celery@worker-1": {
                "clock": 86400,  # 1 day uptime
                "total": {"task1": 100, "task2": 200},  # 300 completed tasks
            },
            "celery@worker-2": {
                "clock": 3600,  # 1 hour uptime
                "total": {"task1": 50},  # 50 completed tasks
            },
        }
        mock_inspector.active.return_value = {
            "celery@worker-1": [{"id": "task-uuid-1"}],  # 1 active task
            "celery@worker-2": [],  # 0 active tasks (idle)
        }

        mock_app = Mock()
        mock_app.control.inspect.return_value = mock_inspector
        mock_get_app.return_value = mock_app

        workers = fetch_celery_workers()

        assert len(workers) == 2

        # Check worker-1 (active)
        assert workers[0]["hostname"] == "worker-1"
        assert workers[0]["uptime_seconds"] == 86400
        assert workers[0]["active_tasks"] == 1
        assert workers[0]["completed_tasks"] == 300
        assert workers[0]["status"] == "active"

        # Check worker-2 (idle)
        assert workers[1]["hostname"] == "worker-2"
        assert workers[1]["uptime_seconds"] == 3600
        assert workers[1]["active_tasks"] == 0
        assert workers[1]["completed_tasks"] == 50
        assert workers[1]["status"] == "idle"

    @patch("src.admin.utils.worker_helper.get_celery_app")
    def test_fetch_celery_workers_no_workers(self, mock_get_app):
        """Test behavior when no workers are active."""
        mock_inspector = Mock()
        mock_inspector.ping.return_value = {}

        mock_app = Mock()
        mock_app.control.inspect.return_value = mock_inspector
        mock_get_app.return_value = mock_app

        workers = fetch_celery_workers()

        assert workers == []

    @patch("src.admin.utils.worker_helper.get_celery_app")
    def test_fetch_celery_workers_connection_error(self, mock_get_app):
        """Test graceful handling of connection errors."""
        mock_app = Mock()
        mock_app.control.inspect.side_effect = Exception("Connection refused")
        mock_get_app.return_value = mock_app

        workers = fetch_celery_workers()

        assert workers == []


class TestFetchWorkerResources:
    """Test worker resource metrics fetching from Prometheus."""

    @patch("src.admin.utils.worker_helper.fetch_prometheus_range_query")
    def test_fetch_worker_resources_success(self, mock_prometheus):
        """Test successful resource metrics fetching."""
        # Mock Prometheus responses
        def prometheus_side_effect(query, start_time, end_time, step):
            if "cpu_percent" in query:
                return ([{"value": 45.2}], False)
            elif "memory_percent" in query:
                return ([{"value": 62.8}], False)
            elif "rate(celery_task_succeeded_total" in query:
                return ([{"value": 12.5}], False)
            return ([], True)

        mock_prometheus.side_effect = prometheus_side_effect

        resources = fetch_worker_resources(["worker-1"])

        assert "worker-1" in resources
        assert resources["worker-1"]["cpu_percent"] == 45.2
        assert resources["worker-1"]["memory_percent"] == 62.8
        assert resources["worker-1"]["throughput_tasks_per_min"] == 12.5
        assert resources["worker-1"]["data_available"] is True

    @patch("src.admin.utils.worker_helper.fetch_prometheus_range_query")
    def test_fetch_worker_resources_prometheus_unavailable(self, mock_prometheus):
        """Test fallback when Prometheus is unavailable."""
        mock_prometheus.return_value = ([], True)  # unavailable=True

        resources = fetch_worker_resources(["worker-1"])

        assert "worker-1" in resources
        assert resources["worker-1"]["cpu_percent"] == 0.0
        assert resources["worker-1"]["memory_percent"] == 0.0
        assert resources["worker-1"]["throughput_tasks_per_min"] == 0.0
        assert resources["worker-1"]["data_available"] is False

    @patch("src.admin.utils.worker_helper.fetch_prometheus_range_query")
    def test_fetch_worker_resources_multiple_workers(self, mock_prometheus):
        """Test fetching resources for multiple workers."""
        mock_prometheus.return_value = ([{"value": 50.0}], False)

        resources = fetch_worker_resources(["worker-1", "worker-2", "worker-3"])

        assert len(resources) == 3
        assert "worker-1" in resources
        assert "worker-2" in resources
        assert "worker-3" in resources


class TestRestartWorkerK8s:
    """Test worker restart via Kubernetes API."""

    @patch("src.admin.utils.worker_helper.config")
    @patch("src.admin.utils.worker_helper.client")
    def test_restart_worker_k8s_success(self, mock_client, mock_config):
        """Test successful worker restart."""
        mock_apps_v1 = Mock()
        mock_apps_v1.patch_namespaced_deployment.return_value = Mock()
        mock_client.AppsV1Api.return_value = mock_apps_v1

        success, message = restart_worker_k8s("worker-1")

        assert success is True
        assert "Worker restart initiated" in message
        assert "worker-1" in message
        mock_apps_v1.patch_namespaced_deployment.assert_called_once()

    @patch("src.admin.utils.worker_helper.config")
    @patch("src.admin.utils.worker_helper.client")
    def test_restart_worker_k8s_permission_denied(self, mock_client, mock_config):
        """Test handling of permission denied errors."""
        from kubernetes.client.rest import ApiException

        mock_apps_v1 = Mock()
        api_exception = ApiException(status=403, reason="Forbidden")
        mock_apps_v1.patch_namespaced_deployment.side_effect = api_exception
        mock_client.AppsV1Api.return_value = mock_apps_v1

        success, message = restart_worker_k8s("worker-1")

        assert success is False
        assert "Permission denied" in message
        assert "RBAC" in message

    @patch("src.admin.utils.worker_helper.config")
    @patch("src.admin.utils.worker_helper.client")
    def test_restart_worker_k8s_deployment_not_found(self, mock_client, mock_config):
        """Test handling when deployment doesn't exist."""
        from kubernetes.client.rest import ApiException

        mock_apps_v1 = Mock()
        api_exception = ApiException(status=404, reason="Not Found")
        mock_apps_v1.patch_namespaced_deployment.side_effect = api_exception
        mock_client.AppsV1Api.return_value = mock_apps_v1

        success, message = restart_worker_k8s("worker-1")

        assert success is False
        assert "not found" in message

    @patch("src.admin.utils.worker_helper.config")
    @patch("src.admin.utils.worker_helper.client")
    def test_restart_worker_k8s_unexpected_error(self, mock_client, mock_config):
        """Test handling of unexpected errors."""
        mock_client.AppsV1Api.side_effect = Exception("Unexpected error")

        success, message = restart_worker_k8s("worker-1")

        assert success is False
        assert "Unexpected error" in message


class TestFetchWorkerLogs:
    """Test worker logs fetching from Kubernetes."""

    @patch("src.admin.utils.worker_helper.config")
    @patch("src.admin.utils.worker_helper.client")
    def test_fetch_worker_logs_success(self, mock_client, mock_config):
        """Test successful log fetching."""
        mock_v1 = Mock()

        # Mock pod list response
        mock_pod = Mock()
        mock_pod.metadata.name = "celery-worker-abc123"
        mock_pod_list = Mock()
        mock_pod_list.items = [mock_pod]
        mock_v1.list_namespaced_pod.return_value = mock_pod_list

        # Mock logs response
        mock_logs = (
            "2025-11-04 10:30:15 INFO Worker started\n"
            "2025-11-04 10:30:20 INFO Task received\n"
            "2025-11-04 10:30:25 ERROR Task failed"
        )
        mock_v1.read_namespaced_pod_log.return_value = mock_logs
        mock_client.CoreV1Api.return_value = mock_v1

        logs = fetch_worker_logs("worker-1", lines=100, log_level="all")

        assert len(logs) == 3
        assert "Worker started" in logs[0]
        assert "Task received" in logs[1]
        assert "Task failed" in logs[2]

    @patch("src.admin.utils.worker_helper.config")
    @patch("src.admin.utils.worker_helper.client")
    def test_fetch_worker_logs_filter_by_level(self, mock_client, mock_config):
        """Test log filtering by log level."""
        mock_v1 = Mock()

        mock_pod = Mock()
        mock_pod.metadata.name = "celery-worker-abc123"
        mock_pod_list = Mock()
        mock_pod_list.items = [mock_pod]
        mock_v1.list_namespaced_pod.return_value = mock_pod_list

        mock_logs = (
            "2025-11-04 10:30:15 INFO Worker started\n"
            "2025-11-04 10:30:20 ERROR Task failed\n"
            "2025-11-04 10:30:25 INFO Task completed"
        )
        mock_v1.read_namespaced_pod_log.return_value = mock_logs
        mock_client.CoreV1Api.return_value = mock_v1

        logs = fetch_worker_logs("worker-1", lines=100, log_level="ERROR")

        assert len(logs) == 1
        assert "ERROR" in logs[0]

    @patch("src.admin.utils.worker_helper.config")
    @patch("src.admin.utils.worker_helper.client")
    def test_fetch_worker_logs_no_pods_found(self, mock_client, mock_config):
        """Test behavior when no pods are found."""
        mock_v1 = Mock()
        mock_pod_list = Mock()
        mock_pod_list.items = []
        mock_v1.list_namespaced_pod.return_value = mock_pod_list
        mock_client.CoreV1Api.return_value = mock_v1

        logs = fetch_worker_logs("worker-1")

        assert len(logs) == 1
        assert "No pods found" in logs[0]


class TestFetchWorkerThroughputHistory:
    """Test historical throughput data fetching."""

    @patch("src.admin.utils.worker_helper.fetch_prometheus_range_query")
    def test_fetch_worker_throughput_history_success(self, mock_prometheus):
        """Test successful historical data fetching."""
        mock_data = [
            {"timestamp": datetime.now(timezone.utc), "value": 10.5},
            {"timestamp": datetime.now(timezone.utc), "value": 12.3},
            {"timestamp": datetime.now(timezone.utc), "value": 11.8},
        ]
        mock_prometheus.return_value = (mock_data, False)

        data = fetch_worker_throughput_history("worker-1", days=7)

        assert len(data) == 3
        assert data[0]["value"] == 10.5
        assert data[1]["value"] == 12.3
        assert data[2]["value"] == 11.8

    @patch("src.admin.utils.worker_helper.fetch_prometheus_range_query")
    def test_fetch_worker_throughput_history_prometheus_unavailable(
        self, mock_prometheus
    ):
        """Test handling when Prometheus is unavailable."""
        mock_prometheus.return_value = ([], True)

        data = fetch_worker_throughput_history("worker-1", days=7)

        assert data == []


class TestCreateWorkerPerformanceChart:
    """Test worker performance chart creation."""

    @patch("src.admin.utils.worker_helper.create_timeseries_chart")
    def test_create_worker_performance_chart_with_data(self, mock_create_chart):
        """Test chart creation with valid data."""
        mock_fig = go.Figure()
        mock_create_chart.return_value = mock_fig

        data = [
            {"timestamp": datetime.now(timezone.utc), "value": 10.0},
            {"timestamp": datetime.now(timezone.utc), "value": 12.0},
            {"timestamp": datetime.now(timezone.utc), "value": 11.0},
        ]

        fig = create_worker_performance_chart(data, "worker-1")

        assert isinstance(fig, go.Figure)
        mock_create_chart.assert_called_once()

    @patch("src.admin.utils.worker_helper.create_timeseries_chart")
    def test_create_worker_performance_chart_empty_data(self, mock_create_chart):
        """Test chart creation with empty data."""
        mock_fig = go.Figure()
        mock_create_chart.return_value = mock_fig

        data = []

        fig = create_worker_performance_chart(data, "worker-1")

        assert isinstance(fig, go.Figure)
        # Should not add average line when data is empty


class TestUtilityFunctions:
    """Test utility functions for formatting and icons."""

    def test_format_uptime_days_hours_minutes(self):
        """Test uptime formatting with days, hours, and minutes."""
        uptime_seconds = 186000  # 2 days, 3 hours, 40 minutes
        formatted = format_uptime(uptime_seconds)

        assert "2d" in formatted
        assert "3h" in formatted
        assert "40m" in formatted

    def test_format_uptime_hours_minutes(self):
        """Test uptime formatting with hours and minutes only."""
        uptime_seconds = 3661  # 1 hour, 1 minute
        formatted = format_uptime(uptime_seconds)

        assert "1h" in formatted
        assert "1m" in formatted
        assert "d" not in formatted

    def test_format_uptime_minutes_only(self):
        """Test uptime formatting with minutes only."""
        uptime_seconds = 120  # 2 minutes
        formatted = format_uptime(uptime_seconds)

        assert "2m" in formatted
        assert "h" not in formatted
        assert "d" not in formatted

    def test_format_uptime_zero(self):
        """Test uptime formatting for zero seconds."""
        uptime_seconds = 0
        formatted = format_uptime(uptime_seconds)

        assert formatted == "0m"

    def test_get_status_icon_active(self):
        """Test status icon for active worker."""
        icon = get_status_icon("active")
        assert icon == "🟢"

    def test_get_status_icon_idle(self):
        """Test status icon for idle worker."""
        icon = get_status_icon("idle")
        assert icon == "🟡"

    def test_get_status_icon_unresponsive(self):
        """Test status icon for unresponsive worker."""
        icon = get_status_icon("unresponsive")
        assert icon == "🔴"

    def test_get_status_icon_unknown(self):
        """Test status icon for unknown status."""
        icon = get_status_icon("unknown")
        assert icon == "⚪"

    def test_get_cpu_alert_icon_normal(self):
        """Test CPU alert icon for normal usage (<80%)."""
        icon = get_cpu_alert_icon(45.0)
        assert icon == "🟢"

    def test_get_cpu_alert_icon_warning(self):
        """Test CPU alert icon for warning threshold (80-95%)."""
        icon = get_cpu_alert_icon(85.0)
        assert icon == "🟡"

    def test_get_cpu_alert_icon_critical(self):
        """Test CPU alert icon for critical threshold (>95%)."""
        icon = get_cpu_alert_icon(98.0)
        assert icon == "🔴"

    def test_get_cpu_alert_icon_boundary_80(self):
        """Test CPU alert icon at 80% boundary."""
        icon = get_cpu_alert_icon(80.0)
        assert icon == "🟡"

    def test_get_cpu_alert_icon_boundary_95(self):
        """Test CPU alert icon at 95% boundary."""
        icon = get_cpu_alert_icon(95.0)
        assert icon == "🔴"
