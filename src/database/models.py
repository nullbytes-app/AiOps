"""
SQLAlchemy database models for the AI Agents application.

This module defines all database models (tables) using SQLAlchemy ORM.
Models support async operations and multi-tenant isolation via row-level security.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Integer,
    func,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
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
