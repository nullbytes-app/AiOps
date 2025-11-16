"""
Agent Performance Metrics DTOs (Data Transfer Objects).

Pydantic v2 schemas for agent performance metrics, execution history, trends,
error analysis, and token usage. Used in service layer and API responses.

Following 2025 best practices:
- Pydantic v2 with @field_validator
- Type hints with Optional, UUID, date
- ConfigDict for model configuration
"""

from datetime import date, datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator


class AgentMetricsDTO(BaseModel):
    """Per-agent execution metrics summary."""

    model_config = ConfigDict(from_attributes=True)

    agent_id: UUID = Field(..., description="Agent ID")
    agent_name: str = Field(..., description="Agent name")
    total_executions: int = Field(default=0, description="Total execution count")
    successful_executions: int = Field(default=0, description="Successful executions")
    failed_executions: int = Field(default=0, description="Failed executions")
    success_rate: float = Field(
        default=0.0, description="Success rate as percentage (0-100)"
    )
    average_duration_seconds: float = Field(
        default=0.0, description="Average execution duration in seconds"
    )
    p50_latency_seconds: float = Field(default=0.0, description="P50 latency in seconds")
    p95_latency_seconds: float = Field(default=0.0, description="P95 latency in seconds")
    p99_latency_seconds: float = Field(default=0.0, description="P99 latency in seconds")
    start_date: Optional[date] = Field(default=None, description="Query start date")
    end_date: Optional[date] = Field(default=None, description="Query end date")

    @field_validator("success_rate")
    @classmethod
    def validate_success_rate(cls, v: float) -> float:
        """Ensure success rate is between 0-100."""
        if not 0 <= v <= 100:
            raise ValueError("success_rate must be between 0 and 100")
        return v


class ExecutionRecordDTO(BaseModel):
    """Single execution record from history."""

    model_config = ConfigDict(from_attributes=True)

    execution_id: UUID = Field(..., description="Execution record ID")
    timestamp: datetime = Field(..., description="When execution occurred")
    status: str = Field(..., description="success or failed")
    duration_ms: int = Field(..., description="Execution duration in milliseconds")
    input_tokens: int = Field(default=0, description="Input tokens used")
    output_tokens: int = Field(default=0, description="Output tokens used")
    total_tokens: int = Field(default=0, description="Total tokens")
    estimated_cost_usd: float = Field(default=0.0, description="Estimated cost in USD")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    error_type: Optional[str] = Field(default=None, description="Error category")


class TrendDataDTO(BaseModel):
    """Daily trend data for charting."""

    model_config = ConfigDict(from_attributes=True)

    trend_date: date = Field(..., alias="date", description="Date of trend point")
    execution_count: int = Field(default=0, description="Executions on this day")
    average_duration_seconds: float = Field(
        default=0.0, description="Avg duration on this day"
    )
    successful: int = Field(default=0, description="Successful executions")
    failed: int = Field(default=0, description="Failed executions")


class ErrorAnalysisDTO(BaseModel):
    """Error type breakdown."""

    model_config = ConfigDict(from_attributes=True)

    error_type: str = Field(..., description="Error category (timeout, rate_limit, etc)")
    count: int = Field(default=0, description="Number of errors of this type")
    percentage: float = Field(default=0.0, description="Percentage of total errors")


class AgentTokenUsageDTO(BaseModel):
    """Token usage aggregated by agent."""

    model_config = ConfigDict(from_attributes=True)

    agent_id: UUID = Field(..., description="Agent ID")
    agent_name: str = Field(..., description="Agent name")
    input_tokens: int = Field(default=0, description="Total input tokens")
    output_tokens: int = Field(default=0, description="Total output tokens")
    total_tokens: int = Field(default=0, description="Total tokens")
    execution_count: int = Field(default=0, description="Number of executions")
    average_tokens_per_execution: float = Field(
        default=0.0, description="Avg tokens per execution"
    )


class SlowAgentMetricsDTO(BaseModel):
    """Agent metrics sorted by latency (for optimization)."""

    model_config = ConfigDict(from_attributes=True)

    agent_id: UUID = Field(..., description="Agent ID")
    agent_name: str = Field(..., description="Agent name")
    execution_count: int = Field(default=0, description="Total executions")
    p95_latency_seconds: float = Field(..., description="P95 latency in seconds")
    average_duration_seconds: float = Field(
        default=0.0, description="Average duration in seconds"
    )
    success_rate: float = Field(default=0.0, description="Success rate percentage")
    optimization_recommendation: str = Field(
        default="Performance OK", description="Optimization suggestion"
    )


class ExecutionFiltersDTO(BaseModel):
    """Filters for execution history queries."""

    model_config = ConfigDict(from_attributes=True)

    status: Optional[str] = Field(default=None, description="success or failed")
    start_date: Optional[date] = Field(default=None, description="Start date")
    end_date: Optional[date] = Field(default=None, description="End date")
    agent_name_search: Optional[str] = Field(default=None, description="Agent name pattern")


class PerformanceMetricsResponseDTO(BaseModel):
    """API response wrapper for performance metrics."""

    model_config = ConfigDict(from_attributes=True)

    metrics: AgentMetricsDTO = Field(..., description="Agent metrics")
    query_executed_at: datetime = Field(
        default_factory=datetime.utcnow, description="When query executed"
    )
