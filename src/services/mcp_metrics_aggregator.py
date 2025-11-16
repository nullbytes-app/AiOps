"""
MCP Server Metrics Aggregation Service.

Story: 11.2.4 - Enhanced MCP Health Monitoring (AC5)

This module provides SQL-based metrics aggregation from the mcp_server_metrics table.
Calculates success rates, response time percentiles, error distributions, and
performance trends for MCP servers.

Functions:
    - get_server_metrics(): Aggregate metrics for API response
    - get_percentile(): Calculate percentile from values list
    - calculate_trend(): Analyze 24h performance trend

Dependencies:
    - PostgreSQL PERCENTILE_CONT() function for SQL-based percentiles
    - SQLAlchemy 2.0 async queries
    - MCPServerMetric model from Story 11.2.4
"""

from datetime import datetime, timedelta, timezone
from typing import Dict
from uuid import UUID

from loguru import logger
from sqlalchemy import func, select, case, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import MCPServer, MCPServerMetric
from src.schemas.mcp_metrics import MCPServerMetrics, MetricsData


async def get_server_metrics(
    server_id: UUID,
    period_hours: int,
    db: AsyncSession
) -> MCPServerMetrics:
    """
    Aggregate health metrics for MCP server over time period.

    Story: 11.2.4 - Enhanced MCP Health Monitoring (AC5)

    Executes SQL aggregations with PERCENTILE_CONT() for P50/P95/P99 calculations.
    Calculates success/error rates, error distribution, and performance trend.

    Args:
        server_id: MCP server UUID
        period_hours: Time period to analyze (1-168 hours)
        db: AsyncSession for database queries

    Returns:
        MCPServerMetrics with aggregated data (success_rate, percentiles, trend)

    Raises:
        ValueError: If server not found or period_hours invalid

    Example:
        >>> metrics = await get_server_metrics(server_id, 24, db)
        >>> print(metrics.metrics.success_rate)
        0.985
        >>> print(metrics.metrics.p95_response_time_ms)
        280
    """
    # Validate period_hours
    if not 1 <= period_hours <= 168:
        raise ValueError("period_hours must be between 1 and 168 (7 days)")

    # Get server for name
    server = await db.get(MCPServer, server_id)
    if not server:
        raise ValueError(f"Server {server_id} not found")

    # Calculate time window
    since = datetime.now(timezone.utc) - timedelta(hours=period_hours)

    # SQL aggregations with PERCENTILE_CONT for percentiles
    # Following 2025 SQLAlchemy patterns from Context7 MCP research
    result = await db.execute(
        select(
            func.count(MCPServerMetric.id).label("total_checks"),
            func.avg(MCPServerMetric.response_time_ms).label("avg_response_time_ms"),
            func.max(MCPServerMetric.response_time_ms).label("max_response_time_ms"),
            func.percentile_cont(0.5).within_group(MCPServerMetric.response_time_ms).label("p50"),
            func.percentile_cont(0.95).within_group(MCPServerMetric.response_time_ms).label("p95"),
            func.percentile_cont(0.99).within_group(MCPServerMetric.response_time_ms).label("p99"),
            func.sum(
                case((MCPServerMetric.status == "success", 1), else_=0)
            ).label("success_count"),
        )
        .where(
            and_(
                MCPServerMetric.mcp_server_id == server_id,
                MCPServerMetric.check_timestamp >= since,
            )
        )
    )
    row = result.one()

    total_checks = row.total_checks or 0
    if total_checks == 0:
        # No metrics in period - return empty metrics
        return MCPServerMetrics(
            server_id=server_id,
            server_name=server.name,
            period_hours=period_hours,
            metrics=MetricsData(
                total_checks=0,
                success_rate=0.0,
                error_rate=0.0,
                avg_response_time_ms=0,
                p50_response_time_ms=0,
                p95_response_time_ms=0,
                p99_response_time_ms=0,
                max_response_time_ms=0,
                errors_by_type={},
                uptime_percentage=0.0,
                last_24h_trend="stable",
            ),
        )

    # Calculate rates
    success_count = row.success_count or 0
    success_rate = success_count / total_checks
    error_rate = 1.0 - success_rate
    uptime_percentage = success_rate * 100.0

    # Get error distribution
    errors_by_type = await _get_errors_by_type(server_id, since, db)

    # Calculate trend (comparing last 24h vs previous 24h)
    trend = await calculate_trend(server_id, db)

    return MCPServerMetrics(
        server_id=server_id,
        server_name=server.name,
        period_hours=period_hours,
        metrics=MetricsData(
            total_checks=total_checks,
            success_rate=round(success_rate, 3),
            error_rate=round(error_rate, 3),
            avg_response_time_ms=int(row.avg_response_time_ms or 0),
            p50_response_time_ms=int(row.p50 or 0),
            p95_response_time_ms=int(row.p95 or 0),
            p99_response_time_ms=int(row.p99 or 0),
            max_response_time_ms=int(row.max_response_time_ms or 0),
            errors_by_type=errors_by_type,
            uptime_percentage=round(uptime_percentage, 1),
            last_24h_trend=trend,
        ),
    )


