"""
Integration tests for enhancement workflow using MockTicketingToolPlugin.

Tests the complete enhancement workflow from webhook validation through ticket update
using mock plugin to avoid real API dependencies. Demonstrates end-to-end mock usage
and failure handling patterns.

Story: 7.6 - Task 4 - Integration Test with Mock Plugin
"""

import asyncio
import pytest

from tests.mocks.mock_plugin import MockTicketingToolPlugin
from tests.utils.plugin_test_helpers import (
    assert_plugin_called,
    assert_plugin_called_with,
    assert_ticket_metadata_valid,
    build_generic_payload,
    build_servicedesk_payload,
    build_jira_payload,
    capture_plugin_response,
)
from src.plugins.servicedesk_plus.api_client import ServiceDeskAPIError


# ============================================================================
# Full Enhancement Workflow Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.plugin
async def test_full_enhancement_workflow_with_mock_plugin():
    """
    Test complete enhancement workflow using mock plugin (success path).

    Workflow phases:
    1. Webhook validation
    2. Metadata extraction
    3. Ticket retrieval (context gathering)
    4. Ticket update (enhancement application)

    This test demonstrates end-to-end mock plugin usage without real API calls.
    """
    # Setup: Create mock plugin and test payload
    plugin = MockTicketingToolPlugin.success_mode()
    payload = build_generic_payload(
        tenant_id="acme-corp",
        ticket_id="TEST-123",
        description="Server performance issue",
        priority="high",
    )

    # Phase 1: Webhook Validation
    signature = "test-signature-sha256-hmac"
    valid = await plugin.validate_webhook(payload, signature)
    assert valid is True, "Webhook validation should succeed in success mode"
    assert_plugin_called(plugin, "validate_webhook", times=1)

    # Phase 2: Metadata Extraction
    metadata = plugin.extract_metadata(payload)
    assert metadata is not None, "Metadata extraction should return TicketMetadata"
    assert_ticket_metadata_valid(metadata)
    assert metadata.tenant_id == "acme-corp"
    assert metadata.ticket_id == "TEST-123"
    assert metadata.priority == "high"
    # Note: extract_metadata is sync, not tracked in call history

    # Phase 3: Ticket Retrieval (Context Gathering)
    ticket = await plugin.get_ticket("acme-corp", "TEST-123")
    assert ticket is not None, "get_ticket should return ticket dict in success mode"
    assert "id" in ticket or "request" in ticket, "Ticket should have expected structure"
    assert_plugin_called(plugin, "get_ticket", times=1)
    assert_plugin_called_with(plugin, "get_ticket", tenant_id="acme-corp", ticket_id="TEST-123")

    # Phase 4: Ticket Update (Enhancement Application)
    enhancement_content = "**Similar Tickets:**\n- TEST-100: Resolution link\n..."
    success = await plugin.update_ticket("acme-corp", "TEST-123", enhancement_content)
    assert success is True, "update_ticket should return True in success mode"
    assert_plugin_called(plugin, "update_ticket", times=1)
    assert_plugin_called_with(
        plugin,
        "update_ticket",
        tenant_id="acme-corp",
        ticket_id="TEST-123",
        content=enhancement_content,
    )

    # Verify call history tracking
    history = plugin.get_call_history()
    assert len(history) == 3, "Should have 3 async method calls recorded"
    assert history[0]["method"] == "validate_webhook"
    assert history[1]["method"] == "get_ticket"
    assert history[2]["method"] == "update_ticket"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.plugin
async def test_servicedesk_plus_workflow_with_mock_plugin(mock_servicedesk_plugin):
    """
    Test enhancement workflow with ServiceDesk Plus-specific mock plugin.

    Uses mock_servicedesk_plugin fixture which has ServiceDesk Plus API response format.
    """
    plugin = mock_servicedesk_plugin
    payload = build_servicedesk_payload(tenant_id="acme-corp", ticket_id="12345", priority="Urgent")

    # Validate webhook
    valid = await plugin.validate_webhook(payload, "sdplus-signature")
    assert valid is True

    # Extract metadata
    metadata = plugin.extract_metadata(payload)
    assert_ticket_metadata_valid(metadata)
    assert metadata.ticket_id == "12345"
    assert metadata.priority == "high"  # Normalized from "Urgent"

    # Get ticket (ServiceDesk Plus wraps response in "request" key)
    ticket = await plugin.get_ticket("acme-corp", "12345")
    assert "request" in ticket, "ServiceDesk Plus response should have 'request' wrapper"
    assert ticket["request"]["id"] == "12345"

    # Update ticket
    success = await plugin.update_ticket("acme-corp", "12345", "Enhancement content")
    assert success is True


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.plugin
async def test_jira_workflow_with_mock_plugin(mock_jira_plugin):
    """
    Test enhancement workflow with Jira-specific mock plugin.

    Uses mock_jira_plugin fixture which has Jira API response format.
    """
    plugin = mock_jira_plugin
    payload = build_jira_payload(tenant_id="acme-corp", ticket_id="JIRA-456", priority="High")

    # Validate webhook
    valid = await plugin.validate_webhook(payload, "jira-signature")
    assert valid is True

    # Extract metadata
    metadata = plugin.extract_metadata(payload)
    assert_ticket_metadata_valid(metadata)
    assert metadata.ticket_id == "JIRA-456"
    assert metadata.priority == "high"

    # Get ticket (Jira response has "key" and "fields")
    ticket = await plugin.get_ticket("acme-corp", "JIRA-456")
    assert ticket["key"] == "JIRA-456"
    assert "fields" in ticket, "Jira response should have 'fields' object"
    assert ticket["fields"]["priority"]["name"] == "High"

    # Update ticket
    success = await plugin.update_ticket("acme-corp", "JIRA-456", "Enhancement content")
    assert success is True


