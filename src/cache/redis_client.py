"""
Redis client initialization and management.

This module provides Redis connection pooling and async client management
with proper error handling. Implements connection pooling per tech spec
with configurable pool size and connection timeout.
"""

from redis import asyncio as aioredis

from src.config import settings, get_settings
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
    # Get settings (initializing if necessary for tests)
    settings = get_settings()

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
    # Get settings (initializing if necessary for tests)
    settings = get_settings()

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


async def set_tenant_config(
    client: aioredis.Redis, tenant_id: str, config: dict, ttl: int = 300
) -> None:
    """
    Cache tenant configuration in Redis with TTL.

    Args:
        client: Redis async client
        tenant_id: Unique tenant identifier
        config: Configuration dict (will be JSON serialized)
        ttl: Time-to-live in seconds (default: 5 minutes)

    Raises:
        Exception: If Redis operation fails (caller should handle gracefully)
    """
    import json
    cache_key = f"tenant:config:{tenant_id}"
    await client.setex(cache_key, ttl, json.dumps(config))


async def get_tenant_config(
    client: aioredis.Redis, tenant_id: str
) -> dict | None:
    """
    Retrieve cached tenant configuration from Redis.

    Args:
        client: Redis async client
        tenant_id: Unique tenant identifier

    Returns:
        Configuration dict if found in cache, None if not found or expired

    Raises:
        Exception: If Redis operation fails (caller should handle gracefully)
    """
    import json
    cache_key = f"tenant:config:{tenant_id}"
    cached = await client.get(cache_key)
    if cached:
        return json.loads(cached)
    return None


async def invalidate_tenant_config(
    client: aioredis.Redis, tenant_id: str
) -> None:
    """
    Invalidate (delete) cached tenant configuration.

    Args:
        client: Redis async client
        tenant_id: Unique tenant identifier

    Raises:
        Exception: If Redis operation fails (caller should handle gracefully)
    """
    cache_key = f"tenant:config:{tenant_id}"
    await client.delete(cache_key)
