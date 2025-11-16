"""
Unit tests for MCP server Pydantic schemas.

Tests cover all acceptance criteria:
- AC1: MCPServerCreate validation (stdio and http_sse)
- AC2: MCPServerUpdate validation (partial updates)
- AC3: MCPServerResponse serialization from ORM
- AC4-6: Discovered capability schemas (Tool, Resource, Prompt)
- AC7: Transport-specific validation with clear error messages
- AC8: OpenAPI examples validity

Target: ≥95% code coverage
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from src.database.models import MCPServerStatus, TransportType
from src.schemas.mcp_server import (
    MCPDiscoveredPrompt,
    MCPDiscoveredResource,
    MCPDiscoveredTool,
    MCPPromptArgument,
    MCPServerCreate,
    MCPServerResponse,
    MCPServerUpdate,
)


# =============================================================================
# Test Discovered Capability Schemas (AC4, AC5, AC6)
# =============================================================================


class TestMCPPromptArgument:
    """Tests for MCPPromptArgument schema."""

    def test_prompt_argument_valid(self):
        """Test valid prompt argument creation."""
        arg = MCPPromptArgument(
            name="language",
            description="Programming language (python, javascript, etc.)",
            required=True
        )
        assert arg.name == "language"
        assert arg.description == "Programming language (python, javascript, etc.)"
        assert arg.required is True

    def test_prompt_argument_defaults(self):
        """Test prompt argument with default values."""
        arg = MCPPromptArgument(name="optional_param")
        assert arg.name == "optional_param"
        assert arg.description is None
        assert arg.required is False  # Default

    def test_prompt_argument_name_required(self):
        """Test prompt argument name is required."""
        with pytest.raises(ValidationError) as exc_info:
            MCPPromptArgument(description="test")
        assert "name" in str(exc_info.value)


class TestMCPDiscoveredTool:
    """Tests for MCPDiscoveredTool schema (AC4)."""

    def test_discovered_tool_valid(self):
        """Test valid tool with complete JSON Schema."""
        tool = MCPDiscoveredTool(
            name="read_file",
            description="Read contents of a file from the filesystem",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute or relative file path"
                    }
                },
                "required": ["path"]
            }
        )
        assert tool.name == "read_file"
        assert tool.description == "Read contents of a file from the filesystem"
        assert tool.inputSchema["type"] == "object"
        assert "path" in tool.inputSchema["properties"]

    def test_discovered_tool_minimal(self):
        """Test tool with minimal required fields."""
        tool = MCPDiscoveredTool(
            name="simple_tool",
            inputSchema={"type": "object"}
        )
        assert tool.name == "simple_tool"
        assert tool.description is None
        assert tool.inputSchema == {"type": "object"}

    def test_discovered_tool_name_required(self):
        """Test tool name is required."""
        with pytest.raises(ValidationError) as exc_info:
            MCPDiscoveredTool(
                inputSchema={"type": "object"}
            )
        assert "name" in str(exc_info.value)

    def test_discovered_tool_input_schema_required(self):
        """Test inputSchema is required."""
        with pytest.raises(ValidationError) as exc_info:
            MCPDiscoveredTool(name="test_tool")
        assert "inputSchema" in str(exc_info.value)


class TestMCPDiscoveredResource:
    """Tests for MCPDiscoveredResource schema (AC5)."""

    def test_discovered_resource_valid(self):
        """Test valid resource with all fields."""
        resource = MCPDiscoveredResource(
            uri="file:///Users/ravi/Documents/config.json",
            name="Application Configuration",
            description="Main application config file",
            mimeType="application/json"
        )
        assert resource.uri == "file:///Users/ravi/Documents/config.json"
        assert resource.name == "Application Configuration"
        assert resource.description == "Main application config file"
        assert resource.mimeType == "application/json"

    def test_discovered_resource_minimal(self):
        """Test resource with minimal required fields."""
        resource = MCPDiscoveredResource(
            uri="file:///path/to/file.txt",
            name="Text File"
        )
        assert resource.uri == "file:///path/to/file.txt"
        assert resource.name == "Text File"
        assert resource.description is None
        assert resource.mimeType is None

    def test_discovered_resource_http_uri(self):
        """Test resource with HTTP URI."""
        resource = MCPDiscoveredResource(
            uri="http://localhost:8080/api/schema",
            name="API Schema"
        )
        assert resource.uri == "http://localhost:8080/api/schema"

    def test_discovered_resource_uri_required(self):
        """Test URI is required."""
        with pytest.raises(ValidationError) as exc_info:
            MCPDiscoveredResource(name="Test")
        assert "uri" in str(exc_info.value)

    def test_discovered_resource_name_required(self):
        """Test name is required."""
        with pytest.raises(ValidationError) as exc_info:
            MCPDiscoveredResource(uri="file:///test")
        assert "name" in str(exc_info.value)


class TestMCPDiscoveredPrompt:
    """Tests for MCPDiscoveredPrompt schema (AC6)."""

    def test_discovered_prompt_with_arguments(self):
        """Test prompt with arguments list."""
        prompt = MCPDiscoveredPrompt(
            name="analyze_code",
            description="Analyze source code for issues and improvements",
            arguments=[
                MCPPromptArgument(
                    name="language",
                    description="Programming language",
                    required=True
                ),
                MCPPromptArgument(
                    name="include_style",
                    description="Include style suggestions",
                    required=False
                )
            ]
        )
        assert prompt.name == "analyze_code"
        assert len(prompt.arguments) == 2
        assert prompt.arguments[0].name == "language"
        assert prompt.arguments[0].required is True
        assert prompt.arguments[1].name == "include_style"
        assert prompt.arguments[1].required is False

    def test_discovered_prompt_minimal(self):
        """Test prompt with no arguments."""
        prompt = MCPDiscoveredPrompt(name="simple_prompt")
        assert prompt.name == "simple_prompt"
        assert prompt.description is None
        assert prompt.arguments == []  # Default empty list

    def test_discovered_prompt_name_required(self):
        """Test prompt name is required."""
        with pytest.raises(ValidationError) as exc_info:
            MCPDiscoveredPrompt(description="test")
        assert "name" in str(exc_info.value)


# =============================================================================
# Test MCPServerCreate Schema (AC1, AC7)
# =============================================================================


class TestMCPServerCreate:
    """Tests for MCPServerCreate schema validation."""

    def test_create_valid_stdio(self):
        """Test valid stdio configuration."""
        server = MCPServerCreate(
            name="Filesystem Server",
            description="Local filesystem access via MCP",
            transport_type=TransportType.STDIO,
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/Users/ravi/Documents"],
            env={"LOG_LEVEL": "debug"}
        )
        assert server.name == "Filesystem Server"
        assert server.transport_type == TransportType.STDIO
        assert server.command == "npx"
        assert len(server.args) == 3
        assert server.env == {"LOG_LEVEL": "debug"}
        assert server.url is None
        assert server.headers == {}

    def test_create_valid_http_sse(self):
        """Test valid http_sse configuration."""
        server = MCPServerCreate(
            name="GitHub MCP Server",
            description="GitHub API integration",
            transport_type=TransportType.HTTP_SSE,
            url="https://mcp.github.com/api",
            headers={"Authorization": "Bearer ghp_xxxxxxxxxxxx"}
        )
        assert server.name == "GitHub MCP Server"
        assert server.transport_type == TransportType.HTTP_SSE
        assert server.url == "https://mcp.github.com/api"
        assert server.headers == {"Authorization": "Bearer ghp_xxxxxxxxxxxx"}
        assert server.command is None
        assert server.args == []
        assert server.env == {}

    def test_create_stdio_missing_command(self):
        """Test stdio missing command raises clear error (AC7)."""
        with pytest.raises(ValidationError) as exc_info:
            MCPServerCreate(
                name="Test Server",
                transport_type=TransportType.STDIO
            )
        error_msg = str(exc_info.value)
        assert "command is required when transport_type is 'stdio'" in error_msg

    def test_create_stdio_empty_command(self):
        """Test stdio with empty command raises error."""
        with pytest.raises(ValidationError) as exc_info:
            MCPServerCreate(
                name="Test Server",
                transport_type=TransportType.STDIO,
                command="   "  # Whitespace only
            )
        error_msg = str(exc_info.value)
        assert "command is required when transport_type is 'stdio'" in error_msg

    def test_create_http_sse_missing_url(self):
        """Test http_sse missing url raises clear error (AC7)."""
        with pytest.raises(ValidationError) as exc_info:
            MCPServerCreate(
                name="Test Server",
                transport_type=TransportType.HTTP_SSE
            )
        error_msg = str(exc_info.value)
        assert "url is required when transport_type is 'http_sse'" in error_msg

    def test_create_http_sse_empty_url(self):
        """Test http_sse with empty url raises error."""
        with pytest.raises(ValidationError) as exc_info:
            MCPServerCreate(
                name="Test Server",
                transport_type=TransportType.HTTP_SSE,
                url="   "  # Whitespace only
            )
        error_msg = str(exc_info.value)
        assert "url is required when transport_type is 'http_sse'" in error_msg

    def test_create_mixed_fields_stdio_with_url(self):
        """Test stdio with url/headers raises error (AC7)."""
        with pytest.raises(ValidationError) as exc_info:
            MCPServerCreate(
                name="Test Server",
                transport_type=TransportType.STDIO,
                command="npx",
                url="https://example.com"  # Invalid for stdio
            )
        error_msg = str(exc_info.value)
        assert "Cannot provide url or headers with stdio transport" in error_msg

    def test_create_mixed_fields_http_sse_with_command(self):
        """Test http_sse with command/args/env raises error (AC7)."""
        with pytest.raises(ValidationError) as exc_info:
            MCPServerCreate(
                name="Test Server",
                transport_type=TransportType.HTTP_SSE,
                url="https://example.com",
                command="npx"  # Invalid for http_sse
            )
        error_msg = str(exc_info.value)
        assert "Cannot provide command, args, or env with http_sse transport" in error_msg

    def test_create_http_sse_invalid_url_format(self):
        """Test http_sse with invalid URL format raises error."""
        with pytest.raises(ValidationError) as exc_info:
            MCPServerCreate(
                name="Test Server",
                transport_type=TransportType.HTTP_SSE,
                url="ftp://example.com"  # Not HTTP/HTTPS
            )
        error_msg = str(exc_info.value)
        assert "url must start with 'http://' or 'https://'" in error_msg

    def test_create_field_max_lengths(self):
        """Test field max length constraints."""
        # Name max 255 chars
        with pytest.raises(ValidationError):
            MCPServerCreate(
                name="x" * 256,
                transport_type=TransportType.STDIO,
                command="test"
            )

        # Command max 500 chars
        with pytest.raises(ValidationError):
            MCPServerCreate(
                name="Test",
                transport_type=TransportType.STDIO,
                command="x" * 501
            )

        # URL max 500 chars
        with pytest.raises(ValidationError):
            MCPServerCreate(
                name="Test",
                transport_type=TransportType.HTTP_SSE,
                url="https://" + "x" * 500
            )

    def test_create_defaults(self):
        """Test default values are applied (AC1)."""
        server = MCPServerCreate(
            name="Test Server",
            transport_type=TransportType.STDIO,
            command="test"
        )
        assert server.args == []  # Default empty list
        assert server.env == {}  # Default empty dict
        assert server.headers == {}  # Default empty dict


# =============================================================================
# Test MCPServerUpdate Schema (AC2, AC7)
# =============================================================================


class TestMCPServerUpdate:
    """Tests for MCPServerUpdate schema validation."""

    def test_update_partial_name_only(self):
        """Test partial update with only name changed."""
        update = MCPServerUpdate(name="Updated Server Name")
        assert update.name == "Updated Server Name"
        assert update.description is None
        assert update.transport_type is None
        assert update.command is None

    def test_update_stdio_to_http_sse(self):
        """Test transport type change from stdio to http_sse."""
        update = MCPServerUpdate(
            transport_type=TransportType.HTTP_SSE,
            url="https://mcp.example.com/api"
        )
        assert update.transport_type == TransportType.HTTP_SSE
        assert update.url == "https://mcp.example.com/api"

    def test_update_http_sse_to_stdio(self):
        """Test transport type change from http_sse to stdio."""
        update = MCPServerUpdate(
            transport_type=TransportType.STDIO,
            command="npx"
        )
        assert update.transport_type == TransportType.STDIO
        assert update.command == "npx"

    def test_update_stdio_validation(self):
        """Test stdio validation in update (AC7)."""
        # Empty command with stdio should fail
        with pytest.raises(ValidationError) as exc_info:
            MCPServerUpdate(
                transport_type=TransportType.STDIO,
                command="   "  # Whitespace only
            )
        assert "command must be non-empty when transport_type is 'stdio'" in str(exc_info.value)

    def test_update_http_sse_validation(self):
        """Test http_sse validation in update (AC7)."""
        # Empty URL with http_sse should fail
        with pytest.raises(ValidationError) as exc_info:
            MCPServerUpdate(
                transport_type=TransportType.HTTP_SSE,
                url="   "  # Whitespace only
            )
        assert "url must be non-empty when transport_type is 'http_sse'" in str(exc_info.value)

    def test_update_stdio_with_http_sse_fields(self):
        """Test stdio update with http_sse fields raises error."""
        with pytest.raises(ValidationError) as exc_info:
            MCPServerUpdate(
                transport_type=TransportType.STDIO,
                url="https://example.com"
            )
        assert "Cannot provide url or headers with stdio transport" in str(exc_info.value)

    def test_update_http_sse_with_stdio_fields(self):
        """Test http_sse update with stdio fields raises error."""
        with pytest.raises(ValidationError) as exc_info:
            MCPServerUpdate(
                transport_type=TransportType.HTTP_SSE,
                url="https://example.com",
                command="test"
            )
        assert "Cannot provide command, args, or env with http_sse transport" in str(exc_info.value)

    def test_update_http_sse_invalid_url_format(self):
        """Test http_sse update with invalid URL format."""
        with pytest.raises(ValidationError) as exc_info:
            MCPServerUpdate(
                transport_type=TransportType.HTTP_SSE,
                url="ftp://example.com"
            )
        assert "url must start with 'http://' or 'https://'" in str(exc_info.value)


# =============================================================================
# Test MCPServerResponse Schema (AC3)
# =============================================================================


class TestMCPServerResponse:
    """Tests for MCPServerResponse schema serialization."""

    def test_response_from_orm_stdio(self):
        """Test response serialization from ORM model (stdio)."""
        # Simulate MCPServer ORM model (using dict with from_attributes=True)
        mock_server = type('MockServer', (), {
            'id': uuid4(),
            'tenant_id': uuid4(),
            'name': 'Filesystem Server',
            'description': 'Local filesystem access',
            'transport_type': TransportType.STDIO,
            'command': 'npx',
            'args': ['-y', '@modelcontextprotocol/server-filesystem'],
            'env': {'LOG_LEVEL': 'debug'},
            'url': None,
            'headers': {},
            'discovered_tools': [
                {
                    'name': 'read_file',
                    'description': 'Read file contents',
                    'inputSchema': {'type': 'object', 'properties': {'path': {'type': 'string'}}}
                }
            ],
            'discovered_resources': [],
            'discovered_prompts': [],
            'status': MCPServerStatus.ACTIVE,
            'last_health_check': datetime.now(timezone.utc),
            'error_message': None,
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        })()

        response = MCPServerResponse.model_validate(mock_server)
        assert isinstance(response.id, UUID)
        assert isinstance(response.tenant_id, UUID)
        assert response.name == 'Filesystem Server'
        assert response.transport_type == TransportType.STDIO
        assert response.command == 'npx'
        assert len(response.discovered_tools) == 1
        assert response.discovered_tools[0].name == 'read_file'

    def test_response_datetime_serialization(self):
        """Test datetime fields are serialized correctly (ISO 8601)."""
        now = datetime.now(timezone.utc)
        mock_server = type('MockServer', (), {
            'id': uuid4(),
            'tenant_id': uuid4(),
            'name': 'Test Server',
            'description': None,
            'transport_type': TransportType.STDIO,
            'command': 'test',
            'args': [],
            'env': {},
            'url': None,
            'headers': {},
            'discovered_tools': [],
            'discovered_resources': [],
            'discovered_prompts': [],
            'status': MCPServerStatus.INACTIVE,
            'last_health_check': now,
            'error_message': None,
            'created_at': now,
            'updated_at': now
        })()

        response = MCPServerResponse.model_validate(mock_server)
        assert isinstance(response.created_at, datetime)
        assert isinstance(response.updated_at, datetime)
        assert isinstance(response.last_health_check, datetime)

        # Test JSON serialization (should be ISO 8601 strings)
        json_data = response.model_dump(mode='json')
        assert isinstance(json_data['created_at'], str)
        assert isinstance(json_data['updated_at'], str)

    def test_response_uuid_serialization(self):
        """Test UUID fields are serialized as strings (AC3)."""
        server_id = uuid4()
        tenant_id = uuid4()
        mock_server = type('MockServer', (), {
            'id': server_id,
            'tenant_id': tenant_id,
            'name': 'Test Server',
            'description': None,
            'transport_type': TransportType.HTTP_SSE,
            'command': None,
            'args': [],
            'env': {},
            'url': 'https://example.com',
            'headers': {},
            'discovered_tools': [],
            'discovered_resources': [],
            'discovered_prompts': [],
            'status': MCPServerStatus.ACTIVE,
            'last_health_check': None,
            'error_message': None,
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        })()

        response = MCPServerResponse.model_validate(mock_server)
        assert response.id == server_id
        assert response.tenant_id == tenant_id

        # Test JSON serialization (UUIDs should be strings)
        json_data = response.model_dump(mode='json')
        assert isinstance(json_data['id'], str)
        assert isinstance(json_data['tenant_id'], str)

    def test_response_jsonb_serialization(self):
        """Test JSONB arrays/objects are serialized correctly."""
        mock_server = type('MockServer', (), {
            'id': uuid4(),
            'tenant_id': uuid4(),
            'name': 'Test Server',
            'description': None,
            'transport_type': TransportType.STDIO,
            'command': 'test',
            'args': ['arg1', 'arg2'],  # JSONB array
            'env': {'KEY1': 'value1', 'KEY2': 'value2'},  # JSONB object
            'url': None,
            'headers': {},
            'discovered_tools': [
                {
                    'name': 'tool1',
                    'description': 'Test tool',
                    'inputSchema': {'type': 'object'}
                }
            ],
            'discovered_resources': [
                {
                    'uri': 'file:///test',
                    'name': 'Test Resource',
                    'description': 'Test',
                    'mimeType': 'text/plain'
                }
            ],
            'discovered_prompts': [
                {
                    'name': 'prompt1',
                    'description': 'Test prompt',
                    'arguments': [
                        {'name': 'arg1', 'description': 'Test arg', 'required': True}
                    ]
                }
            ],
            'status': MCPServerStatus.ACTIVE,
            'last_health_check': datetime.now(timezone.utc),
            'error_message': None,
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        })()

        response = MCPServerResponse.model_validate(mock_server)
        assert response.args == ['arg1', 'arg2']
        assert response.env == {'KEY1': 'value1', 'KEY2': 'value2'}
        assert len(response.discovered_tools) == 1
        assert len(response.discovered_resources) == 1
        assert len(response.discovered_prompts) == 1


# =============================================================================
# Test OpenAPI Examples (AC8)
# =============================================================================


class TestOpenAPIExamples:
    """Tests that OpenAPI examples are valid and pass schema validation."""

    def test_create_stdio_example_valid(self):
        """Test stdio example from schema docs is valid."""
        example = {
            "name": "Filesystem Server",
            "description": "Local filesystem access via MCP",
            "transport_type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/ravi/Documents"],
            "env": {"LOG_LEVEL": "debug"}
        }
        server = MCPServerCreate(**example)
        assert server.name == "Filesystem Server"
        assert server.transport_type == TransportType.STDIO

    def test_create_http_sse_example_valid(self):
        """Test http_sse example from schema docs is valid."""
        example = {
            "name": "GitHub MCP Server",
            "description": "GitHub API integration",
            "transport_type": "http_sse",
            "url": "https://mcp.github.com/api",
            "headers": {"Authorization": "Bearer ghp_xxxxxxxxxxxx"}
        }
        server = MCPServerCreate(**example)
        assert server.name == "GitHub MCP Server"
        assert server.transport_type == TransportType.HTTP_SSE

    def test_examples_json_serializable(self):
        """Test examples can be serialized to JSON."""
        server = MCPServerCreate(
            name="Test",
            transport_type=TransportType.STDIO,
            command="test"
        )
        json_data = server.model_dump(mode='json')
        assert isinstance(json_data, dict)
        assert json_data['name'] == "Test"
        assert json_data['transport_type'] == "stdio"
