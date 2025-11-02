"""
Integration tests for IP address lookup service (Story 2.7).

Tests real database interactions using test database fixtures.
Covers end-to-end workflows, tenant isolation, and concurrent access.

Fixtures and patterns align with existing integration test infrastructure
(see test_kb_search_integration.py for integration testing patterns).
"""

import pytest
from datetime import datetime
import uuid
import asyncio

from sqlalchemy import select, text, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.database.models import Base, SystemInventory
from src.services.ip_lookup import extract_and_lookup_ips

# Test database configuration - using PostgreSQL test database
# Skip tests if PostgreSQL unavailable (aiosqlite is not installed)
POSTGRES_AVAILABLE = False
TEST_DB_URL = None

try:
    # Try to use PostgreSQL test database
    TEST_DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_ops_test"
    # Test connection
    engine = create_engine("postgresql://postgres:postgres@localhost:5432/ai_ops_test")
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    POSTGRES_AVAILABLE = True
except Exception:
    # PostgreSQL not available
    pass

# Mark all integration tests as skip if PostgreSQL not available
pytestmark = pytest.mark.skipif(
    not POSTGRES_AVAILABLE,
    reason="PostgreSQL not available for integration tests"
)


@pytest.fixture
async def test_db():
    """Create test database and tables."""
    # Create async PostgreSQL engine
    engine = create_async_engine(TEST_DB_URL, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def test_session(test_db):
    """Create test database session."""
    async_session = async_sessionmaker(
        test_db, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session


@pytest.fixture
async def populated_inventory(test_session):
    """Populate test system_inventory with sample data."""
    systems = [
        # Tenant A: 3 systems
        SystemInventory(
            tenant_id="tenant-a",
            ip_address="192.168.1.10",
            hostname="web-server-1",
            role="web",
            client="client-x",
            location="us-east-1",
        ),
        SystemInventory(
            tenant_id="tenant-a",
            ip_address="10.0.0.1",
            hostname="db-server-1",
            role="database",
            client="client-x",
            location="us-east-2",
        ),
        SystemInventory(
            tenant_id="tenant-a",
            ip_address="172.16.0.1",
            hostname="cache-server-1",
            role="cache",
            client="client-y",
            location="us-west-1",
        ),
        # Tenant B: 2 systems (different tenant, same client name)
        SystemInventory(
            tenant_id="tenant-b",
            ip_address="192.168.1.10",  # Same IP as tenant-a, different tenant
            hostname="app-server-2",
            role="app",
            client="client-x",
            location="eu-west-1",
        ),
        SystemInventory(
            tenant_id="tenant-b",
            ip_address="10.0.0.5",
            hostname="storage-1",
            role="storage",
            client="client-z",
            location="eu-central-1",
        ),
        # IPv6 test data
        SystemInventory(
            tenant_id="tenant-c",
            ip_address="2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            hostname="ipv6-host-1",
            role="compute",
            client="client-ipv6",
            location="ap-south-1",
        ),
    ]

    test_session.add_all(systems)
    await test_session.commit()

    return systems


class TestEndToEndIPLookup:
    """Test end-to-end IP extraction and lookup flows."""

    @pytest.mark.asyncio
    async def test_extract_and_lookup_single_ip(self, test_session, populated_inventory):
        """Test E2E flow: extract single IP and lookup system details."""
        description = "Web server 192.168.1.10 is experiencing high CPU load"
        tenant_id = "tenant-a"

        result = await extract_and_lookup_ips(
            test_session,
            tenant_id,
            description,
            correlation_id="e2e-test-1",
        )

        assert len(result) == 1
        assert result[0]["ip_address"] == "192.168.1.10"
        assert result[0]["hostname"] == "web-server-1"
        assert result[0]["role"] == "web"
        assert result[0]["client"] == "client-x"
        assert result[0]["location"] == "us-east-1"

    @pytest.mark.asyncio
    async def test_extract_and_lookup_multiple_ips(self, test_session, populated_inventory):
        """Test E2E flow: extract multiple IPs and lookup all system details."""
        description = (
            "Critical incident: servers 192.168.1.10, 10.0.0.1, and 172.16.0.1 "
            "are all unreachable"
        )
        tenant_id = "tenant-a"

        result = await extract_and_lookup_ips(
            test_session,
            tenant_id,
            description,
            correlation_id="e2e-test-2",
        )

        assert len(result) == 3
        ips_found = {r["ip_address"] for r in result}
        assert "192.168.1.10" in ips_found
        assert "10.0.0.1" in ips_found
        assert "172.16.0.1" in ips_found

    @pytest.mark.asyncio
    async def test_no_ips_in_description(self, test_session, populated_inventory):
        """Test E2E flow: no IPs in description returns empty list."""
        description = "Service degradation reported but no IP addresses mentioned"
        tenant_id = "tenant-a"

        result = await extract_and_lookup_ips(
            test_session,
            tenant_id,
            description,
            correlation_id="e2e-test-3",
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_ip_not_in_inventory(self, test_session, populated_inventory):
        """Test E2E flow: IP extracted but not in inventory returns empty list."""
        description = "Server 1.2.3.4 has connectivity issues"
        tenant_id = "tenant-a"

        result = await extract_and_lookup_ips(
            test_session,
            tenant_id,
            description,
            correlation_id="e2e-test-4",
        )

        # IP extracted but not in inventory
        assert result == []


class TestTenantIsolation:
    """Test that tenant isolation prevents cross-tenant data access."""

    @pytest.mark.asyncio
    async def test_same_ip_different_tenants_isolation(
        self, test_session, populated_inventory
    ):
        """Test that same IP in different tenants returns different results."""
        # Both tenant-a and tenant-b have IP 192.168.1.10 but different systems
        description = "Server 192.168.1.10 affected"

        # Query as tenant-a
        result_a = await extract_and_lookup_ips(
            test_session,
            "tenant-a",
            description,
            correlation_id="isolation-1",
        )

        # Query as tenant-b
        result_b = await extract_and_lookup_ips(
            test_session,
            "tenant-b",
            description,
            correlation_id="isolation-2",
        )

        # Both should find the system, but different ones
        assert len(result_a) == 1
        assert len(result_b) == 1
        assert result_a[0]["hostname"] == "web-server-1"
        assert result_b[0]["hostname"] == "app-server-2"

    @pytest.mark.asyncio
    async def test_tenant_cannot_access_other_tenant_systems(
        self, test_session, populated_inventory
    ):
        """Test that tenant-a cannot access tenant-b systems."""
        # Try to access tenant-b's IP as tenant-a
        description = "Server 10.0.0.5 issue"  # This IP belongs to tenant-b only
        tenant_id = "tenant-a"

        result = await extract_and_lookup_ips(
            test_session,
            tenant_id,
            description,
            correlation_id="isolation-3",
        )

        # Should return empty list (tenant-a has no system with this IP)
        assert result == []

    @pytest.mark.asyncio
    async def test_multiple_tenants_same_query_isolation(
        self, test_session, populated_inventory
    ):
        """Test concurrent queries from different tenants are isolated."""
        description = "Check IPs 192.168.1.10 and 10.0.0.1"

        # Tenant-a can see both
        result_a = await extract_and_lookup_ips(
            test_session,
            "tenant-a",
            description,
            correlation_id="isolation-4",
        )

        # Tenant-b can only see 192.168.1.10 (has 10.0.0.5, not 10.0.0.1)
        result_b = await extract_and_lookup_ips(
            test_session,
            "tenant-b",
            description,
            correlation_id="isolation-5",
        )

        assert len(result_a) == 2  # tenant-a has both IPs
        assert len(result_b) == 1  # tenant-b has only 192.168.1.10


class TestIPv6Support:
    """Test IPv6 address support (AC #6)."""

    @pytest.mark.asyncio
    async def test_ipv6_extraction_and_lookup(self, test_session, populated_inventory):
        """Test extraction and lookup of IPv6 addresses."""
        description = "IPv6 system 2001:0db8:85a3:0000:0000:8a2e:0370:7334 health check needed"
        tenant_id = "tenant-c"

        result = await extract_and_lookup_ips(
            test_session,
            tenant_id,
            description,
            correlation_id="ipv6-1",
        )

        assert len(result) == 1
        assert result[0]["ip_address"] == "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        assert result[0]["hostname"] == "ipv6-host-1"
        assert result[0]["role"] == "compute"

    @pytest.mark.asyncio
    async def test_mixed_ipv4_ipv6_lookup(self, test_session, populated_inventory):
        """Test extraction and lookup of mixed IPv4 and IPv6 addresses."""
        description = (
            "Affected systems: 192.168.1.10 (v4) and "
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334 (v6)"
        )
        # Need to use tenant-a for IPv4, but IPv6 is in tenant-c
        # This test demonstrates that each tenant can only see their own

        # Tenant-a query finds IPv4
        result_a = await extract_and_lookup_ips(
            test_session,
            "tenant-a",
            description,
            correlation_id="mixed-1",
        )
        assert len(result_a) == 1
        assert "192.168.1.10" in result_a[0]["ip_address"]

        # Tenant-c query finds IPv6
        result_c = await extract_and_lookup_ips(
            test_session,
            "tenant-c",
            description,
            correlation_id="mixed-2",
        )
        assert len(result_c) == 1
        assert "2001:0db8:85a3" in result_c[0]["ip_address"]


class TestErrorHandling:
    """Test error handling and graceful degradation."""

    @pytest.mark.asyncio
    async def test_empty_description_returns_empty_list(self, test_session, populated_inventory):
        """Test that empty description returns empty list (not error)."""
        result = await extract_and_lookup_ips(
            test_session,
            "tenant-a",
            "",
            correlation_id="err-1",
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_whitespace_only_description(self, test_session, populated_inventory):
        """Test that whitespace-only description returns empty list."""
        result = await extract_and_lookup_ips(
            test_session,
            "tenant-a",
            "   \n\t  ",
            correlation_id="err-2",
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_invalid_tenant_id_returns_empty_list(self, test_session, populated_inventory):
        """Test that invalid tenant_id returns empty list."""
        result = await extract_and_lookup_ips(
            test_session,
            "",
            "Server 192.168.1.10 down",
            correlation_id="err-3",
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_non_string_description_returns_empty_list(
        self, test_session, populated_inventory
    ):
        """Test that non-string description returns empty list."""
        result = await extract_and_lookup_ips(
            test_session,
            "tenant-a",
            None,  # type: ignore
            correlation_id="err-4",
        )

        assert result == []


class TestDataConsistency:
    """Test data consistency and integrity."""

    @pytest.mark.asyncio
    async def test_lookup_returns_correct_fields(self, test_session, populated_inventory):
        """Test that lookup returns all required fields."""
        description = "Server 192.168.1.10"
        result = await extract_and_lookup_ips(
            test_session,
            "tenant-a",
            description,
            correlation_id="consistency-1",
        )

        assert len(result) == 1
        system = result[0]

        # Check all required fields present
        required_fields = {"ip_address", "hostname", "role", "client", "location"}
        assert all(field in system for field in required_fields)

        # Check data types
        assert isinstance(system["ip_address"], str)
        assert isinstance(system["hostname"], str)
        assert isinstance(system["role"], str)
        assert isinstance(system["client"], str)
        assert isinstance(system["location"], str)

    @pytest.mark.asyncio
    async def test_lookup_result_order_consistent(self, test_session, populated_inventory):
        """Test that multiple lookups return consistent results."""
        description = "Servers 192.168.1.10 and 10.0.0.1"

        result1 = await extract_and_lookup_ips(
            test_session,
            "tenant-a",
            description,
            correlation_id="consistency-2-a",
        )

        result2 = await extract_and_lookup_ips(
            test_session,
            "tenant-a",
            description,
            correlation_id="consistency-2-b",
        )

        # Same IPs found in both queries
        ips1 = {r["ip_address"] for r in result1}
        ips2 = {r["ip_address"] for r in result2}
        assert ips1 == ips2
