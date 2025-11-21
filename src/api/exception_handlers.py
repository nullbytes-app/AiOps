"""
Custom exception handlers for FastAPI application.

This module provides structured error responses for:
- Pydantic validation errors (422)
- JWT authentication errors (401)
- General ValueError exceptions (400)
- Rate limit exceeded errors (429)

Story: 1C - API Endpoints & Middleware
Epic: 2 (Authentication & Authorization Foundation)
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from jose.exceptions import JWTError
from slowapi.errors import RateLimitExceeded


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Register custom exception handlers for the FastAPI application.

    This function adds handlers for:
    1. RequestValidationError (422) - Pydantic validation errors
    2. JWTError (401) - JWT token validation errors
    3. ValueError (400) - General value errors
    4. RateLimitExceeded (429) - Rate limit errors

    Args:
        app: FastAPI application instance

    Side Effects:
        Registers exception handlers on the FastAPI app

    Error Response Format:
        All errors return JSON with consistent structure:
        {
            "detail": "Error message",
            "body": {...}  # Only for validation errors
        }

    Security:
        - JWT errors use generic messages (prevent information disclosure)
        - 401 responses include WWW-Authenticate header (OAuth2 requirement)
        - 429 responses include Retry-After header
    """

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """
        Handle Pydantic validation errors with detailed messages.

        Args:
            request: FastAPI request
            exc: RequestValidationError exception

        Returns:
            JSONResponse with 422 status and error details

        Response:
            {
                "detail": [
                    {
                        "loc": ["body", "email"],
                        "msg": "value is not a valid email address",
                        "type": "value_error.email"
                    }
                ],
                "body": {"email": "invalid-email", "password": "..."}
            }
        """
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors(), "body": exc.body},
        )

    @app.exception_handler(JWTError)
    async def jwt_exception_handler(request: Request, exc: JWTError):
        """
        Handle JWT errors with generic message (security).

        Args:
            request: FastAPI request
            exc: JWTError exception

        Returns:
            JSONResponse with 401 status and WWW-Authenticate header

        Security:
            Generic error message prevents information disclosure
            (doesn't reveal if token expired vs invalid signature)

        Response:
            {
                "detail": "Could not validate credentials"
            }
        """
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Could not validate credentials"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """
        Handle ValueError as 400 Bad Request.

        Args:
            request: FastAPI request
            exc: ValueError exception

        Returns:
            JSONResponse with 400 status and error message

        Response:
            {
                "detail": "Password must be at least 12 characters long"
            }
        """
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)}
        )

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        """
        Handle rate limit exceeded with Retry-After header.

        Args:
            request: FastAPI request
            exc: RateLimitExceeded exception

        Returns:
            JSONResponse with 429 status and Retry-After header

        Response:
            {
                "detail": "Rate limit exceeded. Try again later."
            }

        Headers:
            Retry-After: 60  # Seconds until rate limit resets
        """
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded. Try again later."},
            headers={"Retry-After": "60"},
        )
