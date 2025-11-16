"""
MCP Server Service Layer.

Business logic for MCP server CRUD operations and capability discovery.
Handles database operations, MCPStdioClient integration, and error handling.

Story 11.1.4: MCP Server Management API - Service layer implementation.
"""

import logging
from datetime import datetime, timezone
from typing import Any, cast
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import MCPServer, MCPServerStatus, TransportType
from src.schemas.mcp_server import (
    MCPServerCreate,
    MCPServerResponse,
    MCPServerUpdate,
)
from src.services.mcp_stdio_client import (
    InitializationError,
    InvalidJSONError,
    MCPError,
    MCPStdioClient,
    ProcessError,
    TimeoutError as MCPTimeoutError,
)
from src.services.mcp_http_sse_client import (
    MCPStreamableHTTPClient,
    MCPConnectionError,
    MCPClientError,
    MCPServerError,
)

logger = logging.getLogger(__name__)


class MCPServerService:
    """Service class for MCP server CRUD and discovery operations."""

    def __init__(self, db: AsyncSession | None = None):
        """
        Initialize MCP server service.

        Args:
            db: Async database session for queries (optional for test_connection).
        """
        self.db = db

    async def create_server(self, data: MCPServerCreate, tenant_id: UUID) -> MCPServer:
        """
        Create new MCP server with automatic capability discovery.

        Args:
            data: MCP server creation data.
            tenant_id: Tenant ID from authenticated user context.

        Returns:
            Created MCP server with discovered capabilities.

        Raises:
            IntegrityError: If server name already exists for tenant.

        Example:
            >>> service = MCPServerService(db)
            >>> data = MCPServerCreate(
            ...     name="example-server",
            ...     transport_type="stdio",
            ...     command="npx",
            ...     args=["-y", "@modelcontextprotocol/server-everything"]
            ... )
            >>> server = await service.create_server(data, tenant_id)
        """
        # Create server record with status='inactive' initially
        server = MCPServer(
            **data.model_dump(exclude_unset=True),
            tenant_id=tenant_id,
            status=MCPServerStatus.INACTIVE,
        )

        self.db.add(server)
        try:
            await self.db.commit()
            await self.db.refresh(server)
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Failed to create server (duplicate name?): {e}", exc_info=True)
            raise

        # Run automatic discovery
        # Cast server.id to UUID to avoid mypy Column[UUID] vs UUID issue
        await self.discover_capabilities(cast(UUID, server.id))
        await self.db.refresh(server)

        logger.info(
            f"Created MCP server {server.id} for tenant {tenant_id} with status {server.status}"
        )
        return server

    async def list_servers(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: MCPServerStatus | None = None,
        transport_type: TransportType | None = None,
    ) -> tuple[list[MCPServer], int]:
        """
        List MCP servers for tenant with pagination and filtering.

        Args:
            tenant_id: Tenant ID from authenticated user context.
            skip: Number of records to skip (pagination offset).
            limit: Maximum number of records to return (max 1000).
            status: Optional status filter (active/inactive/error).
            transport_type: Optional transport type filter (stdio/http_sse).

        Returns:
            Tuple of (list of servers, total count).

        Example:
            >>> servers, total = await service.list_servers(
            ...     tenant_id=uuid4(),
            ...     skip=0,
            ...     limit=50,
            ...     status=MCPServerStatus.ACTIVE
            ... )
        """
        # Build base query with tenant isolation
        stmt = select(MCPServer).where(MCPServer.tenant_id == tenant_id)

        # Apply filters
        if status:
            stmt = stmt.where(MCPServer.status == status)
        if transport_type:
            stmt = stmt.where(MCPServer.transport_type == transport_type)

        # Count total matching records
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        # Apply pagination
        stmt = stmt.offset(skip).limit(min(limit, 1000))  # Cap at 1000 max

        # Execute query
        result = await self.db.execute(stmt)
        servers = list(result.scalars().all())

        logger.info(f"Listed {len(servers)} MCP servers for tenant {tenant_id} (total: {total})")
        return servers, total

    async def get_server_by_id(self, server_id: UUID, tenant_id: UUID) -> MCPServer | None:
        """
        Get MCP server details by ID with tenant isolation.

        Args:
            server_id: Server UUID.
            tenant_id: Tenant ID from authenticated user context.

        Returns:
            MCP server if found and belongs to tenant, None otherwise.

        Example:
            >>> server = await service.get_server_by_id(server_id, tenant_id)
            >>> if server:
            ...     print(f"Found server: {server.name}")
        """
        stmt = select(MCPServer).where(MCPServer.id == server_id, MCPServer.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        server = result.scalar_one_or_none()

        if server:
            logger.debug(f"Retrieved MCP server {server_id} for tenant {tenant_id}")
        else:
            logger.debug(
                f"MCP server {server_id} not found or not accessible by tenant {tenant_id}"
            )

        return server

    async def update_server(
        self, server_id: UUID, updates: MCPServerUpdate, tenant_id: UUID
    ) -> MCPServer | None:
        """
        Update MCP server (partial update supported).

        Args:
            server_id: Server UUID.
            updates: Partial update data (only provided fields updated).
            tenant_id: Tenant ID from authenticated user context.

        Returns:
            Updated server if found and belongs to tenant, None otherwise.

        Example:
            >>> updates = MCPServerUpdate(name="new-name", description="Updated")
            >>> server = await service.update_server(server_id, updates, tenant_id)
        """
        # Verify server exists and belongs to tenant
        server = await self.get_server_by_id(server_id, tenant_id)
        if not server:
            return None

        # Apply updates (exclude unset fields for partial update)
        update_data = updates.model_dump(exclude_unset=True)

        # Update server fields
        for field, value in update_data.items():
            setattr(server, field, value)

        # updated_at handled automatically by SQLAlchemy onupdate

        await self.db.commit()
        await self.db.refresh(server)

        logger.info(f"Updated MCP server {server_id} for tenant {tenant_id}")
        return server

    async def delete_server(self, server_id: UUID, tenant_id: UUID) -> bool:
        """
        Delete MCP server (hard delete).

        Args:
            server_id: Server UUID.
            tenant_id: Tenant ID from authenticated user context.

        Returns:
            True if server was deleted, False if not found or not accessible.

        Example:
            >>> deleted = await service.delete_server(server_id, tenant_id)
            >>> if deleted:
            ...     print("Server deleted successfully")
        """
        # Verify server exists and belongs to tenant first
        server = await self.get_server_by_id(server_id, tenant_id)
        if not server:
            return False

        # Hard delete
        stmt = delete(MCPServer).where(MCPServer.id == server_id, MCPServer.tenant_id == tenant_id)
        await self.db.execute(stmt)
        await self.db.commit()

        logger.info(f"Deleted MCP server {server_id} for tenant {tenant_id}")
        return True

    async def discover_capabilities(self, server_id: UUID) -> None:
        """
        Run MCP server capability discovery workflow.

        Discovers tools, resources, and prompts via MCPStdioClient.
        Updates server status and discovered_* fields in database.

        Args:
            server_id: Server UUID to discover.

        Workflow:
            1. Load server config from database
            2. Spawn MCPStdioClient
            3. Initialize handshake
            4. List tools, resources, prompts
            5. Update database with results

        Example:
            >>> await service.discover_capabilities(server_id)
        """
        # Load server from database
        result = await self.db.execute(select(MCPServer).where(MCPServer.id == server_id))
        server = result.scalar_one_or_none()
        if not server:
            logger.error(f"Server {server_id} not found for discovery")
            return

        logger.info(f"Starting capability discovery for server {server_id}")

        try:
            # Create config object for client
            config = MCPServerResponse.model_validate(server)

            # Initialize empty lists for capabilities
            tools: list[dict[str, Any]] = []
            resources: list[dict[str, Any]] = []
            prompts: list[dict[str, Any]] = []

            # Select appropriate client based on transport type
            if server.transport_type == TransportType.STDIO:
                # Run discovery with stdio client
                async with MCPStdioClient(config) as client:
                    # Initialize handshake
                    await client.initialize()

                    # Discover capabilities - make resources and prompts optional
                    tools = await client.list_tools()
                    
                    # Try to discover resources, but don't fail if not supported
                    try:
                        resources = await client.list_resources()
                    except MCPError as e:
                        if "Method not found" in str(e):
                            logger.info(f"Server {server_id} does not support resources/list")
                            resources = []
                        else:
                            raise
                    
                    # Try to discover prompts, but don't fail if not supported
                    try:
                        prompts = await client.list_prompts()
                    except MCPError as e:
                        if "Method not found" in str(e):
                            logger.info(f"Server {server_id} does not support prompts/list")
                            prompts = []
                        else:
                            raise

            elif server.transport_type == TransportType.HTTP_SSE:
                # Run discovery with HTTP client
                if not server.url:
                    raise ValueError(f"HTTP transport requires URL for server {server_id}")

                async with MCPStreamableHTTPClient(server.url, server.headers or {}) as client:
                    # Initialize handshake
                    await client.initialize()

                    # Discover capabilities - make resources and prompts optional
                    tools = await client.list_tools()
                    
                    # Try to discover resources, but don't fail if not supported
                    try:
                        resources = await client.list_resources()
                    except MCPError as e:
                        if "Method not found" in str(e):
                            logger.info(f"Server {server_id} does not support resources/list")
                            resources = []
                        else:
                            raise
                    
                    # Try to discover prompts, but don't fail if not supported
                    try:
                        prompts = await client.list_prompts()
                    except MCPError as e:
                        if "Method not found" in str(e):
                            logger.info(f"Server {server_id} does not support prompts/list")
                            prompts = []
                        else:
                            raise

            else:
                raise ValueError(f"Unsupported transport type: {server.transport_type}")

            # Update server with discovered capabilities
            server.discovered_tools = tools  # type: ignore[assignment]
            server.discovered_resources = resources  # type: ignore[assignment]
            server.discovered_prompts = prompts  # type: ignore[assignment]
            server.last_health_check = datetime.now(timezone.utc)  # type: ignore[assignment]
            server.status = MCPServerStatus.ACTIVE  # type: ignore[assignment]
            server.error_message = None  # type: ignore[assignment]

            await self.db.commit()

            logger.info(
                f"Discovery completed for server {server_id}: "
                f"{len(tools)} tools, {len(resources)} resources, {len(prompts)} prompts"
            )

        except MCPTimeoutError as e:
            server.status = MCPServerStatus.ERROR  # type: ignore[assignment]
            server.error_message = f"Discovery timed out: {str(e)}"  # type: ignore[assignment]
            await self.db.commit()
            logger.error(f"Discovery timeout for server {server_id}: {e}", exc_info=True)

        except (
            ProcessError,
            InitializationError,
            InvalidJSONError,
            MCPConnectionError,
            MCPClientError,
            MCPServerError,
            MCPError,
        ) as e:
            server.status = MCPServerStatus.ERROR  # type: ignore[assignment]
            server.error_message = f"Discovery failed: {str(e)}"  # type: ignore[assignment]
            await self.db.commit()
            logger.error(f"Discovery error for server {server_id}: {e}", exc_info=True)

        except Exception as e:
            # Catch-all for unexpected errors
            server.status = MCPServerStatus.ERROR  # type: ignore[assignment]
            server.error_message = f"Unexpected error: {str(e)}"  # type: ignore[assignment]
            await self.db.commit()
            logger.error(
                f"Unexpected error during discovery for server {server_id}: {e}",
                exc_info=True,
            )

    async def test_connection(self, server_config: MCPServerCreate) -> dict[str, Any]:
        """
        Test MCP server connection without saving to database.

        Validates server configuration by performing full discovery workflow:
        initialize → list_tools → list_resources → list_prompts.
        Returns discovered capabilities on success, or error details on failure.

        Args:
            server_config: MCP server configuration to test

        Returns:
            dict with keys:
                - success: bool
                - server_info: dict | None (protocol_version, server_name, capabilities)
                - discovered_tools: list[dict]
                - discovered_resources: list[dict]
                - discovered_prompts: list[dict]
                - error: str | None (high-level error message)
                - error_details: str | None (detailed error for debugging)

        Example Success:
            {
                "success": True,
                "server_info": {
                    "protocol_version": "2025-03-26",
                    "server_name": "Example MCP Server",
                    "capabilities": ["tools", "resources", "prompts"]
                },
                "discovered_tools": [...],
                "discovered_resources": [...],
                "discovered_prompts": [...],
                "error": None,
                "error_details": None
            }

        Example Failure:
            {
                "success": False,
                "server_info": None,
                "discovered_tools": [],
                "discovered_resources": [],
                "discovered_prompts": [],
                "error": "Connection timeout",
                "error_details": "httpx.ConnectTimeout after 10 seconds"
            }

        Story 11.2.2: HTTP+SSE Configuration in UI and API (AC4)
        """
        logger.info(
            f"Testing connection for {server_config.transport_type} server: {server_config.name}"
        )

        try:
            # Select appropriate client based on transport type
            if server_config.transport_type == TransportType.STDIO:
                # Test stdio transport
                async with MCPStdioClient(
                    MCPServerResponse(
                        id=UUID("00000000-0000-0000-0000-000000000000"),  # Dummy ID for testing
                        tenant_id=UUID("00000000-0000-0000-0000-000000000000"),  # Dummy tenant
                        name=server_config.name,
                        description=server_config.description,
                        transport_type=server_config.transport_type,
                        command=server_config.command,
                        args=server_config.args,
                        env=server_config.env,
                        url=None,
                        headers={},
                        discovered_tools=[],
                        discovered_resources=[],
                        discovered_prompts=[],
                        status=MCPServerStatus.INACTIVE,
                        last_health_check=None,
                        error_message=None,
                        consecutive_failures=0,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                ) as client:
                    # Initialize handshake
                    init_response = await client.initialize()

                    # Discover capabilities
                    tools = await client.list_tools()
                    resources = await client.list_resources()
                    prompts = await client.list_prompts()

                    # Build server info from init response
                    server_info = {
                        "protocol_version": init_response.get("protocolVersion", "unknown"),
                        "server_name": init_response.get("serverInfo", {}).get(
                            "name", server_config.name
                        ),
                        "capabilities": list(init_response.get("capabilities", {}).keys()),
                    }

            elif server_config.transport_type == TransportType.HTTP_SSE:
                # Test HTTP+SSE transport
                if not server_config.url:
                    return {
                        "success": False,
                        "server_info": None,
                        "discovered_tools": [],
                        "discovered_resources": [],
                        "discovered_prompts": [],
                        "error": "URL is required for http_sse transport",
                        "error_details": "Cannot test connection without a valid HTTP/HTTPS URL",
                    }

                async with MCPStreamableHTTPClient(
                    server_config.url, server_config.headers or {}
                ) as client:
                    # Initialize handshake
                    init_response = await client.initialize()

                    # Discover capabilities
                    tools = await client.list_tools()
                    resources = await client.list_resources()
                    prompts = await client.list_prompts()

                    # Build server info from init response
                    server_info = {
                        "protocol_version": init_response.get("protocolVersion", "unknown"),
                        "server_name": init_response.get("serverInfo", {}).get(
                            "name", server_config.name
                        ),
                        "capabilities": list(init_response.get("capabilities", {}).keys()),
                    }

            else:
                return {
                    "success": False,
                    "server_info": None,
                    "discovered_tools": [],
                    "discovered_resources": [],
                    "discovered_prompts": [],
                    "error": f"Unsupported transport type: {server_config.transport_type}",
                    "error_details": "Only 'stdio' and 'http_sse' transports are supported",
                }

            # Success - return discovered capabilities
            logger.info(
                f"Connection test successful: {len(tools)} tools, "
                f"{len(resources)} resources, {len(prompts)} prompts"
            )

            return {
                "success": True,
                "server_info": server_info,
                "discovered_tools": [
                    tool.model_dump() if hasattr(tool, "model_dump") else tool for tool in tools
                ],
                "discovered_resources": [
                    res.model_dump() if hasattr(res, "model_dump") else res for res in resources
                ],
                "discovered_prompts": [
                    prompt.model_dump() if hasattr(prompt, "model_dump") else prompt
                    for prompt in prompts
                ],
                "error": None,
                "error_details": None,
            }

        except MCPTimeoutError as e:
            logger.warning(f"Connection test timeout: {e}")
            return {
                "success": False,
                "server_info": None,
                "discovered_tools": [],
                "discovered_resources": [],
                "discovered_prompts": [],
                "error": "Connection timeout",
                "error_details": str(e),
            }

        except (
            ProcessError,
            InitializationError,
            InvalidJSONError,
            MCPConnectionError,
            MCPClientError,
            MCPServerError,
            MCPError,
        ) as e:
            logger.warning(f"Connection test failed: {e}")
            # Extract more specific error message
            error_type = type(e).__name__
            return {
                "success": False,
                "server_info": None,
                "discovered_tools": [],
                "discovered_resources": [],
                "discovered_prompts": [],
                "error": f"{error_type}: {str(e).split(':')[0] if ':' in str(e) else str(e)}",
                "error_details": str(e),
            }

        except Exception as e:
            logger.error(f"Unexpected error during connection test: {e}", exc_info=True)
            return {
                "success": False,
                "server_info": None,
                "discovered_tools": [],
                "discovered_resources": [],
                "discovered_prompts": [],
                "error": "Unexpected error during connection test",
                "error_details": str(e),
            }

    async def check_health(self, server_id: UUID, tenant_id: UUID) -> dict[str, Any] | None:
        """
        Perform lightweight health check on MCP server.

        Runs initialize() only (no full discovery) with 10s timeout.

        Args:
            server_id: Server UUID.
            tenant_id: Tenant ID from authenticated user context.

        Returns:
            Health status dict or None if server not found.

        Example:
            >>> health = await service.check_health(server_id, tenant_id)
            >>> print(f"Status: {health['status']}, Response time: {health['response_time_ms']}ms")
        """
        # Verify server exists and belongs to tenant
        server = await self.get_server_by_id(server_id, tenant_id)
        if not server:
            return None

        logger.info(f"Starting health check for server {server_id}")

        start_time = datetime.now(timezone.utc)
        health_status = {
            "server_id": str(server_id),
            "status": "error",
            "last_check": start_time.isoformat(),
            "response_time_ms": 0,
            "error_message": None,
        }

        try:
            # Create config object
            config = MCPServerResponse.model_validate(server)

            # Perform lightweight health check (initialize only)
            # Note: Uses default 30s timeout from client (no configurable timeout parameter)
            if server.transport_type == TransportType.STDIO:
                async with MCPStdioClient(config) as client:
                    await client.initialize()

            elif server.transport_type == TransportType.HTTP_SSE:
                if not server.url:
                    raise ValueError(f"HTTP transport requires URL for server {server_id}")

                async with MCPStreamableHTTPClient(server.url, server.headers or {}) as client:
                    await client.initialize()

            else:
                raise ValueError(f"Unsupported transport type: {server.transport_type}")

            # Calculate response time
            end_time = datetime.now(timezone.utc)
            response_time_ms = int((end_time - start_time).total_seconds() * 1000)

            # Update health status
            health_status["status"] = "active"
            health_status["response_time_ms"] = response_time_ms

            # Update server in database
            server.last_health_check = start_time  # type: ignore[assignment]
            server.status = MCPServerStatus.ACTIVE  # type: ignore[assignment]
            server.error_message = None  # type: ignore[assignment]
            await self.db.commit()

            logger.info(f"Health check passed for server {server_id} ({response_time_ms}ms)")

        except MCPTimeoutError as e:
            health_status["error_message"] = f"Health check timed out: {str(e)}"
            server.status = MCPServerStatus.ERROR  # type: ignore[assignment]
            server.error_message = health_status["error_message"]  # type: ignore[assignment]
            await self.db.commit()
            logger.warning(f"Health check timeout for server {server_id}: {e}")

        except (
            ProcessError,
            InitializationError,
            MCPConnectionError,
            MCPClientError,
            MCPServerError,
            MCPError,
        ) as e:
            health_status["error_message"] = f"Health check failed: {str(e)}"
            server.status = MCPServerStatus.ERROR  # type: ignore[assignment]
            server.error_message = health_status["error_message"]  # type: ignore[assignment]
            await self.db.commit()
            logger.warning(f"Health check failed for server {server_id}: {e}")

        except Exception as e:
            health_status["error_message"] = f"Unexpected error: {str(e)}"
            server.status = MCPServerStatus.ERROR  # type: ignore[assignment]
            server.error_message = health_status["error_message"]  # type: ignore[assignment]
            await self.db.commit()
            logger.error(
                f"Unexpected error during health check for server {server_id}: {e}",
                exc_info=True,
            )

        return health_status
