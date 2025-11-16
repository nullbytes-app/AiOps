"""add_mcp_servers_table

Revision ID: 009
Revises: 008
Create Date: 2025-11-09

Story: 11.1.1 - MCP Server Data Model & Database Schema
Description: Create mcp_servers table with support for stdio and HTTP+SSE transports.
Enables AI Ops platform to integrate with Model Context Protocol (MCP) servers.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '009'
down_revision: Union[str, Sequence[str], None] = '008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create mcp_servers table for Story 11.1.1.

    Creates table with support for:
    - Multi-tenant isolation (tenant_id FK to tenant_configs)
    - Both stdio and HTTP+SSE transport types
    - JSONB storage for discovered capabilities (tools, resources, prompts)
    - Health status tracking
    - Performance indexes for common query patterns
    """

    # Create mcp_servers table
    op.create_table(
        'mcp_servers',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text('gen_random_uuid()'),
            comment='Unique server identifier (UUID)'
        ),
        sa.Column(
            'tenant_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment='Tenant ownership for multi-tenant isolation'
        ),
        sa.Column(
            'name',
            sa.String(255),
            nullable=False,
            comment='Human-readable server name (unique per tenant)'
        ),
        sa.Column(
            'description',
            sa.Text(),
            nullable=True,
            comment='Optional detailed description of server purpose'
        ),
        sa.Column(
            'transport_type',
            sa.String(20),
            nullable=False,
            comment='Transport protocol: stdio or http_sse'
        ),
        sa.Column(
            'command',
            sa.String(500),
            nullable=True,
            comment='Executable path for stdio (e.g., npx, python)'
        ),
        sa.Column(
            'args',
            postgresql.JSONB(),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
            comment='Command-line arguments array for stdio'
        ),
        sa.Column(
            'env',
            postgresql.JSONB(),
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
            comment='Environment variables object for stdio'
        ),
        sa.Column(
            'url',
            sa.String(500),
            nullable=True,
            comment='Base URL for HTTP+SSE transport'
        ),
        sa.Column(
            'headers',
            postgresql.JSONB(),
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
            comment='HTTP headers for authentication (e.g., Bearer tokens)'
        ),
        sa.Column(
            'discovered_tools',
            postgresql.JSONB(),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
            comment='Tools from MCP tools/list endpoint (array of tool schemas)'
        ),
        sa.Column(
            'discovered_resources',
            postgresql.JSONB(),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
            comment='Resources from MCP resources/list endpoint'
        ),
        sa.Column(
            'discovered_prompts',
            postgresql.JSONB(),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
            comment='Prompts from MCP prompts/list endpoint'
        ),
        sa.Column(
            'status',
            sa.String(20),
            nullable=False,
            server_default=sa.text("'inactive'"),
            comment='Current health status: active, inactive, or error'
        ),
        sa.Column(
            'last_health_check',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Timestamp of last health verification'
        ),
        sa.Column(
            'error_message',
            sa.Text(),
            nullable=True,
            comment='Latest error details if status=error'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment='Server registration timestamp'
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment='Last configuration update timestamp (auto-updated on change)'
        ),

        # Primary key
        sa.PrimaryKeyConstraint('id', name='pk_mcp_servers'),

        # Foreign key to tenant_configs with CASCADE delete
        sa.ForeignKeyConstraint(
            ['tenant_id'],
            ['tenant_configs.id'],
            ondelete='CASCADE',
            name='fk_mcp_servers_tenant_id'
        ),

        # CHECK constraints for enum validation
        sa.CheckConstraint(
            "transport_type IN ('stdio', 'http_sse')",
            name='ck_mcp_servers_transport_type'
        ),
        sa.CheckConstraint(
            "status IN ('active', 'inactive', 'error')",
            name='ck_mcp_servers_status'
        ),

        # Unique constraint: server name unique per tenant
        sa.UniqueConstraint(
            'tenant_id',
            'name',
            name='uq_mcp_servers_tenant_name'
        ),
    )

    # Create indexes for performance

    # Index 1: Fast tenant server lookups (most common query)
    op.create_index(
        'idx_mcp_servers_tenant_id',
        'mcp_servers',
        ['tenant_id']
    )

    # Index 2: Filter by health status
    op.create_index(
        'idx_mcp_servers_status',
        'mcp_servers',
        ['status']
    )

    # Index 3: Filter by transport type (stdio vs HTTP+SSE)
    op.create_index(
        'idx_mcp_servers_transport_type',
        'mcp_servers',
        ['transport_type']
    )

    # Index 4: Composite index for combined tenant + status queries
    # (tenant's active servers - most common filtered query)
    op.create_index(
        'idx_mcp_servers_tenant_status',
        'mcp_servers',
        ['tenant_id', 'status']
    )


def downgrade() -> None:
    """
    Drop mcp_servers table and all associated indexes.

    WARNING: This will delete all MCP server configurations.
    Use only for development/testing.
    """

    # Drop indexes first (required before dropping table)
    op.drop_index('idx_mcp_servers_tenant_status', table_name='mcp_servers')
    op.drop_index('idx_mcp_servers_transport_type', table_name='mcp_servers')
    op.drop_index('idx_mcp_servers_status', table_name='mcp_servers')
    op.drop_index('idx_mcp_servers_tenant_id', table_name='mcp_servers')

    # Drop table (foreign key and check constraints are dropped automatically)
    op.drop_table('mcp_servers')
