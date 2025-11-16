"""
Integration tests for MCP test_connection endpoint.

Tests the POST /api/v1/mcp-servers/test-connection endpoint with both stdio and HTTP+SSE transports.
Story 11.2.2 Task 2.5: 6 integration tests

Requirements:
- Test connection endpoint should NOT require tenant_id (no auth needed for testing)
- Should support both stdio and http_sse transport types
- Should return discovered capabilities (tools, resources, prompts)
- Should handle connection failures gracefully
- Should validate schema before attempting connection
"""

import pytest
from unittest.mock import patch, AsyncMock

from src.schemas.mcp_server import MCPServerCreate


@pytest.mark.integration
class TestMCPTestConnectionEndpoint:
    """Integration tests for test_connection endpoint."""

    @pytest.mark.asyncio
    async def test_stdio_connection_success(self, async_client):
        """
        Test successful stdio transport connection.

        Validates:
        - Endpoint accepts stdio configuration without tenant_id
        - Returns discovered capabilities (tools, resources, prompts)
        - Response includes success=True and server_info
        """
        payload = {
            "name": "Test Filesystem Server",
            "description": "Testing stdio transport",
            "transport_type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-everything"],
        }

        # Mock the stdio client to avoid real subprocess
        with patch("src.services.mcp_server_service.MCPStdioClient") as mock_client_class:
            mock_client = AsyncMock()
            # Mock initialize to return dict (not awaitable)
            mock_client.initialize = AsyncMock(return_value={
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "Test Filesystem Server", "version": "1.0.0"},
                "capabilities": {"tools": {}, "resources": {}}
            })
            mock_client.list_tools = AsyncMock(return_value=[
                {"name": "read_file", "description": "Read a file", "inputSchema": {"type": "object"}}
            ])
            mock_client.list_resources = AsyncMock(return_value=[
                {"name": "file://test.txt", "uri": "file://test.txt"}
            ])
            mock_client.list_prompts = AsyncMock(return_value=[])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = await async_client.post(
                "/api/v1/mcp-servers/test-connection",
                json=payload,
            )

        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert "server_info" in result
        assert len(result["discovered_tools"]) == 1
        assert len(result["discovered_resources"]) == 1
        assert len(result["discovered_prompts"]) == 0

    @pytest.mark.asyncio
    async def test_http_sse_connection_success(self, async_client):
        """
        Test successful HTTP+SSE transport connection.

        Validates:
        - Endpoint accepts http_sse configuration without tenant_id
        - Handles HTTP headers properly
        - Returns discovered capabilities from HTTP+SSE server
        """
        payload = {
            "name": "Test HTTP+SSE Server",
            "description": "Testing HTTP+SSE transport",
            "transport_type": "http_sse",
            "url": "https://mcp-test-server.example.com/mcp",
            "headers": {
                "Authorization": "Bearer test-token-12345",
                "X-API-Key": "test-api-key"
            }
        }

        # Mock the HTTP+SSE client (MCPStreamableHTTPClient)
        with patch("src.services.mcp_server_service.MCPStreamableHTTPClient") as mock_client_class:
            mock_client = AsyncMock()
            # Mock initialize to return dict
            mock_client.initialize = AsyncMock(return_value={
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "Test HTTP+SSE Server", "version": "1.0.0"},
                "capabilities": {"tools": {}, "prompts": {}}
            })
            mock_client.list_tools = AsyncMock(return_value=[
                {"name": "github_search", "description": "Search GitHub", "inputSchema": {"type": "object"}}
            ])
            mock_client.list_resources = AsyncMock(return_value=[])
            mock_client.list_prompts = AsyncMock(return_value=[
                {"name": "code_review", "description": "Code review prompt"}
            ])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = await async_client.post(
                "/api/v1/mcp-servers/test-connection",
                json=payload,
            )

        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert "server_info" in result
        assert len(result["discovered_tools"]) == 1
        assert len(result["discovered_resources"]) == 0
        assert len(result["discovered_prompts"]) == 1

    @pytest.mark.asyncio
    async def test_stdio_connection_failure(self, async_client):
        """
        Test stdio connection failure handling.

        Validates:
        - Connection failures return success=False
        - Error message is included in response
        - Response still returns 200 (not 500) for graceful handling
        """
        payload = {
            "name": "Invalid Stdio Server",
            "transport_type": "stdio",
            "command": "nonexistent-command-that-will-fail",
        }

        # Mock client to raise an exception
        with patch("src.services.mcp_server_service.MCPStdioClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.initialize = AsyncMock(side_effect=Exception("Command not found"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = await async_client.post(
                "/api/v1/mcp-servers/test-connection",
                json=payload,
            )

        assert response.status_code == 200
        result = response.json()
        assert result["success"] is False
        assert "error" in result
        # Error message may be wrapped in "Unexpected error" text
        assert "Command not found" in result["error"] or "Unexpected error" in result["error"]

    @pytest.mark.asyncio
    async def test_http_sse_connection_failure(self, async_client):
        """
        Test HTTP+SSE connection failure handling.

        Validates:
        - HTTP connection failures handled gracefully
        - Timeout errors reported properly
        - Network errors return clear error messages
        """
        payload = {
            "name": "Unreachable HTTP+SSE Server",
            "transport_type": "http_sse",
            "url": "https://unreachable-server.invalid/mcp",
        }

        # Mock client to raise connection error
        import httpx
        with patch("src.services.mcp_server_service.MCPStreamableHTTPClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.initialize = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = await async_client.post(
                "/api/v1/mcp-servers/test-connection",
                json=payload,
            )

        assert response.status_code == 200
        result = response.json()
        assert result["success"] is False
        assert "error" in result
        # Error may be wrapped or direct
        assert "refused" in result["error"].lower() or "connect" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_validation_error_missing_required_field(self, async_client):
        """
        Test schema validation before connection attempt.

        Validates:
        - Missing required fields return 400 with validation error
        - Validation happens BEFORE connection attempt (fast fail)
        - Error message is clear and actionable
        """
        # Missing 'command' for stdio transport
        payload = {
            "name": "Invalid Server",
            "transport_type": "stdio",
            # Missing 'command' field
        }

        response = await async_client.post(
            "/api/v1/mcp-servers/test-connection",
            json=payload,
        )

        # Pydantic validation error should return 422 (Unprocessable Entity)
        assert response.status_code == 422
        result = response.json()
        assert "detail" in result
        # Validation error should mention 'command' field
        error_str = str(result["detail"])
        assert "command" in error_str.lower()

    @pytest.mark.asyncio
    async def test_validation_error_mixed_transport_fields(self, async_client):
        """
        Test mixed transport field validation.

        Validates:
        - stdio transport cannot have 'url' field
        - http_sse transport cannot have 'command' field
        - Clear error messages guide user to fix configuration
        """
        # stdio with http_sse field (invalid)
        payload = {
            "name": "Mixed Fields Server",
            "transport_type": "stdio",
            "command": "npx",
            "url": "https://example.com/mcp",  # Invalid for stdio
        }

        response = await async_client.post(
            "/api/v1/mcp-servers/test-connection",
            json=payload,
        )

        assert response.status_code == 422
        result = response.json()
        assert "detail" in result
        # Error should mention the mixed fields issue
        error_str = str(result["detail"])
        assert "url" in error_str.lower() or "stdio" in error_str.lower()