async def _get_errors_by_type(
    server_id: UUID,
    since: datetime,
    db: AsyncSession
) -> Dict[str, int]:
    """
    Get error count breakdown by error_type.

    Args:
        server_id: MCP server UUID
        since: Start timestamp for query window
        db: AsyncSession for database queries

    Returns:
        Dict mapping error_type to count (e.g., {"TimeoutError": 28})
    """
    result = await db.execute(
        select(
            MCPServerMetric.error_type,
            func.count(MCPServerMetric.id).label("count"),
        )
        .where(
            and_(
                MCPServerMetric.mcp_server_id == server_id,
                MCPServerMetric.check_timestamp >= since,
                MCPServerMetric.status != "success",
                MCPServerMetric.error_type.isnot(None),
            )
        )
        .group_by(MCPServerMetric.error_type)
    )

    return {row.error_type: row.count for row in result.all()}


async def calculate_trend(
    server_id: UUID,
    db: AsyncSession
) -> str:
    """
    Calculate performance trend by comparing last 24h vs previous 24h.

    Story: 11.2.4 - Enhanced MCP Health Monitoring (AC5)

    Trend determination:
    - 'improving': Avg response time decreased > 10%
    - 'degrading': Avg response time increased > 10%
    - 'stable': Change within ±10%

    Args:
        server_id: MCP server UUID
        db: AsyncSession for database queries

    Returns:
        str: 'improving', 'stable', or 'degrading'

    Example:
        >>> trend = await calculate_trend(server_id, db)
        >>> print(trend)
        'stable'
    """
    now = datetime.now(timezone.utc)
    last_24h_start = now - timedelta(hours=24)
    prev_24h_start = now - timedelta(hours=48)

    # Get avg response time for last 24 hours
    result_last = await db.execute(
        select(func.avg(MCPServerMetric.response_time_ms))
        .where(
            and_(
                MCPServerMetric.mcp_server_id == server_id,
                MCPServerMetric.check_timestamp >= last_24h_start,
            )
        )
    )
    avg_last_24h = result_last.scalar()

    # Get avg response time for previous 24 hours
    result_prev = await db.execute(
        select(func.avg(MCPServerMetric.response_time_ms))
        .where(
            and_(
                MCPServerMetric.mcp_server_id == server_id,
                MCPServerMetric.check_timestamp >= prev_24h_start,
                MCPServerMetric.check_timestamp < last_24h_start,
            )
        )
    )
    avg_prev_24h = result_prev.scalar()

    # If either period has no data, return stable
    if not avg_last_24h or not avg_prev_24h:
        return "stable"

    # Calculate percentage change
    change_percent = ((avg_last_24h - avg_prev_24h) / avg_prev_24h) * 100

    # Determine trend
    if change_percent < -10:
        return "improving"  # Response time decreased > 10%
    elif change_percent > 10:
        return "degrading"  # Response time increased > 10%
    else:
        return "stable"  # Within ±10%


async def get_percentile(values: list[int], percentile: int) -> int:
    """
    Calculate percentile from values list (for non-SQL use cases).

    Story: 11.2.4 - Enhanced MCP Health Monitoring (AC5)

    Uses manual sorting for percentile calculation. For SQL queries,
    prefer PERCENTILE_CONT() which is more efficient.

    Args:
        values: List of integer values (e.g., response times in ms)
        percentile: Percentile to calculate (0-100)

    Returns:
        int: Percentile value

    Raises:
        ValueError: If values empty or percentile invalid

    Example:
        >>> values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        >>> p95 = await get_percentile(values, 95)
        >>> print(p95)
        95
    """
    if not values:
        raise ValueError("Cannot calculate percentile of empty list")

    if not 0 <= percentile <= 100:
        raise ValueError("Percentile must be between 0 and 100")

    sorted_values = sorted(values)
    index = int((percentile / 100) * (len(sorted_values) - 1))
    return sorted_values[index]
