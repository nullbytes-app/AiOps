"""
Unit tests for TenantService with mocked database and Redis.

Tests all CRUD operations, caching behavior, encryption/decryption,
and graceful fallback when Redis is unavailable.

Reason:
    Isolates TenantService logic from external dependencies (DB, Redis)
    using mocks to enable fast, deterministic unit tests.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from redis import asyncio as aioredis

from src.services.tenant_service import (
    TenantService,
    TenantNotFoundException,
)
from src.schemas.tenant import (
    TenantConfigCreate,
    TenantConfigUpdate,
    TenantConfigInternal,
)
from src.utils.encryption import encrypt, decrypt


@pytest.fixture
def mock_db() -> AsyncSession:
    """Mock AsyncSession for database operations."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_redis() -> aioredis.Redis:
    """Mock Redis client."""
    return AsyncMock(spec=aioredis.Redis)


@pytest.fixture
def tenant_service(mock_db: AsyncSession, mock_redis: aioredis.Redis) -> TenantService:
    """Create TenantService instance with mocked dependencies."""
    return TenantService(db=mock_db, redis=mock_redis)


@pytest.fixture
def sample_tenant_create() -> TenantConfigCreate:
    """Sample TenantConfigCreate for testing."""
    return TenantConfigCreate(
        tenant_id="test-tenant",
        name="Test Tenant",
        servicedesk_url="https://test.servicedesk.com",
        servicedesk_api_key="test-api-key-12345",
        webhook_signing_secret="test-webhook-secret-12345",
        enhancement_preferences={
            "max_enhancement_length": 500,
            "include_monitoring": True,
        },
    )


# ============================================================================
# CREATE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_create_tenant_success(
    tenant_service: TenantService,
    sample_tenant_create: TenantConfigCreate,
    mock_db: AsyncMock,
    mock_redis: AsyncMock,
):
    """Test successful tenant creation with encryption and caching."""
    from src.database.models import TenantConfig as TenantConfigModel

    # Track added config to populate id/timestamps when flush is called
    added_config_list = []

    def mock_add(config):
        added_config_list.append(config)

    async def mock_flush():
        # Populate id and timestamps on the added config
        for config in added_config_list:
            if not config.id:
                config.id = uuid.uuid4()
            if not config.created_at:
                config.created_at = datetime.now()
            if not config.updated_at:
                config.updated_at = datetime.now()

    mock_db.flush = AsyncMock(side_effect=mock_flush)
    mock_db.add = MagicMock(side_effect=mock_add)

    # Mock Redis caching
    mock_redis.setex = AsyncMock()

    result = await tenant_service.create_tenant(sample_tenant_create)

    # Verify database add was called
    mock_db.add.assert_called_once()
    added_config = mock_db.add.call_args[0][0]
    assert added_config.tenant_id == "test-tenant"
    assert added_config.name == "Test Tenant"

    # Verify encryption was applied
    assert added_config.servicedesk_api_key_encrypted != "test-api-key-12345"
    assert added_config.webhook_signing_secret_encrypted != "test-webhook-secret-12345"

    # Verify cache was set
    mock_redis.setex.assert_called_once()

    # Verify result contains decrypted credentials
    assert result.tenant_id == "test-tenant"
    assert result.servicedesk_api_key == "test-api-key-12345"
    assert result.webhook_signing_secret == "test-webhook-secret-12345"


@pytest.mark.asyncio
async def test_create_tenant_cache_failure_nonfatal(
    tenant_service: TenantService,
    sample_tenant_create: TenantConfigCreate,
    mock_db: AsyncMock,
    mock_redis: AsyncMock,
):
    """Test that Redis cache failure doesn't prevent tenant creation."""
    from src.database.models import TenantConfig as TenantConfigModel

    added_config_list = []

    def mock_add(config):
        added_config_list.append(config)

    async def mock_flush():
        for config in added_config_list:
            if not config.id:
                config.id = uuid.uuid4()
            if not config.created_at:
                config.created_at = datetime.now()
            if not config.updated_at:
                config.updated_at = datetime.now()

    mock_db.flush = AsyncMock(side_effect=mock_flush)
    mock_db.add = MagicMock(side_effect=mock_add)
    mock_redis.setex = AsyncMock(side_effect=Exception("Redis down"))

    # Should not raise, should complete despite cache failure
    result = await tenant_service.create_tenant(sample_tenant_create)

    assert result.tenant_id == "test-tenant"
    # Redis was attempted but failure was logged
    mock_redis.setex.assert_called_once()


