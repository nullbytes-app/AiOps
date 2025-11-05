"""
Unit tests for Jira Service Management plugin.

Tests cover:
- Webhook signature validation
- Metadata extraction
- API client operations (get_issue, add_comment)
- ADF conversion
- Error handling

Minimum 15 tests required by AC7.
"""

import hmac
import hashlib
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from src.plugins.jira import JiraServiceManagementPlugin
from src.plugins.jira.api_client import JiraAPIClient, text_to_adf
from src.plugins.jira.webhook_validator import (
    compute_hmac_signature,
    parse_signature_header,
    secure_compare,
)
from src.plugins.base import TicketMetadata


# ===== Fixtures =====


@pytest.fixture
def jira_plugin():
    """Returns JiraServiceManagementPlugin instance."""
    return JiraServiceManagementPlugin()


@pytest.fixture
def valid_jira_webhook_payload():
    """Returns valid Jira issue_created webhook payload."""
    return {
        "timestamp": 1699200000000,
        "webhookEvent": "jira:issue_created",
        "issue": {
            "key": "PROJ-123",
            "fields": {
                "summary": "Server performance degradation",
                "description": "Production web server experiencing high CPU usage",
                "priority": {"name": "High"},
                "created": "2025-11-05T14:30:00.000+0000",
                "customfield_10000": "tenant-abc",
            },
        },
    }


@pytest.fixture
def mock_tenant_config():
    """Mock tenant configuration for Jira."""
    config = MagicMock()
    config.tenant_id = "tenant-abc"
    config.jira_url = "https://company.atlassian.net"
    config.jira_api_token = "test_api_token_123"
    config.webhook_signing_secret = "test_webhook_secret"
    config.is_active = True
    return config


# ===== Webhook Validation Tests (5 tests) =====


