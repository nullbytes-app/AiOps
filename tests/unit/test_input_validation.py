"""
Unit tests for Pydantic input validation models.

Tests WebhookPayload and ResolvedTicketWebhook models per Epic 3 Story 3.4
AC1, AC3, AC4, AC5 requirements. Minimum 20 test cases as per AC6.
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.schemas.webhook import ResolvedTicketWebhook, WebhookPayload


class TestWebhookPayloadValidInput:
    """Test WebhookPayload with valid inputs."""

    def test_valid_payload_all_fields(self):
        """Test that valid payload with all required fields passes validation."""
        payload = WebhookPayload(
            event="ticket_created",
            ticket_id="TKT-12345",
            tenant_id="tenant-abc",
            description="Server is slow and unresponsive",
            priority="high",
            created_at=datetime(2025, 11, 1, 12, 0, 0, tzinfo=timezone.utc),
        )
        assert payload.ticket_id == "TKT-12345"
        assert payload.tenant_id == "tenant-abc"
        assert payload.priority == "high"

    def test_valid_payload_max_length_description(self):
        """Test that description at exactly 10,000 chars passes validation."""
        description = "A" * 10000
        payload = WebhookPayload(
            event="ticket_created",
            ticket_id="TKT-999",
            tenant_id="tenant-xyz",
            description=description,
            priority="low",
            created_at=datetime.now(timezone.utc),
        )
        assert len(payload.description) == 10000

    def test_valid_payload_different_priorities(self):
        """Test that all valid priority values are accepted."""
        priorities = ["low", "medium", "high", "critical"]
        for priority in priorities:
            payload = WebhookPayload(
                event="ticket_created",
                ticket_id="TKT-001",
                tenant_id="tenant-test",
                description="Test",
                priority=priority,
                created_at=datetime.now(timezone.utc),
            )
            assert payload.priority == priority


class TestWebhookPayloadInvalidTypes:
    """Test WebhookPayload with invalid types (AC1)."""

    def test_ticket_id_as_integer_fails(self):
        """Test that ticket_id as integer instead of string fails."""
        with pytest.raises(ValidationError) as exc_info:
            WebhookPayload(
                event="ticket_created",
                ticket_id=12345,  # Invalid: should be string
                tenant_id="tenant-abc",
                description="Test",
                priority="high",
                created_at=datetime.now(timezone.utc),
            )
        assert "ticket_id" in str(exc_info.value)

    def test_created_at_invalid_string_fails(self):
        """Test that created_at with invalid string format fails."""
        with pytest.raises(ValidationError) as exc_info:
            WebhookPayload(
                event="ticket_created",
                ticket_id="TKT-001",
                tenant_id="tenant-abc",
                description="Test",
                priority="high",
                created_at="not-a-date",  # Invalid: unparseable string
            )
        assert "created_at" in str(exc_info.value)

    def test_invalid_priority_enum_fails(self):
        """Test that invalid priority value fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            WebhookPayload(
                event="ticket_created",
                ticket_id="TKT-001",
                tenant_id="tenant-abc",
                description="Test",
                priority="super-high",  # Invalid: not in enum
                created_at=datetime.now(timezone.utc),
            )
        assert "priority" in str(exc_info.value)

    def test_extra_fields_rejected_with_forbid(self):
        """Test that extra unexpected fields are rejected (model_config extra=forbid)."""
        with pytest.raises(ValidationError) as exc_info:
            WebhookPayload(
                event="ticket_created",
                ticket_id="TKT-001",
                tenant_id="tenant-abc",
                description="Test",
                priority="high",
                created_at=datetime.now(timezone.utc),
                unexpected_field="hacker",  # Extra field
            )
        assert "unexpected_field" in str(exc_info.value) or "extra" in str(exc_info.value).lower()


