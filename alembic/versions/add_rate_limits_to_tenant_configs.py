"""Add rate_limits JSONB field to tenant_configs for per-tenant rate limiting.

Revision ID: add_rate_limits_001
Revises: extend_tenant_configs_001
Create Date: 2025-11-03 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_rate_limits_001'
down_revision = 'extend_tenant_configs_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade: Add rate_limits JSONB column to tenant_configs table.

    Adds a JSONB field for storing per-tenant rate limit configurations.
    Default value includes webhook rate limits (100 requests per 60 seconds).
    """
    op.add_column(
        'tenant_configs',
        sa.Column(
            'rate_limits',
            sa.JSON(),
            nullable=True,
            server_default=sa.text(
                "'{\"webhooks\": {\"ticket_created\": 100, \"ticket_resolved\": 100}}'::jsonb"
            ),
            comment='Per-tenant rate limit configuration (JSONB). Default: 100 webhooks/min per endpoint',
        )
    )


def downgrade() -> None:
    """Downgrade: Remove rate_limits column from tenant_configs table."""
    op.drop_column('tenant_configs', 'rate_limits')
