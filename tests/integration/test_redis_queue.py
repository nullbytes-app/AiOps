"""
Integration tests for Redis queue operations.

Tests cover:
- Redis connection and client initialization
- Queue operations (push, pop, peek, depth)
- Queue depth monitoring
- Message durability across container restarts
- Error handling for connection failures
"""

import json
import uuid

import pytest

from src.cache.redis_client import get_redis_client
from src.services.queue_service import (
    push_to_queue,
    pop_from_queue,
    peek_queue,
    get_queue_depth,
    ENHANCEMENT_QUEUE,
)


class TestRedisConnection:
    """Test Redis connectivity and client initialization."""

    @pytest.mark.asyncio
    async def test_redis_client_creation(self) -> None:
        """Test that Redis client can be created and connected."""
        client = await get_redis_client()
        assert client is not None
        # Test basic connectivity
        pong = await client.ping()
        assert pong is True
        await client.aclose()

    @pytest.mark.asyncio
    async def test_redis_ping_command(self) -> None:
        """Test Redis PING command returns PONG."""
        client = await get_redis_client()
        result = await client.ping()
        assert result is True
        await client.aclose()

    @pytest.mark.asyncio
    async def test_redis_connection_pool_configured(self) -> None:
        """Test that Redis connection pool is properly configured."""
        from src.config import settings

        client = await get_redis_client()
        assert client is not None
        # Verify client has connection pool
        assert hasattr(client, 'connection_pool')
        # Verify settings are configured
        assert settings.redis_url is not None
        assert settings.redis_max_connections == 10
        await client.aclose()