@pytest.mark.asyncio
async def test_validate_webhook_success(
    jira_plugin, valid_jira_webhook_payload, mock_tenant_config
):
    """Test webhook validation with valid X-Hub-Signature returns True."""
    # Compute valid signature
    payload_bytes = json.dumps(valid_jira_webhook_payload, sort_keys=True).encode("utf-8")
    expected_sig = hmac.new(
        mock_tenant_config.webhook_signing_secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    signature_header = f"sha256={expected_sig}"

    # Mock TenantService, database, and redis connections
    with (
        patch("src.plugins.jira.plugin.get_redis_client") as mock_redis,
        patch("src.plugins.jira.plugin.get_db_session") as mock_db,
        patch("src.plugins.jira.plugin.TenantService") as mock_service,
    ):

        # Setup redis and db session mocks
        mock_redis.return_value = AsyncMock()
        mock_db.return_value.__aenter__ = AsyncMock()
        mock_db.return_value.__aexit__ = AsyncMock()

        mock_instance = mock_service.return_value
        mock_instance.get_tenant_config = AsyncMock(return_value=mock_tenant_config)

        # Validate webhook
        result = await jira_plugin.validate_webhook(valid_jira_webhook_payload, signature_header)

        assert result is True


@pytest.mark.asyncio
async def test_validate_webhook_invalid_signature(
    jira_plugin, valid_jira_webhook_payload, mock_tenant_config
):
    """Test webhook validation with invalid signature returns False."""
    signature_header = "sha256=invalid_signature_12345"

    # Mock TenantService
    with patch("src.plugins.jira.plugin.TenantService") as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.get_tenant_config = AsyncMock(return_value=mock_tenant_config)

        # Validate webhook
        result = await jira_plugin.validate_webhook(valid_jira_webhook_payload, signature_header)

        assert result is False


@pytest.mark.asyncio
async def test_validate_webhook_missing_tenant(jira_plugin, valid_jira_webhook_payload):
    """Test webhook validation returns False when tenant not found."""
    signature_header = "sha256=abc123"

    # Mock TenantService to raise Exception (tenant not found)
    with patch("src.plugins.jira.plugin.TenantService") as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.get_tenant_config = AsyncMock(side_effect=Exception("Tenant not found"))

        # Validate webhook
        result = await jira_plugin.validate_webhook(valid_jira_webhook_payload, signature_header)

        assert result is False


@pytest.mark.asyncio
async def test_validate_webhook_inactive_tenant(
    jira_plugin, valid_jira_webhook_payload, mock_tenant_config
):
    """Test webhook validation returns False when tenant is inactive."""
    # Set tenant to inactive
    mock_tenant_config.is_active = False

    signature_header = "sha256=abc123"

    # Mock TenantService
    with patch("src.plugins.jira.plugin.TenantService") as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.get_tenant_config = AsyncMock(return_value=mock_tenant_config)

        # Validate webhook
        result = await jira_plugin.validate_webhook(valid_jira_webhook_payload, signature_header)

        assert result is False


def test_validate_webhook_malformed_header(jira_plugin, valid_jira_webhook_payload):
    """Test webhook validation raises ValueError for malformed signature header."""
    signature_header = "invalid_format_no_equals"

    # Should raise ValueError when parsing header
    with pytest.raises(ValueError):
        parse_signature_header(signature_header)


# ===== Metadata Extraction Tests (5 tests) =====


def test_extract_metadata_success(jira_plugin, valid_jira_webhook_payload):
    """Test metadata extraction with valid payload returns TicketMetadata."""
    metadata = jira_plugin.extract_metadata(valid_jira_webhook_payload)

    assert isinstance(metadata, TicketMetadata)
    assert metadata.tenant_id == "tenant-abc"
    assert metadata.ticket_id == "PROJ-123"
    assert metadata.description == "Production web server experiencing high CPU usage"
    assert metadata.priority == "high"  # Normalized from "High"
    assert isinstance(metadata.created_at, datetime)


def test_extract_metadata_missing_fields(jira_plugin):
    """Test metadata extraction raises ValueError when required fields missing."""
    incomplete_payload = {
        "issue": {
            "fields": {
                "summary": "Test",
            }
        }
    }

    with pytest.raises(ValueError, match="Missing required field"):
        jira_plugin.extract_metadata(incomplete_payload)


def test_extract_metadata_priority_normalization(jira_plugin):
    """Test priority normalization: 'Highest' -> 'high', 'Medium' -> 'medium', 'Lowest' -> 'low'."""
    # Test Highest -> high
    payload_highest = {
        "issue": {
            "key": "PROJ-1",
            "fields": {
                "summary": "Critical issue",
                "priority": {"name": "Highest"},
                "created": "2025-11-05T14:30:00.000+0000",
                "customfield_10000": "tenant-abc",
            },
        },
    }
    metadata = jira_plugin.extract_metadata(payload_highest)
    assert metadata.priority == "high"

    # Test Medium -> medium
    payload_medium = {
        "issue": {
            "key": "PROJ-2",
            "fields": {
                "summary": "Medium issue",
                "priority": {"name": "Medium"},
                "created": "2025-11-05T14:30:00.000+0000",
                "customfield_10000": "tenant-abc",
            },
        },
    }
    metadata = jira_plugin.extract_metadata(payload_medium)
    assert metadata.priority == "medium"

    # Test Lowest -> low
    payload_low = {
        "issue": {
            "key": "PROJ-3",
            "fields": {
                "summary": "Low issue",
                "priority": {"name": "Lowest"},
                "created": "2025-11-05T14:30:00.000+0000",
                "customfield_10000": "tenant-abc",
            },
        },
    }
    metadata = jira_plugin.extract_metadata(payload_low)
    assert metadata.priority == "low"


def test_extract_metadata_null_description(jira_plugin):
    """Test null description uses summary as fallback."""
    payload = {
        "issue": {
            "key": "PROJ-123",
            "fields": {
                "summary": "No description provided",
                "description": None,
                "priority": {"name": "High"},
                "created": "2025-11-05T14:30:00.000+0000",
                "customfield_10000": "tenant-abc",
            },
        },
    }

    metadata = jira_plugin.extract_metadata(payload)
    assert metadata.description == "No description provided"


def test_extract_metadata_invalid_datetime(jira_plugin):
    """Test invalid datetime format raises ValueError."""
    payload = {
        "issue": {
            "key": "PROJ-123",
            "fields": {
                "summary": "Test",
                "priority": {"name": "High"},
                "created": "invalid_date_format",
                "customfield_10000": "tenant-abc",
            },
        },
    }

    with pytest.raises(ValueError, match="Invalid datetime format"):
        jira_plugin.extract_metadata(payload)


# ===== API Client Tests (5 tests) =====


@pytest.mark.asyncio
async def test_get_ticket_success(jira_plugin, mock_tenant_config):
    """Test get_ticket returns issue data on successful API call."""
    expected_issue = {
        "key": "PROJ-123",
        "fields": {
            "summary": "Test issue",
            "description": "Test description",
        },
    }

    # Mock TenantService, API client, and database/redis connections
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

        mock_instance = mock_service.return_value
        mock_instance.get_tenant_config = AsyncMock(return_value=mock_tenant_config)

        mock_client = mock_client_class.return_value
        mock_client.get_issue = AsyncMock(return_value=expected_issue)
        mock_client.close = AsyncMock()

        # Get ticket
        result = await jira_plugin.get_ticket("tenant-abc", "PROJ-123")

        assert result == expected_issue
        mock_client.get_issue.assert_called_once_with("PROJ-123")
        mock_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_ticket_not_found(jira_plugin, mock_tenant_config):
    """Test get_ticket returns None when API returns 404."""
    # Mock TenantService and API client
    with (
        patch("src.plugins.jira.plugin.TenantService") as mock_service,
        patch("src.plugins.jira.plugin.JiraAPIClient") as mock_client_class,
    ):
        mock_instance = mock_service.return_value
        mock_instance.get_tenant_config = AsyncMock(return_value=mock_tenant_config)

        mock_client = mock_client_class.return_value
        mock_client.get_issue = AsyncMock(return_value=None)  # 404
        mock_client.close = AsyncMock()

        # Get ticket
        result = await jira_plugin.get_ticket("tenant-abc", "PROJ-999")

        assert result is None


@pytest.mark.asyncio
async def test_get_ticket_auth_error(jira_plugin):
    """Test get_ticket returns None when tenant not found."""
    # Mock TenantService to raise Exception (tenant not found)
    with patch("src.plugins.jira.plugin.TenantService") as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.get_tenant_config = AsyncMock(side_effect=Exception("Tenant not found"))

        # Get ticket
        result = await jira_plugin.get_ticket("nonexistent-tenant", "PROJ-123")

        assert result is None


@pytest.mark.asyncio
async def test_update_ticket_success(jira_plugin, mock_tenant_config):
    """Test update_ticket returns True on successful API call (201 Created)."""
    # Mock TenantService, API client, database, and redis connections
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

        mock_instance = mock_service.return_value
        mock_instance.get_tenant_config = AsyncMock(return_value=mock_tenant_config)

        mock_client = mock_client_class.return_value
        mock_client.add_comment = AsyncMock(return_value=True)  # 201 Created
        mock_client.close = AsyncMock()

        # Update ticket
        result = await jira_plugin.update_ticket("tenant-abc", "PROJ-123", "Enhancement content")

        assert result is True
        mock_client.add_comment.assert_called_once_with("PROJ-123", "Enhancement content")
        mock_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_update_ticket_failure(jira_plugin, mock_tenant_config):
    """Test update_ticket returns False on API error."""
    # Mock TenantService and API client
    with (
        patch("src.plugins.jira.plugin.TenantService") as mock_service,
        patch("src.plugins.jira.plugin.JiraAPIClient") as mock_client_class,
    ):
        mock_instance = mock_service.return_value
        mock_instance.get_tenant_config = AsyncMock(return_value=mock_tenant_config)

        mock_client = mock_client_class.return_value
        mock_client.add_comment = AsyncMock(return_value=False)  # API error
        mock_client.close = AsyncMock()

        # Update ticket
        result = await jira_plugin.update_ticket("tenant-abc", "PROJ-123", "Enhancement content")

        assert result is False


# ===== ADF Conversion Tests (2 tests) =====


def test_text_to_adf_conversion():
    """Test plain text to ADF conversion."""
    text = "Hello\nWorld"
    adf = text_to_adf(text)

    assert adf["type"] == "doc"
    assert adf["version"] == 1
    assert len(adf["content"]) == 2  # 2 paragraphs

    # First paragraph
    assert adf["content"][0]["type"] == "paragraph"
    assert adf["content"][0]["content"][0]["type"] == "text"
    assert adf["content"][0]["content"][0]["text"] == "Hello"

    # Second paragraph
    assert adf["content"][1]["type"] == "paragraph"
    assert adf["content"][1]["content"][0]["type"] == "text"
    assert adf["content"][1]["content"][0]["text"] == "World"


def test_text_to_adf_empty_text():
    """Test ADF conversion handles empty/whitespace text."""
    text = "   \n\n   "
    adf = text_to_adf(text)

    assert adf["type"] == "doc"
    assert adf["version"] == 1
    # Should have at least one empty paragraph
    assert len(adf["content"]) >= 1


# ===== Helper Function Tests (3 tests) =====


def test_compute_hmac_signature():
    """Test HMAC-SHA256 signature computation."""
    body = b'{"test": "data"}'
    secret = "my_secret"

    signature = compute_hmac_signature(body, secret)

    # Verify it's a 64-character hex string (SHA256)
    assert len(signature) == 64
    assert all(c in "0123456789abcdef" for c in signature)

    # Verify signature is deterministic
    signature2 = compute_hmac_signature(body, secret)
    assert signature == signature2


def test_parse_signature_header():
    """Test X-Hub-Signature header parsing."""
    # Valid header
    method, sig = parse_signature_header("sha256=abc123def456")
    assert method == "sha256"
    assert sig == "abc123def456"

    # Invalid format (no equals)
    with pytest.raises(ValueError, match="Invalid signature header format"):
        parse_signature_header("sha256_abc123")

    # Unsupported method
    with pytest.raises(ValueError, match="Unsupported signature method"):
        parse_signature_header("md5=abc123")


def test_secure_compare():
    """Test constant-time signature comparison."""
    # Matching signatures
    assert secure_compare("abc123", "abc123") is True

    # Non-matching signatures
    assert secure_compare("abc123", "def456") is False

    # Case-sensitive
    assert secure_compare("ABC123", "abc123") is False
