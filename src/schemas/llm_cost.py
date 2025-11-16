"""
LLM Cost Dashboard Schemas.

Pydantic v2 schemas for cost tracking DTOs (Data Transfer Objects).
Used by LLMCostService and cost API endpoints.

Following 2025 Pydantic v2 best practices:
- ConfigDict for model configuration
- @field_validator for custom validation
- Strict type hints with Optional, UUID, datetime
"""

from datetime import date, datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TenantSpendDTO(BaseModel):
    """
    Tenant spend summary.

    Used for AC#2 (spend by tenant - top 10).
    """

    model_config = ConfigDict(from_attributes=True)

    tenant_id: str  # VARCHAR(100) matching tenant_configs.tenant_id
    tenant_name: str
    total_spend: float = Field(ge=0.0, description="Total spend in USD")
    rank: int = Field(ge=1, le=10, description="Rank by spend (1=highest)")


class AgentSpendDTO(BaseModel):
    """
    Agent spend summary with execution statistics.

    Used for AC#6 (cost per agent table).
    """

    model_config = ConfigDict(from_attributes=True)

    agent_id: Optional[UUID] = None
    agent_name: str
    execution_count: int = Field(ge=0, description="Number of executions")
    total_cost: float = Field(ge=0.0, description="Total cost in USD")
    avg_cost: float = Field(ge=0.0, description="Average cost per execution in USD")

    @field_validator("avg_cost", mode="before")
    @classmethod
    def calculate_avg_cost(cls, v: float, info) -> float:
        """Calculate average cost from total and count if not provided."""
        if v is None and info.data.get("execution_count", 0) > 0:
            return info.data["total_cost"] / info.data["execution_count"]
        return v or 0.0


class ModelSpendDTO(BaseModel):
    """
    Model spend summary.

    Used for AC#2 (spend by model) and AC#4 (token breakdown).
    """

    model_config = ConfigDict(from_attributes=True)

    model_name: str
    total_spend: float = Field(ge=0.0, description="Total spend in USD")
    total_tokens: int = Field(ge=0, description="Total tokens consumed")
    prompt_tokens: int = Field(ge=0, description="Input tokens")
    completion_tokens: int = Field(ge=0, description="Output tokens")


class DailySpendDTO(BaseModel):
    """
    Daily spend aggregation for trend chart.

    Used for AC#3 (cost trends chart - last 30 days).
    """

    model_config = ConfigDict(from_attributes=True)

    date: date
    total_spend: float = Field(ge=0.0, description="Total spend for the day in USD")
    transaction_count: int = Field(
        ge=0, description="Number of LLM API calls on this day"
    )


class TokenBreakdownDTO(BaseModel):
    """
    Token usage breakdown by type.

    Used for AC#4 (pie chart of input vs output tokens).
    """

    model_config = ConfigDict(from_attributes=True)

    model_name: str
    prompt_tokens: int = Field(ge=0, description="Input tokens")
    completion_tokens: int = Field(ge=0, description="Output tokens")
    total_tokens: int = Field(ge=0, description="Total tokens")
    prompt_percentage: float = Field(
        ge=0.0, le=100.0, description="Percentage of input tokens"
    )
    completion_percentage: float = Field(
        ge=0.0, le=100.0, description="Percentage of output tokens"
    )

    @field_validator("prompt_percentage", "completion_percentage", mode="before")
    @classmethod
    def calculate_percentages(cls, v: float, info) -> float:
        """Calculate token percentages if not provided."""
        if v is None:
            total = info.data.get("total_tokens", 0)
            if total == 0:
                return 0.0
            field_name = info.field_name
            if field_name == "prompt_percentage":
                return (info.data.get("prompt_tokens", 0) / total) * 100
            elif field_name == "completion_percentage":
                return (info.data.get("completion_tokens", 0) / total) * 100
        return v


class BudgetUtilizationDTO(BaseModel):
    """
    Tenant budget utilization summary.

    Used for AC#5 (budget utilization progress bars).
    """

    model_config = ConfigDict(from_attributes=True)

    tenant_id: str  # VARCHAR(100) matching tenant_configs.tenant_id
    tenant_name: str
    budget_limit: float = Field(ge=0.0, description="Monthly budget limit in USD")
    current_spend: float = Field(ge=0.0, description="Current month spend in USD")
    remaining: float = Field(ge=0.0, description="Remaining budget in USD")
    utilization_pct: float = Field(
        ge=0.0, le=200.0, description="Budget utilization percentage"
    )
    color: str = Field(
        description="Color indicator (green/yellow/red)", pattern="^(green|yellow|red)$"
    )
    is_byok: bool = Field(
        default=False, description="True if tenant uses own keys (BYOK)"
    )

    @field_validator("remaining", mode="before")
    @classmethod
    def calculate_remaining(cls, v: float, info) -> float:
        """Calculate remaining budget if not provided."""
        if v is None:
            return max(
                0.0, info.data.get("budget_limit", 0.0) - info.data.get("current_spend", 0.0)
            )
        return v

    @field_validator("utilization_pct", mode="before")
    @classmethod
    def calculate_utilization(cls, v: float, info) -> float:
        """Calculate utilization percentage if not provided."""
        if v is None:
            budget = info.data.get("budget_limit", 0.0)
            if budget == 0.0:
                return 0.0
            return (info.data.get("current_spend", 0.0) / budget) * 100
        return v

    @field_validator("color", mode="before")
    @classmethod
    def determine_color(cls, v: str, info) -> str:
        """Determine color based on utilization percentage if not provided."""
        if v is None:
            util_pct = info.data.get("utilization_pct", 0.0)
            if util_pct < 70:
                return "green"
            elif util_pct < 90:
                return "yellow"
            else:
                return "red"
        return v


class CostSummaryDTO(BaseModel):
    """
    Overall cost summary with multiple time periods.

    Used for AC#2 (overview metrics).
    """

    model_config = ConfigDict(from_attributes=True)

    today_spend: float = Field(ge=0.0, description="Spend today in USD")
    week_spend: float = Field(ge=0.0, description="Spend this week in USD")
    month_spend: float = Field(ge=0.0, description="Spend this month in USD")
    total_spend_30d: float = Field(ge=0.0, description="Total spend last 30 days in USD")
    top_tenant: Optional[TenantSpendDTO] = None
    top_agent: Optional[AgentSpendDTO] = None


class SpendLogDetailDTO(BaseModel):
    """
    Detailed spend log entry.

    Used for CSV export (AC#7).
    """

    model_config = ConfigDict(from_attributes=True)

    date: date
    tenant_id: Optional[UUID] = None  # Optional for records without valid tenant mapping
    tenant_name: str
    agent_id: Optional[UUID] = None
    agent_name: Optional[str] = None
    model: str
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    cost: float = Field(ge=0.0, description="Cost in USD")


class CostExportRequest(BaseModel):
    """
    CSV export request parameters.

    Used for AC#7 (export functionality).
    """

    model_config = ConfigDict(from_attributes=True)

    start_date: date
    end_date: date
    tenant_id: Optional[UUID] = None
    agent_id: Optional[UUID] = None

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v: date, info) -> date:
        """Validate end_date >= start_date."""
        start = info.data.get("start_date")
        if start and v < start:
            raise ValueError("end_date must be >= start_date")
        return v
