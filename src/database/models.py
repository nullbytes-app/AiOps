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
    CheckConstraint,
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
    desc,
    text,
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

    # Relationships
    mcp_servers = relationship(
        "MCPServer",
        back_populates="tenant",
        cascade="all, delete-orphan",
        doc="MCP servers registered for this tenant (CASCADE delete)"
    )

    mcp_metrics = relationship(
        "MCPServerMetric",
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
        doc="MCP server health metrics for this tenant (CASCADE delete)"
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


class User(Base):
    """
    User account model for authentication and authorization.

    Stores user credentials, account security settings (lockout, password expiry),
    and default tenant association. Users can have different roles across multiple
    tenants (see UserTenantRole model).

    Security features:
    - Password hashing with bcrypt (10 rounds)
    - Account lockout after 5 failed attempts (15 minutes)
    - Password expiration after 90 days
    - Password history (prevents reuse of last 5 passwords)

    Attributes:
        id: UUID primary key (globally unique)
        email: User email (unique, used for login)
        password_hash: Bcrypt hashed password (never store plain text)
        default_tenant_id: FK to tenant user belongs to by default
        failed_login_attempts: Counter for failed logins (reset on success)
        locked_until: Timestamp until which account is locked (nullable)
        password_expires_at: Timestamp when password expires (nullable)
        password_history: JSON array of last 5 password hashes
        is_active: Account active status (False for soft-deleted accounts)
        created_at: Account creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "users"

    id: UUID = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        doc="Globally unique user ID",
    )
    email: str = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="User email address (unique, used for login)",
    )
    password_hash: str = Column(
        String(255),
        nullable=False,
        doc="Bcrypt hashed password (never store plain text)",
    )
    default_tenant_id: UUID = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Default tenant ID for this user",
    )
    failed_login_attempts: int = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Counter for failed login attempts (reset on successful login)",
    )
    locked_until: datetime = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp until which account is locked (15 minutes after 5 failed attempts)",
    )
    password_expires_at: datetime = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when password expires (90 days after creation)",
    )
    password_history: list = Column(
        JSON,
        nullable=False,
        default=list,
        doc="JSON array of last 5 password hashes (prevents password reuse)",
    )
    is_active: bool = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        doc="Account active status (False for soft-deleted accounts)",
    )
    created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Account creation timestamp (UTC)",
    )
    updated_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Last update timestamp (UTC, auto-updated)",
    )

    # Indexes for efficient querying
    __table_args__ = (
        Index("ix_users_email", "email", unique=True),
    )


class RoleEnum(str, Enum):
    """
    RBAC roles for the AI Agents Platform.

    Roles are hierarchical (super_admin > tenant_admin > operator > developer > viewer).
    Each role has specific permissions defined in the permission matrix (see tech-spec).

    Roles:
        super_admin: Platform administrator (all permissions, all tenants)
        tenant_admin: Tenant administrator (all permissions within tenant)
        operator: Operations team member (can pause/resume, view executions)
        developer: Developer (can create/edit agents, test agents)
        viewer: Read-only access (can view dashboards, metrics, history)
    """

    SUPER_ADMIN = "super_admin"
    TENANT_ADMIN = "tenant_admin"
    OPERATOR = "operator"
    DEVELOPER = "developer"
    VIEWER = "viewer"


class UserTenantRole(Base):
    """
    Many-to-many relationship between users and tenants with roles.

    A user can have different roles in different tenants. For example:
    - Alice is super_admin in Tenant A
    - Alice is operator in Tenant B
    - Alice is viewer in Tenant C

    This model stores the (user, tenant, role) triples. The composite unique
    constraint ensures one role per user per tenant.

    CRITICAL: Roles are fetched on-demand from this table, NOT stored in JWT
    (see ADR 003: JWT Roles Fetched On-Demand).

    Attributes:
        id: UUID primary key (globally unique)
        user_id: FK to users table
        tenant_id: Tenant identifier (string, matches TenantConfig.tenant_id)
        role: Role enum (super_admin, tenant_admin, operator, developer, viewer)
        created_at: Role assignment timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "user_tenant_roles"

    id: UUID = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        doc="Globally unique role assignment ID",
    )
    user_id: UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="FK to users table",
    )
    tenant_id: str = Column(
        String(255),
        nullable=False,
        doc="Tenant identifier (matches TenantConfig.tenant_id)",
    )
    role: str = Column(
        String(50),
        nullable=False,
        doc="Role enum: super_admin, tenant_admin, operator, developer, viewer",
    )
    created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Role assignment timestamp (UTC)",
    )
    updated_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Last update timestamp (UTC, auto-updated)",
    )

    # Composite unique constraint: one role per user per tenant
    # Indexes for fast role lookups (CRITICAL for on-demand role fetching)
    __table_args__ = (
        UniqueConstraint("user_id", "tenant_id", name="uq_user_tenant"),
        Index("ix_user_tenant_roles_lookup", "user_id", "tenant_id"),
    )


