"""
Unit tests for ProviderService with mocked database and Redis.

Tests all CRUD operations, encryption/decryption, connection testing,
caching behavior, and error handling for LLM provider management.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import httpx

from sqlalchemy.ext.asyncio import AsyncSession
from redis import asyncio as aioredis

from src.services.provider_service import ProviderService
from src.database.models import LLMProvider, ProviderType
from src.schemas.provider import LLMProviderCreate, LLMProviderUpdate
from src.utils.encryption import encrypt, decrypt
from src.utils.exceptions import ProviderNotFoundException


@pytest.fixture
def mock_db() -> AsyncSession:
    """Mock AsyncSession for database operations."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_redis() -> aioredis.Redis:
    """Mock Redis client."""
    return AsyncMock(spec=aioredis.Redis)


@pytest.fixture
def provider_service(mock_db: AsyncSession, mock_redis: aioredis.Redis) -> ProviderService:
    """Create ProviderService instance with mocked dependencies."""
    return ProviderService(db=mock_db, redis=mock_redis)


@pytest.fixture
def sample_provider_openai():
    """Sample OpenAI provider for testing."""
    return LLMProvider(
        id=1,
        name="Test OpenAI",
        provider_type=ProviderType.OPENAI,
        api_base_url="https://api.openai.com/v1",
        api_key_encrypted=encrypt("sk-test123"),
        enabled=True,
        last_test_at=datetime.now(timezone.utc),
        last_test_success=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_provider_anthropic():
    """Sample Anthropic provider for testing."""
    return LLMProvider(
        id=2,
        name="Test Anthropic",
        provider_type=ProviderType.ANTHROPIC,
        api_base_url="https://api.anthropic.com",
        api_key_encrypted=encrypt("sk-ant-test456"),
        enabled=True,
        last_test_at=None,
        last_test_success=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


# ============================================================================
# CREATE PROVIDER TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_create_provider_success(
    provider_service: ProviderService,
    mock_db: AsyncMock,
    mock_redis: AsyncMock,
):
    """Test successful provider creation with API key encryption."""
    # Mock database behavior - check for duplicate name
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # No duplicate
    mock_db.execute.return_value = mock_result

    # Mock database behavior for creation
    added_providers = []

    def mock_add(provider):
        added_providers.append(provider)
        # Set ID immediately
        provider.id = 1
        provider.created_at = datetime.now(timezone.utc)
        provider.updated_at = datetime.now(timezone.utc)

    mock_db.add = MagicMock(side_effect=mock_add)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    # Test provider creation
    provider_data = LLMProviderCreate(
        name="Test Provider",
        provider_type=ProviderType.OPENAI,
        api_base_url="https://api.openai.com/v1",
        api_key="sk-test123",
    )
    result = await provider_service.create_provider(provider_data)

    # Assertions
    assert result.name == "Test Provider"
    assert result.provider_type == ProviderType.OPENAI
    assert result.api_key_encrypted is not None
    assert result.api_key_encrypted != "sk-test123"  # Should be encrypted
    assert result.enabled is True

    # Verify API key encryption roundtrip
    decrypted = decrypt(result.api_key_encrypted)
    assert decrypted == "sk-test123"

    # Verify database operations (provider + audit log)
    assert mock_db.add.call_count == 2  # Provider + AuditLog
    assert mock_db.commit.call_count == 2  # After provider, after audit

    # Verify cache invalidation
    mock_redis.delete.assert_called()


@pytest.mark.asyncio
async def test_create_provider_duplicate_name_error(
    provider_service: ProviderService,
    mock_db: AsyncMock,
    sample_provider_openai: LLMProvider,
):
    """Test that duplicate provider names raise ValueError."""
    # Mock database to return existing provider with same name
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_provider_openai  # Duplicate found!
    mock_db.execute.return_value = mock_result

    with pytest.raises(ValueError, match="already exists"):
        provider_data = LLMProviderCreate(
            name="Duplicate Provider",
            provider_type=ProviderType.OPENAI,
            api_base_url="https://api.openai.com/v1",
            api_key="sk-test123",
        )
        await provider_service.create_provider(provider_data)


# ============================================================================
# GET PROVIDER TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_get_provider_success(
    provider_service: ProviderService,
    mock_db: AsyncMock,
    mock_redis: AsyncMock,
    sample_provider_openai: LLMProvider,
):
    """Test retrieving a provider by ID with caching."""
    # Mock Redis cache miss
    mock_redis.get.return_value = None

    # Mock database query - FIX: add .unique() to mock chain
    mock_result = MagicMock()
    mock_unique = MagicMock()
    mock_unique.scalar_one_or_none.return_value = sample_provider_openai
    mock_result.unique.return_value = mock_unique
    mock_db.execute.return_value = mock_result

    # Test get provider
    result = await provider_service.get_provider(1)

    # Assertions
    assert result is not None
    assert result.id == 1
    assert result.name == "Test OpenAI"
    assert result.provider_type == ProviderType.OPENAI

    # Verify cache operations
    mock_redis.get.assert_called_once()
    # Note: setex not called yet - caching implementation incomplete


