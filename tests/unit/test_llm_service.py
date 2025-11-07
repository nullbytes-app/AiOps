"""Unit tests for LLM Service (Story 8.9: Virtual Key Management).

Tests cover:
- Virtual key creation with budget constraints
- AsyncOpenAI client provisioning
- Key rotation logic
- Key validation
- Error handling (API failures, timeouts, encryption)
- Retry logic with exponential backoff
- Audit logging
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.services.llm_service import (
    LLMService,
    LLMServiceError,
    VirtualKeyCreationError,
    VirtualKeyRotationError,
    VirtualKeyValidationError,
)
from src.utils.encryption import EncryptionError
import httpx


@pytest.fixture
def mock_db_session():
    """Mock AsyncSession for database operations."""
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.add = MagicMock()
    return mock_db


@pytest.fixture
def llm_service(mock_db_session):
    """Create LLMService instance with mocked database."""
    return LLMService(
        db=mock_db_session,
        litellm_proxy_url="http://test-litellm:4000",
        master_key="test-master-key-123",
    )


class TestLLMServiceInitialization:
    """Test LLMService initialization and configuration."""

    def test_init_with_explicit_config(self, mock_db_session):
        """Test initialization with explicitly provided config."""
        service = LLMService(
            db=mock_db_session,
            litellm_proxy_url="http://custom-proxy:4000",
            master_key="custom-master-key",
        )
        assert service.litellm_proxy_url == "http://custom-proxy:4000"
        assert service.master_key == "custom-master-key"
        assert service.db == mock_db_session

    def test_init_removes_trailing_slash(self, mock_db_session):
        """Test that trailing slash is removed from proxy URL."""
        service = LLMService(
            db=mock_db_session,
            litellm_proxy_url="http://custom-proxy:4000/",
            master_key="custom-master-key",
        )
        assert service.litellm_proxy_url == "http://custom-proxy:4000"

    def test_init_missing_proxy_url(self, mock_db_session):
        """Test initialization fails without proxy URL."""
        with pytest.raises(ValueError, match="LITELLM_PROXY_URL not configured"):
            LLMService(db=mock_db_session, litellm_proxy_url=None, master_key="key")

    def test_init_missing_master_key(self, mock_db_session):
        """Test initialization fails without master key."""
        with pytest.raises(ValueError, match="LITELLM_MASTER_KEY not configured"):
            LLMService(
                db=mock_db_session, litellm_proxy_url="http://proxy:4000", master_key=None
            )


class TestCreateVirtualKey:
    """Test virtual key creation with LiteLLM API."""

    @pytest.mark.asyncio
    async def test_create_virtual_key_success(self, llm_service):
        """Test successful virtual key creation."""
        mock_response = {"key": "sk-test-virtual-key-123", "user_id": "test-tenant"}

        with patch.object(
            llm_service, "_call_litellm_api", return_value=mock_response
        ) as mock_call:
            virtual_key = await llm_service.create_virtual_key_for_tenant(
                tenant_id="test-tenant", max_budget=100.0
            )

            assert virtual_key == "sk-test-virtual-key-123"
            mock_call.assert_called_once()
            call_args = mock_call.call_args
            assert call_args[1]["method"] == "POST"
            assert call_args[1]["endpoint"] == "/key/generate"
            assert call_args[1]["json_data"]["user_id"] == "test-tenant"
            assert call_args[1]["json_data"]["max_budget"] == 100.0

    @pytest.mark.asyncio
    async def test_create_virtual_key_empty_tenant_id(self, llm_service):
        """Test create fails with empty tenant_id."""
        with pytest.raises(ValueError, match="tenant_id cannot be empty"):
            await llm_service.create_virtual_key_for_tenant(tenant_id="", max_budget=100.0)

    @pytest.mark.asyncio
    async def test_create_virtual_key_negative_budget(self, llm_service):
        """Test create fails with negative budget."""
        with pytest.raises(ValueError, match="max_budget must be >= 0"):
            await llm_service.create_virtual_key_for_tenant(
                tenant_id="test-tenant", max_budget=-10.0
            )

    @pytest.mark.asyncio
    async def test_create_virtual_key_api_returns_no_key(self, llm_service):
        """Test error handling when API returns no key."""
        mock_response = {"error": "something went wrong"}

        with patch.object(llm_service, "_call_litellm_api", return_value=mock_response):
            with pytest.raises(
                VirtualKeyCreationError, match="LiteLLM API returned no key"
            ):
                await llm_service.create_virtual_key_for_tenant(
                    tenant_id="test-tenant", max_budget=100.0
                )

    @pytest.mark.asyncio
    async def test_create_virtual_key_api_failure(self, llm_service):
        """Test error handling when API call fails."""
        with patch.object(
            llm_service,
            "_call_litellm_api",
            side_effect=LLMServiceError("API connection failed"),
        ):
            with pytest.raises(VirtualKeyCreationError, match="Failed to create virtual key"):
                await llm_service.create_virtual_key_for_tenant(
                    tenant_id="test-tenant", max_budget=100.0
                )


class TestGetLLMClient:
    """Test AsyncOpenAI client provisioning."""

    @pytest.mark.asyncio
    async def test_get_llm_client_success(self, llm_service, mock_db_session):
        """Test successful client retrieval with decrypted key."""
        # Mock database query result
        mock_result = MagicMock()
        mock_row = ["gAAAAABencrypted_virtual_key_base64=="]
        mock_result.fetchone.return_value = mock_row
        mock_db_session.execute.return_value = mock_result

        # Mock decryption
        with patch("src.services.llm_service.decrypt", return_value="sk-decrypted-key-123"):
            client = await llm_service.get_llm_client_for_tenant("test-tenant")

            # AsyncOpenAI adds trailing slash automatically
            assert str(client.base_url).rstrip("/") == "http://test-litellm:4000/v1"
            assert client.api_key == "sk-decrypted-key-123"
            assert client.timeout == 30.0

    @pytest.mark.asyncio
    async def test_get_llm_client_tenant_not_found(self, llm_service, mock_db_session):
        """Test error when tenant doesn't exist."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Tenant not found or inactive"):
            await llm_service.get_llm_client_for_tenant("nonexistent-tenant")

    @pytest.mark.asyncio
    async def test_get_llm_client_no_virtual_key(self, llm_service, mock_db_session):
        """Test error when tenant has no virtual key."""
        mock_result = MagicMock()
        mock_row = [None]  # Virtual key is None
        mock_result.fetchone.return_value = mock_row
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Virtual key not configured"):
            await llm_service.get_llm_client_for_tenant("test-tenant")

    @pytest.mark.asyncio
    async def test_get_llm_client_decryption_failure(self, llm_service, mock_db_session):
        """Test error when decryption fails."""
        mock_result = MagicMock()
        mock_row = ["corrupted_encrypted_data"]
        mock_result.fetchone.return_value = mock_row
        mock_db_session.execute.return_value = mock_result

        with patch(
            "src.services.llm_service.decrypt",
            side_effect=EncryptionError("Decryption failed"),
        ):
            with pytest.raises(EncryptionError):
                await llm_service.get_llm_client_for_tenant("test-tenant")


