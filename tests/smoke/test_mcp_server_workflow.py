"""
Smoke Test: MCP Server Workflow - Story 12.6

Critical Path: Register MCP server → Discover tools → Assign to agent

Execution Time Target: <30 seconds
"""

import pytest
from httpx import AsyncClient

from src.database.models import TenantConfig, MCPServer, Agent


@pytest.mark.smoke
@pytest.mark.asyncio
@pytest.mark.skip(reason="MCP server workflow test - implement in follow-up if needed")
async def test_mcp_server_workflow(
    async_test_client: AsyncClient,
    smoke_test_tenant: TenantConfig,
    smoke_test_mcp_server: MCPServer,
    smoke_test_agent: Agent
):
    """
    Smoke test: MCP server registration and tool discovery workflow.

    TODO: Implement in Story 12.6A or Story 12.7
    - Reference implementation: test_agent_creation_workflow.py (6 assertions pattern)
    - Use smoke_test_mcp_server fixture (already configured with stdio transport)
    - Test MCP server health check endpoint: GET /api/mcp-servers/{id}/health
    - Test tool discovery: POST /api/mcp-servers/{id}/discover-tools
    - Verify tools merged into unified tool list

    Critical path:
    1. Register MCP server via POST /api/mcp-servers
    2. Trigger tool discovery via POST /api/mcp-servers/{id}/discover
    3. Verify MCP tools merged into unified tool list
    4. Assign MCP tool to agent
    5. Verify tool assignment successful

    Assertions:
    - MCP server registered
    - Tools discovered
    - Tools assignable to agents
    - End-to-end MCP integration works

    Note: Skipped for Story 12.6 delivery - implement in follow-up if needed
    """
    pass
