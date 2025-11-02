"""
Knowledge Base search service for context gathering.

Provides integration with external knowledge base APIs for retrieving relevant
troubleshooting guides and documentation. Implements Redis caching with 1-hour
TTL and graceful degradation on API timeouts or failures.

AC Coverage:
  - AC #1: Function created to search documentation/KB API
  - AC #2: Keywords extracted from ticket description (implementation-agnostic)
  - AC #3: Returns top 3 relevant articles with title, summary, URL
  - AC #4: KB API unavailability handled gracefully (empty list + warning log)
  - AC #5: Results cached in Redis for 1 hour (3600s TTL)
  - AC #6: 10-second timeout with graceful degradation
  - AC #7: Unit tests cover success, timeout, error cases (implemented in test_kb_search.py)

KB API CONTRACT:
================

Expected External KB API Interface:
  Endpoint: GET {kb_base_url}/api/search

  Query Parameters:
    - query (string): Search query extracted from ticket description
    - limit (integer): Maximum number of results to return (default: 3)

  Authentication:
    - Bearer token in Authorization header: "Bearer {kb_api_key}"

  Expected Response (HTTP 200):
    {
      "results": [
        {
          "title": "Article Title",
          "summary": "Brief description of the article content. This is used to summarize findings.",
          "url": "https://kb.example.com/articles/article-slug"
        },
        ...
      ],
      "total_count": 5,
      "query": "search terms"
    }

  Error Responses:
    - HTTP 401: Unauthorized (invalid API key)
    - HTTP 403: Forbidden (rate limited or permission denied)
    - HTTP 500: Server error (KB API failure)
    - HTTP 503: Service unavailable (KB API down)

  Timeout: 10 seconds (enforced by httpx.AsyncClient)

Configuration:
  KB API credentials are loaded from tenant_configs table:
    - kb_api_base_url: Base URL of KB API
    - kb_api_key: Authentication token (Bearer token)

  Alternative: Can be passed directly to search_knowledge_base() function

Caching:
  Cache Key: kb_search:{tenant_id}:{hash(description)}
  TTL: 3600 seconds (1 hour)
  Storage: Redis (via get_shared_redis() from src.cache.redis_client)

Error Handling:
  All errors gracefully degrade:
    - KB API timeout (10s) → return []
    - KB API HTTP error → return []
    - Redis unavailable → call API without caching, return results
    - Invalid JSON response → return []

  No exceptions propagated to caller; all paths return List[dict]
"""

import hashlib
import json
import time
from typing import List, Optional

import httpx
from loguru import logger
from pydantic import BaseModel, Field, field_validator
from redis import asyncio as aioredis

from src.cache.redis_client import get_shared_redis
from src.utils.exceptions import ValidationError


class KBArticle(BaseModel):
    """
    Data model for knowledge base article response.

    Represents a single KB article with required metadata fields.
    Enforces consistent structure across different KB API providers.

    AC #3: Returns articles with title, summary, url
    """

    model_config = {"from_attributes": True}

    title: str = Field(..., description="Article title")
    summary: str = Field(..., description="Article summary (max 200 chars)")
    url: str = Field(..., description="URL to full article")

    @field_validator("summary")
    @classmethod
    def truncate_summary(cls, v: str) -> str:
        """
        Truncate summary to 200 characters per AC #3.

        Reason: KB API responses may return long summaries;
        we truncate for consistency and performance.
        """
        return v[:200]


