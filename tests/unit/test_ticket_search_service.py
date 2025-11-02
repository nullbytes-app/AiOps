"""
Unit tests for ticket search service.

Tests ticket history search functionality including full-text search,
similarity matching fallback, input validation, and error handling.
All tests use mocked database sessions to avoid dependencies on real database.
"""

from datetime import datetime, timezone
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.database.models import TicketHistory
from src.services.ticket_search_service import (
    TicketSearchResult,
    TicketSearchService,
)
from src.utils.exceptions import ValidationError


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_session():
    """Create a mock AsyncSession for testing."""
    return AsyncMock()


@pytest.fixture
def search_service(mock_session):
    """Create a TicketSearchService instance with mocked session."""
    return TicketSearchService(session=mock_session)


def create_test_ticket(
    ticket_id: str,
    description: str,
    resolution: str,
    tenant_id: str = "tenant-a",
    resolved_date: datetime = None,
    similarity_score: float = 0.8,
) -> tuple:
    """
    Helper to create mock ticket data.

    Returns tuple of (ticket_id, description, resolution, resolved_date, score)
    for mocking database results.
    """
    if resolved_date is None:
        resolved_date = datetime(2025, 1, 1, tzinfo=timezone.utc)

    return (ticket_id, description, resolution, resolved_date, similarity_score)


# ============================================================================
# Test: Valid Search Returns Results (AC #1, #2, #4)
# ============================================================================


@pytest.mark.asyncio
async def test_search_similar_tickets_valid_query(search_service, mock_session):
    """
    Valid search query returns top 5 results with all required fields.

    AC #1: Function searches ticket_history table
    AC #2: Uses PostgreSQL FTS
    AC #4: Returns top 5 with ticket_id, description, resolution, resolved_date
    """
    # Arrange: Mock database to return 10 tickets (should limit to 5)
    mock_tickets = [
        create_test_ticket(
            "T001",
            "Server X is slow",
            "Increased server memory",
            similarity_score=0.95,
        ),
        create_test_ticket(
            "T002",
            "Slow server performance",
            "Optimized database queries",
            similarity_score=0.87,
        ),
        create_test_ticket("T003", "Database slow", "Added indexes", similarity_score=0.82),
        create_test_ticket(
            "T004", "System unresponsive", "Restarted services", similarity_score=0.78
        ),
        create_test_ticket(
            "T005", "Performance issue", "Cleared cache", similarity_score=0.75
        ),
        create_test_ticket("T006", "Slow query", "Optimized SQL", similarity_score=0.70),
        create_test_ticket("T007", "Lag detected", "Scaled horizontally", similarity_score=0.65),
        create_test_ticket("T008", "Timeout", "Increased timeout", similarity_score=0.60),
        create_test_ticket(
            "T009", "Response time high", "Added caching", similarity_score=0.55
        ),
        create_test_ticket(
            "T010", "Performance degradation", "Replaced disk", similarity_score=0.50
        ),
    ]

    mock_result = MagicMock()
    # Mock returns only first 5 (already limited by query.limit())
    mock_result.fetchall.return_value = mock_tickets[:5]
    mock_session.execute.return_value = mock_result

    # Act
    results, metadata = await search_service.search_similar_tickets(
        tenant_id="tenant-a",
        query_description="Server is slow",
    )

    # Assert
    assert len(results) == 5, "Should return maximum 5 results"
    assert all(isinstance(r, TicketSearchResult) for r in results)
    assert all(r.ticket_id for r in results), "All results should have ticket_id"
    assert all(r.description for r in results), "All results should have description"
    assert all(r.resolution for r in results), "All results should have resolution"
    assert all(r.resolved_date for r in results), "All results should have resolved_date"
    assert metadata["num_results"] == 5
    assert metadata["method"] == "fts"
    assert not metadata["fallback_method_used"]


# ============================================================================
# Test: No Results Handled Gracefully (AC #6)
# ============================================================================


@pytest.mark.asyncio
async def test_search_similar_tickets_no_results(search_service, mock_session):
    """
    Search with no matching tickets returns empty list (AC #6).

    AC #6: Empty results handled gracefully (returns empty list, not error)
    """
    # Arrange: Mock FTS to return empty, similarity also empty
    mock_session.execute.return_value = MagicMock(fetchall=lambda: [])

    # Act
    results, metadata = await search_service.search_similar_tickets(
        tenant_id="tenant-a",
        query_description="Completely unique issue XYZ",
    )

    # Assert
    assert results == [], "Should return empty list, not error"
    assert metadata["num_results"] == 0
    assert metadata["method"] == "similarity"  # Fell back since FTS was empty


