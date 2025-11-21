"""
Rate limiting middleware using slowapi.

This module provides rate limiting for API endpoints to prevent abuse:
- Default: 1000 requests/hour per IP
- /api/auth/token: 100 requests/minute per IP (login protection)
- /api/auth/register: 10 requests/minute per IP (spam prevention)

Story: 1C - API Endpoints & Middleware
Epic: 2 (Authentication & Authorization Foundation)
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI, Request


# Create limiter instance with IP-based rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/hour"],  # Default for all routes
)


def setup_rate_limiting(app: FastAPI) -> None:
    """
    Configure rate limiting middleware for FastAPI application.

    This function:
    1. Adds limiter to app state
    2. Registers rate limit exceeded exception handler

    Args:
        app: FastAPI application instance

    Side Effects:
        - Sets app.state.limiter
        - Registers exception handler for RateLimitExceeded

    Usage:
        # In auth.py:
        @router.post("/token")
        @limiter.limit("100/minute")
        async def login(...):
            pass

        @router.post("/register")
        @limiter.limit("10/minute")
        async def register(...):
            pass

    Rate Limits:
        - Default: 1000 requests/hour per IP
        - Login (/token): 100 requests/minute per IP
        - Registration (/register): 10 requests/minute per IP

    Response on Rate Limit:
        - Status: 429 Too Many Requests
        - Headers: Retry-After (seconds until rate limit resets)
        - Body: {"detail": "Rate limit exceeded"}
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
