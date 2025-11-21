"""fix_audit_log_legacy_columns

Revision ID: 6e13ea30c0a3
Revises: 015
Create Date: 2025-11-18 08:41:30.202532

Description: Drop legacy user_email and status columns from audit_log table.
These columns were from the old schema and are no longer used in the current
AuditLog model which uses user_id and entity_type/action instead.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6e13ea30c0a3'
down_revision: Union[str, Sequence[str], None] = '015'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Drop legacy columns from audit_log table.

    Removes:
    - user_email: Replaced by user_id (FK to users table)
    - status: No longer used (action and entity_type provide this info)
    """
    # Drop legacy columns that are not in the current AuditLog model
    op.drop_column('audit_log', 'user_email')
    op.drop_column('audit_log', 'status')


def downgrade() -> None:
    """
    Re-add legacy columns to audit_log table.

    WARNING: Data will be lost as these columns are not populated in current code.
    """
    # Re-add legacy columns
    op.add_column('audit_log', sa.Column('user_email', sa.String(255), nullable=True))
    op.add_column('audit_log', sa.Column('status', sa.String(50), nullable=True))
