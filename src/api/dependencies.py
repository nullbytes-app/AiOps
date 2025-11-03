"""
FastAPI Dependencies for Request-Scoped Services.

This module provides FastAPI dependency injection functions for:
- Tenant identification and extraction
- RLS-aware database sessions
- Authentication and authorization

Story: 3.1 - Implement Row-Level Security in PostgreSQL
AC: 3
"""

from typing import AsyncGenerator

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_async_session
from src.database.tenant_context import set_db_tenant_context


async def get_tenant_id(request: Request) -> str:
    """
    Extract tenant_id from incoming request.

    The tenant_id can be sourced from:
    1. Webhook payload body (for ServiceDesk webhooks)
    2. Authentication token claims (for authenticated API calls)
    3. Custom header X-Tenant-ID (for admin/testing)

    Args:
        request: FastAPI Request object

    Returns:
        Validated tenant_id string

    Raises:
        HTTPException: 400 if tenant_id is missing or invalid

    Example:
        @app.post("/webhook/servicedesk")
        async def receive_webhook(
            tenant_id: str = Depends(get_tenant_id)
        ):
            # tenant_id automatically extracted and validated
            pass
    """
    tenant_id = None

    # Strategy 1: Extract from JSON body (webhook payloads)
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.json()
            tenant_id = body.get("tenant_id")
        except Exception:
            # Body might not be JSON, continue to other strategies
            pass

    # Strategy 2: Extract from custom header (testing/admin)
    if not tenant_id:
        tenant_id = request.headers.get("X-Tenant-ID")

    # Strategy 3: Extract from authentication context
    # TODO: Implement auth token parsing when authentication is added
    # if not tenant_id and hasattr(request.state, "user"):
    #     tenant_id = request.state.user.tenant_id

    if not tenant_id:
        raise HTTPException(
            status_code=400,
            detail="Missing tenant_id. Provide in request body or X-Tenant-ID header."
        )

    if not isinstance(tenant_id, str) or not tenant_id.strip():
        raise HTTPException(
            status_code=400,
            detail="Invalid tenant_id format. Must be non-empty string."
        )

    return tenant_id.strip()


async def get_tenant_db(
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_async_session),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide RLS-aware database session with tenant context pre-configured.

    This dependency:
    1. Receives an already-created database session from get_async_session dependency
    2. Sets the tenant context using set_db_tenant_context()
    3. Yields the session for use in request handlers
    4. Session cleanup is handled by the get_async_session dependency

    Args:
        tenant_id: Tenant identifier (injected via get_tenant_id dependency)
        session: AsyncSession from get_async_session dependency

    Yields:
        AsyncSession: Database session with tenant context set

    Raises:
        HTTPException: 500 if tenant context cannot be set (e.g., invalid tenant_id)

    Example:
        @app.post("/enhancements")
        async def create_enhancement(
            data: EnhancementCreate,
            db: AsyncSession = Depends(get_tenant_db)
        ):
            # db session automatically filtered by tenant_id
            enhancement = EnhancementHistory(**data.dict())
            db.add(enhancement)
            await db.commit()
            return enhancement

    Note:
        - Tenant context is automatically cleared when session closes
        - All queries through this session are subject to RLS filtering
        - Superuser roles with BYPASSRLS will see all data regardless
    """
    try:
        # Set tenant context before yielding session
        await set_db_tenant_context(session, tenant_id)

        # Yield session for request handler use
        yield session

    except Exception as e:
        # If tenant context setting fails, return 500
        # This typically means tenant_id doesn't exist in tenant_configs
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set tenant context: {str(e)}"
        )

    finally:
        # Session cleanup handled by get_async_session dependency
        # Tenant context automatically cleared on session close
        pass


async def get_tenant_config_dep(
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Provide tenant configuration with RLS context.

    This dependency:
    1. Extracts tenant_id from request
    2. Loads tenant configuration from TenantService (with caching)
    3. Sets RLS tenant context for database isolation
    4. Returns tenant config for use in request handlers

    Args:
        tenant_id: Tenant identifier (injected via get_tenant_id dependency)
        db: Database session (injected via get_async_session dependency)

    Returns:
        TenantConfigInternal: Loaded tenant configuration with decrypted credentials

    Raises:
        HTTPException: 404 if tenant configuration not found
        HTTPException: 500 if tenant config cannot be loaded

    Example:
        @app.post("/webhook/servicedesk")
        async def receive_webhook(
            payload: WebhookPayload,
            tenant_config: TenantConfigInternal = Depends(get_tenant_config_dep)
        ):
            # tenant_config now available with decrypted credentials
            # RLS context already set by dependency
            servicedesk_url = tenant_config.servicedesk_url
            api_key = tenant_config.servicedesk_api_key
    """
    from redis import asyncio as aioredis
    from src.services.tenant_service import TenantService, TenantNotFoundException
    from src.cache.redis_client import get_redis_client

    try:
        # Initialize services
        redis = await get_redis_client()
        tenant_service = TenantService(db=db, redis=redis)

        # Load tenant configuration (with caching)
        tenant_config = await tenant_service.get_tenant_config(tenant_id)

        # Set RLS tenant context for this request
        await set_db_tenant_context(db, tenant_id)

        return tenant_config

    except TenantNotFoundException:
        # Tenant not found in database
        raise HTTPException(
            status_code=404,
            detail=f"Tenant '{tenant_id}' not found. Please check tenant configuration."
        )
    except Exception as e:
        # Other errors (encryption, database, etc.)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load tenant configuration: {str(e)}"
        )
