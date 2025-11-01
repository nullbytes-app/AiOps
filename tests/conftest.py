"""
Pytest configuration and shared fixtures for all tests.

This module configures pytest for the project and provides shared fixtures
that setup test environment, database, Redis, and other dependencies.
"""

import os
import sys
import pytest


def pytest_configure(config):
    """Configure pytest before test collection."""
    # Set default test environment variables BEFORE importing any modules
    # These defaults are only used if explicitly needed by tests
    # Some tests specifically test error handling when env vars are missing,
    # so we don't set defaults for all required variables

    # Only set environment if not already in CI/Docker environment
    if not os.environ.get("CI"):
        # These can be set safely as they're used by most integration tests
        os.environ.setdefault("AI_AGENTS_ENVIRONMENT", "development")
        os.environ.setdefault("AI_AGENTS_LOG_LEVEL", "DEBUG")


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Set up test environment and reload settings."""
    # Set required environment variables for integration tests
    # (but only if not already set by a test fixture)
    os.environ.setdefault("AI_AGENTS_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/ai_agents")
    os.environ.setdefault("AI_AGENTS_REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("AI_AGENTS_CELERY_BROKER_URL", "redis://localhost:6379/1")
    os.environ.setdefault("AI_AGENTS_CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

    # Import config module AFTER environment variables are set
    from src import config

    # Force reload of settings module to pick up test environment variables
    if config.settings is None:
        try:
            config.settings = config.Settings()
        except Exception as e:
            print(f"Warning: Could not initialize settings: {e}")
            # Continue anyway, some tests may not need settings

    yield


@pytest.fixture
def env_vars(monkeypatch):
    """Fixture to set environment variables for individual tests."""
    def set_env(**kwargs):
        for key, value in kwargs.items():
            monkeypatch.setenv(f"AI_AGENTS_{key.upper()}", str(value))
    return set_env



