"""
Tests for database helper module.

Tests database connection, session management, and query helpers.
"""

import os
from unittest.mock import Mock, patch, MagicMock

import pytest
import streamlit as st
from sqlalchemy.exc import OperationalError

from admin.utils.db_helper import (
    get_sync_engine,
    get_session_maker,
    get_db_session,
    get_tenant_count,
    test_database_connection,
)


@pytest.fixture(autouse=True)
def clear_streamlit_cache():
    """Clear Streamlit cache before each test to avoid cached function results."""
    # Clear cache for all cached functions
    st.cache_resource.clear()
    yield
    # Clear again after test to clean up
    st.cache_resource.clear()


@pytest.fixture
def mock_database_url():
    """Provide mock database URL via environment variable."""
    original_url = os.getenv("AI_AGENTS_DATABASE_URL")
    os.environ["AI_AGENTS_DATABASE_URL"] = "postgresql://test:test@localhost:5432/test_db"
    yield
    if original_url:
        os.environ["AI_AGENTS_DATABASE_URL"] = original_url
    else:
        del os.environ["AI_AGENTS_DATABASE_URL"]


@pytest.fixture
def mock_engine():
    """Create mock SQLAlchemy engine."""
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value.execute.return_value = None
    return engine


class TestGetSyncEngine:
    """Test synchronous engine creation."""

    def test_engine_creation_success(self, mock_database_url):
        """Test successful engine creation with valid connection string."""
        with patch("admin.utils.db_helper.create_engine") as mock_create:
            mock_create.return_value.connect.return_value.__enter__.return_value.execute.return_value = None

            engine = get_sync_engine()

            assert engine is not None
            mock_create.assert_called_once()

            # Verify connection string conversion from asyncpg to psycopg2
            call_args = mock_create.call_args[0][0]
            assert "postgresql://" in call_args
            assert "asyncpg" not in call_args

    def test_engine_creation_missing_url(self):
        """Test engine creation fails gracefully when DATABASE_URL not set."""
        with patch.dict(os.environ, {}, clear=True):
            engine = get_sync_engine()
            assert engine is None

    def test_engine_creation_connection_failure(self, mock_database_url):
        """Test engine creation handles connection failures."""
        with patch("admin.utils.db_helper.create_engine") as mock_create:
            mock_create.return_value.connect.side_effect = OperationalError("Connection failed", None, None)

            engine = get_sync_engine()
            assert engine is None

    def test_asyncpg_url_conversion(self, mock_database_url):
        """Test conversion of asyncpg URL to psycopg2 format."""
        os.environ["AI_AGENTS_DATABASE_URL"] = "postgresql+asyncpg://user:pass@host:5432/db"

        with patch("admin.utils.db_helper.create_engine") as mock_create:
            mock_create.return_value.connect.return_value.__enter__.return_value.execute.return_value = None
            get_sync_engine()

            call_args = mock_create.call_args[0][0]
            assert "postgresql://" in call_args
            assert "asyncpg" not in call_args


class TestGetSessionMaker:
    """Test session factory creation."""

    def test_session_maker_creation_success(self, mock_engine):
        """Test successful session maker creation."""
        with patch("admin.utils.db_helper.get_sync_engine", return_value=mock_engine):
            with patch("admin.utils.db_helper.sessionmaker") as mock_sessionmaker:
                session_maker = get_session_maker()

                assert session_maker is not None
                mock_sessionmaker.assert_called_once()

    def test_session_maker_no_engine(self):
        """Test session maker returns None when engine unavailable."""
        with patch("admin.utils.db_helper.get_sync_engine", return_value=None):
            session_maker = get_session_maker()
            assert session_maker is None


class TestGetDbSession:
    """Test database session context manager."""

    def test_session_context_manager_success(self):
        """Test successful session creation and commit."""
        mock_session = Mock()
        mock_session_maker = Mock(return_value=mock_session)

        with patch("admin.utils.db_helper.get_session_maker", return_value=mock_session_maker):
            with get_db_session() as session:
                assert session == mock_session

            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()

    def test_session_context_manager_rollback_on_error(self):
        """Test session rollback on exception."""
        mock_session = Mock()
        mock_session_maker = Mock(return_value=mock_session)

        with patch("admin.utils.db_helper.get_session_maker", return_value=mock_session_maker):
            with pytest.raises(ValueError):
                with get_db_session() as session:
                    raise ValueError("Test error")

            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()

    def test_session_context_manager_no_session_maker(self):
        """Test context manager raises exception when no session maker available."""
        with patch("admin.utils.db_helper.get_session_maker", return_value=None):
            with pytest.raises(Exception, match="Database connection unavailable"):
                with get_db_session():
                    pass


class TestGetTenantCount:
    """Test tenant count query."""

    def test_get_tenant_count_success(self):
        """Test successful tenant count retrieval."""
        mock_session = Mock()
        mock_query = Mock()
        mock_query.count.return_value = 5
        mock_session.query.return_value = mock_query

        mock_session_maker = Mock(return_value=mock_session)

        with patch("admin.utils.db_helper.get_session_maker", return_value=mock_session_maker):
            count = get_tenant_count()
            assert count == 5
            mock_session.commit.assert_called_once()

    def test_get_tenant_count_zero_tenants(self):
        """Test tenant count when no tenants configured."""
        mock_session = Mock()
        mock_query = Mock()
        mock_query.count.return_value = 0
        mock_session.query.return_value = mock_query

        mock_session_maker = Mock(return_value=mock_session)

        with patch("admin.utils.db_helper.get_session_maker", return_value=mock_session_maker):
            count = get_tenant_count()
            assert count == 0

    def test_get_tenant_count_error_handling(self):
        """Test tenant count returns 0 on error."""
        with patch("admin.utils.db_helper.get_session_maker", return_value=None):
            count = get_tenant_count()
            assert count == 0


class TestDatabaseConnectionTest:
    """Test database connection testing utility."""

    def test_connection_test_success(self, mock_engine):
        """Test successful database connection test."""
        mock_result = Mock()
        mock_result.scalar.return_value = "PostgreSQL 16.0"
        mock_engine.connect.return_value.__enter__.return_value.execute.return_value = mock_result

        with patch("admin.utils.db_helper.get_sync_engine", return_value=mock_engine):
            with patch("admin.utils.db_helper.get_tenant_count", return_value=3):
                success, message = test_database_connection()

                assert success is True
                assert "Connected to PostgreSQL" in message
                # Message uses markdown formatting with **bold**
                assert "**Tenants Configured:** 3" in message

    def test_connection_test_no_engine(self):
        """Test connection test fails when engine unavailable."""
        with patch("admin.utils.db_helper.get_sync_engine", return_value=None):
            success, message = test_database_connection()

            assert success is False
            assert "engine creation failed" in message

    def test_connection_test_connection_error(self, mock_engine):
        """Test connection test handles connection errors."""
        mock_engine.connect.side_effect = Exception("Connection refused")

        with patch("admin.utils.db_helper.get_sync_engine", return_value=mock_engine):
            success, message = test_database_connection()

            assert success is False
            assert "Connection failed" in message
            assert "Connection refused" in message
