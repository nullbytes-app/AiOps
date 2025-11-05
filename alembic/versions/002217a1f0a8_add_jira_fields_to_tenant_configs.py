"""add_jira_fields_to_tenant_configs

Revision ID: 002217a1f0a8
Revises: 3ad133f66494
Create Date: 2025-11-05 08:08:43.710314

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002217a1f0a8'
down_revision: Union[str, Sequence[str], None] = '3ad133f66494'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add Jira-specific fields to tenant_configs table.

    Adds support for Jira Service Management plugin configuration:
    - jira_url: Base URL for Jira Cloud instance
    - jira_api_token_encrypted: Encrypted API token for authentication
    - jira_project_key: Default project key for tenant

    These fields are nullable (optional for non-Jira tenants).
    Existing ServiceDesk Plus tenants are unaffected.
    """
    op.add_column(
        'tenant_configs',
        sa.Column('jira_url', sa.String(length=500), nullable=True)
    )
    op.add_column(
        'tenant_configs',
        sa.Column('jira_api_token_encrypted', sa.LargeBinary(), nullable=True)
    )
    op.add_column(
        'tenant_configs',
        sa.Column('jira_project_key', sa.String(length=50), nullable=True)
    )


def downgrade() -> None:
    """
    Remove Jira-specific fields from tenant_configs table.

    Reverts migration by dropping Jira columns.
    WARNING: This will delete all Jira tenant configurations.
    """
    op.drop_column('tenant_configs', 'jira_project_key')
    op.drop_column('tenant_configs', 'jira_api_token_encrypted')
    op.drop_column('tenant_configs', 'jira_url')
