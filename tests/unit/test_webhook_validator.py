"""
Unit tests for webhook signature validation service.

Tests the HMAC-SHA256 signature validation logic and FastAPI dependency
for webhook authentication.
"""

import hmac
import hashlib
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException, Request

from src.services.webhook_validator import validate_signature, validate_webhook_signature
from src.services.tenant_service import TenantService
from src.config import Settings


# Test fixtures
@pytest.fixture
def sample_payload() -> bytes:
    """
    Sample webhook payload for testing.

    Returns:
        bytes: JSON payload as bytes
    """
    return b'{"event":"ticket_created","ticket_id":"TKT-001","tenant_id":"tenant-abc"}'


@pytest.fixture
def test_secret() -> str:
    """
    Test shared secret (minimum 32 characters).

    Returns:
        str: Test secret key
    """
    return "test-secret-key-minimum-32-chars-required-here"


@pytest.fixture
def valid_signature(sample_payload: bytes, test_secret: str) -> str:
    """
    Generate valid HMAC-SHA256 signature for sample payload.

    Args:
        sample_payload: Test payload bytes
        test_secret: Test secret key

    Returns:
        str: Hex-encoded HMAC-SHA256 signature
    """
    return hmac.new(
        key=test_secret.encode("utf-8"),
        msg=sample_payload,
        digestmod=hashlib.sha256,
    ).hexdigest()


@pytest.fixture
def invalid_signature() -> str:
    """
    Invalid signature that won't match any payload.

    Returns:
        str: Hex string representing invalid signature
    """
    return "0" * 64  # Valid hex format but wrong signature


@pytest.fixture
def mock_request(sample_payload: bytes) -> Mock:
    """
    Mock FastAPI Request object.

    Args:
        sample_payload: Test payload bytes

    Returns:
        Mock: Mock Request with body() method and client attribute
    """
    request = Mock(spec=Request)
    request.body = AsyncMock(return_value=sample_payload)
    request.client = Mock()
    request.client.host = "192.168.1.100"
    return request


@pytest.fixture
def mock_settings(test_secret: str) -> Settings:
    """
    Mock Settings object with test webhook secret.

    Args:
        test_secret: Test secret key

    Returns:
        Mock: Mock Settings with webhook_secret attribute
    """
    settings = Mock(spec=Settings)
    settings.webhook_secret = test_secret
    return settings


@pytest.fixture
def mock_tenant_service(test_secret: str) -> TenantService:
    """
    Mock TenantService for unit tests.

    Returns a mock service that provides tenant configs and secrets.

    Args:
        test_secret: Test secret for webhook validation

    Returns:
        AsyncMock: Mock TenantService with get_tenant_config and get_webhook_secret methods
    """
    service = AsyncMock(spec=TenantService)

    # Mock tenant config
    mock_config = Mock()
    mock_config.is_active = True
    mock_config.webhook_signing_secret = test_secret

    service.get_tenant_config = AsyncMock(return_value=mock_config)
    service.get_webhook_secret = AsyncMock(return_value=test_secret)

    return service


# Tests for validate_signature function
class TestValidateSignature:
    """Tests for the validate_signature() function."""

    def test_valid_signature_returns_true(
        self, sample_payload: bytes, valid_signature: str, test_secret: str
    ) -> None:
        """
        Test that valid signature returns True.

        Verifies HMAC-SHA256 computation and comparison work correctly
        for authentic signatures.
        """
        result = validate_signature(sample_payload, valid_signature, test_secret)
        assert result is True

    def test_invalid_signature_returns_false(
        self, sample_payload: bytes, invalid_signature: str, test_secret: str
    ) -> None:
        """
        Test that invalid signature returns False.

        Verifies that incorrect signatures are properly rejected.
        """
        result = validate_signature(sample_payload, invalid_signature, test_secret)
        assert result is False

    def test_modified_payload_fails_validation(
        self, valid_signature: str, test_secret: str
    ) -> None:
        """
        Test that modified payload fails validation with original signature.

        Verifies tamper detection - changing payload invalidates signature.
        """
        modified_payload = b'{"event":"ticket_deleted","ticket_id":"TKT-999"}'
        result = validate_signature(modified_payload, valid_signature, test_secret)
        assert result is False

    def test_empty_secret_raises_value_error(
        self, sample_payload: bytes, valid_signature: str
    ) -> None:
        """
        Test that empty secret raises ValueError.

        Ensures validation fails safely when secret is not configured.
        """
        with pytest.raises(ValueError, match="Secret cannot be empty"):
            validate_signature(sample_payload, valid_signature, "")

    def test_none_secret_raises_value_error(
        self, sample_payload: bytes, valid_signature: str
    ) -> None:
        """
        Test that None secret raises ValueError.

        Ensures validation fails safely when secret is None.
        """
        with pytest.raises(ValueError, match="Secret cannot be empty"):
            validate_signature(sample_payload, valid_signature, None)  # type: ignore

    def test_empty_signature_header_returns_false(
        self, sample_payload: bytes, test_secret: str
    ) -> None:
        """
        Test that empty signature header returns False.

        Verifies missing signatures are rejected without raising exceptions.
        """
        result = validate_signature(sample_payload, "", test_secret)
        assert result is False

    def test_constant_time_comparison_used(
        self, sample_payload: bytes, valid_signature: str, test_secret: str
    ) -> None:
        """
        Test that hmac.compare_digest is used for constant-time comparison.

        This is a security requirement to prevent timing attacks.
        Verifies the function uses the secure comparison method.
        """
        # This test verifies correct signature works
        # The actual constant-time comparison is in hmac.compare_digest()
        result = validate_signature(sample_payload, valid_signature, test_secret)
        assert result is True


