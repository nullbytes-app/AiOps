"""
Unit tests for Unified Tool Discovery Service.

Tests cover:
- OpenAPI tool transformation (AC2)
- MCP tool/resource/prompt transformation (AC3, AC4, AC5)
- Combined tool lists (AC1)
- Deduplication and conflict resolution (AC6)
- LangChain tool conversion (AC7)
- Caching behavior (AC8)
- Tenant isolation

Target: ≥95% code coverage
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid5, NAMESPACE_DNS

from src.schemas.unified_tool import UnifiedTool, SourceType, MCPPrimitiveType
from src.services.unified_tool_service import UnifiedToolService


# Test fixtures
@pytest.fixture
def tenant_id():
    """Test tenant ID string (as expected by UnifiedToolService.list_tools)."""
    return "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture
def mock_db_session():
    """Mock async database session."""
    return AsyncMock()


@pytest.fixture
def unified_service(mock_db_session):
    """Unified tool service instance with mocked database."""
    # Clear cache before each test
    UnifiedToolService._cache.clear()
    return UnifiedToolService(mock_db_session)


@pytest.fixture
def mock_openapi_tool():
    """Mock OpenAPI tool from database."""
    tool = MagicMock()
    tool.id = 123  # OpenAPITool.id is Integer, not UUID
    tool.tool_name = "get_weather"
    tool.openapi_spec = {
        "info": {"description": "Get weather information"},
        "parameters": {
            "type": "object",
            "properties": {"location": {"type": "string"}},
            "required": ["location"],
        },
    }
    tool.status = "active"
    return tool


@pytest.fixture
def mock_mcp_server():
    """Mock MCP server with discovered primitives."""
    server = MagicMock()
    server.id = UUID("b0b0b0b0-b0b0-b0b0-b0b0-b0b0b0b0b0b0")
    server.name = "test-server"
    server.discovered_tools = [
        {
            "name": "search_docs",
            "description": "Search documentation",
            "inputSchema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        }
    ]
    server.discovered_resources = [
        {
            "uri": "file:///config.json",
            "description": "Configuration file",
        }
    ]
    server.discovered_prompts = [
        {
            "name": "code_review",
            "description": "Review code for best practices",
            "arguments": [
                {"name": "code", "description": "Code to review", "required": True}
            ],
        }
    ]
    return server


# AC2: OpenAPI Tool Transformation Tests
@pytest.mark.asyncio
async def test_openapi_tool_transformation(
    unified_service, mock_db_session, mock_openapi_tool, tenant_id
):
    """Test OpenAPI tool is transformed correctly to UnifiedTool."""
    # Mock database query result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_openapi_tool]
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    tools = await unified_service._get_openapi_tools(tenant_id)

    assert len(tools) == 1
    tool = tools[0]
    assert isinstance(tool, UnifiedTool)
    # Verify deterministic UUID generation from integer ID
    expected_uuid = uuid5(NAMESPACE_DNS, f"openapi:{mock_openapi_tool.id}")
    assert tool.id == expected_uuid
    assert tool.name == "get_weather"
    assert tool.description == "Get weather information"
    assert tool.source_type == SourceType.OPENAPI
    assert tool.mcp_server_id is None
    assert tool.mcp_primitive_type is None
    assert tool.mcp_server_name is None
    assert tool.enabled is True
    assert "location" in tool.input_schema["properties"]


@pytest.mark.asyncio
async def test_openapi_tool_only_active(unified_service, mock_db_session, tenant_id):
    """Test only active OpenAPI tools are queried."""
    # Mock empty result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    tools = await unified_service._get_openapi_tools(tenant_id)

    # Verify query filter includes status='active'
    call_args = mock_db_session.execute.call_args[0][0]
    assert "status" in str(call_args)  # Verify filter applied
    assert len(tools) == 0


# AC3: MCP Tool Transformation Tests
def test_mcp_tool_transformation(unified_service, mock_mcp_server):
    """Test MCP tools are transformed correctly with deterministic UUID5."""
    tools = unified_service._transform_mcp_tools(mock_mcp_server)

    assert len(tools) == 1
    tool = tools[0]

    # Verify deterministic UUID
    expected_seed = f"{mock_mcp_server.id}:search_docs"
    expected_uuid = uuid5(NAMESPACE_DNS, expected_seed)
    assert tool.id == expected_uuid

    assert tool.name == "search_docs"
    assert tool.description == "Search documentation"
    assert tool.source_type == SourceType.MCP
    assert tool.mcp_server_id == mock_mcp_server.id
    assert tool.mcp_primitive_type == MCPPrimitiveType.TOOL
    assert tool.mcp_server_name == "test-server"
    assert "query" in tool.input_schema["properties"]
    assert tool.enabled is True


def test_mcp_tool_deterministic_uuid(unified_service, mock_mcp_server):
    """Test same MCP tool generates same UUID across calls."""
    tools1 = unified_service._transform_mcp_tools(mock_mcp_server)
    tools2 = unified_service._transform_mcp_tools(mock_mcp_server)

    assert tools1[0].id == tools2[0].id


# AC4: MCP Resource Transformation Tests
def test_mcp_resource_transformation(unified_service, mock_mcp_server):
    """Test MCP resources are transformed with resource:// prefix."""
    resources = unified_service._transform_mcp_resources(mock_mcp_server)

    assert len(resources) == 1
    resource = resources[0]

    assert resource.name == "resource://file:///config.json"
    assert "[RESOURCE]" in resource.description
    assert resource.source_type == SourceType.MCP
    assert resource.mcp_primitive_type == MCPPrimitiveType.RESOURCE
    assert resource.mcp_server_name == "test-server"

    # Verify const schema for URI
    assert resource.input_schema["properties"]["uri"]["const"] == "file:///config.json"
    assert "uri" in resource.input_schema["required"]


