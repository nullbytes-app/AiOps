"""
Smoke Test Fixtures - Story 12.6

Provides shared fixtures for smoke tests validating critical end-to-end workflows.
Smoke tests focus on business logic validation (API + DB + Workers), not UI.
"""

import pytest
from uuid import uuid4
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_async_session
from src.database.models import TenantConfig, Agent, OpenAPITool, MCPServer
from src.main import app


@pytest.fixture
async def async_test_client():
    """
    HTTP client for API smoke tests.

    Yields:
        AsyncClient configured for API requests
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
async def smoke_test_tenant(async_db_session: AsyncSession):
    """
    Create a test tenant for smoke tests.

    Args:
        async_db_session: Async database session fixture

    Returns:
        TenantConfig: Test tenant with budget configured
    """
    tenant = TenantConfig(
        id=uuid4(),
        name="Smoke Test Tenant",
        webhook_secret="smoke-test-secret-key-12345",
        webhook_url="https://test.example.com/webhook",
        servicedesk_url="https://test.servicedesk.com",
        servicedesk_api_key_encrypted="encrypted_test_key",
        budget_limit_usd=100.0,
        budget_grace_period_hours=24,
    )
    async_db_session.add(tenant)
    await async_db_session.commit()
    await async_db_session.refresh(tenant)

    yield tenant

    # Cleanup
    await async_db_session.delete(tenant)
    await async_db_session.commit()


@pytest.fixture
async def smoke_test_tool(async_db_session: AsyncSession):
    """
    Create a test tool for smoke tests.

    Args:
        async_db_session: Async database session fixture

    Returns:
        OpenAPITool: Test tool for agent assignment
    """
    tool = OpenAPITool(
        id=uuid4(),
        name="smoke_test_tool",
        description="Test tool for smoke tests",
        openapi_spec={
            "openapi": "3.0.0",
            "info": {"title": "Smoke Test API", "version": "1.0"},
            "paths": {
                "/test": {
                    "get": {
                        "summary": "Test endpoint",
                        "operationId": "test_operation",
                        "responses": {"200": {"description": "Success"}},
                    }
                }
            },
        },
        base_url="https://test.example.com",
    )
    async_db_session.add(tool)
    await async_db_session.commit()
    await async_db_session.refresh(tool)

    yield tool

    # Cleanup
    await async_db_session.delete(tool)
    await async_db_session.commit()


@pytest.fixture
async def smoke_test_agent(
    async_db_session: AsyncSession,
    smoke_test_tenant: TenantConfig,
    smoke_test_tool: OpenAPITool
):
    """
    Create a test agent with tool assignment for smoke tests.

    Args:
        async_db_session: Async database session fixture
        smoke_test_tenant: Test tenant fixture
        smoke_test_tool: Test tool fixture

    Returns:
        Agent: Test agent configured with tool
    """
    agent = Agent(
        id=uuid4(),
        tenant_id=smoke_test_tenant.id,
        name="Smoke Test Agent",
        system_prompt="You are a test agent for smoke tests.",
        model="gpt-4",
        temperature=0.7,
        max_tokens=500,
        tool_ids=[str(smoke_test_tool.id)],
    )
    async_db_session.add(agent)
    await async_db_session.commit()
    await async_db_session.refresh(agent)

    yield agent

    # Cleanup
    await async_db_session.delete(agent)
    await async_db_session.commit()


@pytest.fixture
async def smoke_test_mcp_server(
    async_db_session: AsyncSession,
    smoke_test_tenant: TenantConfig
):
    """
    Create a test MCP server for smoke tests.

    Args:
        async_db_session: Async database session fixture
        smoke_test_tenant: Test tenant fixture

    Returns:
        MCPServer: Test MCP server (stdio transport)
    """
    mcp_server = MCPServer(
        id=uuid4(),
        tenant_id=smoke_test_tenant.id,
        name="Smoke Test MCP Server",
        transport_type="stdio",
        command="npx",
        args=["@modelcontextprotocol/server-everything"],
        env_vars={},
        status="inactive",  # Will be activated during test
    )
    async_db_session.add(mcp_server)
    await async_db_session.commit()
    await async_db_session.refresh(mcp_server)

    yield mcp_server

    # Cleanup
    await async_db_session.delete(mcp_server)
    await async_db_session.commit()
