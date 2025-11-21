"""
Unit tests for User, UserTenantRole, and AuthAuditLog models (Story 1A).

Tests cover:
- User model creation and validation
- UserTenantRole model with role enum
- AuthAuditLog model for authentication events
- Updated AuditLog model with tenant and entity fields
- Database constraints (unique email, composite unique user+tenant)
- Relationships and foreign keys
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    User,
    UserTenantRole,
    RoleEnum,
    AuthAuditLog,
    AuditLog
)


class TestUserModel:
    """Tests for User model."""

    @pytest.mark.asyncio
    async def test_create_user_success(self, async_db_session: AsyncSession):
        """Test creating a user with all required fields."""
        # Arrange - Use unique email to avoid conflicts
        email = f"test-{uuid4()}@example.com"
        password_hash = "hashed_password_123"
        default_tenant_id = uuid4()

        # Act
        user = User(
            email=email,
            password_hash=password_hash,
            default_tenant_id=default_tenant_id,
            failed_login_attempts=0,
            password_history=[],
        )
        async_db_session.add(user)
        await async_db_session.commit()

        # Assert
        result = await async_db_session.execute(
            select(User).where(User.email == email)
        )
        saved_user = result.scalar_one()
        assert saved_user.email == email
        assert saved_user.password_hash == password_hash
        assert saved_user.default_tenant_id == default_tenant_id
        assert saved_user.failed_login_attempts == 0
        assert saved_user.locked_until is None
        assert saved_user.password_expires_at is None
        assert saved_user.password_history == []
        assert saved_user.created_at is not None
        assert saved_user.updated_at is not None

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email_fails(self, async_db_session: AsyncSession):
        """Test that creating a user with duplicate email fails (unique constraint)."""
        # Arrange - Use unique base email per test run
        email = f"duplicate-{uuid4()}@example.com"
        user1 = User(
            email=email,
            password_hash="hash1",
            failed_login_attempts=0,
            password_history=[],
        )
        async_db_session.add(user1)
        await async_db_session.commit()

        # Act & Assert - Try to create another user with same email
        user2 = User(
            email=email,  # Same email as user1
            password_hash="hash2",
            failed_login_attempts=0,
            password_history=[],
        )
        async_db_session.add(user2)
        with pytest.raises(IntegrityError):
            await async_db_session.commit()

    @pytest.mark.asyncio
    async def test_user_account_lockout(self, async_db_session: AsyncSession):
        """Test setting account lockout after failed login attempts."""
        # Arrange - Use unique email
        user = User(
            email=f"lockout-{uuid4()}@example.com",
            password_hash="hash",
            failed_login_attempts=0,
            password_history=[],
        )
        async_db_session.add(user)
        await async_db_session.commit()

        # Act: Simulate 5 failed login attempts
        from datetime import UTC
        user.failed_login_attempts = 5
        user.locked_until = datetime.now(UTC) + timedelta(minutes=15)
        await async_db_session.commit()

        # Assert
        result = await async_db_session.execute(
            select(User).where(User.id == user.id)
        )
        locked_user = result.scalar_one()
        assert locked_user.failed_login_attempts == 5
        assert locked_user.locked_until > datetime.now(UTC)

    @pytest.mark.asyncio
    async def test_user_password_history(self, async_db_session: AsyncSession):
        """Test storing password history (last 5 passwords)."""
        # Arrange - Use unique email
        email = f"history-{uuid4()}@example.com"
        user = User(
            email=email,
            password_hash="current_hash",
            failed_login_attempts=0,
            password_history=["old_hash1", "old_hash2", "old_hash3"],
        )
        async_db_session.add(user)
        await async_db_session.commit()

        # Assert
        result = await async_db_session.execute(
            select(User).where(User.email == email)
        )
        saved_user = result.scalar_one()
        assert len(saved_user.password_history) == 3
        assert "old_hash1" in saved_user.password_history


class TestUserTenantRoleModel:
    """Tests for UserTenantRole model and RoleEnum."""

    @pytest.mark.asyncio
    async def test_create_role_assignment_success(self, async_db_session: AsyncSession):
        """Test assigning a role to a user for a specific tenant."""
        # Arrange: Create user first - Use unique email
        user = User(
            email=f"role-{uuid4()}@example.com",
            password_hash="hash",
            failed_login_attempts=0,
            password_history=[],
        )
        async_db_session.add(user)
        await async_db_session.flush()

        tenant_id = "tenant-123"

        # Act
        role = UserTenantRole(
            user_id=user.id,
            tenant_id=tenant_id,
            role=RoleEnum.OPERATOR.value,
        )
        async_db_session.add(role)
        await async_db_session.commit()

        # Assert
        result = await async_db_session.execute(
            select(UserTenantRole).where(
                UserTenantRole.user_id == user.id,
                UserTenantRole.tenant_id == tenant_id
            )
        )
        saved_role = result.scalar_one()
        assert saved_role.user_id == user.id
        assert saved_role.tenant_id == tenant_id
        assert saved_role.role == RoleEnum.OPERATOR.value
        assert saved_role.created_at is not None

    @pytest.mark.asyncio
    async def test_role_enum_values(self):
        """Test that RoleEnum has all 5 roles defined."""
        assert RoleEnum.SUPER_ADMIN.value == "super_admin"
        assert RoleEnum.TENANT_ADMIN.value == "tenant_admin"
        assert RoleEnum.OPERATOR.value == "operator"
        assert RoleEnum.DEVELOPER.value == "developer"
        assert RoleEnum.VIEWER.value == "viewer"

    @pytest.mark.asyncio
    async def test_composite_unique_constraint(self, async_db_session: AsyncSession):
        """Test that one user can have only one role per tenant (composite unique)."""
        # Arrange: Create user and assign role - Use unique email
        user = User(
            email=f"unique-{uuid4()}@example.com",
            password_hash="hash",
            failed_login_attempts=0,
            password_history=[],
        )
        async_db_session.add(user)
        await async_db_session.flush()

        tenant_id = "tenant-456"

        role1 = UserTenantRole(
            user_id=user.id,
            tenant_id=tenant_id,
            role=RoleEnum.DEVELOPER.value,
        )
        async_db_session.add(role1)
        await async_db_session.commit()

        # Act & Assert: Try to assign another role to same user+tenant
        role2 = UserTenantRole(
            user_id=user.id,
            tenant_id=tenant_id,  # Same user+tenant
            role=RoleEnum.VIEWER.value,
        )
        async_db_session.add(role2)
        with pytest.raises(IntegrityError):
            await async_db_session.commit()

    @pytest.mark.asyncio
    async def test_user_multiple_tenants(self, async_db_session: AsyncSession):
        """Test that user can have different roles in different tenants."""
        # Arrange: Create user - Use unique email
        user = User(
            email=f"multi-{uuid4()}@example.com",
            password_hash="hash",
            failed_login_attempts=0,
            password_history=[],
        )
        async_db_session.add(user)
        await async_db_session.flush()

        # Act: Assign different roles in 3 tenants
        roles = [
            UserTenantRole(user_id=user.id, tenant_id="tenant-a", role=RoleEnum.SUPER_ADMIN.value),
            UserTenantRole(user_id=user.id, tenant_id="tenant-b", role=RoleEnum.OPERATOR.value),
            UserTenantRole(user_id=user.id, tenant_id="tenant-c", role=RoleEnum.VIEWER.value),
        ]
        for role in roles:
            async_db_session.add(role)
        await async_db_session.commit()

        # Assert
        result = await async_db_session.execute(
            select(UserTenantRole).where(UserTenantRole.user_id == user.id)
        )
        user_roles = result.scalars().all()
        assert len(user_roles) == 3
        assert {r.role for r in user_roles} == {
            RoleEnum.SUPER_ADMIN.value,
            RoleEnum.OPERATOR.value,
            RoleEnum.VIEWER.value
        }

    @pytest.mark.asyncio
    async def test_cascade_delete_user(self, async_db_session: AsyncSession):
        """Test that deleting user cascades to user_tenant_roles."""
        # Arrange - Use unique email
        user = User(
            email=f"cascade-{uuid4()}@example.com",
            password_hash="hash",
            failed_login_attempts=0,
            password_history=[],
        )
        async_db_session.add(user)
        await async_db_session.flush()

        role = UserTenantRole(
            user_id=user.id,
            tenant_id="tenant-789",
            role=RoleEnum.DEVELOPER.value,
        )
        async_db_session.add(role)
        await async_db_session.commit()

        # Act: Delete user
        await async_db_session.delete(user)
        await async_db_session.commit()

        # Assert: Role should be deleted too (CASCADE)
        result = await async_db_session.execute(
            select(UserTenantRole).where(UserTenantRole.user_id == user.id)
        )
        assert result.scalar_one_or_none() is None


class TestAuthAuditLogModel:
    """Tests for AuthAuditLog model."""

    @pytest.mark.asyncio
    async def test_create_auth_audit_log_success(self, async_db_session: AsyncSession):
        """Test logging a successful login event."""
        # Arrange: Create user - Use unique email
        user = User(
            email=f"audit-{uuid4()}@example.com",
            password_hash="hash",
            failed_login_attempts=0,
            password_history=[],
        )
        async_db_session.add(user)
        await async_db_session.flush()

        # Act
        log = AuthAuditLog(
            user_id=user.id,
            event_type="login",
            success=True,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
        )
        async_db_session.add(log)
        await async_db_session.commit()

        # Assert
        result = await async_db_session.execute(
            select(AuthAuditLog).where(AuthAuditLog.user_id == user.id)
        )
        saved_log = result.scalar_one()
        assert saved_log.event_type == "login"
        assert saved_log.success is True
        assert saved_log.ip_address == "192.168.1.100"
        assert saved_log.user_agent == "Mozilla/5.0"
        assert saved_log.created_at is not None

    @pytest.mark.asyncio
    async def test_create_auth_audit_log_failed_login(self, async_db_session: AsyncSession):
        """Test logging a failed login (user_id nullable)."""
        # Act: Log failed login without user (email not found)
        log = AuthAuditLog(
            user_id=None,  # User not found
            event_type="login",
            success=False,
            ip_address="192.168.1.200",
            user_agent="curl/7.79.1",
        )
        async_db_session.add(log)
        await async_db_session.commit()

        # Assert - Query by log ID to avoid conflicts from previous test runs
        result = await async_db_session.execute(
            select(AuthAuditLog).where(AuthAuditLog.id == log.id)
        )
        saved_log = result.scalar_one()
        assert saved_log.user_id is None
        assert saved_log.success is False


class TestAuditLogModel:
    """Tests for updated AuditLog model with entity fields."""

    @pytest.mark.asyncio
    async def test_create_audit_log_with_entity_fields(self, async_db_session: AsyncSession):
        """Test logging a CRUD operation with entity details."""
        # Arrange: Create user - Use unique email
        user = User(
            email=f"crud-{uuid4()}@example.com",
            password_hash="hash",
            failed_login_attempts=0,
            password_history=[],
        )
        async_db_session.add(user)
        await async_db_session.flush()

        entity_id = uuid4()

        # Act: Log agent creation
        log = AuditLog(
            user_id=user.id,
            tenant_id="tenant-abc",
            action="create",
            entity_type="agent",
            entity_id=entity_id,
            old_value=None,  # No old value for create
            new_value={"name": "Test Agent", "type": "conversational"},
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )
        async_db_session.add(log)
        await async_db_session.commit()

        # Assert
        result = await async_db_session.execute(
            select(AuditLog).where(AuditLog.entity_id == entity_id)
        )
        saved_log = result.scalar_one()
        assert saved_log.action == "create"
        assert saved_log.entity_type == "agent"
        assert saved_log.old_value is None
        assert saved_log.new_value["name"] == "Test Agent"
        assert saved_log.tenant_id == "tenant-abc"

    @pytest.mark.asyncio
    async def test_audit_log_update_with_old_new_values(self, async_db_session: AsyncSession):
        """Test logging an update with old and new values (JSON diff)."""
        # Arrange: Create user - Use unique email
        user = User(
            email=f"update-{uuid4()}@example.com",
            password_hash="hash",
            failed_login_attempts=0,
            password_history=[],
        )
        async_db_session.add(user)
        await async_db_session.flush()

        entity_id = uuid4()

        # Act: Log agent update
        log = AuditLog(
            user_id=user.id,
            tenant_id="tenant-xyz",
            action="update",
            entity_type="agent",
            entity_id=entity_id,
            old_value={"name": "Old Name", "status": "active"},
            new_value={"name": "New Name", "status": "inactive"},
            ip_address="10.0.0.1",
            user_agent="Mozilla/5.0",
        )
        async_db_session.add(log)
        await async_db_session.commit()

        # Assert
        result = await async_db_session.execute(
            select(AuditLog).where(AuditLog.entity_id == entity_id)
        )
        saved_log = result.scalar_one()
        assert saved_log.action == "update"
        assert saved_log.old_value["name"] == "Old Name"
        assert saved_log.new_value["name"] == "New Name"
        assert saved_log.old_value["status"] == "active"
        assert saved_log.new_value["status"] == "inactive"
