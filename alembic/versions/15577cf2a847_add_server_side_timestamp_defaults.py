"""Add server-side timestamp defaults

Revision ID: 15577cf2a847
Revises: 2075b4285d2b
Create Date: 2025-11-01 13:45:57.554675

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15577cf2a847'
down_revision: Union[str, Sequence[str], None] = '2075b4285d2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add server-side timestamp defaults."""
    # Add server defaults to tenant_configs table
    op.alter_column(
        'tenant_configs',
        'created_at',
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        existing_nullable=False
    )

    op.alter_column(
        'tenant_configs',
        'updated_at',
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        existing_nullable=False
    )

    # Add server default to enhancement_history table
    op.alter_column(
        'enhancement_history',
        'created_at',
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        existing_nullable=False
    )


def downgrade() -> None:
    """Downgrade schema - Remove server-side timestamp defaults."""
    # Remove server defaults from tenant_configs table
    op.alter_column(
        'tenant_configs',
        'created_at',
        existing_type=sa.DateTime(timezone=True),
        server_default=None,
        existing_nullable=False
    )

    op.alter_column(
        'tenant_configs',
        'updated_at',
        existing_type=sa.DateTime(timezone=True),
        server_default=None,
        existing_nullable=False
    )

    # Remove server default from enhancement_history table
    op.alter_column(
        'enhancement_history',
        'created_at',
        existing_type=sa.DateTime(timezone=True),
        server_default=None,
        existing_nullable=False
    )
