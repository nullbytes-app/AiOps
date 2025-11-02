"""
Admin API endpoints for tenant configuration management.

Provides CRUD operations for managing tenant configurations including
ServiceDesk Plus credentials, webhook secrets, and enhancement preferences.
All endpoints require admin API key authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from src.schemas.tenant import (
    TenantConfigCreate,
    TenantConfigUpdate,
    TenantConfigResponse,
    TenantConfigListResponse,
)
from src.services.tenant_service import TenantService
from src.database.session import get_async_session
from src.cache.redis_client import get_redis_client
from src.config import get_settings
from src.utils.logger import logger
from src.utils.exceptions import TenantNotFoundException

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
