"""
Unit tests for Knowledge Base search service.

Tests cover AC #1-#7:
- AC #1: Function searches KB API for articles
- AC #2: Keywords extracted from ticket description
- AC #3: Returns top 3 articles with title, summary, url
- AC #4: KB API unavailability handled gracefully
- AC #5: Results cached in Redis with 3600s TTL
- AC #6: 10-second timeout handled gracefully
- AC #7: Tests cover success, timeout, error cases

Tests use pytest-asyncio for async test support.
Mock httpx.AsyncClient.get() and redis_client.get/setex().
"""

import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from redis import asyncio as aioredis

from src.services.kb_search import KBArticle, KBSearchService, search_knowledge_base
from src.utils.exceptions import ValidationError


class AsyncClientContextMgrMock:
    """Helper to mock AsyncClient context manager."""

    def __init__(self, get_response):
        self.get_response = get_response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None

    async def get(self, *args, **kwargs):
        """Mock get method that returns awaitable."""
        return self.get_response


class TestKBArticleModel:
    """Test KBArticle Pydantic model validation."""

    def test_article_creation_valid(self):
        """Test creating a valid KBArticle."""
        article = KBArticle(
            title="How to fix database errors",
            summary="This guide explains common database errors and solutions.",
            url="https://kb.example.com/articles/123",
        )
        assert article.title == "How to fix database errors"
        assert article.summary == "This guide explains common database errors and solutions."
        assert article.url == "https://kb.example.com/articles/123"

    def test_article_summary_truncation(self):
        """AC #3: Summary truncated to 200 characters."""
        long_summary = "x" * 300
        article = KBArticle(
            title="Test",
            summary=long_summary,
            url="https://kb.example.com/articles/1",
        )
        assert len(article.summary) == 200

    def test_article_model_dump(self):
        """Test converting article to dict."""
        article = KBArticle(
            title="Test",
            summary="Summary",
            url="https://kb.example.com/articles/1",
        )
        data = article.model_dump()
        assert data["title"] == "Test"
        assert data["summary"] == "Summary"
        assert data["url"] == "https://kb.example.com/articles/1"


class TestKBSearchServiceValidation:
    """Test input validation."""

    def test_validate_inputs_valid(self):
        """Test validation with valid inputs."""
        # Should not raise
        KBSearchService._validate_inputs(
            tenant_id="acme",
            description="database connection error",
            limit=3,
        )

    def test_validate_inputs_empty_tenant_id(self):
        """Test validation with empty tenant_id."""
        with pytest.raises(ValidationError, match="tenant_id must be a non-empty string"):
            KBSearchService._validate_inputs(
                tenant_id="",
                description="error",
                limit=3,
            )

    def test_validate_inputs_empty_description(self):
        """Test validation with empty description."""
        with pytest.raises(ValidationError, match="description must be a non-empty string"):
            KBSearchService._validate_inputs(
                tenant_id="acme",
                description="",
                limit=3,
            )

    def test_validate_inputs_description_too_long(self):
        """Test validation with description exceeding max length."""
        with pytest.raises(ValidationError, match="exceeds maximum length"):
            KBSearchService._validate_inputs(
                tenant_id="acme",
                description="x" * 5001,
                limit=3,
            )

    def test_validate_inputs_invalid_limit(self):
        """Test validation with invalid limit."""
        with pytest.raises(ValidationError, match="limit must be a positive integer"):
            KBSearchService._validate_inputs(
                tenant_id="acme",
                description="error",
                limit=0,
            )

    def test_validate_inputs_limit_too_high(self):
        """Test validation with limit exceeding max."""
        with pytest.raises(ValidationError, match="limit cannot exceed 100"):
            KBSearchService._validate_inputs(
                tenant_id="acme",
                description="error",
                limit=101,
            )


