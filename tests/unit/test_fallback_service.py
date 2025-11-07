"""Comprehensive unit tests for FallbackService.

Tests cover:
- CRUD operations (create, read, update, delete)
- Circular fallback prevention and validation
- Trigger configuration and retrieval
- Metrics recording and aggregation
- Edge cases and error handling
"""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    LLMProvider, LLMModel, TenantConfig, FallbackChain,
    FallbackTrigger, FallbackMetric
)
from src.services.fallback_service import FallbackService
from src.schemas.fallback import (
    FallbackChainCreate, FallbackTriggerConfig,
    FallbackChainResponse
)


@pytest.fixture
async def tenant_id() -> str:
    """Provide test tenant ID."""
    return str(uuid4())


@pytest.fixture
async def test_provider(db_session: AsyncSession, tenant_id: str) -> LLMProvider:
    """Create test provider."""
    provider = LLMProvider(
        tenant_id=tenant_id,
        name="Test Provider",
        provider_type="openai",
        api_key_encrypted="test-key",
        api_base_url="https://api.openai.com/v1",
        is_active=True,
    )
    db_session.add(provider)
    await db_session.flush()
    return provider


@pytest.fixture
async def test_models(db_session: AsyncSession, test_provider: LLMProvider) -> list:
    """Create test models for fallback chain testing.

    Returns list of 5 models:
    - models[0]: Primary model (enabled)
    - models[1-2]: Fallback options (enabled)
    - models[3-4]: Disabled models for testing
    """
    models = []
    for i in range(5):
        model = LLMModel(
            provider_id=test_provider.id,
            model_name=f"gpt-4-{i}",
            model_type="chat",
            max_tokens=8000,
            pricing_per_1k_input=0.03,
            pricing_per_1k_output=0.06,
            enabled=i < 3,  # First 3 enabled, last 2 disabled
        )
        db_session.add(model)
        models.append(model)

    await db_session.flush()
    return models


@pytest.fixture
async def fallback_service(db_session: AsyncSession) -> FallbackService:
    """Create FallbackService instance."""
    return FallbackService(db_session)


# ============================================================================
# CRUD Operations Tests
# ============================================================================

