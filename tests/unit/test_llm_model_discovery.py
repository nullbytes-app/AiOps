"""
Unit tests for LLM Model Discovery Service.

Tests the ModelDiscoveryService for:
- Dynamic model fetching from LiteLLM /v1/model/info endpoint
- Cache validity checking with TTL expiry
- Error handling and graceful fallback
- Single model lookup

Story: 9.1 - Dynamic Model Discovery from LiteLLM
Target: >80% coverage with cache, error, and model lookup scenarios
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from src.services.llm_model_discovery import ModelDiscoveryService
from src.schemas.llm_models import ModelInfo


# Helper fixture
@pytest.fixture
def service():
    """Create a ModelDiscoveryService instance with test credentials."""
    return ModelDiscoveryService(
        litellm_proxy_url="http://test-litellm:4000",
        litellm_master_key="test-master-key"
    )


class TestModelDiscoveryServiceInitialization:
    """Test service initialization and cache state."""

    def test_service_initializes_with_custom_url(self, service):
        """Test service initializes with custom credentials."""
        assert service.litellm_proxy_url == "http://test-litellm:4000"
        assert service.litellm_master_key == "test-master-key"
        assert service._cache is None
        assert service._cache_expiry is None

    def test_cache_is_invalid_initially(self, service):
        """Test that cache is not valid on service initialization."""
        assert service._is_cache_valid() is False


class TestCacheValidity:
    """Test cache TTL and validity checking."""

    def test_cache_valid_when_not_expired(self, service):
        """Test cache is valid when expiry time hasn't passed."""
        # Manually set cache with future expiry
        service._cache = [{"id": "gpt-4", "name": "GPT-4"}]
        service._cache_expiry = datetime.now(timezone.utc) + timedelta(minutes=4)

        assert service._is_cache_valid() is True

    def test_cache_invalid_when_expired(self, service):
        """Test cache is invalid when expiry time has passed."""
        # Manually set cache with past expiry
        service._cache = [{"id": "gpt-4", "name": "GPT-4"}]
        service._cache_expiry = datetime.now(timezone.utc) - timedelta(seconds=1)

        assert service._is_cache_valid() is False

    def test_cache_invalid_when_none(self, service):
        """Test cache is invalid when not set."""
        assert service._cache is None
        assert service._cache_expiry is None
        assert service._is_cache_valid() is False

    def test_cache_update_sets_expiry(self, service):
        """Test cache update sets expiry time correctly."""
        models = [{"id": "gpt-4", "name": "GPT-4"}]

        before_update = datetime.now(timezone.utc)
        service._update_cache(models)
        after_update = datetime.now(timezone.utc)

        assert service._cache == models
        # Expiry should be 5 minutes from now
        expected_expiry_min = before_update + timedelta(minutes=5)
        expected_expiry_max = after_update + timedelta(minutes=5) + timedelta(seconds=1)
        assert expected_expiry_min <= service._cache_expiry <= expected_expiry_max


