"""
Async database session management with connection pooling.

This module provides SQLAlchemy async engine and session factory configuration
for use throughout the application. Connection pooling is configured per the
technical specifications with max 20 connections per service.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import pool

from src.config import settings
from src.database.models import Base


# Global async engine instance (lazy initialized)
_async_engine = None


def get_async_engine():
    """
    Get or create the global async database engine.

    Creates an async engine with connection pooling configured per specifications:
    - pool_size: Maximum 20 connections per service
    - pool_pre_ping: True to detect stale connections
    - echo: SQL logging enabled in development mode

    Returns:
        AsyncEngine: SQLAlchemy async engine instance

    Raises:
        RuntimeError: If database URL is not configured
    """
    global _async_engine

    if _async_engine is None:
        if not settings.database_url:
            raise RuntimeError(
                "Database URL not configured. Please set AI_AGENTS_DATABASE_URL "
                "environment variable."
            )

        _async_engine = create_async_engine(
            settings.database_url,
            echo=settings.environment == "development",
            pool_size=settings.database_pool_size,
            pool_pre_ping=True,  # Detect stale connections
            pool_recycle=3600,  # Recycle connections after 1 hour
        )

    return _async_engine


# Create async session factory
async_session_maker = async_sessionmaker(
    get_async_engine(),
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database session management.

    Provides an async SQLAlchemy session for database operations.
    Session is automatically committed on success or rolled back on error.

    Usage:
        @app.get("/items")
        async def get_items(session: AsyncSession = Depends(get_async_session)):
            result = await session.execute(select(Item))
            return result.scalars().all()

    Yields:
        AsyncSession: Database session for async operations

    Raises:
        Exception: If connection fails
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize the database by creating all tables.

    This should be called on application startup if using code-first migrations.
    When using Alembic migrations, this is not necessary.

    Raises:
        Exception: If table creation fails
    """
    engine = get_async_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def dispose_db() -> None:
    """
    Dispose of the database engine and close all connections.

    This should be called on application shutdown.

    Raises:
        Exception: If disposal fails
    """
    global _async_engine
    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None