class TestFallbackChainCRUD:
    """Test fallback chain CRUD operations."""

    async def test_create_fallback_chain_success(
        self,
        fallback_service: FallbackService,
        db_session: AsyncSession,
        tenant_id: str,
        test_models: list
    ):
        """Test successful fallback chain creation."""
        primary_model = test_models[0]
        fallback_models = [test_models[1], test_models[2]]
        fallback_ids = [m.id for m in fallback_models]

        chain = await fallback_service.create_fallback_chain(
            tenant_id=tenant_id,
            model_id=primary_model.id,
            fallback_model_ids=fallback_ids,
        )

        assert chain is not None
        assert chain.model_id == primary_model.id
        assert len(chain.fallback_chain) == 2

    async def test_create_fallback_chain_circular_prevention(
        self,
        fallback_service: FallbackService,
        db_session: AsyncSession,
        tenant_id: str,
        test_models: list
    ):
        """Test circular fallback detection prevents self-reference."""
        model = test_models[0]

        with pytest.raises(ValueError, match="[Cc]ircular"):
            await fallback_service.create_fallback_chain(
                tenant_id=tenant_id,
                model_id=model.id,
                fallback_model_ids=[model.id],  # Self-reference
            )

    async def test_create_fallback_chain_disabled_model_fails(
        self,
        fallback_service: FallbackService,
        db_session: AsyncSession,
        tenant_id: str,
        test_models: list
    ):
        """Test that disabled models cannot be added to fallback chain."""
        primary_model = test_models[0]
        disabled_model = test_models[3]  # Disabled model

        with pytest.raises(ValueError):
            await fallback_service.create_fallback_chain(
                tenant_id=tenant_id,
                model_id=primary_model.id,
                fallback_model_ids=[disabled_model.id],
            )

    async def test_get_fallback_chain_returns_ordered_list(
        self,
        fallback_service: FallbackService,
        db_session: AsyncSession,
        tenant_id: str,
        test_models: list
    ):
        """Test that fallback chain is returned in order."""
        primary_model = test_models[0]
        fallback_ids = [test_models[1].id, test_models[2].id]

        # Create chain
        await fallback_service.create_fallback_chain(
            tenant_id=tenant_id,
            model_id=primary_model.id,
            fallback_model_ids=fallback_ids,
        )

        # Retrieve chain
        chain = await fallback_service.get_fallback_chain(
            tenant_id=tenant_id,
            model_id=primary_model.id,
        )

        assert chain is not None
        assert len(chain) == 2
        # Verify order
        assert chain[0]["model_id"] == fallback_ids[0]
        assert chain[1]["model_id"] == fallback_ids[1]

    async def test_get_nonexistent_chain_returns_none(
        self,
        fallback_service: FallbackService,
        tenant_id: str,
    ):
        """Test that non-existent chain returns None."""
        chain = await fallback_service.get_fallback_chain(
            tenant_id=tenant_id,
            model_id=99999,
        )
        assert chain is None or chain == []

    async def test_update_fallback_chain_replaces_chain(
        self,
        fallback_service: FallbackService,
        db_session: AsyncSession,
        tenant_id: str,
        test_models: list
    ):
        """Test that updating chain replaces existing fallbacks."""
        primary_model = test_models[0]
        first_fallback = test_models[1]
        second_fallback = test_models[2]

        # Create initial chain
        await fallback_service.create_fallback_chain(
            tenant_id=tenant_id,
            model_id=primary_model.id,
            fallback_model_ids=[first_fallback.id],
        )

        # Update chain
        await fallback_service.create_fallback_chain(
            tenant_id=tenant_id,
            model_id=primary_model.id,
            fallback_model_ids=[second_fallback.id],  # Replace with different model
        )

        # Verify new chain
        chain = await fallback_service.get_fallback_chain(
            tenant_id=tenant_id,
            model_id=primary_model.id,
        )

        assert len(chain) == 1
        assert chain[0]["model_id"] == second_fallback.id

    async def test_delete_fallback_chain_removes_all(
        self,
        fallback_service: FallbackService,
        db_session: AsyncSession,
        tenant_id: str,
        test_models: list
    ):
        """Test that deleting chain removes all fallback entries."""
        primary_model = test_models[0]
        fallback_ids = [test_models[1].id, test_models[2].id]

        # Create chain
        await fallback_service.create_fallback_chain(
            tenant_id=tenant_id,
            model_id=primary_model.id,
            fallback_model_ids=fallback_ids,
        )

        # Delete chain
        await fallback_service.delete_fallback_chain(
            tenant_id=tenant_id,
            model_id=primary_model.id,
        )

        # Verify chain is deleted
        chain = await fallback_service.get_fallback_chain(
            tenant_id=tenant_id,
            model_id=primary_model.id,
        )

        assert chain is None or chain == []

    async def test_list_all_fallback_chains(
        self,
        fallback_service: FallbackService,
        db_session: AsyncSession,
        tenant_id: str,
        test_models: list
    ):
        """Test listing all fallback chains."""
        primary_model1 = test_models[0]
        primary_model2 = test_models[1]
        fallback_id = test_models[2].id

        # Create two chains
        await fallback_service.create_fallback_chain(
            tenant_id=tenant_id,
            model_id=primary_model1.id,
            fallback_model_ids=[fallback_id],
        )

        await fallback_service.create_fallback_chain(
            tenant_id=tenant_id,
            model_id=primary_model2.id,
            fallback_model_ids=[fallback_id],
        )

        # List all chains
        chains = await fallback_service.list_all_fallback_chains(tenant_id=tenant_id)

        assert len(chains) >= 2


# ============================================================================
# Trigger Configuration Tests
# ============================================================================

