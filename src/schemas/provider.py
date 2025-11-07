"""
Pydantic schemas for LLM provider and model configuration.

This module defines request/response schemas for provider and model management,
including validation, encryption handling, and API key masking.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from src.database.models import ProviderType


# ============================================================================
# LLM Provider Schemas
# ============================================================================


class LLMProviderBase(BaseModel):
    """Base schema for LLM provider with common fields."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Provider display name (e.g., 'Production OpenAI')",
    )
    provider_type: ProviderType = Field(
        ...,
        description="Provider type (openai, anthropic, azure_openai, etc.)",
    )
    api_base_url: str = Field(
        ...,
        min_length=1,
        description="API base URL (e.g., https://api.openai.com/v1)",
    )

    @field_validator("api_base_url")
    @classmethod
    def validate_url_format(cls, v: str) -> str:
        """Validate URL format (must start with http:// or https://)."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("API base URL must start with http:// or https://")
        return v.rstrip("/")  # Remove trailing slash


class LLMProviderCreate(LLMProviderBase):
    """Schema for creating a new LLM provider."""

    api_key: str = Field(
        ...,
        min_length=1,
        description="API key (will be encrypted before storage)",
    )

    @field_validator("api_key")
    @classmethod
    def validate_api_key_format(cls, v: str, info) -> str:
        """
        Validate API key format based on provider type.

        OpenAI keys must start with 'sk-', Anthropic keys with 'sk-ant-'.
        Other providers have custom formats.
        """
        provider_type = info.data.get("provider_type")

        if provider_type == ProviderType.OPENAI:
            if not v.startswith("sk-"):
                raise ValueError("OpenAI API keys must start with 'sk-'")
        elif provider_type == ProviderType.ANTHROPIC:
            if not v.startswith("sk-ant-"):
                raise ValueError("Anthropic API keys must start with 'sk-ant-'")
        # Bedrock uses AWS credentials (different validation)
        # Azure and custom providers have no standard prefix

        return v


class LLMProviderUpdate(BaseModel):
    """Schema for updating an existing LLM provider."""

    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Provider display name",
    )
    provider_type: Optional[ProviderType] = Field(
        None,
        description="Provider type",
    )
    api_base_url: Optional[str] = Field(
        None,
        min_length=1,
        description="API base URL",
    )
    api_key: Optional[str] = Field(
        None,
        min_length=1,
        description="API key (will be re-encrypted if changed)",
    )
    enabled: Optional[bool] = Field(
        None,
        description="Provider enabled status",
    )

    @field_validator("api_base_url")
    @classmethod
    def validate_url_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate URL format."""
        if v is not None:
            if not v.startswith(("http://", "https://")):
                raise ValueError("API base URL must start with http:// or https://")
            return v.rstrip("/")
        return v


