"""add_litellm_virtual_key_columns

Revision ID: fb8ab610bec8
Revises: d286ce33df93
Create Date: 2025-11-06 12:49:27.792735

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb8ab610bec8'
down_revision: Union[str, Sequence[str], None] = 'd286ce33df93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add LiteLLM virtual key columns to tenant_configs table."""
    # Add litellm_virtual_key column (encrypted, nullable)
    op.add_column(
        'tenant_configs',
        sa.Column('litellm_virtual_key', sa.Text(), nullable=True,
                  comment='Encrypted LiteLLM virtual key for per-tenant cost tracking')
    )

    # Add litellm_key_created_at column (timestamp with timezone, nullable)
    op.add_column(
        'tenant_configs',
        sa.Column('litellm_key_created_at', sa.DateTime(timezone=True), nullable=True,
                  comment='Timestamp when LiteLLM virtual key was created')
    )

    # Add litellm_key_last_rotated column (timestamp with timezone, nullable)
    op.add_column(
        'tenant_configs',
        sa.Column('litellm_key_last_rotated', sa.DateTime(timezone=True), nullable=True,
                  comment='Timestamp when LiteLLM virtual key was last rotated')
    )


def downgrade() -> None:
    """Remove LiteLLM virtual key columns from tenant_configs table."""
    # Drop columns in reverse order
    op.drop_column('tenant_configs', 'litellm_key_last_rotated')
    op.drop_column('tenant_configs', 'litellm_key_created_at')
    op.drop_column('tenant_configs', 'litellm_virtual_key')
