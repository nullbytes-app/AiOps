"""
Unit tests for history_helper.py functions.

Tests cover:
- get_enhancement_history() with various filter combinations
- Pagination (first page, middle page, last page)
- Edge cases (empty results, single record, page boundaries)
- get_all_tenant_ids() tenant list retrieval
- convert_to_csv() DataFrame to CSV conversion
- format_status_badge() status badge formatting
"""

import json
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pandas as pd
import pytest

from admin.utils.history_helper import (
    convert_to_csv,
    format_status_badge,
    get_all_tenant_ids,
    get_enhancement_history,
)


@pytest.fixture(autouse=True)
def clear_streamlit_cache():
    """Clear Streamlit cache before each test to avoid test pollution."""
    import streamlit as st

    st.cache_data.clear()
    st.cache_resource.clear()


@pytest.fixture
def mock_enhancement_records():
    """Create mock EnhancementHistory records for testing."""
    return [
        {
            "id": str(uuid4()),
            "tenant_id": "acme",
            "ticket_id": "INC-001",
            "status": "completed",
            "context_gathered": {"source": "knowledge_base", "items": 5},
            "llm_output": "Enhancement completed successfully",
            "error_message": None,
            "processing_time_ms": 1200,
            "created_at": datetime(2025, 11, 1, 10, 0, 0),
            "completed_at": datetime(2025, 11, 1, 10, 0, 1),
        },
        {
            "id": str(uuid4()),
            "tenant_id": "globex",
            "ticket_id": "INC-002",
            "status": "failed",
            "context_gathered": {"source": "api", "items": 2},
            "llm_output": None,
            "error_message": "Connection timeout",
            "processing_time_ms": None,
            "created_at": datetime(2025, 11, 2, 11, 30, 0),
            "completed_at": None,
        },
        {
            "id": str(uuid4()),
            "tenant_id": "initech",
            "ticket_id": "INC-003",
            "status": "pending",
            "context_gathered": None,
            "llm_output": None,
            "error_message": None,
            "processing_time_ms": None,
            "created_at": datetime(2025, 11, 3, 14, 15, 0),
            "completed_at": None,
        },
    ]


