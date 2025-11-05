"""merge_multiple_heads

Revision ID: 93a65df31932
Revises: 168c9b67e6ca, 8f9c7d8a3e2b, 9a2d3e4f5b6c
Create Date: 2025-11-04 15:39:54.134486

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '93a65df31932'
down_revision: Union[str, Sequence[str], None] = ('168c9b67e6ca', '8f9c7d8a3e2b', '9a2d3e4f5b6c')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
