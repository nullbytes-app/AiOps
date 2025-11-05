"""
Plugin management API endpoints (Story 7.8).

REST API for retrieving registered plugins, plugin configuration schemas,
and testing plugin connections. Enables Streamlit admin UI to manage plugins
without database access.
"""

import asyncio
import time
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status

from src.api.plugins_helpers import get_plugin_config_schema, get_plugin_metadata
from src.api.plugins_schemas import (
    ConnectionTestRequest,
    ConnectionTestResponse,
    PluginDetailsResponse,
    PluginListResponse,
)
from src.plugins.exceptions import PluginNotFoundError
from src.plugins.registry import PluginManager
from src.utils.logger import logger

router = APIRouter(prefix="/api/v1/plugins", tags=["plugins"])


async def log_audit(
    operation: str, details: Dict[str, Any], status: str, user: str = "system"
) -> None:
    """
    Log plugin management operation to audit log.

    Creates audit trail for compliance and troubleshooting. All plugin
    operations (configuration changes, connection tests, tenant assignments)
    are logged with timestamp, user, operation name, and details.

    Args:
        operation: Operation name (e.g., "plugin_connection_test")
        details: Operation-specific details as dict (JSON serializable)
        status: Operation status ("success", "failure")
        user: Username or identifier (default: "system" for API calls)

    Returns:
        None (logs error but doesn't raise exception if logging fails)

    Example:
        await log_audit(
            operation="plugin_connection_test",
            details={"plugin_id": "jira", "test_duration_ms": 234},
            status="success",
            user="admin@example.com"
        )
    """
    try:
        from datetime import datetime, timezone

        from src.database.models import AuditLog
        from src.database.session import async_session_maker

        async with async_session_maker() as session:
            log_entry = AuditLog(
                timestamp=datetime.now(timezone.utc),
                user=user,
                operation=operation,
                details=details,
                status=status,
            )
            session.add(log_entry)
            await session.commit()

            logger.info(f"Audit log created: {operation} by {user} ({status})")

    except Exception as e:
        logger.error(f"Failed to create audit log entry: {e}")
        # Don't block operation if logging fails


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="List registered plugins",
    description="Returns list of all registered plugins with metadata (name, type, version, status, description). "
    "Used by Streamlit admin UI to display available plugins for tenant assignment.",
    response_model=PluginListResponse,
)
async def list_plugins() -> PluginListResponse:
    """
    Retrieve list of all registered plugins.

    Queries PluginManager singleton for registered tool_types and extracts
    metadata from each plugin instance. Returns plugin list suitable for
    display in Streamlit dataframe (AC #4).

    Returns:
        PluginListResponse: List of plugins with metadata and count

    Raises:
        HTTPException(500): If PluginManager access fails

    Example:
        Response (200 OK):
        {
            "plugins": [
                {
                    "plugin_id": "servicedesk_plus",
                    "name": "ServiceDesk Plus",
                    "version": "1.0.0",
                    "status": "active",
                    "description": "ManageEngine ServiceDesk Plus plugin",
                    "tool_type": "servicedesk_plus"
                },
                {
                    "plugin_id": "jira",
                    "name": "Jira Service Management",
                    "version": "1.0.0",
                    "status": "active",
                    "description": "Atlassian Jira Service Management plugin",
                    "tool_type": "jira"
                }
            ],
            "count": 2
        }
    """
    try:
        manager = PluginManager()
        registered_plugins = manager.list_registered_plugins()

        plugins_metadata = []
        for plugin_id in registered_plugins:
            try:
                plugin = manager.get_plugin(plugin_id)
                metadata = get_plugin_metadata(plugin_id, plugin)
                plugins_metadata.append(metadata)
            except PluginNotFoundError:
                logger.warning(f"Plugin '{plugin_id}' listed but not retrievable")
                continue

        logger.info(
            f"Retrieved {len(plugins_metadata)} registered plugins: {registered_plugins}"
        )

        return PluginListResponse(plugins=plugins_metadata, count=len(plugins_metadata))

    except Exception as e:
        logger.error(f"Error listing plugins: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve plugin list: {str(e)}",
        )