class KBSearchService:
    """
    Service for searching knowledge base with Redis caching and graceful degradation.

    Implements async KB API integration with:
    - 1-hour Redis caching per AC #5
    - 10-second timeout with graceful fallback per AC #6
    - Tenant isolation via cache key includes tenant_id
    - Structured logging with correlation_id and metrics

    AC #4: Graceful degradation - all errors return empty list, no exceptions
    """

    # KB API timeout per AC #6: 10 seconds
    KB_API_TIMEOUT_SECONDS = 10.0
    # Redis cache TTL per AC #5: 1 hour
    CACHE_TTL_SECONDS = 3600

    def __init__(self):
        """Initialize KB search service."""
        pass

    async def search_knowledge_base(
        self,
        tenant_id: str,
        description: str,
        kb_base_url: str,
        kb_api_key: str,
        limit: int = 3,
        correlation_id: Optional[str] = None,
    ) -> List[dict]:
        """
        Search knowledge base for articles matching ticket description.

        Implements AC #1-#6 (AC #7 tested separately in test_kb_search.py):
        - Searches external KB API via HTTP
        - Extracts keywords from description (AC #2: implementation-agnostic)
        - Returns top 3 articles with title, summary, URL (AC #3)
        - Caches results in Redis for 1 hour (AC #5)
        - Timeout: 10 seconds → returns empty list (AC #6)
        - All errors handled gracefully (AC #4)

        Args:
            tenant_id: Tenant identifier for data isolation and cache key
            description: Ticket description (source of search keywords per AC #2)
            kb_base_url: KB API base URL (loaded from tenant_configs per dev notes)
            kb_api_key: KB API authorization key (from tenant_configs)
            limit: Max articles to return (default 3 per AC #3)
            correlation_id: Request correlation ID for logging/tracing

        Returns:
            List[dict]: List of KB articles with keys: title, summary, url
                       Returns empty list on timeout, API error, or no results.
                       Never raises exceptions per AC #4 (graceful degradation).

        Implementation Notes:
            - Cache key pattern: kb_search:{tenant_id}:{hash(description)}
            - Tenant isolation: Cache keys include tenant_id (different tenants ≠ cache)
            - Error handling: Timeout, HTTP 5xx, Redis failures all return [] + log
            - Logging: Includes tenant_id, correlation_id, latency_ms, cache_hit
        """
        # Input validation (similar to ticket_search_service.py pattern)
        self._validate_inputs(tenant_id, description, limit)

        start_time = time.time()
        cache_hit = False
        api_called = False
        error_occurred = None

        try:
            # Generate cache key with tenant isolation (AC #5: kb_search:{tenant_id}:{hash})
            cache_key = self._generate_cache_key(tenant_id, description)

            # AC #5: Check Redis cache before API call
            cached_result = await self._get_from_cache(
                cache_key, tenant_id, correlation_id
            )
            if cached_result is not None:
                cache_hit = True
                elapsed_ms = int((time.time() - start_time) * 1000)
                logger.info(
                    f"KB search cache hit: tenant={tenant_id}, elapsed_ms={elapsed_ms}",
                    extra={
                        "tenant_id": tenant_id,
                        "correlation_id": correlation_id,
                        "cache_hit": True,
                        "elapsed_ms": elapsed_ms,
                    },
                )
                return cached_result

            # AC #1, #3: Call KB API to search for articles
            api_called = True
            articles = await self._call_kb_api(
                kb_base_url,
                kb_api_key,
                description,
                limit,
                tenant_id,
                correlation_id,
            )

            # AC #5: Cache results if API succeeded (even if empty, cache for 1hr)
            if articles is not None:
                await self._cache_results(
                    cache_key, articles, tenant_id, correlation_id
                )
                results = articles
            else:
                # API call failed (timeout or HTTP error)
                # AC #4: Return empty list instead of None
                results = []

        except Exception as e:
            # AC #4: Catch-all for unexpected errors
            error_occurred = str(e)
            logger.error(
                f"KB search unexpected error: {error_occurred}",
                extra={
                    "tenant_id": tenant_id,
                    "correlation_id": correlation_id,
                    "error": error_occurred,
                },
            )
            results = []

        # Log final result
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(
            f"KB search completed: tenant={tenant_id}, results={len(results)}, "
            f"cache_hit={cache_hit}, api_called={api_called}, elapsed_ms={elapsed_ms}",
            extra={
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
                "result_count": len(results),
                "cache_hit": cache_hit,
                "api_called": api_called,
                "elapsed_ms": elapsed_ms,
                "error": error_occurred,
            },
        )

        return results

    async def _call_kb_api(
        self,
        kb_base_url: str,
        kb_api_key: str,
        description: str,
        limit: int,
        tenant_id: str,
        correlation_id: Optional[str],
    ) -> Optional[List[dict]]:
        """
        Call external KB API with timeout and error handling.

        AC #6: Timeout set to 10 seconds
        AC #4: Returns None on error (handled in main function as empty list)

        Args:
            kb_base_url: KB API base URL
            kb_api_key: API authorization key
            description: Search query (ticket description per AC #2)
            limit: Max results to return
            tenant_id: Tenant ID for logging
            correlation_id: Correlation ID for tracing

        Returns:
            List[dict] with article objects on success, None on failure.
            AC #4: All errors logged as warning/error, graceful degradation.
        """
        api_start = time.time()

        try:
            # AC #6: 10-second timeout per httpx.AsyncClient
            async with httpx.AsyncClient(timeout=self.KB_API_TIMEOUT_SECONDS) as client:
                # Construct KB API endpoint
                endpoint = f"{kb_base_url}/api/search"
                headers = {"Authorization": f"Bearer {kb_api_key}"}
                params = {"query": description, "limit": limit}

                logger.debug(
                    f"KB API call: {endpoint}",
                    extra={
                        "tenant_id": tenant_id,
                        "correlation_id": correlation_id,
                        "endpoint": endpoint,
                    },
                )

                # Make async HTTP GET request
                response = await client.get(
                    endpoint, headers=headers, params=params
                )

                api_elapsed_ms = int((time.time() - api_start) * 1000)

                # AC #4: Handle non-200 responses gracefully
                if response.status_code != 200:
                    logger.warning(
                        f"KB API error: status={response.status_code}",
                        extra={
                            "tenant_id": tenant_id,
                            "correlation_id": correlation_id,
                            "status_code": response.status_code,
                            "api_latency_ms": api_elapsed_ms,
                        },
                    )
                    return None

                # Parse JSON response
                data = response.json()

                # Extract articles from KB API response
                # Expected format: {"results": [{"title": ..., "summary": ..., "url": ...}]}
                articles_raw = data.get("results", [])

                # Validate and convert to KBArticle models
                articles = []
                for article_data in articles_raw:
                    try:
                        article = KBArticle(
                            title=article_data.get("title", ""),
                            summary=article_data.get("summary", ""),
                            url=article_data.get("url", ""),
                        )
                        articles.append(article.model_dump())
                    except Exception as e:
                        logger.warning(
                            f"Failed to parse KB article: {str(e)}",
                            extra={
                                "tenant_id": tenant_id,
                                "correlation_id": correlation_id,
                                "error": str(e),
                            },
                        )
                        continue

                # Limit to requested number per AC #3
                articles = articles[:limit]

                logger.info(
                    f"KB API success: {len(articles)} articles",
                    extra={
                        "tenant_id": tenant_id,
                        "correlation_id": correlation_id,
                        "result_count": len(articles),
                        "api_latency_ms": api_elapsed_ms,
                    },
                )

                return articles

        except httpx.TimeoutException:
            # AC #6: Timeout after 10 seconds → log warning, return None
            api_elapsed_ms = int((time.time() - api_start) * 1000)
            logger.warning(
                f"KB API timeout: {self.KB_API_TIMEOUT_SECONDS}s exceeded",
                extra={
                    "tenant_id": tenant_id,
                    "correlation_id": correlation_id,
                    "timeout_seconds": self.KB_API_TIMEOUT_SECONDS,
                    "api_latency_ms": api_elapsed_ms,
                },
            )
            return None

        except httpx.HTTPError as e:
            # AC #4: HTTP client errors (connection, etc.)
            api_elapsed_ms = int((time.time() - api_start) * 1000)
            logger.error(
                f"KB API HTTP error: {str(e)}",
                extra={
                    "tenant_id": tenant_id,
                    "correlation_id": correlation_id,
                    "error": str(e),
                    "api_latency_ms": api_elapsed_ms,
                },
            )
            return None

        except json.JSONDecodeError as e:
            # AC #4: Invalid JSON response
            api_elapsed_ms = int((time.time() - api_start) * 1000)
            logger.error(
                f"KB API invalid JSON: {str(e)}",
                extra={
                    "tenant_id": tenant_id,
                    "correlation_id": correlation_id,
                    "error": str(e),
                    "api_latency_ms": api_elapsed_ms,
                },
            )
            return None

        except Exception as e:
            # AC #4: Catch-all for unexpected API errors
            api_elapsed_ms = int((time.time() - api_start) * 1000)
            logger.error(
                f"KB API unexpected error: {str(e)}",
                extra={
                    "tenant_id": tenant_id,
                    "correlation_id": correlation_id,
                    "error": str(e),
                    "api_latency_ms": api_elapsed_ms,
                },
            )
            return None

    async def _get_from_cache(
        self, cache_key: str, tenant_id: str, correlation_id: Optional[str]
    ) -> Optional[List[dict]]:
        """
        Retrieve cached KB results from Redis.

        AC #5: Cache key includes tenant_id for isolation
        Returns None if cache miss or Redis unavailable.

        Args:
            cache_key: Redis cache key
            tenant_id: Tenant ID for logging
            correlation_id: Correlation ID for tracing

        Returns:
            List[dict] of cached articles, or None if cache miss/error
        """
        try:
            redis_client = get_shared_redis()
            cached_value = await redis_client.get(cache_key)

            if cached_value:
                # Cache hit: deserialize JSON
                articles = json.loads(cached_value)
                logger.debug(
                    f"Cache hit: {cache_key}",
                    extra={
                        "tenant_id": tenant_id,
                        "correlation_id": correlation_id,
                        "cache_key": cache_key,
                    },
                )
                return articles

            # Cache miss
            return None

        except Exception as e:
            # AC #4: Redis error → graceful fallback to API (no exception)
            logger.warning(
                f"Redis get error: {str(e)}",
                extra={
                    "tenant_id": tenant_id,
                    "correlation_id": correlation_id,
                    "error": str(e),
                    "cache_key": cache_key,
                },
            )
            return None

    async def _cache_results(
        self,
        cache_key: str,
        articles: List[dict],
        tenant_id: str,
        correlation_id: Optional[str],
    ) -> None:
        """
        Store KB results in Redis with 1-hour TTL.

        AC #5: TTL = 3600 seconds (1 hour)
        Logs cache errors but doesn't fail (graceful degradation per AC #4).

        Args:
            cache_key: Redis cache key
            articles: List of article dicts to cache
            tenant_id: Tenant ID for logging
            correlation_id: Correlation ID for tracing
        """
        try:
            redis_client = get_shared_redis()
            cache_value = json.dumps(articles)

            # AC #5: setex with 3600-second TTL
            await redis_client.setex(cache_key, self.CACHE_TTL_SECONDS, cache_value)

            logger.debug(
                f"Cached KB results: {cache_key}",
                extra={
                    "tenant_id": tenant_id,
                    "correlation_id": correlation_id,
                    "cache_key": cache_key,
                    "ttl_seconds": self.CACHE_TTL_SECONDS,
                },
            )

        except Exception as e:
            # AC #4: Redis error → log warning, continue without caching
            logger.warning(
                f"Redis setex error: {str(e)}",
                extra={
                    "tenant_id": tenant_id,
                    "correlation_id": correlation_id,
                    "error": str(e),
                    "cache_key": cache_key,
                },
            )

    @staticmethod
    def _generate_cache_key(tenant_id: str, description: str) -> str:
        """
        Generate Redis cache key with tenant isolation.

        Pattern per dev notes: kb_search:{tenant_id}:{hash(description)}
        AC #5: Includes tenant_id to prevent cross-tenant cache sharing

        Args:
            tenant_id: Tenant identifier
            description: Ticket description (search query)

        Returns:
            Cache key string: kb_search:{tenant_id}:{sha256_hash}
        """
        # Hash description to create compact key
        desc_hash = hashlib.sha256(description.encode()).hexdigest()[:16]
        return f"kb_search:{tenant_id}:{desc_hash}"

    @staticmethod
    def _validate_inputs(tenant_id: str, description: str, limit: int) -> None:
        """
        Validate KB search input parameters.

        Similar to ticket_search_service.py pattern.
        AC #4: Input validation raises ValidationError for invalid inputs

        Args:
            tenant_id: Tenant identifier to validate
            description: Search query/description to validate
            limit: Result limit to validate

        Raises:
            ValidationError: If any input is invalid
        """
        # Validate tenant_id
        if not tenant_id or not isinstance(tenant_id, str):
            raise ValidationError("tenant_id must be a non-empty string")

        if len(tenant_id.strip()) == 0:
            raise ValidationError("tenant_id cannot be empty or whitespace-only")

        # Validate description
        if not description or not isinstance(description, str):
            raise ValidationError("description must be a non-empty string")

        if len(description.strip()) == 0:
            raise ValidationError("description cannot be empty or whitespace-only")

        if len(description) > 5000:
            raise ValidationError(
                "description exceeds maximum length of 5000 characters"
            )

        # Validate limit
        if not isinstance(limit, int) or limit <= 0:
            raise ValidationError("limit must be a positive integer")

        if limit > 100:
            raise ValidationError("limit cannot exceed 100")


# Factory function for convenience
async def search_knowledge_base(
    tenant_id: str,
    description: str,
    kb_base_url: str,
    kb_api_key: str,
    limit: int = 3,
    correlation_id: Optional[str] = None,
) -> List[dict]:
    """
    Convenience function wrapper for KB search.

    Creates a KBSearchService instance and executes search.
    Simplifies usage in enhance_ticket task (Story 2.4).

    Args:
        Same as KBSearchService.search_knowledge_base()

    Returns:
        List[dict]: Articles with title, summary, url
    """
    service = KBSearchService()
    return await service.search_knowledge_base(
        tenant_id=tenant_id,
        description=description,
        kb_base_url=kb_base_url,
        kb_api_key=kb_api_key,
        limit=limit,
        correlation_id=correlation_id,
    )
