"""
Unit test configuration and fixtures.

Story 7.3: Ensures ServiceDesk Plus plugin is registered for all unit tests
to maintain backward compatibility with existing webhook endpoint tests.
"""

import pytest


@pytest.fixture(scope="session", autouse=True)
def register_servicedesk_plugin():
    """
    Register ServiceDesk Plus plugin for all unit tests.

    Story 7.3: Required for webhook endpoint tests to work with Plugin Manager.
    Runs once per test session before any tests execute (autouse=True).

    This fixture ensures backward compatibility with existing tests by:
    1. Registering the ServiceDesk Plus plugin in PluginManager singleton
    2. Making the plugin available to all webhook endpoint tests
    3. Avoiding need to modify existing test files (maintains AC6)
    """
    from src.plugins import PluginManager
    from src.plugins.servicedesk_plus import ServiceDeskPlusPlugin

    # Get PluginManager singleton and register ServiceDesk Plus plugin
    manager = PluginManager()
    plugin = ServiceDeskPlusPlugin()

    # Register with tool_type 'servicedesk_plus' (matches default in webhook endpoint)
    manager.register_plugin("servicedesk_plus", plugin)

    # Yield control to tests
    yield

    # Cleanup note: PluginManager singleton persists across test session
    # Registry clearing not needed as each test session starts fresh