class AuthAuditLog(Base):
    """
    Audit log for authentication events.

    Tracks all authentication attempts (login, logout, password reset, etc.)
    for security monitoring, compliance, and troubleshooting. Logs both
    successful and failed attempts.

    Use cases:
    - Detect brute force attacks (many failed logins from same IP)
    - Compliance reporting (who logged in when)
    - Troubleshooting login issues (why did login fail?)
    - Account lockout tracking (when was account locked?)

    Attributes:
        id: UUID primary key (globally unique)
        user_id: FK to users table (nullable: failed login before user found)
        event_type: Event type (login, logout, password_reset, account_locked, etc.)
        success: Boolean (True = success, False = failure)
        ip_address: IP address of client
        user_agent: User agent string (browser, OS)
        created_at: Event timestamp (UTC)
    """

    __tablename__ = "auth_audit_log"

    id: UUID = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        doc="Globally unique audit log entry ID",
    )
    user_id: UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="FK to users table (nullable: user not found on failed login)",
    )
    event_type: str = Column(
        String(100),
        nullable=False,
        index=True,
        doc="Event type: login, logout, password_reset, account_locked, etc.",
    )
    success: bool = Column(
        Boolean,
        nullable=False,
        doc="True = success, False = failure",
    )
    ip_address: str = Column(
        String(45),  # IPv6 max length
        nullable=True,
        doc="IP address of client (IPv4 or IPv6)",
    )
    user_agent: str = Column(
        String(500),
        nullable=True,
        doc="User agent string (browser, OS, device)",
    )
    created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        doc="Event timestamp (UTC)",
    )

    # Indexes for efficient querying
    __table_args__ = (
        Index("ix_auth_audit_log_user_created", "user_id", "created_at"),
        Index("ix_auth_audit_log_event_type", "event_type"),
    )


