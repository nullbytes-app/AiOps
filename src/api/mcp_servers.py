"""
MCP Server Management API.

REST API endpoints for creating, reading, updating, and deleting MCP servers.
All endpoints enforce tenant isolation via tenant_id filtering.
Automatic capability discovery runs on server creation.

Story 11.1.4: MCP Server Management API - FastAPI router implementation.
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_tenant_db, get_tenant_id
from src.database.models import MCPServerStatus, TransportType
from src.schemas.mcp_server import (
    MCPServerCreate,
    MCPServerResponse,
    MCPServerUpdate,
)
from src.services.mcp_server_service import MCPServerService
from src.utils.logger import logger

router = APIRouter(prefix="/api/v1/mcp-servers", tags=["MCP Servers"])


@router.post(
    "/",
    response_model=MCPServerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create MCP Server",
    description="Creates a new MCP server and triggers automatic capability discovery. "
    "Discovery runs initialize → list_tools → list_resources → list_prompts. "
    "Returns server with status='active' if discovery succeeds, or status='error' if it fails.",
    responses={
        201: {"description": "MCP server created successfully with discovered capabilities"},
        422: {"description": "Validation error (missing required fields)"},
        409: {"description": "Server name already exists for this tenant"},
    },
)
async def create_mcp_server(
    server_data: Annotated[
        MCPServerCreate,
        Body(
            openapi_examples={
                "stdio_server": {
                    "summary": "stdio Transport Server",
                    "description": "MCP server using stdio transport (subprocess)",
                    "value": {
                        "name": "everything-server",
                        "description": "Example MCP server with all capabilities",
                        "transport_type": "stdio",
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-everything"],
                        "env": {"LOG_LEVEL": "info"},
                    },
                },
                "http_sse_server": {
                    "summary": "HTTP/SSE Transport Server",
                    "description": "MCP server using HTTP with Server-Sent Events",
                    "value": {
                        "name": "remote-server",
                        "description": "Remote MCP server via HTTP",
                        "transport_type": "http_sse",
                        "url": "https://example.com/mcp",
                        "headers": {"Authorization": "Bearer token123"},
                    },
                },
            }
        ),
    ],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
) -> MCPServerResponse:
    """
    Create new MCP server with automatic capability discovery.

    Args:
        server_data: MCP server configuration (validated by Pydantic).
        tenant_uuid: Tenant UUID (resolved from tenant_id VARCHAR).
        db: Async database session.

    Returns:
        Created MCP server with discovered capabilities.

    Raises:
        HTTPException 409: If server name already exists for tenant.
        HTTPException 422: If validation fails (transport-specific fields).
    """
    service = MCPServerService(db)

    try:
        # Create server with automatic discovery
        server = await service.create_server(server_data, tenant_id)

        logger.info(
            f"Created MCP server {server.id} for tenant {tenant_id} with status {server.status}"
        )
        return MCPServerResponse.model_validate(server)

    except ValueError as e:
        # Tenant ID not a valid UUID
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tenant_id format: {str(e)}",
        )
    except Exception as e:
        # Check for duplicate name (IntegrityError)
        if "unique constraint" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Server name '{server_data.name}' already exists for this tenant",
            )
        logger.exception("Error creating MCP server")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create MCP server",
        )


@router.get(
    "/",
    response_model=list[MCPServerResponse],
    status_code=status.HTTP_200_OK,
    summary="List MCP Servers",
    description="Returns paginated list of MCP servers for authenticated tenant. "
    "Supports filtering by status and transport_type. "
    "Only servers belonging to the authenticated tenant are returned.",
    responses={
        200: {"description": "List of MCP servers (may be empty)"},
    },
)
async def list_mcp_servers(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    skip: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
    limit: Annotated[int, Query(ge=1, le=1000, description="Page size (max 1000)")] = 100,
    status_filter: Annotated[
        MCPServerStatus | None,
        Query(alias="status", description="Filter by status (active/inactive/error)"),
    ] = None,
    transport_type: Annotated[
        TransportType | None,
        Query(description="Filter by transport type (stdio/http_sse)"),
    ] = None,
) -> list[MCPServerResponse]:
    """
    List MCP servers with pagination and filtering.

    Args:
        tenant_uuid: Tenant UUID (resolved from tenant_id VARCHAR).
        db: Async database session.
        skip: Number of records to skip (default 0).
        limit: Maximum records to return (default 100, max 1000).
        status_filter: Optional status filter.
        transport_type: Optional transport type filter.

    Returns:
        List of MCP servers (may be empty).
    """
    service = MCPServerService(db)

    try:
        servers, total = await service.list_servers(
            tenant_id,
            skip=skip,
            limit=limit,
            status=status_filter,
            transport_type=transport_type,
        )

        logger.info(f"Listed {len(servers)} MCP servers for tenant {tenant_id} (total: {total})")
        return [MCPServerResponse.model_validate(s) for s in servers]

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list MCP servers: {str(e)}",
        )


@router.get(
    "/{server_id}",
    response_model=MCPServerResponse,
    status_code=status.HTTP_200_OK,
    summary="Get MCP Server Details",
    description="Returns complete MCP server details including full discovered capabilities arrays. "
    "Returns 404 if server doesn't exist or belongs to different tenant.",
    responses={
        200: {"description": "MCP server details with complete discovered capabilities"},
        404: {"description": "Server not found or not accessible by authenticated tenant"},
    },
)
async def get_mcp_server(
    server_id: UUID,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
) -> MCPServerResponse:
    """
    Get MCP server details by ID.

    Args:
        server_id: Server UUID.
        tenant_uuid: Tenant UUID (resolved from tenant_id VARCHAR).
        db: Async database session.

    Returns:
        Complete MCP server details.

    Raises:
        HTTPException 404: If server not found or not accessible.
    """
    service = MCPServerService(db)

    try:
        server = await service.get_server_by_id(server_id, tenant_id)

        if not server:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")

        return MCPServerResponse.model_validate(server)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get MCP server: {str(e)}",
        )


@router.patch(
    "/{server_id}",
    response_model=MCPServerResponse,
    status_code=status.HTTP_200_OK,
    summary="Update MCP Server",
    description="Updates MCP server (partial update supported). "
    "Allows updating: name, description, command, args, env, url, headers. "
    "Does NOT allow updating: tenant_id, discovered_*, created_at, status.",
    responses={
        200: {"description": "MCP server updated successfully"},
        404: {"description": "Server not found or not accessible by authenticated tenant"},
        422: {"description": "Validation error (transport-specific constraints)"},
    },
)
async def update_mcp_server(
    server_id: UUID,
    updates: MCPServerUpdate,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
) -> MCPServerResponse:
    """
    Update MCP server (partial update).

    Args:
        server_id: Server UUID.
        updates: Partial update data (only provided fields updated).
        tenant_uuid: Tenant UUID from authenticated context.
        db: Async database session.

    Returns:
        Updated MCP server details.

    Raises:
        HTTPException 404: If server not found or not accessible.
        HTTPException 422: If validation fails.
    """
    service = MCPServerService(db)

    try:
        server = await service.update_server(server_id, updates, tenant_id)

        if not server:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")

        logger.info(f"Updated MCP server {server_id} for tenant {tenant_id}")
        return MCPServerResponse.model_validate(server)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid update data: {str(e)}",
        )


@router.delete(
    "/{server_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete MCP Server",
    description="Deletes MCP server (hard delete). "
    "Returns 404 if server doesn't exist or belongs to different tenant.",
    responses={
        204: {"description": "MCP server deleted successfully"},
        404: {"description": "Server not found or not accessible by authenticated tenant"},
    },
)
async def delete_mcp_server(
    server_id: UUID,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
) -> None:
    """
    Delete MCP server.

    Args:
        server_id: Server UUID.
        tenant_uuid: Tenant UUID from authenticated context.
        db: Async database session.

    Raises:
        HTTPException 404: If server not found or not accessible.
    """
    service = MCPServerService(db)

    try:
        deleted = await service.delete_server(server_id, tenant_id)

        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")

        logger.info(f"Deleted MCP server {server_id} for tenant {tenant_id}")

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid delete request: {str(e)}",
        )


@router.post(
    "/{server_id}/discover",
    response_model=MCPServerResponse,
    status_code=status.HTTP_200_OK,
    summary="Force Rediscovery",
    description="Triggers manual capability rediscovery for MCP server. "
    "Runs complete discovery workflow: initialize → list_tools → list_resources → list_prompts. "
    "Updates discovered_tools, discovered_resources, discovered_prompts fields. "
    "Returns updated server with status='active' or 'error'.",
    responses={
        200: {"description": "Discovery completed, server updated with results"},
        404: {"description": "Server not found or not accessible by authenticated tenant"},
    },
)
async def rediscover_mcp_server(
    server_id: UUID,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
) -> MCPServerResponse:
    """
    Force rediscovery of MCP server capabilities.

    Args:
        server_id: Server UUID.
        tenant_uuid: Tenant UUID from authenticated context.
        db: Async database session.

    Returns:
        Updated server with refreshed capabilities.

    Raises:
        HTTPException 404: If server not found or not accessible.
    """
    service = MCPServerService(db)

    try:
        # Verify server exists and belongs to tenant
        server = await service.get_server_by_id(server_id, tenant_id)
        if not server:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")

        # Trigger discovery
        await service.discover_capabilities(server_id)

        # Refresh server from database
        await db.refresh(server)

        logger.info(f"Rediscovered capabilities for server {server_id}, status: {server.status}")
        return MCPServerResponse.model_validate(server)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid rediscovery request: {str(e)}",
        )


@router.get(
    "/{server_id}/health",
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Performs lightweight health check on MCP server (initialize only, no full discovery). "
    "Returns health status with response_time_ms. "
    "Timeout: 10 seconds (shorter than full discovery).",
    responses={
        200: {"description": "Health check completed (check status field for result)"},
        404: {"description": "Server not found or not accessible by authenticated tenant"},
    },
)
async def check_mcp_server_health(
    server_id: UUID,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
) -> dict[str, Any]:
    """
    Check MCP server health.

    Args:
        server_id: Server UUID.
        tenant_uuid: Tenant UUID from authenticated context.
        db: Async database session.

    Returns:
        Health status dict with response_time_ms.

    Raises:
        HTTPException 404: If server not found or not accessible.
    """
    service = MCPServerService(db)

    try:
        health_status = await service.check_health(server_id, tenant_id)

        if health_status is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")

        logger.info(
            f"Health check for server {server_id}: {health_status['status']} ({health_status['response_time_ms']}ms)"
        )
        return health_status

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tenant_id format: {str(e)}",
        )


# ============================================================================
# Manual Health Check Endpoint (Story 11.1.8)
# ============================================================================


@router.post(
    "/{server_id}/health-check",
    summary="Perform Manual Health Check",
    description="Immediately performs a health check on the specified MCP server (bypasses 30s interval). "
    "Updates database with results (status, last_health_check, consecutive_failures, error_message). "
    "Enforces tenant isolation - returns 403 if server belongs to different tenant. "
    "Story 11.1.8: Basic MCP Server Health Monitoring",
    responses={
        200: {"description": "Health check completed successfully"},
        404: {"description": "Server not found"},
        403: {"description": "Server belongs to different tenant"},
    },
)
async def manual_health_check(
    server_id: UUID,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
) -> dict[str, Any]:
    """
    Perform manual health check on MCP server (Story 11.1.8).

    Immediately executes health check on the specified server, bypassing the
    30-second Celery Beat schedule. Updates database with results and returns
    current health status.

    Health Check Flow:
        1. Query database for MCP server with tenant isolation check
        2. Validate server belongs to authenticated tenant (403 if mismatch)
        3. Call check_server_health() from mcp_health_monitor service
        4. Update database: status, last_health_check, consecutive_failures, error_message
        5. Return health status to client

    Args:
        server_id: UUID of MCP server to health check
        tenant_uuid: Authenticated tenant UUID (resolved from tenant_id)
        db: Async database session (tenant-scoped)

    Returns:
        dict with keys:
            - status: "active" | "error" | "inactive"
            - last_health_check: ISO 8601 timestamp
            - error_message: str | None (error details if failed)
            - consecutive_failures: int (circuit breaker counter)

    Raises:
        HTTPException 404: If server not found
        HTTPException 403: If server belongs to different tenant

    Example:
        POST /api/v1/mcp-servers/{id}/health-check

        Response 200:
        {
            "status": "active",
            "last_health_check": "2025-11-10T14:32:15.123Z",
            "error_message": null,
            "consecutive_failures": 0
        }

        Response 200 (failure):
        {
            "status": "error",
            "last_health_check": "2025-11-10T14:32:15.123Z",
            "error_message": "Health check timeout (>30s)",
            "consecutive_failures": 2
        }
    """
    from src.services.mcp_health_monitor import check_server_health
    from src.database.models import MCPServer
    from sqlalchemy import select

    try:
        # Query server with tenant isolation check
        stmt = select(MCPServer).where(
            MCPServer.id == server_id, MCPServer.tenant_id == tenant_id
        )
        result = await db.execute(stmt)
        server = result.scalar_one_or_none()

        # 404 if server not found
        if server is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Server {server_id} not found or not accessible",
            )

        # Perform health check immediately (bypasses 30s interval)
        logger.info(
            f"Manual health check triggered for server {server.name}",
            extra={
                "mcp_server_id": str(server.id),
                "mcp_server_name": server.name,
                "tenant_id": tenant_id,
            },
        )

        await check_server_health(server, db)

        # Refresh server object to get updated fields
        await db.refresh(server)

        # Return updated health status
        return {
            "status": server.status,
            "last_health_check": (
                server.last_health_check.isoformat() if server.last_health_check else None
            ),
            "error_message": server.error_message,
            "consecutive_failures": server.consecutive_failures,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tenant_id format: {str(e)}",
        )


# ============================================================================
# Health Metrics Endpoint (Story 11.2.4)
# ============================================================================


@router.get(
    "/{server_id}/metrics",
    response_model=Any,  # Using Any to avoid import complexity
    status_code=status.HTTP_200_OK,
    summary="Get MCP Server Health Metrics",
    description="Returns aggregated health metrics for MCP server over specified time period. "
    "Includes success/error rates, response time percentiles (P50/P95/P99), "
    "error distribution by type, uptime percentage, and 24h performance trend. "
    "Calculated from mcp_server_metrics time-series data with 7-day retention. "
    "Story 11.2.4: Enhanced MCP Health Monitoring (AC4)",
    responses={
        200: {
            "description": "Aggregated health metrics",
            "content": {
                "application/json": {
                    "example": {
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
                                "InvalidJSON": 10,
                            },
                            "uptime_percentage": 98.5,
                            "last_24h_trend": "stable",
                        },
                    }
                }
            },
        },
        404: {"description": "Server not found or not accessible by authenticated tenant"},
        400: {"description": "Invalid query parameters"},
    },
)
async def get_mcp_server_metrics(
    server_id: UUID,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    period_hours: Annotated[
        int,
        Query(
            ge=1,
            le=168,
            description="Time period in hours to analyze (default 24, max 168 for 7 days)",
        ),
    ] = 24,
) -> dict[str, Any]:
    """
    Get aggregated health metrics for MCP server (Story 11.2.4).

    Aggregates raw health check metrics from mcp_server_metrics table over
    the specified time period. Calculates success/error rates, response time
    percentiles using PostgreSQL PERCENTILE_CONT(), error distribution,
    and performance trend analysis.

    Metrics include:
        - Total checks performed in period
        - Success rate (0.0 to 1.0)
        - Error rate (0.0 to 1.0)
        - Average response time (milliseconds)
        - P50/P95/P99 response time percentiles
        - Maximum response time observed
        - Error count breakdown by error_type
        - Uptime percentage (0.0 to 100.0)
        - Performance trend: 'improving'/'stable'/'degrading'

    Trend Calculation:
        Compares last 24h vs previous 24h average response times:
        - 'improving': Response time decreased > 10%
        - 'degrading': Response time increased > 10%
        - 'stable': Change within ±10%

    Args:
        server_id: UUID of MCP server to retrieve metrics for
        tenant_uuid: Authenticated tenant UUID (resolved from tenant_id)
        db: Async database session (tenant-scoped)
        period_hours: Time period to analyze (1-168 hours, default 24)

    Returns:
        MCPServerMetrics dict with aggregated data

    Raises:
        HTTPException 404: If server not found or belongs to different tenant
        HTTPException 400: If period_hours out of range or invalid tenant_id
        HTTPException 500: If metrics aggregation fails

    Example:
        GET /api/v1/mcp-servers/{id}/metrics?period_hours=48

        Response 200:
        {
            "server_id": "550e8400-e29b-41d4-a716-446655440000",
            "server_name": "filesystem-server",
            "period_hours": 48,
            "metrics": {
                "total_checks": 5760,
                "success_rate": 0.985,
                "error_rate": 0.015,
                "avg_response_time_ms": 125,
                "p50_response_time_ms": 95,
                "p95_response_time_ms": 280,
                "p99_response_time_ms": 450,
                "max_response_time_ms": 1200,
                "errors_by_type": {"TimeoutError": 28},
                "uptime_percentage": 98.5,
                "last_24h_trend": "stable"
            }
        }
    """
    from src.services.mcp_metrics_aggregator import get_server_metrics
    from src.database.models import MCPServer
    from sqlalchemy import select

    try:
        # Verify server exists and belongs to tenant (tenant isolation)
        stmt = select(MCPServer).where(
            MCPServer.id == server_id, MCPServer.tenant_id == tenant_id
        )
        result = await db.execute(stmt)
        server = result.scalar_one_or_none()

        if server is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Server {server_id} not found or not accessible",
            )

        # Validate period_hours (should be caught by Query validation, but double-check)
        if not 1 <= period_hours <= 168:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="period_hours must be between 1 and 168 (7 days)",
            )

        logger.info(
            f"Retrieving health metrics for server {server.name} (period: {period_hours}h)",
            extra={
                "mcp_server_id": str(server.id),
                "mcp_server_name": server.name,
                "tenant_id": tenant_id,
                "period_hours": period_hours,
            },
        )

        # Get aggregated metrics from mcp_metrics_aggregator service
        metrics = await get_server_metrics(server_id, period_hours, db)

        # Return as dict (Pydantic model will be serialized by FastAPI)
        return metrics.model_dump()

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: {str(e)}",
        )
    except HTTPException:
        # Re-raise HTTP exceptions (404, 400)
        raise
    except Exception as e:
        logger.error(
            f"Failed to retrieve metrics for server {server_id}: {str(e)}",
            extra={"mcp_server_id": str(server_id), "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics",
        )


# ============================================================================
# Test Connection Endpoint (Story 11.2.2)
# ============================================================================


@router.post(
    "/test-connection",
    response_model=Any,  # Using Any to avoid circular import with MCPTestConnectionResponse
    status_code=status.HTTP_200_OK,
    summary="Test MCP Server Connection",
    description="Tests MCP server configuration without saving to database. "
    "Performs full discovery workflow: initialize → list_tools → list_resources → list_prompts. "
    "Returns discovered capabilities on success (HTTP 200 with success=true), "
    "or error details on failure (HTTP 200 with success=false). "
    "Timeout: 30 seconds total. "
    "Story 11.2.2: HTTP+SSE Configuration in UI and API (AC4)",
    responses={
        200: {
            "description": "Connection test completed (check success field)",
            "content": {
                "application/json": {
                    "examples": {
                        "success": {
                            "summary": "Successful Connection",
                            "value": {
                                "success": True,
                                "server_info": {
                                    "protocol_version": "2025-03-26",
                                    "server_name": "Example MCP Server",
                                    "capabilities": ["tools", "resources", "prompts"],
                                },
                                "discovered_tools": [
                                    {
                                        "name": "read_file",
                                        "description": "Read file contents",
                                        "inputSchema": {
                                            "type": "object",
                                            "properties": {"path": {"type": "string"}},
                                            "required": ["path"],
                                        },
                                    }
                                ],
                                "discovered_resources": [
                                    {
                                        "uri": "file:///Users/ravi/config.json",
                                        "name": "Config File",
                                        "description": "Application configuration",
                                        "mimeType": "application/json",
                                    }
                                ],
                                "discovered_prompts": [],
                                "error": None,
                                "error_details": None,
                            },
                        },
                        "failure": {
                            "summary": "Connection Failed",
                            "value": {
                                "success": False,
                                "server_info": None,
                                "discovered_tools": [],
                                "discovered_resources": [],
                                "discovered_prompts": [],
                                "error": "Connection timeout",
                                "error_details": "httpx.ConnectTimeout after 10 seconds",
                            },
                        },
                    }
                }
            },
        },
        422: {"description": "Validation error (missing required fields)"},
    },
)
async def test_mcp_server_connection(
    server_config: Annotated[
        MCPServerCreate,
        Body(
            openapi_examples={
                "stdio_test": {
                    "summary": "Test stdio Server",
                    "description": "Test connection to stdio MCP server",
                    "value": {
                        "name": "Test Filesystem Server",
                        "description": "Testing filesystem server",
                        "transport_type": "stdio",
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                        "env": {"LOG_LEVEL": "info"},
                    },
                },
                "http_sse_test": {
                    "summary": "Test HTTP+SSE Server",
                    "description": "Test connection to remote HTTP+SSE MCP server",
                    "value": {
                        "name": "Test Remote Server",
                        "description": "Testing remote server",
                        "transport_type": "http_sse",
                        "url": "https://example.com/mcp",
                        "headers": {"Authorization": "Bearer test_token"},
                    },
                },
            }
        ),
    ],
) -> dict[str, Any]:
    """
    Test MCP server connection without saving to database.

    Validates server configuration by initializing client, executing handshake,
    and discovering capabilities. Does not persist server to database.

    This endpoint is used by the Admin UI "Test Connection" button to validate
    configuration before saving (AC3).

    Args:
        server_config: MCP server configuration to test (not saved to DB).

    Returns:
        dict with test results (see response schema examples).

    Note:
        - Returns HTTP 200 even on connection failure (check success field)
        - Does NOT require tenant_id (no database save)
        - Times out after 30 seconds (client timeout + safety margin)
        - Cleans up client resources properly via async context manager

    Example:
        POST /api/v1/mcp-servers/test-connection
        {
            "name": "Test Server",
            "transport_type": "http_sse",
            "url": "https://mcp.example.com",
            "headers": {"Authorization": "Bearer token"}
        }

        Response 200:
        {
            "success": true,
            "server_info": {"protocol_version": "2025-03-26", ...},
            "discovered_tools": [...],
            "discovered_resources": [...],
            "discovered_prompts": [...],
            "error": null,
            "error_details": null
        }

    Story 11.2.2: HTTP+SSE Configuration in UI and API (AC4)
    """
    service = MCPServerService()

    try:
        # Test connection (does not save to database)
        result = await service.test_connection(server_config)

        logger.info(
            f"Connection test for '{server_config.name}' "
            f"({server_config.transport_type}): "
            f"{'SUCCESS' if result['success'] else 'FAILED'}"
        )

        return result

    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(f"Unexpected error in test_connection endpoint: {e}", exc_info=True)
        return {
            "success": False,
            "server_info": None,
            "discovered_tools": [],
            "discovered_resources": [],
            "discovered_prompts": [],
            "error": "Internal server error",
            "error_details": str(e),
        }
