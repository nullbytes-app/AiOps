"""Pydantic models for tenant spend and budget tracking.

Defines request/response schemas for tenant spend queries and budget dashboards,
with proper validation and tenant isolation.
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ModelSpendResponse(BaseModel):
    """Per-model spend breakdown from LiteLLM.

    Attributes:
        model: Model name (e.g., 'gpt-4', 'claude-3-opus')
        spend: Spend in USD for this model
        percentage: Percentage of total spend (0-100)
        requests: Number of requests to this model
    """

    model: str = Field(..., description="LLM model name")
    spend: float = Field(..., ge=0.0, description="Spend in USD")
    percentage: float = Field(..., ge=0.0, le=100.0, description="Percentage of total")
    requests: int = Field(..., ge=0, description="Number of requests")

    model_config = ConfigDict(json_schema_extra={"example": {
        "model": "gpt-4",
        "spend": 30.50,
        "percentage": 66.7,
        "requests": 125,
    }})


class TenantSpendResponse(BaseModel):
    """Real-time spend data for a tenant from LiteLLM.

    Attributes:
        tenant_id: Tenant identifier
        current_spend: Current spend in USD
        max_budget: Maximum budget in USD
        utilization_pct: Budget utilization percentage (0-100+)
        models_breakdown: List of per-model spend details
        last_updated: When spend data was fetched from LiteLLM
        budget_duration: Budget period (e.g., '30d')
        budget_reset_at: When budget resets (ISO 8601 format)
    """

    tenant_id: str = Field(..., description="Tenant identifier")
    current_spend: float = Field(..., ge=0.0, description="Current spend in USD")
    max_budget: float = Field(..., gt=0.0, description="Maximum budget in USD")
    utilization_pct: float = Field(..., ge=0.0, description="Budget utilization %")
    models_breakdown: List[ModelSpendResponse] = Field(
        default_factory=list, description="Per-model spend breakdown"
    )
    last_updated: datetime = Field(..., description="When spend was fetched from LiteLLM")
    budget_duration: Optional[str] = Field(None, description="Budget period (e.g., '30d')")
    budget_reset_at: Optional[str] = Field(None, description="Budget reset timestamp")

    model_config = ConfigDict(json_schema_extra={"example": {
        "tenant_id": "acme-corp",
        "current_spend": 45.67,
        "max_budget": 500.00,
        "utilization_pct": 9.13,
        "models_breakdown": [
            {"model": "gpt-4", "spend": 30.50, "percentage": 66.7, "requests": 125},
            {"model": "claude-3-opus", "spend": 15.17, "percentage": 33.3, "requests": 45},
        ],
        "last_updated": "2025-11-07T12:30:45.123456Z",
        "budget_duration": "30d",
        "budget_reset_at": "2025-12-07T00:00:00Z",
    }})
