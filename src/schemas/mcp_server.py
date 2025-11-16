"""
Pydantic schemas for MCP (Model Context Protocol) server configuration and management.

This module defines data validation schemas for MCP server CRUD operations using
Pydantic v2 patterns. Includes schemas for discovered MCP primitives (tools, resources,
prompts) and comprehensive transport-specific validation.

MCP Specification: https://modelcontextprotocol.io/specification (2025-03-26)

Following 2025 Pydantic v2 best practices:
- @model_validator(mode='after') for cross-field validation
- @field_validator(mode='after') for single-field validation
- ConfigDict(from_attributes=True) for ORM integration
- str mixin for Enum classes (JSON serialization)
- Type hints with | union syntax (Python 3.10+)
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.database.models import MCPServerStatus, TransportType


# =============================================================================
# MCP Discovered Capability Schemas (AC4, AC5, AC6)
# =============================================================================


class MCPPromptArgument(BaseModel):
    """
    Argument definition for MCP prompt templates.

    Prompts can accept arguments to customize template behavior. Each argument
    has a name, optional description, and required flag indicating if the client
    must provide a value.

    Per MCP Specification 2025-03-26, prompt arguments support flexible templating.

    Attributes:
        name: Argument identifier (e.g., 'language', 'file_path')
        description: Human-readable explanation of argument purpose
        required: Whether argument must be provided by client (default False)

    Example:
        {
            "name": "language",
            "description": "Programming language (python, javascript, etc.)",
            "required": true
        }
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Argument name identifier",
        examples=["language", "file_path", "include_comments"],
    )
    description: str | None = Field(
        None,
        description="Human-readable description of argument purpose",
        examples=["Programming language for analysis", "Path to file to process"],
    )
    required: bool = Field(default=False, description="Whether this argument must be provided")


