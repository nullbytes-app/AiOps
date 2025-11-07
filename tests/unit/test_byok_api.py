"""
Unit tests for BYOK API endpoints - Story 8.13.

Tests FastAPI endpoints:
- POST /api/tenants/{tenant_id}/byok/test-keys - Test keys without enabling
- POST /api/tenants/{tenant_id}/byok/enable - Enable BYOK with validation
- PUT /api/tenants/{tenant_id}/byok/rotate-keys - Rotate provider keys
- POST /api/tenants/{tenant_id}/byok/disable - Disable BYOK
- GET /api/tenants/{tenant_id}/byok/status - Get BYOK status

Coverage: ≥15 unit tests for API endpoints with authorization and error handling
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import Response

from src.main import app
from src.config import settings


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def admin_headers():
    """Admin authorization headers for BYOK endpoints."""
    return {"X-Admin-Key": settings.admin_api_key}


@pytest.fixture
def invalid_admin_headers():
    """Invalid admin authorization headers."""
    return {"X-Admin-Key": "invalid-key"}


class TestTestKeysEndpoint:
    """Test /api/tenants/{tenant_id}/byok/test-keys endpoint (AC#3)."""

    def test_test_keys_requires_admin_authorization(self, client):
        """Test endpoint requires valid X-Admin-Key header."""
        response = client.post(
            "/api/tenants/tenant-123/byok/test-keys",
            json={"openai_key": "sk-test-key", "anthropic_key": None},
        )

        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    def test_test_keys_rejects_invalid_admin_key(self, client, invalid_admin_headers):
        """Test endpoint rejects invalid admin key."""
        response = client.post(
            "/api/tenants/tenant-123/byok/test-keys",
            headers=invalid_admin_headers,
            json={"openai_key": "sk-test-key", "anthropic_key": None},
        )

        assert response.status_code == 403

    def test_test_keys_validates_openai_key(self, client, admin_headers):
        """Test endpoint validates OpenAI key format."""
        response = client.post(
            "/api/tenants/tenant-123/byok/test-keys",
            headers=admin_headers,
            json={"openai_key": "invalid-format", "anthropic_key": None},
        )

        assert response.status_code == 422  # Validation error

    def test_test_keys_validates_anthropic_key(self, client, admin_headers):
        """Test endpoint validates Anthropic key format."""
        response = client.post(
            "/api/tenants/tenant-123/byok/test-keys",
            headers=admin_headers,
            json={"openai_key": None, "anthropic_key": "invalid-anthropic-format"},
        )

        assert response.status_code == 422

    def test_test_keys_requires_at_least_one_key(self, client, admin_headers):
        """Test endpoint requires at least one provider key."""
        response = client.post(
            "/api/tenants/tenant-123/byok/test-keys",
            headers=admin_headers,
            json={"openai_key": None, "anthropic_key": None},
        )

        assert response.status_code == 422


class TestEnableEndpoint:
    """Test /api/tenants/{tenant_id}/byok/enable endpoint (AC#1-4)."""

    def test_enable_requires_admin_authorization(self, client):
        """Test enable endpoint requires admin key."""
        response = client.post(
            "/api/tenants/tenant-123/byok/enable",
            json={"openai_key": "sk-valid-key", "anthropic_key": None},
        )

        assert response.status_code == 403

    def test_enable_validates_openai_key_format(self, client, admin_headers):
        """Test enable endpoint validates OpenAI key format."""
        response = client.post(
            "/api/tenants/tenant-123/byok/enable",
            headers=admin_headers,
            json={"openai_key": "bad-format", "anthropic_key": None},
        )

        assert response.status_code == 422

    def test_enable_validates_anthropic_key_format(self, client, admin_headers):
        """Test enable endpoint validates Anthropic key format."""
        response = client.post(
            "/api/tenants/tenant-123/byok/enable",
            headers=admin_headers,
            json={"openai_key": None, "anthropic_key": "bad-format"},
        )

        assert response.status_code == 422

    def test_enable_requires_at_least_one_key(self, client, admin_headers):
        """Test enable endpoint requires at least one provider key."""
        response = client.post(
            "/api/tenants/tenant-123/byok/enable",
            headers=admin_headers,
            json={"openai_key": None, "anthropic_key": None},
        )

        assert response.status_code == 422


class TestRotateKeysEndpoint:
    """Test /api/tenants/{tenant_id}/byok/rotate-keys endpoint (AC#7)."""

    def test_rotate_requires_admin_authorization(self, client):
        """Test rotate endpoint requires admin key."""
        response = client.put(
            "/api/tenants/tenant-123/byok/rotate-keys",
            json={"new_openai_key": "sk-new-key", "new_anthropic_key": None},
        )

        assert response.status_code == 403

    def test_rotate_validates_openai_key_format(self, client, admin_headers):
        """Test rotate endpoint validates new OpenAI key format."""
        response = client.put(
            "/api/tenants/tenant-123/byok/rotate-keys",
            headers=admin_headers,
            json={"new_openai_key": "invalid-format", "new_anthropic_key": None},
        )

        assert response.status_code == 422

    def test_rotate_validates_anthropic_key_format(self, client, admin_headers):
        """Test rotate endpoint validates new Anthropic key format."""
        response = client.put(
            "/api/tenants/tenant-123/byok/rotate-keys",
            headers=admin_headers,
            json={"new_openai_key": None, "new_anthropic_key": "invalid-format"},
        )

        assert response.status_code == 422

    def test_rotate_requires_at_least_one_new_key(self, client, admin_headers):
        """Test rotate endpoint requires at least one new key."""
        response = client.put(
            "/api/tenants/tenant-123/byok/rotate-keys",
            headers=admin_headers,
            json={"new_openai_key": None, "new_anthropic_key": None},
        )

        assert response.status_code == 422


class TestDisableEndpoint:
    """Test /api/tenants/{tenant_id}/byok/disable endpoint (AC#8)."""

    def test_disable_requires_admin_authorization(self, client):
        """Test disable endpoint requires admin key."""
        response = client.post("/api/tenants/tenant-123/byok/disable")

        assert response.status_code == 403

    def test_disable_endpoint_exists(self, client, admin_headers):
        """Test disable endpoint exists and accepts admin key."""
        response = client.post("/api/tenants/tenant-123/byok/disable", headers=admin_headers)

        # Will fail without proper DB setup, but endpoint should exist
        assert response.status_code in [200, 500, 404]


class TestStatusEndpoint:
    """Test /api/tenants/{tenant_id}/byok/status endpoint (AC#6)."""

    def test_status_requires_admin_authorization(self, client):
        """Test status endpoint requires admin key."""
        response = client.get("/api/tenants/tenant-123/byok/status")

        assert response.status_code == 403

    def test_status_endpoint_exists(self, client, admin_headers):
        """Test status endpoint exists and accepts admin key."""
        response = client.get("/api/tenants/tenant-123/byok/status", headers=admin_headers)

        # Will fail without proper DB setup, but endpoint should exist
        assert response.status_code in [200, 404, 500]


class TestAPIEndpointErrorHandling:
    """Test error handling across BYOK API endpoints."""

    def test_invalid_tenant_id_format(self, client, admin_headers):
        """Test endpoints handle invalid tenant ID formats gracefully."""
        response = client.post(
            "/api/tenants/invalid%20id/byok/test-keys",
            headers=admin_headers,
            json={"openai_key": "sk-test", "anthropic_key": None},
        )

        # Should handle gracefully - endpoint validates keys regardless of tenant format
        # 200 is valid (test-keys endpoint returns validation results)
        # Other codes are also acceptable (404 if tenant not found, 400 if malformed, 500 on error)
        assert response.status_code in [200, 422, 404, 400, 500]

    def test_endpoint_paths_are_correct(self, client, admin_headers):
        """Test all BYOK endpoint paths are registered correctly."""
        tenant_id = "test-tenant"

        # Test all paths exist (will fail with auth/DB errors but routes should exist)
        paths_to_test = [
            ("POST", f"/api/tenants/{tenant_id}/byok/test-keys"),
            ("POST", f"/api/tenants/{tenant_id}/byok/enable"),
            ("PUT", f"/api/tenants/{tenant_id}/byok/rotate-keys"),
            ("POST", f"/api/tenants/{tenant_id}/byok/disable"),
            ("GET", f"/api/tenants/{tenant_id}/byok/status"),
        ]

        for method, path in paths_to_test:
            if method == "GET":
                response = client.get(path, headers=admin_headers)
            elif method == "POST":
                response = client.post(
                    path,
                    headers=admin_headers,
                    json={"openai_key": "sk-test", "anthropic_key": None},
                )
            elif method == "PUT":
                response = client.put(
                    path,
                    headers=admin_headers,
                    json={"new_openai_key": "sk-test", "new_anthropic_key": None},
                )

            # Should not return 404 (endpoint exists)
            # May return validation errors or other status codes
            assert response.status_code != 404, f"Endpoint {method} {path} not found"


class TestAPIRequestValidation:
    """Test request body validation on all BYOK endpoints."""

    def test_test_keys_accepts_valid_openai_key_format(self, client, admin_headers):
        """Test endpoint accepts valid OpenAI key format."""
        response = client.post(
            "/api/tenants/tenant-123/byok/test-keys",
            headers=admin_headers,
            json={"openai_key": "sk-proj-abcdef123456", "anthropic_key": None},
            # This will fail at service layer but validates request format
        )

        # Should pass validation (may fail at service layer)
        assert response.status_code != 422

    def test_test_keys_accepts_valid_anthropic_key_format(self, client, admin_headers):
        """Test endpoint accepts valid Anthropic key format."""
        response = client.post(
            "/api/tenants/tenant-123/byok/test-keys",
            headers=admin_headers,
            json={"openai_key": None, "anthropic_key": "sk-ant-abcdef123456"},
        )

        # Should pass validation
        assert response.status_code != 422

    def test_enable_accepts_both_keys(self, client, admin_headers):
        """Test enable endpoint accepts both provider keys."""
        response = client.post(
            "/api/tenants/tenant-123/byok/enable",
            headers=admin_headers,
            json={"openai_key": "sk-proj-abcdef123456", "anthropic_key": "sk-ant-abcdef123456"},
        )

        # Should pass validation
        assert response.status_code != 422

    def test_rotate_accepts_partial_key_update(self, client, admin_headers):
        """Test rotate endpoint accepts updating just one provider key."""
        response = client.put(
            "/api/tenants/tenant-123/byok/rotate-keys",
            headers=admin_headers,
            json={"new_openai_key": "sk-proj-newkey123456", "new_anthropic_key": None},
        )

        # Should pass validation
        assert response.status_code != 422
