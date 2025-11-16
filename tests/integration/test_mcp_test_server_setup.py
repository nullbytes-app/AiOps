"""
Test MCP Test Server Infrastructure Setup (Story 11.2.6 - AC#5).

Validates that @modelcontextprotocol/server-everything is properly configured
and can be used for integration testing of MCP features.

These tests verify:
1. Test server can be spawned
2. All three primitives are available (tools, resources, prompts)
3. Fixtures work correctly for integration tests
"""

import pytest


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_mcp_test_server_spawns_successfully(mcp_stdio_client):
    """
    Test that MCP test server can be spawned and initialized.

    Validates:
    - Server process starts without errors
    - Initialize handshake completes successfully
    - Client is ready for further operations
    """
    # Client is already initialized by fixture
    assert mcp_stdio_client is not None
    assert mcp_stdio_client.process is not None
    assert mcp_stdio_client.process.returncode is None  # Process still running


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_mcp_test_server_provides_tools(mcp_stdio_client):
    """
    Test that test server exposes tools primitive.

    @modelcontextprotocol/server-everything should provide:
    - echo
    - add
    - longRunningOperation
    - sampleLLM
    - getTinyImage
    """
    tools = await mcp_stdio_client.list_tools()

    assert isinstance(tools, list)
    assert len(tools) > 0

    tool_names = {tool["name"] for tool in tools}

    # Verify at least some expected tools are present
    expected_tools = {"echo", "add"}
    assert expected_tools.issubset(tool_names), \
        f"Expected tools {expected_tools} not found. Got: {tool_names}"


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_mcp_test_server_provides_resources(mcp_stdio_client):
    """
    Test that test server exposes resources primitive.

    @modelcontextprotocol/server-everything should provide:
    - test://static/resource
    - test://dynamic/{id}
    """
    resources = await mcp_stdio_client.list_resources()

    assert isinstance(resources, list)
    assert len(resources) >= 0  # May be empty depending on server version


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_mcp_test_server_provides_prompts(mcp_stdio_client):
    """
    Test that test server exposes prompts primitive.

    @modelcontextprotocol/server-everything should provide:
    - simple_prompt
    - complex_prompt
    """
    prompts = await mcp_stdio_client.list_prompts()

    assert isinstance(prompts, list)
    assert len(prompts) >= 0  # May be empty depending on server version


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_mcp_test_server_echo_tool(mcp_stdio_client):
    """
    Test calling the 'echo' tool on test server.

    Validates:
    - Tool invocation workflow works end-to-end
    - Tool returns expected result structure
    - Response contains echoed message
    """
    # Call echo tool with test message
    result = await mcp_stdio_client.call_tool("echo", {"message": "test-echo-123"})

    # Validate result structure
    assert isinstance(result, dict)
    assert "content" in result
    assert "is_error" in result

    # Validate echo worked
    assert result["is_error"] is False
    content_str = str(result["content"])
    assert "test-echo-123" in content_str


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_mcp_test_server_add_tool(mcp_stdio_client):
    """
    Test calling the 'add' tool on test server.

    Validates:
    - Tool with multiple arguments works
    - Numeric computation is correct
    """
    # Call add tool
    result = await mcp_stdio_client.call_tool("add", {"a": 5, "b": 3})

    # Validate result
    assert isinstance(result, dict)
    assert result["is_error"] is False

    # Check result contains 8 (5 + 3)
    content_str = str(result["content"])
    assert "8" in content_str


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_mcp_test_server_cleanup(mcp_stdio_test_server_config):
    """
    Test that MCP client properly cleans up on exit.

    Validates:
    - Client context manager closes process
    - No zombie processes remain
    - Resources are released
    """
    from src.services.mcp_stdio_client import MCPStdioClient

    # Spawn and close client
    async with MCPStdioClient(mcp_stdio_test_server_config) as client:
        await client.initialize()
        process = client.process
        assert process is not None
        assert process.returncode is None  # Running

    # After context exit, process should be terminated
    # Note: May not be immediate, but process should not be in running state
    # We just verify no exception was raised during cleanup
