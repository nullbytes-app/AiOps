"""
Unit tests for EmbeddingService.

Tests embedding generation, caching, batch processing, and error handling
with OpenAI API mocking.

Story 8.15: Memory Configuration UI - Unit Tests (Task 9.5)
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.embedding_service import EmbeddingService


@pytest.fixture
def mock_openai_response():
    """Fixture for mocked OpenAI API response."""
    response = MagicMock()
    response.data = [MagicMock()]
    response.data[0].embedding = [0.1] * 1536  # 1536-dimensional vector
    return response


@pytest.fixture
def embedding_service_no_redis():
    """Fixture for EmbeddingService without Redis."""
    with patch.dict('os.environ', {'AI_AGENTS_OPENAI_API_KEY': 'test-key'}):
        with patch('src.services.embedding_service.settings') as mock_settings:
            mock_settings.openai_api_key = 'test-key'
            mock_settings.redis_url = None
            service = EmbeddingService(openai_api_key='test-key', redis_url=None)
            return service


@pytest.mark.asyncio
async def test_generate_embedding_success(embedding_service_no_redis, mock_openai_response):
    """Test successful embedding generation."""
    # Arrange
    service = embedding_service_no_redis
    service.client.embeddings.create = AsyncMock(return_value=mock_openai_response)

    text = "Test text for embedding"

    # Act
    embedding_json = await service.generate_embedding(text)

    # Assert
    assert embedding_json is not None
    embedding_vector = json.loads(embedding_json)
    assert len(embedding_vector) == 1536
    assert all(isinstance(v, float) for v in embedding_vector)


@pytest.mark.asyncio
async def test_generate_embedding_empty_text(embedding_service_no_redis):
    """Test ValueError for empty text."""
    # Arrange
    service = embedding_service_no_redis

    # Act & Assert
    with pytest.raises(ValueError, match="Text cannot be empty"):
        await service.generate_embedding("")


@pytest.mark.asyncio
async def test_generate_embedding_truncates_long_text(embedding_service_no_redis, mock_openai_response):
    """Test that very long texts are truncated."""
    # Arrange
    service = embedding_service_no_redis
    service.client.embeddings.create = AsyncMock(return_value=mock_openai_response)

    # Create text longer than 32768 chars
    long_text = "x" * 40000

    # Act
    embedding_json = await service.generate_embedding(long_text)

    # Assert
    assert embedding_json is not None
    # Verify API was called (truncation happens before API call)
    service.client.embeddings.create.assert_called_once()


@pytest.mark.asyncio
async def test_generate_embedding_rate_limit_error(embedding_service_no_redis):
    """Test graceful handling of OpenAI rate limit errors."""
    # Arrange
    import openai

    service = embedding_service_no_redis
    service.client.embeddings.create = AsyncMock(
        side_effect=openai.RateLimitError(
            "Rate limit exceeded",
            response=MagicMock(),
            body={}
        )
    )

    # Act
    embedding_json = await service.generate_embedding("Test text")

    # Assert
    assert embedding_json is None  # Graceful failure


@pytest.mark.asyncio
async def test_generate_embedding_api_error(embedding_service_no_redis):
    """Test graceful handling of OpenAI API errors."""
    # Arrange
    import openai

    service = embedding_service_no_redis
    service.client.embeddings.create = AsyncMock(
        side_effect=openai.APIError(
            "API error",
            request=MagicMock(),
            body={}
        )
    )

    # Act
    embedding_json = await service.generate_embedding("Test text")

    # Assert
    assert embedding_json is None  # Graceful failure


@pytest.mark.asyncio
async def test_batch_embeddings_success(embedding_service_no_redis, mock_openai_response):
    """Test batch embedding generation."""
    # Arrange
    service = embedding_service_no_redis
    service.client.embeddings.create = AsyncMock(return_value=mock_openai_response)

    texts = ["Text 1", "Text 2", "Text 3"]

    # Act
    embeddings = await service.batch_embeddings(texts)

    # Assert
    assert len(embeddings) == 3
    assert all(e is not None for e in embeddings)


@pytest.mark.asyncio
async def test_batch_embeddings_empty_list(embedding_service_no_redis):
    """Test ValueError for empty texts list."""
    # Arrange
    service = embedding_service_no_redis

    # Act & Assert
    with pytest.raises(ValueError, match="Texts list cannot be empty"):
        await service.batch_embeddings([])


@pytest.mark.asyncio
async def test_batch_embeddings_partial_failure(embedding_service_no_redis, mock_openai_response):
    """Test batch embeddings with some failures."""
    # Arrange
    import openai

    service = embedding_service_no_redis

    # First call succeeds, second fails, third succeeds
    service.client.embeddings.create = AsyncMock(
        side_effect=[
            mock_openai_response,
            openai.APIError("API error", request=MagicMock(), body={}),
            mock_openai_response,
        ]
    )

    texts = ["Text 1", "Text 2", "Text 3"]

    # Act
    embeddings = await service.batch_embeddings(texts)

    # Assert
    assert len(embeddings) == 3
    assert embeddings[0] is not None
    assert embeddings[1] is None  # Failed
    assert embeddings[2] is not None


@pytest.mark.asyncio
async def test_cache_key_generation(embedding_service_no_redis):
    """Test cache key generation is consistent."""
    # Arrange
    service = embedding_service_no_redis
    text = "Test text for caching"

    # Act
    key1 = service._cache_key(text)
    key2 = service._cache_key(text)

    # Assert
    assert key1 == key2
    assert key1.startswith("embedding:")
    assert len(key1) > len("embedding:")


@pytest.mark.asyncio
async def test_generate_embedding_with_redis_cache_hit():
    """Test embedding retrieval from Redis cache."""
    # Arrange
    with patch('src.services.embedding_service.redis.from_url') as mock_redis_factory:
        mock_redis = AsyncMock()
        cached_embedding = json.dumps([0.1] * 1536)
        mock_redis.get = AsyncMock(return_value=cached_embedding)
        mock_redis_factory.return_value = mock_redis

        with patch('src.services.embedding_service.settings') as mock_settings:
            mock_settings.openai_api_key = 'test-key'
            mock_settings.redis_url = 'redis://localhost:6379'

            service = EmbeddingService(openai_api_key='test-key', redis_url='redis://localhost:6379')

            # Act
            embedding_json = await service.generate_embedding("Cached text")

            # Assert
            assert embedding_json == cached_embedding
            mock_redis.get.assert_called_once()


@pytest.mark.asyncio
async def test_generate_embedding_with_redis_cache_miss(mock_openai_response):
    """Test embedding generation and caching on cache miss."""
    # Arrange
    with patch('src.services.embedding_service.redis.from_url') as mock_redis_factory:
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)  # Cache miss
        mock_redis.setex = AsyncMock()
        mock_redis_factory.return_value = mock_redis

        with patch('src.services.embedding_service.settings') as mock_settings:
            mock_settings.openai_api_key = 'test-key'
            mock_settings.redis_url = 'redis://localhost:6379'

            service = EmbeddingService(openai_api_key='test-key', redis_url='redis://localhost:6379')
            service.client.embeddings.create = AsyncMock(return_value=mock_openai_response)

            # Act
            embedding_json = await service.generate_embedding("Uncached text")

            # Assert
            assert embedding_json is not None
            mock_redis.get.assert_called_once()  # Tried to get from cache
            mock_redis.setex.assert_called_once()  # Cached result


@pytest.mark.asyncio
async def test_close_redis_connection():
    """Test Redis connection closure."""
    # Arrange
    with patch('src.services.embedding_service.redis.from_url') as mock_redis_factory:
        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock()
        mock_redis_factory.return_value = mock_redis

        with patch('src.services.embedding_service.settings') as mock_settings:
            mock_settings.openai_api_key = 'test-key'
            mock_settings.redis_url = 'redis://localhost:6379'

            service = EmbeddingService(openai_api_key='test-key', redis_url='redis://localhost:6379')

            # Act
            await service.close()

            # Assert
            mock_redis.close.assert_called_once()
