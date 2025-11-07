"""Add budget enforcement columns and tables.

Revision ID: 001_budget_enforcement
Revises: fb8ab610bec8
Create Date: 2025-11-06 10:00:00.000000

This migration adds budget enforcement functionality to the AI Agents platform:
- Budget configuration columns in tenant_configs (max_budget, thresholds, duration)
- budget_overrides table for temporary admin overrides
- budget_alert_history table for alert tracking
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_budget_enforcement'
down_revision: Union[str, None] = 'fb8ab610bec8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add budget enforcement columns and tables.

    Changes:
        1. Add budget columns to tenant_configs table:
           - max_budget (FLOAT): Maximum budget in USD (default: 500.00)
           - alert_threshold (INTEGER): Alert percentage 50-100 (default: 80)
           - grace_threshold (INTEGER): Blocking percentage 100-150 (default: 110)
           - budget_duration (VARCHAR(10)): Reset period "30d", "60d", "90d" (default: "30d")
           - budget_reset_at (TIMESTAMPTZ): Next reset timestamp
           - litellm_key_last_reset (TIMESTAMPTZ): Last key budget reset timestamp

        2. Create budget_overrides table:
           - Tracks temporary budget increases by platform admins
           - Includes expiry timestamps and reason tracking

        3. Create budget_alert_history table:
           - Historical record of budget alerts for dashboard display
           - Tracks event type, spend, max_budget, percentage
    """
    # Add budget enforcement columns to tenant_configs
    op.add_column('tenant_configs', sa.Column(
        'max_budget',
        sa.Float(),
        nullable=False,
        server_default='500.00',
        comment='Maximum LLM budget in USD per budget period'
    ))
    op.add_column('tenant_configs', sa.Column(
        'alert_threshold',
        sa.Integer(),
        nullable=False,
        server_default='80',
        comment='Budget alert threshold percentage (50-100%, default: 80%)'
    ))
    op.add_column('tenant_configs', sa.Column(
        'grace_threshold',
        sa.Integer(),
        nullable=False,
        server_default='110',
        comment='Budget blocking threshold percentage (100-150%, default: 110%)'
    ))
    op.add_column('tenant_configs', sa.Column(
        'budget_duration',
        sa.String(10),
        nullable=False,
        server_default='30d',
        comment='Budget reset period: "30s", "30m", "30h", "30d", "60d", "90d"'
    ))
    op.add_column('tenant_configs', sa.Column(
        'budget_reset_at',
        sa.DateTime(timezone=True),
        nullable=True,
        comment='Timestamp when budget will next reset (auto-calculated from budget_duration)'
    ))
    op.add_column('tenant_configs', sa.Column(
        'litellm_key_last_reset',
        sa.DateTime(timezone=True),
        nullable=True,
        comment='Timestamp when LiteLLM virtual key budget was last reset'
    ))

    # Create budget_overrides table
    op.create_table(
        'budget_overrides',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('override_amount', sa.Float(), nullable=False,
                  comment='Temporary budget increase amount in USD'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False,
                  comment='When the temporary override expires'),
        sa.Column('reason', sa.Text(), nullable=False,
                  comment='Admin reason for budget override'),
        sa.Column('created_by', sa.String(255), nullable=False,
                  comment='Username of admin who granted override'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()'),
                  comment='When override was created'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant_configs.tenant_id'],
                                name='fk_budget_overrides_tenant'),
        sa.PrimaryKeyConstraint('id'),
        comment='Tracks temporary budget increases granted by platform admins'
    )
    op.create_index('idx_budget_overrides_tenant', 'budget_overrides', ['tenant_id'])
    op.create_index('idx_budget_overrides_expires', 'budget_overrides', ['expires_at'])
    op.create_index('idx_budget_overrides_tenant_expires', 'budget_overrides',
                    ['tenant_id', 'expires_at'])

    # Create budget_alert_history table
    op.create_table(
        'budget_alert_history',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False,
                  comment='LiteLLM event type: threshold_crossed, budget_crossed, projected_limit_exceeded'),
        sa.Column('spend', sa.Float(), nullable=False,
                  comment='Current spend in USD at time of alert'),
        sa.Column('max_budget', sa.Float(), nullable=False,
                  comment='Max budget in USD at time of alert'),
        sa.Column('percentage', sa.Integer(), nullable=False,
                  comment='Percentage used (spend/max_budget * 100)'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()'),
                  comment='When alert was received'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant_configs.tenant_id'],
                                name='fk_budget_alert_history_tenant'),
        sa.PrimaryKeyConstraint('id'),
        comment='Historical record of budget alerts for dashboard display and analytics'
    )
    op.create_index('idx_budget_alerts_tenant', 'budget_alert_history', ['tenant_id'])
    op.create_index('idx_budget_alerts_created', 'budget_alert_history', ['created_at'])
    op.create_index('idx_budget_alerts_tenant_recent', 'budget_alert_history',
                    ['tenant_id', 'created_at'])


def downgrade() -> None:
    """
    Remove budget enforcement columns and tables.

    WARNING: This will delete all budget configuration and alert history data.
    """
    # Drop indexes first
    op.drop_index('idx_budget_alerts_tenant_recent', 'budget_alert_history')
    op.drop_index('idx_budget_alerts_created', 'budget_alert_history')
    op.drop_index('idx_budget_alerts_tenant', 'budget_alert_history')

    op.drop_index('idx_budget_overrides_tenant_expires', 'budget_overrides')
    op.drop_index('idx_budget_overrides_expires', 'budget_overrides')
    op.drop_index('idx_budget_overrides_tenant', 'budget_overrides')

    # Drop tables
    op.drop_table('budget_alert_history')
    op.drop_table('budget_overrides')

    # Remove columns from tenant_configs
    op.drop_column('tenant_configs', 'litellm_key_last_reset')
    op.drop_column('tenant_configs', 'budget_reset_at')
    op.drop_column('tenant_configs', 'budget_duration')
    op.drop_column('tenant_configs', 'grace_threshold')
    op.drop_column('tenant_configs', 'alert_threshold')
    op.drop_column('tenant_configs', 'max_budget')
