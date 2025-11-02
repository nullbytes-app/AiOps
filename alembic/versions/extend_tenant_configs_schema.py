"""Extend tenant_configs schema for encryption and preferences.

Revision ID: extend_tenant_configs_001
Revises: 2075b4285d2b
Create Date: 2025-11-02 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'extend_tenant_configs_001'
down_revision = '2075b4285d2b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade: Add encryption fields and update schema."""
    # NOTE: These columns already exist in the current schema as of Story 3.1
    # This migration is a no-op but serves as documentation that the schema
    # includes encrypted fields and preferences support
    pass


def downgrade() -> None:
    """Downgrade: Revert schema changes."""
    pass
