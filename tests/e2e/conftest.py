"""
E2E Test Fixtures for Playwright UI Testing.

This module provides fixtures for end-to-end UI testing with Playwright,
including database setup, Streamlit app configuration, and test data management.

Fixtures:
    - streamlit_app_url: Base URL for Streamlit app in test mode
    - test_tenant: Creates and cleans up test tenant
    - test_mcp_server: Creates and cleans up test MCP server
    - test_agent: Creates and cleans up test agent
"""

import os
from typing import Any, AsyncGenerator, Generator
from uuid import UUID

import pytest
from playwright.sync_api import Page
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Agent, Base, MCPServer, TenantConfig  # type: ignore[attr-defined]

# Test database configuration
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://aiagents:password@localhost:5432/ai_agents_test",
)
TEST_ASYNC_DATABASE_URL = TEST_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Streamlit app configuration for E2E tests
STREAMLIT_APP_URL = os.getenv("STREAMLIT_APP_URL", "http://localhost:8502")
STREAMLIT_TEST_MODE = os.getenv("TESTING", "true")


# =============================================================================
# Database Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def sync_db_engine() -> Generator[Engine, None, None]:
    """Create synchronous database engine for session-scoped setup."""
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def async_db_engine() -> Generator[AsyncEngine, None, None]:
    """Create asynchronous database engine for session-scoped setup."""
    engine = create_async_engine(TEST_ASYNC_DATABASE_URL, echo=False)
    yield engine


@pytest.fixture(scope="function")
async def async_db_session(async_db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create async database session for E2E tests.

    Automatically rolls back changes after each test to ensure test isolation.
    """
    async_session_maker = async_sessionmaker(
        async_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_maker() as session:
        yield session
        await session.rollback()


# =============================================================================
# Streamlit App Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def streamlit_app_url() -> str:
    """
    Return Streamlit app URL for E2E tests.

    Default: http://localhost:8502

    Note: Tests assume Streamlit app is running separately.
    Start app before tests: streamlit run src/admin/app.py --server.port=8502
    """
    return STREAMLIT_APP_URL


@pytest.fixture
def admin_page(page: Page, streamlit_app_url: str) -> Generator[Page, None, None]:
    """
    Navigate to Streamlit admin app with authentication bypassed.

    Args:
        page: Playwright Page object (from pytest-playwright)
        streamlit_app_url: Base URL for Streamlit app

    Yields:
        Page: Playwright page ready for admin UI interactions

    Note: TESTING=true environment variable disables authentication
    """
    # Set testing mode cookie if needed
    page.goto(streamlit_app_url)
    yield page


# =============================================================================
# Test Data Fixtures
# =============================================================================


@pytest.fixture
async def test_tenant(async_db_session: AsyncSession) -> AsyncGenerator[TenantConfig, None]:
    """
    Create test tenant for E2E tests.

    Automatically deleted after test completes.
    """
    tenant = TenantConfig(
        name="E2E Test Tenant",
        api_key="e2e-test-key-12345",
        webhook_secret="e2e-webhook-secret",
        webhook_url="https://example.com/webhook",
        servicedesk_url="https://test.example.com",
        servicedesk_api_key_encrypted=b"encrypted-test-key",
        default_budget=100.00,
    )
    async_db_session.add(tenant)
    await async_db_session.commit()
    await async_db_session.refresh(tenant)

    yield tenant

    # Cleanup: Delete test tenant
    await async_db_session.delete(tenant)
    await async_db_session.commit()


@pytest.fixture
async def test_mcp_server(
    async_db_session: AsyncSession, test_tenant: TenantConfig
) -> AsyncGenerator[MCPServer, None]:
    """
    Create test MCP server for E2E tests.

    Automatically deleted after test completes.
    """
    mcp_server = MCPServer(
        tenant_id=test_tenant.id,
        name="E2E Test MCP Server",
        description="MCP server for E2E UI testing",
        transport_type="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-everything"],
        env_vars={"DEBUG": "true"},
        health_status="inactive",
    )
    async_db_session.add(mcp_server)
    await async_db_session.commit()
    await async_db_session.refresh(mcp_server)

    yield mcp_server

    # Cleanup: Delete test MCP server
    await async_db_session.delete(mcp_server)
    await async_db_session.commit()


@pytest.fixture
async def test_agent(
    async_db_session: AsyncSession, test_tenant: TenantConfig
) -> AsyncGenerator[Agent, None]:
    """
    Create test agent for E2E tests.

    Automatically deleted after test completes.
    """
    agent = Agent(
        tenant_id=test_tenant.id,
        name="E2E Test Agent",
        description="Agent for E2E UI testing",
        system_prompt="You are a helpful assistant. Use the echo tool to repeat user messages.",
        model="gpt-4o-mini",
        budget=1.00,
        assigned_tools=[],  # Tools assigned during E2E test
    )
    async_db_session.add(agent)
    await async_db_session.commit()
    await async_db_session.refresh(agent)

    yield agent

    # Cleanup: Delete test agent
    await async_db_session.delete(agent)
    await async_db_session.commit()


# =============================================================================
# Utility Fixtures
# =============================================================================


@pytest.fixture(scope="function", autouse=True)
def set_testing_environment() -> Generator[None, None, None]:
    """
    Set TESTING environment variable for all E2E tests.

    This bypasses authentication and enables test mode in the Streamlit app.
    """
    original_value = os.getenv("TESTING")
    os.environ["TESTING"] = "true"
    yield
    if original_value is not None:
        os.environ["TESTING"] = original_value
    else:
        del os.environ["TESTING"]
