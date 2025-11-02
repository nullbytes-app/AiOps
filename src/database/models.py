"""
SQLAlchemy database models for the AI Agents application.

This module defines all database models (tables) using SQLAlchemy ORM.
Models support async operations and multi-tenant isolation via row-level security.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Index,
    String,
    Text,
    Integer,
    func,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid

# Base class for all database models
Base = declarative_base()


class TenantConfig(Base):
    """
    Multi-tenant configuration storage.

    Stores per-tenant settings including ServiceDesk Plus credentials,
    webhook secrets, and enhancement preferences. All sensitive data
    (API keys, secrets) are encrypted at the application layer.

    Attributes:
        id: UUID primary key (globally unique)
        tenant_id: Unique tenant identifier (string)
        name: Human-readable tenant name
        servicedesk_url: ServiceDesk Plus instance URL
        servicedesk_api_key_encrypted: Encrypted ServiceDesk API key
        webhook_signing_secret_encrypted: Encrypted webhook secret for validation
        enhancement_preferences: JSON object with tenant-specific settings
        created_at: Timestamp when configuration was created
        updated_at: Timestamp when configuration was last updated
    """

    __tablename__ = "tenant_configs"

    id: UUID = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        doc="Globally unique tenant configuration ID",
    )
    tenant_id: str = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique tenant identifier",
    )
    name: str = Column(
        String(255),
        nullable=False,
        doc="Human-readable tenant name",
    )
    servicedesk_url: str = Column(
        String(500),
        nullable=False,
        doc="ServiceDesk Plus instance URL",
    )
    servicedesk_api_key_encrypted: str = Column(
        Text,
        nullable=False,
        doc="Encrypted ServiceDesk API key",
    )
    webhook_signing_secret_encrypted: str = Column(
        Text,
        nullable=False,
        doc="Encrypted webhook signing secret",
    )
    enhancement_preferences: dict = Column(
        JSON,
        nullable=False,
        default=dict,
        doc="JSON object with tenant-specific enhancement preferences",
    )
    created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Creation timestamp",
    )
    updated_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Last modification timestamp",
    )


class EnhancementHistory(Base):
    """
    Audit trail and tracking for enhancement operations.

    Records every enhancement request processed through the system,
    including status, context gathered, LLM output, and performance metrics.
    Used for auditing, debugging, and analytics.

    Attributes:
        id: UUID primary key (globally unique)
        tenant_id: Tenant identifier for multi-tenant isolation
        ticket_id: ServiceDesk ticket being enhanced
        status: Current status (pending, completed, failed)
        context_gathered: JSON object containing gathered context from all sources
        llm_output: Full LLM response text
        error_message: Error details if status=failed
        processing_time_ms: Total processing time in milliseconds
        created_at: Timestamp when enhancement was requested
        completed_at: Timestamp when processing finished (null if still pending)
    """

    __tablename__ = "enhancement_history"

    id: UUID = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        doc="Globally unique enhancement record ID",
    )
    tenant_id: str = Column(
        String(100),
        nullable=False,
        index=True,
        doc="Tenant identifier",
    )
    ticket_id: str = Column(
        String(100),
        nullable=False,
        index=True,
        doc="ServiceDesk ticket ID",
    )
    status: str = Column(
        String(50),
        nullable=False,
        index=True,
        doc="Enhancement status: pending, completed, failed",
    )
    context_gathered: Optional[dict] = Column(
        JSON,
        nullable=True,
        doc="Context data gathered from all sources",
    )
    llm_output: Optional[str] = Column(
        Text,
        nullable=True,
        doc="LLM-generated enhancement output",
    )
    error_message: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Error message if processing failed",
    )
    processing_time_ms: Optional[int] = Column(
        Integer,
        nullable=True,
        doc="Total processing time in milliseconds",
    )
    created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Request creation timestamp",
    )
    completed_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Processing completion timestamp",
    )

    # Create composite index on (tenant_id, ticket_id) for efficient lookups
    __table_args__ = (
        Index("ix_enhancement_history_tenant_ticket", "tenant_id", "ticket_id"),
    )


class TicketHistory(Base):
    """
    Historical ticket records for context gathering and search.

    Stores resolved tickets and their resolutions for use in similarity searches
    when processing new enhancement requests. Enables the agent to find similar
    past tickets to provide context about resolution patterns.

    Attributes:
        id: UUID primary key (globally unique)
        tenant_id: Tenant identifier for multi-tenant isolation
        ticket_id: ServiceDesk ticket ID
        description: Ticket description text (indexed for full-text search)
        resolution: Resolution or solution applied to the ticket
        resolved_date: When the ticket was resolved
        source: Data provenance - 'bulk_import' or 'webhook_resolved'
        ingested_at: Timestamp when record was ingested into system
        created_at: Timestamp when record was created
        updated_at: Timestamp when record was last updated
    """

    __tablename__ = "ticket_history"

    id: UUID = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        doc="Globally unique ticket history record ID",
    )
    tenant_id: str = Column(
        String(100),
        nullable=False,
        index=True,
        doc="Tenant identifier for multi-tenant isolation",
    )
    ticket_id: str = Column(
        String(100),
        nullable=False,
        doc="ServiceDesk ticket ID",
    )
    description: str = Column(
        Text,
        nullable=False,
        doc="Ticket description (indexed for full-text search)",
    )
    resolution: str = Column(
        Text,
        nullable=False,
        doc="Resolution or solution applied to the ticket",
    )
    resolved_date: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        doc="Timestamp when ticket was resolved",
    )
    source: str = Column(
        String(50),
        nullable=False,
        default="bulk_import",
        doc="Data provenance - 'bulk_import' or 'webhook_resolved'",
    )
    ingested_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Timestamp when record was ingested into system",
    )
    created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Record creation timestamp",
    )
    updated_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Last modification timestamp",
    )

    # Create composite indexes for efficient searching and data isolation
    # UNIQUE constraint on (tenant_id, ticket_id) ensures idempotency
    __table_args__ = (
        Index("ix_ticket_history_tenant_id", "tenant_id"),
        Index("ix_ticket_history_resolved_date", "resolved_date"),
        Index("ix_ticket_history_tenant_ticket", "tenant_id", "ticket_id"),
        UniqueConstraint("tenant_id", "ticket_id", name="uq_ticket_history_tenant_ticket"),
    )
