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
    # Set test environment variables BEFORE importing any modules
    # This is critical - many modules import settings at module load time
    os.environ.setdefault("AI_AGENTS_DATABASE_URL", "postgresql+asyncpg://aiagents:password@localhost:5433/ai_agents")
    os.environ.setdefault("AI_AGENTS_REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("AI_AGENTS_CELERY_BROKER_URL", "redis://localhost:6379/1")
    os.environ.setdefault("AI_AGENTS_CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    os.environ.setdefault("AI_AGENTS_WEBHOOK_SECRET", "test-webhook-secret-minimum-32-chars-required-here")
    os.environ.setdefault("AI_AGENTS_ADMIN_API_KEY", "test-admin-api-key-minimum-32-characters-required")
    os.environ.setdefault("AI_AGENTS_OPENROUTER_API_KEY", "test-openrouter-api-key-sk-or-v1-valid-format")
    os.environ.setdefault("AI_AGENTS_SERVICEDESK_API_KEY", "test-servicedesk-api-key")
    os.environ.setdefault("AI_AGENTS_SERVICEDESK_BASE_URL", "https://test.servicedesk.com")
    os.environ.setdefault("AI_AGENTS_OPENROUTER_SITE_URL", "https://test.example.com")
    os.environ.setdefault("AI_AGENTS_OPENROUTER_APP_NAME", "AI Agents Test Suite")
    # Set encryption key for tenant config encryption/decryption tests (Story 3.2 & 3.3)
    # Note: Both ENCRYPTION_KEY and AI_AGENTS_ENCRYPTION_KEY are set for compatibility
    # Must be a valid Fernet key (44 chars, base64 encoded)
    encryption_key = "cQ6XaP2aIb5CiVkoKSYfLKEaRZNpqGVdkJCo6ia_buY="
    os.environ.setdefault("ENCRYPTION_KEY", encryption_key)
    os.environ.setdefault("AI_AGENTS_ENCRYPTION_KEY", encryption_key)
    # Set individual secret fields for Story 3.3 tests (Kubernetes Secrets)
    os.environ.setdefault("AI_AGENTS_POSTGRES_PASSWORD", "test_postgres_password_min_12_chars")
    os.environ.setdefault("AI_AGENTS_REDIS_PASSWORD", "test_redis_password_min_12_chars")
    os.environ.setdefault("AI_AGENTS_OPENAI_API_KEY", "sk-proj-test-openai-api-key-for-testing")

    # Only set additional environment if not already in CI/Docker environment
    if not os.environ.get("CI"):
        # These can be set safely as they're used by most integration tests
        os.environ.setdefault("AI_AGENTS_ENVIRONMENT", "development")
        os.environ.setdefault("AI_AGENTS_LOG_LEVEL", "DEBUG")


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Set up test environment and reload settings."""
    # Set required environment variables for integration tests
    # (but only if not already set by a test fixture)
    os.environ.setdefault("AI_AGENTS_DATABASE_URL", "postgresql+asyncpg://aiagents:password@localhost:5433/ai_agents")
    os.environ.setdefault("AI_AGENTS_REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("AI_AGENTS_CELERY_BROKER_URL", "redis://localhost:6379/1")
    os.environ.setdefault("AI_AGENTS_CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    os.environ.setdefault("AI_AGENTS_WEBHOOK_SECRET", "test-webhook-secret-minimum-32-chars-required-here")
    os.environ.setdefault("AI_AGENTS_ADMIN_API_KEY", "test-admin-api-key-minimum-32-characters-required")
    os.environ.setdefault("AI_AGENTS_OPENROUTER_API_KEY", "test-openrouter-api-key")
    os.environ.setdefault("AI_AGENTS_SERVICEDESK_API_KEY", "test-servicedesk-api-key")
    os.environ.setdefault("AI_AGENTS_SERVICEDESK_BASE_URL", "https://test.servicedesk.com")
    # Story 3.3: Kubernetes Secrets fields
    # Note: Both ENCRYPTION_KEY and AI_AGENTS_ENCRYPTION_KEY are set for compatibility
    # Must be a valid Fernet key (44 chars, base64 encoded)
    encryption_key = "cQ6XaP2aIb5CiVkoKSYfLKEaRZNpqGVdkJCo6ia_buY="
    os.environ.setdefault("ENCRYPTION_KEY", encryption_key)
    os.environ.setdefault("AI_AGENTS_ENCRYPTION_KEY", encryption_key)
    os.environ.setdefault("AI_AGENTS_POSTGRES_PASSWORD", "test_postgres_password_min_12_chars")
    os.environ.setdefault("AI_AGENTS_REDIS_PASSWORD", "test_redis_password_min_12_chars")
    os.environ.setdefault("AI_AGENTS_OPENAI_API_KEY", "sk-proj-test-openai-api-key-for-testing")

    # Import config module AFTER environment variables are set
    from src import config

    # Force reload of settings module to pick up test environment variables
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


# Import all test fixtures for pytest discovery
pytest_plugins = [
    "tests.fixtures.rls_fixtures",
]
