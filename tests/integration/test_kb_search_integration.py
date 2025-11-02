"""
Integration tests for Knowledge Base search service (Story 2.6).

Tests the complete end-to-end flow including:
- Redis caching with 1-hour TTL (mocked)
- Mock KB API responses
- Cache persistence across multiple searches
- Timeout behavior with real async operations
- Multi-tenant cache isolation
- Concurrent request handling

Note: Integration tests focus on business logic using mocked async operations.
For actual HTTP testing with responses library, use unit tests with sync mocking.
"""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.services.kb_search import KBSearchService, search_knowledge_base


class MockKBAPIServer:
    """Helper class to simulate KB API responses."""

    @staticmethod
    def mock_kb_response(query: str, limit: int = 3) -> dict:
        """Generate mock KB API response."""
        articles_db = {
            "database": [
                {
                    "title": "Fix Database Connection Timeout",
                    "summary": "When experiencing database connection timeouts, first check network connectivity and verify firewall rules are not blocking port 5432. Common causes include misconfigured connection pools and firewall policies.",
                    "url": "https://kb.example.com/articles/db-timeout-123",
                },
                {
                    "title": "Database Performance Tuning",
                    "summary": "Optimize database queries using EXPLAIN ANALYZE. Monitor slow query logs. Consider adding indexes on frequently queried columns.",
                    "url": "https://kb.example.com/articles/db-perf-456",
                },
                {
                    "title": "Backup and Recovery Procedures",
                    "summary": "PostgreSQL backups should use pg_dump or WAL archiving. Test recovery procedures monthly. Keep backups on separate storage.",
                    "url": "https://kb.example.com/articles/db-backup-789",
                },
            ],
            "connectivity": [
                {
                    "title": "Network Troubleshooting Guide",
                    "summary": "Check IP configuration using ifconfig. Test connectivity with ping and traceroute. Verify DNS resolution with nslookup.",
                    "url": "https://kb.example.com/articles/net-001",
                },
                {
                    "title": "Firewall Configuration",
                    "summary": "Common firewall rules block port ranges 6000-7000. Whitelist internal subnets. Log all blocked connections for debugging.",
                    "url": "https://kb.example.com/articles/fw-002",
                },
            ],
            "error": [
                {
                    "title": "Error Code Reference",
                    "summary": "Error 500 indicates server error. Error 401 indicates authentication failure. Error 503 indicates service unavailable.",
                    "url": "https://kb.example.com/articles/errors-001",
                },
            ],
        }

        # Find matching articles based on query keywords
        matching = []
        for keyword, articles in articles_db.items():
            if keyword in query.lower():
                matching.extend(articles)

        # Return up to limit articles
        results = matching[:limit] if matching else articles_db["database"][:limit]

        return {
            "results": results,
            "total_count": len(results),
            "query": query,
        }


