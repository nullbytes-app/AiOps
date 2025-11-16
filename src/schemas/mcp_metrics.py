"""
Pydantic schemas for MCP server health metrics.

Story: 11.2.4 - Enhanced MCP Health Monitoring

This module defines Pydantic schemas for time-series health metrics collection,
aggregation, and API responses. Used by:
- src/services/mcp_health_monitor.py (metrics recording)
- src/services/mcp_metrics_aggregator.py (metrics analysis)
- src/api/mcp_servers.py (GET /metrics endpoint)

Schemas:
    - MCPHealthCheckStatus: Enum for health check result statuses
    - MCPHealthMetric: Individual health check measurement record
    - MCPServerMetrics: Aggregated metrics for API response
    - MCPMetricsQueryParams: Query parameters for metrics endpoint

All schemas use Pydantic v2 patterns (ConfigDict, Field, field_validator).
Following 2025 best practices from Context7 MCP research.
"""

from datetime import datetime
from enum import Enum
from typing import Dict
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MCPHealthCheckStatus(str, Enum):
    """
    Health check result status enum.

    Values align with database schema (mcp_server_metrics.status column).

    Attributes:
        SUCCESS: Health check succeeded (response time < timeout)
        TIMEOUT: Health check exceeded configured timeout
        ERROR: General error during health check execution
        CONNECTION_FAILED: Failed to establish connection to MCP server
    """

    SUCCESS = "success"
    TIMEOUT = "timeout"
    ERROR = "error"
    CONNECTION_FAILED = "connection_failed"


class MCPHealthMetric(BaseModel):
    """
    Schema for individual health check metric record.

    Represents a single health check measurement recorded to mcp_server_metrics table.
    Created by mcp_health_monitor.perform_detailed_health_check().

    Attributes:
        mcp_server_id: MCP server that was health checked
        tenant_id: Tenant for row-level security
        response_time_ms: Response time in milliseconds (must be >= 0)
        check_timestamp: When the check was performed
        status: Health check result (success/timeout/error/connection_failed)
        error_message: Error details if status != success (optional)
        error_type: Error classification (e.g., 'TimeoutError', 'ProcessCrashed')
        check_type: Type of health check ('health_check', 'tools_list', 'ping')
        transport_type: Transport protocol ('stdio' or 'http_sse')

    Example:
        {
            "mcp_server_id": "550e8400-e29b-41d4-a716-446655440000",
            "tenant_id": "660e8400-e29b-41d4-a716-446655440001",
            "response_time_ms": 125,
            "check_timestamp": "2025-11-10T12:30:00Z",
            "status": "success",
            "error_message": null,
            "error_type": null,
            "check_type": "tools_list",
            "transport_type": "stdio"
        }

    Error Example:
        {
            "mcp_server_id": "550e8400-e29b-41d4-a716-446655440000",
            "tenant_id": "660e8400-e29b-41d4-a716-446655440001",
            "response_time_ms": 5000,
            "check_timestamp": "2025-11-10T12:35:00Z",
            "status": "timeout",
            "error_message": "Health check exceeded 5000ms timeout",
            "error_type": "TimeoutError",
            "check_type": "tools_list",
            "transport_type": "stdio"
        }
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "mcp_server_id": "550e8400-e29b-41d4-a716-446655440000",
                    "tenant_id": "660e8400-e29b-41d4-a716-446655440001",
                    "response_time_ms": 125,
                    "check_timestamp": "2025-11-10T12:30:00Z",
                    "status": "success",
                    "error_message": None,
                    "error_type": None,
                    "check_type": "tools_list",
                    "transport_type": "stdio",
                }
            ]
        }
    )

    mcp_server_id: UUID = Field(..., description="MCP server identifier")
    tenant_id: UUID = Field(..., description="Tenant for isolation")
    response_time_ms: int = Field(..., ge=0, description="Response time in milliseconds")
    check_timestamp: datetime = Field(
        ..., description="When the health check was performed (ISO 8601)"
    )
    status: MCPHealthCheckStatus = Field(..., description="Health check result status")
    error_message: str | None = Field(
        None, description="Error details if status != success"
    )
    error_type: str | None = Field(
        None, description="Error type classification (e.g., 'TimeoutError')"
    )
    check_type: str = Field(
        ...,
        description="Type of health check: 'health_check', 'tools_list', 'ping'",
        examples=["health_check", "tools_list", "ping"],
    )
    transport_type: str = Field(
        ...,
        description="Transport protocol: 'stdio' or 'http_sse'",
        pattern="^(stdio|http_sse)$",
    )

    @field_validator("response_time_ms")
    @classmethod
    def validate_response_time(cls, v: int) -> int:
        """
        Validate response_time_ms is non-negative.

        Args:
            v: Response time in milliseconds

        Returns:
            int: Validated response time

        Raises:
            ValueError: If response time is negative
        """
        if v < 0:
            raise ValueError("response_time_ms must be >= 0")
        return v


class MCPServerMetrics(BaseModel):
    """
    Schema for aggregated MCP server health metrics API response.

    Returned by GET /api/v1/mcp-servers/{id}/metrics endpoint.
    Calculated by mcp_metrics_aggregator.get_server_metrics().

    Aggregates raw metrics from mcp_server_metrics table over a time period
    to provide:
    - Success/error rates
    - Response time percentiles (P50, P95, P99)
    - Error breakdown by type
    - Uptime percentage
    - Performance trend analysis

    Attributes:
        server_id: MCP server identifier
        server_name: Server name for display
        period_hours: Time period analyzed (default 24h)
        metrics: Aggregated metric calculations

    Example:
        {
            "server_id": "550e8400-e29b-41d4-a716-446655440000",
            "server_name": "filesystem-server",
            "period_hours": 24,
            "metrics": {
                "total_checks": 2880,
                "success_rate": 0.985,
                "error_rate": 0.015,
                "avg_response_time_ms": 125,
                "p50_response_time_ms": 95,
                "p95_response_time_ms": 280,
                "p99_response_time_ms": 450,
                "max_response_time_ms": 1200,
                "errors_by_type": {
                    "TimeoutError": 28,
                    "ProcessCrashed": 5,
                    "InvalidJSON": 10
                },
                "uptime_percentage": 98.5,
                "last_24h_trend": "stable"
            }
        }
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "server_id": "550e8400-e29b-41d4-a716-446655440000",
                    "server_name": "filesystem-server",
                    "period_hours": 24,
                    "metrics": {
                        "total_checks": 2880,
                        "success_rate": 0.985,
                        "error_rate": 0.015,
                        "avg_response_time_ms": 125,
                        "p50_response_time_ms": 95,
                        "p95_response_time_ms": 280,
                        "p99_response_time_ms": 450,
                        "max_response_time_ms": 1200,
                        "errors_by_type": {"TimeoutError": 28, "ProcessCrashed": 5},
                        "uptime_percentage": 98.5,
                        "last_24h_trend": "stable",
                    },
                }
            ]
        }
    )

    server_id: UUID = Field(..., description="MCP server identifier")
    server_name: str = Field(..., description="Server name for display")
    period_hours: int = Field(..., description="Time period analyzed in hours")
    metrics: "MetricsData" = Field(..., description="Aggregated metric calculations")