def test_mcp_resource_empty_array(unified_service):
    """Test empty discovered_resources array returns no resources."""
    server = MagicMock()
    server.discovered_resources = []

    resources = unified_service._transform_mcp_resources(server)

    assert len(resources) == 0


# AC5: MCP Prompt Transformation Tests
def test_mcp_prompt_transformation(unified_service, mock_mcp_server):
    """Test MCP prompts are transformed with [PROMPT] suffix."""
    prompts = unified_service._transform_mcp_prompts(mock_mcp_server)

    assert len(prompts) == 1
    prompt = prompts[0]

    assert prompt.name == "code_review"
    assert "[PROMPT]" in prompt.description
    assert prompt.source_type == SourceType.MCP
    assert prompt.mcp_primitive_type == MCPPrimitiveType.PROMPT

    # Verify arguments converted to JSON Schema
    assert prompt.input_schema["type"] == "object"
    assert "code" in prompt.input_schema["properties"]
    assert "code" in prompt.input_schema["required"]


def test_mcp_prompt_empty_array(unified_service):
    """Test empty discovered_prompts array returns no prompts."""
    server = MagicMock()
    server.discovered_prompts = []

    prompts = unified_service._transform_mcp_prompts(server)

    assert len(prompts) == 0


# AC1: Combined Tool List Tests
@pytest.mark.asyncio
async def test_list_tools_combines_sources(
    unified_service, mock_db_session, mock_openapi_tool, mock_mcp_server, tenant_id
):
    """Test list_tools combines OpenAPI and MCP tools."""
    # Mock tenant UUID lookup query (first query in list_tools)
    tenant_uuid_result = MagicMock()
    tenant_uuid_result.scalar_one_or_none.return_value = UUID(tenant_id)

    # Mock OpenAPI tools query
    openapi_result = MagicMock()
    openapi_result.scalars.return_value.all.return_value = [mock_openapi_tool]

    # Mock MCP servers query
    mcp_row = MagicMock()
    mcp_row.id = mock_mcp_server.id
    mcp_row.name = mock_mcp_server.name
    mcp_row.discovered_tools = mock_mcp_server.discovered_tools
    mcp_row.discovered_resources = mock_mcp_server.discovered_resources
    mcp_row.discovered_prompts = mock_mcp_server.discovered_prompts

    mcp_result = MagicMock()
    mcp_result.all.return_value = [mcp_row]

    # Mock execute to return different results for different queries (tenant UUID, OpenAPI, MCP)
    mock_db_session.execute = AsyncMock(side_effect=[tenant_uuid_result, openapi_result, mcp_result])

    tools = await unified_service.list_tools(tenant_id)

    # Should have 1 OpenAPI + 1 MCP tool + 1 resource + 1 prompt = 4 total
    assert len(tools) >= 4
    source_types = [t.source_type for t in tools]
    assert SourceType.OPENAPI in source_types
    assert SourceType.MCP in source_types


