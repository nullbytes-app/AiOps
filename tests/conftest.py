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
    # Also set TENANT_ENCRYPTION_KEY for Story 8.8 OpenAPI tool auth config encryption
    os.environ.setdefault("TENANT_ENCRYPTION_KEY", encryption_key)
    # Set individual secret fields for Story 3.3 tests (Kubernetes Secrets)
    os.environ.setdefault("AI_AGENTS_POSTGRES_PASSWORD", "test_postgres_password_min_12_chars")
    os.environ.setdefault("AI_AGENTS_REDIS_PASSWORD", "test_redis_password_min_12_chars")
    os.environ.setdefault("AI_AGENTS_OPENAI_API_KEY", "sk-proj-test-openai-api-key-for-testing")
    # Story 8.10: LiteLLM Budget Enforcement
    os.environ.setdefault("AI_AGENTS_LITELLM_MASTER_KEY", "sk-test-master-key-for-budget-enforcement")
    os.environ.setdefault("AI_AGENTS_LITELLM_WEBHOOK_SECRET", "test-webhook-secret-litellm-budget-min-32-chars")
    os.environ.setdefault("AI_AGENTS_LITELLM_PROXY_URL", "http://litellm:4000")

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


# ============================================================================
# Plugin Testing Fixtures (Story 7.6)
# ============================================================================


@pytest.fixture
def mock_generic_plugin():
    """
    Provide clean MockTicketingToolPlugin instance for each test.

    Returns:
        MockTicketingToolPlugin: Fresh mock plugin in success mode with
            clean call history for test isolation.

    Scope:
        Function scope (default) ensures each test gets a fresh instance
        with no state leakage from previous tests.

    Example:
        def test_webhook_validation(mock_generic_plugin):
            valid = await mock_generic_plugin.validate_webhook(payload, sig)
            assert valid is True
    """
    from tests.mocks.mock_plugin import MockTicketingToolPlugin
    return MockTicketingToolPlugin.success_mode()


@pytest.fixture
def mock_servicedesk_plugin():
    """
    Provide MockTicketingToolPlugin with ServiceDesk Plus-specific defaults.

    Returns:
        MockTicketingToolPlugin: Mock plugin configured with ServiceDesk Plus
            webhook payload structure and API response format.

    Notes:
        - Ticket response mimics ServiceDesk Plus API /api/v3/tickets/{id} structure
        - Priority format: {"name": "High"} (ServiceDesk Plus convention)
        - Created time format: {"value": "epoch_milliseconds"} (ServiceDesk Plus)

    Example:
        def test_servicedesk_workflow(mock_servicedesk_plugin):
            ticket = await mock_servicedesk_plugin.get_ticket("tenant", "123")
            assert "request" in ticket  # ServiceDesk Plus wraps in "request"
    """
    from tests.mocks.mock_plugin import MockTicketingToolPlugin
    from datetime import datetime, timezone

    # ServiceDesk Plus-specific ticket response structure
    servicedesk_ticket_response = {
        "request": {
            "id": "12345",
            "subject": "Mock ServiceDesk Plus ticket",
            "description": "<p>Server is slow and unresponsive</p>",
            "status": {"name": "Open"},
            "priority": {"name": "High"},
            "created_time": {"value": str(int(datetime.now(timezone.utc).timestamp() * 1000))},
        }
    }

    return MockTicketingToolPlugin(
        _validate_response=True,
        _get_ticket_response=servicedesk_ticket_response,
        _update_ticket_response=True,
    )


