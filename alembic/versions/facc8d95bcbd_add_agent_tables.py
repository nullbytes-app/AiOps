"""add_agent_tables

Revision ID: facc8d95bcbd
Revises: 002217a1f0a8
Create Date: 2025-11-05 19:40:21.278981

This migration creates three agent-related tables:
1. agents: Core agent configuration with LLM settings
2. agent_triggers: Webhook and schedule triggers per agent
3. agent_tools: Many-to-many junction for agent-tool assignments

Impact:
- Adds multi-tenant agent storage with RLS support
- Enables dynamic AI agent orchestration
- Zero impact on existing tables
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "facc8d95bcbd"
down_revision: Union[str, Sequence[str], None] = "002217a1f0a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create agents, agent_triggers, and agent_tools tables."""

    # Create agents table
    op.create_table(
        "agents",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column(
            "llm_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant_configs.tenant_id"],
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'suspended', 'inactive')", name="ck_agents_status"
        ),
    )

    # Create indexes on agents table
    op.create_index("idx_agents_tenant_id_status", "agents", ["tenant_id", "status"], unique=False)
    op.create_index("idx_agents_created_at", "agents", [sa.text("created_at DESC")], unique=False)

    # Create agent_triggers table
    op.create_table(
        "agent_triggers",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("agent_id", sa.UUID(), nullable=False),
        sa.Column("trigger_type", sa.String(length=50), nullable=False),
        sa.Column("webhook_url", sa.String(length=500), nullable=True),
        sa.Column("hmac_secret", sa.Text(), nullable=True),
        sa.Column("schedule_cron", sa.String(length=100), nullable=True),
        sa.Column("payload_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "trigger_type IN ('webhook', 'schedule')", name="ck_agent_triggers_type"
        ),
    )

    # Create index on agent_triggers table
    op.create_index("idx_agent_triggers_agent_id", "agent_triggers", ["agent_id"], unique=False)

    # Create agent_tools junction table
    op.create_table(
        "agent_tools",
        sa.Column("agent_id", sa.UUID(), nullable=False),
        sa.Column("tool_id", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("agent_id", "tool_id"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
    )

    # Create indexes on agent_tools table
    op.create_index("idx_agent_tools_agent_id", "agent_tools", ["agent_id"], unique=False)
    op.create_index("idx_agent_tools_tool_id", "agent_tools", ["tool_id"], unique=False)


def downgrade() -> None:
    """Drop agents, agent_triggers, and agent_tools tables."""

    # Drop tables in reverse order (junction table and child tables first)
    op.drop_index("idx_agent_tools_tool_id", table_name="agent_tools")
    op.drop_index("idx_agent_tools_agent_id", table_name="agent_tools")
    op.drop_table("agent_tools")

    op.drop_index("idx_agent_triggers_agent_id", table_name="agent_triggers")
    op.drop_table("agent_triggers")

    op.drop_index("idx_agents_created_at", table_name="agents")
    op.drop_index("idx_agents_tenant_id_status", table_name="agents")
    op.drop_table("agents")