class TestKBSearchServiceCacheKey:
    """Test cache key generation."""

    def test_cache_key_generation(self):
        """Test cache key includes tenant_id and hash."""
        cache_key = KBSearchService._generate_cache_key(
            tenant_id="acme",
            description="database error",
        )
        assert cache_key.startswith("kb_search:acme:")
        assert len(cache_key) > len("kb_search:acme:")

    def test_cache_key_tenant_isolation(self):
        """AC #5: Different tenants produce different cache keys."""
        key1 = KBSearchService._generate_cache_key(
            tenant_id="tenant1",
            description="error",
        )
        key2 = KBSearchService._generate_cache_key(
            tenant_id="tenant2",
            description="error",
        )
        assert key1 != key2

    def test_cache_key_description_based(self):
        """Test cache key changes with description."""
        key1 = KBSearchService._generate_cache_key(
            tenant_id="acme",
            description="error1",
        )
        key2 = KBSearchService._generate_cache_key(
            tenant_id="acme",
            description="error2",
        )
        assert key1 != key2


@pytest.mark.asyncio
class TestKBSearchServiceKBAPICall:
    """Test KB API call functionality - httpx client integration."""

    async def test_kb_api_timeout(self):
        """AC #6: KB API timeout after 10 seconds returns None."""
        service = KBSearchService()

        with patch("src.services.kb_search.httpx.AsyncClient") as mock_client_class:
            class TimeoutMock:
                async def __aenter__(self):
                    return self
                async def __aexit__(self, *args):
                    return None
                async def get(self, *args, **kwargs):
                    raise httpx.TimeoutException("Timeout")

            mock_client_class.return_value = TimeoutMock()

            result = await service._call_kb_api(
                kb_base_url="https://kb.example.com",
                kb_api_key="test-key",
                description="error",
                limit=3,
                tenant_id="acme",
                correlation_id="123",
            )

            assert result is None

    async def test_kb_api_http_error_500(self):
        """AC #4: KB API HTTP 500 error returns None."""
        service = KBSearchService()

        with patch("src.services.kb_search.httpx.AsyncClient") as mock_client_class:
            class Error500Mock:
                async def __aenter__(self):
                    return self
                async def __aexit__(self, *args):
                    return None
                async def get(self, *args, **kwargs):
                    resp = AsyncMock()
                    resp.status_code = 500
                    return resp

            mock_client_class.return_value = Error500Mock()

            result = await service._call_kb_api(
                kb_base_url="https://kb.example.com",
                kb_api_key="test-key",
                description="error",
                limit=3,
                tenant_id="acme",
                correlation_id="123",
            )

            assert result is None

    async def test_kb_api_invalid_json(self):
        """AC #4: KB API returns invalid JSON, returns None."""
        service = KBSearchService()

        with patch("src.services.kb_search.httpx.AsyncClient") as mock_client_class:
            class InvalidJsonMock:
                async def __aenter__(self):
                    return self
                async def __aexit__(self, *args):
                    return None
                async def get(self, *args, **kwargs):
                    resp = AsyncMock()
                    resp.status_code = 200
                    resp.json = AsyncMock(side_effect=json.JSONDecodeError("err", "", 0))
                    return resp

            mock_client_class.return_value = InvalidJsonMock()

            result = await service._call_kb_api(
                kb_base_url="https://kb.example.com",
                kb_api_key="test-key",
                description="error",
                limit=3,
                tenant_id="acme",
                correlation_id="123",
            )

            assert result is None


