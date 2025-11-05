"""
Plugin management API (Story 7.8) - Compatibility Shim.

This file re-exports the refactored plugin API components to maintain
backward compatibility with existing imports. All functionality has been
split into focused modules:

- plugins_schemas.py: Pydantic models and response schemas
- plugins_helpers.py: Metadata extraction and schema generation
- plugins_routes.py: FastAPI router and endpoint implementations

Import from this file for backward compatibility, or directly from the
specific modules for better clarity.

Refactored: 2025-11-05 (Code Review Follow-up - Story 7.8)
File size constraint: Original 578 lines → 3 modules (71 + 137 + 156 + 341 lines)
"""

# Re-export all schemas for backward compatibility
from src.api.plugins_schemas import (
    ConfigFieldSchema,
    ConnectionTestRequest,
    ConnectionTestResponse,
    PluginConfigSchema,
    PluginDetailsResponse,
    PluginListResponse,
    PluginMetadata,
)

# Re-export helper functions for backward compatibility
from src.api.plugins_helpers import (
    get_plugin_config_schema,
    get_plugin_metadata,
)

# Re-export router for backward compatibility
from src.api.plugins_routes import router, log_audit

__all__ = [
    # Schemas
    "PluginMetadata",
    "PluginListResponse",
    "ConfigFieldSchema",
    "PluginConfigSchema",
    "PluginDetailsResponse",
    "ConnectionTestRequest",
    "ConnectionTestResponse",
    # Helpers
    "get_plugin_metadata",
    "get_plugin_config_schema",
    # Routes
    "router",
    "log_audit",
]
