"""add_mcp_server_metrics_table

Revision ID: 012
Revises: 011
Create Date: 2025-11-10

Story: 11.2.4 - Enhanced MCP Health Monitoring
Description: Create mcp_server_metrics table for time-series health metrics collection
with response time tracking, status monitoring, and error analysis capabilities.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '012'
down_revision: Union[str, Sequence[str], None] = '011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create mcp_server_metrics table for Story 11.2.4.

    This table stores time-series health check data for MCP servers, enabling:
    - Performance trend analysis (response time tracking)
    - Failure pattern detection (error rates and types)
    - Capacity planning (request rate monitoring)
    - Proactive alerting (degradation detection)

    Retention: 7 days (managed by Celery cleanup task)
    """

    # Create mcp_server_metrics table
    op.create_table(
        'mcp_server_metrics',

        # Primary key
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text('uuid_generate_v4()'),
            comment='Primary key for metrics record'
        ),

        # Foreign keys with CASCADE delete (when server deleted, metrics deleted)
        sa.Column(
            'mcp_server_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('mcp_servers.id', ondelete='CASCADE'),
            nullable=False,
            comment='MCP server this metric belongs to'
        ),
        sa.Column(
            'tenant_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('tenant_configs.id', ondelete='CASCADE'),
            nullable=False,
            comment='Tenant for row-level security and isolation'
        ),

        # Timing metrics
        sa.Column(
            'response_time_ms',
            sa.Integer(),
            nullable=False,
            comment='Health check response time in milliseconds'
        ),
        sa.Column(
            'check_timestamp',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text('now()'),
            comment='When the health check was performed'
        ),

        # Status metrics
        sa.Column(
            'status',
            sa.String(20),
            nullable=False,
            comment="Health check result: 'success', 'timeout', 'error', 'connection_failed'"
        ),
        sa.Column(
            'error_message',
            sa.Text(),
            nullable=True,
            comment='Error message if status is not success'
        ),
        sa.Column(
            'error_type',
            sa.String(100),
            nullable=True,
            comment="Error type classification: 'TimeoutError', 'ProcessCrashed', 'InvalidJSON', etc."
        ),

        # Request metadata
        sa.Column(
            'check_type',
            sa.String(50),
            nullable=False,
            comment="Type of health check: 'health_check', 'tools_list', 'ping'"
        ),
        sa.Column(
            'transport_type',
            sa.String(20),
            nullable=False,
            comment="Transport type: 'stdio' or 'http_sse'"
        ),

        # Timestamp
        sa.Column(
            'created_at',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text('now()'),
            comment='Record creation timestamp'
        ),
    )

    # Index 1: Optimize time-series queries by server (most common query pattern)
    # Query pattern: SELECT * FROM mcp_server_metrics
    #                WHERE mcp_server_id = ? AND check_timestamp >= ?
    #                ORDER BY check_timestamp DESC
    op.create_index(
        'idx_mcp_metrics_server_time',
        'mcp_server_metrics',
        ['mcp_server_id', sa.text('check_timestamp DESC')],
        postgresql_using='btree',
    )

    # Index 2: Optimize tenant isolation queries
    # Query pattern: SELECT * FROM mcp_server_metrics WHERE tenant_id = ?
    op.create_index(
        'idx_mcp_metrics_tenant',
        'mcp_server_metrics',
        ['tenant_id'],
        postgresql_using='btree',
    )

    # Index 3: Optimize error analysis queries
    # Query pattern: SELECT * FROM mcp_server_metrics
    #                WHERE status = 'error' AND check_timestamp >= ?
    op.create_index(
        'idx_mcp_metrics_status_time',
        'mcp_server_metrics',
        ['status', sa.text('check_timestamp DESC')],
        postgresql_using='btree',
    )


def downgrade() -> None:
    """
    Remove mcp_server_metrics table and all associated indexes.

    WARNING: This will permanently delete all historical health metrics data.
    Use only for development/testing rollbacks.
    """

    # Drop indexes first (required before dropping table)
    op.drop_index('idx_mcp_metrics_status_time', table_name='mcp_server_metrics')
    op.drop_index('idx_mcp_metrics_tenant', table_name='mcp_server_metrics')
    op.drop_index('idx_mcp_metrics_server_time', table_name='mcp_server_metrics')

    # Drop table (CASCADE deletes handled by database)
    op.drop_table('mcp_server_metrics')