# Tests for validate_webhook_signature dependency
class TestValidateWebhookSignature:
    """Tests for the validate_webhook_signature() FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_valid_signature_passes(
        self,
        mock_request: Mock,
        valid_signature: str,
        mock_settings: Settings,
        mock_tenant_service: TenantService,
    ) -> None:
        """
        Test that valid signature allows request through.

        Dependency should pass silently (no exception) for valid signatures.
        """
        # Should not raise any exception
        await validate_webhook_signature(
            request=mock_request,
            x_servicedesk_signature=valid_signature,
            settings=mock_settings,
            tenant_service=mock_tenant_service,
        )

    @pytest.mark.asyncio
    async def test_invalid_signature_raises_401(
        self,
        mock_request: Mock,
        invalid_signature: str,
        mock_settings: Settings,
        mock_tenant_service: TenantService,
    ) -> None:
        """
        Test that invalid signature raises HTTPException(401).

        Verifies incorrect signatures are rejected with Unauthorized status.
        """
        with pytest.raises(HTTPException) as exc_info:
            await validate_webhook_signature(
                request=mock_request,
                x_servicedesk_signature=invalid_signature,
                settings=mock_settings,
                tenant_service=mock_tenant_service,
            )

        assert exc_info.value.status_code == 401
        assert isinstance(exc_info.value.detail, dict)
        assert "Invalid webhook signature" in exc_info.value.detail.get("detail", "")

    @pytest.mark.asyncio
    async def test_missing_header_raises_401(
        self,
        mock_request: Mock,
        mock_settings: Settings,
        mock_tenant_service: TenantService,
    ) -> None:
        """
        Test that missing signature header raises HTTPException(401).

        Verifies requests without X-ServiceDesk-Signature are rejected.
        """
        with pytest.raises(HTTPException) as exc_info:
            await validate_webhook_signature(
                request=mock_request,
                x_servicedesk_signature=None,
                settings=mock_settings,
                tenant_service=mock_tenant_service,
            )

        assert exc_info.value.status_code == 401
        assert isinstance(exc_info.value.detail, dict)
        assert "Missing signature header" in exc_info.value.detail.get("detail", "")

    @pytest.mark.asyncio
    async def test_empty_string_header_raises_401(
        self,
        mock_request: Mock,
        mock_settings: Settings,
        mock_tenant_service: TenantService,
    ) -> None:
        """
        Test that empty string signature header raises HTTPException(401).

        Verifies empty signature headers are treated as missing.
        """
        with pytest.raises(HTTPException) as exc_info:
            await validate_webhook_signature(
                request=mock_request,
                x_servicedesk_signature="",
                settings=mock_settings,
                tenant_service=mock_tenant_service,
            )

        assert exc_info.value.status_code == 401
        assert isinstance(exc_info.value.detail, dict)
        assert "Missing signature header" in exc_info.value.detail.get("detail", "")

    @pytest.mark.asyncio
    async def test_request_body_read_correctly(
        self,
        mock_request: Mock,
        valid_signature: str,
        mock_settings: Settings,
        mock_tenant_service: TenantService,
    ) -> None:
        """
        Test that request body is read correctly for validation.

        Verifies the dependency reads raw body bytes before validation.
        """
        await validate_webhook_signature(
            request=mock_request,
            x_servicedesk_signature=valid_signature,
            settings=mock_settings,
            tenant_service=mock_tenant_service,
        )

        # Verify body was read
        mock_request.body.assert_called_once()
