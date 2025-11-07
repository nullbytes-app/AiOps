"""Add fallback chain tables for LLM provider fallback configuration.

Revision ID: 003_add_fallback_chain_tables
Revises: 002_llm_providers
Create Date: 2025-11-07 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "003_add_fallback_chain_tables"
down_revision = "002_llm_providers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create fallback chain, trigger, and metrics tables."""
    # Create fallback_chains table
    op.create_table(
        "fallback_chains",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "model_id",
            sa.Integer(),
            nullable=False,
            comment="Primary model ID (FK to llm_models)",
        ),
        sa.Column(
            "fallback_order",
            sa.Integer(),
            nullable=False,
            comment="Order in fallback chain (0=primary, 1=first fallback, etc)",
        ),
        sa.Column(
            "fallback_model_id",
            sa.Integer(),
            nullable=False,
            comment="Fallback model ID (FK to llm_models)",
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default="TRUE",
            comment="Chain enabled status",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="Creation timestamp",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            comment="Last modification timestamp",
        ),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["llm_models.id"],
            ondelete="CASCADE",
            name="fk_fallback_chains_model_id",
        ),
        sa.ForeignKeyConstraint(
            ["fallback_model_id"],
            ["llm_models.id"],
            ondelete="CASCADE",
            name="fk_fallback_chains_fallback_model_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "model_id",
            "fallback_order",
            name="uq_fallback_chains_model_order",
            comment="Unique constraint to prevent duplicate fallback positions",
        ),
        comment="Fallback chain configuration mapping primary models to fallback models",
    )

    # Create indexes on fallback_chains
    op.create_index(
        "idx_fallback_chains_model_id",
        "fallback_chains",
        ["model_id"],
        unique=False,
    )
    op.create_index(
        "idx_fallback_chains_fallback_model_id",
        "fallback_chains",
        ["fallback_model_id"],
        unique=False,
    )
    op.create_index(
        "idx_fallback_chains_enabled",
        "fallback_chains",
        ["enabled"],
        unique=False,
    )

    # Create fallback_triggers table
    op.create_table(
        "fallback_triggers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "trigger_type",
            sa.String(50),
            nullable=False,
            comment="Error type: RateLimitError, TimeoutError, InternalServerError, ConnectionError, ContentPolicyViolationError",
        ),
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
            server_default="3",
            comment="Number of retry attempts before fallback (0-10)",
        ),
        sa.Column(
            "backoff_factor",
            sa.Float(),
            nullable=False,
            server_default="2.0",
            comment="Exponential backoff multiplier (1.0-5.0)",
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default="TRUE",
            comment="Trigger enabled status",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="Creation timestamp",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "trigger_type",
            name="uq_fallback_triggers_type",
            comment="Unique trigger type configuration",
        ),
        comment="Fallback trigger configuration for different error types",
    )

    # Create index on fallback_triggers
    op.create_index(
        "idx_fallback_triggers_type",
        "fallback_triggers",
        ["trigger_type"],
        unique=False,
    )

    # Create fallback_metrics table
    op.create_table(
        "fallback_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "model_id",
            sa.Integer(),
            nullable=False,
            comment="Model ID (FK to llm_models)",
        ),
        sa.Column(
            "trigger_type",
            sa.String(50),
            nullable=False,
            comment="Error type that triggered fallback",
        ),
        sa.Column(
            "fallback_model_id",
            sa.Integer(),
            nullable=True,
            comment="Fallback model used (FK to llm_models)",
        ),
        sa.Column(
            "trigger_count",
            sa.Integer(),
            nullable=False,
            server_default="1",
            comment="Number of times this fallback was triggered",
        ),
        sa.Column(
            "success_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Number of successful fallback resolutions",
        ),
        sa.Column(
            "failure_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Number of failed fallback attempts",
        ),
        sa.Column(
            "last_triggered_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp of last trigger",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="Creation timestamp",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            comment="Last modification timestamp",
        ),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["llm_models.id"],
            ondelete="CASCADE",
            name="fk_fallback_metrics_model_id",
        ),
        sa.ForeignKeyConstraint(
            ["fallback_model_id"],
            ["llm_models.id"],
            ondelete="SET NULL",
            name="fk_fallback_metrics_fallback_model_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="Fallback metrics tracking trigger counts, success rates, and historical data",
    )

    # Create indexes on fallback_metrics
    op.create_index(
        "idx_fallback_metrics_model_id",
        "fallback_metrics",
        ["model_id"],
        unique=False,
    )
    op.create_index(
        "idx_fallback_metrics_fallback_model_id",
        "fallback_metrics",
        ["fallback_model_id"],
        unique=False,
    )
    op.create_index(
        "idx_fallback_metrics_trigger_type",
        "fallback_metrics",
        ["trigger_type"],
        unique=False,
    )
    op.create_index(
        "idx_fallback_metrics_created_at",
        "fallback_metrics",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop fallback chain tables."""
    # Drop indexes
    op.drop_index("idx_fallback_metrics_created_at", table_name="fallback_metrics")
    op.drop_index("idx_fallback_metrics_trigger_type", table_name="fallback_metrics")
    op.drop_index(
        "idx_fallback_metrics_fallback_model_id", table_name="fallback_metrics"
    )
    op.drop_index("idx_fallback_metrics_model_id", table_name="fallback_metrics")

    op.drop_index("idx_fallback_triggers_type", table_name="fallback_triggers")

    op.drop_index("idx_fallback_chains_enabled", table_name="fallback_chains")
    op.drop_index(
        "idx_fallback_chains_fallback_model_id", table_name="fallback_chains"
    )
    op.drop_index("idx_fallback_chains_model_id", table_name="fallback_chains")

    # Drop tables
    op.drop_table("fallback_metrics")
    op.drop_table("fallback_triggers")
    op.drop_table("fallback_chains")
