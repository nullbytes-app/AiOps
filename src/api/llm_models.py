"""
LLM Model Management API Endpoints.

Story 9.2 refactored provider management to use LiteLLM's API exclusively.
Database-based model CRUD endpoints are deprecated and return HTTP 410 Gone.

Active Endpoints:
- GET /api/llm-models/available: Get available models from LiteLLM (public, no auth)

Deprecated Endpoints (return HTTP 410 Gone):
- POST /api/llm-models: Create model (use LiteLLM Admin UI instead)
- GET /api/llm-models/{model_id}: Get model details
- PUT /api/llm-models/{model_id}: Update model
- DELETE /api/llm-models/{model_id}: Delete model
- POST /api/llm-models/{model_id}/toggle: Toggle model status
- POST /api/llm-models/bulk-enable: Bulk enable models
- POST /api/llm-models/bulk-disable: Bulk disable models

Migration Path:
  - Use LiteLLM Admin UI (http://litellm:4000) to manage models directly
  - Or call LiteLLM API endpoints (/model/new, /v1/model/info, /model/delete)
  - See docs/stories/9-2-provider-management-api.md for migration guide
"""

from fastapi import APIRouter, HTTPException, Header, status, Query, Depends
from typing import List

from src.schemas.llm_models import ModelInfo
from src.services.llm_model_discovery import ModelDiscoveryService
from src.config import get_settings
from src.utils.logger import logger

router = APIRouter(prefix="/api/llm-models", tags=["llm-models"])


@router.get(
    "/available",
    response_model=List[ModelInfo],
    status_code=status.HTTP_200_OK,
    summary="Get available models from LiteLLM",
    description="Returns list of currently available LLM models from the LiteLLM proxy. "
    "Results are cached for 5 minutes. No authentication required (public endpoint).",
)
async def get_available_models(
    force_refresh: bool = Query(
        False,
        description="Skip cache and fetch fresh from LiteLLM",
    ),
) -> List[ModelInfo]:
    """
    Get list of available models from LiteLLM proxy.

    Queries the LiteLLM /v1/model/info endpoint and returns all available models
    with metadata (id, name, provider, max_tokens, supports_function_calling).
    Results are cached for 5 minutes to improve performance. Falls back to sensible
    defaults if LiteLLM is unavailable.

    This is a public endpoint (no authentication required) used by UI dropdowns
    and other components to show available models to users.

    Args:
        force_refresh: If true, bypass cache and fetch fresh from LiteLLM (default: false)

    Returns:
        List[ModelInfo]: List of available models with full metadata

    Raises:
        HTTPException(503): If LiteLLM is unavailable and no cached data exists
            (though graceful fallback is used, so this is rare)

    Example:
        ```python
        # Get cached models (if available within 5-minute window)
        response = await httpx.get("http://api:8000/api/llm-models/available")
        models = response.json()

        # Force refresh from LiteLLM
        response = await httpx.get(
            "http://api:8000/api/llm-models/available",
            params={"force_refresh": True}
        )
        models = response.json()
        ```
    """
    try:
        service = ModelDiscoveryService()
        models = await service.get_available_models(force_refresh=force_refresh)

        logger.info(
            "Available models retrieved",
            extra={
                "count": len(models),
                "force_refresh": force_refresh,
            },
        )

        return models

    except Exception as e:
        logger.error(f"Failed to fetch available models: {str(e)}")
        # Return graceful fallback (service handles this internally)
        service = ModelDiscoveryService()
        fallback_models = await service.get_available_models(force_refresh=False)
        return fallback_models


async def _deprecated_endpoint(endpoint_path: str) -> None:
    """
    Return HTTP 410 Gone for deprecated model management endpoints.

    Args:
        endpoint_path: The requested endpoint path for logging

    Raises:
        HTTPException(410): Always - this endpoint is deprecated
    """
    logger.warning(
        "Deprecated endpoint accessed",
        extra={
            "endpoint": endpoint_path,
            "status_code": 410,
            "migration": "Use LiteLLM API or Admin UI for model management",
        },
    )
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail={
            "error": "Gone - This endpoint has been deprecated",
            "reason": "Story 9.2: Model management refactored to use LiteLLM API exclusively",
            "migration_guide": "See docs/stories/9-2-provider-management-api.md",
            "litellm_endpoints": {
                "add_model": "POST /model/new (to LiteLLM proxy)",
                "list_models": "GET /v1/model/info (to LiteLLM proxy)",
                "delete_model": "POST /model/delete (to LiteLLM proxy)",
            },
            "active_endpoint": "/api/llm-models/available (get available models)",
        },
    )


@router.post(
    "",
    summary="[DEPRECATED] Create new LLM model",
    description="DEPRECATED: Use LiteLLM API instead. Returns HTTP 410 Gone.",
)
async def create_model_deprecated():
    """DEPRECATED: Create model endpoint. Use LiteLLM /model/new API instead."""
    await _deprecated_endpoint("POST /api/llm-models")


@router.get(
    "/{model_id}",
    summary="[DEPRECATED] Get LLM model details",
    description="DEPRECATED: Use LiteLLM API instead. Returns HTTP 410 Gone.",
)
async def get_model_deprecated(model_id: int):
    """DEPRECATED: Get model endpoint. Use LiteLLM /v1/model/info API instead."""
    await _deprecated_endpoint(f"GET /api/llm-models/{model_id}")


@router.put(
    "/{model_id}",
    summary="[DEPRECATED] Update LLM model configuration",
    description="DEPRECATED: Use LiteLLM API instead. Returns HTTP 410 Gone.",
)
async def update_model_deprecated(model_id: int):
    """DEPRECATED: Update model endpoint. Modify models in LiteLLM directly."""
    await _deprecated_endpoint(f"PUT /api/llm-models/{model_id}")


@router.delete(
    "/{model_id}",
    summary="[DEPRECATED] Delete LLM model",
    description="DEPRECATED: Use LiteLLM API instead. Returns HTTP 410 Gone.",
)
async def delete_model_deprecated(model_id: int):
    """DEPRECATED: Delete model endpoint. Use LiteLLM /model/delete API instead."""
    await _deprecated_endpoint(f"DELETE /api/llm-models/{model_id}")


@router.post(
    "/{model_id}/toggle",
    summary="[DEPRECATED] Toggle LLM model enabled status",
    description="DEPRECATED: Use LiteLLM API instead. Returns HTTP 410 Gone.",
)
async def toggle_model_deprecated(model_id: int):
    """DEPRECATED: Toggle model endpoint. Manage status in LiteLLM directly."""
    await _deprecated_endpoint(f"POST /api/llm-models/{model_id}/toggle")


@router.post(
    "/bulk-enable",
    summary="[DEPRECATED] Bulk enable LLM models",
    description="DEPRECATED: Use LiteLLM API instead. Returns HTTP 410 Gone.",
)
async def bulk_enable_models_deprecated():
    """DEPRECATED: Bulk enable endpoint. Manage models in LiteLLM directly."""
    await _deprecated_endpoint("POST /api/llm-models/bulk-enable")


@router.post(
    "/bulk-disable",
    summary="[DEPRECATED] Bulk disable LLM models",
    description="DEPRECATED: Use LiteLLM API instead. Returns HTTP 410 Gone.",
)
async def bulk_disable_models_deprecated():
    """DEPRECATED: Bulk disable endpoint. Manage models in LiteLLM directly."""
    await _deprecated_endpoint("POST /api/llm-models/bulk-disable")
