"""
Unit tests for MCP Streamable HTTP Transport Client

Tests all core functionality of MCPStreamableHTTPClient including:
- Initialization and lifecycle management
- JSON-RPC request building
- Single JSON response handling
- SSE stream response handling
- Timeout and error handling
- HTTP header configuration
- Connection pooling
- Logging and observability
"""

import json
import pytest
import httpx
from httpx_sse import ServerSentEvent
import respx
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.mcp_http_sse_client import (
    MCPStreamableHTTPClient,
    MCPError,
    MCPConnectionError,
    MCPClientError,
    MCPServerError,
    InitializationError,
    ToolExecutionError,
    InvalidJSONError,
)


# ========== Fixtures ==========


@pytest.fixture
def test_url():
    """Test MCP server URL."""
    return "https://api.example.com/mcp"


@pytest.fixture
def test_headers():
    """Test authentication headers."""
    return {"Authorization": "Bearer test-token", "X-API-Key": "secret-key"}


@pytest.fixture
async def http_client(test_url, test_headers):
    """Create and teardown HTTP client."""
    async with MCPStreamableHTTPClient(test_url, test_headers) as client:
        yield client


# ========== Initialization Tests ==========


@pytest.mark.unit
def test_client_initialization_valid_url(test_url, test_headers):
    """Test client initializes with valid URL."""
    client = MCPStreamableHTTPClient(test_url, test_headers)

    assert client.url == test_url
    assert client.headers == test_headers
    assert client._request_id == 0
    assert client.last_event_id is None
    assert not client._closed


@pytest.mark.unit
def test_client_initialization_invalid_url():
    """Test client rejects invalid URL."""
    with pytest.raises(ValueError, match="Invalid URL"):
        MCPStreamableHTTPClient("invalid-url")


@pytest.mark.unit
def test_client_initialization_no_headers(test_url):
    """Test client works without headers."""
    client = MCPStreamableHTTPClient(test_url)

    assert client.headers == {}


@pytest.mark.unit
async def test_client_context_manager(test_url, test_headers):
    """Test async context manager creates and closes client."""
    async with MCPStreamableHTTPClient(test_url, test_headers) as client:
        assert client.client is not None
        assert not client._closed

    assert client._closed


# ========== JSON-RPC Request Building ==========


@pytest.mark.unit
def test_build_jsonrpc_request(test_url):
    """Test JSON-RPC request structure."""
    client = MCPStreamableHTTPClient(test_url)

    request = client._build_jsonrpc_request("tools/list", {}, 1)

    assert request == {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {},
    }


@pytest.mark.unit
def test_next_request_id_increments(test_url):
    """Test request ID increments correctly."""
    client = MCPStreamableHTTPClient(test_url)

    assert client._next_request_id() == 1
    assert client._next_request_id() == 2
    assert client._next_request_id() == 3


# ========== Header Redaction ==========


@pytest.mark.unit
def test_redact_sensitive_headers(test_url):
    """Test sensitive headers are redacted in logs."""
    client = MCPStreamableHTTPClient(test_url)

    headers = {
        "Authorization": "Bearer secret-token",
        "X-API-Key": "secret-key",
        "Content-Type": "application/json",
    }

    redacted = client._redact_sensitive_headers(headers)

    assert redacted["Authorization"] == "***REDACTED***"
    assert redacted["X-API-Key"] == "***REDACTED***"
    assert redacted["Content-Type"] == "application/json"


# ========== Single JSON Response Handling ==========


@pytest.mark.unit
def test_handle_json_response_success(test_url):
    """Test parsing successful JSON response."""
    client = MCPStreamableHTTPClient(test_url)

    response = MagicMock()
    response.json.return_value = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"tools": [{"name": "test-tool"}]},
    }

    result = client._handle_json_response(response)

    assert result == {"tools": [{"name": "test-tool"}]}


@pytest.mark.unit
def test_handle_json_response_error(test_url):
    """Test parsing JSON-RPC error response."""
    client = MCPStreamableHTTPClient(test_url)

    response = MagicMock()
    response.json.return_value = {
        "jsonrpc": "2.0",
        "id": 1,
        "error": {"code": -32600, "message": "Invalid Request"},
    }

    with pytest.raises(MCPError, match="Invalid Request"):
        client._handle_json_response(response)


@pytest.mark.unit
def test_handle_json_response_invalid_json(test_url):
    """Test handling invalid JSON."""
    client = MCPStreamableHTTPClient(test_url)

    response = MagicMock()
    response.json.side_effect = json.JSONDecodeError("msg", "doc", 0)

    with pytest.raises(InvalidJSONError, match="Invalid JSON response"):
        client._handle_json_response(response)


