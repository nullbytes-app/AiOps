"""Unit tests for ServiceDesk Plus Plugin.

Tests all four plugin methods (validate_webhook, extract_metadata, get_ticket, update_ticket)
with success cases, failure cases, and edge cases. Validates plugin implements TicketingToolPlugin
interface correctly and maintains backward compatibility with existing webhook validation logic.

Story 7.3 - Task 11
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from src.plugins.servicedesk_plus.plugin import ServiceDeskPlusPlugin
from src.plugins.base import TicketMetadata
from src.plugins.servicedesk_plus.api_client import (
    ServiceDeskAPIClient,
    ServiceDeskAPIError,
    ServiceDeskAuthenticationError,
)
from src.utils.exceptions import TenantNotFoundException


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def servicedesk_plugin():
    """ServiceDesk Plus plugin instance for testing."""
    return ServiceDeskPlusPlugin()


@pytest.fixture
def valid_webhook_payload():
    """Valid ServiceDesk Plus webhook payload for testing."""
    # Use current timestamp to avoid clock skew issues
    current_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "tenant_id": "acme-corp",
        "event": "ticket_created",
        "data": {
            "ticket": {
                "id": "12345",
                "description": "Server is slow and unresponsive",
                "priority": "Urgent",
                "created_time": current_time,
            }
        },
        "created_at": current_time,
    }


@pytest.fixture
def valid_ticket_response():
    """Valid ServiceDesk Plus API ticket response for testing."""
    return {
        "request": {
            "id": "12345",
            "subject": "Server performance issue",
            "description": "<p>Server is slow and unresponsive</p>",
            "status": {"name": "Open"},
            "priority": {"name": "High"},
            "created_time": {"value": "1699392000000"},
        }
    }


@pytest.fixture
def mock_tenant_config():
    """Mock tenant configuration for testing."""
    mock_config = MagicMock()
    mock_config.tenant_id = "acme-corp"
    mock_config.servicedesk_url = "https://acme.servicedesk.com"
    mock_config.servicedesk_api_key = "test-api-key-12345"  # Fixed: correct attribute name
    mock_config.webhook_signing_secret = "test-webhook-secret"  # Fixed: correct attribute name
    mock_config.is_active = True
    return mock_config


# ============================================================================
# Test validate_webhook() method
# ============================================================================


class TestValidateWebhook:
    """Test webhook signature validation using plugin."""

    @pytest.mark.asyncio
    async def test_validate_webhook_success(
        self, servicedesk_plugin, valid_webhook_payload, mock_tenant_config
    ):
        """Test successful webhook validation with valid signature."""
        # Arrange: Compute valid HMAC signature
        from src.plugins.servicedesk_plus import webhook_validator

        payload_bytes = json.dumps(valid_webhook_payload, separators=(",", ":")).encode("utf-8")
        valid_signature = webhook_validator.compute_hmac_signature(
            secret=mock_tenant_config.webhook_signing_secret, payload_bytes=payload_bytes
        )

        # Mock TenantService to return mock_tenant_config
        with patch("src.plugins.servicedesk_plus.plugin.get_db_session") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            with patch("src.plugins.servicedesk_plus.plugin.get_redis_client") as mock_redis_fn:
                mock_redis = AsyncMock()
                mock_redis_fn.return_value = mock_redis

                with patch("src.plugins.servicedesk_plus.plugin.TenantService") as mock_tenant_service:
                    mock_service = AsyncMock()
                    mock_service.get_tenant_config.return_value = mock_tenant_config
                    mock_tenant_service.return_value = mock_service

                    # Act: Validate webhook
                    is_valid = await servicedesk_plugin.validate_webhook(
                        payload=valid_webhook_payload, signature=valid_signature
                    )

                    # Assert: Validation should succeed
                    assert is_valid is True
                    mock_service.get_tenant_config.assert_awaited_once_with("acme-corp")

    @pytest.mark.asyncio
    async def test_validate_webhook_invalid_signature(
        self, servicedesk_plugin, valid_webhook_payload, mock_tenant_config
    ):
        """Test webhook validation fails with invalid signature."""
        # Arrange: Use incorrect signature
        invalid_signature = "invalid-signature-abc123"

        # Mock TenantService
        with patch("src.plugins.servicedesk_plus.plugin.get_db_session") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session


            with patch("src.plugins.servicedesk_plus.plugin.get_redis_client") as mock_redis_fn:
                mock_redis = AsyncMock()
                mock_redis_fn.return_value = mock_redis

            with patch("src.plugins.servicedesk_plus.plugin.TenantService") as mock_tenant_service:
                mock_service = AsyncMock()
                mock_service.get_tenant_config.return_value = mock_tenant_config
                mock_tenant_service.return_value = mock_service

                # Act: Validate webhook with invalid signature
                is_valid = await servicedesk_plugin.validate_webhook(
                    payload=valid_webhook_payload, signature=invalid_signature
                )

                # Assert: Validation should fail
                assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_webhook_tenant_not_found(
        self, servicedesk_plugin, valid_webhook_payload
    ):
        """Test webhook validation fails when tenant not found."""
        # Arrange: Mock TenantService to raise TenantNotFoundException
        with patch("src.plugins.servicedesk_plus.plugin.get_db_session") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session


            with patch("src.plugins.servicedesk_plus.plugin.get_redis_client") as mock_redis_fn:
                mock_redis = AsyncMock()
                mock_redis_fn.return_value = mock_redis

            with patch("src.plugins.servicedesk_plus.plugin.TenantService") as mock_tenant_service:
                mock_service = AsyncMock()
                mock_service.get_tenant_config.side_effect = TenantNotFoundException(
                    "Tenant 'acme-corp' not found"
                )
                mock_tenant_service.return_value = mock_service

                # Act: Validate webhook
                is_valid = await servicedesk_plugin.validate_webhook(
                    payload=valid_webhook_payload, signature="test-signature"
                )

                # Assert: Validation should fail gracefully
                assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_webhook_inactive_tenant(
        self, servicedesk_plugin, valid_webhook_payload, mock_tenant_config
    ):
        """Test webhook validation fails for inactive tenant."""
        # Arrange: Set tenant as inactive
        mock_tenant_config.is_active = False

        # Mock TenantService
        with patch("src.plugins.servicedesk_plus.plugin.get_db_session") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session


            with patch("src.plugins.servicedesk_plus.plugin.get_redis_client") as mock_redis_fn:
                mock_redis = AsyncMock()
                mock_redis_fn.return_value = mock_redis

            with patch("src.plugins.servicedesk_plus.plugin.TenantService") as mock_tenant_service:
                mock_service = AsyncMock()
                mock_service.get_tenant_config.return_value = mock_tenant_config
                mock_tenant_service.return_value = mock_service

                # Act: Validate webhook
                is_valid = await servicedesk_plugin.validate_webhook(
                    payload=valid_webhook_payload, signature="test-signature"
                )

                # Assert: Validation should fail for inactive tenant
                assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_webhook_expired_timestamp(
        self, servicedesk_plugin, valid_webhook_payload, mock_tenant_config
    ):
        """Test webhook validation fails with expired timestamp (replay attack prevention)."""
        # Arrange: Create payload with old timestamp (>5 minutes ago)
        old_timestamp = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        expired_payload = {**valid_webhook_payload, "created_at": old_timestamp}

        from src.plugins.servicedesk_plus import webhook_validator

        payload_bytes = json.dumps(expired_payload, separators=(",", ":")).encode("utf-8")
        valid_signature = webhook_validator.compute_hmac_signature(
            secret=mock_tenant_config.webhook_signing_secret, payload_bytes=payload_bytes
        )

        # Mock TenantService
        with patch("src.plugins.servicedesk_plus.plugin.get_db_session") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session


            with patch("src.plugins.servicedesk_plus.plugin.get_redis_client") as mock_redis_fn:
                mock_redis = AsyncMock()
                mock_redis_fn.return_value = mock_redis

            with patch("src.plugins.servicedesk_plus.plugin.TenantService") as mock_tenant_service:
                mock_service = AsyncMock()
                mock_service.get_tenant_config.return_value = mock_tenant_config
                mock_tenant_service.return_value = mock_service

                # Act: Validate webhook with expired timestamp
                is_valid = await servicedesk_plugin.validate_webhook(
                    payload=expired_payload, signature=valid_signature
                )

                # Assert: Validation should fail due to timestamp
                assert is_valid is False


# ============================================================================
# Test extract_metadata() method
# ============================================================================


class TestExtractMetadata:
    """Test metadata extraction from webhook payloads."""

    def test_extract_metadata_success(self, servicedesk_plugin, valid_webhook_payload):
        """Test successful metadata extraction from valid payload."""
        # Act: Extract metadata
        metadata = servicedesk_plugin.extract_metadata(valid_webhook_payload)

        # Assert: TicketMetadata returned with correct values
        assert isinstance(metadata, TicketMetadata)
        assert metadata.tenant_id == "acme-corp"
        assert metadata.ticket_id == "12345"
        assert metadata.description == "Server is slow and unresponsive"
        assert metadata.priority == "high"  # Normalized from "Urgent"
        assert isinstance(metadata.created_at, datetime)

    def test_extract_metadata_missing_tenant_id(self, servicedesk_plugin, valid_webhook_payload):
        """Test metadata extraction fails when tenant_id missing."""
        # Arrange: Remove tenant_id from payload
        invalid_payload = {**valid_webhook_payload}
        del invalid_payload["tenant_id"]

        # Act & Assert: Should raise ValueError
        with pytest.raises(ValueError, match="tenant_id field is required"):
            servicedesk_plugin.extract_metadata(invalid_payload)

    def test_extract_metadata_missing_ticket_id(self, servicedesk_plugin, valid_webhook_payload):
        """Test metadata extraction fails when ticket.id missing."""
        # Arrange: Remove ticket.id from payload
        invalid_payload = {**valid_webhook_payload}
        del invalid_payload["data"]["ticket"]["id"]

        # Act & Assert: Should raise ValueError
        with pytest.raises(ValueError, match="ticket.id field is required"):
            servicedesk_plugin.extract_metadata(invalid_payload)

    def test_extract_metadata_invalid_datetime(self, servicedesk_plugin, valid_webhook_payload):
        """Test metadata extraction fails with invalid datetime format."""
        # Arrange: Set invalid datetime format
        invalid_payload = {**valid_webhook_payload}
        invalid_payload["data"]["ticket"]["created_time"] = "not-a-datetime"

        # Act & Assert: Should raise ValueError
        with pytest.raises(ValueError, match="Invalid created_time format"):
            servicedesk_plugin.extract_metadata(invalid_payload)

    def test_extract_metadata_priority_normalization(
        self, servicedesk_plugin, valid_webhook_payload
    ):
        """Test priority normalization for different ServiceDesk Plus values."""
        test_cases = [
            ("Urgent", "high"),
            ("Critical", "high"),
            ("High", "high"),
            ("Medium", "medium"),
            ("Normal", "medium"),
            ("Low", "low"),
            ("Unknown", "medium"),  # Default fallback
        ]

        for sd_priority, expected_priority in test_cases:
            # Arrange: Set priority in payload
            payload = {**valid_webhook_payload}
            payload["data"]["ticket"]["priority"] = sd_priority

            # Act: Extract metadata
            metadata = servicedesk_plugin.extract_metadata(payload)

            # Assert: Priority normalized correctly
            assert metadata.priority == expected_priority

    def test_extract_metadata_ticket_id_as_integer(self, servicedesk_plugin, valid_webhook_payload):
        """Test metadata extraction handles ticket_id as integer (converts to string)."""
        # Arrange: Set ticket_id as integer
        payload = {**valid_webhook_payload}
        payload["data"]["ticket"]["id"] = 12345  # Integer instead of string

        # Act: Extract metadata
        metadata = servicedesk_plugin.extract_metadata(payload)

        # Assert: ticket_id converted to string
        assert metadata.ticket_id == "12345"
        assert isinstance(metadata.ticket_id, str)


# ============================================================================
# Test get_ticket() method
# ============================================================================


class TestGetTicket:
    """Test ticket retrieval via ServiceDesk Plus API."""

    @pytest.mark.asyncio
    async def test_get_ticket_success(
        self, servicedesk_plugin, mock_tenant_config, valid_ticket_response
    ):
        """Test successful ticket retrieval from API."""
        # Arrange: Mock TenantService and API client
        with patch("src.plugins.servicedesk_plus.plugin.get_db_session") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session


            with patch("src.plugins.servicedesk_plus.plugin.get_redis_client") as mock_redis_fn:
                mock_redis = AsyncMock()
                mock_redis_fn.return_value = mock_redis

            with patch("src.plugins.servicedesk_plus.plugin.TenantService") as mock_tenant_service:
                mock_service = AsyncMock()
                mock_service.get_tenant_config.return_value = mock_tenant_config
                mock_tenant_service.return_value = mock_service

                with patch(
                    "src.plugins.servicedesk_plus.plugin.ServiceDeskAPIClient"
                ) as mock_api_client_class:
                    mock_api_client = AsyncMock(spec=ServiceDeskAPIClient)
                    mock_api_client.get_ticket.return_value = valid_ticket_response
                    mock_api_client.close = AsyncMock()
                    mock_api_client_class.return_value = mock_api_client

                    # Act: Get ticket
                    ticket_data = await servicedesk_plugin.get_ticket(
                        tenant_id="acme-corp", ticket_id="12345"
                    )

                    # Assert: Ticket data returned
                    assert ticket_data == valid_ticket_response
                    mock_api_client.get_ticket.assert_awaited_once_with("12345")
                    mock_api_client.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_ticket_not_found(self, servicedesk_plugin, mock_tenant_config):
        """Test get_ticket returns None when ticket not found (404)."""
        # Arrange: Mock API client to return None (404)
        with patch("src.plugins.servicedesk_plus.plugin.get_db_session") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session


            with patch("src.plugins.servicedesk_plus.plugin.get_redis_client") as mock_redis_fn:
                mock_redis = AsyncMock()
                mock_redis_fn.return_value = mock_redis

            with patch("src.plugins.servicedesk_plus.plugin.TenantService") as mock_tenant_service:
                mock_service = AsyncMock()
                mock_service.get_tenant_config.return_value = mock_tenant_config
                mock_tenant_service.return_value = mock_service

                with patch(
                    "src.plugins.servicedesk_plus.plugin.ServiceDeskAPIClient"
                ) as mock_api_client_class:
                    mock_api_client = AsyncMock(spec=ServiceDeskAPIClient)
                    mock_api_client.get_ticket.return_value = None  # 404 Not Found
                    mock_api_client.close = AsyncMock()
                    mock_api_client_class.return_value = mock_api_client

                    # Act: Get non-existent ticket
                    ticket_data = await servicedesk_plugin.get_ticket(
                        tenant_id="acme-corp", ticket_id="99999"
                    )

                    # Assert: Returns None
                    assert ticket_data is None

    @pytest.mark.asyncio
    async def test_get_ticket_api_error(self, servicedesk_plugin, mock_tenant_config):
        """Test get_ticket returns None when API error occurs."""
        # Arrange: Mock API client to raise ServiceDeskAPIError
        with patch("src.plugins.servicedesk_plus.plugin.get_db_session") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session


            with patch("src.plugins.servicedesk_plus.plugin.get_redis_client") as mock_redis_fn:
                mock_redis = AsyncMock()
                mock_redis_fn.return_value = mock_redis

            with patch("src.plugins.servicedesk_plus.plugin.TenantService") as mock_tenant_service:
                mock_service = AsyncMock()
                mock_service.get_tenant_config.return_value = mock_tenant_config
                mock_tenant_service.return_value = mock_service

                with patch(
                    "src.plugins.servicedesk_plus.plugin.ServiceDeskAPIClient"
                ) as mock_api_client_class:
                    mock_api_client = AsyncMock(spec=ServiceDeskAPIClient)
                    mock_api_client.get_ticket.side_effect = ServiceDeskAPIError(
                        "API request failed"
                    )
                    mock_api_client.close = AsyncMock()
                    mock_api_client_class.return_value = mock_api_client

                    # Act: Get ticket (API error occurs)
                    ticket_data = await servicedesk_plugin.get_ticket(
                        tenant_id="acme-corp", ticket_id="12345"
                    )

                    # Assert: Returns None on error
                    assert ticket_data is None

    @pytest.mark.asyncio
    async def test_get_ticket_tenant_not_found(self, servicedesk_plugin):
        """Test get_ticket returns None when tenant not found."""
        # Arrange: Mock TenantService to raise TenantNotFoundException
        with patch("src.plugins.servicedesk_plus.plugin.get_db_session") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session


            with patch("src.plugins.servicedesk_plus.plugin.get_redis_client") as mock_redis_fn:
                mock_redis = AsyncMock()
                mock_redis_fn.return_value = mock_redis

            with patch("src.plugins.servicedesk_plus.plugin.TenantService") as mock_tenant_service:
                mock_service = AsyncMock()
                mock_service.get_tenant_config.side_effect = TenantNotFoundException(
                    "Tenant 'nonexistent' not found"
                )
                mock_tenant_service.return_value = mock_service

                # Act: Get ticket for nonexistent tenant
                ticket_data = await servicedesk_plugin.get_ticket(
                    tenant_id="nonexistent", ticket_id="12345"
                )

                # Assert: Returns None
                assert ticket_data is None


# ============================================================================
# Test update_ticket() method
# ============================================================================


class TestUpdateTicket:
    """Test ticket updates via ServiceDesk Plus API."""

    @pytest.mark.asyncio
    async def test_update_ticket_success(self, servicedesk_plugin, mock_tenant_config):
        """Test successful ticket update via API."""
        # Arrange: Mock TenantService and API client
        enhancement_content = "**Similar Tickets:**\n- TKT-100: Resolved by restart"

        with patch("src.plugins.servicedesk_plus.plugin.get_db_session") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session


            with patch("src.plugins.servicedesk_plus.plugin.get_redis_client") as mock_redis_fn:
                mock_redis = AsyncMock()
                mock_redis_fn.return_value = mock_redis

            with patch("src.plugins.servicedesk_plus.plugin.TenantService") as mock_tenant_service:
                mock_service = AsyncMock()
                mock_service.get_tenant_config.return_value = mock_tenant_config
                mock_tenant_service.return_value = mock_service

                with patch(
                    "src.plugins.servicedesk_plus.plugin.ServiceDeskAPIClient"
                ) as mock_api_client_class:
                    mock_api_client = AsyncMock(spec=ServiceDeskAPIClient)
                    mock_api_client.update_ticket.return_value = True  # Success
                    mock_api_client.close = AsyncMock()
                    mock_api_client_class.return_value = mock_api_client

                    # Act: Update ticket
                    success = await servicedesk_plugin.update_ticket(
                        tenant_id="acme-corp",
                        ticket_id="12345",
                        content=enhancement_content,
                    )

                    # Assert: Update succeeded
                    assert success is True
                    mock_api_client.update_ticket.assert_awaited_once_with(
                        "12345", enhancement_content
                    )
                    mock_api_client.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_ticket_failure(self, servicedesk_plugin, mock_tenant_config):
        """Test update_ticket returns False when API call fails."""
        # Arrange: Mock API client to return False (update failed)
        with patch("src.plugins.servicedesk_plus.plugin.get_db_session") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session


            with patch("src.plugins.servicedesk_plus.plugin.get_redis_client") as mock_redis_fn:
                mock_redis = AsyncMock()
                mock_redis_fn.return_value = mock_redis

            with patch("src.plugins.servicedesk_plus.plugin.TenantService") as mock_tenant_service:
                mock_service = AsyncMock()
                mock_service.get_tenant_config.return_value = mock_tenant_config
                mock_tenant_service.return_value = mock_service

                with patch(
                    "src.plugins.servicedesk_plus.plugin.ServiceDeskAPIClient"
                ) as mock_api_client_class:
                    mock_api_client = AsyncMock(spec=ServiceDeskAPIClient)
                    mock_api_client.update_ticket.return_value = False  # Failure
                    mock_api_client.close = AsyncMock()
                    mock_api_client_class.return_value = mock_api_client

                    # Act: Update ticket (fails)
                    success = await servicedesk_plugin.update_ticket(
                        tenant_id="acme-corp", ticket_id="12345", content="test"
                    )

                    # Assert: Returns False on failure
                    assert success is False

    @pytest.mark.asyncio
    async def test_update_ticket_authentication_error(self, servicedesk_plugin, mock_tenant_config):
        """Test update_ticket returns False on authentication error (401/403)."""
        # Arrange: Mock API client to raise ServiceDeskAuthenticationError
        with patch("src.plugins.servicedesk_plus.plugin.get_db_session") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session


            with patch("src.plugins.servicedesk_plus.plugin.get_redis_client") as mock_redis_fn:
                mock_redis = AsyncMock()
                mock_redis_fn.return_value = mock_redis

            with patch("src.plugins.servicedesk_plus.plugin.TenantService") as mock_tenant_service:
                mock_service = AsyncMock()
                mock_service.get_tenant_config.return_value = mock_tenant_config
                mock_tenant_service.return_value = mock_service

                with patch(
                    "src.plugins.servicedesk_plus.plugin.ServiceDeskAPIClient"
                ) as mock_api_client_class:
                    mock_api_client = AsyncMock(spec=ServiceDeskAPIClient)
                    mock_api_client.update_ticket.side_effect = ServiceDeskAuthenticationError(
                        "Invalid API key"
                    )
                    mock_api_client.close = AsyncMock()
                    mock_api_client_class.return_value = mock_api_client

                    # Act: Update ticket (authentication fails)
                    success = await servicedesk_plugin.update_ticket(
                        tenant_id="acme-corp", ticket_id="12345", content="test"
                    )

                    # Assert: Returns False on auth error
                    assert success is False

    @pytest.mark.asyncio
    async def test_update_ticket_tenant_not_found(self, servicedesk_plugin):
        """Test update_ticket returns False when tenant not found."""
        # Arrange: Mock TenantService to raise TenantNotFoundException
        with patch("src.plugins.servicedesk_plus.plugin.get_db_session") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session


            with patch("src.plugins.servicedesk_plus.plugin.get_redis_client") as mock_redis_fn:
                mock_redis = AsyncMock()
                mock_redis_fn.return_value = mock_redis

            with patch("src.plugins.servicedesk_plus.plugin.TenantService") as mock_tenant_service:
                mock_service = AsyncMock()
                mock_service.get_tenant_config.side_effect = TenantNotFoundException(
                    "Tenant 'nonexistent' not found"
                )
                mock_tenant_service.return_value = mock_service

                # Act: Update ticket for nonexistent tenant
                success = await servicedesk_plugin.update_ticket(
                    tenant_id="nonexistent", ticket_id="12345", content="test"
                )

                # Assert: Returns False
                assert success is False
