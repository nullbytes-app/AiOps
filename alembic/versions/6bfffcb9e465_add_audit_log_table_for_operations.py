"""add_audit_log_table_for_operations

Revision ID: 6bfffcb9e465
Revises: e74b3ef7ccf5
Create Date: 2025-11-04 18:33:31.572674

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6bfffcb9e465'
down_revision: Union[str, Sequence[str], None] = 'e74b3ef7ccf5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create audit_log table for system operations tracking.

    This table stores all system operations performed through the admin UI
    for compliance, troubleshooting, and security auditing.
    """
    # Create audit_log table
    op.create_table(
        'audit_log',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('user', sa.String(length=255), nullable=False),
        sa.Column('operation', sa.String(length=100), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for efficient querying
    # Index on timestamp DESC for "recent operations" queries
    op.create_index(
        'ix_audit_log_timestamp',
        'audit_log',
        ['timestamp'],
        unique=False,
        postgresql_ops={'timestamp': 'DESC'}
    )

    # Index on operation for filtering by operation type
    op.create_index(
        'ix_audit_log_operation',
        'audit_log',
        ['operation'],
        unique=False
    )


def downgrade() -> None:
    """
    Drop audit_log table and indexes.
    """
    # Drop indexes first
    op.drop_index('ix_audit_log_operation', table_name='audit_log')
    op.drop_index('ix_audit_log_timestamp', table_name='audit_log')

    # Drop table
    op.drop_table('audit_log')
