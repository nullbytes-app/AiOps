"""
Tool Conversion for Agent Execution

Converts unified tools (OpenAPI + MCP) to LangChain-compatible format.
Handles MCP tool conversion via MCPToolBridge with connection pooling.

Separation of Concerns:
- This module: Tool format conversion logic
- mcp_bridge_pooler: Bridge lifecycle management
- agent_execution_service: Overall orchestration

References:
- Story 11.1.5: Unified Tool Discovery Service
- Story 11.1.7: MCP Tool Invocation in Agent Execution
- Story 12.7: File Size Refactoring (extracted from agent_execution_service.py)

Usage:
    tools = await convert_tools_to_langchain(
        unified_tools=[{"source_type": "mcp", ...}],
        mcp_servers=[server1, server2],
        execution_context_id="uuid-123"
    )
"""

import logging
from typing import Any, Dict, List

from src.database.models import MCPServer
from src.services.agent_execution.mcp_bridge_pooler import get_or_create_mcp_bridge

logger = logging.getLogger(__name__)


class AgentExecutionError(Exception):
    """Exception raised when agent execution fails."""

    pass


async def convert_tools_to_langchain(
    unified_tools: List[Dict[str, Any]],
    mcp_servers: List[MCPServer],
    execution_context_id: str,
) -> List[Any]:
    """
    Convert unified tools (OpenAPI + MCP) to LangChain-compatible format.

    Handles both OpenAPI tools (from agent_tools table) and MCP tools
    (from assigned_mcp_tools JSON field). Uses MCP bridge pooling to reuse
    client instances within same execution context (Story 11.2.3).

    Args:
        unified_tools: List of tool dicts with source_type discriminator
        mcp_servers: List of active MCP server configurations
        execution_context_id: Execution context ID for bridge pooling

    Returns:
        List of LangChain BaseTool instances

    Raises:
        AgentExecutionError: If tool conversion fails

    Example:
        >>> unified_tools = [
        >>>     {"source_type": "openapi", "name": "github_api", ...},
        >>>     {"source_type": "mcp", "server_name": "filesystem", ...}
        >>> ]
        >>> tools = await convert_tools_to_langchain(
        >>>     unified_tools=unified_tools,
        >>>     mcp_servers=[fs_server],
        >>>     execution_context_id="uuid-123"
        >>> )
    """
    langchain_tools: List[Any] = []

    # Separate tools by source type
    openapi_tools = [t for t in unified_tools if t.get("source_type") == "openapi"]
    mcp_tools = [t for t in unified_tools if t.get("source_type") == "mcp"]

    # NOTE: OpenAPI tool conversion is handled by UnifiedToolService
    # For this implementation, we focus on MCP tools per Story 11.1.7
    if openapi_tools:
        logger.warning(
            f"OpenAPI tools found but conversion not yet implemented: {len(openapi_tools)} tools",
            extra={"openapi_tool_count": len(openapi_tools)},
        )
        # TODO: Implement OpenAPI tool conversion in future story

    # Convert MCP tools using MCPToolBridge (with pooling - Story 11.2.3)
    if mcp_tools:
        logger.debug(f"Converting {len(mcp_tools)} MCP tools")

        try:
            if not mcp_servers:
                logger.warning("No active MCP servers provided for tool conversion")
            else:
                # Get or create MCP bridge from pool (Story 11.2.3)
                bridge = await get_or_create_mcp_bridge(
                    execution_context_id=execution_context_id,
                    mcp_servers=mcp_servers,
                )

                # Convert MCP tools to LangChain tools
                mcp_langchain_tools = await bridge.get_langchain_tools(mcp_tools)
                langchain_tools.extend(mcp_langchain_tools)

                # NOTE: Bridge cleanup is handled by caller's finally block
                # This allows bridge reuse across multiple tool conversions
                # in the same execution context

        except Exception as e:
            logger.error(
                f"Failed to convert MCP tools: {e}",
                extra={"error_type": type(e).__name__},
            )
            # Don't fail execution - continue with OpenAPI tools only
            raise AgentExecutionError(f"MCP tool conversion failed: {e}")

    logger.info(
        f"Converted {len(langchain_tools)} total tools",
        extra={
            "openapi_count": len(openapi_tools),
            "mcp_count": len(mcp_tools),
            "total_count": len(langchain_tools),
        },
    )

    return langchain_tools
