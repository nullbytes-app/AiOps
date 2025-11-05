"""Enable required PostgreSQL extensions

Revision ID: 000000000001
Revises:
Create Date: 2025-11-05 16:11:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '000000000001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable required PostgreSQL extensions."""
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')


def downgrade() -> None:
    """Disable extensions."""
    op.execute('DROP EXTENSION IF EXISTS "pgcrypto" CASCADE;')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp" CASCADE;')
