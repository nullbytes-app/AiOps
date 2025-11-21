#!/usr/bin/env python3
"""
Admin user creation script for Story 1A.

Creates a super_admin user with a default tenant role. This script is idempotent
(checks if user exists before creating) and accepts environment variables for
credentials.

Usage:
    # Set environment variables
    export ADMIN_EMAIL="admin@example.com"
    export ADMIN_PASSWORD="SecurePassword123!"
    export DEFAULT_TENANT_ID="00000000-0000-0000-0000-000000000000"

    # Run script
    python scripts/create_admin_user.py

Environment Variables:
    ADMIN_EMAIL: Email address for admin user (required)
    ADMIN_PASSWORD: Password for admin user (required, min 12 chars)
    DEFAULT_TENANT_ID: UUID of default tenant (required)
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from src.database.models import User, UserTenantRole, RoleEnum


async def hash_password(password: str) -> str:
    """
    Hash password with bcrypt (10 rounds).

    Args:
        password: Plain text password

    Returns:
        Bcrypt hashed password (str)
    """
    # bcrypt.hashpw requires bytes
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=10)  # 10 rounds = balance security vs performance
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


async def create_admin_user(
    email: str,
    password: str,
    default_tenant_id: str,
    db: AsyncSession
) -> None:
    """
    Create super_admin user with default tenant role.

    This function is idempotent - if user already exists, it will skip creation.

    Args:
        email: Admin email address
        password: Admin password (plain text, will be hashed)
        default_tenant_id: UUID of default tenant
        db: Async database session

    Raises:
        ValueError: If password is too weak (< 12 chars)
    """
    # Validate password strength
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters long")

    # Check if user already exists
    result = await db.execute(
        select(User).where(User.email == email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        print(f"✓ User {email} already exists (ID: {existing_user.id})")
        return

    # Hash password
    print(f"Hashing password with bcrypt (10 rounds)...")
    password_hash = await hash_password(password)

    # Calculate password expiry (90 days from now)
    password_expires_at = datetime.utcnow() + timedelta(days=90)

    # Create user
    user = User(
        email=email,
        password_hash=password_hash,
        default_tenant_id=default_tenant_id,
        failed_login_attempts=0,
        locked_until=None,
        password_expires_at=password_expires_at,
        password_history=[],  # Empty on first creation
    )
    db.add(user)
    await db.flush()  # Flush to get user.id

    print(f"✓ Created user {email} (ID: {user.id})")

    # Assign super_admin role to default tenant
    role = UserTenantRole(
        user_id=user.id,
        tenant_id=default_tenant_id,
        role=RoleEnum.SUPER_ADMIN.value,
    )
    db.add(role)

    # Commit transaction
    await db.commit()

    print(f"✓ Assigned super_admin role for tenant {default_tenant_id}")
    print(f"✓ Password expires at: {password_expires_at.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"\n🎉 Admin user created successfully!")
    print(f"   Email: {email}")
    print(f"   Default Tenant: {default_tenant_id}")
    print(f"   Role: super_admin")


async def main():
    """
    Main entry point for script.

    Reads environment variables, validates input, and creates admin user.
    """
    # Read environment variables
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    default_tenant_id = os.getenv("DEFAULT_TENANT_ID")

    # Validate required environment variables
    if not admin_email:
        print("❌ ERROR: ADMIN_EMAIL environment variable is required")
        print("   Example: export ADMIN_EMAIL='admin@example.com'")
        sys.exit(1)

    if not admin_password:
        print("❌ ERROR: ADMIN_PASSWORD environment variable is required")
        print("   Example: export ADMIN_PASSWORD='SecurePassword123!'")
        sys.exit(1)

    if not default_tenant_id:
        print("❌ ERROR: DEFAULT_TENANT_ID environment variable is required")
        print("   Example: export DEFAULT_TENANT_ID='00000000-0000-0000-0000-000000000000'")
        sys.exit(1)

    # Validate password strength
    if len(admin_password) < 12:
        print("❌ ERROR: Password must be at least 12 characters long")
        sys.exit(1)

    # Get database URL from environment
    database_url = os.getenv(
        "AI_AGENTS_DATABASE_URL",
        "postgresql+asyncpg://aiagents:password@localhost:5432/ai_agents"
    )

    print("=" * 60)
    print("Admin User Creation Script")
    print("=" * 60)
    print(f"Email: {admin_email}")
    print(f"Default Tenant: {default_tenant_id}")
    print(f"Database URL: {database_url.split('@')[1] if '@' in database_url else database_url}")
    print("=" * 60)
    print()

    # Create async engine and session
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Create admin user
    try:
        async with async_session() as session:
            await create_admin_user(
                email=admin_email,
                password=admin_password,
                default_tenant_id=default_tenant_id,
                db=session
            )
    except Exception as e:
        print(f"\n❌ ERROR: Failed to create admin user")
        print(f"   {type(e).__name__}: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
