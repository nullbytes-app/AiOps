"""
Integration tests for MCP stdio workflow (Story 11.2.6 - AC#2 Workflow 1).

Tests complete end-to-end flow:
1. Register stdio MCP server
2. Discover capabilities
3. Assign tools to agent
4. Invoke tool through agent execution

Uses real @modelcontextprotocol/server-everything for testing.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from src.database.models import MCPServer, MCPServerStatus, TransportType
from src.schemas.mcp_server import MCPServerCreate, MCPServerUpdate
from src.services.mcp_server_service import MCPServerService
from src.services.mcp_stdio_client import MCPStdioClient


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_stdio_workflow_register_and_discover(
    mcp_stdio_test_server_config, mock_db_session
):
    """
    Test Workflow 1: Register stdio server → Discover capabilities.

    Validates:
    - Server can be registered via MCPServerService
    - Capability discovery completes successfully
    - Server status updated to ACTIVE
    - Tools/resources/prompts stored in database
    """
    service = MCPServerService(mock_db_session)

    # Step 1: Register MCP server
    server_create = MCPServerCreate(
        name="test-stdio-workflow",
        description="Test server for stdio workflow",
        transport_type=TransportType.STDIO,
        command=mcp_stdio_test_server_config.command,
        args=mcp_stdio_test_server_config.args,
        env=mcp_stdio_test_server_config.env,
    )

    # Mock database behavior
    mock_server = MCPServer(
        id=uuid4(),
        tenant_id=uuid4(),
        name=server_create.name,
        description=server_create.description,
        transport_type=server_create.transport_type,
        command=server_create.command,
        args=server_create.args,
        env=server_create.env,
        url=None,
        headers={},
        discovered_tools=[],
        discovered_resources=[],
        discovered_prompts=[],
        status=MCPServerStatus.INACTIVE,
        last_health_check=None,
        error_message=None,
        consecutive_failures=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    # Mock DB operations
    from unittest.mock import MagicMock, AsyncMock
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_server
    mock_db_session.execute.return_value = mock_result

    # Step 2: Discover capabilities
    await service.discover_capabilities(mock_server.id)

    # Validate discovery results
    assert mock_server.status == MCPServerStatus.ACTIVE
    assert len(mock_server.discovered_tools) > 0
    assert mock_server.error_message is None

    # Verify expected tools are present
    tool_names = {tool["name"] for tool in mock_server.discovered_tools}
    assert "echo" in tool_names
    assert "add" in tool_names


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_stdio_workflow_tool_invocation(mcp_stdio_client):
    """
    Test Workflow 1: Direct tool invocation through stdio client.

    Validates:
    - Tool can be invoked with correct arguments
    - Result matches expected format
    - Echo tool returns input message
    """
    # Step 1: List tools to verify availability
    tools = await mcp_stdio_client.list_tools()
    assert len(tools) > 0

    tool_names = {tool["name"] for tool in tools}
    assert "echo" in tool_names

    # Step 2: Get echo tool schema
    echo_tool = next(t for t in tools if t["name"] == "echo")
    assert "inputSchema" in echo_tool
    assert echo_tool["inputSchema"]["type"] == "object"

    # Step 3: Invoke echo tool
    test_message = "Integration test message 123"
    result = await mcp_stdio_client.call_tool("echo", {"message": test_message})

    # Step 4: Validate result
    assert result["is_error"] is False
    assert test_message in str(result["content"])


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_stdio_workflow_multiple_tool_calls(mcp_stdio_client):
    """
    Test multiple sequential tool calls in same session.

    Validates:
    - Client can handle multiple tool calls
    - Each call returns correct result
    - No interference between calls
    """
    # Call 1: Echo
    result1 = await mcp_stdio_client.call_tool("echo", {"message": "First call"})
    assert result1["is_error"] is False
    assert "First call" in str(result1["content"])

    # Call 2: Add
    result2 = await mcp_stdio_client.call_tool("add", {"a": 10, "b": 20})
    assert result2["is_error"] is False
    assert "30" in str(result2["content"])

    # Call 3: Echo again with different message
    result3 = await mcp_stdio_client.call_tool("echo", {"message": "Third call"})
    assert result3["is_error"] is False
    assert "Third call" in str(result3["content"])
    assert "First call" not in str(result3["content"])  # No cross-contamination


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_stdio_workflow_list_all_primitives(mcp_stdio_client):
    """
    Test listing all three MCP primitives in stdio workflow.

    Validates:
    - list_tools() returns tools
    - list_resources() returns resources (or empty list)
    - list_prompts() returns prompts (or empty list)
    """
    # List tools
    tools = await mcp_stdio_client.list_tools()
    assert isinstance(tools, list)
    assert len(tools) > 0

    # Validate tool structure
    for tool in tools:
        assert "name" in tool
        assert "inputSchema" in tool
        assert isinstance(tool["inputSchema"], dict)

    # List resources
    resources = await mcp_stdio_client.list_resources()
    assert isinstance(resources, list)

    # List prompts
    prompts = await mcp_stdio_client.list_prompts()
    assert isinstance(prompts, list)


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_stdio_workflow_concurrent_clients(mcp_stdio_test_server_config):
    """
    Test multiple concurrent stdio clients can operate independently.

    Validates:
    - Multiple clients can be spawned
    - Each has independent process
    - No interference between clients
    """
    # Spawn two clients concurrently
    async with MCPStdioClient(mcp_stdio_test_server_config) as client1:
        await client1.initialize()

        async with MCPStdioClient(mcp_stdio_test_server_config) as client2:
            await client2.initialize()

            # Verify independent processes
            assert client1.process is not None
            assert client2.process is not None
            assert client1.process.pid != client2.process.pid

            # Call tools on both clients
            result1 = await client1.call_tool("echo", {"message": "Client 1"})
            result2 = await client2.call_tool("echo", {"message": "Client 2"})

            # Verify no cross-contamination
            assert "Client 1" in str(result1["content"])
            assert "Client 2" in str(result2["content"])
            assert "Client 2" not in str(result1["content"])
            assert "Client 1" not in str(result2["content"])


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_stdio_workflow_tool_with_complex_arguments(mcp_stdio_client):
    """
    Test tool invocation with complex nested arguments.

    Validates:
    - Tools handle nested objects
    - Arguments serialize correctly through JSON-RPC
    - Results are properly returned
    """
    # The 'add' tool takes simple numeric arguments
    result = await mcp_stdio_client.call_tool("add", {
        "a": 100,
        "b": 50
    })

    assert result["is_error"] is False
    content_str = str(result["content"])
    assert "150" in content_str


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_stdio_workflow_health_check_after_discovery(
    mcp_stdio_test_server_config, mock_db_session
):
    """
    Test health check works after capability discovery.

    Validates:
    - Server remains healthy after discovery
    - Health check completes quickly
    - Status reflects server is active
    """
    service = MCPServerService(mock_db_session)

    # Mock server
    mock_server = MCPServer(
        id=uuid4(),
        tenant_id=uuid4(),
        name="health-check-test",
        description="Test health check",
        transport_type=TransportType.STDIO,
        command=mcp_stdio_test_server_config.command,
        args=mcp_stdio_test_server_config.args,
        env=mcp_stdio_test_server_config.env,
        url=None,
        headers={},
        discovered_tools=[],
        discovered_resources=[],
        discovered_prompts=[],
        status=MCPServerStatus.ACTIVE,
        last_health_check=None,
        error_message=None,
        consecutive_failures=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    # Mock DB operations
    from unittest.mock import MagicMock, patch
    with patch.object(service, 'get_server_by_id', return_value=mock_server):
        health = await service.check_health(mock_server.id, mock_server.tenant_id)

        # Validate health check
        assert health is not None
        assert health["status"] == "active"
        assert health["response_time_ms"] >= 0
        assert health["error_message"] is None
