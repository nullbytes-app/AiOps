"""
Pytest configuration and shared fixtures for all tests.

This module configures pytest for the project and provides shared fixtures
that setup test environment, database, Redis, and other dependencies.
"""

import os
import sys
import pytest
from unittest.mock import MagicMock

# Mock jose module before any imports
sys.modules["jose"] = MagicMock()
sys.modules["jose.jwt"] = MagicMock()
sys.modules["passlib"] = MagicMock()
sys.modules["passlib.context"] = MagicMock()
sys.modules["zxcvbn"] = MagicMock()
sys.modules["langchain_openai"] = MagicMock()
sys.modules["langgraph"] = MagicMock()
sys.modules["langgraph.prebuilt"] = MagicMock()
sys.modules["opentelemetry"] = MagicMock()
sys.modules["opentelemetry.trace"] = MagicMock()
sys.modules["langchain_core"] = MagicMock()
sys.modules["langchain_core.tools"] = MagicMock()
sys.modules["langchain_core.messages"] = MagicMock()
sys.modules["langchain_mcp_adapters"] = MagicMock()
sys.modules["langchain_mcp_adapters.client"] = MagicMock()
sys.modules["langchain_mcp_adapters.tools"] = MagicMock()
sys.modules["jsonschema"] = MagicMock()
sys.modules["jsonschema.exceptions"] = MagicMock()
sys.modules["cryptography"] = MagicMock()
sys.modules["cryptography.fernet"] = MagicMock()
sys.modules["openai"] = MagicMock()
sys.modules["loguru"] = MagicMock()


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
    # Story 1B: JWT and Password Policy Settings
    os.environ.setdefault("AI_AGENTS_JWT_SECRET_KEY", "test-jwt-secret-key-minimum-32-characters-required-for-security")

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
    # This is critical - if it fails, tests cannot run
    config.settings = config.Settings()

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


# ============================================================================
# LLM Cost Dashboard Test Fixtures (Story 8.16)
# ============================================================================


@pytest.fixture
async def async_db_session():
    """
    Provide an async SQLAlchemy database session for unit tests.

    Creates an async database session for testing async services and database operations.
    All changes are rolled back after each test to maintain test isolation.

    Yields:
        AsyncSession: Async database session for test operations

    Note:
        - Uses settings.database_url from config (set in pytest_configure)
        - Automatically rolls back all changes after test completion
        - Creates engine/session within test's event loop to avoid loop conflicts
        - Suitable for unit tests with LiteLLM SpendLogs and other async queries
    """
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from src.config import settings

    # Create engine within the test's event loop
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True
    )

    # Create session factory
    async_session_maker = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    # Create session
    # Create session without context manager to control transaction
    session = async_session_maker()

    try:
        # Start a transaction
        await session.begin()
        yield session
    finally:
        # Always rollback to maintain test isolation
        await session.rollback()
        await session.close()

    # Dispose engine after test
    await engine.dispose()


@pytest.fixture
async def async_client(async_db_session):
    """
    Provide an async FastAPI test client for testing async endpoints.

    Creates an httpx.AsyncClient for making async HTTP requests to the FastAPI app.
    Uses dependency injection to provide the async_db_session to the app.

    Yields:
        httpx.AsyncClient: Async HTTP client for making requests to the app

    Note:
        - Uses the main FastAPI app from src.main
        - Can be used with `await async_client.get()`, `await async_client.post()`, etc.
        - Automatically cleans up after test completion
        - Suitable for testing async API endpoints (Story 8.16 cost API, etc.)
    """
    from httpx import ASGITransport, AsyncClient
    from src.main import app
    from src.database.session import get_async_session

    # Override database dependency to use test session
    async def override_get_async_session():
        yield async_db_session

    app.dependency_overrides[get_async_session] = override_get_async_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Clean up dependency override
    app.dependency_overrides.clear()


@pytest.fixture
def mock_tenant_id():
    """
    Provide a mock tenant ID for testing tenant-scoped operations.

    Returns:
        UUID: A test tenant ID suitable for authorization headers and queries

    Note:
        - Returns a consistent UUID across test for reliable assertions
        - Use in headers like: {"Authorization": f"Bearer {mock_tenant_id}"}
    """
    from uuid import UUID
    return str(UUID("00000000-0000-0000-0000-000000000001"))


# Story 1C: Fixture alias for async_client
@pytest.fixture
async def client(async_client):
    """Alias for async_client fixture for Story 1C auth tests."""
    return async_client


# Story 1C: Fixture alias for async_db_session
@pytest.fixture
async def db_session(async_db_session):
    """Alias for async_db_session fixture for Story 1C auth tests."""
    return async_db_session


# Import all test fixtures for pytest discovery
pytest_plugins = [
    "tests.fixtures.rls_fixtures",
    # "tests.fixtures.auth_fixtures",  # Story 1C: Authentication test fixtures
]
