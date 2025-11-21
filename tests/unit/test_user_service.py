"""
Unit tests for UserService (Story 1B).

Tests user CRUD operations, password updates with history enforcement,
and role management.

Coverage Target: 90%+
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.user_service import UserService
from src.services.auth_service import hash_password
from src.database.models import User, RoleEnum, UserTenantRole


class TestUserCreation:
    """Test user creation with password validation."""

    @pytest.mark.asyncio
    async def test_create_user_success(self):
        """Verify user creation with valid password and hashing."""
        # Arrange
        service = UserService()
        email = "newuser@example.com"
        password = "MyStr0ng!P@ssw0rd2024"
        tenant_id = uuid4()

        mock_db = AsyncMock(spec=AsyncSession)

        # Act
        user = await service.create_user(email, password, tenant_id, mock_db)

        # Assert
        assert user.email == email
        assert user.default_tenant_id == tenant_id
        assert user.password_hash != password  # Hashed
        assert user.password_hash.startswith("$2b$")
        assert user.password_expires_at is not None
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_create_user_weak_password(self):
        """Verify weak password raises ValidationError."""
        # Arrange
        service = UserService()
        email = "newuser@example.com"
        password = "weak"  # Too short, no uppercase, no special
        tenant_id = uuid4()

        mock_db = AsyncMock(spec=AsyncSession)

        # Act & Assert
        with pytest.raises(ValueError, match="at least"):
            await service.create_user(email, password, tenant_id, mock_db)


class TestUserRetrieval:
    """Test user retrieval by email and ID."""

    @pytest.mark.asyncio
    async def test_get_user_by_email_found(self):
        """Verify user retrieval by email when user exists."""
        # Arrange
        service = UserService()
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="dummy",
        )

        # Mock async database session
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=user)

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await service.get_user_by_email("test@example.com", mock_db)

        # Assert
        assert result == user

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self):
        """Verify returns None when user not found."""
        # Arrange
        service = UserService()

        # Mock async database session
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await service.get_user_by_email("nonexistent@example.com", mock_db)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_by_id_found(self):
        """Verify user retrieval by UUID."""
        # Arrange
        service = UserService()
        user_id = uuid4()
        user = User(
            id=user_id,
            email="test@example.com",
            password_hash="dummy",
        )

        # Mock async database session
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=user)

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await service.get_user_by_id(user_id, mock_db)

        # Assert
        assert result == user


class TestUserUpdate:
    """Test user field updates."""

    @pytest.mark.asyncio
    async def test_update_user_fields(self):
        """Verify user field updates work correctly."""
        # Arrange
        service = UserService()
        user_id = uuid4()
        user = User(
            id=user_id,
            email="test@example.com",
            password_hash="dummy",
        )

        # Mock async database session
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=user)

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        # Act
        updates = {"email": "newemail@example.com"}
        result = await service.update_user(user_id, updates, mock_db)

        # Assert
        assert result.email == "newemail@example.com"
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_update_user_not_found(self):
        """Verify update raises error when user not found."""
        # Arrange
        service = UserService()
        user_id = uuid4()

        # Mock async database session
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act & Assert
        with pytest.raises(ValueError, match="User not found"):
            await service.update_user(user_id, {}, mock_db)


class TestPasswordHistory:
    """Test password history enforcement."""

    def test_check_password_history_reused(self):
        """Verify check_password_history detects reused password."""
        # Arrange
        service = UserService()
        old_password = "OldPassword123!"
        old_hash = hash_password(old_password)

        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="current",
            password_history=[old_hash],
        )

        # Act - Pass PLAIN password (not hash) per CRITICAL fix
        is_reused = service.check_password_history(user, old_password)

        # Assert
        assert is_reused is True

    def test_check_password_history_unique(self):
        """Verify check_password_history returns False for new password."""
        # Arrange
        service = UserService()
        old_password = "OldPassword123!"
        new_password = "NewPassword123!"
        old_hash = hash_password(old_password)

        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="current",
            password_history=[old_hash],
        )

        # Act - Pass PLAIN password (not hash) per CRITICAL fix
        is_reused = service.check_password_history(user, new_password)

        # Assert
        assert is_reused is False


class TestRoleManagement:
    """Test user role assignment and retrieval."""

    @pytest.mark.asyncio
    async def test_get_user_role_for_tenant(self):
        """Verify role fetching for specific tenant."""
        # Arrange
        service = UserService()
        user_id = uuid4()
        tenant_id = "tenant-123"
        role = RoleEnum.TENANT_ADMIN

        user_tenant_role = UserTenantRole(
            id=uuid4(),
            user_id=user_id,
            tenant_id=tenant_id,
            role=role,
        )

        # Mock async database session
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=user_tenant_role)

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await service.get_user_role_for_tenant(user_id, tenant_id, mock_db)

        # Assert
        assert result == role

    @pytest.mark.asyncio
    async def test_get_user_role_not_assigned(self):
        """Verify returns None when no role assigned."""
        # Arrange
        service = UserService()
        user_id = uuid4()
        tenant_id = "tenant-123"

        # Mock async database session
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await service.get_user_role_for_tenant(user_id, tenant_id, mock_db)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_assign_role_new(self):
        """Verify role assignment creates new entry."""
        # Arrange
        service = UserService()
        user_id = uuid4()
        tenant_id = "tenant-123"
        role = RoleEnum.DEVELOPER

        # Mock async database session
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)  # No existing role

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()

        # Act
        await service.assign_role(user_id, tenant_id, role, mock_db)

        # Assert
        assert mock_db.add.called
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_assign_role_update_existing(self):
        """Verify role assignment updates existing entry (idempotent)."""
        # Arrange
        service = UserService()
        user_id = uuid4()
        tenant_id = "tenant-123"
        old_role = RoleEnum.VIEWER
        new_role = RoleEnum.DEVELOPER

        existing = UserTenantRole(
            id=uuid4(),
            user_id=user_id,
            tenant_id=tenant_id,
            role=old_role,
        )

        # Mock async database session
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=existing)

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        # Act
        await service.assign_role(user_id, tenant_id, new_role, mock_db)

        # Assert
        assert existing.role == new_role
        assert mock_db.commit.called