# ============================================================================
# READ TESTS (with caching)
# ============================================================================


@pytest.mark.asyncio
async def test_get_tenant_config_cache_hit(
    tenant_service: TenantService,
    mock_redis: AsyncMock,
):
    """Test get_tenant_config returns cached config on cache hit."""
    tenant_id = "cached-tenant"
    cached_config = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "name": "Cached Tenant",
        "servicedesk_url": "https://cached.servicedesk.com",
        "servicedesk_api_key": "decrypted-key",
        "webhook_signing_secret": "decrypted-secret",
        "enhancement_preferences": {"max_enhancement_length": 1000},
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    # Mock Redis returning cached data
    mock_redis.get = AsyncMock(return_value=json.dumps(cached_config))

    result = await tenant_service.get_tenant_config(tenant_id)

    # Verify Redis was queried
    mock_redis.get.assert_called_once()
    assert result.tenant_id == tenant_id
    assert result.servicedesk_api_key == "decrypted-key"


@pytest.mark.asyncio
async def test_get_tenant_config_cache_miss_with_db(
    tenant_service: TenantService,
    mock_db: AsyncMock,
    mock_redis: AsyncMock,
):
    """Test get_tenant_config queries database on cache miss."""
    from src.database.models import TenantConfig as TenantConfigModel

    tenant_id = "db-tenant"

    # Mock Redis cache miss
    mock_redis.get = AsyncMock(return_value=None)

    # Mock database query result
    mock_config = MagicMock(spec=TenantConfigModel)
    mock_config.id = uuid.uuid4()
    mock_config.tenant_id = tenant_id
    mock_config.name = "DB Tenant"
    mock_config.servicedesk_url = "https://db.servicedesk.com"
    mock_config.servicedesk_api_key_encrypted = encrypt("db-api-key")
    mock_config.webhook_signing_secret_encrypted = encrypt("db-webhook-secret")
    mock_config.enhancement_preferences = {"max_enhancement_length": 750}
    mock_config.created_at = datetime.now()
    mock_config.updated_at = datetime.now()

    # Mock SQLAlchemy execute pattern with proper result object
    # Note: scalar_one_or_none is a sync method, not async
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_config)
    mock_db.execute = AsyncMock(return_value=mock_result)

    # Mock Redis cache set
    mock_redis.setex = AsyncMock()

    result = await tenant_service.get_tenant_config(tenant_id)

    # Verify database was queried
    mock_db.execute.assert_called_once()

    # Verify result was decrypted
    assert result.tenant_id == tenant_id
    assert result.servicedesk_api_key == "db-api-key"
    assert result.webhook_signing_secret == "db-webhook-secret"

    # Verify Redis caching was attempted
    mock_redis.setex.assert_called_once()


@pytest.mark.asyncio
async def test_get_tenant_config_not_found(
    tenant_service: TenantService,
    mock_db: AsyncMock,
    mock_redis: AsyncMock,
):
    """Test get_tenant_config raises TenantNotFoundException."""
    # Mock cache miss
    mock_redis.get = AsyncMock(return_value=None)

    # Mock database not found with proper result object
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(TenantNotFoundException):
        await tenant_service.get_tenant_config("nonexistent")


