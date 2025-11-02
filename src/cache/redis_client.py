"""
Redis client initialization and management.

This module provides Redis connection pooling and async client management
with proper error handling. Implements connection pooling per tech spec
with configurable pool size and connection timeout.
"""

from redis import asyncio as aioredis

from src.config import settings
import asyncio

# Redis connection timeout in seconds (per tech spec NFR)
REDIS_CONNECTION_TIMEOUT = 5

_clients_by_loop: dict[int, aioredis.Redis] = {}

async def get_redis_client() -> aioredis.Redis:
    """
    Create and return a Redis async client instance with connection pooling.

    Configures connection pool with max connections and timeout as per
    technical specification. Uses automatic string decoding for convenience.

    Returns:
        aioredis.Redis: Async Redis client instance with pooling

    Raises:
        ConnectionError: If Redis is unavailable
        TimeoutError: If connection timeout is exceeded
    """
    # Create async Redis client with connection pooling
    client = aioredis.from_url(
        settings.redis_url,
        max_connections=settings.redis_max_connections,
        decode_responses=True,
        socket_connect_timeout=REDIS_CONNECTION_TIMEOUT,
        socket_keepalive=True,
    )
    return client


async def check_redis_connection() -> bool:
    """
    Check whether Redis is reachable and responding to PING.

    Returns:
        bool: True if Redis PING succeeds, False otherwise
    """
    try:
        client = await get_redis_client()
        try:
            pong = await client.ping()
            return bool(pong)
        finally:
            await client.aclose()
    except Exception:
        return False


def get_shared_redis() -> aioredis.Redis:
    """
    Return a shared Redis client instance for reuse on hot paths.

    Note: This client should not be closed by callers. Lifecycle can be
    managed by the application process (e.g., on shutdown hooks in future stories).
    """
    loop = asyncio.get_running_loop()
    key = id(loop)
    client = _clients_by_loop.get(key)
    if client is None:
        client = aioredis.from_url(
            settings.redis_url,
            max_connections=settings.redis_max_connections,
            decode_responses=True,
            socket_connect_timeout=REDIS_CONNECTION_TIMEOUT,
            socket_keepalive=True,
        )
        _clients_by_loop[key] = client
    return client
