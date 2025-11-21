"""add_cognitive_architecture_to_agents

Revision ID: 016
Revises: 015
Create Date: 2025-11-19

Story: 12.8 - Dynamic Cognitive Architectures
Description: Add cognitive_architecture column to agents table to support
different execution strategies (ReAct, Plan-and-Solve, etc.).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '016'
down_revision: Union[str, Sequence[str], None] = '015'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add cognitive_architecture column to agents table.
    
    Default value is 'react' to maintain backward compatibility.
    """
    op.add_column(
        'agents',
        sa.Column(
            'cognitive_architecture',
            sa.String(length=50),
            nullable=False,
            server_default='react',
            comment='Cognitive architecture: react, single_step, plan_and_solve'
        )
    )


def downgrade() -> None:
    """
    Remove cognitive_architecture column from agents table.
    """
    op.drop_column('agents', 'cognitive_architecture')
