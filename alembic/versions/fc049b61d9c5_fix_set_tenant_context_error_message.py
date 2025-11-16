"""fix_set_tenant_context_error_message

Revision ID: fc049b61d9c5
Revises: 012
Create Date: 2025-11-10 21:30:05.356393

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fc049b61d9c5'
down_revision: Union[str, Sequence[str], None] = '012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Fix set_tenant_context() function error message formatting.

    The original function used '%' for string formatting in RAISE EXCEPTION,
    which caused "Replacement index 0 out of range" errors when asyncpg
    tried to parse the error message. This migration replaces it with
    PostgreSQL's proper string concatenation using ||.
    """
    op.execute("""
        CREATE OR REPLACE FUNCTION set_tenant_context(p_tenant_id VARCHAR)
        RETURNS VOID AS $$
        BEGIN
            -- Validate tenant exists in tenant_configs before setting context
            IF NOT EXISTS (
                SELECT 1 FROM tenant_configs
                WHERE tenant_id = p_tenant_id
            ) THEN
                -- Use simple string concatenation to avoid ANY % formatting
                -- which asyncpg might try to interpret as Python format strings
                RAISE EXCEPTION 'Invalid tenant_id value'
                    USING DETAIL = 'Provided: ' || p_tenant_id,
                          HINT = 'Tenant must exist in tenant_configs table';
            END IF;

            -- Set session variable (false = session-scoped, not transaction-scoped)
            PERFORM set_config('app.current_tenant_id', p_tenant_id, false);
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER
    """)


def downgrade() -> None:
    """Revert to original function with % formatting."""
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
        $$ LANGUAGE plpgsql SECURITY DEFINER
    """)
