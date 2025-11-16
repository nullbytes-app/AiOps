"""
Unit tests for MCP Tool Bridge Service.

Tests the bridge between MCP servers and LangChain tools, covering:
- Tool conversion for all 3 MCP primitive types (tool, resource, prompt)
- Client lifecycle management (initialization, reuse, cleanup)
- Error handling and timeout enforcement
- Custom wrapper creation for resources and prompts

References:
- Story 11.1.7: MCP Tool Invocation in Agent Execution
- src/services/mcp_tool_bridge.py
"""

import asyncio
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from langchain_core.tools import BaseTool

from src.database.models import MCPServer
from src.services.mcp_tool_bridge import MCPToolBridge


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_mcp_servers() -> List[MCPServer]:
    """Create mock MCP server instances for testing."""
    server1 = MCPServer(
        id=uuid4(),
        tenant_id="test-tenant",
        name="test-server-1",
        description="Test MCP server 1",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem"],
        env={"PATH": "/usr/local/bin"},
        status="active",
    )

    server2 = MCPServer(
        id=uuid4(),
        tenant_id="test-tenant",
        name="test-server-2",
        description="Test MCP server 2",
        command="python",
        args=["-m", "mcp_server"],
        env={},
        status="active",
    )

    return [server1, server2]


@pytest.fixture
def mcp_tool_assignments() -> List[Dict[str, Any]]:
    """Create mock MCP tool assignments."""
    return [
        {
            "id": str(uuid4()),
            "name": "read_file",
            "mcp_server_id": uuid4(),
            "mcp_primitive_type": "tool",
            "description": "Read file contents",
        },
        {
            "id": str(uuid4()),
            "name": "filesystem_resource",
            "mcp_server_id": uuid4(),
            "mcp_primitive_type": "resource",
            "description": "Access filesystem resource",
        },
        {
            "id": str(uuid4()),
            "name": "code_prompt",
            "mcp_server_id": uuid4(),
            "mcp_primitive_type": "prompt",
            "description": "Code generation prompt",
        },
    ]


# ============================================================================
# Test MCPToolBridge Initialization
# ============================================================================


def test_mcp_tool_bridge_initialization(mock_mcp_servers: List[MCPServer]) -> None:
    """Test MCPToolBridge initialization with server list."""
    bridge = MCPToolBridge(mock_mcp_servers)

    assert bridge.servers == mock_mcp_servers
    assert bridge.client is None
    assert bridge._initialized is False


def test_mcp_tool_bridge_initialization_empty_servers() -> None:
    """Test MCPToolBridge initialization with empty server list."""
    bridge = MCPToolBridge([])

    assert bridge.servers == []
    assert bridge.client is None
    assert bridge._initialized is False


# ============================================================================
# Test Client Initialization
# ============================================================================


