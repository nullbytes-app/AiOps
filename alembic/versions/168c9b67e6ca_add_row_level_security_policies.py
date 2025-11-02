"""add_row_level_security_policies

Revision ID: 168c9b67e6ca
Revises: 8f9c7d8a3e2b
Create Date: 2025-11-02 21:52:14.429210

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '168c9b67e6ca'
down_revision: Union[str, Sequence[str], None] = '15577cf2a847'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Implement Row-Level Security (RLS) for multi-tenant data isolation.

    This migration:
    0. Creates missing tables (ticket_history, system_inventory)
    1. Creates set_tenant_context() helper function for session variable management
    2. Enables RLS on all tenant-scoped tables
    3. Creates tenant isolation policies for each table
    4. Documents admin role requirements for bypassing RLS

    Story: 3.1 - Implement Row-Level Security in PostgreSQL
    AC: 1, 2, 4
    """

    # Step 0: Create missing tables that weren't created in previous migrations
    # ticket_history table
    op.execute("""
        CREATE TABLE IF NOT EXISTS ticket_history (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(100) NOT NULL,
            ticket_id VARCHAR(100) NOT NULL,
            subject VARCHAR(255),
            description TEXT,
            resolution TEXT,
            resolved_date TIMESTAMP WITH TIME ZONE,
            priority VARCHAR(20),
            tags TEXT[],
            source VARCHAR(50) DEFAULT 'bulk_import' NOT NULL,
            ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            UNIQUE(tenant_id, ticket_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_ticket_history_tenant_id ON ticket_history(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ticket_history_ticket_id ON ticket_history(ticket_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ticket_history_resolved_date ON ticket_history(resolved_date)")

    # system_inventory table
    op.execute("""
        CREATE TABLE IF NOT EXISTS system_inventory (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(100) NOT NULL,
            ip_address VARCHAR(45) NOT NULL,
            hostname VARCHAR(255),
            role VARCHAR(100),
            client VARCHAR(200),
            location VARCHAR(200),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            UNIQUE(tenant_id, ip_address)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_system_inventory_tenant_id ON system_inventory(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_system_inventory_ip_address ON system_inventory(ip_address)")

    # Step 1: Create helper function for setting tenant context
    # This function validates tenant_id and sets the session variable securely
    # SECURITY DEFINER ensures it runs with creator's privileges to prevent escalation
    op.execute("""
        CREATE OR REPLACE FUNCTION set_tenant_context(p_tenant_id VARCHAR)
        RETURNS VOID AS $$
        BEGIN
            -- Validate tenant exists in tenant_configs before setting context
            IF NOT EXISTS (
                SELECT 1 FROM tenant_configs
                WHERE tenant_id = p_tenant_id
            ) THEN
                RAISE EXCEPTION 'Invalid tenant_id: %', p_tenant_id;
            END IF;

            -- Set session variable (false = session-scoped, not transaction-scoped)
            PERFORM set_config('app.current_tenant_id', p_tenant_id, false);
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;

        COMMENT ON FUNCTION set_tenant_context(VARCHAR) IS
        'Sets PostgreSQL session variable for RLS tenant context. '
        'Validates tenant_id exists before setting. '
        'Must be called before any tenant-scoped database operations.';
    """)

    # Step 2: Enable Row Level Security on all tenant-scoped tables
    # When RLS is enabled, a default-deny policy applies (no rows visible)
    # until explicit policies are created
    op.execute("ALTER TABLE tenant_configs ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE enhancement_history ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE ticket_history ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE system_inventory ENABLE ROW LEVEL SECURITY;")

    # Step 3: Create RLS policies for tenant isolation
    # FOR ALL = applies to SELECT, INSERT, UPDATE, DELETE
    # USING clause = filter condition for visible/modifiable rows
    # Pattern: Only show rows where tenant_id matches current session's tenant_id

    # Policy for tenant_configs table
    op.execute("""
        CREATE POLICY tenant_configs_tenant_isolation_policy
        ON tenant_configs
        FOR ALL
        USING (tenant_id = COALESCE(current_setting('app.current_tenant_id', true), ''));

        COMMENT ON POLICY tenant_configs_tenant_isolation_policy ON tenant_configs IS
        'Isolates tenant configuration data by tenant_id using session variable. Returns no rows if context not set.';
    """)

    # Policy for enhancement_history table
    op.execute("""
        CREATE POLICY enhancement_history_tenant_isolation_policy
        ON enhancement_history
        FOR ALL
        USING (tenant_id = COALESCE(current_setting('app.current_tenant_id', true), ''));

        COMMENT ON POLICY enhancement_history_tenant_isolation_policy ON enhancement_history IS
        'Isolates enhancement tracking data by tenant_id using session variable. Returns no rows if context not set.';
    """)

    # Policy for ticket_history table
    op.execute("""
        CREATE POLICY ticket_history_tenant_isolation_policy
        ON ticket_history
        FOR ALL
        USING (tenant_id = COALESCE(current_setting('app.current_tenant_id', true), ''));

        COMMENT ON POLICY ticket_history_tenant_isolation_policy ON ticket_history IS
        'Isolates historical ticket data by tenant_id using session variable. Returns no rows if context not set.';
    """)

    # Policy for system_inventory table
    op.execute("""
        CREATE POLICY system_inventory_tenant_isolation_policy
        ON system_inventory
        FOR ALL
        USING (tenant_id = COALESCE(current_setting('app.current_tenant_id', true), ''));

        COMMENT ON POLICY system_inventory_tenant_isolation_policy ON system_inventory IS
        'Isolates system inventory data by tenant_id using session variable. Returns no rows if context not set.';
    """)

    # Note: Database admin role with BYPASSRLS should be created manually
    # via environment-specific scripts, not in migrations
    # Example: CREATE ROLE db_admin WITH BYPASSRLS LOGIN PASSWORD '<secure>';
    # See docs/security.md for admin role configuration


def downgrade() -> None:
    """
    Rollback Row-Level Security implementation.

    Removes all RLS policies, disables RLS on tables, and drops helper function.
    This restores the database to pre-RLS state.
    """

    # Step 1: Drop all RLS policies (must be done before disabling RLS)
    op.execute("DROP POLICY IF EXISTS tenant_configs_tenant_isolation_policy ON tenant_configs;")
    op.execute("DROP POLICY IF EXISTS enhancement_history_tenant_isolation_policy ON enhancement_history;")
    op.execute("DROP POLICY IF EXISTS ticket_history_tenant_isolation_policy ON ticket_history;")
    op.execute("DROP POLICY IF EXISTS system_inventory_tenant_isolation_policy ON system_inventory;")

    # Step 2: Disable Row Level Security on all tables
    op.execute("ALTER TABLE tenant_configs DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE enhancement_history DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE ticket_history DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE system_inventory DISABLE ROW LEVEL SECURITY;")

    # Step 3: Drop helper function
    op.execute("DROP FUNCTION IF EXISTS set_tenant_context(VARCHAR);")

    # Step 4: Drop tables created in this migration
    op.execute("DROP TABLE IF EXISTS ticket_history CASCADE;")
    op.execute("DROP TABLE IF EXISTS system_inventory CASCADE;")

    # Note: Admin role (if created) should be removed manually
    # Example: DROP ROLE IF EXISTS db_admin;
