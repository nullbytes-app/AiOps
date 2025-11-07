"""
Enhancement feedback service (Story 5.5 - AC5).

Business logic for storing, retrieving, and aggregating enhancement feedback
from technicians. Supports thumbs up/down and 1-5 rating scales for continuous
quality monitoring, satisfaction tracking, and data-driven roadmap prioritization.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import EnhancementFeedback
from src.schemas.feedback import FeedbackSubmitRequest, FeedbackType
from src.utils.logger import logger


class FeedbackService:
    """
    Service for managing enhancement feedback operations.

    Provides methods for creating feedback records, retrieving feedback with filters,
    and calculating aggregated statistics (average ratings, thumbs up/down counts).
    All queries enforce tenant isolation via RLS (row-level security).
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize feedback service with database session.

        Args:
            db: Async database session with RLS context set (app.current_tenant_id)
        """
        self.db = db

    async def create_feedback(
        self,
        feedback_request: FeedbackSubmitRequest
    ) -> EnhancementFeedback:
        """
        Store new enhancement feedback record.

        Creates feedback record in enhancement_feedback table. RLS policies ensure
        tenant isolation (feedback only visible to owning tenant). Validates that
        rating_value is provided when feedback_type='rating' (enforced by Pydantic).

        Args:
            feedback_request: Validated feedback submission request

        Returns:
            EnhancementFeedback: Created database record with assigned UUID

        Raises:
            sqlalchemy.exc.IntegrityError: If database constraints violated
            sqlalchemy.exc.OperationalError: If database unavailable

        Example:
            >>> service = FeedbackService(db)
            >>> request = FeedbackSubmitRequest(
            ...     tenant_id="tenant-abc",
            ...     ticket_id="TKT-001",
            ...     feedback_type=FeedbackType.RATING,
            ...     rating_value=5,
            ...     feedback_comment="Very helpful!"
            ... )
            >>> feedback = await service.create_feedback(request)
            >>> print(feedback.id)
            UUID('7c9e6679-7425-40de-944b-e07fc1f90ae7')
        """
        # Create new feedback record from request
        feedback = EnhancementFeedback(
            tenant_id=feedback_request.tenant_id,
            ticket_id=feedback_request.ticket_id,
            enhancement_id=feedback_request.enhancement_id,
            technician_email=feedback_request.technician_email,
            feedback_type=feedback_request.feedback_type.value,
            rating_value=feedback_request.rating_value,
            feedback_comment=feedback_request.feedback_comment,
        )

        # Add to session and commit
        self.db.add(feedback)
        await self.db.commit()
        await self.db.refresh(feedback)

        logger.info(
            f"Feedback created: id={feedback.id}, tenant={feedback.tenant_id}, "
            f"ticket={feedback.ticket_id}, type={feedback.feedback_type}"
        )

        return feedback

    async def get_feedback(
        self,
        tenant_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        feedback_type: Optional[FeedbackType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[EnhancementFeedback]:
        """
        Retrieve feedback records with optional filters.

        Queries enhancement_feedback table with RLS enforcement ensuring only
        tenant's own feedback is visible. Supports filtering by date range,
        feedback type, and pagination for large result sets.

        Args:
            tenant_id: Tenant identifier (must match RLS context)
            start_date: Optional start date filter (created_at >= start_date)
            end_date: Optional end date filter (created_at <= end_date)
            feedback_type: Optional filter by feedback type (thumbs_up, thumbs_down, rating)
            limit: Maximum records to return (default 100, max 1000)
            offset: Pagination offset (default 0)

        Returns:
            list[EnhancementFeedback]: List of feedback records matching filters

        Example:
            >>> from datetime import datetime, timedelta
            >>> service = FeedbackService(db)
            >>> # Get all ratings from last 7 days
            >>> feedback_list = await service.get_feedback(
            ...     tenant_id="tenant-abc",
            ...     start_date=datetime.now(timezone.utc) - timedelta(days=7),
            ...     feedback_type=FeedbackType.RATING
            ... )
            >>> avg_rating = sum(f.rating_value for f in feedback_list) / len(feedback_list)
            >>> print(f"Average rating: {avg_rating:.2f}/5")
            Average rating: 4.35/5
        """
        # Build query with filters
        query = select(EnhancementFeedback).where(
            EnhancementFeedback.tenant_id == tenant_id
        )

        # Add date range filters
        if start_date:
            query = query.where(EnhancementFeedback.created_at >= start_date)
        if end_date:
            query = query.where(EnhancementFeedback.created_at <= end_date)

        # Add feedback type filter
        if feedback_type:
            query = query.where(EnhancementFeedback.feedback_type == feedback_type.value)

        # Add ordering (most recent first) and pagination
        query = query.order_by(EnhancementFeedback.created_at.desc())
        query = query.limit(min(limit, 1000)).offset(offset)  # Cap limit at 1000

        # Execute query
        result = await self.db.execute(query)
        feedback_list = result.scalars().all()

        logger.info(
            f"Retrieved {len(feedback_list)} feedback records: tenant={tenant_id}, "
            f"filters=(start_date={start_date}, end_date={end_date}, type={feedback_type})"
        )

        return list(feedback_list)

    async def get_average_rating(
        self,
        tenant_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Optional[float]:
        """
        Calculate average rating value for a tenant.

        Aggregates rating_value for all feedback records where feedback_type='rating'.
        Excludes thumbs up/down feedback (rating_value=null). Used for AC2 success
        criterion tracking (target: >4/5 average satisfaction score).

        Args:
            tenant_id: Tenant identifier (must match RLS context)
            start_date: Optional start date filter (created_at >= start_date)
            end_date: Optional end date filter (created_at <= end_date)

        Returns:
            Optional[float]: Average rating (1.0-5.0) or None if no ratings exist

        Example:
            >>> service = FeedbackService(db)
            >>> avg_rating = await service.get_average_rating("tenant-abc")
            >>> if avg_rating and avg_rating >= 4.0:
            ...     print("✅ SUCCESS CRITERION MET: >4/5 average satisfaction")
            ... else:
            ...     print(f"⚠️ Below target: {avg_rating:.2f}/5")
        """
        # Build query for average rating
        query = (
            select(func.avg(EnhancementFeedback.rating_value))
            .where(EnhancementFeedback.tenant_id == tenant_id)
            .where(EnhancementFeedback.feedback_type == FeedbackType.RATING.value)
            .where(EnhancementFeedback.rating_value.isnot(None))
        )

        # Add date range filters
        if start_date:
            query = query.where(EnhancementFeedback.created_at >= start_date)
        if end_date:
            query = query.where(EnhancementFeedback.created_at <= end_date)

        # Execute aggregation query
        result = await self.db.execute(query)
        avg_rating = result.scalar()

        logger.info(
            f"Calculated average rating: tenant={tenant_id}, avg={avg_rating}, "
            f"period=({start_date}, {end_date})"
        )

        return float(avg_rating) if avg_rating is not None else None

    async def get_feedback_counts(
        self,
        tenant_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict[str, int]:
        """
        Count feedback submissions by type (thumbs up, thumbs down, rating).

        Aggregates total counts for each feedback_type. Used for sentiment analysis
        and baseline metrics reporting (e.g., "78% positive feedback" = thumbs_up / total).

        Args:
            tenant_id: Tenant identifier (must match RLS context)
            start_date: Optional start date filter (created_at >= start_date)
            end_date: Optional end date filter (created_at <= end_date)

        Returns:
            dict[str, int]: Count by feedback type, e.g.
                {"thumbs_up": 45, "thumbs_down": 8, "rating": 12}

        Example:
            >>> service = FeedbackService(db)
            >>> counts = await service.get_feedback_counts("tenant-abc")
            >>> total = sum(counts.values())
            >>> positive_pct = (counts["thumbs_up"] / total) * 100
            >>> print(f"Positive feedback: {positive_pct:.1f}%")
            Positive feedback: 84.9%
        """
        # Build count query grouped by feedback_type
        query = (
            select(
                EnhancementFeedback.feedback_type,
                func.count(EnhancementFeedback.id).label("count"),
            )
            .where(EnhancementFeedback.tenant_id == tenant_id)
            .group_by(EnhancementFeedback.feedback_type)
        )

        # Add date range filters
        if start_date:
            query = query.where(EnhancementFeedback.created_at >= start_date)
        if end_date:
            query = query.where(EnhancementFeedback.created_at <= end_date)

        # Execute aggregation query
        result = await self.db.execute(query)
        rows = result.all()

        # Convert to dict with default 0 counts
        counts = {
            FeedbackType.THUMBS_UP.value: 0,
            FeedbackType.THUMBS_DOWN.value: 0,
            FeedbackType.RATING.value: 0,
        }
        for feedback_type, count in rows:
            counts[feedback_type] = count

        logger.info(
            f"Feedback counts: tenant={tenant_id}, counts={counts}, "
            f"period=({start_date}, {end_date})"
        )

        return counts
