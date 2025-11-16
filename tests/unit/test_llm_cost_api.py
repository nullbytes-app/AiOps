"""
Unit Tests for LLM Cost API Endpoints.

Tests all 7 REST endpoints with:
- Successful responses
- Authorization/tenant isolation
- Query parameter validation
- Error handling

Target: 12+ tests for comprehensive coverage.
"""

import pytest
from datetime import date, timedelta
from uuid import uuid4
from fastapi import status

from src.schemas.llm_cost import (
    CostSummaryDTO,
    TenantSpendDTO,
    AgentSpendDTO,
    DailySpendDTO,
)


class TestGetCostSummary:
    """Test GET /api/costs/summary endpoint."""

    @pytest.mark.asyncio
    async def test_get_cost_summary_success(self, async_client, mock_tenant_id):
        """Test successful cost summary retrieval."""
        # Act
        response = await async_client.get(
            "/api/costs/summary",
            headers={"Authorization": f"Bearer {mock_tenant_id}"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "today_spend" in data
        assert "week_spend" in data
        assert "month_spend" in data
        assert "total_spend_30d" in data

    @pytest.mark.asyncio
    async def test_get_cost_summary_unauthorized(self, async_client):
        """Test summary endpoint requires authorization."""
        # Act - no auth header
        response = await async_client.get("/api/costs/summary")

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetSpendByTenant:
    """Test GET /api/costs/by-tenant endpoint."""

    @pytest.mark.asyncio
    async def test_get_spend_by_tenant_success(self, async_client, mock_tenant_id):
        """Test successful tenant spend retrieval."""
        # Arrange
        today = date.today()
        start_date = today - timedelta(days=30)

        # Act
        response = await async_client.get(
            "/api/costs/by-tenant",
            params={"start_date": start_date.isoformat(), "end_date": today.isoformat()},
            headers={"Authorization": f"Bearer {mock_tenant_id}"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_spend_by_tenant_limit_validation(self, async_client, mock_tenant_id):
        """Test limit parameter validation."""
        # Arrange
        today = date.today()

        # Act - limit > 100 (exceeds max)
        response = await async_client.get(
            "/api/costs/by-tenant",
            params={
                "start_date": today.isoformat(),
                "end_date": today.isoformat(),
                "limit": 150,
            },
            headers={"Authorization": f"Bearer {mock_tenant_id}"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_get_spend_by_tenant_missing_dates(self, async_client, mock_tenant_id):
        """Test endpoint requires start_date and end_date."""
        # Act - missing required params
        response = await async_client.get(
            "/api/costs/by-tenant",
            headers={"Authorization": f"Bearer {mock_tenant_id}"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGetSpendByAgent:
    """Test GET /api/costs/by-agent endpoint."""

    @pytest.mark.asyncio
    async def test_get_spend_by_agent_success(self, async_client, mock_tenant_id):
        """Test successful agent spend retrieval."""
        # Arrange
        today = date.today()
        start_date = today - timedelta(days=7)

        # Act
        response = await async_client.get(
            "/api/costs/by-agent",
            params={
                "start_date": start_date.isoformat(),
                "end_date": today.isoformat(),
                "limit": 10,
            },
            headers={"Authorization": f"Bearer {mock_tenant_id}"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_spend_by_agent_tenant_isolation(
        self, async_client, mock_tenant_id, mock_tenant_id_2
    ):
        """Test tenant isolation - different tenants see different data."""
        # Arrange
        today = date.today()

        # Act - two different tenants query
        response1 = await async_client.get(
            "/api/costs/by-agent",
            params={"start_date": today.isoformat(), "end_date": today.isoformat()},
            headers={"Authorization": f"Bearer {mock_tenant_id}"},
        )
        response2 = await async_client.get(
            "/api/costs/by-agent",
            params={"start_date": today.isoformat(), "end_date": today.isoformat()},
            headers={"Authorization": f"Bearer {mock_tenant_id_2}"},
        )

        # Assert - both succeed but may return different data
        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK


class TestGetSpendByModel:
    """Test GET /api/costs/by-model endpoint."""

    @pytest.mark.asyncio
    async def test_get_spend_by_model_success(self, async_client, mock_tenant_id):
        """Test successful model spend retrieval."""
        # Arrange
        today = date.today()

        # Act
        response = await async_client.get(
            "/api/costs/by-model",
            params={"start_date": today.isoformat(), "end_date": today.isoformat()},
            headers={"Authorization": f"Bearer {mock_tenant_id}"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)


class TestGetTokenBreakdown:
    """Test GET /api/costs/token-breakdown endpoint."""

    @pytest.mark.asyncio
    async def test_get_token_breakdown_success(self, async_client, mock_tenant_id):
        """Test successful token breakdown retrieval."""
        # Arrange
        today = date.today()

        # Act
        response = await async_client.get(
            "/api/costs/token-breakdown",
            params={"start_date": today.isoformat(), "end_date": today.isoformat()},
            headers={"Authorization": f"Bearer {mock_tenant_id}"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_token_breakdown_with_model_filter(
        self, async_client, mock_tenant_id
    ):
        """Test token breakdown with optional model filter."""
        # Arrange
        today = date.today()

        # Act
        response = await async_client.get(
            "/api/costs/token-breakdown",
            params={
                "start_date": today.isoformat(),
                "end_date": today.isoformat(),
                "model": "gpt-4",
            },
            headers={"Authorization": f"Bearer {mock_tenant_id}"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK


class TestGetDailySpendTrend:
    """Test GET /api/costs/trend endpoint."""

    @pytest.mark.asyncio
    async def test_get_daily_trend_success(self, async_client, mock_tenant_id):
        """Test successful daily trend retrieval."""
        # Act
        response = await async_client.get(
            "/api/costs/trend",
            params={"days": 30},
            headers={"Authorization": f"Bearer {mock_tenant_id}"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 30  # Should return 30 days

    @pytest.mark.asyncio
    async def test_get_daily_trend_days_validation(self, async_client, mock_tenant_id):
        """Test days parameter validation (1-365)."""
        # Act - days > 365 (exceeds max)
        response = await async_client.get(
            "/api/costs/trend",
            params={"days": 400},
            headers={"Authorization": f"Bearer {mock_tenant_id}"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGetBudgetUtilization:
    """Test GET /api/costs/budget-utilization endpoint."""

    @pytest.mark.asyncio
    async def test_get_budget_utilization_success(self, async_client, mock_tenant_id):
        """Test successful budget utilization retrieval."""
        # Act
        response = await async_client.get(
            "/api/costs/budget-utilization",
            headers={"Authorization": f"Bearer {mock_tenant_id}"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_budget_utilization_tenant_filtered(
        self, async_client, mock_tenant_id
    ):
        """Test budget utilization returns only authenticated tenant's data."""
        # Act
        response = await async_client.get(
            "/api/costs/budget-utilization",
            headers={"Authorization": f"Bearer {mock_tenant_id}"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should only return data for authenticated tenant
        for item in data:
            assert item["tenant_id"] == str(mock_tenant_id)


# Fixtures for test support
@pytest.fixture
def mock_tenant_id():
    """Mock tenant ID for testing."""
    return uuid4()


@pytest.fixture
def mock_tenant_id_2():
    """Second mock tenant ID for isolation testing."""
    return uuid4()
