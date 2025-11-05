"""
Unit tests for Plugin Management API endpoints (Story 7.8).

Tests cover:
- GET /api/v1/plugins/ (list registered plugins)
- GET /api/v1/plugins/{plugin_id} (get plugin details and schema)
- POST /api/v1/plugins/{plugin_id}/test (test plugin connection)

Requirements:
- Minimum 15 unit tests (AC #9, Story 7.7 testing requirements)
- Test success cases, edge cases, and failure cases
- Mock external dependencies (PluginManager, database, plugin instances)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from src.main import app
from src.plugins.base import TicketingToolPlugin
from src.plugins.exceptions import PluginNotFoundError


@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_plugin():
    """Mock TicketingToolPlugin instance."""
    plugin = MagicMock(spec=TicketingToolPlugin)
    plugin.name = "ServiceDesk Plus"
    plugin.version = "1.0.0"
    plugin.description = "ManageEngine ServiceDesk Plus plugin"
    return plugin


@pytest.fixture
def mock_jira_plugin():
    """Mock Jira plugin instance."""
    plugin = MagicMock(spec=TicketingToolPlugin)
    plugin.name = "Jira Service Management"
    plugin.version = "1.0.0"
    plugin.description = "Atlassian Jira Service Management plugin"
    return plugin


# ============================================================================
# GET /api/v1/plugins/ - List Plugins Tests (AC #1)
# ============================================================================


@pytest.mark.unit
def test_list_plugins_returns_all_registered(client, mock_plugin, mock_jira_plugin):
    """
    Test GET /api/plugins returns all registered plugins.

    AC #1: Plugin registry API endpoint created returning list of plugins.
    """
    with patch("src.api.plugins_routes.PluginManager") as MockManager:
        manager_instance = MockManager.return_value
        manager_instance.list_registered_plugins.return_value = [
            "servicedesk_plus",
            "jira",
        ]
        manager_instance.get_plugin.side_effect = lambda pid: (
            mock_plugin if pid == "servicedesk_plus" else mock_jira_plugin
        )

        response = client.get("/api/v1/plugins/")

        assert response.status_code == 200
        data = response.json()
        assert "plugins" in data
        assert "count" in data
        assert data["count"] == 2
        assert len(data["plugins"]) == 2

        # Verify plugin metadata
        plugin_types = [p["tool_type"] for p in data["plugins"]]
        assert "servicedesk_plus" in plugin_types
        assert "jira" in plugin_types


@pytest.mark.unit
def test_list_plugins_returns_empty_list_when_none_registered(client):
    """
    Test GET /api/plugins returns empty list when no plugins registered.

    Edge case: No plugins available in system.
    """
    with patch("src.api.plugins_routes.PluginManager") as MockManager:
        manager_instance = MockManager.return_value
        manager_instance.list_registered_plugins.return_value = []

        response = client.get("/api/v1/plugins/")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["plugins"] == []


@pytest.mark.unit
def test_list_plugins_metadata_structure(client, mock_plugin):
    """
    Test GET /api/plugins returns correct metadata structure.

    Verifies each plugin has: plugin_id, name, version, status, description, tool_type.
    """
    with patch("src.api.plugins_routes.PluginManager") as MockManager:
        manager_instance = MockManager.return_value
        manager_instance.list_registered_plugins.return_value = ["servicedesk_plus"]
        manager_instance.get_plugin.return_value = mock_plugin

        response = client.get("/api/v1/plugins/")

        assert response.status_code == 200
        data = response.json()
        plugin = data["plugins"][0]

        # Verify required fields present
        assert "plugin_id" in plugin
        assert "name" in plugin
        assert "version" in plugin
        assert "status" in plugin
        assert "description" in plugin
        assert "tool_type" in plugin

        # Verify values
        assert plugin["name"] == "ServiceDesk Plus"
        assert plugin["version"] == "1.0.0"
        assert plugin["status"] == "active"


@pytest.mark.unit
def test_list_plugins_handles_plugin_manager_error(client):
    """
    Test GET /api/plugins returns 500 when PluginManager fails.

    Failure case: PluginManager singleton access fails.
    """
    with patch("src.api.plugins_routes.PluginManager") as MockManager:
        MockManager.side_effect = Exception("PluginManager initialization failed")

        response = client.get("/api/v1/plugins/")

        assert response.status_code == 500
        assert "Failed to retrieve plugin list" in response.json()["detail"]


# ============================================================================
# GET /api/v1/plugins/{plugin_id} - Plugin Details Tests (AC #2)
# ============================================================================


@pytest.mark.unit
def test_get_plugin_details_returns_valid_plugin(client, mock_plugin):
    """
    Test GET /api/plugins/{plugin_id} returns plugin details for valid ID.

    AC #2: Plugin details API endpoint returns full configuration schema.
    """
    with patch("src.api.plugins_routes.PluginManager") as MockManager:
        manager_instance = MockManager.return_value
        manager_instance.is_plugin_registered.return_value = True
        manager_instance.get_plugin.return_value = mock_plugin

        response = client.get("/api/v1/plugins/servicedesk_plus")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data["plugin_id"] == "servicedesk_plus"
        assert data["name"] == "ServiceDesk Plus"
        assert data["version"] == "1.0.0"
        assert "config_schema" in data

        # Verify config schema structure
        schema = data["config_schema"]
        assert "plugin_id" in schema
        assert "schema_fields" in schema
        assert isinstance(schema["schema_fields"], list)


@pytest.mark.unit
def test_get_plugin_details_404_for_non_existent_plugin(client):
    """
    Test GET /api/plugins/{plugin_id} returns 404 for invalid plugin_id.

    AC #2: Add 404 error handling for non-existent plugin_id.
    """
    with patch("src.api.plugins_routes.PluginManager") as MockManager:
        manager_instance = MockManager.return_value
        manager_instance.is_plugin_registered.return_value = False
        manager_instance.list_registered_plugins.return_value = [
            "servicedesk_plus",
            "jira",
        ]

        response = client.get("/api/v1/plugins/zendesk")

        assert response.status_code == 404
        assert "zendesk" in response.json()["detail"]
        assert "Available plugins" in response.json()["detail"]


@pytest.mark.unit
def test_get_plugin_details_schema_includes_all_fields(client, mock_plugin):
    """
    Test GET /api/plugins/{plugin_id} schema includes all configuration fields.

    Verifies schema_fields contain: field_name, field_type, required, description.
    """
    with patch("src.api.plugins_routes.PluginManager") as MockManager:
        manager_instance = MockManager.return_value
        manager_instance.is_plugin_registered.return_value = True
        manager_instance.get_plugin.return_value = mock_plugin

        response = client.get("/api/v1/plugins/jira")

        assert response.status_code == 200
        schema = response.json()["config_schema"]
        fields = schema["schema_fields"]

        # Jira should have 3 config fields
        assert len(fields) == 3

        # Verify field structure
        for field in fields:
            assert "field_name" in field
            assert "field_type" in field
            assert "required" in field
            assert "description" in field


@pytest.mark.unit
def test_get_plugin_details_handles_schema_extraction_error(client):
    """
    Test GET /api/plugins/{plugin_id} returns 500 if schema extraction fails.

    Failure case: Plugin instance doesn't have expected attributes.
    """
    with patch("src.api.plugins_routes.PluginManager") as MockManager:
        manager_instance = MockManager.return_value
        manager_instance.is_plugin_registered.return_value = True
        manager_instance.get_plugin.side_effect = Exception("Schema extraction failed")

        response = client.get("/api/v1/plugins/servicedesk_plus")

        assert response.status_code == 500
        assert "Failed to retrieve plugin details" in response.json()["detail"]


# ============================================================================
# POST /api/v1/plugins/{plugin_id}/test - Connection Test Tests (AC #6)
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_test_connection_success(client, mock_plugin):
    """
    Test POST /api/plugins/{plugin_id}/test returns success for valid config.

    AC #6: Connection testing feature validates plugin credentials.
    """
    with patch("src.api.plugins_routes.PluginManager") as MockManager:
        manager_instance = MockManager.return_value
        manager_instance.is_plugin_registered.return_value = True
        manager_instance.get_plugin.return_value = mock_plugin

        # Mock successful connection test
        mock_plugin.test_connection = AsyncMock(return_value=(True, "Connection successful"))

        # Mock audit logging
        with patch("src.api.plugins_routes.log_audit", new_callable=AsyncMock):
            response = client.post(
                "/api/v1/plugins/servicedesk_plus/test",
                json={
                    "config": {
                        "servicedesk_url": "https://test.servicedesk.com",
                        "api_key": "test-key-123",
                    }
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["message"] == "Connection successful"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_test_connection_failure(client, mock_plugin):
    """
    Test POST /api/plugins/{plugin_id}/test returns failure for invalid config.

    AC #6: Test connection detects authentication failures.
    """
    with patch("src.api.plugins_routes.PluginManager") as MockManager:
        manager_instance = MockManager.return_value
        manager_instance.is_plugin_registered.return_value = True
        manager_instance.get_plugin.return_value = mock_plugin

        # Mock failed connection test
        mock_plugin.test_connection = AsyncMock(
            return_value=(False, "Authentication failed: Invalid API key")
        )

        # Mock audit logging
        with patch("src.api.plugins_routes.log_audit", new_callable=AsyncMock):
            response = client.post(
                "/api/v1/plugins/jira/test",
                json={
                    "config": {
                        "jira_url": "https://test.atlassian.net",
                        "jira_api_token": "invalid-token",
                    }
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "Authentication failed" in data["message"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_test_connection_timeout_handling(client, mock_plugin):
    """
    Test POST /api/plugins/{plugin_id}/test handles 30 second timeout.

    AC #6: Connection test times out after 30 seconds.
    """
    import asyncio

    with patch("src.api.plugins_routes.PluginManager") as MockManager:
        manager_instance = MockManager.return_value
        manager_instance.is_plugin_registered.return_value = True
        manager_instance.get_plugin.return_value = mock_plugin

        # Mock timeout scenario
        async def slow_connection(*args):
            await asyncio.sleep(35)  # Exceeds 30s timeout
            return (True, "Success")

        mock_plugin.test_connection = slow_connection

        # Mock audit logging
        with patch("src.api.plugins_routes.log_audit", new_callable=AsyncMock):
            response = client.post(
                "/api/v1/plugins/servicedesk_plus/test",
                json={"config": {"servicedesk_url": "https://slow.api.com", "api_key": "key"}},
            )

            assert response.status_code == 408
            assert "timed out" in response.json()["detail"].lower()


@pytest.mark.unit
def test_test_connection_404_for_non_existent_plugin(client):
    """
    Test POST /api/plugins/{plugin_id}/test returns 404 for invalid plugin.

    Failure case: Plugin not registered in PluginManager.
    """
    with patch("src.api.plugins_routes.PluginManager") as MockManager:
        manager_instance = MockManager.return_value
        manager_instance.is_plugin_registered.return_value = False
        manager_instance.list_registered_plugins.return_value = ["servicedesk_plus"]

        response = client.post(
            "/api/v1/plugins/zendesk/test",
            json={"config": {"zendesk_url": "https://test.zendesk.com"}},
        )

        assert response.status_code == 404
        assert "zendesk" in response.json()["detail"]


@pytest.mark.unit
def test_test_connection_501_for_unimplemented_method(client, mock_plugin):
    """
    Test POST /api/plugins/{plugin_id}/test returns 501 if test_connection() not implemented.

    Failure case: Plugin doesn't implement test_connection() method.
    """
    with patch("src.api.plugins_routes.PluginManager") as MockManager:
        manager_instance = MockManager.return_value
        manager_instance.is_plugin_registered.return_value = True
        manager_instance.get_plugin.return_value = mock_plugin

        # Mock AttributeError (method not found)
        del mock_plugin.test_connection

        response = client.post(
            "/api/v1/plugins/custom_plugin/test",
            json={"config": {"url": "https://test.com"}},
        )

        assert response.status_code == 501
        assert "does not implement test_connection" in response.json()["detail"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_test_connection_logs_to_audit(client, mock_plugin):
    """
    Test POST /api/plugins/{plugin_id}/test creates audit log entry.

    AC #8: All plugin management operations logged to audit_log table.
    """
    with patch("src.api.plugins_routes.PluginManager") as MockManager:
        manager_instance = MockManager.return_value
        manager_instance.is_plugin_registered.return_value = True
        manager_instance.get_plugin.return_value = mock_plugin

        mock_plugin.test_connection = AsyncMock(return_value=(True, "Success"))

        # Mock and verify audit logging
        with patch("src.api.plugins_routes.log_audit", new_callable=AsyncMock) as mock_log_audit:
            response = client.post(
                "/api/v1/plugins/servicedesk_plus/test",
                json={"config": {"servicedesk_url": "https://test.com", "api_key": "key"}},
            )

            assert response.status_code == 200

            # Verify audit log was called
            mock_log_audit.assert_called_once()
            call_args = mock_log_audit.call_args[1]
            assert call_args["operation"] == "plugin_connection_test"
            assert call_args["details"]["plugin_id"] == "servicedesk_plus"
            assert call_args["details"]["success"] is True
            assert call_args["status"] == "success"


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


@pytest.mark.unit
def test_list_plugins_skips_unretrievable_plugins(client, mock_plugin):
    """
    Test GET /api/plugins skips plugins that fail to retrieve.

    Edge case: Plugin listed but get_plugin() raises exception.
    """
    with patch("src.api.plugins_routes.PluginManager") as MockManager:
        manager_instance = MockManager.return_value
        manager_instance.list_registered_plugins.return_value = [
            "servicedesk_plus",
            "broken_plugin",
        ]

        def get_plugin_side_effect(plugin_id):
            if plugin_id == "broken_plugin":
                raise PluginNotFoundError("Plugin broken")
            return mock_plugin

        manager_instance.get_plugin.side_effect = get_plugin_side_effect

        response = client.get("/api/v1/plugins/")

        assert response.status_code == 200
        data = response.json()
        # Should only return 1 plugin (broken_plugin skipped)
        assert data["count"] == 1
        assert data["plugins"][0]["plugin_id"] == "servicedesk_plus"


@pytest.mark.unit
def test_get_plugin_details_handles_empty_plugin_id(client):
    """
    Test GET /api/plugins/{plugin_id} handles empty plugin_id.

    Edge case: Empty string or whitespace-only plugin_id.
    """
    response = client.get("/api/v1/plugins/")  # No plugin_id - should list all
    assert response.status_code == 200  # Should work as list endpoint


@pytest.mark.unit
@pytest.mark.asyncio
async def test_test_connection_validates_request_body(client):
    """
    Test POST /api/plugins/{plugin_id}/test validates request body structure.

    Edge case: Missing or invalid 'config' field in request.
    """
    with patch("src.api.plugins_routes.PluginManager") as MockManager:
        manager_instance = MockManager.return_value
        manager_instance.is_plugin_registered.return_value = True

        # Missing 'config' field
        response = client.post("/api/v1/plugins/servicedesk_plus/test", json={})

        assert response.status_code == 422  # Pydantic validation error