class TestWebhookPayloadOversizedInput:
    """Test WebhookPayload with oversized inputs (AC3)."""

    def test_description_exceeds_10000_chars_fails(self):
        """Test that description with 10,001 characters fails validation."""
        description = "A" * 10001
        with pytest.raises(ValidationError) as exc_info:
            WebhookPayload(
                event="ticket_created",
                ticket_id="TKT-001",
                tenant_id="tenant-abc",
                description=description,
                priority="high",
                created_at=datetime.now(timezone.utc),
            )
        error_str = str(exc_info.value)
        assert "description" in error_str
        assert "max_length" in error_str or "10000" in error_str

    def test_ticket_id_exceeds_100_chars_fails(self):
        """Test that ticket_id with 101 characters fails validation."""
        ticket_id = "T" * 101
        with pytest.raises(ValidationError) as exc_info:
            WebhookPayload(
                event="ticket_created",
                ticket_id=ticket_id,
                tenant_id="tenant-abc",
                description="Test",
                priority="high",
                created_at=datetime.now(timezone.utc),
            )
        error_str = str(exc_info.value)
        assert "ticket_id" in error_str
        assert "max_length" in error_str or "100" in error_str


class TestWebhookPayloadFormatValidation:
    """Test WebhookPayload field format validators (AC1, AC5)."""

    def test_ticket_id_invalid_format_fails(self):
        """Test that ticket_id with invalid chars (lowercase, special) fails."""
        with pytest.raises(ValidationError) as exc_info:
            WebhookPayload(
                event="ticket_created",
                ticket_id="tkt-12345",  # Invalid: must be uppercase
                tenant_id="tenant-abc",
                description="Test",
                priority="high",
                created_at=datetime.now(timezone.utc),
            )
        assert "ticket_id" in str(exc_info.value)
        assert "pattern" in str(exc_info.value).lower()

    def test_tenant_id_invalid_format_fails(self):
        """Test that tenant_id with uppercase or special chars fails."""
        with pytest.raises(ValidationError) as exc_info:
            WebhookPayload(
                event="ticket_created",
                ticket_id="TKT-001",
                tenant_id="Tenant-ABC",  # Invalid: must be lowercase
                description="Test",
                priority="high",
                created_at=datetime.now(timezone.utc),
            )
        assert "tenant_id" in str(exc_info.value)
        assert "pattern" in str(exc_info.value).lower()

    def test_naive_datetime_fails(self):
        """Test that datetime without timezone (naive) fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            WebhookPayload(
                event="ticket_created",
                ticket_id="TKT-001",
                tenant_id="tenant-abc",
                description="Test",
                priority="high",
                created_at=datetime(2025, 11, 1, 12, 0, 0),  # Naive: no timezone
            )
        assert "created_at" in str(exc_info.value)
        assert "timezone" in str(exc_info.value).lower()


class TestWebhookPayloadSpecialCharacters:
    """Test WebhookPayload handles special characters safely (AC5)."""

    def test_legitimate_technical_content_passes(self):
        """Test that legitimate technical content with < > passes."""
        payload = WebhookPayload(
            event="ticket_created",
            ticket_id="TKT-001",
            tenant_id="tenant-abc",
            description="if (x < 10 && y > 5)",
            priority="high",
            created_at=datetime.now(timezone.utc),
        )
        assert "<" in payload.description
        assert ">" in payload.description

    def test_company_names_with_special_chars_pass(self):
        """Test that company names like AT&T, O'Brien pass validation."""
        payload = WebhookPayload(
            event="ticket_created",
            ticket_id="TKT-001",
            tenant_id="tenant-abc",
            description="AT&T service issue for O'Brien",
            priority="medium",
            created_at=datetime.now(timezone.utc),
        )
        assert "&" in payload.description
        assert "'" in payload.description

    def test_path_traversal_in_ticket_id_fails(self):
        """Test that path traversal attempt in ticket_id is rejected."""
        with pytest.raises(ValidationError):
            WebhookPayload(
                event="ticket_created",
                ticket_id="../../etc/passwd",  # Invalid format
                tenant_id="tenant-abc",
                description="Test",
                priority="high",
                created_at=datetime.now(timezone.utc),
            )


