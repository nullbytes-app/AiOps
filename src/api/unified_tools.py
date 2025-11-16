"""
Unified Tools API - GET endpoint for unified tool discovery.

Provides a single API endpoint to discover tools from multiple sources
(OpenAPI tools and MCP servers) in a consistent format.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_tenant_db, get_tenant_id
from src.schemas.unified_tool import UnifiedTool
from src.services.unified_tool_service import UnifiedToolService

router = APIRouter(prefix="/api/v1", tags=["unified-tools"])
logger = logging.getLogger(__name__)


@router.get("/unified-tools/", response_model=list[UnifiedTool])
async def list_unified_tools(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
) -> list[UnifiedTool]:
    """
    List all available tools for a tenant from all sources.

    Queries both OpenAPI tools and MCP servers, transforms them to unified format,
    handles deduplication (OpenAPI tools take precedence), and returns cached
    results when available.

    Args:
        tenant_id: Tenant ID from X-Tenant-ID header (extracted by dependency)
        db: Database session with tenant context (provided by dependency)

    Returns:
        List of UnifiedTool instances from all sources (deduplicated)

    Performance:
        - First call: <500ms (p95) - database queries
        - Cached calls: <10ms (p95) - in-memory cache hit
        - Cache TTL: 60 seconds

    Example:
        GET /api/v1/unified-tools/
        Headers: X-Tenant-ID: test-tenant

        Response:
        [
            {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "get_weather",
                "description": "Get current weather information",
                "source_type": "openapi",
                "mcp_server_id": null,
                "mcp_primitive_type": null,
                "mcp_server_name": null,
                "input_schema": {...},
                "enabled": true
            }
        ]
    """
    logger.info(f"Fetching unified tools for tenant: {tenant_id}")

    # Initialize service and fetch tools
    service = UnifiedToolService(db)
    tools = await service.list_tools(tenant_id)

    logger.info(f"Returning {len(tools)} unified tools for tenant {tenant_id}")
    return tools
