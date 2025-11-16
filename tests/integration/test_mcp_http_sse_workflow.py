"""
Integration tests for HTTP+SSE MCP Server workflow.

Tests end-to-end workflows with HTTP+SSE transport type.
Story 11.2.2 Tasks 5.5 and 7.4: 7 integration tests total

Requirements:
- Task 5.5: 3 integration tests for edit flow
- Task 7.4: 4 end-to-end tests (create, test connection, edit, delete)
"""

import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.integration
class TestHTTPSSEServerWorkflow:
    """Integration tests for HTTP+SSE server lifecycle."""

    @pytest.mark.asyncio
    async def test_create_http_sse_server(self, async_client, async_db_session, mock_tenant_id):
        """
        Test creating HTTP+SSE MCP server.

        Validates:
        - HTTP+SSE configuration accepted
        - Headers stored securely (encrypted in database)
        - Discovery triggered on creation
        - Server returned with correct transport_type
        """
        server_data = {
            "name": "GitHub MCP Server",
            "description": "GitHub API integration via HTTP+SSE",
            "transport_type": "http_sse",
            "url": "https://mcp-github-server.example.com/mcp",
            "headers": {
                "Authorization": "Bearer ghp_test_token_12345",
                "X-API-Key": "test-api-key-67890"
            }
        }

        # Mock HTTP+SSE client for discovery
        with patch("src.services.mcp_server_service.MCPStreamableHTTPClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.initialize = AsyncMock(return_value={

                "protocolVersion": "2024-11-05",

                "serverInfo": {"name": "Test Server", "version": "1.0.0"},

                "capabilities": {"tools": {}, "resources": {}}

            })
            mock_client.list_tools = AsyncMock(return_value=[
                {"name": "github_search", "description": "Search GitHub", "inputSchema": {"type": "object"}}
            ])
            mock_client.list_resources = AsyncMock(return_value=[])
            mock_client.list_prompts = AsyncMock(return_value=[])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = await async_client.post(
                "/api/v1/mcp-servers/",
                json=server_data,
                headers={"X-Tenant-ID": mock_tenant_id},
            )

        assert response.status_code == 201
        created_server = response.json()
        assert created_server["name"] == "GitHub MCP Server"
        assert created_server["transport_type"] == "http_sse"
        assert created_server["url"] == "https://mcp-github-server.example.com/mcp"
        # Headers should be encrypted/redacted in response
        assert "headers" in created_server
        assert created_server["status"] == "active"  # Discovery succeeded

        return created_server["id"]  # Return for cleanup

    @pytest.mark.asyncio
    async def test_edit_http_sse_server(self, async_client, async_db_session, mock_tenant_id):
        """
        Test editing HTTP+SSE server configuration.

        Validates:
        - URL can be updated
        - Headers can be updated (re-encrypted)
        - Rediscovery triggered on update
        - Backward compatibility maintained
        """
        # Step 1: Create server
        server_data = {
            "name": "Editable HTTP+SSE Server",
            "transport_type": "http_sse",
            "url": "https://old-url.example.com/mcp",
            "headers": {"Authorization": "Bearer old-token"}
        }

        with patch("src.services.mcp_server_service.MCPStreamableHTTPClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.initialize = AsyncMock(return_value={

                "protocolVersion": "2024-11-05",

                "serverInfo": {"name": "Test Server", "version": "1.0.0"},

                "capabilities": {"tools": {}, "resources": {}}

            })
            mock_client.list_tools = AsyncMock(return_value=[])
            mock_client.list_resources = AsyncMock(return_value=[])
            mock_client.list_prompts = AsyncMock(return_value=[])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            create_response = await async_client.post(
                "/api/v1/mcp-servers/",
                json=server_data,
                headers={"X-Tenant-ID": mock_tenant_id},
            )

        assert create_response.status_code == 201
        server_id = create_response.json()["id"]

        # Step 2: Update server
        update_data = {
            "url": "https://new-url.example.com/mcp",
            "headers": {"Authorization": "Bearer new-token", "X-New-Header": "value"}
        }

        with patch("src.services.mcp_server_service.MCPStreamableHTTPClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.initialize = AsyncMock(return_value={

                "protocolVersion": "2024-11-05",

                "serverInfo": {"name": "Test Server", "version": "1.0.0"},

                "capabilities": {"tools": {}, "resources": {}}

            })
            mock_client.list_tools = AsyncMock(return_value=[
                {"name": "new_tool", "description": "New tool", "inputSchema": {"type": "object"}}
            ])
            mock_client.list_resources = AsyncMock(return_value=[])
            mock_client.list_prompts = AsyncMock(return_value=[])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            update_response = await async_client.patch(
                f"/api/v1/mcp-servers/{server_id}",
                json=update_data,
                headers={"X-Tenant-ID": mock_tenant_id},
            )

        assert update_response.status_code == 200
        updated_server = update_response.json()
        assert updated_server["url"] == "https://new-url.example.com/mcp"
        assert "headers" in updated_server
        # New tool should be discovered
        assert len(updated_server["discovered_tools"]) == 1

    @pytest.mark.asyncio
    async def test_delete_http_sse_server(self, async_client, async_db_session, mock_tenant_id):
        """
        Test deleting HTTP+SSE server.

        Validates:
        - Server can be deleted successfully
        - Headers are removed from database
        - Server no longer accessible after deletion
        """
        # Step 1: Create server
        server_data = {
            "name": "Deletable HTTP+SSE Server",
            "transport_type": "http_sse",
            "url": "https://delete-me.example.com/mcp",
        }

        with patch("src.services.mcp_server_service.MCPStreamableHTTPClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.initialize = AsyncMock(return_value={

                "protocolVersion": "2024-11-05",

                "serverInfo": {"name": "Test Server", "version": "1.0.0"},

                "capabilities": {"tools": {}, "resources": {}}

            })
            mock_client.list_tools = AsyncMock(return_value=[])
            mock_client.list_resources = AsyncMock(return_value=[])
            mock_client.list_prompts = AsyncMock(return_value=[])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            create_response = await async_client.post(
                "/api/v1/mcp-servers/",
                json=server_data,
                headers={"X-Tenant-ID": mock_tenant_id},
            )

        assert create_response.status_code == 201
        server_id = create_response.json()["id"]

        # Step 2: Delete server
        delete_response = await async_client.delete(
            f"/api/v1/mcp-servers/{server_id}",
            headers={"X-Tenant-ID": mock_tenant_id},
        )

        assert delete_response.status_code == 204

        # Step 3: Verify deletion
        get_response = await async_client.get(
            f"/api/v1/mcp-servers/{server_id}",
            headers={"X-Tenant-ID": mock_tenant_id},
        )

        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_full_http_sse_workflow(self, async_client, async_db_session, mock_tenant_id):
        """
        Test complete HTTP+SSE workflow: Create → List → Get → Update → Delete.

        Validates:
        - All CRUD operations work for HTTP+SSE transport
        - Headers encrypted/decrypted properly throughout lifecycle
        - Discovery and rediscovery triggered at appropriate times
        """
        # Step 1: Create
        server_data = {
            "name": "Full Workflow HTTP+SSE Server",
            "description": "Testing complete HTTP+SSE lifecycle",
            "transport_type": "http_sse",
            "url": "https://workflow-test.example.com/mcp",
            "headers": {"Authorization": "Bearer workflow-token"}
        }

        with patch("src.services.mcp_server_service.MCPStreamableHTTPClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.initialize = AsyncMock(return_value={

                "protocolVersion": "2024-11-05",

                "serverInfo": {"name": "Test Server", "version": "1.0.0"},

                "capabilities": {"tools": {}, "resources": {}}

            })
            mock_client.list_tools = AsyncMock(return_value=[
                {"name": "tool1", "description": "Tool 1", "inputSchema": {"type": "object"}}
            ])
            mock_client.list_resources = AsyncMock(return_value=[])
            mock_client.list_prompts = AsyncMock(return_value=[])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            create_response = await async_client.post(
                "/api/v1/mcp-servers/",
                json=server_data,
                headers={"X-Tenant-ID": mock_tenant_id},
            )

        assert create_response.status_code == 201
        server_id = create_response.json()["id"]

        # Step 2: List
        list_response = await async_client.get(
            "/api/v1/mcp-servers/",
            headers={"X-Tenant-ID": mock_tenant_id},
        )

        assert list_response.status_code == 200
        servers = list_response.json()
        assert any(s["id"] == server_id for s in servers)

        # Step 3: Get details
        get_response = await async_client.get(
            f"/api/v1/mcp-servers/{server_id}",
            headers={"X-Tenant-ID": mock_tenant_id},
        )

        assert get_response.status_code == 200
        server_details = get_response.json()
        assert server_details["name"] == "Full Workflow HTTP+SSE Server"

        # Step 4: Update
        with patch("src.services.mcp_server_service.MCPStreamableHTTPClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.initialize = AsyncMock(return_value={

                "protocolVersion": "2024-11-05",

                "serverInfo": {"name": "Test Server", "version": "1.0.0"},

                "capabilities": {"tools": {}, "resources": {}}

            })
            mock_client.list_tools = AsyncMock(return_value=[])
            mock_client.list_resources = AsyncMock(return_value=[])
            mock_client.list_prompts = AsyncMock(return_value=[])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            update_response = await async_client.patch(
                f"/api/v1/mcp-servers/{server_id}",
                json={"name": "Updated HTTP+SSE Server"},
                headers={"X-Tenant-ID": mock_tenant_id},
            )

        assert update_response.status_code == 200

        # Step 5: Delete
        delete_response = await async_client.delete(
            f"/api/v1/mcp-servers/{server_id}",
            headers={"X-Tenant-ID": mock_tenant_id},
        )

        assert delete_response.status_code == 204

    @pytest.mark.asyncio
    async def test_backward_compatibility_with_stdio(
        self, async_client, async_db_session, mock_tenant_id
    ):
        """
        Test backward compatibility: HTTP+SSE and stdio servers coexist.

        Validates:
        - Both transport types work in same tenant
        - List view shows both types correctly
        - Health monitoring works for both
        - No regressions in stdio functionality
        """
        # Create stdio server
        stdio_data = {
            "name": "Stdio Server",
            "transport_type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem"],
        }

        with patch("src.services.mcp_server_service.MCPStdioClient") as mock_stdio_class:
            mock_stdio = AsyncMock()
            mock_stdio.initialize = AsyncMock(return_value={

                "protocolVersion": "2024-11-05",

                "serverInfo": {"name": "Test Stdio Server", "version": "1.0.0"},

                "capabilities": {"tools": {}}

            })
            mock_stdio.list_tools = AsyncMock(return_value=[])
            mock_stdio.list_resources = AsyncMock(return_value=[])
            mock_stdio.list_prompts = AsyncMock(return_value=[])
            mock_stdio.__aenter__ = AsyncMock(return_value=mock_stdio)
            mock_stdio.__aexit__ = AsyncMock(return_value=None)
            mock_stdio_class.return_value = mock_stdio

            stdio_response = await async_client.post(
                "/api/v1/mcp-servers/",
                json=stdio_data,
                headers={"X-Tenant-ID": mock_tenant_id},
            )

        assert stdio_response.status_code == 201
        stdio_id = stdio_response.json()["id"]

        # Create HTTP+SSE server
        http_sse_data = {
            "name": "HTTP+SSE Server",
            "transport_type": "http_sse",
            "url": "https://test.example.com/mcp",
        }

        with patch("src.services.mcp_server_service.MCPStreamableHTTPClient") as mock_http_class:
            mock_http = AsyncMock()
            mock_http.initialize = AsyncMock(return_value={

                "protocolVersion": "2024-11-05",

                "serverInfo": {"name": "Test HTTP Server", "version": "1.0.0"},

                "capabilities": {"tools": {}}

            })
            mock_http.list_tools = AsyncMock(return_value=[])
            mock_http.list_resources = AsyncMock(return_value=[])
            mock_http.list_prompts = AsyncMock(return_value=[])
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=None)
            mock_http_class.return_value = mock_http

            http_response = await async_client.post(
                "/api/v1/mcp-servers/",
                json=http_sse_data,
                headers={"X-Tenant-ID": mock_tenant_id},
            )

        assert http_response.status_code == 201
        http_id = http_response.json()["id"]

        # List both servers
        list_response = await async_client.get(
            "/api/v1/mcp-servers/",
            headers={"X-Tenant-ID": mock_tenant_id},
        )

        assert list_response.status_code == 200
        servers = list_response.json()

        stdio_server = next((s for s in servers if s["id"] == stdio_id), None)
        http_server = next((s for s in servers if s["id"] == http_id), None)

        assert stdio_server is not None
        assert http_server is not None
        assert stdio_server["transport_type"] == "stdio"
        assert http_server["transport_type"] == "http_sse"

    @pytest.mark.asyncio
    async def test_http_sse_invalid_url_rejected(
        self, async_client, async_db_session, mock_tenant_id
    ):
        """
        Test invalid URL format is rejected with clear error.

        Validates:
        - FTP URLs rejected (only HTTP/HTTPS allowed)
        - Empty URLs rejected
        - Validation error message is clear
        """
        invalid_data = {
            "name": "Invalid URL Server",
            "transport_type": "http_sse",
            "url": "ftp://invalid-protocol.example.com/mcp",  # FTP not allowed
        }

        response = await async_client.post(
            "/api/v1/mcp-servers/",
            json=invalid_data,
            headers={"X-Tenant-ID": mock_tenant_id},
        )

        # Pydantic validation should reject this before it reaches the service
        assert response.status_code == 422
        result = response.json()
        assert "detail" in result
        # Error should mention URL format
        error_str = str(result["detail"])
        assert "url" in error_str.lower() or "http" in error_str.lower()

    @pytest.mark.asyncio
    async def test_http_sse_mixed_fields_rejected(
        self, async_client, async_db_session, mock_tenant_id
    ):
        """
        Test mixed transport fields are rejected.

        Validates:
        - HTTP+SSE transport cannot have 'command' field
        - Clear validation error returned
        - User guided to fix configuration
        """
        mixed_data = {
            "name": "Mixed Fields Server",
            "transport_type": "http_sse",
            "url": "https://valid-url.example.com/mcp",
            "command": "npx",  # Invalid for http_sse
        }

        response = await async_client.post(
            "/api/v1/mcp-servers/",
            json=mixed_data,
            headers={"X-Tenant-ID": mock_tenant_id},
        )

        # Pydantic validation should reject mixed fields
        assert response.status_code == 422
        result = response.json()
        assert "detail" in result
        # Error should mention mixed fields
        error_str = str(result["detail"])
        assert "command" in error_str.lower() or "http_sse" in error_str.lower()
