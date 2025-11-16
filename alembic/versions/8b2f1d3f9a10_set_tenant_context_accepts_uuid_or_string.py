"""set_tenant_context accepts UUID or tenant_id string

Revision ID: 8b2f1d3f9a10
Revises: 7aeba6a5a240
Create Date: 2025-11-11 19:05:00

Purpose:
    Update set_tenant_context() to accept either a tenant UUID (tenant_configs.id)
    or the tenant_id string (tenant_configs.tenant_id). This resolves failures when
    clients send X-Tenant-ID as the UUID while the DB function only validated the
    string identifier.

    Behavior:
    - If input parses as UUID, it looks up tenant_configs.tenant_id by id and requires is_active=true
    - Otherwise, it validates the provided string exists in tenant_configs.tenant_id and is_active=true
    - In both cases, it sets app.current_tenant_id to the resolved tenant_id string
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b2f1d3f9a10'
down_revision: Union[str, Sequence[str], None] = '7aeba6a5a240'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_tenant_context(p_tenant_id VARCHAR)
        RETURNS VOID AS $$
        DECLARE
            v_uuid UUID;
            v_tenant_id VARCHAR;
        BEGIN
            -- Try to interpret the input as a UUID (tenant_configs.id)
            BEGIN
                v_uuid := p_tenant_id::uuid;
                -- If cast succeeds, fetch the canonical tenant_id string
                SELECT tenant_id INTO v_tenant_id
                FROM tenant_configs
                WHERE id = v_uuid AND is_active = true;
            EXCEPTION WHEN others THEN
                -- Not a valid UUID, treat input as the tenant_id string directly
                v_tenant_id := NULL;  -- ensure it's null unless validated below
            END;

            IF v_tenant_id IS NULL THEN
                -- Validate the provided string exists and is active
                IF NOT EXISTS (
                    SELECT 1 FROM tenant_configs
                    WHERE tenant_id = p_tenant_id AND is_active = true
                ) THEN
                    RAISE EXCEPTION 'Invalid tenant_id value'
                        USING DETAIL = 'Provided: ' || p_tenant_id,
                              HINT = 'Tenant must exist in tenant_configs table and be active';
                END IF;

                -- Use the provided string as the tenant context
                v_tenant_id := p_tenant_id;
            END IF;

            -- Set session variable (false = session-scoped, not transaction-scoped)
            PERFORM set_config('app.current_tenant_id', v_tenant_id, false);
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER
        """
    )


def downgrade() -> None:
    # Revert to the previous version that only validates tenant_id string
    op.execute(
        """
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
        """
    )

