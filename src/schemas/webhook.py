"""
Webhook payload schemas for external integrations.

This module defines Pydantic models for validating incoming webhook requests,
particularly from ServiceDesk Plus for ticket notifications. Models are separated
from API routes for reusability across multiple modules.

Implements strict validation per Epic 3 Story 3.4 security requirements:
- Field validators for format constraints (ticket_id, tenant_id patterns)
- Datetime timezone validation (reject naive datetimes)
- Length constraints via constants
- extra="forbid" to reject unknown fields (prevent parameter pollution)
"""

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, ConfigDict

from src.utils.constants import (
    MAX_TICKET_DESCRIPTION_LENGTH,
    MAX_TICKET_ID_LENGTH,
    MAX_TENANT_ID_LENGTH,
    MAX_RESOLUTION_LENGTH,
    MAX_SUBJECT_LENGTH,
    TICKET_ID_PATTERN,
    TENANT_ID_PATTERN,
)


class WebhookPayload(BaseModel):
    """
    Schema for webhook payloads from ServiceDesk Plus.

    Validates incoming webhook notifications when tickets are created or updated.
    Enforces field requirements, types, and lengths per Epic 3 Story 3.4 security specs.

    Attributes:
        event: Type of webhook event (e.g., "ticket_created")
        ticket_id: Unique identifier (alphanumeric + dashes, max 100 chars)
        tenant_id: Tenant identifier (lowercase alphanumeric + dashes, max 100 chars)
        description: Ticket description (max 10,000 chars)
        priority: Ticket priority level (low, medium, high, critical)
        created_at: ISO 8601 timestamp with timezone (naive datetimes rejected)

    Raises:
        ValidationError: If any field fails validation (invalid format, missing timezone, etc.)
    """

    event: str = Field(
        ...,
        min_length=1,
        description="Type of webhook event",
        json_schema_extra={"example": "ticket_created"},
    )
    ticket_id: str = Field(
        ...,
        min_length=1,
        max_length=MAX_TICKET_ID_LENGTH,
        description="Unique ticket identifier from ServiceDesk Plus",
        json_schema_extra={"example": "TKT-001"},
    )
    tenant_id: str = Field(
        ...,
        min_length=1,
        max_length=MAX_TENANT_ID_LENGTH,
        description="Client/tenant identifier for multi-tenant support",
        json_schema_extra={"example": "tenant-abc"},
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=MAX_TICKET_DESCRIPTION_LENGTH,
        description="Ticket description or problem statement",
        json_schema_extra={"example": "Server is slow and unresponsive"},
    )
    priority: Literal["low", "medium", "high", "critical"] = Field(
        ...,
        description="Ticket priority level",
        json_schema_extra={"example": "high"},
    )
    created_at: datetime = Field(
        ...,
        description="ISO 8601 timestamp of ticket creation with timezone",
        json_schema_extra={"example": "2025-11-01T12:00:00Z"},
    )

    # Strict validation: reject unknown fields (prevent parameter pollution)
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "event": "ticket_created",
                "ticket_id": "TKT-001",
                "tenant_id": "tenant-abc",
                "description": "Server is slow and unresponsive",
                "priority": "high",
                "created_at": "2025-11-01T12:00:00Z",
            }
        },
    )

    @field_validator("ticket_id")
    @classmethod
    def validate_ticket_id_format(cls, v: str) -> str:
        """
        Validate ticket_id matches required pattern: alphanumeric + dashes.

        Args:
            v: Ticket ID value to validate

        Returns:
            Validated ticket ID

        Raises:
            ValueError: If ticket_id doesn't match pattern (e.g., contains special chars)
        """
        if not re.match(TICKET_ID_PATTERN, v):
            raise ValueError(
                f"ticket_id must match pattern {TICKET_ID_PATTERN} "
                "(uppercase alphanumeric and dashes only, e.g., 'TKT-12345')"
            )
        return v

    @field_validator("tenant_id")
    @classmethod
    def validate_tenant_id_format(cls, v: str) -> str:
        """
        Validate tenant_id matches required pattern: lowercase alphanumeric + dashes.

        Args:
            v: Tenant ID value to validate

        Returns:
            Validated tenant ID

        Raises:
            ValueError: If tenant_id doesn't match pattern
        """
        if not re.match(TENANT_ID_PATTERN, v):
            raise ValueError(
                f"tenant_id must match pattern {TENANT_ID_PATTERN} "
                "(lowercase alphanumeric and dashes only, e.g., 'tenant-abc')"
            )
        return v

    @field_validator("created_at")
    @classmethod
    def validate_datetime_has_timezone(cls, v: datetime) -> datetime:
        """
        Validate datetime has timezone information (reject naive datetimes).

        Args:
            v: Datetime value to validate

        Returns:
            Validated datetime with timezone

        Raises:
            ValueError: If datetime is naive (missing timezone)
        """
        if v.tzinfo is None:
            raise ValueError(
                "created_at must include timezone information "
                "(e.g., '2025-11-01T12:00:00Z' or '2025-11-01T12:00:00+00:00')"
            )
        return v


