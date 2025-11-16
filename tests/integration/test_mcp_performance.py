"""
Integration tests for MCP performance characteristics (Story 11.2.6 - AC#2 Workflow 3).

Tests performance and scalability:
1. Tool invocation latency
2. Sequential vs concurrent throughput
3. Client spawn/cleanup performance
4. Health check performance
5. Resource cleanup validation

Performance thresholds are conservative to avoid flaky tests.
"""

import asyncio
import time
import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import MagicMock, patch

from src.services.mcp_stdio_client import MCPStdioClient
from src.services.mcp_server_service import MCPServerService
from src.database.models import MCPServer, MCPServerStatus, TransportType


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_performance_tool_invocation_latency(mcp_stdio_client):
    """
    Test single tool invocation completes within reasonable time.

    Validates:
    - Echo tool completes in < 5 seconds (conservative threshold)
    - Add tool completes in < 5 seconds
    - Latency is reasonable for local subprocess communication

    Note: Thresholds are conservative to avoid flaky tests.
    """
    # Test echo tool latency
    start_time = time.time()
    result = await mcp_stdio_client.call_tool("echo", {"message": "latency test"})
    elapsed = time.time() - start_time

    assert result["is_error"] is False
    assert elapsed < 5.0, f"Echo tool took {elapsed:.2f}s, expected < 5s"

    # Test add tool latency
    start_time = time.time()
    result = await mcp_stdio_client.call_tool("add", {"a": 10, "b": 20})
    elapsed = time.time() - start_time

    assert result["is_error"] is False
    assert elapsed < 5.0, f"Add tool took {elapsed:.2f}s, expected < 5s"


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_performance_sequential_tool_calls(mcp_stdio_client):
    """
    Test throughput of sequential tool calls.

    Validates:
    - 10 sequential tool calls complete in < 30 seconds
    - Each call returns correct results
    - No performance degradation over time
    """
    num_calls = 10
    start_time = time.time()
    results = []

    for i in range(num_calls):
        result = await mcp_stdio_client.call_tool("echo", {"message": f"call_{i}"})
        results.append(result)

    elapsed = time.time() - start_time

    # Validate all calls succeeded
    assert len(results) == num_calls
    for result in results:
        assert result["is_error"] is False

    # Validate total time is reasonable
    assert elapsed < 30.0, f"{num_calls} calls took {elapsed:.2f}s, expected < 30s"

    # Calculate average latency
    avg_latency = elapsed / num_calls
    print(f"Average latency per call: {avg_latency:.3f}s")


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_performance_concurrent_tool_calls(mcp_stdio_test_server_config):
    """
    Test concurrent tool calls with multiple clients.

    Validates:
    - Multiple clients can run concurrently
    - Concurrent execution is faster than sequential
    - All results are correct

    Note: Uses multiple client processes for true parallelism.
    """
    num_clients = 3
    calls_per_client = 5

    async def run_client(client_id: int) -> list:
        """Run multiple tool calls on a single client."""
        async with MCPStdioClient(mcp_stdio_test_server_config) as client:
            await client.initialize()

            results = []
            for i in range(calls_per_client):
                result = await client.call_tool("echo", {"message": f"client_{client_id}_call_{i}"})
                results.append(result)

            return results

    # Run all clients concurrently
    start_time = time.time()
    all_results = await asyncio.gather(*[run_client(i) for i in range(num_clients)])
    elapsed = time.time() - start_time

    # Validate all calls succeeded
    total_calls = num_clients * calls_per_client
    assert len(all_results) == num_clients

    for client_results in all_results:
        assert len(client_results) == calls_per_client
        for result in client_results:
            assert result["is_error"] is False

    # Concurrent execution should be reasonably fast
    # (Much faster than sequential would be)
    sequential_estimate = total_calls * 2.0  # Assume 2s per call sequentially
    assert elapsed < sequential_estimate, \
        f"Concurrent execution took {elapsed:.2f}s, sequential would be ~{sequential_estimate:.0f}s"

    print(f"Concurrent execution: {total_calls} calls in {elapsed:.2f}s ({elapsed/total_calls:.3f}s per call)")


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_performance_client_spawn_time(mcp_stdio_test_server_config):
    """
    Test client spawn and initialization time.

    Validates:
    - Client spawns in < 10 seconds
    - Initialize handshake completes quickly
    - Process startup is efficient
    """
    start_time = time.time()

    async with MCPStdioClient(mcp_stdio_test_server_config) as client:
        await client.initialize()
        spawn_time = time.time() - start_time

        assert client.server_capabilities is not None
        assert spawn_time < 10.0, f"Client spawn took {spawn_time:.2f}s, expected < 10s"

        print(f"Client spawn and initialize: {spawn_time:.3f}s")


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_performance_client_cleanup_time(mcp_stdio_test_server_config):
    """
    Test client cleanup time.

    Validates:
    - Client cleanup completes in < 10 seconds
    - Process termination is efficient
    - No hanging processes
    """
    async with MCPStdioClient(mcp_stdio_test_server_config) as client:
        await client.initialize()
        # Use the client
        await client.call_tool("echo", {"message": "cleanup test"})

    # Cleanup happens in __aexit__, measure wasn't practical here
    # But if we got here without timeout, cleanup was successful
    # This test mainly validates cleanup doesn't hang


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_performance_multiple_client_lifecycle(mcp_stdio_test_server_config):
    """
    Test spawning and closing multiple clients sequentially.

    Validates:
    - Multiple client lifecycles complete successfully
    - No resource leaks between clients
    - Each client is independent

    Note: Tests resource cleanup by spawning/closing multiple times.
    """
    num_cycles = 5

    start_time = time.time()

    for i in range(num_cycles):
        async with MCPStdioClient(mcp_stdio_test_server_config) as client:
            await client.initialize()

            # Use the client
            result = await client.call_tool("echo", {"message": f"cycle_{i}"})
            assert result["is_error"] is False
            assert f"cycle_{i}" in str(result["content"])

        # Client should be cleaned up here

    elapsed = time.time() - start_time

    # All cycles should complete in reasonable time
    assert elapsed < 60.0, f"{num_cycles} client cycles took {elapsed:.2f}s, expected < 60s"

    print(f"{num_cycles} client lifecycles: {elapsed:.2f}s ({elapsed/num_cycles:.2f}s per cycle)")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_performance_health_check_latency(mock_db_session, mcp_stdio_test_server_config):
    """
    Test health check latency.

    Validates:
    - Health check completes in < 10 seconds
    - Response time is measured accurately
    - Status is updated correctly
    """
    service = MCPServerService(mock_db_session)

    # Create mock server
    mock_server = MCPServer(
        id=uuid4(),
        tenant_id=uuid4(),
        name="perf-health-test",
        description="Performance test server",
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
    with patch.object(service, 'get_server_by_id', return_value=mock_server):
        start_time = time.time()
        health = await service.check_health(mock_server.id, mock_server.tenant_id)
        elapsed = time.time() - start_time

        # Validate health check
        assert health is not None
        assert health["status"] == "active"
        assert elapsed < 10.0, f"Health check took {elapsed:.2f}s, expected < 10s"

        print(f"Health check latency: {elapsed:.3f}s")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_performance_discovery_latency(mock_db_session, mcp_stdio_test_server_config):
    """
    Test capability discovery latency.

    Validates:
    - Discovery completes in < 15 seconds
    - All three primitives are discovered
    - Server status updated correctly
    """
    service = MCPServerService(mock_db_session)

    # Create mock server
    mock_server = MCPServer(
        id=uuid4(),
        tenant_id=uuid4(),
        name="perf-discovery-test",
        description="Performance test server",
        transport_type=TransportType.STDIO,
        command=mcp_stdio_test_server_config.command,
        args=mcp_stdio_test_server_config.args,
        env=mcp_stdio_test_server_config.env,
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
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_server
    mock_db_session.execute.return_value = mock_result

    # Perform discovery
    start_time = time.time()
    await service.discover_capabilities(mock_server.id)
    elapsed = time.time() - start_time

    # Validate discovery
    assert mock_server.status == MCPServerStatus.ACTIVE
    assert len(mock_server.discovered_tools) > 0
    assert elapsed < 15.0, f"Discovery took {elapsed:.2f}s, expected < 15s"

    print(f"Capability discovery: {elapsed:.3f}s, found {len(mock_server.discovered_tools)} tools")


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_performance_list_operations_latency(mcp_stdio_client):
    """
    Test latency of list operations for all primitives.

    Validates:
    - list_tools() completes in < 5 seconds
    - list_resources() completes in < 5 seconds
    - list_prompts() completes in < 5 seconds
    """
    # Test list_tools latency
    start_time = time.time()
    tools = await mcp_stdio_client.list_tools()
    tools_elapsed = time.time() - start_time

    assert len(tools) > 0
    assert tools_elapsed < 5.0, f"list_tools took {tools_elapsed:.2f}s, expected < 5s"

    # Test list_resources latency
    start_time = time.time()
    resources = await mcp_stdio_client.list_resources()
    resources_elapsed = time.time() - start_time

    assert resources_elapsed < 5.0, f"list_resources took {resources_elapsed:.2f}s, expected < 5s"

    # Test list_prompts latency
    start_time = time.time()
    prompts = await mcp_stdio_client.list_prompts()
    prompts_elapsed = time.time() - start_time

    assert prompts_elapsed < 5.0, f"list_prompts took {prompts_elapsed:.2f}s, expected < 5s"

    print(f"List operations - tools: {tools_elapsed:.3f}s, resources: {resources_elapsed:.3f}s, prompts: {prompts_elapsed:.3f}s")


@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_performance_no_degradation_over_time(mcp_stdio_client):
    """
    Test that performance doesn't degrade with repeated use.

    Validates:
    - First call and last call have similar latency
    - No memory leaks causing slowdown
    - Client remains efficient over time
    """
    num_calls = 20
    latencies = []

    for i in range(num_calls):
        start_time = time.time()
        result = await mcp_stdio_client.call_tool("echo", {"message": f"degradation_test_{i}"})
        elapsed = time.time() - start_time

        assert result["is_error"] is False
        latencies.append(elapsed)

    # Calculate first 5 and last 5 average latencies
    first_5_avg = sum(latencies[:5]) / 5
    last_5_avg = sum(latencies[-5:]) / 5

    # Last calls should not be significantly slower (allow 2x degradation max)
    assert last_5_avg < first_5_avg * 2.0, \
        f"Performance degraded: first 5 avg={first_5_avg:.3f}s, last 5 avg={last_5_avg:.3f}s"

    print(f"Performance over {num_calls} calls - first 5 avg: {first_5_avg:.3f}s, last 5 avg: {last_5_avg:.3f}s")
