"""add_agent_prompt_versions_and_templates_tables

Revision ID: ba192a59ecc7
Revises: facc8d95bcbd
Create Date: 2025-11-05 21:36:27.066518

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ba192a59ecc7'
down_revision: Union[str, Sequence[str], None] = 'facc8d95bcbd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create agent_prompt_versions table
    op.create_table(
        'agent_prompt_versions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('agent_id', sa.UUID(), nullable=False),
        sa.Column('prompt_text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('is_current', sa.Boolean(), server_default='false', nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_agent_prompt_versions_agent_id_created_at', 'agent_prompt_versions', ['agent_id', 'created_at'], postgresql_ops={'created_at': 'DESC'})
    op.create_index('idx_agent_prompt_versions_agent_id_is_current', 'agent_prompt_versions', ['agent_id', 'is_current'])

    # Create agent_prompt_templates table
    op.create_table(
        'agent_prompt_templates',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.String(100), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('template_text', sa.Text(), nullable=False),
        sa.Column('is_builtin', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_prompt_templates_builtin_active', 'agent_prompt_templates', ['is_builtin', 'is_active'])
    op.create_index('idx_prompt_templates_tenant_id_active', 'agent_prompt_templates', ['tenant_id', 'is_active'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_prompt_templates_tenant_id_active', table_name='agent_prompt_templates')
    op.drop_index('idx_prompt_templates_builtin_active', table_name='agent_prompt_templates')
    op.drop_table('agent_prompt_templates')
    op.drop_index('idx_agent_prompt_versions_agent_id_is_current', table_name='agent_prompt_versions')
    op.drop_index('idx_agent_prompt_versions_agent_id_created_at', table_name='agent_prompt_versions')
    op.drop_table('agent_prompt_versions')