class LLMProviderResponse(LLMProviderBase):
    """Schema for LLM provider API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Provider ID")
    api_key_masked: str = Field(
        ...,
        description="Masked API key (first 3 + last 3 characters)",
    )
    enabled: bool = Field(..., description="Provider enabled status")
    last_test_at: Optional[datetime] = Field(
        None,
        description="Timestamp of last connection test",
    )
    last_test_success: Optional[bool] = Field(
        None,
        description="Result of last connection test",
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last modification timestamp")
    model_count: Optional[int] = Field(
        None,
        description="Number of models configured for this provider",
    )


# ============================================================================
# LLM Model Schemas
# ============================================================================


class LLMModelBase(BaseModel):
    """Base schema for LLM model with common fields."""

    model_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Model identifier (e.g., 'gpt-4', 'claude-3-5-sonnet-20240620')",
    )
    display_name: Optional[str] = Field(
        None,
        max_length=255,
        description="User-friendly display name (e.g., 'GPT-4 Turbo')",
    )
    cost_per_input_token: Optional[float] = Field(
        None,
        ge=0.0,
        description="Cost per 1M input tokens in USD (e.g., 0.03 = $30/1M tokens)",
    )
    cost_per_output_token: Optional[float] = Field(
        None,
        ge=0.0,
        description="Cost per 1M output tokens in USD (e.g., 0.06 = $60/1M tokens)",
    )
    context_window: Optional[int] = Field(
        None,
        gt=0,
        le=1_000_000,
        description="Context window size in tokens (e.g., 128000 for GPT-4 Turbo)",
    )
    capabilities: Optional[dict] = Field(
        None,
        description="Model capabilities JSONB: {'streaming': true, 'function_calling': true, 'vision': true}",
    )

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(cls, v: Optional[dict]) -> Optional[dict]:
        """
        Validate capabilities JSONB structure.

        Expected keys: streaming, function_calling, vision (all boolean).
        """
        if v is not None:
            valid_keys = {"streaming", "function_calling", "vision"}
            if not all(k in valid_keys for k in v.keys()):
                raise ValueError(
                    f"Invalid capability keys. Valid keys: {valid_keys}"
                )
            if not all(isinstance(val, bool) for val in v.values()):
                raise ValueError("All capability values must be boolean")
        return v


class LLMModelCreate(LLMModelBase):
    """Schema for creating a new LLM model."""

    provider_id: int = Field(..., gt=0, description="Provider ID (foreign key)")
    enabled: bool = Field(
        False,
        description="Model enabled in LiteLLM config (default: false)",
    )


class LLMModelUpdate(BaseModel):
    """Schema for updating an existing LLM model."""

    display_name: Optional[str] = Field(
        None,
        max_length=255,
        description="User-friendly display name",
    )
    enabled: Optional[bool] = Field(
        None,
        description="Model enabled status",
    )
    cost_per_input_token: Optional[float] = Field(
        None,
        ge=0.0,
        description="Cost per 1M input tokens (USD)",
    )
    cost_per_output_token: Optional[float] = Field(
        None,
        ge=0.0,
        description="Cost per 1M output tokens (USD)",
    )
    context_window: Optional[int] = Field(
        None,
        gt=0,
        le=1_000_000,
        description="Context window size (tokens)",
    )
    capabilities: Optional[dict] = Field(
        None,
        description="Model capabilities JSONB",
    )

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(cls, v: Optional[dict]) -> Optional[dict]:
        """Validate capabilities JSONB structure."""
        if v is not None:
            valid_keys = {"streaming", "function_calling", "vision"}
            if not all(k in valid_keys for k in v.keys()):
                raise ValueError(
                    f"Invalid capability keys. Valid keys: {valid_keys}"
                )
            if not all(isinstance(val, bool) for val in v.values()):
                raise ValueError("All capability values must be boolean")
        return v


class LLMModelResponse(LLMModelBase):
    """Schema for LLM model API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Model ID")
    provider_id: int = Field(..., description="Provider ID (foreign key)")
    enabled: bool = Field(..., description="Model enabled status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last modification timestamp")


# ============================================================================
# Specialized Response Schemas
# ============================================================================


class ConnectionTestResponse(BaseModel):
    """Schema for provider connection test results."""

    success: bool = Field(..., description="Connection test success")
    models: list[str] = Field(
        default_factory=list,
        description="Available models from provider API",
    )
    response_time_ms: Optional[int] = Field(
        None,
        description="Response time in milliseconds",
    )
    error: Optional[str] = Field(
        None,
        description="Error message if test failed",
    )


class ConfigRegenerationResponse(BaseModel):
    """Schema for config regeneration API response."""

    success: bool = Field(..., description="Config regeneration success")
    backup_path: str = Field(..., description="Path to backup config file")
    config_path: str = Field(..., description="Path to new config file")
    restart_required: bool = Field(
        True,
        description="Whether LiteLLM restart is required (always true)",
    )
    restart_command: str = Field(
        default="docker-compose restart litellm",
        description="Command to restart LiteLLM proxy",
    )
    error: Optional[str] = Field(
        None,
        description="Error message if regeneration failed",
    )


class BulkModelOperation(BaseModel):
    """Schema for bulk model enable/disable operations."""

    model_ids: list[int] = Field(
        ...,
        min_length=1,
        description="List of model IDs to enable/disable",
    )


class BulkModelOperationResponse(BaseModel):
    """Schema for bulk model operation response."""

    success: bool = Field(..., description="Bulk operation success")
    updated_count: int = Field(..., description="Number of models updated")
    failed_ids: list[int] = Field(
        default_factory=list,
        description="List of model IDs that failed to update",
    )
