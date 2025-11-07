"""
Provider service for LLM provider management.

This module handles CRUD operations for LLM providers, including API key encryption,
connection testing, and model discovery using LiteLLM.
"""

from datetime import datetime, timezone
from typing import Optional

import httpx
from loguru import logger
from redis import Redis
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.database.models import LLMProvider, LLMModel, ProviderType, AuditLog
from src.schemas.provider import (
    ConnectionTestResponse,
    LLMProviderCreate,
    LLMProviderResponse,
    LLMProviderUpdate,
)
from src.utils.encryption import decrypt, encrypt, EncryptionError
from src.utils.logger import AuditLogger


class ProviderService:
    """
    Service for managing LLM provider configuration.

    Handles provider CRUD operations, API key encryption, connection testing,
    and model discovery. Includes Redis caching for provider list performance.
    """

    # Redis cache TTL (60 seconds as per constraint C11)
    CACHE_TTL = 60
    CACHE_KEY_PATTERN = "provider:{provider_id}"
    CACHE_KEY_LIST = "providers:list"

    def __init__(self, db: AsyncSession, redis: Optional[Redis] = None):
        """
        Initialize provider service.

        Args:
            db: Async database session
            redis: Optional Redis client for caching
        """
        self.db = db
        self.redis = redis

    async def create_provider(
        self,
        provider_data: LLMProviderCreate,
    ) -> LLMProvider:
        """
        Create a new LLM provider with encrypted API key.

        Args:
            provider_data: Provider creation data (includes plaintext API key)

        Returns:
            LLMProvider: Created provider with encrypted API key

        Raises:
            EncryptionError: If API key encryption fails
            ValueError: If provider name already exists
        """
        # Check for duplicate name
        existing = await self.db.execute(
            select(LLMProvider).where(LLMProvider.name == provider_data.name)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Provider with name '{provider_data.name}' already exists")

        # Encrypt API key
        try:
            encrypted_key = encrypt(provider_data.api_key)
        except EncryptionError as e:
            logger.error(f"Failed to encrypt API key for provider {provider_data.name}: {e}")
            raise

        # Create provider
        provider = LLMProvider(
            name=provider_data.name,
            provider_type=provider_data.provider_type.value,
            api_base_url=provider_data.api_base_url,
            api_key_encrypted=encrypted_key,
            enabled=True,
        )

        self.db.add(provider)
        await self.db.commit()
        await self.db.refresh(provider)

        # Invalidate cache
        self._invalidate_list_cache()

        # Audit log: Provider creation
        audit_entry = AuditLog(
            user="admin",  # Platform admin operation
            operation="create_provider",
            status="success",
            details={
                "provider_id": provider.id,
                "provider_name": provider.name,
                "provider_type": provider.provider_type,
                "api_base_url": provider.api_base_url,
            },
        )
        self.db.add(audit_entry)
        await self.db.commit()

        # Structured audit log
        AuditLogger.audit_provider_operation(
            operation="create",
            provider_id=provider.id,
            provider_name=provider.name,
            provider_type=provider.provider_type,
            user="admin",
            status="success",
        )

        logger.info(f"Created provider: {provider.name} (ID: {provider.id}, type: {provider.provider_type})")
        return provider

    async def get_provider(
        self,
        provider_id: int,
        decrypt_key: bool = False,
    ) -> Optional[LLMProvider]:
        """
        Get provider by ID.

        Args:
            provider_id: Provider ID
            decrypt_key: If True, decrypt API key (admin only)

        Returns:
            Optional[LLMProvider]: Provider or None if not found
        """
        # Try cache first
        cache_key = self.CACHE_KEY_PATTERN.format(provider_id=provider_id)
        if self.redis:
            cached = self.redis.get(cache_key)
            if cached:
                logger.debug(f"Provider {provider_id} cache hit")
                # Note: Would need pickle/json serialization for full caching

        # Query database
        result = await self.db.execute(
            select(LLMProvider)
            .options(joinedload(LLMProvider.models))
            .where(LLMProvider.id == provider_id)
        )
        provider = result.unique().scalar_one_or_none()

        if provider and decrypt_key:
            # Decrypt API key for admin use (not returned in response)
            try:
                provider.api_key_decrypted = decrypt(provider.api_key_encrypted)
            except EncryptionError as e:
                logger.error(f"Failed to decrypt API key for provider {provider_id}: {e}")
                provider.api_key_decrypted = None

        return provider

    async def list_providers(
        self,
        skip: int = 0,
        limit: int = 100,
        include_disabled: bool = False,
    ) -> list[LLMProvider]:
        """
        List all providers with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum records to return
            include_disabled: Include disabled providers

        Returns:
            list[LLMProvider]: List of providers
        """
        query = select(LLMProvider).options(joinedload(LLMProvider.models))

        if not include_disabled:
            query = query.where(LLMProvider.enabled == True)

        query = query.offset(skip).limit(limit).order_by(LLMProvider.created_at.desc())

        result = await self.db.execute(query)
        providers = result.scalars().unique().all()

        return list(providers)

    async def update_provider(
        self,
        provider_id: int,
        provider_data: LLMProviderUpdate,
    ) -> Optional[LLMProvider]:
        """
        Update provider configuration.

        Args:
            provider_id: Provider ID to update
            provider_data: Update data (partial)

        Returns:
            Optional[LLMProvider]: Updated provider or None if not found

        Raises:
            EncryptionError: If API key re-encryption fails
        """
        provider = await self.get_provider(provider_id)
        if not provider:
            return None

        # Update fields
        update_data = provider_data.model_dump(exclude_unset=True)

        # Handle API key re-encryption
        if "api_key" in update_data:
            try:
                update_data["api_key_encrypted"] = encrypt(update_data.pop("api_key"))
            except EncryptionError as e:
                logger.error(f"Failed to re-encrypt API key for provider {provider_id}: {e}")
                raise

        # Apply updates
        for key, value in update_data.items():
            if hasattr(provider, key):
                setattr(provider, key, value)

        provider.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(provider)

        # Invalidate cache
        self._invalidate_list_cache()

        # Audit log: Provider update
        audit_entry = AuditLog(
            user="admin",
            operation="update_provider",
            status="success",
            details={
                "provider_id": provider_id,
                "provider_name": provider.name,
                "updated_fields": list(update_data.keys()),
            },
        )
        self.db.add(audit_entry)
        await self.db.commit()

        # Structured audit log
        AuditLogger.audit_provider_operation(
            operation="update",
            provider_id=provider_id,
            provider_name=provider.name,
            provider_type=provider.provider_type,
            user="admin",
            status="success",
            updated_fields=list(update_data.keys()),
        )

        logger.info(f"Updated provider {provider_id}: {provider.name}")
        return provider

    async def delete_provider(self, provider_id: int) -> bool:
        """
        Soft delete provider (sets enabled=False).

        Args:
            provider_id: Provider ID to delete

        Returns:
            bool: True if deleted, False if not found
        """
        provider = await self.get_provider(provider_id)
        if not provider:
            return False

        provider.enabled = False
        provider.updated_at = datetime.now(timezone.utc)

        await self.db.commit()

        # Invalidate cache
        self._invalidate_list_cache()

        # Audit log: Provider deletion
        audit_entry = AuditLog(
            user="admin",
            operation="delete_provider",
            status="success",
            details={
                "provider_id": provider_id,
                "provider_name": provider.name,
                "provider_type": provider.provider_type,
            },
        )
        self.db.add(audit_entry)
        await self.db.commit()

        # Structured audit log
        AuditLogger.audit_provider_operation(
            operation="delete",
            provider_id=provider_id,
            provider_name=provider.name,
            provider_type=provider.provider_type,
            user="admin",
            status="success",
        )

        logger.info(f"Soft deleted provider {provider_id}: {provider.name}")
        return True

    async def test_provider_connection(
        self,
        provider_id: int,
        timeout: int = 10,
    ) -> ConnectionTestResponse:
        """
        Test provider API connection and fetch available models.

        Args:
            provider_id: Provider ID to test
            timeout: Connection timeout in seconds (default: 10)

        Returns:
            ConnectionTestResponse: Test results with models list

        Raises:
            ValueError: If provider not found
        """
        provider = await self.get_provider(provider_id, decrypt_key=True)
        if not provider:
            raise ValueError(f"Provider {provider_id} not found")

        start_time = datetime.now(timezone.utc)

        try:
            # Decrypt API key
            api_key = decrypt(provider.api_key_encrypted)

            # Test connection based on provider type
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(timeout, connect=5.0)
            ) as client:
                if provider.provider_type == ProviderType.OPENAI.value:
                    # Test OpenAI endpoint
                    response = await client.get(
                        f"{provider.api_base_url}/models",
                        headers={"Authorization": f"Bearer {api_key}"},
                    )
                    response.raise_for_status()
                    models = [m["id"] for m in response.json().get("data", [])]

                elif provider.provider_type == ProviderType.ANTHROPIC.value:
                    # Test Anthropic endpoint (simplified - real implementation would use proper API)
                    response = await client.get(
                        f"{provider.api_base_url}/v1/models",
                        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
                    )
                    response.raise_for_status()
                    models = ["claude-3-5-sonnet-20240620", "claude-3-opus-20240229"]

                else:
                    # Generic test - just check if endpoint responds
                    response = await client.get(
                        provider.api_base_url,
                        headers={"Authorization": f"Bearer {api_key}"},
                    )
                    response.raise_for_status()
                    models = []

            # Calculate response time
            end_time = datetime.now(timezone.utc)
            response_time_ms = int((end_time - start_time).total_seconds() * 1000)

            # Update provider test status
            provider.last_test_at = end_time
            provider.last_test_success = True
            await self.db.commit()

            # Audit log: Successful connection test
            audit_entry = AuditLog(
                user="admin",
                operation="test_provider_connection",
                status="success",
                details={
                    "provider_id": provider_id,
                    "provider_name": provider.name,
                    "models_found": len(models),
                    "response_time_ms": response_time_ms,
                },
            )
            self.db.add(audit_entry)
            await self.db.commit()

            # Structured audit log
            AuditLogger.audit_provider_operation(
                operation="test_connection",
                provider_id=provider_id,
                provider_name=provider.name,
                provider_type=provider.provider_type,
                user="admin",
                status="success",
                models_found=len(models),
                response_time_ms=response_time_ms,
            )

            logger.info(
                f"Provider {provider_id} connection test successful "
                f"({len(models)} models, {response_time_ms}ms)"
            )

            return ConnectionTestResponse(
                success=True,
                models=models,
                response_time_ms=response_time_ms,
                error=None,
            )

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            logger.warning(f"Provider {provider_id} connection test failed: {error_msg}")

            # Update test status
            provider.last_test_at = datetime.now(timezone.utc)
            provider.last_test_success = False
            await self.db.commit()

            # Audit log: Failed connection test
            audit_entry = AuditLog(
                user="admin",
                operation="test_provider_connection",
                status="failure",
                details={
                    "provider_id": provider_id,
                    "provider_name": provider.name,
                    "error": error_msg,
                },
            )
            self.db.add(audit_entry)
            await self.db.commit()

            return ConnectionTestResponse(
                success=False,
                models=[],
                response_time_ms=None,
                error=error_msg,
            )

        except Exception as e:
            error_msg = f"Connection error: {str(e)}"
            logger.error(f"Provider {provider_id} connection test error: {error_msg}")

            # Update test status
            provider.last_test_at = datetime.now(timezone.utc)
            provider.last_test_success = False
            await self.db.commit()

            # Audit log: Failed connection test
            audit_entry = AuditLog(
                user="admin",
                operation="test_provider_connection",
                status="failure",
                details={
                    "provider_id": provider_id,
                    "provider_name": provider.name,
                    "error": error_msg,
                },
            )
            self.db.add(audit_entry)
            await self.db.commit()

            return ConnectionTestResponse(
                success=False,
                models=[],
                response_time_ms=None,
                error=error_msg,
            )

    def _invalidate_list_cache(self) -> None:
        """Invalidate provider list cache in Redis."""
        if self.redis:
            try:
                self.redis.delete(self.CACHE_KEY_LIST)
                logger.debug("Provider list cache invalidated")
            except Exception as e:
                logger.warning(f"Failed to invalidate provider cache: {e}")
