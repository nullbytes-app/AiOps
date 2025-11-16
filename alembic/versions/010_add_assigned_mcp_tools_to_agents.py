"""add_assigned_mcp_tools_to_agents

Revision ID: 010
Revises: 009
Create Date: 2025-11-09

Story: 11.1.6 - Agent Tool Assignment with MCP Support
Description: Add assigned_mcp_tools JSONB column to agents table for storing
MCP tool assignments. Enables agents to use both OpenAPI and MCP tools seamlessly.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '010'
down_revision: Union[str, Sequence[str], None] = '009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add assigned_mcp_tools column to agents table for Story 11.1.6.

    Adds JSONB column to store MCP tool assignments. MCP tools are discovered
    dynamically from mcp_servers.discovered_* arrays, so they don't have stable
    database records like OpenAPI tools. This column stores metadata needed for
    agent execution (tool ID, server ID, primitive type).

    Schema: List of MCPToolAssignment objects
    [
        {
            "id": "uuid5-deterministic",
            "name": "tool_name",
            "source_type": "mcp",
            "mcp_server_id": "uuid",
            "mcp_server_name": "server-name",
            "mcp_primitive_type": "tool|resource|prompt"
        }
    ]

    Backward compatible: Defaults to empty array for existing agents.
    """

    # Add assigned_mcp_tools column to agents table
    op.add_column(
        'agents',
        sa.Column(
            'assigned_mcp_tools',
            postgresql.JSONB(),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
            comment='MCP tool assignments (tools, resources, prompts) from mcp_servers'
        )
    )


def downgrade() -> None:
    """
    Remove assigned_mcp_tools column from agents table.

    WARNING: This will delete all MCP tool assignments for agents.
    Use only for development/testing. Agents will revert to OpenAPI-only tools.
    """

    # Drop assigned_mcp_tools column
    op.drop_column('agents', 'assigned_mcp_tools')
