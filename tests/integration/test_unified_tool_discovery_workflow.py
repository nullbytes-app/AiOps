"""
Integration tests for Unified Tool Discovery Service.

Tests end-to-end workflows with real database:
- Create OpenAPI tools and MCP servers
- Discover MCP capabilities
- List unified tools
- Verify tenant isolation
- Test caching behavior
- Performance validation
"""

import pytest
import time
from uuid import UUID

from src.database.models import OpenAPITool, MCPServer, TenantConfig
from src.services.unified_tool_service import UnifiedToolService
from src.schemas.unified_tool import SourceType, MCPPrimitiveType


@pytest.fixture
async def setup_tenant(async_db_session, mock_tenant_id):
    """Create a tenant_config record for integration tests."""
    # mock_tenant_id is already a string
    tenant_id_str = mock_tenant_id
    tenant_id_uuid = UUID(tenant_id_str)

    # Create tenant config (tenant_id column is String in database)
    # Note: servicedesk_api_key_encrypted and webhook_signing_secret_encrypted are NOT NULL
    tenant_config = TenantConfig(
        tenant_id=tenant_id_str,
        name="Test Tenant",
        servicedesk_url="https://test.servicedesk.com",
        servicedesk_api_key_encrypted="gAAAAA_test_encrypted_api_key",
        webhook_signing_secret_encrypted="gAAAAA_test_encrypted_secret",
        is_active=True
    )
    async_db_session.add(tenant_config)
    # DON'T commit here - let the test commit, and rollback will clean up

    yield tenant_id_uuid  # Return UUID for use in tests

    # Cleanup handled by rollback in async_db_session fixture


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_create_and_list_unified_tools(
    async_db_session, setup_tenant
):
    """
    End-to-end test: Create OpenAPI tool and MCP server, then list unified tools.

    Tests AC1: Combined tool list from multiple sources
    """
    mock_tenant_id = setup_tenant

    # Create OpenAPI tool (id is auto-increment Integer, tenant_id is String)
    openapi_tool = OpenAPITool(
        tenant_id=str(mock_tenant_id),
        tool_name="get_weather",
        openapi_spec={
            "info": {"description": "Weather API"},
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string"}},
            },
        },
        spec_version="3.0",
        base_url="https://api.weather.com",
        status="active",
    )
    async_db_session.add(openapi_tool)

    # Create MCP server with discovered tools (tenant_id is String)
    mcp_server = MCPServer(
        id=UUID("b0b0b0b0-b0b0-b0b0-b0b0-b0b0b0b0b0b0"),
        tenant_id=str(mock_tenant_id),
        name="docs-server",
        transport_type="stdio",
        command="node",
        args=["server.js"],
        status="active",
        discovered_tools=[
            {
                "name": "search_docs",
                "description": "Search documentation",
                "inputSchema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
            }
        ],
        discovered_resources=[
            {"uri": "config://app.json", "description": "App config"}
        ],
        discovered_prompts=[
            {
                "name": "summarize",
                "description": "Summarize text",
                "arguments": [
                    {"name": "text", "description": "Text to summarize", "required": True}
                ],
            }
        ],
    )
    async_db_session.add(mcp_server)

    await async_db_session.commit()

    # List unified tools
    service = UnifiedToolService(async_db_session)
    tools = await service.list_tools(mock_tenant_id)

    # Verify combined list
    assert len(tools) == 4  # 1 OpenAPI + 1 MCP tool + 1 resource + 1 prompt

    # Verify sources
    openapi_tools = [t for t in tools if t.source_type == SourceType.OPENAPI]
    mcp_tools = [t for t in tools if t.source_type == SourceType.MCP]

    assert len(openapi_tools) == 1
    assert len(mcp_tools) == 3

    # Verify OpenAPI tool
    assert openapi_tools[0].name == "get_weather"
    assert openapi_tools[0].mcp_server_id is None

    # Verify MCP primitives
    mcp_tool = next(t for t in mcp_tools if t.mcp_primitive_type == MCPPrimitiveType.TOOL)
    assert mcp_tool.name == "search_docs"
    assert mcp_tool.mcp_server_name == "docs-server"

    mcp_resource = next(
        t for t in mcp_tools if t.mcp_primitive_type == MCPPrimitiveType.RESOURCE
    )
    assert "resource://" in mcp_resource.name

    mcp_prompt = next(
        t for t in mcp_tools if t.mcp_primitive_type == MCPPrimitiveType.PROMPT
    )
    assert "[PROMPT]" in mcp_prompt.description


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multi_tenant_isolation(async_db_session):
    """
    Test tenant isolation: Different tenants see different tools.

    Tests security constraint: Tenant isolation required
    """
    tenant_a_uuid = UUID("00000000-0000-0000-0000-000000000001")
    tenant_b_uuid = UUID("00000000-0000-0000-0000-000000000002")
    tenant_a = str(tenant_a_uuid)
    tenant_b = str(tenant_b_uuid)

    # Create tenant configs first (tenant_id is String in database)
    tenant_config_a = TenantConfig(
        tenant_id=tenant_a,
        name="Tenant A",
        servicedesk_url="https://tenanta.servicedesk.com",
        servicedesk_api_key_encrypted="gAAAAA_test_encrypted_api_key_a",
        webhook_signing_secret_encrypted="gAAAAA_test_encrypted_secret_a",
        is_active=True
    )
    async_db_session.add(tenant_config_a)

    tenant_config_b = TenantConfig(
        tenant_id=tenant_b,
        name="Tenant B",
        servicedesk_url="https://tenantb.servicedesk.com",
        servicedesk_api_key_encrypted="gAAAAA_test_encrypted_api_key_b",
        webhook_signing_secret_encrypted="gAAAAA_test_encrypted_secret_b",
        is_active=True
    )
    async_db_session.add(tenant_config_b)
    # Flush to make tenant configs visible to FK constraints, but don't commit yet
    await async_db_session.flush()

    # Create tools for Tenant A (id is auto-increment, omit it)
    tool_a = OpenAPITool(
        tenant_id=tenant_a,  # String in database
        tool_name="tenant_a_tool",
        openapi_spec={"info": {}, "parameters": {}},
        spec_version="3.0",
        base_url="https://api.example.com",
        status="active",
    )
    async_db_session.add(tool_a)

    # Create tools for Tenant B (id is auto-increment, omit it)
    tool_b = OpenAPITool(
        tenant_id=tenant_b,  # String in database
        tool_name="tenant_b_tool",
        openapi_spec={"info": {}, "parameters": {}},
        spec_version="3.0",
        base_url="https://api.example.com",
        status="active",
    )
    async_db_session.add(tool_b)

    await async_db_session.commit()

    # Query as Tenant A (list_tools expects UUID)
    service = UnifiedToolService(async_db_session)
    tools_a = await service.list_tools(tenant_a_uuid)

    # Query as Tenant B
    tools_b = await service.list_tools(tenant_b_uuid)

    # Verify isolation
    assert len(tools_a) == 1
    assert len(tools_b) == 1
    assert tools_a[0].name == "tenant_a_tool"
    assert tools_b[0].name == "tenant_b_tool"

    # Verify no cross-tenant leakage
    tool_names_a = [t.name for t in tools_a]
    tool_names_b = [t.name for t in tools_b]
    assert "tenant_b_tool" not in tool_names_a
    assert "tenant_a_tool" not in tool_names_b


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_behavior_across_calls(async_db_session, setup_tenant):
    """
    Test caching: First call slow, second call fast, invalidation works.

    Tests AC8: Performance and caching
    """
    mock_tenant_id = setup_tenant

    # Create test tool (id is auto-increment, omit it)
    tool = OpenAPITool(
        tenant_id=str(mock_tenant_id),
        tool_name="test_cache",
        openapi_spec={"info": {}, "parameters": {}},
        spec_version="3.0",
        base_url="https://api.example.com",
        status="active",
    )
    async_db_session.add(tool)
    await async_db_session.commit()

    service = UnifiedToolService(async_db_session)

    # Clear cache
    service.invalidate_cache(mock_tenant_id)

    # First call (database query)
    start = time.time()
    tools1 = await service.list_tools(mock_tenant_id)
    first_call_time = (time.time() - start) * 1000  # ms

    # Second call (cached)
    start = time.time()
    tools2 = await service.list_tools(mock_tenant_id)
    second_call_time = (time.time() - start) * 1000  # ms

    # Verify results are identical
    assert len(tools1) == len(tools2)
    assert tools1[0].id == tools2[0].id

    # Verify second call is much faster (cached)
    assert second_call_time < first_call_time
    assert second_call_time < 10  # AC8: cached reads <10ms

    # Invalidate cache
    service.invalidate_cache(mock_tenant_id)

    # Third call (database query again)
    start = time.time()
    tools3 = await service.list_tools(mock_tenant_id)
    third_call_time = (time.time() - start) * 1000  # ms

    # Verify third call slower than cached second call
    assert third_call_time > second_call_time
    assert len(tools3) == len(tools1)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_deduplication_with_real_data(async_db_session, setup_tenant):
    """
    Test deduplication with real database: OpenAPI tool takes precedence.

    Tests AC6: Tool deduplication and conflict resolution
    """
    mock_tenant_id = setup_tenant

    # Create OpenAPI tool named "search" (id is auto-increment, omit it)
    openapi_tool = OpenAPITool(
        tenant_id=str(mock_tenant_id),
        tool_name="search",
        openapi_spec={"info": {"description": "OpenAPI search"}, "parameters": {}},
        spec_version="3.0",
        base_url="https://api.example.com",
        status="active",
    )
    async_db_session.add(openapi_tool)

    # Create MCP server with tool also named "search"
    mcp_server = MCPServer(
        id=UUID("b0b0b0b0-b0b0-b0b0-b0b0-b0b0b0b0b0b0"),
        tenant_id=str(mock_tenant_id),
        name="search-server",
        transport_type="stdio",
        command="node",
        args=["server.js"],
        status="active",
        discovered_tools=[
            {
                "name": "search",
                "description": "MCP search",
                "inputSchema": {"type": "object"},
            }
        ],
        discovered_resources=[],
        discovered_prompts=[],
    )
    async_db_session.add(mcp_server)

    await async_db_session.commit()

    # List tools
    service = UnifiedToolService(async_db_session)
    tools = await service.list_tools(mock_tenant_id)

    # Should have 2 tools (MCP renamed to avoid conflict)
    assert len(tools) == 2

    tool_names = [t.name for t in tools]
    assert "search" in tool_names  # OpenAPI keeps original name
    assert "search_mcp_search-server" in tool_names  # MCP renamed