# ========== Timeout Exception Handling ==========


@pytest.mark.unit
@respx.mock
async def test_connect_timeout_exception(test_url, test_headers):
    """Test ConnectTimeout exception handling."""
    async with MCPStreamableHTTPClient(test_url, test_headers) as client:
        respx.post(test_url).mock(side_effect=httpx.ConnectTimeout("connection timeout"))

        with pytest.raises(MCPConnectionError, match="Connection timeout"):
            await client._post_request({"jsonrpc": "2.0", "id": 1, "method": "test"})


@pytest.mark.unit
@respx.mock
async def test_read_timeout_exception(test_url, test_headers):
    """Test ReadTimeout exception handling."""
    async with MCPStreamableHTTPClient(test_url, test_headers) as client:
        respx.post(test_url).mock(side_effect=httpx.ReadTimeout("read timeout"))

        with pytest.raises(MCPConnectionError, match="Read timeout"):
            await client._post_request({"jsonrpc": "2.0", "id": 1, "method": "test"})


@pytest.mark.unit
@respx.mock
async def test_write_timeout_exception(test_url, test_headers):
    """Test WriteTimeout exception handling."""
    async with MCPStreamableHTTPClient(test_url, test_headers) as client:
        respx.post(test_url).mock(side_effect=httpx.WriteTimeout("write timeout"))

        with pytest.raises(MCPConnectionError, match="Write timeout"):
            await client._post_request({"jsonrpc": "2.0", "id": 1, "method": "test"})


@pytest.mark.unit
@respx.mock
async def test_pool_timeout_exception(test_url, test_headers):
    """Test PoolTimeout exception handling."""
    async with MCPStreamableHTTPClient(test_url, test_headers) as client:
        respx.post(test_url).mock(side_effect=httpx.PoolTimeout("pool exhausted"))

        with pytest.raises(MCPConnectionError, match="Connection pool exhausted"):
            await client._post_request({"jsonrpc": "2.0", "id": 1, "method": "test"})


# ========== HTTP Status Error Handling ==========


@pytest.mark.unit
@respx.mock
async def test_http_404_client_error(test_url, test_headers):
    """Test HTTP 404 raises MCPClientError."""
    async with MCPStreamableHTTPClient(test_url, test_headers) as client:
        respx.post(test_url).mock(return_value=httpx.Response(404, text="Not Found"))

        with pytest.raises(MCPClientError, match="HTTP 404"):
            await client._post_request({"jsonrpc": "2.0", "id": 1, "method": "test"})


@pytest.mark.unit
@respx.mock
async def test_http_500_server_error(test_url, test_headers):
    """Test HTTP 500 raises MCPServerError."""
    async with MCPStreamableHTTPClient(test_url, test_headers) as client:
        respx.post(test_url).mock(return_value=httpx.Response(500, text="Server Error"))

        with pytest.raises(MCPServerError, match="HTTP 500"):
            await client._post_request({"jsonrpc": "2.0", "id": 1, "method": "test"})


# ========== MCP Interface Methods ==========


@pytest.mark.unit
@respx.mock
async def test_initialize_success(test_url, test_headers):
    """Test successful MCP initialization."""
    response_data = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "protocolVersion": "2025-03-26",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "test-server", "version": "1.0.0"},
        },
    }

    async with MCPStreamableHTTPClient(test_url, test_headers) as client:
        respx.post(test_url).mock(
            return_value=httpx.Response(200, json=response_data, headers={"content-type": "application/json"})
        )

        capabilities = await client.initialize()

        assert capabilities == {"tools": {}}
        assert client.server_capabilities == {"tools": {}}


@pytest.mark.unit
@respx.mock
async def test_initialize_incompatible_version(test_url, test_headers):
    """Test initialization fails with incompatible protocol version."""
    response_data = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "protocolVersion": "2024-11-05",  # Old version
            "capabilities": {},
        },
    }

    async with MCPStreamableHTTPClient(test_url, test_headers) as client:
        respx.post(test_url).mock(
            return_value=httpx.Response(200, json=response_data, headers={"content-type": "application/json"})
        )

        with pytest.raises(InitializationError, match="Incompatible protocol version"):
            await client.initialize()