@pytest.fixture
def mock_jira_plugin():
    """
    Provide MockTicketingToolPlugin with Jira-specific defaults.

    Returns:
        MockTicketingToolPlugin: Mock plugin configured with Jira Service Management
            webhook payload structure and API response format.

    Notes:
        - Ticket response mimics Jira API /rest/api/3/issue/{key} structure
        - Key format: "PROJ-123" (Jira issue key convention)
        - Priority format: {"name": "High", "id": "2"} (Jira priority object)
        - Created format: "2025-11-05T10:00:00.000+0000" (ISO 8601 Jira format)

    Example:
        def test_jira_workflow(mock_jira_plugin):
            ticket = await mock_jira_plugin.get_ticket("tenant", "JIRA-456")
            assert ticket["key"] == "JIRA-456"
            assert "fields" in ticket  # Jira wraps data in "fields"
    """
    from tests.mocks.mock_plugin import MockTicketingToolPlugin
    from datetime import datetime, timezone

    # Jira-specific ticket response structure
    jira_ticket_response = {
        "id": "10456",
        "key": "JIRA-456",
        "fields": {
            "summary": "Mock Jira Service Management ticket",
            "description": "Server is slow and unresponsive",
            "status": {"name": "Open", "id": "1"},
            "priority": {"name": "High", "id": "2"},
            "created": datetime.now(timezone.utc).isoformat().replace("+00:00", "+0000"),
            "issuetype": {"name": "Incident", "id": "10001"},
        },
    }

    return MockTicketingToolPlugin(
        _validate_response=True,
        _get_ticket_response=jira_ticket_response,
        _update_ticket_response=True,
    )


@pytest.fixture
def mock_plugin_manager(monkeypatch):
    """
    Provide mocked PluginManager for plugin routing tests.

    Patches PluginManager singleton to return mock plugins for tenant lookups.
    Ensures proper cleanup after test.

    Args:
        monkeypatch: Pytest monkeypatch fixture for dependency injection.

    Yields:
        MagicMock: Mocked PluginManager instance with get_plugin method configured
            to return MockTicketingToolPlugin.

    Notes:
        - Uses monkeypatch to safely replace PluginManager singleton
        - Automatically cleans up after test (monkeypatch handles teardown)
        - get_plugin() returns MockTicketingToolPlugin.success_mode() by default

    Example:
        def test_plugin_routing(mock_plugin_manager):
            from src.plugins.registry import PluginManager
            plugin = PluginManager().get_plugin("servicedesk_plus")
            assert isinstance(plugin, MockTicketingToolPlugin)
    """
    from unittest.mock import MagicMock
    from tests.mocks.mock_plugin import MockTicketingToolPlugin

    # Create mock manager
    mock_manager = MagicMock()
    mock_manager.get_plugin.return_value = MockTicketingToolPlugin.success_mode()

    # Patch PluginManager singleton
    monkeypatch.setattr(
        "src.plugins.registry.PluginManager._instance",
        mock_manager
    )

    yield mock_manager

    # Cleanup happens automatically via monkeypatch teardown


@pytest.fixture(params=["api_error", "auth_error", "timeout", "not_found"])
def plugin_failure_mode(request):
    """
    Parameterized fixture for testing all plugin failure scenarios.

    Provides a MockTicketingToolPlugin instance configured for one of four
    failure modes. Test function using this fixture will be executed four times,
    once for each failure mode.

    Args:
        request: Pytest request object with param attribute.

    Returns:
        MockTicketingToolPlugin: Plugin configured for specific failure mode.

    Failure Modes:
        - api_error: Raises ServiceDeskAPIError in get_ticket/update_ticket
        - auth_error: Raises ValidationError in validate_webhook
        - timeout: Raises asyncio.TimeoutError in all async methods
        - not_found: Returns None from get_ticket (ticket not found)

    Example:
        def test_handle_failures(plugin_failure_mode):
            # This test runs 4 times, once for each failure mode
            plugin = plugin_failure_mode
            # Test error handling logic...
    """
    from tests.mocks.mock_plugin import MockTicketingToolPlugin

    factory_map = {
        "api_error": MockTicketingToolPlugin.api_error_mode,
        "auth_error": MockTicketingToolPlugin.auth_error_mode,
        "timeout": MockTicketingToolPlugin.timeout_mode,
        "not_found": MockTicketingToolPlugin.not_found_mode,
    }

    return factory_map[request.param]()


# Import all test fixtures for pytest discovery
pytest_plugins = [
    "tests.fixtures.rls_fixtures",
]
