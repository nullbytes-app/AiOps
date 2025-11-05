"""
Unit tests for Plugin Manager and Registry.

Tests cover:
- Singleton pattern enforcement
- Plugin registration with validation
- Plugin retrieval with error handling
- Helper methods (list, is_registered, unregister)
- Plugin discovery from directories
- Error messages and exceptions

Copyright (c) 2025 AI Agents Platform
License: MIT
"""

import pytest
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch
from pathlib import Path

from src.plugins.base import TicketingToolPlugin, TicketMetadata
from src.plugins.registry import (
    PluginManager,
    PluginNotFoundError,
    PluginValidationError,
)


# Mock plugin classes for testing
class MockServiceDeskPlugin(TicketingToolPlugin):
    """Mock ServiceDesk Plus plugin for testing."""

    async def validate_webhook(self, payload: Dict[str, Any], signature: str) -> bool:
        """Mock webhook validation."""
        return True

    async def get_ticket(self, tenant_id: str, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Mock ticket retrieval."""
        return {"id": ticket_id, "tenant": tenant_id, "status": "Open"}

    async def update_ticket(self, tenant_id: str, ticket_id: str, content: str) -> bool:
        """Mock ticket update."""
        return True

    def extract_metadata(self, payload: Dict[str, Any]) -> TicketMetadata:
        """Mock metadata extraction."""
        return TicketMetadata(
            tenant_id="test-tenant",
            ticket_id="DESK-123",
            description="Test ticket",
            priority="high",
            created_at=datetime.now(timezone.utc),
        )


class MockJiraPlugin(TicketingToolPlugin):
    """Mock Jira Service Management plugin for testing."""

    async def validate_webhook(self, payload: Dict[str, Any], signature: str) -> bool:
        """Mock webhook validation."""
        return True

    async def get_ticket(self, tenant_id: str, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Mock ticket retrieval."""
        return {"key": ticket_id, "tenant": tenant_id, "status": "In Progress"}

    async def update_ticket(self, tenant_id: str, ticket_id: str, content: str) -> bool:
        """Mock ticket update."""
        return True

    def extract_metadata(self, payload: Dict[str, Any]) -> TicketMetadata:
        """Mock metadata extraction."""
        return TicketMetadata(
            tenant_id="test-tenant",
            ticket_id="JIRA-456",
            description="Jira test ticket",
            priority="medium",
            created_at=datetime.now(timezone.utc),
        )


class InvalidPlugin:
    """Not a TicketingToolPlugin - used to test validation."""

    def some_method(self) -> str:
        """Random method."""
        return "I'm not a valid plugin"


@pytest.fixture
def plugin_manager():
    """
    Provide fresh PluginManager instance for each test.

    Resets the singleton instance to ensure test isolation.

    Returns:
        PluginManager: Fresh plugin manager instance with empty registry.
    """
    # Reset singleton instance
    PluginManager._instance = None
    manager = PluginManager()
    # Clear any plugins from previous tests
    manager._plugins = {}
    return manager


@pytest.fixture
def mock_servicedesk_plugin():
    """
    Provide MockServiceDeskPlugin instance.

    Returns:
        MockServiceDeskPlugin: Mock plugin for testing registration/retrieval.
    """
    return MockServiceDeskPlugin()


@pytest.fixture
def mock_jira_plugin():
    """
    Provide MockJiraPlugin instance.

    Returns:
        MockJiraPlugin: Mock plugin for testing multi-plugin scenarios.
    """
    return MockJiraPlugin()


class TestPluginManagerSingleton:
    """Test singleton pattern enforcement for PluginManager."""

    def test_plugin_manager_singleton(self, plugin_manager):
        """
        Test PluginManager returns same instance on multiple instantiations.

        Verifies singleton pattern ensures only one registry exists application-wide.
        """
        manager1 = PluginManager()
        manager2 = PluginManager()
        manager3 = PluginManager()

        # All references should point to same instance
        assert manager1 is manager2
        assert manager2 is manager3
        assert id(manager1) == id(manager2) == id(manager3)

    def test_plugin_manager_shared_state(self, plugin_manager, mock_servicedesk_plugin):
        """
        Test plugins registered in one instance are available in another.

        Verifies singleton state is shared across all references.
        """
        manager1 = PluginManager()
        manager1.register_plugin("servicedesk_plus", mock_servicedesk_plugin)

        # New reference should see registered plugin
        manager2 = PluginManager()
        retrieved_plugin = manager2.get_plugin("servicedesk_plus")

        assert retrieved_plugin is mock_servicedesk_plugin
        assert manager1.list_registered_plugins() == manager2.list_registered_plugins()


class TestPluginRegistration:
    """Test plugin registration with validation."""

    def test_register_plugin_success(self, plugin_manager, mock_servicedesk_plugin):
        """
        Test successful plugin registration.

        Verifies plugin is stored in registry and can be listed.
        """
        plugin_manager.register_plugin("servicedesk_plus", mock_servicedesk_plugin)

        assert "servicedesk_plus" in plugin_manager.list_registered_plugins()
        assert plugin_manager.is_plugin_registered("servicedesk_plus")

    def test_register_plugin_invalid_type(self, plugin_manager):
        """
        Test registration rejects non-plugin objects.

        Verifies PluginValidationError raised when registering object
        that doesn't inherit from TicketingToolPlugin.
        """
        invalid_plugin = InvalidPlugin()

        with pytest.raises(PluginValidationError) as exc_info:
            plugin_manager.register_plugin("invalid", invalid_plugin)

        assert "must be an instance of TicketingToolPlugin" in str(exc_info.value)

    def test_register_plugin_empty_tool_type(self, plugin_manager, mock_servicedesk_plugin):
        """
        Test registration rejects empty tool_type.

        Verifies PluginValidationError raised for invalid tool_type.
        """
        with pytest.raises(PluginValidationError) as exc_info:
            plugin_manager.register_plugin("", mock_servicedesk_plugin)

        assert "must be a non-empty string" in str(exc_info.value)

    def test_register_plugin_none_tool_type(self, plugin_manager, mock_servicedesk_plugin):
        """
        Test registration rejects None as tool_type.

        Verifies type validation catches None values.
        """
        with pytest.raises(PluginValidationError) as exc_info:
            plugin_manager.register_plugin(None, mock_servicedesk_plugin)

        assert "must be a non-empty string" in str(exc_info.value)

    def test_register_plugin_dict_fails(self, plugin_manager):
        """
        Test registration rejects dict (common mistake).

        Verifies clear error message when user passes wrong type.
        """
        with pytest.raises(PluginValidationError) as exc_info:
            plugin_manager.register_plugin("test", {"key": "value"})

        assert "TicketingToolPlugin" in str(exc_info.value)

    def test_register_multiple_plugins(
        self, plugin_manager, mock_servicedesk_plugin, mock_jira_plugin
    ):
        """
        Test registering multiple plugins with different tool_types.

        Verifies registry can store multiple plugins independently.
        """
        plugin_manager.register_plugin("servicedesk_plus", mock_servicedesk_plugin)
        plugin_manager.register_plugin("jira", mock_jira_plugin)

        registered = plugin_manager.list_registered_plugins()
        assert len(registered) == 2
        assert "servicedesk_plus" in registered
        assert "jira" in registered


class TestPluginRetrieval:
    """Test plugin retrieval with error handling."""

    def test_get_plugin_success(self, plugin_manager, mock_servicedesk_plugin):
        """
        Test successful plugin retrieval.

        Verifies get_plugin returns same instance that was registered.
        """
        plugin_manager.register_plugin("servicedesk_plus", mock_servicedesk_plugin)

        retrieved_plugin = plugin_manager.get_plugin("servicedesk_plus")

        assert retrieved_plugin is mock_servicedesk_plugin

    def test_get_plugin_not_found(self, plugin_manager):
        """
        Test PluginNotFoundError raised for unregistered tool_type.

        Verifies error message includes list of available plugins for debugging.
        """
        with pytest.raises(PluginNotFoundError) as exc_info:
            plugin_manager.get_plugin("unknown_tool")

        error_message = str(exc_info.value)
        assert "unknown_tool" in error_message
        assert "not registered" in error_message
        assert "Available plugins" in error_message

    def test_get_plugin_error_message_includes_available(
        self, plugin_manager, mock_servicedesk_plugin, mock_jira_plugin
    ):
        """
        Test error message lists available plugins.

        Verifies helpful error message when requesting wrong tool_type.
        """
        plugin_manager.register_plugin("servicedesk_plus", mock_servicedesk_plugin)
        plugin_manager.register_plugin("jira", mock_jira_plugin)

        with pytest.raises(PluginNotFoundError) as exc_info:
            plugin_manager.get_plugin("zendesk")

        error_message = str(exc_info.value)
        assert "servicedesk_plus" in error_message or "jira" in error_message


class TestHelperMethods:
    """Test helper methods for plugin management."""

    def test_list_registered_plugins_empty(self, plugin_manager):
        """
        Test list_registered_plugins returns empty list initially.

        Verifies fresh manager starts with no plugins.
        """
        registered = plugin_manager.list_registered_plugins()
        assert registered == []

    def test_list_registered_plugins(
        self, plugin_manager, mock_servicedesk_plugin, mock_jira_plugin
    ):
        """
        Test list_registered_plugins returns all tool_types.

        Verifies all registered plugins are listed.
        """
        plugin_manager.register_plugin("servicedesk_plus", mock_servicedesk_plugin)
        plugin_manager.register_plugin("jira", mock_jira_plugin)
        plugin_manager.register_plugin("zendesk", mock_servicedesk_plugin)  # Reuse mock

        registered = plugin_manager.list_registered_plugins()
        assert len(registered) == 3
        assert "servicedesk_plus" in registered
        assert "jira" in registered
        assert "zendesk" in registered

    def test_is_plugin_registered_true(self, plugin_manager, mock_servicedesk_plugin):
        """
        Test is_plugin_registered returns True for registered plugin.

        Verifies check method accurately detects registered plugins.
        """
        plugin_manager.register_plugin("servicedesk_plus", mock_servicedesk_plugin)

        assert plugin_manager.is_plugin_registered("servicedesk_plus") is True

    def test_is_plugin_registered_false(self, plugin_manager):
        """
        Test is_plugin_registered returns False for unregistered plugin.

        Verifies check method returns False instead of raising exception.
        """
        assert plugin_manager.is_plugin_registered("unknown_tool") is False

    def test_unregister_plugin_success(self, plugin_manager, mock_servicedesk_plugin):
        """
        Test successful plugin unregistration.

        Verifies plugin is removed from registry and no longer accessible.
        """
        plugin_manager.register_plugin("servicedesk_plus", mock_servicedesk_plugin)
        assert plugin_manager.is_plugin_registered("servicedesk_plus")

        plugin_manager.unregister_plugin("servicedesk_plus")

        assert not plugin_manager.is_plugin_registered("servicedesk_plus")
        assert "servicedesk_plus" not in plugin_manager.list_registered_plugins()

    def test_unregister_plugin_not_found(self, plugin_manager):
        """
        Test unregister raises PluginNotFoundError for unregistered plugin.

        Verifies cannot unregister plugin that doesn't exist.
        """
        with pytest.raises(PluginNotFoundError) as exc_info:
            plugin_manager.unregister_plugin("unknown_tool")

        assert "Cannot unregister" in str(exc_info.value)
        assert "unknown_tool" in str(exc_info.value)

    def test_unregister_and_reregister(self, plugin_manager, mock_servicedesk_plugin):
        """
        Test plugin can be re-registered after unregistration.

        Verifies hot-reload scenario works correctly.
        """
        plugin_manager.register_plugin("servicedesk_plus", mock_servicedesk_plugin)
        plugin_manager.unregister_plugin("servicedesk_plus")

        # Re-register same plugin
        plugin_manager.register_plugin("servicedesk_plus", mock_servicedesk_plugin)

        assert plugin_manager.is_plugin_registered("servicedesk_plus")
        retrieved = plugin_manager.get_plugin("servicedesk_plus")
        assert retrieved is mock_servicedesk_plugin


class TestPluginDiscovery:
    """Test automatic plugin discovery from directories."""

    @patch("src.plugins.registry.Path")
    @patch("src.plugins.registry.importlib.import_module")
    def test_discover_plugins_no_directories(self, mock_import, mock_path, plugin_manager):
        """
        Test discover_plugins handles empty plugins directory.

        Verifies discovery doesn't crash when no plugin directories exist.
        """
        # Mock Path to return empty list
        mock_plugins_dir = MagicMock()
        mock_plugins_dir.iterdir.return_value = []
        mock_path.return_value.parent = mock_plugins_dir

        plugin_manager.discover_plugins()

        # Should complete without errors, no plugins registered
        assert len(plugin_manager.list_registered_plugins()) == 0

    def test_discover_plugins_skips_non_directories(self, plugin_manager):
        """
        Test discovery skips files in plugins directory.

        Verifies only subdirectories are scanned for plugins.
        """
        with patch("src.plugins.registry.Path") as mock_path:
            mock_file = MagicMock()
            mock_file.is_dir.return_value = False
            mock_file.name = "base.py"

            mock_plugins_dir = MagicMock()
            mock_plugins_dir.iterdir.return_value = [mock_file]
            mock_path.return_value.parent = mock_plugins_dir

            plugin_manager.discover_plugins()

            # No plugins should be registered
            assert len(plugin_manager.list_registered_plugins()) == 0

    def test_discover_plugins_skips_underscore_directories(self, plugin_manager):
        """
        Test discovery skips directories starting with underscore.

        Verifies __pycache__ and similar directories are ignored.
        """
        with patch("src.plugins.registry.Path") as mock_path:
            mock_dir = MagicMock()
            mock_dir.is_dir.return_value = True
            mock_dir.name = "__pycache__"

            mock_plugins_dir = MagicMock()
            mock_plugins_dir.iterdir.return_value = [mock_dir]
            mock_path.return_value.parent = mock_plugins_dir

            plugin_manager.discover_plugins()

            # No plugins should be registered
            assert len(plugin_manager.list_registered_plugins()) == 0

    def test_load_plugins_on_startup(self, plugin_manager):
        """
        Test load_plugins_on_startup calls discover_plugins.

        Verifies convenience method works as expected.
        """
        with patch.object(plugin_manager, "discover_plugins") as mock_discover:
            plugin_manager.load_plugins_on_startup()
            mock_discover.assert_called_once()
