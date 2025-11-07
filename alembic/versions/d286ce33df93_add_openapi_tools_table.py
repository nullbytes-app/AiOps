"""add_openapi_tools_table

Revision ID: d286ce33df93
Revises: ba192a59ecc7
Create Date: 2025-11-06 09:36:08.952232

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd286ce33df93'
down_revision: Union[str, Sequence[str], None] = 'ba192a59ecc7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add openapi_tools table."""
    # Create openapi_tools table
    op.create_table(
        'openapi_tools',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tool_name', sa.String(length=255), nullable=False),
        sa.Column('openapi_spec', sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column('spec_version', sa.String(length=10), nullable=False),
        sa.Column('base_url', sa.Text(), nullable=False),
        sa.Column('auth_config_encrypted', sa.LargeBinary(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant_configs.tenant_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'tool_name', name='uq_tenant_tool_name'),
        sa.CheckConstraint("spec_version IN ('2.0', '3.0', '3.1')", name='ck_spec_version'),
        sa.CheckConstraint("status IN ('active', 'inactive')", name='ck_status'),
    )

    # Create indexes
    op.create_index('idx_openapi_tools_status', 'openapi_tools', ['status'])
    op.create_index('idx_openapi_tools_tenant', 'openapi_tools', ['tenant_id'])


def downgrade() -> None:
    """Downgrade schema - drop openapi_tools table."""
    op.drop_index('idx_openapi_tools_tenant', table_name='openapi_tools')
    op.drop_index('idx_openapi_tools_status', table_name='openapi_tools')
    op.drop_table('openapi_tools')