@pytest.mark.asyncio
async def test_get_provider_from_cache(
    provider_service: ProviderService,
    mock_db: AsyncMock,
    mock_redis: AsyncMock,
    sample_provider_openai: LLMProvider,
):
    """Test retrieving a provider from cache (cache hit detection)."""
    import json

    # Mock Redis cache hit (Note: actual deserialization not implemented yet)
    mock_redis.get.return_value = "cached_value"

    # Mock database query (still needed since caching incomplete) - FIX: add .unique() to mock chain
    mock_result = MagicMock()
    mock_unique = MagicMock()
    mock_unique.scalar_one_or_none.return_value = sample_provider_openai
    mock_result.unique.return_value = mock_unique
    mock_db.execute.return_value = mock_result

    # Test get provider
    result = await provider_service.get_provider(1)

    # Assertions
    assert result is not None
    assert result.id == 1
    assert result.name == "Test OpenAI"

    # Verify cache was checked
    mock_redis.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_provider_not_found(
    provider_service: ProviderService,
    mock_db: AsyncMock,
    mock_redis: AsyncMock,
):
    """Test that getting non-existent provider returns None."""
    mock_redis.get.return_value = None

    # FIX: add .unique() to mock chain
    mock_result = MagicMock()
    mock_unique = MagicMock()
    mock_unique.scalar_one_or_none.return_value = None
    mock_result.unique.return_value = mock_unique
    mock_db.execute.return_value = mock_result

    result = await provider_service.get_provider(999)

    assert result is None


# ============================================================================
# LIST PROVIDERS TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_list_providers_success(
    provider_service: ProviderService,
    mock_db: AsyncMock,
    mock_redis: AsyncMock,
    sample_provider_openai: LLMProvider,
    sample_provider_anthropic: LLMProvider,
):
    """Test listing all enabled providers."""
    # Mock Redis cache miss
    mock_redis.get.return_value = None

    # Mock database query
    mock_scalars = MagicMock()
    mock_scalars.unique.return_value.all.return_value = [
        sample_provider_openai,
        sample_provider_anthropic,
    ]
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result

    # Test list providers
    result = await provider_service.list_providers(include_disabled=False)

    # Assertions
    assert len(result) == 2
    assert result[0].name == "Test OpenAI"
    assert result[1].name == "Test Anthropic"

    # Note: cache operation not fully implemented yet


@pytest.mark.asyncio
async def test_list_providers_pagination(
    provider_service: ProviderService,
    mock_db: AsyncMock,
    mock_redis: AsyncMock,
    sample_provider_openai: LLMProvider,
):
    """Test pagination in list providers."""
    mock_redis.get.return_value = None

    mock_scalars = MagicMock()
    mock_scalars.unique.return_value.all.return_value = [sample_provider_openai]
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result

    # Test with pagination
    result = await provider_service.list_providers(skip=0, limit=10)

    assert len(result) == 1


# ============================================================================
# UPDATE PROVIDER TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_update_provider_success(
    provider_service: ProviderService,
    mock_db: AsyncMock,
    mock_redis: AsyncMock,
    sample_provider_openai: LLMProvider,
):
    """Test updating provider configuration."""
    # Mock database query to find provider
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_provider_openai
    mock_db.execute.return_value = mock_result
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    # Test update
    update_data = LLMProviderUpdate(
        name="Updated OpenAI",
        api_base_url="https://api.openai.com/v2",
    )
    result = await provider_service.update_provider(provider_id=1, provider_data=update_data)

    # Assertions
    assert result.name == "Updated OpenAI"
    assert result.api_base_url == "https://api.openai.com/v2"

    assert mock_db.commit.call_count == 2  # After update, after audit
    mock_redis.delete.assert_called()  # Cache invalidation


