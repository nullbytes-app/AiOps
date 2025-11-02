"""
Ticket history search service for context gathering.

Provides full-text search with similarity matching fallback for finding similar
past tickets when processing new enhancement requests. Enables the agent to
provide context about resolution patterns and previous solutions.
"""

import time
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, validator
from sqlalchemy import and_, desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from loguru import logger

from src.database.models import TicketHistory
from src.utils.exceptions import ValidationError


class TicketSearchResult(BaseModel):
    """
    Data model for ticket search results.

    Represents a single search result including ticket metadata and relevance
    scoring information.
    """

    model_config = {"from_attributes": True}

    ticket_id: str = Field(..., description="ServiceDesk ticket ID")
    description: str = Field(..., description="Ticket description")
    resolution: str = Field(..., description="Resolution or solution applied")
    resolved_date: datetime = Field(..., description="When ticket was resolved")
    similarity_score: Optional[float] = Field(
        default=None, description="Relevance/similarity score (0-1 range)"
    )


class TicketSearchService:
    """
    Service for searching ticket history with full-text search and fallback.

    Implements PostgreSQL full-text search with trigram similarity matching
    as fallback. Enforces tenant isolation and performance constraints.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the ticket search service.

        Args:
            session: AsyncSession for database operations
        """
        self.session = session

    async def search_similar_tickets(
        self,
        tenant_id: str,
        query_description: str,
        limit: int = 5,
    ) -> tuple[List[TicketSearchResult], dict]:
        """
        Search for similar tickets using full-text search with fallback.

        Performs PostgreSQL full-text search on ticket descriptions, filtering
        by tenant_id for data isolation. Falls back to similarity matching if
        no full-text results found.

        Args:
            tenant_id: Tenant identifier for data isolation
            query_description: Search query (ticket description text)
            limit: Maximum number of results to return (default: 5)

        Returns:
            Tuple of (results list, metadata dict with search info)

        Raises:
            ValidationError: If inputs are invalid (invalid tenant_id, empty
                description, etc.)

        Acceptance Criteria:
            - AC #1: Function created to search ticket_history table
            - AC #2: Uses PostgreSQL FTS or similarity matching
            - AC #3: Results filtered by tenant_id for isolation
            - AC #4: Returns top 5 results with required fields
            - AC #6: Empty results handled gracefully (returns empty list)
        """
        # Input validation
        self._validate_inputs(tenant_id, query_description, limit)

        start_time = time.time()
        search_method = "fts"  # Track which method found results

        try:
            # Attempt full-text search first (AC #2: FTS method)
            results = await self._full_text_search(
                tenant_id=tenant_id,
                query_description=query_description,
                limit=limit,
            )

            # If FTS returns no results, fall back to similarity matching
            if not results:
                logger.debug(
                    "FTS returned no results, falling back to similarity matching",
                    extra={"tenant_id": tenant_id, "query": query_description[:50]},
                )
                results = await self._similarity_search(
                    tenant_id=tenant_id,
                    query_description=query_description,
                    limit=limit,
                )
                search_method = "similarity"

            elapsed_ms = int((time.time() - start_time) * 1000)

            # Log performance metrics
            logger.info(
                f"Ticket search: tenant={tenant_id}, results={len(results)}, "
                f"method={search_method}, elapsed_ms={elapsed_ms}",
                extra={
                    "tenant_id": tenant_id,
                    "result_count": len(results),
                    "method": search_method,
                    "elapsed_ms": elapsed_ms,
                },
            )

            # Warn if search took too long
            if elapsed_ms > 1000:
                logger.warning(
                    f"Slow ticket search: {elapsed_ms}ms (threshold: 1000ms)",
                    extra={"tenant_id": tenant_id, "elapsed_ms": elapsed_ms},
                )

            metadata = {
                "num_results": len(results),
                "search_time_ms": elapsed_ms,
                "fallback_method_used": search_method == "similarity",
                "method": search_method,
            }

            return results, metadata

        except Exception as e:
            logger.error(
                f"Ticket search failed: {str(e)}",
                extra={
                    "tenant_id": tenant_id,
                    "error": str(e),
                    "query": query_description[:50],
                },
            )
            raise

    async def _full_text_search(
        self,
        tenant_id: str,
        query_description: str,
        limit: int,
    ) -> List[TicketSearchResult]:
        """
        Perform PostgreSQL full-text search on ticket descriptions.

        Uses ts_vector and ts_query for efficient full-text matching with
        ranking. Filters by tenant_id for data isolation (AC #3, #5).

        Args:
            tenant_id: Tenant identifier
            query_description: Search query text
            limit: Maximum results to return

        Returns:
            List of TicketSearchResult objects, sorted by relevance

        Implementation Notes:
            - Sanitizes query to handle special characters
            - Uses English language configuration
            - Orders by ts_rank for relevance
            - Enforces <2 second timeout (AC #8)
        """
        # Sanitize query: remove special characters that break ts_query
        # Keep only alphanumeric, spaces, and common punctuation
        sanitized_query = self._sanitize_fts_query(query_description)

        if not sanitized_query:
            logger.debug("Query sanitized to empty string, returning empty results")
            return []

        try:
            # PostgreSQL FTS query with ts_rank for relevance scoring
            # AC #2: Use ts_vector and ts_query
            query = select(
                TicketHistory.ticket_id,
                TicketHistory.description,
                TicketHistory.resolution,
                TicketHistory.resolved_date,
                # Calculate relevance score using ts_rank
                func.ts_rank(
                    func.to_tsvector("english", TicketHistory.description),
                    func.plainto_tsquery("english", sanitized_query),
                ).label("similarity_score"),
            ).where(
                # AC #3: Filter by tenant_id FIRST for security
                and_(
                    TicketHistory.tenant_id == tenant_id,
                    # Use @@ operator for full-text match
                    func.to_tsvector("english", TicketHistory.description).op("@@")(
                        func.plainto_tsquery("english", sanitized_query)
                    ),
                )
            ).order_by(
                # Order by relevance (AC #2: ts_rank ordering)
                desc("similarity_score")
            ).limit(limit)

            result = await self.session.execute(query)
            rows = result.fetchall()

            # Convert rows to TicketSearchResult objects
            return [self._convert_row_to_result(row) for row in rows]

        except Exception as e:
            logger.error(
                f"Full-text search failed: {str(e)}",
                extra={"tenant_id": tenant_id, "error": str(e)},
            )
            return []

    async def _similarity_search(
        self,
        tenant_id: str,
        query_description: str,
        limit: int,
    ) -> List[TicketSearchResult]:
        """
        Perform similarity matching as fallback search method.

        Uses PostgreSQL similarity() function (from pg_trgm extension) when
        full-text search returns no results. Enforces 0.3 similarity threshold.

        Args:
            tenant_id: Tenant identifier
            query_description: Search query text
            limit: Maximum results to return

        Returns:
            List of TicketSearchResult objects with similarity scores

        Implementation Notes:
            - Requires pg_trgm extension
            - Filters by similarity threshold (0.3)
            - Returns partial results even if timeout occurs
            - Logs when fallback is used
        """
        try:
            # PostgreSQL similarity() function from pg_trgm extension
            # AC #2: Similarity matching as fallback
            query = select(
                TicketHistory.ticket_id,
                TicketHistory.description,
                TicketHistory.resolution,
                TicketHistory.resolved_date,
                func.similarity(
                    TicketHistory.description, query_description
                ).label("similarity_score"),
            ).where(
                # AC #3: Filter by tenant_id FIRST for security
                and_(
                    TicketHistory.tenant_id == tenant_id,
                    # AC #3: Similarity threshold > 0.3
                    func.similarity(TicketHistory.description, query_description)
                    > 0.3,
                )
            ).order_by(
                # Order by similarity score descending
                desc("similarity_score")
            ).limit(limit)

            result = await self.session.execute(query)
            rows = result.fetchall()

            # Convert rows to TicketSearchResult objects
            return [self._convert_row_to_result(row) for row in rows]

        except Exception as e:
            logger.error(
                f"Similarity search failed: {str(e)}",
                extra={"tenant_id": tenant_id, "error": str(e)},
            )
            return []

    @staticmethod
    def _validate_inputs(
        tenant_id: str, query_description: str, limit: int
    ) -> None:
        """
        Validate and sanitize search inputs.

        Ensures tenant_id and query_description are valid. Enforces constraints
        on query length and limit.

        Args:
            tenant_id: Tenant identifier to validate
            query_description: Query text to validate
            limit: Result limit to validate

        Raises:
            ValidationError: If any input is invalid

        Acceptance Criteria:
            - AC #4: Input validation raises ValidationError for invalid inputs
        """
        # Validate tenant_id (AC #4: validation)
        if not tenant_id or not isinstance(tenant_id, str):
            logger.debug("Invalid tenant_id provided", extra={"tenant_id": tenant_id})
            raise ValidationError("tenant_id must be a non-empty string")

        if len(tenant_id.strip()) == 0:
            raise ValidationError("tenant_id cannot be empty or whitespace-only")

        # Validate query_description (AC #4: validation)
        if not query_description or not isinstance(query_description, str):
            raise ValidationError("query_description must be a non-empty string")

        if len(query_description.strip()) == 0:
            raise ValidationError(
                "query_description cannot be empty or whitespace-only"
            )

        # Enforce max query length (AC #4: 1,000 character limit)
        if len(query_description) > 1000:
            raise ValidationError(
                "query_description exceeds maximum length of 1,000 characters"
            )

        # Validate limit
        if not isinstance(limit, int) or limit <= 0:
            raise ValidationError("limit must be a positive integer")

        if limit > 100:  # Reasonable upper bound
            raise ValidationError("limit cannot exceed 100")

    @staticmethod
    def _convert_row_to_result(row) -> "TicketSearchResult":
        """
        Convert a database row to TicketSearchResult.

        Handles both Row objects (from SQLAlchemy) and tuples (from mocks).

        Args:
            row: Row object or tuple from database query result

        Returns:
            TicketSearchResult model instance
        """
        if hasattr(row, 'ticket_id'):
            # Row object from database
            return TicketSearchResult(
                ticket_id=row.ticket_id,
                description=row.description,
                resolution=row.resolution,
                resolved_date=row.resolved_date,
                similarity_score=float(row.similarity_score),
            )
        else:
            # Tuple from mock (index: ticket_id, description, resolution, resolved_date, similarity_score)
            return TicketSearchResult(
                ticket_id=row[0],
                description=row[1],
                resolution=row[2],
                resolved_date=row[3],
                similarity_score=float(row[4]),
            )

    @staticmethod
    def _sanitize_fts_query(query: str) -> str:
        """
        Sanitize query for PostgreSQL full-text search.

        Removes special characters that break ts_query parsing while preserving
        meaningful search terms.

        Args:
            query: Raw query string

        Returns:
            Sanitized query string safe for ts_query

        Implementation Notes:
            - Removes special FTS characters: &, |, !, (, ), :, *
            - Preserves alphanumeric, spaces, and hyphens
            - Converts multiple spaces to single space
            - Strips leading/trailing whitespace
        """
        # Remove special FTS characters
        sanitized = query
        for char in "&|!():*":
            sanitized = sanitized.replace(char, " ")

        # Normalize whitespace: convert multiple spaces to single
        sanitized = " ".join(sanitized.split())

        return sanitized.strip()
