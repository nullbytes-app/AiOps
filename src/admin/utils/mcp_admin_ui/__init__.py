"""
MCP Admin UI Helper Modules

Extracted from 12_MCP_Servers.py for maintainability (Story 12.7).
Provides focused, testable components for MCP server management UI:

- list_display: Server list view with tenant selector and action buttons
- form_renderers: Add/edit server forms for stdio and HTTP+SSE transports
- detail_view: Detailed server view with capabilities and metrics

Each module handles a specific UI concern with clear boundaries.

References:
- Story 12.7: File Size Refactoring and Code Quality
- Story 11.1.9: Admin UI for MCP Server Management
- Story 11.2.4: Enhanced MCP Health Monitoring

Usage:
    from src.admin.utils.mcp_admin_ui import (
        render_server_list,
        render_server_form,
        render_server_details,
    )
"""

from .detail_view import render_server_details
from .form_renderers import render_server_form
from .list_display import render_server_list

__all__ = [
    "render_server_list",
    "render_server_form",
    "render_server_details",
]
