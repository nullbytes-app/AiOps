"""add_byok_columns

Revision ID: 004
Revises: 002217a1f0a8
Create Date: 2025-11-07

Add BYOK (Bring Your Own Key) columns to tenant_configs table for Story 8.13.
Supports per-tenant API key management for OpenAI and Anthropic models.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, Sequence[str], None] = ['002217a1f0a8', '003_add_fallback_chain_tables']
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add BYOK columns to tenant_configs table (Story 8.13).

    New columns:
    - byok_enabled: BOOLEAN flag to switch between platform/BYOK mode
    - byok_openai_key_encrypted: TEXT for Fernet-encrypted OpenAI API key
    - byok_anthropic_key_encrypted: TEXT for Fernet-encrypted Anthropic API key
    - byok_virtual_key: TEXT for LiteLLM virtual key specific to BYOK tenant
    - byok_enabled_at: TIMESTAMP for audit trail of BYOK enablement

    Existing tenants default to byok_enabled=False (platform mode).
    """
    op.add_column(
        'tenant_configs',
        sa.Column(
            'byok_enabled',
            sa.Boolean(),
            nullable=False,
            server_default='FALSE',
            comment='Flag to enable Bring Your Own Key (BYOK) mode for tenant'
        )
    )
    op.add_column(
        'tenant_configs',
        sa.Column(
            'byok_openai_key_encrypted',
            sa.Text(),
            nullable=True,
            comment='Fernet-encrypted OpenAI API key for BYOK tenants'
        )
    )
    op.add_column(
        'tenant_configs',
        sa.Column(
            'byok_anthropic_key_encrypted',
            sa.Text(),
            nullable=True,
            comment='Fernet-encrypted Anthropic API key for BYOK tenants'
        )
    )
    op.add_column(
        'tenant_configs',
        sa.Column(
            'byok_virtual_key',
            sa.Text(),
            nullable=True,
            comment='LiteLLM virtual key for BYOK tenant (separate from platform litellm_virtual_key)'
        )
    )
    op.add_column(
        'tenant_configs',
        sa.Column(
            'byok_enabled_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Timestamp when BYOK was enabled (audit trail)'
        )
    )


def downgrade() -> None:
    """
    Remove BYOK columns from tenant_configs table.

    WARNING: This will delete all BYOK tenant configurations and API keys.
    Use only for development/testing. Production downgrades should be reviewed carefully.
    """
    op.drop_column('tenant_configs', 'byok_enabled_at')
    op.drop_column('tenant_configs', 'byok_virtual_key')
    op.drop_column('tenant_configs', 'byok_anthropic_key_encrypted')
    op.drop_column('tenant_configs', 'byok_openai_key_encrypted')
    op.drop_column('tenant_configs', 'byok_enabled')
