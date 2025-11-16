"""add_mcp_health_tracking

Revision ID: 011
Revises: 010
Create Date: 2025-11-10

Story: 11.1.8 - Basic MCP Server Health Monitoring
Description: Add consecutive_failures column and health check performance index
to mcp_servers table for circuit breaker functionality and query optimization.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '011'
down_revision: Union[str, Sequence[str], None] = '010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add health monitoring fields and indexes to mcp_servers table for Story 11.1.8.

    Adds:
    - consecutive_failures column: INTEGER DEFAULT 0 (circuit breaker tracking)
    - Index on (status, last_health_check): Optimize health check queries
    """

    # Add consecutive_failures column for circuit breaker logic
    op.add_column(
        'mcp_servers',
        sa.Column(
            'consecutive_failures',
            sa.Integer(),
            nullable=False,
            server_default='0',
            comment='Number of consecutive failed health checks (circuit breaker at >=3)'
        )
    )

    # Create composite index for health check queries
    # Pattern: SELECT * FROM mcp_servers WHERE status IN ('active', 'error') ORDER BY last_health_check
    # This index optimizes the periodic health check task query
    op.create_index(
        'idx_mcp_servers_status_health_check',
        'mcp_servers',
        ['status', 'last_health_check'],
        postgresql_ops={'status': 'text_pattern_ops'}  # Optimize for IN queries
    )


def downgrade() -> None:
    """
    Remove health monitoring fields and indexes from mcp_servers table.

    WARNING: This will delete consecutive_failures data for all servers.
    Use only for development/testing.
    """

    # Drop index first
    op.drop_index('idx_mcp_servers_status_health_check', table_name='mcp_servers')

    # Drop consecutive_failures column
    op.drop_column('mcp_servers', 'consecutive_failures')