class MetricsData(BaseModel):
    """
    Nested schema for aggregated metrics data.

    Contains calculated statistics from raw health check metrics:
    - Count aggregations (total_checks, error counts by type)
    - Rate calculations (success_rate, error_rate, uptime_percentage)
    - Percentiles (P50, P95, P99 response times)
    - Trend analysis (improving/stable/degrading)

    All percentages are represented as floats (0.0 to 1.0).
    Trend values: 'improving', 'stable', 'degrading'.

    Attributes:
        total_checks: Total health checks performed in period
        success_rate: Success rate (0.0 to 1.0)
        error_rate: Error rate (0.0 to 1.0)
        avg_response_time_ms: Average response time
        p50_response_time_ms: Median response time (50th percentile)
        p95_response_time_ms: 95th percentile response time
        p99_response_time_ms: 99th percentile response time
        max_response_time_ms: Maximum response time observed
        errors_by_type: Error count breakdown by error_type
        uptime_percentage: Uptime percentage (0.0 to 100.0)
        last_24h_trend: Trend analysis ('improving', 'stable', 'degrading')
    """

    total_checks: int = Field(..., ge=0, description="Total health checks performed")
    success_rate: float = Field(
        ..., ge=0.0, le=1.0, description="Success rate (0.0 to 1.0)"
    )
    error_rate: float = Field(..., ge=0.0, le=1.0, description="Error rate (0.0 to 1.0)")
    avg_response_time_ms: int = Field(
        ..., ge=0, description="Average response time in milliseconds"
    )
    p50_response_time_ms: int = Field(
        ..., ge=0, description="Median (50th percentile) response time"
    )
    p95_response_time_ms: int = Field(
        ..., ge=0, description="95th percentile response time"
    )
    p99_response_time_ms: int = Field(
        ..., ge=0, description="99th percentile response time"
    )
    max_response_time_ms: int = Field(
        ..., ge=0, description="Maximum response time observed"
    )
    errors_by_type: Dict[str, int] = Field(
        ..., description="Error count breakdown by error_type"
    )
    uptime_percentage: float = Field(
        ..., ge=0.0, le=100.0, description="Uptime percentage (0.0 to 100.0)"
    )
    last_24h_trend: str = Field(
        ...,
        description="Performance trend: 'improving', 'stable', or 'degrading'",
        pattern="^(improving|stable|degrading)$",
    )


# Rebuild forward references for nested models
MCPServerMetrics.model_rebuild()


class MCPMetricsQueryParams(BaseModel):
    """
    Query parameters for GET /api/v1/mcp-servers/{id}/metrics endpoint.

    Controls time period and granularity for metrics aggregation.

    Attributes:
        period_hours: Time period to analyze (default 24, max 168 for 7 days)
        granularity: Aggregation granularity ('hourly' or 'daily')

    Example:
        GET /api/v1/mcp-servers/{id}/metrics?period_hours=48&granularity=hourly
    """

    period_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Time period in hours (max 168 for 7 days retention)",
    )
    granularity: str = Field(
        default="hourly",
        description="Aggregation granularity: 'hourly' or 'daily'",
        pattern="^(hourly|daily)$",
    )


# Export all schemas
__all__ = [
    "MCPHealthCheckStatus",
    "MCPHealthMetric",
    "MCPServerMetrics",
    "MetricsData",
    "MCPMetricsQueryParams",
]
