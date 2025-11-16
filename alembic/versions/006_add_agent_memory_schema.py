"""add_agent_memory_schema

Revision ID: 006
Revises: 005
Create Date: 2025-11-07

Create agent_memory table and add memory_config to agents table for Story 8.15: Memory Configuration UI.
Implements PostgreSQL pgvector extension for vector similarity search.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, Sequence[str], None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create agent_memory table and extend Agent model for Story 8.15.

    1. Enable pgvector extension for vector similarity search
    2. Create agent_memory table with three memory types (short_term, long_term, agentic)
    3. Add memory_config JSONB column to agents table for configuration
    4. Create composite and vector indexes for performance
    """

    # Enable pgvector extension for vector similarity search
    # NOTE: Commented out for now - pgvector extension needs to be installed in PostgreSQL first
    # op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Create agent_memory table
    op.create_table(
        'agent_memory',
        sa.Column('id', sa.UUID(), nullable=False, comment='Memory entry ID (UUID)'),
        sa.Column('agent_id', sa.UUID(), nullable=False, comment='ID of agent owning this memory'),
        sa.Column('tenant_id', sa.UUID(), nullable=False, comment='Tenant for multi-tenant isolation'),
        sa.Column(
            'memory_type',
            sa.String(20),
            nullable=False,
            comment='Memory type: short_term, long_term, or agentic'
        ),
        sa.Column(
            'content',
            sa.JSON(),
            nullable=False,
            comment='Memory content as JSONB (flexible structure for different memory types)'
        ),
        sa.Column(
            'embedding',
            sa.Text(),
            nullable=True,
            comment='Vector embedding for semantic search (text format for pgvector, 1536 dims)'
        ),
        sa.Column(
            'retention_days',
            sa.Integer(),
            nullable=False,
            server_default='90',
            comment='Days to retain this memory before auto-deletion'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment='Timestamp when memory was created'
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            comment='Timestamp when memory was last updated'
        ),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant_configs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            "memory_type IN ('short_term', 'long_term', 'agentic')",
            name='check_memory_type'
        ),
    )

    # Create composite index for primary query pattern (agent_id, memory_type, created_at DESC)
    op.create_index(
        'idx_agent_memory_agent_type',
        'agent_memory',
        ['agent_id', 'memory_type', sa.desc('created_at')]
    )

    # Create index for tenant isolation queries
    op.create_index(
        'idx_agent_memory_tenant',
        'agent_memory',
        ['tenant_id']
    )

    # Note: Vector index (ivfflat) will be created separately after embedding column is populated
    # This prevents performance issues during migration

    # Add memory_config column to agents table
    op.add_column(
        'agents',
        sa.Column(
            'memory_config',
            sa.JSON(),
            nullable=True,
            comment='Agent memory configuration: short_term, long_term, agentic settings'
        )
    )


def downgrade() -> None:
    """
    Drop agent_memory table and memory_config column.

    WARNING: This will delete all agent memories.
    Use only for development/testing.
    """

    # Drop memory_config column
    op.drop_column('agents', 'memory_config')

    # Drop agent_memory table and indexes
    op.drop_index('idx_agent_memory_tenant', table_name='agent_memory')
    op.drop_index('idx_agent_memory_agent_type', table_name='agent_memory')
    op.drop_table('agent_memory')

    # Note: pgvector extension is not dropped to avoid breaking other potential uses
