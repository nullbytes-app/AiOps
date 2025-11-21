"""
Test fixtures for authentication tests.

Provides:
- test_user: Active user with hashed password
- locked_user: User with account locked (5+ failed attempts)
- inactive_user: User with is_active=False
- auth_tokens: Access and refresh tokens for test_user
- expired_access_token: Expired access token for testing
- expired_refresh_token: Expired refresh token for testing

Story: 1C - API Endpoints & Middleware
"""

import pytest
from datetime import datetime, UTC, timedelta
from uuid import uuid4
from httpx import AsyncClient

from src.database.models import User
from src.services.auth_service import hash_password, AuthService


@pytest.fixture
async def test_user(async_db_session):
    """
    Create active test user with known password.

    Email: test-{uuid}@example.com (unique per test)
    Password: TestPassword123!
    """
    tenant_id = uuid4()
    # Use unique email to avoid conflicts between tests
    unique_email = f"test-{uuid4().hex[:8]}@example.com"
    user = User(
        email=unique_email,
        password_hash=hash_password("TestPassword123!"),
        default_tenant_id=tenant_id,
        is_active=True,
        failed_login_attempts=0,
        locked_until=None,
        password_expires_at=datetime.now(UTC) + timedelta(days=90),
        password_history=[],
    )
    async_db_session.add(user)
    await async_db_session.flush()  # Flush to get ID, but don't commit
    await async_db_session.refresh(user)
    return user


@pytest.fixture
async def locked_user(async_db_session):
    """
    Create locked user (5+ failed attempts, locked for 15 min).

    Email: locked-{uuid}@example.com (unique per test)
    Password: TestPassword123!
    """
    tenant_id = uuid4()
    unique_email = f"locked-{uuid4().hex[:8]}@example.com"
    user = User(
        email=unique_email,
        password_hash=hash_password("TestPassword123!"),
        default_tenant_id=tenant_id,
        is_active=True,
        failed_login_attempts=5,
        locked_until=datetime.now(UTC) + timedelta(minutes=15),
        password_expires_at=datetime.now(UTC) + timedelta(days=90),
        password_history=[],
    )
    async_db_session.add(user)
    await async_db_session.flush()  # Flush to get ID, but don't commit
    await async_db_session.refresh(user)
    return user


@pytest.fixture
async def inactive_user(async_db_session):
    """
    Create inactive user (is_active=False).

    Email: inactive-{uuid}@example.com (unique per test)
    Password: TestPassword123!
    """
    tenant_id = uuid4()
    unique_email = f"inactive-{uuid4().hex[:8]}@example.com"
    user = User(
        email=unique_email,
        password_hash=hash_password("TestPassword123!"),
        default_tenant_id=tenant_id,
        is_active=False,  # Inactive
        failed_login_attempts=0,
        locked_until=None,
        password_expires_at=datetime.now(UTC) + timedelta(days=90),
        password_history=[],
    )
    async_db_session.add(user)
    await async_db_session.flush()  # Flush to get ID, but don't commit
    await async_db_session.refresh(user)
    return user


@pytest.fixture
async def auth_tokens(client: AsyncClient, test_user):
    """
    Login test_user and return access + refresh tokens.

    Returns:
        dict: {"access_token": str, "refresh_token": str}
    """
    response = await client.post(
        "/api/auth/token",
        data={
            "username": test_user.email,
            "password": "TestPassword123!",
        },
    )
    return response.json()


@pytest.fixture
async def inactive_user_tokens(client: AsyncClient, inactive_user, async_db_session):
    """
    Create tokens for inactive user (for testing rejection).

    Note: Tokens are created directly (bypassing login) since inactive
    users shouldn't be able to login normally.

    Returns:
        dict: {"access_token": str, "refresh_token": str}
    """
    from src.services.auth_service import create_access_token, create_refresh_token

    access_token = create_access_token(inactive_user)
    refresh_token = create_refresh_token(inactive_user)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


@pytest.fixture
async def expired_access_token():
    """
    Create an expired access token for testing expiration handling.

    Returns:
        str: Expired JWT access token
    """
    from jose import jwt
    from src.config import settings
    from uuid import uuid4

    # Create token that expired 1 hour ago
    exp = datetime.now(UTC) - timedelta(hours=1)
    payload = {
        "sub": str(uuid4()),
        "exp": exp,
        "type": "access",
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token


@pytest.fixture
async def expired_refresh_token():
    """
    Create an expired refresh token for testing expiration handling.

    Returns:
        str: Expired JWT refresh token
    """
    from jose import jwt
    from src.config import settings
    from uuid import uuid4

    # Create token that expired 1 day ago
    exp = datetime.now(UTC) - timedelta(days=1)
    payload = {
        "sub": str(uuid4()),
        "exp": exp,
        "type": "refresh",
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token
