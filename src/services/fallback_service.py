"""Service for managing LLM fallback chain configuration and metrics."""

import logging
from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from src.database.models import (
    FallbackChain,
    FallbackTrigger,
    FallbackMetric,
    LLMModel,
)
from src.schemas.fallback import (
    FallbackChainCreate,
    FallbackChainUpdate,
    FallbackChainResponse,
    FallbackTriggerConfig,
    FallbackMetricResponse,
    FallbackMetricsAggregateResponse,
)

logger = logging.getLogger(__name__)


class FallbackService:
    """Service for fallback chain configuration and metrics tracking."""

    # Default trigger configuration values
    DEFAULT_TRIGGER_CONFIG = {
        "RateLimitError": {"retry_count": 3, "backoff_factor": 2.0},
        "TimeoutError": {"retry_count": 3, "backoff_factor": 2.0},
        "InternalServerError": {"retry_count": 3, "backoff_factor": 2.0},
        "ConnectionError": {"retry_count": 3, "backoff_factor": 2.0},
        "ContentPolicyViolationError": {"retry_count": 4, "backoff_factor": 1.5},
    }

    def __init__(self, db: AsyncSession):
        """
        Initialize FallbackService.

        Args:
            db: AsyncSession database connection

        Raises:
            ValueError: If db is None
        """
        if not db:
            raise ValueError("Database session cannot be None")
        self.db = db

    async def create_fallback_chain(
        self,
        tenant_id: UUID,
        model_id: int,
        fallback_model_ids: List[int],
    ) -> FallbackChainResponse:
        """
        Create a new fallback chain for a model.

        Args:
            tenant_id: Tenant ID for multi-tenancy
            model_id: Primary model ID
            fallback_model_ids: List of fallback model IDs in order

        Returns:
            FallbackChainResponse: Created fallback chain

        Raises:
            ValueError: If model not found, disabled, or circular fallback detected
        """
        # Validate primary model exists and is enabled
        primary_model = await self._get_enabled_model(model_id)
        if not primary_model:
            raise ValueError(f"Primary model {model_id} not found or disabled")

        # Validate no circular fallbacks
        await self._validate_no_circular_fallback(model_id, fallback_model_ids)

        # Delete existing fallback chain for this model
        stmt = select(FallbackChain).where(FallbackChain.model_id == model_id)
        result = await self.db.execute(stmt)
        existing_chains = result.scalars().all()
        for chain in existing_chains:
            await self.db.delete(chain)

        # Create new fallback chains
        chains = []
        for order, fallback_model_id in enumerate(fallback_model_ids):
            # Validate fallback model exists and is enabled
            fallback_model = await self._get_enabled_model(fallback_model_id)
            if not fallback_model:
                raise ValueError(
                    f"Fallback model {fallback_model_id} not found or disabled"
                )

            chain = FallbackChain(
                model_id=model_id,
                fallback_order=order,
                fallback_model_id=fallback_model_id,
                enabled=True,
            )
            chains.append(chain)
            self.db.add(chain)

        await self.db.commit()

        # Return first chain for response (represent full chain)
        if chains:
            await self.db.refresh(chains[0])
            return FallbackChainResponse.from_attributes(chains[0])

        raise ValueError("Failed to create fallback chain")

    async def update_fallback_chain(
        self,
        tenant_id: UUID,
        model_id: int,
        fallback_model_ids: List[int],
    ) -> None:
        """
        Update fallback chain for a model.

        Args:
            tenant_id: Tenant ID for multi-tenancy
            model_id: Primary model ID
            fallback_model_ids: Updated list of fallback model IDs

        Raises:
            ValueError: If model not found or circular fallback detected
        """
        # Validate primary model exists
        primary_model = await self._get_enabled_model(model_id)
        if not primary_model:
            raise ValueError(f"Primary model {model_id} not found or disabled")

        # Validate no circular fallbacks
        await self._validate_no_circular_fallback(model_id, fallback_model_ids)

        # Delete existing chains
        stmt = select(FallbackChain).where(FallbackChain.model_id == model_id)
        result = await self.db.execute(stmt)
        existing_chains = result.scalars().all()
        for chain in existing_chains:
            await self.db.delete(chain)

        # Create new chains
        for order, fallback_model_id in enumerate(fallback_model_ids):
            fallback_model = await self._get_enabled_model(fallback_model_id)
            if not fallback_model:
                raise ValueError(
                    f"Fallback model {fallback_model_id} not found or disabled"
                )

            chain = FallbackChain(
                model_id=model_id,
                fallback_order=order,
                fallback_model_id=fallback_model_id,
                enabled=True,
            )
            self.db.add(chain)

        await self.db.commit()
        logger.info(f"Updated fallback chain for model {model_id}")

    async def delete_fallback_chain(
        self,
        tenant_id: UUID,
        model_id: int,
    ) -> None:
        """
        Delete fallback chain for a model.

        Args:
            tenant_id: Tenant ID for multi-tenancy
            model_id: Primary model ID
        """
        stmt = select(FallbackChain).where(FallbackChain.model_id == model_id)
        result = await self.db.execute(stmt)
        chains = result.scalars().all()

        for chain in chains:
            await self.db.delete(chain)

        await self.db.commit()
        logger.info(f"Deleted fallback chain for model {model_id}")

    async def get_fallback_chain(
        self, tenant_id: UUID, model_id: int
    ) -> Optional[List[Dict]]:
        """
        Get fallback chain for a model.

        Args:
            tenant_id: Tenant ID for multi-tenancy
            model_id: Primary model ID

        Returns:
            List of fallback models in order, or None if no chain exists
        """
        stmt = (
            select(FallbackChain)
            .where(FallbackChain.model_id == model_id)
            .order_by(FallbackChain.fallback_order)
        )
        result = await self.db.execute(stmt)
        chains = result.scalars().all()

        if not chains:
            return None

        return [
            {
                "order": chain.fallback_order,
                "model_id": chain.fallback_model_id,
                "model_name": chain.fallback_model.model_name,
                "enabled": chain.enabled,
            }
            for chain in chains
        ]

    async def list_all_fallback_chains(
        self, tenant_id: UUID
    ) -> List[Dict]:
        """
        List all fallback chains.

        Args:
            tenant_id: Tenant ID for multi-tenancy

        Returns:
            List of all fallback chains with model details
        """
        stmt = (
            select(FallbackChain)
            .join(LLMModel, FallbackChain.model_id == LLMModel.id)
            .order_by(FallbackChain.model_id, FallbackChain.fallback_order)
        )
        result = await self.db.execute(stmt)
        chains = result.scalars().all()

        # Group by primary model
        chains_by_model = {}
        for chain in chains:
            model_id = chain.model_id
            if model_id not in chains_by_model:
                chains_by_model[model_id] = {
                    "model_id": model_id,
                    "model_name": chain.model.model_name,
                    "fallback_chain": [],
                }
            chains_by_model[model_id]["fallback_chain"].append(
                {
                    "order": chain.fallback_order,
                    "model_id": chain.fallback_model_id,
                    "model_name": chain.fallback_model.model_name,
                    "enabled": chain.enabled,
                }
            )

        return list(chains_by_model.values())

    async def configure_triggers(
        self,
        tenant_id: UUID,
        trigger_configs: List[FallbackTriggerConfig],
    ) -> None:
        """
        Configure fallback triggers for error types.

        Args:
            tenant_id: Tenant ID for multi-tenancy
            trigger_configs: List of trigger configurations
        """
        for config in trigger_configs:
            # Check if trigger exists
            stmt = select(FallbackTrigger).where(
                FallbackTrigger.trigger_type == config.trigger_type
            )
            result = await self.db.execute(stmt)
            trigger = result.scalars().first()

            if trigger:
                # Update existing
                trigger.retry_count = config.retry_count
                trigger.backoff_factor = config.backoff_factor
                trigger.enabled = config.enabled
            else:
                # Create new
                trigger = FallbackTrigger(
                    trigger_type=config.trigger_type,
                    retry_count=config.retry_count,
                    backoff_factor=config.backoff_factor,
                    enabled=config.enabled,
                )
                self.db.add(trigger)

        await self.db.commit()
        logger.info(f"Configured {len(trigger_configs)} fallback triggers")

    async def get_trigger_config(
        self,
        tenant_id: UUID,
        trigger_type: str,
    ) -> Optional[Dict]:
        """
        Get trigger configuration for error type.

        Args:
            tenant_id: Tenant ID for multi-tenancy
            trigger_type: Error type

        Returns:
            Trigger configuration or None if not found
        """
        stmt = select(FallbackTrigger).where(
            FallbackTrigger.trigger_type == trigger_type
        )
        result = await self.db.execute(stmt)
        trigger = result.scalars().first()

        if not trigger:
            # Return default config if not found
            if trigger_type in self.DEFAULT_TRIGGER_CONFIG:
                return {
                    "trigger_type": trigger_type,
                    **self.DEFAULT_TRIGGER_CONFIG[trigger_type],
                    "enabled": True,
                }
            return None

        return {
            "id": trigger.id,
            "trigger_type": trigger.trigger_type,
            "retry_count": trigger.retry_count,
            "backoff_factor": trigger.backoff_factor,
            "enabled": trigger.enabled,
        }

    async def record_fallback_event(
        self,
        tenant_id: UUID,
        model_id: int,
        trigger_type: str,
        fallback_model_id: Optional[int],
        success: bool,
    ) -> None:
        """
        Record a fallback event for metrics tracking.

        Args:
            tenant_id: Tenant ID for multi-tenancy
            model_id: Model ID that had fallback
            trigger_type: Error type that triggered fallback
            fallback_model_id: Fallback model used
            success: Whether fallback was successful
        """
        stmt = select(FallbackMetric).where(
            and_(
                FallbackMetric.model_id == model_id,
                FallbackMetric.trigger_type == trigger_type,
                FallbackMetric.fallback_model_id == fallback_model_id,
            )
        )
        result = await self.db.execute(stmt)
        metric = result.scalars().first()

        if metric:
            # Update existing metric
            metric.trigger_count += 1
            if success:
                metric.success_count += 1
            else:
                metric.failure_count += 1
            metric.last_triggered_at = datetime.now(timezone.utc)
        else:
            # Create new metric
            metric = FallbackMetric(
                model_id=model_id,
                trigger_type=trigger_type,
                fallback_model_id=fallback_model_id,
                trigger_count=1,
                success_count=1 if success else 0,
                failure_count=0 if success else 1,
                last_triggered_at=datetime.now(timezone.utc),
            )
            self.db.add(metric)

        await self.db.commit()

    async def get_fallback_metrics(
        self,
        tenant_id: UUID,
        model_id: Optional[int] = None,
        days: int = 7,
    ) -> FallbackMetricsAggregateResponse:
        """
        Get aggregated fallback metrics.

        Args:
            tenant_id: Tenant ID for multi-tenancy
            model_id: Optional model ID to filter by
            days: Number of days to include in metrics

        Returns:
            Aggregated fallback metrics
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        stmt = select(FallbackMetric).where(
            FallbackMetric.created_at >= cutoff_date
        )

        if model_id:
            stmt = stmt.where(FallbackMetric.model_id == model_id)

        result = await self.db.execute(stmt)
        metrics = result.scalars().all()

        if not metrics:
            return FallbackMetricsAggregateResponse(
                total_fallbacks=0,
                total_success=0,
                total_failure=0,
                overall_success_rate=0.0,
                metrics_by_model=[],
                metrics_by_trigger=[],
            )

        total_success = sum(m.success_count for m in metrics)
        total_failure = sum(m.failure_count for m in metrics)
        total_fallbacks = total_success + total_failure

        # Calculate success rate
        overall_success_rate = (
            (total_success / total_fallbacks * 100) if total_fallbacks > 0 else 0.0
        )

        # Group metrics by model
        by_model = {}
        for metric in metrics:
            model_key = metric.model_id
            if model_key not in by_model:
                by_model[model_key] = {
                    "model_id": model_key,
                    "total_triggers": 0,
                    "total_success": 0,
                    "total_failure": 0,
                }
            by_model[model_key]["total_triggers"] += metric.trigger_count
            by_model[model_key]["total_success"] += metric.success_count
            by_model[model_key]["total_failure"] += metric.failure_count

        # Group metrics by trigger type
        by_trigger = {}
        for metric in metrics:
            trigger_key = metric.trigger_type
            if trigger_key not in by_trigger:
                by_trigger[trigger_key] = {
                    "trigger_type": trigger_key,
                    "total_triggers": 0,
                    "total_success": 0,
                    "total_failure": 0,
                }
            by_trigger[trigger_key]["total_triggers"] += metric.trigger_count
            by_trigger[trigger_key]["total_success"] += metric.success_count
            by_trigger[trigger_key]["total_failure"] += metric.failure_count

        return FallbackMetricsAggregateResponse(
            total_fallbacks=total_fallbacks,
            total_success=total_success,
            total_failure=total_failure,
            overall_success_rate=overall_success_rate,
            metrics_by_model=list(by_model.values()),
            metrics_by_trigger=list(by_trigger.values()),
        )

    async def _validate_no_circular_fallback(
        self, model_id: int, fallback_model_ids: List[int]
    ) -> None:
        """
        Validate no circular fallbacks exist.

        Args:
            model_id: Primary model ID
            fallback_model_ids: List of fallback model IDs

        Raises:
            ValueError: If circular fallback detected
        """
        if model_id in fallback_model_ids:
            raise ValueError(
                f"Circular fallback detected: model cannot fallback to itself"
            )

        # Check if any fallback model has a chain back to primary
        for fallback_id in fallback_model_ids:
            stmt = select(FallbackChain).where(
                FallbackChain.model_id == fallback_id
            )
            result = await self.db.execute(stmt)
            chains = result.scalars().all()

            for chain in chains:
                if chain.fallback_model_id == model_id:
                    raise ValueError(
                        f"Circular fallback detected: {model_id} -> {fallback_id} -> {model_id}"
                    )

    async def _get_enabled_model(self, model_id: int) -> Optional[LLMModel]:
        """
        Get enabled model by ID.

        Args:
            model_id: Model ID

        Returns:
            LLMModel if exists and enabled, None otherwise
        """
        stmt = select(LLMModel).where(
            and_(
                LLMModel.id == model_id,
                LLMModel.enabled.is_(True),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()