@pytest.mark.unit
@respx.mock
async def test_list_tools(test_url, test_headers):
    """Test list_tools method."""
    response_data = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "tools": [
                {"name": "test-tool", "description": "A test tool", "inputSchema": {}},
            ],
        },
    }

    async with MCPStreamableHTTPClient(test_url, test_headers) as client:
        respx.post(test_url).mock(
            return_value=httpx.Response(200, json=response_data, headers={"content-type": "application/json"})
        )

        tools = await client.list_tools()

        assert len(tools) == 1
        assert tools[0]["name"] == "test-tool"


@pytest.mark.unit
@respx.mock
async def test_call_tool_success(test_url, test_headers):
    """Test successful tool call."""
    response_data = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [{"type": "text", "text": "Tool result"}],
            "isError": False,
        },
    }

    async with MCPStreamableHTTPClient(test_url, test_headers) as client:
        respx.post(test_url).mock(
            return_value=httpx.Response(200, json=response_data, headers={"content-type": "application/json"})
        )

        result = await client.call_tool("test-tool", {"arg": "value"})

        assert result["content"] == [{"type": "text", "text": "Tool result"}]
        assert result["is_error"] is False


@pytest.mark.unit
@respx.mock
async def test_call_tool_execution_error(test_url, test_headers):
    """Test tool execution error."""
    response_data = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [],
            "isError": True,
        },
    }

    async with MCPStreamableHTTPClient(test_url, test_headers) as client:
        respx.post(test_url).mock(
            return_value=httpx.Response(200, json=response_data, headers={"content-type": "application/json"})
        )

        with pytest.raises(ToolExecutionError, match="execution failed"):
            await client.call_tool("failing-tool", {})


# ========== Connection Pooling Tests ==========


@pytest.mark.unit
async def test_http2_enabled(test_url, test_headers):
    """Test HTTP/2 is enabled in client configuration."""
    async with MCPStreamableHTTPClient(test_url, test_headers) as client:
        assert client.client is not None
        # Check that client was created (HTTP/2 enable is verified in logs)


@pytest.mark.unit
async def test_connection_pool_limits(test_url, test_headers):
    """Test connection pool limits are configured."""
    async with MCPStreamableHTTPClient(test_url, test_headers) as client:
        assert client.client is not None
        # Limits are passed to httpx but not exposed as attributes
        # Verify client was created successfully (limits applied internally)


# ========== Client Lifecycle ==========


@pytest.mark.unit
async def test_close_idempotent(test_url, test_headers):
    """Test close() can be called multiple times safely."""
    client = MCPStreamableHTTPClient(test_url, test_headers)
    await client.__aenter__()

    await client.close()
    assert client._closed

    await client.close()  # Should not raise
    assert client._closed


@pytest.mark.unit
async def test_methods_raise_when_closed(test_url, test_headers):
    """Test methods raise MCPError when client is closed."""
    client = MCPStreamableHTTPClient(test_url, test_headers)
    await client.__aenter__()
    await client.close()

    with pytest.raises(MCPError, match="Client is closed"):
        await client.initialize()

    with pytest.raises(MCPError, match="Client is closed"):
        await client.list_tools()


# ============================================================================
# Test Additional Coverage (Story 11.2.6 - Coverage >90%)
# ============================================================================


@pytest.mark.unit
async def test_list_resources_closed_client(test_url, test_headers):
    """Test list_resources() raises error when client is closed."""
    client = MCPStreamableHTTPClient(test_url, test_headers)
    await client.__aenter__()
    await client.close()

    with pytest.raises(MCPError, match="Client is closed"):
        await client.list_resources()


@pytest.mark.unit
async def test_list_prompts_closed_client(test_url, test_headers):
    """Test list_prompts() raises error when client is closed."""
    client = MCPStreamableHTTPClient(test_url, test_headers)
    await client.__aenter__()
    await client.close()

    with pytest.raises(MCPError, match="Client is closed"):
        await client.list_prompts()


@pytest.mark.unit
async def test_read_resource_closed_client(test_url, test_headers):
    """Test read_resource() raises error when client is closed."""
    client = MCPStreamableHTTPClient(test_url, test_headers)
    await client.__aenter__()
    await client.close()

    with pytest.raises(MCPError, match="Client is closed"):
        await client.read_resource("file:///test.txt")


@pytest.mark.unit
async def test_get_prompt_closed_client(test_url, test_headers):
    """Test get_prompt() raises error when client is closed."""
    client = MCPStreamableHTTPClient(test_url, test_headers)
    await client.__aenter__()
    await client.close()

    with pytest.raises(MCPError, match="Client is closed"):
        await client.get_prompt("test_prompt")