@pytest.mark.asyncio
class TestGetAvailableModels:
    """Test model fetching from LiteLLM endpoint."""

    async def test_get_available_models_success(self, service):
        """Test successful model fetch from LiteLLM."""
        # Mock LiteLLM response
        mock_response = {
            "data": [
                {
                    "id": "gpt-4",
                    "display_name": "GPT-4",
                    "litellm_provider": "openai",
                    "max_tokens": 8192,
                    "supports_function_calling": True,
                    "input_cost_per_token": 0.00003,
                    "output_cost_per_token": 0.00006,
                }
            ]
        }

        with patch("src.services.llm_model_discovery.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.get = AsyncMock(
                return_value=MagicMock(json=MagicMock(return_value=mock_response))
            )
            mock_client.return_value.__aenter__.return_value = mock_async_client

            models = await service.get_available_models()

            assert len(models) == 1
            assert isinstance(models[0], ModelInfo)
            assert models[0].id == "gpt-4"
            assert models[0].name == "GPT-4"
            assert models[0].provider == "openai"

    async def test_get_available_models_uses_cache(self, service):
        """Test that cached models are returned without API call."""
        # Manually set cache
        cached_models = [{"id": "gpt-4", "name": "GPT-4", "provider": "openai", "max_tokens": 8192, "supports_function_calling": True}]
        service._cache = cached_models
        service._cache_expiry = datetime.now(timezone.utc) + timedelta(minutes=4)

        with patch("src.services.llm_model_discovery.httpx.AsyncClient") as mock_client:
            # API should not be called
            models = await service.get_available_models()

            assert len(models) == 1
            assert models[0].id == "gpt-4"
            mock_client.assert_not_called()

    async def test_get_available_models_force_refresh_bypasses_cache(self, service):
        """Test that force_refresh=True bypasses cache."""
        # Manually set cache
        service._cache = [{"id": "old-model"}]
        service._cache_expiry = datetime.now(timezone.utc) + timedelta(minutes=4)

        # Mock fresh response
        mock_response = {
            "data": [
                {
                    "id": "gpt-4",
                    "display_name": "GPT-4",
                    "litellm_provider": "openai",
                    "max_tokens": 8192,
                    "supports_function_calling": True,
                }
            ]
        }

        with patch("src.services.llm_model_discovery.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.get = AsyncMock(
                return_value=MagicMock(json=MagicMock(return_value=mock_response))
            )
            mock_client.return_value.__aenter__.return_value = mock_async_client

            models = await service.get_available_models(force_refresh=True)

            # Should get new models, not cached
            assert len(models) == 1
            assert models[0].id == "gpt-4"
            mock_client.assert_called_once()

    async def test_get_available_models_connection_error_returns_fallback(self, service):
        """Test that connection errors gracefully fall back to default models."""
        with patch("src.services.llm_model_discovery.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            mock_client.return_value.__aenter__.return_value = mock_async_client

            models = await service.get_available_models()

            # Should return fallback models
            assert len(models) >= 2
            assert any(m.id == "gpt-4" for m in models)
            assert any(m.id == "claude-3-opus-20240229" for m in models)

    async def test_get_available_models_timeout_returns_fallback(self, service):
        """Test that timeouts gracefully fall back to default models."""
        with patch("src.services.llm_model_discovery.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client.return_value.__aenter__.return_value = mock_async_client

            models = await service.get_available_models()

            # Should return fallback models
            assert len(models) >= 2
            assert any(m.id == "gpt-4" for m in models)

    async def test_get_available_models_http_error_returns_fallback(self, service):
        """Test that HTTP errors gracefully fall back to default models."""
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"

        with patch("src.services.llm_model_discovery.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.get = AsyncMock(
                side_effect=httpx.HTTPStatusError("503", request=MagicMock(), response=mock_response)
            )
            mock_client.return_value.__aenter__.return_value = mock_async_client

            models = await service.get_available_models()

            # Should return fallback models
            assert len(models) >= 2
            assert any(m.id == "gpt-4" for m in models)

    async def test_get_available_models_empty_response_returns_fallback(self, service):
        """Test that empty LiteLLM response returns fallback models."""
        mock_response = {"data": []}

        with patch("src.services.llm_model_discovery.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.get = AsyncMock(
                return_value=MagicMock(json=MagicMock(return_value=mock_response))
            )
            mock_client.return_value.__aenter__.return_value = mock_async_client

            models = await service.get_available_models()

            # Should return fallback models
            assert len(models) >= 2
            assert any(m.id == "gpt-4" for m in models)


    async def test_get_available_models_filters_models_with_missing_required_fields(self, service):
        """Test that models with missing required fields (id, name, provider) are filtered out.
        
        Regression test for bug where models with None values for required fields
        were added to cache and caused Pydantic validation errors when accessed.
        """
        # Mock LiteLLM response with models that have missing required fields
        mock_response = {
            "data": [
                {
                    # Valid model
                    "id": "gpt-4",
                    "display_name": "GPT-4",
                    "litellm_provider": "openai",
                    "max_tokens": 8192,
                    "supports_function_calling": True,
                },
                {
                    # Missing id
                    "id": None,
                    "display_name": "Bad Model 1",
                    "litellm_provider": "test",
                    "max_tokens": 4096,
                },
                {
                    # Missing name
                    "id": "bad-model-2",
                    "display_name": None,
                    "name": None,
                    "litellm_provider": "test",
                    "max_tokens": 4096,
                },
                {
                    # Missing provider
                    "id": "bad-model-3",
                    "display_name": "Bad Model 3",
                    "litellm_provider": None,
                    "provider": None,
                    "max_tokens": 4096,
                },
                {
                    # Another valid model
                    "id": "claude-3-opus-20240229",
                    "display_name": "Claude 3 Opus",
                    "litellm_provider": "anthropic",
                    "max_tokens": 200000,
                    "supports_function_calling": True,
                },
            ]
        }

        with patch("src.services.llm_model_discovery.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.get = AsyncMock(
                return_value=MagicMock(json=MagicMock(return_value=mock_response))
            )
            mock_client.return_value.__aenter__.return_value = mock_async_client

            models = await service.get_available_models()

            # Should only return the 2 valid models, filtering out the 3 invalid ones
            assert len(models) == 2
            assert all(isinstance(m, ModelInfo) for m in models)
            
            # Verify the valid models are returned
            model_ids = [m.id for m in models]
            assert "gpt-4" in model_ids
            assert "claude-3-opus-20240229" in model_ids
            
            # Verify invalid models were filtered out
            assert "bad-model-2" not in model_ids
            assert "bad-model-3" not in model_ids
            
            # Verify all returned models have required fields
            for model in models:
                assert model.id is not None
                assert model.name is not None
                assert model.provider is not None


@pytest.mark.asyncio
class TestGetModelDetails:
    """Test single model lookup."""

    async def test_get_model_details_found(self, service):
        """Test get_model_details returns matching model."""
        mock_response = {
            "data": [
                {
                    "id": "gpt-4",
                    "display_name": "GPT-4",
                    "litellm_provider": "openai",
                    "max_tokens": 8192,
                    "supports_function_calling": True,
                },
                {
                    "id": "claude-3-opus-20240229",
                    "display_name": "Claude 3 Opus",
                    "litellm_provider": "anthropic",
                    "max_tokens": 200000,
                    "supports_function_calling": True,
                },
            ]
        }

        with patch("src.services.llm_model_discovery.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.get = AsyncMock(
                return_value=MagicMock(json=MagicMock(return_value=mock_response))
            )
            mock_client.return_value.__aenter__.return_value = mock_async_client

            model = await service.get_model_details("gpt-4")

            assert model is not None
            assert model.id == "gpt-4"
            assert model.name == "GPT-4"

    async def test_get_model_details_not_found(self, service):
        """Test get_model_details returns None when model not found."""
        mock_response = {
            "data": [
                {
                    "id": "gpt-4",
                    "display_name": "GPT-4",
                    "litellm_provider": "openai",
                    "max_tokens": 8192,
                    "supports_function_calling": True,
                }
            ]
        }

        with patch("src.services.llm_model_discovery.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.get = AsyncMock(
                return_value=MagicMock(json=MagicMock(return_value=mock_response))
            )
            mock_client.return_value.__aenter__.return_value = mock_async_client

            model = await service.get_model_details("claude-3-opus-20240229")

            assert model is None