@pytest.mark.asyncio
async def test_list_tools_empty_result(unified_service, mock_db_session, tenant_id):
    """Test list_tools returns empty list when no tools exist."""
    # Mock tenant UUID lookup query
    tenant_uuid_result = MagicMock()
    tenant_uuid_result.scalar_one_or_none.return_value = UUID(tenant_id)

    # Mock empty results
    empty_openapi_result = MagicMock()
    empty_openapi_result.scalars.return_value.all.return_value = []

    empty_mcp_result = MagicMock()
    empty_mcp_result.all.return_value = []

    mock_db_session.execute = AsyncMock(side_effect=[tenant_uuid_result, empty_openapi_result, empty_mcp_result])

    tools = await unified_service.list_tools(tenant_id)

    assert len(tools) == 0


# AC6: Deduplication and Conflict Resolution Tests
def test_tool_deduplication_openapi_wins(unified_service):
    """Test OpenAPI tool takes precedence over MCP tool with same name."""
    openapi_tool = UnifiedTool(
        id=UUID("a0a0a0a0-a0a0-a0a0-a0a0-a0a0a0a0a0a0"),
        name="get_weather",
        description="OpenAPI weather tool",
        source_type=SourceType.OPENAPI,
        input_schema={},
        enabled=True,
    )

    mcp_tool = UnifiedTool(
        id=UUID("b0b0b0b0-b0b0-b0b0-b0b0-b0b0b0b0b0b0"),
        name="get_weather",
        description="MCP weather tool",
        source_type=SourceType.MCP,
        mcp_server_id=UUID("c0c0c0c0-c0c0-c0c0-c0c0-c0c0c0c0c0c0"),
        mcp_primitive_type=MCPPrimitiveType.TOOL,
        mcp_server_name="weather-server",
        input_schema={},
        enabled=True,
    )

    tools = unified_service._deduplicate_tools([openapi_tool, mcp_tool])

    # Should have 2 tools (MCP renamed)
    assert len(tools) == 2
    tool_names = [t.name for t in tools]
    assert "get_weather" in tool_names  # OpenAPI keeps name
    assert "get_weather_mcp_weather-server" in tool_names  # MCP renamed


def test_tool_deduplication_case_sensitive(unified_service):
    """Test tool names are case-sensitive for deduplication."""
    tool1 = UnifiedTool(
        id=UUID("a0a0a0a0-a0a0-a0a0-a0a0-a0a0a0a0a0a0"),
        name="GetWeather",
        description="Tool 1",
        source_type=SourceType.OPENAPI,
        input_schema={},
        enabled=True,
    )

    tool2 = UnifiedTool(
        id=UUID("b0b0b0b0-b0b0-b0b0-b0b0-b0b0b0b0b0b0"),
        name="get_weather",
        description="Tool 2",
        source_type=SourceType.MCP,
        mcp_server_id=UUID("c0c0c0c0-c0c0-c0c0-c0c0-c0c0c0c0c0c0"),
        mcp_primitive_type=MCPPrimitiveType.TOOL,
        mcp_server_name="server",
        input_schema={},
        enabled=True,
    )

    tools = unified_service._deduplicate_tools([tool1, tool2])

    # Both should be present (different names)
    assert len(tools) == 2
    assert "GetWeather" in [t.name for t in tools]
    assert "get_weather" in [t.name for t in tools]


