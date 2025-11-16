"""
LLM Cost Aggregations Module.

High-level cost aggregation and formatting logic.
Combines raw queries into composite results (summaries, utilization reports).
"""

import logging
from datetime import date, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import TenantConfig
from src.schemas.llm_cost import (
    BudgetUtilizationDTO,
    CostSummaryDTO,
)
from src.services.llm_cost_queries import CostQueryBuilder

logger = logging.getLogger(__name__)


class CostAggregator:
    """Helper class for aggregating and formatting cost data."""

    def __init__(self, db: AsyncSession):
        """Initialize aggregator."""
        self.db = db
        self.query_builder = CostQueryBuilder(db)

    async def get_budget_utilization(
        self,
        tenant_id: Optional[UUID] = None,
    ) -> List[BudgetUtilizationDTO]:
        """
        Get budget utilization for tenants.

        Returns list of budget utilization summaries with color indicators.
        """
        try:
            today = date.today()
            start_of_month = today.replace(day=1)

            tenant_stmt = select(
                TenantConfig.tenant_id,
                TenantConfig.name,
                TenantConfig.max_budget,
            ).where(TenantConfig.max_budget > 0)

            if tenant_id:
                tenant_stmt = tenant_stmt.where(TenantConfig.tenant_id == tenant_id)

            tenant_result = await self.db.execute(tenant_stmt)
            tenants = tenant_result.all()

            utilization_dtos = []
            for tenant in tenants:
                current_spend = await self.query_builder.get_total_spend(
                    start_date=start_of_month,
                    end_date=today,
                    tenant_id=tenant.tenant_id,
                )

                budget_limit = float(tenant.max_budget)
                remaining = max(0.0, budget_limit - current_spend)
                utilization_pct = (
                    (current_spend / budget_limit * 100) if budget_limit > 0 else 0.0
                )

                # Determine color
                if utilization_pct < 70:
                    color = "green"
                elif utilization_pct < 90:
                    color = "yellow"
                else:
                    color = "red"

                utilization_dtos.append(
                    BudgetUtilizationDTO(
                        tenant_id=tenant.tenant_id,
                        tenant_name=tenant.name,
                        budget_limit=budget_limit,
                        current_spend=current_spend,
                        remaining=remaining,
                        utilization_pct=utilization_pct,
                        color=color,
                        is_byok=False,
                    )
                )

            logger.info(f"Retrieved budget utilization for {len(utilization_dtos)} tenants")
            return utilization_dtos

        except Exception as e:
            logger.error(f"Error fetching budget utilization: {e}", exc_info=True)
            raise

    async def get_cost_summary(
        self,
        tenant_id: Optional[UUID] = None,
    ) -> CostSummaryDTO:
        """
        Get overall cost summary with multiple time periods.

        Returns cost summary with today/week/month/30d totals and top tenant/agent.
        """
        try:
            today = date.today()

            # Today
            today_spend = await self.query_builder.get_total_spend(today, today, tenant_id)

            # This week (Monday to today)
            week_start = today - timedelta(days=today.weekday())
            week_spend = await self.query_builder.get_total_spend(
                week_start, today, tenant_id
            )

            # This month
            month_start = today.replace(day=1)
            month_spend = await self.query_builder.get_total_spend(
                month_start, today, tenant_id
            )

            # Last 30 days
            days_30_start = today - timedelta(days=30)
            total_spend_30d = await self.query_builder.get_total_spend(
                days_30_start, today, tenant_id
            )

            # Top tenant (if not filtered)
            top_tenant = None
            if not tenant_id:
                tenants = await self.query_builder.get_spend_by_tenant(
                    days_30_start, today, limit=1
                )
                top_tenant = tenants[0] if tenants else None

            # Top agent
            top_agent = None
            agents = await self.query_builder.get_spend_by_agent(
                days_30_start, today, tenant_id, limit=1
            )
            top_agent = agents[0] if agents else None

            return CostSummaryDTO(
                today_spend=today_spend,
                week_spend=week_spend,
                month_spend=month_spend,
                total_spend_30d=total_spend_30d,
                top_tenant=top_tenant,
                top_agent=top_agent,
            )

        except Exception as e:
            logger.error(f"Error fetching cost summary: {e}", exc_info=True)
            raise
