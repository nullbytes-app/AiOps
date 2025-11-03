"""
Unit tests for schema correlation_id validation.

Tests that correlation_id fields in EnhancementJob, WebhookPayload, and EnhancementState
schemas properly validate UUID v4 format and enforce required constraints.
"""

import uuid
from typing import Optional

import pytest
from pydantic import ValidationError

from src.schemas.job import EnhancementJob
from src.schemas.webhook import WebhookPayload


class TestEnhancementJobCorrelationId:
    """Test suite for correlation_id validation in EnhancementJob schema."""

    def test_valid_correlation_id_uuid_v4(self):
        """Test EnhancementJob accepts valid UUID v4 correlation_id."""
        valid_uuid = str(uuid.uuid4())
        job = EnhancementJob(
            job_id="550e8400-e29b-41d4-a716-446655440000",
            ticket_id="TKT-001",
            tenant_id="tenant-abc",
            description="Test description",
            priority="high",
            timestamp="2025-11-01T12:00:00Z",
            correlation_id=valid_uuid,
        )
        assert job.correlation_id == valid_uuid

    def test_invalid_correlation_id_too_short(self):
        """Test EnhancementJob rejects correlation_id shorter than 36 chars."""
        with pytest.raises(ValidationError) as exc_info:
            EnhancementJob(
                job_id="550e8400-e29b-41d4-a716-446655440000",
                ticket_id="TKT-001",
                tenant_id="tenant-abc",
                description="Test description",
                priority="high",
                timestamp="2025-11-01T12:00:00Z",
                correlation_id="short-id",
            )
        assert "correlation_id" in str(exc_info.value).lower()

    def test_invalid_correlation_id_too_long(self):
        """Test EnhancementJob rejects correlation_id longer than 36 chars."""
        with pytest.raises(ValidationError) as exc_info:
            EnhancementJob(
                job_id="550e8400-e29b-41d4-a716-446655440000",
                ticket_id="TKT-001",
                tenant_id="tenant-abc",
                description="Test description",
                priority="high",
                timestamp="2025-11-01T12:00:00Z",
                correlation_id="550e8400-e29b-41d4-a716-446655440000-extra",
            )
        assert "correlation_id" in str(exc_info.value).lower()

    def test_missing_correlation_id_required(self):
        """Test EnhancementJob requires correlation_id field."""
        with pytest.raises(ValidationError) as exc_info:
            EnhancementJob(
                job_id="550e8400-e29b-41d4-a716-446655440000",
                ticket_id="TKT-001",
                tenant_id="tenant-abc",
                description="Test description",
                priority="high",
                timestamp="2025-11-01T12:00:00Z",
                # correlation_id is missing
            )
        assert "correlation_id" in str(exc_info.value).lower()

    def test_correlation_id_exact_length_36(self):
        """Test correlation_id must be exactly 36 characters (UUID format)."""
        # Valid UUID v4 is always 36 chars (8-4-4-4-12 with dashes)
        valid_uuid = str(uuid.uuid4())
        assert len(valid_uuid) == 36

        job = EnhancementJob(
            job_id="550e8400-e29b-41d4-a716-446655440000",
            ticket_id="TKT-001",
            tenant_id="tenant-abc",
            description="Test description",
            priority="high",
            timestamp="2025-11-01T12:00:00Z",
            correlation_id=valid_uuid,
        )
        assert len(job.correlation_id) == 36