def test_tool_deduplication_logs_conflicts(unified_service, caplog):
    """Test conflicts are logged at INFO level."""
    openapi_tool = UnifiedTool(
        id=UUID("a0a0a0a0-a0a0-a0a0-a0a0-a0a0a0a0a0a0"),
        name="search",
        description="OpenAPI",
        source_type=SourceType.OPENAPI,
        input_schema={},
        enabled=True,
    )

    mcp_tool = UnifiedTool(
        id=UUID("b0b0b0b0-b0b0-b0b0-b0b0-b0b0b0b0b0b0"),
        name="search",
        description="MCP",
        source_type=SourceType.MCP,
        mcp_server_id=UUID("c0c0c0c0-c0c0-c0c0-c0c0-c0c0c0c0c0c0"),
        mcp_primitive_type=MCPPrimitiveType.TOOL,
        mcp_server_name="search-server",
        input_schema={},
        enabled=True,
    )

    with caplog.at_level("INFO"):
        unified_service._deduplicate_tools([openapi_tool, mcp_tool])

    assert "conflict" in caplog.text.lower()


# AC7: LangChain Tool Conversion Tests
def test_to_langchain_tools_conversion(unified_service):
    """Test UnifiedTools convert to LangChain-compatible format."""
    unified_tools = [
        UnifiedTool(
            id=UUID("a0a0a0a0-a0a0-a0a0-a0a0-a0a0a0a0a0a0"),
            name="test_tool",
            description="Test tool",
            source_type=SourceType.OPENAPI,
            input_schema={
                "type": "object",
                "properties": {"param1": {"type": "string"}},
                "required": ["param1"],
            },
            enabled=True,
        )
    ]

    langchain_tools = unified_service.to_langchain_tools(unified_tools)

    assert len(langchain_tools) == 1
    tool = langchain_tools[0]
    assert tool["name"] == "test_tool"
    assert tool["description"] == "Test tool"
    assert tool["args_schema"] is not None
    assert tool["metadata"]["source_type"] == "openapi"


def test_json_schema_to_pydantic_conversion(unified_service):
    """Test JSON Schema converts to Pydantic BaseModel."""
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "User name"},
            "age": {"type": "integer", "description": "User age"},
        },
        "required": ["name"],
    }

    pydantic_model = unified_service._json_schema_to_pydantic(schema, "TestModel")

    # Verify it's a Pydantic model
    assert hasattr(pydantic_model, "model_fields")
    assert "name" in pydantic_model.model_fields
    assert "age" in pydantic_model.model_fields


# AC8: Caching Tests
@pytest.mark.asyncio
async def test_cache_hit_on_second_call(
    unified_service, mock_db_session, tenant_id
):
    """Test second call returns cached result without database query."""
    # Mock tenant UUID lookup query
    tenant_uuid_result = MagicMock()
    tenant_uuid_result.scalar_one_or_none.return_value = UUID(tenant_id)

    # Mock empty results
    empty_openapi_result = MagicMock()
    empty_openapi_result.scalars.return_value.all.return_value = []

    empty_mcp_result = MagicMock()
    empty_mcp_result.all.return_value = []

    mock_db_session.execute = AsyncMock(side_effect=[tenant_uuid_result, empty_openapi_result, empty_mcp_result])

    # First call
    tools1 = await unified_service.list_tools(tenant_id)

    # Reset mock to verify second call doesn't query database
    mock_db_session.execute.reset_mock()

    # Second call (should hit cache)
    tools2 = await unified_service.list_tools(tenant_id)

    assert tools1 == tools2
    # Database should not be queried on second call
    assert mock_db_session.execute.call_count == 0


