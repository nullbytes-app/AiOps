"""
LLM Cost Queries Module.

Low-level database queries for LiteLLM spend tracking.
Handles raw SQL/SQLAlchemy operations for cost data retrieval.

CRITICAL: ALL queries MUST filter by tenant_id for security.
"""

import logging
from datetime import date, datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.litellm_models import LiteLLMSpendLog
from src.database.models import Agent, TenantConfig
from src.schemas.llm_cost import (
    AgentSpendDTO,
    DailySpendDTO,
    ModelSpendDTO,
    SpendLogDetailDTO,
    TenantSpendDTO,
    TokenBreakdownDTO,
)

logger = logging.getLogger(__name__)


class CostQueryBuilder:
    """Helper class for building cost queries."""

    def __init__(self, db: AsyncSession):
        """Initialize query builder."""
        self.db = db

    async def get_total_spend(
        self,
        start_date: date,
        end_date: date,
        tenant_id: Optional[UUID] = None,
    ) -> float:
        """Calculate total spend for date range with optional tenant filter."""
        try:
            stmt = select(func.coalesce(func.sum(LiteLLMSpendLog.spend), 0.0))
            stmt = stmt.where(
                and_(
                    func.date(LiteLLMSpendLog.startTime) >= start_date,
                    func.date(LiteLLMSpendLog.startTime) <= end_date,
                )
            )
            if tenant_id:
                stmt = stmt.where(LiteLLMSpendLog.end_user == str(tenant_id))
            result = await self.db.execute(stmt)
            return float(result.scalar())
        except Exception as e:
            logger.error(f"Error calculating total spend: {e}", exc_info=True)
            raise

    async def get_spend_by_tenant(
        self,
        start_date: date,
        end_date: date,
        limit: int = 10,
    ) -> List[TenantSpendDTO]:
        """Get top N tenants by spend."""
        try:
            stmt = (
                select(
                    LiteLLMSpendLog.end_user.label("tenant_id"),
                    func.sum(LiteLLMSpendLog.spend).label("total_spend"),
                )
                .where(
                    and_(
                        func.date(LiteLLMSpendLog.startTime) >= start_date,
                        func.date(LiteLLMSpendLog.startTime) <= end_date,
                        LiteLLMSpendLog.end_user.isnot(None),
                        LiteLLMSpendLog.end_user != '',  # Exclude empty strings
                    )
                )
                .group_by(LiteLLMSpendLog.end_user)
                .order_by(func.sum(LiteLLMSpendLog.spend).desc())
                .limit(limit)
            )

            result = await self.db.execute(stmt)
            rows = result.all()

            tenant_dtos = []
            for idx, row in enumerate(rows, start=1):
                tenant_id_str = row.tenant_id
                total_spend = float(row.total_spend)

                # Skip invalid or empty tenant IDs
                if not tenant_id_str or not isinstance(tenant_id_str, str):
                    logger.warning(f"Invalid tenant_id format: {tenant_id_str}")
                    continue

                # Query tenant name using VARCHAR tenant_id (not UUID conversion)
                tenant_stmt = select(TenantConfig.name).where(
                    TenantConfig.tenant_id == tenant_id_str
                )
                tenant_result = await self.db.execute(tenant_stmt)
                tenant_name = tenant_result.scalar() or f"Tenant {tenant_id_str[:8]}"
                tenant_dtos.append(
                    TenantSpendDTO(
                        tenant_id=tenant_id_str,  # Use VARCHAR string, not UUID
                        tenant_name=tenant_name,
                        total_spend=total_spend,
                        rank=idx,
                    )
                )
            return tenant_dtos
        except Exception as e:
            logger.error(f"Error fetching spend by tenant: {e}", exc_info=True)
            raise

    async def get_spend_by_agent(
        self,
        start_date: date,
        end_date: date,
        tenant_id: Optional[UUID] = None,
        limit: int = 10,
    ) -> List[AgentSpendDTO]:
        """Get top N agents by spend with execution statistics."""
        try:
            # Use a subquery to expand the array elements first
            subq = (
                select(
                    LiteLLMSpendLog.request_id,
                    LiteLLMSpendLog.spend,
                    func.jsonb_array_elements_text(LiteLLMSpendLog.request_tags).label("tag")
                )
                .where(
                    and_(
                        func.date(LiteLLMSpendLog.startTime) >= start_date,
                        func.date(LiteLLMSpendLog.startTime) <= end_date,
                        LiteLLMSpendLog.request_tags.isnot(None),
                    )
                )
            )

            if tenant_id:
                subq = subq.where(LiteLLMSpendLog.end_user == str(tenant_id))

            subq = subq.subquery()

            # Now group by tag and filter for agent tags
            stmt = (
                select(
                    subq.c.tag,
                    func.count(subq.c.request_id).label("execution_count"),
                    func.sum(subq.c.spend).label("total_cost"),
                )
                .where(subq.c.tag.like("agent:%"))
                .group_by(subq.c.tag)
                .order_by(func.sum(subq.c.spend).desc())
                .limit(limit)
            )

            result = await self.db.execute(stmt)
            rows = result.all()

            agent_dtos = []
            for row in rows:
                tag = row.tag
                if tag and tag.startswith("agent:"):
                    agent_name = tag.split(":", 1)[1]
                    execution_count = int(row.execution_count)
                    total_cost = float(row.total_cost)
                    avg_cost = total_cost / execution_count if execution_count > 0 else 0.0

                    agent_stmt = select(Agent.id).where(Agent.name == agent_name)
                    agent_result = await self.db.execute(agent_stmt)
                    agent_id = agent_result.scalar()

                    agent_dtos.append(
                        AgentSpendDTO(
                            agent_id=agent_id,
                            agent_name=agent_name,
                            execution_count=execution_count,
                            total_cost=total_cost,
                            avg_cost=avg_cost,
                        )
                    )
            return agent_dtos
        except Exception as e:
            logger.error(f"Error fetching spend by agent: {e}", exc_info=True)
            raise

    async def get_spend_by_model(
        self,
        start_date: date,
        end_date: date,
        tenant_id: Optional[UUID] = None,
    ) -> List[ModelSpendDTO]:
        """Get spend breakdown by model."""
        try:
            stmt = (
                select(
                    LiteLLMSpendLog.model_group.label("model_name"),
                    func.sum(LiteLLMSpendLog.spend).label("total_spend"),
                    func.sum(LiteLLMSpendLog.total_tokens).label("total_tokens"),
                    func.sum(LiteLLMSpendLog.prompt_tokens).label("prompt_tokens"),
                    func.sum(LiteLLMSpendLog.completion_tokens).label("completion_tokens"),
                )
                .where(
                    and_(
                        func.date(LiteLLMSpendLog.startTime) >= start_date,
                        func.date(LiteLLMSpendLog.startTime) <= end_date,
                    )
                )
                .group_by(LiteLLMSpendLog.model_group)
                .order_by(func.sum(LiteLLMSpendLog.spend).desc())
            )

            if tenant_id:
                stmt = stmt.where(LiteLLMSpendLog.end_user == str(tenant_id))

            result = await self.db.execute(stmt)
            rows = result.all()

            return [
                ModelSpendDTO(
                    model_name=row.model_name,
                    total_spend=float(row.total_spend),
                    total_tokens=int(row.total_tokens),
                    prompt_tokens=int(row.prompt_tokens),
                    completion_tokens=int(row.completion_tokens),
                )
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Error fetching spend by model: {e}", exc_info=True)
            raise

    async def get_token_breakdown(
        self,
        start_date: date,
        end_date: date,
        model: Optional[str] = None,
        tenant_id: Optional[UUID] = None,
    ) -> List[TokenBreakdownDTO]:
        """Get token usage breakdown (input vs output) by model."""
        try:
            stmt = (
                select(
                    LiteLLMSpendLog.model_group.label("model_name"),
                    func.sum(LiteLLMSpendLog.prompt_tokens).label("prompt_tokens"),
                    func.sum(LiteLLMSpendLog.completion_tokens).label("completion_tokens"),
                    func.sum(LiteLLMSpendLog.total_tokens).label("total_tokens"),
                )
                .where(
                    and_(
                        func.date(LiteLLMSpendLog.startTime) >= start_date,
                        func.date(LiteLLMSpendLog.startTime) <= end_date,
                    )
                )
                .group_by(LiteLLMSpendLog.model_group)
            )

            if model:
                stmt = stmt.where(LiteLLMSpendLog.model_group == model)

            if tenant_id:
                stmt = stmt.where(LiteLLMSpendLog.end_user == str(tenant_id))

            result = await self.db.execute(stmt)
            rows = result.all()

            breakdown_dtos = []
            for row in rows:
                total = int(row.total_tokens)
                prompt = int(row.prompt_tokens)
                completion = int(row.completion_tokens)
                prompt_pct = (prompt / total * 100) if total > 0 else 0.0
                completion_pct = (completion / total * 100) if total > 0 else 0.0

                breakdown_dtos.append(
                    TokenBreakdownDTO(
                        model_name=row.model_name,
                        prompt_tokens=prompt,
                        completion_tokens=completion,
                        total_tokens=total,
                        prompt_percentage=prompt_pct,
                        completion_percentage=completion_pct,
                    )
                )
            return breakdown_dtos
        except Exception as e:
            logger.error(f"Error fetching token breakdown: {e}", exc_info=True)
            raise

    async def get_daily_spend_trend(
        self,
        days: int = 30,
        tenant_id: Optional[UUID] = None,
    ) -> List[DailySpendDTO]:
        """Get daily spend time series for trend chart."""
        try:
            start_date = date.today() - timedelta(days=days)
            end_date = date.today()

            stmt = (
                select(
                    func.date(LiteLLMSpendLog.startTime).label("date"),
                    func.sum(LiteLLMSpendLog.spend).label("total_spend"),
                    func.count(LiteLLMSpendLog.request_id).label("transaction_count"),
                )
                .where(
                    and_(
                        func.date(LiteLLMSpendLog.startTime) >= start_date,
                        func.date(LiteLLMSpendLog.startTime) <= end_date,
                    )
                )
                .group_by(func.date(LiteLLMSpendLog.startTime))
                .order_by(func.date(LiteLLMSpendLog.startTime).asc())
            )

            if tenant_id:
                stmt = stmt.where(LiteLLMSpendLog.end_user == str(tenant_id))

            result = await self.db.execute(stmt)
            rows = result.all()

            daily_dtos = []
            existing_dates = {row.date: row for row in rows}

            for i in range(days):
                current_date = start_date + timedelta(days=i)
                if current_date in existing_dates:
                    row = existing_dates[current_date]
                    daily_dtos.append(
                        DailySpendDTO(
                            date=current_date,
                            total_spend=float(row.total_spend),
                            transaction_count=int(row.transaction_count),
                        )
                    )
                else:
                    daily_dtos.append(
                        DailySpendDTO(
                            date=current_date,
                            total_spend=0.0,
                            transaction_count=0,
                        )
                    )
            return daily_dtos
        except Exception as e:
            logger.error(f"Error fetching daily spend trend: {e}", exc_info=True)
            raise

    async def get_detailed_logs(
        self,
        start_date: date,
        end_date: date,
        tenant_id: Optional[UUID] = None,
        agent_id: Optional[UUID] = None,
    ) -> List[SpendLogDetailDTO]:
        """Get detailed spend logs for CSV export."""
        try:
            stmt = select(LiteLLMSpendLog).where(
                and_(
                    func.date(LiteLLMSpendLog.startTime) >= start_date,
                    func.date(LiteLLMSpendLog.startTime) <= end_date,
                )
            )

            if tenant_id:
                stmt = stmt.where(LiteLLMSpendLog.end_user == str(tenant_id))

            if agent_id:
                agent_stmt = select(Agent.name).where(Agent.id == agent_id)
                agent_result = await self.db.execute(agent_stmt)
                agent_name = agent_result.scalar()
                if agent_name:
                    stmt = stmt.where(
                        LiteLLMSpendLog.request_tags.contains([f"agent:{agent_name}"])
                    )

            result = await self.db.execute(stmt)
            logs = result.scalars().all()

            detail_dtos = []
            for log in logs:
                # Validate and convert tenant UUID
                tenant_uuid = None
                tenant_name = "Unknown"
                if log.end_user and log.end_user.strip():
                    try:
                        tenant_uuid = UUID(log.end_user)
                        tenant_stmt = select(TenantConfig.name).where(
                            TenantConfig.tenant_id == tenant_uuid
                        )
                        tenant_result = await self.db.execute(tenant_stmt)
                        tenant_name = tenant_result.scalar() or f"Tenant {log.end_user[:8]}"
                    except (ValueError, AttributeError, TypeError):
                        logger.warning(f"Invalid UUID format for end_user: {log.end_user}")
                        tenant_name = f"Invalid tenant ID"

                detail_dtos.append(
                    SpendLogDetailDTO(
                        date=log.startTime.date(),
                        tenant_id=tenant_uuid,
                        tenant_name=tenant_name,
                        agent_id=None,
                        agent_name=log.agent_name,
                        model=log.model_group,
                        prompt_tokens=log.prompt_tokens,
                        completion_tokens=log.completion_tokens,
                        total_tokens=log.total_tokens,
                        cost=log.spend,
                    )
                )
            return detail_dtos
        except Exception as e:
            logger.error(f"Error fetching detailed logs: {e}", exc_info=True)
            raise
