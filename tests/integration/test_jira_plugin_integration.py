"""
Integration tests for Jira Service Management plugin.

Tests end-to-end flow:
1. Send webhook → validate → extract metadata → get issue → add comment

Verifies plugin works correctly with PluginManager and routes properly.
"""

import hmac
import hashlib
import json
from unittest.mock import AsyncMock, patch

import pytest

from src.plugins import PluginManager
from src.plugins.jira import JiraServiceManagementPlugin
from src.plugins.base import TicketMetadata


@pytest.fixture
def plugin_manager():
    """Returns PluginManager with Jira plugin registered."""
    manager = PluginManager()
    jira_plugin = JiraServiceManagementPlugin()
    manager.register_plugin("jira", jira_plugin)
    return manager


@pytest.fixture
def valid_jira_webhook():
    """Complete valid Jira webhook with signature."""
    payload = {
        "timestamp": 1699200000000,
        "webhookEvent": "jira:issue_created",
        "issue": {
            "key": "PROJ-123",
            "fields": {
                "summary": "Server performance degradation",
                "description": "Web server experiencing high CPU usage",
                "priority": {"name": "High"},
                "created": "2025-11-05T14:30:00.000+0000",
                "customfield_10000": "tenant-abc",
            },
        },
    }

    # Compute valid signature
    webhook_secret = "test_webhook_secret"
    payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
    signature = hmac.new(webhook_secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    return payload, f"sha256={signature}", webhook_secret


@pytest.mark.asyncio
async def test_end_to_end_webhook_to_comment(plugin_manager, valid_jira_webhook):
    """
    Test end-to-end flow: webhook validation → metadata extraction → get issue → add comment.

    Verifies all plugin methods work together in sequence.
    """
    payload, signature_header, webhook_secret = valid_jira_webhook

    # Mock tenant configuration
    mock_tenant = AsyncMock()
    mock_tenant.tenant_id = "tenant-abc"
    mock_tenant.jira_url = "https://company.atlassian.net"
    mock_tenant.jira_api_token = "test_api_token"
    mock_tenant.webhook_signing_secret = webhook_secret
    mock_tenant.is_active = True

    # Mock API responses
    mock_issue_data = {
        "key": "PROJ-123",
        "fields": {
            "summary": "Server performance degradation",
            "description": "Web server experiencing high CPU usage",
            "status": {"name": "Open"},
        },
    }

    # Get plugin from manager
    plugin = plugin_manager.get_plugin("jira")
    assert plugin is not None
    assert plugin.__tool_type__ == "jira"

    # Mock TenantService, JiraAPIClient, database, and redis connections
    with (
        patch("src.plugins.jira.plugin.get_redis_client") as mock_redis,
        patch("src.plugins.jira.plugin.get_db_session") as mock_db,
        patch("src.plugins.jira.plugin.TenantService") as mock_service,
        patch("src.plugins.jira.plugin.JiraAPIClient") as mock_client_class,
    ):

        # Setup redis and db session mocks
        mock_redis.return_value = AsyncMock()
        mock_db.return_value.__aenter__ = AsyncMock()
        mock_db.return_value.__aexit__ = AsyncMock()

        # Setup TenantService mock
        mock_service_instance = mock_service.return_value
        mock_service_instance.get_tenant_config = AsyncMock(return_value=mock_tenant)

        # Setup JiraAPIClient mock
        mock_client = mock_client_class.return_value
        mock_client.get_issue = AsyncMock(return_value=mock_issue_data)
        mock_client.add_comment = AsyncMock(return_value=True)
        mock_client.close = AsyncMock()

        # Step 1: Validate webhook
        is_valid = await plugin.validate_webhook(payload, signature_header)
        assert is_valid is True, "Webhook validation should pass"

        # Step 2: Extract metadata
        metadata = plugin.extract_metadata(payload)
        assert isinstance(metadata, TicketMetadata)
        assert metadata.tenant_id == "tenant-abc"
        assert metadata.ticket_id == "PROJ-123"
        assert metadata.priority == "high"  # Normalized

        # Step 3: Get issue
        issue = await plugin.get_ticket(metadata.tenant_id, metadata.ticket_id)
        assert issue is not None
        assert issue["key"] == "PROJ-123"
        mock_client.get_issue.assert_called_once_with("PROJ-123")

        # Step 4: Add enhancement comment
        enhancement_content = "**Similar Tickets:**\n- PROJ-100: Resolved by restarting service"
        success = await plugin.update_ticket(
            metadata.tenant_id, metadata.ticket_id, enhancement_content
        )
        assert success is True
        mock_client.add_comment.assert_called_once_with("PROJ-123", enhancement_content)

        # Verify cleanup was called
        assert (
            mock_client.close.call_count == 2
        )  # Once for get_ticket, once for update_ticket  # Once for get_ticket, once for update_ticket


@pytest.mark.asyncio
async def test_plugin_manager_routes_to_jira(plugin_manager):
    """
    Test PluginManager correctly routes to Jira plugin based on tool_type.

    Verifies plugin registration and retrieval works correctly.
    """
    # Get Jira plugin
    jira_plugin = plugin_manager.get_plugin("jira")
    assert jira_plugin is not None
    assert isinstance(jira_plugin, JiraServiceManagementPlugin)
    assert jira_plugin.__tool_type__ == "jira"

    # Verify it's a different instance from ServiceDesk Plus plugin
    servicedesk_plugin = plugin_manager.get_plugin("servicedesk_plus")
    if servicedesk_plugin:  # May not be registered in test environment
        assert type(jira_plugin) != type(servicedesk_plugin)


@pytest.mark.asyncio
async def test_plugin_handles_missing_credentials(plugin_manager):
    """
    Test plugin gracefully handles missing Jira credentials.

    Should return None/False instead of raising exceptions.
    """
    # Mock tenant with missing Jira credentials
    mock_tenant = AsyncMock()
    mock_tenant.tenant_id = "tenant-missing-creds"
    mock_tenant.jira_url = None  # Missing
    mock_tenant.jira_api_token = None  # Missing
    mock_tenant.webhook_signing_secret = "test_secret"
    mock_tenant.is_active = True

    plugin = plugin_manager.get_plugin("jira")

    with patch("src.plugins.jira.plugin.TenantService") as mock_service:
        mock_service_instance = mock_service.return_value
        mock_service_instance.get_tenant_config = AsyncMock(return_value=mock_tenant)

        # get_ticket should return None (not raise exception)
        result = await plugin.get_ticket("tenant-missing-creds", "PROJ-123")
        assert result is None

        # update_ticket should return False (not raise exception)
        result = await plugin.update_ticket("tenant-missing-creds", "PROJ-123", "content")
        assert result is False
