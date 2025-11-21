"""merge_heads

Revision ID: f031ea488d6d
Revises: 016, cee49e850502
Create Date: 2025-11-19 15:49:28.952419

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f031ea488d6d'
down_revision: Union[str, Sequence[str], None] = ('016', 'cee49e850502')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
