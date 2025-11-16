"""
Unit tests for MCP Server Service layer.

Tests business logic with mocked database and MCPStdioClient.
Validates CRUD operations, discovery workflow, and error handling.

Story 11.1.4: MCP Server Management API - Service layer unit tests.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.exc import IntegrityError

from src.database.models import MCPServer, MCPServerStatus, TransportType
from src.schemas.mcp_server import MCPServerCreate, MCPServerUpdate
from src.services.mcp_server_service import MCPServerService
from src.services.mcp_stdio_client import (
    MCPError,
    ProcessError,
    TimeoutError as MCPTimeoutError,
)


@pytest.fixture
def mock_db_session():
    """Mock async database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def service(mock_db_session):
    """MCP Server Service instance with mocked database."""
    return MCPServerService(mock_db_session)


@pytest.fixture
def tenant_id():
    """Tenant ID for testing."""
    return uuid4()


@pytest.fixture
def sample_server_data():
    """Sample MCP server create data."""
    return MCPServerCreate(
        name="test-server",
        description="Test MCP server",
        transport_type=TransportType.STDIO,
        command="npx",
        args=["-y", "@modelcontextprotocol/server-everything"],
        env={"LOG_LEVEL": "info"},
    )


class TestCreateServer:
    """Tests for create_server method."""

    @pytest.mark.asyncio
    async def test_create_server_success(
        self, service, mock_db_session, tenant_id, sample_server_data
    ):
        """Test creating server triggers discovery and returns server."""
        # Arrange
        mock_db_session.refresh.side_effect = lambda obj: setattr(
            obj, "id", uuid4()
        )

        with patch.object(
            service, "discover_capabilities", new_callable=AsyncMock
        ) as mock_discover:
            # Act
            server = await service.create_server(sample_server_data, tenant_id)

            # Assert
            assert server.name == "test-server"
            assert server.tenant_id == tenant_id
            assert server.status == MCPServerStatus.INACTIVE
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called()
            mock_discover.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_server_duplicate_name(
        self, service, mock_db_session, tenant_id, sample_server_data
    ):
        """Test creating server with duplicate name raises IntegrityError."""
        # Arrange
        mock_db_session.commit.side_effect = IntegrityError(
            "duplicate", None, None
        )

        # Act & Assert
        with pytest.raises(IntegrityError):
            await service.create_server(sample_server_data, tenant_id)

        mock_db_session.rollback.assert_called_once()


