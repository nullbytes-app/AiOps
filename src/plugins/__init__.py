"""
Plugin Package for Ticketing Tool Integrations.

This package provides the plugin architecture for supporting multiple ticketing tools
(ServiceDesk Plus, Jira Service Management, Zendesk, etc.) through a standardized
interface. The TicketingToolPlugin abstract base class defines the contract that all
plugins must implement.

Exports:
    TicketingToolPlugin: Abstract base class for ticketing tool plugins.
    TicketMetadata: Standardized dataclass for ticket metadata.
    PluginManager: Singleton registry for managing plugin instances.
    PluginNotFoundError: Exception raised when plugin not registered.
    PluginValidationError: Exception raised when plugin validation fails.

Usage:
    # Import plugin interface
    from src.plugins import TicketingToolPlugin, TicketMetadata

    # Create plugin implementation
    class MyPlugin(TicketingToolPlugin):
        # Implement abstract methods
        ...

    # Register and retrieve plugins
    from src.plugins import PluginManager

    manager = PluginManager()
    manager.register_plugin("my_tool", MyPlugin())
    plugin = manager.get_plugin("my_tool")

See Also:
    - docs/plugin-architecture.md for comprehensive implementation guide
    - src/plugins/base.py for interface definitions
    - src/plugins/registry.py for plugin manager implementation
"""

from src.plugins.base import TicketingToolPlugin, TicketMetadata
from src.plugins.registry import (
    PluginManager,
    PluginNotFoundError,
    PluginValidationError,
)

__all__ = [
    "TicketingToolPlugin",
    "TicketMetadata",
    "PluginManager",
    "PluginNotFoundError",
    "PluginValidationError",
]
