"""
Performance Dashboard Helper Functions (Story 8.17).

Utility functions for data fetching, chart creation, and table formatting
for the Agent Performance dashboard.

Following 2025 best practices with Plotly Express and Pandas.
"""

import logging
from datetime import date
from typing import Dict, List, Optional, Tuple
from uuid import UUID

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.agent_performance import (
    ExecutionRecordDTO,
    SlowAgentMetricsDTO,
    TrendDataDTO,
)
from src.services.agent_performance_service import AgentPerformanceService

logger = logging.getLogger(__name__)


# ============================================================================
# Data Fetching Functions (Async)
# ============================================================================


async def fetch_agent_list(db: AsyncSession) -> List[Dict]:
    """
    Fetch list of all agents for tenant.

    Args:
        db: AsyncSession for database queries

    Returns:
        List of dicts with id and name
    """
    try:
        from sqlalchemy import select

        from src.database.models import Agent

        # TODO: Filter by current tenant from authentication
        stmt = select(Agent).order_by(Agent.name)
        result = await db.execute(stmt)
        agents = result.scalars().all()

        return [{"id": str(agent.id), "name": agent.name} for agent in agents]
    except Exception as e:
        logger.error(f"Error fetching agent list: {e}")
        return []


async def fetch_metrics(
    db: AsyncSession, agent_id: str, start_date: date, end_date: date
):
    """
    Fetch performance metrics for an agent.

    Args:
        db: AsyncSession for database queries
        agent_id: UUID string
        start_date: Start date
        end_date: End date

    Returns:
        AgentMetricsDTO or None
    """
    try:
        from uuid import UUID

        service = AgentPerformanceService(db)
        metrics = await service.get_agent_metrics(
            UUID(agent_id), "Agent", start_date, end_date
        )
        return metrics
    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        return None


async def fetch_trends(
    db: AsyncSession, agent_id: str, days: int = 7
) -> List[TrendDataDTO]:
    """
    Fetch performance trends for an agent.

    Args:
        db: AsyncSession for database queries
        agent_id: UUID string
        days: Number of days

    Returns:
        List of TrendDataDTO
    """
    try:
        from uuid import UUID

        service = AgentPerformanceService(db)
        trends = await service.get_performance_trends(UUID(agent_id), days)
        return trends
    except Exception as e:
        logger.error(f"Error fetching trends: {e}")
        return []


async def fetch_error_analysis(
    db: AsyncSession, agent_id: str, start_date: date, end_date: date
) -> Dict[str, int]:
    """
    Fetch error analysis for an agent.

    Args:
        db: AsyncSession for database queries
        agent_id: UUID string
        start_date: Start date
        end_date: End date

    Returns:
        Dict of error type -> count
    """
    try:
        from uuid import UUID

        service = AgentPerformanceService(db)
        errors = await service.get_error_analysis(UUID(agent_id), start_date, end_date)
        return errors
    except Exception as e:
        logger.error(f"Error fetching error analysis: {e}")
        return {}


async def fetch_execution_history(
    db: AsyncSession,
    agent_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[ExecutionRecordDTO], int]:
    """
    Fetch execution history for an agent.

    Args:
        db: AsyncSession for database queries
        agent_id: UUID string
        status: Optional filter (success/failed)
        limit: Results per page
        offset: Pagination offset

    Returns:
        Tuple of (List[ExecutionRecordDTO], total_count)
    """
    try:
        from uuid import UUID

        from src.schemas.agent_performance import ExecutionFiltersDTO

        service = AgentPerformanceService(db)
        filters = ExecutionFiltersDTO(status=status)
        records, total = await service.get_execution_history(
            UUID(agent_id), filters, limit, offset
        )
        return records, total
    except Exception as e:
        logger.error(f"Error fetching execution history: {e}")
        return [], 0


async def fetch_slowest_agents(
    db: AsyncSession, limit: int = 10
) -> List[SlowAgentMetricsDTO]:
    """
    Fetch slowest agents for tenant.

    Args:
        db: AsyncSession for database queries
        limit: Max agents to return

    Returns:
        List of SlowAgentMetricsDTO
    """
    try:
        import os
        from sqlalchemy import select
        from src.database.models import Agent

        # Get tenant_id from currently selected agent or fall back to environment
        tenant_id = None
        
        # Try to get tenant from selected agent
        if "selected_agent_id" in st.session_state and st.session_state.selected_agent_id:
            try:
                from uuid import UUID
                agent_id = UUID(str(st.session_state.selected_agent_id))
                stmt = select(Agent.tenant_id).where(Agent.id == agent_id)
                result = await db.execute(stmt)
                tenant_id = result.scalar_one_or_none()
            except Exception as e:
                logger.warning(f"Could not get tenant_id from selected agent: {e}")
        
        # Fall back to session state or environment
        if not tenant_id:
            tenant_id = st.session_state.get("tenant_id") or \
                        os.getenv("AI_AGENTS_DEFAULT_TENANT_ID", os.getenv("DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000001"))

        service = AgentPerformanceService(db)
        slowest = await service.get_slowest_agents(tenant_id, limit)
        return slowest
    except Exception as e:
        logger.error(f"Error fetching slowest agents: {e}")
        return []


