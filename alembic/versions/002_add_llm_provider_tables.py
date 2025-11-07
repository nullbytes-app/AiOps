"""Add LLM provider and model configuration tables.

Revision ID: 002_llm_providers
Revises: 001_budget_enforcement
Create Date: 2025-11-06 16:00:00.000000

This migration adds LLM provider configuration functionality:
- llm_providers table for storing provider credentials (OpenAI, Anthropic, Azure, etc.)
- llm_models table for model configuration (pricing, context window, capabilities)
- Encrypted API key storage with Fernet cipher
- Indexes for performance optimization
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_llm_providers'
down_revision: Union[str, None] = '001_budget_enforcement'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add LLM provider and model tables.

    Changes:
        1. Create llm_providers table:
           - Stores provider credentials (OpenAI, Anthropic, Azure OpenAI, etc.)
           - API keys encrypted with Fernet cipher
           - Connection test tracking (last_test_at, last_test_success)
           - Indexes on provider_type and enabled columns

        2. Create llm_models table:
           - Model configuration (pricing, context window, capabilities)
           - Foreign key to llm_providers with CASCADE delete
           - Unique constraint on (provider_id, model_name)
           - Indexes on provider_id and enabled columns
    """
    # Create llm_providers table
    op.create_table(
        'llm_providers',
        sa.Column(
            'id',
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
            comment='Primary key'
        ),
        sa.Column(
            'name',
            sa.String(255),
            nullable=False,
            unique=True,
            comment='Provider name (e.g., "Production OpenAI", "Azure GPT-4")'
        ),
        sa.Column(
            'provider_type',
            sa.String(50),
            nullable=False,
            comment='Provider type: openai, anthropic, azure_openai, bedrock, replicate, together_ai, custom'
        ),
        sa.Column(
            'api_base_url',
            sa.Text(),
            nullable=False,
            comment='API base URL (e.g., https://api.openai.com/v1)'
        ),
        sa.Column(
            'api_key_encrypted',
            sa.Text(),
            nullable=False,
            comment='Encrypted API key using Fernet cipher from ENCRYPTION_KEY env var'
        ),
        sa.Column(
            'enabled',
            sa.Boolean(),
            nullable=False,
            server_default='TRUE',
            comment='Provider enabled status (soft delete when FALSE)'
        ),
        sa.Column(
            'last_test_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Timestamp of last connection test'
        ),
        sa.Column(
            'last_test_success',
            sa.Boolean(),
            nullable=True,
            comment='Result of last connection test (TRUE=success, FALSE=failure, NULL=not tested)'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('NOW()'),
            comment='Creation timestamp'
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('NOW()'),
            comment='Last modification timestamp'
        ),
    )

    # Create indexes on llm_providers
    op.create_index(
        'idx_llm_providers_type',
        'llm_providers',
        ['provider_type'],
        unique=False
    )
    op.create_index(
        'idx_llm_providers_enabled',
        'llm_providers',
        ['enabled'],
        unique=False
    )

    # Create llm_models table
    op.create_table(
        'llm_models',
        sa.Column(
            'id',
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
            comment='Primary key'
        ),
        sa.Column(
            'provider_id',
            sa.Integer(),
            sa.ForeignKey('llm_providers.id', ondelete='CASCADE'),
            nullable=False,
            comment='Foreign key to llm_providers table (CASCADE delete)'
        ),
        sa.Column(
            'model_name',
            sa.String(255),
            nullable=False,
            comment='Model identifier (e.g., "gpt-4", "claude-3-5-sonnet-20240620")'
        ),
        sa.Column(
            'display_name',
            sa.String(255),
            nullable=True,
            comment='User-friendly display name (e.g., "GPT-4 Turbo", "Claude 3.5 Sonnet")'
        ),
        sa.Column(
            'enabled',
            sa.Boolean(),
            nullable=False,
            server_default='FALSE',
            comment='Model enabled in LiteLLM config (default: disabled until explicitly enabled)'
        ),
        sa.Column(
            'cost_per_input_token',
            sa.Float(),
            nullable=True,
            comment='Cost per 1M input tokens in USD (e.g., 0.03 = $30/1M tokens)'
        ),
        sa.Column(
            'cost_per_output_token',
            sa.Float(),
            nullable=True,
            comment='Cost per 1M output tokens in USD (e.g., 0.06 = $60/1M tokens)'
        ),
        sa.Column(
            'context_window',
            sa.Integer(),
            nullable=True,
            comment='Maximum context window size in tokens (e.g., 128000 for GPT-4 Turbo)'
        ),
        sa.Column(
            'capabilities',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='Model capabilities JSONB: {"streaming": true, "function_calling": true, "vision": true}'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('NOW()'),
            comment='Creation timestamp'
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('NOW()'),
            comment='Last modification timestamp'
        ),
    )

    # Create unique constraint on (provider_id, model_name)
    op.create_unique_constraint(
        'uq_llm_models_provider_model',
        'llm_models',
        ['provider_id', 'model_name']
    )

    # Create indexes on llm_models
    op.create_index(
        'idx_llm_models_provider',
        'llm_models',
        ['provider_id'],
        unique=False
    )
    op.create_index(
        'idx_llm_models_enabled',
        'llm_models',
        ['enabled'],
        unique=False
    )


def downgrade() -> None:
    """
    Remove LLM provider and model tables.

    Drops tables in reverse order to respect foreign key constraints.
    """
    # Drop llm_models table (child first due to foreign key)
    op.drop_index('idx_llm_models_enabled', table_name='llm_models')
    op.drop_index('idx_llm_models_provider', table_name='llm_models')
    op.drop_constraint('uq_llm_models_provider_model', 'llm_models', type_='unique')
    op.drop_table('llm_models')

    # Drop llm_providers table (parent)
    op.drop_index('idx_llm_providers_enabled', table_name='llm_providers')
    op.drop_index('idx_llm_providers_type', table_name='llm_providers')
    op.drop_table('llm_providers')
