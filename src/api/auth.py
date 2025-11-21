"""
Authentication API endpoints for user registration and JWT token management.

This module provides OAuth2-compliant authentication endpoints:
- POST /api/auth/register - User registration
- POST /api/auth/token - OAuth2 password flow login
- POST /api/auth/refresh - Token refresh
- POST /api/auth/logout - Token revocation

Story: 1C - API Endpoints & Middleware
Epic: 2 (Authentication & Authorization Foundation)
"""

from datetime import datetime, UTC
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import (
    get_auth_service,
    get_current_active_user,
    get_user_service,
)
from src.database.models import AuthAuditLog, User
from src.database.session import get_async_session
from src.services.auth_service import (
    AuthService,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    verify_token,
    revoke_token,
)
from src.services.user_service import UserService
from src.middleware.rate_limit import limiter  # Story 1C: Rate limiting

# Create router with /api/auth prefix
router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


# ==============================================================================
# Request/Response Schemas
# ==============================================================================


class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr
    password: str
    default_tenant_id: UUID

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123!",
                "default_tenant_id": "123e4567-e89b-12d3-a456-426614174000",
            }
        }
    }


class UserResponse(BaseModel):
    """User response (password excluded)."""

    id: UUID
    email: EmailStr
    default_tenant_id: UUID
    created_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """OAuth2 token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Seconds until access token expires

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIs...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
                "token_type": "bearer",
                "expires_in": 604800,
            }
        }
    }


class RefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str

    model_config = {"json_schema_extra": {"example": {"refresh_token": "eyJhbGciOiJIUzI1NiIs..."}}}


class LogoutRequest(BaseModel):
    """Logout request with tokens to revoke."""

    access_token: str
    refresh_token: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIs...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
            }
        }
    }


# ==============================================================================
# Endpoints
# ==============================================================================


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    response_description="User successfully registered",
)
@limiter.limit("10/minute")  # Story 1C: Prevent spam registration
async def register(
    request: Request,  # Required by slowapi for rate limiting
    request_data: RegisterRequest,
    db: AsyncSession = Depends(get_async_session),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """
    Register new user with email and password.

    Args:
        request_data: RegisterRequest with email, password, default_tenant_id
        db: Database session
        user_service: User service

    Returns:
        UserResponse with user details (no password)

    Raises:
        400: Email already exists
        422: Validation error (weak password, invalid email)
        500: Database error

    Security:
        - Password validated for strength before hashing
        - Password hashed with bcrypt (10 rounds)
        - Email uniqueness enforced by database constraint
    """
    try:
        # Create user (validation happens in UserService)
        user = await user_service.create_user(
            email=request_data.email,
            password=request_data.password,
            default_tenant_id=request_data.default_tenant_id,
            db=db,
        )

        return UserResponse.model_validate(user)

    except ValueError as e:
        # Password validation failed
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except IntegrityError:
        # Email already exists (unique constraint violation)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="OAuth2 compatible token login",
    response_description="Access token and refresh token",
)
@limiter.limit("100/minute")  # Story 1C: Prevent brute force attacks
async def login(
    request: Request,  # Required by slowapi for rate limiting (moved to first position)
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_async_session),
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service),
) -> TokenResponse:
    """
    OAuth2 compatible token endpoint.

    Uses OAuth2PasswordRequestForm for standard compatibility:
    - username field contains email
    - password field contains password

    Args:
        form_data: OAuth2 form with username/password
        request: FastAPI request for IP/user-agent extraction
        db: Database session
        auth_service: Authentication service
        user_service: User service

    Returns:
        TokenResponse with access_token, refresh_token, token_type

    Raises:
        401: Invalid credentials or account locked
        429: Rate limit exceeded

    Security:
        - Account lockout after 5 failed attempts (15 min lockout)
        - Failed attempts logged to auth_audit_log
        - Generic error message (prevents user enumeration)
    """
    # Extract IP and user-agent for audit logging
    ip_address = request.client.host
    user_agent = request.headers.get("User-Agent", "Unknown")

    # First, check if user exists and if account is locked
    from sqlalchemy import select

    stmt = select(User).where(User.email == form_data.username)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    # Check if account is locked BEFORE authentication (prevents timing attacks on lock status)
    if (
        existing_user
        and existing_user.locked_until
        and existing_user.locked_until > datetime.now(UTC)
    ):
        # Log failed attempt due to lock
        audit_entry = AuthAuditLog(
            user_id=existing_user.id,
            event_type="login",
            success=False,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(audit_entry)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Account locked until {existing_user.locked_until.isoformat()}. Too many failed login attempts.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Authenticate user (OAuth2PasswordRequestForm uses 'username' field for email)
    user = await authenticate_user(email=form_data.username, password=form_data.password, db=db)

    # Create audit log entry
    audit_entry = AuthAuditLog(
        user_id=user.id if user else None,
        event_type="login",
        success=user is not None,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(audit_entry)
    await db.commit()

    # If authentication failed, return 401
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate tokens (pass redis_client for token version tracking)
    access_token = await create_access_token(user, auth_service.redis)
    refresh_token = await create_refresh_token(user, auth_service.redis)

    # Update last_login_at and reset failed_login_attempts
    user.last_login_at = datetime.now(UTC)
    user.failed_login_attempts = 0
    user.locked_until = None
    await db.commit()

    # Calculate expires_in from settings
    from src.config import settings

    expires_in = settings.jwt_expiration_days * 24 * 60 * 60  # Convert days to seconds

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    response_description="New access token using refresh token",
)
async def refresh_token(
    request_data: RefreshRequest,
    db: AsyncSession = Depends(get_async_session),
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service),
) -> TokenResponse:
    """
    Get new access token using refresh token.

    Args:
        request_data: RefreshRequest with refresh_token
        db: Database session
        auth_service: Authentication service
        user_service: User service

    Returns:
        TokenResponse with new access_token (same refresh_token)

    Raises:
        401: Invalid or expired refresh token
        401: Token has been revoked

    Security:
        - Refresh token verified (signature, expiration, blacklist)
        - User must still exist and be active
        - Does NOT rotate refresh token (30-day TTL acceptable)
    """
    try:
        # Verify refresh token (needs redis_client for blacklist check)
        payload = await verify_token(auth_service.redis, request_data.refresh_token)

        # Extract user_id
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = UUID(user_id_str)

        # Verify user still exists
        user = await user_service.get_user_by_id(user_id, db)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Generate new access token (pass redis_client for token version tracking)
        access_token = await create_access_token(user, auth_service.redis)

        # Calculate expires_in
        from src.config import settings

        expires_in = settings.jwt_expiration_days * 24 * 60 * 60

        return TokenResponse(
            access_token=access_token,
            refresh_token=request_data.refresh_token,  # Don't rotate
            token_type="bearer",
            expires_in=expires_in,
        )

    except Exception:
        # Generic error for security (don't reveal if token expired vs invalid)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout user",
    response_description="Successfully logged out",
)
async def logout(
    current_user: Annotated[User, Depends(get_current_active_user)],
    request_data: LogoutRequest,
    auth_service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """
    Logout user by revoking access and refresh tokens.

    Args:
        current_user: Authenticated user from dependency
        request_data: LogoutRequest with tokens to revoke
        auth_service: Authentication service
        db: Database session

    Returns:
        204 No Content

    Side Effects:
        - Adds both tokens to Redis blacklist
        - Logs logout event to auth_audit_log

    Security:
        - Requires valid access token to logout
        - Both access and refresh tokens added to blacklist
        - TTL on blacklist entries matches token expiration
    """
    # Revoke both tokens
    await revoke_token(auth_service.redis, request_data.access_token)
    await revoke_token(auth_service.redis, request_data.refresh_token)

    # Log logout event
    audit_entry = AuthAuditLog(
        user_id=current_user.id,
        event_type="logout",
        success=True,
        ip_address="Unknown",  # Could extract from Request if needed
        user_agent="Unknown",
    )
    db.add(audit_entry)
    await db.commit()

    # 204 No Content (no response body)
    return None
