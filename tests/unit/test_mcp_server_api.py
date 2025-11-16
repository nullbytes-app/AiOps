"""
Unit tests for MCP Server API endpoints.

Tests all REST endpoints with mocked service layer.
Validates HTTP status codes, response schemas, and error handling.

Story 11.1.4: MCP Server Management API - API endpoint unit tests.
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from src.database.models import MCPServer, MCPServerStatus, TransportType


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_tenant_id():
    """Mock tenant ID for testing."""
    return str(uuid4())


@pytest.fixture
def app(mock_db, mock_tenant_id):
    """FastAPI test app with dependency overrides."""
    from src.api.dependencies import get_tenant_db, get_tenant_id
    from src.api.mcp_servers import router

    app = FastAPI()
    app.include_router(router)

    # Override dependencies to use mocks
    async def override_get_tenant_db():
        yield mock_db

    async def override_get_tenant_id():
        return mock_tenant_id

    app.dependency_overrides[get_tenant_db] = override_get_tenant_db
    app.dependency_overrides[get_tenant_id] = override_get_tenant_id
    return app


@pytest.fixture
def client(app):
    """Test client for API calls."""
    return TestClient(app)


@pytest.fixture
def sample_server():
    """Sample MCP server for testing."""
    server_id = uuid4()
    tenant_id = uuid4()
    now = datetime.now(timezone.utc)

    return MCPServer(
        id=server_id,
        tenant_id=tenant_id,
        name="test-server",
        description="Test MCP server",
        transport_type=TransportType.STDIO,
        command="npx",
        args=["-y", "@modelcontextprotocol/server-everything"],
        env={"LOG_LEVEL": "info"},
        headers={},
        discovered_tools=[
            {"name": "test_tool", "description": "A test tool", "inputSchema": {}}
        ],
        discovered_resources=[
            {
                "uri": "test://resource",
                "name": "test_resource",
                "description": "A test resource",
                "mimeType": "text/plain",
            }
        ],
        discovered_prompts=[
            {"name": "test_prompt", "description": "A test prompt", "arguments": []}
        ],
        status=MCPServerStatus.ACTIVE,
        last_health_check=None,
        error_message=None,
        consecutive_failures=0,  # Required by Pydantic MCPServerResponse
        created_at=now,
        updated_at=now,
    )


class TestCreateMCPServer:
    """Tests for POST /api/v1/mcp-servers endpoint."""

    @patch("src.api.mcp_servers.MCPServerService")
    def test_create_stdio_server_success(
        self, mock_service_class, client, sample_server
    ):
        """Test creating stdio MCP server returns 201 Created."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.create_server.return_value = sample_server
        mock_service_class.return_value = mock_service

        server_data = {
            "name": "test-server",
            "description": "Test MCP server",
            "transport_type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-everything"],
            "env": {"LOG_LEVEL": "info"},
        }

        # Act
        response = client.post("/api/v1/mcp-servers/", json=server_data)

        # Debug: Print error if not 201
        if response.status_code != status.HTTP_201_CREATED:
            print(f"\nDEBUG - Status: {response.status_code}")
            print(f"DEBUG - Response: {response.json()}\n")

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "test-server"
        assert data["transport_type"] == "stdio"
        assert data["status"] == "active"
        assert len(data["discovered_tools"]) == 1

    @patch("src.api.mcp_servers.MCPServerService")
    def test_create_http_sse_server_success(
        self, mock_service_class, client, mock_tenant_id
    ):
        """Test creating HTTP/SSE MCP server returns 201 Created."""
        # Arrange
        now = datetime.now(timezone.utc)
        http_server = MCPServer(
            id=uuid4(),
            tenant_id=uuid4(),
            name="http-server",
            description="HTTP MCP server",
            transport_type=TransportType.HTTP_SSE,
            url="https://example.com/mcp",
            headers={"Authorization": "Bearer token123"},
            command=None,  # Not used for HTTP transport
            args=[],
            env={},
            discovered_tools=[],
            discovered_resources=[],
            discovered_prompts=[],
            status=MCPServerStatus.ACTIVE,
            last_health_check=None,
            error_message=None,
            consecutive_failures=0,  # Required by Pydantic MCPServerResponse
            created_at=now,
            updated_at=now,
        )
        mock_service = AsyncMock()
        mock_service.create_server.return_value = http_server
        mock_service_class.return_value = mock_service

        server_data = {
            "name": "http-server",
            "description": "HTTP MCP server",
            "transport_type": "http_sse",
            "url": "https://example.com/mcp",
            "headers": {"Authorization": "Bearer token123"},
        }

        # Act
        response = client.post("/api/v1/mcp-servers/", json=server_data)

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["transport_type"] == "http_sse"
        assert data["url"] == "https://example.com/mcp"

    @patch("src.api.mcp_servers.MCPServerService")
    def test_create_server_duplicate_name(
        self, mock_service_class, client, mock_tenant_id
    ):
        """Test creating server with duplicate name returns 409 Conflict."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.create_server.side_effect = Exception(
            "duplicate key value violates unique constraint"
        )
        mock_service_class.return_value = mock_service

        server_data = {
            "name": "duplicate-server",
            "transport_type": "stdio",
            "command": "npx",
        }

        # Act
        response = client.post("/api/v1/mcp-servers/", json=server_data)

        # Assert
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response.json()["detail"]


class TestListMCPServers:
    """Tests for GET /api/v1/mcp-servers endpoint."""

    @patch("src.api.mcp_servers.MCPServerService")
    def test_list_servers_empty(self, mock_service_class, client, mock_tenant_id):
        """Test listing servers returns empty array when no servers exist."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.list_servers.return_value = ([], 0)
        mock_service_class.return_value = mock_service

        # Act
        response = client.get("/api/v1/mcp-servers/")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    @patch("src.api.mcp_servers.MCPServerService")
    def test_list_servers_pagination(
        self, mock_service_class, client, mock_tenant_id, sample_server
    ):
        """Test listing servers with pagination parameters."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.list_servers.return_value = ([sample_server], 1)
        mock_service_class.return_value = mock_service

        # Act
        response = client.get("/api/v1/mcp-servers/?skip=0&limit=50")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        mock_service.list_servers.assert_called_once()

    @patch("src.api.mcp_servers.MCPServerService")
    def test_list_servers_filter_by_status(
        self, mock_service_class, client, mock_tenant_id, sample_server
    ):
        """Test filtering servers by status."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.list_servers.return_value = ([sample_server], 1)
        mock_service_class.return_value = mock_service

        # Act
        response = client.get("/api/v1/mcp-servers/?status=active")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "active"


