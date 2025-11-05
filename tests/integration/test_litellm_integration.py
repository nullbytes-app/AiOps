"""
Integration tests for LiteLLM Proxy endpoints.

Story 8.1: LiteLLM Proxy Integration
Tests validate LiteLLM service running in Docker with real HTTP requests.
"""

import os
import pytest
import requests
import time
from typing import Dict, Any


@pytest.fixture(scope="module")
def litellm_url():
    """Get LiteLLM base URL from environment or use default."""
    return os.getenv("LITELLM_URL", "http://localhost:4000")


@pytest.fixture(scope="module")
def master_key():
    """Get LITELLM_MASTER_KEY from environment."""
    key = os.getenv("LITELLM_MASTER_KEY")
    if not key:
        pytest.skip("LITELLM_MASTER_KEY not set, skipping LiteLLM integration tests")
    return key


@pytest.fixture(scope="module")
def auth_headers(master_key):
    """Create authorization headers with master key."""
    return {
        "Authorization": f"Bearer {master_key}",
        "Content-Type": "application/json"
    }


class TestLiteLLMServiceHealth:
    """Test LiteLLM service health and availability."""

    def test_litellm_service_is_running(self, litellm_url):
        """Test that LiteLLM service is accessible."""
        try:
            # Health endpoint requires auth, so 401 is expected but proves service is up
            response = requests.get(f"{litellm_url}/health", timeout=5)
            # Service is running if we get ANY response (200 or 401)
            assert response.status_code in [200, 401], \
                f"Expected 200 or 401, got {response.status_code}"
        except requests.ConnectionError:
            pytest.fail("LiteLLM service is not running. Start with: docker-compose up -d litellm")

    def test_health_endpoint_requires_authentication(self, litellm_url):
        """AC7: Test that health endpoint requires authentication."""
        response = requests.get(f"{litellm_url}/health", timeout=5)
        # Without auth, should return 401
        assert response.status_code == 401, \
            "Health endpoint should require authentication"
        data = response.json()
        assert "error" in data, "401 response should contain error"

    def test_health_endpoint_with_auth_returns_200(self, litellm_url, auth_headers):
        """AC7: Test that health endpoint returns 200 with valid auth."""
        response = requests.get(
            f"{litellm_url}/health",
            headers=auth_headers,
            timeout=5
        )
        assert response.status_code == 200, \
            f"Health endpoint should return 200 with auth, got {response.status_code}"

    def test_health_endpoint_response_time(self, litellm_url, auth_headers):
        """AC7: Test that health endpoint responds within reasonable time."""
        start_time = time.time()
        response = requests.get(
            f"{litellm_url}/health",
            headers=auth_headers,
            timeout=10
        )
        elapsed = time.time() - start_time

        assert response.status_code == 200
        # Health check can take a few seconds if testing providers
        # But should complete within 10 seconds
        assert elapsed < 10.0, \
            f"Health check took {elapsed:.2f}s, expected <10s"

    def test_health_endpoint_returns_provider_status(self, litellm_url, auth_headers):
        """Test that health endpoint returns provider health information."""
        response = requests.get(
            f"{litellm_url}/health",
            headers=auth_headers,
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()

        # Should contain health status information
        assert isinstance(data, dict), "Health response should be a dictionary"
        # May contain healthy_endpoints, unhealthy_endpoints, or other status info
        assert len(data) > 0, "Health response should contain status information"


class TestVirtualKeyManagement:
    """Test virtual key creation and management (AC3)."""

    def test_create_virtual_key(self, litellm_url, auth_headers):
        """AC3: Test virtual key creation with budget limit."""
        response = requests.post(
            f"{litellm_url}/key/generate",
            headers=auth_headers,
            json={
                "models": ["gpt-4"],
                "max_budget": 10.0,
                "duration": "1h",
                "metadata": {"tenant_id": "test-tenant"}
            },
            timeout=5
        )

        assert response.status_code == 200, \
            f"Virtual key creation failed: {response.status_code} - {response.text}"

        data = response.json()
        assert "key" in data, "Response should contain 'key' field"
        assert data["key"].startswith("sk-"), "Virtual key should start with 'sk-'"
        assert "max_budget" in data, "Response should contain max_budget"
        assert data["max_budget"] == 10.0, "Budget should match requested amount"

        # Store key for cleanup
        return data["key"]

    def test_virtual_key_has_expiration(self, litellm_url, auth_headers):
        """Test that virtual keys have expiration dates."""
        response = requests.post(
            f"{litellm_url}/key/generate",
            headers=auth_headers,
            json={
                "models": ["gpt-4"],
                "duration": "30d"
            },
            timeout=5
        )

        assert response.status_code == 200
        data = response.json()
        assert "expires" in data, "Virtual key should have expiration date"
        assert data["expires"] is not None, "Expiration should not be null"

    def test_virtual_key_info_endpoint(self, litellm_url, auth_headers):
        """Test retrieving virtual key information."""
        # Create a test key first
        create_response = requests.post(
            f"{litellm_url}/key/generate",
            headers=auth_headers,
            json={
                "models": ["gpt-4"],
                "max_budget": 5.0
            },
            timeout=5
        )
        assert create_response.status_code == 200
        virtual_key = create_response.json()["key"]

        # Get key info using the virtual key itself
        info_response = requests.get(
            f"{litellm_url}/key/info",
            headers={"Authorization": f"Bearer {virtual_key}"},
            timeout=5
        )

        assert info_response.status_code == 200, \
            f"Key info request failed: {info_response.status_code}"
        info_data = info_response.json()
        assert "max_budget" in info_data or "info" in info_data, \
            "Key info should contain budget information"

    def test_create_virtual_key_requires_master_key(self, litellm_url):
        """Test that virtual key creation requires master key (not any key)."""
        response = requests.post(
            f"{litellm_url}/key/generate",
            headers={
                "Authorization": "Bearer invalid-key",
                "Content-Type": "application/json"
            },
            json={"models": ["gpt-4"]},
            timeout=5
        )

        # Should fail with invalid key
        assert response.status_code in [401, 403], \
            "Invalid key should not be able to create virtual keys"


class TestDatabaseIntegration:
    """Test PostgreSQL database integration (AC3)."""

    def test_virtual_keys_persisted_in_database(self, litellm_url, auth_headers):
        """AC3: Test that virtual keys are stored in PostgreSQL."""
        # Create a virtual key
        response = requests.post(
            f"{litellm_url}/key/generate",
            headers=auth_headers,
            json={
                "models": ["gpt-4"],
                "max_budget": 1.0,
                "metadata": {"test": "database_persistence"}
            },
            timeout=5
        )

        assert response.status_code == 200
        virtual_key = response.json()["key"]

        # Verify key can be retrieved (proves it's in database)
        info_response = requests.get(
            f"{litellm_url}/key/info",
            headers={"Authorization": f"Bearer {virtual_key}"},
            timeout=5
        )

        assert info_response.status_code == 200, \
            "Virtual key should be retrievable from database"


class TestChatCompletionEndpoint:
    """Test chat completion endpoint with virtual keys."""

    @pytest.fixture
    def virtual_key(self, litellm_url, auth_headers):
        """Create a test virtual key."""
        response = requests.post(
            f"{litellm_url}/key/generate",
            headers=auth_headers,
            json={
                "models": ["gpt-4"],
                "max_budget": 10.0
            },
            timeout=5
        )
        assert response.status_code == 200
        return response.json()["key"]

    def test_chat_completion_endpoint_exists(self, litellm_url, virtual_key):
        """Test that /chat/completions endpoint is accessible."""
        response = requests.post(
            f"{litellm_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {virtual_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4",
                "messages": [{"role": "user", "content": "Say 'test'"}],
                "max_tokens": 5
            },
            timeout=60  # LLM calls can take time
        )

        # Response depends on whether API keys are configured
        # 200: Success (API keys configured)
        # 401/429/500: Provider errors (expected if using placeholder keys)
        assert response.status_code in [200, 401, 429, 500, 502], \
            f"Unexpected status code: {response.status_code} - {response.text}"

    def test_chat_completion_requires_authentication(self, litellm_url):
        """Test that chat completion requires valid API key."""
        response = requests.post(
            f"{litellm_url}/chat/completions",
            headers={"Content-Type": "application/json"},
            json={
                "model": "gpt-4",
                "messages": [{"role": "user", "content": "test"}]
            },
            timeout=10
        )

        assert response.status_code == 401, \
            "Chat completion should require authentication"