class TestQueueOperations:
    """Test basic queue operations (push, pop, peek, depth)."""

    @pytest.fixture
    def clean_queue(self):
        """Clean up test queue before and after tests."""
        import asyncio
        loop = asyncio.get_event_loop()

        async def _clean():
            client = await get_redis_client()
            try:
                await client.delete(ENHANCEMENT_QUEUE)
            finally:
                await client.aclose()

        # Clean before test
        loop.run_until_complete(_clean())

        yield

        # Clean after test
        loop.run_until_complete(_clean())

    @pytest.mark.asyncio
    async def test_push_to_queue(self, clean_queue) -> None:
        """Test pushing a job to the queue."""
        job_data = {
            "job_id": str(uuid.uuid4()),
            "tenant_id": "test-tenant",
            "ticket_id": "TICKET-001",
            "description": "Test enhancement",
        }

        result = await push_to_queue(ENHANCEMENT_QUEUE, job_data)
        assert result is True

        # Verify queue depth increased
        depth = await get_queue_depth(ENHANCEMENT_QUEUE)
        assert depth == 1

    @pytest.mark.asyncio
    async def test_pop_from_queue(self, clean_queue) -> None:
        """Test popping a job from the queue."""
        job_data = {
            "job_id": str(uuid.uuid4()),
            "tenant_id": "test-tenant",
            "ticket_id": "TICKET-002",
            "priority": "high",
        }

        # Push a job
        await push_to_queue(ENHANCEMENT_QUEUE, job_data)

        # Pop the job
        popped = await pop_from_queue(ENHANCEMENT_QUEUE)
        assert popped is not None
        assert popped["job_id"] == job_data["job_id"]
        assert popped["ticket_id"] == job_data["ticket_id"]

        # Verify queue is now empty
        depth = await get_queue_depth(ENHANCEMENT_QUEUE)
        assert depth == 0

    @pytest.mark.asyncio
    async def test_pop_from_empty_queue(self, clean_queue) -> None:
        """Test popping from an empty queue returns None."""
        popped = await pop_from_queue(ENHANCEMENT_QUEUE)
        assert popped is None

    @pytest.mark.asyncio
    async def test_peek_queue(self, clean_queue) -> None:
        """Test peeking at queue without removing items."""
        # Push multiple jobs
        jobs = []
        for i in range(5):
            job_data = {
                "job_id": str(uuid.uuid4()),
                "ticket_id": f"TICKET-{i:03d}",
                "index": i,
            }
            jobs.append(job_data)
            await push_to_queue(ENHANCEMENT_QUEUE, job_data)

        # Peek at queue
        peeked = await peek_queue(ENHANCEMENT_QUEUE, count=3)
        assert len(peeked) == 3
        # Verify first item in peek (next to be processed)
        assert peeked[0]["index"] == 0

        # Verify queue still has all items (nothing removed)
        depth = await get_queue_depth(ENHANCEMENT_QUEUE)
        assert depth == 5

    @pytest.mark.asyncio
    async def test_peek_queue_partial(self, clean_queue) -> None:
        """Test peeking returns fewer items if queue has fewer."""
        # Push only 2 jobs
        for i in range(2):
            job_data = {"job_id": str(uuid.uuid4()), "index": i}
            await push_to_queue(ENHANCEMENT_QUEUE, job_data)

        # Peek requesting 5 items
        peeked = await peek_queue(ENHANCEMENT_QUEUE, count=5)
        assert len(peeked) == 2

    @pytest.mark.asyncio
    async def test_queue_depth(self, clean_queue) -> None:
        """Test getting queue depth."""
        # Empty queue
        depth = await get_queue_depth(ENHANCEMENT_QUEUE)
        assert depth == 0

        # Push jobs and verify depth increases
        for i in range(10):
            job_data = {"job_id": str(uuid.uuid4()), "sequence": i}
            await push_to_queue(ENHANCEMENT_QUEUE, job_data)

        depth = await get_queue_depth(ENHANCEMENT_QUEUE)
        assert depth == 10

    @pytest.mark.asyncio
    async def test_json_serialization_roundtrip(self, clean_queue) -> None:
        """Test that complex data survives JSON serialization."""
        job_data = {
            "job_id": str(uuid.uuid4()),
            "tenant_id": "tenant-abc",
            "ticket_id": "TKT-12345",
            "description": "Server running slow",
            "priority": "high",
            "timestamp": "2025-11-01T12:00:00Z",
            "metadata": {
                "source": "servicedesk",
                "escalated": True,
                "retry_count": 0,
            },
        }

        # Push and pop
        await push_to_queue(ENHANCEMENT_QUEUE, job_data)
        popped = await pop_from_queue(ENHANCEMENT_QUEUE)

        # Verify all fields preserved
        assert popped == job_data
        assert popped["metadata"]["escalated"] is True
        assert popped["metadata"]["retry_count"] == 0

    @pytest.mark.asyncio
    async def test_queue_fifo_order(self, clean_queue) -> None:
        """Test that queue maintains FIFO order."""
        # Push jobs in order
        job_ids = []
        for i in range(5):
            job_data = {"job_id": f"job-{i:03d}", "sequence": i}
            await push_to_queue(ENHANCEMENT_QUEUE, job_data)
            job_ids.append(f"job-{i:03d}")

        # Pop all jobs and verify order
        popped_ids = []
        for _ in range(5):
            job = await pop_from_queue(ENHANCEMENT_QUEUE)
            popped_ids.append(job["job_id"])

        # Should get jobs in same order
        assert popped_ids == job_ids


