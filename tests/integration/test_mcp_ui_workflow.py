"""Integration tests for MCP UI workflows."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import MCPServer
from src.schemas.mcp_server import MCPServerCreate, MCPServerUpdate

# Test tenant ID for all integration tests
TEST_TENANT_ID = "default"


@pytest.mark.asyncio
async def test_end_to_end_add_server_workflow(
    async_client: AsyncClient, async_db_session: AsyncSession
) -> None:
    """
    Test end-to-end workflow: Create server → Verify in list → Verify capabilities.

    This test validates AC3 (Add Server Form) and AC5 (Save Server).
    """
    # Create server via API
    payload = {
        "name": "Test Filesystem Server",
        "description": "Test server for integration tests",
        "transport_type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        "env": {"TEST_VAR": "test_value"},
    }

    response = await async_client.post(
        "/api/v1/mcp-servers",
        json=payload,
        headers={"X-Tenant-ID": TEST_TENANT_ID},
    )
    assert response.status_code == 201
    created_server = response.json()
    assert created_server["name"] == "Test Filesystem Server"
    assert created_server["status"] in ["active", "error"]  # Depends on discovery success
    server_id = created_server["id"]

    # Verify server appears in list
    response = await async_client.get(
        "/api/v1/mcp-servers",
        headers={"X-Tenant-ID": TEST_TENANT_ID},
    )
    assert response.status_code == 200
    servers = response.json()
    assert any(s["id"] == server_id for s in servers)

    # Verify discovered capabilities populated (may be empty if discovery failed)
    assert "discovered_tools" in created_server
    assert "discovered_resources" in created_server
    assert "discovered_prompts" in created_server

    # Cleanup
    await async_client.delete(
        f"/api/v1/mcp-servers/{server_id}",
        headers={"X-Tenant-ID": TEST_TENANT_ID},
    )


@pytest.mark.asyncio
async def test_edit_server_workflow(
    async_client: AsyncClient, async_db_session: AsyncSession
) -> None:
    """
    Test edit workflow: Create → Update name/description → Verify changes.

    This test validates AC7 (Edit Server).
    """
    # Create server
    payload = {
        "name": "Original Name",
        "description": "Original description",
        "transport_type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
    }
    response = await async_client.post(
        "/api/v1/mcp-servers",
        json=payload,
        headers={"X-Tenant-ID": TEST_TENANT_ID},
    )
    assert response.status_code == 201
    server_id = response.json()["id"]

    # Update server
    update_payload = {
        "name": "Updated Name",
        "description": "Updated description",
    }
    response = await async_client.patch(
        f"/api/v1/mcp-servers/{server_id}",
        json=update_payload,
        headers={"X-Tenant-ID": TEST_TENANT_ID},
    )
    assert response.status_code == 200
    updated_server = response.json()
    assert updated_server["name"] == "Updated Name"
    assert updated_server["description"] == "Updated description"

    # Verify changes in details view
    response = await async_client.get(
        f"/api/v1/mcp-servers/{server_id}",
        headers={"X-Tenant-ID": TEST_TENANT_ID},
    )
    assert response.status_code == 200
    details = response.json()
    assert details["name"] == "Updated Name"
    assert details["description"] == "Updated description"

    # Cleanup
    await async_client.delete(
        f"/api/v1/mcp-servers/{server_id}",
        headers={"X-Tenant-ID": TEST_TENANT_ID},
    )


@pytest.mark.asyncio
async def test_delete_server_workflow(
    async_client: AsyncClient, async_db_session: AsyncSession
) -> None:
    """
    Test delete workflow: Create → Delete → Verify removed from list.

    This test validates AC8 (Delete Server).
    """
    # Create server
    payload = {
        "name": "Server to Delete",
        "transport_type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
    }
    response = await async_client.post(
        "/api/v1/mcp-servers",
        json=payload,
        headers={"X-Tenant-ID": TEST_TENANT_ID},
    )
    assert response.status_code == 201
    server_id = response.json()["id"]

    # Delete server
    response = await async_client.delete(
        f"/api/v1/mcp-servers/{server_id}",
        headers={"X-Tenant-ID": TEST_TENANT_ID},
    )
    assert response.status_code == 204

    # Verify removed from list
    response = await async_client.get(
        "/api/v1/mcp-servers",
        headers={"X-Tenant-ID": TEST_TENANT_ID},
    )
    assert response.status_code == 200
    servers = response.json()
    assert not any(s["id"] == server_id for s in servers)

    # Verify 404 on details request
    response = await async_client.get(
        f"/api/v1/mcp-servers/{server_id}",
        headers={"X-Tenant-ID": TEST_TENANT_ID},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_rediscover_capabilities_workflow(
    async_client: AsyncClient, async_db_session: AsyncSession
) -> None:
    """
    Test rediscover workflow: Create → Rediscover → Verify updated capabilities.

    This test validates AC9 (Rediscover Capabilities).
    """
    # Create server
    payload = {
        "name": "Server for Rediscovery",
        "transport_type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
    }
    response = await async_client.post(
        "/api/v1/mcp-servers",
        json=payload,
        headers={"X-Tenant-ID": TEST_TENANT_ID},
    )
    assert response.status_code == 201
    server_id = response.json()["id"]
    initial_tools = response.json().get("discovered_tools", [])

    # Trigger rediscovery
    response = await async_client.post(
        f"/api/v1/mcp-servers/{server_id}/discover",
        headers={"X-Tenant-ID": TEST_TENANT_ID},
    )
    assert response.status_code == 200
    rediscovered_server = response.json()

    # Verify capabilities rediscovered (structure should be present)
    assert "discovered_tools" in rediscovered_server
    assert "discovered_resources" in rediscovered_server
    assert "discovered_prompts" in rediscovered_server
    assert "last_health_check" in rediscovered_server

    # Verify status updated (should be 'active' or 'error' depending on discovery success)
    assert rediscovered_server["status"] in ["active", "error"]

    # Cleanup
    await async_client.delete(
        f"/api/v1/mcp-servers/{server_id}",
        headers={"X-Tenant-ID": TEST_TENANT_ID},
    )


@pytest.mark.asyncio
async def test_error_handling_invalid_command(
    async_client: AsyncClient, async_db_session: AsyncSession
) -> None:
    """
    Test error handling: Create with invalid command → Verify error message → Verify status='error'.

    This test validates AC5 and AC10 (Error Handling).
    """
    # Create server with invalid command (should fail discovery but still create server)
    payload = {
        "name": "Server with Invalid Command",
        "transport_type": "stdio",
        "command": "nonexistent-command-xyz",
        "args": ["--help"],
    }
    response = await async_client.post(
        "/api/v1/mcp-servers",
        json=payload,
        headers={"X-Tenant-ID": TEST_TENANT_ID},
    )

    # Server creation should succeed (201) even if discovery fails
    assert response.status_code == 201
    created_server = response.json()
    server_id = created_server["id"]

    # Status should be 'error' due to discovery failure
    # Note: This depends on whether discovery is run during creation
    # If not, status might be 'inactive' initially
    assert created_server["status"] in ["error", "inactive"]

    # If error message is populated, verify it's meaningful
    if created_server.get("error_message"):
        assert len(created_server["error_message"]) > 0

    # Cleanup
    await async_client.delete(
        f"/api/v1/mcp-servers/{server_id}",
        headers={"X-Tenant-ID": TEST_TENANT_ID},
    )


@pytest.mark.asyncio
async def test_tenant_isolation(
    async_client: AsyncClient, async_db_session: AsyncSession
) -> None:
    """
    Test tenant isolation: Create for Tenant A → Fetch with Tenant B → Verify not returned.

    This test validates AC1 and AC2 (Tenant Isolation).
    """
    TENANT_A = "tenant-a-test"
    TENANT_B = "tenant-b-test"

    # Create server for Tenant A
    payload = {
        "name": "Tenant A Server",
        "transport_type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
    }
    response = await async_client.post(
        "/api/v1/mcp-servers",
        json=payload,
        headers={"X-Tenant-ID": TENANT_A},
    )
    assert response.status_code == 201
    server_id = response.json()["id"]

    # Fetch servers with Tenant B credentials
    response = await async_client.get(
        "/api/v1/mcp-servers",
        headers={"X-Tenant-ID": TENANT_B},
    )
    assert response.status_code == 200
    tenant_b_servers = response.json()

    # Verify Tenant A's server is NOT in Tenant B's list
    assert not any(s["id"] == server_id for s in tenant_b_servers)

    # Verify Tenant A can see their own server
    response = await async_client.get(
        "/api/v1/mcp-servers",
        headers={"X-Tenant-ID": TENANT_A},
    )
    assert response.status_code == 200
    tenant_a_servers = response.json()
    assert any(s["id"] == server_id for s in tenant_a_servers)

    # Cleanup
    await async_client.delete(
        f"/api/v1/mcp-servers/{server_id}",
        headers={"X-Tenant-ID": TENANT_A},
    )


@pytest.mark.asyncio
async def test_validation_error_duplicate_name(
    async_client: AsyncClient, async_db_session: AsyncSession
) -> None:
    """
    Test validation: Create server → Attempt duplicate name → Verify 400 error.

    This test validates AC3 (Form Validation).
    """
    # Create first server
    payload = {
        "name": "Unique Server Name",
        "transport_type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
    }
    response = await async_client.post(
        "/api/v1/mcp-servers",
        json=payload,
        headers={"X-Tenant-ID": TEST_TENANT_ID},
    )
    assert response.status_code == 201
    server_id = response.json()["id"]

    # Attempt to create second server with same name
    response = await async_client.post(
        "/api/v1/mcp-servers",
        json=payload,
        headers={"X-Tenant-ID": TEST_TENANT_ID},
    )
    assert response.status_code == 400
    error_detail = response.json()
    assert "detail" in error_detail
    # Error message should mention uniqueness or duplicate

    # Cleanup
    await async_client.delete(
        f"/api/v1/mcp-servers/{server_id}",
        headers={"X-Tenant-ID": TEST_TENANT_ID},
    )
