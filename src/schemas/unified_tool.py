"""
Unified Tool Schema for OpenAPI and MCP tool discovery.

This module defines the UnifiedTool schema that combines tools from multiple sources
(OpenAPI tools and MCP servers) into a consistent format for agent execution.
"""

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class SourceType(str, Enum):
    """Source type for unified tools."""

    OPENAPI = "openapi"
    MCP = "mcp"


class MCPPrimitiveType(str, Enum):
    """MCP primitive types (only applicable when source_type=MCP)."""

    TOOL = "tool"
    RESOURCE = "resource"
    PROMPT = "prompt"


class UnifiedTool(BaseModel):
    """
    Unified tool schema combining OpenAPI tools and MCP primitives.

    This schema provides a consistent interface for tools from different sources,
    enabling agents to discover and use tools regardless of their origin.

    Attributes:
        id: Unique identifier (UUID from OpenAPI tool or deterministic UUID5 for MCP)
        name: Tool name (operationId for OpenAPI, tool/resource/prompt name for MCP)
        description: Human-readable description for LLM context
        source_type: Source indicator ("openapi" or "mcp")
        openapi_tool_id: Original OpenAPI tool integer ID (null for MCP tools)
        mcp_server_id: MCP server ID (null for OpenAPI tools)
        mcp_primitive_type: MCP type ("tool", "resource", "prompt" - null for OpenAPI)
        mcp_server_name: MCP server name for disambiguation (null for OpenAPI)
        input_schema: JSON Schema for input validation (parameters_schema for OpenAPI)
        enabled: Whether tool is enabled for use
    """

    id: UUID = Field(description="Unique tool identifier")
    name: str = Field(description="Tool name for LLM invocation")
    description: str = Field(description="Human-readable tool description")
    source_type: SourceType = Field(description="Source type: openapi or mcp")
    openapi_tool_id: int | None = Field(
        default=None, description="Original OpenAPI tool integer ID (null for MCP tools)"
    )
    mcp_server_id: UUID | None = Field(
        default=None, description="MCP server ID (null for OpenAPI tools)"
    )
    mcp_primitive_type: MCPPrimitiveType | None = Field(
        default=None, description="MCP primitive type (null for OpenAPI tools)"
    )
    mcp_server_name: str | None = Field(
        default=None, description="MCP server name (null for OpenAPI tools)"
    )
    input_schema: dict[str, Any] = Field(description="JSON Schema for input validation")
    enabled: bool = Field(default=True, description="Whether tool is enabled")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "get_weather",
                "description": "Get current weather information for a location",
                "source_type": "openapi",
                "mcp_server_id": None,
                "mcp_primitive_type": None,
                "mcp_server_name": None,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City name or zip code",
                        }
                    },
                    "required": ["location"],
                },
                "enabled": True,
            }
        }
    )