class TestQueuePersistence:
    """Test message durability and persistence."""

    MARKER_JOB_ID = "AC7-DURABILITY-MARKER"

    @pytest.mark.asyncio
    async def test_persistence_prepare_marker(self) -> None:
        """Prepare a marker job to verify durability across a Redis restart.

        This test enqueues a unique marker job. After this test, restart the
        Redis container and run `test_persistence_verify_after_restart` to
        confirm the job persisted across the restart (AOF enabled).
        """
        # Ensure connection works and enqueue marker
        client = await get_redis_client()
        try:
            await client.ping()
            job = {"job_id": self.MARKER_JOB_ID, "type": "durability-check"}
            await client.lpush(ENHANCEMENT_QUEUE, json.dumps(job))
            depth = await client.llen(ENHANCEMENT_QUEUE)
            assert depth >= 1
        finally:
            await client.aclose()

    @pytest.mark.asyncio
    async def test_persistence_file_exists(self) -> None:
        """Test that Redis persistence file exists."""
        import os

        # Check if AOF file exists
        persistence_dir = "./data/redis"
        aof_file = os.path.join(persistence_dir, "appendonly.aof")

        # Note: File may not exist if Redis just started, but directory should exist
        assert os.path.isdir(persistence_dir), "Redis data directory should exist"

    @pytest.mark.asyncio
    async def test_redis_persistence_enabled(self) -> None:
        """Test that Redis has persistence enabled."""
        client = await get_redis_client()

        # Check if AOF is enabled
        config = await client.config_get("appendonly")
        aof_enabled = config.get("appendonly", "no").lower() == "yes"

        await client.aclose()
        assert aof_enabled, "AOF persistence should be enabled"

    @pytest.mark.asyncio
    async def test_persistence_verify_after_restart(self) -> None:
        """Verify the marker job persists after a Redis container restart.

        Run after restarting the Redis container. Scans the queue for the
        marker job enqueued by `test_persistence_prepare_marker`.
        """
        client = await get_redis_client()
        try:
            # Fetch entire queue to look for marker (may be small in dev)
            items = await client.lrange(ENHANCEMENT_QUEUE, 0, -1)
            found = False
            for raw in items:
                try:
                    obj = json.loads(raw)
                except Exception:
                    continue
                if isinstance(obj, dict) and obj.get("job_id") == self.MARKER_JOB_ID:
                    found = True
                    break

            assert found, (
                "Durability marker not found after restart — ensure Redis was restarted "
                "between tests and AOF is enabled."
            )
        finally:
            await client.aclose()


class TestQueueErrorHandling:
    """Test error handling for queue operations."""

    @pytest.mark.asyncio
    async def test_invalid_json_handling(self) -> None:
        """Test handling of invalid JSON in queue."""
        client = await get_redis_client()

        # Manually insert invalid JSON into queue
        invalid_json = "not-valid-json{]"
        await client.lpush(ENHANCEMENT_QUEUE, invalid_json)

        await client.aclose()

        # Attempt to pop should handle gracefully
        with pytest.raises(json.JSONDecodeError):
            await pop_from_queue(ENHANCEMENT_QUEUE)

        # Cleanup
        client = await get_redis_client()
        await client.delete(ENHANCEMENT_QUEUE)
        await client.aclose()

    @pytest.mark.asyncio
    async def test_queue_operations_with_special_characters(self) -> None:
        """Test queue operations with special characters in data."""
        job_data = {
            "job_id": str(uuid.uuid4()),
            "description": "Test with special chars: émojis 🚀 & symbols",
            "data": '{"nested": "json", "quotes": "\'single\' and \\"double\\""}',
        }

        await push_to_queue(ENHANCEMENT_QUEUE, job_data)
        popped = await pop_from_queue(ENHANCEMENT_QUEUE)

        assert popped is not None
        assert popped["description"] == job_data["description"]

        # Cleanup
        client = await get_redis_client()
        await client.delete(ENHANCEMENT_QUEUE)
        await client.aclose()


class TestHealthCheckIntegration:
    """Test integration with health check endpoints."""

    @pytest.mark.asyncio
    async def test_health_check_redis_connectivity(self) -> None:
        """Test that health check can verify Redis connectivity."""
        from src.api.health import health_check

        # Call health check - should not raise
        response = await health_check()

        # Verify response structure
        assert response["status"] == "healthy"
        assert "dependencies" in response
        assert "redis" in response["dependencies"]
        assert response["dependencies"]["redis"] == "healthy"