class MCPDiscoveredTool(BaseModel):
    """
    MCP tool discovered from tools/list endpoint.

    Tools are model-controlled functions that agents can invoke to interact with
    external systems (query databases, call APIs, perform computations).

    Per MCP Specification 2025-03-26, tools include:
    - name: Unique identifier for tool invocation
    - description: Explains functionality for LLM context
    - inputSchema: JSON Schema (draft 2020-12) defining parameters

    Attributes:
        name: Tool identifier used in tools/call (unique per server)
        description: Human-readable explanation of tool functionality
        inputSchema: JSON Schema object defining expected parameters

    Example:
        {
            "name": "read_file",
            "description": "Read contents of a file from the filesystem",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"}
                },
                "required": ["path"]
            }
        }
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Tool identifier for invocation",
        examples=["read_file", "search_database", "send_email"],
    )
    description: str | None = Field(
        None,
        description="Human-readable tool functionality description",
        examples=["Read file contents", "Search database records"],
    )
    inputSchema: dict = Field(
        ...,
        description="JSON Schema (draft 2020-12) defining tool parameters",
        examples=[
            {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "File path"}},
                "required": ["path"],
            }
        ],
    )


class MCPDiscoveredResource(BaseModel):
    """
    MCP resource discovered from resources/list endpoint.

    Resources are application-controlled data sources that provide context to LLMs
    (files, database schemas, logs, configuration). Resources are read-only and
    identified by URI.

    Per MCP Specification 2025-03-26, resources include:
    - uri: Resource location (file://, http://, custom schemes)
    - name: Human-readable identifier for UI display
    - description: Explains what resource represents
    - mimeType: Content type if known (text/plain, application/json, etc.)

    Attributes:
        uri: Resource URI (e.g., file:///path/to/file.txt)
        name: Human-readable resource name for UI population
        description: Explanation of resource contents/purpose
        mimeType: MIME type indicating content format

    Example:
        {
            "uri": "file:///Users/ravi/Documents/config.json",
            "name": "Application Configuration",
            "description": "Main application config file",
            "mimeType": "application/json"
        }
    """

    uri: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Resource URI (file://, http://, or custom scheme)",
        examples=[
            "file:///Users/ravi/Documents/config.json",
            "http://localhost:8080/api/schema",
            "db://production/schema",
        ],
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable resource name",
        examples=["Application Configuration", "Database Schema", "API Logs"],
    )
    description: str | None = Field(
        None,
        description="Explanation of resource contents or purpose",
        examples=["Main application config file", "Production database schema"],
    )
    mimeType: str | None = Field(
        None,
        max_length=100,
        description="MIME type indicating content format",
        examples=["text/plain", "application/json", "text/csv"],
    )


class MCPDiscoveredPrompt(BaseModel):
    """
    MCP prompt template discovered from prompts/list endpoint.

    Prompts are user-controlled templates for common tasks, allowing servers to
    provide structured messages and instructions for LLM interactions.

    Per MCP Specification 2025-03-26, prompts include:
    - name: Prompt identifier
    - description: Explains provided functionality
    - arguments: Optional list of MCPPromptArgument for template customization

    Attributes:
        name: Prompt template identifier
        description: Explanation of prompt functionality
        arguments: List of template arguments (parameters)

    Example:
        {
            "name": "analyze_code",
            "description": "Analyze source code for issues and improvements",
            "arguments": [
                {
                    "name": "language",
                    "description": "Programming language",
                    "required": true
                },
                {
                    "name": "include_style",
                    "description": "Include style suggestions",
                    "required": false
                }
            ]
        }
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Prompt template identifier",
        examples=["analyze_code", "summarize_docs", "debug_error"],
    )
    description: str | None = Field(
        None,
        description="Explanation of prompt functionality",
        examples=["Analyze code for issues", "Summarize documentation"],
    )
    arguments: list[MCPPromptArgument] = Field(
        default_factory=list, description="List of template arguments"
    )


# =============================================================================
# MCP Server CRUD Schemas (AC1, AC2, AC3, AC7)
# =============================================================================


class MCPServerCreate(BaseModel):
    """
    Schema for creating new MCP servers.

    Validates transport-specific requirements:
    - stdio transport: command required, url/headers not allowed
    - http_sse transport: url required, command/args/env not allowed

    Following MCP Specification 2025-03-26 transport types.

    Attributes:
        name: Human-readable server name (max 255 chars, unique per tenant)
        description: Optional detailed description of server purpose
        transport_type: Transport protocol ('stdio' or 'http_sse')
        command: Executable path for stdio (e.g., 'npx', '/usr/bin/python3')
        args: Command-line arguments array for stdio (default [])
        env: Environment variables object for stdio (default {})
        url: Base URL for HTTP+SSE transport (max 500 chars)
        headers: HTTP headers for authentication (default {})

    Examples:
        stdio configuration:
        {
            "name": "Filesystem Server",
            "description": "Local filesystem access via MCP",
            "transport_type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/ravi/Documents"],
            "env": {"LOG_LEVEL": "debug"}
        }

        http_sse configuration:
        {
            "name": "GitHub MCP Server",
            "description": "GitHub API integration",
            "transport_type": "http_sse",
            "url": "https://mcp.github.com/api",
            "headers": {"Authorization": "Bearer ghp_xxxxxxxxxxxx"}
        }
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable MCP server name",
        examples=["Filesystem Server", "GitHub MCP", "Database Query Server"],
    )
    description: str | None = Field(
        None,
        description="Detailed description of server purpose",
        examples=[
            "Local filesystem access via MCP",
            "GitHub API integration for repository operations",
        ],
    )
    transport_type: TransportType = Field(
        ..., description="Transport protocol: 'stdio' or 'http_sse'"
    )

    # stdio transport fields
    command: str | None = Field(
        None,
        max_length=500,
        description="Command to spawn stdio MCP server process",
        examples=["npx", "python", "/usr/local/bin/mcp-server"],
    )
    args: list[str] = Field(
        default_factory=list,
        description="Command-line arguments array for stdio",
        examples=[
            ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"],
            ["server.py", "--port", "8080"],
        ],
    )
    env: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables object for stdio",
        examples=[{"LOG_LEVEL": "debug", "API_KEY": "secret"}, {"NODE_ENV": "production"}],
    )

    # http_sse transport fields
    url: str | None = Field(
        None,
        max_length=500,
        description="Base URL for HTTP+SSE transport",
        examples=["https://mcp.github.com/api", "http://localhost:3000/mcp"],
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="HTTP headers for authentication",
        examples=[{"Authorization": "Bearer ghp_xxxxxxxxxxxx"}, {"X-API-Key": "secret_key_here"}],
    )

    @model_validator(mode="after")
    def validate_transport_fields(self) -> "MCPServerCreate":
        """
        Validate transport-specific required fields.

        stdio transport:
        - command must be non-empty string
        - url and headers not allowed

        http_sse transport:
        - url must be valid HTTP/HTTPS URL
        - command, args, and env not allowed

        Returns:
            MCPServerCreate: Validated instance

        Raises:
            ValueError: If transport requirements not met
        """
        if self.transport_type == TransportType.STDIO:
            # stdio requires command
            if not self.command or not self.command.strip():
                raise ValueError(
                    "command is required when transport_type is 'stdio'. "
                    "Provide an executable path (e.g., 'npx', '/usr/bin/python3')."
                )
            # stdio should not have http_sse fields
            if self.url or self.headers:
                raise ValueError(
                    "Cannot provide url or headers with stdio transport. "
                    "These fields are only valid for http_sse transport."
                )

        elif self.transport_type == TransportType.HTTP_SSE:
            # http_sse requires url
            if not self.url or not self.url.strip():
                raise ValueError(
                    "url is required when transport_type is 'http_sse'. "
                    "Provide a valid HTTP/HTTPS URL (e.g., 'https://mcp.example.com/api')."
                )
            # http_sse should not have stdio fields
            if self.command or self.args or self.env:
                raise ValueError(
                    "Cannot provide command, args, or env with http_sse transport. "
                    "These fields are only valid for stdio transport."
                )
            # Validate URL format (basic HTTP/HTTPS check)
            if not (self.url.startswith("http://") or self.url.startswith("https://")):
                raise ValueError("url must start with 'http://' or 'https://'. " f"Got: {self.url}")

        return self

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Filesystem Server",
                    "description": "Local filesystem access via MCP",
                    "transport_type": "stdio",
                    "command": "npx",
                    "args": [
                        "-y",
                        "@modelcontextprotocol/server-filesystem",
                        "/Users/ravi/Documents",
                    ],
                    "env": {"LOG_LEVEL": "debug"},
                },
                {
                    "name": "GitHub MCP Server",
                    "description": "GitHub API integration",
                    "transport_type": "http_sse",
                    "url": "https://mcp.github.com/api",
                    "headers": {"Authorization": "Bearer ghp_xxxxxxxxxxxx"},
                },
            ]
        }
    )


class MCPServerUpdate(BaseModel):
    """
    Schema for updating existing MCP servers.

    All fields are optional, allowing partial updates. Transport-specific validation
    applies same rules as MCPServerCreate.

    If transport_type is changed, corresponding transport fields must be provided.

    Attributes:
        name: Optional new server name
        description: Optional new description
        transport_type: Optional new transport type
        command: Optional new command (stdio)
        args: Optional new arguments (stdio)
        env: Optional new environment variables (stdio)
        url: Optional new URL (http_sse)
        headers: Optional new headers (http_sse)

    Example:
        Partial update (name only):
        {"name": "Updated Filesystem Server"}

        Transport type change (stdio → http_sse):
        {
            "transport_type": "http_sse",
            "url": "https://mcp.example.com/api",
            "command": null,
            "args": [],
            "env": {}
        }
    """

    name: str | None = Field(
        None, min_length=1, max_length=255, description="Human-readable MCP server name"
    )
    description: str | None = Field(None, description="Detailed description of server purpose")
    transport_type: TransportType | None = Field(
        None, description="Transport protocol: 'stdio' or 'http_sse'"
    )
    command: str | None = Field(
        None, max_length=500, description="Command to spawn stdio MCP server process"
    )
    args: list[str] | None = Field(None, description="Command-line arguments array for stdio")
    env: dict[str, str] | None = Field(None, description="Environment variables object for stdio")
    url: str | None = Field(None, max_length=500, description="Base URL for HTTP+SSE transport")
    headers: dict[str, str] | None = Field(None, description="HTTP headers for authentication")

    @model_validator(mode="after")
    def validate_transport_fields(self) -> "MCPServerUpdate":
        """
        Validate transport-specific requirements for updates.

        If transport_type is provided, validate corresponding fields.
        If transport_type is changed, ensure new transport fields are valid.

        Returns:
            MCPServerUpdate: Validated instance

        Raises:
            ValueError: If transport requirements not met
        """
        # Only validate if transport_type is being updated
        if self.transport_type is not None:
            if self.transport_type == TransportType.STDIO:
                # If switching to stdio, command should be provided
                if self.command is not None and not self.command.strip():
                    raise ValueError("command must be non-empty when transport_type is 'stdio'")
                # Warn if http_sse fields provided with stdio
                if self.url or self.headers:
                    raise ValueError("Cannot provide url or headers with stdio transport")

            elif self.transport_type == TransportType.HTTP_SSE:
                # If switching to http_sse, url should be provided
                if self.url is not None:
                    if not self.url.strip():
                        raise ValueError("url must be non-empty when transport_type is 'http_sse'")
                    # Validate URL format
                    if not (self.url.startswith("http://") or self.url.startswith("https://")):
                        raise ValueError("url must start with 'http://' or 'https://'")
                # Warn if stdio fields provided with http_sse
                if self.command or self.args or self.env:
                    raise ValueError("Cannot provide command, args, or env with http_sse transport")

        return self


class MCPServerResponse(BaseModel):
    """
    Schema for MCP server API responses.

    Serializes complete MCPServer database model including all configuration,
    discovered capabilities, health status, and timestamps.

    Uses ConfigDict(from_attributes=True) for SQLAlchemy ORM compatibility.
    Serializes UUIDs as strings and datetimes as ISO 8601 format.

    Attributes:
        id: Unique server identifier (UUID)
        tenant_id: Tenant ownership (UUID)
        name: Human-readable server name
        description: Optional server description
        transport_type: Transport protocol ('stdio' or 'http_sse')
        command: stdio command (None for http_sse)
        args: stdio arguments array (empty for http_sse)
        env: stdio environment variables (empty for http_sse)
        url: HTTP+SSE URL (None for stdio)
        headers: HTTP headers (empty for stdio)
        discovered_tools: Tools from tools/list
        discovered_resources: Resources from resources/list
        discovered_prompts: Prompts from prompts/list
        status: Health status ('active', 'inactive', 'error')
        last_health_check: Last health verification timestamp
        error_message: Error details if status='error'
        consecutive_failures: Number of consecutive failed health checks
        created_at: Registration timestamp
        updated_at: Last update timestamp

    Example:
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "tenant_id": "660e8400-e29b-41d4-a716-446655440001",
            "name": "Filesystem Server",
            "description": "Local filesystem access",
            "transport_type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem"],
            "env": {"LOG_LEVEL": "debug"},
            "url": null,
            "headers": {},
            "discovered_tools": [
                {
                    "name": "read_file",
                    "description": "Read file contents",
                    "inputSchema": {"type": "object", "properties": {...}}
                }
            ],
            "discovered_resources": [],
            "discovered_prompts": [],
            "status": "active",
            "last_health_check": "2025-11-09T12:00:00Z",
            "error_message": null,
            "consecutive_failures": 0,
            "created_at": "2025-11-09T10:00:00Z",
            "updated_at": "2025-11-09T12:00:00Z"
        }
    """

    # Enable ORM serialization
    model_config = ConfigDict(from_attributes=True)

    # Primary key
    id: UUID = Field(..., description="Unique server identifier")

    # Tenant isolation
    tenant_id: str = Field(..., description="Tenant ownership (for multi-tenant isolation)")

    # Server identification
    name: str = Field(..., description="Human-readable server name")
    description: str | None = Field(None, description="Optional server description")

    # Transport configuration
    transport_type: TransportType = Field(
        ..., description="Transport protocol: 'stdio' or 'http_sse'"
    )
    command: str | None = Field(None, description="stdio command (None for http_sse)")
    args: list[str] = Field(
        default_factory=list, description="stdio arguments (empty for http_sse)"
    )
    env: dict[str, str] = Field(
        default_factory=dict, description="stdio environment variables (empty for http_sse)"
    )
    url: str | None = Field(None, description="HTTP+SSE URL (None for stdio)")
    headers: dict[str, str] = Field(
        default_factory=dict, description="HTTP headers (empty for stdio)"
    )

    # Discovered capabilities (JSONB arrays)
    discovered_tools: list[MCPDiscoveredTool] = Field(
        default_factory=list, description="Tools from MCP tools/list endpoint"
    )
    discovered_resources: list[MCPDiscoveredResource] = Field(
        default_factory=list, description="Resources from MCP resources/list endpoint"
    )
    discovered_prompts: list[MCPDiscoveredPrompt] = Field(
        default_factory=list, description="Prompts from MCP prompts/list endpoint"
    )

    # Health and status
    status: MCPServerStatus = Field(
        ..., description="Current health status: 'active', 'inactive', or 'error'"
    )
    last_health_check: datetime | None = Field(
        None, description="Last health verification timestamp (ISO 8601)"
    )
    error_message: str | None = Field(None, description="Error details if status='error'")
    consecutive_failures: int = Field(
        default=0,
        description="Number of consecutive failed health checks (circuit breaker triggers at >=3)",
    )

    # Timestamps
    created_at: datetime = Field(..., description="Server registration timestamp (ISO 8601)")
    updated_at: datetime = Field(..., description="Last update timestamp (ISO 8601)")


class MCPTestConnectionResponse(BaseModel):
    """
    Response schema for MCP server test connection endpoint.

    Used for /api/v1/mcp-servers/test-connection endpoint to validate MCP server
    configuration before saving to database. Returns discovered capabilities and
    server info on success, or error details on failure.

    Attributes:
        success: Whether connection test succeeded
        server_info: Server metadata from initialize handshake (if successful)
        discovered_tools: Tools discovered from list_tools (if successful)
        discovered_resources: Resources discovered from list_resources (if successful)
        discovered_prompts: Prompts discovered from list_prompts (if successful)
        error: High-level error message (if failed)
        error_details: Detailed error information for debugging (if failed)

    Example Success:
        {
            "success": true,
            "server_info": {
                "protocol_version": "2025-03-26",
                "server_name": "Example MCP Server",
                "capabilities": ["tools", "resources", "prompts"]
            },
            "discovered_tools": [
                {"name": "read_file", "description": "Read file", "inputSchema": {...}}
            ],
            "discovered_resources": [
                {"uri": "file:///path", "name": "Config", "description": "...", "mimeType": "application/json"}
            ],
            "discovered_prompts": [
                {"name": "analyze", "description": "Analyze code", "arguments": [...]}
            ],
            "error": null,
            "error_details": null
        }

    Example Failure:
        {
            "success": false,
            "server_info": null,
            "discovered_tools": [],
            "discovered_resources": [],
            "discovered_prompts": [],
            "error": "Connection timeout",
            "error_details": "httpx.ConnectTimeout after 10 seconds"
        }
    """

    success: bool = Field(..., description="Whether connection test succeeded")
    server_info: dict[str, str | list[str]] | None = Field(
        None,
        description="Server metadata from initialize handshake",
        examples=[
            {
                "protocol_version": "2025-03-26",
                "server_name": "Example MCP Server",
                "capabilities": ["tools", "resources", "prompts"],
            }
        ],
    )
    discovered_tools: list[MCPDiscoveredTool] = Field(
        default_factory=list, description="Tools discovered from list_tools endpoint"
    )
    discovered_resources: list[MCPDiscoveredResource] = Field(
        default_factory=list, description="Resources discovered from list_resources endpoint"
    )
    discovered_prompts: list[MCPDiscoveredPrompt] = Field(
        default_factory=list, description="Prompts discovered from list_prompts endpoint"
    )
    error: str | None = Field(
        None,
        description="High-level error message if connection failed",
        examples=["Connection timeout", "Authentication failed", "Invalid URL"],
    )
    error_details: str | None = Field(
        None,
        description="Detailed error information for debugging",
        examples=[
            "httpx.ConnectTimeout after 10 seconds",
            "401 Unauthorized: Invalid API key",
            "URL must start with http:// or https://",
        ],
    )


# Export all schemas
__all__ = [
    "MCPPromptArgument",
    "MCPDiscoveredTool",
    "MCPDiscoveredResource",
    "MCPDiscoveredPrompt",
    "MCPServerCreate",
    "MCPServerUpdate",
    "MCPServerResponse",
    "MCPTestConnectionResponse",
]