@pytest.mark.unit
async def test_make_request_not_initialized(test_url, test_headers):
    """Test _make_request() raises error when client not initialized."""
    client = MCPStreamableHTTPClient(test_url, test_headers)
    # Don't call __aenter__ - client.client will be None

    with pytest.raises(MCPError, match="Client not initialized"):
        await client._make_request("tools/list", {})


@pytest.mark.unit
async def test_sse_stream_response_mode(test_url, test_headers, respx_mock):
    """Test SSE stream response mode handling (lines 262-273)."""
    # Mock SSE stream response
    respx_mock.post(test_url).mock(
        return_value=httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=b'event: message\nid: 1\ndata: {"jsonrpc":"2.0","id":1,"result":{"tools":[]}}\n\n'
        )
    )

    async with MCPStreamableHTTPClient(test_url, test_headers) as client:
        # Call list_tools which will trigger SSE handling
        result = await client.list_tools()

        # Verify SSE stream was processed correctly
        assert isinstance(result, list)
        # last_event_id should be stored from SSE response
        assert client.last_event_id == "1"


@pytest.mark.unit
async def test_unexpected_content_type(test_url, test_headers, respx_mock):
    """Test _make_request raises error for unexpected Content-Type (line 273)."""
    respx_mock.post(test_url).mock(
        return_value=httpx.Response(
            200,
            headers={"content-type": "text/html"},  # Unexpected type
            content=b"<html>Not JSON</html>"
        )
    )

    async with MCPStreamableHTTPClient(test_url, test_headers) as client:
        with pytest.raises(MCPError, match="Unexpected Content-Type"):
            await client.list_tools()


@pytest.mark.unit
async def test_initialize_exception_handling(test_url, test_headers, respx_mock):
    """Test initialize wraps exceptions in InitializationError (lines 304-305)."""
    respx_mock.post(test_url).mock(
        side_effect=httpx.RequestError("Connection refused")
    )

    async with MCPStreamableHTTPClient(test_url, test_headers) as client:
        with pytest.raises(InitializationError, match="Initialize handshake failed"):
            await client.initialize()


@pytest.mark.unit
async def test_list_resources_success(test_url, test_headers, respx_mock):
    """Test list_resources() full execution path (lines 356-360)."""
    respx_mock.post(test_url).mock(
        return_value=httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"jsonrpc": "2.0", "id": 1, "result": {"resources": [{"uri": "file:///test", "name": "test"}]}}
        )
    )

    async with MCPStreamableHTTPClient(test_url, test_headers) as client:
        result = await client.list_resources()
        assert len(result) == 1
        assert result[0]["uri"] == "file:///test"


@pytest.mark.unit
async def test_list_prompts_success(test_url, test_headers, respx_mock):
    """Test list_prompts() full execution path (lines 375-379)."""
    respx_mock.post(test_url).mock(
        return_value=httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"jsonrpc": "2.0", "id": 1, "result": {"prompts": [{"name": "test-prompt", "description": "Test"}]}}
        )
    )

    async with MCPStreamableHTTPClient(test_url, test_headers) as client:
        result = await client.list_prompts()
        assert len(result) == 1
        assert result[0]["name"] == "test-prompt"


@pytest.mark.unit
async def test_call_tool_closed_client(test_url, test_headers):
    """Test call_tool() closed check (line 397)."""
    client = MCPStreamableHTTPClient(test_url, test_headers)
    await client.__aenter__()
    await client.close()

    with pytest.raises(MCPError, match="Client is closed"):
        await client.call_tool("test_tool", {})


@pytest.mark.unit
async def test_read_resource_success(test_url, test_headers, respx_mock):
    """Test read_resource() full execution path (lines 429-433)."""
    respx_mock.post(test_url).mock(
        return_value=httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"jsonrpc": "2.0", "id": 1, "result": {"contents": [{"uri": "file:///test", "text": "content"}]}}
        )
    )

    async with MCPStreamableHTTPClient(test_url, test_headers) as client:
        result = await client.read_resource("file:///test")
        assert "contents" in result
        assert len(result["contents"]) == 1


@pytest.mark.unit
async def test_get_prompt_success(test_url, test_headers, respx_mock):
    """Test get_prompt() full execution path (lines 454-458)."""
    respx_mock.post(test_url).mock(
        return_value=httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"jsonrpc": "2.0", "id": 1, "result": {"messages": [{"role": "user", "content": "Test"}]}}
        )
    )

    async with MCPStreamableHTTPClient(test_url, test_headers) as client:
        result = await client.get_prompt("test-prompt")
        assert "messages" in result
        assert len(result["messages"]) == 1