class TestTriggerConfiguration:
    """Test fallback trigger configuration and retrieval."""

    async def test_configure_triggers_success(
        self,
        fallback_service: FallbackService,
        tenant_id: str,
    ):
        """Test successful trigger configuration."""
        triggers = [
            FallbackTriggerConfig(
                trigger_type="RateLimitError",
                retry_count=3,
                backoff_factor=2.0,
                enabled=True,
            ),
            FallbackTriggerConfig(
                trigger_type="TimeoutError",
                retry_count=2,
                backoff_factor=1.5,
                enabled=True,
            ),
        ]

        result = await fallback_service.configure_triggers(
            tenant_id=tenant_id,
            trigger_configs=triggers,
        )

        assert result is not None

    async def test_configure_triggers_invalid_retry_count(
        self,
        fallback_service: FallbackService,
        tenant_id: str,
    ):
        """Test trigger configuration rejects invalid retry counts."""
        triggers = [
            FallbackTriggerConfig(
                trigger_type="RateLimitError",
                retry_count=11,  # Max is 10
                backoff_factor=2.0,
                enabled=True,
            )
        ]

        with pytest.raises(ValueError):
            await fallback_service.configure_triggers(
                tenant_id=tenant_id,
                trigger_configs=triggers,
            )

    async def test_configure_triggers_invalid_backoff(
        self,
        fallback_service: FallbackService,
        tenant_id: str,
    ):
        """Test trigger configuration rejects invalid backoff factors."""
        triggers = [
            FallbackTriggerConfig(
                trigger_type="RateLimitError",
                retry_count=3,
                backoff_factor=6.0,  # Max is 5.0
                enabled=True,
            )
        ]

        with pytest.raises(ValueError):
            await fallback_service.configure_triggers(
                tenant_id=tenant_id,
                trigger_configs=triggers,
            )

    async def test_get_trigger_config_returns_settings(
        self,
        fallback_service: FallbackService,
        tenant_id: str,
    ):
        """Test retrieving configured trigger settings."""
        triggers = [
            FallbackTriggerConfig(
                trigger_type="RateLimitError",
                retry_count=3,
                backoff_factor=2.0,
                enabled=True,
            )
        ]

        await fallback_service.configure_triggers(
            tenant_id=tenant_id,
            trigger_configs=triggers,
        )

        config = await fallback_service.get_trigger_config(
            tenant_id=tenant_id,
            trigger_type="RateLimitError",
        )

        assert config is not None
        assert config.get("retry_count") == 3
        assert config.get("backoff_factor") == 2.0

    async def test_get_trigger_config_unconfigured_returns_none(
        self,
        fallback_service: FallbackService,
        tenant_id: str,
    ):
        """Test unconfigured trigger returns None."""
        config = await fallback_service.get_trigger_config(
            tenant_id=tenant_id,
            trigger_type="NonexistentError",
        )

        assert config is None


# ============================================================================
# Metrics Tests
# ============================================================================

