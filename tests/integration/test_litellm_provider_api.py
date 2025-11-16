"""
Integration tests for LiteLLM Provider API (Story 9.2).

Tests the full flow of:
- Adding models via /model/new
- Listing models via /v1/model/info
- Deleting models via /model/delete
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from src.services.litellm_provider_service import LiteLLMProviderService


@pytest.mark.asyncio
class TestLiteLLMProviderAPIIntegration:
    """Integration tests for LiteLLM provider API."""

    @pytest.fixture
    def service(self):
        """Create service with test configuration."""
        return LiteLLMProviderService(
            base_url="http://litellm-test:4000",
            master_key="test-key-123",
        )

    async def test_full_model_lifecycle(self, service):
        """Test complete flow: add -> list -> delete."""
        # Mock responses
        add_response = MagicMock()
        add_response.json.return_value = {"status": "success", "model_id": "test-model"}
        add_response.raise_for_status = MagicMock()

        list_response = MagicMock()
        list_response.json.return_value = {
            "data": [
                {
                    "model_name": "test-model",
                    "litellm_params": {"model": "openai/gpt-4"},
                    "model_info": {"max_tokens": 8192},
                }
            ]
        }
        list_response.raise_for_status = MagicMock()

        delete_response = MagicMock()
        delete_response.json.return_value = {"status": "success"}
        delete_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance

            # Setup sequential responses
            mock_instance.post.return_value = add_response
            mock_instance.get.return_value = list_response
            mock_client.return_value = mock_instance

            # Step 1: Add model
            add_result = await service.add_model_to_litellm(
                model_name="test-model",
                litellm_params={"model": "openai/gpt-4", "api_key": "sk-test"},
            )
            assert add_result["status"] == "success"

            # Step 2: List models
            list_result = await service.list_models()
            assert len(list_result) == 1
            assert list_result[0]["model_name"] == "test-model"

            # Step 3: Delete model
            mock_instance.post.return_value = delete_response
            delete_result = await service.delete_model("test-model")
            assert delete_result["status"] == "success"

    async def test_add_openai_model_integration(self, service):
        """Test adding an OpenAI model with full parameters."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "model_id": "gpt-4-turbo-production",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.post.return_value = mock_response
            mock_client.return_value = mock_instance

            result = await service.add_model_to_litellm(
                model_name="gpt-4-turbo-production",
                litellm_params={
                    "model": "openai/gpt-4-turbo-preview",
                    "api_key": "sk-proj-1234567890",
                },
                model_info={
                    "description": "GPT-4 Turbo for production use",
                    "tags": ["production", "high-capacity"],
                },
            )

            assert result["status"] == "success"
            assert result["model_id"] == "gpt-4-turbo-production"

            # Verify call was made correctly
            call_args = mock_instance.post.call_args
            assert call_args.kwargs["headers"]["Authorization"] == "Bearer test-key-123"
            payload = call_args.kwargs["json"]
            assert payload["model_name"] == "gpt-4-turbo-production"
            assert "production" in payload["model_info"]["tags"]

    async def test_add_anthropic_model_integration(self, service):
        """Test adding an Anthropic model."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.post.return_value = mock_response
            mock_client.return_value = mock_instance

            result = await service.add_model_to_litellm(
                model_name="claude-3-opus",
                litellm_params={
                    "model": "anthropic/claude-3-opus-20240229",
                    "api_key": "sk-ant-abc123def456",
                },
            )

            assert result["status"] == "success"

    async def test_add_azure_model_with_custom_base(self, service):
        """Test adding an Azure OpenAI model with custom API base."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.post.return_value = mock_response
            mock_client.return_value = mock_instance

            result = await service.add_model_to_litellm(
                model_name="azure-gpt-4",
                litellm_params={
                    "model": "azure/gpt-4",
                    "api_key": "os.environ/AZURE_API_KEY",
                    "api_base": "https://my-resource.openai.azure.com/",
                },
                model_info={"description": "Azure GPT-4 deployment"},
            )

            assert result["status"] == "success"

            # Verify api_base was included
            call_args = mock_instance.post.call_args
            payload = call_args.kwargs["json"]
            assert payload["litellm_params"]["api_base"] == "https://my-resource.openai.azure.com/"

    async def test_list_mixed_providers(self, service):
        """Test listing models from multiple providers."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "model_name": "gpt-4-prod",
                    "litellm_params": {"model": "openai/gpt-4"},
                    "model_info": {"max_tokens": 8192, "input_cost_per_token": 0.00003},
                },
                {
                    "model_name": "claude-opus",
                    "litellm_params": {"model": "anthropic/claude-3-opus-20240229"},
                    "model_info": {"max_tokens": 200000},
                },
                {
                    "model_name": "azure-turbo",
                    "litellm_params": {"model": "azure/gpt-3.5-turbo"},
                    "model_info": {"max_tokens": 4096},
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.get.return_value = mock_response
            mock_client.return_value = mock_instance

            models = await service.list_models()

            assert len(models) == 3
            providers = {m["litellm_params"]["model"].split("/")[0] for m in models}
            assert providers == {"openai", "anthropic", "azure"}

    async def test_error_handling_with_retry_context(self, service):
        """Test that errors are properly logged and raised."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = Exception("500 Server Error")

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.post.side_effect = Exception("500 Server Error")
            mock_client.return_value = mock_instance

            with pytest.raises(Exception, match="500 Server Error"):
                await service.add_model_to_litellm(
                    model_name="test",
                    litellm_params={"model": "openai/gpt-4", "api_key": "sk-test"},
                )

    async def test_model_not_found_on_list(self, service):
        """Test listing when LiteLLM returns empty list."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.get.return_value = mock_response
            mock_client.return_value = mock_instance

            models = await service.list_models()

            assert models == []

    async def test_bulk_add_models(self, service):
        """Test adding multiple models sequentially."""
        models_to_add = [
            ("gpt-4", "openai/gpt-4"),
            ("gpt-3.5", "openai/gpt-3.5-turbo"),
            ("claude-3", "anthropic/claude-3-opus-20240229"),
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.post.return_value = mock_response
            mock_client.return_value = mock_instance

            for model_name, underlying_model in models_to_add:
                result = await service.add_model_to_litellm(
                    model_name=model_name,
                    litellm_params={
                        "model": underlying_model,
                        "api_key": f"key-for-{model_name}",
                    },
                )
                assert result["status"] == "success"

            # Verify all 3 POST calls were made
            assert mock_instance.post.call_count == 3
