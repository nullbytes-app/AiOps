"""
Job payload schemas for enhancement processing.

This module defines Pydantic models for job payloads that are queued to Redis
for asynchronous processing by Celery workers. Jobs represent enhancement tasks
for tickets received via webhooks.
"""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class EnhancementJob(BaseModel):
    """
    Schema for enhancement job payloads queued to Redis.

    Represents a ticket enhancement request that has been validated and is ready
    for asynchronous processing. This model is serialized to JSON and pushed to
    Redis queue for consumption by Celery workers.

    Attributes:
        job_id: Unique identifier for this job (UUID format)
        ticket_id: Unique identifier for the ticket in ServiceDesk Plus
        tenant_id: Client/tenant identifier for multi-tenant support
        description: Ticket description or problem statement (max 10000 chars)
        priority: Ticket priority level (low, medium, high, critical)
        timestamp: ISO 8601 timestamp when job was created
        created_at: UTC timestamp when job was queued (auto-generated)

    Example:
        {
            "job_id": "550e8400-e29b-41d4-a716-446655440000",
            "ticket_id": "TKT-001",
            "tenant_id": "tenant-abc",
            "description": "Server is slow and unresponsive",
            "priority": "high",
            "timestamp": "2025-11-01T12:00:00Z",
            "created_at": "2025-11-01T12:00:05.123456Z"
        }
    """

    job_id: str = Field(
        ...,
        min_length=1,
        description="Unique job identifier (UUID format)",
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440000"},
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
    timestamp: datetime = Field(
        ...,
        description="ISO 8601 timestamp from original webhook",
        json_schema_extra={"example": "2025-11-01T12:00:00Z"},
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp when job was queued",
    )
    correlation_id: str = Field(
        ...,
        min_length=36,
        max_length=36,
        description="Request correlation ID for distributed tracing (UUID v4 format)",
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440000"},
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "ticket_id": "TKT-001",
                "tenant_id": "tenant-abc",
                "description": "Server is slow and unresponsive",
                "priority": "high",
                "timestamp": "2025-11-01T12:00:00Z",
                "created_at": "2025-11-01T12:00:05.123456Z",
                "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        }
    }

    @field_validator("correlation_id")
    @classmethod
    def validate_correlation_id_format(cls, v: str) -> str:
        """
        Validate correlation_id is in UUID v4 format (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx).

        Args:
            v: Correlation ID value to validate

        Returns:
            Validated correlation ID

        Raises:
            ValueError: If correlation_id is not in UUID v4 format
        """
        import re
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        if not re.match(uuid_pattern, v, re.IGNORECASE):
            raise ValueError(
                "correlation_id must be in UUID v4 format "
                "(e.g., '550e8400-e29b-41d4-a716-446655440000')"
            )
        return v
