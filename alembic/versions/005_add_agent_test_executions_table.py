"""add_agent_test_executions_table

Revision ID: 005
Revises: 004
Create Date: 2025-11-07

Create agent_test_executions table for Story 8.14: Agent Testing Sandbox.
Stores test execution results, traces, token usage, timing, and errors.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, Sequence[str], None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create agent_test_executions table for Story 8.14.

    Stores sandbox test execution results including:
    - Test payload (webhook or trigger simulation)
    - Execution trace (step-by-step execution details)
    - Token usage (input/output/total tokens and cost)
    - Execution timing (total duration and per-step breakdown)
    - Error information (stack traces for debugging)
    """
    op.create_table(
        'agent_test_executions',
        sa.Column('id', sa.UUID(), nullable=False, comment='Test execution ID (UUID)'),
        sa.Column('agent_id', sa.UUID(), nullable=False, comment='ID of agent being tested'),
        sa.Column('tenant_id', sa.UUID(), nullable=False, comment='Tenant for isolation'),
        sa.Column(
            'payload',
            sa.JSON(),
            nullable=False,
            comment='Test payload: webhook data or trigger parameters'
        ),
        sa.Column(
            'execution_trace',
            sa.JSON(),
            nullable=False,
            comment='Step-by-step execution trace: {steps: [{step_type, tool_name, input, output, duration_ms}]}'
        ),
        sa.Column(
            'token_usage',
            sa.JSON(),
            nullable=False,
            comment='Token tracking: {input_tokens, output_tokens, total_tokens, estimated_cost_usd}'
        ),
        sa.Column(
            'execution_time',
            sa.JSON(),
            nullable=False,
            comment='Timing breakdown: {total_duration_ms, steps: [{name, duration_ms}]}'
        ),
        sa.Column(
            'errors',
            sa.JSON(),
            nullable=True,
            comment='Error details if execution failed: {error_type, message, stack_trace}'
        ),
        sa.Column(
            'status',
            sa.String(),
            nullable=False,
            server_default='success',
            comment='Execution status: success or failed'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment='Timestamp when test was executed'
        ),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant_configs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create indexes for fast history retrieval
    op.create_index(
        'idx_agent_test_executions_agent_id',
        'agent_test_executions',
        ['agent_id']
    )
    op.create_index(
        'idx_agent_test_executions_created_at',
        'agent_test_executions',
        ['created_at']
    )
    op.create_index(
        'idx_agent_test_executions_tenant_id',
        'agent_test_executions',
        ['tenant_id']
    )


def downgrade() -> None:
    """
    Drop agent_test_executions table and indexes.

    WARNING: This will delete all test execution history.
    Use only for development/testing.
    """
    op.drop_index('idx_agent_test_executions_tenant_id', table_name='agent_test_executions')
    op.drop_index('idx_agent_test_executions_created_at', table_name='agent_test_executions')
    op.drop_index('idx_agent_test_executions_agent_id', table_name='agent_test_executions')
    op.drop_table('agent_test_executions')
