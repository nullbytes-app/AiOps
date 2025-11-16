"""
LiteLLM Database Models.

SQLAlchemy models for LiteLLM proxy tables.
These tables are created and managed by LiteLLM (Story 8.1).

IMPORTANT: These are READ-ONLY models. Do not modify these tables.
LiteLLM proxy manages the schema and data.

Table: LiteLLM_SpendLogs
- Automatically populated by LiteLLM proxy on every LLM API call
- Contains spend tracking data (cost, tokens, model, user, etc.)
- Used for cost dashboard queries (Story 8.16)
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Column, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import declarative_base

# Separate base for LiteLLM tables (not managed by our migrations)
LiteLLMBase = declarative_base()


class LiteLLMSpendLog(LiteLLMBase):
    """
    LiteLLM Spend Log Model (READ-ONLY).

    Maps to LiteLLM_SpendLogs table created by LiteLLM proxy.
    Structure from Context7 MCP /berriai/litellm documentation.

    Fields:
    - request_id: Unique request identifier (chatcmpl-xxx format)
    - call_type: Type of call (e.g., "acompletion", "completion")
    - api_key: Hash of API key used
    - user: Internal LiteLLM user (from LiteLLM_UserTable)
    - team_id: Team ID (from LiteLLM_TeamTable)
    - end_user: Customer/tenant identifier (mapped to our tenant_id)
    - model_group: Model name (e.g., "gpt-4", "gpt-3.5-turbo")
    - api_base: API base URL of the model provider
    - spend: Cost in USD
    - total_tokens: Total tokens consumed
    - prompt_tokens: Input tokens
    - completion_tokens: Output tokens
    - request_tags: Array of tags (e.g., ["jobID:xxx", "taskName:yyy"])
    - metadata: JSON metadata (includes spend_logs_metadata)
    - created_at: Timestamp of the request
    """

    __tablename__ = "LiteLLM_SpendLogs"
    __table_args__ = {"schema": "public"}

    # Primary key
    request_id = Column(
        String(255),
        primary_key=True,
        comment="Unique request identifier (e.g., chatcmpl-9ZKMURhVYSi9D6r6PJ9vLcayIK0Vm)",
    )

    # Call metadata
    call_type = Column(
        String(50),
        nullable=False,
        comment="Type of LLM call (acompletion, completion, embedding)",
    )
    startTime = Column(
        "startTime",  # Column name in database uses camelCase
        DateTime(timezone=False),  # LiteLLM uses timestamp without timezone
        nullable=False,
        index=True,
        comment="Timestamp when request was started (from LiteLLM)",
    )

    # Authentication
    api_key = Column(
        String(255),
        nullable=True,
        comment="Hash of API key used (fe6b0cab4ff5a5a8df823196cc8a450*****)",
    )
    user = Column(
        String(255),
        nullable=True,
        comment="Internal LiteLLM user (LiteLLM_UserTable)",
    )
    team_id = Column(
        String(255),
        nullable=True,
        index=True,
        comment="Team ID (LiteLLM_TeamTable)",
    )

    # Customer/Tenant mapping
    end_user = Column(
        String(255),
        nullable=True,
        index=True,
        comment="Customer identifier - maps to our tenant_id (CRITICAL for tenant isolation)",
    )

    # Model information
    model_group = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Model name (gpt-4, gpt-3.5-turbo, etc.)",
    )
    api_base = Column(
        Text,
        nullable=True,
        comment="API base URL (https://api.openai.com/v1/, etc.)",
    )

    # Cost tracking
    spend = Column(
        Float,
        nullable=False,
        default=0.0,
        comment="Cost in USD (e.g., 0.000002)",
    )
    total_tokens = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Total tokens consumed (prompt + completion)",
    )
    prompt_tokens = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Input tokens consumed",
    )
    completion_tokens = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Output tokens generated",
    )

    # Tags and metadata
    request_tags = Column(
        JSON,
        nullable=True,
        comment='Array of tags (e.g., ["jobID:214590dsff09fds", "taskName:run_page_classification"])',
    )
    # Note: 'metadata' is reserved in SQLAlchemy, so we map it to 'request_metadata'
    request_metadata = Column(
        "metadata",  # Actual column name in database
        JSON,
        nullable=True,
        comment="JSON metadata (includes spend_logs_metadata for custom tracking)",
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<LiteLLMSpendLog(request_id='{self.request_id}', "
            f"model='{self.model_group}', spend=${self.spend:.6f}, "
            f"tokens={self.total_tokens})>"
        )

    @property
    def tenant_id(self) -> Optional[UUID]:
        """
        Extract tenant_id from end_user field.

        LiteLLM stores tenant_id as string in end_user field.
        This property converts it to UUID for our domain logic.

        Returns:
            UUID if end_user is valid UUID string, None otherwise
        """
        if self.end_user:
            try:
                return UUID(self.end_user)
            except (ValueError, AttributeError):
                return None
        return None

    @property
    def agent_name(self) -> Optional[str]:
        """
        Extract agent name from request_tags.

        Request tags format: ["agent:enhancement_agent", "taskID:xxx"]

        Returns:
            Agent name if found in tags, None otherwise
        """
        if self.request_tags and isinstance(self.request_tags, list):
            for tag in self.request_tags:
                if isinstance(tag, str) and tag.startswith("agent:"):
                    return tag.split(":", 1)[1]
        return None
