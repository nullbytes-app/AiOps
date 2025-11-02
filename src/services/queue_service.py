"""
Redis queue operations service.

This module provides high-level queue operations for job processing.
Implements push, pop, peek, and depth checking operations using Redis
list data structures with JSON serialization. Includes both class-based
QueueService and function-based utilities for backwards compatibility.
"""

import json
import logging
import uuid
from typing import Any, Dict

from redis import asyncio as aioredis
from redis.exceptions import ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError

from src.cache.redis_client import get_shared_redis, get_redis_client
from src.schemas.job import EnhancementJob
from src.utils.exceptions import QueueServiceError
from src.utils.logger import logger as app_logger

logger = logging.getLogger(__name__)

# Queue naming convention: module:purpose
ENHANCEMENT_QUEUE = "enhancement:queue"
ENHANCEMENT_QUEUE_KEY = "enhancement:queue"  # Alias for consistency
BRPOP_TIMEOUT = 1  # Blocking pop timeout in seconds


class QueueService:
    """
    Service for managing Redis queue operations.

    Provides methods to push enhancement jobs to Redis queue using LPUSH command.
    Uses connection pooling for performance and implements comprehensive error
    handling for queue failures.

    Attributes:
        redis_client: Async Redis client instance with connection pooling

    Example:
        redis_client = await get_redis_client()
        queue_service = QueueService(redis_client)
        job_id = await queue_service.push_job(job_data)
    """

    def __init__(self, redis_client: aioredis.Redis):
        """
        Initialize QueueService with Redis client.

        Args:
            redis_client: Async Redis client instance with connection pooling.
                         Should be obtained via dependency injection.
        """
        self.redis_client = redis_client

    async def push_job(
        self, job_data: Dict[str, Any], tenant_id: str = "", ticket_id: str = ""
    ) -> str:
        """
        Push enhancement job to Redis queue for asynchronous processing.

        Serializes job data to JSON and pushes to `enhancement:queue` using LPUSH
        command. This implements FIFO queue where workers use BRPOP to consume jobs.
        Returns unique job ID for tracking.

        Args:
            job_data: Dictionary with EnhancementJob fields (job_id, ticket_id, etc.)
            tenant_id: Tenant identifier for error logging context (optional)
            ticket_id: Ticket identifier for error logging context (optional)

        Returns:
            str: UUID job_id that was queued

        Raises:
            QueueServiceError: If Redis push operation fails due to connection
                              errors, timeouts, or other Redis issues

        Example:
            job_data = {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "ticket_id": "TKT-001",
                "tenant_id": "tenant-abc",
                "description": "Server issue",
                "priority": "high",
                "timestamp": "2025-11-01T12:00:00Z"
            }
            job_id = await queue_service.push_job(job_data, "tenant-abc", "TKT-001")
        """
        try:
            # Create EnhancementJob instance for validation and serialization
            job = EnhancementJob(**job_data)

            # Serialize job to JSON for Redis storage
            job_json = job.model_dump_json()

            # Push job to Redis queue using LPUSH (producer side of FIFO queue)
            # LPUSH inserts at head, BRPOP removes from tail (FIFO order)
            queue_depth = await self.redis_client.lpush(
                ENHANCEMENT_QUEUE_KEY, job_json
            )

            app_logger.info(
                f"Job queued successfully: {job.job_id} "
                f"(queue depth: {queue_depth})",
                extra={
                    "job_id": job.job_id,
                    "ticket_id": job.ticket_id,
                    "tenant_id": job.tenant_id,
                    "queue_key": ENHANCEMENT_QUEUE_KEY,
                    "queue_depth": queue_depth,
                },
            )

            return job.job_id

        except (RedisConnectionError, RedisTimeoutError) as e:
            # Log error with context for debugging
            error_msg = (
                f"Redis queue push failed for tenant {tenant_id}, "
                f"ticket {ticket_id}: {type(e).__name__} - {str(e)}"
            )
            app_logger.error(
                error_msg,
                extra={
                    "tenant_id": tenant_id,
                    "ticket_id": ticket_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise QueueServiceError(error_msg) from e

        except Exception as e:
            # Catch unexpected errors and wrap in QueueServiceError
            error_msg = (
                f"Unexpected error queuing job for tenant {tenant_id}, "
                f"ticket {ticket_id}: {type(e).__name__} - {str(e)}"
            )
            # Use string concatenation to avoid f-string formatting issues
            app_logger.error(
                "Unexpected error queuing job for tenant %s, ticket %s: %s - %s",
                tenant_id,
                ticket_id,
                type(e).__name__,
                str(e),
                extra={
                    "tenant_id": tenant_id,
                    "ticket_id": ticket_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise QueueServiceError(error_msg) from e


async def get_queue_service() -> QueueService:
    """
    FastAPI dependency to provide QueueService instance.

    Creates and returns a QueueService with async Redis client.
    This function follows FastAPI dependency injection pattern.

    Returns:
        QueueService: Configured queue service instance

    Example:
        # In FastAPI endpoint
        @router.post("/webhook")
        async def webhook(queue: QueueService = Depends(get_queue_service)):
            job_id = await queue.push_job(job_data)
    """
    redis_client = await get_redis_client()
    return QueueService(redis_client)


async def push_to_queue(queue_name: str, data: dict) -> bool:
    """
    Push a job to the queue.

    Args:
        queue_name: Redis list key name (e.g., 'enhancement:queue')
        data: Job data to enqueue (will be JSON serialized)

    Returns:
        bool: True if successful, False if failed

    Raises:
        ConnectionError: If Redis connection fails
        TimeoutError: If operation times out
    """
    try:
        client = get_shared_redis()
        # Serialize data to JSON string
        job_json = json.dumps(data)
        # LPUSH adds to the left side of the list (enqueue)
        result = await client.lpush(queue_name, job_json)
        logger.debug(f"Pushed job to queue '{queue_name}': {result} items in queue")
        return result > 0
    except RedisTimeoutError as e:
        logger.error("Queue push timeout", extra={"queue": queue_name, "error": str(e)})
        raise
    except RedisConnectionError as e:
        logger.error("Queue push connection error", extra={"queue": queue_name, "error": str(e)})
        raise
    except Exception as e:
        logger.error("Queue push failed", extra={"queue": queue_name, "error": str(e)})
        raise


async def pop_from_queue(queue_name: str) -> dict[str, Any] | None:
    """
    Pop a job from the queue (blocking).

    Uses BRPOP (blocking right pop) to fetch jobs from the right side
    of the list with a 1-second timeout.

    Args:
        queue_name: Redis list key name

    Returns:
        dict: Deserialized job data, or None if queue is empty or timeout

    Raises:
        ConnectionError: If Redis connection fails
        json.JSONDecodeError: If stored data is not valid JSON
    """
    try:
        client = get_shared_redis()
        # BRPOP waits up to timeout seconds for an item on the right
        result = await client.brpop(queue_name, timeout=BRPOP_TIMEOUT)

        if result is None:
            logger.debug(f"Queue '{queue_name}' is empty or timeout reached")
            return None

        # result is a tuple: (key, value)
        _, job_json = result
        job_data = json.loads(job_json)
        logger.debug(f"Popped job from queue '{queue_name}'")
        return job_data
    except RedisTimeoutError as e:
        logger.error("Queue pop timeout", extra={"queue": queue_name, "error": str(e)})
        raise
    except RedisConnectionError as e:
        logger.error("Queue pop connection error", extra={"queue": queue_name, "error": str(e)})
        raise
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in queue", extra={"queue": queue_name, "error": str(e)})
        raise
    except Exception as e:
        logger.error("Queue pop failed", extra={"queue": queue_name, "error": str(e)})
        raise


async def peek_queue(queue_name: str, count: int = 10) -> list[dict[str, Any]]:
    """
    Peek at jobs in the queue without removing them.

    Returns the next `count` jobs that would be processed in FIFO order
    (shows what would be dequeued by BRPOP next).

    Args:
        queue_name: Redis list key name
        count: Number of jobs to peek at (default: 10)

    Returns:
        list: List of deserialized job data dictionaries in FIFO order
              (first item is next to be dequeued)

    Raises:
        ConnectionError: If Redis connection fails
        json.JSONDecodeError: If stored data is not valid JSON
    """
    try:
        client = get_shared_redis()
        # LPUSH adds to left, BRPOP takes from right
        # To peek at what would be popped next, get rightmost items and reverse
        # LRANGE -count -1 returns the rightmost `count` items from left to right
        # We reverse them to show in the order they'll be processed (right-to-left)
        job_jsons = await client.lrange(queue_name, -count, -1)

        jobs = []
        for job_json in reversed(job_jsons):
            try:
                job_data = json.loads(job_json)
                jobs.append(job_data)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in queue '{queue_name}': {str(e)}")
                # Continue processing other items
                continue

        logger.debug(f"Peeked {len(jobs)} jobs from queue '{queue_name}'")
        return jobs
    except RedisTimeoutError as e:
        logger.error("Queue peek timeout", extra={"queue": queue_name, "error": str(e)})
        raise
    except RedisConnectionError as e:
        logger.error("Queue peek connection error", extra={"queue": queue_name, "error": str(e)})
        raise
    except Exception as e:
        logger.error("Queue peek failed", extra={"queue": queue_name, "error": str(e)})
        raise


async def get_queue_depth(queue_name: str) -> int:
    """
    Get the number of jobs currently in the queue.

    Args:
        queue_name: Redis list key name

    Returns:
        int: Number of jobs in the queue (0 if queue doesn't exist)

    Raises:
        ConnectionError: If Redis connection fails
    """
    try:
        client = get_shared_redis()
        # LLEN returns the length of the list
        depth = await client.llen(queue_name)
        logger.debug(f"Queue '{queue_name}' depth: {depth}")
        return depth
    except RedisTimeoutError as e:
        logger.error("Queue depth timeout", extra={"queue": queue_name, "error": str(e)})
        raise
    except RedisConnectionError as e:
        logger.error("Queue depth connection error", extra={"queue": queue_name, "error": str(e)})
        raise
    except Exception as e:
        logger.error("Queue depth failed", extra={"queue": queue_name, "error": str(e)})
        raise
