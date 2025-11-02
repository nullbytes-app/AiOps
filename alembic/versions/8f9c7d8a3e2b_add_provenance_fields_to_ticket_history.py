"""Add source and ingested_at provenance fields to ticket_history

Revision ID: 8f9c7d8a3e2b
Revises: 15577cf2a847
Create Date: 2025-11-02 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f9c7d8a3e2b'
down_revision: Union[str, Sequence[str], None] = '15577cf2a847'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add provenance fields and UNIQUE constraint to ticket_history."""
    # Add source column with default 'bulk_import'
    op.add_column(
        'ticket_history',
        sa.Column(
            'source',
            sa.String(50),
            nullable=False,
            server_default='bulk_import',
            comment="Data provenance - 'bulk_import' or 'webhook_resolved'"
        )
    )

    # Add ingested_at column with server default
    op.add_column(
        'ticket_history',
        sa.Column(
            'ingested_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="Timestamp when record was ingested into system"
        )
    )

    # Create UNIQUE constraint on (tenant_id, ticket_id) for idempotency
    op.create_unique_constraint(
        'uq_ticket_history_tenant_ticket',
        'ticket_history',
        ['tenant_id', 'ticket_id']
    )


def downgrade() -> None:
    """Downgrade schema - Remove provenance fields and UNIQUE constraint from ticket_history."""
    # Drop UNIQUE constraint
    op.drop_constraint(
        'uq_ticket_history_tenant_ticket',
        'ticket_history',
        type_='unique'
    )

    # Remove ingested_at column
    op.drop_column(
        'ticket_history',
        'ingested_at'
    )

    # Remove source column
    op.drop_column(
        'ticket_history',
        'source'
    )
