"""add_history_query_performance_indexes

Revision ID: e74b3ef7ccf5
Revises: 1e548d509815
Create Date: 2025-11-04 17:40:35.415181

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e74b3ef7ccf5'
down_revision: Union[str, Sequence[str], None] = '1e548d509815'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema.

    Adds composite index on enhancement_history table to optimize
    filter queries by tenant_id, status, and created_at.

    This index supports Story 6.4 AC7 requirement: query returns < 5 seconds for 10K rows.
    """
    # Create composite index for filter performance
    # Optimizes queries filtering by tenant + status + date range
    op.create_index(
        'ix_history_tenant_status_created',
        'enhancement_history',
        ['tenant_id', 'status', sa.text('created_at DESC')],
        unique=False
    )


def downgrade() -> None:
    """
    Downgrade schema.

    Removes the composite index added in upgrade.
    """
    op.drop_index('ix_history_tenant_status_created', table_name='enhancement_history')
