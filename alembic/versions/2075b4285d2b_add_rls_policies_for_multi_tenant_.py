"""Add RLS policies for multi-tenant isolation

Revision ID: 2075b4285d2b
Revises: 63a573401118
Create Date: 2025-11-01 14:11:18.078874

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2075b4285d2b'
down_revision: Union[str, Sequence[str], None] = '63a573401118'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Enable RLS and create policies for multi-tenant isolation."""
    # Create database roles if they don't exist
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user') THEN
                CREATE ROLE app_user;
            END IF;
        END
        $$;
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'admin') THEN
                CREATE ROLE admin;
            END IF;
        END
        $$;
    """)

    # Enable Row-Level Security on both tables
    op.execute("ALTER TABLE enhancement_history ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE tenant_configs ENABLE ROW LEVEL SECURITY;")

    # Create RLS policy for enhancement_history table
    # This policy ensures users can only see records for their tenant
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON enhancement_history
        USING (tenant_id = current_setting('app.current_tenant_id')::VARCHAR)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::VARCHAR);
    """)

    # Create RLS policy for tenant_configs table
    op.execute("""
        CREATE POLICY tenant_config_isolation_policy ON tenant_configs
        USING (tenant_id = current_setting('app.current_tenant_id')::VARCHAR)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::VARCHAR);
    """)

    # Grant permissions to app_user role for enhancement_history
    op.execute("GRANT SELECT, INSERT, UPDATE ON enhancement_history TO app_user;")
    op.execute("GRANT USAGE ON SCHEMA public TO app_user;")

    # Grant permissions to app_user role for tenant_configs
    op.execute("GRANT SELECT, INSERT, UPDATE ON tenant_configs TO app_user;")

    # Grant all permissions to admin role (bypass RLS)
    op.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO admin;")
    op.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO admin;")

    # Grant usage on all sequences to app_user (needed for UUID defaults)
    op.execute("GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO app_user;")


def downgrade() -> None:
    """Downgrade schema - Disable RLS policies."""
    # Drop policies
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON enhancement_history;")
    op.execute("DROP POLICY IF EXISTS tenant_config_isolation_policy ON tenant_configs;")

    # Disable RLS on tables
    op.execute("ALTER TABLE enhancement_history DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE tenant_configs DISABLE ROW LEVEL SECURITY;")

    # Revoke permissions
    op.execute("REVOKE ALL PRIVILEGES ON enhancement_history FROM app_user;")
    op.execute("REVOKE ALL PRIVILEGES ON tenant_configs FROM app_user;")
    op.execute("REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM admin;")

    # Note: Roles are intentionally not dropped during downgrade
    # to avoid issues if other databases reference them.
    # Manual cleanup of roles may be needed if completely removing RLS.