@pytest.mark.asyncio
async def test_get_tenant_config_cache_failure_fallback_to_db(
    tenant_service: TenantService,
    mock_db: AsyncMock,
    mock_redis: AsyncMock,
):
    """Test graceful fallback to database when Redis fails."""
    from src.database.models import TenantConfig as TenantConfigModel

    # Mock Redis get failure
    mock_redis.get = AsyncMock(side_effect=Exception("Redis connection failed"))

    # Mock database success with proper result object
    mock_config = MagicMock(spec=TenantConfigModel)
    mock_config.id = uuid.uuid4()
    mock_config.tenant_id = "resilient-tenant"
    mock_config.name = "Resilient Tenant"
    mock_config.servicedesk_url = "https://resilient.servicedesk.com"
    mock_config.servicedesk_api_key_encrypted = encrypt("resilient-key")
    mock_config.webhook_signing_secret_encrypted = encrypt("resilient-secret")
    mock_config.enhancement_preferences = {}
    mock_config.created_at = datetime.now()
    mock_config.updated_at = datetime.now()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_config)
    mock_db.execute = AsyncMock(return_value=mock_result)

    # Should not raise, should fall back to database
    result = await tenant_service.get_tenant_config("resilient-tenant")

    assert result.tenant_id == "resilient-tenant"
    mock_db.execute.assert_called_once()


# ============================================================================
# UPDATE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_update_tenant_success(
    tenant_service: TenantService,
    mock_db: AsyncMock,
    mock_redis: AsyncMock,
):
    """Test successful tenant configuration update."""
    from src.database.models import TenantConfig as TenantConfigModel

    tenant_id = "update-tenant"

    # Mock existing config
    mock_config = MagicMock(spec=TenantConfigModel)
    mock_config.id = uuid.uuid4()
    mock_config.tenant_id = tenant_id
    mock_config.name = "Original Name"
    mock_config.servicedesk_url = "https://original.servicedesk.com"
    mock_config.servicedesk_api_key_encrypted = encrypt("original-key")
    mock_config.webhook_signing_secret_encrypted = encrypt("original-secret")
    mock_config.enhancement_preferences = {"max_enhancement_length": 500}
    mock_config.created_at = datetime.now()
    mock_config.updated_at = datetime.now()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_config)
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.flush = AsyncMock()
    mock_redis.delete = AsyncMock()

    # Update with new values
    updates = TenantConfigUpdate(
        name="Updated Name",
        servicedesk_api_key="new-api-key",
    )

    result = await tenant_service.update_tenant(tenant_id, updates)

    # Verify updates were applied
    assert mock_config.name == "Updated Name"
    assert decrypt(mock_config.servicedesk_api_key_encrypted) == "new-api-key"

    # Verify cache invalidation
    mock_redis.delete.assert_called_once()

    # Verify result
    assert result.tenant_id == tenant_id
    assert result.servicedesk_api_key == "new-api-key"


@pytest.mark.asyncio
async def test_update_tenant_not_found(
    tenant_service: TenantService,
    mock_db: AsyncMock,
    mock_redis: AsyncMock,
):
    """Test update_tenant raises when tenant not found."""
    from src.database.models import TenantConfig as TenantConfigModel

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_db.execute = AsyncMock(return_value=mock_result)

    updates = TenantConfigUpdate(name="New Name")

    with pytest.raises(TenantNotFoundException):
        await tenant_service.update_tenant("nonexistent", updates)


# ============================================================================
# DELETE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_delete_tenant_success(
    tenant_service: TenantService,
    mock_db: AsyncMock,
    mock_redis: AsyncMock,
):
    """Test successful tenant deletion."""
    from src.database.models import TenantConfig as TenantConfigModel

    tenant_id = "delete-tenant"

    # Mock existing config
    mock_config = MagicMock(spec=TenantConfigModel)
    mock_config.tenant_id = tenant_id

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_config)
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.delete = MagicMock()  # Not async
    mock_db.flush = AsyncMock()  # Add flush for delete operation
    mock_redis.delete = AsyncMock()

    await tenant_service.delete_tenant(tenant_id)

    # Verify delete was called
    mock_db.delete.assert_called_once_with(mock_config)

    # Verify flush was called
    mock_db.flush.assert_called_once()

    # Verify cache invalidation
    mock_redis.delete.assert_called_once()


@pytest.mark.asyncio
async def test_delete_tenant_not_found(
    tenant_service: TenantService,
    mock_db: AsyncMock,
    mock_redis: AsyncMock,
):
    """Test delete_tenant raises when tenant not found."""
    from src.database.models import TenantConfig as TenantConfigModel

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(TenantNotFoundException):
        await tenant_service.delete_tenant("nonexistent")


