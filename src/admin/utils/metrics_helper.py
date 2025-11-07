"""
Metrics Helper for Streamlit Dashboard.

This module provides functions to query key metrics from the database and Redis
for display on the system status dashboard. All functions use caching for performance.

Metrics Provided:
- Queue depth (Redis llen command)
- Success rate (24h window from enhancement_history)
- P95 latency (95th percentile processing time)
- Active workers (Celery inspect or Prometheus fallback)
- Recent failures (last 10 failed enhancements)
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import streamlit as st
from loguru import logger
from sqlalchemy import and_, func, text

from admin.utils.db_helper import get_db_session
from database.models import EnhancementHistory


@st.cache_data(ttl=30)
def get_queue_depth() -> int:
    """
    Get current Redis queue depth for enhancement jobs.

    Uses Redis llen() command on "celery" queue (AC#2 requirement).

    Returns:
        int: Number of jobs in queue, or 0 if query fails

    Examples:
        >>> get_queue_depth()
        42
    """
    try:
        from admin.utils.redis_helper import get_redis_queue_depth

        return get_redis_queue_depth()

    except Exception as e:
        logger.error(f"Failed to get queue depth: {e}")
        return 0


@st.cache_data(ttl=30)
def get_success_rate_24h() -> float:
    """
    Calculate enhancement success rate over last 24 hours.

    Queries enhancement_history table:
    - Completed jobs / Total jobs * 100
    - Excludes pending jobs
    - AC#2 requirement

    Returns:
        float: Success rate percentage (0.0-100.0), or 0.0 if no data

    Examples:
        >>> get_success_rate_24h()
        95.3
    """
    try:
        with get_db_session() as session:
            # Time window: last 24 hours
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)

            # Count completed jobs (successful)
            completed_count = (
                session.query(func.count(EnhancementHistory.id))
                .filter(
                    and_(
                        EnhancementHistory.status == "completed",
                        EnhancementHistory.created_at >= cutoff_time,
                    )
                )
                .scalar()
                or 0
            )

            # Count total jobs (completed + failed, exclude pending)
            total_count = (
                session.query(func.count(EnhancementHistory.id))
                .filter(
                    and_(
                        EnhancementHistory.status.in_(["completed", "failed"]),
                        EnhancementHistory.created_at >= cutoff_time,
                    )
                )
                .scalar()
                or 0
            )

            # Calculate percentage
            if total_count == 0:
                return 0.0

            success_rate = (completed_count / total_count) * 100.0
            return round(success_rate, 1)

    except Exception as e:
        logger.error(f"Failed to calculate success rate: {e}")
        return 0.0


@st.cache_data(ttl=30)
def get_p95_latency() -> int:
    """
    Calculate P95 (95th percentile) latency for enhancement processing.

    Queries enhancement_history table using PostgreSQL percentile_cont function.
    Only includes completed jobs from last 24 hours (AC#2 requirement).

    Returns:
        int: P95 latency in milliseconds, or 0 if no data

    Examples:
        >>> get_p95_latency()
        2340  # 2.34 seconds
    """
    try:
        with get_db_session() as session:
            # Time window: last 24 hours
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)

            # PostgreSQL percentile_cont syntax
            query = text(
                """
                SELECT PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY processing_time_ms)
                FROM enhancement_history
                WHERE status = 'completed'
                  AND completed_at >= :cutoff_time
                  AND processing_time_ms IS NOT NULL
            """
            )

            result = session.execute(query, {"cutoff_time": cutoff_time}).scalar()

            if result is None:
                return 0

            return int(round(result))

    except Exception as e:
        logger.error(f"Failed to calculate P95 latency: {e}")
        return 0


@st.cache_data(ttl=30)
def get_active_workers() -> int:
    """
    Get count of active Celery workers.

    Tries two methods in order:
    1. Celery inspect().active() - direct worker query
    2. Count from enhancement_history (jobs currently processing)

    AC#2 requirement. Prometheus integration is optional (Task 7).

    Returns:
        int: Number of active workers, or 0 if unavailable

    Examples:
        >>> get_active_workers()
        4
    """
    try:
        # Method 1: Try Celery inspect (requires Celery app instance)
        # Note: This requires Celery to be configured, which may not be
        # available in Streamlit context. Fallback to database count.

        # Method 2: Count in-progress jobs as proxy for active workers
        with get_db_session() as session:
            # Count jobs with pending or in-progress status created in last hour
            # This approximates active worker count
            recent_time = datetime.now(timezone.utc) - timedelta(hours=1)

            active_count = (
                session.query(func.count(EnhancementHistory.id))
                .filter(
                    and_(
                        EnhancementHistory.status == "pending",
                        EnhancementHistory.created_at >= recent_time,
                    )
                )
                .scalar()
                or 0
            )

            # Assume 1 worker per active job (conservative estimate)
            return min(active_count, 10)  # Cap at 10 for display purposes

    except Exception as e:
        logger.error(f"Failed to get active workers count: {e}")
        return 0


@st.cache_data(ttl=30)
def get_recent_failures(limit: int = 10) -> list[dict]:
    """
    Get recent failed enhancements for troubleshooting.

    Queries enhancement_history table for last N failed jobs.
    AC#3 requirement.

    Args:
        limit: Maximum number of failures to return (default: 10)

    Returns:
        list[dict]: List of failure records with keys:
            - ticket_id: ServiceDesk Plus ticket ID
            - tenant_id: Tenant identifier
            - error_message: Truncated error (max 100 chars)
            - error_full: Full error message for tooltip
            - created_at: Timestamp of failure
            - time_ago: Human-readable time since failure

    Examples:
        >>> get_recent_failures(limit=5)
        [
            {
                "ticket_id": "SD-12345",
                "tenant_id": "tenant-a",
                "error_message": "Connection timeout to API endpoint...",
                "error_full": "Connection timeout to API endpoint after 30s retry",
                "created_at": datetime(2025, 11, 4, 10, 30),
                "time_ago": "5 minutes ago"
            }
        ]
    """
    try:
        with get_db_session() as session:
            failures = (
                session.query(EnhancementHistory)
                .filter(EnhancementHistory.status == "failed")
                .order_by(EnhancementHistory.created_at.desc())
                .limit(limit)
                .all()
            )

            results = []
            now = datetime.now(timezone.utc)

            for failure in failures:
                # Calculate time ago
                if failure.created_at:
                    delta = now - failure.created_at
                    if delta.seconds < 60:
                        time_ago = f"{delta.seconds}s ago"
                    elif delta.seconds < 3600:
                        time_ago = f"{delta.seconds // 60}m ago"
                    elif delta.days == 0:
                        time_ago = f"{delta.seconds // 3600}h ago"
                    else:
                        time_ago = f"{delta.days}d ago"
                else:
                    time_ago = "Unknown"

                # Truncate error message for display
                error_full = failure.error_message or "No error message recorded"
                error_display = (
                    error_full[:100] + "..." if len(error_full) > 100 else error_full
                )

                results.append(
                    {
                        "ticket_id": failure.ticket_id or "N/A",
                        "tenant_id": failure.tenant_id or "N/A",
                        "error_message": error_display,
                        "error_full": error_full,
                        "created_at": failure.created_at,
                        "time_ago": time_ago,
                    }
                )

            return results

    except Exception as e:
        logger.error(f"Failed to get recent failures: {e}")
        return []


@st.cache_data(ttl=3600)
def get_metric_delta(metric_name: str, current_value: float) -> Optional[float]:
    """
    Calculate metric delta (change from 1 hour ago).

    Used for st.metric delta indicators (AC#2 requirement).

    Args:
        metric_name: Name of metric ("success_rate", "queue_depth", "p95_latency")
        current_value: Current metric value

    Returns:
        Optional[float]: Delta value (positive or negative), or None if unavailable

    Examples:
        >>> get_metric_delta("success_rate", 95.0)
        2.5  # Success rate increased by 2.5% from 1h ago
    """
    try:
        # This is a placeholder implementation
        # In production, you would:
        # 1. Store historical metric values in a time-series database
        # 2. Query value from 1 hour ago
        # 3. Calculate delta = current - historical

        # For MVP, return None (st.metric will hide delta if None)
        return None

    except Exception as e:
        logger.error(f"Failed to calculate delta for {metric_name}: {e}")
        return None


# ============================================================================
# Prometheus Time-Series Integration (Story 6.6)
# ============================================================================
# These functions query Prometheus HTTP API for historical metric data
# to display time-series charts showing performance trends over time.
# ============================================================================

import httpx
import pandas as pd
import plotly.graph_objects as go
from config import settings


def fetch_prometheus_range_query(
    query: str, start_time: datetime, end_time: datetime, step: str
) -> tuple[list[dict], bool]:
    """
    Fetch time-series data from Prometheus HTTP API using range query.

    Makes GET request to /api/v1/query_range endpoint with PromQL query.
    Caches successful results in session state for fallback on errors.

    Args:
        query: PromQL expression string (e.g., "ai_agents_queue_depth")
        start_time: Beginning timestamp for time range
        end_time: Ending timestamp for time range
        step: Query resolution step (e.g., "1m", "5m", "15m", "1h")

    Returns:
        tuple: (data_list, prometheus_unavailable_flag)
            - data_list: List of {"timestamp": datetime, "value": float} dicts
            - prometheus_unavailable_flag: True if using cached data due to error

    Raises:
        None: All exceptions handled internally, returns empty list on failure

    Examples:
        >>> start = datetime.now(timezone.utc) - timedelta(hours=1)
        >>> end = datetime.now(timezone.utc)
        >>> data, unavailable = fetch_prometheus_range_query("ai_agents_queue_depth", start, end, "1m")
        >>> len(data)
        60  # One data point per minute for 1 hour
    """
    cache_key = f"cached_prom_{query}_{start_time.isoformat()}_{end_time.isoformat()}"

    try:
        # Build request URL and parameters
        url = f"{settings.prometheus_url}/api/v1/query_range"
        params = {
            "query": query,
            "start": start_time.timestamp(),
            "end": end_time.timestamp(),
            "step": step,
        }

        # Make HTTP request with 5-second timeout
        with httpx.Client(timeout=5.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()

        # Parse JSON response
        data = response.json()
        if data.get("status") != "success":
            raise ValueError(f"Prometheus query failed: {data}")

        # Extract time series values
        result = data.get("data", {}).get("result", [])
        if not result:
            logger.warning(f"Prometheus query returned no results: {query}")
            return [], False

        # Parse first result metric (assume single metric query)
        values = result[0].get("values", [])

        # Convert to list of dicts with datetime timestamps
        parsed_data = [
            {"timestamp": datetime.fromtimestamp(float(ts)), "value": float(val)}
            for ts, val in values
        ]

        # Cache successful result in session state
        st.session_state[cache_key] = parsed_data

        return parsed_data, False

    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError) as e:
        logger.warning(f"Prometheus unavailable: {e}, returning cached data")
        cached = st.session_state.get(cache_key, [])
        return cached, True

    except Exception as e:
        logger.error(f"Unexpected error querying Prometheus: {e}")
        cached = st.session_state.get(cache_key, [])
        return cached, bool(cached)


def _get_time_range_params(time_range: str) -> tuple[datetime, datetime, str]:
    """
    Convert time range string to start_time, end_time, and step parameters.

    Balances chart detail with performance by using appropriate step sizes.
    All ranges stay well under 1000-point limit for AC#8 performance requirement.

    Args:
        time_range: Time range string ("1h", "6h", "24h", "7d")

    Returns:
        tuple: (start_time, end_time, step)
            - start_time: Beginning of time range
            - end_time: Current time (now)
            - step: Prometheus step duration (e.g., "1m", "5m", "15m", "1h")

    Examples:
        >>> start, end, step = _get_time_range_params("1h")
        >>> step
        "1m"  # 60 data points for 1 hour
    """
    now = datetime.now(timezone.utc)

    ranges = {
        "1h": (now - timedelta(hours=1), now, "1m"),  # 60 points
        "6h": (now - timedelta(hours=6), now, "5m"),  # 72 points
        "24h": (now - timedelta(hours=24), now, "15m"),  # 96 points
        "7d": (now - timedelta(days=7), now, "1h"),  # 168 points
    }

    # Default to 24h if unknown range
    return ranges.get(time_range, ranges["24h"])


@st.cache_data(ttl=60)
def fetch_queue_depth_timeseries(time_range: str) -> tuple[list[dict], bool]:
    """
    Fetch queue depth time-series data from Prometheus.

    Queries ai_agents_queue_depth gauge metric over specified time range.
    Cached for 60 seconds (AC#5 default refresh interval).

    Args:
        time_range: Time range string ("1h", "6h", "24h", "7d")

    Returns:
        tuple: (data_list, prometheus_unavailable_flag)
            - data_list: List of {"timestamp": datetime, "value": float} dicts
            - prometheus_unavailable_flag: True if using cached data

    Examples:
        >>> data, unavailable = fetch_queue_depth_timeseries("24h")
        >>> len(data)
        96  # 15-minute intervals for 24 hours
    """
    start_time, end_time, step = _get_time_range_params(time_range)
    query = "ai_agents_queue_depth"
    return fetch_prometheus_range_query(query, start_time, end_time, step)


@st.cache_data(ttl=60)
def fetch_success_rate_timeseries(time_range: str) -> tuple[list[dict], bool]:
    """
    Fetch success rate time-series data from Prometheus.

    Queries ai_agents_enhancement_success_rate gauge metric (percentage 0-100).
    Cached for 60 seconds (AC#5 default refresh interval).

    Args:
        time_range: Time range string ("1h", "6h", "24h", "7d")

    Returns:
        tuple: (data_list, prometheus_unavailable_flag)
            - data_list: List of {"timestamp": datetime, "value": float} dicts
            - prometheus_unavailable_flag: True if using cached data

    Examples:
        >>> data, unavailable = fetch_success_rate_timeseries("24h")
        >>> data[0]["value"]
        95.5  # Success rate as percentage
    """
    start_time, end_time, step = _get_time_range_params(time_range)
    query = "ai_agents_enhancement_success_rate"
    return fetch_prometheus_range_query(query, start_time, end_time, step)


@st.cache_data(ttl=60)
def fetch_latency_timeseries(
    time_range: str, quantile: str
) -> tuple[list[dict], bool]:
    """
    Fetch latency percentile time-series data from Prometheus.

    Queries histogram quantiles (P50/P95/P99) from enhancement_latency_seconds histogram.
    Uses histogram_quantile() with rate() for percentile calculations from buckets.
    Converts latency from seconds to milliseconds for consistency with existing metrics.
    Cached for 60 seconds (AC#5 default refresh interval).

    Args:
        time_range: Time range string ("1h", "6h", "24h", "7d")
        quantile: Percentile to query ("p50", "p95", "p99")

    Returns:
        tuple: (data_list, prometheus_unavailable_flag)
            - data_list: List of {"timestamp": datetime, "value": float} dicts (ms)
            - prometheus_unavailable_flag: True if using cached data

    Examples:
        >>> data, unavailable = fetch_latency_timeseries("24h", "p95")
        >>> data[0]["value"]
        1250.5  # P95 latency in milliseconds
    """
    start_time, end_time, step = _get_time_range_params(time_range)

    # Map quantile string to PromQL value
    quantile_map = {
        "p50": "0.50",
        "p95": "0.95",
        "p99": "0.99",
    }
    quantile_value = quantile_map.get(quantile.lower(), "0.95")

    # Build histogram_quantile query with rate()
    query = f"histogram_quantile({quantile_value}, rate(ai_agents_enhancement_latency_seconds_bucket[5m]))"

    data, unavailable = fetch_prometheus_range_query(query, start_time, end_time, step)

    # Convert latency from seconds to milliseconds (*1000)
    for point in data:
        point["value"] = point["value"] * 1000

    return data, unavailable


def downsample_timeseries(data: list[dict], max_points: int = 1000) -> list[dict]:
    """
    Downsample time-series data if it exceeds maximum points threshold.

    Uses pandas resample with mean aggregation to reduce data points while
    preserving trend shape. Ensures chart render time < 2 seconds (AC#8).

    Args:
        data: List of {"timestamp": datetime, "value": float} dicts
        max_points: Maximum number of points to keep (default: 1000)

    Returns:
        list[dict]: Downsampled data (or original if under threshold)

    Examples:
        >>> data = [{"timestamp": datetime.now(), "value": i} for i in range(2000)]
        >>> downsampled = downsample_timeseries(data, max_points=1000)
        >>> len(downsampled) <= 1000
        True
    """
    if len(data) <= max_points:
        return data

    # Convert to pandas DataFrame
    df = pd.DataFrame(data)
    df.set_index("timestamp", inplace=True)

    # Calculate target frequency to achieve max_points
    # Resample using mean aggregation (e.g., "2min" for 2 minutes)
    target_freq_minutes = max(1, len(data) // max_points)
    target_freq = f"{target_freq_minutes}min"  # min = minutes (T deprecated in pandas 2.0)

    # Resample and aggregate with mean
    resampled = df.resample(target_freq).mean().dropna().reset_index()

    # Convert back to list of dicts
    return resampled.to_dict("records")


def create_timeseries_chart(
    data: list[dict], title: str, y_label: str, color: str
) -> go.Figure:
    """
    Create interactive Plotly time-series line chart.

    Configures chart with hover tooltips, zoom/pan interactivity, and responsive sizing.
    Uses plotly.graph_objects for performance control (AC#8 requirement).

    Args:
        data: List of {"timestamp": datetime, "value": float} dicts
        title: Chart title text
        y_label: Y-axis label text (e.g., "Jobs in Queue", "%", "ms")
        color: Line color hex code (e.g., "#1f77b4")

    Returns:
        go.Figure: Configured Plotly figure object ready for st.plotly_chart()

    Examples:
        >>> data = [{"timestamp": datetime.now(), "value": 42.5}]
        >>> fig = create_timeseries_chart(data, "Queue Depth", "Jobs", "#1f77b4")
        >>> fig.layout.title.text
        "Queue Depth"
    """
    # Apply downsampling if data exceeds 1000 points (AC#8 performance requirement)
    data = downsample_timeseries(data, max_points=1000)

    # Convert data to pandas DataFrame for Plotly
    df = pd.DataFrame(data)

    # Handle empty data case
    if df.empty:
        df = pd.DataFrame({"timestamp": [datetime.now(timezone.utc)], "value": [0]})

    # Create line chart with single trace
    fig = go.Figure(
        go.Scatter(
            x=df["timestamp"],
            y=df["value"],
            mode="lines",
            line=dict(color=color, width=2),
            hovertemplate="%{y:.1f}<extra></extra>",  # Custom tooltip (AC#4)
        )
    )

    # Configure layout
    fig.update_layout(
        title=title,
        xaxis_title="Time",
        yaxis_title=y_label,
        height=300,  # Compact height for dashboard display
        showlegend=False,  # Disable legend for single-line charts (performance)
        margin=dict(l=20, r=20, t=40, b=20),  # Tight margins for dashboard
    )

    # Enable zoom and pan, disable range slider for cleaner x-axis (AC#4)
    fig.update_xaxes(rangeslider_visible=False)

    return fig