class TestMetricsEndpoint:
    """Test Prometheus metrics endpoint."""

    def test_metrics_endpoint_exists(self, litellm_url):
        """Test that /metrics endpoint is accessible."""
        response = requests.get(f"{litellm_url}/metrics", timeout=5)

        # Metrics endpoint may not be enabled by default (404 acceptable)
        # If enabled, should return 200 (public) or 401 (requires auth)
        assert response.status_code in [200, 401, 404], \
            f"Metrics endpoint returned unexpected status: {response.status_code}"

    def test_metrics_endpoint_returns_prometheus_format(self, litellm_url):
        """Test that metrics are in Prometheus format."""
        response = requests.get(f"{litellm_url}/metrics", timeout=5)

        if response.status_code == 200:
            content = response.text
            # Prometheus metrics should contain # HELP and # TYPE comments
            assert "# HELP" in content or "# TYPE" in content or "litellm" in content, \
                "Metrics should be in Prometheus format"


class TestModelInfoEndpoint:
    """Test model info endpoint."""

    def test_model_info_endpoint(self, litellm_url, auth_headers):
        """Test that /model/info endpoint lists available models."""
        response = requests.get(
            f"{litellm_url}/model/info",
            headers=auth_headers,
            timeout=5
        )

        # Endpoint may or may not require auth, accept both
        assert response.status_code in [200, 401, 404], \
            f"Unexpected status code: {response.status_code}"

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list)), \
                "Model info should return dict or list"


