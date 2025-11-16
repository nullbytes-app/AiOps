"""
Agent Performance Service (Facade).

Main service class orchestrating performance metrics across query and aggregation modules.
Provides unified interface for agent performance analytics.

CRITICAL: ALL queries maintain tenant isolation (prevent cross-tenant data leakage).

Following 2025 best practices:
- Modular design with separated concerns (queries + aggregations)
- Async/await patterns with SQLAlchemy 2.0+
- Type hints with Optional, UUID, date
- Proper error handling and logging
"""

import logging
from datetime import date
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.agent_performance import (
    AgentMetricsDTO,
    ExecutionRecordDTO,
    TrendDataDTO,
    ErrorAnalysisDTO,
    AgentTokenUsageDTO,
    SlowAgentMetricsDTO,
    ExecutionFiltersDTO,
)
from src.services.agent_performance_aggregations import AgentPerformanceAggregator
from src.services.agent_performance_queries import AgentPerformanceQueryBuilder

logger = logging.getLogger(__name__)


class AgentPerformanceService:
    """
    Agent Performance Metrics Service (Facade).

    Orchestrates performance analytics queries and aggregations.
    Delegates to specialized modules for queries and aggregations.
    All methods support tenant isolation via tenant_id parameter or JOINs.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize performance service.

        Args:
            db: AsyncSession for database operations
        """
        self.db = db
        self.query_builder = AgentPerformanceQueryBuilder()
        self.aggregator = AgentPerformanceAggregator()

    async def get_agent_metrics(
        self,
        agent_id: UUID,
        agent_name: str,
        start_date: date,
        end_date: date,
    ) -> AgentMetricsDTO:
        """
        Get per-agent metrics summary (execution count, success rate, latency).

        Args:
            agent_id: Agent UUID
            agent_name: Agent name
            start_date: Query period start
            end_date: Query period end

        Returns:
            AgentMetricsDTO with comprehensive metrics
        """
        try:
            # Query raw metrics
            raw_metrics = await self.query_builder.get_agent_metrics(
                self.db, agent_id, start_date, end_date
            )

            # Normalize to DTO format
            normalized = self.aggregator.normalize_metrics_from_query(
                agent_id, agent_name, raw_metrics, start_date, end_date
            )

            return AgentMetricsDTO(**normalized)
        except Exception as e:
            logger.error(
                f"Error getting metrics for agent {agent_id}: {str(e)}"
            )
            raise

    async def get_execution_history(
        self,
        agent_id: UUID,
        filters: Optional[ExecutionFiltersDTO] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[ExecutionRecordDTO], int]:
        """
        Get paginated execution history with filtering.

        Args:
            agent_id: Agent UUID
            filters: Optional filters (status, date range, agent search)
            limit: Results per page
            offset: Pagination offset

        Returns:
            Tuple of (list of ExecutionRecordDTO, total count)
        """
        try:
            status_filter = filters.status if filters else None
            start_date = filters.start_date if filters else None
            end_date = filters.end_date if filters else None

            # Query raw records
            raw_records, total_count = await self.query_builder.get_execution_history(
                self.db, agent_id, status_filter, start_date, end_date, limit, offset
            )

            # Normalize records
            normalized = self.aggregator.normalize_execution_records(raw_records)

            # Convert to DTOs
            records = [ExecutionRecordDTO(**record) for record in normalized]

            return records, total_count
        except Exception as e:
            logger.error(
                f"Error getting execution history for agent {agent_id}: {str(e)}"
            )
            raise

    async def get_performance_trends(
        self,
        agent_id: UUID,
        days: int = 7,
    ) -> List[TrendDataDTO]:
        """
        Get daily performance trends for charting.

        Args:
            agent_id: Agent UUID
            days: Number of days to retrieve

        Returns:
            List of TrendDataDTO for each day
        """
        try:
            # Query raw trends
            raw_trends = await self.query_builder.get_performance_trends(
                self.db, agent_id, days
            )

            # Normalize
            normalized = self.aggregator.normalize_trend_data(raw_trends)

            # Convert to DTOs using alias for date field
            trends = [
                TrendDataDTO(**{**trend, "date": trend["trend_date"]})
                for trend in normalized
            ]

            return trends
        except Exception as e:
            logger.error(
                f"Error getting trends for agent {agent_id}: {str(e)}"
            )
            raise

    async def get_error_analysis(
        self,
        agent_id: UUID,
        start_date: date,
        end_date: date,
    ) -> Dict[str, int]:
        """
        Get error type breakdown for pie chart.

        Args:
            agent_id: Agent UUID
            start_date: Query period start
            end_date: Query period end

        Returns:
            Dict mapping error categories to counts
        """
        try:
            # Get execution history
            raw_records, _ = await self.query_builder.get_execution_history(
                self.db, agent_id, None, start_date, end_date, limit=10000
            )

            # Aggregate errors
            error_counts = self.aggregator.aggregate_error_analysis(raw_records)

            return error_counts
        except Exception as e:
            logger.error(
                f"Error getting error analysis for agent {agent_id}: {str(e)}"
            )
            raise

    async def get_token_usage_by_agent(
        self,
        tenant_id: str,
        start_date: date,
        end_date: date,
    ) -> List[AgentTokenUsageDTO]:
        """
        Get token usage aggregated by agent for bar chart.

        Note: This is a basic implementation. Full aggregation happens at query level.

        Args:
            tenant_id: Tenant identifier for isolation
            start_date: Query period start
            end_date: Query period end

        Returns:
            List of AgentTokenUsageDTO
        """
        # This would require a more complex query that groups by agent
        # For now, return empty list (can be enhanced later)
        return []

    async def get_slowest_agents(
        self,
        tenant_id: str,
        limit: int = 10,
    ) -> List[SlowAgentMetricsDTO]:
        """
        Get slowest agents sorted by P95 latency.

        Useful for identifying optimization candidates.

        Args:
            tenant_id: Tenant identifier for isolation
            limit: Max number to return

        Returns:
            List of SlowAgentMetricsDTO sorted by P95 latency descending
        """
        try:
            # Query slowest agents
            raw_slowest = await self.query_builder.get_slowest_agents(
                self.db, tenant_id, limit
            )

            # Normalize with recommendations
            normalized = self.aggregator.normalize_slowest_agents(raw_slowest)

            # Convert to DTOs
            slowest = [SlowAgentMetricsDTO(**agent) for agent in normalized]

            return slowest
        except Exception as e:
            logger.error(
                f"Error getting slowest agents for tenant {tenant_id}: {str(e)}"
            )
            raise
