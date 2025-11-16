"""
Agent Performance Queries Module.

Specialized module for building and executing SQL queries against agent_test_executions.
Handles JSONB extraction, percentile calculations, and complex aggregations.

Following 2025 best practices:
- SQLAlchemy 2.0+ async patterns
- JSONB extraction with func.jsonb_extract_path_text()
- Percentile calculation with func.percentile_cont()
- Efficient indexing via created_at and agent_id
"""

import logging
from datetime import date, datetime, timedelta
from typing import List, Tuple, Optional
from uuid import UUID

from sqlalchemy import and_, func, select, cast, Integer, case
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.database.models import Agent, AgentTestExecution, TenantConfig

logger = logging.getLogger(__name__)


class AgentPerformanceQueryBuilder:
    """SQL query builder for agent performance metrics."""

    @staticmethod
    async def get_agent_metrics(
        db: AsyncSession,
        agent_id: UUID,
        start_date: date,
        end_date: date,
    ) -> dict:
        """
        Calculate per-agent metrics using SQL aggregations.

        Returns dict with:
        - total_executions
        - successful_executions
        - failed_executions
        - success_rate
        - average_duration_seconds
        - p50/p95/p99_latency_seconds
        """
        from sqlalchemy import Float
        
        end_datetime = datetime.combine(end_date, datetime.max.time())
        start_datetime = datetime.combine(start_date, datetime.min.time())

        stmt = select(
            func.count(AgentTestExecution.id).label("total"),
            func.sum(
                case(
                    (AgentTestExecution.status == "success", 1),
                    else_=0,
                )
            ).label("successful"),
            func.sum(
                case(
                    (AgentTestExecution.status == "failed", 1),
                    else_=0,
                )
            ).label("failed"),
            func.avg(
                cast(
                    func.jsonb_extract_path_text(
                        cast(AgentTestExecution.execution_time, JSONB), "total_duration_ms"
                    ),
                    Float,
                )
            ).label("avg_duration_ms"),
            func.percentile_cont(0.50)
            .within_group(
                cast(
                    func.jsonb_extract_path_text(
                        cast(AgentTestExecution.execution_time, JSONB), "total_duration_ms"
                    ),
                    Float,
                )
            )
            .label("p50_ms"),
            func.percentile_cont(0.95)
            .within_group(
                cast(
                    func.jsonb_extract_path_text(
                        cast(AgentTestExecution.execution_time, JSONB), "total_duration_ms"
                    ),
                    Float,
                )
            )
            .label("p95_ms"),
            func.percentile_cont(0.99)
            .within_group(
                cast(
                    func.jsonb_extract_path_text(
                        cast(AgentTestExecution.execution_time, JSONB), "total_duration_ms"
                    ),
                    Float,
                )
            )
            .label("p99_ms"),
        ).where(
            and_(
                AgentTestExecution.agent_id == agent_id,
                AgentTestExecution.created_at >= start_datetime,
                AgentTestExecution.created_at <= end_datetime,
            )
        )

        result = await db.execute(stmt)
        row = result.first()

        return {
            "total_executions": row.total or 0,
            "successful_executions": row.successful or 0,
            "failed_executions": row.failed or 0,
            "average_duration_ms": row.avg_duration_ms or 0,
            "p50_latency_ms": row.p50_ms or 0,
            "p95_latency_ms": row.p95_ms or 0,
            "p99_latency_ms": row.p99_ms or 0,
        }

    @staticmethod
    async def get_execution_history(
        db: AsyncSession,
        agent_id: UUID,
        status_filter: Optional[str],
        start_date: Optional[date],
        end_date: Optional[date],
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[dict], int]:
        """
        Get paginated execution history with filters.

        Returns tuple of (records, total_count)
        """
        from sqlalchemy import Float
        
        end_datetime = (
            datetime.combine(end_date, datetime.max.time())
            if end_date
            else datetime.now()
        )
        start_datetime = (
            datetime.combine(start_date, datetime.min.time())
            if start_date
            else datetime.min
        )

        conditions = [AgentTestExecution.agent_id == agent_id]
        if status_filter:
            conditions.append(AgentTestExecution.status == status_filter)
        if start_date:
            conditions.append(AgentTestExecution.created_at >= start_datetime)
        if end_date:
            conditions.append(AgentTestExecution.created_at <= end_datetime)

        # Count query
        count_stmt = select(func.count(AgentTestExecution.id)).where(
            and_(*conditions)
        )
        count_result = await db.execute(count_stmt)
        total_count = count_result.scalar() or 0

        # Data query
        stmt = (
            select(
                AgentTestExecution.id,
                AgentTestExecution.created_at,
                AgentTestExecution.status,
                func.jsonb_extract_path_text(
                    cast(AgentTestExecution.execution_time, JSONB), "total_duration_ms"
                ).cast(Float),
                func.jsonb_extract_path_text(
                    cast(AgentTestExecution.token_usage, JSONB), "input_tokens"
                ).cast(Float),
                func.jsonb_extract_path_text(
                    cast(AgentTestExecution.token_usage, JSONB), "output_tokens"
                ).cast(Float),
                func.jsonb_extract_path_text(
                    cast(AgentTestExecution.token_usage, JSONB), "estimated_cost_usd"
                ).cast(float),
                func.jsonb_extract_path_text(cast(AgentTestExecution.errors, JSONB), "error_message"),
                func.jsonb_extract_path_text(cast(AgentTestExecution.errors, JSONB), "error_type"),
            )
            .where(and_(*conditions))
            .order_by(AgentTestExecution.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(stmt)
        rows = result.fetchall()

        records = [
            {
                "execution_id": row[0],
                "timestamp": row[1],
                "status": row[2],
                "duration_ms": row[3] or 0,
                "input_tokens": int(row[4] or 0),
                "output_tokens": int(row[5] or 0),
                "estimated_cost_usd": row[6] or 0.0,
                "error_message": row[7],
                "error_type": row[8],
            }
            for row in rows
        ]

        return records, total_count

    @staticmethod
    async def get_performance_trends(
        db: AsyncSession,
        agent_id: UUID,
        days: int = 7,
    ) -> List[dict]:
        """
        Get daily execution trends for last N days.

        Returns list of dicts with date, execution_count, avg_duration_ms
        """
        from sqlalchemy import Float
        
        start_date = datetime.now() - timedelta(days=days)

        stmt = select(
            func.date(AgentTestExecution.created_at).label("trend_date"),
            func.count(AgentTestExecution.id).label("execution_count"),
            func.sum(
                case(
                    (AgentTestExecution.status == "success", 1),
                    else_=0,
                )
            ).label("successful"),
            func.sum(
                case(
                    (AgentTestExecution.status == "failed", 1),
                    else_=0,
                )
            ).label("failed"),
            func.avg(
                cast(
                    func.jsonb_extract_path_text(
                        cast(AgentTestExecution.execution_time, JSONB), "total_duration_ms"
                    ),
                    Float,
                )
            ).label("avg_duration_ms"),
        ).where(
            and_(
                AgentTestExecution.agent_id == agent_id,
                AgentTestExecution.created_at >= start_date,
            )
        ).group_by(
            func.date(AgentTestExecution.created_at)
        ).order_by(
            func.date(AgentTestExecution.created_at)
        )

        result = await db.execute(stmt)
        rows = result.fetchall()

        return [
            {
                "date": row.trend_date,
                "execution_count": row.execution_count or 0,
                "successful": row.successful or 0,
                "failed": row.failed or 0,
                "average_duration_seconds": (row.avg_duration_ms or 0) / 1000,
            }
            for row in rows
        ]

    @staticmethod
    async def get_slowest_agents(
        db: AsyncSession,
        tenant_id: str,
        limit: int = 10,
    ) -> List[dict]:
        """
        Get agents sorted by P95 latency (slowest first).

        Tenant-isolated query.
        """
        from sqlalchemy import Float
        
        stmt = select(
            Agent.id,
            Agent.name,
            func.count(AgentTestExecution.id).label("execution_count"),
            func.percentile_cont(0.95)
            .within_group(
                cast(
                    func.jsonb_extract_path_text(
                        cast(AgentTestExecution.execution_time, JSONB), "total_duration_ms"
                    ),
                    Float,
                )
            )
            .label("p95_ms"),
            func.avg(
                cast(
                    func.jsonb_extract_path_text(
                        cast(AgentTestExecution.execution_time, JSONB), "total_duration_ms"
                    ),
                    Float,
                )
            ).label("avg_duration_ms"),
            func.sum(
                case(
                    (AgentTestExecution.status == "success", 1),
                    else_=0,
                )
            ).label("successful"),
        ).select_from(Agent).join(
            AgentTestExecution,
            Agent.id == AgentTestExecution.agent_id,
        ).where(
            Agent.tenant_id == tenant_id
        ).group_by(
            Agent.id, Agent.name
        ).order_by(
            func.percentile_cont(0.95)
            .within_group(
                cast(
                    func.jsonb_extract_path_text(
                        cast(AgentTestExecution.execution_time, JSONB), "total_duration_ms"
                    ),
                    Float,
                )
            )
            .desc()
        ).limit(limit)

        result = await db.execute(stmt)
        rows = result.fetchall()

        return [
            {
                "agent_id": row.id,
                "agent_name": row.name,
                "execution_count": row.execution_count or 0,
                "p95_latency_ms": row.p95_ms or 0,
                "average_duration_ms": row.avg_duration_ms or 0,
                "successful_count": row.successful or 0,
                "success_rate": (
                    (row.successful or 0) / (row.execution_count or 1) * 100
                ),
            }
            for row in rows
        ]
