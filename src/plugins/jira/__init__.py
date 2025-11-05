"""
Jira Service Management Plugin

This module provides a Jira Service Management plugin implementation for the
AI-powered ticket enhancement platform. It enables MSPs using Jira to benefit
from automated ticket enhancement capabilities.

The plugin implements the TicketingToolPlugin interface and provides:
- Webhook signature validation using HMAC-SHA256
- Ticket retrieval via Jira REST API v3
- Ticket updates via comment posting in Atlassian Document Format (ADF)
- Metadata extraction from Jira webhook payloads

Example:
    >>> from src.plugins.jira import JiraServiceManagementPlugin
    >>> plugin = JiraServiceManagementPlugin()
    >>> manager.register_plugin("jira", plugin)
"""

from src.plugins.jira.plugin import JiraServiceManagementPlugin

__all__ = ["JiraServiceManagementPlugin"]
