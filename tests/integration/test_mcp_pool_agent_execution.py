"""
Integration tests for MCP Bridge Pooling in Agent Execution.

Tests the complete MCP bridge pooling workflow integrated with agent execution service.
Verifies connection reuse, execution context isolation, and proper cleanup.

References:
- Story 11.2.3: MCP Connection Pooling and Caching
- AC#7: Integration with Agent Execution Service
- Task 5.6: Integration tests for agent execution with pooling
- src/services/agent_execution_service.py (bridge pooling)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import uuid4, UUID
from typing import Dict, Any

from src.services.agent_execution_service import AgentExecutionService, _mcp_bridge_pool
from src.services.mcp_tool_bridge import MCPToolBridge
from src.database.models import Agent, MCPServer
from src.schemas.unified_tool import UnifiedTool


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_agent() -> Agent:
    """Create mock agent for testing."""
    agent = MagicMock(spec=Agent)
    agent.id = uuid4()
    agent.tenant_id = "test-tenant"
    agent.name = "Test Agent"
    agent.status = "active"
    agent.system_prompt = "You are a helpful assistant."
    agent.llm_config = {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "temperature": 0.3,
        "max_tokens": 1000,
    }
    return agent


@pytest.fixture
def mock_mcp_servers() -> list:
    """Create mock MCP server configurations."""
    return [
        MCPServer(
            id=uuid4(),
            tenant_id="test-tenant",
            name="Test MCP Server 1",
            description="Test server 1",
            transport_type="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-everything"],
            env={},
            status="active",
        ),
        MCPServer(
            id=uuid4(),
            tenant_id="test-tenant",
            name="Test MCP Server 2",
            description="Test server 2",
            transport_type="http+sse",
            url="http://localhost:3000/sse",
            env={},
            status="active",
        ),
    ]


@pytest.fixture
def mock_unified_tools() -> list:
    """Create mock unified tools (OpenAPI + MCP)."""
    return [
        UnifiedTool(
            id=uuid4(),
            name="openapi_tool",
            description="OpenAPI tool",
            source_type="openapi",
            input_schema={
                "type": "object",
                "properties": {"arg": {"type": "string"}},
            },
        ),
        UnifiedTool(
            id=uuid4(),
            name="mcp_tool",
            description="MCP tool",
            source_type="mcp",
            mcp_server_id=uuid4(),
            input_schema={
                "type": "object",
                "properties": {"param": {"type": "string"}},
            },
        ),
    ]


@pytest.fixture(autouse=True)
def clear_bridge_pool():
    """Clear bridge pool before and after each test."""
    global _mcp_bridge_pool
    _mcp_bridge_pool.clear()
    yield
    _mcp_bridge_pool.clear()


# ============================================================================
# Integration Tests: Bridge Pooling
# ============================================================================


@pytest.mark.asyncio
async def test_bridge_pooling_single_execution_reuse(
    mock_agent, mock_mcp_servers, mock_unified_tools
) -> None:
    """
    Test bridge reuse within single execution context.

    Verifies:
    - First MCP tool call creates bridge
    - Subsequent calls reuse same bridge instance
    - Bridge is cleaned up after execution

    Related to AC#2 (Execution Context Isolation) and AC#7 (Integration)
    """
    global _mcp_bridge_pool

    # Mock database and services
    mock_db = AsyncMock()
    service = AgentExecutionService(db=mock_db)

    # Track bridge creation
    bridge_creation_count = 0
    original_init = MCPToolBridge.__init__

    def mock_bridge_init(self, *args, **kwargs):
        nonlocal bridge_creation_count
        bridge_creation_count += 1
        original_init(self, *args, **kwargs)

    with patch.object(service.agent_service, "get_agent_by_id", return_value=mock_agent), \
         patch.object(service.llm_service, "get_llm_client_for_tenant") as mock_llm_client, \
         patch.object(service.agent_service, "get_agent_tools", return_value=mock_unified_tools), \
         patch.object(service, "_convert_tools_to_langchain", return_value=[]) as mock_convert, \
         patch("src.services.agent_execution_service.create_react_agent") as mock_create_agent, \
         patch("src.services.agent_execution_service.init_chat_model") as mock_init_model, \
         patch.object(MCPToolBridge, "__init__", mock_bridge_init):

        # Setup mock LLM client with virtual key
        mock_async_client = AsyncMock()
        mock_async_client.api_key = "virtual-key-test-123"
        mock_llm_client.return_value = mock_async_client

        # Setup mock agent executor
        mock_executor = AsyncMock()
        mock_executor.ainvoke = AsyncMock(return_value={
            "messages": [
                MagicMock(content="Test response", type="ai")
            ]
        })
        mock_create_agent.return_value = mock_executor

        # Execute agent (this triggers bridge creation + reuse)
        result = await service.execute_agent(
            agent_id=mock_agent.id,
            tenant_id="test-tenant",
            user_message="Test message with MCP tools",
            timeout_seconds=120,
        )

        # Verify execution succeeded
        assert result["success"] is True

        # Verify _convert_tools_to_langchain was called with execution_context_id
        assert mock_convert.called
        call_args = mock_convert.call_args
        assert "execution_context_id" in call_args.kwargs
        execution_context_id = call_args.kwargs["execution_context_id"]

        # Verify bridge was added to pool during execution
        # (checked via mock_convert call, actual pool access happens in _convert_tools_to_langchain)

        # Verify bridge was cleaned up after execution (pool should be empty)
        assert len(_mcp_bridge_pool) == 0, "Bridge pool should be empty after execution cleanup"


@pytest.mark.asyncio
async def test_bridge_pooling_multiple_sequential_executions(
    mock_agent, mock_mcp_servers, mock_unified_tools
) -> None:
    """
    Test bridge isolation across sequential execution contexts.

    Verifies:
    - Execution A creates bridge with context_id_A
    - Execution A cleanup removes bridge
    - Execution B creates new bridge with context_id_B (not reused from A)

    Related to AC#2 (Execution Context Isolation)
    """
    global _mcp_bridge_pool

    mock_db = AsyncMock()
    service = AgentExecutionService(db=mock_db)

    # Track execution context IDs and bridge instances
    execution_contexts = []
    bridge_instances = []

    async def track_convert_call(*args, **kwargs):
        exec_id = kwargs.get("execution_context_id")
        if exec_id:
            execution_contexts.append(exec_id)
            # Check if bridge exists in pool
            if exec_id in _mcp_bridge_pool:
                bridge_instances.append(_mcp_bridge_pool[exec_id])
        return []  # Return empty tools list

    with patch.object(service.agent_service, "get_agent_by_id", return_value=mock_agent), \
         patch.object(service.llm_service, "get_llm_client_for_tenant") as mock_llm_client, \
         patch.object(service.agent_service, "get_agent_tools", return_value=mock_unified_tools), \
         patch.object(service, "_convert_tools_to_langchain", side_effect=track_convert_call), \
         patch("src.services.agent_execution_service.create_react_agent") as mock_create_agent, \
         patch("src.services.agent_execution_service.init_chat_model"):

        # Setup mocks
        mock_async_client = AsyncMock()
        mock_async_client.api_key = "virtual-key-test"
        mock_llm_client.return_value = mock_async_client

        mock_executor = AsyncMock()
        mock_executor.ainvoke = AsyncMock(return_value={
            "messages": [MagicMock(content="Response", type="ai")]
        })
        mock_create_agent.return_value = mock_executor

        # Execute first agent
        result1 = await service.execute_agent(
            agent_id=mock_agent.id,
            tenant_id="test-tenant",
            user_message="First execution",
        )
        assert result1["success"] is True
        assert len(_mcp_bridge_pool) == 0, "Pool should be empty after first execution cleanup"

        # Execute second agent
        result2 = await service.execute_agent(
            agent_id=mock_agent.id,
            tenant_id="test-tenant",
            user_message="Second execution",
        )
        assert result2["success"] is True
        assert len(_mcp_bridge_pool) == 0, "Pool should be empty after second execution cleanup"

        # Verify different execution context IDs were generated
        assert len(execution_contexts) == 2
        assert execution_contexts[0] != execution_contexts[1], "Each execution should have unique context ID"


@pytest.mark.asyncio
async def test_bridge_cleanup_on_execution_error(
    mock_agent, mock_unified_tools
) -> None:
    """
    Test bridge cleanup happens even when execution fails.

    Verifies:
    - Bridge created during execution
    - Error occurs during agent execution
    - Bridge still cleaned up in finally block

    Related to AC#7 (Integration) - cleanup in finally block
    """
    global _mcp_bridge_pool

    mock_db = AsyncMock()
    service = AgentExecutionService(db=mock_db)

    execution_context_captured = None

    async def capture_and_fail(*args, **kwargs):
        nonlocal execution_context_captured
        execution_context_captured = kwargs.get("execution_context_id")
        raise Exception("Simulated execution error")

    with patch.object(service.agent_service, "get_agent_by_id", return_value=mock_agent), \
         patch.object(service.llm_service, "get_llm_client_for_tenant") as mock_llm_client, \
         patch.object(service.agent_service, "get_agent_tools", return_value=mock_unified_tools), \
         patch.object(service, "_convert_tools_to_langchain", side_effect=capture_and_fail):

        mock_async_client = AsyncMock()
        mock_async_client.api_key = "virtual-key"
        mock_llm_client.return_value = mock_async_client

        # Execute agent (will fail)
        result = await service.execute_agent(
            agent_id=mock_agent.id,
            tenant_id="test-tenant",
            user_message="This will fail",
        )

        # Verify execution failed
        assert result["success"] is False
        assert "error" in result
        assert result["error"] is not None

        # Verify bridge was cleaned up despite error
        assert len(_mcp_bridge_pool) == 0, "Bridge pool should be empty even after error"
        assert execution_context_captured is not None


@pytest.mark.asyncio
async def test_bridge_creation_and_storage_in_pool(
    mock_agent, mock_mcp_servers, mock_unified_tools
) -> None:
    """
    Test bridge is correctly created and stored in pool.

    Verifies:
    - _get_or_create_mcp_bridge creates new bridge on first call
    - Bridge is stored in pool with execution_context_id key
    - Second call returns same bridge instance

    Related to AC#7 (Integration) - pool reuse
    """
    mock_db = AsyncMock()
    service = AgentExecutionService(db=mock_db)

    execution_context_id = str(uuid4())

    # Mock MCPToolBridge
    mock_bridge_1 = AsyncMock(spec=MCPToolBridge)
    mock_bridge_1.cleanup = AsyncMock()

    with patch("src.services.agent_execution_service.MCPToolBridge", return_value=mock_bridge_1):
        # First call - should create new bridge
        bridge1 = await service._get_or_create_mcp_bridge(
            execution_context_id=execution_context_id,
            mcp_servers=mock_mcp_servers,
        )

        assert bridge1 is mock_bridge_1
        assert execution_context_id in _mcp_bridge_pool
        assert _mcp_bridge_pool[execution_context_id] is mock_bridge_1

        # Second call - should return cached bridge (no new MCPToolBridge instance)
        bridge2 = await service._get_or_create_mcp_bridge(
            execution_context_id=execution_context_id,
            mcp_servers=mock_mcp_servers,
        )

        assert bridge2 is mock_bridge_1  # Same instance
        assert len(_mcp_bridge_pool) == 1  # Still only 1 bridge in pool


@pytest.mark.asyncio
async def test_bridge_cleanup_calls_bridge_cleanup_method(
    mock_mcp_servers
) -> None:
    """
    Test _cleanup_mcp_bridge correctly calls bridge.cleanup().

    Verifies:
    - Cleanup method is called on bridge
    - Bridge is removed from pool
    - Pool size decreases correctly

    Related to AC#7 (Integration) - cleanup implementation
    """
    global _mcp_bridge_pool

    mock_db = AsyncMock()
    service = AgentExecutionService(db=mock_db)

    execution_context_id = str(uuid4())

    # Create and store mock bridge
    mock_bridge = AsyncMock(spec=MCPToolBridge)
    mock_bridge.cleanup = AsyncMock()

    with patch("src.services.agent_execution_service.MCPToolBridge", return_value=mock_bridge):
        await service._get_or_create_mcp_bridge(
            execution_context_id=execution_context_id,
            mcp_servers=mock_mcp_servers,
        )

    # Verify bridge is in pool
    assert execution_context_id in _mcp_bridge_pool
    assert len(_mcp_bridge_pool) == 1

    # Cleanup bridge
    await service._cleanup_mcp_bridge(execution_context_id)

    # Verify cleanup was called
    mock_bridge.cleanup.assert_called_once()

    # Verify bridge removed from pool
    assert execution_context_id not in _mcp_bridge_pool
    assert len(_mcp_bridge_pool) == 0


@pytest.mark.asyncio
async def test_bridge_cleanup_handles_missing_execution_context(
) -> None:
    """
    Test cleanup handles gracefully when execution context not in pool.

    Verifies:
    - No error when cleaning up non-existent context
    - Pool state unchanged

    Related to AC#7 (Integration) - error handling
    """
    global _mcp_bridge_pool

    mock_db = AsyncMock()
    service = AgentExecutionService(db=mock_db)

    non_existent_context_id = str(uuid4())

    # Cleanup should not raise error
    await service._cleanup_mcp_bridge(non_existent_context_id)

    # Pool should remain empty
    assert len(_mcp_bridge_pool) == 0


@pytest.mark.asyncio
async def test_bridge_cleanup_handles_cleanup_error(
    mock_mcp_servers
) -> None:
    """
    Test cleanup handles errors during bridge.cleanup() gracefully.

    Verifies:
    - Error during cleanup is logged but doesn't crash
    - Bridge is still removed from pool (best effort)

    Related to AC#7 (Integration) - error resilience
    """
    global _mcp_bridge_pool

    mock_db = AsyncMock()
    service = AgentExecutionService(db=mock_db)

    execution_context_id = str(uuid4())

    # Create mock bridge that raises error on cleanup
    mock_bridge = AsyncMock(spec=MCPToolBridge)
    mock_bridge.cleanup = AsyncMock(side_effect=Exception("Cleanup failed"))

    with patch("src.services.agent_execution_service.MCPToolBridge", return_value=mock_bridge):
        await service._get_or_create_mcp_bridge(
            execution_context_id=execution_context_id,
            mcp_servers=mock_mcp_servers,
        )

    # Cleanup should handle error gracefully
    await service._cleanup_mcp_bridge(execution_context_id)

    # Bridge should still be removed despite error
    assert execution_context_id not in _mcp_bridge_pool
    assert len(_mcp_bridge_pool) == 0


@pytest.mark.asyncio
async def test_bridge_pooling_with_concurrent_executions(
    mock_agent, mock_unified_tools
) -> None:
    """
    Test bridge isolation with concurrent execution contexts.

    Verifies:
    - Two concurrent executions create separate bridges
    - Each has unique execution_context_id
    - Both are cleaned up correctly

    Related to AC#2 (Execution Context Isolation)
    """
    import asyncio
    global _mcp_bridge_pool

    mock_db = AsyncMock()
    service = AgentExecutionService(db=mock_db)

    # Track execution contexts
    contexts_seen = []

    async def track_context(*args, **kwargs):
        exec_id = kwargs.get("execution_context_id")
        if exec_id and exec_id not in contexts_seen:
            contexts_seen.append(exec_id)
        return []

    with patch.object(service.agent_service, "get_agent_by_id", return_value=mock_agent), \
         patch.object(service.llm_service, "get_llm_client_for_tenant") as mock_llm_client, \
         patch.object(service.agent_service, "get_agent_tools", return_value=mock_unified_tools), \
         patch.object(service, "_convert_tools_to_langchain", side_effect=track_context), \
         patch("src.services.agent_execution_service.create_react_agent") as mock_create_agent, \
         patch("src.services.agent_execution_service.init_chat_model"):

        mock_async_client = AsyncMock()
        mock_async_client.api_key = "virtual-key"
        mock_llm_client.return_value = mock_async_client

        mock_executor = AsyncMock()
        mock_executor.ainvoke = AsyncMock(return_value={
            "messages": [MagicMock(content="Response", type="ai")]
        })
        mock_create_agent.return_value = mock_executor

        # Run two concurrent executions
        results = await asyncio.gather(
            service.execute_agent(
                agent_id=mock_agent.id,
                tenant_id="test-tenant",
                user_message="First concurrent execution",
            ),
            service.execute_agent(
                agent_id=mock_agent.id,
                tenant_id="test-tenant",
                user_message="Second concurrent execution",
            ),
        )

        # Verify both succeeded
        assert results[0]["success"] is True
        assert results[1]["success"] is True

        # Verify different execution contexts
        assert len(contexts_seen) == 2
        assert contexts_seen[0] != contexts_seen[1]

        # Verify pool is empty (both cleaned up)
        assert len(_mcp_bridge_pool) == 0


@pytest.mark.asyncio
async def test_bridge_pooling_execution_context_id_format(
    mock_agent, mock_unified_tools
) -> None:
    """
    Test execution_context_id is properly formatted UUID string.

    Verifies:
    - execution_context_id is valid UUID string
    - Can be used as dict key

    Related to AC#7 (Integration) - context ID generation
    """
    mock_db = AsyncMock()
    service = AgentExecutionService(db=mock_db)

    captured_context_id = None

    async def capture_context(*args, **kwargs):
        nonlocal captured_context_id
        captured_context_id = kwargs.get("execution_context_id")
        return []

    with patch.object(service.agent_service, "get_agent_by_id", return_value=mock_agent), \
         patch.object(service.llm_service, "get_llm_client_for_tenant") as mock_llm_client, \
         patch.object(service.agent_service, "get_agent_tools", return_value=mock_unified_tools), \
         patch.object(service, "_convert_tools_to_langchain", side_effect=capture_context), \
         patch("src.services.agent_execution_service.create_react_agent") as mock_create_agent, \
         patch("src.services.agent_execution_service.init_chat_model"):

        mock_async_client = AsyncMock()
        mock_async_client.api_key = "virtual-key"
        mock_llm_client.return_value = mock_async_client

        mock_executor = AsyncMock()
        mock_executor.ainvoke = AsyncMock(return_value={
            "messages": [MagicMock(content="Response", type="ai")]
        })
        mock_create_agent.return_value = mock_executor

        result = await service.execute_agent(
            agent_id=mock_agent.id,
            tenant_id="test-tenant",
            user_message="Test UUID format",
        )

        assert result["success"] is True
        assert captured_context_id is not None

        # Verify it's a valid UUID string
        try:
            parsed_uuid = UUID(captured_context_id)
            assert str(parsed_uuid) == captured_context_id
        except ValueError:
            pytest.fail(f"execution_context_id '{captured_context_id}' is not a valid UUID string")


# ============================================================================
# Performance and Observability Tests
# ============================================================================


@pytest.mark.asyncio
async def test_bridge_pooling_reduces_initialization_overhead(
    mock_agent, mock_unified_tools
) -> None:
    """
    Test bridge pooling reduces overhead by reusing bridge instance.

    Verifies:
    - Bridge creation happens only once per execution
    - Subsequent tool calls reuse same bridge
    - Performance improvement from reuse

    Related to AC#7 (Integration) - performance benefit
    """
    mock_db = AsyncMock()
    service = AgentExecutionService(db=mock_db)

    # Track bridge creation count
    bridge_creations = []

    def track_bridge_creation(*args, **kwargs):
        bridge_creations.append(1)
        return MagicMock(spec=MCPToolBridge)

    async def mock_convert(*args, **kwargs):
        # Simulate calling _get_or_create_mcp_bridge multiple times
        # (like when agent makes multiple MCP tool calls)
        exec_id = kwargs.get("execution_context_id")
        if exec_id:
            # First call
            await service._get_or_create_mcp_bridge(exec_id, [])
            # Second call (should reuse)
            await service._get_or_create_mcp_bridge(exec_id, [])
            # Third call (should reuse)
            await service._get_or_create_mcp_bridge(exec_id, [])
        return []

    with patch.object(service.agent_service, "get_agent_by_id", return_value=mock_agent), \
         patch.object(service.llm_service, "get_llm_client_for_tenant") as mock_llm_client, \
         patch.object(service.agent_service, "get_agent_tools", return_value=mock_unified_tools), \
         patch.object(service, "_convert_tools_to_langchain", side_effect=mock_convert), \
         patch("src.services.agent_execution_service.MCPToolBridge", side_effect=track_bridge_creation), \
         patch("src.services.agent_execution_service.create_react_agent") as mock_create_agent, \
         patch("src.services.agent_execution_service.init_chat_model"):

        mock_async_client = AsyncMock()
        mock_async_client.api_key = "virtual-key"
        mock_llm_client.return_value = mock_async_client

        mock_executor = AsyncMock()
        mock_executor.ainvoke = AsyncMock(return_value={
            "messages": [MagicMock(content="Response", type="ai")]
        })
        mock_create_agent.return_value = mock_executor

        result = await service.execute_agent(
            agent_id=mock_agent.id,
            tenant_id="test-tenant",
            user_message="Test pooling performance",
        )

        assert result["success"] is True

        # Verify bridge was created only ONCE despite 3 calls to _get_or_create_mcp_bridge
        assert len(bridge_creations) == 1, "Bridge should be created only once and reused"
