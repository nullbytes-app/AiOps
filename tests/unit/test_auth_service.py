"""
Unit tests for AuthService (Story 1B).

Tests password hashing, JWT token generation/validation, password policy,
and account lockout logic.

Coverage Target: 90%+
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.auth_service import (
    hash_password,
    verify_password,
    validate_password_strength,
    create_access_token,
    create_refresh_token,
    verify_token,
    authenticate_user,
    handle_failed_login,
    reset_failed_attempts,
    revoke_token,
    is_token_revoked,
    TokenRevokedException,
)
from src.database.models import User
from src.config import get_settings


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password_returns_bcrypt_hash(self):
        """Verify hash_password returns valid bcrypt hash starting with $2b$."""
        password = "TestPassword123!"
        hashed = hash_password(password)

        assert hashed.startswith("$2b$")
        assert len(hashed) > 50
        assert hashed != password

    def test_hash_password_different_salts(self):
        """Verify same password produces different hashes (salting works)."""
        password = "TestPassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2  # Different salts
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)

    def test_hash_password_empty_raises_error(self):
        """Verify empty password raises ValueError."""
        with pytest.raises(ValueError, match="Password cannot be empty"):
            hash_password("")

    def test_verify_password_valid(self):
        """Verify correct password validates successfully."""
        password = "TestPassword123!"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_invalid(self):
        """Verify incorrect password fails validation."""
        password = "TestPassword123!"
        hashed = hash_password(password)

        assert verify_password("WrongPassword123!", hashed) is False


class TestPasswordPolicy:
    """Test password strength validation."""

    def test_validate_password_too_short(self):
        """Verify password < 12 chars rejected."""
        is_valid, error = validate_password_strength("Short1!")
        assert is_valid is False
        assert "at least 12 characters" in error

    def test_validate_password_no_uppercase(self):
        """Verify password without uppercase rejected."""
        is_valid, error = validate_password_strength("testpassword123!")
        assert is_valid is False
        assert "uppercase letter" in error

    def test_validate_password_no_digit(self):
        """Verify password without digit rejected."""
        is_valid, error = validate_password_strength("TestPassword!")
        assert is_valid is False
        assert "number" in error

    def test_validate_password_no_special(self):
        """Verify password without special char rejected."""
        is_valid, error = validate_password_strength("TestPassword123")
        assert is_valid is False
        assert "special character" in error

    def test_validate_password_common_password(self):
        """Verify common password (e.g., 'Password123!') rejected by zxcvbn."""
        # This is a very common weak password pattern
        is_valid, error = validate_password_strength("Password123!")
        assert is_valid is False
        assert "weak" in error.lower() or "common" in error.lower()

    def test_validate_password_success(self):
        """Verify strong password passes all checks."""
        is_valid, error = validate_password_strength("MyStr0ng!P@ssw0rd2024")
        assert is_valid is True
        assert error == ""


class TestJWTTokens:
    """Test JWT token generation and verification."""

    def test_create_access_token_structure(self):
        """Verify access token has correct payload structure (ADR 003)."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="dummy",
            default_tenant_id=uuid4(),
        )

        token = create_access_token(user)
        # Decode without verifying signature (for testing structure only)
        settings = get_settings()
        payload = jwt.decode(
            token,
            key=settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_signature": False},
        )

        # Assert: sub, email, default_tenant_id, iat, exp, jti present
        assert "sub" in payload
        assert "email" in payload
        assert "default_tenant_id" in payload
        assert "iat" in payload
        assert "exp" in payload
        assert "jti" in payload  # JWT ID for uniqueness

        # Assert: roles NOT in payload (ADR 003)
        assert "roles" not in payload
        assert "permissions" not in payload
        assert "tenants" not in payload

    def test_create_access_token_expiration(self):
        """Verify access token expires in configured days (default: 7)."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="dummy",
            default_tenant_id=uuid4(),
        )

        token = create_access_token(user)
        # Decode without verifying signature (for testing expiration only)
        settings = get_settings()
        payload = jwt.decode(
            token,
            key=settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_signature": False},
        )

        exp_timestamp = payload["exp"]
        iat_timestamp = payload["iat"]
        exp_date = datetime.fromtimestamp(exp_timestamp, UTC)
        iat_date = datetime.fromtimestamp(iat_timestamp, UTC)

        delta = exp_date - iat_date
        expected_days = settings.jwt_expiration_days

        assert delta.days == expected_days

    def test_create_refresh_token_expiration(self):
        """Verify refresh token expires in 30 days."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="dummy",
            default_tenant_id=uuid4(),
        )

        token = create_refresh_token(user)
        # Decode without verifying signature (for testing expiration only)
        settings = get_settings()
        payload = jwt.decode(
            token,
            key=settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_signature": False},
        )

        exp_timestamp = payload["exp"]
        iat_timestamp = payload["iat"]
        exp_date = datetime.fromtimestamp(exp_timestamp, UTC)
        iat_date = datetime.fromtimestamp(iat_timestamp, UTC)

        delta = exp_date - iat_date
        expected_days = settings.jwt_refresh_expiration_days

        assert delta.days == expected_days

    @pytest.mark.asyncio
    async def test_verify_token_valid(self):
        """Verify valid token decodes successfully."""
        # Arrange
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)  # Token not revoked

        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="dummy",
            default_tenant_id=uuid4(),
        )

        token = create_access_token(user)

        # Act
        payload = await verify_token(mock_redis, token)

        # Assert
        assert payload["sub"] == str(user.id)
        assert payload["email"] == user.email

    @pytest.mark.asyncio
    async def test_verify_token_expired(self):
        """Verify expired token raises JWTError."""
        # Arrange
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)  # Token not revoked

        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="dummy",
            default_tenant_id=uuid4(),
        )

        # Create token that expired 1 day ago
        token = create_access_token(user, expires_delta=timedelta(days=-1))

        # Act & Assert
        with pytest.raises(JWTError):
            await verify_token(mock_redis, token)

    @pytest.mark.asyncio
    async def test_verify_token_invalid_signature(self):
        """Verify JWT with wrong signature raises JWTError."""
        # Arrange
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)  # Token not revoked

        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="dummy",
            default_tenant_id=uuid4(),
        )

        token = create_access_token(user)

        # Tamper with token (change last character)
        tampered_token = token[:-5] + "XXXXX"

        # Act & Assert
        with pytest.raises(JWTError):
            await verify_token(mock_redis, tampered_token)


