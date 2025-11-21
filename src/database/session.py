"""
Async database session management with connection pooling.

This module provides SQLAlchemy async engine and session factory configuration
for use throughout the application. Connection pooling is configured per the
technical specifications with max 20 connections per service.
"""

from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import pool

from src import config
from src.database.models import Base


# Global async engine instance (lazy initialized)
_async_engine = None


def _get_settings():
    """
    Get settings, initializing if necessary.

    This helper handles the case where settings is None during test collection
    but environment variables have been set by pytest_configure.
    """
    if config.settings is None:
        # Try to initialize settings (this works if env vars are set)
        try:
            config.settings = config.Settings()
        except Exception:
            pass  # If initialization fails, settings remains None
    return config.settings


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
        # Get settings (initializing if necessary for tests)
        settings = _get_settings()

        # Handle case when settings is None (during test initialization)
        if settings is None:
            raise RuntimeError(
                "Settings not initialized. Please ensure environment variables are set "
                "and settings module is properly loaded."
            )

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


# Global async session maker (lazy initialized)
_async_session_maker = None


def get_async_session_maker():
    """
    Get or create the global async session maker.

    Returns:
        async_sessionmaker: SQLAlchemy async session factory
    """
    global _async_session_maker

    if _async_session_maker is None:
        _async_session_maker = async_sessionmaker(
            get_async_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

    return _async_session_maker


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
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions in background tasks and webhooks.

    Use this for non-FastAPI contexts where Depends() is not available:
    - Webhook handlers (Jira, ServiceDesk Plus)
    - Celery background tasks
    - Scheduled jobs (APScheduler)
    - CLI commands and scripts
    - Direct async functions outside request handlers

    This is identical to get_async_session() but with clearer naming for
    non-request contexts. Both yield a session that auto-commits on success
    and auto-rolls back on exceptions.

    Usage (Webhook Handler):
        async def handle_webhook(payload: dict):
            async with get_db_session() as db:
                tenant_service = TenantService(db, redis_client)
                config = await tenant_service.get_tenant_config(tenant_id)
                # ... process webhook

    Usage (Celery Task):
        @celery_app.task
        async def process_enhancement(job_id: str):
            async with get_db_session() as db:
                job_service = JobService(db, redis_client)
                await job_service.update_status(job_id, "processing")
                # ... process job

    Yields:
        AsyncSession: Database session (auto-commits on success, auto-rolls back on error)

    Raises:
        Exception: If database operations fail
    """
    session_maker = get_async_session_maker()
    async with session_maker() as session:
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