class TestMetricsTracking:
    """Test fallback metrics recording and aggregation."""

    async def test_record_fallback_event_success(
        self,
        fallback_service: FallbackService,
        db_session: AsyncSession,
        tenant_id: str,
        test_models: list
    ):
        """Test recording successful fallback event."""
        primary_model = test_models[0]
        fallback_model = test_models[1]

        await fallback_service.record_fallback_event(
            tenant_id=tenant_id,
            model_id=primary_model.id,
            trigger_type="RateLimitError",
            fallback_model_id=fallback_model.id,
            success=True,
        )

        # Verify metric was recorded
        metrics = await fallback_service.get_fallback_metrics(
            tenant_id=tenant_id,
            model_id=primary_model.id,
            days=7,
        )

        assert metrics.total_fallbacks >= 1
        assert metrics.total_success >= 1

    async def test_record_fallback_event_failure(
        self,
        fallback_service: FallbackService,
        db_session: AsyncSession,
        tenant_id: str,
        test_models: list
    ):
        """Test recording failed fallback event."""
        primary_model = test_models[0]
        fallback_model = test_models[1]

        await fallback_service.record_fallback_event(
            tenant_id=tenant_id,
            model_id=primary_model.id,
            trigger_type="TimeoutError",
            fallback_model_id=fallback_model.id,
            success=False,
        )

        # Verify metric was recorded
        metrics = await fallback_service.get_fallback_metrics(
            tenant_id=tenant_id,
            model_id=primary_model.id,
            days=7,
        )

        assert metrics.total_fallbacks >= 1
        assert metrics.total_failure >= 1

    async def test_get_fallback_metrics_calculates_success_rate(
        self,
        fallback_service: FallbackService,
        db_session: AsyncSession,
        tenant_id: str,
        test_models: list
    ):
        """Test metrics calculation includes success rate."""
        primary_model = test_models[0]
        fallback_model = test_models[1]

        # Record 3 successes and 1 failure
        for _ in range(3):
            await fallback_service.record_fallback_event(
                tenant_id=tenant_id,
                model_id=primary_model.id,
                trigger_type="RateLimitError",
                fallback_model_id=fallback_model.id,
                success=True,
            )

        await fallback_service.record_fallback_event(
            tenant_id=tenant_id,
            model_id=primary_model.id,
            trigger_type="RateLimitError",
            fallback_model_id=fallback_model.id,
            success=False,
        )

        metrics = await fallback_service.get_fallback_metrics(
            tenant_id=tenant_id,
            model_id=primary_model.id,
            days=7,
        )

        # Success rate should be 75% (3/4)
        assert metrics.overall_success_rate == pytest.approx(75.0, rel=1)
        assert metrics.total_fallbacks == 4
        assert metrics.total_success == 3
        assert metrics.total_failure == 1

    async def test_get_fallback_metrics_empty_returns_zeros(
        self,
        fallback_service: FallbackService,
        tenant_id: str,
    ):
        """Test empty metrics returns zeros."""
        metrics = await fallback_service.get_fallback_metrics(
            tenant_id=tenant_id,
            model_id=99999,
            days=7,
        )

        assert metrics.total_fallbacks == 0
        assert metrics.overall_success_rate == 0.0
        assert metrics.total_success == 0
        assert metrics.total_failure == 0

    async def test_get_fallback_metrics_date_filtering(
        self,
        fallback_service: FallbackService,
        db_session: AsyncSession,
        tenant_id: str,
        test_models: list
    ):
        """Test metrics filtering by date range."""
        primary_model = test_models[0]
        fallback_model = test_models[1]

        # Record event
        await fallback_service.record_fallback_event(
            tenant_id=tenant_id,
            model_id=primary_model.id,
            trigger_type="RateLimitError",
            fallback_model_id=fallback_model.id,
            success=True,
        )

        # Get metrics for last 1 day
        metrics_1day = await fallback_service.get_fallback_metrics(
            tenant_id=tenant_id,
            model_id=primary_model.id,
            days=1,
        )

        # Get metrics for last 30 days
        metrics_30days = await fallback_service.get_fallback_metrics(
            tenant_id=tenant_id,
            model_id=primary_model.id,
            days=30,
        )

        # Both should include the recent event
        assert metrics_1day.total_fallbacks >= 1
        assert metrics_30days.total_fallbacks >= 1

    async def test_get_metrics_with_model_id_filter(
        self,
        fallback_service: FallbackService,
        db_session: AsyncSession,
        tenant_id: str,
        test_models: list
    ):
        """Test metrics filtering by specific model."""
        model1 = test_models[0]
        model2 = test_models[1]
        fallback_model = test_models[2]

        # Record events for model1
        await fallback_service.record_fallback_event(
            tenant_id=tenant_id,
            model_id=model1.id,
            trigger_type="RateLimitError",
            fallback_model_id=fallback_model.id,
            success=True,
        )

        # Record events for model2
        await fallback_service.record_fallback_event(
            tenant_id=tenant_id,
            model_id=model2.id,
            trigger_type="RateLimitError",
            fallback_model_id=fallback_model.id,
            success=True,
        )

        # Get metrics for model1 only
        metrics = await fallback_service.get_fallback_metrics(
            tenant_id=tenant_id,
            model_id=model1.id,
            days=7,
        )

        assert metrics.total_fallbacks >= 1


# ============================================================================
# Validation Tests
# ============================================================================

