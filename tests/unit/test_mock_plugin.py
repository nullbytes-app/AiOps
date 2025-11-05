"""
Unit tests for MockTicketingToolPlugin.

Tests all factory methods, configurable behaviors, and call tracking functionality.
Validates mock plugin implements TicketingToolPlugin interface correctly.

Story: 7.6 - Task 7 - Unit Tests for MockTicketingToolPlugin
"""

import asyncio
import pytest

from tests.mocks.mock_plugin import MockTicketingToolPlugin
from src.plugins.base import TicketMetadata
from src.plugins.servicedesk_plus.api_client import ServiceDeskAPIError
from src.utils.exceptions import ValidationError


# ============================================================================
# Factory Method Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.plugin
class TestFactoryMethods:
    """Test all factory methods create correctly configured plugins."""

    @pytest.mark.asyncio
    async def test_success_mode(self):
        """Test success_mode factory creates plugin with all success responses."""
        plugin = MockTicketingToolPlugin.success_mode()

        # validate_webhook returns True
        valid = await plugin.validate_webhook({"test": "payload"}, "signature")
        assert valid is True

        # get_ticket returns valid ticket dict
        ticket = await plugin.get_ticket("tenant-1", "ticket-123")
        assert ticket is not None
        assert isinstance(ticket, dict)
        assert "id" in ticket or "MOCK" in str(ticket)

        # update_ticket returns True
        success = await plugin.update_ticket("tenant-1", "ticket-123", "content")
        assert success is True

        # extract_metadata returns valid TicketMetadata
        metadata = plugin.extract_metadata({"tenant_id": "test", "ticket_id": "123"})
        assert isinstance(metadata, TicketMetadata)

    @pytest.mark.asyncio
    async def test_api_error_mode(self):
        """Test api_error_mode factory raises ServiceDeskAPIError."""
        plugin = MockTicketingToolPlugin.api_error_mode()

        # get_ticket raises ServiceDeskAPIError
        with pytest.raises(ServiceDeskAPIError) as exc_info:
            await plugin.get_ticket("tenant-1", "ticket-123")
        assert "Mock API error" in str(exc_info.value)
        assert "status=500" in str(exc_info.value)
        assert "retries=3" in str(exc_info.value)

        # update_ticket raises ServiceDeskAPIError
        with pytest.raises(ServiceDeskAPIError) as exc_info:
            await plugin.update_ticket("tenant-1", "ticket-123", "content")
        assert "Mock update failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_auth_error_mode(self):
        """Test auth_error_mode factory raises ValidationError."""
        plugin = MockTicketingToolPlugin.auth_error_mode()

        # validate_webhook raises ValidationError
        with pytest.raises(ValidationError) as exc_info:
            await plugin.validate_webhook({"test": "payload"}, "invalid-signature")
        assert "Mock authentication failure" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_timeout_mode(self):
        """Test timeout_mode factory raises asyncio.TimeoutError."""
        plugin = MockTicketingToolPlugin.timeout_mode()

        # validate_webhook raises TimeoutError after 10s (test with 1s timeout)
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                plugin.validate_webhook({"test": "payload"}, "signature"), timeout=1.0
            )

        # get_ticket raises TimeoutError
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(plugin.get_ticket("tenant-1", "ticket-123"), timeout=1.0)

        # update_ticket raises TimeoutError
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                plugin.update_ticket("tenant-1", "ticket-123", "content"), timeout=1.0
            )

    @pytest.mark.asyncio
    async def test_not_found_mode(self):
        """Test not_found_mode factory returns None from get_ticket."""
        plugin = MockTicketingToolPlugin.not_found_mode()

        # get_ticket returns None (ticket not found)
        ticket = await plugin.get_ticket("tenant-1", "non-existent")
        assert ticket is None