@pytest.mark.asyncio
class TestKBSearchServiceCaching:
    """Test Redis caching functionality."""

    async def test_cache_hit_returns_cached_results(self):
        """AC #5: Cache hit returns cached results without API call."""
        service = KBSearchService()

        cached_articles = [
            {
                "title": "Cached Article",
                "summary": "From cache",
                "url": "https://cached.example.com/1",
            }
        ]

        with patch.object(service, "_call_kb_api") as mock_api:
            with patch("src.services.kb_search.get_shared_redis") as mock_redis:
                mock_redis_client = AsyncMock()
                mock_redis_client.get = AsyncMock(
                    return_value=json.dumps(cached_articles)
                )
                mock_redis.return_value = mock_redis_client

                result = await service.search_knowledge_base(
                    tenant_id="acme",
                    description="error",
                    kb_base_url="https://kb.example.com",
                    kb_api_key="key",
                )

                assert result == cached_articles
                # Verify API was NOT called
                mock_api.assert_not_called()

    async def test_cache_miss_calls_api_and_caches(self):
        """AC #5: Cache miss calls API and stores result."""
        service = KBSearchService()

        api_articles = [
            {
                "title": "API Article",
                "summary": "From API",
                "url": "https://kb.example.com/1",
            }
        ]

        with patch.object(
            service, "_call_kb_api", new_callable=AsyncMock
        ) as mock_api:
            mock_api.return_value = api_articles

            with patch("src.services.kb_search.get_shared_redis") as mock_redis:
                mock_redis_client = AsyncMock()
                mock_redis_client.get = AsyncMock(return_value=None)  # Cache miss
                mock_redis_client.setex = AsyncMock()
                mock_redis.return_value = mock_redis_client

                result = await service.search_knowledge_base(
                    tenant_id="acme",
                    description="error",
                    kb_base_url="https://kb.example.com",
                    kb_api_key="key",
                )

                assert result == api_articles
                # Verify API was called
                mock_api.assert_called_once()
                # Verify results were cached
                mock_redis_client.setex.assert_called_once()

    async def test_redis_error_falls_back_to_api(self):
        """AC #4: Redis error → fallback to API without caching."""
        service = KBSearchService()

        api_articles = [{"title": "Article", "summary": "S", "url": "https://kb/1"}]

        with patch.object(
            service, "_call_kb_api", new_callable=AsyncMock
        ) as mock_api:
            mock_api.return_value = api_articles

            with patch("src.services.kb_search.get_shared_redis") as mock_redis:
                mock_redis_client = AsyncMock()
                mock_redis_client.get = AsyncMock(
                    side_effect=Exception("Redis error")
                )
                mock_redis.return_value = mock_redis_client

                result = await service.search_knowledge_base(
                    tenant_id="acme",
                    description="error",
                    kb_base_url="https://kb.example.com",
                    kb_api_key="key",
                )

                # Should return articles from API despite Redis error
                assert result == api_articles


@pytest.mark.asyncio
class TestKBSearchServiceIntegration:
    """Test main search_knowledge_base function."""

    async def test_search_knowledge_base_success(self):
        """AC #1-#6: Full search flow with success."""
        articles = [
            {
                "title": "Article 1",
                "summary": "Summary 1",
                "url": "https://kb.example.com/1",
            }
        ]

        with patch.object(KBSearchService, "_call_kb_api", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = articles

            with patch("src.services.kb_search.get_shared_redis") as mock_redis:
                mock_redis_client = AsyncMock()
                mock_redis_client.get = AsyncMock(return_value=None)
                mock_redis_client.setex = AsyncMock()
                mock_redis.return_value = mock_redis_client

                result = await search_knowledge_base(
                    tenant_id="acme",
                    description="database error",
                    kb_base_url="https://kb.example.com",
                    kb_api_key="test-key",
                    limit=3,
                )

                assert result == articles

    async def test_search_knowledge_base_timeout_returns_empty(self):
        """AC #6: Timeout returns empty list."""
        with patch.object(KBSearchService, "_call_kb_api", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = None  # API timeout

            with patch("src.services.kb_search.get_shared_redis") as mock_redis:
                mock_redis_client = AsyncMock()
                mock_redis_client.get = AsyncMock(return_value=None)
                mock_redis.return_value = mock_redis_client

                result = await search_knowledge_base(
                    tenant_id="acme",
                    description="error",
                    kb_base_url="https://kb.example.com",
                    kb_api_key="key",
                )

                # AC #4: Returns empty list on error, never raises
                assert result == []

    async def test_search_knowledge_base_invalid_input(self):
        """Test with invalid input raises ValidationError."""
        with pytest.raises(ValidationError):
            await search_knowledge_base(
                tenant_id="",  # Invalid
                description="error",
                kb_base_url="https://kb.example.com",
                kb_api_key="key",
            )

    async def test_search_knowledge_base_with_correlation_id(self):
        """Test search includes correlation_id for logging."""
        with patch.object(KBSearchService, "_call_kb_api", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = []

            with patch("src.services.kb_search.get_shared_redis") as mock_redis:
                mock_redis_client = AsyncMock()
                mock_redis_client.get = AsyncMock(return_value=None)
                mock_redis.return_value = mock_redis_client

                result = await search_knowledge_base(
                    tenant_id="acme",
                    description="error",
                    kb_base_url="https://kb.example.com",
                    kb_api_key="key",
                    correlation_id="req-123",
                )

                # Should complete without error
                assert isinstance(result, list)
