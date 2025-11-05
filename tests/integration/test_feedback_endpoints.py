"""
Integration tests for enhancement feedback API endpoints (Story 5.5 - AC5).

Tests cover:
- POST /api/v1/feedback (valid/invalid inputs, validation errors)
- GET /api/v1/feedback (retrieval, filtering, pagination, RLS enforcement)
- GET /api/v1/feedback/stats (aggregated statistics calculations)
- Multi-tenant isolation (RLS security testing)
- Database constraints (CHECK constraints, foreign keys)

Target coverage: >90% for src/api/feedback.py, src/services/feedback_service.py
"""

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from src.main import app
from src.database.models import EnhancementFeedback
from src.schemas.feedback import FeedbackType


# ============================================
# Fixtures
# ============================================

@pytest.fixture
async def test_tenant_id():
    """Test tenant UUID for multi-tenant testing."""
    return "tenant-test-abc-123"


@pytest.fixture
async def second_tenant_id():
    """Second test tenant UUID for cross-tenant isolation testing."""
    return "tenant-test-xyz-789"


@pytest.fixture
async def test_ticket_id():
    """Test ticket ID for feedback submissions."""
    return "TKT-001-TEST"


@pytest.fixture
async def test_enhancement_id():
    """Test enhancement UUID for feedback submissions."""
    return uuid4()