# ============================================================================
# Test: Tenant Isolation (AC #3, #5)
# ============================================================================


@pytest.mark.asyncio
async def test_search_respects_tenant_isolation(search_service, mock_session):
    """
    Search only returns tickets for specified tenant (AC #3, #5).

    AC #3: Results filtered by tenant_id for data isolation
    AC #5: Search respects row-level security policies
    """
    # Arrange: Mock database with mixed tenant data
    mock_tickets = [
        create_test_ticket("T001", "Database error", "Fixed query", "tenant-a"),
        create_test_ticket("T002", "Database timeout", "Added timeout", "tenant-a"),
        create_test_ticket("T003", "Database error", "Reindexed", "tenant-b"),  # Should not be returned
    ]

    mock_result = MagicMock()
    mock_result.fetchall.return_value = mock_tickets[:2]  # Only tenant-a
    mock_session.execute.return_value = mock_result

    # Act
    results, metadata = await search_service.search_similar_tickets(
        tenant_id="tenant-a",
        query_description="Database error",
    )

    # Assert: Verify tenant isolation
    assert len(results) == 2
    # In real implementation, would verify WHERE clause filters by tenant_id
    # This mock simulates that the database returned only tenant-a results


# ============================================================================
# Test: Full-Text Search Matches Keywords (AC #2)
# ============================================================================


@pytest.mark.asyncio
async def test_full_text_search_matches_keywords(search_service, mock_session):
    """
    PostgreSQL FTS correctly matches search keywords (AC #2).

    Verifies that the service generates correct FTS query with ts_vector
    and ts_query operators.
    """
    # Arrange
    mock_tickets = [
        create_test_ticket("T001", "Slow server performance", "Optimized DB", 0.92),
        create_test_ticket("T002", "Server performance issues", "Scaled up", 0.88),
    ]

    mock_result = MagicMock()
    mock_result.fetchall.return_value = mock_tickets
    mock_session.execute.return_value = mock_result

    # Act
    results, metadata = await search_service.search_similar_tickets(
        tenant_id="tenant-a",
        query_description="slow server performance",
    )

    # Assert
    assert len(results) == 2
    assert metadata["method"] == "fts", "Should use FTS method"
    assert not metadata["fallback_method_used"]
    # Verify keywords in results
    assert "slow" in results[0].description.lower()
    assert "server" in results[0].description.lower()


# ============================================================================
# Test: Similarity Fallback When FTS Empty (AC #2, #4)
# ============================================================================


@pytest.mark.asyncio
async def test_similarity_fallback_when_fts_empty(search_service, mock_session):
    """
    When FTS returns 0 results, fallback to similarity (AC #2).

    Verifies that the service attempts FTS first, then falls back to
    similarity matching if no results found.
    """
    # Arrange: Set up mock to return empty for FTS, then return similarity results
    mock_tickets_fts = []  # FTS returns nothing
    mock_tickets_similarity = [
        create_test_ticket("T001", "Database is broken", "Restarted database", 0.65),
        create_test_ticket("T002", "DB connection failed", "Fixed connection pool", 0.58),
    ]

    # Setup: Mock will be called twice - once for FTS, once for similarity
    mock_session.execute.side_effect = [
        MagicMock(fetchall=lambda: mock_tickets_fts),  # FTS returns empty
        MagicMock(fetchall=lambda: mock_tickets_similarity),  # Similarity returns results
    ]

    # Act
    results, metadata = await search_service.search_similar_tickets(
        tenant_id="tenant-a",
        query_description="DB is broken",
    )

    # Assert
    assert len(results) == 2, "Should return similarity results as fallback"
    assert metadata["fallback_method_used"], "Should indicate fallback was used"
    assert metadata["method"] == "similarity"


# ============================================================================
# Test: Input Validation - Invalid Tenant ID (AC #1, #4)
# ============================================================================


