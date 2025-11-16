"""
DEPRECATED: LLM Provider Management API Endpoints.

Story 9.2 refactored provider management to use LiteLLM's API exclusively.
All legacy database-based provider endpoints are deprecated and return HTTP 410 Gone.

Migration Path:
  - Use LiteLLM Admin UI (http://litellm:4000) to manage providers directly
  - Or call LiteLLM API endpoints (/model/new, /v1/model/info, /model/delete)
  - See docs/stories/9-2-provider-management-api.md for migration guide
"""

from fastapi import APIRouter, HTTPException, Header, status
from src.config import get_settings
from src.utils.logger import logger

router = APIRouter(prefix="/api/llm-providers", tags=["llm-providers"])


async def _deprecated_endpoint(endpoint_path: str) -> None:
    """
    Return HTTP 410 Gone for deprecated provider management endpoints.

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
            "migration": "Use LiteLLM API or Admin UI for provider management",
        },
    )
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail={
            "error": "Gone - This endpoint has been deprecated",
            "reason": "Story 9.2: Provider management refactored to use LiteLLM API exclusively",
            "migration_guide": "See docs/stories/9-2-provider-management-api.md",
            "litellm_endpoints": {
                "add_model": "POST /model/new (to LiteLLM proxy)",
                "list_models": "GET /v1/model/info (to LiteLLM proxy)",
                "delete_model": "POST /model/delete (to LiteLLM proxy)",
            },
        },
    )


@router.post(
    "",
    summary="[DEPRECATED] Create LLM provider",
    description="DEPRECATED: Use LiteLLM API instead. Returns HTTP 410 Gone.",
)
async def create_provider_deprecated():
    """DEPRECATED: Create provider endpoint. Use LiteLLM /model/new API instead."""
    await _deprecated_endpoint("POST /api/llm-providers")


@router.get(
    "",
    summary="[DEPRECATED] List LLM providers",
    description="DEPRECATED: Use LiteLLM API instead. Returns HTTP 410 Gone.",
)
async def list_providers_deprecated():
    """DEPRECATED: List providers endpoint. Use LiteLLM /v1/model/info API instead."""
    await _deprecated_endpoint("GET /api/llm-providers")


@router.get(
    "/{provider_id}",
    summary="[DEPRECATED] Get LLM provider details",
    description="DEPRECATED: Use LiteLLM API instead. Returns HTTP 410 Gone.",
)
async def get_provider_deprecated(provider_id: int):
    """DEPRECATED: Get provider endpoint. Use LiteLLM /v1/model/info API instead."""
    await _deprecated_endpoint(f"GET /api/llm-providers/{provider_id}")


@router.put(
    "/{provider_id}",
    summary="[DEPRECATED] Update LLM provider",
    description="DEPRECATED: Use LiteLLM API instead. Returns HTTP 410 Gone.",
)
async def update_provider_deprecated(provider_id: int):
    """DEPRECATED: Update provider endpoint. Modify models in LiteLLM directly."""
    await _deprecated_endpoint(f"PUT /api/llm-providers/{provider_id}")


@router.delete(
    "/{provider_id}",
    summary="[DEPRECATED] Delete LLM provider",
    description="DEPRECATED: Use LiteLLM API instead. Returns HTTP 410 Gone.",
)
async def delete_provider_deprecated(provider_id: int):
    """DEPRECATED: Delete provider endpoint. Use LiteLLM /model/delete API instead."""
    await _deprecated_endpoint(f"DELETE /api/llm-providers/{provider_id}")


@router.post(
    "/{provider_id}/test-connection",
    summary="[DEPRECATED] Test provider connection",
    description="DEPRECATED: Use LiteLLM API instead. Returns HTTP 410 Gone.",
)
async def test_connection_deprecated(provider_id: int):
    """DEPRECATED: Test connection endpoint. LiteLLM validates on add."""
    await _deprecated_endpoint(f"POST /api/llm-providers/{provider_id}/test-connection")


@router.get(
    "/{provider_id}/models",
    summary="[DEPRECATED] Get provider models",
    description="DEPRECATED: Use LiteLLM API instead. Returns HTTP 410 Gone.",
)
async def get_models_deprecated(provider_id: int):
    """DEPRECATED: Get models endpoint. Use LiteLLM /v1/model/info API instead."""
    await _deprecated_endpoint(f"GET /api/llm-providers/{provider_id}/models")


@router.post(
    "/{provider_id}/sync-models",
    summary="[DEPRECATED] Sync provider models",
    description="DEPRECATED: Use LiteLLM API instead. Returns HTTP 410 Gone.",
)
async def sync_models_deprecated(provider_id: int):
    """DEPRECATED: Sync models endpoint. Models are managed directly in LiteLLM."""
    await _deprecated_endpoint(f"POST /api/llm-providers/{provider_id}/sync-models")


