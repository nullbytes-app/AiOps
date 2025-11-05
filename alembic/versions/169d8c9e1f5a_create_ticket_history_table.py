"""Create ticket_history table

Revision ID: 169d8c9e1f5a
Revises: 15577cf2a847
Create Date: 2025-11-05 16:11:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '169d8c9e1f5a'
down_revision: Union[str, Sequence[str], None] = '15577cf2a847'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Create ticket_history table (base columns only)."""
    # This creates the base ticket_history table.
    # Additional columns (source, ingested_at) are added by migration 8f9c7d8a3e2b
    op.create_table(
        'ticket_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('ticket_id', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('resolution', sa.Text(), nullable=False),
        sa.Column('resolved_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ticket_history_tenant_id', 'ticket_history', ['tenant_id'], unique=False)
    op.create_index('ix_ticket_history_resolved_date', 'ticket_history', ['resolved_date'], unique=False)


def downgrade() -> None:
    """Downgrade schema - Drop ticket_history table."""
    op.drop_index('ix_ticket_history_resolved_date', table_name='ticket_history')
    op.drop_index('ix_ticket_history_tenant_id', table_name='ticket_history')
    op.drop_table('ticket_history')
