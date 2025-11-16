"""
Unified Tool Discovery Service.

This service provides a single interface for discovering and retrieving tools from
multiple sources (OpenAPI tools and MCP servers), combining them into a unified format
for agent execution with LangChain/LangGraph.
"""

import logging
from typing import Any
from uuid import UUID, uuid5, NAMESPACE_DNS

from cachetools import TTLCache
from pydantic import BaseModel, Field, create_model
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import MCPServer, OpenAPITool, TenantConfig
from src.schemas.unified_tool import (
    UnifiedTool,
    SourceType,
    MCPPrimitiveType,
)

logger = logging.getLogger(__name__)


class UnifiedToolService:
    """
    Service for unified tool discovery across OpenAPI and MCP sources.

    This service queries both OpenAPI tools and MCP servers, transforms them into
    a consistent UnifiedTool format, handles deduplication and conflict resolution,
    and provides LangChain-compatible tool definitions.

    Attributes:
        db: Async database session for querying tools and servers
        _cache: TTL cache for tool lists (60 second expiration, max 100 entries)
    """

    # Class-level cache shared across instances (60s TTL, max 100 entries)
    _cache: TTLCache[str, list[UnifiedTool]] = TTLCache(maxsize=100, ttl=60)

    def __init__(self, db: AsyncSession):
        """
        Initialize the unified tool service.

        Args:
            db: Async SQLAlchemy session for database queries
        """
        self.db = db

    async def list_tools(self, tenant_id: str) -> list[UnifiedTool]:
        """
        List all available tools for a tenant from all sources.

        Queries both OpenAPI tools and MCP servers, transforms them to unified format,
        handles deduplication (OpenAPI tools take precedence), and returns cached
        results when available.

        Args:
            tenant_id: Tenant ID string to filter tools

        Returns:
            List of UnifiedTool instances from all sources (deduplicated)

        Performance:
            - First call: <500ms (p95) - database queries
            - Cached calls: <10ms (p95) - in-memory cache hit
            - Cache TTL: 60 seconds
        """
        cache_key = f"tools:{tenant_id}"

        # Check cache first
        if cache_key in self._cache:
            logger.debug(f"Cache hit for tenant {tenant_id}")
            return self._cache[cache_key]

        logger.debug(f"Cache miss for tenant {tenant_id}, querying database")

        # Query both sources (both use tenant_id VARCHAR)
        openapi_tools = await self._get_openapi_tools(tenant_id)
        mcp_servers = await self._get_mcp_servers(tenant_id)

        # Transform MCP primitives
        mcp_tools: list[UnifiedTool] = []
        for server in mcp_servers:
            mcp_tools.extend(self._transform_mcp_tools(server))
            mcp_tools.extend(self._transform_mcp_resources(server))
            mcp_tools.extend(self._transform_mcp_prompts(server))

        # Combine all tools
        all_tools = openapi_tools + mcp_tools

        # Deduplicate and resolve conflicts
        deduplicated_tools = self._deduplicate_tools(all_tools)

        # Cache results
        self._cache[cache_key] = deduplicated_tools

        logger.info(
            f"Discovered {len(deduplicated_tools)} tools for tenant {tenant_id} "
            f"({len(openapi_tools)} OpenAPI, {len(mcp_tools)} MCP)"
        )

        return deduplicated_tools

    async def _get_openapi_tools(self, tenant_id: str) -> list[UnifiedTool]:
        """
        Query and transform OpenAPI tools for a tenant.

        Args:
            tenant_id: Tenant ID string to filter tools

        Returns:
            List of UnifiedTool instances from OpenAPI source
        """
        # tenant_id is already a string, use it directly
        tenant_id_str = tenant_id
        # Note: Multiple where conditions are ANDed together automatically in SQLAlchemy 2.0
        stmt = (
            select(OpenAPITool)
            .where(OpenAPITool.tenant_id == tenant_id_str)  # type: ignore[arg-type]
            .where(OpenAPITool.status == "active")  # type: ignore[arg-type]
        )

        result = await self.db.execute(stmt)
        openapi_tools = result.scalars().all()

        unified_tools = []
        for tool in openapi_tools:
            # Generate deterministic UUID from OpenAPI tool ID (int → UUID)
            tool_uuid = uuid5(NAMESPACE_DNS, f"openapi:{tool.id}")
            unified_tool = UnifiedTool(
                id=tool_uuid,
                name=tool.tool_name,
                description=tool.openapi_spec.get("info", {}).get("description", tool.tool_name),
                source_type=SourceType.OPENAPI,
                openapi_tool_id=tool.id,  # Store original integer ID
                mcp_server_id=None,
                mcp_primitive_type=None,
                mcp_server_name=None,
                input_schema=tool.openapi_spec.get("parameters", {}),
                enabled=True,  # Only active tools queried
            )
            unified_tools.append(unified_tool)

        logger.debug(f"Found {len(unified_tools)} OpenAPI tools for tenant {tenant_id}")
        return unified_tools

    async def _get_mcp_servers(self, tenant_id: str) -> list[MCPServer]:
        """
        Query active MCP servers for a tenant.

        Only selects needed columns (id, name, discovered_*) to minimize data transfer.

        Args:
            tenant_id: Tenant ID string to filter servers (VARCHAR)

        Returns:
            List of MCPServer instances with discovered primitives
        """
        # Note: Multiple where conditions are ANDed together automatically in SQLAlchemy 2.0
        stmt = (
            select(
                MCPServer.id,
                MCPServer.name,
                MCPServer.discovered_tools,
                MCPServer.discovered_resources,
                MCPServer.discovered_prompts,
            )
            .where(MCPServer.tenant_id == tenant_id)
            .where(MCPServer.status == "active")
        )

        result = await self.db.execute(stmt)
        servers = result.all()

        # Convert Row objects to MCPServer instances (partial)
        # Note: We only need id, name, and discovered_* fields
        mcp_servers = []
        for row in servers:
            # Create a minimal MCPServer-like object for transformation
            server_data = {
                "id": row.id,
                "name": row.name,
                "discovered_tools": row.discovered_tools or [],
                "discovered_resources": row.discovered_resources or [],
                "discovered_prompts": row.discovered_prompts or [],
            }
            mcp_servers.append(type("MCPServerPartial", (), server_data)())

        logger.debug(f"Found {len(mcp_servers)} active MCP servers for tenant {tenant_id}")
        return mcp_servers

    def _transform_mcp_tools(self, server: Any) -> list[UnifiedTool]:
        """
        Transform MCP tools from discovered_tools array.

        Generates deterministic UUID5 from server ID + tool name for consistency.

        Args:
            server: MCP server instance with discovered_tools array

        Returns:
            List of UnifiedTool instances for MCP tools
        """
        unified_tools = []
        discovered_tools = server.discovered_tools or []
        for tool in discovered_tools:
            # Generate deterministic UUID5
            seed = f"{server.id}:{tool['name']}"
            tool_id = uuid5(NAMESPACE_DNS, seed)

            unified_tool = UnifiedTool(
                id=tool_id,
                name=tool["name"],
                description=tool.get("description", tool["name"]),
                source_type=SourceType.MCP,
                mcp_server_id=server.id,
                mcp_primitive_type=MCPPrimitiveType.TOOL,
                mcp_server_name=server.name,
                input_schema=tool.get("inputSchema", {}),
                enabled=True,
            )
            unified_tools.append(unified_tool)

        return unified_tools

    def _transform_mcp_resources(self, server: Any) -> list[UnifiedTool]:
        """
        Transform MCP resources from discovered_resources array.

        Resources are prefixed with "resource://" and include a const schema for URI.

        Args:
            server: MCP server instance with discovered_resources array

        Returns:
            List of UnifiedTool instances for MCP resources
        """
        unified_tools = []
        discovered_resources = server.discovered_resources or []
        for resource in discovered_resources:
            # Generate deterministic UUID5
            seed = f"{server.id}:{resource['uri']}"
            resource_id = uuid5(NAMESPACE_DNS, seed)

            # Create const schema for resource URI
            input_schema = {
                "type": "object",
                "properties": {"uri": {"type": "string", "const": resource["uri"]}},
                "required": ["uri"],
            }

            unified_tool = UnifiedTool(
                id=resource_id,
                name=f"resource://{resource['uri']}",
                description=f"{resource.get('description', resource['uri'])} [RESOURCE]",
                source_type=SourceType.MCP,
                mcp_server_id=server.id,
                mcp_primitive_type=MCPPrimitiveType.RESOURCE,
                mcp_server_name=server.name,
                input_schema=input_schema,
                enabled=True,
            )
            unified_tools.append(unified_tool)

        return unified_tools

    def _transform_mcp_prompts(self, server: Any) -> list[UnifiedTool]:
        """
        Transform MCP prompts from discovered_prompts array.

        Prompts include "[PROMPT]" suffix in description for clarity.

        Args:
            server: MCP server instance with discovered_prompts array

        Returns:
            List of UnifiedTool instances for MCP prompts
        """
        unified_tools = []
        discovered_prompts = server.discovered_prompts or []
        for prompt in discovered_prompts:
            # Generate deterministic UUID5
            seed = f"{server.id}:{prompt['name']}"
            prompt_id = uuid5(NAMESPACE_DNS, seed)

            # Convert MCP prompt arguments to JSON Schema
            input_schema = self._convert_prompt_arguments_to_schema(prompt.get("arguments", []))

            unified_tool = UnifiedTool(
                id=prompt_id,
                name=prompt["name"],
                description=f"{prompt.get('description', prompt['name'])} [PROMPT]",
                source_type=SourceType.MCP,
                mcp_server_id=server.id,
                mcp_primitive_type=MCPPrimitiveType.PROMPT,
                mcp_server_name=server.name,
                input_schema=input_schema,
                enabled=True,
            )
            unified_tools.append(unified_tool)

        return unified_tools

    def _convert_prompt_arguments_to_schema(
        self, arguments: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Convert MCP prompt arguments to JSON Schema.

        MCP prompt arguments are in format:
        [{"name": "code", "description": "...", "required": true}]

        Converts to JSON Schema:
        {"type": "object", "properties": {...}, "required": [...]}

        Args:
            arguments: List of MCP prompt argument definitions

        Returns:
            JSON Schema dict for input validation
        """
        properties = {}
        required = []

        for arg in arguments:
            properties[arg["name"]] = {
                "type": "string",  # MCP prompts typically use strings
                "description": arg.get("description", ""),
            }
            if arg.get("required", False):
                required.append(arg["name"])

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    def _deduplicate_tools(self, tools: list[UnifiedTool]) -> list[UnifiedTool]:
        """
        Deduplicate tools with name conflicts, giving OpenAPI tools precedence.

        When multiple tools have the same name:
        - OpenAPI tools take precedence
        - MCP tools are renamed: {name}_mcp_{server_name}
        - Conflicts are logged at INFO level

        Args:
            tools: Combined list of tools from all sources

        Returns:
            Deduplicated list with renamed MCP tools where conflicts exist
        """
        seen_names: dict[str, UnifiedTool] = {}
        deduplicated: list[UnifiedTool] = []

        for tool in tools:
            if tool.name not in seen_names:
                # First occurrence - add to tracking
                seen_names[tool.name] = tool
                deduplicated.append(tool)
            else:
                # Conflict detected
                existing_tool = seen_names[tool.name]

                if existing_tool.source_type == SourceType.OPENAPI:
                    # OpenAPI takes precedence - rename MCP tool
                    if tool.source_type == SourceType.MCP:
                        new_name = f"{tool.name}_mcp_{tool.mcp_server_name}"
                        logger.info(
                            f"Tool name conflict: '{tool.name}' exists in both OpenAPI and MCP "
                            f"(server: {tool.mcp_server_name}). Renaming MCP tool to '{new_name}'"
                        )
                        tool.name = new_name
                        seen_names[new_name] = tool
                        deduplicated.append(tool)
                    else:
                        # Both OpenAPI - keep first, log warning
                        logger.warning(
                            f"Duplicate OpenAPI tool name: '{tool.name}'. Keeping first occurrence."
                        )
                elif tool.source_type == SourceType.OPENAPI:
                    # New OpenAPI tool conflicts with existing MCP - rename MCP
                    logger.info(
                        f"Tool name conflict: '{tool.name}' exists in both MCP "
                        f"(server: {existing_tool.mcp_server_name}) and OpenAPI. "
                        f"Renaming MCP tool to '{existing_tool.name}_mcp_{existing_tool.mcp_server_name}'"
                    )
                    # Rename the existing MCP tool
                    existing_tool.name = f"{existing_tool.name}_mcp_{existing_tool.mcp_server_name}"
                    # Add new OpenAPI tool
                    seen_names[tool.name] = tool
                    deduplicated.append(tool)
                else:
                    # Both MCP - rename second one
                    new_name = f"{tool.name}_mcp_{tool.mcp_server_name}"
                    logger.info(
                        f"Tool name conflict: '{tool.name}' exists in multiple MCP servers. "
                        f"Renaming to '{new_name}'"
                    )
                    tool.name = new_name
                    seen_names[new_name] = tool
                    deduplicated.append(tool)

        return deduplicated

    def to_langchain_tools(self, unified_tools: list[UnifiedTool]) -> list[Any]:
        """
        Convert UnifiedTool list to LangChain Tool instances.

        Creates LangChain-compatible tools with:
        - name: Tool identifier for LLM
        - description: Human-readable description
        - args_schema: Pydantic BaseModel generated from input_schema

        Args:
            unified_tools: List of unified tools to convert

        Returns:
            List of LangChain Tool instances (placeholder for now)

        Note:
            Full LangChain integration requires importing langchain.tools.Tool
            and creating actual callable functions for each tool. This is a
            simplified version that prepares the data structure.
        """
        langchain_tools = []

        for tool in unified_tools:
            # Generate Pydantic BaseModel from JSON Schema
            args_schema = self._json_schema_to_pydantic(tool.input_schema, tool.name)

            # Create LangChain-compatible tool dict
            # (Full implementation would create actual langchain.tools.Tool instances)
            langchain_tool = {
                "name": tool.name,
                "description": tool.description,
                "args_schema": args_schema,
                "metadata": {
                    "source_type": tool.source_type.value,
                    "openapi_tool_id": tool.id if tool.source_type == SourceType.OPENAPI else None,
                    "mcp_server_id": tool.mcp_server_id,
                    "mcp_primitive_type": (
                        tool.mcp_primitive_type.value if tool.mcp_primitive_type else None
                    ),
                },
            }
            langchain_tools.append(langchain_tool)

        return langchain_tools

    def _json_schema_to_pydantic(self, schema: dict[str, Any], model_name: str) -> type[BaseModel]:
        """
        Convert JSON Schema to Pydantic BaseModel using create_model.

        Args:
            schema: JSON Schema dict with properties and required fields
            model_name: Name for the generated Pydantic model

        Returns:
            Dynamically created Pydantic BaseModel class
        """
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        # Build field definitions for create_model
        fields: dict[str, Any] = {}
        for prop_name, prop_schema in properties.items():
            # Map JSON Schema types to Python types (simplified)
            json_type = prop_schema.get("type", "string")
            python_type = {
                "string": str,
                "integer": int,
                "number": float,
                "boolean": bool,
                "array": list,
                "object": dict,
            }.get(json_type, str)

            # Determine if field is required
            if prop_name in required:
                fields[prop_name] = (
                    python_type,
                    Field(description=prop_schema.get("description", "")),
                )
            else:
                fields[prop_name] = (
                    python_type | None,
                    Field(default=None, description=prop_schema.get("description", "")),
                )

        # Create dynamic Pydantic model
        return create_model(f"{model_name}Args", **fields)

    def invalidate_cache(self, tenant_id: str) -> None:
        """
        Invalidate cached tool list for a tenant.

        Should be called when:
        - New OpenAPI tool is created
        - MCP server discovery is triggered
        - Tool is enabled/disabled

        Args:
            tenant_id: Tenant ID string whose cache should be cleared
        """
        cache_key = f"tools:{tenant_id}"
        if cache_key in self._cache:
            del self._cache[cache_key]
            logger.debug(f"Cache invalidated for tenant {tenant_id}")
