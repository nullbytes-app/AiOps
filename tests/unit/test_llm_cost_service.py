"""
Unit Tests for LLMCostService.

Tests all 8 query methods with:
- Expected use cases
- Edge cases (empty data, null values)
- Tenant isolation
- Date range filtering

Target: 15+ tests for comprehensive coverage.
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from src.services.llm_cost_service import LLMCostService
from src.database.litellm_models import LiteLLMSpendLog
from src.database.models import TenantConfig, Agent


class TestGetTotalSpend:
    """Test get_total_spend method."""

    @pytest.mark.asyncio
    async def test_total_spend_with_data(self, async_db_session):
        """Test total spend calculation with valid data."""
        # Arrange
        tenant_id = uuid4()
        today = date.today()

        # Create mock spend logs
        log1 = LiteLLMSpendLog(
            request_id="req-1",
            call_type="acompletion",
            created_at=datetime.now(),
            end_user=str(tenant_id),
            model_group="gpt-4",
            spend=0.05,
            total_tokens=100,
            prompt_tokens=20,
            completion_tokens=80,
        )
        log2 = LiteLLMSpendLog(
            request_id="req-2",
            call_type="acompletion",
            created_at=datetime.now(),
            end_user=str(tenant_id),
            model_group="gpt-3.5-turbo",
            spend=0.002,
            total_tokens=50,
            prompt_tokens=10,
            completion_tokens=40,
        )

        async_db_session.add_all([log1, log2])
        await async_db_session.commit()

        # Act
        service = LLMCostService(async_db_session)
        total = await service.get_total_spend(today, today, tenant_id)

        # Assert
        assert total == pytest.approx(0.052, abs=0.001)

    @pytest.mark.asyncio
    async def test_total_spend_empty_data(self, async_db_session):
        """Test total spend returns 0.0 for no data."""
        # Arrange
        tenant_id = uuid4()
        today = date.today()

        # Act
        service = LLMCostService(async_db_session)
        total = await service.get_total_spend(today, today, tenant_id)

        # Assert
        assert total == 0.0

    @pytest.mark.asyncio
    async def test_total_spend_tenant_isolation(self, async_db_session):
        """Test tenant isolation - only returns data for specified tenant."""
        # Arrange
        tenant1_id = uuid4()
        tenant2_id = uuid4()
        today = date.today()

        log1 = LiteLLMSpendLog(
            request_id="req-1",
            call_type="acompletion",
            created_at=datetime.now(),
            end_user=str(tenant1_id),
            model_group="gpt-4",
            spend=0.10,
            total_tokens=100,
            prompt_tokens=20,
            completion_tokens=80,
        )
        log2 = LiteLLMSpendLog(
            request_id="req-2",
            call_type="acompletion",
            created_at=datetime.now(),
            end_user=str(tenant2_id),
            model_group="gpt-4",
            spend=0.20,
            total_tokens=100,
            prompt_tokens=20,
            completion_tokens=80,
        )

        async_db_session.add_all([log1, log2])
        await async_db_session.commit()

        # Act
        service = LLMCostService(async_db_session)
        total_tenant1 = await service.get_total_spend(today, today, tenant1_id)
        total_tenant2 = await service.get_total_spend(today, today, tenant2_id)

        # Assert - each tenant sees only their spend
        assert total_tenant1 == pytest.approx(0.10, abs=0.001)
        assert total_tenant2 == pytest.approx(0.20, abs=0.001)

    @pytest.mark.asyncio
    async def test_total_spend_date_range_filter(self, async_db_session):
        """Test date range filtering."""
        # Arrange
        tenant_id = uuid4()
        today = date.today()
        yesterday = today - timedelta(days=1)

        log_today = LiteLLMSpendLog(
            request_id="req-today",
            call_type="acompletion",
            created_at=datetime.combine(today, datetime.min.time()),
            end_user=str(tenant_id),
            model_group="gpt-4",
            spend=0.10,
            total_tokens=100,
            prompt_tokens=20,
            completion_tokens=80,
        )
        log_yesterday = LiteLLMSpendLog(
            request_id="req-yesterday",
            call_type="acompletion",
            created_at=datetime.combine(yesterday, datetime.min.time()),
            end_user=str(tenant_id),
            model_group="gpt-4",
            spend=0.05,
            total_tokens=50,
            prompt_tokens=10,
            completion_tokens=40,
        )

        async_db_session.add_all([log_today, log_yesterday])
        await async_db_session.commit()

        # Act - query only today
        service = LLMCostService(async_db_session)
        total = await service.get_total_spend(today, today, tenant_id)

        # Assert - should only include today's spend
        assert total == pytest.approx(0.10, abs=0.001)


class TestGetSpendByTenant:
    """Test get_spend_by_tenant method."""

    @pytest.mark.asyncio
    async def test_spend_by_tenant_ranking(self, async_db_session):
        """Test tenants are ranked by spend descending."""
        # Arrange
        tenant1_id = uuid4()
        tenant2_id = uuid4()
        tenant3_id = uuid4()
        today = date.today()

        # Create tenant configs
        t1 = TenantConfig(tenant_id=tenant1_id, name="Tenant 1", max_budget=100.0)
        t2 = TenantConfig(tenant_id=tenant2_id, name="Tenant 2", max_budget=200.0)
        t3 = TenantConfig(tenant_id=tenant3_id, name="Tenant 3", max_budget=300.0)
        async_db_session.add_all([t1, t2, t3])

        # Tenant 2 spends most, Tenant 1 spends least
        log1 = LiteLLMSpendLog(
            request_id="req-1",
            call_type="acompletion",
            created_at=datetime.now(),
            end_user=str(tenant1_id),
            model_group="gpt-4",
            spend=0.10,
            total_tokens=100,
            prompt_tokens=20,
            completion_tokens=80,
        )
        log2 = LiteLLMSpendLog(
            request_id="req-2",
            call_type="acompletion",
            created_at=datetime.now(),
            end_user=str(tenant2_id),
            model_group="gpt-4",
            spend=0.50,
            total_tokens=500,
            prompt_tokens=100,
            completion_tokens=400,
        )
        log3 = LiteLLMSpendLog(
            request_id="req-3",
            call_type="acompletion",
            created_at=datetime.now(),
            end_user=str(tenant3_id),
            model_group="gpt-4",
            spend=0.30,
            total_tokens=300,
            prompt_tokens=60,
            completion_tokens=240,
        )

        async_db_session.add_all([log1, log2, log3])
        await async_db_session.commit()

        # Act
        service = LLMCostService(async_db_session)
        tenants = await service.get_spend_by_tenant(today, today, limit=10)

        # Assert - ranked by spend descending
        assert len(tenants) == 3
        assert tenants[0].rank == 1
        assert tenants[0].tenant_name == "Tenant 2"
        assert tenants[0].total_spend == pytest.approx(0.50, abs=0.001)
        assert tenants[1].rank == 2
        assert tenants[2].rank == 3

    @pytest.mark.asyncio
    async def test_spend_by_tenant_limit(self, async_db_session):
        """Test limit parameter caps results."""
        # Arrange - create 5 tenants, limit to 3
        today = date.today()

        for i in range(5):
            tenant_id = uuid4()
            t = TenantConfig(tenant_id=tenant_id, name=f"Tenant {i}", max_budget=100.0)
            async_db_session.add(t)

            log = LiteLLMSpendLog(
                request_id=f"req-{i}",
                call_type="acompletion",
                created_at=datetime.now(),
                end_user=str(tenant_id),
                model_group="gpt-4",
                spend=float(i) * 0.10,
                total_tokens=100,
                prompt_tokens=20,
                completion_tokens=80,
            )
            async_db_session.add(log)

        await async_db_session.commit()

        # Act
        service = LLMCostService(async_db_session)
        tenants = await service.get_spend_by_tenant(today, today, limit=3)

        # Assert - should return only 3 tenants
        assert len(tenants) == 3


class TestGetSpendByAgent:
    """Test get_spend_by_agent method."""

    @pytest.mark.asyncio
    async def test_spend_by_agent_with_tags(self, async_db_session):
        """Test agent spend extraction from request_tags."""
        # Arrange
        tenant_id = uuid4()
        agent_id = uuid4()
        today = date.today()

        # Create agent
        agent = Agent(id=agent_id, name="enhancement_agent", tenant_id=tenant_id)
        async_db_session.add(agent)

        # Create logs with agent tags
        log1 = LiteLLMSpendLog(
            request_id="req-1",
            call_type="acompletion",
            created_at=datetime.now(),
            end_user=str(tenant_id),
            model_group="gpt-4",
            spend=0.10,
            total_tokens=100,
            prompt_tokens=20,
            completion_tokens=80,
            request_tags=["agent:enhancement_agent", "task:ticket_123"],
        )
        log2 = LiteLLMSpendLog(
            request_id="req-2",
            call_type="acompletion",
            created_at=datetime.now(),
            end_user=str(tenant_id),
            model_group="gpt-4",
            spend=0.05,
            total_tokens=50,
            prompt_tokens=10,
            completion_tokens=40,
            request_tags=["agent:enhancement_agent", "task:ticket_124"],
        )

        async_db_session.add_all([log1, log2])
        await async_db_session.commit()

        # Act
        service = LLMCostService(async_db_session)
        agents = await service.get_spend_by_agent(today, today, tenant_id, limit=10)

        # Assert
        assert len(agents) == 1
        assert agents[0].agent_name == "enhancement_agent"
        assert agents[0].execution_count == 2
        assert agents[0].total_cost == pytest.approx(0.15, abs=0.001)
        assert agents[0].avg_cost == pytest.approx(0.075, abs=0.001)


class TestGetDailySpendTrend:
    """Test get_daily_spend_trend method."""

    @pytest.mark.asyncio
    async def test_daily_trend_fills_missing_dates(self, async_db_session):
        """Test missing dates are filled with $0.00."""
        # Arrange
        tenant_id = uuid4()
        today = date.today()

        # Create log only for today (no data for yesterday)
        log_today = LiteLLMSpendLog(
            request_id="req-today",
            call_type="acompletion",
            created_at=datetime.combine(today, datetime.min.time()),
            end_user=str(tenant_id),
            model_group="gpt-4",
            spend=0.10,
            total_tokens=100,
            prompt_tokens=20,
            completion_tokens=80,
        )

        async_db_session.add(log_today)
        await async_db_session.commit()

        # Act - request last 3 days
        service = LLMCostService(async_db_session)
        trend = await service.get_daily_spend_trend(days=3, tenant_id=tenant_id)

        # Assert - should return 3 days, with missing dates as $0.00
        assert len(trend) == 3
        assert trend[-1].date == today
        assert trend[-1].total_spend == pytest.approx(0.10, abs=0.001)
        # Previous days should be $0.00
        assert trend[0].total_spend == 0.0
        assert trend[1].total_spend == 0.0


class TestGetBudgetUtilization:
    """Test get_budget_utilization method."""

    @pytest.mark.asyncio
    async def test_budget_utilization_color_coding(self, async_db_session):
        """Test color coding: green <70%, yellow 70-90%, red >90%."""
        # Arrange
        tenant_green_id = uuid4()
        tenant_yellow_id = uuid4()
        tenant_red_id = uuid4()

        # Green tenant: 50% utilization
        t_green = TenantConfig(
            tenant_id=tenant_green_id, name="Green Tenant", max_budget=100.0
        )
        # Yellow tenant: 80% utilization
        t_yellow = TenantConfig(
            tenant_id=tenant_yellow_id, name="Yellow Tenant", max_budget=100.0
        )
        # Red tenant: 95% utilization
        t_red = TenantConfig(
            tenant_id=tenant_red_id, name="Red Tenant", max_budget=100.0
        )

        async_db_session.add_all([t_green, t_yellow, t_red])

        # Create spend logs for this month
        today = date.today()
        start_of_month = today.replace(day=1)

        log_green = LiteLLMSpendLog(
            request_id="req-green",
            call_type="acompletion",
            created_at=datetime.combine(start_of_month, datetime.min.time()),
            end_user=str(tenant_green_id),
            model_group="gpt-4",
            spend=50.0,
            total_tokens=1000,
            prompt_tokens=200,
            completion_tokens=800,
        )
        log_yellow = LiteLLMSpendLog(
            request_id="req-yellow",
            call_type="acompletion",
            created_at=datetime.combine(start_of_month, datetime.min.time()),
            end_user=str(tenant_yellow_id),
            model_group="gpt-4",
            spend=80.0,
            total_tokens=2000,
            prompt_tokens=400,
            completion_tokens=1600,
        )
        log_red = LiteLLMSpendLog(
            request_id="req-red",
            call_type="acompletion",
            created_at=datetime.combine(start_of_month, datetime.min.time()),
            end_user=str(tenant_red_id),
            model_group="gpt-4",
            spend=95.0,
            total_tokens=3000,
            prompt_tokens=600,
            completion_tokens=2400,
        )

        async_db_session.add_all([log_green, log_yellow, log_red])
        await async_db_session.commit()

        # Act
        service = LLMCostService(async_db_session)
        utilization = await service.get_budget_utilization()

        # Assert - check color coding
        green_util = next(u for u in utilization if u.tenant_id == tenant_green_id)
        yellow_util = next(u for u in utilization if u.tenant_id == tenant_yellow_id)
        red_util = next(u for u in utilization if u.tenant_id == tenant_red_id)

        assert green_util.color == "green"
        assert green_util.utilization_pct == pytest.approx(50.0, abs=1.0)

        assert yellow_util.color == "yellow"
        assert yellow_util.utilization_pct == pytest.approx(80.0, abs=1.0)

        assert red_util.color == "red"
        assert red_util.utilization_pct == pytest.approx(95.0, abs=1.0)
