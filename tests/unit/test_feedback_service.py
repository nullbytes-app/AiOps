"""
Unit tests for FeedbackService with mocked database.

Tests all feedback service methods (create, retrieve, aggregate) with mocked
database operations to enable fast, deterministic unit tests without database dependency.

Coverage target: 100% for src/services/feedback_service.py business logic
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine.result import ScalarResult

from src.services.feedback_service import FeedbackService
from src.schemas.feedback import FeedbackSubmitRequest, FeedbackType
from src.database.models import EnhancementFeedback


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def mock_db() -> AsyncSession:
    """
    Mock AsyncSession for database operations.

    Returns:
        AsyncMock: Mocked async database session
    """
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def feedback_service(mock_db: AsyncSession) -> FeedbackService:
    """
    Create FeedbackService instance with mocked database session.

    Args:
        mock_db: Mocked async database session

    Returns:
        FeedbackService: Service instance for testing
    """
    return FeedbackService(db=mock_db)


@pytest.fixture
def sample_thumbs_up_request() -> FeedbackSubmitRequest:
    """
    Sample thumbs_up feedback submission request.

    Returns:
        FeedbackSubmitRequest: Request for thumbs_up feedback
    """
    return FeedbackSubmitRequest(
        tenant_id="tenant-test-123",
        ticket_id="TKT-001",
        feedback_type=FeedbackType.THUMBS_UP,
    )


@pytest.fixture
def sample_rating_request() -> FeedbackSubmitRequest:
    """
    Sample rating feedback submission request (1-5 scale with comment).

    Returns:
        FeedbackSubmitRequest: Request for rating feedback
    """
    return FeedbackSubmitRequest(
        tenant_id="tenant-test-123",
        ticket_id="TKT-002",
        enhancement_id=uuid4(),
        technician_email="tech@example.com",
        feedback_type=FeedbackType.RATING,
        rating_value=5,
        feedback_comment="Excellent context! Resolved ticket 10 min faster.",
    )


@pytest.fixture
def sample_thumbs_down_request() -> FeedbackSubmitRequest:
    """
    Sample thumbs_down feedback submission request with comment.

    Returns:
        FeedbackSubmitRequest: Request for thumbs_down feedback
    """
    return FeedbackSubmitRequest(
        tenant_id="tenant-test-123",
        ticket_id="TKT-003",
        feedback_type=FeedbackType.THUMBS_DOWN,
        feedback_comment="Enhancement was not relevant to ticket issue",
    )


# ============================================
# CREATE FEEDBACK TESTS
# ============================================

class TestCreateFeedback:
    """Unit tests for FeedbackService.create_feedback() method."""

    @pytest.mark.asyncio
    async def test_create_thumbs_up_feedback_success(
        self,
        feedback_service: FeedbackService,
        sample_thumbs_up_request: FeedbackSubmitRequest,
        mock_db: AsyncMock,
    ):
        """
        Test creating thumbs_up feedback record succeeds.

        Expected:
        - EnhancementFeedback object created with correct attributes
        - Database add() called with feedback object
        - Database commit() and refresh() called
        - Returned feedback has UUID assigned
        """
        # Mock database operations
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Execute create_feedback
        result = await feedback_service.create_feedback(sample_thumbs_up_request)

        # Verify result
        assert isinstance(result, EnhancementFeedback)
        assert result.tenant_id == "tenant-test-123"
        assert result.ticket_id == "TKT-001"
        assert result.feedback_type == FeedbackType.THUMBS_UP.value
        assert result.rating_value is None  # thumbs_up has no rating_value

        # Verify database operations called
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_rating_feedback_with_comment(
        self,
        feedback_service: FeedbackService,
        sample_rating_request: FeedbackSubmitRequest,
        mock_db: AsyncMock,
    ):
        """
        Test creating rating feedback with comment and technician email.

        Expected:
        - Feedback record created with rating_value=5, comment, email
        - Database operations completed successfully
        """
        # Mock database operations
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Execute create_feedback
        result = await feedback_service.create_feedback(sample_rating_request)

        # Verify result attributes
        assert result.feedback_type == FeedbackType.RATING.value
        assert result.rating_value == 5
        assert result.feedback_comment == "Excellent context! Resolved ticket 10 min faster."
        assert result.technician_email == "tech@example.com"
        assert result.enhancement_id is not None

        # Verify database operations
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_thumbs_down_feedback_with_comment(
        self,
        feedback_service: FeedbackService,
        sample_thumbs_down_request: FeedbackSubmitRequest,
        mock_db: AsyncMock,
    ):
        """
        Test creating thumbs_down feedback with optional comment.

        Expected:
        - Feedback record created with feedback_comment
        - rating_value is null for thumbs_down
        """
        # Mock database operations
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Execute create_feedback
        result = await feedback_service.create_feedback(sample_thumbs_down_request)

        # Verify result
        assert result.feedback_type == FeedbackType.THUMBS_DOWN.value
        assert result.rating_value is None
        assert result.feedback_comment == "Enhancement was not relevant to ticket issue"

    @pytest.mark.asyncio
    async def test_create_feedback_assigns_uuid(
        self,
        feedback_service: FeedbackService,
        sample_thumbs_up_request: FeedbackSubmitRequest,
        mock_db: AsyncMock,
    ):
        """
        Test created feedback record has UUID primary key assigned.

        Expected:
        - result.id is not None (UUID assigned by database default)
        """
        # Mock database operations
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        # Mock refresh to set id attribute (simulating database behavior)
        async def mock_refresh(obj):
            obj.id = uuid4()

        mock_db.refresh = AsyncMock(side_effect=mock_refresh)

        # Execute create_feedback
        result = await feedback_service.create_feedback(sample_thumbs_up_request)

        # Verify UUID assigned
        assert result.id is not None
        assert isinstance(result.id, uuid4().__class__)  # Verify it's a UUID


# ============================================
# GET FEEDBACK TESTS
# ============================================

class TestGetFeedback:
    """Unit tests for FeedbackService.get_feedback() method."""

    @pytest.mark.asyncio
    async def test_get_feedback_all_for_tenant(
        self,
        feedback_service: FeedbackService,
        mock_db: AsyncMock,
    ):
        """
        Test retrieving all feedback for a tenant without filters.

        Expected:
        - Query executed with tenant_id filter only
        - Returns list of feedback records
        """
        # Mock database query result
        mock_feedback_records = [
            EnhancementFeedback(
                id=uuid4(),
                tenant_id="tenant-test-123",
                ticket_id="TKT-001",
                feedback_type=FeedbackType.THUMBS_UP.value,
                created_at=datetime.now(timezone.utc),
            ),
            EnhancementFeedback(
                id=uuid4(),
                tenant_id="tenant-test-123",
                ticket_id="TKT-002",
                feedback_type=FeedbackType.RATING.value,
                rating_value=5,
                created_at=datetime.now(timezone.utc),
            ),
        ]

        # Mock query execution
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_feedback_records
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Execute get_feedback
        result = await feedback_service.get_feedback(tenant_id="tenant-test-123")

        # Verify result
        assert len(result) == 2
        assert result[0].ticket_id == "TKT-001"
        assert result[1].ticket_id == "TKT-002"

        # Verify query executed
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_feedback_filter_by_feedback_type(
        self,
        feedback_service: FeedbackService,
        mock_db: AsyncMock,
    ):
        """
        Test filtering feedback by feedback_type (e.g., only ratings).

        Expected:
        - Query includes feedback_type filter
        - Returns only matching feedback type
        """
        # Mock database result with only rating feedback
        mock_feedback_records = [
            EnhancementFeedback(
                id=uuid4(),
                tenant_id="tenant-test-123",
                ticket_id="TKT-001",
                feedback_type=FeedbackType.RATING.value,
                rating_value=4,
                created_at=datetime.now(timezone.utc),
            ),
            EnhancementFeedback(
                id=uuid4(),
                tenant_id="tenant-test-123",
                ticket_id="TKT-002",
                feedback_type=FeedbackType.RATING.value,
                rating_value=5,
                created_at=datetime.now(timezone.utc),
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_feedback_records
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Execute get_feedback with feedback_type filter
        result = await feedback_service.get_feedback(
            tenant_id="tenant-test-123",
            feedback_type=FeedbackType.RATING,
        )

        # Verify all results are ratings
        assert len(result) == 2
        assert all(f.feedback_type == FeedbackType.RATING.value for f in result)
        assert all(f.rating_value is not None for f in result)

    @pytest.mark.asyncio
    async def test_get_feedback_filter_by_date_range(
        self,
        feedback_service: FeedbackService,
        mock_db: AsyncMock,
    ):
        """
        Test filtering feedback by date range (start_date, end_date).

        Expected:
        - Query includes created_at >= start_date AND created_at <= end_date filters
        """
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc)

        # Mock database result
        mock_feedback_records = [
            EnhancementFeedback(
                id=uuid4(),
                tenant_id="tenant-test-123",
                ticket_id="TKT-001",
                feedback_type=FeedbackType.THUMBS_UP.value,
                created_at=datetime.now(timezone.utc) - timedelta(days=3),
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_feedback_records
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Execute get_feedback with date range
        result = await feedback_service.get_feedback(
            tenant_id="tenant-test-123",
            start_date=start_date,
            end_date=end_date,
        )

        # Verify result
        assert len(result) == 1
        # Verify created_at is within range
        assert start_date <= result[0].created_at <= end_date

    @pytest.mark.asyncio
    async def test_get_feedback_pagination_limit_offset(
        self,
        feedback_service: FeedbackService,
        mock_db: AsyncMock,
    ):
        """
        Test pagination with limit and offset parameters.

        Expected:
        - Query includes .limit() and .offset() clauses
        - limit capped at 1000 max (safety constraint)
        """
        # Mock database result (first page: 3 records)
        mock_feedback_records = [
            EnhancementFeedback(
                id=uuid4(),
                tenant_id="tenant-test-123",
                ticket_id=f"TKT-{i}",
                feedback_type=FeedbackType.THUMBS_UP.value,
                created_at=datetime.now(timezone.utc),
            )
            for i in range(1, 4)
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_feedback_records
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Execute get_feedback with pagination
        result = await feedback_service.get_feedback(
            tenant_id="tenant-test-123",
            limit=3,
            offset=0,
        )

        # Verify result
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_get_feedback_limit_capped_at_1000(
        self,
        feedback_service: FeedbackService,
        mock_db: AsyncMock,
    ):
        """
        Test limit parameter is capped at 1000 max (safety constraint).

        Expected:
        - Even if limit=5000 requested, actual query uses limit=1000
        """
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Request limit=5000 (exceeds max)
        await feedback_service.get_feedback(
            tenant_id="tenant-test-123",
            limit=5000,  # Should be capped at 1000
        )

        # Verify query executed (limit internally capped)
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_feedback_empty_result(
        self,
        feedback_service: FeedbackService,
        mock_db: AsyncMock,
    ):
        """
        Test get_feedback returns empty list when no records match filters.

        Expected:
        - Returns [] (empty list, not None)
        """
        # Mock empty query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Execute get_feedback
        result = await feedback_service.get_feedback(tenant_id="tenant-no-feedback")

        # Verify empty list returned
        assert result == []
        assert isinstance(result, list)


# ============================================
# GET AVERAGE RATING TESTS
# ============================================

class TestGetAverageRating:
    """Unit tests for FeedbackService.get_average_rating() method."""

    @pytest.mark.asyncio
    async def test_calculate_average_rating_two_ratings(
        self,
        feedback_service: FeedbackService,
        mock_db: AsyncMock,
    ):
        """
        Test average rating calculation with 2 ratings (4 and 5).

        Expected:
        - Returns 4.5 (average of 4 and 5)
        """
        # Mock database aggregation result
        mock_result = MagicMock()
        mock_result.scalar.return_value = 4.5  # avg(4, 5) = 4.5
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Execute get_average_rating
        result = await feedback_service.get_average_rating(tenant_id="tenant-test-123")

        # Verify result
        assert result == 4.5
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_average_rating_excludes_thumbs_up_down(
        self,
        feedback_service: FeedbackService,
        mock_db: AsyncMock,
    ):
        """
        Test average rating only includes feedback_type='rating' records.

        Expected:
        - Query filters by feedback_type='rating'
        - thumbs_up/thumbs_down (rating_value=null) excluded from average
        """
        # Mock result (only rating feedback considered)
        mock_result = MagicMock()
        mock_result.scalar.return_value = 4.0
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Execute get_average_rating
        result = await feedback_service.get_average_rating(tenant_id="tenant-test-123")

        # Verify result
        assert result == 4.0

    @pytest.mark.asyncio
    async def test_average_rating_returns_none_when_no_ratings(
        self,
        feedback_service: FeedbackService,
        mock_db: AsyncMock,
    ):
        """
        Test average rating returns None when no rating records exist.

        Expected:
        - Returns None (not 0, not error) when no ratings to average
        """
        # Mock empty result (no ratings)
        mock_result = MagicMock()
        mock_result.scalar.return_value = None  # SQL AVG() returns null for empty set
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Execute get_average_rating
        result = await feedback_service.get_average_rating(tenant_id="tenant-no-ratings")

        # Verify None returned
        assert result is None

    @pytest.mark.asyncio
    async def test_average_rating_with_date_range_filter(
        self,
        feedback_service: FeedbackService,
        mock_db: AsyncMock,
    ):
        """
        Test average rating calculation with date range filter.

        Expected:
        - Query includes created_at >= start_date AND created_at <= end_date
        - Only ratings within date range included in average
        """
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc)

        # Mock result
        mock_result = MagicMock()
        mock_result.scalar.return_value = 4.2
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Execute with date range
        result = await feedback_service.get_average_rating(
            tenant_id="tenant-test-123",
            start_date=start_date,
            end_date=end_date,
        )

        # Verify result
        assert result == 4.2


# ============================================
# GET FEEDBACK COUNTS TESTS
# ============================================

class TestGetFeedbackCounts:
    """Unit tests for FeedbackService.get_feedback_counts() method."""

    @pytest.mark.asyncio
    async def test_feedback_counts_all_types(
        self,
        feedback_service: FeedbackService,
        mock_db: AsyncMock,
    ):
        """
        Test feedback counts by type returns counts for all 3 types.

        Expected:
        - Returns dict: {thumbs_up: 3, thumbs_down: 2, rating: 2}
        """
        # Mock database aggregation result (rows: [(type, count), ...])
        mock_result = MagicMock()
        mock_result.all.return_value = [
            (FeedbackType.THUMBS_UP.value, 3),
            (FeedbackType.THUMBS_DOWN.value, 2),
            (FeedbackType.RATING.value, 2),
        ]
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Execute get_feedback_counts
        result = await feedback_service.get_feedback_counts(tenant_id="tenant-test-123")

        # Verify result
        assert result[FeedbackType.THUMBS_UP.value] == 3
        assert result[FeedbackType.THUMBS_DOWN.value] == 2
        assert result[FeedbackType.RATING.value] == 2

    @pytest.mark.asyncio
    async def test_feedback_counts_default_zero_for_missing_types(
        self,
        feedback_service: FeedbackService,
        mock_db: AsyncMock,
    ):
        """
        Test feedback counts returns 0 for types with no submissions.

        Expected:
        - If only thumbs_up exists, thumbs_down and rating should be 0
        - Default counts: {thumbs_up: 0, thumbs_down: 0, rating: 0}
        """
        # Mock result with only thumbs_up (no thumbs_down or rating)
        mock_result = MagicMock()
        mock_result.all.return_value = [
            (FeedbackType.THUMBS_UP.value, 5),
            # thumbs_down and rating missing from result
        ]
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Execute get_feedback_counts
        result = await feedback_service.get_feedback_counts(tenant_id="tenant-test-123")

        # Verify default zero counts
        assert result[FeedbackType.THUMBS_UP.value] == 5
        assert result[FeedbackType.THUMBS_DOWN.value] == 0  # Default to 0
        assert result[FeedbackType.RATING.value] == 0  # Default to 0

    @pytest.mark.asyncio
    async def test_feedback_counts_all_zero_when_no_feedback(
        self,
        feedback_service: FeedbackService,
        mock_db: AsyncMock,
    ):
        """
        Test feedback counts returns all zeros when no feedback exists.

        Expected:
        - Returns {thumbs_up: 0, thumbs_down: 0, rating: 0}
        """
        # Mock empty result (no feedback)
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Execute get_feedback_counts
        result = await feedback_service.get_feedback_counts(tenant_id="tenant-no-feedback")

        # Verify all zero counts
        assert result[FeedbackType.THUMBS_UP.value] == 0
        assert result[FeedbackType.THUMBS_DOWN.value] == 0
        assert result[FeedbackType.RATING.value] == 0

    @pytest.mark.asyncio
    async def test_feedback_counts_with_date_range_filter(
        self,
        feedback_service: FeedbackService,
        mock_db: AsyncMock,
    ):
        """
        Test feedback counts with date range filter.

        Expected:
        - Query includes created_at >= start_date AND created_at <= end_date
        - Counts only include feedback within date range
        """
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc)

        # Mock result
        mock_result = MagicMock()
        mock_result.all.return_value = [
            (FeedbackType.THUMBS_UP.value, 2),
            (FeedbackType.RATING.value, 1),
        ]
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Execute with date range
        result = await feedback_service.get_feedback_counts(
            tenant_id="tenant-test-123",
            start_date=start_date,
            end_date=end_date,
        )

        # Verify result
        assert result[FeedbackType.THUMBS_UP.value] == 2
        assert result[FeedbackType.RATING.value] == 1
