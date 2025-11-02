"""
Database connection and session management.

This module provides PostgreSQL connection pooling and session management.
Full implementation will be completed in Story 1.3.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings


# Global engine instance (will be initialized on startup)
_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    """
    Get or create the global database engine.

    Creates an async engine with connection pooling configured per specifications:
    - pool_size: Maximum connections per service
    - pool_pre_ping: True to detect and remove stale connections
    - echo: SQL query logging enabled in development mode

    Returns:
        AsyncEngine: SQLAlchemy async engine instance

    Raises:
        RuntimeError: If engine not initialized
    """
    global _engine
    if _engine is None:
        import os
        # Get database URL from environment or settings
        db_url = os.getenv("AI_AGENTS_DATABASE_URL") or settings.database_url

        # For local development, replace 'postgres' service name with 'localhost'
        # This allows running the app locally while tests run in Docker
        if "postgres:" in db_url:
            db_url = db_url.replace("postgres:5432", "localhost:5433")

        _engine = create_async_engine(
            db_url,
            pool_size=settings.database_pool_size,
            pool_pre_ping=True,  # Detect stale connections
            pool_recycle=3600,  # Recycle connections after 1 hour
            echo=settings.environment == "development",
        )
    return _engine


async def check_database_connection() -> bool:
    """
    Check if database connection is healthy.

    Returns:
        bool: True if connection is healthy, False otherwise
    """
    try:
        import os
        import socket
        # Get database URL from environment or settings
        db_url = os.getenv("AI_AGENTS_DATABASE_URL") or settings.database_url

        # For local development, replace 'postgres' service name with 'localhost'
        # But only if NOT running inside a Docker container
        hostname = socket.gethostname()
        is_in_docker = os.path.exists('/.dockerenv') or hostname.startswith('ai-agents-')

        if "postgres:" in db_url and not is_in_docker:
            db_url = db_url.replace("postgres:5432", "localhost:5433")

        # Create a temporary engine for health check
        check_engine = create_async_engine(
            db_url,
            echo=False,
            pool_pre_ping=True,
        )

        async with check_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

        await check_engine.dispose()
        return True
    except Exception:
        return False


async def get_db_session() -> AsyncSession:
    """
    Create a database session.

    This is a placeholder that will be fully implemented in Story 1.3
    with proper dependency injection for FastAPI.

    Returns:
        AsyncSession: Database session
    """
    engine = get_engine()
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
