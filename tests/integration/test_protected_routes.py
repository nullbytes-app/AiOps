"""
Integration tests for protected user endpoints.

Tests cover:
- GET /api/users/me (current user profile with roles)
- PUT /api/users/me/password (password change with validation)
- Authentication requirements for protected routes

Story: 1C - API Endpoints & Middleware
Epic: 2 (Authentication & Authorization Foundation)
"""

import pytest
from httpx import AsyncClient
from fastapi import status

from src.database.models import User, UserTenantRole, RoleEnum


class TestGetCurrentUserEndpoint:
    """Test GET /api/users/me endpoint."""

    @pytest.mark.asyncio
    async def test_get_current_user_success(
        self, client: AsyncClient, auth_tokens, test_user, db_session
    ):
        """Verify /users/me returns user profile with roles."""
        # Create a role assignment for test user
        from uuid import uuid4

        tenant_id = test_user.default_tenant_id
        role_assignment = UserTenantRole(
            user_id=test_user.id,
            tenant_id=tenant_id,
            role=RoleEnum.ADMIN,
        )
        db_session.add(role_assignment)
        await db_session.commit()

        # Get current user profile
        response = await client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == test_user.email
        assert data["id"] == str(test_user.id)
        assert "roles" in data
        assert isinstance(data["roles"], list)
        assert data["is_active"] is True
        assert "created_at" in data
        assert "password" not in data  # Password never exposed

    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self, client: AsyncClient):
        """Verify missing token returns 401."""
        response = await client.get("/api/users/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, client: AsyncClient):
        """Verify invalid token returns 401."""
        response = await client.get(
            "/api/users/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "WWW-Authenticate" in response.headers

    @pytest.mark.asyncio
    async def test_get_current_user_expired_token(
        self, client: AsyncClient, expired_access_token
    ):
        """Verify expired token returns 401."""
        response = await client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {expired_access_token}"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestChangePasswordEndpoint:
    """Test PUT /api/users/me/password endpoint."""

    @pytest.mark.asyncio
    async def test_change_password_success(
        self, client: AsyncClient, auth_tokens, test_user, db_session
    ):
        """Verify password change succeeds with valid data."""
        response = await client.put(
            "/api/users/me/password",
            json={
                "current_password": "TestPassword123!",
                "new_password": "NewSecurePass456!",
            },
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify user can login with new password
        login_response = await client.post(
            "/api/auth/token",
            data={
                "username": test_user.email,
                "password": "NewSecurePass456!",
            },
        )
        assert login_response.status_code == status.HTTP_200_OK

        # Verify old password no longer works
        old_login_response = await client.post(
            "/api/auth/token",
            data={
                "username": test_user.email,
                "password": "TestPassword123!",
            },
        )
        assert old_login_response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(
        self, client: AsyncClient, auth_tokens
    ):
        """Verify wrong current password returns 400."""
        response = await client.put(
            "/api/users/me/password",
            json={
                "current_password": "WrongPassword!",
                "new_password": "NewSecurePass456!",
            },
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "incorrect" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_change_password_weak_new(
        self, client: AsyncClient, auth_tokens
    ):
        """Verify weak new password returns 422."""
        response = await client.put(
            "/api/users/me/password",
            json={
                "current_password": "TestPassword123!",
                "new_password": "weak",  # Too short and weak
            },
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_change_password_reuse_recent(
        self, client: AsyncClient, auth_tokens, test_user, db_session
    ):
        """Verify cannot reuse recent password."""
        # Change password first time
        await client.put(
            "/api/users/me/password",
            json={
                "current_password": "TestPassword123!",
                "new_password": "NewSecurePass456!",
            },
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"},
        )

        # Get new tokens with new password
        login_response = await client.post(
            "/api/auth/token",
            data={
                "username": test_user.email,
                "password": "NewSecurePass456!",
            },
        )
        new_tokens = login_response.json()

        # Try to change back to old password
        response = await client.put(
            "/api/users/me/password",
            json={
                "current_password": "NewSecurePass456!",
                "new_password": "TestPassword123!",  # Old password
            },
            headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "last 5 passwords" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_change_password_requires_authentication(
        self, client: AsyncClient
    ):
        """Verify password change requires authentication."""
        response = await client.put(
            "/api/users/me/password",
            json={
                "current_password": "TestPassword123!",
                "new_password": "NewSecurePass456!",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_password_change_logged(
        self, client: AsyncClient, auth_tokens, test_user, db_session
    ):
        """Verify password change is logged to auth_audit_log."""
        from src.database.models import AuthAuditLog
        from sqlalchemy import select

        # Change password
        await client.put(
            "/api/users/me/password",
            json={
                "current_password": "TestPassword123!",
                "new_password": "NewSecurePass456!",
            },
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"},
        )

        # Check audit log
        stmt = select(AuthAuditLog).where(
            AuthAuditLog.user_id == test_user.id,
            AuthAuditLog.event_type == "password_change",
        )
        result = await db_session.execute(stmt)
        audit_entries = result.scalars().all()

        assert len(audit_entries) > 0
        latest = audit_entries[-1]
        assert latest.success is True


class TestInactiveUserAccess:
    """Test that inactive users cannot access protected routes."""

    @pytest.mark.asyncio
    async def test_inactive_user_rejected(
        self, client: AsyncClient, inactive_user_tokens
    ):
        """Verify inactive user cannot access protected endpoints."""
        response = await client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {inactive_user_tokens['access_token']}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "inactive" in response.json()["detail"].lower()
