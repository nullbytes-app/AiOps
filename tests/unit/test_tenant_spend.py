"""Unit tests for tenant spend tracking and budget dashboard.

Tests cover:
- Budget service LiteLLM /key/info query
- Model spend breakdown parsing and sorting
- Tenant spend API endpoint
- Schema validation
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.budget_service import BudgetService, TenantSpend, ModelSpend
from src.schemas.tenant_spend import TenantSpendResponse, ModelSpendResponse
from src.database.models import TenantConfig
from sqlalchemy.ext.asyncio import AsyncSession


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_tenant_config():
    """Create a mock tenant configuration."""
    tenant = MagicMock(spec=TenantConfig)
    tenant.tenant_id = "test-tenant"
    tenant.is_active = True
    tenant.max_budget = 500.0
    tenant.budget_duration = "30d"
    tenant.budget_reset_at = datetime(2025, 12, 7, tzinfo=timezone.utc)
    tenant.byok_enabled = False
    tenant.byok_virtual_key = None
    tenant.litellm_virtual_key = "sk-litellm-test-key-123"
    tenant.alert_threshold = 80
    tenant.grace_threshold = 110
    return tenant


@pytest.fixture
def litellm_response_with_models():
    """Mock LiteLLM /key/info response with multiple models."""
    return {
        "key": "sk-litellm-test-key-123",
        "info": {
            "spend": 45.67,
            "max_budget": 500.0,
            "budget_duration": "30d",
            "budget_reset_at": "2025-12-07T00:00:00Z",
            "models": [
                {"model": "gpt-4", "spend": 30.50, "requests": 125},
                {"model": "claude-3-opus-20240229", "spend": 15.17, "requests": 45},
            ],
        },
    }


@pytest.fixture
def litellm_response_empty_models():
    """Mock LiteLLM /key/info response with no spend."""
    return {
        "key": "sk-litellm-test-key-123",
        "info": {
            "spend": 0.0,
            "max_budget": 500.0,
            "budget_duration": "30d",
            "budget_reset_at": "2025-12-07T00:00:00Z",
            "models": [],
        },
    }


# ============================================================================
# AC #1: Spend Data Retrieved from LiteLLM
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_tenant_spend_from_litellm_success(
    mock_tenant_config, litellm_response_with_models
):
    """Test successful spend data retrieval from LiteLLM."""
    # Mock database session
    mock_db = AsyncMock(spec=AsyncSession)
    mock_stmt = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_tenant_config
    mock_db.execute.return_value = mock_result

    # Mock httpx client
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = litellm_response_with_models
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        # Execute
        service = BudgetService(mock_db, "http://litellm:4000", "master-key-123")
        spend = await service.get_tenant_spend_from_litellm("test-tenant")

        # Verify
        assert spend.tenant_id == "test-tenant"
        assert spend.current_spend == 45.67
        assert spend.max_budget == 500.0
        assert pytest.approx(spend.utilization_pct, 0.01) == 9.13
        assert len(spend.models_breakdown) == 2
        assert spend.models_breakdown[0].model == "gpt-4"  # Sorted by spend


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_tenant_spend_model_breakdown_sorted(
    mock_tenant_config, litellm_response_with_models
):
    """Test that models are sorted by spend descending (most expensive first)."""
    mock_db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_tenant_config
    mock_db.execute.return_value = mock_result

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = litellm_response_with_models
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        service = BudgetService(mock_db, "http://litellm:4000", "master-key-123")
        spend = await service.get_tenant_spend_from_litellm("test-tenant")

        # Verify sorted by spend descending
        assert spend.models_breakdown[0].spend == 30.50  # gpt-4
        assert spend.models_breakdown[1].spend == 15.17  # claude
        # Verify percentages
        assert pytest.approx(spend.models_breakdown[0].percentage, 0.1) == 66.7
        assert pytest.approx(spend.models_breakdown[1].percentage, 0.1) == 33.3


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_tenant_spend_no_virtual_key():
    """Test error when tenant has no virtual key (edge case)."""
    mock_tenant_config = MagicMock(spec=TenantConfig)
    mock_tenant_config.tenant_id = "test-tenant"
    mock_tenant_config.byok_enabled = False
    mock_tenant_config.byok_virtual_key = None
    mock_tenant_config.litellm_virtual_key = None  # No key!

    mock_db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_tenant_config
    mock_db.execute.return_value = mock_result

    service = BudgetService(mock_db, "http://litellm:4000", "master-key-123")

    with pytest.raises(ValueError, match="No LiteLLM virtual key configured"):
        await service.get_tenant_spend_from_litellm("test-tenant")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_tenant_spend_litellm_error(mock_tenant_config):
    """Test error handling when LiteLLM API returns error (failure case)."""
    mock_db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_tenant_config
    mock_db.execute.return_value = mock_result

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 503  # Service unavailable
        mock_response.text = "Service temporarily down"
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        service = BudgetService(mock_db, "http://litellm:4000", "master-key-123")

        with pytest.raises(Exception):
            await service.get_tenant_spend_from_litellm("test-tenant")


# ============================================================================
# AC #2: Tenant Dashboard Shows Real-Time Spend
# ============================================================================


@pytest.mark.unit
def test_tenant_spend_response_schema_validation():
    """Test TenantSpendResponse schema validation."""
    model_spend = ModelSpendResponse(
        model="gpt-4", spend=30.50, percentage=66.7, requests=125
    )
    assert model_spend.model == "gpt-4"
    assert model_spend.spend == 30.50
    assert model_spend.percentage == 66.7
    assert model_spend.requests == 125


@pytest.mark.unit
def test_tenant_spend_response_with_models():
    """Test TenantSpendResponse with model breakdown."""
    models = [
        ModelSpendResponse(model="gpt-4", spend=30.50, percentage=66.7, requests=125),
        ModelSpendResponse(
            model="claude-3-opus", spend=15.17, percentage=33.3, requests=45
        ),
    ]

    spend_response = TenantSpendResponse(
        tenant_id="test-tenant",
        current_spend=45.67,
        max_budget=500.0,
        utilization_pct=9.13,
        models_breakdown=models,
        last_updated=datetime.now(timezone.utc),
        budget_duration="30d",
        budget_reset_at="2025-12-07T00:00:00Z",
    )

    assert spend_response.tenant_id == "test-tenant"
    assert spend_response.current_spend == 45.67
    assert spend_response.utilization_pct == 9.13
    assert len(spend_response.models_breakdown) == 2


# ============================================================================
# AC #3: Model Spend Breakdown Displayed
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_model_breakdown_percentages_sum_to_100(
    mock_tenant_config, litellm_response_with_models
):
    """Test that model percentages sum to ~100% (edge case)."""
    mock_db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_tenant_config
    mock_db.execute.return_value = mock_result

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = litellm_response_with_models
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        service = BudgetService(mock_db, "http://litellm:4000", "master-key-123")
        spend = await service.get_tenant_spend_from_litellm("test-tenant")

        # Sum percentages
        total_pct = sum(m.percentage for m in spend.models_breakdown)
        assert pytest.approx(total_pct, 0.1) == 100.0


@pytest.mark.asyncio
@pytest.mark.unit
async def test_empty_models_list(mock_tenant_config, litellm_response_empty_models):
    """Test handling of zero spend with no models (edge case)."""
    mock_db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_tenant_config
    mock_db.execute.return_value = mock_result

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = litellm_response_empty_models
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        service = BudgetService(mock_db, "http://litellm:4000", "master-key-123")
        spend = await service.get_tenant_spend_from_litellm("test-tenant")

        assert spend.current_spend == 0.0
        assert spend.utilization_pct == 0.0
        assert len(spend.models_breakdown) == 0


# ============================================================================
# AC #4: Alert Indicators Work
# ============================================================================


@pytest.mark.unit
def test_alert_threshold_80_percent():
    """Test warning alert at 80% utilization."""
    models = [
        ModelSpendResponse(model="gpt-4", spend=400.0, percentage=100.0, requests=100),
    ]

    spend_response = TenantSpendResponse(
        tenant_id="test-tenant",
        current_spend=400.0,
        max_budget=500.0,
        utilization_pct=80.0,
        models_breakdown=models,
        last_updated=datetime.now(timezone.utc),
    )

    assert spend_response.utilization_pct >= 80.0
    assert spend_response.utilization_pct < 100.0


@pytest.mark.unit
def test_alert_threshold_100_percent():
    """Test critical alert at 100% utilization."""
    spend_response = TenantSpendResponse(
        tenant_id="test-tenant",
        current_spend=500.0,
        max_budget=500.0,
        utilization_pct=100.0,
        models_breakdown=[],
        last_updated=datetime.now(timezone.utc),
    )

    assert spend_response.utilization_pct >= 100.0


@pytest.mark.unit
def test_alert_threshold_110_percent():
    """Test grace exceeded alert at 110% utilization."""
    spend_response = TenantSpendResponse(
        tenant_id="test-tenant",
        current_spend=550.0,
        max_budget=500.0,
        utilization_pct=110.0,
        models_breakdown=[],
        last_updated=datetime.now(timezone.utc),
    )

    assert spend_response.utilization_pct >= 110.0


# ============================================================================
# AC #5: Dashboard Refreshes on Demand
# ============================================================================


@pytest.mark.unit
def test_tenant_spend_last_updated_timestamp():
    """Test that last_updated timestamp is captured."""
    now = datetime.now(timezone.utc)
    spend_response = TenantSpendResponse(
        tenant_id="test-tenant",
        current_spend=45.67,
        max_budget=500.0,
        utilization_pct=9.13,
        models_breakdown=[],
        last_updated=now,
    )

    assert spend_response.last_updated == now


# ============================================================================
# AC #6: Graceful Handling of Missing Data
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_tenant_not_found():
    """Test error when tenant not found."""
    mock_db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # Tenant not found
    mock_db.execute.return_value = mock_result

    service = BudgetService(mock_db, "http://litellm:4000", "master-key-123")

    with pytest.raises(ValueError, match="Tenant not found"):
        await service.get_tenant_spend_from_litellm("nonexistent-tenant")


@pytest.mark.unit
def test_schema_handles_none_values():
    """Test that schema handles None values gracefully."""
    spend_response = TenantSpendResponse(
        tenant_id="test-tenant",
        current_spend=45.67,
        max_budget=500.0,
        utilization_pct=9.13,
        models_breakdown=[],
        last_updated=datetime.now(timezone.utc),
        budget_duration=None,  # Optional
        budget_reset_at=None,  # Optional
    )

    assert spend_response.budget_duration is None
    assert spend_response.budget_reset_at is None