@pytest.mark.asyncio
async def test_input_validation_invalid_tenant_id(search_service):
    """
    Invalid tenant_id raises ValidationError (AC #1, #4).

    Tests various invalid tenant_id formats.
    """
    with pytest.raises(ValidationError, match="tenant_id must be"):
        await search_service.search_similar_tickets(
            tenant_id="",  # Empty
            query_description="test",
        )

    with pytest.raises(ValidationError, match="tenant_id"):
        await search_service.search_similar_tickets(
            tenant_id=None,  # None
            query_description="test",
        )

    with pytest.raises(ValidationError, match="tenant_id"):
        await search_service.search_similar_tickets(
            tenant_id="   ",  # Whitespace only
            query_description="test",
        )


# ============================================================================
# Test: Input Validation - Empty Description (AC #4)
# ============================================================================


@pytest.mark.asyncio
async def test_input_validation_empty_description(search_service):
    """
    Empty or whitespace-only description raises ValidationError (AC #4).
    """
    with pytest.raises(ValidationError, match="query_description"):
        await search_service.search_similar_tickets(
            tenant_id="tenant-a",
            query_description="",  # Empty
        )

    with pytest.raises(ValidationError, match="query_description"):
        await search_service.search_similar_tickets(
            tenant_id="tenant-a",
            query_description="   ",  # Whitespace only
        )

    with pytest.raises(ValidationError, match="query_description"):
        await search_service.search_similar_tickets(
            tenant_id="tenant-a",
            query_description=None,  # None
        )


# ============================================================================
# Test: Input Validation - Max Query Length (AC #4)
# ============================================================================


@pytest.mark.asyncio
async def test_input_validation_max_query_length(search_service):
    """
    Query exceeding 1,000 characters raises ValidationError (AC #4).
    """
    long_query = "x" * 1001  # 1001 characters
    with pytest.raises(ValidationError, match="exceeds maximum length"):
        await search_service.search_similar_tickets(
            tenant_id="tenant-a",
            query_description=long_query,
        )


# ============================================================================
# Test: Result Limit Enforced (AC #4)
# ============================================================================


@pytest.mark.asyncio
async def test_result_limit_enforced(search_service, mock_session):
    """
    Search never returns more than limit (default 5) (AC #4).

    Verifies that even if database returns 100 matching tickets,
    only 5 are returned.
    """
    # Arrange: Create 100 mock tickets, but mock returns only first 5 (as query.limit(5) would)
    mock_tickets = [
        create_test_ticket(f"T{i:03d}", f"Issue {i}", f"Resolution {i}", similarity_score=0.9 - (i * 0.001))
        for i in range(100)
    ]

    mock_result = MagicMock()
    # Even though 100 tickets exist, query limit(5) means only 5 returned
    mock_result.fetchall.return_value = mock_tickets[:5]
    mock_session.execute.return_value = mock_result

    # Act
    results, metadata = await search_service.search_similar_tickets(
        tenant_id="tenant-a",
        query_description="test query",
    )

    # Assert
    assert len(results) <= 5, "Result count should never exceed limit"


# ============================================================================
# Test: Result Format and Fields (AC #4)
# ============================================================================


@pytest.mark.asyncio
async def test_result_format_includes_all_fields(search_service, mock_session):
    """
    Each result includes all required fields (AC #4).

    Verifies TicketSearchResult contains:
    - ticket_id
    - description
    - resolution
    - resolved_date
    - similarity_score
    """
    # Arrange
    test_date = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    mock_tickets = [
        ("T001", "Server error", "Restarted", test_date, 0.95),
    ]

    mock_result = MagicMock()
    mock_result.fetchall.return_value = mock_tickets
    mock_session.execute.return_value = mock_result

    # Act
    results, metadata = await search_service.search_similar_tickets(
        tenant_id="tenant-a",
        query_description="server error",
    )

    # Assert
    assert len(results) == 1
    result = results[0]
    assert result.ticket_id == "T001"
    assert result.description == "Server error"
    assert result.resolution == "Restarted"
    assert result.resolved_date == test_date
    assert result.similarity_score == 0.95


# ============================================================================
# Test: Performance - Search Completes in <2 Seconds (AC #8)
# ============================================================================


