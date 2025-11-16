"""Remove LLM provider tables (Story 9.2)

Revision ID: 007
Revises: 006_add_agent_memory_schema
Create Date: 2025-11-07

Story 9.2: Provider Management via LiteLLM API
- Removes llm_providers and llm_models tables
- Providers are now managed via LiteLLM proxy API
- No provider data stored in application database
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop llm_providers and llm_models tables with CASCADE for dependent objects."""
    # Note: fallback_chains and fallback_metrics tables have foreign keys to llm_models
    # We need to drop those foreign key constraints first or use CASCADE

    # Drop foreign key constraints from fallback_chains table
    op.drop_constraint(
        "fk_fallback_chains_model_id",
        "fallback_chains",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_fallback_chains_fallback_model_id",
        "fallback_chains",
        type_="foreignkey",
    )

    # Drop foreign key constraints from fallback_metrics table
    op.drop_constraint(
        "fk_fallback_metrics_model_id",
        "fallback_metrics",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_fallback_metrics_fallback_model_id",
        "fallback_metrics",
        type_="foreignkey",
    )

    # Now drop llm_models table
    op.drop_table("llm_models", schema=None)

    # Then drop llm_providers table
    op.drop_table("llm_providers", schema=None)


def downgrade() -> None:
    """Recreate llm_providers and llm_models tables (schema only)."""
    # Recreate llm_providers table
    op.create_table(
        "llm_providers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("provider_type", sa.String(length=100), nullable=False),
        sa.Column("api_base_url", sa.String(length=500), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_test_at", sa.DateTime(), nullable=True),
        sa.Column("last_test_success", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_llm_providers_tenant_id"),
        sa.PrimaryKeyConstraint("id", name="pk_llm_providers"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_llm_provider_name_per_tenant"),
    )

    # Recreate llm_models table
    op.create_table(
        "llm_models",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider_id", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("context_window", sa.Integer(), nullable=True),
        sa.Column("cost_per_input_token", sa.Numeric(precision=12, scale=10), nullable=True),
        sa.Column("cost_per_output_token", sa.Numeric(precision=12, scale=10), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["provider_id"], ["llm_providers.id"], name="fk_llm_models_provider_id"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_llm_models"),
        sa.UniqueConstraint("provider_id", "model_name", name="uq_llm_model_name_per_provider"),
    )
