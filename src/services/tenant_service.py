"""
Tenant configuration service with caching and encryption.

CRUD operations for tenant configs with Redis caching (5min TTL),
transparent encryption/decryption, and async SQLAlchemy support.
"""

import json
from typing import Optional, List
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from redis import asyncio as aioredis
from loguru import logger

from src.database.models import TenantConfig as TenantConfigModel
from src.schemas.tenant import (
    TenantConfigCreate,
    TenantConfigUpdate,
    TenantConfigInternal,
    TenantConfigResponse,
    EnhancementPreferences,
)
from src.utils.encryption import encrypt, decrypt, EncryptionError
from src.utils.exceptions import TenantNotFoundException
from src.plugins.registry import PluginManager, PluginNotFoundError


class TenantService:
    """Service for managing tenant configurations with caching and encryption."""

    # Cache TTL in seconds (5 minutes)
    CACHE_TTL = 300

    # Cache key pattern for tenant configs
    CACHE_KEY_PATTERN = "tenant:config:{tenant_id}"

    def __init__(self, db: AsyncSession, redis: aioredis.Redis):
        """Initialize with database and Redis clients."""
        self.db = db
        self.redis = redis

    async def get_tenant_config(self, tenant_id: str) -> TenantConfigInternal:
        """
        Load tenant configuration with caching and multi-tool support.

        Args:
            tenant_id: Unique tenant identifier

        Returns:
            TenantConfigInternal: Configuration with decrypted credentials

        Raises:
            TenantNotFoundException: If tenant not found
            EncryptionError: If decryption fails
        """
        cache_key = self.CACHE_KEY_PATTERN.format(tenant_id=tenant_id)

        # Check Redis cache
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                logger.info(f"Cache HIT for tenant {tenant_id}")
                return TenantConfigInternal(**json.loads(cached))
        except Exception as e:
            logger.warning(f"Cache read failed for {tenant_id}: {str(e)}")

        # Query database
        logger.info(f"Cache MISS for tenant {tenant_id}")
        stmt = select(TenantConfigModel).where(TenantConfigModel.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        db_config = result.scalar_one_or_none()

        if not db_config:
            raise TenantNotFoundException(f"Tenant '{tenant_id}' not found")

        # Decrypt credentials based on tool_type
        decrypted_webhook_secret = decrypt(db_config.webhook_signing_secret_encrypted)

        config_data = {
            "id": db_config.id,
            "tenant_id": db_config.tenant_id,
            "name": db_config.name,
            "tool_type": db_config.tool_type,
            "webhook_signing_secret": decrypted_webhook_secret,
            "enhancement_preferences": db_config.enhancement_preferences,
            "created_at": db_config.created_at,
            "updated_at": db_config.updated_at,
            "is_active": db_config.is_active,
        }

        if db_config.tool_type == "servicedesk_plus" and db_config.servicedesk_api_key_encrypted:
            config_data["servicedesk_url"] = db_config.servicedesk_url
            config_data["servicedesk_api_key"] = decrypt(db_config.servicedesk_api_key_encrypted)
        elif db_config.tool_type == "jira" and db_config.jira_api_token_encrypted:
            config_data["jira_url"] = db_config.jira_url
            config_data["jira_api_token"] = decrypt(db_config.jira_api_token_encrypted)
            config_data["jira_project_key"] = db_config.jira_project_key

        config = TenantConfigInternal(**config_data)

        # Cache result
        try:
            await self.redis.setex(cache_key, self.CACHE_TTL, config.model_dump_json())
        except Exception as e:
            logger.warning(f"Failed to cache tenant {tenant_id}: {str(e)}")

        return config

    async def create_tenant(self, config: TenantConfigCreate) -> TenantConfigInternal:
        """
        Create new tenant configuration with multi-tool support.

        Validates tool_type against registered plugins before creation.

        Args:
            config: TenantConfigCreate with plaintext credentials

        Returns:
            TenantConfigInternal: Created configuration with decrypted credentials

        Raises:
            PluginNotFoundError: If tool_type not registered
            SQLAlchemy.IntegrityError: If tenant_id already exists
            EncryptionError: If encryption fails
        """
        # Validate tool_type registered
        plugin_manager = PluginManager()
        try:
            plugin_manager.get_plugin(config.tool_type)
        except PluginNotFoundError:
            available = plugin_manager.list_registered_plugins()
            raise ValueError(
                f"Invalid tool_type '{config.tool_type}'. "
                f"Available: {[p['tool_type'] for p in available]}"
            )

        # Encrypt credentials based on tool_type
        encrypted_webhook_secret = encrypt(config.webhook_signing_secret)

        db_config_data = {
            "tenant_id": config.tenant_id,
            "name": config.name,
            "tool_type": config.tool_type,
            "webhook_signing_secret_encrypted": encrypted_webhook_secret,
            "enhancement_preferences": (
                config.enhancement_preferences.model_dump()
                if config.enhancement_preferences
                else {}
            ),
        }

        # Add tool-specific encrypted fields
        if config.tool_type == "servicedesk_plus":
            db_config_data["servicedesk_url"] = str(config.servicedesk_url)
            db_config_data["servicedesk_api_key_encrypted"] = encrypt(config.servicedesk_api_key)
        elif config.tool_type == "jira":
            db_config_data["jira_url"] = str(config.jira_url)
            db_config_data["jira_api_token_encrypted"] = encrypt(config.jira_api_token)
            db_config_data["jira_project_key"] = config.jira_project_key

        db_config = TenantConfigModel(**db_config_data)
        self.db.add(db_config)
        await self.db.flush()
        logger.info(f"Created {config.tool_type} tenant: {config.tenant_id}")

        # Build result with decrypted credentials
        result_data = {
            "id": db_config.id,
            "tenant_id": db_config.tenant_id,
            "name": db_config.name,
            "tool_type": db_config.tool_type,
            "webhook_signing_secret": config.webhook_signing_secret,
            "enhancement_preferences": db_config.enhancement_preferences,
            "created_at": db_config.created_at,
            "updated_at": db_config.updated_at,
            "is_active": db_config.is_active,
        }

        if config.tool_type == "servicedesk_plus":
            result_data["servicedesk_url"] = db_config.servicedesk_url
            result_data["servicedesk_api_key"] = config.servicedesk_api_key
        elif config.tool_type == "jira":
            result_data["jira_url"] = db_config.jira_url
            result_data["jira_api_token"] = config.jira_api_token
            result_data["jira_project_key"] = db_config.jira_project_key

        result = TenantConfigInternal(**result_data)

        cache_key = self.CACHE_KEY_PATTERN.format(tenant_id=config.tenant_id)
        try:
            await self.redis.setex(cache_key, self.CACHE_TTL, result.model_dump_json())
        except Exception as e:
            logger.warning(f"Failed to cache new tenant {config.tenant_id}: {str(e)}")

        return result

    async def update_tenant(
        self, tenant_id: str, updates: TenantConfigUpdate
    ) -> TenantConfigInternal:
        """
        Update tenant configuration.

        Applies partial updates, re-encrypts if credentials changed,
        invalidates cache.

        Args:
            tenant_id: Tenant identifier
            updates: TenantConfigUpdate with fields to change

        Returns:
            TenantConfigInternal: Updated configuration with decrypted credentials

        Raises:
            TenantNotFoundException: If tenant not found
            EncryptionError: If encryption fails
        """
        # Load existing config
        stmt = select(TenantConfigModel).where(TenantConfigModel.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        db_config = result.scalar_one_or_none()

        if not db_config:
            raise TenantNotFoundException(f"Tenant '{tenant_id}' not found")

        # Apply updates
        update_data = updates.model_dump(exclude_unset=True)

        if "name" in update_data:
            db_config.name = update_data["name"]

        if "servicedesk_url" in update_data:
            db_config.servicedesk_url = str(update_data["servicedesk_url"])

        if "servicedesk_api_key" in update_data:
            try:
                db_config.servicedesk_api_key_encrypted = encrypt(
                    update_data["servicedesk_api_key"]
                )
            except EncryptionError as e:
                logger.error(f"Failed to encrypt new API key: {str(e)}")
                raise

        if "webhook_signing_secret" in update_data:
            try:
                db_config.webhook_signing_secret_encrypted = encrypt(
                    update_data["webhook_signing_secret"]
                )
            except EncryptionError as e:
                logger.error(f"Failed to encrypt new webhook secret: {str(e)}")
                raise

        if "enhancement_preferences" in update_data:
            prefs = update_data["enhancement_preferences"]
            db_config.enhancement_preferences = (
                prefs.model_dump() if isinstance(prefs, EnhancementPreferences) else prefs
            )

        # Commit changes
        await self.db.flush()
        logger.info(f"Updated tenant config for {tenant_id}")

        # Invalidate cache
        cache_key = self.CACHE_KEY_PATTERN.format(tenant_id=tenant_id)
        try:
            await self.redis.delete(cache_key)
            logger.info(f"Invalidated cache for tenant {tenant_id}")
        except Exception as e:
            logger.warning(f"Failed to invalidate cache for {tenant_id}: {str(e)}")

        # Decrypt and return updated config
        try:
            decrypted_api_key = decrypt(db_config.servicedesk_api_key_encrypted)
            decrypted_webhook_secret = decrypt(db_config.webhook_signing_secret_encrypted)
        except EncryptionError as e:
            logger.error(f"Failed to decrypt updated credentials for {tenant_id}: {str(e)}")
            raise

        return TenantConfigInternal(
            id=db_config.id,
            tenant_id=db_config.tenant_id,
            name=db_config.name,
            servicedesk_url=db_config.servicedesk_url,
            servicedesk_api_key=decrypted_api_key,
            webhook_signing_secret=decrypted_webhook_secret,
            enhancement_preferences=db_config.enhancement_preferences,
            created_at=db_config.created_at,
            updated_at=db_config.updated_at,
        )

    async def delete_tenant(self, tenant_id: str) -> None:
        """
        Delete tenant configuration (soft delete).

        Sets active flag to False and invalidates cache.

        Args:
            tenant_id: Tenant identifier

        Raises:
            TenantNotFoundException: If tenant not found
        """
        stmt = select(TenantConfigModel).where(TenantConfigModel.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        db_config = result.scalar_one_or_none()

        if not db_config:
            raise TenantNotFoundException(f"Tenant '{tenant_id}' not found")

        # Note: Soft delete would require adding 'active' column to schema
        # For now, perform hard delete as per AC
        self.db.delete(db_config)
        await self.db.flush()
        logger.info(f"Deleted tenant config for {tenant_id}")

        # Invalidate cache
        cache_key = self.CACHE_KEY_PATTERN.format(tenant_id=tenant_id)
        try:
            await self.redis.delete(cache_key)
        except Exception as e:
            logger.warning(f"Failed to invalidate cache for {tenant_id}: {str(e)}")

    async def list_tenants(
        self, skip: int = 0, limit: int = 50
    ) -> tuple[List[TenantConfigResponse], int]:
        """
        List tenant configurations with pagination.

        Returns masked response models (sensitive fields not decrypted).

        Args:
            skip: Number of results to skip (pagination offset)
            limit: Maximum results to return (pagination limit)

        Returns:
            Tuple of (list of TenantConfigResponse, total count)
        """
        from sqlalchemy import func

        # Get total count
        count_stmt = select(func.count(TenantConfigModel.id))
        count_result = await self.db.execute(count_stmt)
        total_count = count_result.scalar() or 0

        # Query paginated results
        stmt = (
            select(TenantConfigModel)
            .order_by(TenantConfigModel.created_at)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        db_configs = result.scalars().all()

        # Convert to response models (masked)
        configs = [
            TenantConfigResponse(
                id=config.id,
                tenant_id=config.tenant_id,
                name=config.name,
                servicedesk_url=config.servicedesk_url,
                servicedesk_api_key_encrypted="***encrypted***",
                webhook_signing_secret_encrypted="***encrypted***",
                enhancement_preferences=config.enhancement_preferences,
                created_at=config.created_at,
                updated_at=config.updated_at,
            )
            for config in db_configs
        ]

        return configs, total_count

    async def invalidate_cache(self, tenant_id: str) -> None:
        """
        Manually invalidate cache for a tenant.

        Args:
            tenant_id: Tenant identifier
        """
        cache_key = self.CACHE_KEY_PATTERN.format(tenant_id=tenant_id)
        try:
            await self.redis.delete(cache_key)
            logger.info(f"Manually invalidated cache for tenant {tenant_id}")
        except Exception as e:
            logger.warning(f"Failed to invalidate cache for {tenant_id}: {str(e)}")

    async def get_webhook_secret(self, tenant_id: str) -> str:
        """
        Retrieve webhook signing secret for a tenant (cached).

        Checks Redis cache first; on cache miss, loads from database.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Decrypted webhook signing secret

        Raises:
            TenantNotFoundException: If tenant not found
            EncryptionError: If decryption fails
        """
        # Try to get from full tenant config (cached)
        config = await self.get_tenant_config(tenant_id)
        return config.webhook_signing_secret

    async def rotate_webhook_secret(self, tenant_id: str) -> str:
        """
        Rotate webhook signing secret for a tenant.

        Generates new secret, updates database, invalidates cache.

        Args:
            tenant_id: Tenant identifier

        Returns:
            New webhook signing secret

        Raises:
            TenantNotFoundException: If tenant not found
        """
        import secrets

        # Generate new secret: 64 characters base64-encoded
        new_secret = secrets.token_urlsafe(48)  # 48 bytes -> 64 chars base64

        # Update tenant config
        updates = TenantConfigUpdate(webhook_signing_secret=new_secret)
        updated_config = await self.update_tenant(tenant_id, updates)

        logger.info(f"Rotated webhook secret for tenant {tenant_id}")
        return updated_config.webhook_signing_secret

    async def get_rate_limits(self, tenant_id: str) -> dict:
        """
        Retrieve rate limit configuration for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Rate limit configuration dict

        Raises:
            TenantNotFoundException: If tenant not found
        """
        config = await self.get_tenant_config(tenant_id)
        rate_limits = (
            config.enhancement_preferences.get("rate_limits")
            if hasattr(config, "enhancement_preferences")
            else None
        )

        if not rate_limits:
            rate_limits = {"webhooks": {"ticket_created": 100, "ticket_resolved": 100}}

        return rate_limits

    async def get_tool_preferences(self, tenant_id: str, tool_type: str) -> dict:
        """
        Retrieve tool-specific preferences from enhancement_preferences JSONB.

        Args:
            tenant_id: Tenant identifier
            tool_type: Tool type (e.g., 'jira', 'servicedesk_plus')

        Returns:
            Tool-specific configuration dict from enhancement_preferences

        Raises:
            TenantNotFoundException: If tenant not found
        """
        config = await self.get_tenant_config(tenant_id)
        if hasattr(config, "enhancement_preferences") and config.enhancement_preferences:
            return config.enhancement_preferences.get("tool_config", {})
        return {}

    async def update_tool_preferences(
        self, tenant_id: str, preferences: dict
    ) -> TenantConfigInternal:
        """
        Update tool-specific preferences in enhancement_preferences JSONB.

        Args:
            tenant_id: Tenant identifier
            preferences: Tool-specific configuration dict

        Returns:
            Updated TenantConfigInternal

        Raises:
            TenantNotFoundException: If tenant not found
        """
        current_config = await self.get_tenant_config(tenant_id)
        current_prefs = current_config.enhancement_preferences or {}
        current_prefs["tool_config"] = preferences

        updates = TenantConfigUpdate(enhancement_preferences=current_prefs)
        updated_config = await self.update_tenant(tenant_id, updates)

        logger.info(f"Updated tool preferences for tenant {tenant_id}")
        return updated_config
