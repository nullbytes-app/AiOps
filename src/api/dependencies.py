"""
FastAPI Dependencies for Request-Scoped Services.

This module provides FastAPI dependency injection functions for:
- Tenant identification and extraction
- RLS-aware database sessions
- Authentication and authorization (Story 1C)

Story: 3.1 - Implement Row-Level Security in PostgreSQL
Story: 1C - API Endpoints & Middleware
"""

from typing import Annotated, AsyncGenerator
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database.session import get_async_session
from src.database.tenant_context import set_db_tenant_context
from src.database.models import User, RoleEnum
from src.services.auth_service import AuthService, verify_token
from src.services.user_service import UserService


# Story 1C: OAuth2 scheme for JWT token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", scheme_name="JWT")


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

    # Strategy 3: Extract from JWT token (for authenticated session-based requests)
    if not tenant_id:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                # Decode JWT without verification (just for tenant extraction)
                # Full validation happens later in get_current_user if needed
                payload = jwt.decode(
                    token,
                    settings.jwt_secret_key,
                    algorithms=["HS256"]
                )
                tenant_id = payload.get("default_tenant_id")
            except (JWTError, Exception):
                # Token decoding failed, continue to fallback strategy
                pass

    # Strategy 4: Fallback to DEFAULT_TENANT_ID from environment
    # Used for single-tenant deployments or development environments
    if not tenant_id:
        tenant_id = settings.default_tenant_id

    if not tenant_id:
        raise HTTPException(
            status_code=400,
            detail="Missing tenant_id. Provide in request body or X-Tenant-ID header.",
        )

    if not isinstance(tenant_id, str) or not tenant_id.strip():
        raise HTTPException(
            status_code=400, detail="Invalid tenant_id format. Must be non-empty string."
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
    # Set tenant context before yielding session
    await set_db_tenant_context(session, tenant_id)

    # Yield session for request handler use
    # Note: We don't catch exceptions here to allow FastAPI's built-in
    # validation errors (RequestValidationError) to propagate correctly.
    # Tenant context setting errors will raise before the yield.
    yield session

    # Session cleanup handled by get_async_session dependency
    # Tenant context automatically cleared on session close


async def get_tenant_uuid(
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_async_session),
) -> "UUID":
    """
    Resolve tenant_id (VARCHAR) to TenantConfig.id (UUID).

    Many models use TenantConfig.id (UUID) as foreign key, but the
    dependency get_tenant_id returns TenantConfig.tenant_id (VARCHAR).
    This dependency resolves the VARCHAR identifier to the UUID primary key.

    Args:
        tenant_id: Tenant identifier (VARCHAR from get_tenant_id)
        session: Database session

    Returns:
        UUID: TenantConfig.id (primary key)

    Raises:
        HTTPException: 404 if tenant not found

    Example:
        @app.get("/api/v1/mcp-servers")
        async def list_servers(
            tenant_uuid: UUID = Depends(get_tenant_uuid),
            db: AsyncSession = Depends(get_tenant_db)
        ):
            servers = await service.list_servers(tenant_uuid)
    """
    from uuid import UUID
    from sqlalchemy import select
    from src.database.models import TenantConfig

    try:
        # Query TenantConfig to get UUID id from VARCHAR tenant_id
        stmt = select(TenantConfig.id).where(TenantConfig.tenant_id == tenant_id)
        result = await session.execute(stmt)
        tenant_uuid = result.scalar_one_or_none()

        if not tenant_uuid:
            raise HTTPException(status_code=404, detail=f"Tenant '{tenant_id}' not found")

        return tenant_uuid

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resolve tenant UUID: {str(e)}")


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
            detail=f"Tenant '{tenant_id}' not found. Please check tenant configuration.",
        )
    except Exception as e:
        # Other errors (encryption, database, etc.)
        raise HTTPException(
            status_code=500, detail=f"Failed to load tenant configuration: {str(e)}"
        )


# ==============================================================================
# Story 1C: Authentication Dependencies
# ==============================================================================