class ResolvedTicketWebhook(BaseModel):
    """
    Schema for resolved ticket webhook payloads from ServiceDesk Plus.

    Validates incoming webhook notifications when tickets are marked as resolved or closed.
    Used for continuous ingestion of resolved tickets into the ticket_history table for
    context gathering by the enhancement agent (Story 2.5B).

    Implements strict validation per Epic 3 Story 3.4 security requirements.

    Attributes:
        tenant_id: Tenant identifier (lowercase alphanumeric + dashes, max 100 chars)
        ticket_id: Unique identifier (alphanumeric + dashes, max 100 chars)
        subject: Ticket subject/title (max 500 chars)
        description: Ticket description (max 10,000 chars)
        resolution: Resolution or solution (max 20,000 chars)
        resolved_date: ISO 8601 timestamp with timezone
        priority: Ticket priority level (low, medium, high, critical)
        tags: Optional list of tags/categories

    Raises:
        ValidationError: If any field fails validation (invalid format, missing timezone, etc.)

    Example:
        {
            "tenant_id": "acme-corp",
            "ticket_id": "TKT-12345",
            "subject": "Database connection pool exhausted",
            "description": "Database connection pool exhausted after office hours backup job.",
            "resolution": "Increased pool size from 10 to 25. Added monitoring alert.",
            "resolved_date": "2025-11-01T14:30:00Z",
            "priority": "high",
            "tags": ["database", "performance", "infrastructure"]
        }
    """

    tenant_id: str = Field(
        ...,
        min_length=1,
        max_length=MAX_TENANT_ID_LENGTH,
        description="Client/tenant identifier for multi-tenant support",
        json_schema_extra={"example": "acme-corp"},
    )
    ticket_id: str = Field(
        ...,
        min_length=1,
        max_length=MAX_TICKET_ID_LENGTH,
        description="Unique ticket identifier from ServiceDesk Plus",
        json_schema_extra={"example": "TKT-12345"},
    )
    subject: str = Field(
        ...,
        min_length=1,
        max_length=MAX_SUBJECT_LENGTH,
        description="Ticket subject or title",
        json_schema_extra={"example": "Database connection pool exhausted"},
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=MAX_TICKET_DESCRIPTION_LENGTH,
        description="Ticket description or problem statement (max 10K chars per Epic 3 security AC)",
        json_schema_extra={
            "example": "Database connection pool exhausted after office hours backup job."
        },
    )
    resolution: str = Field(
        ...,
        min_length=1,
        max_length=MAX_RESOLUTION_LENGTH,
        description="Resolution or solution applied to the ticket",
        json_schema_extra={"example": "Increased pool size from 10 to 25. Added monitoring alert."},
    )
    resolved_date: datetime = Field(
        ...,
        description="ISO 8601 timestamp when ticket was resolved with timezone",
        json_schema_extra={"example": "2025-11-01T14:30:00Z"},
    )
    priority: Literal["low", "medium", "high", "critical"] = Field(
        ...,
        description="Ticket priority level",
        json_schema_extra={"example": "high"},
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Optional tags or categories for the ticket",
        json_schema_extra={"example": ["database", "performance", "infrastructure"]},
    )

    # Strict validation: reject unknown fields (prevent parameter pollution)
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "tenant_id": "acme-corp",
                "ticket_id": "TKT-12345",
                "subject": "Database connection pool exhausted",
                "description": "Database connection pool exhausted after office hours backup job.",
                "resolution": "Increased pool size from 10 to 25. Added monitoring alert.",
                "resolved_date": "2025-11-01T14:30:00Z",
                "priority": "high",
                "tags": ["database", "performance", "infrastructure"],
            }
        },
    )

    @field_validator("ticket_id")
    @classmethod
    def validate_ticket_id_format(cls, v: str) -> str:
        """
        Validate ticket_id matches required pattern: alphanumeric + dashes.

        Args:
            v: Ticket ID value to validate

        Returns:
            Validated ticket ID

        Raises:
            ValueError: If ticket_id doesn't match pattern
        """
        if not re.match(TICKET_ID_PATTERN, v):
            raise ValueError(
                f"ticket_id must match pattern {TICKET_ID_PATTERN} "
                "(uppercase alphanumeric and dashes only, e.g., 'TKT-12345')"
            )
        return v

    @field_validator("tenant_id")
    @classmethod
    def validate_tenant_id_format(cls, v: str) -> str:
        """
        Validate tenant_id matches required pattern: lowercase alphanumeric + dashes.

        Args:
            v: Tenant ID value to validate

        Returns:
            Validated tenant ID

        Raises:
            ValueError: If tenant_id doesn't match pattern
        """
        if not re.match(TENANT_ID_PATTERN, v):
            raise ValueError(
                f"tenant_id must match pattern {TENANT_ID_PATTERN} "
                "(lowercase alphanumeric and dashes only, e.g., 'tenant-abc')"
            )
        return v

    @field_validator("resolved_date")
    @classmethod
    def validate_datetime_has_timezone(cls, v: datetime) -> datetime:
        """
        Validate datetime has timezone information (reject naive datetimes).

        Args:
            v: Datetime value to validate

        Returns:
            Validated datetime with timezone

        Raises:
            ValueError: If datetime is naive (missing timezone)
        """
        if v.tzinfo is None:
            raise ValueError(
                "resolved_date must include timezone information "
                "(e.g., '2025-11-01T14:30:00Z' or '2025-11-01T14:30:00+00:00')"
            )
        return v


class WebhookResponse(BaseModel):
    """
    Response schema for webhook endpoint (202 Accepted).

    Attributes:
        status: Response status indicator ("accepted")
        job_id: Unique job identifier for tracking the enhancement job
        message: Human-readable confirmation message
    """

    status: str = Field(
        ...,
        description="Response status",
        json_schema_extra={"example": "accepted"},
    )
    job_id: str = Field(
        ...,
        description="Unique job identifier for tracking",
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440000"},
    )
    message: str = Field(
        ...,
        description="Confirmation message",
        json_schema_extra={"example": "Enhancement job queued successfully"},
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "accepted",
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "Enhancement job queued successfully",
            }
        }
    )
