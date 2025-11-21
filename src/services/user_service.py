"""
User management service for CRUD operations.

This service provides user management functions including creation,
retrieval, password updates with password history enforcement, and
role management.

Story: 1B - Auth Service & JWT Implementation
Epic: 2 (Authentication & Authorization Foundation)
"""

from datetime import datetime, timedelta, UTC
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings, get_settings
from src.database.models import User, UserTenantRole, RoleEnum
from src.services.auth_service import hash_password, validate_password_strength, verify_password


class UserService:
    """
    User management service for CRUD operations and role assignment.

    This class provides methods for:
    - User creation with password validation
    - User retrieval by email and ID
    - User updates
    - Soft deletion
    - Password history enforcement
    - Role assignment and retrieval
    """

    async def create_user(
        self,
        email: str,
        password: str,
        default_tenant_id: UUID,
        db: AsyncSession,
    ) -> User:
        """
        Create new user account with hashed password.

        Steps:
        1. Validate password strength
        2. Hash password with bcrypt
        3. Create user record
        4. Set password_expires_at (90 days from now by default)
        5. Save to database

        Args:
            email: User email (must be unique)
            password: Plain text password
            default_tenant_id: User's default tenant UUID
            db: Database session

        Returns:
            Created User object

        Raises:
            ValueError: If password validation fails
            IntegrityError: If email already exists (from SQLAlchemy)

        Security:
            - Password strength validated before hashing
            - Password hashed with bcrypt (10 rounds)
            - Password expiration set automatically
        """
        # Validate password strength
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            raise ValueError(error_msg)

        # Hash password
        password_hash = hash_password(password)

        # Get settings (initializing if necessary for tests)
        settings = get_settings()

        # Calculate password expiration
        password_expires_at = datetime.now(UTC) + timedelta(
            days=settings.password_expiration_days
        )

        # Create user
        user = User(
            email=email,
            password_hash=password_hash,
            default_tenant_id=default_tenant_id,
            password_expires_at=password_expires_at,
            failed_login_attempts=0,
            password_history=[],
            is_active=True,  # Explicitly set default value for Pydantic validation
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        return user

    async def get_user_by_email(
        self,
        email: str,
        db: AsyncSession,
    ) -> Optional[User]:
        """
        Retrieve user by email address.

        Args:
            email: User email
            db: Database session

        Returns:
            User if found, None otherwise

        Security:
            Uses parameterized queries to prevent SQL injection
        """
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_id(
        self,
        user_id: UUID,
        db: AsyncSession,
    ) -> Optional[User]:
        """
        Retrieve user by UUID.

        Args:
            user_id: User UUID
            db: Database session

        Returns:
            User if found, None otherwise
        """
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_user(
        self,
        user_id: UUID,
        updates: dict,
        db: AsyncSession,
    ) -> User:
        """
        Update user fields.

        Args:
            user_id: User UUID
            updates: Dict of fields to update
            db: Database session

        Returns:
            Updated User instance

        Raises:
            ValueError: If user not found

        Note:
            Does not allow updating password directly.
            Use update_password() for password changes.
        """
        user = await self.get_user_by_id(user_id, db)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        # Remove password fields if present (use update_password instead)
        updates.pop("password", None)
        updates.pop("password_hash", None)

        # Update fields
        for key, value in updates.items():
            if hasattr(user, key):
                setattr(user, key, value)

        await db.commit()
        await db.refresh(user)

        return user

    async def delete_user(
        self,
        user_id: UUID,
        db: AsyncSession,
    ) -> None:
        """
        Soft delete user (set deleted flag).

        Args:
            user_id: User UUID
            db: Database session

        Raises:
            ValueError: If user not found

        Note:
            This is a soft delete. The user record remains in the database
            but is marked as deleted. Implement User.deleted_at field if needed.
        """
        user = await self.get_user_by_id(user_id, db)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        # Note: Story 1A User model doesn't have deleted_at field
        # This would need to be added in a future story
        # For now, just raise not implemented
        raise NotImplementedError(
            "Soft delete not implemented. User model needs deleted_at field."
        )

    async def update_password(
        self,
        user: User,
        new_password: str,
        db: AsyncSession,
    ) -> User:
        """
        Update user password with history check.

        Steps:
        1. Validate password strength
        2. Hash new password
        3. Check password history (reject if reused)
        4. Update password_hash
        5. Add old hash to password_history (trim to 5)
        6. Set new password_expires_at (90 days from now)
        7. Save to database

        Args:
            user: User to update
            new_password: New plain text password
            db: Database session

        Returns:
            Updated User object

        Raises:
            ValueError: If password invalid or reused

        Security:
            - Validates password strength
            - Checks last 5 passwords to prevent reuse
            - Maintains password history for audit
        """
        # Get settings (initializing if necessary for tests)
        settings = get_settings()

        # Validate password strength
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            raise ValueError(error_msg)

        # Hash new password
        new_hash = hash_password(new_password)

        # Check password history (use plain password, not hash)
        if self.check_password_history(user, new_password):
            raise ValueError(
                "You cannot reuse any of your last 5 passwords. Please choose a new password."
            )

        # Update password
        old_hash = user.password_hash
        user.password_hash = new_hash

        # Update password history (prepend old hash, trim to 5)
        history = user.password_history or []
        history.insert(0, old_hash)
        user.password_history = history[:5]  # Keep only last 5

        # Set new expiration
        user.password_expires_at = datetime.now(UTC) + timedelta(
            days=settings.password_expiration_days
        )

        await db.commit()
        await db.refresh(user)

        return user

    def check_password_history(self, user: User, new_password: str) -> bool:
        """
        Check if new password was used in password history.

        CRITICAL FIX: Now accepts plain text password and verifies against each
        historical hash using verify_password(). This is the ONLY correct way to
        check password reuse with bcrypt, as bcrypt hashes include random salts.

        Args:
            user: User object
            new_password: New PLAIN TEXT password to check

        Returns:
            True if password was previously used, False otherwise

        Security:
            Uses verify_password() for constant-time comparison against each
            historical hash. This prevents:
            1. Password reuse (primary security goal)
            2. Timing attacks (constant-time verification)

        Implementation:
            For each hash in password_history, verify the plain password against
            that hash. If any match, the password has been used before.
        """
        history = user.password_history or []

        # Check if new password matches any password in history
        # MUST use verify_password() because bcrypt hashes have random salts
        # Direct hash comparison would NEVER match (bcrypt design)
        for old_hash in history:
            if verify_password(new_password, old_hash):
                return True  # Password reused - REJECT

        return False  # Password unique - ACCEPT

    async def get_user_role_for_tenant(
        self,
        user_id: UUID,
        tenant_id: str,
        db: AsyncSession,
    ) -> Optional[RoleEnum]:
        """
        Fetch user's role for specific tenant.

        Args:
            user_id: User UUID
            tenant_id: Tenant identifier
            db: Database session

        Returns:
            Role enum or None if no role assigned

        Critical:
            Roles fetched on-demand, not from JWT (ADR 003).
            This prevents token bloat for users with access to many tenants.
        """
        stmt = (
            select(UserTenantRole)
            .where(UserTenantRole.user_id == user_id)
            .where(UserTenantRole.tenant_id == tenant_id)
        )
        result = await db.execute(stmt)
        user_tenant_role = result.scalar_one_or_none()

        if user_tenant_role:
            return user_tenant_role.role

        return None

    async def assign_role(
        self,
        user_id: UUID,
        tenant_id: str,
        role: RoleEnum,
        db: AsyncSession,
    ) -> None:
        """
        Assign role to user for tenant.

        Args:
            user_id: User UUID
            tenant_id: Tenant identifier
            role: Role enum value
            db: Database session

        Side Effects:
            - Creates UserTenantRole entry if not exists
            - Updates role if entry exists (idempotent via UPSERT logic)

        Note:
            Uses manual idempotency check instead of ON CONFLICT
            due to SQLAlchemy async limitations.
        """
        # Check if role assignment exists
        stmt = (
            select(UserTenantRole)
            .where(UserTenantRole.user_id == user_id)
            .where(UserTenantRole.tenant_id == tenant_id)
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing role
            existing.role = role
        else:
            # Create new role assignment
            user_tenant_role = UserTenantRole(
                user_id=user_id,
                tenant_id=tenant_id,
                role=role,
            )
            db.add(user_tenant_role)

        await db.commit()
