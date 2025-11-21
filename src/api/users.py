"""
User management API endpoints for profile and password operations.

This module provides protected endpoints for authenticated users:
- GET /api/users/me - Get current user profile with roles
- PUT /api/users/me/password - Change password with validation

Story: 1C - API Endpoints & Middleware
Epic: 2 (Authentication & Authorization Foundation)
"""

from datetime import datetime, UTC
from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import (
    get_auth_service,
    get_current_active_user,
    get_user_service,
)
from src.database.models import AuthAuditLog, User, UserTenantRole, RoleEnum
from src.database.session import get_async_session
from src.services.auth_service import AuthService, hash_password, verify_password, validate_password_strength
from src.services.user_service import UserService

# Create router with /api/users prefix
router = APIRouter(
    prefix="/api/users",
    tags=["Users"],
)


# ==============================================================================
# Request/Response Schemas
# ==============================================================================


class RoleAssignment(BaseModel):
    """User role assignment for a tenant."""

    tenant_id: UUID
    role: RoleEnum

    model_config = {"from_attributes": True}


class UserDetailResponse(BaseModel):
    """Detailed user profile with roles."""

    id: UUID
    email: EmailStr
    default_tenant_id: UUID
    roles: List[RoleAssignment]
    created_at: datetime
    last_login_at: datetime | None
    is_active: bool

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "default_tenant_id": "123e4567-e89b-12d3-a456-426614174000",
                "roles": [
                    {
                        "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
                        "role": "admin",
                    },
                    {
                        "tenant_id": "987e6543-e21b-12d3-a456-426614174000",
                        "role": "viewer",
                    },
                ],
                "created_at": "2025-11-18T10:00:00Z",
                "last_login_at": "2025-11-18T14:30:00Z",
                "is_active": True,
            }
        },
    }


class ChangePasswordRequest(BaseModel):
    """Password change request."""

    current_password: str
    new_password: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "current_password": "OldPass123!",
                "new_password": "NewSecurePass456!",
            }
        }
    }


# ==============================================================================
# Endpoints
# ==============================================================================


@router.get(
    "/me",
    response_model=UserDetailResponse,
    summary="Get current user profile",
    response_description="Current authenticated user details",
)
async def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_async_session),
) -> UserDetailResponse:
    """
    Get authenticated user's profile with roles.

    Args:
        current_user: User from JWT token
        db: Database session

    Returns:
        UserDetailResponse with user details and roles

    Security:
        Requires valid JWT access token

    Example:
        GET /api/users/me
        Headers: Authorization: Bearer <access_token>
    """
    # Fetch user's roles for all tenants
    stmt = select(UserTenantRole).where(UserTenantRole.user_id == current_user.id)
    result = await db.execute(stmt)
    roles = result.scalars().all()

    # Build response with roles
    role_assignments = [
        RoleAssignment(tenant_id=role.tenant_id, role=role.role) for role in roles
    ]

    return UserDetailResponse(
        id=current_user.id,
        email=current_user.email,
        default_tenant_id=current_user.default_tenant_id,
        roles=role_assignments,
        created_at=current_user.created_at,
        last_login_at=current_user.last_login_at,
        is_active=current_user.is_active,
    )


@router.put(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change password",
    response_description="Password successfully changed",
)
async def change_password(
    current_user: Annotated[User, Depends(get_current_active_user)],
    request_data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_async_session),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    """
    Change user password with validation.

    Args:
        current_user: Authenticated user
        request_data: ChangePasswordRequest with old and new passwords
        db: Database session
        auth_service: Authentication service

    Returns:
        204 No Content

    Raises:
        400: Current password incorrect
        422: New password fails strength validation
        422: New password matches recent password (password history)

    Side Effects:
        - Updates password_hash
        - Appends to password_history
        - Revokes all existing tokens (force re-login)

    Security:
        - Current password verified before changing
        - New password validated for strength
        - New password checked against password history (prevent reuse)
        - All tokens revoked to force re-authentication
        - Password change logged to auth_audit_log
    """
    # Verify current password
    if not verify_password(request_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Validate new password strength
    is_valid, error_msg = validate_password_strength(request_data.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error_msg
        )

    # Check password history (prevent reuse of last 5 passwords)
    password_history = current_user.password_history or []
    for old_hash in password_history[-5:]:  # Check last 5 passwords
        if verify_password(request_data.new_password, old_hash):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="New password cannot match any of your last 5 passwords",
            )

    # Update password
    new_hash = hash_password(request_data.new_password)

    # Append current password to history
    updated_history = password_history + [current_user.password_hash]
    current_user.password_history = updated_history[-10:]  # Keep last 10

    current_user.password_hash = new_hash
    current_user.password_changed_at = datetime.now(UTC)

    # Revoke all existing tokens (force re-login across all devices)
    # Implementation: Increment user's token version in Redis
    # All tokens issued before this version increment will be rejected during verification
    if auth_service.redis:
        user_token_key = f"user:token_version:{str(current_user.id)}"
        current_version = await auth_service.redis.get(user_token_key)

        if current_version is None:
            # First password change - set version to 1
            new_version = 1
        else:
            # Increment existing version
            new_version = int(current_version) + 1

        # Store new version in Redis (no TTL - persists until next password change)
        await auth_service.redis.set(user_token_key, str(new_version))

        # This invalidates ALL tokens issued before this moment by incrementing the version
        # Tokens contain the version they were issued with, and will be rejected if version doesn't match

    # Log password change event
    audit_entry = AuthAuditLog(
        user_id=current_user.id,
        event_type="password_change",
        success=True,
        ip_address="Unknown",
        user_agent="Unknown",
    )
    db.add(audit_entry)

    await db.commit()

    # 204 No Content (no response body)
    return None
