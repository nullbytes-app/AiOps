"""
MCP Server UI Helpers - Streamlit UI functions for MCP server management.

Provides:
- API client functions for CRUD operations on MCP servers
- Helper functions for rendering status badges, timestamps
- Form handling for add/edit MCP server operations
- Test connection functionality
- Error handling and user feedback

This module enables the MCP Servers admin page to manage MCP server configurations
through a user-friendly Streamlit interface.
"""

import asyncio
import os
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
import streamlit as st

# ============================================================================
# Configuration
# ============================================================================

API_BASE_URL: str = os.getenv("API_BASE_URL", "http://api:8000")
# DEFAULT_TENANT_ID should match the id column (PRIMARY KEY) from tenant_configs table (must be UUID format)
# This is a fallback only - UI should get tenant_id from database/session
DEFAULT_TENANT_ID: str = os.getenv("AI_AGENTS_DEFAULT_TENANT_ID", os.getenv("DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000001"))


# ============================================================================
# Async API Functions
# ============================================================================


async def _fetch_mcp_servers_async(
    tenant_id: str,
    status: Optional[str] = None,
    transport_type: Optional[str] = None,
) -> list[dict[str, Any]]:
    """
    Fetch MCP servers from API (async).

    Args:
        tenant_id: Tenant ID to filter servers
        status: Optional status filter ('active', 'error', 'inactive')
        transport_type: Optional transport type filter ('stdio', 'http_sse')

    Returns:
        List of MCP server dicts from API

    Raises:
        httpx.HTTPError: If API request fails
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        params: dict[str, Any] = {}
        if status:
            params["status"] = status
        if transport_type:
            params["transport_type"] = transport_type

        response = await client.get(
            f"{API_BASE_URL}/api/v1/mcp-servers/",
            headers={"X-Tenant-ID": tenant_id},
            params=params,
        )
        response.raise_for_status()
        return response.json()


async def _fetch_mcp_server_details_async(server_id: str, tenant_id: str) -> dict[str, Any]:
    """
    Fetch MCP server details from API (async).

    Args:
        server_id: Server ID to fetch
        tenant_id: Tenant ID for authentication

    Returns:
        MCP server dict from API

    Raises:
        httpx.HTTPError: If API request fails (404 if not found)
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{API_BASE_URL}/api/v1/mcp-servers/{server_id}",
            headers={"X-Tenant-ID": tenant_id},
        )
        response.raise_for_status()
        return response.json()


async def _create_mcp_server_async(payload: dict[str, Any], tenant_id: str) -> dict[str, Any]:
    """
    Create MCP server via API (async).

    Args:
        payload: MCPServerCreate dict with server configuration
        tenant_id: Tenant ID for authentication

    Returns:
        Created MCP server dict from API

    Raises:
        httpx.HTTPError: If API request fails (400 for validation errors)
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{API_BASE_URL}/api/v1/mcp-servers/",
            headers={"X-Tenant-ID": tenant_id},
            json=payload,
        )
        response.raise_for_status()
        return response.json()


async def _update_mcp_server_async(
    server_id: str, payload: dict[str, Any], tenant_id: str
) -> dict[str, Any]:
    """
    Update MCP server via API (async).

    Args:
        server_id: Server ID to update
        payload: MCPServerUpdate dict with updated fields
        tenant_id: Tenant ID for authentication

    Returns:
        Updated MCP server dict from API

    Raises:
        httpx.HTTPError: If API request fails (404 if not found)
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.patch(
            f"{API_BASE_URL}/api/v1/mcp-servers/{server_id}",
            headers={"X-Tenant-ID": tenant_id},
            json=payload,
        )
        response.raise_for_status()
        return response.json()


async def _delete_mcp_server_async(server_id: str, tenant_id: str) -> bool:
    """
    Delete MCP server via API (async).

    Args:
        server_id: Server ID to delete
        tenant_id: Tenant ID for authentication

    Returns:
        True if deletion succeeded

    Raises:
        httpx.HTTPError: If API request fails (404 if not found)
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.delete(
            f"{API_BASE_URL}/api/v1/mcp-servers/{server_id}",
            headers={"X-Tenant-ID": tenant_id},
        )
        response.raise_for_status()
        return True


async def _rediscover_server_async(server_id: str, tenant_id: str) -> dict[str, Any]:
    """
    Rediscover MCP server capabilities via API (async).

    Args:
        server_id: Server ID to rediscover
        tenant_id: Tenant ID for authentication

    Returns:
        Updated MCP server dict with rediscovered capabilities

    Raises:
        httpx.HTTPError: If API request fails
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{API_BASE_URL}/api/v1/mcp-servers/{server_id}/discover",
            headers={"X-Tenant-ID": tenant_id},
        )
        response.raise_for_status()
        return response.json()