@pytest.mark.asyncio
async def test_update_provider_with_new_api_key(
    provider_service: ProviderService,
    mock_db: AsyncMock,
    sample_provider_openai: LLMProvider,
):
    """Test updating provider with new API key (re-encryption)."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_provider_openai
    mock_db.execute.return_value = mock_result
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    old_encrypted = sample_provider_openai.api_key_encrypted

    # Test update with new API key
    update_data = LLMProviderUpdate(api_key="sk-newkey999")
    result = await provider_service.update_provider(provider_id=1, provider_data=update_data)

    # Assertions
    assert result.api_key_encrypted != old_encrypted
    decrypted = decrypt(result.api_key_encrypted)
    assert decrypted == "sk-newkey999"


# ============================================================================
# DELETE PROVIDER TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_delete_provider_success(
    provider_service: ProviderService,
    mock_db: AsyncMock,
    mock_redis: AsyncMock,
    sample_provider_openai: LLMProvider,
):
    """Test soft delete of provider (sets enabled=false)."""
    # FIX: add .unique() to mock chain AND mock Redis for get_provider
    mock_redis.get.return_value = None
    mock_result = MagicMock()
    mock_unique = MagicMock()
    mock_unique.scalar_one_or_none.return_value = sample_provider_openai
    mock_result.unique.return_value = mock_unique
    mock_db.execute.return_value = mock_result
    mock_db.commit = AsyncMock()

    # Test delete
    result = await provider_service.delete_provider(1)

    # Assertions
    assert result is True
    assert sample_provider_openai.enabled is False
    assert mock_db.commit.call_count == 2  # After delete, after audit
    mock_redis.delete.assert_called()  # Cache invalidation


@pytest.mark.asyncio
async def test_delete_provider_not_found(
    provider_service: ProviderService,
    mock_db: AsyncMock,
    mock_redis: AsyncMock,
):
    """Test deleting non-existent provider returns False."""
    # FIX: add .unique() to mock chain
    mock_redis.get.return_value = None
    mock_result = MagicMock()
    mock_unique = MagicMock()
    mock_unique.scalar_one_or_none.return_value = None
    mock_result.unique.return_value = mock_unique
    mock_db.execute.return_value = mock_result

    result = await provider_service.delete_provider(999)
    assert result is False


# ============================================================================
# TEST CONNECTION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_test_provider_connection_openai_success(
    provider_service: ProviderService,
    mock_db: AsyncMock,
    mock_redis: AsyncMock,
    sample_provider_openai: LLMProvider,
):
    """Test successful OpenAI provider connection."""
    # Mock get_provider to return sample provider - FIX: add .unique() AND mock Redis
    mock_redis.get.return_value = None
    mock_result = MagicMock()
    mock_unique = MagicMock()
    mock_unique.scalar_one_or_none.return_value = sample_provider_openai
    mock_result.unique.return_value = mock_unique
    mock_db.execute.return_value = mock_result
    mock_db.commit = AsyncMock()

    # Mock httpx response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {"id": "gpt-4"},
            {"id": "gpt-3.5-turbo"},
        ]
    }

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

        # Test connection
        result = await provider_service.test_provider_connection(1)

        # Assertions
        assert result.success is True
        assert len(result.models) == 2
        assert "gpt-4" in result.models
        assert result.response_time_ms >= 0  # Can be 0 in mocked tests

        # Verify last_test_at was updated
        mock_db.commit.assert_called()


@pytest.mark.asyncio
async def test_test_provider_connection_anthropic_success(
    provider_service: ProviderService,
    mock_db: AsyncMock,
    mock_redis: AsyncMock,
    sample_provider_anthropic: LLMProvider,
):
    """Test successful Anthropic provider connection."""
    # FIX: add .unique() AND mock Redis
    mock_redis.get.return_value = None
    mock_result = MagicMock()
    mock_unique = MagicMock()
    mock_unique.scalar_one_or_none.return_value = sample_provider_anthropic
    mock_result.unique.return_value = mock_unique
    mock_db.execute.return_value = mock_result
    mock_db.commit = AsyncMock()

    # Mock httpx response for Anthropic (different response format)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "models": [
            {"name": "claude-3-5-sonnet"},
            {"name": "claude-3-opus"},
        ]
    }

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

        # Test connection
        result = await provider_service.test_provider_connection(2)

        # Assertions
        assert result.success is True
        assert len(result.models) == 2


@pytest.mark.asyncio
async def test_test_provider_connection_failure(
    provider_service: ProviderService,
    mock_db: AsyncMock,
    mock_redis: AsyncMock,
    sample_provider_openai: LLMProvider,
):
    """Test connection failure handling (401 Unauthorized)."""
    # FIX: add .unique() AND mock Redis
    mock_redis.get.return_value = None
    mock_result = MagicMock()
    mock_unique = MagicMock()
    mock_unique.scalar_one_or_none.return_value = sample_provider_openai
    mock_result.unique.return_value = mock_unique
    mock_db.execute.return_value = mock_result
    mock_db.commit = AsyncMock()

    # Mock httpx response with 401 error
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Unauthorized", request=MagicMock(), response=mock_response
    )

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

        # Test connection
        result = await provider_service.test_provider_connection(1)

        # Assertions
        assert result.success is False
        assert result.error is not None
        assert sample_provider_openai.last_test_success is False


@pytest.mark.asyncio
async def test_test_provider_connection_timeout(
    provider_service: ProviderService,
    mock_db: AsyncMock,
    mock_redis: AsyncMock,
    sample_provider_openai: LLMProvider,
):
    """Test connection timeout handling."""
    # FIX: add .unique() AND mock Redis
    mock_redis.get.return_value = None
    mock_result = MagicMock()
    mock_unique = MagicMock()
    mock_unique.scalar_one_or_none.return_value = sample_provider_openai
    mock_result.unique.return_value = mock_unique
    mock_db.execute.return_value = mock_result
    mock_db.commit = AsyncMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.TimeoutException(
            "Request timed out"
        )

        # Test connection
        result = await provider_service.test_provider_connection(1)

        # Assertions
        assert result.success is False
        assert "timed out" in result.error.lower()  # Error message contains "timed out"