class TestGetMCPServer:
    """Tests for GET /api/v1/mcp-servers/{id} endpoint."""

    @patch("src.api.mcp_servers.MCPServerService")
    def test_get_server_success(
        self, mock_service_class, client, mock_tenant_id, sample_server
    ):
        """Test getting server by ID returns 200 OK with complete details."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.get_server_by_id.return_value = sample_server
        mock_service_class.return_value = mock_service

        # Act
        response = client.get(f"/api/v1/mcp-servers/{sample_server.id}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "test-server"
        assert len(data["discovered_tools"]) == 1
        assert len(data["discovered_resources"]) == 1

    @patch("src.api.mcp_servers.MCPServerService")
    def test_get_server_not_found(
        self, mock_service_class, client, mock_tenant_id
    ):
        """Test getting non-existent server returns 404 Not Found."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.get_server_by_id.return_value = None
        mock_service_class.return_value = mock_service

        # Act
        response = client.get(f"/api/v1/mcp-servers/{uuid4()}")

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()


class TestUpdateMCPServer:
    """Tests for PATCH /api/v1/mcp-servers/{id} endpoint."""

    @patch("src.api.mcp_servers.MCPServerService")
    def test_update_server_partial(
        self, mock_service_class, client, mock_tenant_id, sample_server
    ):
        """Test partial update returns 200 OK with updated server."""
        # Arrange
        updated_server = sample_server
        updated_server.name = "updated-server"
        mock_service = AsyncMock()
        mock_service.update_server.return_value = updated_server
        mock_service_class.return_value = mock_service

        update_data = {"name": "updated-server"}

        # Act
        response = client.patch(
            f"/api/v1/mcp-servers/{sample_server.id}", json=update_data
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "updated-server"

    @patch("src.api.mcp_servers.MCPServerService")
    def test_update_server_not_found(
        self, mock_service_class, client, mock_tenant_id
    ):
        """Test updating non-existent server returns 404 Not Found."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.update_server.return_value = None
        mock_service_class.return_value = mock_service

        update_data = {"name": "new-name"}

        # Act
        response = client.patch(
            f"/api/v1/mcp-servers/{uuid4()}", json=update_data
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDeleteMCPServer:
    """Tests for DELETE /api/v1/mcp-servers/{id} endpoint."""

    @patch("src.api.mcp_servers.MCPServerService")
    def test_delete_server_success(
        self, mock_service_class, client, mock_tenant_id, sample_server
    ):
        """Test deleting server returns 204 No Content."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.delete_server.return_value = True
        mock_service_class.return_value = mock_service

        # Act
        response = client.delete(f"/api/v1/mcp-servers/{sample_server.id}")

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT

    @patch("src.api.mcp_servers.MCPServerService")
    def test_delete_server_not_found(
        self, mock_service_class, client, mock_tenant_id
    ):
        """Test deleting non-existent server returns 404 Not Found."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.delete_server.return_value = False
        mock_service_class.return_value = mock_service

        # Act
        response = client.delete(f"/api/v1/mcp-servers/{uuid4()}")

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestRediscoverMCPServer:
    """Tests for POST /api/v1/mcp-servers/{id}/discover endpoint."""

    @patch("src.api.mcp_servers.MCPServerService")
    def test_rediscover_success(
        self, mock_service_class, client, mock_tenant_id, sample_server
    ):
        """Test force rediscovery returns 200 OK with updated server."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.get_server_by_id.return_value = sample_server
        mock_service.discover_capabilities.return_value = None
        mock_service_class.return_value = mock_service

        # Act
        response = client.post(f"/api/v1/mcp-servers/{sample_server.id}/discover")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "test-server"
        mock_service.discover_capabilities.assert_called_once()

    @patch("src.api.mcp_servers.MCPServerService")
    def test_rediscover_not_found(
        self, mock_service_class, client, mock_tenant_id
    ):
        """Test rediscovery of non-existent server returns 404 Not Found."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.get_server_by_id.return_value = None
        mock_service_class.return_value = mock_service

        # Act
        response = client.post(f"/api/v1/mcp-servers/{uuid4()}/discover")

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestHealthCheckMCPServer:
    """Tests for GET /api/v1/mcp-servers/{id}/health endpoint."""

    @patch("src.api.mcp_servers.MCPServerService")
    def test_health_check_success(
        self, mock_service_class, client, mock_tenant_id, sample_server
    ):
        """Test health check returns 200 OK with health status."""
        # Arrange
        health_status = {
            "server_id": str(sample_server.id),
            "status": "active",
            "last_check": "2025-11-09T12:00:00Z",
            "response_time_ms": 150,
            "error_message": None,
        }
        mock_service = AsyncMock()
        mock_service.check_health.return_value = health_status
        mock_service_class.return_value = mock_service

        # Act
        response = client.get(f"/api/v1/mcp-servers/{sample_server.id}/health")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "active"
        assert data["response_time_ms"] == 150

    @patch("src.api.mcp_servers.MCPServerService")
    def test_health_check_failure(
        self, mock_service_class, client, mock_tenant_id, sample_server
    ):
        """Test health check returns error status when server unreachable."""
        # Arrange
        health_status = {
            "server_id": str(sample_server.id),
            "status": "error",
            "last_check": "2025-11-09T12:00:00Z",
            "response_time_ms": 0,
            "error_message": "Health check timed out",
        }
        mock_service = AsyncMock()
        mock_service.check_health.return_value = health_status
        mock_service_class.return_value = mock_service

        # Act
        response = client.get(f"/api/v1/mcp-servers/{sample_server.id}/health")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "error"
        assert data["error_message"] is not None

    @patch("src.api.mcp_servers.MCPServerService")
    def test_health_check_not_found(
        self, mock_service_class, client, mock_tenant_id
    ):
        """Test health check of non-existent server returns 404 Not Found."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.check_health.return_value = None
        mock_service_class.return_value = mock_service

        # Act
        response = client.get(f"/api/v1/mcp-servers/{uuid4()}/health")

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
