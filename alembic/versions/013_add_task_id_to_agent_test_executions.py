"""add_task_id_to_agent_test_executions

Revision ID: 013
Revises: 8b2f1d3f9a10
Create Date: 2025-11-14 07:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '013'
down_revision: Union[str, None] = '8b2f1d3f9a10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add task_id column to agent_test_executions table.

    This column stores the Celery task ID (UUID format) to enable correlation
    between the webhook response (task ID) and the execution record (execution ID).
    Useful for troubleshooting and tracking async task processing.
    """
    op.add_column(
        'agent_test_executions',
        sa.Column('task_id', sa.String(length=100), nullable=True, comment='Celery task ID for correlation with async queue')
    )

    # Add index for faster lookups by task_id
    op.create_index(
        'idx_agent_test_executions_task_id',
        'agent_test_executions',
        ['task_id']
    )


def downgrade() -> None:
    """Remove task_id column and index."""
    op.drop_index('idx_agent_test_executions_task_id', table_name='agent_test_executions')
    op.drop_column('agent_test_executions', 'task_id')