class TestListServers:
    """Tests for list_servers method."""

    @pytest.mark.asyncio
    async def test_list_servers_with_filters(
        self, service, mock_db_session, tenant_id
    ):
        """Test listing servers applies filters and pagination."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 5  # Total count
        mock_result.scalars.return_value.all.return_value = [
            MagicMock(spec=MCPServer)
        ]

        mock_db_session.execute.side_effect = [
            mock_result,  # Count query
            mock_result,  # Data query
        ]

        # Act
        servers, total = await service.list_servers(
            tenant_id,
            skip=0,
            limit=10,
            status=MCPServerStatus.ACTIVE,
            transport_type=TransportType.STDIO,
        )

        # Assert
        assert total == 5
        assert len(servers) == 1
        assert mock_db_session.execute.call_count == 2


class TestGetServerById:
    """Tests for get_server_by_id method."""

    @pytest.mark.asyncio
    async def test_get_server_exists(self, service, mock_db_session, tenant_id):
        """Test getting existing server returns server object."""
        # Arrange
        server_id = uuid4()
        mock_server = MagicMock(spec=MCPServer)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_server
        mock_db_session.execute.return_value = mock_result

        # Act
        server = await service.get_server_by_id(server_id, tenant_id)

        # Assert
        assert server == mock_server

    @pytest.mark.asyncio
    async def test_get_server_not_found(self, service, mock_db_session, tenant_id):
        """Test getting non-existent server returns None."""
        # Arrange
        server_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Act
        server = await service.get_server_by_id(server_id, tenant_id)

        # Assert
        assert server is None


class TestUpdateServer:
    """Tests for update_server method."""

    @pytest.mark.asyncio
    async def test_update_server_partial(self, service, mock_db_session, tenant_id):
        """Test partial update modifies only specified fields."""
        # Arrange
        server_id = uuid4()
        mock_server = MagicMock(spec=MCPServer)
        mock_server.name = "old-name"

        with patch.object(
            service, "get_server_by_id", return_value=mock_server
        ):
            updates = MCPServerUpdate(name="new-name")

            # Act
            server = await service.update_server(server_id, updates, tenant_id)

            # Assert
            assert server.name == "new-name"
            mock_db_session.commit.assert_called_once()


class TestDeleteServer:
    """Tests for delete_server method."""

    @pytest.mark.asyncio
    async def test_delete_server_success(self, service, mock_db_session, tenant_id):
        """Test deleting existing server returns True."""
        # Arrange
        server_id = uuid4()
        mock_server = MagicMock(spec=MCPServer)

        with patch.object(
            service, "get_server_by_id", return_value=mock_server
        ):
            # Act
            deleted = await service.delete_server(server_id, tenant_id)

            # Assert
            assert deleted is True
            mock_db_session.execute.assert_called_once()
            mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_server_not_found(
        self, service, mock_db_session, tenant_id
    ):
        """Test deleting non-existent server returns False."""
        # Arrange
        server_id = uuid4()

        with patch.object(service, "get_server_by_id", return_value=None):
            # Act
            deleted = await service.delete_server(server_id, tenant_id)

            # Assert
            assert deleted is False


class TestDiscoverCapabilities:
    """Tests for discover_capabilities method."""

    @pytest.mark.asyncio
    async def test_discover_success(self, service, mock_db_session):
        """Test successful discovery updates server with capabilities."""
        # Arrange
        server_id = uuid4()
        tenant_id = uuid4()
        now = datetime.now(timezone.utc)

        mock_server = MagicMock(spec=MCPServer)
        # Set all required fields for Pydantic validation
        mock_server.id = server_id
        mock_server.tenant_id = tenant_id
        mock_server.name = "test-server"
        mock_server.description = "Test MCP server"
        mock_server.transport_type = TransportType.STDIO
        mock_server.command = "npx"
        mock_server.args = ["-y", "@modelcontextprotocol/server-everything"]
        mock_server.env = {}
        mock_server.url = None
        mock_server.headers = {}
        mock_server.discovered_tools = []
        mock_server.discovered_resources = []
        mock_server.discovered_prompts = []
        mock_server.status = MCPServerStatus.INACTIVE
        mock_server.last_health_check = None
        mock_server.error_message = None
        mock_server.consecutive_failures = 0
        mock_server.created_at = now
        mock_server.updated_at = now

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_server
        mock_db_session.execute.return_value = mock_result

        mock_client = AsyncMock()
        mock_client.initialize = AsyncMock()
        mock_client.list_tools = AsyncMock(return_value=[{"name": "test_tool"}])
        mock_client.list_resources = AsyncMock(return_value=[])
        mock_client.list_prompts = AsyncMock(return_value=[])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "src.services.mcp_server_service.MCPStdioClient",
            return_value=mock_client,
        ):
            # Act
            await service.discover_capabilities(server_id)

            # Assert
            assert mock_server.status == MCPServerStatus.ACTIVE
            assert mock_server.discovered_tools == [{"name": "test_tool"}]
            assert mock_server.error_message is None
            mock_db_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_discover_timeout(self, service, mock_db_session):
        """Test discovery timeout sets status to error."""
        # Arrange
        server_id = uuid4()
        tenant_id = uuid4()
        now = datetime.now(timezone.utc)

        mock_server = MagicMock(spec=MCPServer)
        # Set all required fields for Pydantic validation
        mock_server.id = server_id
        mock_server.tenant_id = tenant_id
        mock_server.name = "test-server"
        mock_server.description = "Test MCP server"
        mock_server.transport_type = TransportType.STDIO
        mock_server.command = "npx"
        mock_server.args = ["-y", "@modelcontextprotocol/server-everything"]
        mock_server.env = {}
        mock_server.url = None
        mock_server.headers = {}
        mock_server.discovered_tools = []
        mock_server.discovered_resources = []
        mock_server.discovered_prompts = []
        mock_server.status = MCPServerStatus.INACTIVE
        mock_server.last_health_check = None
        mock_server.error_message = None
        mock_server.consecutive_failures = 0
        mock_server.created_at = now
        mock_server.updated_at = now

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_server
        mock_db_session.execute.return_value = mock_result

        mock_client = AsyncMock()
        mock_client.initialize.side_effect = MCPTimeoutError("Timeout")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "src.services.mcp_server_service.MCPStdioClient",
            return_value=mock_client,
        ):
            # Act
            await service.discover_capabilities(server_id)

            # Assert
            assert mock_server.status == MCPServerStatus.ERROR
            assert "timed out" in mock_server.error_message.lower()

    @pytest.mark.asyncio
    async def test_discover_process_error(self, service, mock_db_session):
        """Test discovery process error sets status to error."""
        # Arrange
        server_id = uuid4()
        tenant_id = uuid4()
        now = datetime.now(timezone.utc)

        mock_server = MagicMock(spec=MCPServer)
        # Set all required fields for Pydantic validation
        mock_server.id = server_id
        mock_server.tenant_id = tenant_id
        mock_server.name = "test-server"
        mock_server.description = "Test MCP server"
        mock_server.transport_type = TransportType.STDIO
        mock_server.command = "npx"
        mock_server.args = ["-y", "@modelcontextprotocol/server-everything"]
        mock_server.env = {}
        mock_server.url = None
        mock_server.headers = {}
        mock_server.discovered_tools = []
        mock_server.discovered_resources = []
        mock_server.discovered_prompts = []
        mock_server.status = MCPServerStatus.INACTIVE
        mock_server.last_health_check = None
        mock_server.error_message = None
        mock_server.consecutive_failures = 0
        mock_server.created_at = now
        mock_server.updated_at = now

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_server
        mock_db_session.execute.return_value = mock_result

        mock_client = AsyncMock()
        mock_client.initialize.side_effect = ProcessError("Process crashed")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "src.services.mcp_server_service.MCPStdioClient",
            return_value=mock_client,
        ):
            # Act
            await service.discover_capabilities(server_id)

            # Assert
            assert mock_server.status == MCPServerStatus.ERROR
            assert "failed" in mock_server.error_message.lower()


class TestCheckHealth:
    """Tests for check_health method."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, service, mock_db_session, tenant_id):
        """Test successful health check returns active status."""
        # Arrange
        server_id = uuid4()
        now = datetime.now(timezone.utc)

        mock_server = MagicMock(spec=MCPServer)
        # Set all required fields for Pydantic validation
        mock_server.id = server_id
        mock_server.tenant_id = tenant_id
        mock_server.name = "test-server"
        mock_server.description = "Test MCP server"
        mock_server.transport_type = TransportType.STDIO
        mock_server.command = "npx"
        mock_server.args = ["-y", "@modelcontextprotocol/server-everything"]
        mock_server.env = {}
        mock_server.url = None
        mock_server.headers = {}
        mock_server.discovered_tools = []
        mock_server.discovered_resources = []
        mock_server.discovered_prompts = []
        mock_server.status = MCPServerStatus.INACTIVE
        mock_server.last_health_check = None
        mock_server.error_message = None
        mock_server.consecutive_failures = 0
        mock_server.created_at = now
        mock_server.updated_at = now

        with patch.object(
            service, "get_server_by_id", return_value=mock_server
        ):
            mock_client = AsyncMock()
            mock_client.initialize = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch(
                "src.services.mcp_server_service.MCPStdioClient",
                return_value=mock_client,
            ):
                # Act
                health = await service.check_health(server_id, tenant_id)

                # Assert
                assert health["status"] == "active"
                assert health["response_time_ms"] >= 0  # Mock completes instantly
                assert health["error_message"] is None
                assert mock_server.status == MCPServerStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_health_check_timeout(self, service, mock_db_session, tenant_id):
        """Test health check timeout returns error status."""
        # Arrange
        server_id = uuid4()
        now = datetime.now(timezone.utc)

        mock_server = MagicMock(spec=MCPServer)
        # Set all required fields for Pydantic validation
        mock_server.id = server_id
        mock_server.tenant_id = tenant_id
        mock_server.name = "test-server"
        mock_server.description = "Test MCP server"
        mock_server.transport_type = TransportType.STDIO
        mock_server.command = "npx"
        mock_server.args = ["-y", "@modelcontextprotocol/server-everything"]
        mock_server.env = {}
        mock_server.url = None
        mock_server.headers = {}
        mock_server.discovered_tools = []
        mock_server.discovered_resources = []
        mock_server.discovered_prompts = []
        mock_server.status = MCPServerStatus.INACTIVE
        mock_server.last_health_check = None
        mock_server.error_message = None
        mock_server.consecutive_failures = 0
        mock_server.created_at = now
        mock_server.updated_at = now

        with patch.object(
            service, "get_server_by_id", return_value=mock_server
        ):
            mock_client = AsyncMock()
            mock_client.initialize.side_effect = MCPTimeoutError("Timeout")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch(
                "src.services.mcp_server_service.MCPStdioClient",
                return_value=mock_client,
            ):
                # Act
                health = await service.check_health(server_id, tenant_id)

                # Assert
                assert health["status"] == "error"
                assert "timed out" in health["error_message"].lower()

    @pytest.mark.asyncio
    async def test_health_check_not_found(
        self, service, mock_db_session, tenant_id
    ):
        """Test health check of non-existent server returns None."""
        # Arrange
        server_id = uuid4()

        with patch.object(service, "get_server_by_id", return_value=None):
            # Act
            health = await service.check_health(server_id, tenant_id)

            # Assert
            assert health is None
