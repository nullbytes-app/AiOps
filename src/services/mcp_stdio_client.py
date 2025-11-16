"""
MCP stdio Transport Client

This module implements a client for the Model Context Protocol (MCP) using stdio transport.
It spawns MCP server subprocesses and communicates via JSON-RPC 2.0 over stdin/stdout.

Implements MCP Specification 2025-03-26.
"""

import asyncio
import json
import logging
import os
from typing import Any, Self, cast

from src.schemas.mcp_server import MCPServerResponse

logger = logging.getLogger(__name__)


# Custom Exceptions
class MCPError(Exception):
    """Base exception for MCP client errors."""

    pass


class InitializationError(MCPError):
    """Raised when MCP server initialization fails."""

    pass


class ToolExecutionError(MCPError):
    """Raised when tool execution fails."""

    pass


class ProcessError(MCPError):
    """Raised when subprocess crashes or exits unexpectedly."""

    pass


class InvalidJSONError(MCPError):
    """Raised when JSON-RPC message parsing fails."""

    pass


class TimeoutError(MCPError):
    """Raised when an operation times out."""

    pass


class MCPStdioClient:
    """
    MCP stdio transport client for spawning and communicating with local MCP servers.

    Implements JSON-RPC 2.0 over stdin/stdout per MCP Specification 2025-03-26.
    Supports async context manager for automatic cleanup.

    Example usage:
        async with MCPStdioClient(config) as client:
            await client.initialize()
            tools = await client.list_tools()
            result = await client.call_tool("tool_name", {"arg": "value"})
    """

    def __init__(self, config: MCPServerResponse):
        """
        Initialize MCP stdio client.

        Args:
            config: MCPServerResponse schema containing transport configuration.

        Raises:
            ValueError: If transport_type is not "stdio" or command is missing.
        """
        if config.transport_type != "stdio":
            raise ValueError(f"Expected stdio transport, got {config.transport_type}")

        if not config.command:
            raise ValueError("Command is required for stdio transport")

        self.command = config.command
        self.args = config.args or []
        self.env = config.env or {}

        # Process management
        self.process: asyncio.subprocess.Process | None = None
        self._closed = False

        # JSON-RPC state
        self._request_id = 0
        self._pending_requests: dict[int, asyncio.Future[dict[str, Any]]] = {}

        # Server capabilities (set after initialize)
        self.server_capabilities: dict[str, Any] | None = None

        # Background tasks
        self._stderr_task: asyncio.Task[None] | None = None

    def _next_id(self) -> int:
        """
        Generate next unique request ID.

        Returns:
            Incrementing integer ID.
        """
        self._request_id += 1
        return self._request_id

    def _create_request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Construct JSON-RPC 2.0 request message.

        Args:
            method: JSON-RPC method name (e.g., "initialize", "tools/list").
            params: Optional method parameters.

        Returns:
            JSON-RPC 2.0 request dict.
        """
        request: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
        }

        if params is not None:
            request["params"] = params

        return request

    async def _send_request(self, request: dict[str, Any]) -> None:
        """
        Send JSON-RPC request to MCP server via stdin.

        Args:
            request: JSON-RPC 2.0 request dict.

        Raises:
            ProcessError: If subprocess stdin is unavailable.
        """
        if not self.process or not self.process.stdin:
            raise ProcessError("Process stdin is not available")

        # Serialize to JSON, append newline, encode UTF-8
        message = json.dumps(request) + "\n"
        message_bytes = message.encode("utf-8")

        logger.debug(f"Sending request: {request}")
        self.process.stdin.write(message_bytes)
        await self.process.stdin.drain()

    async def _send_notification(self, method: str, params: dict[str, Any] | None = None) -> None:
        """
        Send JSON-RPC notification to MCP server (no response expected).

        Args:
            method: JSON-RPC method name (e.g., "notifications/initialized").
            params: Optional method parameters.

        Raises:
            ProcessError: If subprocess stdin is unavailable.
        """
        if not self.process or not self.process.stdin:
            raise ProcessError("Process stdin is not available")

        # Create notification (no id field)
        notification: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
        }

        if params is not None:
            notification["params"] = params

        # Serialize and send
        message = json.dumps(notification) + "\n"
        message_bytes = message.encode("utf-8")

        logger.debug(f"Sending notification: {notification}")
        self.process.stdin.write(message_bytes)
        await self.process.stdin.drain()

    async def _read_response(self) -> dict[str, Any]:
        """
        Read JSON-RPC response from MCP server stdout.

        Returns:
            JSON-RPC 2.0 response dict.

        Raises:
            EOFError: If stdout is closed unexpectedly.
            InvalidJSONError: If response is malformed JSON.
        """
        if not self.process or not self.process.stdout:
            raise ProcessError("Process stdout is not available")

        # Read one line from stdout (newline-delimited)
        line = await self.process.stdout.readline()

        if not line:
            raise EOFError("MCP server closed stdout unexpectedly")

        # Decode UTF-8 and parse JSON
        try:
            message = line.decode("utf-8").strip()
            response = json.loads(message)
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise InvalidJSONError(f"Failed to parse JSON-RPC response: {e}")

        # Validate JSON-RPC 2.0 format
        if response.get("jsonrpc") != "2.0":
            raise InvalidJSONError(f"Invalid JSON-RPC version: {response.get('jsonrpc')}")

        logger.debug(f"Received response: {response}")
        return cast(dict[str, Any], response)

    async def _monitor_stderr(self) -> None:
        """
        Monitor stderr output from MCP server process.

        Logs stderr output at WARNING level for debugging.
        """
        if not self.process or not self.process.stderr:
            return

        try:
            while True:
                line = await self.process.stderr.readline()
                if not line:
                    break

                stderr_msg = line.decode("utf-8", errors="replace").strip()
                if stderr_msg:
                    logger.warning(f"MCP server stderr: {stderr_msg}")
        except Exception as e:
            logger.error(f"Error monitoring stderr: {e}")

    async def _send_and_wait(
        self, method: str, params: dict[str, Any] | None = None, timeout: float = 30.0
    ) -> dict[str, Any]:
        """
        Send JSON-RPC request and wait for matching response.

        Args:
            method: JSON-RPC method name.
            params: Optional method parameters.
            timeout: Timeout in seconds (default: 30s).

        Returns:
            Response result dict.

        Raises:
            TimeoutError: If no response received within timeout.
            MCPError: If server returns error response.
            ProcessError: If subprocess exits unexpectedly.
        """
        request = self._create_request(method, params)
        request_id = request["id"]

        # Create future for this request
        future: asyncio.Future[dict[str, Any]] = asyncio.Future()
        self._pending_requests[request_id] = future

        try:
            # Send request
            await self._send_request(request)

            # Start reading responses in background
            asyncio.create_task(self._read_responses())

            # Wait for response with timeout
            try:
                response = await asyncio.wait_for(future, timeout=timeout)
            except asyncio.TimeoutError:
                raise TimeoutError(f"No response received for method '{method}' within {timeout}s")

            # Check for JSON-RPC error
            if "error" in response:
                error = response["error"]
                raise MCPError(
                    f"Server error: {error.get('message', 'Unknown error')} (code: {error.get('code')})"
                )

            # Return result
            return cast(dict[str, Any], response.get("result", {}))

        finally:
            # Clean up pending request
            self._pending_requests.pop(request_id, None)

    async def _read_responses(self) -> None:
        """
        Background task to read and dispatch JSON-RPC responses.

        Matches responses to pending requests by ID and resolves futures.
        """
        try:
            response = await self._read_response()
            response_id = response.get("id")

            if response_id and response_id in self._pending_requests:
                future = self._pending_requests[response_id]
                if not future.done():
                    future.set_result(response)
        except Exception as e:
            # Propagate error to all pending requests
            for future in self._pending_requests.values():
                if not future.done():
                    future.set_exception(e)

    async def __aenter__(self) -> Self:
        """
        Async context manager entry - spawn subprocess.

        Returns:
            self

        Raises:
            ProcessError: If subprocess spawning fails.
        """
        # Merge env with os.environ to preserve system environment
        full_env = {**os.environ, **self.env}

        logger.info(f"Spawning MCP server: {self.command} {' '.join(self.args)}")

        try:
            # BUGFIX: Celery wraps sys.stdout/sys.stderr in LoggingProxy objects
            # which don't have fileno() method needed by asyncio subprocess.
            # Temporarily restore real file descriptors if in Celery environment.
            # Reason: asyncio.create_subprocess_exec needs fileno() for pipe setup
            import sys

            # Check if we're in Celery environment (stdout/stderr are LoggingProxy)
            has_fileno = hasattr(sys.stdout, 'fileno')
            is_celery = not has_fileno

            logger.info(
                f"Subprocess spawn environment check: "
                f"stdout has fileno={has_fileno}, "
                f"stdout type={type(sys.stdout).__name__}, "
                f"is_celery={is_celery}"
            )

            if is_celery:
                # Save Celery's LoggingProxy wrappers
                original_stdout = sys.stdout
                original_stderr = sys.stderr

                # Restore real file descriptors temporarily
                sys.stdout = sys.__stdout__
                sys.stderr = sys.__stderr__

                logger.info(
                    f"Detected Celery environment, temporarily restored real stdout/stderr. "
                    f"New stdout type: {type(sys.stdout).__name__}"
                )

            try:
                logger.info(f"Creating subprocess with command: {self.command} {' '.join(self.args)}")
                self.process = await asyncio.create_subprocess_exec(
                    self.command,
                    *self.args,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=full_env,
                )
                logger.info("Subprocess created successfully")
            finally:
                # Restore LoggingProxy wrappers if we changed them
                if is_celery:
                    sys.stdout = original_stdout
                    sys.stderr = original_stderr
                    logger.info("Restored Celery LoggingProxy wrappers")

        except Exception as e:
            logger.error(
                f"Failed to spawn subprocess: {e}",
                exc_info=True,
                extra={
                    "command": self.command,
                    "args": self.args,
                    "error_type": type(e).__name__,
                }
            )
            raise ProcessError(f"Failed to spawn subprocess: {e}")

        # Start monitoring stderr
        self._stderr_task = asyncio.create_task(self._monitor_stderr())

        logger.info(f"MCP server process started (PID: {self.process.pid})")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """
        Async context manager exit - cleanup subprocess.

        Args:
            exc_type: Exception type (if any).
            exc_val: Exception value (if any).
            exc_tb: Exception traceback (if any).
        """
        await self.close()

    async def close(self) -> None:
        """
        Gracefully terminate MCP server process.

        Sends SIGTERM, waits 5 seconds, then sends SIGKILL if still running.
        Closes stdin/stdout/stderr pipes and cancels background tasks.
        """
        if self._closed or not self.process:
            return

        self._closed = True

        logger.info(f"Closing MCP server process (PID: {self.process.pid})")

        # Cancel stderr monitoring
        if self._stderr_task and not self._stderr_task.done():
            self._stderr_task.cancel()
            try:
                await self._stderr_task
            except asyncio.CancelledError:
                pass

        # Check if already terminated
        if self.process.returncode is not None:
            logger.info("Process already terminated")
            return

        # Send SIGTERM
        self.process.terminate()

        try:
            # Wait up to 5 seconds for graceful exit
            await asyncio.wait_for(self.process.wait(), timeout=5.0)
            logger.info("Process terminated gracefully")
        except asyncio.TimeoutError:
            # Force kill if still running
            logger.warning("Process did not terminate gracefully, sending SIGKILL")
            self.process.kill()
            await self.process.wait()
            logger.info("Process killed")

        # Close pipes
        if self.process.stdin:
            self.process.stdin.close()
        # Note: stdout/stderr are StreamReaders which don't have close() method
        # They are automatically cleaned up when the process exits

        logger.info("MCP server process closed")

    async def initialize(self) -> dict[str, Any]:
        """
        Perform MCP initialize handshake.

        Sends initialize request with protocol version 2025-03-26.
        Validates server response and stores capabilities.

        Returns:
            Server capabilities dict.

        Raises:
            InitializationError: If server returns error or incompatible version.
            MCPError: If handshake fails.
        """
        if self._closed:
            raise MCPError("Client is closed")

        params = {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "ai-ops-platform", "version": "1.0.0"},
        }

        logger.info("Initializing MCP connection")

        try:
            result = await self._send_and_wait("initialize", params)
        except Exception as e:
            raise InitializationError(f"Initialize handshake failed: {e}")

        # Validate protocol version (accept 2024-11-05 and 2025-03-26 for compatibility)
        server_version = result.get("protocolVersion")
        supported_versions = ["2024-11-05", "2025-03-26"]
        if server_version not in supported_versions:
            raise InitializationError(
                f"Incompatible protocol version: {server_version} (expected one of: {supported_versions})"
            )

        # Store server capabilities
        self.server_capabilities = result.get("capabilities", {})

        server_info = result.get("serverInfo", {})
        logger.info(
            f"MCP initialized - Server: {server_info.get('name')} v{server_info.get('version')}"
        )

        # Send initialized notification to complete handshake (per MCP spec)
        await self._send_notification("notifications/initialized", {})
        logger.debug("Sent initialized notification")

        return self.server_capabilities

    async def list_tools(self) -> list[dict[str, Any]]:
        """
        List available tools from MCP server.

        Returns:
            List of tool dicts with name, description (optional), inputSchema.

        Raises:
            MCPError: If server returns error.
        """
        if self._closed:
            raise MCPError("Client is closed")

        result = await self._send_and_wait("tools/list", {})
        tools = result.get("tools", [])

        logger.debug(f"Listed {len(tools)} tools")
        return cast(list[dict[str, Any]], tools)

    async def list_resources(self) -> list[dict[str, Any]]:
        """
        List available resources from MCP server.

        Returns:
            List of resource dicts with uri, name, description (optional), mimeType (optional).

        Raises:
            MCPError: If server returns error.
        """
        if self._closed:
            raise MCPError("Client is closed")

        result = await self._send_and_wait("resources/list", {})
        resources = result.get("resources", [])

        logger.debug(f"Listed {len(resources)} resources")
        return cast(list[dict[str, Any]], resources)

    async def list_prompts(self) -> list[dict[str, Any]]:
        """
        List available prompts from MCP server.

        Returns:
            List of prompt dicts with name, description (optional), arguments.

        Raises:
            MCPError: If server returns error.
        """
        if self._closed:
            raise MCPError("Client is closed")

        result = await self._send_and_wait("prompts/list", {})
        prompts = result.get("prompts", [])

        logger.debug(f"Listed {len(prompts)} prompts")
        return cast(list[dict[str, Any]], prompts)

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Call a tool on the MCP server.

        Args:
            name: Tool name (from list_tools).
            arguments: Tool arguments matching inputSchema.

        Returns:
            Dict with "content" (list of content blocks) and "is_error" (bool).

        Raises:
            ToolExecutionError: If tool execution fails (isError: true).
            MCPError: If server returns error.
        """
        if self._closed:
            raise MCPError("Client is closed")

        params = {"name": name, "arguments": arguments}

        result = await self._send_and_wait("tools/call", params)

        # Check for tool execution error
        is_error = result.get("isError", False)
        if is_error:
            raise ToolExecutionError(f"Tool '{name}' execution failed")

        return {
            "content": result.get("content", []),
            "is_error": is_error,
        }

    async def read_resource(self, uri: str) -> dict[str, Any]:
        """
        Read a resource from the MCP server.

        Args:
            uri: Resource URI (from list_resources).

        Returns:
            Dict with "contents" (list of content blocks).

        Raises:
            MCPError: If server returns error.
        """
        if self._closed:
            raise MCPError("Client is closed")

        params = {"uri": uri}

        result = await self._send_and_wait("resources/read", params)

        return {"contents": result.get("contents", [])}

    async def get_prompt(
        self, name: str, arguments: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Get a prompt from the MCP server.

        Args:
            name: Prompt name (from list_prompts).
            arguments: Optional prompt arguments.

        Returns:
            Dict with "messages" (list of message templates).

        Raises:
            MCPError: If server returns error.
        """
        if self._closed:
            raise MCPError("Client is closed")

        params = {"name": name, "arguments": arguments or {}}

        result = await self._send_and_wait("prompts/get", params)

        return {"messages": result.get("messages", [])}


__all__ = [
    "MCPStdioClient",
    "MCPError",
    "InitializationError",
    "ToolExecutionError",
    "ProcessError",
    "InvalidJSONError",
    "TimeoutError",
]
