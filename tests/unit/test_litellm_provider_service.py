"""
Unit tests for LiteLLMProviderService.

Story 9.2: Provider Management via LiteLLM API
Tests for LiteLLM proxy API integration.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from src.services.litellm_provider_service import LiteLLMProviderService


class TestLiteLLMProviderService:
    """Test suite for LiteLLMProviderService."""

    @pytest.fixture
    def service(self):
        """Create service instance with test config."""
        return LiteLLMProviderService(
            base_url="http://litellm-test:4000",
            master_key="test-master-key",
        )

    @pytest.mark.asyncio
    async def test_add_model_success(self, service):
        """Test successfully adding a model to LiteLLM."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "model_id": "gpt-4-production",
            "message": "Model added successfully",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.post.return_value = mock_response
            mock_client.return_value = mock_instance

            result = await service.add_model_to_litellm(
                model_name="gpt-4-production",
                litellm_params={
                    "model": "openai/gpt-4",
                    "api_key": "sk-test123",
                },
            )

            assert result["status"] == "success"
            assert result["model_id"] == "gpt-4-production"
            mock_instance.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_model_with_optional_fields(self, service):
        """Test adding model with optional model_info and api_base."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.post.return_value = mock_response
            mock_client.return_value = mock_instance

            result = await service.add_model_to_litellm(
                model_name="azure-gpt-turbo",
                litellm_params={
                    "model": "azure/gpt-3.5-turbo",
                    "api_key": "sk-test",
                    "api_base": "https://my-azure.openai.azure.com",
                },
                model_info={
                    "description": "Test model",
                    "tags": ["test", "azure"],
                },
            )

            assert result["status"] == "success"
            call_args = mock_instance.post.call_args
            payload = call_args.kwargs["json"]
            assert payload["model_info"]["description"] == "Test model"

    @pytest.mark.asyncio
    async def test_add_model_http_error(self, service):
        """Test handling of HTTP errors when adding model."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.post.return_value = mock_response
            mock_instance.post.side_effect = Exception("401 Unauthorized")
            mock_client.return_value = mock_instance

            with pytest.raises(Exception):
                await service.add_model_to_litellm(
                    model_name="test",
                    litellm_params={"model": "openai/gpt-4", "api_key": "bad"},
                )

    @pytest.mark.asyncio
    async def test_list_models_success_new_format(self, service):
        """Test successfully listing models (new /v1/model/info format)."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "model_name": "gpt-4",
                    "litellm_params": {"model": "openai/gpt-4"},
                    "model_info": {"max_tokens": 8192},
                },
                {
                    "model_name": "claude-3",
                    "litellm_params": {"model": "anthropic/claude-3-opus-20240229"},
                    "model_info": {"max_tokens": 200000},
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.get.return_value = mock_response
            mock_client.return_value = mock_instance

            result = await service.list_models()

            assert len(result) == 2
            assert result[0]["model_name"] == "gpt-4"
            assert result[1]["model_info"]["max_tokens"] == 200000

    @pytest.mark.asyncio
    async def test_list_models_success_old_format(self, service):
        """Test listing models (old dict format)."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "gpt-4": {
                "litellm_params": {"model": "openai/gpt-4"},
                "model_info": {"max_tokens": 8192},
            },
            "claude-3": {
                "litellm_params": {"model": "anthropic/claude-3-opus"},
                "model_info": {"max_tokens": 200000},
            },
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.get.return_value = mock_response
            mock_client.return_value = mock_instance

            result = await service.list_models()

            assert len(result) == 2
            model_names = [m["model_name"] for m in result]
            assert "gpt-4" in model_names
            assert "claude-3" in model_names

    @pytest.mark.asyncio
    async def test_list_models_empty(self, service):
        """Test listing models when none are configured."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.get.return_value = mock_response
            mock_client.return_value = mock_instance

            result = await service.list_models()

            assert result == []

    @pytest.mark.asyncio
    async def test_delete_model_success(self, service):
        """Test successfully deleting a model."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success", "message": "Model deleted"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.post.return_value = mock_response
            mock_client.return_value = mock_instance

            result = await service.delete_model("gpt-4-production")

            assert result["status"] == "success"
            mock_instance.post.assert_called_once()
            call_args = mock_instance.post.call_args
            assert call_args.kwargs["json"]["model_id"] == "gpt-4-production"

    @pytest.mark.asyncio
    async def test_delete_model_not_found(self, service):
        """Test deleting a model that doesn't exist."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Model not found"
        mock_response.raise_for_status.side_effect = Exception("404 Not found")

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.post.side_effect = Exception("404 Not found")
            mock_client.return_value = mock_instance

            with pytest.raises(Exception):
                await service.delete_model("nonexistent-model")

    def test_auth_headers_generated(self, service):
        """Test that authorization headers are correctly generated."""
        headers = service._get_auth_headers()

        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-master-key"

    def test_missing_master_key_warning(self, caplog):
        """Test that missing LITELLM_MASTER_KEY generates warning."""
        with patch.dict("os.environ", {"LITELLM_MASTER_KEY": ""}):
            service = LiteLLMProviderService(
                base_url="http://litellm:4000",
                master_key="",
            )
            assert service.master_key == ""

    def test_service_initialization_with_defaults(self):
        """Test service initializes with default URL from env."""
        with patch.dict("os.environ", {"LITELLM_URL": "http://custom:4000"}):
            service = LiteLLMProviderService()
            assert service.base_url == "http://custom:4000"

    @pytest.mark.asyncio
    async def test_timeout_configuration(self, service):
        """Test that timeout is properly configured."""
        # httpx.Timeout has connect, read, write, and pool attributes
        assert service.timeout.connect == 5.0
        assert service.timeout.read == 30.0
        assert service.timeout.write == 5.0
        assert service.timeout.pool == 5.0