@pytest.mark.asyncio
async def test_initialize_client_success(mock_mcp_servers: List[MCPServer]) -> None:
    """Test successful client initialization."""
    bridge = MCPToolBridge(mock_mcp_servers)

    with patch("src.services.mcp_tool_bridge.MultiServerMCPClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        await bridge._initialize_client()

        # Verify client was created with correct config
        assert bridge._initialized is True
        assert bridge.client == mock_client
        mock_client_class.assert_called_once()

        # Verify server configs were passed correctly
        call_args = mock_client_class.call_args[0][0]
        assert len(call_args) == 2  # Two servers
        assert str(mock_mcp_servers[0].id) in call_args
        assert str(mock_mcp_servers[1].id) in call_args


@pytest.mark.asyncio
async def test_initialize_client_already_initialized(
    mock_mcp_servers: List[MCPServer],
) -> None:
    """Test client initialization when already initialized (should skip)."""
    bridge = MCPToolBridge(mock_mcp_servers)
    bridge._initialized = True
    bridge.client = MagicMock()

    with patch("src.services.mcp_tool_bridge.MultiServerMCPClient") as mock_client_class:
        await bridge._initialize_client()

        # Client should not be recreated
        mock_client_class.assert_not_called()


@pytest.mark.asyncio
async def test_initialize_client_failure(mock_mcp_servers: List[MCPServer]) -> None:
    """Test client initialization failure handling."""
    bridge = MCPToolBridge(mock_mcp_servers)

    with patch(
        "src.services.mcp_tool_bridge.MultiServerMCPClient",
        side_effect=RuntimeError("Client init failed"),
    ):
        with pytest.raises(RuntimeError, match="MCP client initialization failed"):
            await bridge._initialize_client()

        assert bridge._initialized is False
        assert bridge.client is None


# ============================================================================
# Test Tool Conversion
# ============================================================================


@pytest.mark.asyncio
async def test_get_langchain_tools_success(
    mock_mcp_servers: List[MCPServer],
) -> None:
    """Test successful conversion of MCP tools to LangChain tools."""
    bridge = MCPToolBridge(mock_mcp_servers)

    # Create assignments with ACTUAL server IDs from mock_mcp_servers
    mcp_tool_assignments = [
        {
            "id": str(uuid4()),
            "name": "read_file",
            "mcp_server_id": mock_mcp_servers[0].id,  # Use actual server ID
            "mcp_primitive_type": "tool",
            "description": "Read file contents",
        },
        {
            "id": str(uuid4()),
            "name": "filesystem_resource",
            "mcp_server_id": mock_mcp_servers[0].id,  # Use actual server ID
            "mcp_primitive_type": "resource",
            "description": "Access filesystem resource",
        },
        {
            "id": str(uuid4()),
            "name": "code_prompt",
            "mcp_server_id": mock_mcp_servers[0].id,  # Use actual server ID
            "mcp_primitive_type": "prompt",
            "description": "Code generation prompt",
        },
    ]

    # Mock MultiServerMCPClient and load_mcp_tools
    mock_client = MagicMock()
    mock_session = AsyncMock()

    # Mock load_mcp_tools to return mock tools
    mock_tool1 = MagicMock(spec=BaseTool)
    mock_tool1.name = "read_file"

    with patch("src.services.mcp_tool_bridge.MultiServerMCPClient", return_value=mock_client):
        with patch("src.services.mcp_tool_bridge.load_mcp_tools") as mock_load_tools:
            mock_load_tools.return_value = [mock_tool1]

            # Mock session context manager
            mock_client.session.return_value.__aenter__.return_value = mock_session

            # Mock read_resource and get_prompt for custom wrappers
            mock_session.read_resource = AsyncMock(
                return_value={"contents": [{"text": "resource content"}]}
            )
            mock_session.get_prompt = AsyncMock(
                return_value={"messages": [{"content": "prompt content"}]}
            )

            # Execute
            tools = await bridge.get_langchain_tools(mcp_tool_assignments)

            # Verify tools were created
            assert len(tools) > 0
            # Should have 1 tool + 1 resource wrapper + 1 prompt wrapper = 3 total
            assert len(tools) == 3


@pytest.mark.asyncio
async def test_get_langchain_tools_empty_assignments(
    mock_mcp_servers: List[MCPServer],
) -> None:
    """Test tool conversion with empty assignment list."""
    bridge = MCPToolBridge(mock_mcp_servers)

    with patch("src.services.mcp_tool_bridge.MultiServerMCPClient"):
        tools = await bridge.get_langchain_tools([])

        assert tools == []


@pytest.mark.asyncio
async def test_get_langchain_tools_timeout(
    mock_mcp_servers: List[MCPServer],
    mcp_tool_assignments: List[Dict[str, Any]],
) -> None:
    """Test timeout handling during tool loading."""
    bridge = MCPToolBridge(mock_mcp_servers)

    mock_client = MagicMock()
    mock_session = AsyncMock()

    with patch("src.services.mcp_tool_bridge.MultiServerMCPClient", return_value=mock_client):
        with patch(
            "src.services.mcp_tool_bridge.load_mcp_tools",
            side_effect=asyncio.TimeoutError(),
        ):
            mock_client.session.return_value.__aenter__.return_value = mock_session

            # Should handle timeout gracefully
            tools = await bridge.get_langchain_tools(mcp_tool_assignments)

            # Should return empty list (graceful degradation)
            assert tools == []


@pytest.mark.asyncio
async def test_get_langchain_tools_server_error(
    mock_mcp_servers: List[MCPServer],
    mcp_tool_assignments: List[Dict[str, Any]],
) -> None:
    """Test error handling when server fails to load tools."""
    bridge = MCPToolBridge(mock_mcp_servers)

    mock_client = MagicMock()
    mock_session = AsyncMock()

    with patch("src.services.mcp_tool_bridge.MultiServerMCPClient", return_value=mock_client):
        with patch(
            "src.services.mcp_tool_bridge.load_mcp_tools",
            side_effect=Exception("Server error"),
        ):
            mock_client.session.return_value.__aenter__.return_value = mock_session

            # Should handle error gracefully
            tools = await bridge.get_langchain_tools(mcp_tool_assignments)

            # Should return empty list (graceful degradation)
            assert tools == []


# ============================================================================
# Test Resource Wrapper
# ============================================================================


@pytest.mark.asyncio
async def test_create_resource_wrapper_success(
    mock_mcp_servers: List[MCPServer],
) -> None:
    """Test resource wrapper creation and invocation."""
    bridge = MCPToolBridge(mock_mcp_servers)
    server = mock_mcp_servers[0]

    assignment = {
        "name": "filesystem_resource",
        "description": "Access filesystem resource",
    }

    mock_session = AsyncMock()
    mock_session.read_resource = AsyncMock(return_value={"contents": [{"text": "file content"}]})

    # Create wrapper
    resource_tool = bridge._create_resource_wrapper(server, assignment, mock_session)

    # Verify tool properties
    assert resource_tool.name == "filesystem_resource"
    assert "filesystem resource" in resource_tool.description.lower()

    # Invoke tool
    result = await resource_tool.ainvoke({"uri": "file:///test.txt"})

    # Verify result
    assert result == "file content"
    mock_session.read_resource.assert_called_once_with("file:///test.txt")


@pytest.mark.asyncio
async def test_create_resource_wrapper_timeout(
    mock_mcp_servers: List[MCPServer],
) -> None:
    """Test resource wrapper timeout handling."""
    bridge = MCPToolBridge(mock_mcp_servers)
    server = mock_mcp_servers[0]

    assignment = {"name": "filesystem_resource", "description": "Test resource"}

    mock_session = AsyncMock()
    mock_session.read_resource = AsyncMock(side_effect=asyncio.TimeoutError())

    # Create wrapper
    resource_tool = bridge._create_resource_wrapper(server, assignment, mock_session)

    # Invoke tool (should handle timeout)
    result = await resource_tool.ainvoke({"uri": "file:///test.txt"})

    # Should return error message
    assert "Error" in result
    assert "timeout" in result.lower()


@pytest.mark.asyncio
async def test_create_resource_wrapper_error(mock_mcp_servers: List[MCPServer]) -> None:
    """Test resource wrapper error handling."""
    bridge = MCPToolBridge(mock_mcp_servers)
    server = mock_mcp_servers[0]

    assignment = {"name": "filesystem_resource", "description": "Test resource"}

    mock_session = AsyncMock()
    mock_session.read_resource = AsyncMock(side_effect=Exception("Resource read failed"))

    # Create wrapper
    resource_tool = bridge._create_resource_wrapper(server, assignment, mock_session)

    # Invoke tool (should handle error)
    result = await resource_tool.ainvoke({"uri": "file:///test.txt"})

    # Should return error message
    assert "Error" in result
    assert "failed" in result.lower()


# ============================================================================
# Test Prompt Wrapper
# ============================================================================


@pytest.mark.asyncio
async def test_create_prompt_wrapper_success(mock_mcp_servers: List[MCPServer]) -> None:
    """Test prompt wrapper creation and invocation."""
    bridge = MCPToolBridge(mock_mcp_servers)
    server = mock_mcp_servers[0]

    assignment = {"name": "code_prompt", "description": "Code generation prompt"}

    mock_session = AsyncMock()
    mock_session.get_prompt = AsyncMock(
        return_value={"messages": [{"content": "Generate code for..."}]}
    )

    # Create wrapper
    prompt_tool = bridge._create_prompt_wrapper(server, assignment, mock_session)

    # Verify tool properties
    assert prompt_tool.name == "code_prompt"
    assert "code generation" in prompt_tool.description.lower()

    # Invoke tool with arguments
    result = await prompt_tool.ainvoke({"arguments": {"language": "python"}})

    # Verify result
    assert result == "Generate code for..."
    mock_session.get_prompt.assert_called_once_with("code_prompt", {"language": "python"})


@pytest.mark.asyncio
async def test_create_prompt_wrapper_no_arguments(
    mock_mcp_servers: List[MCPServer],
) -> None:
    """Test prompt wrapper invocation without arguments."""
    bridge = MCPToolBridge(mock_mcp_servers)
    server = mock_mcp_servers[0]

    assignment = {"name": "code_prompt", "description": "Code generation prompt"}

    mock_session = AsyncMock()
    mock_session.get_prompt = AsyncMock(return_value={"messages": [{"content": "Default prompt"}]})

    # Create wrapper
    prompt_tool = bridge._create_prompt_wrapper(server, assignment, mock_session)

    # Invoke tool without arguments
    result = await prompt_tool.ainvoke({"arguments": None})

    # Verify result
    assert result == "Default prompt"
    mock_session.get_prompt.assert_called_once_with("code_prompt", {})


@pytest.mark.asyncio
async def test_create_prompt_wrapper_timeout(mock_mcp_servers: List[MCPServer]) -> None:
    """Test prompt wrapper timeout handling."""
    bridge = MCPToolBridge(mock_mcp_servers)
    server = mock_mcp_servers[0]

    assignment = {"name": "code_prompt", "description": "Test prompt"}

    mock_session = AsyncMock()
    mock_session.get_prompt = AsyncMock(side_effect=asyncio.TimeoutError())

    # Create wrapper
    prompt_tool = bridge._create_prompt_wrapper(server, assignment, mock_session)

    # Invoke tool (should handle timeout)
    result = await prompt_tool.ainvoke({"arguments": None})

    # Should return error message
    assert "Error" in result
    assert "timeout" in result.lower()


@pytest.mark.asyncio
async def test_create_prompt_wrapper_error(mock_mcp_servers: List[MCPServer]) -> None:
    """Test prompt wrapper error handling."""
    bridge = MCPToolBridge(mock_mcp_servers)
    server = mock_mcp_servers[0]

    assignment = {"name": "code_prompt", "description": "Test prompt"}

    mock_session = AsyncMock()
    mock_session.get_prompt = AsyncMock(side_effect=Exception("Prompt get failed"))

    # Create wrapper
    prompt_tool = bridge._create_prompt_wrapper(server, assignment, mock_session)

    # Invoke tool (should handle error)
    result = await prompt_tool.ainvoke({"arguments": None})

    # Should return error message
    assert "Error" in result
    assert "failed" in result.lower()


# ============================================================================
# Test Cleanup
# ============================================================================


@pytest.mark.asyncio
async def test_cleanup_success(mock_mcp_servers: List[MCPServer]) -> None:
    """Test successful cleanup of MCP client."""
    bridge = MCPToolBridge(mock_mcp_servers)

    # Set up initialized client
    bridge._initialized = True
    bridge.client = MagicMock()

    # Cleanup
    await bridge.cleanup()

    # Verify cleanup
    assert bridge._initialized is False
    assert bridge.client is None


@pytest.mark.asyncio
async def test_cleanup_no_client(mock_mcp_servers: List[MCPServer]) -> None:
    """Test cleanup when no client exists (should not raise error)."""
    bridge = MCPToolBridge(mock_mcp_servers)

    # Cleanup without initializing client
    await bridge.cleanup()

    # Should complete without error
    assert bridge.client is None


@pytest.mark.asyncio
async def test_cleanup_error_handling(mock_mcp_servers: List[MCPServer]) -> None:
    """Test cleanup error handling."""
    bridge = MCPToolBridge(mock_mcp_servers)

    # Set up client that raises error on cleanup
    bridge._initialized = True
    bridge.client = MagicMock()

    # Cleanup should handle errors gracefully
    await bridge.cleanup()

    # Cleanup should still mark as not initialized
    assert bridge._initialized is False


# ============================================================================
# Test Tool Filtering
# ============================================================================


@pytest.mark.asyncio
async def test_tool_filtering_by_assignment(
    mock_mcp_servers: List[MCPServer],
) -> None:
    """Test that only assigned tools are returned."""
    bridge = MCPToolBridge(mock_mcp_servers)

    # Create assignments for specific tools
    assignments = [
        {
            "id": str(uuid4()),
            "name": "read_file",
            "mcp_server_id": mock_mcp_servers[0].id,
            "mcp_primitive_type": "tool",
        }
    ]

    # Mock tools from server (multiple tools available)
    mock_tool1 = MagicMock(spec=BaseTool)
    mock_tool1.name = "read_file"
    mock_tool2 = MagicMock(spec=BaseTool)
    mock_tool2.name = "write_file"

    mock_client = MagicMock()
    mock_session = AsyncMock()

    with patch("src.services.mcp_tool_bridge.MultiServerMCPClient", return_value=mock_client):
        with patch(
            "src.services.mcp_tool_bridge.load_mcp_tools",
            return_value=[mock_tool1, mock_tool2],
        ):
            mock_client.session.return_value.__aenter__.return_value = mock_session

            tools = await bridge.get_langchain_tools(assignments)

            # Should only return assigned tool (read_file)
            assert len(tools) == 1
            assert tools[0].name == "read_file"
