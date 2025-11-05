"""
System Status Helper for Streamlit Dashboard.

This module provides system health status calculation for the dashboard page.
It aggregates connection states, metrics, and operational data to determine
overall system health: Healthy, Degraded, or Down.

Status Logic:
- Down: No database or Redis connection
- Degraded: Success rate < 80% OR queue depth > 100
- Healthy: All checks pass
"""

from typing import Literal

import streamlit as st
from loguru import logger

# Import connection testing functions
from admin.utils.db_helper import test_database_connection

SystemStatus = Literal["Healthy", "Degraded", "Down"]


def get_system_status(
    db_connected: bool = None,
    redis_connected: bool = None,
    success_rate: float = None,
    queue_depth: int = None,
) -> tuple[SystemStatus, str, str]:
    """
    Calculate overall system health status.

    Evaluates multiple health indicators to determine if system is Healthy,
    Degraded, or Down. Follows AC#1 requirements:
    - Down: No database or Redis connection
    - Degraded: Success rate < 80% OR queue depth > 100
    - Healthy: All checks pass

    Args:
        db_connected: Database connection status (None = auto-check)
        redis_connected: Redis connection status (None = auto-check)
        success_rate: 24h success rate percentage (0-100)
        queue_depth: Current enhancement queue depth

    Returns:
        tuple[SystemStatus, str, str]: (status, emoji, message)
            status: "Healthy", "Degraded", or "Down"
            emoji: "✅", "⚠️", or "❌"
            message: Human-readable status description

    Examples:
        >>> get_system_status(True, True, 95.0, 50)
        ("Healthy", "✅", "All systems operational")

        >>> get_system_status(True, True, 75.0, 50)
        ("Degraded", "⚠️", "Success rate below threshold (75.0% < 80%)")

        >>> get_system_status(False, True, 95.0, 50)
        ("Down", "❌", "Database connection failed")
    """
    # Auto-check database connection if not provided
    if db_connected is None:
        db_connected, _ = test_database_connection()

    # Auto-check Redis connection if not provided (imported later to avoid circular import)
    if redis_connected is None:
        try:
            from admin.utils.redis_helper import test_redis_connection

            redis_connected, _ = test_redis_connection()
        except Exception as e:
            logger.warning(f"Redis connection check failed during status calc: {e}")
            redis_connected = False

    # Critical failures → Down status
    if not db_connected:
        return "Down", "❌", "Database connection failed"

    if not redis_connected:
        return "Down", "❌", "Redis connection failed"

    # Performance degradation checks
    degradation_reasons = []

    if success_rate is not None and success_rate < 80.0:
        degradation_reasons.append(f"Success rate below threshold ({success_rate:.1f}% < 80%)")

    if queue_depth is not None and queue_depth > 100:
        degradation_reasons.append(f"Queue depth exceeds limit ({queue_depth} > 100)")

    if degradation_reasons:
        return "Degraded", "⚠️", "; ".join(degradation_reasons)

    # All checks passed
    return "Healthy", "✅", "All systems operational"


@st.cache_data(ttl=30)
def get_cached_system_status(
    db_connected: bool,
    redis_connected: bool,
    success_rate: float,
    queue_depth: int,
) -> tuple[SystemStatus, str, str]:
    """
    Cached version of get_system_status for dashboard efficiency.

    Cache expires after 30 seconds to ensure dashboard shows recent status.

    Args:
        db_connected: Database connection status
        redis_connected: Redis connection status
        success_rate: 24h success rate percentage
        queue_depth: Current enhancement queue depth

    Returns:
        tuple[SystemStatus, str, str]: Same as get_system_status()
    """
    return get_system_status(db_connected, redis_connected, success_rate, queue_depth)


def display_system_status(
    db_connected: bool = None,
    redis_connected: bool = None,
    success_rate: float = None,
    queue_depth: int = None,
) -> None:
    """
    Display system status indicator in Streamlit UI using st.status() widget.

    Follows AC#1 and AC#7 requirements for visual indicators with color coding.

    Args:
        db_connected: Database connection status (None = auto-check)
        redis_connected: Redis connection status (None = auto-check)
        success_rate: 24h success rate percentage
        queue_depth: Current enhancement queue depth

    Usage:
        # Auto-check connections
        display_system_status(success_rate=95.0, queue_depth=42)

        # Provide explicit connection states
        display_system_status(True, True, 95.0, 42)
    """
    status, emoji, message = get_system_status(
        db_connected, redis_connected, success_rate, queue_depth
    )

    # Map status to st.status() state parameter
    state_map = {
        "Healthy": "complete",  # Green
        "Degraded": "running",  # Yellow/Orange
        "Down": "error",  # Red
    }

    with st.status(
        f"{emoji} System Status: **{status}**",
        state=state_map[status],
        expanded=(status != "Healthy"),  # Auto-expand if issues detected
    ):
        st.write(message)

        # Show detailed health info when expanded
        if db_connected is not None:
            st.write(f"🗄️ Database: {'✅ Connected' if db_connected else '❌ Disconnected'}")

        if redis_connected is not None:
            st.write(
                f"🔴 Redis: {'✅ Connected' if redis_connected else '❌ Disconnected'}"
            )

        if success_rate is not None:
            status_icon = "✅" if success_rate >= 80 else "⚠️"
            st.write(f"📊 Success Rate: {status_icon} {success_rate:.1f}%")

        if queue_depth is not None:
            status_icon = "✅" if queue_depth <= 100 else "⚠️"
            st.write(f"📥 Queue Depth: {status_icon} {queue_depth}")