async def get_auth_service() -> AuthService:
    """
    Dependency to get AuthService instance.

    Returns:
        AuthService: Authentication service instance with Redis client

    Example:
        @router.post("/login")
        async def login(
            auth_service: AuthService = Depends(get_auth_service)
        ):
            token = await auth_service.create_access_token(...)
    """
    from src.cache.redis_client import get_redis_client

    redis_client = await get_redis_client()
    return AuthService(redis_client=redis_client)


async def get_user_service() -> UserService:
    """
    Dependency to get UserService instance.

    Returns:
        UserService: User management service instance

    Example:
        @router.get("/users")
        async def list_users(
            user_service: UserService = Depends(get_user_service)
        ):
            users = await user_service.list_users(db)
    """
    return UserService()


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    """
    Get current user from JWT token.

    This dependency:
    1. Extracts JWT token from Authorization header (via oauth2_scheme)
    2. Verifies token signature, expiration, and blacklist status
    3. Extracts user_id from 'sub' claim
    4. Fetches user from database
    5. Returns User model instance

    Args:
        token: JWT access token from Authorization header
        db: Database session
        auth_service: Authentication service
        user_service: User service

    Returns:
        User: Authenticated user model instance

    Raises:
        HTTPException: 401 if token invalid, expired, or revoked
        HTTPException: 401 if user not found

    Security:
        - Token signature verified with JWT_SECRET_KEY
        - Token expiration checked
        - Token blacklist checked (Redis)
        - Returns generic error message to prevent information disclosure

    Example:
        @router.get("/protected")
        async def protected_route(
            current_user: User = Depends(get_current_user)
        ):
            return {"user_id": current_user.id}
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Verify token (checks signature, expiration, and blacklist)
        payload = await verify_token(auth_service.redis, token)

        # Extract user_id from 'sub' claim
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception

        # Convert string to UUID
        user_id = UUID(user_id_str)

    except (JWTError, ValueError):
        # JWTError: invalid token, expired, or signature mismatch
        # ValueError: invalid UUID format
        raise credentials_exception

    # Fetch user from database
    user = await user_service.get_user_by_id(user_id, db)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """
    Verify current user is active (not disabled/deleted).

    This dependency:
    1. Receives authenticated user from get_current_user
    2. Checks is_active flag
    3. Returns user if active, raises 400 if inactive

    Args:
        current_user: User from get_current_user dependency

    Returns:
        User: Active user model instance

    Raises:
        HTTPException: 400 if user account is inactive

    Example:
        @router.post("/create-post")
        async def create_post(
            current_user: User = Depends(get_current_active_user)
        ):
            # Only active users can create posts
            pass
    """
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user account")

    return current_user


async def require_role(
    required_role: RoleEnum,
    tenant_id: str,
) -> callable:
    """
    Factory to create role-checking dependency.

    This creates a dependency that verifies the user has the required role
    for a specific tenant. Uses role hierarchy: admin > operator > viewer.

    Args:
        required_role: Minimum role required
        tenant_id: Tenant context for role check

    Returns:
        Dependency function that checks role

    Example:
        @router.delete("/users/{user_id}")
        async def delete_user(
            user_id: UUID,
            current_user: User = Depends(require_role(RoleEnum.ADMIN, "tenant-123"))
        ):
            # Only admins can delete users
            pass

    Security:
        Role hierarchy enforced: admin (3) > operator (2) > viewer (1)
    """

    async def role_checker(
        current_user: Annotated[User, Depends(get_current_active_user)],
        db: Annotated[AsyncSession, Depends(get_async_session)],
        user_service: Annotated[UserService, Depends(get_user_service)],
    ) -> User:
        """Check if user has required role for tenant."""
        # Get user's role for this tenant
        user_role = await user_service.get_user_role_for_tenant(current_user.id, tenant_id, db)

        # Role hierarchy: admin (3) > operator (2) > viewer (1)
        role_hierarchy = {RoleEnum.ADMIN: 3, RoleEnum.OPERATOR: 2, RoleEnum.VIEWER: 1}

        # Check if user has sufficient permissions
        user_level = role_hierarchy.get(user_role, 0) if user_role else 0
        required_level = role_hierarchy[required_role]

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role.value} role for tenant {tenant_id}",
            )

        return current_user

    return role_checker
