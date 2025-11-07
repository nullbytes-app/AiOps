"""BYOK (Bring Your Own Key) Pydantic Schemas - Story 8.13.

Schemas for BYOK API endpoints, enabling tenants to use their own
OpenAI/Anthropic API keys instead of platform keys.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class BYOKEnableRequest(BaseModel):
    """Request body for enabling BYOK mode with tenant's API keys."""

    openai_key: Optional[str] = None
    anthropic_key: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("openai_key")
    @classmethod
    def validate_openai_key(cls, v: Optional[str]) -> Optional[str]:
        """Validate OpenAI key format (must start with 'sk-')."""
        if v and not v.startswith("sk-"):
            raise ValueError("OpenAI key must start with 'sk-'")
        return v

    @field_validator("anthropic_key")
    @classmethod
    def validate_anthropic_key(cls, v: Optional[str]) -> Optional[str]:
        """Validate Anthropic key format (must start with 'sk-ant-')."""
        if v and not v.startswith("sk-ant-"):
            raise ValueError("Anthropic key must start with 'sk-ant-'")
        return v

    @model_validator(mode="after")
    def validate_at_least_one_key(self) -> "BYOKEnableRequest":
        """Ensure at least one provider key is provided."""
        if not self.openai_key and not self.anthropic_key:
            raise ValueError("At least one provider key must be provided")
        return self


class BYOKTestKeysRequest(BaseModel):
    """Request body for testing tenant's provider API keys."""

    openai_key: Optional[str] = None
    anthropic_key: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("openai_key")
    @classmethod
    def validate_openai_key(cls, v: Optional[str]) -> Optional[str]:
        """Validate OpenAI key format."""
        if v and not v.startswith("sk-"):
            raise ValueError("OpenAI key must start with 'sk-'")
        return v

    @field_validator("anthropic_key")
    @classmethod
    def validate_anthropic_key(cls, v: Optional[str]) -> Optional[str]:
        """Validate Anthropic key format."""
        if v and not v.startswith("sk-ant-"):
            raise ValueError("Anthropic key must start with 'sk-ant-'")
        return v

    @model_validator(mode="after")
    def validate_at_least_one_key(self) -> "BYOKTestKeysRequest":
        """Ensure at least one provider key is provided."""
        if not self.openai_key and not self.anthropic_key:
            raise ValueError("At least one provider key must be provided")
        return self


class ProviderValidationResult(BaseModel):
    """Validation result for a single provider's API key."""

    valid: bool
    models: List[str] = []
    error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BYOKTestKeysResponse(BaseModel):
    """Response body for test keys endpoint with validation results."""

    openai: ProviderValidationResult
    anthropic: ProviderValidationResult

    model_config = ConfigDict(from_attributes=True)


class BYOKRotateKeysRequest(BaseModel):
    """Request body for rotating BYOK tenant's provider keys."""

    new_openai_key: Optional[str] = None
    new_anthropic_key: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("new_openai_key")
    @classmethod
    def validate_new_openai_key(cls, v: Optional[str]) -> Optional[str]:
        """Validate new OpenAI key format."""
        if v and not v.startswith("sk-"):
            raise ValueError("OpenAI key must start with 'sk-'")
        return v

    @field_validator("new_anthropic_key")
    @classmethod
    def validate_new_anthropic_key(cls, v: Optional[str]) -> Optional[str]:
        """Validate new Anthropic key format."""
        if v and not v.startswith("sk-ant-"):
            raise ValueError("Anthropic key must start with 'sk-ant-'")
        return v

    @model_validator(mode="after")
    def validate_at_least_one_key(self) -> "BYOKRotateKeysRequest":
        """Ensure at least one new provider key is provided."""
        if not self.new_openai_key and not self.new_anthropic_key:
            raise ValueError("At least one new provider key must be provided")
        return self


class BYOKStatusResponse(BaseModel):
    """Response body for BYOK status endpoint."""

    byok_enabled: bool
    providers_configured: List[str]
    enabled_at: Optional[datetime] = None
    cost_tracking_mode: str  # "platform" or "byok"

    model_config = ConfigDict(from_attributes=True)


class BYOKEnableResponse(BaseModel):
    """Response body for enable BYOK endpoint."""

    success: bool
    virtual_key_created: bool
    message: str
    providers_configured: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True)


class BYOKRotateKeysResponse(BaseModel):
    """Response body for rotate keys endpoint."""

    success: bool
    new_virtual_key_created: bool
    message: str
    providers_updated: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True)


class BYOKDisableResponse(BaseModel):
    """Response body for disable BYOK endpoint."""

    success: bool
    reverted_to_platform: bool
    message: str

    model_config = ConfigDict(from_attributes=True)
