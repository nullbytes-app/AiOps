"""
Plugin Manager and Registry for Ticketing Tool Plugins.

This module provides a centralized registry for managing ticketing tool plugins,
enabling dynamic plugin loading, validation, and routing based on tenant configuration.
The PluginManager follows the singleton pattern to ensure a single registry instance
across the application.

Key Features:
- Singleton pattern for consistent plugin availability
- Type-safe plugin registration with runtime validation
- Dynamic plugin discovery from src/plugins/*/ directories
- Clear error messages for debugging
- Logging support via Loguru

Usage:
    # Get singleton instance
    manager = PluginManager()

    # Register plugin programmatically
    plugin = ServiceDeskPlusPlugin()
    manager.register_plugin("servicedesk_plus", plugin)

    # Retrieve plugin by tool_type
    plugin = manager.get_plugin("servicedesk_plus")

    # Auto-discover and load plugins at startup
    manager.load_plugins_on_startup()

Copyright (c) 2025 AI Agents Platform
License: MIT
"""

import importlib
import inspect
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Type

from loguru import logger

if TYPE_CHECKING:
    # Static imports for mypy type checking (not executed at runtime)
    from src.plugins.base import TicketingToolPlugin
else:
    # Runtime imports
    from src.plugins.base import TicketingToolPlugin


class PluginNotFoundError(Exception):
    """
    Raised when attempting to retrieve a plugin that is not registered.

    This exception includes a list of available plugins in the error message
    to assist with debugging configuration issues.

    Example:
        try:
            plugin = manager.get_plugin("unknown_tool")
        except PluginNotFoundError as e:
            logger.error(f"Plugin error: {e}")
            # Error message: "Plugin for tool_type 'unknown_tool' not registered.
            #                 Available plugins: ['servicedesk_plus', 'jira']"
    """

    pass


class PluginValidationError(Exception):
    """
    Raised when a plugin fails validation during registration.

    Validation ensures:
    - Plugin is an instance of TicketingToolPlugin
    - All abstract methods are implemented
    - tool_type is a non-empty string

    Example:
        try:
            manager.register_plugin("test", invalid_plugin)
        except PluginValidationError as e:
            logger.error(f"Validation failed: {e}")
    """

    pass


