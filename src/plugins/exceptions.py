"""
Plugin-related exceptions for the AI Agents platform.

Defines custom exceptions for plugin operations:
- PluginNotFoundError: Plugin not registered or doesn't exist
- PluginConnectionError: Plugin connection/communication failures
- PluginConfigurationError: Invalid plugin configuration
"""


class PluginNotFoundError(Exception):
    """
    Raised when requested plugin is not registered in PluginManager.

    Examples:
        - Attempt to get plugin with invalid tool_type
        - Plugin removed but still referenced in database
        - Typo in plugin identifier
    """

    pass


class PluginConnectionError(Exception):
    """
    Raised when plugin fails to connect to external API.

    Examples:
        - API endpoint unreachable (network issue)
        - Authentication failure (invalid credentials)
        - API rate limit exceeded
        - Timeout (response took >30 seconds)
    """

    pass


class PluginConfigurationError(Exception):
    """
    Raised when plugin configuration is invalid or incomplete.

    Examples:
        - Missing required configuration fields
        - Invalid URL format
        - Configuration fails validation rules
        - Encrypted field decryption failure
    """

    pass
