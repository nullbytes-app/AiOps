"""
SQLAlchemy database models for the AI Agents application.

This module defines all database models (tables) using SQLAlchemy ORM.
Models support async operations and multi-tenant isolation via row-level security.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    func,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship
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
        rate_limits: JSON object with per-tenant rate limit configuration
        is_active: Boolean flag for soft delete (False = inactive/deleted)
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
    rate_limits: dict = Column(
        JSON,
        nullable=True,
        default=lambda: {"webhooks": {"ticket_created": 100, "ticket_resolved": 100}},
        doc="Per-tenant rate limit configuration (JSONB). Default: 100 webhooks/min per endpoint",
    )
    is_active: bool = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="TRUE",
        doc="Soft delete flag - FALSE indicates tenant is inactive (soft deleted)",
    )
    tool_type: str = Column(
        String(50),
        nullable=False,
        default="servicedesk_plus",
        server_default="servicedesk_plus",
        index=True,
        doc="Ticketing tool type for plugin routing (e.g., 'servicedesk_plus', 'jira', 'zendesk')",
    )

    # LiteLLM Virtual Key columns (Story 8.9)
    litellm_virtual_key: str = Column(
        Text,
        nullable=True,
        doc="Encrypted LiteLLM virtual key for per-tenant cost tracking",
    )
    litellm_key_created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when LiteLLM virtual key was created",
    )
    litellm_key_last_rotated: datetime = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when LiteLLM virtual key was last rotated",
    )

    # Budget Enforcement columns (Story 8.10)
    max_budget: float = Column(
        Float,
        nullable=False,
        default=500.00,
        server_default="500.00",
        doc="Maximum LLM budget in USD per budget period (default: $500)",
    )
    alert_threshold: int = Column(
        Integer,
        nullable=False,
        default=80,
        server_default="80",
        doc="Budget alert threshold percentage 50-100% (default: 80%)",
    )
    grace_threshold: int = Column(
        Integer,
        nullable=False,
        default=110,
        server_default="110",
        doc="Budget blocking threshold percentage 100-150% (default: 110% = 10% grace)",
    )
    budget_duration: str = Column(
        String(10),
        nullable=False,
        default="30d",
        server_default="30d",
        doc="Budget reset period: '30s', '30m', '30h', '30d', '60d', '90d'",
    )
    budget_reset_at: datetime = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when budget will next reset (auto-calculated from budget_duration)",
    )
    litellm_key_last_reset: datetime = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when LiteLLM virtual key budget was last reset",
    )

    # BYOK (Bring Your Own Key) columns (Story 8.13)
    byok_enabled: bool = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="FALSE",
        doc="Flag to enable Bring Your Own Key (BYOK) mode for tenant",
    )
    byok_openai_key_encrypted: str = Column(
        Text,
        nullable=True,
        doc="Fernet-encrypted OpenAI API key for BYOK tenants",
    )
    byok_anthropic_key_encrypted: str = Column(
        Text,
        nullable=True,
        doc="Fernet-encrypted Anthropic API key for BYOK tenants",
    )
    byok_virtual_key: str = Column(
        Text,
        nullable=True,
        doc="LiteLLM virtual key for BYOK tenant (separate from platform litellm_virtual_key)",
    )
    byok_enabled_at: datetime = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when BYOK was enabled (audit trail)",
    )


class BudgetOverride(Base):
    """
    Temporary budget overrides granted by platform admins.

    Tracks temporary budget increases for specific tenants, typically granted
    during traffic spikes, marketing campaigns, or other exceptional circumstances.
    Overrides automatically expire after the specified duration.

    Attributes:
        id: Integer primary key
        tenant_id: Foreign key to tenant_configs.tenant_id
        override_amount: Temporary budget increase in USD
        expires_at: Expiration timestamp (override no longer active after this)
        reason: Admin explanation for granting override
        created_by: Username of admin who granted override
        created_at: Creation timestamp
    """

    __tablename__ = "budget_overrides"

    id: int = Column(
        Integer,
        primary_key=True,
        nullable=False,
        doc="Integer primary key",
    )
    tenant_id: str = Column(
        String(100),
        ForeignKey("tenant_configs.tenant_id"),
        nullable=False,
        index=True,
        doc="Tenant ID (foreign key to tenant_configs)",
    )
    override_amount: float = Column(
        Float,
        nullable=False,
        doc="Temporary budget increase amount in USD",
    )
    expires_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="When the temporary override expires (no longer active after this)",
    )
    reason: str = Column(
        Text,
        nullable=False,
        doc="Admin reason for granting budget override (e.g., 'marketing campaign', 'traffic spike')",
    )
    created_by: str = Column(
        String(255),
        nullable=False,
        doc="Username of admin who granted override",
    )
    created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Creation timestamp",
    )


class BudgetAlertHistory(Base):
    """
    Historical record of budget alerts for dashboard display and analytics.

    Stores all budget-related events (threshold_crossed, budget_crossed,
    projected_limit_exceeded) received from LiteLLM proxy webhooks. Used for
    displaying alert history in tenant dashboard and analyzing usage patterns.

    Attributes:
        id: Integer primary key
        tenant_id: Foreign key to tenant_configs.tenant_id
        event_type: LiteLLM event type (threshold_crossed, budget_crossed, etc.)
        spend: Current spend in USD at time of alert
        max_budget: Max budget in USD at time of alert
        percentage: Percentage used (spend/max_budget * 100)
        created_at: Creation timestamp (when alert was received)
    """

    __tablename__ = "budget_alert_history"

    id: int = Column(
        Integer,
        primary_key=True,
        nullable=False,
        doc="Integer primary key",
    )
    tenant_id: str = Column(
        String(100),
        ForeignKey("tenant_configs.tenant_id"),
        nullable=False,
        index=True,
        doc="Tenant ID (foreign key to tenant_configs)",
    )
    event_type: str = Column(
        String(50),
        nullable=False,
        doc="LiteLLM event type: threshold_crossed, budget_crossed, projected_limit_exceeded",
    )
    spend: float = Column(
        Float,
        nullable=False,
        doc="Current spend in USD at time of alert",
    )
    max_budget: float = Column(
        Float,
        nullable=False,
        doc="Max budget in USD at time of alert",
    )
    percentage: int = Column(
        Integer,
        nullable=False,
        doc="Percentage used (spend/max_budget * 100)",
    )
    created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        doc="Creation timestamp (when alert was received)",
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
    __table_args__ = (Index("ix_enhancement_history_tenant_ticket", "tenant_id", "ticket_id"),)


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


class SystemInventory(Base):
    """
    System inventory records for IP address cross-reference.

    Stores information about systems and their IP addresses (both IPv4 and IPv6).
    Enables the enhancement agent to identify which systems are affected based on
    IP addresses mentioned in ticket descriptions. Supports multi-tenant isolation.

    Attributes:
        id: UUID primary key (globally unique)
        tenant_id: Tenant identifier for multi-tenant isolation
        ip_address: IPv4 or IPv6 address (stored as string, indexed)
        hostname: System hostname
        role: System role/function (e.g., 'web', 'db', 'cache')
        client: Client/project name associated with system
        location: Physical or logical location of system
        created_at: Timestamp when record was created
        updated_at: Timestamp when record was last updated
    """

    __tablename__ = "system_inventory"

    id: UUID = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        doc="Globally unique system inventory record ID",
    )
    tenant_id: str = Column(
        String(100),
        nullable=False,
        index=True,
        doc="Tenant identifier for multi-tenant isolation",
    )
    ip_address: str = Column(
        String(45),  # Max length for IPv6 addresses
        nullable=False,
        index=True,
        doc="IPv4 or IPv6 address",
    )
    hostname: str = Column(
        String(255),
        nullable=False,
        doc="System hostname",
    )
    role: str = Column(
        String(100),
        nullable=False,
        doc="System role/function (e.g., 'web', 'db', 'cache')",
    )
    client: str = Column(
        String(255),
        nullable=False,
        doc="Client/project name associated with system",
    )
    location: str = Column(
        String(255),
        nullable=False,
        doc="Physical or logical location of system",
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

    # Composite indexes for efficient searching and data isolation
    # UNIQUE constraint on (tenant_id, ip_address) prevents duplicates per tenant
    __table_args__ = (
        Index("ix_system_inventory_tenant_id", "tenant_id"),
        Index("ix_system_inventory_ip_address", "ip_address"),
        Index("ix_system_inventory_tenant_ip", "tenant_id", "ip_address"),
        UniqueConstraint("tenant_id", "ip_address", name="uq_system_inventory_tenant_ip"),
    )


class EnhancementFeedback(Base):
    """
    Client feedback and satisfaction ratings for ticket enhancements.

    Enables technicians to rate enhancement quality with thumbs up/down or 1-5 scale.
    Supports continuous quality monitoring, trend analysis, and product roadmap
    prioritization based on user satisfaction data. Implements row-level security
    for multi-tenant isolation.

    Attributes:
        id: UUID primary key (globally unique)
        tenant_id: Tenant identifier for multi-tenant isolation (references tenant_configs)
        ticket_id: ServiceDesk ticket ID that was enhanced
        enhancement_id: Reference to enhancement_history record (optional but recommended)
        technician_email: Email of technician providing feedback (optional, for attribution)
        feedback_type: Type of feedback - 'thumbs_up', 'thumbs_down', or 'rating'
        rating_value: Numeric rating 1-5 (required if feedback_type='rating', null otherwise)
        feedback_comment: Optional qualitative feedback text from technician
        created_at: Timestamp when feedback was submitted
    """

    __tablename__ = "enhancement_feedback"

    id: UUID = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        doc="Globally unique feedback record ID",
    )
    tenant_id: str = Column(
        String(100),
        nullable=False,
        index=True,
        doc="Tenant identifier for multi-tenant isolation",
    )
    ticket_id: str = Column(
        String(255),
        nullable=False,
        doc="ServiceDesk ticket ID that was enhanced",
    )
    enhancement_id: Optional[UUID] = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Reference to enhancement_history.id (optional, for correlation)",
    )
    technician_email: Optional[str] = Column(
        String(255),
        nullable=True,
        doc="Email of technician providing feedback (optional, supports anonymous feedback)",
    )
    feedback_type: str = Column(
        String(50),
        nullable=False,
        doc="Feedback type: 'thumbs_up', 'thumbs_down', or 'rating'",
    )
    rating_value: Optional[int] = Column(
        Integer,
        nullable=True,
        doc="Numeric rating 1-5 (required if feedback_type='rating', null for thumbs up/down)",
    )
    feedback_comment: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Optional qualitative feedback text from technician",
    )
    created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Feedback submission timestamp",
    )

    # Composite indexes for efficient querying and analytics
    # Index on tenant_id for RLS enforcement and multi-tenant queries
    # Index on created_at for time-based aggregations and trend analysis
    # Index on feedback_type for sentiment analysis (thumbs up/down distribution)
    # Composite index on (tenant_id, ticket_id) for per-ticket feedback retrieval
    __table_args__ = (
        Index("ix_enhancement_feedback_tenant_id", "tenant_id"),
        Index("ix_enhancement_feedback_created_at", "created_at"),
        Index("ix_enhancement_feedback_feedback_type", "feedback_type"),
        Index("ix_enhancement_feedback_tenant_ticket", "tenant_id", "ticket_id"),
    )


class AuditLog(Base):
    """
    Audit log for system operations tracking.

    Stores all system operations performed through the admin UI for compliance,
    troubleshooting, and security auditing. Each operation (pause/resume processing,
    queue clearing, config sync) creates an audit log entry.

    Attributes:
        id: UUID primary key (globally unique)
        timestamp: UTC timestamp when operation was performed
        user: Username or identifier of user who performed operation
        operation: Operation name (e.g., "pause_processing", "clear_queue")
        details: JSON object with operation-specific details
        status: Operation status ("success", "failure", "in_progress")
    """

    __tablename__ = "audit_log"

    id: UUID = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        doc="Globally unique audit log entry ID",
    )
    timestamp: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        doc="UTC timestamp when operation was performed",
    )
    user: str = Column(
        String(255),
        nullable=False,
        doc="Username or identifier of user who performed operation",
    )
    operation: str = Column(
        String(100),
        nullable=False,
        index=True,
        doc="Operation name (e.g., 'pause_processing', 'clear_queue')",
    )
    details: dict = Column(
        JSON,
        nullable=True,
        default=dict,
        doc="JSON object with operation-specific details",
    )
    status: str = Column(
        String(50),
        nullable=False,
        doc="Operation status: 'success', 'failure', or 'in_progress'",
    )

    # Indexes for efficient querying
    # Index on timestamp DESC for "recent operations" queries
    # Index on operation for filtering by operation type
    __table_args__ = (
        Index("ix_audit_log_timestamp", "timestamp", postgresql_ops={"timestamp": "DESC"}),
        Index("ix_audit_log_operation", "operation"),
    )


class Agent(Base):
    """
    AI Agent configuration and management.

    Stores dynamic AI agent definitions with LLM configuration, system prompts,
    and status management. Enables multi-tenant agent orchestration where each
    tenant can create and manage their own custom agents for ticket processing.

    Attributes:
        id: UUID primary key (globally unique)
        tenant_id: Tenant identifier for multi-tenant isolation
        name: Human-readable agent name
        description: Detailed description of agent purpose
        status: Agent status (draft, active, suspended, inactive)
        system_prompt: LLM system prompt defining agent behavior
        llm_config: JSONB configuration for LLM (model, temperature, max_tokens)
        created_at: Timestamp when agent was created
        updated_at: Timestamp when agent was last updated
        created_by: User who created the agent
        triggers: Relationship to AgentTrigger (webhook/schedule triggers)
        tools: Relationship to AgentTool (assigned plugin tools)
    """

    __tablename__ = "agents"

    id: UUID = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        doc="Globally unique agent ID",
    )
    tenant_id: str = Column(
        String(100),
        nullable=False,
        index=True,
        doc="Tenant identifier for multi-tenant isolation",
    )
    name: str = Column(
        String(255),
        nullable=False,
        doc="Human-readable agent name",
    )
    description: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Detailed description of agent purpose",
    )
    status: str = Column(
        String(20),
        nullable=False,
        index=True,
        doc="Agent status: draft, active, suspended, inactive",
    )
    system_prompt: str = Column(
        Text,
        nullable=False,
        doc="LLM system prompt defining agent behavior (up to 32K chars)",
    )
    llm_config: dict = Column(
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
        doc="JSONB configuration for LLM (provider, model, temperature, max_tokens)",
    )
    created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Agent creation timestamp",
    )
    updated_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Last modification timestamp",
    )
    created_by: Optional[str] = Column(
        String(255),
        nullable=True,
        doc="User who created the agent",
    )

    # Relationships
    triggers = relationship("AgentTrigger", back_populates="agent", cascade="all, delete-orphan")
    tools = relationship("AgentTool", back_populates="agent", cascade="all, delete-orphan")

    # Composite index for (tenant_id, status) - primary query pattern
    # Descending index on created_at for "recent agents" queries
    __table_args__ = (
        Index("idx_agents_tenant_id_status", "tenant_id", "status"),
        Index("idx_agents_created_at", "created_at", postgresql_ops={"created_at": "DESC"}),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<Agent(id={self.id}, name={self.name}, status={self.status})>"


class AgentTrigger(Base):
    """
    Agent trigger configuration (webhook or schedule).

    Defines how an agent is invoked - either via webhook (HTTP POST) or
    scheduled execution (cron). Each agent can have multiple triggers of
    different types. Webhook triggers include HMAC signature validation.

    Attributes:
        id: UUID primary key (globally unique)
        agent_id: Foreign key to agents table (CASCADE delete)
        trigger_type: Trigger type (webhook or schedule)
        webhook_url: Auto-generated webhook endpoint URL
        hmac_secret: Fernet-encrypted HMAC signing secret for webhook validation
        schedule_cron: Cron expression for scheduled execution
        payload_schema: JSON schema for webhook payload validation
        created_at: Timestamp when trigger was created
        updated_at: Timestamp when trigger was last updated
        agent: Relationship to Agent
    """

    __tablename__ = "agent_triggers"

    id: UUID = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        doc="Globally unique trigger ID",
    )
    agent_id: UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to agents table",
    )
    trigger_type: str = Column(
        String(50),
        nullable=False,
        doc="Trigger type: webhook or schedule",
    )
    webhook_url: Optional[str] = Column(
        String(500),
        nullable=True,
        doc="Auto-generated webhook endpoint URL",
    )
    hmac_secret: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Fernet-encrypted HMAC signing secret for webhook validation",
    )
    schedule_cron: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="Cron expression for scheduled execution",
    )
    payload_schema: Optional[dict] = Column(
        JSON,
        nullable=True,
        doc="JSON schema for webhook payload validation",
    )
    created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Trigger creation timestamp",
    )
    updated_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Last modification timestamp",
    )

    # Relationship
    agent = relationship("Agent", back_populates="triggers")

    # Index on agent_id for fast trigger lookups per agent
    __table_args__ = (Index("idx_agent_triggers_agent_id", "agent_id"),)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<AgentTrigger(id={self.id}, type={self.trigger_type}, agent_id={self.agent_id})>"


class AgentTool(Base):
    """
    Agent-Tool junction table (many-to-many).

    Links agents to plugin tools via tool_id. Enables assigning multiple
    tools (e.g., ServiceDesk Plus, Jira) to an agent. Tool IDs reference
    registered plugin identifiers from the PluginManager.

    Attributes:
        agent_id: Foreign key to agents table (composite PK, CASCADE delete)
        tool_id: Plugin tool identifier (composite PK, e.g., "servicedesk_plus", "jira")
        created_at: Timestamp when tool was assigned
        agent: Relationship to Agent
    """

    __tablename__ = "agent_tools"

    agent_id: UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        doc="Foreign key to agents table",
    )
    tool_id: str = Column(
        String(100),
        primary_key=True,
        nullable=False,
        doc="Plugin tool identifier (e.g., 'servicedesk_plus', 'jira')",
    )
    created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Tool assignment timestamp",
    )

    # Relationship
    agent = relationship("Agent", back_populates="tools")

    # Indexes for bi-directional lookups (agent→tools and tool→agents)
    __table_args__ = (
        Index("idx_agent_tools_agent_id", "agent_id"),
        Index("idx_agent_tools_tool_id", "tool_id"),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<AgentTool(agent_id={self.agent_id}, tool_id={self.tool_id})>"



class AgentPromptVersion(Base):
    """
    Immutable history of agent system prompt versions.

    Tracks all changes to agent prompts with timestamps and metadata.
    Enables reverting to previous prompts and auditing prompt evolution.

    Attributes:
        id: UUID primary key
        agent_id: Foreign key to Agent (cascade delete)
        prompt_text: The system prompt text (immutable after insert)
        created_at: When this version was created
        created_by: User who created this version
        description: Optional description of changes (e.g., "Updated for better RCA analysis")
        is_current: Boolean flag indicating if this is the agent's active prompt
    """

    __tablename__ = "agent_prompt_versions"

    id: UUID = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        doc="Globally unique version ID",
    )
    agent_id: UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Agent this prompt version belongs to",
    )
    prompt_text: str = Column(
        Text,
        nullable=False,
        doc="System prompt text (complete, immutable)",
    )
    created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Version creation timestamp",
    )
    created_by: Optional[str] = Column(
        String(255),
        nullable=True,
        doc="User who created this version",
    )
    description: Optional[str] = Column(
        String(500),
        nullable=True,
        doc="Optional description of what changed",
    )
    is_current: bool = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        doc="True if this is the agent's active prompt",
    )

    # Indexes for common queries
    __table_args__ = (
        Index(
            "idx_agent_prompt_versions_agent_id_created_at",
            "agent_id",
            "created_at",
            postgresql_ops={"created_at": "DESC"},
        ),
        Index("idx_agent_prompt_versions_agent_id_is_current", "agent_id", "is_current"),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<AgentPromptVersion(agent_id={self.agent_id}, is_current={self.is_current})>"


class AgentPromptTemplate(Base):
    """
    Reusable system prompt templates for agents.

    Stores both built-in templates (shared across all tenants) and custom
    templates (tenant-scoped). Enables rapid agent creation with predefined prompts.

    Attributes:
        id: UUID primary key
        tenant_id: Tenant identifier (NULL for built-in templates)
        name: Template name (e.g., "Ticket Enhancement")
        description: Purpose and usage description
        template_text: The actual prompt template (supports {{variable}} placeholders)
        is_builtin: True for templates included with system
        is_active: False for soft-deleted templates
        created_by: User who created this template
        created_at: Creation timestamp
        updated_at: Last modification timestamp
    """

    __tablename__ = "agent_prompt_templates"

    id: UUID = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        doc="Globally unique template ID",
    )
    tenant_id: Optional[str] = Column(
        String(100),
        nullable=True,
        index=True,
        doc="Tenant for custom templates; NULL for built-in",
    )
    name: str = Column(
        String(255),
        nullable=False,
        doc="Template name (e.g., 'Ticket Enhancement')",
    )
    description: str = Column(
        Text,
        nullable=False,
        doc="Purpose and usage description",
    )
    template_text: str = Column(
        Text,
        nullable=False,
        doc="Prompt template with {{variable}} placeholders",
    )
    is_builtin: bool = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        doc="True for system-provided templates",
    )
    is_active: bool = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        doc="False for soft-deleted templates",
    )
    created_by: Optional[str] = Column(
        String(255),
        nullable=True,
        doc="User who created this template",
    )
    created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Template creation timestamp",
    )
    updated_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Last modification timestamp",
    )

    # Indexes for common queries
    __table_args__ = (
        Index("idx_prompt_templates_builtin_active", "is_builtin", "is_active"),
        Index("idx_prompt_templates_tenant_id_active", "tenant_id", "is_active"),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<AgentPromptTemplate(name={self.name}, is_builtin={self.is_builtin})>"



class OpenAPITool(Base):
    """
    OpenAPI tool configuration for dynamic MCP tool generation.

    Stores uploaded OpenAPI specifications and authentication config for
    automatic FastMCP tool generation. Supports multi-tenancy with encrypted
    credentials storage.

    Attributes:
        id: Serial primary key
        tenant_id: Tenant identifier for multi-tenant isolation
        tool_name: Unique tool name (unique per tenant)
        openapi_spec: Full OpenAPI spec (JSONB)
        spec_version: OpenAPI version (2.0, 3.0, 3.1)
        base_url: API base URL
        auth_config_encrypted: Encrypted authentication config (Fernet)
        status: Tool status (active, inactive)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        created_by: User who created the tool
    """

    __tablename__ = "openapi_tools"

    id: int = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        nullable=False,
        doc="Tool ID",
    )
    tenant_id: int = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Tenant identifier for multi-tenant isolation",
    )
    tool_name: str = Column(
        String(255),
        nullable=False,
        doc="Tool name from OpenAPI spec",
    )
    openapi_spec: dict = Column(
        JSON,
        nullable=False,
        doc="Full OpenAPI specification (JSONB)",
    )
    spec_version: str = Column(
        String(10),
        nullable=False,
        doc="OpenAPI version: 2.0, 3.0, 3.1",
    )
    base_url: str = Column(
        Text,
        nullable=False,
        doc="API base URL",
    )
    auth_config_encrypted: Optional[bytes] = Column(
        LargeBinary,
        nullable=True,
        doc="Encrypted authentication config (Fernet)",
    )
    status: str = Column(
        String(20),
        nullable=False,
        server_default="active",
        doc="Tool status: active, inactive",
    )
    created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Tool creation timestamp",
    )
    updated_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Last modification timestamp",
    )
    created_by: Optional[str] = Column(
        String(100),
        nullable=True,
        doc="User who created the tool",
    )

    __table_args__ = (
        Index("idx_openapi_tools_status", "status"),
        Index("idx_openapi_tools_tenant", "tenant_id"),
        UniqueConstraint("tenant_id", "tool_name", name="uq_tenant_tool_name"),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<OpenAPITool(id={self.id}, name={self.tool_name}, status={self.status})>"


class ProviderType(str, Enum):
    """
    LLM provider types supported by the platform.

    Enum values map to LiteLLM provider identifiers.
    """

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    BEDROCK = "bedrock"
    REPLICATE = "replicate"
    TOGETHER_AI = "together_ai"
    CUSTOM = "custom"


class LLMProvider(Base):
    """
    LLM provider configuration and credentials.

    Stores provider-specific configuration including encrypted API keys,
    base URLs, and connection test results. Supports multiple providers
    (OpenAI, Anthropic, Azure OpenAI, etc.) with encrypted credential storage.

    Attributes:
        id: Primary key
        name: Provider display name (e.g., "Production OpenAI", "Azure GPT-4")
        provider_type: Provider identifier (openai, anthropic, azure_openai, etc.)
        api_base_url: API endpoint base URL
        api_key_encrypted: Fernet-encrypted API key
        enabled: Soft delete flag (false = disabled/deleted)
        last_test_at: Timestamp of last connection test
        last_test_success: Result of last connection test (null if never tested)
        created_at: Creation timestamp
        updated_at: Last modification timestamp
    """

    __tablename__ = "llm_providers"

    id: int = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        nullable=False,
        doc="Primary key",
    )
    name: str = Column(
        String(255),
        unique=True,
        nullable=False,
        doc="Provider display name (must be unique)",
    )
    provider_type: str = Column(
        String(50),
        nullable=False,
        doc="Provider type enum value",
    )
    api_base_url: str = Column(
        Text,
        nullable=False,
        doc="API base URL (e.g., https://api.openai.com/v1)",
    )
    api_key_encrypted: str = Column(
        Text,
        nullable=False,
        doc="Fernet-encrypted API key",
    )
    enabled: bool = Column(
        Boolean,
        nullable=False,
        server_default="TRUE",
        doc="Provider enabled status",
    )
    last_test_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of last connection test",
    )
    last_test_success: Optional[bool] = Column(
        Boolean,
        nullable=True,
        doc="Last test result (null if never tested)",
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

    # Relationship to models (one-to-many)
    models = relationship(
        "LLMModel",
        back_populates="provider",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("idx_llm_providers_type", "provider_type"),
        Index("idx_llm_providers_enabled", "enabled"),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<LLMProvider(id={self.id}, name={self.name}, type={self.provider_type}, enabled={self.enabled})>"


class LLMModel(Base):
    """
    LLM model configuration and pricing.

    Stores model-specific configuration including pricing (cost per token),
    context window size, and capabilities. Models belong to a provider
    and are enabled/disabled individually for LiteLLM config generation.

    Attributes:
        id: Primary key
        provider_id: Foreign key to llm_providers
        model_name: Model identifier (e.g., "gpt-4", "claude-3-5-sonnet-20240620")
        display_name: User-friendly display name (optional)
        enabled: Model enabled in LiteLLM config (default: false)
        cost_per_input_token: Cost per 1M input tokens in USD
        cost_per_output_token: Cost per 1M output tokens in USD
        context_window: Maximum context window in tokens
        capabilities: JSONB with model capabilities (streaming, function_calling, vision)
        created_at: Creation timestamp
        updated_at: Last modification timestamp
    """

    __tablename__ = "llm_models"

    id: int = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        nullable=False,
        doc="Primary key",
    )
    provider_id: int = Column(
        Integer,
        ForeignKey("llm_providers.id", ondelete="CASCADE"),
        nullable=False,
        doc="Foreign key to provider (CASCADE delete)",
    )
    model_name: str = Column(
        String(255),
        nullable=False,
        doc="Model identifier",
    )
    display_name: Optional[str] = Column(
        String(255),
        nullable=True,
        doc="User-friendly display name",
    )
    enabled: bool = Column(
        Boolean,
        nullable=False,
        server_default="FALSE",
        doc="Model enabled status (default: disabled)",
    )
    cost_per_input_token: Optional[float] = Column(
        Float,
        nullable=True,
        doc="Cost per 1M input tokens (USD)",
    )
    cost_per_output_token: Optional[float] = Column(
        Float,
        nullable=True,
        doc="Cost per 1M output tokens (USD)",
    )
    context_window: Optional[int] = Column(
        Integer,
        nullable=True,
        doc="Context window size (tokens)",
    )
    capabilities: Optional[dict] = Column(
        JSONB,
        nullable=True,
        doc="Model capabilities JSONB",
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

    # Relationship to provider (many-to-one)
    provider = relationship("LLMProvider", back_populates="models")

    __table_args__ = (
        UniqueConstraint("provider_id", "model_name", name="uq_llm_models_provider_model"),
        Index("idx_llm_models_provider", "provider_id"),
        Index("idx_llm_models_enabled", "enabled"),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<LLMModel(id={self.id}, name={self.model_name}, provider_id={self.provider_id}, enabled={self.enabled})>"


class FallbackChain(Base):
    """
    Fallback chain configuration for LLM models.

    Maps primary models to ordered fallback models for automatic failover.
    When primary model fails with specific error types, system attempts
    fallback models in order until success or all fallbacks exhausted.

    Attributes:
        id: Primary key
        model_id: Primary model ID (FK to llm_models)
        fallback_order: Order in fallback chain (0=primary, 1=first fallback, etc)
        fallback_model_id: Fallback model ID (FK to llm_models)
        enabled: Chain enabled status (default: true)
        created_at: Creation timestamp
        updated_at: Last modification timestamp
    """

    __tablename__ = "fallback_chains"

    id: int = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        nullable=False,
        doc="Primary key",
    )
    model_id: int = Column(
        Integer,
        ForeignKey("llm_models.id", ondelete="CASCADE"),
        nullable=False,
        doc="Primary model ID (FK to llm_models)",
    )
    fallback_order: int = Column(
        Integer,
        nullable=False,
        doc="Order in fallback chain (0=primary, 1=first fallback, etc)",
    )
    fallback_model_id: int = Column(
        Integer,
        ForeignKey("llm_models.id", ondelete="CASCADE"),
        nullable=False,
        doc="Fallback model ID (FK to llm_models)",
    )
    enabled: bool = Column(
        Boolean,
        nullable=False,
        server_default="TRUE",
        doc="Chain enabled status (default: enabled)",
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

    # Relationships
    model = relationship(
        "LLMModel",
        foreign_keys=[model_id],
        primaryjoin="FallbackChain.model_id == LLMModel.id",
    )
    fallback_model = relationship(
        "LLMModel",
        foreign_keys=[fallback_model_id],
        primaryjoin="FallbackChain.fallback_model_id == LLMModel.id",
    )

    __table_args__ = (
        UniqueConstraint(
            "model_id",
            "fallback_order",
            name="uq_fallback_chains_model_order",
        ),
        Index("idx_fallback_chains_model_id", "model_id"),
        Index("idx_fallback_chains_fallback_model_id", "fallback_model_id"),
        Index("idx_fallback_chains_enabled", "enabled"),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<FallbackChain(id={self.id}, model_id={self.model_id}, fallback_order={self.fallback_order}, fallback_model_id={self.fallback_model_id}, enabled={self.enabled})>"


class FallbackTrigger(Base):
    """
    Fallback trigger configuration for specific error types.

    Configures retry and backoff behavior for different error types
    (RateLimitError, TimeoutError, InternalServerError, ConnectionError, etc).
    Each trigger type has independent retry count and backoff factor settings.

    Attributes:
        id: Primary key
        trigger_type: Error type (RateLimitError, TimeoutError, InternalServerError, ConnectionError, ContentPolicyViolationError)
        retry_count: Number of retry attempts before fallback (0-10, default 3)
        backoff_factor: Exponential backoff multiplier (1.0-5.0, default 2.0)
        enabled: Trigger enabled status (default: true)
        created_at: Creation timestamp
    """

    __tablename__ = "fallback_triggers"

    id: int = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        nullable=False,
        doc="Primary key",
    )
    trigger_type: str = Column(
        String(50),
        nullable=False,
        doc="Error type: RateLimitError, TimeoutError, InternalServerError, ConnectionError, ContentPolicyViolationError",
    )
    retry_count: int = Column(
        Integer,
        nullable=False,
        server_default="3",
        doc="Number of retry attempts before fallback (0-10)",
    )
    backoff_factor: float = Column(
        Float,
        nullable=False,
        server_default="2.0",
        doc="Exponential backoff multiplier (1.0-5.0)",
    )
    enabled: bool = Column(
        Boolean,
        nullable=False,
        server_default="TRUE",
        doc="Trigger enabled status (default: enabled)",
    )
    created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Creation timestamp",
    )

    __table_args__ = (
        UniqueConstraint("trigger_type", name="uq_fallback_triggers_type"),
        Index("idx_fallback_triggers_type", "trigger_type"),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<FallbackTrigger(id={self.id}, trigger_type={self.trigger_type}, retry_count={self.retry_count}, backoff_factor={self.backoff_factor}, enabled={self.enabled})>"


class FallbackMetric(Base):
    """
    Fallback event metrics and statistics.

    Records metrics for fallback trigger events including trigger type,
    fallback model used, success/failure counts, and timing data for analytics
    and monitoring fallback effectiveness.

    Attributes:
        id: Primary key
        model_id: Model ID (FK to llm_models)
        trigger_type: Error type that triggered fallback
        fallback_model_id: Fallback model used (FK to llm_models)
        trigger_count: Number of times this fallback was triggered
        success_count: Number of successful fallback resolutions
        failure_count: Number of failed fallback attempts
        last_triggered_at: Timestamp of last trigger
        created_at: Creation timestamp
        updated_at: Last modification timestamp
    """

    __tablename__ = "fallback_metrics"

    id: int = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        nullable=False,
        doc="Primary key",
    )
    model_id: int = Column(
        Integer,
        ForeignKey("llm_models.id", ondelete="CASCADE"),
        nullable=False,
        doc="Model ID (FK to llm_models)",
    )
    trigger_type: str = Column(
        String(50),
        nullable=False,
        doc="Error type that triggered fallback",
    )
    fallback_model_id: Optional[int] = Column(
        Integer,
        ForeignKey("llm_models.id", ondelete="SET NULL"),
        nullable=True,
        doc="Fallback model used (FK to llm_models)",
    )
    trigger_count: int = Column(
        Integer,
        nullable=False,
        server_default="1",
        doc="Number of times this fallback was triggered",
    )
    success_count: int = Column(
        Integer,
        nullable=False,
        server_default="0",
        doc="Number of successful fallback resolutions",
    )
    failure_count: int = Column(
        Integer,
        nullable=False,
        server_default="0",
        doc="Number of failed fallback attempts",
    )
    last_triggered_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of last trigger",
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

    # Relationships
    model = relationship(
        "LLMModel",
        foreign_keys=[model_id],
        primaryjoin="FallbackMetric.model_id == LLMModel.id",
    )
    fallback_model = relationship(
        "LLMModel",
        foreign_keys=[fallback_model_id],
        primaryjoin="FallbackMetric.fallback_model_id == LLMModel.id",
    )

    __table_args__ = (
        Index("idx_fallback_metrics_model_id", "model_id"),
        Index("idx_fallback_metrics_fallback_model_id", "fallback_model_id"),
        Index("idx_fallback_metrics_trigger_type", "trigger_type"),
        Index("idx_fallback_metrics_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<FallbackMetric(id={self.id}, model_id={self.model_id}, trigger_type={self.trigger_type}, fallback_model_id={self.fallback_model_id}, success_count={self.success_count})>"
