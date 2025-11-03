"""
Rate limiting service using Redis sliding window algorithm.

Implements per-tenant, per-endpoint rate limiting to prevent abuse.
Uses Redis sorted sets for efficient sliding window tracking.
"""

import time
from typing import Optional
from redis.asyncio import Redis
from src.utils.logger import logger


class RateLimiter:
    """Redis-based sliding window rate limiter."""

    def __init__(self, redis_client: Redis):
        """
        Initialize rate limiter with Redis client.

        Args:
            redis_client: Async Redis client
        """
        self.redis = redis_client

    async def check_rate_limit(
        self,
        tenant_id: str,
        endpoint: str,
        limit: int = 100,
        window: int = 60,
    ) -> tuple[bool, Optional[int]]:
        """
        Check if request is within rate limit (sliding window).

        Algorithm:
        1. Remove expired entries from sorted set (older than window)
        2. Count current requests in window
        3. Add current request if under limit
        4. Return status and seconds until reset

        Args:
            tenant_id: Tenant identifier
            endpoint: Endpoint name (e.g., "ticket_created")
            limit: Maximum requests per window (default 100)
            window: Window size in seconds (default 60)

        Returns:
            Tuple of (allowed: bool, retry_after_seconds: Optional[int])
            - allowed=True means request is within limit
            - allowed=False, retry_after=N means retry after N seconds
        """
        key = f"webhook_rate_limit:{tenant_id}:{endpoint}"
        now = time.time()
        window_start = now - window

        try:
            # Remove expired entries (older than window)
            await self.redis.zremrangebyscore(key, 0, window_start)

            # Count current requests in window
            current_count = await self.redis.zcard(key)

            if current_count < limit:
                # Add current request to sorted set
                # Use request ID as value, current time as score
                request_id = f"{now}_{tenant_id}"
                await self.redis.zadd(key, {request_id: now})

                # Set expiration (window + buffer)
                await self.redis.expire(key, window + 60)

                logger.info(
                    f"Rate limit check: {tenant_id}/{endpoint} - {current_count}/{limit} "
                    f"requests in window",
                    extra={"tenant_id": tenant_id, "endpoint": endpoint},
                )
                return True, None
            else:
                # Rate limit exceeded - calculate retry_after
                # Get oldest entry in window
                oldest = await self.redis.zrange(key, 0, 0, withscores=True)
                if oldest:
                    oldest_time = oldest[0][1]
                    retry_after = int(window - (now - oldest_time)) + 1
                else:
                    retry_after = window

                logger.warning(
                    f"Rate limit exceeded: {tenant_id}/{endpoint} - {current_count} > {limit}",
                    extra={
                        "tenant_id": tenant_id,
                        "endpoint": endpoint,
                        "current_count": current_count,
                        "limit": limit,
                        "retry_after": retry_after,
                    },
                )
                return False, retry_after

        except Exception as e:
            logger.error(
                f"Rate limit check failed for {tenant_id}/{endpoint}: {str(e)}",
                extra={
                    "tenant_id": tenant_id,
                    "endpoint": endpoint,
                    "error": str(e),
                },
            )
            # Fail open: allow request on error
            return True, None

    async def reset_limit(self, tenant_id: str, endpoint: str) -> None:
        """
        Reset rate limit counter for a tenant/endpoint.

        Args:
            tenant_id: Tenant identifier
            endpoint: Endpoint name
        """
        key = f"webhook_rate_limit:{tenant_id}:{endpoint}"
        try:
            await self.redis.delete(key)
            logger.info(
                f"Reset rate limit for {tenant_id}/{endpoint}",
                extra={"tenant_id": tenant_id, "endpoint": endpoint},
            )
        except Exception as e:
            logger.warning(
                f"Failed to reset rate limit for {tenant_id}/{endpoint}: {str(e)}"
            )