# ============================================================================
# Chart Creation Functions
# ============================================================================


def create_trends_chart(trends: List[TrendDataDTO]):
    """
    Create performance trends line chart.

    Args:
        trends: List of TrendDataDTO

    Returns:
        Plotly Figure
    """
    try:
        df = pd.DataFrame(
            [
                {
                    "date": trend.trend_date,
                    "execution_count": trend.execution_count,
                    "success_rate": trend.success_rate,
                    "avg_duration_seconds": trend.average_duration_seconds,
                }
                for trend in trends
            ]
        )

        # Create secondary y-axis chart (execution count + success rate)
        fig = px.line(
            df,
            x="date",
            y="avg_duration_seconds",
            title="Performance Trends",
            labels={
                "date": "Date",
                "avg_duration_seconds": "Avg Duration (seconds)",
            },
            markers=True,
            color_discrete_sequence=["#1f77b4"],
        )

        fig.update_xaxes(title="Date")
        fig.update_yaxes(title="Avg Duration (seconds)")
        fig.update_layout(hovermode="x unified", height=400)

        return fig
    except Exception as e:
        logger.error(f"Error creating trends chart: {e}")
        return None


def create_error_distribution_chart(errors: Dict[str, int]):
    """
    Create error distribution pie chart.

    Args:
        errors: Dict of error type -> count

    Returns:
        Plotly Figure
    """
    try:
        # Filter out zero counts
        non_zero_errors = {k: v for k, v in errors.items() if v > 0}

        if not non_zero_errors:
            return None

        df = pd.DataFrame(
            [
                {"error_type": k, "count": v}
                for k, v in non_zero_errors.items()
            ]
        )

        fig = px.pie(
            df,
            values="count",
            names="error_type",
            title="Error Distribution",
            color_discrete_sequence=px.colors.sequential.RdBu,
        )

        fig.update_layout(height=400)

        return fig
    except Exception as e:
        logger.error(f"Error creating error distribution chart: {e}")
        return None


# ============================================================================
# Table Creation Functions
# ============================================================================


def create_performance_metrics_cards(metrics):
    """
    Render performance metrics as cards.

    Args:
        metrics: AgentMetricsDTO with metrics data
    """
    # Row 1: Success Rate, Avg Duration, P95 Latency, Execution Count
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Success Rate",
            f"{metrics.success_rate:.1f}%",
            delta=None,
            help="Percentage of successful executions",
        )

    with col2:
        st.metric(
            "Avg Duration",
            f"{metrics.average_duration_seconds:.2f}s",
            delta=None,
            help="Average execution duration",
        )

    with col3:
        st.metric(
            "P95 Latency",
            f"{metrics.p95_latency_seconds:.2f}s",
            delta=None,
            help="95th percentile latency",
        )

    with col4:
        st.metric(
            "Total Executions",
            f"{metrics.total_executions}",
            delta=None,
            help="Total number of executions",
        )

    # Row 2: P50, P99, Failed Count
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "P50 Latency",
            f"{metrics.p50_latency_seconds:.2f}s",
            delta=None,
            help="50th percentile (median) latency",
        )

    with col2:
        st.metric(
            "P99 Latency",
            f"{metrics.p99_latency_seconds:.2f}s",
            delta=None,
            help="99th percentile latency",
        )

    with col3:
        st.metric(
            "Failed Executions",
            f"{metrics.failed_executions}",
            delta=None,
            help="Number of failed executions",
        )

    with col4:
        st.metric(
            "Success Count",
            f"{metrics.successful_executions}",
            delta=None,
            help="Number of successful executions",
        )


def create_execution_history_dataframe(
    records: List[ExecutionRecordDTO],
) -> pd.DataFrame:
    """
    Convert execution records to DataFrame for display.

    Args:
        records: List of ExecutionRecordDTO

    Returns:
        Formatted pandas DataFrame
    """
    df = pd.DataFrame(
        [
            {
                "Timestamp": record.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "Status": record.status.upper(),
                "Duration (s)": record.duration_seconds,
                "Tokens": record.total_tokens,
                "Cost (USD)": f"${record.estimated_cost_usd:.4f}",
                "Error": record.error_message or "",
            }
            for record in records
        ]
    )

    return df


def create_slowest_agents_table(
    agents: List[SlowAgentMetricsDTO],
) -> pd.DataFrame:
    """
    Convert slowest agents to DataFrame for display.

    Args:
        agents: List of SlowAgentMetricsDTO

    Returns:
        Formatted pandas DataFrame
    """
    df = pd.DataFrame(
        [
            {
                "Agent": agent.agent_name,
                "Executions": agent.execution_count,
                "P95 Latency (s)": f"{agent.p95_latency_seconds:.2f}",
                "Avg Duration (s)": f"{agent.average_duration_seconds:.2f}",
                "Success Rate (%)": f"{agent.success_rate:.1f}%",
                "Recommendation": agent.optimization_recommendation,
            }
            for agent in agents
        ]
    )

    return df
