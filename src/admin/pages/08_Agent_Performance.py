"""
Agent Performance Metrics Dashboard (Story 8.17).

Real-time performance monitoring for all agents with metrics, trends, error analysis,
and optimization recommendations.

Uses Streamlit 2025 best practices:
- @st.cache_data(ttl=60) for efficient caching
- @st.fragment(run_every=60) for auto-refresh
- Plotly Express for interactive charts
"""

import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Optional

import plotly.express as px
import streamlit as st
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.utils.performance_dashboard_helpers import (
    create_error_distribution_chart,
    create_execution_history_dataframe,
    create_performance_metrics_cards,
    create_slowest_agents_table,
    create_trends_chart,
    fetch_agent_list,
    fetch_error_analysis,
    fetch_execution_history,
    fetch_metrics,
    fetch_slowest_agents,
    fetch_trends,
)
from src.database.session import get_async_session

logger = logging.getLogger(__name__)


def run_async(coro):
    """
    Run async coroutine safely in Streamlit environment.

    Handles event loop management to avoid conflicts with Streamlit's internal event loop.
    """
    try:
        # Always create a fresh event loop in a thread to avoid conflicts
        import concurrent.futures
        import threading

        def run_in_thread():
            # Create new loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_in_thread)
            return future.result(timeout=30)  # 30 second timeout
    except Exception as e:
        logger.error(f"Error in run_async: {e}", exc_info=True)
        raise

# Initialize session state
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = datetime.now()
if "selected_agent_id" not in st.session_state:
    st.session_state.selected_agent_id = None


@st.cache_data(ttl=60)  # Cache for 60 seconds
def fetch_all_metrics(agent_id: str, start_date: date, end_date: date):
    """
    Fetch all performance metrics (cached).

    Args:
        agent_id: UUID string for agent
        start_date: Start date for metrics
        end_date: End date for metrics

    Returns:
        Metrics DTO or None if error
    """
    try:
        async def _fetch():
            result = None
            async for db in get_async_session():
                result = await fetch_metrics(db, agent_id, start_date, end_date)
                break  # Exit after first iteration
            return result

        return run_async(_fetch())
    except Exception as e:
        logger.error(f"Error fetching metrics for {agent_id}: {e}")
        return None


@st.cache_data(ttl=60)
def fetch_all_trends(agent_id: str, days: int = 7):
    """
    Fetch performance trends (cached).

    Args:
        agent_id: UUID string for agent
        days: Number of days to retrieve

    Returns:
        List of TrendDataDTO
    """
    try:
        async def _fetch():
            result = []
            async for db in get_async_session():
                result = await fetch_trends(db, agent_id, days)
                break
            return result

        return run_async(_fetch())
    except Exception as e:
        logger.error(f"Error fetching trends for {agent_id}: {e}")
        return []


@st.cache_data(ttl=60)
def fetch_all_errors(agent_id: str, start_date: date, end_date: date):
    """
    Fetch error analysis (cached).

    Args:
        agent_id: UUID string for agent
        start_date: Start date
        end_date: End date

    Returns:
        Dict of error type -> count
    """
    try:
        async def _fetch():
            result = {}
            async for db in get_async_session():
                result = await fetch_error_analysis(db, agent_id, start_date, end_date)
                break
            return result

        return run_async(_fetch())
    except Exception as e:
        logger.error(f"Error fetching error analysis for {agent_id}: {e}")
        return {}


@st.cache_data(ttl=60)
def fetch_all_slowest(limit: int = 10):
    """
    Fetch slowest agents (cached).

    Args:
        limit: Max agents to return

    Returns:
        List of SlowAgentMetricsDTO
    """
    try:
        async def _fetch():
            result = []
            async for db in get_async_session():
                result = await fetch_slowest_agents(db, limit)
                break
            return result

        return run_async(_fetch())
    except Exception as e:
        logger.error(f"Error fetching slowest agents: {e}")
        return []


@st.cache_data(ttl=60)
def fetch_all_history(agent_id: str, status: Optional[str] = None, limit: int = 50):
    """
    Fetch execution history (cached).

    Args:
        agent_id: UUID string for agent
        status: Filter by status (success/failed) or None
        limit: Results per page

    Returns:
        Tuple of (List[ExecutionRecordDTO], total_count)
    """
    try:
        async def _fetch():
            result = ([], 0)
            async for db in get_async_session():
                result = await fetch_execution_history(db, agent_id, status, limit, 0)
                break
            return result

        return run_async(_fetch())
    except Exception as e:
        logger.error(f"Error fetching execution history for {agent_id}: {e}")
        return [], 0


