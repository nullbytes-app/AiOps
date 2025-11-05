"""
ServiceDesk Plus Plugin Module.

This module implements the TicketingToolPlugin interface for ManageEngine ServiceDesk Plus
integration. Provides webhook validation, ticket retrieval, and ticket update capabilities
following the plugin architecture established in Stories 7.1 and 7.2.

Main Components:
    - ServiceDeskPlusPlugin: Plugin class implementing TicketingToolPlugin ABC
    - ServiceDeskAPIClient: HTTP client for ServiceDesk Plus REST API
    - webhook_validator: Helper functions for HMAC-SHA256 signature validation

Usage:
    from src.plugins.servicedesk_plus import ServiceDeskPlusPlugin
    from src.plugins import PluginManager

    # Register plugin on application startup
    manager = PluginManager()
    plugin = ServiceDeskPlusPlugin()
    manager.register_plugin("servicedesk_plus", plugin)

See Also:
    - docs/plugin-architecture.md for comprehensive implementation guide
    - Story 7.3 for migration from monolithic to plugin architecture
"""

from src.plugins.servicedesk_plus.plugin import ServiceDeskPlusPlugin

__all__ = ["ServiceDeskPlusPlugin"]