# ============================================================================
# Failure Mode Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.plugin
async def test_workflow_api_error_during_get_ticket():
    """
    Test workflow handles API error during ticket retrieval gracefully.

    Simulates ServiceDeskAPIError during get_ticket phase.
    """
    plugin = MockTicketingToolPlugin.api_error_mode()
    payload = build_generic_payload()

    # Webhook validation should still succeed
    valid = await plugin.validate_webhook(payload, "signature")
    assert valid is True

    # get_ticket should raise ServiceDeskAPIError
    with pytest.raises(ServiceDeskAPIError) as exc_info:
        await plugin.get_ticket("tenant-1", "ticket-123")

    assert "Mock API error" in str(exc_info.value)
    assert "status=500" in str(exc_info.value)
    assert "retries=3" in str(exc_info.value)

    # Verify call was recorded before exception
    assert_plugin_called(plugin, "get_ticket", times=1)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.plugin
async def test_workflow_timeout_during_update_ticket():
    """
    Test workflow handles timeout during ticket update gracefully.

    Simulates asyncio.TimeoutError during update_ticket phase.
    """
    plugin = MockTicketingToolPlugin.timeout_mode()
    payload = build_generic_payload()

    # get_ticket would timeout, but update_ticket timeout is more realistic
    # In production, get_ticket has shorter timeout than update_ticket

    # Test with 1s timeout (should fail since plugin delays 10s)
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            plugin.update_ticket("tenant-1", "ticket-123", "enhancement"), timeout=1.0
        )

    # Verify call was recorded before timeout
    assert_plugin_called(plugin, "update_ticket", times=1)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.plugin
async def test_workflow_ticket_not_found():
    """
    Test workflow handles ticket not found (None response) gracefully.

    Simulates 404 response from ticketing tool API.
    """
    plugin = MockTicketingToolPlugin.not_found_mode()
    payload = build_generic_payload()

    # Webhook validation succeeds
    valid = await plugin.validate_webhook(payload, "signature")
    assert valid is True

    # get_ticket returns None (ticket not found)
    ticket = await plugin.get_ticket("tenant-1", "non-existent-ticket")
    assert ticket is None, "not_found_mode should return None from get_ticket"

    # Workflow should handle None gracefully (no exception)
    # In production, this would skip enhancement and log warning
    assert_plugin_called(plugin, "get_ticket", times=1)


# ============================================================================
# Response Capture Utility Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.plugin
async def test_capture_plugin_response_success():
    """
    Test capture_plugin_response utility with successful method call.
    """
    plugin = MockTicketingToolPlugin.success_mode()

    result, exception, duration_ms = await capture_plugin_response(
        plugin, "get_ticket", "tenant-1", "ticket-123"
    )

    assert exception is None, "Should not raise exception in success mode"
    assert result is not None, "Should return ticket dict"
    assert duration_ms < 100, "Should complete in <100ms (no I/O)"
    assert "id" in result or "MOCK" in result.get("id", "")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.plugin
async def test_capture_plugin_response_api_error():
    """
    Test capture_plugin_response utility with API error.
    """
    plugin = MockTicketingToolPlugin.api_error_mode()

    result, exception, duration_ms = await capture_plugin_response(
        plugin, "update_ticket", "tenant-1", "ticket-123", "content"
    )

    assert exception is not None, "Should capture ServiceDeskAPIError"
    assert isinstance(exception, ServiceDeskAPIError)
    assert result is None, "Result should be None when exception raised"
    assert duration_ms < 100, "Should fail fast (no retries in mock)"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.plugin
async def test_capture_plugin_response_timeout():
    """
    Test capture_plugin_response utility with timeout.
    """
    plugin = MockTicketingToolPlugin.timeout_mode()

    result, exception, duration_ms = await capture_plugin_response(
        plugin,
        "validate_webhook",
        {"test": "payload"},
        "signature",
        timeout=1.0,  # 1s timeout (plugin delays 10s)
    )

    assert exception is not None, "Should capture TimeoutError"
    assert isinstance(exception, asyncio.TimeoutError)
    assert result is None
    assert 900 < duration_ms < 1500, "Should timeout after ~1s"


# ============================================================================
# Edge Case Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.plugin
async def test_workflow_with_malformed_payload():
    """
    Test extract_metadata handles malformed payload gracefully.

    Mock plugin should use defaults for missing fields.
    """
    plugin = MockTicketingToolPlugin.success_mode()

    # Payload missing most fields
    malformed_payload = {"tenant_id": "test-tenant"}

    # extract_metadata should not raise exception
    metadata = plugin.extract_metadata(malformed_payload)
    assert_ticket_metadata_valid(metadata)
    assert metadata.tenant_id == "test-tenant"
    # Should use defaults for missing fields
    assert "MOCK" in metadata.ticket_id  # Default ticket ID
    assert metadata.description  # Default description
    assert metadata.priority in ["high", "medium", "low"]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.plugin
async def test_workflow_with_call_history_reset():
    """
    Test call history can be reset between test phases.
    """
    plugin = MockTicketingToolPlugin.success_mode()

    # Phase 1: Initial calls
    await plugin.validate_webhook({"test": "payload"}, "sig1")
    await plugin.get_ticket("tenant-1", "ticket-1")
    assert len(plugin.get_call_history()) == 2

    # Reset call history
    plugin.reset_call_history()
    assert len(plugin.get_call_history()) == 0

    # Phase 2: New calls
    await plugin.update_ticket("tenant-2", "ticket-2", "content")
    history = plugin.get_call_history()
    assert len(history) == 1
    assert history[0]["method"] == "update_ticket"
    assert history[0]["kwargs"]["tenant_id"] == "tenant-2"
