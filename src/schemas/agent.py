"""
Pydantic schemas for AI Agent configuration and management.

This module defines data validation schemas for agent CRUD operations using
Pydantic v2 patterns. Includes enums for agent status and trigger types,
nested schemas for LLM configuration, and comprehensive field validation.

Following 2025 Pydantic v2 best practices:
- @field_validator(mode='after') for single-field validation
- @model_validator(mode='after') for cross-field validation
- ConfigDict(from_attributes=True) for ORM integration
- str mixin for Enum classes (JSON serialization)
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AgentStatus(str, Enum):
    """
    Agent lifecycle status.

    Valid transitions:
    - DRAFT → ACTIVE (activate after configuration complete)
    - ACTIVE → SUSPENDED (temporarily pause agent)
    - SUSPENDED → ACTIVE (resume suspended agent)
    - ACTIVE → INACTIVE (soft delete)
    - SUSPENDED → INACTIVE (soft delete from suspended)

    Invalid transitions (blocked by validation):
    - ACTIVE → DRAFT (cannot un-activate)
    - INACTIVE → * (cannot reactivate deleted agents)
    """

    DRAFT = "draft"  # Agent created but not activated
    ACTIVE = "active"  # Agent running and processing triggers
    SUSPENDED = "suspended"  # Temporarily paused, triggers ignored
    INACTIVE = "inactive"  # Soft deleted, triggers disabled


class TriggerType(str, Enum):
    """
    Agent trigger types.

    WEBHOOK: HTTP POST webhook trigger (external systems push events)
    SCHEDULE: Cron-based scheduled execution (periodic tasks)
    """

    WEBHOOK = "webhook"
    SCHEDULE = "schedule"


class LLMConfig(BaseModel):
    """
    LLM provider configuration for agents.

    Flexible JSONB configuration supporting multiple LLM providers via LiteLLM.
    Includes validation for temperature and token limits following OpenAI conventions.

    Attributes:
        provider: LLM provider name (default: litellm proxy)
        model: Model identifier (e.g., gpt-4, claude-3-5-sonnet)
        temperature: Sampling temperature (0.0-2.0, default 0.7)
        max_tokens: Maximum tokens in response (1-32000, default 4096)

    Example:
        {
            "provider": "litellm",
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 4096
        }
    """

    provider: str = Field(default="litellm", min_length=1, max_length=50)
    model: str = Field(..., min_length=1, max_length=100)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=32000)

    @field_validator("model", mode="after")
    @classmethod
    def validate_model(cls, v: str) -> str:
        """
        Validate model identifier against known models.

        Args:
            v: Model identifier to validate

        Returns:
            str: Validated model identifier

        Raises:
            ValueError: If model is not in allowed list
        """
        # Comprehensive list of supported models (2025)
        allowed_models = [
            # OpenAI models
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4-turbo-preview",
            "gpt-3.5-turbo",
            # Anthropic Claude models
            "claude-3-5-sonnet",
            "claude-3-5-sonnet-20241022",
            "claude-3-opus",
            "claude-3-sonnet",
            "claude-3-haiku",
            # Open source models via LiteLLM
            "ollama/llama3",
            "ollama/mistral",
        ]
        if v not in allowed_models:
            raise ValueError(
                f"Model must be one of {allowed_models}. "
                f"Got: {v}. Add new models to validation list if needed."
            )
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "provider": "litellm",
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 4096,
            }
        }
    )


class AgentTriggerCreate(BaseModel):
    """
    Schema for creating agent triggers.

    Supports webhook and scheduled triggers with appropriate validation.
    Webhook triggers auto-generate URL and HMAC secret if not provided.
    Schedule triggers require cron expression.

    Attributes:
        trigger_type: Trigger type (webhook or schedule)
        webhook_url: Optional webhook URL (auto-generated if None)
        hmac_secret: Optional HMAC secret (auto-generated if None)
        schedule_cron: Required cron expression for schedule triggers
        payload_schema: Optional JSON schema for webhook payload validation
    """

    trigger_type: TriggerType
    webhook_url: Optional[str] = Field(None, max_length=500)
    hmac_secret: Optional[str] = None
    schedule_cron: Optional[str] = Field(None, max_length=100)
    payload_schema: Optional[dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_trigger_requirements(self) -> "AgentTriggerCreate":
        """
        Validate trigger type-specific requirements.

        Schedule triggers MUST have schedule_cron.
        Webhook triggers can have webhook_url and hmac_secret (auto-generated if None).

        Returns:
            AgentTriggerCreate: Validated trigger

        Raises:
            ValueError: If schedule trigger missing cron expression
        """
        if self.trigger_type == TriggerType.SCHEDULE and not self.schedule_cron:
            raise ValueError(
                "schedule_cron is required when trigger_type is 'schedule'. "
                "Provide a valid cron expression (e.g., '0 9 * * *' for daily 9 AM)."
            )
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "trigger_type": "webhook",
                    "webhook_url": "/agents/{agent_id}/webhook",
                    "hmac_secret": "encrypted_secret_here",
                },
                {
                    "trigger_type": "schedule",
                    "schedule_cron": "0 * * * *",  # Every hour
                },
            ]
        }
    )


class AgentCreate(BaseModel):
    """
    Schema for creating new agents.

    All fields except triggers and tool_ids are required. Agents default to
    DRAFT status and must be explicitly activated. System prompt must be
    between 10-32000 characters (reasonable prompt length).

    Attributes:
        name: Human-readable agent name (3-255 chars)
        description: Optional detailed description
        system_prompt: LLM system prompt (10-32000 chars)
        llm_config: LLM configuration (provider, model, temperature, max_tokens)
        status: Agent status (default: draft)
        created_by: Optional user who created agent
        triggers: List of triggers to create with agent
        tool_ids: List of tool identifiers to assign (e.g., ["servicedesk_plus", "jira"])
    """

    name: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    system_prompt: str = Field(..., min_length=10, max_length=32000)
    llm_config: LLMConfig
    status: AgentStatus = Field(default=AgentStatus.DRAFT)
    created_by: Optional[str] = Field(None, max_length=255)
    triggers: list[AgentTriggerCreate] = Field(default_factory=list)
    tool_ids: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_active_agent_has_trigger(self) -> "AgentCreate":
        """
        Validate that active agents have at least one trigger.

        Draft agents can be created without triggers, but active agents must
        have triggers defined to be invoked.

        Returns:
            AgentCreate: Validated agent

        Raises:
            ValueError: If active agent has no triggers
        """
        if self.status == AgentStatus.ACTIVE and len(self.triggers) == 0:
            raise ValueError(
                "Active agents must have at least one trigger (webhook or schedule). "
                "Either add triggers or set status to 'draft'."
            )
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Ticket Enhancement Agent",
                "description": "Enhances ServiceDesk tickets with context from history and docs",
                "system_prompt": "You are a helpful assistant that enhances support tickets...",
                "llm_config": {
                    "provider": "litellm",
                    "model": "gpt-4",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                },
                "status": "draft",
                "created_by": "admin@example.com",
                "triggers": [
                    {
                        "trigger_type": "webhook",
                        "webhook_url": "/agents/uuid-123/webhook",
                    }
                ],
                "tool_ids": ["servicedesk_plus"],
            }
        }
    )


class AgentUpdate(BaseModel):
    """
    Schema for updating existing agents.

    All fields are optional (partial updates supported). Status transitions
    are validated to prevent invalid state changes (e.g., active→draft).

    Attributes:
        name: Optional agent name update
        description: Optional description update
        system_prompt: Optional system prompt update
        llm_config: Optional LLM configuration update
        status: Optional status update (validated for valid transitions)
        tool_ids: Optional list of tool identifiers to assign (Story 8.7, AC#3, AC#5)
    """

    name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    system_prompt: Optional[str] = Field(None, min_length=10, max_length=32000)
    llm_config: Optional[LLMConfig] = None
    status: Optional[AgentStatus] = None
    tool_ids: Optional[list[str]] = Field(None, max_length=20)  # AC#3, AC#5: Tool assignment updates

    @model_validator(mode="after")
    def validate_status_transition(self) -> "AgentUpdate":
        """
        Validate status transitions.

        Invalid transitions blocked:
        - ACTIVE → DRAFT (cannot un-activate, use suspend or inactive)
        - INACTIVE → * (cannot reactivate deleted agents)

        Note: This validator only checks the new status. API layer must
        check current status before applying update.

        Returns:
            AgentUpdate: Validated update

        Raises:
            ValueError: If attempting invalid transition to DRAFT
        """
        # Cannot transition TO draft from any other status
        # (Draft is only valid for initial creation)
        if self.status == AgentStatus.DRAFT:
            raise ValueError(
                "Cannot transition agent status to 'draft'. "
                "Valid transitions: draft→active, active→suspended, "
                "suspended→active, active/suspended→inactive."
            )
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Updated Ticket Enhancement Agent",
                "system_prompt": "You are an expert support assistant...",
                "status": "active",
                "tool_ids": ["servicedesk_plus", "jira"],  # AC#3, AC#5 example
            }
        }
    )


class AgentResponse(BaseModel):
    """
    Schema for agent API responses.

    Full agent details including relationships (triggers, tools). Used for
    GET /agents/{id} and POST /agents responses. Includes ORM mapping via
    from_attributes for seamless SQLAlchemy model conversion.

    Attributes:
        id: Agent UUID
        tenant_id: Tenant identifier
        name: Agent name
        description: Agent description
        status: Current status
        system_prompt: System prompt
        llm_config: LLM configuration (serialized JSONB dict)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        created_by: Creator identifier
        triggers: List of trigger details
        tool_ids: List of assigned tool identifiers
    """

    id: UUID
    tenant_id: str
    name: str
    description: Optional[str]
    status: AgentStatus
    system_prompt: str
    llm_config: dict[str, Any]  # JSONB serialized as dict
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    triggers: list[dict[str, Any]] = Field(default_factory=list)
    tool_ids: list[str] = Field(default_factory=list)
    webhook_url: Optional[str] = Field(
        default=None,
        description="Auto-generated webhook URL for triggering agent (/agents/{agent_id}/webhook)",
    )
    hmac_secret_masked: Optional[str] = Field(
        default=None,
        description="Masked HMAC secret for webhook signature validation (use Show Secret to reveal)",
    )

    model_config = ConfigDict(
        from_attributes=True,  # Enable ORM mode for SQLAlchemy models
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "tenant_id": "tenant_123",
                "name": "Ticket Enhancement Agent",
                "description": "Enhances tickets with context",
                "status": "active",
                "system_prompt": "You are a helpful assistant...",
                "llm_config": {
                    "provider": "litellm",
                    "model": "gpt-4",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                },
                "created_at": "2025-11-05T19:00:00Z",
                "updated_at": "2025-11-05T19:30:00Z",
                "created_by": "admin@example.com",
                "triggers": [
                    {
                        "id": "660e8400-e29b-41d4-a716-446655440001",
                        "trigger_type": "webhook",
                        "webhook_url": "/agents/uuid-123/webhook",
                    }
                ],
                "tool_ids": ["servicedesk_plus", "jira"],
            }
        },
    )



class PromptVersionResponse(BaseModel):
    """
    Schema for prompt version history responses.

    Returns metadata about a prompt version without including the full text
    (to reduce response size). Used for version history listing.

    Attributes:
        id: Version UUID
        created_at: When this version was created
        created_by: User who created this version
        description: Optional description of what changed
        is_current: True if this is the agent's active prompt
    """

    id: UUID
    created_at: datetime
    created_by: Optional[str]
    description: Optional[str]
    is_current: bool

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "created_at": "2025-11-05T19:00:00Z",
                "created_by": "admin@example.com",
                "description": "Updated for better RCA analysis",
                "is_current": True,
            }
        },
    )


class PromptVersionDetail(PromptVersionResponse):
    """
    Extended version response including full prompt text.

    Used when retrieving a specific version or reverting to a version.

    Attributes:
        prompt_text: The full system prompt text
    """

    prompt_text: str

    model_config = ConfigDict(from_attributes=True)


class PromptTemplateCreate(BaseModel):
    """
    Schema for creating custom prompt templates.

    Attributes:
        name: Template name (3-255 chars)
        description: Purpose and usage description (required)
        template_text: Prompt with {{variable}} placeholders
    """

    name: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=5, max_length=1000)
    template_text: str = Field(..., min_length=10, max_length=32000)

    @field_validator("template_text", mode="after")
    @classmethod
    def validate_template_variables(cls, v: str) -> str:
        """
        Validate that template only uses defined variables.

        Valid variables: {{tenant_name}}, {{tools}}, {{current_date}}, {{agent_name}}

        Args:
            v: Template text

        Returns:
            str: Validated template

        Raises:
            ValueError: If template contains undefined variables
        """
        import re

        # Find all {{variable}} patterns
        variables = set(re.findall(r"\{\{(\w+)\}\}", v))
        allowed = {"tenant_name", "tools", "current_date", "agent_name"}
        undefined = variables - allowed

        if undefined:
            raise ValueError(
                f"Template contains undefined variables: {undefined}. "
                f"Allowed variables: {allowed}"
            )
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Ticket Enhancement",
                "description": "Agent that enhances support tickets with context from history and documentation",
                "template_text": "You are an AI assistant for {{tenant_name}}...",
            }
        }
    )


class PromptTemplateResponse(BaseModel):
    """
    Schema for prompt template API responses.

    Attributes:
        id: Template UUID
        name: Template name
        description: Purpose and usage
        template_text: Prompt template
        is_builtin: True for system-provided templates
        usage_count: Number of agents using this template
        created_by: User who created custom template
        created_at: Creation timestamp
        updated_at: Last modification timestamp
    """

    id: UUID
    name: str
    description: str
    template_text: str
    is_builtin: bool
    usage_count: int = Field(default=0)
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Ticket Enhancement",
                "description": "Enhances support tickets with context",
                "template_text": "You are an AI assistant...",
                "is_builtin": True,
                "usage_count": 3,
                "created_by": None,
                "created_at": "2025-11-05T19:00:00Z",
                "updated_at": "2025-11-05T19:00:00Z",
            }
        },
    )


class PromptTestRequest(BaseModel):
    """
    Schema for testing a prompt with LLM.

    Attributes:
        system_prompt: System prompt to test
        user_message: Sample user input
        model: LLM model to use (default: from agent config)
        temperature: Sampling temperature (optional override)
        max_tokens: Max tokens in response (optional override)
    """

    system_prompt: str = Field(..., min_length=10, max_length=32000)
    user_message: str = Field(..., min_length=1, max_length=5000)
    model: str = Field(default="gpt-4", max_length=100)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=32000)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "system_prompt": "You are a helpful support assistant...",
                "user_message": "How do I reset my password?",
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 1000,
            }
        }
    )


class PromptTestResponse(BaseModel):
    """
    Schema for prompt test results.

    Attributes:
        text: LLM response text
        tokens_used: {input, output} token counts
        execution_time: Time taken in milliseconds
        cost: Estimated cost in USD
    """

    text: str
    tokens_used: dict[str, int] = Field(
        ...,
        json_schema_extra={
            "example": {"input": 100, "output": 250}
        },
    )
    execution_time: int  # milliseconds
    cost: float  # USD

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "To reset your password, click the 'Forgot Password' link...",
                "tokens_used": {"input": 100, "output": 250},
                "execution_time": 1234,
                "cost": 0.005,
            }
        }
    )