@router.get(
    "/{plugin_id}",
    status_code=status.HTTP_200_OK,
    summary="Get plugin details and configuration schema",
    description="Returns full plugin details including configuration schema (JSON Schema format). "
    "Used by Streamlit admin UI to dynamically generate configuration forms (AC #5).",
    response_model=PluginDetailsResponse,
)
async def get_plugin_details(plugin_id: str) -> PluginDetailsResponse:
    """
    Retrieve detailed plugin information and configuration schema.

    Returns plugin metadata plus JSON Schema representation of configuration
    fields. Schema includes field types, validation rules (required, min/max,
    pattern), and descriptions for dynamic form generation.

    Args:
        plugin_id: Plugin identifier (tool_type, e.g., "servicedesk_plus", "jira")

    Returns:
        PluginDetailsResponse: Plugin details with configuration schema

    Raises:
        HTTPException(404): If plugin_id not registered
        HTTPException(500): If schema extraction fails

    Example:
        Path: /api/v1/plugins/jira

        Response (200 OK):
        {
            "plugin_id": "jira",
            "name": "Jira Service Management",
            "version": "1.0.0",
            "description": "Atlassian Jira Service Management plugin",
            "tool_type": "jira",
            "config_schema": {
                "plugin_id": "jira",
                "schema_fields": [
                    {
                        "field_name": "jira_url",
                        "field_type": "string",
                        "required": true,
                        "description": "Jira instance URL",
                        "pattern": "^https?://.*\\.atlassian\\.net.*"
                    },
                    {
                        "field_name": "jira_api_token",
                        "field_type": "string",
                        "required": true,
                        "description": "Jira API token (encrypted)",
                        "min_length": 20
                    }
                ]
            }
        }
    """
    try:
        manager = PluginManager()

        # Check if plugin registered
        if not manager.is_plugin_registered(plugin_id):
            available = manager.list_registered_plugins()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plugin '{plugin_id}' not found. Available plugins: {available}",
            )

        # Retrieve plugin instance
        plugin = manager.get_plugin(plugin_id)

        # Extract metadata and schema
        metadata = get_plugin_metadata(plugin_id, plugin)
        config_schema = get_plugin_config_schema(plugin_id, plugin)

        logger.info(f"Retrieved details for plugin: {plugin_id}")

        return PluginDetailsResponse(
            plugin_id=metadata.plugin_id,
            name=metadata.name,
            version=metadata.version,
            description=metadata.description,
            tool_type=metadata.tool_type,
            config_schema=config_schema,
        )

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error retrieving plugin details: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve plugin details: {str(e)}",
        )


@router.post(
    "/{plugin_id}/test",
    status_code=status.HTTP_200_OK,
    summary="Test plugin connection",
    description="Validates plugin configuration by testing connection to ticketing tool API. "
    "Calls plugin.test_connection() method with provided config. Timeout: 30 seconds (AC #6).",
    response_model=ConnectionTestResponse,
)
async def test_plugin_connection(
    plugin_id: str, request: ConnectionTestRequest
) -> ConnectionTestResponse:
    """
    Test plugin connection with provided configuration.

    Validates that plugin can successfully connect to ticketing tool API
    using provided credentials. Useful for verifying configuration before
    saving to database. Maximum execution time: 30 seconds.

    Args:
        plugin_id: Plugin identifier (tool_type)
        request: Configuration to test (API URL, tokens, keys)

    Returns:
        ConnectionTestResponse: Success/failure status with message

    Raises:
        HTTPException(404): If plugin_id not registered
        HTTPException(408): If connection test times out (>30s)
        HTTPException(500): If test execution fails

    Example:
        Path: POST /api/v1/plugins/servicedesk_plus/test

        Request body:
        {
            "config": {
                "servicedesk_url": "https://sdp.example.com",
                "api_key": "test-key-12345",
                "technician_key": "tech-key-67890"
            }
        }

        Response (200 OK) - Success:
        {
            "success": true,
            "message": "Connection successful",
            "details": {
                "response_time_ms": 234,
                "api_version": "v3"
            }
        }

        Response (200 OK) - Failure:
        {
            "success": false,
            "message": "Authentication failed: Invalid API key",
            "details": {
                "error_code": "401"
            }
        }
    """
    try:
        manager = PluginManager()

        # Check if plugin registered
        if not manager.is_plugin_registered(plugin_id):
            available = manager.list_registered_plugins()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plugin '{plugin_id}' not found. Available plugins: {available}",
            )

        # Retrieve plugin instance
        plugin = manager.get_plugin(plugin_id)

        # Test connection (with 30s timeout)
        start_time = time.time()
        try:
            success, message = await asyncio.wait_for(
                plugin.test_connection(request.config), timeout=30.0
            )
            duration_ms = int((time.time() - start_time) * 1000)

            # AC#8: Log connection test to audit log
            await log_audit(
                operation="plugin_connection_test",
                details={
                    "plugin_id": plugin_id,
                    "success": success,
                    "duration_ms": duration_ms,
                    "message": message,
                },
                status="success" if success else "failure",
                user="admin",  # TODO: Get from auth context when auth is implemented
            )

            logger.info(
                f"Connection test for '{plugin_id}': success={success}, message={message}"
            )

            return ConnectionTestResponse(success=success, message=message)

        except asyncio.TimeoutError:
            # AC#8: Log timeout to audit log
            await log_audit(
                operation="plugin_connection_test",
                details={
                    "plugin_id": plugin_id,
                    "error": "timeout",
                    "timeout_seconds": 30,
                },
                status="failure",
                user="admin",
            )

            logger.warning(f"Connection test timed out for plugin: {plugin_id}")
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail="Connection test timed out (30 second limit exceeded)",
            )

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except AttributeError as e:
        # test_connection() method not implemented yet
        logger.error(f"test_connection() not implemented for {plugin_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"Plugin '{plugin_id}' does not implement test_connection() method",
        )
    except Exception as e:
        # AC#8: Log unexpected error to audit log
        await log_audit(
            operation="plugin_connection_test",
            details={"plugin_id": plugin_id, "error": str(e)},
            status="failure",
            user="admin",
        )

        logger.error(f"Error testing plugin connection: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test plugin connection: {str(e)}",
        )