class TestGetEnhancementHistory:
    """Test suite for get_enhancement_history() function."""

    @patch("admin.utils.history_helper.get_db_session")
    def test_get_all_records_no_filters(self, mock_session, mock_enhancement_records):
        """Test querying all records without any filters (AC1)."""
        # Setup mock
        mock_query = MagicMock()
        mock_query.count.return_value = 3
        mock_query.order_by.return_value.limit.return_value.offset.return_value.all.return_value = []

        mock_session.return_value.__enter__.return_value.query.return_value = mock_query

        # Execute
        records, total = get_enhancement_history(page=1, page_size=50)

        # Assert
        assert total == 3
        assert isinstance(records, list)
        mock_query.order_by.assert_called_once()
        mock_query.order_by.return_value.limit.assert_called_once_with(50)

    @patch("admin.utils.history_helper.get_db_session")
    def test_filter_by_tenant(self, mock_session):
        """Test filtering by tenant_id (AC2)."""
        # Setup mock
        mock_query = MagicMock()
        mock_query.filter.return_value.count.return_value = 1
        mock_query.filter.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = (
            []
        )

        mock_session.return_value.__enter__.return_value.query.return_value = mock_query

        # Execute
        records, total = get_enhancement_history(tenant_id="acme", page=1, page_size=50)

        # Assert
        assert total == 1
        mock_query.filter.assert_called_once()

    @patch("admin.utils.history_helper.get_db_session")
    def test_filter_by_status(self, mock_session):
        """Test filtering by status (AC2)."""
        # Setup mock
        mock_query = MagicMock()
        mock_query.filter.return_value.count.return_value = 2
        mock_query.filter.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = (
            []
        )

        mock_session.return_value.__enter__.return_value.query.return_value = mock_query

        # Execute
        records, total = get_enhancement_history(status="completed", page=1, page_size=50)

        # Assert
        assert total == 2
        mock_query.filter.assert_called_once()

    @patch("admin.utils.history_helper.get_db_session")
    def test_filter_by_date_range(self, mock_session):
        """Test filtering by date range (AC2)."""
        # Setup mock
        mock_query = MagicMock()
        mock_query.filter.return_value.count.return_value = 1
        mock_query.filter.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = (
            []
        )

        mock_session.return_value.__enter__.return_value.query.return_value = mock_query

        # Execute
        from_date = date(2025, 11, 1)
        to_date = date(2025, 11, 2)
        records, total = get_enhancement_history(
            date_from=from_date, date_to=to_date, page=1, page_size=50
        )

        # Assert
        assert total == 1
        mock_query.filter.assert_called_once()

    @patch("admin.utils.history_helper.get_db_session")
    def test_search_by_ticket_id(self, mock_session):
        """Test searching by ticket_id (AC3)."""
        # Setup mock
        mock_query = MagicMock()
        mock_query.filter.return_value.count.return_value = 1
        mock_query.filter.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = (
            []
        )

        mock_session.return_value.__enter__.return_value.query.return_value = mock_query

        # Execute
        records, total = get_enhancement_history(search_query="INC-001", page=1, page_size=50)

        # Assert
        assert total == 1
        mock_query.filter.assert_called_once()

    @patch("admin.utils.history_helper.get_db_session")
    def test_combined_filters(self, mock_session):
        """Test combining multiple filters (AC2, AC3)."""
        # Setup mock
        mock_query = MagicMock()
        mock_query.filter.return_value.count.return_value = 1
        mock_query.filter.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = (
            []
        )

        mock_session.return_value.__enter__.return_value.query.return_value = mock_query

        # Execute
        records, total = get_enhancement_history(
            tenant_id="acme",
            status="completed",
            search_query="INC-001",
            page=1,
            page_size=50,
        )

        # Assert
        assert total == 1
        mock_query.filter.assert_called_once()

    @patch("admin.utils.history_helper.get_db_session")
    def test_pagination_first_page(self, mock_session):
        """Test pagination on first page (AC1)."""
        # Setup mock
        mock_query = MagicMock()
        mock_query.count.return_value = 100
        mock_query.order_by.return_value.limit.return_value.offset.return_value.all.return_value = []

        mock_session.return_value.__enter__.return_value.query.return_value = mock_query

        # Execute
        records, total = get_enhancement_history(page=1, page_size=25)

        # Assert
        assert total == 100
        mock_query.order_by.return_value.limit.assert_called_once_with(25)
        mock_query.order_by.return_value.limit.return_value.offset.assert_called_once_with(0)

    @patch("admin.utils.history_helper.get_db_session")
    def test_pagination_middle_page(self, mock_session):
        """Test pagination on middle page (AC1)."""
        # Setup mock
        mock_query = MagicMock()
        mock_query.count.return_value = 100
        mock_query.order_by.return_value.limit.return_value.offset.return_value.all.return_value = []

        mock_session.return_value.__enter__.return_value.query.return_value = mock_query

        # Execute
        records, total = get_enhancement_history(page=3, page_size=25)

        # Assert
        assert total == 100
        # Offset should be (page - 1) * page_size = (3 - 1) * 25 = 50
        mock_query.order_by.return_value.limit.return_value.offset.assert_called_once_with(50)

    @patch("admin.utils.history_helper.get_db_session")
    def test_pagination_last_page(self, mock_session):
        """Test pagination on last page (AC1)."""
        # Setup mock
        mock_query = MagicMock()
        mock_query.count.return_value = 100
        mock_query.order_by.return_value.limit.return_value.offset.return_value.all.return_value = []

        mock_session.return_value.__enter__.return_value.query.return_value = mock_query

        # Execute
        records, total = get_enhancement_history(page=4, page_size=25)

        # Assert
        assert total == 100
        # Offset should be (page - 1) * page_size = (4 - 1) * 25 = 75
        mock_query.order_by.return_value.limit.return_value.offset.assert_called_once_with(75)

    @patch("admin.utils.history_helper.get_db_session")
    def test_empty_result_set(self, mock_session):
        """Test handling of empty result set."""
        # Setup mock
        mock_query = MagicMock()
        mock_query.count.return_value = 0
        mock_query.order_by.return_value.limit.return_value.offset.return_value.all.return_value = []

        mock_session.return_value.__enter__.return_value.query.return_value = mock_query

        # Execute
        records, total = get_enhancement_history(page=1, page_size=50)

        # Assert
        assert total == 0
        assert records == []

    @patch("admin.utils.history_helper.get_db_session")
    def test_single_record(self, mock_session):
        """Test handling of single record result."""
        # Setup mock
        mock_record = MagicMock()
        mock_record.id = uuid4()
        mock_record.tenant_id = "acme"
        mock_record.ticket_id = "INC-001"
        mock_record.status = "completed"
        mock_record.context_gathered = {}
        mock_record.llm_output = "output"
        mock_record.error_message = None
        mock_record.processing_time_ms = 1000
        mock_record.created_at = datetime.now()
        mock_record.completed_at = datetime.now()

        mock_query = MagicMock()
        mock_query.count.return_value = 1
        mock_query.order_by.return_value.limit.return_value.offset.return_value.all.return_value = [
            mock_record
        ]

        mock_session.return_value.__enter__.return_value.query.return_value = mock_query

        # Execute
        records, total = get_enhancement_history(page=1, page_size=50)

        # Assert
        assert total == 1
        assert len(records) == 1