# ============================================================================
# Call Tracking Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.plugin
class TestCallTracking:
    """Test call history tracking functionality."""

    @pytest.mark.asyncio
    async def test_call_history_records_all_methods(self):
        """Test all async methods are recorded in call history."""
        plugin = MockTicketingToolPlugin.success_mode()

        # Make calls to all async methods
        await plugin.validate_webhook({"test": "payload"}, "sig1")
        await plugin.get_ticket("tenant-1", "ticket-1")
        await plugin.update_ticket("tenant-1", "ticket-1", "content")

        # Check call history
        history = plugin.get_call_history()
        assert len(history) == 3

        # Verify first call (validate_webhook)
        assert history[0]["method"] == "validate_webhook"
        assert "payload" in history[0]["kwargs"]
        assert history[0]["kwargs"]["signature"] == "sig1"

        # Verify second call (get_ticket)
        assert history[1]["method"] == "get_ticket"
        assert history[1]["kwargs"]["tenant_id"] == "tenant-1"
        assert history[1]["kwargs"]["ticket_id"] == "ticket-1"

        # Verify third call (update_ticket)
        assert history[2]["method"] == "update_ticket"
        assert history[2]["kwargs"]["content"] == "content"

    @pytest.mark.asyncio
    async def test_call_history_includes_timestamps(self):
        """Test call history includes timestamps for each call."""
        plugin = MockTicketingToolPlugin.success_mode()

        await plugin.get_ticket("tenant-1", "ticket-123")

        history = plugin.get_call_history()
        assert len(history) == 1
        assert "timestamp" in history[0]
        assert history[0]["timestamp"] is not None

    def test_reset_call_history(self):
        """Test reset_call_history clears all recorded calls."""
        plugin = MockTicketingToolPlugin.success_mode()

        # Add some calls (using sync method to avoid async)
        plugin.extract_metadata({"test": "payload"})
        # Note: extract_metadata is sync and not tracked, so use __init__ directly
        plugin._call_history.append({"method": "test", "args": [], "kwargs": {}})

        # Verify history has entries
        assert len(plugin.get_call_history()) > 0

        # Reset
        plugin.reset_call_history()

        # Verify history is empty
        assert len(plugin.get_call_history()) == 0

    @pytest.mark.asyncio
    async def test_call_history_preserved_on_exception(self):
        """Test call history is recorded even when method raises exception."""
        plugin = MockTicketingToolPlugin.api_error_mode()

        # Call that will raise exception
        with pytest.raises(ServiceDeskAPIError):
            await plugin.get_ticket("tenant-1", "ticket-123")

        # Verify call was still recorded
        history = plugin.get_call_history()
        assert len(history) == 1
        assert history[0]["method"] == "get_ticket"


# ============================================================================
# Custom Configuration Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.plugin
class TestCustomConfiguration:
    """Test custom plugin configuration via constructor."""

    @pytest.mark.asyncio
    async def test_custom_validate_response(self):
        """Test custom _validate_response configuration."""
        plugin = MockTicketingToolPlugin(_validate_response=False)

        valid = await plugin.validate_webhook({"test": "payload"}, "signature")
        assert valid is False

    @pytest.mark.asyncio
    async def test_custom_get_ticket_response(self):
        """Test custom _get_ticket_response configuration."""
        custom_ticket = {"id": "CUSTOM-789", "priority": "critical"}
        plugin = MockTicketingToolPlugin(_get_ticket_response=custom_ticket)

        ticket = await plugin.get_ticket("tenant-1", "ticket-123")
        assert ticket == custom_ticket
        assert ticket["id"] == "CUSTOM-789"

    @pytest.mark.asyncio
    async def test_custom_update_ticket_response(self):
        """Test custom _update_ticket_response configuration."""
        plugin = MockTicketingToolPlugin(_update_ticket_response=False)

        success = await plugin.update_ticket("tenant-1", "ticket-123", "content")
        assert success is False


