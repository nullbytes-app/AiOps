"""
Common error handling utilities for API endpoints.

Provides reusable error handling patterns to reduce boilerplate in FastAPI endpoints.
Includes HTTP exception mapping for domain exceptions and generic error handling.
"""

from functools import wraps
from typing import Callable, Any
from fastapi import HTTPException, status

from src.utils.logger import logger
from src.utils.exceptions import (
    ProviderNotFoundException,
    ModelNotFoundException,
)


def handle_provider_errors(operation_name: str) -> Callable:
    """
    Decorator for standardized provider-related error handling.

    Maps domain exceptions to appropriate HTTP status codes and logs errors.
    Reduces repetitive try-except blocks across provider endpoints.

    Args:
        operation_name: Human-readable operation description for logging (e.g., "create provider")

    Returns:
        Decorated async function with error handling

    Example:
        @handle_provider_errors("create provider")
        async def create_provider(...):
            # Implementation
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)

            except ProviderNotFoundException as e:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(e),
                )

            except ValueError as e:
                logger.error(f"{operation_name} validation failed: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=str(e),
                )

            except HTTPException:
                # Re-raise HTTPExceptions unchanged (already formatted)
                raise

            except Exception as e:
                logger.error(f"Failed to {operation_name}: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to {operation_name}: {str(e)}",
                )

        return wrapper

    return decorator


def handle_model_errors(operation_name: str) -> Callable:
    """
    Decorator for standardized model-related error handling.

    Maps domain exceptions to appropriate HTTP status codes and logs errors.
    Similar to handle_provider_errors but for model-specific operations.

    Args:
        operation_name: Human-readable operation description for logging (e.g., "update model")

    Returns:
        Decorated async function with error handling

    Example:
        @handle_model_errors("sync models")
        async def sync_models(...):
            # Implementation
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)

            except (ProviderNotFoundException, ModelNotFoundException) as e:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(e),
                )

            except ValueError as e:
                logger.error(f"{operation_name} validation failed: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=str(e),
                )

            except HTTPException:
                # Re-raise HTTPExceptions unchanged (already formatted)
                raise

            except Exception as e:
                logger.error(f"Failed to {operation_name}: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to {operation_name}: {str(e)}",
                )

        return wrapper

    return decorator
