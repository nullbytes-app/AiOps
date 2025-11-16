"""
Integration tests for import_tickets script.

Tests the full import pipeline with real database and mocked API.
Covers:
- End-to-end import workflow
- Database persistence and constraint handling
- Performance benchmarking
- Idempotency

KNOWN ISSUE (Story 12.1): These tests fail with SQLAlchemy MissingGreenlet error.
Root cause: async database session fixture incompatibility.
Temporarily skipped pending fixture refactoring (tracked in test-audit-report).
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import sys
from pathlib import Path

# Tests re-enabled in Story 12.2 after async fixture refactoring
# Uses async_session_maker from database.session for proper async support
pytestmark = pytest.mark.anyio  # Enable proper async/await support

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.import_tickets import (
    import_tickets,
    extract_ticket_data,
)
from src.database.models import TicketHistory
from src.database.session import async_session_maker
from sqlalchemy import select, delete


@pytest.fixture(scope="function")
async def test_database_session():
    """Provide clean database session for each test."""
    # Create session
    async with async_session_maker() as session:
        yield session
        # Cleanup: delete all test data
        await session.execute(delete(TicketHistory))
        await session.commit()


class TestEndToEndImport:
    """Test complete import workflow."""

    @pytest.mark.asyncio
    async def test_import_small_batch(self, test_database_session):
        """Test importing a small batch of 10 tickets."""
        tenant_id = "test-e2e-1"
        base_url = "http://test.api"
        api_key = "test-key"

        # Mock API response
        mock_tickets = [
            {
                "id": str(i),
                "subject": f"Ticket {i}",
                "description": f"Description {i}",
                "resolution": {"content": f"Resolution {i}"},
                "resolved_time": {
                    "value": int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
                },
                "tags": [{"name": f"tag-{i}"}],
            }
            for i in range(1, 11)
        ]

        # Mock the fetch function to return our test data
        async def mock_fetch_page(*args, **kwargs):
            return mock_tickets, False  # has_more_rows=False

        with patch("scripts.import_tickets.fetch_tickets_page", side_effect=mock_fetch_page):
            with patch("scripts.import_tickets.async_session_maker") as mock_session_maker:
                # Setup mock session
                mock_session_maker.return_value.__aenter__.return_value = test_database_session
                mock_session_maker.return_value.__aexit__.return_value = None

                # Mock tenant config fetch
                with patch("scripts.import_tickets.fetch_tenant_config") as mock_config:
                    mock_config.return_value = (base_url, api_key)

                    # Run import
                    result = await import_tickets(
                        tenant_id,
                        base_url,
                        api_key,
                        datetime.now() - timedelta(days=90),
                        datetime.now(),
                    )

        # Import should succeed
        assert result == 0

        # Verify tickets in database
        query = select(TicketHistory).filter_by(tenant_id=tenant_id)
        results = await test_database_session.execute(query)
        tickets_in_db = results.scalars().all()

        assert len(tickets_in_db) == 10
        assert all(t.source == "bulk_import" for t in tickets_in_db)
        assert all(t.tenant_id == tenant_id for t in tickets_in_db)

    @pytest.mark.asyncio
    async def test_import_pagination(self, test_database_session):
        """Test importing across multiple pages."""
        tenant_id = "test-pagination"
        base_url = "http://test.api"
        api_key = "test-key"

        # First page: 100 tickets
        page1_tickets = [
            {
                "id": str(i),
                "subject": f"Ticket {i}",
                "description": f"Description {i}",
                "resolution": {"content": f"Fixed"},
                "resolved_time": {
                    "value": int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
                },
                "tags": [],
            }
            for i in range(1, 101)
        ]

        # Second page: 50 tickets
        page2_tickets = [
            {
                "id": str(i),
                "subject": f"Ticket {i}",
                "description": f"Description {i}",
                "resolution": {"content": f"Fixed"},
                "resolved_time": {
                    "value": int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
                },
                "tags": [],
            }
            for i in range(101, 151)
        ]

        # Mock fetch to return pages in sequence
        call_count = 0

        async def mock_fetch_page(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return page1_tickets, True  # has_more_rows=True
            else:
                return page2_tickets, False  # has_more_rows=False

        with patch("scripts.import_tickets.fetch_tickets_page", side_effect=mock_fetch_page):
            with patch("scripts.import_tickets.async_session_maker") as mock_session_maker:
                mock_session_maker.return_value.__aenter__.return_value = test_database_session
                mock_session_maker.return_value.__aexit__.return_value = None

                with patch("scripts.import_tickets.fetch_tenant_config") as mock_config:
                    mock_config.return_value = (base_url, api_key)

                    result = await import_tickets(
                        tenant_id,
                        base_url,
                        api_key,
                        datetime.now() - timedelta(days=90),
                        datetime.now(),
                    )

        assert result == 0

        # Verify all 150 tickets in database
        query = select(TicketHistory).filter_by(tenant_id=tenant_id)
        results = await test_database_session.execute(query)
        tickets_in_db = results.scalars().all()

        assert len(tickets_in_db) == 150

    @pytest.mark.asyncio
    async def test_import_with_duplicates(self, test_database_session):
        """Test duplicate handling with UNIQUE constraint."""
        tenant_id = "test-duplicates"
        base_url = "http://test.api"
        api_key = "test-key"

        # Create 10 unique tickets
        unique_tickets = [
            {
                "id": str(i),
                "subject": f"Ticket {i}",
                "description": f"Description {i}",
                "resolution": {"content": f"Fixed"},
                "resolved_time": {
                    "value": int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
                },
                "tags": [],
            }
            for i in range(1, 11)
        ]

        # Mock fetch for first import
        async def mock_fetch_page_first_run(*args, **kwargs):
            return unique_tickets, False

        with patch(
            "scripts.import_tickets.fetch_tickets_page", side_effect=mock_fetch_page_first_run
        ):
            with patch("scripts.import_tickets.async_session_maker") as mock_session_maker:
                mock_session_maker.return_value.__aenter__.return_value = test_database_session
                mock_session_maker.return_value.__aexit__.return_value = None

                with patch("scripts.import_tickets.fetch_tenant_config") as mock_config:
                    mock_config.return_value = (base_url, api_key)

                    # First import
                    result = await import_tickets(
                        tenant_id,
                        base_url,
                        api_key,
                        datetime.now() - timedelta(days=90),
                        datetime.now(),
                    )

        assert result == 0

        # Verify first import
        query = select(TicketHistory).filter_by(tenant_id=tenant_id)
        results = await test_database_session.execute(query)
        tickets_after_first = results.scalars().all()
        assert len(tickets_after_first) == 10

        # Run import again with same data (duplicates)
        async def mock_fetch_page_second_run(*args, **kwargs):
            return unique_tickets, False

        with patch(
            "scripts.import_tickets.fetch_tickets_page", side_effect=mock_fetch_page_second_run
        ):
            with patch("scripts.import_tickets.async_session_maker") as mock_session_maker:
                mock_session_maker.return_value.__aenter__.return_value = test_database_session
                mock_session_maker.return_value.__aexit__.return_value = None

                with patch("scripts.import_tickets.fetch_tenant_config") as mock_config:
                    mock_config.return_value = (base_url, api_key)

                    # Second import (should skip all as duplicates)
                    result = await import_tickets(
                        tenant_id,
                        base_url,
                        api_key,
                        datetime.now() - timedelta(days=90),
                        datetime.now(),
                    )

        assert result == 0

        # Verify idempotency: still only 10 tickets (no duplicates inserted)
        results = await test_database_session.execute(query)
        tickets_after_second = results.scalars().all()
        assert len(tickets_after_second) == 10  # No new tickets from second import

    @pytest.mark.asyncio
    async def test_import_with_invalid_data(self, test_database_session):
        """Test handling of invalid/incomplete ticket data."""
        tenant_id = "test-invalid"
        base_url = "http://test.api"
        api_key = "test-key"

        # Mix of valid and invalid tickets
        mixed_tickets = [
            {  # Valid
                "id": "1",
                "subject": "Valid ticket",
                "description": "Has all required fields",
                "resolution": {"content": "Fixed"},
                "resolved_time": {
                    "value": int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
                },
                "tags": [],
            },
            {  # Invalid: missing resolved_time
                "id": "2",
                "subject": "Missing resolved_time",
                "description": "Should be skipped",
                "resolution": {"content": "In progress"},
                "tags": [],
            },
            {  # Invalid: missing description
                "id": "3",
                "subject": "",
                "description": "",
                "resolution": {"content": "Fixed"},
                "resolved_time": {
                    "value": int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
                },
                "tags": [],
            },
            {  # Valid
                "id": "4",
                "subject": "Another valid",
                "description": "Complete data",
                "resolution": {"content": "Resolved"},
                "resolved_time": {
                    "value": int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
                },
                "tags": [],
            },
        ]

        async def mock_fetch_page(*args, **kwargs):
            return mixed_tickets, False

        with patch("scripts.import_tickets.fetch_tickets_page", side_effect=mock_fetch_page):
            with patch("scripts.import_tickets.async_session_maker") as mock_session_maker:
                mock_session_maker.return_value.__aenter__.return_value = test_database_session
                mock_session_maker.return_value.__aexit__.return_value = None

                with patch("scripts.import_tickets.fetch_tenant_config") as mock_config:
                    mock_config.return_value = (base_url, api_key)

                    result = await import_tickets(
                        tenant_id,
                        base_url,
                        api_key,
                        datetime.now() - timedelta(days=90),
                        datetime.now(),
                    )

        assert result == 0

        # Verify only valid tickets inserted (2 out of 4)
        query = select(TicketHistory).filter_by(tenant_id=tenant_id)
        results = await test_database_session.execute(query)
        tickets_in_db = results.scalars().all()

        assert len(tickets_in_db) == 2
        ticket_ids = {t.ticket_id for t in tickets_in_db}
        assert "1" in ticket_ids
        assert "4" in ticket_ids
        assert "2" not in ticket_ids  # Invalid
        assert "3" not in ticket_ids  # Invalid

    @pytest.mark.asyncio
    async def test_import_performance(self, test_database_session):
        """Test import performance (100 tickets should complete in <60s)."""
        tenant_id = "test-performance"
        base_url = "http://test.api"
        api_key = "test-key"

        # Generate 100 test tickets
        test_tickets = [
            {
                "id": str(i),
                "subject": f"Ticket {i}",
                "description": f"Performance test ticket {i}",
                "resolution": {"content": f"Fixed"},
                "resolved_time": {
                    "value": int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
                },
                "tags": [{"name": f"perf-{i % 5}"}],
            }
            for i in range(1, 101)
        ]

        async def mock_fetch_page(*args, **kwargs):
            return test_tickets, False

        start_time = datetime.now()

        with patch("scripts.import_tickets.fetch_tickets_page", side_effect=mock_fetch_page):
            with patch("scripts.import_tickets.async_session_maker") as mock_session_maker:
                mock_session_maker.return_value.__aenter__.return_value = test_database_session
                mock_session_maker.return_value.__aexit__.return_value = None

                with patch("scripts.import_tickets.fetch_tenant_config") as mock_config:
                    mock_config.return_value = (base_url, api_key)

                    with patch("asyncio.sleep", new_callable=AsyncMock):  # Skip actual sleep
                        result = await import_tickets(
                            tenant_id,
                            base_url,
                            api_key,
                            datetime.now() - timedelta(days=90),
                            datetime.now(),
                        )

        elapsed = (datetime.now() - start_time).total_seconds()

        assert result == 0
        assert elapsed < 60  # Target: 100 tickets in <60s

        # Verify all tickets inserted
        query = select(TicketHistory).filter_by(tenant_id=tenant_id)
        results = await test_database_session.execute(query)
        tickets_in_db = results.scalars().all()
        assert len(tickets_in_db) == 100


class TestDatabaseConstraints:
    """Test database constraints and isolation."""

    @pytest.mark.asyncio
    async def test_unique_constraint_enforced(self, test_database_session):
        """Test that UNIQUE(tenant_id, ticket_id) constraint is enforced."""
        # Insert first ticket
        ticket1 = TicketHistory(
            tenant_id="test-constraint",
            ticket_id="123",
            description="First entry",
            resolution="Fixed",
            resolved_date=datetime.now(),
            source="bulk_import",
        )
        test_database_session.add(ticket1)
        await test_database_session.commit()

        # Try to insert duplicate
        ticket2 = TicketHistory(
            tenant_id="test-constraint",
            ticket_id="123",  # Same tenant and ticket ID
            description="Duplicate entry",
            resolution="Fixed",
            resolved_date=datetime.now(),
            source="bulk_import",
        )
        test_database_session.add(ticket2)

        # Should raise IntegrityError
        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            await test_database_session.commit()

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, test_database_session):
        """Test that data is properly isolated by tenant_id."""
        # Insert tickets for different tenants
        for tenant in ["tenant1", "tenant2", "tenant3"]:
            for i in range(1, 6):
                ticket = TicketHistory(
                    tenant_id=tenant,
                    ticket_id=str(i),
                    description=f"Ticket {i} for {tenant}",
                    resolution="Fixed",
                    resolved_date=datetime.now(),
                    source="bulk_import",
                )
                test_database_session.add(ticket)

        await test_database_session.commit()

        # Query tickets for tenant1 only
        query = select(TicketHistory).filter_by(tenant_id="tenant1")
        results = await test_database_session.execute(query)
        tenant1_tickets = results.scalars().all()

        assert len(tenant1_tickets) == 5
        assert all(t.tenant_id == "tenant1" for t in tenant1_tickets)

        # Verify tenant2 tickets are separate
        query = select(TicketHistory).filter_by(tenant_id="tenant2")
        results = await test_database_session.execute(query)
        tenant2_tickets = results.scalars().all()

        assert len(tenant2_tickets) == 5
        assert all(t.tenant_id == "tenant2" for t in tenant2_tickets)

    @pytest.mark.asyncio
    async def test_source_field_tracking(self, test_database_session):
        """Test that source field correctly tracks data provenance."""
        ticket = TicketHistory(
            tenant_id="test-source",
            ticket_id="123",
            description="Test ticket",
            resolution="Fixed",
            resolved_date=datetime.now(),
            source="bulk_import",
        )
        test_database_session.add(ticket)
        await test_database_session.commit()

        query = select(TicketHistory).filter_by(ticket_id="123")
        results = await test_database_session.execute(query)
        retrieved = results.scalar_one()

        assert retrieved.source == "bulk_import"
        assert retrieved.ingested_at is not None
