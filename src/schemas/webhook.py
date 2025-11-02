"""
Webhook payload schemas for external integrations.

This module defines Pydantic models for validating incoming webhook requests,
particularly from ServiceDesk Plus for ticket notifications. Models are separated
from API routes for reusability across multiple modules.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class WebhookPayload(BaseModel):
    """
    Schema for webhook payloads from ServiceDesk Plus.

    Validates incoming webhook notifications when tickets are created or updated.
    Enforces field requirements, types, and lengths per architecture specifications.

    Attributes:
        event: Type of webhook event (e.g., "ticket_created")
        ticket_id: Unique identifier for the ticket in ServiceDesk Plus
        tenant_id: Client/tenant identifier for multi-tenant support
        description: Ticket description or problem statement (max 10000 chars)
        priority: Ticket priority level (low, medium, high, critical)
        created_at: ISO 8601 timestamp of ticket creation

    Raises:
        ValidationError: If any field fails validation (e.g., invalid priority)
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
        description="Unique ticket identifier from ServiceDesk Plus",
        json_schema_extra={"example": "TKT-001"},
    )
    tenant_id: str = Field(
        ...,
        min_length=1,
        description="Client/tenant identifier for multi-tenant support",
        json_schema_extra={"example": "tenant-abc"},
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=10000,
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
        description="ISO 8601 timestamp of ticket creation",
        json_schema_extra={"example": "2025-11-01T12:00:00Z"},
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "event": "ticket_created",
                "ticket_id": "TKT-001",
                "tenant_id": "tenant-abc",
                "description": "Server is slow and unresponsive",
                "priority": "high",
                "created_at": "2025-11-01T12:00:00Z",
            }
        }
    }


class ResolvedTicketWebhook(BaseModel):
    """
    Schema for resolved ticket webhook payloads from ServiceDesk Plus.

    Validates incoming webhook notifications when tickets are marked as resolved or closed.
    Used for continuous ingestion of resolved tickets into the ticket_history table for
    context gathering by the enhancement agent (Story 2.5B).

    Attributes:
        tenant_id: Client/tenant identifier for multi-tenant support
        ticket_id: Unique identifier for the ticket in ServiceDesk Plus
        subject: Ticket subject/title
        description: Ticket description or problem statement (max 10000 chars per Epic 3 AC)
        resolution: Resolution or solution applied to the ticket
        resolved_date: ISO 8601 timestamp when ticket was resolved
        priority: Ticket priority level (low, medium, high, critical)
        tags: Optional list of tags/categories for the ticket

    Raises:
        ValidationError: If any field fails validation (invalid datetime, empty ticket_id, etc.)

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
        description="Client/tenant identifier for multi-tenant support",
        json_schema_extra={"example": "acme-corp"},
    )
    ticket_id: str = Field(
        ...,
        min_length=1,
        description="Unique ticket identifier from ServiceDesk Plus",
        json_schema_extra={"example": "TKT-12345"},
    )
    subject: str = Field(
        ...,
        min_length=1,
        description="Ticket subject or title",
        json_schema_extra={"example": "Database connection pool exhausted"},
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Ticket description or problem statement (max 10K chars per Epic 3 security AC)",
        json_schema_extra={
            "example": "Database connection pool exhausted after office hours backup job."
        },
    )
    resolution: str = Field(
        ...,
        min_length=1,
        description="Resolution or solution applied to the ticket",
        json_schema_extra={"example": "Increased pool size from 10 to 25. Added monitoring alert."},
    )
    resolved_date: datetime = Field(
        ...,
        description="ISO 8601 timestamp when ticket was resolved",
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

    model_config = {
        "json_schema_extra": {
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
        }
    }