class TestResolvedTicketWebhookValidation:
    """Test ResolvedTicketWebhook model (AC1, AC3, AC5)."""

    def test_valid_resolved_ticket_payload(self):
        """Test that valid ResolvedTicketWebhook passes validation."""
        payload = ResolvedTicketWebhook(
            tenant_id="acme-corp",
            ticket_id="TKT-12345",
            subject="Database connection pool exhausted",
            description="Database connection pool exhausted after office hours backup job.",
            resolution="Increased pool size from 10 to 25. Added monitoring alert.",
            resolved_date=datetime(2025, 11, 1, 14, 30, 0, tzinfo=timezone.utc),
            priority="high",
            tags=["database", "performance"],
        )
        assert payload.tenant_id == "acme-corp"
        assert len(payload.tags) == 2

    def test_resolution_max_length_20000_chars(self):
        """Test that resolution field accepts up to 20,000 chars."""
        resolution = "R" * 20000
        payload = ResolvedTicketWebhook(
            tenant_id="tenant-abc",
            ticket_id="TKT-999",
            subject="Test",
            description="Test",
            resolution=resolution,
            resolved_date=datetime.now(timezone.utc),
            priority="low",
        )
        assert len(payload.resolution) == 20000

    def test_resolution_exceeds_20000_chars_fails(self):
        """Test that resolution with 20,001 chars fails validation."""
        resolution = "R" * 20001
        with pytest.raises(ValidationError) as exc_info:
            ResolvedTicketWebhook(
                tenant_id="tenant-abc",
                ticket_id="TKT-999",
                subject="Test",
                description="Test",
                resolution=resolution,
                resolved_date=datetime.now(timezone.utc),
                priority="low",
            )
        assert "resolution" in str(exc_info.value)
        assert "max_length" in str(exc_info.value) or "20000" in str(exc_info.value)

    def test_subject_max_length_500_chars(self):
        """Test that subject field is limited to 500 chars."""
        subject = "S" * 500
        payload = ResolvedTicketWebhook(
            tenant_id="tenant-abc",
            ticket_id="TKT-999",
            subject=subject,
            description="Test",
            resolution="Test",
            resolved_date=datetime.now(timezone.utc),
            priority="low",
        )
        assert len(payload.subject) == 500

    def test_resolved_date_naive_datetime_fails(self):
        """Test that resolved_date without timezone fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            ResolvedTicketWebhook(
                tenant_id="tenant-abc",
                ticket_id="TKT-001",
                subject="Test",
                description="Test",
                resolution="Test",
                resolved_date=datetime(2025, 11, 1, 14, 30, 0),  # Naive
                priority="low",
            )
        assert "resolved_date" in str(exc_info.value)
        assert "timezone" in str(exc_info.value).lower()

    def test_tags_optional_defaults_to_empty_list(self):
        """Test that tags field is optional and defaults to empty list."""
        payload = ResolvedTicketWebhook(
            tenant_id="tenant-abc",
            ticket_id="TKT-001",
            subject="Test",
            description="Test",
            resolution="Test",
            resolved_date=datetime.now(timezone.utc),
            priority="low",
            # tags omitted
        )
        assert payload.tags == []

    def test_extra_fields_rejected(self):
        """Test that extra fields are rejected (model_config extra=forbid)."""
        with pytest.raises(ValidationError) as exc_info:
            ResolvedTicketWebhook(
                tenant_id="tenant-abc",
                ticket_id="TKT-001",
                subject="Test",
                description="Test",
                resolution="Test",
                resolved_date=datetime.now(timezone.utc),
                priority="low",
                malicious_field="hack",  # Extra field
            )
        assert "malicious_field" in str(exc_info.value) or "extra" in str(exc_info.value).lower()
