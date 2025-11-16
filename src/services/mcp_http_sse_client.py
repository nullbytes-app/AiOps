"""
MCP Streamable HTTP Transport Client

This module implements a client for the Model Context Protocol (MCP) using Streamable HTTP transport.
It connects to remote MCP servers via HTTP POST with dual response modes: single JSON or SSE streaming.

Implements MCP Specification 2025-03-26 Streamable HTTP transport.
"""

import asyncio
from typing import Any, Self, cast

import httpx
from loguru import logger

# Reuse exception hierarchy from stdio client
from src.services.mcp_stdio_client import (
    MCPError,
    InitializationError,
    ToolExecutionError,
    InvalidJSONError,
    TimeoutError as MCPTimeoutError,
)

# HTTP-specific exceptions and handlers
from src.services._mcp_http_response_handlers import (
    MCPConnectionError,
    MCPClientError,
    MCPServerError,
    handle_sse_stream,
    handle_json_response,
    post_request,
    redact_sensitive_headers,
)


class MCPStreamableHTTPClient:
    """
    MCP Streamable HTTP transport client for remote MCP servers.

    Implements JSON-RPC 2.0 over HTTP POST with dual response modes per MCP Specification 2025-03-26.
    Supports async context manager for automatic cleanup.

    Example usage:
        async with MCPStreamableHTTPClient(url, headers) as client:
            await client.initialize()
            tools = await client.list_tools()
            result = await client.call_tool("tool_name", {"arg": "value"})
    """

    def __init__(self, url: str, headers: dict[str, str] | None = None):
        """
        Initialize MCP Streamable HTTP client.

        Args:
            url: Base URL of MCP server endpoint (e.g., "https://api.example.com/mcp").
            headers: Optional HTTP headers for authentication (e.g., {"Authorization": "Bearer token"}).

        Raises:
            ValueError: If URL is invalid.
        """
        if not url or not url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid URL: {url}")

        self.url = url
        self.headers = headers or {}

        # HTTP client (created in __aenter__)
        self.client: httpx.AsyncClient | None = None
        self._closed = False

        # JSON-RPC state
        self._request_id = 0

        # SSE resumability
        self.last_event_id: str | None = None

        # Server capabilities (set after initialize)
        self.server_capabilities: dict[str, Any] = {}

    async def __aenter__(self) -> Self:
        """
        Async context manager entry: create HTTP client.

        Returns:
            Self for use in async with statement.
        """
        # Configure granular timeouts (2025 best practice)
        timeout = httpx.Timeout(
            connect=10.0,  # TCP connection establishment
            read=60.0,  # Response reading
            write=10.0,  # Request writing
            pool=5.0,  # Connection pool acquisition
        )

        # Configure connection pooling
        limits = httpx.Limits(
            max_connections=100,  # Total concurrent connections
            max_keepalive_connections=20,  # Reusable persistent connections
        )

        # Create async HTTP client with HTTP/2 support
        self.client = httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            http2=True,  # Enable HTTP/2 with automatic fallback to HTTP/1.1
            headers=self.headers,
            follow_redirects=True,
        )

        logger.info(
            "MCP HTTP client initialized",
            url=self.url,
            http2=True,
            max_connections=100,
        )

        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Async context manager exit: close HTTP client.

        Args:
            exc_type: Exception type (if any).
            exc_val: Exception value (if any).
            exc_tb: Exception traceback (if any).
        """
        await self.close()

    async def close(self) -> None:
        """
        Close HTTP client and release all connections.

        Idempotent: safe to call multiple times.
        """
        if self._closed:
            return

        if self.client:
            await self.client.aclose()
            logger.info("MCP HTTP client closed")

        self._closed = True

    def _next_request_id(self) -> int:
        """
        Generate next JSON-RPC request ID.

        Returns:
            Incremental request ID.
        """
        self._request_id += 1
        return self._request_id

    def _build_jsonrpc_request(
        self, method: str, params: dict[str, Any], request_id: int
    ) -> dict[str, Any]:
        """
        Build JSON-RPC 2.0 request payload.

        Args:
            method: JSON-RPC method name (e.g., "tools/list").
            params: Method parameters.
            request_id: Unique request ID.

        Returns:
            JSON-RPC request dict.
        """
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

    def _redact_sensitive_headers(self, headers: dict[str, str]) -> dict[str, str]:
        """
        Redact sensitive header values for logging (wrapper for handler function).

        Args:
            headers: Original headers dict.

        Returns:
            Headers dict with sensitive values redacted.
        """
        return redact_sensitive_headers(headers)

    async def _post_request(self, jsonrpc_payload: dict[str, Any]) -> httpx.Response:
        """
        Send HTTP POST request to MCP server (wrapper for handler function).

        Args:
            jsonrpc_payload: JSON-RPC request payload.

        Returns:
            httpx.Response object.

        Raises:
            MCPConnectionError: On connection failures or timeouts.
            MCPClientError: On HTTP 4xx errors.
            MCPServerError: On HTTP 5xx errors.
        """
        if not self.client:
            raise MCPError("Client not initialized (use async with)")

        return await post_request(
            self.client, self.url, jsonrpc_payload, self.headers, redact_sensitive_headers
        )

    def _handle_json_response(self, response: httpx.Response) -> dict[str, Any]:
        """
        Handle single JSON response mode (wrapper for handler function).

        Args:
            response: httpx.Response with application/json Content-Type.

        Returns:
            JSON-RPC result dict.

        Raises:
            InvalidJSONError: If response is not valid JSON-RPC.
            MCPError: If JSON-RPC error response.
        """
        return handle_json_response(response)

    async def _make_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Make JSON-RPC request with dual response mode handling.

        Args:
            method: JSON-RPC method name.
            params: Method parameters.

        Returns:
            JSON-RPC result dict.

        Raises:
            MCPError: On any error during request/response.
        """
        if self._closed:
            raise MCPError("Client is closed")

        if not self.client:
            raise MCPError("Client not initialized (use async with)")

        request_id = self._next_request_id()
        jsonrpc_payload = self._build_jsonrpc_request(method, params, request_id)

        # Attempt POST request using handler
        response = await post_request(
            self.client, self.url, jsonrpc_payload, self.headers, redact_sensitive_headers
        )

        # Determine response mode based on Content-Type
        content_type = response.headers.get("content-type", "")

        if "application/json" in content_type:
            # Single JSON response mode
            return handle_json_response(response)

        elif "text/event-stream" in content_type:
            # SSE stream response mode - delegate to handler
            result, last_event_id = await handle_sse_stream(self.client, self.url, jsonrpc_payload)

            # Store last event ID for resumability
            if last_event_id:
                self.last_event_id = last_event_id

            return result

        else:
            raise MCPError(f"Unexpected Content-Type: {content_type}")

    # ========== MCP Interface Methods (Match stdio client) ==========

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

        logger.info("Initializing MCP HTTP connection", url=self.url)

        try:
            result = await self._make_request("initialize", params)
        except Exception as e:
            raise InitializationError(f"Initialize handshake failed: {e}") from e

        # Validate protocol version
        server_version = result.get("protocolVersion")
        if server_version != "2025-03-26":
            raise InitializationError(
                f"Incompatible protocol version: {server_version} (expected 2025-03-26)"
            )

        # Store server capabilities
        self.server_capabilities = result.get("capabilities", {})

        server_info = result.get("serverInfo", {})
        logger.info(
            f"MCP HTTP initialized - Server: {server_info.get('name')} v{server_info.get('version')}"
        )

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

        result = await self._make_request("tools/list", {})
        tools = result.get("tools", [])

        logger.debug(f"Listed {len(tools)} tools via HTTP")
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

        result = await self._make_request("resources/list", {})
        resources = result.get("resources", [])

        logger.debug(f"Listed {len(resources)} resources via HTTP")
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

        result = await self._make_request("prompts/list", {})
        prompts = result.get("prompts", [])

        logger.debug(f"Listed {len(prompts)} prompts via HTTP")
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

        result = await self._make_request("tools/call", params)

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

        result = await self._make_request("resources/read", params)

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

        result = await self._make_request("prompts/get", params)

        return {"messages": result.get("messages", [])}


__all__ = [
    "MCPStreamableHTTPClient",
    "MCPError",
    "MCPConnectionError",
    "MCPClientError",
    "MCPServerError",
    "InitializationError",
    "ToolExecutionError",
    "InvalidJSONError",
    "MCPTimeoutError",
]
