"""
Database Helper for Streamlit Admin UI.

This module provides synchronous database access for the Streamlit admin interface.
It creates a separate synchronous SQLAlchemy session factory that reuses the existing
models from src/database/models.py but uses psycopg2 (sync) instead of asyncpg (async).

The FastAPI application continues to use async sessions (asyncpg), while
Streamlit uses this sync session helper.

Key Features:
- Synchronous database access compatible with Streamlit's execution model
- Reuses existing SQLAlchemy models (TenantConfig, EnhancementHistory)
- Connection pooling with st.cache_resource
- Graceful error handling with user-friendly messages
"""

import os
from contextlib import contextmanager
from typing import Generator, Optional

import streamlit as st
from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# Import existing models (shared with FastAPI)
from database.models import Base, TenantConfig, EnhancementHistory


@st.cache_resource
def get_sync_engine() -> Optional[Engine]:
    """
    Create synchronous SQLAlchemy engine with connection pooling.

    Uses @st.cache_resource to persist the engine across Streamlit reruns.
    This ensures efficient connection pooling and avoids recreating the engine
    on every interaction.

    Returns:
        Engine: SQLAlchemy synchronous engine, or None if connection fails

    Environment Variables:
        AI_AGENTS_DATABASE_URL: PostgreSQL connection string
            Format: postgresql://user:password@host:port/database
            Example: postgresql://aiagents:password@localhost:5432/ai_agents
    """
    try:
        # Get database URL from environment
        # Convert asyncpg URL to psycopg2 if needed
        database_url = os.getenv("AI_AGENTS_DATABASE_URL", "")

        if not database_url:
            logger.error("AI_AGENTS_DATABASE_URL environment variable not set")
            return None

        # Convert asyncpg URL to psycopg2 format
        if database_url.startswith("postgresql+asyncpg://"):
            database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        elif database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://")

        # Create synchronous engine with connection pooling
        engine = create_engine(
            database_url,
            pool_size=5,  # Small pool for admin UI
            max_overflow=10,
            pool_pre_ping=True,  # Verify connections before using
            echo=False,  # Set to True for SQL debugging
        )

        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        logger.info("Database connection established successfully")
        return engine

    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        return None


@st.cache_resource
def get_session_maker() -> Optional[sessionmaker]:
    """
    Create session factory for database operations.

    Returns:
        sessionmaker: SQLAlchemy session factory, or None if engine unavailable
    """
    engine = get_sync_engine()
    if engine is None:
        return None

    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Provides a database session with automatic commit/rollback handling.
    Use this in a `with` statement for safe database operations.

    Usage:
        with get_db_session() as session:
            tenants = session.query(TenantConfig).all()
            for tenant in tenants:
                print(tenant.name)

    Yields:
        Session: SQLAlchemy session for database operations

    Raises:
        Exception: If database connection is unavailable
    """
    SessionMaker = get_session_maker()

    if SessionMaker is None:
        raise Exception(
            "Database connection unavailable. "
            "Check AI_AGENTS_DATABASE_URL environment variable."
        )

    session = SessionMaker()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()


def get_tenant_count() -> int:
    """
    Get total number of configured tenants.

    This is a simple test query to verify database connectivity.

    Returns:
        int: Number of tenants, or 0 if query fails
    """
    try:
        with get_db_session() as session:
            count = session.query(TenantConfig).count()
            return count
    except Exception as e:
        logger.error(f"Failed to get tenant count: {e}")
        return 0


def test_database_connection() -> tuple[bool, str]:
    """
    Test database connectivity and return status.

    Used on app startup to display connection status to users.

    Returns:
        tuple[bool, str]: (success, message)
            success: True if connection works, False otherwise
            message: User-friendly status message
    """
    try:
        engine = get_sync_engine()
        if engine is None:
            return False, "❌ Database engine creation failed. Check configuration."

        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()

        tenant_count = get_tenant_count()

        return (
            True,
            f"✅ Connected to PostgreSQL\n\n"
            f"**Database Version:** {version[:50]}...\n\n"
            f"**Tenants Configured:** {tenant_count}",
        )

    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False, f"❌ Connection failed: {str(e)}"


def show_connection_status() -> None:
    """
    Display database connection status in Streamlit UI.

    Shows a success or error message based on connectivity test.
    Should be called in the sidebar or main area on app startup.
    """
    success, message = test_database_connection()

    if success:
        st.success(message)
    else:
        st.error(message)
        st.warning(
            "**Troubleshooting:**\n\n"
            "1. Verify `AI_AGENTS_DATABASE_URL` environment variable is set\n"
            "2. Check PostgreSQL service is running\n"
            "3. Verify network connectivity to database host\n"
            "4. Check database credentials are correct"
        )
