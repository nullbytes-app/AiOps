"""
Cleanup script to remove test users from database before running tests.

This script should be run before auth integration tests to ensure
a clean slate.

Story: 1C - API Endpoints & Middleware
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path so we can import src
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os


async def cleanup_test_users():
    """Delete all test users from database."""
    # Use test database URL
    db_url = os.environ.get(
        "AI_AGENTS_DATABASE_URL",
        "postgresql+asyncpg://aiagents:password@localhost:5433/ai_agents"
    )

    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            from src.database.models import User

            # Delete test users (those with @example.com emails)
            result = await session.execute(
                delete(User).where(User.email.like('%@example.com'))
            )
            deleted_count = result.rowcount
            await session.commit()

            print(f"Deleted {deleted_count} test users from database")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(cleanup_test_users())