class TestAuthentication:
    """Test user authentication with account lockout."""

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self):
        """Verify correct credentials return user and reset counter."""
        # Arrange
        password = "TestPassword123!"
        password_hash = hash_password(password)

        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash=password_hash,
            failed_login_attempts=2,
            locked_until=None,
        )

        # Mock async database session
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=user)

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        # Act
        result = await authenticate_user("test@example.com", password, mock_db)

        # Assert
        assert result == user
        assert user.failed_login_attempts == 0
        # Note: commit is no longer called in service layer (handled by API layer)

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self):
        """Verify wrong password returns None and increments counter."""
        # Arrange
        password = "TestPassword123!"
        password_hash = hash_password(password)

        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash=password_hash,
            failed_login_attempts=1,
            locked_until=None,
        )

        # Mock async database session
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=user)

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        # Act
        result = await authenticate_user("test@example.com", "WrongPassword!", mock_db)

        # Assert
        assert result is None
        assert user.failed_login_attempts == 2
        # Note: commit is no longer called in service layer (handled by API layer)

    @pytest.mark.asyncio
    async def test_authenticate_user_account_locked(self):
        """Verify locked account returns None even with correct password."""
        # Arrange
        password = "TestPassword123!"
        password_hash = hash_password(password)

        # Account locked until 1 hour from now
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash=password_hash,
            failed_login_attempts=5,
            locked_until=datetime.now(UTC) + timedelta(hours=1),
        )

        # Mock async database session
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=user)

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await authenticate_user("test@example.com", password, mock_db)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_user_user_not_found(self):
        """Verify non-existent email returns None (no information disclosure)."""
        # Arrange
        # Mock async database session
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await authenticate_user("nonexistent@example.com", "password", mock_db)

        # Assert
        assert result is None


