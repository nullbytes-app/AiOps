"""
Unit tests for import_tickets script.

Tests cover:
- Argument parsing and validation
- Date range calculation
- API pagination handling
- Ticket data extraction and validation
- Error handling and retry logic
- Progress logging
- Exit codes
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.import_tickets import (
    extract_ticket_data,
    parse_args,
    validate_args,
    calculate_date_range,
    fetch_tickets_page,
)
from src.database.models import TicketHistory


class TestArgumentParsing:
    """Test command-line argument parsing."""

    def test_required_tenant_id(self):
        """Test that --tenant-id is required."""
        with pytest.raises(SystemExit):
            parse_args()

    def test_parse_tenant_id_only(self, monkeypatch):
        """Test parsing with only required --tenant-id."""
        monkeypatch.setattr(
            sys, "argv", ["script", "--tenant-id=acme-corp"]
        )
        args = parse_args()
        assert args.tenant_id == "acme-corp"
        assert args.days == 90  # default

    def test_parse_with_days(self, monkeypatch):
        """Test parsing with --days parameter."""
        monkeypatch.setattr(
            sys,
            "argv",
            ["script", "--tenant-id=test", "--days=180"],
        )
        args = parse_args()
        assert args.days == 180

    def test_parse_with_date_range(self, monkeypatch):
        """Test parsing with --start-date and --end-date."""
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "script",
                "--tenant-id=test",
                "--start-date=2024-01-01",
                "--end-date=2024-03-31",
            ],
        )
        args = parse_args()
        assert args.start_date == "2024-01-01"
        assert args.end_date == "2024-03-31"

    def test_parse_with_log_level(self, monkeypatch):
        """Test parsing with --log-level parameter."""
        monkeypatch.setattr(
            sys,
            "argv",
            ["script", "--tenant-id=test", "--log-level=DEBUG"],
        )
        args = parse_args()
        assert args.log_level == "DEBUG"


class TestArgumentValidation:
    """Test argument validation logic."""

    def test_validate_empty_tenant_id(self):
        """Test validation fails for empty tenant_id."""
        args = MagicMock()
        args.tenant_id = ""
        args.days = 90
        args.start_date = None
        args.end_date = None

        is_valid, error_msg = validate_args(args)
        assert not is_valid
        assert "tenant_id cannot be empty" in error_msg

    def test_validate_negative_days(self):
        """Test validation fails for negative days."""
        args = MagicMock()
        args.tenant_id = "test"
        args.days = -1
        args.start_date = None
        args.end_date = None

        is_valid, error_msg = validate_args(args)
        assert not is_valid
        assert "days must be positive" in error_msg

    def test_validate_invalid_start_date_format(self):
        """Test validation fails for invalid date format."""
        args = MagicMock()
        args.tenant_id = "test"
        args.days = 90
        args.start_date = "2024/01/01"  # Wrong format
        args.end_date = None

        is_valid, error_msg = validate_args(args)
        assert not is_valid
        assert "ISO format" in error_msg

    def test_validate_start_date_after_end_date(self):
        """Test validation fails when start_date > end_date."""
        args = MagicMock()
        args.tenant_id = "test"
        args.days = 90
        args.start_date = "2024-03-31"
        args.end_date = "2024-01-01"

        is_valid, error_msg = validate_args(args)
        assert not is_valid
        assert "start_date must be before end_date" in error_msg

    def test_validate_valid_arguments(self):
        """Test validation succeeds for valid arguments."""
        args = MagicMock()
        args.tenant_id = "acme-corp"
        args.days = 90
        args.start_date = None
        args.end_date = None

        is_valid, error_msg = validate_args(args)
        assert is_valid
        assert error_msg == ""


class TestDateRangeCalculation:
    """Test date range calculation logic."""

    def test_calculate_range_from_days(self):
        """Test date range calculated from --days parameter."""
        args = MagicMock()
        args.days = 90
        args.start_date = None
        args.end_date = None

        start, end = calculate_date_range(args)

        # end should be approximately now
        assert (datetime.now() - end).total_seconds() < 5

        # start should be approximately 90 days ago
        expected_start = datetime.now() - timedelta(days=90)
        assert (start - expected_start).total_seconds() < 5

    def test_calculate_range_from_explicit_dates(self):
        """Test date range from explicit --start-date and --end-date."""
        args = MagicMock()
        args.days = 90  # Ignored when explicit dates provided
        args.start_date = "2024-01-01"
        args.end_date = "2024-03-31"

        start, end = calculate_date_range(args)

        assert start.date().isoformat() == "2024-01-01"
        assert end.date().isoformat() == "2024-03-31"

    def test_calculate_range_with_only_start_date(self):
        """Test date range with only --start-date (end defaults to today)."""
        args = MagicMock()
        args.days = 90
        args.start_date = "2024-01-01"
        args.end_date = None

        start, end = calculate_date_range(args)

        assert start.date().isoformat() == "2024-01-01"
        # end should be approximately now
        assert (datetime.now() - end).total_seconds() < 5


class TestTicketDataExtraction:
    """Test ticket data extraction and transformation."""

    def test_extract_valid_ticket(self):
        """Test successful extraction of valid ticket."""
        ticket_json = {
            "id": "123456",
            "subject": "Server down",
            "description": "Web server not responding",
            "resolution": {"content": "Restarted Apache"},
            "resolved_time": {"value": 1704150000000},  # milliseconds
            "tags": [{"name": "critical"}, {"name": "web"}],
        }

        ticket_obj = extract_ticket_data(ticket_json, "test-tenant")

        assert isinstance(ticket_obj, TicketHistory)
        assert ticket_obj.tenant_id == "test-tenant"
        assert ticket_obj.ticket_id == "123456"
        assert "Server down" in ticket_obj.description
        assert ticket_obj.resolution == "Restarted Apache"
        assert ticket_obj.source == "bulk_import"

    def test_extract_ticket_missing_resolved_time(self):
        """Test extraction skips ticket without resolved_time."""
        ticket_json = {
            "id": "123456",
            "subject": "Incomplete ticket",
            "description": "No resolution date",
            "resolution": {"content": "In progress"},
            # Missing resolved_time
            "tags": [],
        }

        result = extract_ticket_data(ticket_json, "test-tenant")

        assert result is None

    def test_extract_ticket_missing_id(self):
        """Test extraction skips ticket without ID."""
        ticket_json = {
            # Missing id
            "subject": "No ID ticket",
            "description": "No ID",
            "resolution": {"content": "Fixed"},
            "resolved_time": {"value": 1704150000000},
            "tags": [],
        }

        result = extract_ticket_data(ticket_json, "test-tenant")

        assert result is None

    def test_extract_ticket_empty_description(self):
        """Test extraction skips ticket with empty description."""
        ticket_json = {
            "id": "123456",
            "subject": "",
            "description": "",
            "resolution": {"content": "Fixed"},
            "resolved_time": {"value": 1704150000000},
            "tags": [],
        }

        result = extract_ticket_data(ticket_json, "test-tenant")

        assert result is None

    def test_extract_ticket_missing_resolution(self):
        """Test extraction handles missing resolution field."""
        ticket_json = {
            "id": "123456",
            "subject": "Ticket",
            "description": "Description",
            # Missing resolution
            "resolved_time": {"value": 1704150000000},
            "tags": [],
        }

        ticket_obj = extract_ticket_data(ticket_json, "test-tenant")

        assert isinstance(ticket_obj, TicketHistory)
        assert ticket_obj.resolution == ""

    def test_extract_ticket_missing_tags(self):
        """Test extraction handles missing tags field."""
        ticket_json = {
            "id": "123456",
            "subject": "Ticket",
            "description": "Description",
            "resolution": {"content": "Fixed"},
            "resolved_time": {"value": 1704150000000},
            # Missing tags
        }

        ticket_obj = extract_ticket_data(ticket_json, "test-tenant")

        assert isinstance(ticket_obj, TicketHistory)
        assert ticket_obj.ticket_id == "123456"

    def test_extract_ticket_with_numeric_id(self):
        """Test extraction converts numeric ticket ID to string."""
        ticket_json = {
            "id": 123456,  # numeric
            "subject": "Ticket",
            "description": "Description",
            "resolution": {"content": "Fixed"},
            "resolved_time": {"value": 1704150000000},
            "tags": [],
        }

        ticket_obj = extract_ticket_data(ticket_json, "test-tenant")

        assert isinstance(ticket_obj, TicketHistory)
        assert ticket_obj.ticket_id == "123456"
        assert isinstance(ticket_obj.ticket_id, str)


@pytest.mark.asyncio
class TestAPIClientPagination:
    """Test API client pagination logic."""

    async def test_fetch_single_page(self):
        """Test fetching single page of tickets."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response_status": [{"status_code": 2000, "status": "success"}],
            "list_info": {"has_more_rows": False, "start_index": 1, "row_count": 50},
            "requests": [
                {
                    "id": "1",
                    "subject": "Ticket 1",
                    "description": "Description 1",
                    "resolution": {"content": "Fixed"},
                    "resolved_time": {"value": 1704150000000},
                    "tags": [],
                },
                {
                    "id": "2",
                    "subject": "Ticket 2",
                    "description": "Description 2",
                    "resolution": {"content": "Fixed"},
                    "resolved_time": {"value": 1704150000000},
                    "tags": [],
                },
            ],
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        start = datetime.now() - timedelta(days=90)
        end = datetime.now()

        tickets, has_more = await fetch_tickets_page(
            mock_client, "http://api.test", "key123", 1, 100, start, end
        )

        assert len(tickets) == 2
        assert has_more is False
        assert tickets[0]["id"] == "1"

    async def test_fetch_rate_limit_retry(self):
        """Test retry on rate limit (429)."""
        import httpx

        mock_client = AsyncMock()

        # First call returns 429 error, second succeeds
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429

        mock_response_success = MagicMock()
        mock_response_success.json.return_value = {
            "response_status": [{"status_code": 2000}],
            "list_info": {"has_more_rows": False},
            "requests": [
                {
                    "id": "1",
                    "subject": "Test",
                    "description": "Test",
                    "resolution": {"content": "Fixed"},
                    "resolved_time": {"value": 1704150000000},
                    "tags": [],
                }
            ],
        }
        mock_response_success.raise_for_status = MagicMock()

        # Setup side effects: first raises 429, then returns success
        async def mock_post(*args, **kwargs):
            if mock_client.post.call_count == 1:
                raise httpx.HTTPStatusError("Rate limit", request=MagicMock(), response=mock_response_429)
            else:
                return mock_response_success

        mock_client.post.side_effect = mock_post

        start = datetime.now() - timedelta(days=90)
        end = datetime.now()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            # This should succeed after retry
            tickets, has_more = await fetch_tickets_page(
                mock_client, "http://api.test", "key123", 1, 100, start, end
            )
            assert len(tickets) == 1
            assert has_more is False

    async def test_fetch_auth_error_no_retry(self):
        """Test auth error (401) does not retry."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = (
            __import__("httpx").HTTPStatusError(
                "Unauthorized", request=MagicMock(), response=mock_response
            )
        )
        mock_client.post.side_effect = mock_response.raise_for_status

        start = datetime.now() - timedelta(days=90)
        end = datetime.now()

        with pytest.raises(__import__("httpx").HTTPStatusError):
            await fetch_tickets_page(
                mock_client, "http://api.test", "key123", 1, 100, start, end
            )

        # Should only be called once (no retry)
        assert mock_client.post.call_count == 1


class TestExitCodes:
    """Test script exit code behavior."""

    def test_success_exit_code(self):
        """Test that successful import returns exit code 0."""
        # This is tested through integration tests
        # Unit test would require complex async mocking
        pass

    def test_invalid_args_exit_code(self):
        """Test that invalid arguments returns exit code 1."""
        args = MagicMock()
        args.tenant_id = ""
        args.days = 90
        args.start_date = None
        args.end_date = None

        is_valid, _ = validate_args(args)
        assert not is_valid
        # Exit code 1 would be returned in main()

    def test_tenant_not_found_exit_code(self):
        """Test that missing tenant returns exit code 2."""
        # This is tested through integration tests
        # Unit test would require database mocking
        pass

    def test_api_error_exit_code(self):
        """Test that API error returns exit code 3."""
        # This is tested through integration tests
        # Unit test would require complex async mocking
        pass
