"""
MCP Bridge Connection Pooling

Manages lifecycle of MCP bridge instances for agent execution contexts.
Implements connection pooling to reuse MCP client connections within
the same execution context, improving performance and resource efficiency.

Pattern: Module-level dictionary pool with execution_context_id as key.
Each execution context gets its own bridge instance that is reused for
multiple tool conversions, then cleaned up in finally block.

References:
- Story 11.2.3: MCP Connection Pooling and Caching
- Story 12.7: File Size Refactoring (extracted from agent_execution_service.py)
- Story 12.8: OpenTelemetry Tracing (AC3)

Usage:
    # Get or create bridge
    bridge = await get_or_create_mcp_bridge(
        execution_context_id="uuid-123",
        mcp_servers=[server1, server2]
    )

    # Use bridge for tool conversion...

    # Cleanup when done
    await cleanup_mcp_bridge("uuid-123")
"""

import logging
from typing import Any, Dict, List

from opentelemetry import trace

from src.database.models import MCPServer
from src.services.mcp_tool_bridge import MCPToolBridge

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Module-level bridge pool for connection reuse within execution contexts
# Key: execution_context_id (str)
# Value: MCPToolBridge instance
_mcp_bridge_pool: Dict[str, MCPToolBridge] = {}


async def get_or_create_mcp_bridge(
    execution_context_id: str,
    mcp_servers: List[MCPServer],
) -> MCPToolBridge:
    """
    Get or create MCP bridge from pool for execution context.

    Implements connection pooling by reusing MCP bridge instances within
    the same execution context (Story 11.2.3). If bridge exists in pool,
    returns cached instance. Otherwise creates new bridge and adds to pool.

    Story 12.8 AC3: Adds OpenTelemetry span for pool operations with cache hit/miss tracking.

    Args:
        execution_context_id: Unique identifier for this execution
        mcp_servers: List of active MCP server configurations

    Returns:
        MCPToolBridge instance (new or from pool)

    Example:
        >>> servers = [mcp_server_1, mcp_server_2]
        >>> bridge = await get_or_create_mcp_bridge("uuid-123", servers)
        >>> # Bridge is now cached for "uuid-123" context
    """
    global _mcp_bridge_pool

    # Story 12.8 AC3: Parent span for pool operation
    with tracer.start_as_current_span("mcp.pool.get_or_create") as pool_span:
        pool_span.set_attribute("mcp.execution_context_id", execution_context_id)
        pool_span.set_attribute("mcp.server_count", len(mcp_servers))
        pool_span.set_attribute("mcp.pool_size_before", len(_mcp_bridge_pool))

        # Check if bridge exists in pool for this execution context
        if execution_context_id in _mcp_bridge_pool:
            # Story 12.8 AC3: Cache hit - reuse existing bridge
            pool_span.set_attribute("mcp.pool_hit", True)
            pool_span.set_attribute("mcp.pool_operation", "reuse")

            logger.debug(
                "Reusing MCP bridge from pool",
                extra={"execution_context_id": execution_context_id},
            )
            return _mcp_bridge_pool[execution_context_id]

        # Story 12.8 AC3: Cache miss - create new bridge
        pool_span.set_attribute("mcp.pool_hit", False)
        pool_span.set_attribute("mcp.pool_operation", "create")

        # Create new bridge and add to pool
        logger.debug(
            "Creating new MCP bridge",
            extra={
                "execution_context_id": execution_context_id,
                "server_count": len(mcp_servers),
            },
        )

        # Story 12.8 AC3: Child span for bridge creation
        with tracer.start_as_current_span("mcp.pool.create_bridge") as create_span:
            create_span.set_attribute("mcp.execution_context_id", execution_context_id)
            create_span.set_attribute("mcp.server_count", len(mcp_servers))

            bridge = MCPToolBridge(mcp_servers)
            _mcp_bridge_pool[execution_context_id] = bridge

        pool_span.set_attribute("mcp.pool_size_after", len(_mcp_bridge_pool))

        logger.info(
            "MCP bridge added to pool",
            extra={
                "execution_context_id": execution_context_id,
                "pool_size": len(_mcp_bridge_pool),
            },
        )

        return bridge


async def cleanup_mcp_bridge(execution_context_id: str) -> None:
    """
    Cleanup MCP bridge for execution context.

    Removes bridge from pool and calls cleanup() to close all MCP server
    connections. Called in finally block after agent execution completes.

    This function is idempotent - safe to call multiple times for same context.
    If bridge doesn't exist in pool, function returns silently.

    Story 12.8 AC3: Adds OpenTelemetry span for connection cleanup with success/failure tracking.

    Args:
        execution_context_id: Execution context to clean up

    Example:
        >>> try:
        >>>     bridge = await get_or_create_mcp_bridge("uuid-123", servers)
        >>>     # Use bridge...
        >>> finally:
        >>>     await cleanup_mcp_bridge("uuid-123")
    """
    global _mcp_bridge_pool

    if execution_context_id not in _mcp_bridge_pool:
        return

    # Story 12.8 AC3: Parent span for cleanup operation
    with tracer.start_as_current_span("mcp.pool.cleanup") as cleanup_span:
        cleanup_span.set_attribute("mcp.execution_context_id", execution_context_id)
        cleanup_span.set_attribute("mcp.pool_size_before", len(_mcp_bridge_pool))

        bridge = _mcp_bridge_pool[execution_context_id]

        try:
            # Story 12.8 AC3: Child span for bridge cleanup (close connections)
            with tracer.start_as_current_span("mcp.pool.close_connections") as close_span:
                close_span.set_attribute("mcp.execution_context_id", execution_context_id)

                await bridge.cleanup()

                close_span.set_attribute("mcp.cleanup_success", True)

            cleanup_span.set_attribute("mcp.cleanup_success", True)

            logger.info(
                "MCP bridge cleaned up successfully",
                extra={"execution_context_id": execution_context_id},
            )
        except Exception as e:
            # Story 12.8 AC3: Track cleanup failure
            cleanup_span.set_attribute("mcp.cleanup_success", False)
            cleanup_span.set_attribute("error.type", type(e).__name__)
            cleanup_span.set_attribute("error.message", str(e))

            logger.error(
                f"Error cleaning up MCP bridge: {e}",
                extra={
                    "execution_context_id": execution_context_id,
                    "error_type": type(e).__name__,
                },
            )
        finally:
            # ALWAYS remove from pool, even if cleanup failed
            del _mcp_bridge_pool[execution_context_id]

            cleanup_span.set_attribute("mcp.pool_size_after", len(_mcp_bridge_pool))

            logger.info(
                "MCP bridge removed from pool",
                extra={
                    "execution_context_id": execution_context_id,
                    "remaining_pool_size": len(_mcp_bridge_pool),
                },
            )


def get_pool_size() -> int:
    """
    Get current size of MCP bridge pool.

    Utility function for monitoring and debugging pool state.

    Returns:
        int: Number of bridges currently in pool

    Example:
        >>> size = get_pool_size()
        >>> logger.info(f"Current pool size: {size}")
    """
    return len(_mcp_bridge_pool)