class TestAccountLockout:
    """Test account lockout logic."""

    @pytest.mark.asyncio
    async def test_handle_failed_login_lockout(self):
        """Verify account locks after configured threshold attempts (default: 5)."""
        # Arrange
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="dummy",
            failed_login_attempts=4,  # One away from lockout
            locked_until=None,
        )

        mock_db = AsyncMock(spec=AsyncSession)

        # Act
        await handle_failed_login(user, mock_db)

        # Assert
        assert user.failed_login_attempts == 5
        assert user.locked_until is not None
        assert user.locked_until > datetime.now(UTC)
        # Note: commit is no longer called in service layer (handled by API layer)

    @pytest.mark.asyncio
    async def test_reset_failed_attempts(self):
        """Verify successful login resets counter and clears lockout."""
        # Arrange
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="dummy",
            failed_login_attempts=3,
            locked_until=datetime.now(UTC) + timedelta(minutes=15),
        )

        mock_db = AsyncMock(spec=AsyncSession)

        # Act
        await reset_failed_attempts(user, mock_db)

        # Assert
        assert user.failed_login_attempts == 0
        assert user.locked_until is None
        # Note: commit is no longer called in service layer (handled by API layer)


class TestTokenRevocation:
    """Test JWT token revocation via Redis blacklist."""

    @pytest.mark.asyncio
    async def test_revoke_token_adds_to_redis(self):
        """Verify revoke_token() adds token to Redis blacklist with TTL."""
        # Arrange
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()

        user = User(
            id=uuid4(),
            email="test@example.com",
            default_tenant_id=uuid4(),
        )
        token = create_access_token(user)

        # Act
        await revoke_token(mock_redis, token)

        # Assert
        # Verify Redis set was called
        assert mock_redis.set.called
        # Verify key starts with "revoked:"
        call_args = mock_redis.set.call_args[0]
        assert call_args[0].startswith("revoked:")
        # Verify value is "1"
        assert call_args[1] == "1"
        # Verify TTL (ex parameter) was set
        assert mock_redis.set.call_args[1]["ex"] > 0

    @pytest.mark.asyncio
    async def test_is_token_revoked_returns_true_for_revoked_token(self):
        """Verify is_token_revoked() returns True for blacklisted token."""
        # Arrange
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="1")  # Token exists in blacklist

        user = User(
            id=uuid4(),
            email="test@example.com",
            default_tenant_id=uuid4(),
        )
        token = create_access_token(user)

        # Act
        result = await is_token_revoked(mock_redis, token)

        # Assert
        assert result is True
        assert mock_redis.get.called

    @pytest.mark.asyncio
    async def test_is_token_revoked_returns_false_for_valid_token(self):
        """Verify is_token_revoked() returns False for non-blacklisted token."""
        # Arrange
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)  # Token NOT in blacklist

        user = User(
            id=uuid4(),
            email="test@example.com",
            default_tenant_id=uuid4(),
        )
        token = create_access_token(user)

        # Act
        result = await is_token_revoked(mock_redis, token)

        # Assert
        assert result is False
        assert mock_redis.get.called

    @pytest.mark.asyncio
    async def test_verify_token_raises_exception_for_revoked_token(self):
        """Verify verify_token() raises TokenRevokedException for revoked token."""
        # Arrange
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="1")  # Token is revoked

        user = User(
            id=uuid4(),
            email="test@example.com",
            default_tenant_id=uuid4(),
        )
        token = create_access_token(user)

        # Act & Assert
        with pytest.raises(TokenRevokedException) as exc_info:
            await verify_token(mock_redis, token)

        assert "revoked" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_verify_token_succeeds_for_valid_non_revoked_token(self):
        """Verify verify_token() succeeds for valid, non-revoked token."""
        # Arrange
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)  # Token NOT revoked

        user_id = uuid4()
        user = User(
            id=user_id,
            email="test@example.com",
            default_tenant_id=uuid4(),
        )
        token = create_access_token(user)

        # Act
        payload = await verify_token(mock_redis, token)

        # Assert
        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["email"] == "test@example.com"
        assert "exp" in payload
        assert "iat" in payload
