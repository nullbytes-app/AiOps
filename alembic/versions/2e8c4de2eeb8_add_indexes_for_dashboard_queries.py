"""add_indexes_for_dashboard_queries

Revision ID: 2e8c4de2eeb8
Revises: 93a65df31932
Create Date: 2025-11-04 15:39:58.942516

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e8c4de2eeb8'
down_revision: Union[str, Sequence[str], None] = '93a65df31932'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add indexes for dashboard query performance optimization.

    Story 6.2 - Task 6.3: Add indexes on enhancement_history table for:
    1. (status, created_at) - Optimizes success rate and recent failures queries
    2. (status, completed_at) - Optimizes P95 latency calculations

    These indexes significantly improve dashboard load time (target: <2s).
    """
    # Index for success rate and recent failures queries
    # Used by: get_success_rate_24h(), get_recent_failures()
    op.create_index(
        'idx_enhancement_history_status_created',
        'enhancement_history',
        ['status', 'created_at'],
        unique=False,
    )

    # Index for P95 latency calculations
    # Used by: get_p95_latency()
    op.create_index(
        'idx_enhancement_history_status_completed',
        'enhancement_history',
        ['status', 'completed_at'],
        unique=False,
    )


def downgrade() -> None:
    """Remove dashboard performance indexes."""
    op.drop_index('idx_enhancement_history_status_completed', table_name='enhancement_history')
    op.drop_index('idx_enhancement_history_status_created', table_name='enhancement_history')