@st.fragment(run_every=60)  # Auto-refresh every 60 seconds
def dashboard_fragment():
    """
    Dashboard content with auto-refresh.

    Uses @st.fragment decorator (2025 Streamlit best practice) for
    isolated updates without full page reload.
    """
    # Update last refresh timestamp
    st.session_state.last_refresh = datetime.now()

    # Title and intro
    st.title("📊 Agent Performance Dashboard")
    st.markdown("Monitor execution metrics, trends, and optimization opportunities.")

    # Filters row
    st.markdown("### 🔍 Filters")
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([2, 2, 1, 1])

    with filter_col1:
        # Agent selector
        try:
            async def get_agents():
                result = []
                async for db in get_async_session():
                    result = await fetch_agent_list(db)
                    break
                return result

            agents = run_async(get_agents())
            agent_names = [agent.get("name", "Unknown") for agent in agents]
            selected_agent = st.selectbox(
                "Select Agent",
                options=agent_names,
                help="Choose an agent to view its performance metrics",
            )
            # Get agent ID from list
            selected_idx = agent_names.index(selected_agent) if selected_agent in agent_names else 0
            st.session_state.selected_agent_id = agents[selected_idx].get("id") if agents else None
        except Exception as e:
            st.error(f"Error loading agents: {e}")
            st.session_state.selected_agent_id = None

    with filter_col2:
        # Date range selector (default: last 7 days)
        default_start = date.today() - timedelta(days=7)
        default_end = date.today()
        date_range = st.date_input(
            "Date Range",
            value=(default_start, default_end),
            max_value=date.today(),
            help="Select start and end dates for metrics",
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date = default_start
            end_date = default_end

    with filter_col3:
        # Trend days selector
        trend_days = st.selectbox(
            "Trend Period",
            options=[7, 14, 30],
            index=0,
            help="Number of days for trend analysis",
        )

    with filter_col4:
        # Manual refresh button
        if st.button("🔄 Refresh Now", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # Last updated timestamp
    st.caption(
        f"Last Updated: {st.session_state.last_refresh.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    st.divider()

    # Check if agent selected
    if not st.session_state.selected_agent_id:
        st.warning("Please select an agent to view its performance metrics")
        return

    agent_id_str = str(st.session_state.selected_agent_id)

    # Fetch data with spinner
    with st.spinner("Loading performance data..."):
        try:
            # Fetch all data
            metrics = fetch_all_metrics(agent_id_str, start_date, end_date)
            trends = fetch_all_trends(agent_id_str, trend_days)
            errors = fetch_all_errors(agent_id_str, start_date, end_date)
            history, total_count = fetch_all_history(agent_id_str, None, 50)

        except Exception as e:
            st.error(f"Error loading performance data: {e}")
            logger.error(f"Dashboard data fetch error: {e}", exc_info=True)
            return

    # Performance Metrics Cards (AC#2)
    if metrics:
        st.markdown("### 📈 Performance Metrics")
        create_performance_metrics_cards(metrics)
        st.divider()

    # Charts Section (AC#3, AC#4)
    st.markdown("### 📊 Performance Analysis")
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        if trends:
            # Performance trends chart
            trend_fig = create_trends_chart(trends)
            if trend_fig:
                st.plotly_chart(trend_fig, use_container_width=True, key="trends_chart")
            else:
                st.info("Unable to create trend chart")
        else:
            st.info("No trend data available for the selected period")

    with chart_col2:
        if errors:
            # Error distribution pie chart
            error_fig = create_error_distribution_chart(errors)
            if error_fig:
                st.plotly_chart(error_fig, use_container_width=True, key="error_chart")
            else:
                st.info("Unable to create error chart")
        else:
            st.info("No errors recorded for the selected period")

    st.divider()

    # Execution History Table (AC#5)
    st.markdown("### 📋 Execution History")
    history_col1, history_col2 = st.columns([4, 1])

    with history_col1:
        status_filter = None
        # Status filter could be added here
        st.caption(f"Showing {len(history)} of {total_count} executions")

    with history_col2:
        if st.button("View All", use_container_width=True):
            st.session_state.show_full_history = True

    if history:
        history_df = create_execution_history_dataframe(history)
        st.dataframe(
            history_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Duration (s)": st.column_config.NumberColumn("Duration (s)", width="small"),
                "Tokens": st.column_config.NumberColumn("Tokens", width="small"),
                "Cost": st.column_config.NumberColumn("Cost (USD)", width="small"),
            },
        )
    else:
        st.info("No execution records found for the selected date range")

    st.divider()


# Main layout
st.markdown(
    """
    ---
    **Quick Tips:**
    - P95 latency > 15s? Review tool integration and consider async execution
    - Success rate < 90%? Check timeout settings and error patterns
    - Use date range filters to compare performance over time
    """
)

# Render the fragment
dashboard_fragment()

st.divider()

# Slowest Agents Overview (tenant-wide, AC#8)
st.markdown("### 🐢 Slowest Agents (Tenant-wide)")
try:
    slowest = fetch_all_slowest(limit=10)
    if slowest:
        slowest_df = create_slowest_agents_table(slowest)
        st.dataframe(
            slowest_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Agent": st.column_config.TextColumn("Agent", width="medium"),
                "Executions": st.column_config.NumberColumn("Executions", width="small"),
                "P95 Latency (s)": st.column_config.NumberColumn("P95 Latency (s)", width="small"),
                "Success Rate (%)": st.column_config.NumberColumn("Success Rate (%)", width="small"),
                "Recommendation": st.column_config.TextColumn("Recommendation", width="large"),
            },
        )
    else:
        st.info("No agent data available yet")
except Exception as e:
    st.error(f"Error loading slowest agents: {e}")
    logger.error(f"Slowest agents error: {e}", exc_info=True)
