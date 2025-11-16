"""OpenAPI Tools API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_tenant_db
from src.schemas.openapi_tool import (
    OpenAPITool,
    OpenAPIToolCreate,
    TestConnectionRequest,
    TestConnectionResponse,
)
from src.services.openapi_parser_service import (
    detect_spec_version,
    extract_tool_metadata,
    parse_openapi_spec,
    format_validation_errors,
    detect_common_issues,
)
from src.services.mcp_tool_generator import validate_openapi_connection
from src.services.openapi_tool_service import OpenAPIToolService

router = APIRouter(prefix="/api/openapi-tools", tags=["openapi-tools"])


@router.post("/parse")
async def parse_spec(request: dict[str, Any]) -> dict[str, Any]:
    """Parse and validate OpenAPI spec, extract metadata."""
    try:
        spec = request.get("spec")
        if not spec:
            raise HTTPException(400, "Missing 'spec' field")

        # Detect common issues first
        issues = detect_common_issues(spec)
        if issues:
            return {"success": False, "validation_errors": issues}

        # Parse spec
        spec_version = detect_spec_version(spec)
        openapi = parse_openapi_spec(spec)
        metadata = extract_tool_metadata(openapi, spec_version)

        return {"success": True, "parsed_spec": True, "metadata": metadata}

    except Exception as e:
        from pydantic import ValidationError
        if isinstance(e, ValidationError):
            errors = format_validation_errors(e.errors())
            return {"success": False, "validation_errors": errors}
        raise HTTPException(400, str(e))


@router.post("/test-connection", response_model=TestConnectionResponse)
async def test_connection(request: TestConnectionRequest) -> TestConnectionResponse:
    """Test API connection with provided credentials."""
    try:
        spec_version = detect_spec_version(request.spec)
        openapi = parse_openapi_spec(request.spec)
        metadata = extract_tool_metadata(openapi, spec_version)
        base_url = metadata.get("base_url", "")

        result = await validate_openapi_connection(request.spec, request.auth_config, base_url)
        return TestConnectionResponse(**result)

    except Exception as e:
        raise HTTPException(400, str(e))


@router.post("", response_model=dict[str, Any])
async def create_tool(tool_data: OpenAPIToolCreate) -> dict[str, Any]:
    """Create new OpenAPI tool."""
    from src.database.session import get_async_session
    from src.database.tenant_context import set_db_tenant_context
    from sqlalchemy.exc import IntegrityError

    try:
        # Get database session without tenant dependency
        async for db in get_async_session():
            # Set tenant context using tenant_id from request body
            await set_db_tenant_context(db, tool_data.tenant_id)

            service = OpenAPIToolService(db)
            tool, tools_count = await service.create_tool(tool_data)

            return {
                "id": tool.id,
                "tool_name": tool.tool_name,
                "spec_version": tool.spec_version,
                "base_url": tool.base_url,
                "status": tool.status,
                "tools_count": tools_count,
                "created_at": tool.created_at.isoformat(),
            }

    except ValueError as e:
        # Handle duplicate tool name error from service layer
        raise HTTPException(409, str(e))
    except IntegrityError as e:
        # Handle database constraint violations
        if "uq_tenant_tool_name" in str(e):
            raise HTTPException(
                409,
                f"A tool with this name already exists for this tenant. "
                "Please use a different name or delete the existing tool first."
            )
        raise HTTPException(400, f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("", response_model=list[OpenAPITool])
async def list_tools(tenant_id: str, status: str | None = None, db: AsyncSession = Depends(get_tenant_db)) -> list[OpenAPITool]:
    """List all tools for tenant."""
    service = OpenAPIToolService(db)
    tools = await service.get_tools(tenant_id, status)
    return tools


@router.get("/{tool_id}", response_model=OpenAPITool)
async def get_tool(tool_id: int, db: AsyncSession = Depends(get_tenant_db)) -> OpenAPITool:
    """Get tool by ID."""
    service = OpenAPIToolService(db)
    tool = await service.get_tool_by_id(tool_id)
    if not tool:
        raise HTTPException(404, "Tool not found")
    return tool
