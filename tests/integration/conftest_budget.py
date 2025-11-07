"""Configuration for budget integration tests.

Mocks settings before imports to avoid database connection issues during test collection.
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(scope="session", autouse=True)
def mock_settings_for_import():
    """Mock settings before any imports to avoid database connection errors."""
    with patch("src.config.settings") as mock_settings:
        mock_settings.database_url = "postgresql+asyncpg://test:test@localhost:5432/test"
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.litellm_proxy_url = "http://litellm:4000"
        mock_settings.litellm_master_key = "sk-test-master-key"
        mock_settings.litellm_webhook_secret = "test-webhook-secret"
        yield mock_settings
