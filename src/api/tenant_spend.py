"""API endpoints for tenant spend tracking and budget dashboards.

Provides real-time access to tenant spending data from LiteLLM virtual keys,
enabling dashboard visibility into LLM costs and budget utilization.

Routes:
    GET /api/tenants/{tenant_id}/spend - Get real-time spend data for tenant
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_async_session
from src.services.budget_service import BudgetService
from src.schemas.tenant_spend import TenantSpendResponse
from loguru import logger


router = APIRouter(
    prefix="/api/tenants",
    tags=["tenant-spend"],
    responses={
        404: {"description": "Tenant not found"},
        503: {"description": "LiteLLM service unavailable"},
    },
)


@router.get(
    "/{tenant_id}/spend",
    response_model=TenantSpendResponse,
    summary="Get tenant spend data",
    description="Retrieve real-time spend data for a tenant from LiteLLM virtual key. "
    "Includes budget utilization percentage and per-model spend breakdown. "
    "Used by admin dashboard to display cost visibility.",
    responses={
        200: {"description": "Real-time spend data retrieved successfully"},
        404: {"description": "Tenant not found or has no virtual key configured"},
        503: {"description": "LiteLLM proxy service unavailable"},
        500: {"description": "Internal server error"},
    },
)
async def get_tenant_spend(
    tenant_id: str,
    db: AsyncSession = Depends(get_async_session),
) -> TenantSpendResponse:
    """
    Get real-time spend data for a tenant from LiteLLM.

    Queries the LiteLLM proxy /key/info endpoint for current spend, max budget,
    and per-model breakdown. Used by tenant dashboard to display budget status.

    Args:
        tenant_id: Tenant identifier
        db: Database session (dependency injection)

    Returns:
        TenantSpendResponse: Current spend, budget, and model breakdown

    Raises:
        HTTPException(404): If tenant not found or no virtual key configured
        HTTPException(503): If LiteLLM service unavailable
        HTTPException(500): For other internal errors

    Example:
        ```
        GET /api/tenants/acme-corp/spend
        Authorization: Bearer <token>

        Response (200):
        {
            "tenant_id": "acme-corp",
            "current_spend": 45.67,
            "max_budget": 500.00,
            "utilization_pct": 9.13,
            "models_breakdown": [
                {"model": "gpt-4", "spend": 30.50, "percentage": 66.7, "requests": 125},
                {"model": "claude-3-opus", "spend": 15.17, "percentage": 33.3, "requests": 45}
            ],
            "last_updated": "2025-11-07T12:30:45.123456Z",
            "budget_duration": "30d",
            "budget_reset_at": "2025-12-07T00:00:00Z"
        }
        ```
    """
    try:
        budget_service = BudgetService(db)
        spend_data = await budget_service.get_tenant_spend_from_litellm(tenant_id)

        # Convert TenantSpend dataclass to response model
        return TenantSpendResponse(
            tenant_id=spend_data.tenant_id,
            current_spend=spend_data.current_spend,
            max_budget=spend_data.max_budget,
            utilization_pct=spend_data.utilization_pct,
            models_breakdown=[
                {
                    "model": m.model,
                    "spend": m.spend,
                    "percentage": m.percentage,
                    "requests": m.requests,
                }
                for m in spend_data.models_breakdown
            ],
            last_updated=spend_data.last_updated,
            budget_duration=spend_data.budget_duration,
            budget_reset_at=spend_data.budget_reset_at,
        )

    except ValueError as e:
        # Tenant not found or no virtual key
        logger.warning(f"Spend query failed for tenant {tenant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except ConnectionError as e:
        # LiteLLM service unavailable
        logger.error(f"LiteLLM connection error for tenant {tenant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LiteLLM proxy service unavailable. Please try again later.",
        )

    except Exception as e:
        # Other errors
        logger.error(f"Error fetching spend data for tenant {tenant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while fetching spend data",
        )
