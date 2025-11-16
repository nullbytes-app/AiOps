"""OpenAPI Tool Service - Business logic for OpenAPI tool management."""

from typing import Any, Optional

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import OpenAPITool
from src.schemas.openapi_tool import OpenAPIToolCreate, OpenAPIToolUpdate
from src.services.openapi_parser_service import (
    detect_spec_version,
    extract_tool_metadata,
    parse_openapi_spec,
)
from src.services.mcp_tool_generator import generate_mcp_tools_from_openapi, count_generated_tools


def get_encryption_cipher() -> Fernet:
    """Get Fernet cipher for auth config encryption."""
    import os
    key = os.getenv("TENANT_ENCRYPTION_KEY", Fernet.generate_key())
    return Fernet(key if isinstance(key, bytes) else key.encode())


def encrypt_auth_config(auth_config: dict[str, Any]) -> bytes:
    """Encrypt authentication config."""
    import json
    cipher = get_encryption_cipher()
    return cipher.encrypt(json.dumps(auth_config).encode())


def decrypt_auth_config(encrypted: bytes) -> dict[str, Any]:
    """Decrypt authentication config."""
    import json
    cipher = get_encryption_cipher()
    return json.loads(cipher.decrypt(encrypted).decode())


class OpenAPIToolService:
    """Service for OpenAPI tool operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_tool(self, tool_data: OpenAPIToolCreate) -> tuple[OpenAPITool, int]:
        """Create new OpenAPI tool with MCP generation."""
        # Check if tool with same name already exists for this tenant
        existing = await self.db.execute(
            select(OpenAPITool).where(
                OpenAPITool.tenant_id == tool_data.tenant_id,
                OpenAPITool.tool_name == tool_data.tool_name
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(
                f"Tool '{tool_data.tool_name}' already exists for this tenant. "
                "Please use a different name or delete the existing tool first."
            )

        # Parse and validate spec
        spec_version = detect_spec_version(tool_data.openapi_spec)
        openapi = parse_openapi_spec(tool_data.openapi_spec)

        # Generate MCP tools
        mcp = await generate_mcp_tools_from_openapi(
            tool_data.openapi_spec,
            tool_data.auth_config,
            tool_data.base_url,
            tool_data.tool_name,
        )
        tools_count = count_generated_tools(mcp)

        # Encrypt auth config
        auth_encrypted = encrypt_auth_config(tool_data.auth_config) if tool_data.auth_config else None

        # Create database record
        db_tool = OpenAPITool(
            tenant_id=tool_data.tenant_id,
            tool_name=tool_data.tool_name,
            openapi_spec=tool_data.openapi_spec,
            spec_version=spec_version,
            base_url=tool_data.base_url,
            auth_config_encrypted=auth_encrypted,
            status="active",
            created_by=tool_data.created_by,
        )

        self.db.add(db_tool)
        await self.db.commit()
        await self.db.refresh(db_tool)

        return db_tool, tools_count

    async def get_tools(self, tenant_id: str, status: Optional[str] = None) -> list[OpenAPITool]:
        """Get all tools for tenant."""
        query = select(OpenAPITool).where(OpenAPITool.tenant_id == tenant_id)
        if status:
            query = query.where(OpenAPITool.status == status)
        result = await self.db.execute(query.order_by(OpenAPITool.created_at.desc()))
        return list(result.scalars().all())

    async def get_tool_by_id(self, tool_id: int) -> Optional[OpenAPITool]:
        """Get tool by ID."""
        result = await self.db.execute(select(OpenAPITool).where(OpenAPITool.id == tool_id))
        return result.scalar_one_or_none()

    async def update_tool(self, tool_id: int, update_data: OpenAPIToolUpdate) -> Optional[OpenAPITool]:
        """Update tool."""
        tool = await self.get_tool_by_id(tool_id)
        if not tool:
            return None

        if update_data.tool_name:
            tool.tool_name = update_data.tool_name
        if update_data.base_url:
            tool.base_url = update_data.base_url
        if update_data.auth_config:
            tool.auth_config_encrypted = encrypt_auth_config(update_data.auth_config)
        if update_data.status:
            tool.status = update_data.status

        await self.db.commit()
        await self.db.refresh(tool)
        return tool
