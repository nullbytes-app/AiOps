"""add_tool_type_to_tenant_configs

Revision ID: 3ad133f66494
Revises: 6bfffcb9e465
Create Date: 2025-11-05 06:34:40.812915

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3ad133f66494'
down_revision: Union[str, Sequence[str], None] = '6bfffcb9e465'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add tool_type column to tenant_configs table for plugin routing.

    Story 7.3: Migrate ServiceDesk Plus to Plugin Architecture
    Adds tool_type column with default 'servicedesk_plus' for backward compatibility.
    Creates index for fast plugin lookup.
    """
    # Add tool_type column with default value
    op.add_column(
        'tenant_configs',
        sa.Column(
            'tool_type',
            sa.String(50),
            nullable=False,
            server_default='servicedesk_plus'
        )
    )

    # Create index for fast plugin lookup by tool_type
    op.create_index(
        'idx_tenant_configs_tool_type',
        'tenant_configs',
        ['tool_type']
    )


def downgrade() -> None:
    """
    Remove tool_type column and index from tenant_configs table.
    """
    # Drop index first
    op.drop_index('idx_tenant_configs_tool_type', 'tenant_configs')

    # Drop column
    op.drop_column('tenant_configs', 'tool_type')
