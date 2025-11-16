"""Fix tenant_id schema mismatch - convert UUID to VARCHAR

Revision ID: 014_fix_tenant_id_schema_mismatch
Revises: 013_add_task_id_to_agent_test_executions
Create Date: 2025-11-15

Root Cause:
-----------
Migrations 009, 011, and 006 created tables (mcp_servers, mcp_server_metrics, agent_memory)
with UUID tenant_id columns that FK to tenant_configs.id (UUID).

However, the rest of the codebase (12 other tables) uses VARCHAR(100) tenant_id that FKs
to tenant_configs.tenant_id (VARCHAR).

This inconsistency causes errors when the application queries MCP servers with tenant_id='Test1'
because PostgreSQL cannot cast VARCHAR to UUID.

Solution:
---------
1. Drop FK constraints on 3 tables (mcp_servers, mcp_server_metrics, agent_memory)
2. Alter tenant_id columns from UUID to VARCHAR(100)
3. Migrate existing data by mapping UUID tenant_configs.id → VARCHAR tenant_configs.tenant_id
4. Recreate FK constraints pointing to tenant_configs.tenant_id (VARCHAR) instead of .id (UUID)

Impact:
-------
- mcp_servers: 1 row needs data migration (58568cee... → 'Test1')
- mcp_server_metrics: 0 rows (empty table)
- agent_memory: 0 rows (empty table)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade():
    """
    Fix tenant_id schema mismatch by converting UUID columns to VARCHAR(100)
    and updating FK constraints to reference tenant_configs.tenant_id.
    """

    # Step 1: Drop existing FK constraints (all point to tenant_configs.id UUID)
    op.drop_constraint('fk_mcp_servers_tenant_id', 'mcp_servers', type_='foreignkey')
    op.drop_constraint('mcp_server_metrics_tenant_id_fkey', 'mcp_server_metrics', type_='foreignkey')
    op.drop_constraint('agent_memory_tenant_id_fkey', 'agent_memory', type_='foreignkey')

    # Step 2: Add temporary VARCHAR columns to hold the mapped tenant_id values
    op.add_column('mcp_servers', sa.Column('tenant_id_temp', sa.String(100), nullable=True))
    op.add_column('mcp_server_metrics', sa.Column('tenant_id_temp', sa.String(100), nullable=True))
    op.add_column('agent_memory', sa.Column('tenant_id_temp', sa.String(100), nullable=True))

    # Step 3: Populate temp columns with mapped VARCHAR tenant_ids
    # For mcp_servers: Map UUID tenant_configs.id → VARCHAR tenant_configs.tenant_id
    op.execute("""
        UPDATE mcp_servers ms
        SET tenant_id_temp = tc.tenant_id
        FROM tenant_configs tc
        WHERE ms.tenant_id = tc.id
    """)

    # mcp_server_metrics and agent_memory are empty, but include for completeness
    op.execute("""
        UPDATE mcp_server_metrics msm
        SET tenant_id_temp = tc.tenant_id
        FROM tenant_configs tc
        WHERE msm.tenant_id = tc.id
    """)

    op.execute("""
        UPDATE agent_memory am
        SET tenant_id_temp = tc.tenant_id
        FROM tenant_configs tc
        WHERE am.tenant_id = tc.id
    """)

    # Step 4: Drop old UUID tenant_id columns
    op.drop_column('mcp_servers', 'tenant_id')
    op.drop_column('mcp_server_metrics', 'tenant_id')
    op.drop_column('agent_memory', 'tenant_id')

    # Step 5: Rename temp columns to tenant_id
    op.alter_column('mcp_servers', 'tenant_id_temp', new_column_name='tenant_id')
    op.alter_column('mcp_server_metrics', 'tenant_id_temp', new_column_name='tenant_id')
    op.alter_column('agent_memory', 'tenant_id_temp', new_column_name='tenant_id')

    # Step 6: Make tenant_id columns NOT NULL
    op.alter_column('mcp_servers', 'tenant_id', nullable=False)
    op.alter_column('mcp_server_metrics', 'tenant_id', nullable=False)
    op.alter_column('agent_memory', 'tenant_id', nullable=False)

    # Step 7: Recreate FK constraints pointing to tenant_configs.tenant_id (VARCHAR)
    op.create_foreign_key(
        'fk_mcp_servers_tenant_id',
        'mcp_servers',
        'tenant_configs',
        ['tenant_id'],
        ['tenant_id'],
        ondelete='CASCADE'
    )

    op.create_foreign_key(
        'mcp_server_metrics_tenant_id_fkey',
        'mcp_server_metrics',
        'tenant_configs',
        ['tenant_id'],
        ['tenant_id'],
        ondelete='CASCADE'
    )

    op.create_foreign_key(
        'agent_memory_tenant_id_fkey',
        'agent_memory',
        'tenant_configs',
        ['tenant_id'],
        ['tenant_id'],
        ondelete='CASCADE'
    )


def downgrade():
    """
    Rollback: Convert VARCHAR(100) back to UUID and restore original FK constraints.

    WARNING: This downgrade will FAIL if any VARCHAR tenant_ids cannot be cast to UUID.
    Only use this if you know all tenant_id values are valid UUIDs.
    """

    # Step 1: Drop VARCHAR FK constraints
    op.drop_constraint('fk_mcp_servers_tenant_id', 'mcp_servers', type_='foreignkey')
    op.drop_constraint('mcp_server_metrics_tenant_id_fkey', 'mcp_server_metrics', type_='foreignkey')
    op.drop_constraint('agent_memory_tenant_id_fkey', 'agent_memory', type_='foreignkey')

    # Step 2: Migrate data back: VARCHAR tenant_configs.tenant_id → UUID tenant_configs.id
    op.execute("""
        UPDATE mcp_servers ms
        SET tenant_id = tc.id::text
        FROM tenant_configs tc
        WHERE ms.tenant_id = tc.tenant_id
    """)

    # Step 3: Alter column types back to UUID
    op.alter_column(
        'mcp_servers',
        'tenant_id',
        type_=postgresql.UUID(as_uuid=True),
        existing_type=sa.String(100),
        existing_nullable=False,
        postgresql_using='tenant_id::uuid'
    )

    op.alter_column(
        'mcp_server_metrics',
        'tenant_id',
        type_=postgresql.UUID(as_uuid=True),
        existing_type=sa.String(100),
        existing_nullable=False,
        postgresql_using='tenant_id::uuid'
    )

    op.alter_column(
        'agent_memory',
        'tenant_id',
        type_=postgresql.UUID(as_uuid=True),
        existing_type=sa.String(100),
        existing_nullable=False,
        postgresql_using='tenant_id::uuid'
    )

    # Step 4: Recreate original FK constraints pointing to tenant_configs.id (UUID)
    op.create_foreign_key(
        'fk_mcp_servers_tenant_id',
        'mcp_servers',
        'tenant_configs',
        ['tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )

    op.create_foreign_key(
        'mcp_server_metrics_tenant_id_fkey',
        'mcp_server_metrics',
        'tenant_configs',
        ['tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )

    op.create_foreign_key(
        'agent_memory_tenant_id_fkey',
        'agent_memory',
        'tenant_configs',
        ['tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )
