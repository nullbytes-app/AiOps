"""Add enhancement_feedback table with RLS

Revision ID: 9a2d3e4f5b6c
Revises: add_rate_limits_to_tenant_configs
Create Date: 2025-11-04 09:00:00.000000

Story: 5.5 - Establish Baseline Metrics and Success Criteria (AC5)
Purpose: Add enhancement_feedback table to enable in-product feedback collection
         from technicians for continuous quality monitoring and roadmap prioritization.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9a2d3e4f5b6c'
down_revision: Union[str, Sequence[str], None] = 'add_rate_limits_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema - Create enhancement_feedback table with RLS policies.

    This table stores client feedback (thumbs up/down, 1-5 ratings, comments)
    for ticket enhancements to enable:
    - Continuous quality monitoring via in-product feedback
    - Technician satisfaction tracking (AC2 success criterion: >4/5 average)
    - Product roadmap prioritization based on feedback themes
    - Trend analysis over time (7-day baseline and ongoing)

    RLS policy ensures multi-tenant isolation matching existing tables.
    """
    # Create enhancement_feedback table
    op.create_table(
        'enhancement_feedback',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('ticket_id', sa.String(length=255), nullable=False),
        sa.Column('enhancement_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('technician_email', sa.String(length=255), nullable=True),
        sa.Column('feedback_type', sa.String(length=50), nullable=False),
        sa.Column('rating_value', sa.Integer(), nullable=True),
        sa.Column('feedback_comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),

        # Check constraints for data integrity
        sa.CheckConstraint(
            "feedback_type IN ('thumbs_up', 'thumbs_down', 'rating')",
            name='ck_feedback_type_valid'
        ),
        sa.CheckConstraint(
            "rating_value IS NULL OR (rating_value >= 1 AND rating_value <= 5)",
            name='ck_rating_value_range'
        ),
    )

    # Create indexes for efficient querying
    # Index on tenant_id for RLS enforcement and multi-tenant queries
    op.create_index(
        'ix_enhancement_feedback_tenant_id',
        'enhancement_feedback',
        ['tenant_id']
    )

    # Index on created_at for time-based aggregations (7-day baseline, trends)
    op.create_index(
        'ix_enhancement_feedback_created_at',
        'enhancement_feedback',
        ['created_at']
    )

    # Index on feedback_type for sentiment analysis (thumbs up/down distribution)
    op.create_index(
        'ix_enhancement_feedback_feedback_type',
        'enhancement_feedback',
        ['feedback_type']
    )

    # Composite index on (tenant_id, ticket_id) for per-ticket feedback retrieval
    op.create_index(
        'ix_enhancement_feedback_tenant_ticket',
        'enhancement_feedback',
        ['tenant_id', 'ticket_id']
    )

    # Enable Row-Level Security for multi-tenant isolation
    op.execute("ALTER TABLE enhancement_feedback ENABLE ROW LEVEL SECURITY;")

    # Create RLS policy matching pattern from enhancement_history and other tables
    # Policy ensures users can only see/modify records for their tenant
    # Uses app.current_tenant_id session variable set by application middleware
    op.execute("""
        CREATE POLICY tenant_isolation_policy_enhancement_feedback ON enhancement_feedback
        USING (tenant_id = current_setting('app.current_tenant_id')::VARCHAR)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::VARCHAR);
    """)

    # Grant permissions to app_user role (standard application role)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON enhancement_feedback TO app_user;")

    # Grant all permissions to admin role (for analytics, debugging, support)
    op.execute("GRANT ALL PRIVILEGES ON enhancement_feedback TO admin;")


def downgrade() -> None:
    """
    Downgrade schema - Remove enhancement_feedback table and RLS policies.

    Warning: This will delete all feedback data. Use with caution in production.
    """
    # Drop RLS policy
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy_enhancement_feedback ON enhancement_feedback;")

    # Disable RLS on table
    op.execute("ALTER TABLE enhancement_feedback DISABLE ROW LEVEL SECURITY;")

    # Revoke permissions
    op.execute("REVOKE ALL PRIVILEGES ON enhancement_feedback FROM app_user;")
    op.execute("REVOKE ALL PRIVILEGES ON enhancement_feedback FROM admin;")

    # Drop indexes (will be dropped automatically with table, but explicit for clarity)
    op.drop_index('ix_enhancement_feedback_tenant_ticket', table_name='enhancement_feedback')
    op.drop_index('ix_enhancement_feedback_feedback_type', table_name='enhancement_feedback')
    op.drop_index('ix_enhancement_feedback_created_at', table_name='enhancement_feedback')
    op.drop_index('ix_enhancement_feedback_tenant_id', table_name='enhancement_feedback')

    # Drop table
    op.drop_table('enhancement_feedback')
