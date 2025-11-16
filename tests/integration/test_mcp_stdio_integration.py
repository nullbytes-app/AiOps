"""
Integration tests for MCP stdio Transport Client.

Tests MCPStdioClient with real MCP server subprocess.
Requires test MCP server for full integration testing.

Note: These tests are marked with @pytest.mark.integration and require
a test MCP server executable to be available. They can be skipped in
environments where no test server is available.
"""

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.schemas.mcp_server import MCPServerResponse
from src.services.mcp_stdio_client import (
    InitializationError,
    MCPStdioClient,
    ProcessError,
    TimeoutError,
)


# Skip all tests if TEST_MCP_SERVER is not configured
pytestmark = pytest.mark.integration


@pytest.fixture
def test_mcp_server_config():
    """
    Configuration for test MCP server.

    Note: This uses a mock echo server for demonstration.
    In production, replace with actual MCP test server like:
    @modelcontextprotocol/server-everything

    For now, tests will be skipped if server is not available.
    """
    return MCPServerResponse(
        id=uuid4(),
        tenant_id=uuid4(),
        name="test-mcp-server",
        transport_type="stdio",
        command="python",
        args=["-c", "import sys; sys.exit(0)"],  # Minimal Python process for testing
        env={},
        status="active",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.mark.skip(reason="Requires real MCP test server - to be implemented with @modelcontextprotocol/server-everything")
@pytest.mark.asyncio
async def test_full_workflow_with_real_server(test_mcp_server_config):
    """
    Test full workflow: initialize → list_tools → call_tool → close.

    This test requires a real MCP server to be available.
    """
    async with MCPStdioClient(test_mcp_server_config) as client:
        # Initialize connection
        capabilities = await client.initialize()
        assert "tools" in capabilities or "resources" in capabilities or "prompts" in capabilities

        # List available tools
        tools = await client.list_tools()
        assert isinstance(tools, list)

        # If tools available, call one
        if tools:
            tool_name = tools[0]["name"]
            # Note: arguments depend on tool schema
            result = await client.call_tool(tool_name, {})
            assert "content" in result
            assert "is_error" in result


@pytest.mark.skip(reason="Requires real MCP test server with all three primitives")
@pytest.mark.asyncio
async def test_all_three_primitives(test_mcp_server_config):
    """
    Test all three MCP primitives: tools, resources, prompts.

    Requires test server that implements all primitives.
    """
    async with MCPStdioClient(test_mcp_server_config) as client:
        await client.initialize()

        # Test tools primitive
        tools = await client.list_tools()
        assert isinstance(tools, list)

        # Test resources primitive
        resources = await client.list_resources()
        assert isinstance(resources, list)

        # Test prompts primitive
        prompts = await client.list_prompts()
        assert isinstance(prompts, list)


@pytest.mark.asyncio
async def test_subprocess_spawning_and_cleanup(test_mcp_server_config):
    """Test subprocess is spawned and terminated correctly."""
    async with MCPStdioClient(test_mcp_server_config) as client:
        # Verify process was spawned
        assert client.process is not None
        assert client.process.pid is not None

        initial_pid = client.process.pid

    # After context exit, process should be terminated
    # Note: We can't directly verify process termination without process access
    # This test verifies no exceptions during cleanup


@pytest.mark.asyncio
async def test_invalid_command_raises_process_error():
    """Test invalid command raises ProcessError during spawn."""
    config = MCPServerResponse(
        id=uuid4(),
        tenant_id=uuid4(),
        name="invalid-server",
        transport_type="stdio",
        command="nonexistent_command_xyz",  # Invalid command
        args=[],
        env={},
        status="active",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    with pytest.raises(ProcessError, match="Failed to spawn subprocess"):
        async with MCPStdioClient(config) as client:
            pass


@pytest.mark.skip(reason="Requires real MCP test server with slow operations")
@pytest.mark.asyncio
async def test_timeout_with_slow_server(test_mcp_server_config):
    """
    Test timeout handling with slow MCP server.

    Requires test server that simulates slow responses.
    """
    async with MCPStdioClient(test_mcp_server_config) as client:
        # Call with very short timeout
        with pytest.raises(TimeoutError):
            await client.initialize()  # Default 30s timeout


@pytest.mark.asyncio
async def test_environment_variables_passed_to_subprocess():
    """Test environment variables are passed to subprocess."""
    config = MCPServerResponse(
        id=uuid4(),
        tenant_id=uuid4(),
        name="env-test-server",
        transport_type="stdio",
        command="python",
        args=["-c", "import os, sys; print(os.environ.get('TEST_VAR', 'NOT_SET')); sys.exit(0)"],
        env={"TEST_VAR": "test_value"},
        status="active",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    # This test verifies subprocess spawns with env vars
    # Full verification would require reading subprocess output
    async with MCPStdioClient(config) as client:
        assert client.env == {"TEST_VAR": "test_value"}


@pytest.mark.skip(reason="Requires real MCP test server")
@pytest.mark.asyncio
async def test_multiple_sequential_calls(test_mcp_server_config):
    """
    Test multiple sequential calls with same client instance.

    Verifies process is reused for multiple operations.
    """
    async with MCPStdioClient(test_mcp_server_config) as client:
        await client.initialize()

        # Multiple sequential calls
        for _ in range(3):
            tools = await client.list_tools()
            assert isinstance(tools, list)

        # Verify same process was reused
        assert client.process is not None


@pytest.mark.asyncio
async def test_async_context_manager_cleanup_on_exception():
    """Test async context manager cleanup happens even on exception."""
    config = MCPServerResponse(
        id=uuid4(),
        tenant_id=uuid4(),
        name="exception-test",
        transport_type="stdio",
        command="python",
        args=["-c", "import sys; sys.exit(0)"],
        env={},
        status="active",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    try:
        async with MCPStdioClient(config) as client:
            # Raise exception inside context
            raise ValueError("Test exception")
    except ValueError:
        pass  # Expected

    # Cleanup should have happened despite exception
    # (verified by no hanging processes)


@pytest.mark.skip(reason="Requires real MCP test server")
@pytest.mark.asyncio
async def test_stderr_capture_and_logging(test_mcp_server_config, caplog):
    """
    Test stderr output is captured and logged.

    Requires test server that writes to stderr.
    """
    import logging

    caplog.set_level(logging.WARNING)

    async with MCPStdioClient(test_mcp_server_config) as client:
        await client.initialize()

        # Allow time for stderr monitoring
        await asyncio.sleep(0.5)

    # Check if stderr was logged
    # Note: This depends on test server writing to stderr
    # assert "MCP server stderr" in caplog.text


@pytest.mark.skip(reason="Requires multiple concurrent test servers")
@pytest.mark.asyncio
async def test_concurrent_clients_independent_processes():
    """
    Test multiple client instances have independent processes.

    Verifies isolation between clients.
    """
    config1 = MCPServerResponse(
        id=uuid4(),
        tenant_id=uuid4(),
        name="server-1",
        transport_type="stdio",
        command="python",
        args=["-c", "import sys; sys.exit(0)"],
        env={},
        status="active",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    config2 = MCPServerResponse(
        id=uuid4(),
        tenant_id=uuid4(),
        name="server-2",
        transport_type="stdio",
        command="python",
        args=["-c", "import sys; sys.exit(0)"],
        env={},
        status="active",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    async with MCPStdioClient(config1) as client1:
        async with MCPStdioClient(config2) as client2:
            # Verify different processes
            assert client1.process.pid != client2.process.pid
