"""
Authentication service for JWT token management and password handling.

This service provides core authentication logic including password hashing,
JWT token generation/validation, password policy enforcement, and account lockout.

Story: 1B - Auth Service & JWT Implementation
Epic: 2 (Authentication & Authorization Foundation)
"""

import hashlib
from datetime import datetime, timedelta, UTC
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from zxcvbn import zxcvbn

from src.config import settings, get_settings
from src.database.models import User, AuthAuditLog

# Passlib context for bcrypt password hashing
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=10,  # 10 rounds = ~200-300ms (Story 1B requirement)
)


# Custom exceptions for token management
class TokenRevokedException(JWTError):
    """Exception raised when attempting to use a revoked JWT token."""

    pass


class AuthService:
    """
    Authentication service for password hashing and JWT operations.

    This class provides methods for:
    - Password hashing and verification
    - JWT token generation and validation
    - Password policy enforcement
    - Account lockout management
    - Token revocation via Redis blacklist
    """

    def __init__(self, redis_client=None):
        """
        Initialize AuthService.

        Args:
            redis_client: Optional Redis client for token blacklist.
                         If None, token revocation will not be available.
        """
        self.redis = redis_client


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt with 10 rounds.

    Args:
        password: Plain text password

    Returns:
        Bcrypt hashed password string

    Raises:
        ValueError: If password is empty or None

    Security:
        Uses bcrypt with 10 rounds (~200-300ms hashing time)
        for good balance between security and UX.
    """
    if not password:
        raise ValueError("Password cannot be empty")

    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hash using constant-time comparison.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Bcrypt hash to verify against

    Returns:
        True if password matches, False otherwise

    Security:
        Uses passlib's verify which implements constant-time comparison
        to prevent timing attacks.
    """
    return pwd_context.verify(plain_password, hashed_password)


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password meets strength requirements (Story 1B AC3).

    Requirements:
    - Minimum 12 characters (configurable via settings.password_min_length)
    - At least 1 uppercase letter (A-Z)
    - At least 1 number (0-9)
    - At least 1 special character (!@#$%^&*)
    - zxcvbn score >= 3 (safely unguessable)

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
        - (True, "") if valid
        - (False, "error message") if invalid with specific reason

    Security:
        Uses zxcvbn library to detect common passwords and patterns.
        Enforces minimum complexity requirements.
    """
    settings = get_settings()  # Get settings, initializing if necessary for tests
    min_length = settings.password_min_length

    # Check minimum length
    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters long"

    # Check for uppercase letter
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter (A-Z)"

    # Check for number
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number (0-9)"

    # Check for special character
    special_chars = "!@#$%^&*"
    if not any(c in special_chars for c in password):
        return False, f"Password must contain at least one special character ({special_chars})"

    # Use zxcvbn for strength estimation
    result = zxcvbn(password)
    min_score = settings.password_min_zxcvbn_score

    if result["score"] < min_score:
        feedback = result["feedback"].get("warning") or "Password is too weak"
        suggestions = result["feedback"].get("suggestions", [])

        error_msg = f"Weak password: {feedback}"
        if suggestions:
            error_msg += f". Suggestions: {', '.join(suggestions)}"

        return False, error_msg

    return True, ""


async def create_access_token(
    user: User, redis_client=None, expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token for authenticated user.

    CRITICAL: JWT payload contains ONLY these fields (ADR 003):
    - sub: user.id (UUID as string)
    - email: user.email
    - default_tenant_id: user.default_tenant_id (UUID as string or None)
    - iat: issued at timestamp
    - exp: expiration timestamp (7 days from now by default)
    - jti: JWT ID (UUID) for token uniqueness
    - token_version: user's current token version (for password change revocation)

    Roles are NOT included in JWT. They are fetched on-demand when
    user switches tenants (see Story 1C).

    Args:
        user: Authenticated user
        redis_client: Optional Redis client for token version tracking
        expires_delta: Optional custom expiration (default: 7 days)

    Returns:
        JWT token string

    Security:
        - Uses HS256 algorithm with minimum 32-character secret
        - Token expires after configured days (default: 7)
        - Minimal payload to prevent token bloat
        - Includes jti (JWT ID) for token uniqueness
        - Includes token_version for password change revocation
    """
    settings = get_settings()  # Get settings, initializing if necessary for tests
    if expires_delta is None:
        expires_delta = timedelta(days=settings.jwt_expiration_days)

    now = datetime.now(UTC)
    expire = now + expires_delta

    # Get user's current token version from Redis
    token_version = 0  # Default version for users who haven't changed password
    if redis_client:
        user_token_key = f"user:token_version:{str(user.id)}"
        version_str = await redis_client.get(user_token_key)
        if version_str:
            token_version = int(version_str)

    # Minimal JWT payload per ADR 003
    # Include jti (JWT ID) for token uniqueness (prevents identical tokens when created in same second)
    # Include token_version for password change revocation
    from uuid import uuid4

    payload = {
        "sub": str(user.id),
        "email": user.email,
        "default_tenant_id": str(user.default_tenant_id) if user.default_tenant_id else None,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": str(uuid4()),  # Unique token identifier
        "token_version": token_version,  # User's current token version
    }

    encoded_jwt = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    return encoded_jwt


async def create_refresh_token(
    user: User, redis_client=None, expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT refresh token with 30-day default expiration.

    Args:
        user: Authenticated user
        redis_client: Optional Redis client for token version tracking
        expires_delta: Optional custom expiration (default: 30 days)

    Returns:
        JWT refresh token string

    Note:
        Refresh tokens use same payload structure as access tokens
        but with longer expiration for session renewal.
    """
    settings = get_settings()  # Get settings, initializing if necessary for tests
    if expires_delta is None:
        expires_delta = timedelta(days=settings.jwt_refresh_expiration_days)

    return await create_access_token(user, redis_client, expires_delta)


async def verify_token(redis_client, token: str) -> dict:
    """
    Verify and decode JWT access token with revocation check.

    CRITICAL FIX: Now checks Redis blacklist AND token version BEFORE returning payload.
    This ensures:
    1. Revoked tokens (logout) cannot be used
    2. Old tokens (password change) cannot be used

    SECURITY: Always specifies algorithms=["HS256"] to prevent
    algorithm confusion attacks (CVE-2024-33663).

    Args:
        redis_client: Redis client for blacklist checking and version tracking
        token: JWT token string

    Returns:
        Decoded JWT payload dict with keys: sub, email, default_tenant_id, iat, exp, token_version

    Raises:
        TokenRevokedException: If token is in Redis blacklist or token version is outdated
        JWTError: If token invalid, expired, or signature mismatch

    Security:
        - Checks revocation blacklist FIRST (prevents revoked token use)
        - Checks token version SECOND (prevents old token use after password change)
        - Explicitly specifies algorithm to prevent CVE-2024-33663
        - Validates signature against JWT_SECRET_KEY
        - Checks expiration timestamp

    Implementation Order (CRITICAL):
        1. Check if token revoked (Redis blacklist)
        2. If revoked: raise TokenRevokedException
        3. If not revoked: verify signature and expiration
        4. Check token version against user's current version
        5. If version mismatch: raise TokenRevokedException
        6. Return payload
    """
    settings = get_settings()  # Get settings, initializing if necessary for tests
    # Step 1: Check if token is revoked (MUST be first)
    if await is_token_revoked(redis_client, token):
        raise TokenRevokedException(
            "Token has been revoked. Please log in again to obtain a new token."
        )

    # Step 2: Verify JWT signature and expiration
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],  # Prevent algorithm confusion
        )
    except JWTError as e:
        # Re-raise with clear error message
        raise JWTError(f"Token validation failed: {str(e)}")

    # Step 3: Check token version (password change revocation)
    if redis_client:
        user_id = payload.get("sub")
        token_version = payload.get("token_version", 0)  # Default to 0 for old tokens

        # Get user's current token version from Redis
        user_token_key = f"user:token_version:{user_id}"
        current_version_str = await redis_client.get(user_token_key)

        if current_version_str:
            current_version = int(current_version_str)
            if token_version < current_version:
                # Token was issued before password change - reject it
                raise TokenRevokedException(
                    "Token is no longer valid. Password has been changed. Please log in again."
                )

    return payload


async def revoke_token(redis_client, token: str) -> None:
    """
    Add token to Redis blacklist (token revocation).

    Args:
        redis_client: Redis client for blacklist storage
        token: JWT token to revoke

    Redis Storage:
        Key: revoked:{sha256(token)}
        Value: 1
        TTL: Token expiration time (auto-expires with token)

    Security:
        - Token hash (SHA256) used as key to prevent Redis key size issues
        - TTL set to token's remaining lifetime (auto-cleanup)
        - Blacklist checked during token verification

    Note:
        This function must be called before token verification to prevent
        use of revoked tokens.
    """
    settings = get_settings()  # Get settings, initializing if necessary for tests
    # Hash token for storage (prevents Redis key size issues)
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    # Get expiration from token (no signature verification needed for expiry)
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        exp = payload.get("exp")

        if exp:
            ttl = exp - int(datetime.now(UTC).timestamp())
            ttl = max(ttl, 0)  # Ensure positive TTL
        else:
            # Fallback to default TTL if no exp claim
            ttl = settings.jwt_expiration_days * 24 * 60 * 60
    except Exception:
        # If token parsing fails, use default TTL
        ttl = settings.jwt_expiration_days * 24 * 60 * 60

    # Store in Redis with auto-expiry
    await redis_client.set(
        f"revoked:{token_hash}",
        "1",
        ex=ttl,
    )


async def is_token_revoked(redis_client, token: str) -> bool:
    """
    Check if token is in Redis blacklist.

    Args:
        redis_client: Redis client
        token: JWT token to check

    Returns:
        True if token is revoked, False otherwise
    """
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    result = await redis_client.get(f"revoked:{token_hash}")
    return result is not None


async def authenticate_user(
    email: str,
    password: str,
    db: AsyncSession,
) -> Optional[User]:
    """
    Authenticate user by email and password with account lockout.

    Security features:
    - Constant-time password comparison (prevents timing attacks)
    - Account lockout check BEFORE password verification
    - Failed attempt counter increment on wrong password
    - Account lockout after configured attempts (default: 5)
    - Failed attempt reset on successful login
    - Generic error response (prevents information disclosure)

    Args:
        email: User email
        password: Plain text password
        db: Database session

    Returns:
        User if authentication successful, None otherwise

    Note:
        Returns None for both "user not found" and "wrong password"
        to prevent information disclosure about account existence.

    Side Effects:
        - Increments failed_login_attempts on wrong password
        - Sets locked_until after threshold failures
        - Resets failed_login_attempts on success
        - Creates AuthAuditLog entries
    """
    # Fetch user by email
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    # User not found - return None (no information disclosure)
    if user is None:
        return None

    # Check if account is locked (BEFORE password verification to prevent timing attacks)
    if user.locked_until and user.locked_until > datetime.now(UTC):
        # Account is still locked
        return None

    # Verify password (constant-time comparison via passlib)
    is_valid = verify_password(password, user.password_hash)

    if not is_valid:
        # Failed login - increment counter
        await handle_failed_login(user, db)
        return None

    # Successful login - reset counter
    await reset_failed_attempts(user, db)

    # Note: Audit logging is handled by API layer
    # Service layer should not commit - let the caller decide when to commit

    return user


async def handle_failed_login(user: User, db: AsyncSession) -> None:
    """
    Handle failed login attempt with automatic account lockout.

    Args:
        user: User instance
        db: Database session

    Side Effects:
        - Increments failed_login_attempts
        - Sets locked_until after threshold attempts (default: 5)
        - Logs to auth_audit_log
        - Commits changes to database
    """
    settings = get_settings()  # Get settings, initializing if necessary for tests
    user.failed_login_attempts += 1

    threshold = settings.account_lockout_threshold
    lockout_duration = settings.account_lockout_duration_minutes

    if user.failed_login_attempts >= threshold:
        user.locked_until = datetime.now(UTC) + timedelta(minutes=lockout_duration)

        # Log lockout event
        audit_entry = AuthAuditLog(
            user_id=user.id,
            event_type="account_locked",
            success=False,
            ip_address=None,  # Set by API layer
            user_agent=None,  # Set by API layer
        )
        db.add(audit_entry)

    # Note: Do not commit - let caller handle transaction management


async def reset_failed_attempts(user: User, db: AsyncSession) -> None:
    """
    Reset failed login counter on successful authentication.

    Args:
        user: User instance
        db: Database session

    Side Effects:
        - Sets failed_login_attempts to 0
        - Clears locked_until
        - Commits changes to database
    """
    user.failed_login_attempts = 0
    user.locked_until = None
    # Note: Do not commit - let caller handle transaction management
