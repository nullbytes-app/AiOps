"""Fix agent_test_executions tenant_id foreign key

Revision ID: 008_fix_tenant_fk
Revises: 007_remove_provider_tables
Create Date: 2025-11-09

Story: Bug Fix - Execution Retrieval
Description: Fix agent_test_executions.tenant_id to reference tenant_configs.tenant_id
instead of tenant_configs.id (UUID vs VARCHAR mismatch)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Fix tenant_id column type and foreign key to reference correct column."""
    # Drop existing foreign key constraint
    op.drop_constraint(
        'agent_test_executions_tenant_id_fkey',
        'agent_test_executions',
        type_='foreignkey'
    )

    # Change tenant_id column type from UUID to VARCHAR to match tenant_configs.tenant_id
    # This is safe because tenant IDs are string identifiers (e.g., 'default', 'mvp-customer-1')
    op.execute(
        "ALTER TABLE agent_test_executions ALTER COLUMN tenant_id TYPE VARCHAR(100) USING tenant_id::text"
    )

    # Recreate foreign key with correct reference to tenant_configs.tenant_id (VARCHAR)
    op.create_foreign_key(
        'agent_test_executions_tenant_id_fkey',
        'agent_test_executions',
        'tenant_configs',
        ['tenant_id'],
        ['tenant_id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Revert to original column type and foreign key."""
    # Drop corrected foreign key
    op.drop_constraint(
        'agent_test_executions_tenant_id_fkey',
        'agent_test_executions',
        type_='foreignkey'
    )

    # Revert column type from VARCHAR back to UUID
    op.execute(
        "ALTER TABLE agent_test_executions ALTER COLUMN tenant_id TYPE UUID USING tenant_id::uuid"
    )

    # Recreate original (incorrect) reference to tenant_configs.id (UUID)
    op.create_foreign_key(
        'agent_test_executions_tenant_id_fkey',
        'agent_test_executions',
        'tenant_configs',
        ['tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )
