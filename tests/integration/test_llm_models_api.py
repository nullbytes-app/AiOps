"""
Integration tests for LLM Models API endpoint.

Tests the GET /api/llm-models/available endpoint for:
- Successful model retrieval from LiteLLM
- Cache behavior and force_refresh parameter
- Error handling (LiteLLM unavailable)
- Fallback to default models

Story: 9.1 - Dynamic Model Discovery from LiteLLM
Target: Test API endpoint integration with ModelDiscoveryService
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Provide TestClient for FastAPI app."""
    return TestClient(app)


class TestGetAvailableModelsEndpoint:
    """Test suite for GET /api/llm-models/available endpoint."""

    def test_get_available_models_success(self, client):
        """Test endpoint returns available models from LiteLLM."""
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
                },
                {
                    "id": "claude-3-opus-20240229",
                    "display_name": "Claude 3 Opus",
                    "litellm_provider": "anthropic",
                    "max_tokens": 200000,
                    "supports_function_calling": True,
                    "input_cost_per_token": 0.0000075,
                    "output_cost_per_token": 0.0000075,
                },
            ]
        }

        with patch("src.services.llm_model_discovery.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.get = AsyncMock(
                return_value=MagicMock(
                    json=MagicMock(return_value=mock_response),
                    raise_for_status=MagicMock()
                )
            )
            mock_client.return_value.__aenter__.return_value = mock_async_client

            response = client.get("/api/llm-models/available")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) >= 2
            assert any(m["id"] == "gpt-4" for m in data)
            assert any(m["id"] == "claude-3-opus-20240229" for m in data)

    def test_get_available_models_with_force_refresh(self, client):
        """Test endpoint respects force_refresh=true parameter."""
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
                return_value=MagicMock(
                    json=MagicMock(return_value=mock_response),
                    raise_for_status=MagicMock()
                )
            )
            mock_client.return_value.__aenter__.return_value = mock_async_client

            response = client.get("/api/llm-models/available?force_refresh=true")

            assert response.status_code == 200
            data = response.json()
            assert len(data) >= 1
            assert data[0]["id"] == "gpt-4"

    def test_get_available_models_returns_fallback_on_error(self, client):
        """Test endpoint returns fallback models when LiteLLM unavailable."""
        with patch("src.services.llm_model_discovery.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.get = AsyncMock(side_effect=Exception("Connection failed"))
            mock_client.return_value.__aenter__.return_value = mock_async_client

            response = client.get("/api/llm-models/available")

            # Should still return 200 with fallback models
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) >= 2
            # Should have fallback models
            assert any(m["id"] == "gpt-4" for m in data)

    def test_get_available_models_response_schema(self, client):
        """Test endpoint returns valid ModelInfo schema."""
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
                return_value=MagicMock(
                    json=MagicMock(return_value=mock_response),
                    raise_for_status=MagicMock()
                )
            )
            mock_client.return_value.__aenter__.return_value = mock_async_client

            response = client.get("/api/llm-models/available")

            assert response.status_code == 200
            data = response.json()
            # Each model should have required fields
            for model in data:
                assert "id" in model
                assert "name" in model
                assert "provider" in model
                assert "max_tokens" in model
                assert "supports_function_calling" in model
                assert isinstance(model["id"], str)
                assert isinstance(model["name"], str)
                assert isinstance(model["max_tokens"], int)
                assert isinstance(model["supports_function_calling"], bool)

    def test_get_available_models_no_auth_required(self, client):
        """Test endpoint is public and doesn't require authentication."""
        # This is a public endpoint (AC#8), no X-Admin-Key required
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
                return_value=MagicMock(
                    json=MagicMock(return_value=mock_response),
                    raise_for_status=MagicMock()
                )
            )
            mock_client.return_value.__aenter__.return_value = mock_async_client

            # Make request without auth headers
            response = client.get("/api/llm-models/available")

            # Should succeed (not 401)
            assert response.status_code == 200
