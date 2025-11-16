"""
MCP Tool Bridge Service

Converts MCP primitives (tools, resources, prompts) to LangChain-compatible tools
for use in LangGraph agent execution workflows.

Implements:
- Tool conversion using langchain-mcp-adapters for primitive_type="tool"
- Custom wrappers for resources (session.read_resource) and prompts (session.get_prompt)
- Client lifecycle management (spawn, reuse, cleanup)
- Error handling with graceful degradation
- 30-second timeout enforcement
- OpenTelemetry distributed tracing (Story 12.8)

References:
- Story 11.1.7: MCP Tool Invocation in Agent Execution
- Story 12.8: OpenTelemetry Tracing Implementation
- Context7 MCP Research 2025-11-09: LangChain MCP Adapters patterns
"""

import asyncio
import logging
from typing import Any
from uuid import UUID

from langchain_core.tools import BaseTool, StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient  # type: ignore[import-untyped]
from langchain_mcp_adapters.tools import load_mcp_tools  # type: ignore[import-untyped]
from opentelemetry import trace

from src.database.models import MCPServer

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class MCPToolBridge:
    """
    Bridge between MCP servers and LangChain tools for agent execution.

    Manages MCP client lifecycle (spawn, reuse, cleanup) and converts MCP primitives
    to LangChain BaseTool format using langchain-mcp-adapters for tools and custom
    wrappers for resources/prompts.

    Example usage:
        bridge = MCPToolBridge(mcp_servers)
        tools = await bridge.get_langchain_tools(mcp_tool_assignments)
        # Use tools with LangGraph agent
        await bridge.cleanup()
    """

    def __init__(self, mcp_servers: list[MCPServer]):
        """
        Initialize MCP Tool Bridge with MCP server configurations.

        Args:
            mcp_servers: List of active MCP server records from database.
        """
        self.servers = mcp_servers
        self.client: MultiServerMCPClient | None = None
        self._initialized = False
        # BUGFIX (Story 11.1.7): Store active sessions to keep them alive during agent execution
        # Reason: langchain_mcp_adapters tools hold references to sessions, which must remain
        # open for the entire agent execution lifecycle, not just during tool loading
        self._sessions: dict[str, Any] = {}  # Key: server_id, Value: session context manager

    async def _initialize_client(self) -> None:
        """
        Initialize MultiServerMCPClient for all configured MCP servers.

        Creates client with stdio transport configurations for each server.
        Handles client initialization errors gracefully.

        Raises:
            RuntimeError: If client initialization fails.
        """
        if self._initialized and self.client:
            return

        server_configs: dict[str, dict[str, Any]] = {}
        for server in self.servers:
            server_configs[str(server.id)] = {
                "transport": "stdio",
                "command": server.command,
                "args": server.args or [],
                "env": server.env or {},
            }

        try:
            # Note: Celery LoggingProxy workaround is handled by get_langchain_tools()
            # which wraps the entire method execution (including session() calls)
            self.client = MultiServerMCPClient(server_configs)
            self._initialized = True
            logger.info(
                f"MCP Tool Bridge initialized with {len(self.servers)} servers",
                extra={"server_count": len(self.servers)},
            )
        except Exception as e:
            logger.error(
                f"Failed to initialize MCP client: {e}",
                extra={"error_type": type(e).__name__, "server_count": len(self.servers)},
            )
            raise RuntimeError(f"MCP client initialization failed: {e}") from e

    async def get_langchain_tools(
        self, mcp_tool_assignments: list[dict[str, Any]]
    ) -> list[BaseTool]:
        """
        Convert MCP tool assignments to LangChain-compatible tools.

        Loads tools from MCP servers using langchain-mcp-adapters for primitive_type="tool"
        and creates custom wrappers for resources and prompts.

        Args:
            mcp_tool_assignments: List of MCP tool assignment dicts from agent.assigned_mcp_tools.
                                  Each dict contains: name, mcp_server_id, mcp_primitive_type, etc.

        Returns:
            List of LangChain BaseTool instances ready for agent binding.

        Raises:
            RuntimeError: If client initialization fails.
        """
        # BUGFIX (Story 11.1.7): Celery wraps sys.stdout/sys.stderr in LoggingProxy
        # objects which don't have fileno() method needed by asyncio subprocess.
        # Keep real file descriptors active for ENTIRE get_langchain_tools() execution
        # because subprocess spawning happens in client.session(), not just in __init__.
        # Reason: langchain_mcp_adapters spawns subprocesses when session() is called
        import sys

        # Check if we're in Celery environment
        has_fileno = hasattr(sys.stdout, "fileno")
        is_celery = not has_fileno

        if is_celery:
            # Save Celery's LoggingProxy wrappers
            original_stdout = sys.stdout
            original_stderr = sys.stderr

            # Restore real file descriptors for entire method execution
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__

            logger.info(
                "Celery environment detected in get_langchain_tools(), "
                f"using real stdout/stderr (type: {type(sys.stdout).__name__})"
            )

        try:
            # Story 12.8 AC1: Parent span for entire MCP tool invocation workflow
            with tracer.start_as_current_span("mcp.tool.invocation") as parent_span:
                parent_span.set_attribute("mcp.server_count", len(self.servers))
                parent_span.set_attribute("mcp.assignment_count", len(mcp_tool_assignments))

                await self._initialize_client()

            if not self.client:
                logger.error("MCP client not initialized")
                parent_span.set_attribute("mcp.error", "client_not_initialized")
                return []

            langchain_tools: list[BaseTool] = []

            # Group assignments by server for efficient loading
            # BUGFIX: Normalize mcp_server_id to UUID type for consistent lookup
            # Reason: mcp_server_id from DB may be str, but server.id is UUID
            tools_by_server: dict[UUID, list[dict[str, Any]]] = {}
            for assignment in mcp_tool_assignments:
                server_id = assignment.get("mcp_server_id")
                if server_id:
                    # Convert to UUID if it's a string to ensure type consistency
                    if isinstance(server_id, str):
                        server_id = UUID(server_id)
                    tools_by_server.setdefault(server_id, []).append(assignment)

            # Load tools from each MCP server
            for server in self.servers:
                server_assignments: list[dict[str, Any]] = tools_by_server.get(server.id, [])  # type: ignore[call-overload]
                if not server_assignments:
                    continue

                # Story 12.8 AC1: Child span for loading tools from one server
                with tracer.start_as_current_span("mcp.bridge.load_tools") as load_span:
                    load_span.set_attribute("mcp.server_id", str(server.id))
                    load_span.set_attribute("mcp.server_name", server.name)
                    load_span.set_attribute("mcp.transport_type", "stdio")  # Currently only stdio supported
                    load_span.set_attribute("mcp.assignment_count", len(server_assignments))

                    try:
                        # BUGFIX (Story 11.1.7): Manually manage session lifecycle to keep it alive
                        # Reason: langchain_mcp_adapters tools reference the session, which must remain
                        # open for the entire agent execution. Using 'async with' would close it when
                        # get_langchain_tools() returns, causing ClosedResourceError during tool execution.

                        server_id_str = str(server.id)

                        # Manually enter the session context manager
                        session_cm = self.client.session(server_id_str)
                        session = await session_cm.__aenter__()

                        # Store session for later cleanup (in cleanup() method)
                        self._sessions[server_id_str] = session_cm

                        logger.info(
                            f"MCP session opened for server (will remain open until cleanup)",
                            extra={"server_id": server_id_str, "server_name": server.name},
                        )

                        # Story 12.8 AC1: Span for MCP client connection
                        with tracer.start_as_current_span("mcp.client.connect") as connect_span:
                            connect_span.set_attribute("mcp.server_id", str(server.id))
                            connect_span.set_attribute("mcp.server_name", server.name)
                            # Connection happens in context manager, so we just track it

                        # Story 12.8 AC1: Span for listing tools from server
                        with tracer.start_as_current_span("mcp.client.list_tools") as list_span:
                            list_span.set_attribute("mcp.server_id", str(server.id))
                            # Load all tools from server (primitive_type="tool")
                            server_tools = await asyncio.wait_for(load_mcp_tools(session), timeout=30.0)
                            list_span.set_attribute("mcp.tools_discovered", len(server_tools))

                        # Filter tools by assignments (only include assigned tools)
                        assigned_tool_names = {
                            a["name"]
                            for a in server_assignments
                            if a.get("mcp_primitive_type") == "tool"
                        }
                        filtered_tools = [t for t in server_tools if t.name in assigned_tool_names]

                        # Story 12.8 AC1: Span for validating filtered tools
                        with tracer.start_as_current_span("mcp.tool.validate") as validate_span:
                            validate_span.set_attribute("mcp.tools_filtered", len(filtered_tools))
                            validate_span.set_attribute("mcp.tools_assigned", len(assigned_tool_names))

                        langchain_tools.extend(filtered_tools)

                        logger.info(
                            f"Loaded {len(filtered_tools)} tools from MCP server",
                            extra={
                                "server_id": str(server.id),
                                "server_name": server.name,
                                "tool_count": len(filtered_tools),
                            },
                        )

                        # Create custom wrappers for resources and prompts
                        for assignment in server_assignments:
                            primitive_type = assignment.get("mcp_primitive_type")

                            if primitive_type == "resource":
                                resource_tool = self._create_resource_wrapper(
                                    server, assignment, session
                                )
                                langchain_tools.append(resource_tool)

                            elif primitive_type == "prompt":
                                prompt_tool = self._create_prompt_wrapper(server, assignment, session)
                                langchain_tools.append(prompt_tool)

                        load_span.set_attribute("mcp.tools_loaded", len(filtered_tools))

                    except asyncio.TimeoutError:
                        # Story 12.8 AC1: Error handling span
                        with tracer.start_as_current_span("mcp.error.handling") as error_span:
                            error_span.set_attribute("error.type", "TimeoutError")
                            error_span.set_attribute("error.message", "MCP server timeout >30s")
                            error_span.set_attribute("mcp.server_id", str(server.id))
                            error_span.set_attribute("mcp.server_name", server.name)

                        logger.error(
                            f"Timeout loading tools from MCP server (>30s)",
                            extra={
                                "server_id": str(server.id),
                                "server_name": server.name,
                                "timeout_seconds": 30,
                            },
                        )
                        load_span.set_attribute("mcp.error", "timeout")

                    except Exception as e:
                        # Story 12.8 AC1: Error handling span
                        with tracer.start_as_current_span("mcp.error.handling") as error_span:
                            error_span.set_attribute("error.type", type(e).__name__)
                            error_span.set_attribute("error.message", str(e))
                            error_span.set_attribute("mcp.server_id", str(server.id))
                            error_span.set_attribute("mcp.server_name", server.name)

                        logger.error(
                            f"Failed to load tools from MCP server: {e}",
                            extra={
                                "server_id": str(server.id),
                                "server_name": server.name,
                                "error_type": type(e).__name__,
                            },
                        )
                        load_span.set_attribute("mcp.error", type(e).__name__)

                logger.info(
                    f"MCP Tool Bridge created {len(langchain_tools)} LangChain tools",
                    extra={"total_tool_count": len(langchain_tools)},
                )

                parent_span.set_attribute("mcp.total_tools_loaded", len(langchain_tools))

                return langchain_tools
        finally:
            # Restore LoggingProxy wrappers if we changed them
            if is_celery:
                sys.stdout = original_stdout
                sys.stderr = original_stderr
                logger.info("Restored Celery LoggingProxy wrappers after get_langchain_tools()")

    def _create_resource_wrapper(
        self, server: MCPServer, assignment: dict[str, Any], session: Any
    ) -> BaseTool:
        """
        Create custom LangChain tool wrapper for MCP resource.

        Args:
            server: MCP server configuration.
            assignment: Tool assignment dict with resource metadata.
            session: Active MCP client session for this server.

        Returns:
            LangChain BaseTool wrapping session.read_resource(uri).
        """
        resource_name = assignment.get("name", "unnamed_resource")
        resource_description = assignment.get(
            "description", f"Read MCP resource from {server.name}"
        )

        async def read_mcp_resource(uri: str) -> str:
            """Read an MCP resource by URI."""
            # Story 12.8 AC1: Span for MCP resource tool execution
            with tracer.start_as_current_span("mcp.tool.execute") as exec_span:
                exec_span.set_attribute("mcp.tool_name", resource_name)
                exec_span.set_attribute("mcp.primitive_type", "resource")
                exec_span.set_attribute("mcp.server_id", str(server.id))
                exec_span.set_attribute("mcp.server_name", server.name)
                exec_span.set_attribute("mcp.resource_uri", uri)

                try:
                    # Story 12.8 AC1: Span for actual MCP call
                    with tracer.start_as_current_span("mcp.client.call_tool") as call_span:
                        call_span.set_attribute("mcp.operation", "read_resource")
                        call_span.set_attribute("mcp.transport_type", "stdio")

                        result = await asyncio.wait_for(session.read_resource(uri), timeout=30.0)

                    # MCP returns dict with 'contents' array
                    contents = result.get("contents", [])
                    if contents and len(contents) > 0:
                        # Extract text content from first item
                        first_content = contents[0]
                        if isinstance(first_content, dict):
                            response = str(first_content.get("text", str(result)))
                        else:
                            response = str(result)
                    else:
                        response = str(result)

                    exec_span.set_attribute("mcp.execution_success", True)
                    return response

                except asyncio.TimeoutError:
                    error_msg = f"MCP resource read timeout (>30s): {uri}"
                    logger.error(error_msg, extra={"uri": uri, "server_name": server.name})

                    exec_span.set_attribute("mcp.execution_success", False)
                    exec_span.set_attribute("error.type", "TimeoutError")
                    exec_span.set_attribute("error.message", error_msg)

                    return f"Error: {error_msg}"

                except Exception as e:
                    error_msg = f"MCP resource read failed: {e}"
                    logger.error(
                        error_msg,
                        extra={
                            "uri": uri,
                            "server_name": server.name,
                            "error_type": type(e).__name__,
                        },
                    )

                    exec_span.set_attribute("mcp.execution_success", False)
                    exec_span.set_attribute("error.type", type(e).__name__)
                    exec_span.set_attribute("error.message", str(e))

                    return f"Error: {error_msg}"

        # Create StructuredTool with custom name and description
        return StructuredTool.from_function(
            coroutine=read_mcp_resource,
            name=resource_name,
            description=resource_description,
        )

    def _create_prompt_wrapper(
        self, server: MCPServer, assignment: dict[str, Any], session: Any
    ) -> BaseTool:
        """
        Create custom LangChain tool wrapper for MCP prompt.

        Args:
            server: MCP server configuration.
            assignment: Tool assignment dict with prompt metadata.
            session: Active MCP client session for this server.

        Returns:
            LangChain BaseTool wrapping session.get_prompt(name, arguments).
        """
        prompt_name = assignment.get("name", "unnamed_prompt")
        prompt_description = assignment.get("description", f"Get MCP prompt from {server.name}")

        async def get_mcp_prompt(arguments: dict[str, Any] | None = None) -> str:
            """Get an MCP prompt with optional arguments."""
            # Story 12.8 AC1: Span for MCP prompt tool execution
            with tracer.start_as_current_span("mcp.tool.execute") as exec_span:
                exec_span.set_attribute("mcp.tool_name", prompt_name)
                exec_span.set_attribute("mcp.primitive_type", "prompt")
                exec_span.set_attribute("mcp.server_id", str(server.id))
                exec_span.set_attribute("mcp.server_name", server.name)

                try:
                    # Story 12.8 AC1: Span for actual MCP call
                    with tracer.start_as_current_span("mcp.client.call_tool") as call_span:
                        call_span.set_attribute("mcp.operation", "get_prompt")
                        call_span.set_attribute("mcp.transport_type", "stdio")

                        result = await asyncio.wait_for(
                            session.get_prompt(prompt_name, arguments or {}), timeout=30.0
                        )

                    # MCP returns dict with 'messages' array
                    messages = result.get("messages", [])
                    if messages and len(messages) > 0:
                        # Extract content from first message
                        first_message = messages[0]
                        if isinstance(first_message, dict):
                            response = str(first_message.get("content", str(result)))
                        else:
                            response = str(result)
                    else:
                        response = str(result)

                    exec_span.set_attribute("mcp.execution_success", True)
                    return response

                except asyncio.TimeoutError:
                    error_msg = f"MCP prompt get timeout (>30s): {prompt_name}"
                    logger.error(
                        error_msg, extra={"prompt_name": prompt_name, "server_name": server.name}
                    )

                    exec_span.set_attribute("mcp.execution_success", False)
                    exec_span.set_attribute("error.type", "TimeoutError")
                    exec_span.set_attribute("error.message", error_msg)

                    return f"Error: {error_msg}"

                except Exception as e:
                    error_msg = f"MCP prompt get failed: {e}"
                    logger.error(
                        error_msg,
                        extra={
                            "prompt_name": prompt_name,
                            "server_name": server.name,
                            "error_type": type(e).__name__,
                        },
                    )

                    exec_span.set_attribute("mcp.execution_success", False)
                    exec_span.set_attribute("error.type", type(e).__name__)
                    exec_span.set_attribute("error.message", str(e))

                    return f"Error: {error_msg}"

        # Create StructuredTool with custom name and description
        return StructuredTool.from_function(
            coroutine=get_mcp_prompt,
            name=prompt_name,
            description=prompt_description,
        )

    async def cleanup(self) -> None:
        """
        Cleanup MCP client resources.

        Closes all active MCP server connections and subprocess handles.
        Should be called when agent execution completes.

        BUGFIX (Story 11.1.7): Now properly closes all manually-managed sessions
        that were opened in get_langchain_tools() to keep tools functional during
        agent execution.
        """
        # Close all active sessions
        if self._sessions:
            logger.info(
                f"Closing {len(self._sessions)} active MCP sessions",
                extra={"session_count": len(self._sessions)},
            )

            for server_id, session_cm in list(self._sessions.items()):
                try:
                    # Manually exit the session context manager
                    await session_cm.__aexit__(None, None, None)
                    logger.info(
                        f"MCP session closed for server",
                        extra={"server_id": server_id},
                    )
                except Exception as e:
                    logger.error(
                        f"Error closing MCP session for server {server_id}: {e}",
                        extra={"server_id": server_id, "error_type": type(e).__name__},
                    )

            # Clear sessions dict
            self._sessions.clear()

        if self.client:
            try:
                # MultiServerMCPClient cleanup handled by context manager
                # But explicit cleanup in case not used with async context manager
                logger.info("MCP Tool Bridge cleanup initiated")
                self._initialized = False
                self.client = None
            except Exception as e:
                logger.error(
                    f"Error during MCP Tool Bridge cleanup: {e}",
                    extra={"error_type": type(e).__name__},
                )