class AuditLog(Base):
    """
    General audit log for CRUD operations tracking.

    Stores all system CRUD operations (create, update, delete) for compliance,
    troubleshooting, and security auditing. Tracks changes to entities with
    old/new values (JSON diff).

    Use cases:
    - Compliance reporting (who changed what when)
    - Troubleshooting (what changed before the issue started?)
    - Security auditing (detect unauthorized changes)
    - Data recovery (restore old values)

    Attributes:
        id: UUID primary key (globally unique)
        user_id: FK to users table (who performed the action)
        tenant_id: Tenant identifier (which tenant the entity belongs to)
        action: Action type (create, update, delete)
        entity_type: Entity type (agent, tenant, mcp_server, etc.)
        entity_id: UUID of the entity that was modified
        old_value: JSONB object with entity state before change (nullable for create)
        new_value: JSONB object with entity state after change (nullable for delete)
        ip_address: IP address of client
        user_agent: User agent string (browser, OS)
        created_at: Event timestamp (UTC)
    """

    __tablename__ = "audit_log"

    id: UUID = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        doc="Globally unique audit log entry ID",
    )
    user_id: UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="FK to users table (who performed the action)",
    )
    tenant_id: str = Column(
        String(255),
        nullable=False,
        index=True,
        doc="Tenant identifier (which tenant the entity belongs to)",
    )
    action: str = Column(
        String(50),
        nullable=False,
        doc="Action type: create, update, delete",
    )
    entity_type: str = Column(
        String(100),
        nullable=False,
        index=True,
        doc="Entity type: agent, tenant, mcp_server, tool, etc.",
    )
    entity_id: UUID = Column(
        UUID(as_uuid=True),
        nullable=False,
        doc="UUID of the entity that was modified",
    )
    old_value: dict = Column(
        JSONB,
        nullable=True,
        doc="JSONB object with entity state before change (null for create)",
    )
    new_value: dict = Column(
        JSONB,
        nullable=True,
        doc="JSONB object with entity state after change (null for delete)",
    )
    ip_address: str = Column(
        String(45),  # IPv6 max length
        nullable=True,
        doc="IP address of client (IPv4 or IPv6)",
    )
    user_agent: str = Column(
        String(500),
        nullable=True,
        doc="User agent string (browser, OS, device)",
    )
    created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        doc="Event timestamp (UTC)",
    )

    # Indexes for efficient querying
    __table_args__ = (
        Index("ix_audit_log_user_tenant_created", "user_id", "tenant_id", "created_at"),
        Index("ix_audit_log_entity_type_created", "entity_type", "created_at"),
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
        memory_config: Agent memory configuration (short_term, long_term, agentic)
        assigned_mcp_tools: MCP tool assignments (tools, resources, prompts from MCP servers)
        created_at: Timestamp when agent was created
        updated_at: Timestamp when agent was last updated
        created_by: User who created the agent
        triggers: Relationship to AgentTrigger (webhook/schedule triggers)
        tools: Relationship to AgentTool (assigned OpenAPI tools via agent_tools table)
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
    cognitive_architecture: str = Column(
        String(50),
        nullable=False,
        default="react",
        server_default="react",
        doc="Cognitive architecture: react, single_step, plan_and_solve",
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
    memory_config: Optional[dict] = Column(
        JSON,
        nullable=True,
        default=None,
        doc="Agent memory configuration: short_term, long_term, agentic settings",
    )
    assigned_mcp_tools: Optional[list] = Column(
        JSON,
        nullable=True,
        default=list,
        server_default=text("'[]'::jsonb"),
        doc="MCP tool assignments (tools, resources, prompts) - list of MCPToolAssignment dicts",
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


class AgentMemory(Base):
    """
    Agent memory storage for multi-type memory system.

    Stores short-term, long-term, and agentic memories with optional vector embeddings
    for semantic similarity search. Supports retention policies for automatic cleanup.

    Attributes:
        id: UUID primary key
        agent_id: Reference to Agent
        tenant_id: Tenant identifier for isolation
        memory_type: Type of memory (short_term, long_term, agentic)
        content: JSONB content (flexible structure)
        embedding: Vector embedding for similarity search (1536 dims)
        retention_days: Days before auto-deletion
        created_at: Timestamp when memory was created
        updated_at: Timestamp when memory was last updated
    """

    __tablename__ = "agent_memory"

    id: UUID = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        doc="Memory entry ID (UUID)",
    )
    agent_id: UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of agent owning this memory",
    )
    tenant_id: str = Column(
        String(100),
        ForeignKey("tenant_configs.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Tenant identifier for multi-tenant isolation",
    )
    memory_type: str = Column(
        String(20),
        nullable=False,
        doc="Memory type: short_term, long_term, or agentic",
    )
    content: dict = Column(
        JSON,
        nullable=False,
        doc="Memory content as JSONB (flexible structure for different memory types)",
    )
    embedding: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Vector embedding for semantic search (text format for pgvector, 1536 dims)",
    )
    retention_days: int = Column(
        Integer,
        nullable=False,
        default=90,
        doc="Days to retain this memory before auto-deletion",
    )
    created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Timestamp when memory was created",
    )
    updated_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Timestamp when memory was last updated",
    )

    # Composite index for agent_id, memory_type, created_at DESC
    __table_args__ = (
        Index("idx_agent_memory_agent_type", "agent_id", "memory_type", desc("created_at")),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<AgentMemory(id={self.id}, agent_id={self.agent_id}, memory_type={self.memory_type})>"


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
    tenant_id: str = Column(
        String(100),
        ForeignKey("tenant_configs.tenant_id", ondelete="CASCADE"),
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




class AgentTestExecution(Base):
    """
    Agent test execution results for sandbox testing (Story 8.14).

    Stores results of test executions in dry-run mode, including execution traces,
    token usage, timing breakdowns, and error information. Used for verification
    before agent activation and for testing/debugging agent behavior.

    Attributes:
        id: UUID primary key
        agent_id: Foreign key to Agent (cascade delete)
        tenant_id: Tenant identifier for isolation
        payload: Test input (webhook payload or trigger parameters)
        execution_trace: JSON with step-by-step execution details
        token_usage: JSON with token counts and estimated cost
        execution_time: JSON with timing breakdown
        errors: JSON with error details if execution failed
        status: success or failed
        task_id: Celery task ID for correlation with webhook response (nullable)
        created_at: When test was executed
    """

    __tablename__ = "agent_test_executions"

    id: UUID = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        doc="Test execution ID (globally unique)",
    )
    agent_id: UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of agent being tested",
    )
    tenant_id: str = Column(
        String(100),
        ForeignKey("tenant_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Tenant for isolation",
    )
    payload: dict = Column(
        JSON,
        nullable=False,
        doc="Test payload: webhook data or trigger parameters",
    )
    execution_trace: dict = Column(
        JSON,
        nullable=False,
        doc="Step-by-step execution: {steps: [{step_type, tool_name, input, output, duration_ms}], total_duration_ms}",
    )
    token_usage: dict = Column(
        JSON,
        nullable=False,
        doc="Token tracking: {input_tokens, output_tokens, total_tokens, estimated_cost_usd}",
    )
    execution_time: dict = Column(
        JSON,
        nullable=False,
        doc="Timing breakdown: {total_duration_ms, steps: [{name, duration_ms}]}",
    )
    errors: Optional[dict] = Column(
        JSON,
        nullable=True,
        doc="Error details if failed: {error_type, message, stack_trace}",
    )
    status: str = Column(
        String(50),
        nullable=False,
        server_default="success",
        doc="Execution status: success or failed",
    )
    task_id: Optional[str] = Column(
        String(100),
        nullable=True,
        index=True,
        doc="Celery task ID for correlation with webhook response",
    )
    created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        doc="Timestamp when test was executed",
    )

    # Indexes for common queries
    __table_args__ = (
        Index("idx_agent_test_executions_agent_id", "agent_id"),
        Index("idx_agent_test_executions_tenant_id", "tenant_id"),
        Index("idx_agent_test_executions_created_at", "created_at", postgresql_ops={"created_at": "DESC"}),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<AgentTestExecution(agent_id={self.agent_id}, status={self.status}, created_at={self.created_at})>"

# ============================================================================
# MCP Server Models (Epic 11)
# ============================================================================


class TransportType(str, Enum):
    """
    MCP server transport protocol types.
    
    Attributes:
        STDIO: Subprocess communication via stdin/stdout (JSON-RPC over pipes)
        HTTP_SSE: HTTP with Server-Sent Events for streaming (future support)
    """
    STDIO = "stdio"
    HTTP_SSE = "http_sse"


class MCPServerStatus(str, Enum):
    """
    MCP server health and operational status.
    
    Attributes:
        ACTIVE: Server is healthy and ready to process requests
        INACTIVE: Server is registered but not currently in use
        ERROR: Server encountered an error during last operation
    """
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class MCPServer(Base):
    """
    Model Context Protocol (MCP) server configuration and state.
    
    Stores MCP server configurations with support for both stdio and HTTP+SSE
    transport types. Each tenant can register multiple MCP servers to extend
    agent capabilities with external tools, resources, and prompts.
    
    MCP Specification: https://modelcontextprotocol.io/specification (2025-03-26)
    
    Transport Types:
        - stdio: Subprocess communication (command, args, env)
        - http_sse: HTTP with Server-Sent Events (url, headers)
    
    Discovered Capabilities:
        - tools: Functions agents can invoke (e.g., read_file, search_docs)
        - resources: Data sources agents can access (e.g., config files, databases)
        - prompts: Templated prompts for common tasks (e.g., analyze_code)
    
    Attributes:
        id: Unique server identifier (UUID)
        tenant_id: Tenant ownership for multi-tenant isolation
        name: Human-readable server name (unique per tenant)
        description: Optional detailed description of server purpose
        transport_type: Protocol type ('stdio' or 'http_sse')
        command: Executable path for stdio (e.g., 'npx', 'python')
        args: Command-line arguments array for stdio (JSONB)
        env: Environment variables object for stdio (JSONB)
        url: Base URL for HTTP+SSE transport
        headers: HTTP headers for authentication (JSONB, e.g., Bearer tokens)
        discovered_tools: Tools from MCP tools/list endpoint (JSONB array)
        discovered_resources: Resources from resources/list (JSONB array)
        discovered_prompts: Prompts from prompts/list (JSONB array)
        status: Current health status ('active', 'inactive', 'error')
        last_health_check: Timestamp of last health verification
        error_message: Latest error details if status='error'
        consecutive_failures: Number of consecutive failed health checks (circuit breaker at >=3)
        created_at: Server registration timestamp
        updated_at: Last configuration update timestamp

    Relationships:
        tenant: Reference to TenantConfig (CASCADE delete)

    Constraints:
        - Unique (tenant_id, name): Server names unique per tenant
        - CHECK transport_type IN ('stdio', 'http_sse')
        - CHECK status IN ('active', 'inactive', 'error')

    Indexes:
        - idx_mcp_servers_tenant_id: Fast tenant server lookups
        - idx_mcp_servers_status: Filter by health status
        - idx_mcp_servers_transport_type: Filter by transport type
        - idx_mcp_servers_tenant_status: Combined tenant + status queries
        - idx_mcp_servers_status_health_check: Combined status + last_health_check for health monitoring
    """
    __tablename__ = "mcp_servers"

    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique server identifier"
    )
    
    # Tenant isolation
    tenant_id = Column(
        String(100),
        ForeignKey("tenant_configs.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Tenant ownership (CASCADE delete when tenant removed)"
    )
    
    # Server identification
    name = Column(
        String(255),
        nullable=False,
        doc="Human-readable server name (unique per tenant)"
    )
    
    description = Column(
        Text,
        nullable=True,
        doc="Optional detailed description of server purpose"
    )
    
    # Transport configuration
    transport_type = Column(
        String(20),
        nullable=False,
        index=True,
        doc="Transport protocol: 'stdio' or 'http_sse'"
    )
    
    # stdio transport fields (required when transport_type='stdio')
    command = Column(
        String(500),
        nullable=True,
        doc="Executable path for stdio (e.g., 'npx', '/usr/bin/python3')"
    )
    
    args = Column(
        JSONB,
        nullable=True,
        default=list,
        server_default=func.cast(func.text("'[]'"), JSONB),
        doc="Command-line arguments array for stdio (e.g., ['@modelcontextprotocol/server-filesystem', '/workspace'])"
    )
    
    env = Column(
        JSONB,
        nullable=True,
        default=dict,
        server_default=func.cast(func.text("'{}'"), JSONB),
        doc="Environment variables object for stdio (e.g., {'API_KEY': 'secret', 'LOG_LEVEL': 'debug'})"
    )
    
    # HTTP+SSE transport fields (required when transport_type='http_sse')
    url = Column(
        String(500),
        nullable=True,
        doc="Base URL for HTTP+SSE transport (e.g., 'https://mcp.example.com/api')"
    )
    
    headers = Column(
        JSONB,
        nullable=True,
        default=dict,
        server_default=func.cast(func.text("'{}'"), JSONB),
        doc="HTTP headers for authentication (e.g., {'Authorization': 'Bearer token'})"
    )
    
    # Discovered capabilities from MCP protocol
    discovered_tools = Column(
        JSONB,
        nullable=True,
        default=list,
        server_default=func.cast(func.text("'[]'"), JSONB),
        doc="Tools from MCP tools/list endpoint (array of tool schemas)"
    )
    
    discovered_resources = Column(
        JSONB,
        nullable=True,
        default=list,
        server_default=func.cast(func.text("'[]'"), JSONB),
        doc="Resources from MCP resources/list endpoint (array of resource descriptors)"
    )
    
    discovered_prompts = Column(
        JSONB,
        nullable=True,
        default=list,
        server_default=func.cast(func.text("'[]'"), JSONB),
        doc="Prompts from MCP prompts/list endpoint (array of prompt templates)"
    )
    
    # Health and status tracking
    status = Column(
        String(20),
        nullable=False,
        default=MCPServerStatus.INACTIVE.value,
        server_default=func.text("'inactive'"),
        index=True,
        doc="Current health status: 'active', 'inactive', or 'error'"
    )
    
    last_health_check = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of last health verification"
    )
    
    error_message = Column(
        Text,
        nullable=True,
        doc="Latest error details if status='error'"
    )

    consecutive_failures = Column(
        Integer,
        nullable=False,
        default=0,
        server_default=func.text("0"),
        doc="Number of consecutive failed health checks (circuit breaker triggers at >=3)"
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Server registration timestamp"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Last configuration update timestamp"
    )
    
    # Relationships
    tenant = relationship(
        "TenantConfig",
        back_populates="mcp_servers",
        doc="Parent tenant configuration (CASCADE delete)"
    )

    metrics = relationship(
        "MCPServerMetric",
        back_populates="mcp_server",
        cascade="all, delete-orphan",
        passive_deletes=True,
        doc="Time-series health metrics (CASCADE delete, 7-day retention)"
    )
    
    # Constraints and indexes
    __table_args__ = (
        # CHECK constraints for enum validation
        CheckConstraint(
            "transport_type IN ('stdio', 'http_sse')",
            name="ck_mcp_servers_transport_type"
        ),
        CheckConstraint(
            "status IN ('active', 'inactive', 'error')",
            name="ck_mcp_servers_status"
        ),
        
        # Unique constraint: server name unique per tenant
        UniqueConstraint(
            "tenant_id",
            "name",
            name="uq_mcp_servers_tenant_name"
        ),
        
        # Composite index for common query pattern (tenant's active servers)
        Index(
            "idx_mcp_servers_tenant_status",
            "tenant_id",
            "status"
        ),
    )
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<MCPServer("
            f"id={self.id}, "
            f"name='{self.name}', "
            f"transport={self.transport_type}, "
            f"status={self.status}"
            f")>"
        )


