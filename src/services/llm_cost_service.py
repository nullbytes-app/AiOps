"""
LLM Cost Service (Facade).

Main service class that orchestrates cost tracking across query and aggregation modules.
Provides a unified interface for cost analytics operations.

CRITICAL: ALL queries maintain tenant isolation (prevent cross-tenant data leakage).

Following 2025 best practices:
- Modular design with separated concerns
- Async/await patterns with SQLAlchemy 2.0+
- Type hints with Optional, UUID, date
- Proper error handling and logging
"""

import logging
from datetime import date
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.llm_cost import (
    AgentSpendDTO,
    BudgetUtilizationDTO,
    CostSummaryDTO,
    DailySpendDTO,
    ModelSpendDTO,
    SpendLogDetailDTO,
    TenantSpendDTO,
    TokenBreakdownDTO,
)
from src.services.llm_cost_aggregations import CostAggregator
from src.services.llm_cost_queries import CostQueryBuilder

logger = logging.getLogger(__name__)


class LLMCostService:
    """
    LLM Cost Tracking Service (Facade).

    Orchestrates cost analytics queries and aggregations.
    Delegates to specialized modules for queries and aggregations.
    All methods support tenant isolation via tenant_id parameter.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize cost service.

        Args:
            db: Async database session
        """
        self.db = db
        self.query_builder = CostQueryBuilder(db)
        self.aggregator = CostAggregator(db)

    async def get_total_spend(
        self,
        start_date: date,
        end_date: date,
        tenant_id: Optional[UUID] = None,
    ) -> float:
        """Calculate total spend for date range (delegates to query builder)."""
        return await self.query_builder.get_total_spend(start_date, end_date, tenant_id)

    async def get_spend_by_tenant(
        self,
        start_date: date,
        end_date: date,
        limit: int = 10,
    ) -> List[TenantSpendDTO]:
        """Get top N tenants by spend (delegates to query builder)."""
        return await self.query_builder.get_spend_by_tenant(start_date, end_date, limit)

    async def get_spend_by_agent(
        self,
        start_date: date,
        end_date: date,
        tenant_id: Optional[UUID] = None,
        limit: int = 10,
    ) -> List[AgentSpendDTO]:
        """Get top N agents by spend (delegates to query builder)."""
        return await self.query_builder.get_spend_by_agent(
            start_date, end_date, tenant_id, limit
        )

    async def get_spend_by_model(
        self,
        start_date: date,
        end_date: date,
        tenant_id: Optional[UUID] = None,
    ) -> List[ModelSpendDTO]:
        """Get spend breakdown by model (delegates to query builder)."""
        return await self.query_builder.get_spend_by_model(start_date, end_date, tenant_id)

    async def get_token_breakdown(
        self,
        start_date: date,
        end_date: date,
        model: Optional[str] = None,
        tenant_id: Optional[UUID] = None,
    ) -> List[TokenBreakdownDTO]:
        """Get token usage breakdown (delegates to query builder)."""
        return await self.query_builder.get_token_breakdown(
            start_date, end_date, model, tenant_id
        )

    async def get_daily_spend_trend(
        self,
        days: int = 30,
        tenant_id: Optional[UUID] = None,
    ) -> List[DailySpendDTO]:
        """Get daily spend time series (delegates to query builder)."""
        return await self.query_builder.get_daily_spend_trend(days, tenant_id)

    async def get_budget_utilization(
        self,
        tenant_id: Optional[UUID] = None,
    ) -> List[BudgetUtilizationDTO]:
        """Get budget utilization for tenants (delegates to aggregator)."""
        return await self.aggregator.get_budget_utilization(tenant_id)

    async def get_cost_summary(
        self,
        tenant_id: Optional[UUID] = None,
    ) -> CostSummaryDTO:
        """Get overall cost summary (delegates to aggregator)."""
        return await self.aggregator.get_cost_summary(tenant_id)

    async def get_detailed_logs(
        self,
        start_date: date,
        end_date: date,
        tenant_id: Optional[UUID] = None,
        agent_id: Optional[UUID] = None,
    ) -> List[SpendLogDetailDTO]:
        """Get detailed spend logs (delegates to query builder)."""
        return await self.query_builder.get_detailed_logs(
            start_date, end_date, tenant_id, agent_id
        )