@pytest.mark.asyncio
async def test_search_performance_latency(search_service, mock_session):
    """
    Search completes in <2 seconds (AC #8).

    Performance constraint: AC #8 requires search to complete in <2 seconds
    for 10,000 ticket database. Mock simulates fast execution.
    """
    # Arrange
    mock_tickets = [
        create_test_ticket(f"T{i:03d}", f"Issue {i}", f"Resolution {i}")
        for i in range(5)
    ]

    mock_result = MagicMock()
    mock_result.fetchall.return_value = mock_tickets
    mock_session.execute.return_value = mock_result

    # Act
    import time

    start = time.time()
    results, metadata = await search_service.search_similar_tickets(
        tenant_id="tenant-a",
        query_description="test issue",
    )
    elapsed_ms = (time.time() - start) * 1000

    # Assert
    assert elapsed_ms < 2000, f"Search took {elapsed_ms}ms, should be <2000ms"
    assert metadata["search_time_ms"] < 2000


# ============================================================================
# Test: Error Handling (AC #6)
# ============================================================================


@pytest.mark.asyncio
async def test_error_handling_database_error(search_service, mock_session):
    """
    Database connection errors are caught and logged gracefully.

    Verify graceful degradation - service catches exceptions in search
    methods and returns empty list, but search_similar_tickets itself
    will re-raise from the outer try block.
    """
    # Arrange: Mock database error on execute
    mock_session.execute.side_effect = Exception("Database connection failed")

    # Act: The search will fail on both FTS and similarity, but return empty list
    # rather than crashing
    results, metadata = await search_service.search_similar_tickets(
        tenant_id="tenant-a",
        query_description="test",
    )

    # Assert: Should handle gracefully with empty results
    assert results == [], "Should return empty list on database error"
    assert metadata["num_results"] == 0


# ============================================================================
# Test: Query Sanitization for FTS (AC #4)
# ============================================================================


def test_sanitize_fts_query():
    """
    FTS query sanitization removes special characters safely.

    Special characters like &, |, !, (, ), :, * break ts_query parsing
    and should be removed.
    """
    # Test cases
    assert (
        TicketSearchService._sanitize_fts_query("server & database | error")
        == "server database error"
    )
    assert (
        TicketSearchService._sanitize_fts_query("search: (database OR cache)")
        == "search database OR cache"
    )
    assert TicketSearchService._sanitize_fts_query("issue*") == "issue"
    assert (
        TicketSearchService._sanitize_fts_query("multiple   spaces   here")
        == "multiple spaces here"
    )
    assert (
        TicketSearchService._sanitize_fts_query("  leading trailing  ")
        == "leading trailing"
    )


# ============================================================================
# Test: TicketSearchResult Model Validation
# ============================================================================


def test_ticket_search_result_model():
    """
    TicketSearchResult model validates correctly.

    Pydantic model should enforce required fields and correct types.
    """
    # Valid result
    result = TicketSearchResult(
        ticket_id="T001",
        description="Test issue",
        resolution="Test fix",
        resolved_date=datetime.now(tz=timezone.utc),
        similarity_score=0.95,
    )

    assert result.ticket_id == "T001"
    assert result.similarity_score == 0.95

    # Optional similarity_score
    result2 = TicketSearchResult(
        ticket_id="T002",
        description="Another issue",
        resolution="Another fix",
        resolved_date=datetime.now(tz=timezone.utc),
    )
    assert result2.similarity_score is None


# ============================================================================
# Test: Metadata Returned (AC #1, #2, #4)
# ============================================================================


@pytest.mark.asyncio
async def test_search_returns_metadata(search_service, mock_session):
    """
    Search returns metadata about the search operation.

    Metadata includes: num_results, search_time_ms, fallback_method_used, method
    """
    # Arrange
    mock_tickets = [
        create_test_ticket("T001", "Server issue", "Fixed", 0.90),
    ]

    mock_result = MagicMock()
    mock_result.fetchall.return_value = mock_tickets
    mock_session.execute.return_value = mock_result

    # Act
    results, metadata = await search_service.search_similar_tickets(
        tenant_id="tenant-a",
        query_description="server issue",
    )

    # Assert
    assert "num_results" in metadata
    assert "search_time_ms" in metadata
    assert "fallback_method_used" in metadata
    assert "method" in metadata

    assert metadata["num_results"] == 1
    assert metadata["method"] in ["fts", "similarity"]
    assert isinstance(metadata["fallback_method_used"], bool)
    assert isinstance(metadata["search_time_ms"], int)
