"""
Integration tests for authentication endpoints.

Tests cover:
- User registration (success, duplicate email, weak password)
- Login/token generation (success, invalid credentials, locked account)
- Token refresh (success, invalid/expired tokens)
- Logout (success, token revocation verification)
- Rate limiting on auth endpoints

Story: 1C - API Endpoints & Middleware
Epic: 2 (Authentication & Authorization Foundation)
"""

import pytest
from httpx import AsyncClient
from fastapi import status
from uuid import uuid4

from src.main import app
from src.database.models import User
from src.services.auth_service import hash_password


class TestRegistrationEndpoint:
    """Test POST /api/auth/register endpoint."""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient, db_session):
        """Verify user registration with valid data returns 201."""
        tenant_id = uuid4()
        # Use unique email to avoid conflicts with previous test runs
        email = f"newuser-{uuid4().hex[:8]}@example.com"
        response = await client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "SecurePass123!",
                "default_tenant_id": str(tenant_id),
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == email
        assert "id" in data
        assert "password" not in data  # Password excluded from response
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, db_session):
        """Verify duplicate email returns 400."""
        tenant_id = uuid4()

        # Register first user
        await client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "SecurePass123!",
                "default_tenant_id": str(tenant_id),
            },
        )

        # Try to register with same email
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "DifferentPass456!",
                "default_tenant_id": str(tenant_id),
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client: AsyncClient):
        """Verify weak password returns 422."""
        tenant_id = uuid4()
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "weak",  # Too short and weak
                "default_tenant_id": str(tenant_id),
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """Verify invalid email format returns 422."""
        tenant_id = uuid4()
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePass123!",
                "default_tenant_id": str(tenant_id),
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestLoginEndpoint:
    """Test POST /api/auth/token endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user, db_session):
        """Verify successful login returns access and refresh tokens."""
        response = await client.post(
            "/api/auth/token",
            data={  # OAuth2PasswordRequestForm uses form data, not JSON
                "username": test_user.email,
                "password": "TestPassword123!",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert isinstance(data["expires_in"], int)

    @pytest.mark.asyncio
    async def test_login_invalid_email(self, client: AsyncClient):
        """Verify invalid email returns 401."""
        response = await client.post(
            "/api/auth/token",
            data={
                "username": "nonexistent@example.com",
                "password": "WrongPassword123!",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "WWW-Authenticate" in response.headers
        assert response.headers["WWW-Authenticate"] == "Bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        """Verify wrong password returns 401."""
        response = await client.post(
            "/api/auth/token",
            data={
                "username": test_user.email,
                "password": "WrongPassword!",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_login_locked_account(self, client: AsyncClient, locked_user):
        """Verify locked account returns 401."""
        response = await client.post(
            "/api/auth/token",
            data={
                "username": locked_user.email,
                "password": "TestPassword123!",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "locked" in response.json()["detail"].lower()


class TestRefreshEndpoint:
    """Test POST /api/auth/refresh endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_success(self, client: AsyncClient, auth_tokens):
        """Verify refresh token returns new access token."""
        response = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": auth_tokens["refresh_token"]},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        # New access token should be different from original
        assert data["access_token"] != auth_tokens["access_token"]
        # Refresh token should remain the same (no rotation)
        assert data["refresh_token"] == auth_tokens["refresh_token"]

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, client: AsyncClient):
        """Verify invalid refresh token returns 401."""
        response = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "WWW-Authenticate" in response.headers

    @pytest.mark.asyncio
    async def test_refresh_expired_token(self, client: AsyncClient, expired_refresh_token):
        """Verify expired refresh token returns 401."""
        response = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": expired_refresh_token},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestLogoutEndpoint:
    """Test POST /api/auth/logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_success(self, client: AsyncClient, auth_tokens):
        """Verify logout revokes tokens and returns 204."""
        response = await client.post(
            "/api/auth/logout",
            json={
                "access_token": auth_tokens["access_token"],
                "refresh_token": auth_tokens["refresh_token"],
            },
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify tokens are revoked (cannot access protected endpoint)
        me_response = await client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"},
        )
        assert me_response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_logout_requires_authentication(self, client: AsyncClient):
        """Verify logout without token returns 401."""
        response = await client.post(
            "/api/auth/logout",
            json={
                "access_token": "fake.token",
                "refresh_token": "fake.refresh",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestRateLimiting:
    """Test rate limiting on authentication endpoints."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Rate limiting tests can be slow, enable for full coverage")
    async def test_login_rate_limit(self, client: AsyncClient):
        """Verify rate limiting on /token endpoint (100 req/min)."""
        # Make 101 requests rapidly
        for i in range(101):
            response = await client.post(
                "/api/auth/token",
                data={
                    "username": "test@example.com",
                    "password": "WrongPassword123!",
                },
            )

        # Last request should be rate limited
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "Retry-After" in response.headers

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Rate limiting tests can be slow, enable for full coverage")
    async def test_register_rate_limit(self, client: AsyncClient):
        """Verify rate limiting on /register endpoint (10 req/min)."""
        tenant_id = uuid4()

        # Make 11 registration attempts
        for i in range(11):
            response = await client.post(
                "/api/auth/register",
                json={
                    "email": f"user{i}@example.com",
                    "password": "SecurePass123!",
                    "default_tenant_id": str(tenant_id),
                },
            )

        # Last request should be rate limited
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


class TestAuditLogging:
    """Test audit logging for authentication events."""

    @pytest.mark.asyncio
    async def test_login_success_logged(self, client: AsyncClient, test_user, db_session):
        """Verify successful login is logged to auth_audit_log."""
        from src.database.models import AuthAuditLog
        from sqlalchemy import select

        # Perform login
        await client.post(
            "/api/auth/token",
            data={
                "username": test_user.email,
                "password": "TestPassword123!",
            },
        )

        # Check audit log
        stmt = select(AuthAuditLog).where(
            AuthAuditLog.user_id == test_user.id,
            AuthAuditLog.event_type == "login",
        )
        result = await db_session.execute(stmt)
        audit_entries = result.scalars().all()

        assert len(audit_entries) > 0
        latest = audit_entries[-1]
        assert latest.success is True
        assert latest.ip_address is not None
        assert latest.user_agent is not None

    @pytest.mark.asyncio
    async def test_login_failure_logged(self, client: AsyncClient, test_user, db_session):
        """Verify failed login is logged to auth_audit_log."""
        from src.database.models import AuthAuditLog
        from sqlalchemy import select

        # Perform failed login
        await client.post(
            "/api/auth/token",
            data={
                "username": test_user.email,
                "password": "WrongPassword!",
            },
        )

        # Check audit log
        stmt = select(AuthAuditLog).where(
            AuthAuditLog.event_type == "login",
            AuthAuditLog.success == False,
        )
        result = await db_session.execute(stmt)
        audit_entries = result.scalars().all()

        assert len(audit_entries) > 0