# ============================================================================
# Synchronous Wrappers (for Streamlit)
# ============================================================================


def fetch_mcp_servers(
    tenant_id: str,
    status: Optional[str] = None,
    transport_type: Optional[str] = None,
) -> list[dict[str, Any]]:
    """
    Fetch MCP servers from API.

    Args:
        tenant_id: Tenant ID to filter servers
        status: Optional status filter ('active', 'error', 'inactive')
        transport_type: Optional transport type filter ('stdio', 'http_sse')

    Returns:
        List of MCP server dicts from API

    Raises:
        Exception: If API request fails
    """
    try:
        return asyncio.run(_fetch_mcp_servers_async(tenant_id, status, transport_type))
    except httpx.HTTPStatusError as e:
        raise Exception(f"API request failed: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        raise Exception(f"Failed to fetch MCP servers: {str(e)}")


def fetch_mcp_server_details(server_id: str, tenant_id: str) -> dict[str, Any]:
    """
    Fetch MCP server details from API.

    Args:
        server_id: Server ID to fetch
        tenant_id: Tenant ID for authentication

    Returns:
        MCP server dict from API

    Raises:
        Exception: If API request fails
    """
    try:
        return asyncio.run(_fetch_mcp_server_details_async(server_id, tenant_id))
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise Exception(f"Server not found: {server_id}")
        raise Exception(f"API request failed: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        raise Exception(f"Failed to fetch server details: {str(e)}")


def create_mcp_server(payload: dict[str, Any], tenant_id: str) -> dict[str, Any]:
    """
    Create MCP server via API.

    Args:
        payload: MCPServerCreate dict with server configuration
        tenant_id: Tenant ID for authentication

    Returns:
        Created MCP server dict from API

    Raises:
        Exception: If API request fails
    """
    try:
        return asyncio.run(_create_mcp_server_async(payload, tenant_id))
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 400:
            raise Exception(f"Validation error: {e.response.text}")
        raise Exception(f"API request failed: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        raise Exception(f"Failed to create server: {str(e)}")


def update_mcp_server(server_id: str, payload: dict[str, Any], tenant_id: str) -> dict[str, Any]:
    """
    Update MCP server via API.

    Args:
        server_id: Server ID to update
        payload: MCPServerUpdate dict with updated fields
        tenant_id: Tenant ID for authentication

    Returns:
        Updated MCP server dict from API

    Raises:
        Exception: If API request fails
    """
    try:
        return asyncio.run(_update_mcp_server_async(server_id, payload, tenant_id))
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise Exception(f"Server not found: {server_id}")
        raise Exception(f"API request failed: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        raise Exception(f"Failed to update server: {str(e)}")


def delete_mcp_server(server_id: str, tenant_id: str) -> bool:
    """
    Delete MCP server via API.

    Args:
        server_id: Server ID to delete
        tenant_id: Tenant ID for authentication

    Returns:
        True if deletion succeeded

    Raises:
        Exception: If API request fails
    """
    try:
        return asyncio.run(_delete_mcp_server_async(server_id, tenant_id))
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise Exception(f"Server not found: {server_id}")
        raise Exception(f"API request failed: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        raise Exception(f"Failed to delete server: {str(e)}")


def rediscover_server(server_id: str, tenant_id: str) -> dict[str, Any]:
    """
    Rediscover MCP server capabilities via API.

    Args:
        server_id: Server ID to rediscover
        tenant_id: Tenant ID for authentication

    Returns:
        Updated MCP server dict with rediscovered capabilities

    Raises:
        Exception: If API request fails
    """
    try:
        return asyncio.run(_rediscover_server_async(server_id, tenant_id))
    except httpx.HTTPStatusError as e:
        raise Exception(f"API request failed: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        raise Exception(f"Failed to rediscover capabilities: {str(e)}")


# ============================================================================
# Helper Functions
# ============================================================================


def format_timestamp(ts: Optional[datetime]) -> str:
    """
    Format timestamp as relative time string.

    Args:
        ts: Datetime object to format (None returns "Never")

    Returns:
        Human-readable relative time string (e.g., "2 minutes ago")
    """
    if ts is None:
        return "Never"

    # Ensure timezone-aware comparison
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    delta = now - ts

    seconds = delta.total_seconds()
    if seconds < 60:
        return "Just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"


def render_status_badge(status: str) -> None:
    """
    Render status indicator with color coding.

    Note: st.badge() not available in Streamlit 1.44.0, using colored markdown instead.

    Args:
        status: Status value ('active', 'error', 'inactive')
    """
    status_colors = {
        "active": "🟢",
        "error": "🔴",
        "inactive": "⚪",
    }
    emoji = status_colors.get(status, "⚪")
    st.markdown(f"{emoji} **{status.title()}**")


def render_transport_badge(transport: str) -> None:
    """
    Render transport type badge.

    Args:
        transport: Transport type ('stdio' or 'http_sse')
    """
    transport_emojis = {
        "stdio": "🔌",
        "http_sse": "🌐",
    }
    emoji = transport_emojis.get(transport, "❓")
    st.markdown(f"{emoji} **{transport.upper()}**")


def is_sensitive_header(header_key: str) -> bool:
    """
    Check if header key contains sensitive keywords.

    Args:
        header_key: Header name to check

    Returns:
        True if header contains sensitive keywords requiring masking
    """
    sensitive_keywords = ["token", "key", "secret", "password", "auth", "bearer", "api"]
    header_lower = header_key.lower()
    return any(keyword in header_lower for keyword in sensitive_keywords)


async def _test_mcp_connection_async(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Test MCP server connection via API (async).

    Args:
        payload: MCPServerCreate dict with server configuration (no tenant_id required)

    Returns:
        Connection test result with discovered capabilities

    Raises:
        httpx.HTTPError: If API request fails
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{API_BASE_URL}/api/v1/mcp-servers/test-connection",
            json=payload,
        )
        response.raise_for_status()
        return response.json()


def test_mcp_connection(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Test MCP server connection via API.

    Args:
        payload: MCPServerCreate dict with server configuration

    Returns:
        Connection test result with discovered capabilities

    Raises:
        Exception: If API request fails
    """
    try:
        return asyncio.run(_test_mcp_connection_async(payload))
    except httpx.HTTPStatusError as e:
        raise Exception(f"API request failed: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        raise Exception(f"Failed to test connection: {str(e)}")



# ============================================================================
# MCP Server Health Metrics Helpers (Story 11.2.4)
# ============================================================================


async def _fetch_mcp_server_metrics_async(
    server_id: str, tenant_id: str, period_hours: int = 24
) -> dict[str, Any]:
    """
    Fetch health metrics for MCP server (async).

    Args:
        server_id: Server UUID string
        tenant_id: Tenant UUID string
        period_hours: Time period to analyze (default 24h)

    Returns:
        dict: Aggregated health metrics from API

    Raises:
        httpx.HTTPStatusError: If API request fails
    """
    import httpx

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{API_BASE_URL}/api/v1/mcp-servers/{server_id}/metrics",
            params={"period_hours": period_hours},
            headers={"X-Tenant-ID": tenant_id},
        )
        response.raise_for_status()
        return response.json()


def fetch_mcp_server_metrics(
    server_id: str, tenant_id: str, period_hours: int = 24
) -> dict[str, Any]:
    """
    Fetch health metrics for MCP server (sync wrapper for Streamlit).

    Args:
        server_id: Server UUID string
        tenant_id: Tenant UUID string
        period_hours: Time period to analyze (default 24h)

    Returns:
        dict: Aggregated health metrics with keys:
            - server_id: UUID
            - server_name: str
            - period_hours: int
            - metrics: dict with success_rate, percentiles, errors_by_type, etc.

    Example:
        >>> metrics = fetch_mcp_server_metrics(server_id, tenant_id, period_hours=48)
        >>> print(metrics["metrics"]["success_rate"])
        0.985
    """
    import asyncio

    return asyncio.run(_fetch_mcp_server_metrics_async(server_id, tenant_id, period_hours))


def render_health_metrics_dashboard(
    server_id: str, tenant_id: str, period_hours: int = 24
) -> None:
    """
    Render health metrics dashboard with charts (Story 11.2.4 AC7).

    Displays:
        - Key metrics grid (success rate, uptime, avg response time, total checks)
        - Response time percentiles chart (P50/P95/P99)
        - Success/Error rate pie chart
        - Error distribution bar chart
        - Performance trend indicator

    Args:
        server_id: Server UUID string
        tenant_id: Tenant UUID string
        period_hours: Time period to analyze (default 24h)

    Note:
        Requires streamlit, plotly installed
        Auto-refreshes every 30 seconds via st.rerun()
    """
    import streamlit as st
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    try:
        # Fetch metrics from API
        metrics_data = fetch_mcp_server_metrics(server_id, tenant_id, period_hours)
        metrics = metrics_data["metrics"]

        # Header
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("### 📊 Health Metrics Dashboard")
        with col2:
            # Period selector
            selected_period = st.selectbox(
                "Period",
                options=[1, 6, 12, 24, 48, 72, 168],
                index=3,  # Default to 24h
                format_func=lambda h: f"{h}h" if h < 24 else f"{h//24}d",
                key="metrics_period",
            )
            if selected_period != period_hours:
                st.rerun()

        # Key metrics grid
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

        with metric_col1:
            success_rate_pct = metrics["success_rate"] * 100
            st.metric(
                "Success Rate",
                f"{success_rate_pct:.1f}%",
                delta=None,
                help="Percentage of successful health checks",
            )

        with metric_col2:
            st.metric(
                "Uptime",
                f"{metrics['uptime_percentage']:.1f}%",
                delta=None,
                help="Server uptime percentage",
            )

        with metric_col3:
            st.metric(
                "Avg Response Time",
                f"{metrics['avg_response_time_ms']}ms",
                delta=None,
                help="Average response time across all checks",
            )

        with metric_col4:
            st.metric(
                "Total Checks",
                f"{metrics['total_checks']:,}",
                delta=None,
                help="Total health checks performed in period",
            )

        st.divider()

        # Charts row
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            # Response time percentiles chart
            st.markdown("**Response Time Distribution**")
            percentiles_fig = go.Figure(
                data=[
                    go.Bar(
                        x=["P50 (Median)", "P95", "P99", "Max"],
                        y=[
                            metrics["p50_response_time_ms"],
                            metrics["p95_response_time_ms"],
                            metrics["p99_response_time_ms"],
                            metrics["max_response_time_ms"],
                        ],
                        marker_color=["#2E7D32", "#FFA726", "#FF5722", "#D32F2F"],
                        text=[
                            f"{metrics['p50_response_time_ms']}ms",
                            f"{metrics['p95_response_time_ms']}ms",
                            f"{metrics['p99_response_time_ms']}ms",
                            f"{metrics['max_response_time_ms']}ms",
                        ],
                        textposition="auto",
                    )
                ]
            )
            percentiles_fig.update_layout(
                yaxis_title="Response Time (ms)",
                height=300,
                showlegend=False,
                margin=dict(l=10, r=10, t=10, b=10),
            )
            st.plotly_chart(percentiles_fig, use_container_width=True)

        with chart_col2:
            # Success/Error rate pie chart
            st.markdown("**Success vs Error Rate**")
            success_count = int(metrics["total_checks"] * metrics["success_rate"])
            error_count = metrics["total_checks"] - success_count
            pie_fig = go.Figure(
                data=[
                    go.Pie(
                        labels=["Success", "Error"],
                        values=[success_count, error_count],
                        marker_colors=["#4CAF50", "#F44336"],
                        hole=0.4,
                        textinfo="label+percent",
                    )
                ]
            )
            pie_fig.update_layout(
                height=300,
                showlegend=True,
                margin=dict(l=10, r=10, t=10, b=10),
            )
            st.plotly_chart(pie_fig, use_container_width=True)

        # Error distribution (if errors exist)
        if metrics["errors_by_type"]:
            st.markdown("**Error Distribution by Type**")
            error_types = list(metrics["errors_by_type"].keys())
            error_counts = list(metrics["errors_by_type"].values())

            errors_fig = go.Figure(
                data=[
                    go.Bar(
                        x=error_types,
                        y=error_counts,
                        marker_color="#FF5722",
                        text=error_counts,
                        textposition="auto",
                    )
                ]
            )
            errors_fig.update_layout(
                xaxis_title="Error Type",
                yaxis_title="Count",
                height=250,
                showlegend=False,
                margin=dict(l=10, r=10, t=10, b=10),
            )
            st.plotly_chart(errors_fig, use_container_width=True)

        # Performance trend
        trend = metrics["last_24h_trend"]
        trend_emoji = {
            "improving": "📈",
            "stable": "➡️",
            "degrading": "📉",
        }.get(trend, "❓")
        trend_color = {
            "improving": "green",
            "stable": "blue",
            "degrading": "red",
        }.get(trend, "gray")

        st.markdown(
            f"**Performance Trend (24h):** :{trend_color}[{trend_emoji} {trend.capitalize()}]"
        )

        # Auto-refresh every 30 seconds
        st.caption(
            f"📊 Showing metrics for last {period_hours}h | Auto-refreshes every 30s"
        )

        # Schedule rerun for auto-refresh
        import time
        time.sleep(30)
        st.rerun()

    except Exception as e:
        st.warning(f"No metrics available for this period: {str(e)}")
        st.caption(
            "Health metrics will appear after the first health check runs (every 30 seconds)"
        )