# ============================================================================
# LIST TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_list_tenants_paginated(
    tenant_service: TenantService,
    mock_db: AsyncMock,
):
    """Test paginated tenant listing with masked sensitive fields."""
    from src.database.models import TenantConfig as TenantConfigModel

    # Mock list results
    mock_configs = []
    for i in range(3):
        mock_config = MagicMock(spec=TenantConfigModel)
        mock_config.id = uuid.uuid4()
        mock_config.tenant_id = f"tenant-{i}"
        mock_config.name = f"Tenant {i}"
        mock_config.servicedesk_url = f"https://tenant{i}.servicedesk.com"
        mock_config.servicedesk_api_key_encrypted = encrypt(f"key-{i}")
        mock_config.webhook_signing_secret_encrypted = encrypt(f"secret-{i}")
        mock_config.enhancement_preferences = {}
        mock_config.created_at = datetime.now()
        mock_config.updated_at = datetime.now()
        mock_configs.append(mock_config)

    # First call returns count result - scalar() is not async
    count_result = MagicMock()
    count_result.scalar = MagicMock(return_value=10)

    # Second call returns list results - scalars().all() is not async
    list_result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=mock_configs)
    list_result.scalars = MagicMock(return_value=scalars_mock)

    # Setup execute to return different results for each call
    call_count = 0

    def mock_execute_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return count_result
        else:
            return list_result

    mock_db.execute = AsyncMock(side_effect=mock_execute_side_effect)

    results, total = await tenant_service.list_tenants(skip=0, limit=3)

    # Verify pagination
    assert len(results) == 3
    assert total == 10

    # Verify sensitive fields are masked
    for result in results:
        assert result.servicedesk_api_key_encrypted == "***encrypted***"
        assert result.webhook_signing_secret_encrypted == "***encrypted***"


# ============================================================================
# EDGE CASES
# ============================================================================


@pytest.mark.asyncio
async def test_tenant_service_with_empty_preferences(
    tenant_service: TenantService,
    mock_db: AsyncMock,
    mock_redis: AsyncMock,
):
    """Test creating tenant with empty enhancement preferences."""
    config = TenantConfigCreate(
        tenant_id="minimal-tenant",
        name="Minimal Tenant",
        servicedesk_url="https://minimal.servicedesk.com",
        servicedesk_api_key="minimal-key",
        webhook_signing_secret="minimal-secret",
        enhancement_preferences=None,  # No preferences
    )

    added_config_list = []

    def mock_add(config_obj):
        added_config_list.append(config_obj)

    async def mock_flush():
        for config_obj in added_config_list:
            if not config_obj.id:
                config_obj.id = uuid.uuid4()
            if not config_obj.created_at:
                config_obj.created_at = datetime.now()
            if not config_obj.updated_at:
                config_obj.updated_at = datetime.now()

    mock_db.flush = AsyncMock(side_effect=mock_flush)
    mock_db.add = MagicMock(side_effect=mock_add)
    mock_redis.setex = AsyncMock()

    result = await tenant_service.create_tenant(config)

    # Verify the config was created successfully
    assert result.tenant_id == "minimal-tenant"
    assert result.name == "Minimal Tenant"


@pytest.mark.asyncio
async def test_cache_invalidation_failure_nonfatal(
    tenant_service: TenantService,
    mock_db: AsyncMock,
    mock_redis: AsyncMock,
):
    """Test that Redis cache invalidation failure doesn't prevent delete."""
    from src.database.models import TenantConfig as TenantConfigModel

    mock_config = MagicMock(spec=TenantConfigModel)
    mock_config.tenant_id = "delete-me"

    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = AsyncMock(return_value=mock_config)
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.delete = MagicMock()
    mock_db.flush = AsyncMock()

    # Redis delete fails
    mock_redis.delete = AsyncMock(side_effect=Exception("Redis down"))

    # Should not raise, should complete despite cache failure
    await tenant_service.delete_tenant("delete-me")

    mock_db.delete.assert_called_once()
    mock_db.flush.assert_called_once()
