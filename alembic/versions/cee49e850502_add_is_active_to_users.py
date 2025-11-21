"""add_is_active_to_users

Revision ID: cee49e850502
Revises: 6e13ea30c0a3
Create Date: 2025-11-18 10:54:26.665116

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cee49e850502'
down_revision: Union[str, Sequence[str], None] = '6e13ea30c0a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_active column to users table."""
    # Add is_active column with default True
    op.add_column(
        'users',
        sa.Column(
            'is_active',
            sa.Boolean(),
            nullable=False,
            server_default='true',
            comment='Account active status (False for soft-deleted accounts)'
        )
    )


def downgrade() -> None:
    """Remove is_active column from users table."""
    op.drop_column('users', 'is_active')
