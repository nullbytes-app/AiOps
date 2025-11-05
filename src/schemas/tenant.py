"""Pydantic models for tenant configuration management.

Defines request/response schemas for tenant configuration CRUD operations,
with proper validation and separation of internal vs. external representations.
"""

from typing import Optional
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator, HttpUrl, ConfigDict


class EnhancementPreferences(BaseModel):
    """Tenant-specific enhancement processing preferences.

    Attributes:
        max_enhancement_length: Maximum length of generated enhancement (100-2000 chars)
        include_monitoring: Include monitoring data in context gathering
        kb_timeout_seconds: Timeout for knowledge base searches (1-60 seconds)
    """

    max_enhancement_length: int = Field(default=500, ge=100, le=2000)
    include_monitoring: bool = True
    kb_timeout_seconds: int = Field(default=10, ge=1, le=60)


class TenantConfigCreate(BaseModel):
    """Request model for creating tenant configuration.

    Supports multiple ticketing tools via plugin architecture.
    Tool-specific fields required based on tool_type.
    """

    tenant_id: str = Field(..., pattern=r"^[a-z0-9\-]+$", max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    tool_type: str = Field(default="servicedesk_plus")

    # ServiceDesk Plus fields (required if tool_type='servicedesk_plus')
    servicedesk_url: Optional[HttpUrl] = None
    servicedesk_api_key: Optional[str] = Field(None, min_length=1)

    # Jira fields (required if tool_type='jira')
    jira_url: Optional[HttpUrl] = None
    jira_api_token: Optional[str] = Field(None, min_length=1)
    jira_project_key: Optional[str] = Field(None, min_length=1)

    webhook_signing_secret: str = Field(..., min_length=1)
    enhancement_preferences: Optional[EnhancementPreferences] = None

    @field_validator("tenant_id")
    @classmethod
    def validate_tenant_id(cls, v: str) -> str:
        """Ensure tenant_id follows naming conventions."""
        if not v or v.startswith("-") or v.endswith("-"):
            raise ValueError("Tenant ID cannot start/end with hyphen")
        return v.lower()

    @model_validator(mode="after")
    def validate_tool_specific_fields(self) -> "TenantConfigCreate":
        """Validate required fields present for tool_type."""
        if self.tool_type == "servicedesk_plus":
            if not self.servicedesk_url or not self.servicedesk_api_key:
                raise ValueError("ServiceDesk Plus requires: servicedesk_url, servicedesk_api_key")
        elif self.tool_type == "jira":
            if not self.jira_url or not self.jira_api_token or not self.jira_project_key:
                raise ValueError("Jira requires: jira_url, jira_api_token, jira_project_key")
        return self

    def model_post_init(self, __context: any) -> None:
        """Apply defaults to enhancement preferences."""
        if self.enhancement_preferences is None:
            self.enhancement_preferences = EnhancementPreferences()

    @property
    def servicedesk_url_str(self) -> str:
        """Get servicedesk_url as string for storage."""
        return str(self.servicedesk_url) if self.servicedesk_url else ""


class TenantConfigUpdate(BaseModel):
    """Request model for updating tenant configuration.

    All fields are optional - only provided fields will be updated.
    """

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    tool_type: Optional[str] = None

    # ServiceDesk Plus fields
    servicedesk_url: Optional[HttpUrl] = None
    servicedesk_api_key: Optional[str] = Field(None, min_length=1)

    # Jira fields
    jira_url: Optional[HttpUrl] = None
    jira_api_token: Optional[str] = Field(None, min_length=1)
    jira_project_key: Optional[str] = Field(None, min_length=1)

    webhook_signing_secret: Optional[str] = Field(None, min_length=1)
    enhancement_preferences: Optional[dict] = None


class TenantConfigResponse(BaseModel):
    """Response model for GET endpoints.

    Sensitive fields (api_key, webhook_secret) are masked in responses.
    Supports multi-tool architecture with tool-specific fields.
    """

    id: UUID
    tenant_id: str
    name: str
    tool_type: str

    # ServiceDesk Plus fields
    servicedesk_url: Optional[str] = None
    servicedesk_api_key_encrypted: Optional[str] = Field(default="***encrypted***")

    # Jira fields
    jira_url: Optional[str] = None
    jira_api_token_encrypted: Optional[str] = Field(default="***encrypted***")
    jira_project_key: Optional[str] = None

    webhook_signing_secret_encrypted: str = Field(default="***encrypted***")
    enhancement_preferences: EnhancementPreferences
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenantConfigInternal(BaseModel):
    """Internal model with decrypted sensitive fields.

    Used internally by TenantService after decryption.
    Never exposed in API responses.

    Supports multiple ticketing tools via plugin architecture:
    - ServiceDesk Plus: servicedesk_url, servicedesk_api_key
    - Jira Service Management: jira_url, jira_api_token, jira_project_key
    """

    id: UUID
    tenant_id: str
    name: str

    # ServiceDesk Plus fields (optional for Jira tenants)
    servicedesk_url: Optional[str] = None
    servicedesk_api_key: Optional[str] = None  # Decrypted

    # Jira Service Management fields (optional for ServiceDesk Plus tenants)
    jira_url: Optional[str] = None
    jira_api_token: Optional[str] = None  # Decrypted
    jira_project_key: Optional[str] = None

    # Common fields
    webhook_signing_secret: str  # Decrypted
    enhancement_preferences: EnhancementPreferences
    created_at: datetime
    updated_at: datetime

    tool_type: str = "servicedesk_plus"  # Default for backward compatibility
    is_active: bool = True  # Default for backward compatibility
    model_config = ConfigDict(from_attributes=True)


class TenantConfigListResponse(BaseModel):
    """Paginated list response for GET /admin/tenants.

    Attributes:
        items: List of tenant configurations (with masked sensitive fields)
        total_count: Total number of tenants in system
        skip: Number of records skipped in pagination
        limit: Number of records returned
    """

    items: list[TenantConfigResponse]
    total_count: int
    skip: int
    limit: int
