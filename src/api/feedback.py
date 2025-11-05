"""
Enhancement feedback API endpoints (Story 5.5 - AC5).

REST API for technicians to submit feedback (thumbs up/down, 1-5 ratings) on
ticket enhancements, and for retrieving/analyzing feedback data for continuous
quality monitoring and roadmap prioritization.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_tenant_db, get_tenant_id
from src.database.models import EnhancementFeedback
from src.schemas.feedback import (
    FeedbackSubmitRequest,
    FeedbackResponse,
    FeedbackListResponse,
    FeedbackRecord,
    FeedbackType,
)
from src.services.feedback_service import FeedbackService
from src.utils.logger import logger

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Submit enhancement feedback",
    description="Allows technicians to rate enhancement quality with thumbs up/down or 1-5 scale. "
    "Supports anonymous feedback (no email required) or attributed feedback with optional comments. "
    "Used for continuous quality monitoring, satisfaction tracking (AC2: >4/5 target), and "
    "data-driven roadmap prioritization. RLS ensures tenant isolation.",
    response_model=FeedbackResponse,
)
async def submit_feedback(
    feedback_request: FeedbackSubmitRequest,
    db: AsyncSession = Depends(get_tenant_db),
) -> FeedbackResponse:
    """
    Submit enhancement feedback from technician.

    Accepts thumbs up/down for quick binary feedback or 1-5 rating with optional
    comment for detailed feedback. Validates that rating_value is provided when
    feedback_type='rating' (Pydantic validation). Stores feedback in enhancement_feedback
    table with RLS enforcement ensuring tenant isolation.

    Args:
        feedback_request: Validated feedback submission (tenant_id, ticket_id, feedback_type, etc.)
        db: RLS-aware async database session (tenant context set via middleware)

    Returns:
        FeedbackResponse: Confirmation with created feedback record UUID

    Raises:
        HTTPException(422): If validation fails (e.g., rating_value missing for rating type)
        HTTPException(500): If database error occurs during storage

    Example:
        Request body (thumbs up):
        {
            "tenant_id": "tenant-abc",
            "ticket_id": "TKT-001",
            "feedback_type": "thumbs_up"
        }

        Request body (detailed rating):
        {
            "tenant_id": "tenant-abc",
            "ticket_id": "TKT-002",
            "enhancement_id": "550e8400-e29b-41d4-a716-446655440000",
            "technician_email": "tech@example.com",
            "feedback_type": "rating",
            "rating_value": 5,
            "feedback_comment": "Excellent context! Resolved ticket 10 min faster."
        }

        Response (201 Created):
        {
            "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
            "status": "created",
            "message": "Feedback submitted successfully"
        }
    """
    try:
        # Create feedback service and store record
        service = FeedbackService(db)
        feedback = await service.create_feedback(feedback_request)

        logger.info(
            f"Feedback submitted successfully: id={feedback.id}, "
            f"tenant={feedback.tenant_id}, ticket={feedback.ticket_id}, "
            f"type={feedback.feedback_type}"
        )

        return FeedbackResponse(
            id=feedback.id,
            status="created",
            message="Feedback submitted successfully",
        )

    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}",
        )


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Retrieve feedback records",
    description="Retrieves enhancement feedback with optional filters: date range, feedback type, pagination. "
    "Used for analyzing satisfaction trends, generating baseline metrics reports, and identifying "
    "improvement themes. RLS ensures tenant isolation (only returns feedback for authenticated tenant). "
    "Supports pagination via limit/offset for large datasets.",
    response_model=FeedbackListResponse,
)
async def get_feedback(
    tenant_id: str = Query(..., description="Tenant identifier (must match RLS context)"),
    start_date: Optional[datetime] = Query(None, description="Filter by created_at >= start_date (ISO8601 format)"),
    end_date: Optional[datetime] = Query(None, description="Filter by created_at <= end_date (ISO8601 format)"),
    feedback_type: Optional[FeedbackType] = Query(None, description="Filter by feedback type (thumbs_up, thumbs_down, rating)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return (default 100, max 1000)"),
    offset: int = Query(0, ge=0, description="Pagination offset (default 0)"),
    db: AsyncSession = Depends(get_tenant_db),
) -> FeedbackListResponse:
    """
    Retrieve feedback records with optional filters.

    Queries enhancement_feedback table with RLS enforcement ensuring only tenant's
    own feedback is visible. Supports filtering by date range (for 7-day baseline
    period), feedback type (for sentiment analysis), and pagination for large result sets.

    Args:
        tenant_id: Tenant identifier (validated against RLS context)
        start_date: Optional start date filter (created_at >= start_date)
        end_date: Optional end date filter (created_at <= end_date)
        feedback_type: Optional filter by feedback type (thumbs_up, thumbs_down, rating)
        limit: Maximum records to return (default 100, max 1000)
        offset: Pagination offset for large datasets
        db: RLS-aware async database session

    Returns:
        FeedbackListResponse: List of feedback records and total count

    Raises:
        HTTPException(403): If tenant_id doesn't match RLS context (unauthorized access)
        HTTPException(500): If database error occurs during retrieval

    Example:
        Query parameters:
        ?tenant_id=tenant-abc&start_date=2025-11-01T00:00:00Z&end_date=2025-11-07T23:59:59Z&feedback_type=rating

        Response (200 OK):
        {
            "feedback": [
                {
                    "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                    "tenant_id": "tenant-abc",
                    "ticket_id": "TKT-001",
                    "feedback_type": "rating",
                    "rating_value": 5,
                    "created_at": "2025-11-04T10:30:00Z"
                }
            ],
            "count": 1
        }
    """
    try:
        # Create feedback service and retrieve records
        service = FeedbackService(db)
        feedback_list = await service.get_feedback(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            feedback_type=feedback_type,
            limit=limit,
            offset=offset,
        )

        # Convert to response schema
        feedback_records = [FeedbackRecord.model_validate(f) for f in feedback_list]

        logger.info(
            f"Retrieved {len(feedback_records)} feedback records: tenant={tenant_id}, "
            f"filters=(start={start_date}, end={end_date}, type={feedback_type})"
        )

        return FeedbackListResponse(
            feedback=feedback_records,
            count=len(feedback_records),
        )

    except Exception as e:
        logger.error(f"Error retrieving feedback: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve feedback: {str(e)}",
        )


@router.get(
    "/stats",
    status_code=status.HTTP_200_OK,
    summary="Get feedback statistics",
    description="Returns aggregated feedback statistics: average rating (for AC2 target tracking: >4/5), "
    "feedback counts by type (for sentiment analysis), and positive feedback percentage. "
    "Used for baseline metrics reporting, weekly review dashboards, and success criteria validation.",
)
async def get_feedback_stats(
    query_tenant_id: str = Query(..., alias="tenant_id", description="Tenant identifier (must match authenticated tenant)"),
    start_date: Optional[datetime] = Query(None, description="Filter by created_at >= start_date (ISO8601 format)"),
    end_date: Optional[datetime] = Query(None, description="Filter by created_at <= end_date (ISO8601 format)"),
    authenticated_tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """
    Get aggregated feedback statistics.

    Calculates average rating (for AC2 success criterion: >4/5 target), feedback
    counts by type (thumbs_up, thumbs_down, rating), and positive feedback percentage.
    Used for baseline metrics reporting (Task 1.6, 7.1), weekly review dashboards
    (AC4), and Grafana dashboard visualization (AC3).

    Args:
        query_tenant_id: Tenant identifier from query parameter (validated against authenticated tenant)
        start_date: Optional start date filter (for 7-day baseline period)
        end_date: Optional end date filter (for 7-day baseline period)
        authenticated_tenant_id: Authenticated tenant ID from request context
        db: RLS-aware async database session

    Returns:
        dict: Statistics summary with keys:
            - average_rating: float (1.0-5.0) or null if no ratings
            - feedback_counts: dict with keys (thumbs_up, thumbs_down, rating)
            - total_feedback: int (sum of all feedback submissions)
            - positive_percentage: float (thumbs_up / (thumbs_up + thumbs_down) * 100)

    Raises:
        HTTPException: 403 Forbidden if query tenant_id doesn't match authenticated tenant

    Example:
        Query parameters:
        ?tenant_id=tenant-abc&start_date=2025-11-01T00:00:00Z&end_date=2025-11-07T23:59:59Z

        Response (200 OK):
        {
            "average_rating": 4.35,
            "feedback_counts": {
                "thumbs_up": 45,
                "thumbs_down": 8,
                "rating": 12
            },
            "total_feedback": 65,
            "positive_percentage": 84.9
        }
    """
    # Defense-in-depth: Explicit tenant validation (Finding L2 from code review)
    # Verify query parameter tenant_id matches authenticated tenant to prevent
    # tenant enumeration attacks if RLS middleware fails
    if query_tenant_id != authenticated_tenant_id:
        logger.warning(
            f"Tenant mismatch detected: query_tenant_id={query_tenant_id}, "
            f"authenticated_tenant_id={authenticated_tenant_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: tenant_id in query does not match authenticated tenant",
        )

    try:
        service = FeedbackService(db)

        # Get average rating (for AC2 target: >4/5)
        avg_rating = await service.get_average_rating(
            tenant_id=query_tenant_id,
            start_date=start_date,
            end_date=end_date,
        )

        # Get feedback counts by type
        counts = await service.get_feedback_counts(
            tenant_id=query_tenant_id,
            start_date=start_date,
            end_date=end_date,
        )

        # Calculate total feedback and positive percentage
        total_feedback = sum(counts.values())
        positive_count = counts[FeedbackType.THUMBS_UP.value]
        negative_count = counts[FeedbackType.THUMBS_DOWN.value]
        binary_total = positive_count + negative_count

        positive_percentage = (
            (positive_count / binary_total * 100) if binary_total > 0 else 0.0
        )

        stats = {
            "average_rating": avg_rating,
            "feedback_counts": counts,
            "total_feedback": total_feedback,
            "positive_percentage": round(positive_percentage, 2),
        }

        logger.info(
            f"Feedback stats calculated: tenant={query_tenant_id}, "
            f"avg_rating={avg_rating}, total={total_feedback}, "
            f"positive_pct={positive_percentage:.2f}%"
        )

        return stats

    except Exception as e:
        logger.error(f"Error calculating feedback stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate feedback statistics: {str(e)}",
        )
