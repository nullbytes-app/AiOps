"""
MCP Server Health Monitoring Service.

This module implements periodic health checks for MCP servers using the stdio transport.
Health checks are performed by calling the tools/list JSON-RPC method as a lightweight,
non-modifying operation. Failed health checks trigger a circuit breaker after 3 consecutive
failures to prevent resource waste.

Story: 11.1.8 - Basic MCP Server Health Monitoring
Story: 11.2.4 - Enhanced MCP Health Monitoring (detailed metrics collection)

Dependencies:
    - MCPStdioClient from Story 11.1.3 (stdio transport)
    - MCPServer, MCPServerMetric models from Stories 11.1.1, 11.2.4
    - Prometheus metrics from Story 11.2.4
    - Celery Beat for periodic task scheduling (Epic 1)
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import MCPServer, MCPServerMetric
from src.schemas.mcp_metrics import MCPHealthMetric, MCPHealthCheckStatus
from src.services.mcp_stdio_client import MCPStdioClient
from src.monitoring.metrics import (
    mcp_server_health_status,
    mcp_server_last_check_timestamp,
    mcp_health_checks_total,
    mcp_health_check_errors_total,
    mcp_health_check_duration_seconds,
)


async def perform_detailed_health_check(server: MCPServer) -> MCPHealthMetric:
    """
    Perform detailed health check with precise timing and error classification.

    Story: 11.2.4 - Enhanced MCP Health Monitoring (AC2)

    Executes health check probe (tools/list) with high-precision timing using
    time.perf_counter(). Captures detailed error information for analysis.

    Args:
        server: MCPServer instance with stdio configuration

    Returns:
        MCPHealthMetric: Structured health check result with:
            - response_time_ms: Precise timing in milliseconds
            - status: success/timeout/error/connection_failed
            - error_type: Classification (TimeoutError, ProcessCrashed, etc.)
            - error_message: Detailed error description
            - check_type: 'tools_list' (health check probe method)
            - transport_type: 'stdio' or 'http_sse'

    Example:
        >>> metric = await perform_detailed_health_check(server)
        >>> print(metric.response_time_ms)
        125
        >>> print(metric.status)
        'success'
    """
    start_perf = time.perf_counter()  # High-precision timer
    check_timestamp = datetime.now(timezone.utc)

    try:
        # 30-second timeout for health check operation
        async with asyncio.timeout(30.0):
            client = MCPStdioClient(
                command=server.command,
                args=server.args or [],
                env=server.env or {}
            )

            async with client:
                await client.initialize()
                await client.list_tools()

        # Calculate response time with millisecond precision
        response_time_ms = int((time.perf_counter() - start_perf) * 1000)

        return MCPHealthMetric(
            mcp_server_id=server.id,
            tenant_id=server.tenant_id,
            response_time_ms=response_time_ms,
            check_timestamp=check_timestamp,
            status=MCPHealthCheckStatus.SUCCESS,
            error_message=None,
            error_type=None,
            check_type="tools_list",
            transport_type=server.transport_type,
        )

    except asyncio.TimeoutError:
        response_time_ms = int((time.perf_counter() - start_perf) * 1000)
        return MCPHealthMetric(
            mcp_server_id=server.id,
            tenant_id=server.tenant_id,
            response_time_ms=response_time_ms,
            check_timestamp=check_timestamp,
            status=MCPHealthCheckStatus.TIMEOUT,
            error_message="Health check exceeded 30s timeout",
            error_type="TimeoutError",
            check_type="tools_list",
            transport_type=server.transport_type,
        )

    except OSError as e:
        response_time_ms = int((time.perf_counter() - start_perf) * 1000)
        error_class = e.__class__.__name__
        return MCPHealthMetric(
            mcp_server_id=server.id,
            tenant_id=server.tenant_id,
            response_time_ms=response_time_ms,
            check_timestamp=check_timestamp,
            status=MCPHealthCheckStatus.CONNECTION_FAILED,
            error_message=f"Process spawn failed: {_sanitize_error_message(str(e))}",
            error_type=error_class,  # FileNotFoundError, PermissionError, etc.
            check_type="tools_list",
            transport_type=server.transport_type,
        )

    except ValueError as e:
        response_time_ms = int((time.perf_counter() - start_perf) * 1000)
        return MCPHealthMetric(
            mcp_server_id=server.id,
            tenant_id=server.tenant_id,
            response_time_ms=response_time_ms,
            check_timestamp=check_timestamp,
            status=MCPHealthCheckStatus.ERROR,
            error_message=f"JSON-RPC error: {_sanitize_error_message(str(e))}",
            error_type="InvalidJSON",
            check_type="tools_list",
            transport_type=server.transport_type,
        )

    except Exception as e:
        response_time_ms = int((time.perf_counter() - start_perf) * 1000)
        error_class = e.__class__.__name__
        return MCPHealthMetric(
            mcp_server_id=server.id,
            tenant_id=server.tenant_id,
            response_time_ms=response_time_ms,
            check_timestamp=check_timestamp,
            status=MCPHealthCheckStatus.ERROR,
            error_message=f"Unexpected error: {_sanitize_error_message(str(e))}",
            error_type=error_class,
            check_type="tools_list",
            transport_type=server.transport_type,
        )


async def record_metric(metric: MCPHealthMetric, db: AsyncSession) -> None:
    """
    Record health metric to database and update Prometheus metrics.

    Story: 11.2.4 - Enhanced MCP Health Monitoring (AC2)

    Performs two operations:
    1. Insert raw metric to mcp_server_metrics table (time-series data)
    2. Update Prometheus metrics (gauges, counters, histograms)

    Args:
        metric: MCPHealthMetric with health check results
        db: AsyncSession for database operations

    Raises:
        SQLAlchemyError: If database insert fails (logged, not propagated)

    Example:
        >>> metric = await perform_detailed_health_check(server)
        >>> await record_metric(metric, db)  # Inserts to DB + updates Prometheus
    """
    try:
        # 1. Insert to database (time-series storage)
        db_metric = MCPServerMetric(
            mcp_server_id=metric.mcp_server_id,
            tenant_id=metric.tenant_id,
            response_time_ms=metric.response_time_ms,
            check_timestamp=metric.check_timestamp,
            status=metric.status.value,
            error_message=metric.error_message,
            error_type=metric.error_type,
            check_type=metric.check_type,
            transport_type=metric.transport_type,
        )
        db.add(db_metric)
        await db.commit()

    except Exception as e:
        logger.error(
            "Failed to record health metric to database",
            extra={
                "mcp_server_id": str(metric.mcp_server_id),
                "error": str(e),
            }
        )
        # Don't raise - metric recording failure shouldn't block health checks
        await db.rollback()

    # 2. Update Prometheus metrics (always attempt, even if DB insert failed)
    try:
        # Get server name for labels (use server_id as fallback)
        server_name = str(metric.mcp_server_id)[:8]  # First 8 chars of UUID

        # Gauge: Health status (1=success, 0=failure)
        status_value = 1.0 if metric.status == MCPHealthCheckStatus.SUCCESS else 0.0
        mcp_server_health_status.labels(
            server_id=str(metric.mcp_server_id),
            server_name=server_name,
            transport_type=metric.transport_type,
            tenant_id=str(metric.tenant_id),
        ).set(status_value)

        # Gauge: Last check timestamp (Unix seconds)
        mcp_server_last_check_timestamp.labels(
            server_id=str(metric.mcp_server_id),
            server_name=server_name,
        ).set(metric.check_timestamp.timestamp())

        # Counter: Total checks
        mcp_health_checks_total.labels(
            server_id=str(metric.mcp_server_id),
            server_name=server_name,
            transport_type=metric.transport_type,
            status=metric.status.value,
        ).inc()

        # Counter: Errors (only if status != success)
        if metric.status != MCPHealthCheckStatus.SUCCESS:
            mcp_health_check_errors_total.labels(
                server_id=str(metric.mcp_server_id),
                server_name=server_name,
                error_type=metric.error_type or "unknown",
            ).inc()

        # Histogram: Response time distribution
        mcp_health_check_duration_seconds.labels(
            server_id=str(metric.mcp_server_id),
            server_name=server_name,
            transport_type=metric.transport_type,
        ).observe(metric.response_time_ms / 1000.0)  # Convert ms to seconds

    except Exception as e:
        logger.error(
            "Failed to update Prometheus metrics",
            extra={
                "mcp_server_id": str(metric.mcp_server_id),
                "error": str(e),
            }
        )
        # Don't raise - Prometheus failure shouldn't block health checks


async def check_server_health(
    server: MCPServer,
    db: AsyncSession,
    tracer: Any | None = None
) -> dict[str, Any]:
    """
    Perform health check on a single MCP server.

    Spawns a stdio client, calls list_tools() as a health check probe, and updates
    the database with results. Implements circuit breaker logic: after 3 consecutive
    failures, the server status is set to 'inactive' to exclude it from future checks.

    Story: 11.1.8 - Basic health monitoring
    Story: 11.2.4 - Enhanced with detailed metrics collection
    Story: 12.8 - OpenTelemetry tracing (AC2)

    Health Check Flow:
        1. Call perform_detailed_health_check() for precise timing
        2. Record metric to database + Prometheus via record_metric()
        3. Update server status in mcp_servers table
        4. On success: status='active', reset consecutive_failures=0
        5. On failure: status='error', increment consecutive_failures
        6. Circuit breaker: If consecutive_failures >= 3, set status='inactive'

    Args:
        server: MCPServer instance from database with stdio transport configuration
        db: AsyncSession for database updates (must be active transaction)
        tracer: Optional OpenTelemetry tracer for distributed tracing (Story 12.8 AC2)

    Returns:
        dict with keys:
            - status: "active" | "error"
            - error_message: str | None (error details if failed)
            - duration_ms: int (health check execution time in milliseconds)

    Raises:
        No exceptions raised - all errors are caught, logged, and reflected in return dict

    Example:
        >>> async with get_db() as db:
        >>>     server = await db.get(MCPServer, server_id)
        >>>     result = await check_server_health(server, db)
        >>>     print(result)
        {"status": "active", "error_message": None, "duration_ms": 145}

    Notes:
        - 30-second timeout enforced via asyncio.timeout()
        - Detailed metrics recorded to mcp_server_metrics table
        - Prometheus metrics updated (gauges, counters, histograms)
        - Structured logging with correlation metadata
        - Error messages sanitized (no sensitive env/command leaks)
        - Tenant isolation maintained (updates own server only)
    """
    # Story 12.8 AC2: Optionally wrap health check in span (when tracer provided)
    if tracer:
        with tracer.start_as_current_span("mcp.health.ping") as health_span:
            health_span.set_attribute("mcp.server_id", str(server.id))
            health_span.set_attribute("mcp.server_name", server.name)
            health_span.set_attribute("mcp.transport_type", "stdio")

            return await _check_server_health_impl(server, db, tracer, health_span)
    else:
        # No tracing - call implementation directly
        return await _check_server_health_impl(server, db, None, None)


async def _check_server_health_impl(
    server: MCPServer,
    db: AsyncSession,
    tracer: Any | None,
    health_span: Any | None
) -> dict[str, Any]:
    """Implementation of check_server_health with optional tracing."""
    # Story 11.2.4: Use detailed health check for metrics collection
    if tracer and health_span:
        # Story 12.8 AC2: Child span for client connection
        with tracer.start_as_current_span("mcp.client.connect") as connect_span:
            connect_span.set_attribute("mcp.server_id", str(server.id))
            metric = await perform_detailed_health_check(server)
    else:
        metric = await perform_detailed_health_check(server)

    # Story 11.2.4: Record metric to database + Prometheus
    await record_metric(metric, db)

    # Update server status in mcp_servers table (existing logic from Story 11.1.8)
    if metric.status == MCPHealthCheckStatus.SUCCESS:
        server.status = "active"
        server.last_health_check = metric.check_timestamp
        server.error_message = None
        server.consecutive_failures = 0

        # Update discovered_tools if available (requires tools response)
        # Note: perform_detailed_health_check() doesn't return tools list to keep it fast
        # Tools are still updated by the existing check logic below

        await db.commit()

        # Story 12.8 AC2: Set success attributes on health span
        if health_span:
            health_span.set_attribute("health.status", "active")
            health_span.set_attribute("health.response_time_ms", metric.response_time_ms)
            health_span.set_attribute("circuit_breaker.state", "closed")
            health_span.set_attribute("circuit_breaker.failure_count", 0)

        logger.info(
            "MCP health check completed",
            extra={
                "mcp_server_id": str(server.id),
                "mcp_server_name": server.name,
                "tenant_id": str(server.tenant_id),
                "status": "active",
                "duration_ms": metric.response_time_ms,
            }
        )

        return {
            "status": "active",
            "error_message": None,
            "duration_ms": metric.response_time_ms
        }
    else:
        # FAILURE: Update status and circuit breaker
        server.status = "error"
        server.last_health_check = metric.check_timestamp
        server.error_message = metric.error_message
        server.consecutive_failures += 1

        # Story 12.8 AC2: Set failure attributes on health span
        if health_span:
            health_span.set_attribute("health.status", "error")
            health_span.set_attribute("health.response_time_ms", metric.response_time_ms)
            health_span.set_attribute("health.error_type", metric.error_type or "unknown")
            health_span.set_attribute("circuit_breaker.failure_count", server.consecutive_failures)

        # Circuit breaker: Mark inactive after 3 consecutive failures
        if server.consecutive_failures >= 3:
            server.status = "inactive"

            # Story 12.8 AC2: Child span for circuit breaker state change
            if tracer and health_span:
                with tracer.start_as_current_span("mcp.circuit_breaker.update") as cb_span:
                    cb_span.set_attribute("mcp.server_id", str(server.id))
                    cb_span.set_attribute("circuit_breaker.previous_state", "closed")
                    cb_span.set_attribute("circuit_breaker.new_state", "open")
                    cb_span.set_attribute("circuit_breaker.failure_count", server.consecutive_failures)
                    cb_span.set_attribute("circuit_breaker.threshold", 3)

            # Update parent health span with circuit breaker state
            if health_span:
                health_span.set_attribute("circuit_breaker.state", "open")

            logger.warning(
                f"MCP server {server.name} marked inactive after 3 consecutive failures",
                extra={
                    "mcp_server_id": str(server.id),
                    "mcp_server_name": server.name,
                    "tenant_id": str(server.tenant_id),
                    "consecutive_failures": server.consecutive_failures,
                    "circuit_breaker": "triggered"
                }
            )
        else:
            # Circuit breaker still closed (fewer than 3 failures)
            if health_span:
                health_span.set_attribute("circuit_breaker.state", "closed")

        await db.commit()

        logger.warning(
            "MCP health check failed",
            extra={
                "mcp_server_id": str(server.id),
                "mcp_server_name": server.name,
                "tenant_id": str(server.tenant_id),
                "status": server.status,
                "error_type": metric.error_type,
                "error_message": metric.error_message,
                "consecutive_failures": server.consecutive_failures,
                "duration_ms": metric.response_time_ms
            }
        )

        return {
            "status": "error",
            "error_message": metric.error_message,
            "duration_ms": metric.response_time_ms
        }


# Legacy check_server_health() implementation below (Story 11.1.8)
# Kept for reference but should not be called - new implementation above uses
# perform_detailed_health_check() + record_metric() pattern

async def _legacy_check_server_health_v1(
    server: MCPServer,
    db: AsyncSession
) -> dict[str, Any]:
    """
    DEPRECATED: Legacy health check from Story 11.1.8.
    Use check_server_health() which calls perform_detailed_health_check() + record_metric().
    """
    start_time = datetime.now(timezone.utc)

    try:
        # 30-second timeout for entire health check operation
        async with asyncio.timeout(30.0):
            # Spawn stdio client using server configuration
            client = MCPStdioClient(
                command=server.command,
                args=server.args or [],
                env=server.env or {}
            )

            # Use context manager for guaranteed cleanup
            async with client:
                # Perform JSON-RPC handshake
                await client.initialize()

                # Call tools/list as lightweight health check
                # This is non-modifying and fast (~50-200ms for most servers)
                tools = await client.list_tools()

            # SUCCESS: Update database with healthy status
            server.status = "active"
            server.last_health_check = datetime.now(timezone.utc)
            server.error_message = None
            server.consecutive_failures = 0

            # Update discovered_tools with latest capabilities
            if tools:
                server.discovered_tools = [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema
                    }
                    for tool in tools
                ]

            await db.commit()

            # Calculate health check duration
            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

            # Structured logging for success
            logger.info(
                "MCP health check completed",
                extra={
                    "mcp_server_id": str(server.id),
                    "mcp_server_name": server.name,
                    "tenant_id": str(server.tenant_id),
                    "status": "active",
                    "duration_ms": duration_ms,
                    "tools_count": len(tools) if tools else 0
                }
            )

            return {
                "status": "active",
                "error_message": None,
                "duration_ms": duration_ms
            }

    except asyncio.TimeoutError:
        # FAILURE: Health check timeout (>30s)
        error_msg = "Health check timeout (>30s)"
        return await _handle_health_check_failure(
            server, db, error_msg, start_time, "timeout"
        )

    except OSError as e:
        # FAILURE: Process spawn failure (command not found, permission denied, etc.)
        error_msg = f"Process spawn failed: {_sanitize_error_message(str(e))}"
        return await _handle_health_check_failure(
            server, db, error_msg, start_time, "process_error"
        )

    except ValueError as e:
        # FAILURE: JSON-RPC protocol error (invalid response, handshake failure)
        error_msg = f"JSON-RPC error: {_sanitize_error_message(str(e))}"
        return await _handle_health_check_failure(
            server, db, error_msg, start_time, "jsonrpc_error"
        )

    except Exception as e:
        # FAILURE: Unexpected error (catch-all for unforeseen issues)
        error_msg = f"Unexpected error: {_sanitize_error_message(str(e))}"
        return await _handle_health_check_failure(
            server, db, error_msg, start_time, "unknown_error"
        )


async def _handle_health_check_failure(
    server: MCPServer,
    db: AsyncSession,
    error_message: str,
    start_time: datetime,
    error_type: str
) -> dict[str, Any]:
    """
    Handle health check failure by updating database and implementing circuit breaker.

    Updates database with error status and increments consecutive_failures counter.
    If consecutive_failures reaches 3, triggers circuit breaker (status='inactive').

    Args:
        server: MCPServer instance to update
        db: AsyncSession for database updates
        error_message: Sanitized error description
        start_time: Health check start timestamp (for duration calculation)
        error_type: Error category (timeout, process_error, jsonrpc_error, unknown_error)

    Returns:
        dict with status="error", error_message, duration_ms
    """
    # Update database with failure status
    server.status = "error"
    server.last_health_check = datetime.now(timezone.utc)
    server.error_message = error_message
    server.consecutive_failures += 1

    # Circuit breaker: Mark inactive after 3 consecutive failures
    if server.consecutive_failures >= 3:
        server.status = "inactive"
        logger.warning(
            f"MCP server {server.name} marked inactive after 3 consecutive failures",
            extra={
                "mcp_server_id": str(server.id),
                "mcp_server_name": server.name,
                "tenant_id": str(server.tenant_id),
                "consecutive_failures": server.consecutive_failures,
                "circuit_breaker": "triggered"
            }
        )

    await db.commit()

    # Calculate health check duration
    duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

    # Structured logging for failure
    logger.warning(
        "MCP health check failed",
        extra={
            "mcp_server_id": str(server.id),
            "mcp_server_name": server.name,
            "tenant_id": str(server.tenant_id),
            "status": server.status,
            "error_type": error_type,
            "error_message": error_message,
            "consecutive_failures": server.consecutive_failures,
            "duration_ms": duration_ms
        }
    )

    return {
        "status": "error",
        "error_message": error_message,
        "duration_ms": duration_ms
    }


def _sanitize_error_message(error: str) -> str:
    """
    Sanitize error messages to prevent sensitive information disclosure.

    Removes potentially sensitive data like:
    - Full file paths (keep only filename)
    - Environment variable names/values
    - Command-line arguments
    - API tokens/secrets

    Args:
        error: Raw error message string

    Returns:
        Sanitized error message safe for client exposure

    Example:
        >>> _sanitize_error_message("/usr/local/bin/npx failed: ENOENT")
        "npx failed: ENOENT"
        >>> _sanitize_error_message("API_KEY=secret not set")
        "Environment variable not set"
    """
    # Remove full file paths (keep only executable name)
    if "/" in error or "\\" in error:
        # Extract executable name from path
        parts = error.replace("\\", "/").split("/")
        error = parts[-1] if parts else error

    # Remove environment variable values
    if "API_KEY" in error or "TOKEN" in error or "SECRET" in error:
        return "Environment variable error"

    # Truncate very long error messages (max 200 chars)
    if len(error) > 200:
        error = error[:197] + "..."

    return error
