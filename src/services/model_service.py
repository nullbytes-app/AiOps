"""
Model service for LLM model configuration management.

This module handles CRUD operations for LLM models, including pricing configuration,
enable/disable operations, and bulk model management.
"""

from typing import Optional

from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import LLMModel, LLMProvider
from src.schemas.provider import (
    BulkModelOperation,
    BulkModelOperationResponse,
    LLMModelCreate,
    LLMModelUpdate,
)


class ModelService:
    """
    Service for managing LLM model configuration.

    Handles model CRUD operations, pricing configuration, and bulk enable/disable
    operations for LiteLLM config generation.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize model service.

        Args:
            db: Async database session
        """
        self.db = db

    async def create_model(
        self,
        model_data: LLMModelCreate,
    ) -> LLMModel:
        """
        Create a new LLM model configuration.

        Args:
            model_data: Model creation data

        Returns:
            LLMModel: Created model

        Raises:
            ValueError: If provider not found or model already exists
        """
        # Verify provider exists
        provider = await self.db.get(LLMProvider, model_data.provider_id)
        if not provider:
            raise ValueError(f"Provider {model_data.provider_id} not found")

        # Check for duplicate (provider_id, model_name)
        existing = await self.db.execute(
            select(LLMModel).where(
                and_(
                    LLMModel.provider_id == model_data.provider_id,
                    LLMModel.model_name == model_data.model_name,
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(
                f"Model '{model_data.model_name}' already exists for provider {model_data.provider_id}"
            )

        # Create model
        model = LLMModel(
            provider_id=model_data.provider_id,
            model_name=model_data.model_name,
            display_name=model_data.display_name,
            enabled=model_data.enabled,
            cost_per_input_token=model_data.cost_per_input_token,
            cost_per_output_token=model_data.cost_per_output_token,
            context_window=model_data.context_window,
            capabilities=model_data.capabilities,
        )

        self.db.add(model)
        await self.db.commit()
        await self.db.refresh(model)

        logger.info(
            f"Created model: {model.model_name} (ID: {model.id}, provider: {model.provider_id}, enabled: {model.enabled})"
        )
        return model

    async def get_model(self, model_id: int) -> Optional[LLMModel]:
        """
        Get model by ID.

        Args:
            model_id: Model ID

        Returns:
            Optional[LLMModel]: Model or None if not found
        """
        return await self.db.get(LLMModel, model_id)

    async def list_models_by_provider(
        self,
        provider_id: int,
        enabled_only: bool = False,
    ) -> list[LLMModel]:
        """
        List all models for a specific provider.

        Args:
            provider_id: Provider ID
            enabled_only: Only return enabled models

        Returns:
            list[LLMModel]: List of models for provider
        """
        query = select(LLMModel).where(LLMModel.provider_id == provider_id)

        if enabled_only:
            query = query.where(LLMModel.enabled == True)

        query = query.order_by(LLMModel.model_name)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def sync_models_from_provider(
        self,
        provider_id: int,
        available_models: list[str],
    ) -> dict:
        """
        Sync models from provider API to database.

        Creates new model entries for models that don't exist yet.
        Skips models that already exist in the database.

        Args:
            provider_id: Provider ID to sync models for
            available_models: List of model names from provider API

        Returns:
            dict: Sync results with counts
                {
                    "created": int,
                    "skipped": int,
                    "failed": int,
                }

        Raises:
            ValueError: If provider not found
        """
        # Verify provider exists
        provider = await self.db.get(LLMProvider, provider_id)
        if not provider:
            raise ValueError(f"Provider {provider_id} not found")

        # Get existing model names for this provider
        existing_models = await self.list_models_by_provider(
            provider_id=provider_id,
            enabled_only=False,
        )
        existing_model_names = {m.model_name for m in existing_models}

        created_count = 0
        skipped_count = 0
        failed_count = 0

        for model_name in available_models:
            try:
                # Skip if model already exists
                if model_name in existing_model_names:
                    skipped_count += 1
                    continue

                # Create new model entry (disabled by default)
                model_data = LLMModelCreate(
                    provider_id=provider_id,
                    model_name=model_name,
                    display_name=model_name,
                    enabled=False,  # Default to disabled, admin must enable
                    cost_per_input_token=None,
                    cost_per_output_token=None,
                    context_window=None,
                    capabilities=None,
                )
                await self.create_model(model_data)
                created_count += 1

            except Exception as e:
                logger.warning(f"Failed to sync model {model_name}: {str(e)}")
                failed_count += 1

        await self.db.commit()

        logger.info(
            f"Synced models for provider {provider_id}: "
            f"created={created_count}, skipped={skipped_count}, failed={failed_count}"
        )

        return {
            "created": created_count,
            "skipped": skipped_count,
            "failed": failed_count,
        }

    async def update_model(
        self,
        model_id: int,
        model_data: LLMModelUpdate,
    ) -> Optional[LLMModel]:
        """
        Update model configuration.

        Args:
            model_id: Model ID to update
            model_data: Update data (partial)

        Returns:
            Optional[LLMModel]: Updated model or None if not found
        """
        model = await self.get_model(model_id)
        if not model:
            return None

        # Update fields
        update_data = model_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(model, key):
                setattr(model, key, value)

        await self.db.commit()
        await self.db.refresh(model)

        logger.info(f"Updated model {model_id}: {model.model_name}")
        return model

    async def toggle_model(self, model_id: int) -> Optional[LLMModel]:
        """
        Toggle model enabled status.

        Args:
            model_id: Model ID to toggle

        Returns:
            Optional[LLMModel]: Updated model or None if not found
        """
        model = await self.get_model(model_id)
        if not model:
            return None

        model.enabled = not model.enabled
        await self.db.commit()
        await self.db.refresh(model)

        logger.info(f"Toggled model {model_id}: {model.model_name} (enabled={model.enabled})")
        return model

    async def delete_model(self, model_id: int) -> bool:
        """
        Soft delete model (sets enabled=False).

        Args:
            model_id: Model ID to delete

        Returns:
            bool: True if deleted, False if not found
        """
        model = await self.get_model(model_id)
        if not model:
            return False

        model.enabled = False
        await self.db.commit()

        logger.info(f"Soft deleted model {model_id}: {model.model_name}")
        return True

    async def bulk_enable_models(
        self,
        bulk_data: BulkModelOperation,
    ) -> BulkModelOperationResponse:
        """
        Enable multiple models at once.

        Args:
            bulk_data: Bulk operation data with model IDs

        Returns:
            BulkModelOperationResponse: Operation results
        """
        updated_count = 0
        failed_ids = []

        for model_id in bulk_data.model_ids:
            try:
                model = await self.get_model(model_id)
                if model:
                    model.enabled = True
                    updated_count += 1
                else:
                    failed_ids.append(model_id)
            except Exception as e:
                logger.error(f"Failed to enable model {model_id}: {e}")
                failed_ids.append(model_id)

        await self.db.commit()

        logger.info(f"Bulk enabled {updated_count} models (failed: {len(failed_ids)})")

        return BulkModelOperationResponse(
            success=len(failed_ids) == 0,
            updated_count=updated_count,
            failed_ids=failed_ids,
        )

    async def bulk_disable_models(
        self,
        bulk_data: BulkModelOperation,
    ) -> BulkModelOperationResponse:
        """
        Disable multiple models at once.

        Args:
            bulk_data: Bulk operation data with model IDs

        Returns:
            BulkModelOperationResponse: Operation results
        """
        updated_count = 0
        failed_ids = []

        for model_id in bulk_data.model_ids:
            try:
                model = await self.get_model(model_id)
                if model:
                    model.enabled = False
                    updated_count += 1
                else:
                    failed_ids.append(model_id)
            except Exception as e:
                logger.error(f"Failed to disable model {model_id}: {e}")
                failed_ids.append(model_id)

        await self.db.commit()

        logger.info(f"Bulk disabled {updated_count} models (failed: {len(failed_ids)})")

        return BulkModelOperationResponse(
            success=len(failed_ids) == 0,
            updated_count=updated_count,
            failed_ids=failed_ids,
        )
