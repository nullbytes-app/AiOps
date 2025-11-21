"""add_auth_tables

Revision ID: 015
Revises: 014
Create Date: 2025-01-17

Story: 1A - Database & Auth Foundation
Description: Create users, user_tenant_roles, and auth_audit_log tables for authentication and RBAC.
Also updates audit_log table to support CRUD operation tracking with old/new values.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '015'
down_revision: Union[str, Sequence[str], None] = '014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create auth tables for Story 1A.

    Creates:
    - users table (authentication credentials and security settings)
    - user_tenant_roles table (RBAC role assignments per tenant)
    - auth_audit_log table (authentication event tracking)
    - Updates audit_log table (adds tenant_id, entity fields, old/new values)
    """

    # ========================================
    # 1. Create users table
    # ========================================
    op.create_table(
        'users',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text('gen_random_uuid()'),
            comment='Globally unique user ID'
        ),
        sa.Column(
            'email',
            sa.String(255),
            nullable=False,
            comment='User email address (unique, used for login)'
        ),
        sa.Column(
            'password_hash',
            sa.String(255),
            nullable=False,
            comment='Bcrypt hashed password (never store plain text)'
        ),
        sa.Column(
            'default_tenant_id',
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment='Default tenant ID for this user'
        ),
        sa.Column(
            'failed_login_attempts',
            sa.Integer(),
            nullable=False,
            server_default=sa.text('0'),
            comment='Counter for failed login attempts (reset on successful login)'
        ),
        sa.Column(
            'locked_until',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Timestamp until which account is locked (15 minutes after 5 failed attempts)'
        ),
        sa.Column(
            'password_expires_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Timestamp when password expires (90 days after creation)'
        ),
        sa.Column(
            'password_history',
            postgresql.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
            comment='JSON array of last 5 password hashes (prevents password reuse)'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment='Account creation timestamp (UTC)'
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment='Last update timestamp (UTC, auto-updated)'
        ),

        # Primary key
        sa.PrimaryKeyConstraint('id', name='pk_users'),
    )

    # Create unique index on email
    op.create_index(
        'ix_users_email',
        'users',
        ['email'],
        unique=True
    )

    # ========================================
    # 2. Create user_tenant_roles table
    # ========================================
    op.create_table(
        'user_tenant_roles',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text('gen_random_uuid()'),
            comment='Globally unique role assignment ID'
        ),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment='FK to users table'
        ),
        sa.Column(
            'tenant_id',
            sa.String(255),
            nullable=False,
            comment='Tenant identifier (matches TenantConfig.tenant_id)'
        ),
        sa.Column(
            'role',
            sa.String(50),
            nullable=False,
            comment='Role enum: super_admin, tenant_admin, operator, developer, viewer'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment='Role assignment timestamp (UTC)'
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment='Last update timestamp (UTC, auto-updated)'
        ),

        # Primary key
        sa.PrimaryKeyConstraint('id', name='pk_user_tenant_roles'),

        # Foreign key to users with CASCADE delete
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
            ondelete='CASCADE',
            name='fk_user_tenant_roles_user_id'
        ),

        # CHECK constraint for role enum validation
        sa.CheckConstraint(
            "role IN ('super_admin', 'tenant_admin', 'operator', 'developer', 'viewer')",
            name='ck_user_tenant_roles_role'
        ),

        # Unique constraint: one role per user per tenant
        sa.UniqueConstraint(
            'user_id',
            'tenant_id',
            name='uq_user_tenant'
        ),
    )

    # CRITICAL: Composite index for fast role lookups (on-demand role fetching, see ADR 003)
    op.create_index(
        'ix_user_tenant_roles_lookup',
        'user_tenant_roles',
        ['user_id', 'tenant_id']
    )

    # ========================================
    # 3. Create auth_audit_log table
    # ========================================
    op.create_table(
        'auth_audit_log',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text('gen_random_uuid()'),
            comment='Globally unique audit log entry ID'
        ),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment='FK to users table (nullable: user not found on failed login)'
        ),
        sa.Column(
            'event_type',
            sa.String(100),
            nullable=False,
            comment='Event type: login, logout, password_reset, account_locked, etc.'
        ),
        sa.Column(
            'success',
            sa.Boolean(),
            nullable=False,
            comment='True = success, False = failure'
        ),
        sa.Column(
            'ip_address',
            sa.String(45),  # IPv6 max length
            nullable=True,
            comment='IP address of client (IPv4 or IPv6)'
        ),
        sa.Column(
            'user_agent',
            sa.String(500),
            nullable=True,
            comment='User agent string (browser, OS, device)'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment='Event timestamp (UTC)'
        ),

        # Primary key
        sa.PrimaryKeyConstraint('id', name='pk_auth_audit_log'),

        # Foreign key to users with SET NULL on delete
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
            ondelete='SET NULL',
            name='fk_auth_audit_log_user_id'
        ),
    )

    # Indexes for efficient querying
    op.create_index(
        'ix_auth_audit_log_user_created',
        'auth_audit_log',
        ['user_id', 'created_at']
    )
    op.create_index(
        'ix_auth_audit_log_event_type',
        'auth_audit_log',
        ['event_type']
    )

    # ========================================
    # 4. Update existing audit_log table
    # ========================================
    # Drop existing indexes before altering table
    op.drop_index('ix_audit_log_timestamp', table_name='audit_log')
    op.drop_index('ix_audit_log_operation', table_name='audit_log')

    # Rename columns for clarity
    op.alter_column('audit_log', 'user', new_column_name='user_email', existing_type=sa.String(255))
    op.alter_column('audit_log', 'operation', new_column_name='action', existing_type=sa.String(100))
    op.alter_column('audit_log', 'details', new_column_name='old_value', existing_type=postgresql.JSON())

    # Add new columns
    op.add_column('audit_log', sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('audit_log', sa.Column('tenant_id', sa.String(255), nullable=True))
    op.add_column('audit_log', sa.Column('entity_type', sa.String(100), nullable=True))
    op.add_column('audit_log', sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('audit_log', sa.Column('new_value', postgresql.JSONB(), nullable=True))
    op.add_column('audit_log', sa.Column('ip_address', sa.String(45), nullable=True))
    op.add_column('audit_log', sa.Column('user_agent', sa.String(500), nullable=True))

    # Change old_value column type from JSON to JSONB
    op.alter_column('audit_log', 'old_value', type_=postgresql.JSONB(), postgresql_using='old_value::jsonb')

    # Rename timestamp to created_at for consistency
    op.alter_column('audit_log', 'timestamp', new_column_name='created_at', existing_type=sa.DateTime(timezone=True))

    # Add foreign key to users
    op.create_foreign_key(
        'fk_audit_log_user_id',
        'audit_log',
        'users',
        ['user_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Create new indexes
    op.create_index(
        'ix_audit_log_user_tenant_created',
        'audit_log',
        ['user_id', 'tenant_id', 'created_at']
    )
    op.create_index(
        'ix_audit_log_entity_type_created',
        'audit_log',
        ['entity_type', 'created_at']
    )


def downgrade() -> None:
    """
    Drop auth tables and revert audit_log changes.

    WARNING: This will delete all user accounts, role assignments, and auth audit logs.
    Use only for development/testing.
    """

    # ========================================
    # 1. Revert audit_log changes
    # ========================================
    # Drop new indexes
    op.drop_index('ix_audit_log_entity_type_created', table_name='audit_log')
    op.drop_index('ix_audit_log_user_tenant_created', table_name='audit_log')

    # Drop foreign key
    op.drop_constraint('fk_audit_log_user_id', 'audit_log', type_='foreignkey')

    # Remove new columns
    op.drop_column('audit_log', 'user_agent')
    op.drop_column('audit_log', 'ip_address')
    op.drop_column('audit_log', 'new_value')
    op.drop_column('audit_log', 'entity_id')
    op.drop_column('audit_log', 'entity_type')
    op.drop_column('audit_log', 'tenant_id')
    op.drop_column('audit_log', 'user_id')

    # Change old_value back to JSON
    op.alter_column('audit_log', 'old_value', type_=postgresql.JSON(), postgresql_using='old_value::json')

    # Rename columns back
    op.alter_column('audit_log', 'created_at', new_column_name='timestamp', existing_type=sa.DateTime(timezone=True))
    op.alter_column('audit_log', 'old_value', new_column_name='details', existing_type=postgresql.JSON())
    op.alter_column('audit_log', 'action', new_column_name='operation', existing_type=sa.String(100))
    op.alter_column('audit_log', 'user_email', new_column_name='user', existing_type=sa.String(255))

    # Recreate original indexes
    op.create_index('ix_audit_log_operation', 'audit_log', ['operation'])
    op.create_index('ix_audit_log_timestamp', 'audit_log', ['timestamp'], postgresql_ops={'timestamp': 'DESC'})

    # ========================================
    # 2. Drop auth_audit_log table
    # ========================================
    op.drop_index('ix_auth_audit_log_event_type', table_name='auth_audit_log')
    op.drop_index('ix_auth_audit_log_user_created', table_name='auth_audit_log')
    op.drop_table('auth_audit_log')

    # ========================================
    # 3. Drop user_tenant_roles table
    # ========================================
    op.drop_index('ix_user_tenant_roles_lookup', table_name='user_tenant_roles')
    op.drop_table('user_tenant_roles')

    # ========================================
    # 4. Drop users table
    # ========================================
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
