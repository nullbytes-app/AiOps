"""fix set_tenant_context to check tenant_id column not id

Revision ID: 7aeba6a5a240
Revises: 168623ad107d
Create Date: 2025-11-11 06:53:59.256913

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7aeba6a5a240'
down_revision: Union[str, Sequence[str], None] = '168623ad107d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Fix set_tenant_context() to check tenant_id column (VARCHAR identifier)
    instead of id column (UUID primary key).

    The application uses tenant_configs.tenant_id for tenant identification,
    so the validation must check against tenant_id, not id.
    """
    op.execute("""
        CREATE OR REPLACE FUNCTION set_tenant_context(p_tenant_id VARCHAR)
        RETURNS VOID AS $$
        BEGIN
            -- Validate tenant exists by checking tenant_id column (VARCHAR identifier)
            -- This is the column the application actually uses for tenant identification
            IF NOT EXISTS (
                SELECT 1 FROM tenant_configs
                WHERE tenant_id = p_tenant_id AND is_active = true
            ) THEN
                RAISE EXCEPTION 'Invalid tenant_id value'
                    USING DETAIL = 'Provided: ' || p_tenant_id,
                          HINT = 'Tenant must exist in tenant_configs table and be active';
            END IF;

            -- Set session variable (false = session-scoped, not transaction-scoped)
            PERFORM set_config('app.current_tenant_id', p_tenant_id, false);
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER
    """)


def downgrade() -> None:
    """Revert to checking id column (UUID) instead of tenant_id column."""
    op.execute("""
        CREATE OR REPLACE FUNCTION set_tenant_context(p_tenant_id VARCHAR)
        RETURNS VOID AS $$
        BEGIN
            -- Validate tenant exists by checking id column (UUID primary key)
            IF NOT EXISTS (
                SELECT 1 FROM tenant_configs
                WHERE id::text = p_tenant_id
            ) THEN
                RAISE EXCEPTION 'Invalid tenant_id value'
                    USING DETAIL = 'Provided: ' || p_tenant_id,
                          HINT = 'Tenant must exist in tenant_configs table (checked against id column)';
            END IF;

            -- Set session variable (false = session-scoped, not transaction-scoped)
            PERFORM set_config('app.current_tenant_id', p_tenant_id, false);
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER
    """)