class TestRotateVirtualKey:
    """Test virtual key rotation logic."""

    @pytest.mark.asyncio
    async def test_rotate_virtual_key_success(self, llm_service, mock_db_session):
        """Test successful key rotation."""
        # Mock tenant exists check
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (1,)  # Tenant exists
        mock_db_session.execute.return_value = mock_result

        # Mock create_virtual_key_for_tenant
        with patch.object(
            llm_service,
            "create_virtual_key_for_tenant",
            return_value="sk-new-rotated-key-456",
        ):
            new_key = await llm_service.rotate_virtual_key("test-tenant")

            assert new_key == "sk-new-rotated-key-456"

    @pytest.mark.asyncio
    async def test_rotate_virtual_key_tenant_not_found(self, llm_service, mock_db_session):
        """Test rotation fails when tenant doesn't exist."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Tenant not found or inactive"):
            await llm_service.rotate_virtual_key("nonexistent-tenant")

    @pytest.mark.asyncio
    async def test_rotate_virtual_key_creation_fails(self, llm_service, mock_db_session):
        """Test rotation fails when new key creation fails."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (1,)
        mock_db_session.execute.return_value = mock_result

        with patch.object(
            llm_service,
            "create_virtual_key_for_tenant",
            side_effect=VirtualKeyCreationError("API error"),
        ):
            with pytest.raises(VirtualKeyRotationError, match="Failed to rotate virtual key"):
                await llm_service.rotate_virtual_key("test-tenant")