class PluginManager:
    """
    Singleton registry for managing ticketing tool plugins.

    The PluginManager provides centralized storage and retrieval of plugin instances,
    enabling dynamic routing based on tenant configuration. It follows the singleton
    pattern to ensure all parts of the application access the same plugin registry.

    Attributes:
        _instance (PluginManager): Singleton instance (class variable).
        _plugins (Dict[str, TicketingToolPlugin]): Internal registry mapping
            tool_type to plugin instances.

    Design Pattern:
        Singleton using __new__ method ensures only one PluginManager instance
        exists application-wide. This prevents inconsistent plugin availability
        across different modules.

    Example:
        # Both references point to same instance
        manager1 = PluginManager()
        manager2 = PluginManager()
        assert manager1 is manager2  # True

    Thread Safety:
        Not required - Python GIL provides protection, and FastAPI/Celery workers
        run in separate processes with isolated PluginManager instances.
    """

    _instance: Optional["PluginManager"] = None
    _plugins: Dict[str, TicketingToolPlugin]

    def __new__(cls) -> "PluginManager":
        """
        Enforce singleton pattern by returning existing instance or creating new one.

        Returns:
            PluginManager: The singleton PluginManager instance.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._plugins = {}
            logger.debug("PluginManager singleton instance created")
        return cls._instance

    def register_plugin(self, tool_type: str, plugin: TicketingToolPlugin) -> None:
        """
        Register a plugin instance for a specific tool_type.

        Validates that:
        1. tool_type is a non-empty string
        2. plugin is an instance of TicketingToolPlugin
        3. All abstract methods are implemented (enforced by ABC)

        Args:
            tool_type (str): Unique identifier for the ticketing tool
                (e.g., "servicedesk_plus", "jira").
            plugin (TicketingToolPlugin): Plugin instance implementing the
                TicketingToolPlugin interface.

        Raises:
            PluginValidationError: If validation fails (invalid tool_type,
                plugin not instance of TicketingToolPlugin, or missing
                abstract method implementations).

        Example:
            manager = PluginManager()
            plugin = ServiceDeskPlusPlugin()
            manager.register_plugin("servicedesk_plus", plugin)
            logger.info("ServiceDesk Plus plugin registered successfully")
        """
        # Validate tool_type
        if not tool_type or not isinstance(tool_type, str):
            raise PluginValidationError(
                f"tool_type must be a non-empty string, got: {type(tool_type).__name__}"
            )

        # Validate plugin is instance of TicketingToolPlugin
        if not isinstance(plugin, TicketingToolPlugin):
            raise PluginValidationError(
                f"Plugin '{plugin.__class__.__name__}' must be an instance of "
                f"TicketingToolPlugin, got: {type(plugin).__name__}"
            )

        # ABC automatically validates all abstract methods are implemented
        # If not implemented, TypeError would have been raised during instantiation

        # Store plugin in registry
        self._plugins[tool_type] = plugin
        logger.info(
            f"Plugin registered: tool_type='{tool_type}', " f"class={plugin.__class__.__name__}"
        )

    def get_plugin(self, tool_type: str) -> TicketingToolPlugin:
        """
        Retrieve a registered plugin by tool_type.

        Args:
            tool_type (str): The tool_type identifier used during registration.

        Returns:
            TicketingToolPlugin: The registered plugin instance.

        Raises:
            PluginNotFoundError: If no plugin is registered for the given tool_type.
                Error message includes list of available plugins for debugging.

        Example:
            manager = PluginManager()
            plugin = manager.get_plugin("servicedesk_plus")
            metadata = plugin.extract_metadata(webhook_payload)
        """
        logger.debug(f"Attempting to retrieve plugin for tool_type='{tool_type}'")

        if tool_type not in self._plugins:
            available = list(self._plugins.keys())
            raise PluginNotFoundError(
                f"Plugin for tool_type '{tool_type}' not registered. "
                f"Available plugins: {available}"
            )

        plugin = self._plugins[tool_type]
        logger.debug(
            f"Plugin retrieved: tool_type='{tool_type}', " f"class={plugin.__class__.__name__}"
        )
        return plugin

    def list_registered_plugins(self) -> List[str]:
        """
        Return list of all registered tool_types.

        Returns:
            List[str]: List of tool_type strings for all registered plugins.

        Example:
            manager = PluginManager()
            plugins = manager.list_registered_plugins()
            print(f"Available plugins: {plugins}")
            # Output: Available plugins: ['servicedesk_plus', 'jira']
        """
        return list(self._plugins.keys())

    def is_plugin_registered(self, tool_type: str) -> bool:
        """
        Check if a plugin is registered for the given tool_type.

        Args:
            tool_type (str): The tool_type to check.

        Returns:
            bool: True if plugin registered, False otherwise.

        Example:
            manager = PluginManager()
            if manager.is_plugin_registered("jira"):
                plugin = manager.get_plugin("jira")
            else:
                logger.warning("Jira plugin not available")
        """
        return tool_type in self._plugins

    def unregister_plugin(self, tool_type: str) -> None:
        """
        Remove a plugin from the registry.

        Primarily used for testing or hot-reload scenarios. In production,
        plugins are typically registered once at startup.

        Args:
            tool_type (str): The tool_type to unregister.

        Raises:
            PluginNotFoundError: If tool_type not registered.

        Example:
            manager = PluginManager()
            manager.unregister_plugin("test_plugin")
            # Plugin can now be re-registered with updated implementation
        """
        if tool_type not in self._plugins:
            raise PluginNotFoundError(
                f"Cannot unregister: Plugin '{tool_type}' not found in registry"
            )

        del self._plugins[tool_type]
        logger.info(f"Plugin unregistered: tool_type='{tool_type}'")

    def discover_plugins(self) -> None:
        """
        Automatically discover and register plugins from src/plugins/*/ directories.

        Discovery Process:
        1. Scan src/plugins/*/ for subdirectories (e.g., src/plugins/servicedesk_plus/)
        2. Look for plugin.py file in each subdirectory
        3. Dynamically import the module using importlib
        4. Inspect module for classes inheriting from TicketingToolPlugin
        5. Instantiate discovered plugin classes
        6. Auto-register using directory name as tool_type (or __tool_type__ attribute)
        7. Log warnings for import failures but continue discovery

        Directory Structure Convention:
            src/plugins/
            ├── servicedesk_plus/
            │   └── plugin.py  # Contains ServiceDeskPlusPlugin class
            └── jira/
                └── plugin.py  # Contains JiraPlugin class

        Error Handling:
            Non-fatal - import errors are logged as warnings but don't stop discovery
            of other plugins. This prevents one broken plugin from breaking the entire
            application.

        Example:
            manager = PluginManager()
            manager.discover_plugins()
            logger.info(f"Discovered plugins: {manager.list_registered_plugins()}")
        """
        plugins_dir = Path(__file__).parent
        logger.info(f"Starting plugin discovery in: {plugins_dir}")

        # Scan for plugin directories
        for plugin_path in plugins_dir.iterdir():
            # Skip non-directories and special files
            if not plugin_path.is_dir() or plugin_path.name.startswith("_"):
                continue

            plugin_module_path = plugin_path / "plugin.py"
            if not plugin_module_path.exists():
                logger.debug(f"Skipping {plugin_path.name}: no plugin.py found")
                continue

            # Attempt to import plugin module
            module_name = f"src.plugins.{plugin_path.name}.plugin"
            try:
                logger.debug(f"Importing plugin module: {module_name}")
                module = importlib.import_module(module_name)

                # Discover plugin classes in module
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    # Check if class inherits from TicketingToolPlugin
                    if issubclass(obj, TicketingToolPlugin) and obj is not TicketingToolPlugin:
                        try:
                            # Instantiate plugin
                            plugin_instance = obj()

                            # Determine tool_type (use __tool_type__ or directory name)
                            tool_type = getattr(obj, "__tool_type__", plugin_path.name)

                            # Register plugin
                            self.register_plugin(tool_type, plugin_instance)
                            logger.info(
                                f"Auto-discovered and registered: {name} " f"as '{tool_type}'"
                            )
                        except Exception as e:
                            logger.warning(
                                f"Failed to instantiate plugin {name} from " f"{module_name}: {e}"
                            )
            except Exception as e:
                logger.warning(f"Failed to import plugin from {module_name}: {e}. Skipping.")
                continue

    def load_plugins_on_startup(self) -> None:
        """
        Convenience method to load plugins at application startup.

        This method calls discover_plugins() and logs summary of loaded plugins.
        Intended to be called from main.py or celery_app.py startup hooks.

        Example:
            # In main.py
            from src.plugins import PluginManager

            @app.on_event("startup")
            async def startup_event():
                manager = PluginManager()
                manager.load_plugins_on_startup()
        """
        logger.info("Loading plugins on application startup...")
        self.discover_plugins()
        registered = self.list_registered_plugins()
        logger.info(
            f"Plugin loading complete. Registered plugins: {registered} "
            f"(count: {len(registered)})"
        )
