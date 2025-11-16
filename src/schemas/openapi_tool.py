"""
OpenAPI Tool Schemas - Pydantic models for OpenAPI tool management.

Story 8.8: OpenAPI Tool Upload and Auto-Generation
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OpenAPIToolCreate(BaseModel):
    """Schema for creating a new OpenAPI tool."""

    tool_name: str = Field(..., min_length=1, max_length=255, description="Tool name")
    openapi_spec: dict[str, Any] = Field(..., description="Full OpenAPI specification")
    spec_version: str = Field(..., pattern="^(2\\.0|3\\.0|3\\.1)$", description="OpenAPI version")
    base_url: str = Field(..., min_length=1, description="API base URL")
    auth_config: dict[str, Any] = Field(default_factory=dict, description="Authentication configuration")
    tenant_id: str = Field(..., min_length=1, max_length=100, description="Tenant ID")
    created_by: Optional[str] = Field(None, max_length=100, description="Creator username")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "tool_name": "GitHub API",
            "openapi_spec": {"openapi": "3.0.0", "info": {"title": "GitHub API"}},
            "spec_version": "3.0",
            "base_url": "https://api.github.com",
            "auth_config": {"type": "bearer", "token": "ghp_xxx"},
            "tenant_id": "test-tenant",
            "created_by": "admin"
        }
    })


class OpenAPIToolUpdate(BaseModel):
    """Schema for updating an OpenAPI tool."""

    tool_name: Optional[str] = Field(None, min_length=1, max_length=255)
    base_url: Optional[str] = None
    auth_config: Optional[dict[str, Any]] = None
    status: Optional[str] = Field(None, pattern="^(active|inactive)$")


class OpenAPITool(BaseModel):
    """Schema for OpenAPI tool response."""

    id: int
    tenant_id: str
    tool_name: str
    spec_version: str
    base_url: str
    status: str
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    tools_generated_count: Optional[int] = Field(None, description="Number of MCP tools generated")

    model_config = ConfigDict(from_attributes=True)


class TestConnectionRequest(BaseModel):
    """Schema for test connection request."""

    spec: dict[str, Any] = Field(..., description="OpenAPI spec")
    auth_config: dict[str, Any] = Field(default_factory=dict, description="Auth config")


class TestConnectionResponse(BaseModel):
    """Schema for test connection response."""

    success: bool
    status_code: Optional[int] = None
    response_preview: Optional[str] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    test_endpoint: Optional[str] = None
