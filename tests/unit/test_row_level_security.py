"""
Unit tests for Row-Level Security (RLS) implementation.

Tests RLS policies, tenant context management, and isolation guarantees.
These tests verify that multi-tenant data is properly isolated at the database level.

Story: 3.1 - Implement Row-Level Security in PostgreSQL
AC: 1, 2, 5
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.tenant_context import set_db_tenant_context, clear_tenant_context
from src.database.models import TenantConfig, EnhancementHistory, TicketHistory, SystemInventory


class TestTenantContextManagement:
    """Test tenant context setting and clearing."""

    @pytest.mark.asyncio
    async def test_set_tenant_context_valid_tenant(self, db_session: AsyncSession, test_tenant_config):
        """Test setting tenant context with valid tenant_id."""
        tenant_id = test_tenant_config.tenant_id

        # Should not raise exception
        await set_db_tenant_context(db_session, tenant_id)

        # Verify session variable is set
        result = await db_session.execute(
            text("SELECT current_setting('app.current_tenant_id', true)")
        )
        current_tenant = result.scalar()
        assert current_tenant == tenant_id

    @pytest.mark.asyncio
    async def test_set_tenant_context_invalid_tenant(self, db_session: AsyncSession):
        """Test setting tenant context with non-existent tenant_id raises exception."""
        invalid_tenant_id = "nonexistent-tenant-12345"

        with pytest.raises(Exception) as exc_info:
            await set_db_tenant_context(db_session, invalid_tenant_id)

        assert "Invalid tenant_id" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_clear_tenant_context(self, db_session: AsyncSession, test_tenant_config):
        """Test clearing tenant context."""
        # Set context first
        await set_db_tenant_context(db_session, test_tenant_config.tenant_id)

        # Clear context
        await clear_tenant_context(db_session)

        # Verify session variable is cleared
        result = await db_session.execute(
            text("SELECT current_setting('app.current_tenant_id', true)")
        )
        current_tenant = result.scalar()
        assert current_tenant == "" or current_tenant is None


class TestRLSCrossTenantIsolation:
    """Test RLS policies prevent cross-tenant data access."""

    @pytest.mark.asyncio
    async def test_rls_blocks_cross_tenant_select(
        self, rls_test_session: AsyncSession, tenant_a_config, tenant_b_config,
        tenant_a_enhancement, tenant_b_enhancement
    ):
        """Test SELECT queries only return rows for current tenant."""
        # Set context to tenant_a
        await set_db_tenant_context(rls_test_session, tenant_a_config.tenant_id)

        # Query enhancement_history
        result = await rls_test_session.execute(
            text("SELECT ticket_id FROM enhancement_history")
        )
        tickets = [row[0] for row in result.fetchall()]

        # Should only see tenant_a tickets
        assert tenant_a_enhancement.ticket_id in tickets
        assert tenant_b_enhancement.ticket_id not in tickets

    @pytest.mark.asyncio
    async def test_rls_blocks_cross_tenant_update(
        self, rls_test_session: AsyncSession, db_session: AsyncSession,
        tenant_a_config, tenant_b_config,
        tenant_a_enhancement, tenant_b_enhancement
    ):
        """Test UPDATE cannot modify rows from different tenant."""
        # Set context to tenant_a
        await set_db_tenant_context(rls_test_session, tenant_a_config.tenant_id)

        # Attempt to update tenant_b's row
        result = await rls_test_session.execute(
            text(
                "UPDATE enhancement_history SET status = 'modified' "
                "WHERE ticket_id = :ticket_id"
            ),
            {"ticket_id": tenant_b_enhancement.ticket_id}
        )

        # Should update 0 rows (RLS filtered out tenant_b row)
        assert result.rowcount == 0

        # Verify tenant_b row unchanged using privileged session
        await clear_tenant_context(db_session)
        await set_db_tenant_context(db_session, tenant_b_config.tenant_id)
        result = await db_session.execute(
            text(
                "SELECT status FROM enhancement_history "
                "WHERE ticket_id = :ticket_id"
            ),
            {"ticket_id": tenant_b_enhancement.ticket_id}
        )
        status = result.scalar()
        assert status != "modified"

    @pytest.mark.asyncio
    async def test_rls_blocks_cross_tenant_delete(
        self, rls_test_session: AsyncSession, db_session: AsyncSession,
        tenant_a_config, tenant_b_config,
        tenant_a_enhancement, tenant_b_enhancement
    ):
        """Test DELETE cannot remove rows from different tenant."""
        # Set context to tenant_a
        await set_db_tenant_context(rls_test_session, tenant_a_config.tenant_id)

        # Attempt to delete tenant_b's row
        result = await rls_test_session.execute(
            text(
                "DELETE FROM enhancement_history "
                "WHERE ticket_id = :ticket_id"
            ),
            {"ticket_id": tenant_b_enhancement.ticket_id}
        )

        # Should delete 0 rows
        assert result.rowcount == 0

        # Verify tenant_b row still exists using privileged session
        await clear_tenant_context(db_session)
        await set_db_tenant_context(db_session, tenant_b_config.tenant_id)
        result = await db_session.execute(
            text(
                "SELECT COUNT(*) FROM enhancement_history "
                "WHERE ticket_id = :ticket_id"
            ),
            {"ticket_id": tenant_b_enhancement.ticket_id}
        )
        count = result.scalar()
        assert count == 1


class TestRLSMissingContext:
    """Test behavior when tenant context is not set."""

    @pytest.mark.asyncio
    async def test_missing_context_returns_empty_results(
        self, rls_test_session: AsyncSession, tenant_a_enhancement
    ):
        """Test queries return 0 rows when tenant context not set."""
        # Do NOT set tenant context
        # Query should return no rows (safe default)
        result = await rls_test_session.execute(
            text("SELECT COUNT(*) FROM enhancement_history")
        )
        count = result.scalar()

        # Should return 0 rows when no context set
        assert count == 0


class TestRLSAllTables:
    """Test RLS is enabled on all tenant-scoped tables."""

    @pytest.mark.asyncio
    async def test_rls_enabled_on_tenant_configs(self, db_session: AsyncSession):
        """Verify RLS is enabled on tenant_configs table."""
        result = await db_session.execute(
            text(
                "SELECT relrowsecurity FROM pg_class "
                "WHERE relname = 'tenant_configs'"
            )
        )
        rls_enabled = result.scalar()
        assert rls_enabled is True

    @pytest.mark.asyncio
    async def test_rls_enabled_on_enhancement_history(self, db_session: AsyncSession):
        """Verify RLS is enabled on enhancement_history table."""
        result = await db_session.execute(
            text(
                "SELECT relrowsecurity FROM pg_class "
                "WHERE relname = 'enhancement_history'"
            )
        )
        rls_enabled = result.scalar()
        assert rls_enabled is True

    @pytest.mark.asyncio
    async def test_rls_enabled_on_ticket_history(self, db_session: AsyncSession):
        """Verify RLS is enabled on ticket_history table."""
        result = await db_session.execute(
            text(
                "SELECT relrowsecurity FROM pg_class "
                "WHERE relname = 'ticket_history'"
            )
        )
        rls_enabled = result.scalar()
        assert rls_enabled is True

    @pytest.mark.asyncio
    async def test_rls_enabled_on_system_inventory(self, db_session: AsyncSession):
        """Verify RLS is enabled on system_inventory table."""
        result = await db_session.execute(
            text(
                "SELECT relrowsecurity FROM pg_class "
                "WHERE relname = 'system_inventory'"
            )
        )
        rls_enabled = result.scalar()
        assert rls_enabled is True


class TestRLSPolicyStructure:
    """Test RLS policy expressions match specification."""

    @pytest.mark.asyncio
    async def test_enhancement_history_policy_exists(self, db_session: AsyncSession):
        """Verify enhancement_history has correct RLS policy."""
        result = await db_session.execute(
            text(
                "SELECT policyname, cmd, qual::text FROM pg_policies "
                "WHERE tablename = 'enhancement_history'"
            )
        )
        policies = result.fetchall()

        assert len(policies) >= 1
        policy = policies[0]
        assert "tenant_isolation" in policy[0]
        assert policy[1] == "ALL"  # FOR ALL (PostgreSQL returns "ALL", not "*")
        assert "current_setting" in policy[2]
        assert "app.current_tenant_id" in policy[2]
