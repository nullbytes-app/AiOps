"""add_is_active_to_tenant_configs

Revision ID: 1e548d509815
Revises: 2e8c4de2eeb8
Create Date: 2025-11-04 16:38:57.176301

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1e548d509815'
down_revision: Union[str, Sequence[str], None] = '2e8c4de2eeb8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_active boolean column to tenant_configs table for soft delete support."""
    # Add is_active column with default TRUE
    op.add_column(
        'tenant_configs',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='TRUE')
    )

    # Backfill existing records to ensure they are marked as active
    op.execute("UPDATE tenant_configs SET is_active = TRUE WHERE is_active IS NULL")


def downgrade() -> None:
    """Remove is_active column from tenant_configs table."""
    op.drop_column('tenant_configs', 'is_active')