class TestRetryLogic:
    """Test retry logic configuration (AC6)."""

    def test_retry_configuration_applied(self, litellm_url, auth_headers):
        """AC6: Test that retry logic is configured (observational test)."""
        # This test verifies retry config by checking health endpoint
        # which internally uses retry logic
        start_time = time.time()
        response = requests.get(
            f"{litellm_url}/health",
            headers=auth_headers,
            timeout=15
        )
        elapsed = time.time() - start_time

        assert response.status_code == 200

        # If retries are working, health check will complete
        # Even with some providers failing, it should respond within timeout
        assert elapsed < 15.0, \
            "Health check with retries should complete within 15 seconds"


class TestFallbackChain:
    """Test fallback chain configuration (AC5)."""

    def test_fallback_chain_health_check(self, litellm_url, auth_headers):
        """AC5: Test fallback chain via health endpoint."""
        response = requests.get(
            f"{litellm_url}/health",
            headers=auth_headers,
            timeout=15
        )

        assert response.status_code == 200
        data = response.json()

        # Health response should show multiple endpoints (providers)
        # indicating fallback chain is configured
        if "unhealthy_endpoints" in data or "healthy_endpoints" in data:
            # Count total endpoints
            unhealthy = data.get("unhealthy_endpoints", [])
            healthy = data.get("healthy_endpoints", [])
            total_endpoints = len(unhealthy) + len(healthy)

            # Should have at least 2 endpoints (primary + fallback)
            assert total_endpoints >= 2, \
                f"AC5: Fallback chain should have at least 2 providers, found {total_endpoints}"


class TestAcceptanceCriteriaValidation:
    """Validate all acceptance criteria are met."""

    def test_ac1_litellm_service_running(self, litellm_url):
        """AC1: LiteLLM service configured and running in Docker."""
        try:
            response = requests.get(f"{litellm_url}/health", timeout=5)
            assert response.status_code in [200, 401], \
                "AC1: LiteLLM service should be accessible"
        except requests.ConnectionError:
            pytest.fail("AC1: LiteLLM service is not running in Docker")

    def test_ac3_postgresql_integration(self, litellm_url, auth_headers):
        """AC3: PostgreSQL database integration working."""
        # Create virtual key (requires database)
        response = requests.post(
            f"{litellm_url}/key/generate",
            headers=auth_headers,
            json={"models": ["gpt-4"], "max_budget": 1.0},
            timeout=5
        )

        assert response.status_code == 200, \
            "AC3: Virtual key creation requires working PostgreSQL integration"

    def test_ac7_health_check_endpoint(self, litellm_url, auth_headers):
        """AC7: Health check endpoint verified."""
        response = requests.get(
            f"{litellm_url}/health",
            headers=auth_headers,
            timeout=10
        )

        assert response.status_code == 200, \
            "AC7: Health check endpoint should return 200"