@pytest.mark.integration
@pytest.mark.asyncio
async def test_only_active_mcp_servers(async_db_session, setup_tenant):
    """
    Test only active MCP servers are included in tool discovery.

    Tests constraint: Only query MCP servers with status='active'
    """
    mock_tenant_id = setup_tenant

    # Create active MCP server
    active_server = MCPServer(
        id=UUID("a0a0a0a0-a0a0-a0a0-a0a0-a0a0a0a0a0a0"),
        tenant_id=str(mock_tenant_id),
        name="active-server",
        transport_type="stdio",
        command="node",
        args=["server.js"],
        status="active",
        discovered_tools=[{"name": "active_tool", "inputSchema": {}}],
        discovered_resources=[],
        discovered_prompts=[],
    )
    async_db_session.add(active_server)

    # Create inactive MCP server
    inactive_server = MCPServer(
        id=UUID("b0b0b0b0-b0b0-b0b0-b0b0-b0b0b0b0b0b0"),
        tenant_id=str(mock_tenant_id),
        name="inactive-server",
        transport_type="stdio",
        command="node",
        args=["server.js"],
        status="inactive",
        discovered_tools=[{"name": "inactive_tool", "inputSchema": {}}],
        discovered_resources=[],
        discovered_prompts=[],
    )
    async_db_session.add(inactive_server)

    await async_db_session.commit()

    # List tools
    service = UnifiedToolService(async_db_session)
    tools = await service.list_tools(mock_tenant_id)

    # Should only include active server's tool
    assert len(tools) == 1
    assert tools[0].name == "active_tool"
    assert tools[0].mcp_server_name == "active-server"


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
async def test_performance_with_many_tools(async_db_session, setup_tenant):
    """
    Test performance with 100 tools meets <500ms target.

    Tests AC8: Performance targets (first load <500ms p95)
    """
    mock_tenant_id = setup_tenant

    # Create 50 OpenAPI tools (id is auto-increment, omit it)
    for i in range(50):
        tool = OpenAPITool(
            tenant_id=str(mock_tenant_id),
            tool_name=f"tool_{i}",
            openapi_spec={"info": {}, "parameters": {}},
            spec_version="3.0",
            base_url="https://api.example.com",
            status="active",
        )
        async_db_session.add(tool)

    # Create 5 MCP servers with 10 tools each
    for i in range(5):
        server = MCPServer(
            id=UUID(f"{(100 + i):032x}"),
            tenant_id=str(mock_tenant_id),
            name=f"server-{i}",
            transport_type="stdio",
            command="node",
            args=["server.js"],
            status="active",
            discovered_tools=[
                {"name": f"mcp_tool_{i}_{j}", "inputSchema": {}}
                for j in range(10)
            ],
            discovered_resources=[],
            discovered_prompts=[],
        )
        async_db_session.add(server)

    await async_db_session.commit()

    # Test performance
    service = UnifiedToolService(async_db_session)
    service.invalidate_cache(mock_tenant_id)  # Ensure fresh query

    start = time.time()
    tools = await service.list_tools(mock_tenant_id)
    elapsed_ms = (time.time() - start) * 1000

    # Verify results
    assert len(tools) == 100  # 50 OpenAPI + 50 MCP

    # Verify performance target
    assert elapsed_ms < 500, f"Query took {elapsed_ms:.2f}ms (target: <500ms)"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_empty_database_returns_empty_list(async_db_session, setup_tenant):
    """Test querying with no tools returns empty list gracefully."""
    mock_tenant_id = setup_tenant

    service = UnifiedToolService(async_db_session)
    tools = await service.list_tools(mock_tenant_id)

    assert len(tools) == 0
    assert isinstance(tools, list)
