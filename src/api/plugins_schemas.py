"""
Pydantic schemas for plugin management API (Story 7.8).

Data models for plugin metadata, configuration schemas, and API request/response
validation. Used by plugins_routes.py for type-safe REST endpoint handling.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PluginMetadata(BaseModel):
    """Plugin metadata for list display."""

    plugin_id: str = Field(..., description="Unique plugin identifier (tool_type)")
    name: str = Field(..., description="Human-readable plugin name")
    version: str = Field(..., description="Plugin version")
    status: str = Field(..., description="Plugin status (active, inactive, error)")
    description: str = Field(..., description="Brief plugin description")
    tool_type: str = Field(..., description="Tool type identifier")


class PluginListResponse(BaseModel):
    """Response for GET /api/plugins endpoint."""

    plugins: List[PluginMetadata]
    count: int = Field(..., description="Total number of registered plugins")


class ConfigFieldSchema(BaseModel):
    """JSON Schema representation of a configuration field."""

    field_name: str
    field_type: str  # "string", "integer", "boolean", "enum"
    required: bool
    description: Optional[str] = None
    default: Optional[Any] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    enum_values: Optional[List[str]] = None


class PluginConfigSchema(BaseModel):
    """Complete plugin configuration schema."""

    plugin_id: str
    schema_fields: List[ConfigFieldSchema]


class PluginDetailsResponse(BaseModel):
    """Response for GET /api/plugins/{plugin_id} endpoint."""

    plugin_id: str
    name: str
    version: str
    description: str
    tool_type: str
    config_schema: PluginConfigSchema


class ConnectionTestRequest(BaseModel):
    """Request for POST /api/plugins/{plugin_id}/test endpoint."""

    config: Dict[str, Any] = Field(
        ..., description="Plugin configuration to test (e.g., url, api_token)"
    )


class ConnectionTestResponse(BaseModel):
    """Response for connection test endpoint."""

    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None
