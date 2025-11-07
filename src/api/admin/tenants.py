"""
Admin API endpoints for tenant configuration management.

Provides CRUD operations for managing tenant configurations including
ServiceDesk Plus credentials, webhook secrets, and enhancement preferences.
All endpoints require admin API key authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import timezone

from src.schemas.tenant import (
    TenantConfigCreate,
    TenantConfigUpdate,
    TenantConfigResponse,
    TenantConfigListResponse,
)
from src.services.tenant_service import TenantService
from src.services.llm_service import LLMService, VirtualKeyRotationError
from src.database.session import get_async_session
from src.cache.redis_client import get_redis_client
from src.config import get_settings
from src.utils.logger import logger
from src.utils.exceptions import TenantNotFoundException
from src.utils.encryption import encrypt
from datetime import datetime

router = APIRouter(prefix="/admin/tenants", tags=["admin-tenants"])


async def require_admin(
    x_admin_key: str = Header(None, alias="X-Admin-Key"),
    settings=Depends(get_settings),
) -> None:
    """
    Verify admin API key.

    Args:
        x_admin_key: Admin API key from X-Admin-Key header
        settings: Application settings with admin key

    Raises:
        HTTPException(401): If API key is missing or invalid
    """
    if not x_admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Admin-Key header",
        )

    if x_admin_key != settings.admin_api_key:
        logger.warning(
            "Admin endpoint accessed with invalid API key",
            extra={"endpoint": "admin/tenants"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )


@router.post(
    "",
    response_model=TenantConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new tenant configuration",
    description="Creates a new tenant configuration with ServiceDesk Plus credentials and preferences. "
    "Sensitive fields (api_key, webhook_secret) are encrypted before storage. "
    "Requires admin authentication via X-Admin-Key header.",
)
async def create_tenant(
    config: TenantConfigCreate,
    db: AsyncSession = Depends(get_async_session),
    redis_client=Depends(get_redis_client),
    _: None = Depends(require_admin),
) -> TenantConfigResponse:
    """
    Create a new tenant configuration.

    Args:
        config: Tenant configuration data
        db: Database session
        redis_client: Redis client for caching
        _: Admin authentication (dependency)

    Returns:
        TenantConfigResponse: Created tenant with masked sensitive fields

    Raises:
        HTTPException(409): If tenant_id already exists
    """
    tenant_service = TenantService(db, redis_client)

    try:
        # Create tenant config (encrypts sensitive fields)
        created_config = await tenant_service.create_tenant(config)

        logger.info(
            f"Tenant configuration created: {created_config.tenant_id}",
            extra={"tenant_id": created_config.tenant_id},
        )

        # Return response with masked sensitive fields
        return TenantConfigResponse(
            tenant_id=created_config.tenant_id,
            name=created_config.name,
            servicedesk_url=created_config.servicedesk_url,
            api_key="***encrypted***",
            webhook_secret="***encrypted***",
            enhancement_preferences=created_config.enhancement_preferences,
        )

    except ValueError as e:
        # Duplicate tenant_id or validation error
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tenant creation failed: {str(e)}",
        )
    except Exception as e:
        logger.error(
            f"Failed to create tenant: {str(e)}",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create tenant configuration",
        )


@router.get(
    "",
    response_model=TenantConfigListResponse,
    summary="List all tenant configurations",
    description="Returns paginated list of all tenant configurations with masked sensitive fields. "
    "Requires admin authentication via X-Admin-Key header.",
)
async def list_tenants(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_async_session),
    redis_client=Depends(get_redis_client),
    _: None = Depends(require_admin),
) -> TenantConfigListResponse:
    """
    List all tenant configurations with pagination.

    Args:
        skip: Number of records to skip (default 0)
        limit: Maximum records to return (default 50)
        db: Database session
        redis_client: Redis client for caching
        _: Admin authentication (dependency)

    Returns:
        TenantConfigListResponse: Paginated list with masked sensitive fields
    """
    if limit > 100:
        limit = 100  # Cap limit at 100

    tenant_service = TenantService(db, redis_client)

    try:
        configs = await tenant_service.list_tenants(skip=skip, limit=limit)

        # Convert to response models with masked fields
        responses = [
            TenantConfigResponse(
                tenant_id=cfg.tenant_id,
                name=cfg.name,
                servicedesk_url=cfg.servicedesk_url,
                api_key="***encrypted***",
                webhook_secret="***encrypted***",
                enhancement_preferences=cfg.enhancement_preferences,
            )
            for cfg in configs
        ]

        return TenantConfigListResponse(
            items=responses,
            total_count=len(responses),  # Note: True total would require separate count query
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.error(
            f"Failed to list tenants: {str(e)}",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tenant list",
        )


@router.get(
    "/{tenant_id}",
    response_model=TenantConfigResponse,
    summary="Get specific tenant configuration",
    description="Retrieves configuration for a specific tenant with masked sensitive fields. "
    "Requires admin authentication via X-Admin-Key header.",
)
async def get_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_async_session),
    redis_client=Depends(get_redis_client),
    _: None = Depends(require_admin),
) -> TenantConfigResponse:
    """
    Get tenant configuration by tenant_id.

    Args:
        tenant_id: Tenant identifier
        db: Database session
        redis_client: Redis client for caching
        _: Admin authentication (dependency)

    Returns:
        TenantConfigResponse: Tenant configuration with masked sensitive fields

    Raises:
        HTTPException(404): If tenant not found
    """
    tenant_service = TenantService(db, redis_client)

    try:
        config = await tenant_service.get_tenant_config(tenant_id)

        return TenantConfigResponse(
            tenant_id=config.tenant_id,
            name=config.name,
            servicedesk_url=config.servicedesk_url,
            api_key="***encrypted***",
            webhook_secret="***encrypted***",
            enhancement_preferences=config.enhancement_preferences,
        )

    except TenantNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )
    except Exception as e:
        logger.error(
            f"Failed to get tenant {tenant_id}: {str(e)}",
            extra={"tenant_id": tenant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tenant configuration",
        )


@router.put(
    "/{tenant_id}",
    response_model=TenantConfigResponse,
    summary="Update tenant configuration",
    description="Updates tenant configuration. All fields are optional. "
    "Sensitive fields (api_key, webhook_secret) are encrypted before storage. "
    "Cache is invalidated on update to ensure freshness. "
    "Requires admin authentication via X-Admin-Key header.",
)
async def update_tenant(
    tenant_id: str,
    updates: TenantConfigUpdate,
    db: AsyncSession = Depends(get_async_session),
    redis_client=Depends(get_redis_client),
    _: None = Depends(require_admin),
) -> TenantConfigResponse:
    """
    Update tenant configuration.

    Args:
        tenant_id: Tenant identifier
        updates: Partial tenant configuration updates
        db: Database session
        redis_client: Redis client for caching
        _: Admin authentication (dependency)

    Returns:
        TenantConfigResponse: Updated tenant configuration with masked fields

    Raises:
        HTTPException(404): If tenant not found
    """
    tenant_service = TenantService(db, redis_client)

    try:
        updated_config = await tenant_service.update_tenant(tenant_id, updates)

        logger.info(
            f"Tenant configuration updated: {tenant_id}",
            extra={"tenant_id": tenant_id},
        )

        return TenantConfigResponse(
            tenant_id=updated_config.tenant_id,
            name=updated_config.name,
            servicedesk_url=updated_config.servicedesk_url,
            api_key="***encrypted***",
            webhook_secret="***encrypted***",
            enhancement_preferences=updated_config.enhancement_preferences,
        )

    except TenantNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )
    except Exception as e:
        logger.error(
            f"Failed to update tenant {tenant_id}: {str(e)}",
            extra={"tenant_id": tenant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update tenant configuration",
        )


@router.delete(
    "/{tenant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete tenant configuration",
    description="Soft deletes tenant (marks as inactive). Configuration remains in database "
    "for audit trail but becomes inactive and inaccessible. Can be reactivated via update. "
    "Requires admin authentication via X-Admin-Key header.",
)
async def delete_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_async_session),
    redis_client=Depends(get_redis_client),
    _: None = Depends(require_admin),
) -> None:
    """
    Delete tenant configuration (soft delete).

    Args:
        tenant_id: Tenant identifier
        db: Database session
        redis_client: Redis client for caching
        _: Admin authentication (dependency)

    Raises:
        HTTPException(404): If tenant not found
    """
    tenant_service = TenantService(db, redis_client)

    try:
        await tenant_service.delete_tenant(tenant_id)

        logger.info(
            f"Tenant configuration deleted: {tenant_id}",
            extra={"tenant_id": tenant_id},
        )

    except TenantNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )
    except Exception as e:
        logger.error(
            f"Failed to delete tenant {tenant_id}: {str(e)}",
            extra={"tenant_id": tenant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete tenant configuration",
        )


@router.post(
    "/{tenant_id}/rotate-llm-key",
    status_code=status.HTTP_200_OK,
    summary="Rotate LiteLLM virtual key for tenant",
    description="Generates new LiteLLM virtual key for tenant, invalidates old key, "
    "and updates database with encrypted new key. Audit log entry created. "
    "Requires admin authentication via X-Admin-Key header. "
    "Story 8.9: Virtual Key Management",
)
async def rotate_llm_key(
    tenant_id: str,
    db: AsyncSession = Depends(get_async_session),
    redis_client=Depends(get_redis_client),
    _: None = Depends(require_admin),
) -> dict:
    """
    Rotate LiteLLM virtual key for tenant.

    Creates new virtual key via LiteLLM proxy, encrypts and stores it,
    invalidates cache, and logs audit entry.

    Args:
        tenant_id: Tenant identifier
        db: Database session
        redis_client: Redis client for caching
        _: Admin authentication (dependency)

    Returns:
        dict: Success message with rotation timestamp

    Raises:
        HTTPException(404): If tenant not found
        HTTPException(500): If rotation fails
    """
    tenant_service = TenantService(db, redis_client)

    try:
        # Verify tenant exists
        config = await tenant_service.get_tenant_config(tenant_id)

        # Rotate virtual key
        llm_service = LLMService(db=db)
        new_virtual_key = await llm_service.rotate_virtual_key(tenant_id)

        # Update database with encrypted new key
        from sqlalchemy import update
        from src.database.models import TenantConfig as TenantConfigModel

        encrypted_key = encrypt(new_virtual_key)
        rotation_time = datetime.now(timezone.utc)

        stmt = (
            update(TenantConfigModel)
            .where(TenantConfigModel.tenant_id == tenant_id)
            .values(
                litellm_virtual_key=encrypted_key,
                litellm_key_last_rotated=rotation_time,
            )
        )
        await db.execute(stmt)
        await db.commit()

        # Invalidate cache
        cache_key = tenant_service.CACHE_KEY_PATTERN.format(tenant_id=tenant_id)
        try:
            await redis_client.delete(cache_key)
        except Exception as e:
            logger.warning(f"Failed to invalidate cache for tenant {tenant_id}: {str(e)}")

        # Log audit entry
        await llm_service.log_audit_entry(
            operation="llm_key_rotated",
            tenant_id=tenant_id,
            user="admin",
            details={"rotation_timestamp": rotation_time.isoformat()},
            status="success",
        )

        logger.info(
            f"LiteLLM virtual key rotated for tenant: {tenant_id}",
            extra={"tenant_id": tenant_id, "rotation_time": rotation_time},
        )

        return {
            "message": f"Virtual key rotated successfully for tenant {tenant_id}",
            "tenant_id": tenant_id,
            "rotated_at": rotation_time.isoformat(),
        }

    except TenantNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )
    except VirtualKeyRotationError as e:
        logger.error(
            f"Failed to rotate virtual key for tenant {tenant_id}: {str(e)}",
            extra={"tenant_id": tenant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rotate virtual key: {str(e)}",
        )
    except Exception as e:
        logger.error(
            f"Unexpected error rotating key for tenant {tenant_id}: {str(e)}",
            extra={"tenant_id": tenant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rotate virtual key",
        )



# ============================================================================
# Budget Override Endpoints (Story 8.10 AC#8)
# ============================================================================

from pydantic import BaseModel, Field

class BudgetOverrideRequest(BaseModel):
    """Request schema for budget override."""
    override_amount: float = Field(..., gt=0, description="Temporary budget increase amount in dollars")
    duration_days: int = Field(..., gt=0, le=90, description="Override duration in days (max 90)")
    reason: str = Field(..., min_length=10, description="Reason for budget override (min 10 chars)")


@router.post(
    "/{tenant_id}/budget-override",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_admin)],
    summary="Grant temporary budget override",
    description="Admin-only: Grant temporary budget increase for a tenant (Story 8.10 AC#8)",
)
async def grant_budget_override(
    tenant_id: str,
    override_request: BudgetOverrideRequest,
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """
    Grant temporary budget override for a tenant.

    Updates LiteLLM virtual key with temp_budget_increase and expiry.
    Stores override in budget_overrides table with audit logging.

    Args:
        tenant_id: Tenant identifier
        override_request: Override details (amount, duration, reason)
        db: Database session

    Returns:
        Dict with override details and updated budget info

    Raises:
        HTTPException 404: Tenant not found
        HTTPException 500: Failed to apply override
    """
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import select
    from src.database.models import TenantConfig, BudgetOverride, AuditLog
    from src.config import settings
    import httpx

    try:
        # Get tenant
        stmt = select(TenantConfig).where(TenantConfig.tenant_id == tenant_id)
        result = await db.execute(stmt)
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant '{tenant_id}' not found"
            )

        # Calculate expiry
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=override_request.duration_days)

        # Update LiteLLM virtual key with temp_budget_increase
        if tenant.litellm_virtual_key:
            async with httpx.AsyncClient(timeout=30.0) as client:
                litellm_url = f"{settings.litellm_proxy_url}/key/update"
                headers = {"Authorization": f"Bearer {settings.litellm_master_key}"}
                payload = {
                    "key": tenant.litellm_virtual_key,
                    "metadata": {
                        "temp_budget_increase": override_request.override_amount,
                        "temp_budget_expiry": expires_at.isoformat(),
                    }
                }

                response = await client.post(litellm_url, json=payload, headers=headers)
                response.raise_for_status()

                logger.info(f"Applied budget override via LiteLLM for tenant {tenant_id}")

        # Store override in database
        budget_override = BudgetOverride(
            tenant_id=tenant_id,
            override_amount=override_request.override_amount,
            reason=override_request.reason,
            granted_by="admin",  # TODO: Get from auth context
            granted_at=now,
            expires_at=expires_at,
            is_active=True
        )
        db.add(budget_override)

        # Log audit entry
        audit_entry = AuditLog(
            tenant_id=tenant_id,
            operation="budget_override_granted",
            user="admin",  # TODO: Get from auth context
            timestamp=now,
            details={
                "override_amount": override_request.override_amount,
                "duration_days": override_request.duration_days,
                "expires_at": expires_at.isoformat(),
                "reason": override_request.reason,
                "original_budget": tenant.max_budget
            }
        )
        db.add(audit_entry)

        await db.commit()

        logger.info(
            f"Budget override granted for tenant {tenant_id}",
            extra={
                "tenant_id": tenant_id,
                "override_amount": override_request.override_amount,
                "duration_days": override_request.duration_days,
                "expires_at": expires_at.isoformat()
            }
        )

        return {
            "message": "Budget override granted successfully",
            "tenant_id": tenant_id,
            "original_budget": tenant.max_budget,
            "override_amount": override_request.override_amount,
            "new_effective_budget": tenant.max_budget + override_request.override_amount,
            "granted_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "duration_days": override_request.duration_days,
            "reason": override_request.reason
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to grant budget override for tenant {tenant_id}: {str(e)}",
            extra={"tenant_id": tenant_id, "error": str(e)}
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to grant budget override: {str(e)}"
        )


@router.delete(
    "/{tenant_id}/budget-override",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_admin)],
    summary="Remove budget override",
    description="Admin-only: Remove temporary budget override for a tenant (Story 8.10 AC#8)",
)
async def remove_budget_override(
    tenant_id: str,
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """
    Remove active budget override for a tenant.

    Updates LiteLLM virtual key to remove temp_budget_increase.
    Marks override as inactive in budget_overrides table.

    Args:
        tenant_id: Tenant identifier
        db: Database session

    Returns:
        Dict with removal confirmation

    Raises:
        HTTPException 404: Tenant or active override not found
        HTTPException 500: Failed to remove override
    """
    from datetime import datetime, timezone
    from sqlalchemy import select, update
    from src.database.models import TenantConfig, BudgetOverride, AuditLog
    from src.config import settings
    import httpx

    try:
        # Get tenant
        stmt = select(TenantConfig).where(TenantConfig.tenant_id == tenant_id)
        result = await db.execute(stmt)
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant '{tenant_id}' not found"
            )

        # Get active override
        override_stmt = select(BudgetOverride).where(
            BudgetOverride.tenant_id == tenant_id,
            BudgetOverride.is_active == True
        ).order_by(BudgetOverride.granted_at.desc())
        override_result = await db.execute(override_stmt)
        override = override_result.scalar_one_or_none()

        if not override:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active budget override found for tenant '{tenant_id}'"
            )

        # Remove temp_budget_increase from LiteLLM virtual key
        if tenant.litellm_virtual_key:
            async with httpx.AsyncClient(timeout=30.0) as client:
                litellm_url = f"{settings.litellm_proxy_url}/key/update"
                headers = {"Authorization": f"Bearer {settings.litellm_master_key}"}
                payload = {
                    "key": tenant.litellm_virtual_key,
                    "metadata": {
                        "temp_budget_increase": 0,
                        "temp_budget_expiry": None,
                    }
                }

                response = await client.post(litellm_url, json=payload, headers=headers)
                response.raise_for_status()

                logger.info(f"Removed budget override from LiteLLM for tenant {tenant_id}")

        # Mark override as inactive
        now = datetime.now(timezone.utc)
        await db.execute(
            update(BudgetOverride)
            .where(BudgetOverride.id == override.id)
            .values(is_active=False, updated_at=now)
        )

        # Log audit entry
        audit_entry = AuditLog(
            tenant_id=tenant_id,
            operation="budget_override_removed",
            user="admin",  # TODO: Get from auth context
            timestamp=now,
            details={
                "override_amount": override.override_amount,
                "original_granted_at": override.granted_at.isoformat(),
                "original_expires_at": override.expires_at.isoformat(),
                "removed_at": now.isoformat(),
                "reason": override.reason
            }
        )
        db.add(audit_entry)

        await db.commit()

        logger.info(
            f"Budget override removed for tenant {tenant_id}",
            extra={"tenant_id": tenant_id, "override_id": override.id}
        )

        return {
            "message": "Budget override removed successfully",
            "tenant_id": tenant_id,
            "original_override_amount": override.override_amount,
            "removed_at": now.isoformat(),
            "restored_budget": tenant.max_budget
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to remove budget override for tenant {tenant_id}: {str(e)}",
            extra={"tenant_id": tenant_id, "error": str(e)}
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove budget override: {str(e)}"
        )