class TestWebhookPayloadCorrelationId:
    """Test suite for correlation_id validation in WebhookPayload schema."""

    def test_correlation_id_optional_in_webhook_payload(self):
        """Test WebhookPayload accepts webhook without correlation_id."""
        # correlation_id should be Optional in WebhookPayload (generated at API entry)
        from datetime import datetime, timezone
        payload = WebhookPayload(
            event="ticket_created",
            ticket_id="TKT-001",
            tenant_id="tenant-abc",
            description="Test description",
            priority="high",
            created_at=datetime.now(timezone.utc),
            # correlation_id is optional
        )
        assert payload.correlation_id is None or isinstance(payload.correlation_id, str)

    def test_correlation_id_provided_in_webhook_payload(self):
        """Test WebhookPayload accepts provided correlation_id."""
        from datetime import datetime, timezone
        valid_uuid = str(uuid.uuid4())
        payload = WebhookPayload(
            event="ticket_created",
            ticket_id="TKT-001",
            tenant_id="tenant-abc",
            description="Test description",
            priority="high",
            created_at=datetime.now(timezone.utc),
            correlation_id=valid_uuid,
        )
        assert payload.correlation_id == valid_uuid

    def test_correlation_id_invalid_format_in_webhook_payload(self):
        """Test WebhookPayload rejects invalid correlation_id format."""
        from datetime import datetime, timezone
        with pytest.raises(ValidationError):
            WebhookPayload(
                event="ticket_created",
                ticket_id="TKT-001",
                tenant_id="tenant-abc",
                description="Test description",
                priority="high",
                created_at=datetime.now(timezone.utc),
                correlation_id="invalid-id-format",  # Not 36 chars
            )


class TestEnhancementJobSerialization:
    """Test suite for EnhancementJob serialization with correlation_id."""

    def test_enhancement_job_to_json_includes_correlation_id(self):
        """Test EnhancementJob serializes to JSON with correlation_id."""
        valid_uuid = str(uuid.uuid4())
        job = EnhancementJob(
            job_id="550e8400-e29b-41d4-a716-446655440000",
            ticket_id="TKT-001",
            tenant_id="tenant-abc",
            description="Test description",
            priority="high",
            timestamp="2025-11-01T12:00:00Z",
            correlation_id=valid_uuid,
        )

        json_data = job.model_dump_json()
        assert valid_uuid in json_data
        assert '"correlation_id"' in json_data

    def test_enhancement_job_from_json_includes_correlation_id(self):
        """Test EnhancementJob deserializes from JSON with correlation_id."""
        valid_uuid = str(uuid.uuid4())
        json_str = f'''
        {{
            "job_id": "550e8400-e29b-41d4-a716-446655440000",
            "ticket_id": "TKT-001",
            "tenant_id": "tenant-abc",
            "description": "Test description",
            "priority": "high",
            "timestamp": "2025-11-01T12:00:00Z",
            "correlation_id": "{valid_uuid}"
        }}
        '''

        job = EnhancementJob.model_validate_json(json_str)
        assert job.correlation_id == valid_uuid

    def test_enhancement_job_dict_includes_correlation_id(self):
        """Test EnhancementJob dict representation includes correlation_id."""
        valid_uuid = str(uuid.uuid4())
        job = EnhancementJob(
            job_id="550e8400-e29b-41d4-a716-446655440000",
            ticket_id="TKT-001",
            tenant_id="tenant-abc",
            description="Test description",
            priority="high",
            timestamp="2025-11-01T12:00:00Z",
            correlation_id=valid_uuid,
        )

        job_dict = job.model_dump()
        assert "correlation_id" in job_dict
        assert job_dict["correlation_id"] == valid_uuid


class TestCorrelationIdConsistency:
    """Test consistency of correlation_id across schemas."""

    def test_webhook_payload_to_enhancement_job_correlation_id_propagation(self):
        """Test correlation_id can be propagated from WebhookPayload to EnhancementJob."""
        from datetime import datetime, timezone
        valid_uuid = str(uuid.uuid4())

        # Create WebhookPayload with correlation_id
        payload = WebhookPayload(
            event="ticket_created",
            ticket_id="TKT-001",
            tenant_id="tenant-abc",
            description="Test description",
            priority="high",
            created_at=datetime.now(timezone.utc),
            correlation_id=valid_uuid,
        )

        # Create EnhancementJob from WebhookPayload data
        job = EnhancementJob(
            job_id=str(uuid.uuid4()),
            ticket_id=payload.ticket_id,
            tenant_id=payload.tenant_id,
            description=payload.description,
            priority=payload.priority,
            timestamp=payload.created_at,
            correlation_id=payload.correlation_id,  # Propagate from webhook
        )

        assert job.correlation_id == valid_uuid
        assert job.correlation_id == payload.correlation_id