class TestGetAllTenantIds:
    """Test suite for get_all_tenant_ids() function."""

    @patch("admin.utils.history_helper.get_db_session")
    def test_get_tenant_list(self, mock_session):
        """Test retrieving distinct tenant IDs."""
        # Setup mock
        mock_query = MagicMock()
        mock_query.distinct.return_value.order_by.return_value.all.return_value = [
            ("acme",),
            ("globex",),
            ("initech",),
        ]

        mock_session.return_value.__enter__.return_value.query.return_value = mock_query

        # Execute
        tenant_ids = get_all_tenant_ids()

        # Assert
        assert tenant_ids == ["acme", "globex", "initech"]
        assert isinstance(tenant_ids, list)

    @patch("admin.utils.history_helper.get_db_session")
    def test_empty_tenant_list(self, mock_session):
        """Test handling of empty tenant list."""
        # Setup mock
        mock_query = MagicMock()
        mock_query.distinct.return_value.order_by.return_value.all.return_value = []

        mock_session.return_value.__enter__.return_value.query.return_value = mock_query

        # Execute
        tenant_ids = get_all_tenant_ids()

        # Assert
        assert tenant_ids == []


class TestConvertToCsv:
    """Test suite for convert_to_csv() function."""

    def test_convert_simple_dataframe(self):
        """Test converting simple DataFrame to CSV (AC6)."""
        # Setup
        df = pd.DataFrame(
            [
                {"ticket_id": "INC-001", "status": "completed", "tenant_id": "acme"},
                {"ticket_id": "INC-002", "status": "failed", "tenant_id": "globex"},
            ]
        )

        # Execute
        csv_bytes = convert_to_csv(df)

        # Assert
        assert isinstance(csv_bytes, bytes)
        csv_string = csv_bytes.decode("utf-8")
        assert "ticket_id" in csv_string
        assert "INC-001" in csv_string
        assert "INC-002" in csv_string

    def test_convert_empty_dataframe(self):
        """Test converting empty DataFrame to CSV."""
        # Setup
        df = pd.DataFrame()

        # Execute
        csv_bytes = convert_to_csv(df)

        # Assert
        assert isinstance(csv_bytes, bytes)

    def test_flatten_json_fields(self):
        """Test flattening of JSON fields in CSV export (AC6)."""
        # Setup
        df = pd.DataFrame(
            [
                {
                    "ticket_id": "INC-001",
                    "context_gathered": {"source": "kb", "items": 5},
                    "status": "completed",
                }
            ]
        )

        # Execute
        csv_bytes = convert_to_csv(df)

        # Assert
        assert isinstance(csv_bytes, bytes)
        csv_string = csv_bytes.decode("utf-8")
        assert "context_summary" in csv_string
        # JSON should be serialized to string
        assert "source" in csv_string or "kb" in csv_string

    def test_utf8_encoding(self):
        """Test UTF-8 encoding for CSV export (AC6)."""
        # Setup
        df = pd.DataFrame([{"ticket_id": "INC-001", "description": "Émoji test 🚀"}])

        # Execute
        csv_bytes = convert_to_csv(df)

        # Assert
        assert isinstance(csv_bytes, bytes)
        csv_string = csv_bytes.decode("utf-8")
        assert "INC-001" in csv_string


class TestFormatStatusBadge:
    """Test suite for format_status_badge() function."""

    def test_completed_status(self):
        """Test formatting of completed status (AC8)."""
        result = format_status_badge("completed")
        assert ":green[" in result
        assert "completed" in result

    def test_failed_status(self):
        """Test formatting of failed status (AC8)."""
        result = format_status_badge("failed")
        assert ":red[" in result
        assert "failed" in result

    def test_pending_status(self):
        """Test formatting of pending status (AC8)."""
        result = format_status_badge("pending")
        assert ":blue[" in result
        assert "pending" in result

    def test_case_insensitive(self):
        """Test case-insensitive status matching."""
        result_upper = format_status_badge("COMPLETED")
        result_lower = format_status_badge("completed")
        assert ":green[" in result_upper
        assert ":green[" in result_lower

    def test_invalid_status_fallback(self):
        """Test fallback for invalid status."""
        result = format_status_badge("unknown")
        assert ":gray[" in result
        assert "unknown" in result