class TestValidateVirtualKey:
    """Test virtual key validation."""

    @pytest.mark.asyncio
    async def test_validate_virtual_key_valid(self, llm_service):
        """Test validation of valid key."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            is_valid = await llm_service.validate_virtual_key("sk-valid-key-123")

            assert is_valid is True
            mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_virtual_key_invalid(self, llm_service):
        """Test validation of invalid key."""
        mock_response = MagicMock()
        mock_response.status_code = 401  # Unauthorized

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            is_valid = await llm_service.validate_virtual_key("sk-invalid-key-123")

            assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_virtual_key_wrong_format(self, llm_service):
        """Test validation fails for wrong key format."""
        is_valid = await llm_service.validate_virtual_key("not-a-valid-format")
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_virtual_key_api_error(self, llm_service):
        """Test validation returns False on API error."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("Timeout")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            is_valid = await llm_service.validate_virtual_key("sk-test-key-123")

            assert is_valid is False


class TestRetryLogic:
    """Test retry logic with exponential backoff."""

    @pytest.mark.asyncio
    async def test_api_call_retry_on_5xx_error(self, llm_service):
        """Test API call retries on 5xx errors."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            # First 2 calls fail, 3rd succeeds
            mock_client.request.side_effect = [
                mock_response,
                mock_response,
                MagicMock(status_code=200, json=lambda: {"key": "sk-success-key"}),
            ]
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with patch("asyncio.sleep"):  # Skip actual delays
                result = await llm_service._call_litellm_api(
                    method="POST", endpoint="/key/generate", json_data={}
                )

                assert result["key"] == "sk-success-key"
                assert mock_client.request.call_count == 3

    @pytest.mark.asyncio
    async def test_api_call_no_retry_on_4xx_error(self, llm_service):
        """Test API call doesn't retry on 4xx errors."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(LLMServiceError, match="LiteLLM API error 400"):
                await llm_service._call_litellm_api(
                    method="POST", endpoint="/key/generate", json_data={}
                )

            # Should only call once (no retry on 4xx)
            assert mock_client.request.call_count == 1

    @pytest.mark.asyncio
    async def test_api_call_timeout_with_retry(self, llm_service):
        """Test API call retries on timeout."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            # First 2 calls timeout, 3rd succeeds
            mock_client.request.side_effect = [
                httpx.TimeoutException("Request timeout"),
                httpx.TimeoutException("Request timeout"),
                MagicMock(status_code=200, json=lambda: {"key": "sk-success-key"}),
            ]
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with patch("asyncio.sleep"):  # Skip actual delays
                result = await llm_service._call_litellm_api(
                    method="POST", endpoint="/key/generate", json_data={}
                )

                assert result["key"] == "sk-success-key"
                assert mock_client.request.call_count == 3


class TestAuditLogging:
    """Test audit logging functionality."""

    @pytest.mark.asyncio
    async def test_log_audit_entry_success(self, llm_service, mock_db_session):
        """Test successful audit log entry creation."""
        await llm_service.log_audit_entry(
            operation="llm_key_created",
            tenant_id="test-tenant",
            user="admin",
            details={"max_budget": 100.0},
            status="success",
        )

        # Verify database operations
        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_called_once()

        # Verify AuditLog object was created correctly
        audit_log = mock_db_session.add.call_args[0][0]
        assert audit_log.operation == "llm_key_created"
        assert audit_log.user == "admin"
        assert audit_log.details == {"max_budget": 100.0}
        assert audit_log.status == "success"

    @pytest.mark.asyncio
    async def test_log_audit_entry_defaults(self, llm_service, mock_db_session):
        """Test audit logging with default values."""
        await llm_service.log_audit_entry(operation="llm_key_validated")

        audit_log = mock_db_session.add.call_args[0][0]
        assert audit_log.operation == "llm_key_validated"
        assert audit_log.user == "system"
        assert audit_log.details == {}
        assert audit_log.status == "success"
