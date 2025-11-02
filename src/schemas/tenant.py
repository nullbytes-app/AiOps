"""Pydantic models for tenant configuration management.

Defines request/response schemas for tenant configuration CRUD operations,
with proper validation and separation of internal vs. external representations.
"""

from typing import Optional
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, HttpUrl, ConfigDict


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

    Attributes:
        tenant_id: Unique tenant identifier (lowercase alphanumeric + hyphens)
        name: Human-readable tenant name
        servicedesk_url: ServiceDesk Plus instance URL
        servicedesk_api_key: Plaintext API key (encrypted before storage)
        webhook_signing_secret: Plaintext webhook secret (encrypted before storage)
        enhancement_preferences: Optional preferences, defaults applied if omitted
    """

    tenant_id: str = Field(..., pattern=r"^[a-z0-9\-]+$", max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    servicedesk_url: HttpUrl
    servicedesk_api_key: str = Field(..., min_length=1)
    webhook_signing_secret: str = Field(..., min_length=1)
    enhancement_preferences: Optional[EnhancementPreferences] = None

    @field_validator("tenant_id")
    @classmethod
    def validate_tenant_id(cls, v: str) -> str:
        """Ensure tenant_id follows naming conventions."""
        if not v or v.startswith("-") or v.endswith("-"):
            raise ValueError("Tenant ID cannot start/end with hyphen")
        return v.lower()

    def model_post_init(self, __context):
        """Apply defaults to enhancement preferences."""
        if self.enhancement_preferences is None:
            self.enhancement_preferences = EnhancementPreferences()

    @property
    def servicedesk_url_str(self) -> str:
        """Get servicedesk_url as string for storage."""
        return str(self.servicedesk_url)


class TenantConfigUpdate(BaseModel):
    """Request model for updating tenant configuration.

    All fields are optional - only provided fields will be updated.
    """

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    servicedesk_url: Optional[HttpUrl] = None
    servicedesk_api_key: Optional[str] = Field(None, min_length=1)
    webhook_signing_secret: Optional[str] = Field(None, min_length=1)
    enhancement_preferences: Optional[EnhancementPreferences] = None


class TenantConfigResponse(BaseModel):
    """Response model for GET endpoints.

    Sensitive fields (api_key, webhook_secret) are masked in responses.
    Used for all GET endpoints and list operations.
    """

    id: UUID
    tenant_id: str
    name: str
    servicedesk_url: str
    servicedesk_api_key_encrypted: str = Field(default="***encrypted***")
    webhook_signing_secret_encrypted: str = Field(default="***encrypted***")
    enhancement_preferences: EnhancementPreferences
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenantConfigInternal(BaseModel):
    """Internal model with decrypted sensitive fields.

    Used internally by TenantService after decryption.
    Never exposed in API responses.
    """

    id: UUID
    tenant_id: str
    name: str
    servicedesk_url: str
    servicedesk_api_key: str  # Decrypted
    webhook_signing_secret: str  # Decrypted
    enhancement_preferences: EnhancementPreferences
    created_at: datetime
    updated_at: datetime

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