@pytest.mark.asyncio
async def test_cache_uses_tenant_id_key(unified_service, mock_db_session):
    """Test different tenants have different cache keys."""
    tenant1 = "00000000-0000-0000-0000-000000000001"
    tenant2 = "00000000-0000-0000-0000-000000000002"

    # Mock tenant UUID lookup results
    tenant1_uuid_result = MagicMock()
    tenant1_uuid_result.scalar_one_or_none.return_value = UUID(tenant1)

    tenant2_uuid_result = MagicMock()
    tenant2_uuid_result.scalar_one_or_none.return_value = UUID(tenant2)

    # Mock results
    empty_openapi_result = MagicMock()
    empty_openapi_result.scalars.return_value.all.return_value = []

    empty_mcp_result = MagicMock()
    empty_mcp_result.all.return_value = []

    mock_db_session.execute = AsyncMock(side_effect=[
        tenant1_uuid_result, empty_openapi_result, empty_mcp_result,  # tenant1
        tenant2_uuid_result, empty_openapi_result, empty_mcp_result,  # tenant2
    ])

    # Query for both tenants
    await unified_service.list_tools(tenant1)
    await unified_service.list_tools(tenant2)

    # Both should have queried database (different cache keys) - 3 queries per tenant (UUID lookup + OpenAPI + MCP)
    assert mock_db_session.execute.call_count == 6


def test_cache_invalidation_clears_tenant_cache(unified_service, tenant_id):
    """Test invalidate_cache removes tenant's cached tools."""
    # Manually populate cache
    cache_key = f"tools:{tenant_id}"
    unified_service._cache[cache_key] = []

    assert cache_key in unified_service._cache

    # Invalidate
    unified_service.invalidate_cache(tenant_id)

    assert cache_key not in unified_service._cache


# Tenant Isolation Tests
@pytest.mark.asyncio
async def test_tenant_isolation_filters_by_tenant_id(
    unified_service, mock_db_session, tenant_id
):
    """Test all queries filter by tenant_id for security."""
    # Mock tenant UUID lookup query
    tenant_uuid_result = MagicMock()
    tenant_uuid_result.scalar_one_or_none.return_value = UUID(tenant_id)

    # Mock OpenAPI query result
    empty_openapi_result = MagicMock()
    empty_openapi_result.scalars.return_value.all.return_value = []

    # Mock MCP query result
    empty_mcp_result = MagicMock()
    empty_mcp_result.all.return_value = []

    # Use AsyncMock for execute method itself
    mock_db_session.execute = AsyncMock(side_effect=[tenant_uuid_result, empty_openapi_result, empty_mcp_result])

    await unified_service.list_tools(tenant_id)

    # Verify all 3 queries include tenant_id filter
    assert mock_db_session.execute.call_count == 3
    for call in mock_db_session.execute.call_args_list:
        query_str = str(call[0][0])
        assert "tenant_id" in query_str


# Edge Cases
def test_convert_prompt_arguments_empty_list(unified_service):
    """Test converting empty prompt arguments returns minimal schema."""
    schema = unified_service._convert_prompt_arguments_to_schema([])

    assert schema["type"] == "object"
    assert schema["properties"] == {}
    assert schema["required"] == []


def test_mcp_server_with_missing_fields(unified_service):
    """Test MCP server with missing discovered_* fields returns empty lists."""
    server = MagicMock()
    server.id = UUID("b0b0b0b0-b0b0-b0b0-b0b0-b0b0b0b0b0b0")
    server.name = "minimal-server"
    server.discovered_tools = None  # Missing field
    server.discovered_resources = None
    server.discovered_prompts = None

    # Should handle gracefully (None -> empty list in transformation)
    # This tests error resilience mentioned in constraints
    tools = unified_service._transform_mcp_tools(server)
    assert len(tools) == 0
