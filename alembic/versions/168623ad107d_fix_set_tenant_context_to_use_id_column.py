"""fix_set_tenant_context_to_use_id_column

Revision ID: 168623ad107d
Revises: fc049b61d9c5
Create Date: 2025-11-10 21:55:53.824746

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '168623ad107d'
down_revision: Union[str, Sequence[str], None] = 'fc049b61d9c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Fix set_tenant_context() to check against tenant_configs.id (UUID primary key)
    instead of tenant_configs.tenant_id (VARCHAR identifier).

    The application uses tenant_configs.id as the foreign key reference, so the
    context validation must also check against id, not tenant_id.
    """
    op.execute("""
        CREATE OR REPLACE FUNCTION set_tenant_context(p_tenant_id VARCHAR)
        RETURNS VOID AS $$
        BEGIN
            -- Validate tenant exists by checking id column (UUID primary key)
            -- NOT tenant_id column (VARCHAR identifier)
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


def downgrade() -> None:
    """Revert to checking tenant_id column instead of id column."""
    op.execute("""
        CREATE OR REPLACE FUNCTION set_tenant_context(p_tenant_id VARCHAR)
        RETURNS VOID AS $$
        BEGIN
            -- Validate tenant exists in tenant_configs before setting context
            IF NOT EXISTS (
                SELECT 1 FROM tenant_configs
                WHERE tenant_id = p_tenant_id
            ) THEN
                RAISE EXCEPTION 'Invalid tenant_id value'
                    USING DETAIL = 'Provided: ' || p_tenant_id,
                          HINT = 'Tenant must exist in tenant_configs table';
            END IF;

            -- Set session variable (false = session-scoped, not transaction-scoped)
            PERFORM set_config('app.current_tenant_id', p_tenant_id, false);
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER
    """)
