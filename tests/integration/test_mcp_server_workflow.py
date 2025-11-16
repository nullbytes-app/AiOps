"""
Integration tests for MCP Server Management API workflow.

Tests end-to-end workflows with real database (test fixtures).
Validates complete CRUD operations, multi-tenant isolation, and pagination.

Story 11.1.4: MCP Server Management API - Integration tests.
"""

import pytest
from uuid import uuid4

from src.database.models import MCPServerStatus, TransportType
from src.schemas.mcp_server import MCPServerCreate


@pytest.mark.integration
class TestMCPServerEndToEndWorkflow:
    """Tests for complete MCP server lifecycle."""

    @pytest.mark.asyncio
    async def test_full_crud_workflow(
        self, async_client, async_db_session, mock_tenant_id
    ):
        """
        Test complete workflow: Create → List → Get → Update → Delete.

        This test uses mocked discovery to avoid subprocess spawning.
        """
        # Step 1: Create server (discovery will be mocked in service layer)
        server_data = {
            "name": "integration-test-server",
            "description": "Integration test MCP server",
            "transport_type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-everything"],
        }

        # Mock discovery to avoid real subprocess
        from unittest.mock import patch, AsyncMock
        with patch(
            "src.services.mcp_server_service.MCPStdioClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.initialize = AsyncMock()
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
        created_server = create_response.json()
        server_id = created_server["id"]
        assert created_server["name"] == "integration-test-server"

        # Step 2: List servers
        list_response = await async_client.get(
            "/api/v1/mcp-servers/",
            headers={"X-Tenant-ID": mock_tenant_id},
        )
        assert list_response.status_code == 200
        servers = list_response.json()
        assert len(servers) >= 1
        assert any(s["id"] == server_id for s in servers)

        # Step 3: Get server details
        get_response = await async_client.get(
            f"/api/v1/mcp-servers/{server_id}",
            headers={"X-Tenant-ID": mock_tenant_id},
        )
        assert get_response.status_code == 200
        server_details = get_response.json()
        assert server_details["name"] == "integration-test-server"

        # Step 4: Update server
        update_response = await async_client.patch(
            f"/api/v1/mcp-servers/{server_id}",
            json={"name": "updated-integration-server"},
            headers={"X-Tenant-ID": mock_tenant_id},
        )
        assert update_response.status_code == 200
        updated_server = update_response.json()
        assert updated_server["name"] == "updated-integration-server"

        # Step 5: Delete server
        delete_response = await async_client.delete(
            f"/api/v1/mcp-servers/{server_id}",
            headers={"X-Tenant-ID": mock_tenant_id},
        )
        assert delete_response.status_code == 204

        # Step 6: Verify deletion
        get_after_delete = await async_client.get(
            f"/api/v1/mcp-servers/{server_id}",
            headers={"X-Tenant-ID": mock_tenant_id},
        )
        assert get_after_delete.status_code == 404

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation(
        self, async_client, async_db_session
    ):
        """Test servers from different tenants are isolated."""
        tenant_a_id = str(uuid4())
        tenant_b_id = str(uuid4())

        server_data = {
            "name": "tenant-server",
            "transport_type": "stdio",
            "command": "npx",
        }

        # Mock discovery
        from unittest.mock import patch, AsyncMock
        with patch(
            "src.services.mcp_server_service.MCPStdioClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.initialize = AsyncMock()
            mock_client.list_tools = AsyncMock(return_value=[])
            mock_client.list_resources = AsyncMock(return_value=[])
            mock_client.list_prompts = AsyncMock(return_value=[])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Create server for Tenant A
            response_a = await async_client.post(
                "/api/v1/mcp-servers/",
                json=server_data,
                headers={"X-Tenant-ID": tenant_a_id},
            )
        assert response_a.status_code == 201
        server_a_id = response_a.json()["id"]

        # Tenant B should NOT see Tenant A's server
        get_response = await async_client.get(
            f"/api/v1/mcp-servers/{server_a_id}",
            headers={"X-Tenant-ID": tenant_b_id},
        )
        assert get_response.status_code == 404

        # Tenant A should see their own server
        get_response_a = await async_client.get(
            f"/api/v1/mcp-servers/{server_a_id}",
            headers={"X-Tenant-ID": tenant_a_id},
        )
        assert get_response_a.status_code == 200

    @pytest.mark.asyncio
    async def test_pagination_with_multiple_servers(
        self, async_client, mock_tenant_id
    ):
        """Test pagination works correctly with multiple servers."""
        # Create 5 servers
        from unittest.mock import patch, AsyncMock
        with patch(
            "src.services.mcp_server_service.MCPStdioClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.initialize = AsyncMock()
            mock_client.list_tools = AsyncMock(return_value=[])
            mock_client.list_resources = AsyncMock(return_value=[])
            mock_client.list_prompts = AsyncMock(return_value=[])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            for i in range(5):
                await async_client.post(
                    "/api/v1/mcp-servers/",
                    json={
                        "name": f"server-{i}",
                        "transport_type": "stdio",
                        "command": "npx",
                    },
                    headers={"X-Tenant-ID": mock_tenant_id},
                )

        # Test pagination (limit=2)
        page_1 = await async_client.get(
            "/api/v1/mcp-servers/?skip=0&limit=2",
            headers={"X-Tenant-ID": mock_tenant_id},
        )
        assert page_1.status_code == 200
        page_1_data = page_1.json()
        assert len(page_1_data) == 2

        # Test second page
        page_2 = await async_client.get(
            "/api/v1/mcp-servers/?skip=2&limit=2",
            headers={"X-Tenant-ID": mock_tenant_id},
        )
        assert page_2.status_code == 200
        page_2_data = page_2.json()
        assert len(page_2_data) == 2

        # Verify different results
        page_1_ids = {s["id"] for s in page_1_data}
        page_2_ids = {s["id"] for s in page_2_data}
        assert page_1_ids.isdisjoint(page_2_ids)

    @pytest.mark.asyncio
    async def test_filtering_by_status(
        self, async_client, async_db_session, mock_tenant_id
    ):
        """Test filtering servers by status."""
        # This test would require manipulating server status
        # For now, verify filter parameter is accepted
        response = await async_client.get(
            "/api/v1/mcp-servers/?status=active",
            headers={"X-Tenant-ID": mock_tenant_id},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_check_endpoint(
        self, async_client, mock_tenant_id
    ):
        """Test health check endpoint workflow."""
        # Create server first
        from unittest.mock import patch, AsyncMock
        with patch(
            "src.services.mcp_server_service.MCPStdioClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.initialize = AsyncMock()
            mock_client.list_tools = AsyncMock(return_value=[])
            mock_client.list_resources = AsyncMock(return_value=[])
            mock_client.list_prompts = AsyncMock(return_value=[])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            create_response = await async_client.post(
                "/api/v1/mcp-servers/",
                json={
                    "name": "health-test-server",
                    "transport_type": "stdio",
                    "command": "npx",
                },
                headers={"X-Tenant-ID": mock_tenant_id},
            )

        server_id = create_response.json()["id"]

        # Perform health check (mocked)
        with patch(
            "src.services.mcp_server_service.MCPStdioClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.initialize = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            health_response = await async_client.get(
                f"/api/v1/mcp-servers/{server_id}/health",
                headers={"X-Tenant-ID": mock_tenant_id},
            )

        assert health_response.status_code == 200
        health_data = health_response.json()
        assert "status" in health_data
        assert "response_time_ms" in health_data
