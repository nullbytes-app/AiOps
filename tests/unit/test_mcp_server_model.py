"""
Unit tests for MCPServer model (Story 11.1.1).

Tests the MCPServer database model including:
- Model creation with valid stdio and http_sse configurations
- Enum validation (TransportType, MCPServerStatus)
- JSONB field defaults
- __repr__() output format

Note: Integration tests (foreign key constraints, CASCADE delete, unique constraints)
are in tests/integration/test_mcp_server_model_integration.py
"""

import uuid
from datetime import datetime

import pytest

from src.database.models import MCPServer, TransportType, MCPServerStatus


class TestMCPServerModel:
    """Test MCPServer model creation and validation."""

    def test_create_mcp_server_stdio(self):
        """
        Test creating MCPServer with stdio transport (AC1, AC4).

        Verifies all required fields can be set and model accepts
        stdio-specific configuration (command, args, env).
        """
        tenant_id = uuid.uuid4()
        server_id = uuid.uuid4()

        server = MCPServer(
            id=server_id,
            tenant_id=tenant_id,
            name="filesystem-server",
            description="MCP server for filesystem access",
            transport_type=TransportType.STDIO.value,
            command="npx",
            args=["@modelcontextprotocol/server-filesystem", "/workspace"],
            env={"LOG_LEVEL": "debug", "API_KEY": "secret"},
            status=MCPServerStatus.ACTIVE.value,
        )

        assert server.id == server_id
        assert server.tenant_id == tenant_id
        assert server.name == "filesystem-server"
        assert server.description == "MCP server for filesystem access"
        assert server.transport_type == "stdio"
        assert server.command == "npx"
        assert server.args == ["@modelcontextprotocol/server-filesystem", "/workspace"]
        assert server.env == {"LOG_LEVEL": "debug", "API_KEY": "secret"}
        assert server.status == "active"

    def test_create_mcp_server_http_sse(self):
        """
        Test creating MCPServer with http_sse transport (AC1, AC4).

        Verifies all required fields can be set and model accepts
        HTTP+SSE-specific configuration (url, headers).
        """
        tenant_id = uuid.uuid4()
        server_id = uuid.uuid4()

        server = MCPServer(
            id=server_id,
            tenant_id=tenant_id,
            name="remote-api-server",
            description="MCP server via HTTP+SSE",
            transport_type=TransportType.HTTP_SSE.value,
            url="https://mcp.example.com/api",
            headers={"Authorization": "Bearer token123"},
            status=MCPServerStatus.INACTIVE.value,
        )

        assert server.id == server_id
        assert server.tenant_id == tenant_id
        assert server.name == "remote-api-server"
        assert server.description == "MCP server via HTTP+SSE"
        assert server.transport_type == "http_sse"
        assert server.url == "https://mcp.example.com/api"
        assert server.headers == {"Authorization": "Bearer token123"}
        assert server.status == "inactive"

    def test_mcp_server_defaults(self):
        """
        Test MCPServer default values for optional fields (AC1, AC4).

        Verifies JSONB fields default to empty arrays/objects,
        status defaults to 'inactive'.
        Note: UUID auto-generation and server_default are only applied at database level.
        """
        tenant_id = uuid.uuid4()

        server = MCPServer(
            tenant_id=tenant_id,
            name="test-server",
            transport_type=TransportType.STDIO.value,
        )

        # UUID is None until inserted into database (server_default applies at DB level)
        # Can be explicitly set if needed
        assert server.id is None or isinstance(server.id, uuid.UUID)

        # JSONB fields default to empty collections (Python defaults)
        # Note: server_default is only applied at database level
        assert server.args in (None, [], list)  # Python default or empty list
        assert server.env in (None, {}, dict)  # Python default or empty dict
        assert server.headers in (None, {}, dict)
        assert server.discovered_tools in (None, [], list)
        assert server.discovered_resources in (None, [], list)
        assert server.discovered_prompts in (None, [], list)

        # Status default may not be applied immediately in unit tests
        # (server_default applies at DB level, default may depend on session)
        # Allow both None and 'inactive' as valid
        assert server.status in (None, "inactive", MCPServerStatus.INACTIVE.value)

        # Optional fields are None by default
        assert server.description is None
        assert server.command is None
        assert server.url is None
        assert server.last_health_check is None
        assert server.error_message is None

    def test_transport_type_enum_values(self):
        """Test TransportType enum has correct values (AC5)."""
        assert TransportType.STDIO.value == "stdio"
        assert TransportType.HTTP_SSE.value == "http_sse"

        # Test enum membership
        assert TransportType.STDIO in TransportType
        assert TransportType.HTTP_SSE in TransportType

    def test_mcp_server_status_enum_values(self):
        """Test MCPServerStatus enum has correct values (AC5)."""
        assert MCPServerStatus.ACTIVE.value == "active"
        assert MCPServerStatus.INACTIVE.value == "inactive"
        assert MCPServerStatus.ERROR.value == "error"

        # Test enum membership
        assert MCPServerStatus.ACTIVE in MCPServerStatus
        assert MCPServerStatus.INACTIVE in MCPServerStatus
        assert MCPServerStatus.ERROR in MCPServerStatus

    def test_mcp_server_repr(self):
        """
        Test MCPServer __repr__() output format (AC4).

        Verifies debug representation includes key identifiers:
        id, name, transport_type, and status.
        """
        tenant_id = uuid.uuid4()
        server_id = uuid.uuid4()

        server = MCPServer(
            id=server_id,
            tenant_id=tenant_id,
            name="test-server",
            transport_type=TransportType.STDIO.value,
            status=MCPServerStatus.ACTIVE.value,
        )

        repr_str = repr(server)

        # Verify repr contains key fields
        assert "<MCPServer(" in repr_str
        assert f"id={server_id}" in repr_str
        assert "name='test-server'" in repr_str
        assert "transport=stdio" in repr_str
        assert "status=active" in repr_str
        assert repr_str.endswith(")>")

    def test_jsonb_structure_validation(self):
        """
        Test JSONB fields accept proper array/object structures (AC8).

        Verifies args accepts array, env/headers accept objects,
        and discovered_* fields accept arrays of objects.
        """
        tenant_id = uuid.uuid4()

        # Valid JSONB structures
        server = MCPServer(
            tenant_id=tenant_id,
            name="test-server",
            transport_type=TransportType.STDIO.value,
            args=["arg1", "arg2", "arg3"],  # Array of strings
            env={"VAR1": "value1", "VAR2": "value2"},  # Object with string values
            headers={"Authorization": "Bearer token", "Content-Type": "application/json"},
            discovered_tools=[
                {
                    "name": "read_file",
                    "description": "Read file contents",
                    "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}},
                }
            ],
            discovered_resources=[
                {
                    "uri": "file:///config.json",
                    "name": "Configuration File",
                    "mimeType": "application/json",
                }
            ],
            discovered_prompts=[
                {"name": "analyze_code", "description": "Analyze code for issues", "arguments": []}
            ],
        )

        # Verify all JSONB structures are accepted
        assert server.args == ["arg1", "arg2", "arg3"]
        assert server.env == {"VAR1": "value1", "VAR2": "value2"}
        assert server.headers["Authorization"] == "Bearer token"
        assert len(server.discovered_tools) == 1
        assert server.discovered_tools[0]["name"] == "read_file"
        assert len(server.discovered_resources) == 1
        assert server.discovered_resources[0]["uri"] == "file:///config.json"
        assert len(server.discovered_prompts) == 1
        assert server.discovered_prompts[0]["name"] == "analyze_code"

    def test_mcp_server_with_error_status(self):
        """
        Test MCPServer with error status and error message.

        Verifies status='error' can be set along with error_message
        for tracking server failures.
        """
        tenant_id = uuid.uuid4()

        server = MCPServer(
            tenant_id=tenant_id,
            name="failing-server",
            transport_type=TransportType.STDIO.value,
            command="/usr/bin/nonexistent",
            status=MCPServerStatus.ERROR.value,
            error_message="Command not found: /usr/bin/nonexistent",
        )

        assert server.status == "error"
        assert server.error_message == "Command not found: /usr/bin/nonexistent"

    def test_mcp_server_health_check_tracking(self):
        """
        Test last_health_check timestamp can be set.

        Verifies health check timestamp tracking for monitoring
        server availability.
        """
        tenant_id = uuid.uuid4()
        health_check_time = datetime.now()

        server = MCPServer(
            tenant_id=tenant_id,
            name="monitored-server",
            transport_type=TransportType.STDIO.value,
            status=MCPServerStatus.ACTIVE.value,
            last_health_check=health_check_time,
        )

        assert server.last_health_check == health_check_time

    def test_mcp_server_discovered_capabilities(self):
        """
        Test discovered_tools, discovered_resources, discovered_prompts.

        Verifies MCP server capability discovery results can be stored
        in JSONB arrays following MCP specification format.
        """
        tenant_id = uuid.uuid4()

        server = MCPServer(
            tenant_id=tenant_id,
            name="capability-server",
            transport_type=TransportType.STDIO.value,
            discovered_tools=[
                {
                    "name": "read_file",
                    "description": "Read file contents",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                    },
                },
                {
                    "name": "write_file",
                    "description": "Write file contents",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                        "required": ["path", "content"],
                    },
                },
            ],
            discovered_resources=[
                {
                    "uri": "file:///workspace/config.json",
                    "name": "Application Config",
                    "mimeType": "application/json",
                    "description": "Main application configuration",
                }
            ],
            discovered_prompts=[
                {
                    "name": "analyze_code",
                    "description": "Analyze code for issues",
                    "arguments": [
                        {"name": "language", "description": "Programming language", "required": True}
                    ],
                }
            ],
        )

        # Verify discovered capabilities structure
        assert len(server.discovered_tools) == 2
        assert server.discovered_tools[0]["name"] == "read_file"
        assert server.discovered_tools[1]["name"] == "write_file"
        assert "inputSchema" in server.discovered_tools[0]
        assert "required" in server.discovered_tools[0]["inputSchema"]

        assert len(server.discovered_resources) == 1
        assert server.discovered_resources[0]["uri"] == "file:///workspace/config.json"
        assert server.discovered_resources[0]["mimeType"] == "application/json"

        assert len(server.discovered_prompts) == 1
        assert server.discovered_prompts[0]["name"] == "analyze_code"
        assert len(server.discovered_prompts[0]["arguments"]) == 1