class MCPServerMetric(Base):
    """
    SQLAlchemy model for MCP server health metrics time-series data.

    Story: 11.2.4 - Enhanced MCP Health Monitoring

    Stores individual health check measurements for performance tracking,
    failure analysis, and trend detection. Enables:
    - Response time tracking (millisecond precision)
    - Success/failure rate calculation
    - Error pattern detection by type
    - Capacity planning via request rate monitoring

    Retention: 7 days (managed by Celery cleanup task)

    Relationships:
        - Many-to-one with MCPServer (CASCADE delete)
        - Many-to-one with TenantConfig (CASCADE delete)

    Indexes:
        - idx_mcp_metrics_server_time: (mcp_server_id, check_timestamp DESC)
        - idx_mcp_metrics_tenant: (tenant_id)
        - idx_mcp_metrics_status_time: (status, check_timestamp DESC)

    Example query:
        SELECT AVG(response_time_ms), PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time_ms)
        FROM mcp_server_metrics
        WHERE mcp_server_id = ? AND check_timestamp >= NOW() - INTERVAL '24 hours'
    """

    __tablename__ = "mcp_server_metrics"

    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
        doc="Primary key for metrics record"
    )

    # Foreign keys with CASCADE delete
    mcp_server_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mcp_servers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="MCP server this metric belongs to"
    )
    tenant_id = Column(
        String(100),
        ForeignKey("tenant_configs.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Tenant for row-level security and isolation"
    )

    # Timing metrics
    response_time_ms = Column(
        Integer,
        nullable=False,
        doc="Health check response time in milliseconds"
    )
    check_timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="When the health check was performed"
    )

    # Status metrics
    status = Column(
        String(20),
        nullable=False,
        doc="Health check result: 'success', 'timeout', 'error', 'connection_failed'"
    )
    error_message = Column(
        Text,
        nullable=True,
        doc="Error message if status is not success"
    )
    error_type = Column(
        String(100),
        nullable=True,
        doc="Error type classification: 'TimeoutError', 'ProcessCrashed', 'InvalidJSON', etc."
    )

    # Request metadata
    check_type = Column(
        String(50),
        nullable=False,
        doc="Type of health check: 'health_check', 'tools_list', 'ping'"
    )
    transport_type = Column(
        String(20),
        nullable=False,
        doc="Transport type: 'stdio' or 'http_sse'"
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Record creation timestamp"
    )

    # Relationships
    mcp_server = relationship(
        "MCPServer",
        back_populates="metrics",
    )
    tenant = relationship(
        "TenantConfig",
        back_populates="mcp_metrics",
    )

    # Indexes defined in Alembic migration 012:
    # - idx_mcp_metrics_server_time (mcp_server_id, check_timestamp DESC)
    # - idx_mcp_metrics_tenant (tenant_id)
    # - idx_mcp_metrics_status_time (status, check_timestamp DESC)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<MCPServerMetric("
            f"id={self.id}, "
            f"server_id={self.mcp_server_id}, "
            f"response_time={self.response_time_ms}ms, "
            f"status={self.status}, "
            f"timestamp={self.check_timestamp}"
            f")>"
        )
