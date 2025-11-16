"""
DEPRECATED: Fallback Chain Configuration API Endpoints.

Story 9.2 refactored provider management to use LiteLLM's API exclusively.
The fallback chain feature depends on the deprecated LLMModel table and is temporarily disabled.

All fallback chain endpoints are deprecated and return HTTP 410 Gone.

Migration Path:
  - Fallback chains will be reimplemented to use LiteLLM model names instead of database IDs
  - Use LiteLLM's built-in fallback/retry mechanisms in the meantime
  - See docs/stories/9-2-provider-management-api.md for migration guide
"""

from fastapi import APIRouter, HTTPException, Header, status, Depends
from src.config import get_settings
from src.utils.logger import logger

router = APIRouter(
    prefix="/api/fallback-chains",
    tags=["fallback-chains"],
    responses={404: {"description": "Not found"}},
)


async def _deprecated_endpoint(endpoint_path: str) -> None:
    """
    Return HTTP 410 Gone for deprecated fallback chain endpoints.

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
            "migration": "Use LiteLLM's built-in fallback mechanisms",
        },
    )
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail={
            "error": "Gone - This endpoint has been temporarily deprecated",
            "reason": "Story 9.2: Fallback chains depend on deprecated LLMModel table",
            "migration_guide": "See docs/stories/9-2-provider-management-api.md",
            "temporary_solution": "Use LiteLLM's built-in fallback/retry configuration",
            "future_plan": "Will be reimplemented to use LiteLLM model names instead of database IDs",
        },
    )


@router.post(
    "",
    summary="[DEPRECATED] Create fallback chain",
    description="DEPRECATED: Returns HTTP 410 Gone. Use LiteLLM fallback mechanisms.",
)
async def create_fallback_chain_deprecated():
    """DEPRECATED: Create fallback chain endpoint."""
    await _deprecated_endpoint("POST /api/fallback-chains")


@router.get(
    "",
    summary="[DEPRECATED] List fallback chains",
    description="DEPRECATED: Returns HTTP 410 Gone. Use LiteLLM fallback mechanisms.",
)
async def list_fallback_chains_deprecated():
    """DEPRECATED: List fallback chains endpoint."""
    await _deprecated_endpoint("GET /api/fallback-chains")


@router.get(
    "/{chain_id}",
    summary="[DEPRECATED] Get fallback chain details",
    description="DEPRECATED: Returns HTTP 410 Gone. Use LiteLLM fallback mechanisms.",
)
async def get_fallback_chain_deprecated(chain_id: int):
    """DEPRECATED: Get fallback chain endpoint."""
    await _deprecated_endpoint(f"GET /api/fallback-chains/{chain_id}")


@router.put(
    "/{chain_id}",
    summary="[DEPRECATED] Update fallback chain",
    description="DEPRECATED: Returns HTTP 410 Gone. Use LiteLLM fallback mechanisms.",
)
async def update_fallback_chain_deprecated(chain_id: int):
    """DEPRECATED: Update fallback chain endpoint."""
    await _deprecated_endpoint(f"PUT /api/fallback-chains/{chain_id}")


@router.delete(
    "/{chain_id}",
    summary="[DEPRECATED] Delete fallback chain",
    description="DEPRECATED: Returns HTTP 410 Gone. Use LiteLLM fallback mechanisms.",
)
async def delete_fallback_chain_deprecated(chain_id: int):
    """DEPRECATED: Delete fallback chain endpoint."""
    await _deprecated_endpoint(f"DELETE /api/fallback-chains/{chain_id}")


@router.post(
    "/{chain_id}/toggle",
    summary="[DEPRECATED] Toggle fallback chain",
    description="DEPRECATED: Returns HTTP 410 Gone. Use LiteLLM fallback mechanisms.",
)
async def toggle_fallback_chain_deprecated(chain_id: int):
    """DEPRECATED: Toggle fallback chain endpoint."""
    await _deprecated_endpoint(f"POST /api/fallback-chains/{chain_id}/toggle")


@router.get(
    "/model/{model_id}",
    summary="[DEPRECATED] Get fallback chains by model",
    description="DEPRECATED: Returns HTTP 410 Gone. Use LiteLLM fallback mechanisms.",
)
async def get_fallback_chains_by_model_deprecated(model_id: int):
    """DEPRECATED: Get fallback chains by model endpoint."""
    await _deprecated_endpoint(f"GET /api/fallback-chains/model/{model_id}")


@router.get(
    "/metrics",
    summary="[DEPRECATED] Get fallback metrics",
    description="DEPRECATED: Returns HTTP 410 Gone. Use LiteLLM fallback mechanisms.",
)
async def get_fallback_metrics_deprecated():
    """DEPRECATED: Get fallback metrics endpoint."""
    await _deprecated_endpoint("GET /api/fallback-chains/metrics")


@router.post(
    "/test",
    summary="[DEPRECATED] Test fallback chain",
    description="DEPRECATED: Returns HTTP 410 Gone. Use LiteLLM fallback mechanisms.",
)
async def test_fallback_chain_deprecated():
    """DEPRECATED: Test fallback chain endpoint."""
    await _deprecated_endpoint("POST /api/fallback-chains/test")