class TestFallbackValidation:
    """Test fallback validation logic."""

    async def test_circular_fallback_self_reference(
        self,
        fallback_service: FallbackService,
        tenant_id: str,
    ):
        """Test self-referencing circular fallback detection."""
        with pytest.raises(ValueError):
            await fallback_service._validate_no_circular_fallback(
                model_id=1,
                fallback_model_ids=[1],  # Self-reference
            )

    async def test_circular_fallback_chain(
        self,
        fallback_service: FallbackService,
        tenant_id: str,
    ):
        """Test circular chain detection."""
        with pytest.raises(ValueError, match="[Cc]ircular"):
            await fallback_service._validate_no_circular_fallback(
                model_id=1,
                fallback_model_ids=[2, 1],  # Chain back to original
            )

    async def test_valid_linear_fallback_chain(
        self,
        fallback_service: FallbackService,
        tenant_id: str,
    ):
        """Test valid linear fallback chain passes validation."""
        # Should not raise
        try:
            await fallback_service._validate_no_circular_fallback(
                model_id=1,
                fallback_model_ids=[2, 3, 4],
            )
        except ValueError:
            pytest.fail("Valid fallback chain raised error")

    async def test_validate_model_enabled_status(
        self,
        fallback_service: FallbackService,
        db_session: AsyncSession,
        test_models: list
    ):
        """Test validation checks model enabled status."""
        enabled_model = test_models[0]
        disabled_model = test_models[3]

        # Enabled model should pass
        try:
            await fallback_service._validate_model_enabled(enabled_model.id)
        except ValueError:
            pytest.fail("Enabled model validation failed")

        # Disabled model should fail
        with pytest.raises(ValueError):
            await fallback_service._validate_model_enabled(disabled_model.id)


# ============================================================================
# Edge Cases Tests
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    async def test_empty_fallback_chain_list(
        self,
        fallback_service: FallbackService,
        tenant_id: str,
        test_models: list
    ):
        """Test creating chain with empty fallback list."""
        primary_model = test_models[0]

        chain = await fallback_service.create_fallback_chain(
            tenant_id=tenant_id,
            model_id=primary_model.id,
            fallback_model_ids=[],  # Empty list
        )

        assert chain is not None

    async def test_single_fallback_model(
        self,
        fallback_service: FallbackService,
        db_session: AsyncSession,
        tenant_id: str,
        test_models: list
    ):
        """Test chain with single fallback model."""
        primary_model = test_models[0]
        fallback_model = test_models[1]

        chain = await fallback_service.create_fallback_chain(
            tenant_id=tenant_id,
            model_id=primary_model.id,
            fallback_model_ids=[fallback_model.id],
        )

        assert len(chain.fallback_chain) == 1

    async def test_many_fallback_models(
        self,
        fallback_service: FallbackService,
        db_session: AsyncSession,
        tenant_id: str,
        test_models: list
    ):
        """Test chain with multiple fallback models."""
        primary_model = test_models[0]
        fallback_ids = [test_models[1].id, test_models[2].id]

        chain = await fallback_service.create_fallback_chain(
            tenant_id=tenant_id,
            model_id=primary_model.id,
            fallback_model_ids=fallback_ids,
        )

        assert len(chain.fallback_chain) == 2

    async def test_zero_retry_count_valid(
        self,
        fallback_service: FallbackService,
        tenant_id: str,
    ):
        """Test zero retry count is valid."""
        triggers = [
            FallbackTriggerConfig(
                trigger_type="RateLimitError",
                retry_count=0,  # Zero retries
                backoff_factor=1.0,
                enabled=True,
            )
        ]

        result = await fallback_service.configure_triggers(
            tenant_id=tenant_id,
            trigger_configs=triggers,
        )

        assert result is not None

    async def test_max_retry_count(
        self,
        fallback_service: FallbackService,
        tenant_id: str,
    ):
        """Test maximum retry count is accepted."""
        triggers = [
            FallbackTriggerConfig(
                trigger_type="RateLimitError",
                retry_count=10,  # Max value
                backoff_factor=5.0,  # Max value
                enabled=True,
            )
        ]

        result = await fallback_service.configure_triggers(
            tenant_id=tenant_id,
            trigger_configs=triggers,
        )

        assert result is not None

    async def test_metrics_multiple_trigger_types(
        self,
        fallback_service: FallbackService,
        db_session: AsyncSession,
        tenant_id: str,
        test_models: list
    ):
        """Test metrics aggregation across multiple trigger types."""
        primary_model = test_models[0]
        fallback_model = test_models[1]

        # Record events for different trigger types
        for trigger_type in ["RateLimitError", "TimeoutError", "ConnectionError"]:
            await fallback_service.record_fallback_event(
                tenant_id=tenant_id,
                model_id=primary_model.id,
                trigger_type=trigger_type,
                fallback_model_id=fallback_model.id,
                success=True,
            )

        metrics = await fallback_service.get_fallback_metrics(
            tenant_id=tenant_id,
            model_id=primary_model.id,
            days=7,
        )

        assert metrics.total_fallbacks >= 3