# ============================================================================
# extract_metadata Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.plugin
class TestExtractMetadata:
    """Test extract_metadata method with various payload structures."""

    def test_extract_metadata_generic_payload(self):
        """Test extract_metadata with simple flat payload."""
        plugin = MockTicketingToolPlugin.success_mode()
        payload = {
            "tenant_id": "test-tenant",
            "ticket_id": "TICKET-123",
            "description": "Test description",
            "priority": "high",
            "created_at": "2025-11-05T10:00:00Z",
        }

        metadata = plugin.extract_metadata(payload)

        assert metadata.tenant_id == "test-tenant"
        assert metadata.ticket_id == "TICKET-123"
        assert metadata.description == "Test description"
        assert metadata.priority == "high"

    def test_extract_metadata_servicedesk_payload(self):
        """Test extract_metadata with ServiceDesk Plus nested structure."""
        plugin = MockTicketingToolPlugin.success_mode()
        payload = {
            "tenant_id": "acme-corp",
            "data": {
                "ticket": {
                    "id": "12345",
                    "description": "Server slow",
                    "priority": "Urgent",  # Should normalize to "high"
                    "created_time": "2025-11-05T10:00:00Z",
                }
            },
        }

        metadata = plugin.extract_metadata(payload)

        assert metadata.tenant_id == "acme-corp"
        assert metadata.ticket_id == "12345"
        assert metadata.description == "Server slow"
        assert metadata.priority == "high"  # Normalized from "Urgent"

    def test_extract_metadata_jira_payload(self):
        """Test extract_metadata with Jira nested structure."""
        plugin = MockTicketingToolPlugin.success_mode()
        payload = {
            "tenant_id": "acme-corp",
            "issue": {
                "key": "JIRA-456",
                "fields": {
                    "description": "Network issue",
                    "priority": {"name": "High"},  # Jira priority object
                },
            },
        }

        metadata = plugin.extract_metadata(payload)

        assert metadata.tenant_id == "acme-corp"
        assert metadata.ticket_id == "JIRA-456"
        assert metadata.description == "Network issue"
        assert metadata.priority == "high"

    def test_extract_metadata_missing_fields(self):
        """Test extract_metadata handles missing fields with defaults."""
        plugin = MockTicketingToolPlugin.success_mode()
        payload = {"tenant_id": "test"}  # Missing most fields

        metadata = plugin.extract_metadata(payload)

        # Should use defaults
        assert metadata.tenant_id == "test"
        assert "MOCK" in metadata.ticket_id  # Default ticket ID
        assert metadata.description  # Has default description
        assert metadata.priority in ["high", "medium", "low"]
        assert metadata.created_at is not None

    def test_extract_metadata_priority_normalization(self):
        """Test priority is normalized to lowercase."""
        plugin = MockTicketingToolPlugin.success_mode()

        test_cases = [
            ("Urgent", "high"),
            ("Critical", "high"),
            ("HIGH", "high"),
            ("medium", "medium"),
            ("MEDIUM", "medium"),
            ("low", "low"),
            ("LOW", "low"),
            ("unknown_priority", "medium"),  # Unknown → default to medium
        ]

        for input_priority, expected_priority in test_cases:
            payload = {"tenant_id": "test", "priority": input_priority}
            metadata = plugin.extract_metadata(payload)
            assert (
                metadata.priority == expected_priority
            ), f"Priority '{input_priority}' should normalize to '{expected_priority}'"


# ============================================================================
# Behavior Verification Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.plugin
class TestBehaviorVerification:
    """Test specific mock plugin behaviors."""

    @pytest.mark.asyncio
    async def test_extract_metadata_not_tracked_in_history(self):
        """Test extract_metadata (sync method) is not tracked in call history."""
        plugin = MockTicketingToolPlugin.success_mode()

        # Call extract_metadata (sync method)
        plugin.extract_metadata({"tenant_id": "test"})

        # Call history should be empty (only async methods tracked)
        history = plugin.get_call_history()
        assert len(history) == 0

    @pytest.mark.asyncio
    async def test_multiple_calls_same_method(self):
        """Test call history tracks multiple calls to same method."""
        plugin = MockTicketingToolPlugin.success_mode()

        # Call get_ticket 3 times with different args
        await plugin.get_ticket("tenant-1", "ticket-1")
        await plugin.get_ticket("tenant-1", "ticket-2")
        await plugin.get_ticket("tenant-2", "ticket-3")

        # Verify all 3 calls tracked
        history = plugin.get_call_history()
        assert len(history) == 3
        assert all(call["method"] == "get_ticket" for call in history)

        # Verify different ticket IDs
        ticket_ids = [call["kwargs"]["ticket_id"] for call in history]
        assert ticket_ids == ["ticket-1", "ticket-2", "ticket-3"]

    @pytest.mark.asyncio
    async def test_get_call_history_returns_copy(self):
        """Test get_call_history returns copy (mutations don't affect internal history)."""
        plugin = MockTicketingToolPlugin.success_mode()

        await plugin.get_ticket("tenant-1", "ticket-123")

        # Get history and mutate it
        history = plugin.get_call_history()
        history.append({"fake": "call"})

        # Get history again - should not include fake call
        history2 = plugin.get_call_history()
        assert len(history2) == 1
        assert "fake" not in history2[0]
