"""Pydantic schemas for fallback chain configuration and management."""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict


class FallbackChainCreate(BaseModel):
    """Schema for creating a new fallback chain."""

    model_id: int = Field(..., description="Primary model ID")
    fallback_model_ids: List[int] = Field(
        ..., min_length=1, description="List of fallback model IDs in order"
    )
    enabled: bool = Field(default=True, description="Chain enabled status")

    @field_validator("fallback_model_ids")
    @classmethod
    def validate_no_duplicates(cls, v):
        """Ensure no duplicate model IDs in fallback chain."""
        if len(v) != len(set(v)):
            raise ValueError("Duplicate model IDs in fallback chain")
        return v


class FallbackChainUpdate(BaseModel):
    """Schema for updating an existing fallback chain."""

    fallback_model_ids: List[int] = Field(
        ..., min_length=1, description="Updated list of fallback model IDs in order"
    )
    enabled: Optional[bool] = Field(default=None, description="Chain enabled status")

    @field_validator("fallback_model_ids")
    @classmethod
    def validate_no_duplicates(cls, v):
        """Ensure no duplicate model IDs in fallback chain."""
        if len(v) != len(set(v)):
            raise ValueError("Duplicate model IDs in fallback chain")
        return v


class FallbackChainResponse(BaseModel):
    """Schema for fallback chain API response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    model_id: int
    fallback_order: int
    fallback_model_id: int
    enabled: bool
    created_at: datetime
    updated_at: datetime


class FallbackChainsListResponse(BaseModel):
    """Schema for listing fallback chains."""

    model_id: int
    model_name: str
    provider_name: str
    fallback_chain: List[dict] = Field(
        default_factory=list, description="Ordered list of fallback models"
    )
    enabled: bool
    created_at: datetime


class FallbackTriggerConfig(BaseModel):
    """Schema for fallback trigger configuration."""

    trigger_type: str = Field(
        ...,
        description="Error type: RateLimitError, TimeoutError, InternalServerError, ConnectionError, ContentPolicyViolationError",
    )
    retry_count: int = Field(
        default=3, ge=0, le=10, description="Number of retry attempts (0-10)"
    )
    backoff_factor: float = Field(
        default=2.0, ge=1.0, le=5.0, description="Exponential backoff multiplier (1.0-5.0)"
    )
    enabled: bool = Field(default=True, description="Trigger enabled status")


class FallbackTriggerResponse(BaseModel):
    """Schema for fallback trigger API response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    trigger_type: str
    retry_count: int
    backoff_factor: float
    enabled: bool
    created_at: datetime


class FallbackMetricResponse(BaseModel):
    """Schema for fallback metrics API response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    model_id: int
    model_name: str
    trigger_type: str
    fallback_model_id: Optional[int]
    fallback_model_name: Optional[str]
    trigger_count: int
    success_count: int
    failure_count: int
    success_rate: float = Field(description="Success rate as percentage (0-100)")
    last_triggered_at: Optional[datetime]
    created_at: datetime


class FallbackMetricsAggregateResponse(BaseModel):
    """Schema for aggregated fallback metrics."""

    total_fallbacks: int
    total_success: int
    total_failure: int
    overall_success_rate: float = Field(description="Overall success rate as percentage")
    avg_response_time_ms: Optional[float] = Field(
        default=None, description="Average response time in milliseconds"
    )
    metrics_by_model: List[dict] = Field(
        default_factory=list, description="Per-model metrics"
    )
    metrics_by_trigger: List[dict] = Field(
        default_factory=list, description="Per-trigger-type metrics"
    )


class FallbackTestRequest(BaseModel):
    """Schema for testing fallback chain."""

    model_id: int = Field(..., description="Model to test")
    test_message: str = Field(
        default="Test fallback chain", description="Test prompt message"
    )
    failure_type: str = Field(
        ...,
        description="Failure type to simulate: rate_limit, timeout, server_error, connection",
    )


class FallbackTestResponse(BaseModel):
    """Schema for fallback test results."""

    primary_model: str
    primary_failed: bool
    attempts: List[dict] = Field(
        default_factory=list,
        description="List of retry attempts with status and timing",
    )
    fallback_triggered: bool
    fallback_model_used: Optional[str]
    final_response: Optional[str]
    success: bool
    total_time_ms: float
    error_message: Optional[str]


class CircularFallbackError(BaseModel):
    """Schema for circular fallback error response."""

    error: str = Field(..., description="Error message about circular chain")
    chain: List[str] = Field(
        ..., description="Models involved in circular chain"
    )
