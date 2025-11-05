"""
Helper functions for plugin management API (Story 7.8).

Utility functions for extracting plugin metadata and generating configuration
schemas. Supports dynamic plugin discovery and schema introspection.
"""

from typing import List

from src.api.plugins_schemas import (
    ConfigFieldSchema,
    PluginConfigSchema,
    PluginMetadata,
)
from src.plugins.base import TicketingToolPlugin


def get_plugin_metadata(plugin_id: str, plugin: TicketingToolPlugin) -> PluginMetadata:
    """
    Extract metadata from plugin instance.

    Args:
        plugin_id: Plugin identifier (tool_type)
        plugin: Plugin instance

    Returns:
        PluginMetadata: Structured plugin metadata
    """
    # Get plugin attributes (with fallbacks)
    name = getattr(plugin, "name", plugin_id.replace("_", " ").title())
    version = getattr(plugin, "version", "1.0.0")
    description = getattr(plugin, "description", f"{name} ticketing tool plugin")
    status = "active"  # Future: Could check plugin health

    return PluginMetadata(
        plugin_id=plugin_id,
        name=name,
        version=version,
        status=status,
        description=description,
        tool_type=plugin_id,
    )


def get_plugin_config_schema(
    plugin_id: str, plugin: TicketingToolPlugin
) -> PluginConfigSchema:
    """
    Extract configuration schema from plugin instance.

    Args:
        plugin_id: Plugin identifier
        plugin: Plugin instance

    Returns:
        PluginConfigSchema: JSON Schema representation of plugin configuration

    Note:
        This is a simplified schema extraction. Production implementation
        would use plugin.__config_schema__ attribute or introspection.
    """
    # Default schema based on common ticketing tool configurations
    # Future enhancement: Plugins should define their own schema via __config_schema__
    schema_fields: List[ConfigFieldSchema] = []

    if plugin_id == "servicedesk_plus":
        schema_fields = [
            ConfigFieldSchema(
                field_name="servicedesk_url",
                field_type="string",
                required=True,
                description="ServiceDesk Plus API base URL",
                pattern=r"^https?://.*",
            ),
            ConfigFieldSchema(
                field_name="api_key",
                field_type="string",
                required=True,
                description="ServiceDesk Plus API key",
                min_length=20,
            ),
            ConfigFieldSchema(
                field_name="technician_key",
                field_type="string",
                required=True,
                description="Technician key for authentication",
                min_length=20,
            ),
        ]
    elif plugin_id == "jira":
        schema_fields = [
            ConfigFieldSchema(
                field_name="jira_url",
                field_type="string",
                required=True,
                description="Jira instance URL",
                pattern=r"^https?://.*\.atlassian\.net.*",
            ),
            ConfigFieldSchema(
                field_name="jira_api_token",
                field_type="string",
                required=True,
                description="Jira API token (encrypted)",
                min_length=20,
            ),
            ConfigFieldSchema(
                field_name="jira_project_key",
                field_type="string",
                required=True,
                description="Jira project key (e.g., PROJ)",
                pattern=r"^[A-Z][A-Z0-9]+$",
                max_length=10,
            ),
        ]
    else:
        # Generic schema for unknown plugins
        schema_fields = [
            ConfigFieldSchema(
                field_name="api_url",
                field_type="string",
                required=True,
                description="API base URL",
            ),
            ConfigFieldSchema(
                field_name="api_token",
                field_type="string",
                required=True,
                description="API authentication token",
            ),
        ]

    return PluginConfigSchema(plugin_id=plugin_id, schema_fields=schema_fields)