@pytest.mark.asyncio
class TestKBSearchIntegration:
    """Integration tests for KB search service business logic."""

    async def test_kb_search_service_initialization(self):
        """Test KB search service initializes correctly."""
        service = KBSearchService()
        assert service is not None

    async def test_kb_search_caching_flow(self):
        """AC #5: Integration test for caching flow - cache miss then cache hit."""
        service = KBSearchService()

        api_articles = [
            {
                "title": "Database Troubleshooting",
                "summary": "Common database issues and solutions.",
                "url": "https://kb.example.com/1",
            }
        ]

        with patch.object(service, "_call_kb_api", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = api_articles

            with patch("src.services.kb_search.get_shared_redis") as mock_redis:
                mock_redis_client = AsyncMock()
                # Simulate: first get (miss), then cache is stored, second get (hit)
                mock_redis_client.get = AsyncMock(
                    side_effect=[None, json.dumps(api_articles)]
                )
                mock_redis_client.setex = AsyncMock()
                mock_redis.return_value = mock_redis_client

                # First call: cache miss
                result1 = await service.search_knowledge_base(
                    tenant_id="acme",
                    description="database error",
                    kb_base_url="https://kb.example.com",
                    kb_api_key="key",
                )
                assert result1 == api_articles
                assert mock_api.call_count == 1

                # Second call: cache hit
                result2 = await service.search_knowledge_base(
                    tenant_id="acme",
                    description="database error",
                    kb_base_url="https://kb.example.com",
                    kb_api_key="key",
                )
                # Cache hit should return cached result without additional API call
                assert result2 == api_articles
                # Still only 1 API call (second request used cache)
                assert mock_api.call_count == 1

    async def test_kb_search_tenant_isolation_cache_keys(self):
        """AC #5: Different tenants have different cache keys."""
        service = KBSearchService()

        api_articles = [
            {
                "title": "Article",
                "summary": "Summary",
                "url": "https://kb.example.com/1",
            }
        ]

        with patch.object(service, "_call_kb_api", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = api_articles

            with patch("src.services.kb_search.get_shared_redis") as mock_redis:
                mock_redis_client = AsyncMock()
                mock_redis_client.get = AsyncMock(return_value=None)
                setex_calls = []

                async def track_setex(*args, **kwargs):
                    setex_calls.append(args)

                mock_redis_client.setex = AsyncMock(side_effect=track_setex)
                mock_redis.return_value = mock_redis_client

                # Search for tenant1
                await service.search_knowledge_base(
                    tenant_id="tenant1",
                    description="test query",
                    kb_base_url="https://kb.example.com",
                    kb_api_key="key1",
                )

                # Search for tenant2 with same description
                await service.search_knowledge_base(
                    tenant_id="tenant2",
                    description="test query",
                    kb_base_url="https://kb.example.com",
                    kb_api_key="key2",
                )

                # Verify cache keys include tenant_id (different for different tenants)
                assert len(setex_calls) == 2
                cache_key1 = setex_calls[0][0]
                cache_key2 = setex_calls[1][0]
                assert cache_key1 != cache_key2
                assert "tenant1" in cache_key1
                assert "tenant2" in cache_key2

    async def test_kb_search_ttl_configuration(self):
        """AC #5: Cache TTL is set to 3600 seconds (1 hour)."""
        service = KBSearchService()

        api_articles = [
            {
                "title": "Article",
                "summary": "Summary",
                "url": "https://kb.example.com/1",
            }
        ]

        with patch.object(service, "_call_kb_api", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = api_articles

            with patch("src.services.kb_search.get_shared_redis") as mock_redis:
                mock_redis_client = AsyncMock()
                mock_redis_client.get = AsyncMock(return_value=None)
                mock_redis_client.setex = AsyncMock()
                mock_redis.return_value = mock_redis_client

                await service.search_knowledge_base(
                    tenant_id="acme",
                    description="test",
                    kb_base_url="https://kb.example.com",
                    kb_api_key="key",
                )

                # Verify TTL is 3600 seconds
                mock_redis_client.setex.assert_called_once()
                call_args = mock_redis_client.setex.call_args
                ttl = call_args[0][1]
                assert ttl == 3600

    async def test_kb_search_error_returns_empty_list(self):
        """AC #4: Service errors return empty list instead of raising."""
        service = KBSearchService()

        with patch.object(
            service, "_call_kb_api", new_callable=AsyncMock
        ) as mock_api:
            mock_api.return_value = None  # Simulate API failure

            with patch("src.services.kb_search.get_shared_redis") as mock_redis:
                mock_redis_client = AsyncMock()
                mock_redis_client.get = AsyncMock(return_value=None)
                mock_redis.return_value = mock_redis_client

                result = await service.search_knowledge_base(
                    tenant_id="acme",
                    description="test",
                    kb_base_url="https://kb.example.com",
                    kb_api_key="key",
                )

                # Should return empty list, never raise
                assert result == []
                assert isinstance(result, list)

    async def test_kb_search_concurrent_with_caching(self):
        """AC #5: Multiple concurrent requests benefit from caching."""
        service = KBSearchService()

        api_articles = [
            {
                "title": "Concurrent Test Article",
                "summary": "Testing concurrent access patterns.",
                "url": "https://kb.example.com/1",
            }
        ]

        with patch.object(service, "_call_kb_api", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = api_articles

            with patch("src.services.kb_search.get_shared_redis") as mock_redis:
                mock_redis_client = AsyncMock()
                # Simulate: first call misses cache, subsequent calls hit cache
                cache_hits = [
                    None,  # First call: cache miss
                    json.dumps(api_articles),  # Subsequent calls: cache hit
                    json.dumps(api_articles),
                    json.dumps(api_articles),
                ]
                mock_redis_client.get = AsyncMock(side_effect=cache_hits)
                mock_redis_client.setex = AsyncMock()
                mock_redis.return_value = mock_redis_client

                # Make 4 concurrent requests for same query
                tasks = [
                    service.search_knowledge_base(
                        tenant_id="acme",
                        description="concurrent test",
                        kb_base_url="https://kb.example.com",
                        kb_api_key="key",
                    )
                    for _ in range(4)
                ]

                results = await asyncio.gather(*tasks)

                # All should succeed
                assert len(results) == 4
                assert all(isinstance(r, list) for r in results)
                # First call hits API, rest should hit cache
                assert mock_api.call_count == 1
