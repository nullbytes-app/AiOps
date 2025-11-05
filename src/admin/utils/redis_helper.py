"""
Redis Helper for Streamlit Dashboard.

This module provides synchronous Redis operations for the Streamlit admin UI.
Unlike src/cache/redis_client.py (async), this uses sync redis.Redis for
compatibility with Streamlit's execution model.

Key Features:
- Synchronous Redis connection (redis.Redis, not aioredis)
- Connection health testing with timeout
- Queue depth queries for Celery queue
- Cached operations for dashboard performance
"""

import os
import time
from typing import Optional

import redis
import streamlit as st
from loguru import logger


@st.cache_resource
def get_sync_redis_client() -> Optional[redis.Redis]:
    """
    Create synchronous Redis client with connection pooling.

    Uses @st.cache_resource to persist client across Streamlit reruns.
    AC#4 requirement for Redis connection status.

    Returns:
        redis.Redis: Synchronous Redis client, or None if connection fails

    Environment Variables:
        AI_AGENTS_REDIS_URL: Redis connection string
            Format: redis://host:port/db
            Example: redis://localhost:6379/1 (Celery queue on db 1)
    """
    try:
        redis_url = os.getenv("AI_AGENTS_REDIS_URL", "redis://localhost:6379/1")

        # Create synchronous Redis client
        client = redis.Redis.from_url(
            redis_url,
            decode_responses=True,  # Return strings instead of bytes
            socket_connect_timeout=2,  # 2-second timeout for connection
            socket_timeout=2,  # 2-second timeout for operations
            retry_on_timeout=True,
            health_check_interval=30,  # Verify connection every 30s
        )

        # Test connection
        client.ping()

        logger.info("Redis connection established successfully")
        return client

    except Exception as e:
        logger.error(f"Failed to create Redis client: {e}")
        return None


def test_redis_connection() -> tuple[bool, str]:
    """
    Test Redis connectivity and measure response time.

    Used on dashboard to display connection status (AC#4 requirement).

    Returns:
        tuple[bool, str]: (success, message)
            success: True if connection works, False otherwise
            message: User-friendly status with response time

    Examples:
        >>> test_redis_connection()
        (True, "✅ Connected (12ms)")

        >>> test_redis_connection()
        (False, "❌ Connection timeout after 2s")
    """
    try:
        client = get_sync_redis_client()

        if client is None:
            return False, "❌ Redis client creation failed. Check configuration."

        # Measure ping response time
        start_time = time.time()
        result = client.ping()
        elapsed_ms = int((time.time() - start_time) * 1000)

        if result:
            return True, f"✅ Connected ({elapsed_ms}ms)"
        else:
            return False, "❌ Ping returned False (unexpected)"

    except redis.ConnectionError as e:
        logger.error(f"Redis connection error: {e}")
        return False, f"❌ Connection failed: {str(e)[:50]}"

    except redis.TimeoutError:
        logger.error("Redis connection timeout")
        return False, "❌ Connection timeout after 2s"

    except Exception as e:
        logger.error(f"Redis connection test failed: {e}")
        return False, f"❌ Error: {str(e)[:50]}"


@st.cache_data(ttl=30)
def get_redis_queue_depth(queue_name: str = "celery") -> int:
    """
    Get current depth of Redis queue.

    Uses Redis llen() command to count items in list (AC#2 requirement).

    Args:
        queue_name: Redis list key name (default: "celery" for Celery queue)

    Returns:
        int: Number of jobs in queue, or 0 if query fails

    Examples:
        >>> get_redis_queue_depth()
        42

        >>> get_redis_queue_depth("custom_queue")
        7
    """
    try:
        client = get_sync_redis_client()

        if client is None:
            logger.warning("Redis client unavailable, returning queue depth 0")
            return 0

        # Use llen() to get list length
        depth = client.llen(queue_name)

        return int(depth) if depth is not None else 0

    except Exception as e:
        logger.error(f"Failed to get queue depth for '{queue_name}': {e}")
        return 0


@st.cache_data(ttl=60)
def get_redis_info() -> dict:
    """
    Get Redis server information for diagnostics.

    Queries Redis INFO command for memory, clients, and stats.

    Returns:
        dict: Redis info fields, or empty dict if unavailable

    Examples:
        >>> info = get_redis_info()
        >>> info["used_memory_human"]
        "2.50M"
    """
    try:
        client = get_sync_redis_client()

        if client is None:
            return {}

        # Get Redis server info
        info = client.info()

        # Extract useful fields for dashboard
        return {
            "redis_version": info.get("redis_version", "Unknown"),
            "used_memory_human": info.get("used_memory_human", "Unknown"),
            "connected_clients": info.get("connected_clients", 0),
            "total_commands_processed": info.get("total_commands_processed", 0),
            "uptime_in_days": info.get("uptime_in_days", 0),
        }

    except Exception as e:
        logger.error(f"Failed to get Redis info: {e}")
        return {}


def clear_redis_cache() -> tuple[bool, str]:
    """
    Clear all cached data in Redis (admin operation).

    WARNING: This clears the entire Redis database. Use with caution.

    Returns:
        tuple[bool, str]: (success, message)

    Examples:
        >>> clear_redis_cache()
        (True, "✅ Redis cache cleared (1,234 keys deleted)")
    """
    try:
        client = get_sync_redis_client()

        if client is None:
            return False, "❌ Redis client unavailable"

        # Count keys before flush
        key_count = client.dbsize()

        # Flush current database only (not all databases)
        client.flushdb()

        return True, f"✅ Redis cache cleared ({key_count:,} keys deleted)"

    except Exception as e:
        logger.error(f"Failed to clear Redis cache: {e}")
        return False, f"❌ Error: {str(e)}"