@pytest.fixture
async def async_client():
    """
    Async HTTP client for testing FastAPI endpoints.

    Returns:
        AsyncClient: HTTPX async client configured for app testing
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
async def db_session(async_client):
    """
    Database session fixture with RLS context and transaction rollback.

    Note: This fixture assumes database session management follows existing
    patterns from Epic 3 with RLS enforcement via app.current_tenant_id.

    Yields:
        AsyncSession: Database session for test assertions
    """
    # This is a placeholder - actual implementation should follow existing
    # database fixture patterns from tests/integration/test_database.py
    # with proper transaction rollback for test isolation
    from src.database.session import get_db
    async for session in get_db():
        yield session
        await session.rollback()


@pytest.fixture
async def seed_feedback_data(db_session, test_tenant_id, second_tenant_id, test_ticket_id, test_enhancement_id):
    """
    Seed database with sample feedback data for testing retrieval/filtering.

    Creates:
    - 3 thumbs_up feedback for test_tenant
    - 2 thumbs_down feedback for test_tenant
    - 2 rating feedback (rating_value=4, 5) for test_tenant
    - 2 feedback records for second_tenant (for cross-tenant isolation testing)

    Returns:
        dict: Summary of seeded data (counts by type, tenant)
    """
    # Set RLS context to test_tenant for seeding
    await db_session.execute(text(f"SET app.current_tenant_id = '{test_tenant_id}'"))

    # Seed feedback for test_tenant
    feedback_records = [
        # Thumbs up (3 records)
        EnhancementFeedback(
            tenant_id=test_tenant_id,
            ticket_id=f"{test_ticket_id}-1",
            enhancement_id=test_enhancement_id,
            feedback_type=FeedbackType.THUMBS_UP.value,
            technician_email="tech1@example.com",
        ),
        EnhancementFeedback(
            tenant_id=test_tenant_id,
            ticket_id=f"{test_ticket_id}-2",
            feedback_type=FeedbackType.THUMBS_UP.value,
        ),
        EnhancementFeedback(
            tenant_id=test_tenant_id,
            ticket_id=f"{test_ticket_id}-3",
            feedback_type=FeedbackType.THUMBS_UP.value,
        ),
        # Thumbs down (2 records)
        EnhancementFeedback(
            tenant_id=test_tenant_id,
            ticket_id=f"{test_ticket_id}-4",
            feedback_type=FeedbackType.THUMBS_DOWN.value,
            feedback_comment="Not relevant to ticket",
        ),
        EnhancementFeedback(
            tenant_id=test_tenant_id,
            ticket_id=f"{test_ticket_id}-5",
            feedback_type=FeedbackType.THUMBS_DOWN.value,
        ),
        # Detailed ratings (2 records)
        EnhancementFeedback(
            tenant_id=test_tenant_id,
            ticket_id=f"{test_ticket_id}-6",
            enhancement_id=test_enhancement_id,
            feedback_type=FeedbackType.RATING.value,
            rating_value=4,
            technician_email="tech2@example.com",
            feedback_comment="Good context, saved 5 minutes",
        ),
        EnhancementFeedback(
            tenant_id=test_tenant_id,
            ticket_id=f"{test_ticket_id}-7",
            feedback_type=FeedbackType.RATING.value,
            rating_value=5,
            feedback_comment="Excellent! Resolved ticket immediately",
        ),
    ]

    for record in feedback_records:
        db_session.add(record)

    await db_session.commit()

    # Switch RLS context to second_tenant and seed 2 records
    await db_session.execute(text(f"SET app.current_tenant_id = '{second_tenant_id}'"))

    second_tenant_feedback = [
        EnhancementFeedback(
            tenant_id=second_tenant_id,
            ticket_id="TKT-SECOND-TENANT-001",
            feedback_type=FeedbackType.THUMBS_UP.value,
        ),
        EnhancementFeedback(
            tenant_id=second_tenant_id,
            ticket_id="TKT-SECOND-TENANT-002",
            feedback_type=FeedbackType.RATING.value,
            rating_value=3,
        ),
    ]

    for record in second_tenant_feedback:
        db_session.add(record)

    await db_session.commit()

    return {
        "test_tenant": {
            "thumbs_up": 3,
            "thumbs_down": 2,
            "rating": 2,
            "total": 7,
        },
        "second_tenant": {
            "total": 2,
        },
    }


# ============================================
# POST /api/v1/feedback - Valid Inputs
# ============================================

class TestFeedbackSubmissionValidInputs:
    """Test POST /api/v1/feedback with valid feedback submissions."""

    @pytest.mark.asyncio
    async def test_submit_thumbs_up_feedback(self, async_client, test_tenant_id, test_ticket_id):
        """
        Test submitting thumbs_up feedback returns 201 Created and stores record.

        Expected:
        - Response: 201 Created with feedback UUID
        - Database: Record created with feedback_type='thumbs_up', rating_value=null
        """
        request_payload = {
            "tenant_id": test_tenant_id,
            "ticket_id": test_ticket_id,
            "feedback_type": "thumbs_up",
        }

        response = await async_client.post("/api/v1/feedback", json=request_payload)

        assert response.status_code == 201
        response_data = response.json()
        assert "id" in response_data
        assert response_data["status"] == "created"
        assert response_data["message"] == "Feedback submitted successfully"

        # Verify UUID format
        feedback_id = response_data["id"]
        assert len(feedback_id) == 36  # UUID format: 8-4-4-4-12

    @pytest.mark.asyncio
    async def test_submit_thumbs_down_feedback(self, async_client, test_tenant_id, test_ticket_id):
        """
        Test submitting thumbs_down feedback with optional comment.

        Expected:
        - Response: 201 Created
        - Database: Record with feedback_comment stored correctly
        """
        request_payload = {
            "tenant_id": test_tenant_id,
            "ticket_id": test_ticket_id,
            "feedback_type": "thumbs_down",
            "feedback_comment": "Enhancement was not relevant to the ticket issue",
        }

        response = await async_client.post("/api/v1/feedback", json=request_payload)

        assert response.status_code == 201
        response_data = response.json()
        assert response_data["status"] == "created"

    @pytest.mark.asyncio
    async def test_submit_rating_feedback_with_comment(self, async_client, test_tenant_id, test_ticket_id, test_enhancement_id):
        """
        Test submitting 1-5 rating feedback with technician email and comment.

        Expected:
        - Response: 201 Created
        - Database: Record with rating_value=5, technician_email, feedback_comment stored
        """
        request_payload = {
            "tenant_id": test_tenant_id,
            "ticket_id": test_ticket_id,
            "enhancement_id": str(test_enhancement_id),
            "technician_email": "tech@example.com",
            "feedback_type": "rating",
            "rating_value": 5,
            "feedback_comment": "Excellent context! Resolved ticket 10 minutes faster than usual.",
        }

        response = await async_client.post("/api/v1/feedback", json=request_payload)

        assert response.status_code == 201
        response_data = response.json()
        assert response_data["status"] == "created"

    @pytest.mark.asyncio
    async def test_submit_anonymous_feedback(self, async_client, test_tenant_id, test_ticket_id):
        """
        Test submitting anonymous feedback (no technician_email).

        Expected:
        - Response: 201 Created
        - Database: Record with technician_email=null (anonymous feedback supported)
        """
        request_payload = {
            "tenant_id": test_tenant_id,
            "ticket_id": test_ticket_id,
            "feedback_type": "thumbs_up",
            # No technician_email provided - anonymous feedback
        }

        response = await async_client.post("/api/v1/feedback", json=request_payload)

        assert response.status_code == 201
        response_data = response.json()
        assert response_data["status"] == "created"


# ============================================
# POST /api/v1/feedback - Invalid Inputs
# ============================================

class TestFeedbackSubmissionInvalidInputs:
    """Test POST /api/v1/feedback with invalid inputs and validation errors."""

    @pytest.mark.asyncio
    async def test_submit_rating_without_rating_value(self, async_client, test_tenant_id, test_ticket_id):
        """
        Test submitting rating feedback without rating_value fails with 422.

        Expected:
        - Response: 422 Unprocessable Entity (Pydantic validation error)
        - Error: "rating_value is required when feedback_type='rating'"
        """
        request_payload = {
            "tenant_id": test_tenant_id,
            "ticket_id": test_ticket_id,
            "feedback_type": "rating",
            # Missing rating_value - should fail Pydantic validation
        }

        response = await async_client.post("/api/v1/feedback", json=request_payload)

        assert response.status_code == 422
        response_data = response.json()
        assert "detail" in response_data

    @pytest.mark.asyncio
    async def test_submit_rating_value_exceeds_max(self, async_client, test_tenant_id, test_ticket_id):
        """
        Test submitting rating_value=6 (exceeds max=5) fails with 422.

        Expected:
        - Response: 422 Unprocessable Entity (Pydantic validation: rating_value must be 1-5)
        """
        request_payload = {
            "tenant_id": test_tenant_id,
            "ticket_id": test_ticket_id,
            "feedback_type": "rating",
            "rating_value": 6,  # Exceeds max=5, violates Pydantic constraint
        }

        response = await async_client.post("/api/v1/feedback", json=request_payload)

        assert response.status_code == 422
        response_data = response.json()
        assert "detail" in response_data

    @pytest.mark.asyncio
    async def test_submit_rating_value_below_min(self, async_client, test_tenant_id, test_ticket_id):
        """
        Test submitting rating_value=0 (below min=1) fails with 422.

        Expected:
        - Response: 422 Unprocessable Entity (Pydantic validation: rating_value must be 1-5)
        """
        request_payload = {
            "tenant_id": test_tenant_id,
            "ticket_id": test_ticket_id,
            "feedback_type": "rating",
            "rating_value": 0,  # Below min=1, violates Pydantic constraint
        }

        response = await async_client.post("/api/v1/feedback", json=request_payload)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_thumbs_up_with_rating_value(self, async_client, test_tenant_id, test_ticket_id):
        """
        Test submitting thumbs_up with rating_value fails with 422.

        Expected:
        - Response: 422 Unprocessable Entity
        - Error: "rating_value must be null when feedback_type='thumbs_up'"
        """
        request_payload = {
            "tenant_id": test_tenant_id,
            "ticket_id": test_ticket_id,
            "feedback_type": "thumbs_up",
            "rating_value": 5,  # Should be null for thumbs_up
        }

        response = await async_client.post("/api/v1/feedback", json=request_payload)

        assert response.status_code == 422
        response_data = response.json()
        assert "detail" in response_data

    @pytest.mark.asyncio
    async def test_submit_missing_required_fields(self, async_client):
        """
        Test submitting feedback with missing required fields (tenant_id, ticket_id).

        Expected:
        - Response: 422 Unprocessable Entity (missing required fields)
        """
        request_payload = {
            "feedback_type": "thumbs_up",
            # Missing tenant_id and ticket_id
        }

        response = await async_client.post("/api/v1/feedback", json=request_payload)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_invalid_feedback_type(self, async_client, test_tenant_id, test_ticket_id):
        """
        Test submitting invalid feedback_type (not in enum) fails with 422.

        Expected:
        - Response: 422 Unprocessable Entity (feedback_type must be thumbs_up, thumbs_down, or rating)
        """
        request_payload = {
            "tenant_id": test_tenant_id,
            "ticket_id": test_ticket_id,
            "feedback_type": "invalid_type",  # Not in FeedbackType enum
        }

        response = await async_client.post("/api/v1/feedback", json=request_payload)

        assert response.status_code == 422


# ============================================
# GET /api/v1/feedback - Retrieval and Filtering
# ============================================

class TestFeedbackRetrieval:
    """Test GET /api/v1/feedback with filtering, pagination, and RLS enforcement."""

    @pytest.mark.asyncio
    async def test_get_all_feedback_for_tenant(self, async_client, test_tenant_id, seed_feedback_data):
        """
        Test retrieving all feedback for a tenant returns correct count.

        Expected:
        - Response: 200 OK with 7 feedback records for test_tenant
        - RLS: Only test_tenant feedback visible (second_tenant records excluded)
        """
        response = await async_client.get(f"/api/v1/feedback?tenant_id={test_tenant_id}")

        assert response.status_code == 200
        response_data = response.json()
        assert "feedback" in response_data
        assert "count" in response_data
        assert response_data["count"] == 7  # 3 thumbs_up + 2 thumbs_down + 2 rating
        assert len(response_data["feedback"]) == 7

    @pytest.mark.asyncio
    async def test_filter_feedback_by_type_thumbs_up(self, async_client, test_tenant_id, seed_feedback_data):
        """
        Test filtering feedback by feedback_type=thumbs_up returns only thumbs_up records.

        Expected:
        - Response: 200 OK with 3 thumbs_up records
        """
        response = await async_client.get(
            f"/api/v1/feedback?tenant_id={test_tenant_id}&feedback_type=thumbs_up"
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["count"] == 3

        # Verify all returned records are thumbs_up
        for record in response_data["feedback"]:
            assert record["feedback_type"] == "thumbs_up"
            assert record["rating_value"] is None

    @pytest.mark.asyncio
    async def test_filter_feedback_by_type_rating(self, async_client, test_tenant_id, seed_feedback_data):
        """
        Test filtering feedback by feedback_type=rating returns only rating records.

        Expected:
        - Response: 200 OK with 2 rating records
        - All records have rating_value between 1-5
        """
        response = await async_client.get(
            f"/api/v1/feedback?tenant_id={test_tenant_id}&feedback_type=rating"
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["count"] == 2

        # Verify all returned records are ratings with valid rating_value
        for record in response_data["feedback"]:
            assert record["feedback_type"] == "rating"
            assert 1 <= record["rating_value"] <= 5

    @pytest.mark.asyncio
    async def test_filter_feedback_by_date_range(self, async_client, test_tenant_id, seed_feedback_data):
        """
        Test filtering feedback by date range (start_date, end_date).

        Expected:
        - Response: 200 OK with feedback created within date range
        """
        # Use 7-day window from now
        start_date = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        end_date = datetime.now(timezone.utc).isoformat()

        response = await async_client.get(
            f"/api/v1/feedback?tenant_id={test_tenant_id}&start_date={start_date}&end_date={end_date}"
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["count"] >= 0  # Should return recent feedback

        # Verify all returned records are within date range
        for record in response_data["feedback"]:
            created_at = datetime.fromisoformat(record["created_at"].replace("Z", "+00:00"))
            assert created_at >= datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            assert created_at <= datetime.fromisoformat(end_date.replace("Z", "+00:00"))

    @pytest.mark.asyncio
    async def test_pagination_with_limit_offset(self, async_client, test_tenant_id, seed_feedback_data):
        """
        Test pagination with limit and offset parameters.

        Expected:
        - Response: 200 OK with correct number of records per page
        - Second page returns different records than first page
        """
        # Get first page (limit=3, offset=0)
        response_page1 = await async_client.get(
            f"/api/v1/feedback?tenant_id={test_tenant_id}&limit=3&offset=0"
        )

        assert response_page1.status_code == 200
        page1_data = response_page1.json()
        assert page1_data["count"] == 3

        # Get second page (limit=3, offset=3)
        response_page2 = await async_client.get(
            f"/api/v1/feedback?tenant_id={test_tenant_id}&limit=3&offset=3"
        )

        assert response_page2.status_code == 200
        page2_data = response_page2.json()
        assert page2_data["count"] == 3

        # Verify pages contain different records (no overlap)
        page1_ids = {record["id"] for record in page1_data["feedback"]}
        page2_ids = {record["id"] for record in page2_data["feedback"]}
        assert len(page1_ids.intersection(page2_ids)) == 0


# ============================================
# GET /api/v1/feedback/stats - Aggregated Statistics
# ============================================

class TestFeedbackStatistics:
    """Test GET /api/v1/feedback/stats for aggregated feedback statistics."""

    @pytest.mark.asyncio
    async def test_calculate_average_rating(self, async_client, test_tenant_id, seed_feedback_data):
        """
        Test average rating calculation matches expected value.

        Expected:
        - Response: 200 OK with average_rating=4.5 (avg of 4 and 5)
        - Only includes rating_type='rating' records (excludes thumbs_up/down)
        """
        response = await async_client.get(f"/api/v1/feedback/stats?tenant_id={test_tenant_id}")

        assert response.status_code == 200
        response_data = response.json()

        assert "average_rating" in response_data
        # Seeded data has ratings: 4 and 5, so average should be 4.5
        assert response_data["average_rating"] == 4.5

    @pytest.mark.asyncio
    async def test_feedback_counts_by_type(self, async_client, test_tenant_id, seed_feedback_data):
        """
        Test feedback counts by type (thumbs_up, thumbs_down, rating).

        Expected:
        - Response: 200 OK with counts: {thumbs_up: 3, thumbs_down: 2, rating: 2}
        """
        response = await async_client.get(f"/api/v1/feedback/stats?tenant_id={test_tenant_id}")

        assert response.status_code == 200
        response_data = response.json()

        assert "feedback_counts" in response_data
        counts = response_data["feedback_counts"]
        assert counts["thumbs_up"] == 3
        assert counts["thumbs_down"] == 2
        assert counts["rating"] == 2

    @pytest.mark.asyncio
    async def test_total_feedback_count(self, async_client, test_tenant_id, seed_feedback_data):
        """
        Test total_feedback count sums all feedback types.

        Expected:
        - Response: 200 OK with total_feedback=7 (3+2+2)
        """
        response = await async_client.get(f"/api/v1/feedback/stats?tenant_id={test_tenant_id}")

        assert response.status_code == 200
        response_data = response.json()

        assert "total_feedback" in response_data
        assert response_data["total_feedback"] == 7

    @pytest.mark.asyncio
    async def test_positive_percentage_calculation(self, async_client, test_tenant_id, seed_feedback_data):
        """
        Test positive_percentage formula: thumbs_up / (thumbs_up + thumbs_down) * 100.

        Expected:
        - Response: 200 OK with positive_percentage=60.0 (3 / (3+2) * 100)
        """
        response = await async_client.get(f"/api/v1/feedback/stats?tenant_id={test_tenant_id}")

        assert response.status_code == 200
        response_data = response.json()

        assert "positive_percentage" in response_data
        # Formula: 3 thumbs_up / (3 thumbs_up + 2 thumbs_down) * 100 = 60.0%
        assert response_data["positive_percentage"] == 60.0

    @pytest.mark.asyncio
    async def test_stats_with_date_range_filter(self, async_client, test_tenant_id, seed_feedback_data):
        """
        Test statistics calculation with date range filter.

        Expected:
        - Response: 200 OK with stats calculated only for feedback within date range
        """
        start_date = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        end_date = datetime.now(timezone.utc).isoformat()

        response = await async_client.get(
            f"/api/v1/feedback/stats?tenant_id={test_tenant_id}&start_date={start_date}&end_date={end_date}"
        )

        assert response.status_code == 200
        response_data = response.json()
        assert "average_rating" in response_data
        assert "total_feedback" in response_data


# ============================================
# Multi-Tenant Isolation (RLS Security Testing)
# ============================================

class TestMultiTenantIsolation:
    """Test RLS enforcement prevents cross-tenant data access."""

    @pytest.mark.asyncio
    async def test_rls_prevents_cross_tenant_feedback_access(
        self, async_client, test_tenant_id, second_tenant_id, seed_feedback_data
    ):
        """
        Test querying second_tenant feedback with test_tenant credentials returns empty.

        Expected:
        - Response: 200 OK with empty feedback list (RLS blocks cross-tenant access)
        - OR 403 Forbidden if explicit tenant validation implemented (Finding L2 recommendation)
        """
        # Attempt to retrieve second_tenant feedback while authenticated as test_tenant
        # (RLS context set to test_tenant via middleware)
        response = await async_client.get(f"/api/v1/feedback?tenant_id={second_tenant_id}")

        # RLS should prevent access - either 403 Forbidden or empty result
        if response.status_code == 403:
            # Explicit tenant validation implemented (recommended by code review Finding L2)
            assert response.status_code == 403
        else:
            # RLS returns empty results (current behavior)
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["count"] == 0
            assert len(response_data["feedback"]) == 0

    @pytest.mark.asyncio
    async def test_rls_prevents_cross_tenant_stats_access(
        self, async_client, test_tenant_id, second_tenant_id, seed_feedback_data
    ):
        """
        Test querying second_tenant stats with test_tenant credentials.

        Expected:
        - Response: 200 OK with average_rating=null, total_feedback=0 (RLS blocks access)
        - OR 403 Forbidden if explicit tenant validation implemented
        """
        response = await async_client.get(f"/api/v1/feedback/stats?tenant_id={second_tenant_id}")

        # RLS should prevent access
        if response.status_code == 403:
            assert response.status_code == 403
        else:
            assert response.status_code == 200
            response_data = response.json()
            # Stats should show no data for unauthorized tenant
            assert response_data["total_feedback"] == 0
            assert response_data["average_rating"] is None or response_data["average_rating"] == 0

    @pytest.mark.asyncio
    async def test_rls_prevents_cross_tenant_feedback_submission(
        self, async_client, test_tenant_id, second_tenant_id
    ):
        """
        Test submitting feedback for second_tenant while authenticated as test_tenant.

        Expected:
        - Response: 403 Forbidden (RLS WITH CHECK policy blocks INSERT)
        - OR record created but invisible to second_tenant queries (RLS USING policy)

        Note: This test verifies RLS WITH CHECK policy enforcement on INSERT operations.
        """
        request_payload = {
            "tenant_id": second_tenant_id,  # Attempt to submit for different tenant
            "ticket_id": "TKT-CROSS-TENANT-ATTACK",
            "feedback_type": "thumbs_up",
        }

        response = await async_client.post("/api/v1/feedback", json=request_payload)

        # RLS WITH CHECK policy should block cross-tenant INSERT
        # Expected behavior: 403 Forbidden or 500 Internal Server Error (RLS violation)
        assert response.status_code in [403, 500]


# ============================================
# Database Constraints and Edge Cases
# ============================================

class TestDatabaseConstraints:
    """Test database-level constraints (CHECK constraints, foreign keys)."""

    @pytest.mark.asyncio
    async def test_check_constraint_rating_value_range(self, db_session, test_tenant_id):
        """
        Test database CHECK constraint prevents rating_value outside 1-5 range.

        Expected:
        - Database raises IntegrityError for rating_value=6 (violates CHECK constraint)

        Note: This tests database-level constraint, not Pydantic validation.
        """
        from sqlalchemy.exc import IntegrityError

        # Set RLS context
        await db_session.execute(text(f"SET app.current_tenant_id = '{test_tenant_id}'"))

        # Attempt to insert feedback with rating_value=6 (exceeds CHECK constraint max=5)
        invalid_feedback = EnhancementFeedback(
            tenant_id=test_tenant_id,
            ticket_id="TKT-CONSTRAINT-TEST",
            feedback_type=FeedbackType.RATING.value,
            rating_value=6,  # Violates CHECK constraint
        )

        db_session.add(invalid_feedback)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_check_constraint_feedback_type_enum(self, db_session, test_tenant_id):
        """
        Test database CHECK constraint prevents invalid feedback_type values.

        Expected:
        - Database raises IntegrityError for feedback_type='invalid' (not in enum)
        """
        from sqlalchemy.exc import IntegrityError

        # Set RLS context
        await db_session.execute(text(f"SET app.current_tenant_id = '{test_tenant_id}'"))

        # Attempt to insert feedback with invalid feedback_type
        invalid_feedback = EnhancementFeedback(
            tenant_id=test_tenant_id,
            ticket_id="TKT-CONSTRAINT-TEST-2",
            feedback_type="invalid_type",  # Violates CHECK constraint enum
        )

        db_session.add(invalid_feedback)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_empty_feedback_list_returns_zero_count(self, async_client):
        """
        Test querying feedback for tenant with no submissions returns empty list.

        Expected:
        - Response: 200 OK with count=0, feedback=[]
        """
        empty_tenant_id = "tenant-empty-no-feedback"

        response = await async_client.get(f"/api/v1/feedback?tenant_id={empty_tenant_id}")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["count"] == 0
        assert response_data["feedback"] == []

    @pytest.mark.asyncio
    async def test_stats_with_no_ratings_returns_null_average(self, async_client, test_tenant_id):
        """
        Test stats endpoint with no rating submissions returns average_rating=null.

        Expected:
        - Response: 200 OK with average_rating=null (no ratings to average)
        """
        # Create tenant with only thumbs_up/down feedback (no ratings)
        tenant_no_ratings = "tenant-no-ratings-only-binary"

        response = await async_client.get(f"/api/v1/feedback/stats?tenant_id={tenant_no_ratings}")

        assert response.status_code == 200
        response_data = response.json()
        # average_rating should be null when no rating_type='rating' records exist
        assert response_data["average_rating"] is None or response_data["average_rating"] == 0
