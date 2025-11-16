"""
Agent Performance API Endpoints.

FastAPI router for agent performance metrics REST API.
Provides endpoints for dashboard data retrieval with tenant isolation.

Following 2025 best practices:
- Async/await patterns with FastAPI
- Tenant isolation via get_tenant_id() dependency
- Type hints for all endpoints
- Proper HTTP status codes and error handling
"""

import logging
from datetime import date, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_tenant_id
from src.database.session import get_async_session
from src.schemas.agent_performance import (
    AgentMetricsDTO,
    ExecutionRecordDTO,
    TrendDataDTO,
    ErrorAnalysisDTO,
    SlowAgentMetricsDTO,
    ExecutionFiltersDTO,
)
from src.services.agent_performance_service import AgentPerformanceService
from src.database.models import Agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agent-performance"])


@router.get("/{agent_id}/metrics", response_model=dict)
async def get_agent_metrics(
    agent_id: UUID,
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """
    Get per-agent performance metrics.

    Returns: execution count, success rate, latency percentiles.
    Requires tenant isolation.
    """
    try:
        # Verify agent belongs to tenant
        from sqlalchemy import select

        agent_stmt = select(Agent).where(
            (Agent.id == agent_id) & (Agent.tenant_id == tenant_id)
        )
        result = await db.execute(agent_stmt)
        agent = result.scalar()

        if not agent:
            raise HTTPException(status_code=403, detail="Agent not found or access denied")

        # Default to last 7 days
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=7)

        service = AgentPerformanceService(db)
        metrics = await service.get_agent_metrics(
            agent_id, agent.name, start_date, end_date
        )

        return {
            "metrics": metrics.model_dump(),
            "query_executed_at": metrics.model_dump().get("query_executed_at"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metrics for agent {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{agent_id}/history", response_model=dict)
async def get_execution_history(
    agent_id: UUID,
    status: Optional[str] = Query(None, description="success or failed"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(50, description="Results per page", ge=1, le=500),
    offset: int = Query(0, description="Pagination offset", ge=0),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """
    Get paginated execution history with filtering.

    Supports status, date range, and pagination filters.
    """
    try:
        # Verify agent belongs to tenant
        from sqlalchemy import select

        agent_stmt = select(Agent).where(
            (Agent.id == agent_id) & (Agent.tenant_id == tenant_id)
        )
        result = await db.execute(agent_stmt)
        agent = result.scalar()

        if not agent:
            raise HTTPException(status_code=403, detail="Agent not found or access denied")

        # Validate status filter
        if status and status not in ["success", "failed"]:
            raise HTTPException(status_code=400, detail="Invalid status filter")

        service = AgentPerformanceService(db)
        filters = ExecutionFiltersDTO(
            status=status, start_date=start_date, end_date=end_date
        )
        records, total_count = await service.get_execution_history(
            agent_id, filters, limit, offset
        )

        return {
            "records": [r.model_dump() for r in records],
            "pagination": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total_count,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting history for agent {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{agent_id}/trends", response_model=dict)
async def get_performance_trends(
    agent_id: UUID,
    days: int = Query(7, description="Number of days", ge=1, le=90),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """
    Get performance trends for charting (execution count and duration over time).

    Default: last 7 days.
    """
    try:
        # Verify agent belongs to tenant
        from sqlalchemy import select

        agent_stmt = select(Agent).where(
            (Agent.id == agent_id) & (Agent.tenant_id == tenant_id)
        )
        result = await db.execute(agent_stmt)
        agent = result.scalar()

        if not agent:
            raise HTTPException(status_code=403, detail="Agent not found or access denied")

        service = AgentPerformanceService(db)
        trends = await service.get_performance_trends(agent_id, days)

        return {
            "trends": [t.model_dump() for t in trends],
            "days_requested": days,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trends for agent {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{agent_id}/error-analysis", response_model=dict)
async def get_error_analysis(
    agent_id: UUID,
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """
    Get error type breakdown for pie chart.

    Categorizes errors by type: timeout, rate_limit, validation_error, tool_failure, other.
    """
    try:
        # Verify agent belongs to tenant
        from sqlalchemy import select

        agent_stmt = select(Agent).where(
            (Agent.id == agent_id) & (Agent.tenant_id == tenant_id)
        )
        result = await db.execute(agent_stmt)
        agent = result.scalar()

        if not agent:
            raise HTTPException(status_code=403, detail="Agent not found or access denied")

        # Default to last 7 days
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=7)

        service = AgentPerformanceService(db)
        error_counts = await service.get_error_analysis(agent_id, start_date, end_date)

        # Convert to list format for charting
        error_breakdown = [
            {"error_type": k, "count": v} for k, v in error_counts.items()
        ]

        return {
            "error_breakdown": error_breakdown,
            "total_errors": sum(error_counts.values()),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting error analysis for agent {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/slowest", response_model=dict)
async def get_slowest_agents(
    limit: int = Query(10, description="Max agents to return", ge=1, le=100),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """
    Get slowest agents sorted by P95 latency.

    Useful for identifying optimization candidates.
    Tenant-isolated.
    """
    try:
        service = AgentPerformanceService(db)
        slowest = await service.get_slowest_agents(tenant_id, limit)

        return {
            "slowest_agents": [a.model_dump() for a in slowest],
            "count": len(slowest),
        }
    except Exception as e:
        logger.error(f"Error getting slowest agents for tenant {tenant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
