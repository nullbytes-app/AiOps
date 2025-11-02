"""
Pytest fixtures for Row-Level Security (RLS) testing.

Provides multi-tenant test data and database sessions for RLS validation.
Story: 3.1 - Implement Row-Level Security in PostgreSQL
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import TenantConfig, EnhancementHistory, TicketHistory, SystemInventory
from datetime import datetime, UTC


@pytest.fixture
async def db_session():
    """
    Provide a test database session with automatic rollback.

    Creates an async database session for testing RLS functionality.
    All changes are rolled back after each test to maintain test isolation.

    Yields:
        AsyncSession: Database session for test operations

    Note:
        - Does NOT set tenant context - individual test fixtures handle that
        - Automatically rolls back all changes after test completion
        - Uses the same database URL from conftest.py environment setup
        - Creates engine/session within test's event loop to avoid loop conflicts
    """
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from src.config import settings

    # Create engine within the test's event loop
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True
    )

    # Create session factory
    async_session_maker = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    # Create session
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            # Rollback all changes to maintain test isolation
            await session.rollback()
            await session.close()

    # Dispose engine after test
    await engine.dispose()


@pytest.fixture
async def rls_test_session():
    """
    Provide a test database session using non-privileged user for RLS isolation testing.

    This fixture connects as 'test_user' which does NOT have BYPASSRLS privilege,
    allowing RLS policies to be properly tested. Use this fixture for tests that
    verify RLS isolation (cross-tenant blocking, missing context, etc.).

    Yields:
        AsyncSession: Database session subject to RLS policies

    Note:
        - RLS policies WILL apply to this session (test_user has no BYPASSRLS)
        - Automatically rolls back all changes after test completion
        - Use regular db_session fixture for admin/setup operations
    """
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    # Create engine with test_user (no BYPASSRLS)
    test_db_url = "postgresql+asyncpg://test_user:test_password@localhost:5433/ai_agents"
    engine = create_async_engine(
        test_db_url,
        echo=False,
        pool_pre_ping=True
    )

    # Create session factory
    async_session_maker = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    # Create session
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            # Rollback all changes to maintain test isolation
            await session.rollback()
            await session.close()

    # Dispose engine after test
    await engine.dispose()


@pytest.fixture
async def test_tenant_config(db_session: AsyncSession):
    """Create a test tenant configuration."""
    tenant = TenantConfig(
        tenant_id="test-tenant-001",
        name="Test Tenant Inc",
        servicedesk_url="https://test.servicedesk.com",
        servicedesk_api_key_encrypted="encrypted_key_test",
        webhook_signing_secret_encrypted="encrypted_secret_test",
        enhancement_preferences={}
    )
    db_session.add(tenant)
    await db_session.flush()  # Flush instead of commit to keep changes in transaction
    await db_session.refresh(tenant)
    return tenant


@pytest.fixture
async def tenant_a_config(db_session: AsyncSession):
    """Create tenant A configuration for multi-tenant tests."""
    tenant = TenantConfig(
        tenant_id="tenant-a",
        name="Tenant A Corporation",
        servicedesk_url="https://tenanta.servicedesk.com",
        servicedesk_api_key_encrypted="encrypted_key_a",
        webhook_signing_secret_encrypted="encrypted_secret_a",
        enhancement_preferences={}
    )
    db_session.add(tenant)
    await db_session.commit()  # Commit so test_user session can see it
    await db_session.refresh(tenant)

    # Clean up after test
    yield tenant

    # Delete tenant after test completes
    await db_session.delete(tenant)
    await db_session.commit()


@pytest.fixture
async def tenant_b_config(db_session: AsyncSession):
    """Create tenant B configuration for multi-tenant tests."""
    tenant = TenantConfig(
        tenant_id="tenant-b",
        name="Tenant B Industries",
        servicedesk_url="https://tenantb.servicedesk.com",
        servicedesk_api_key_encrypted="encrypted_key_b",
        webhook_signing_secret_encrypted="encrypted_secret_b",
        enhancement_preferences={}
    )
    db_session.add(tenant)
    await db_session.commit()  # Commit so test_user session can see it
    await db_session.refresh(tenant)

    # Clean up after test
    yield tenant

    # Delete tenant after test completes
    await db_session.delete(tenant)
    await db_session.commit()


@pytest.fixture
async def tenant_a_enhancement(db_session: AsyncSession, tenant_a_config):
    """Create enhancement record for tenant A."""
    from src.database.tenant_context import set_db_tenant_context

    # Set tenant context before inserting
    await set_db_tenant_context(db_session, tenant_a_config.tenant_id)

    enhancement = EnhancementHistory(
        tenant_id=tenant_a_config.tenant_id,
        ticket_id="TKT-A-001",
        status="pending",
        context_gathered={"test": "data"},
        llm_output="Test enhancement for tenant A",
        processing_time_ms=100
    )
    db_session.add(enhancement)
    await db_session.commit()  # Commit so test_user session can see it
    await db_session.refresh(enhancement)

    # Clean up after test
    yield enhancement

    # Delete enhancement after test completes
    await db_session.delete(enhancement)
    await db_session.commit()


@pytest.fixture
async def tenant_b_enhancement(db_session: AsyncSession, tenant_b_config):
    """Create enhancement record for tenant B."""
    from src.database.tenant_context import set_db_tenant_context

    # Set tenant context before inserting
    await set_db_tenant_context(db_session, tenant_b_config.tenant_id)

    enhancement = EnhancementHistory(
        tenant_id=tenant_b_config.tenant_id,
        ticket_id="TKT-B-001",
        status="pending",
        context_gathered={"test": "data"},
        llm_output="Test enhancement for tenant B",
        processing_time_ms=100
    )
    db_session.add(enhancement)
    await db_session.commit()  # Commit so test_user session can see it
    await db_session.refresh(enhancement)

    # Clean up after test
    yield enhancement

    # Delete enhancement after test completes
    await db_session.delete(enhancement)
    await db_session.commit()
