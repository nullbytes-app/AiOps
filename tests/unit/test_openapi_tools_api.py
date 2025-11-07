"""
Unit Tests for OpenAPI Tools API Endpoints.

Story 8.8: OpenAPI Tool Upload and Auto-Generation (Task 10.4)
Tests for FastAPI endpoints in src/api/openapi_tools.py.

Test Coverage:
- POST /api/openapi-tools (create tool) - 3 tests
- POST /api/openapi-tools/parse (parse spec) - 3 tests
- POST /api/openapi-tools/test-connection - 4 tests
- GET /api/openapi-tools (list tools) - 2 tests
- GET /api/openapi-tools/{id} (get tool) - 2 tests

Total: 14 tests (exceeds requirement of 10+)
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

# Import the router
from src.api.openapi_tools import router
from src.schemas.openapi_tool import OpenAPIToolCreate


# Fixtures

@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def app(mock_db):
    """FastAPI test app with dependency overrides."""
    from src.api.dependencies import get_tenant_db

    app = FastAPI()
    app.include_router(router)

    # Override dependency to use mock database
    async def override_get_tenant_db():
        yield mock_db

    app.dependency_overrides[get_tenant_db] = override_get_tenant_db
    return app


@pytest.fixture
def client(app):
    """Test client for API calls."""
    return TestClient(app)


@pytest.fixture
def sample_openapi_spec():
    """Sample OpenAPI 3.0 spec."""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Test API",
            "description": "Test API description",
            "version": "1.0.0",
        },
        "servers": [{"url": "https://api.example.com"}],
        "paths": {
            "/users": {
                "get": {
                    "summary": "List users",
                    "operationId": "listUsers",
                    "responses": {"200": {"description": "Success"}},
                }
            },
        },
    }


@pytest.fixture
def auth_config_bearer():
    """Bearer token auth config."""
    return {
        "type": "http",
        "http_scheme": "bearer",
        "token": "test-token-12345",
    }


# Test Suite: POST /api/openapi-tools (Create Tool)


class TestCreateToolEndpoint:
    """Tests for POST /api/openapi-tools endpoint."""

    @patch("src.api.openapi_tools.OpenAPIToolService")
    def test_create_tool_success(
        self, mock_service_class, client, sample_openapi_spec, auth_config_bearer
    ):
        """Test successful tool creation."""
        # Mock service
        mock_service = AsyncMock()
        mock_tool = MagicMock()
        mock_tool.id = 1
        mock_tool.tool_name = "Test API"
        mock_tool.spec_version = "3.0"
        mock_tool.base_url = "https://api.example.com"
        mock_tool.status = "active"
        mock_tool.created_at = MagicMock()
        mock_tool.created_at.isoformat.return_value = "2025-11-06T12:00:00"
        mock_service.create_tool.return_value = (mock_tool, 1)  # 1 tool generated
        mock_service_class.return_value = mock_service

        # Make request
        payload = {
            "tool_name": "Test API",
            "openapi_spec": sample_openapi_spec,
            "spec_version": "3.0",
            "base_url": "https://api.example.com",
            "auth_config": auth_config_bearer,
            "tenant_id": 1,  # Integer as expected by schema
            "created_by": "test_user",
        }

        response = client.post("/api/openapi-tools", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["tool_name"] == "Test API"
        assert data["tools_count"] == 1
        assert data["status"] == "active"

    @patch("src.api.openapi_tools.OpenAPIToolService")
    def test_create_tool_invalid_spec_returns_400(
        self, mock_service_class, client
    ):
        """Test creating tool with invalid spec returns 400."""
        # Mock service to raise validation error
        mock_service = AsyncMock()
        mock_service.create_tool.side_effect = ValueError("Invalid spec: missing required field 'info'")
        mock_service_class.return_value = mock_service

        # Invalid spec - missing 'info'
        invalid_spec = {
            "openapi": "3.0.0",
            "paths": {"/users": {"get": {"responses": {"200": {"description": "OK"}}}}},
        }

        payload = {
            "tool_name": "Invalid API",
            "openapi_spec": invalid_spec,
            "spec_version": "3.0",
            "base_url": "https://api.example.com",
            "auth_config": {"type": "none"},
            "tenant_id": 1,  # Integer as expected by schema
        }

        response = client.post("/api/openapi-tools", json=payload)

        assert response.status_code == 400
        assert "Invalid spec" in response.json()["detail"]

    def test_create_tool_missing_required_fields_returns_422(self, client):
        """Test creating tool with missing required fields returns 422 (Pydantic validation)."""
        # Missing: openapi_spec, spec_version, base_url
        payload = {
            "tool_name": "Test API",
            "tenant_id": 1,  # Integer as expected by schema
        }

        response = client.post("/api/openapi-tools", json=payload)

        assert response.status_code == 422  # FastAPI Pydantic validation error
        errors = response.json()["detail"]
        assert len(errors) >= 3  # At least 3 missing fields


# Test Suite: POST /api/openapi-tools/parse


class TestParseSpecEndpoint:
    """Tests for POST /api/openapi-tools/parse endpoint."""

    @patch("src.services.openapi_parser_service.parse_openapi_spec")
    @patch("src.services.openapi_parser_service.extract_tool_metadata")
    @patch("src.services.openapi_parser_service.detect_spec_version")
    def test_parse_valid_spec_success(
        self, mock_detect_version, mock_extract_metadata, mock_parse, client, sample_openapi_spec
    ):
        """Test parsing valid OpenAPI spec returns metadata."""
        # Mock dependencies
        mock_detect_version.return_value = "3.0"
        mock_parse.return_value = MagicMock()
        mock_extract_metadata.return_value = {
            "tool_name": "Test API",
            "description": "Test API description",
            "base_url": "https://api.example.com",
            "auth_schemes": {},
            "operations": [{"method": "GET", "path": "/users"}],
            "endpoint_count": 1,
        }

        response = client.post("/api/openapi-tools/parse", json={"spec": sample_openapi_spec})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["parsed_spec"] is True
        assert data["metadata"]["tool_name"] == "Test API"
        assert data["metadata"]["endpoint_count"] == 1

    @patch("src.services.openapi_parser_service.detect_common_issues")
    def test_parse_spec_with_common_issues_returns_errors(
        self, mock_detect_issues, client
    ):
        """Test parsing spec with common issues returns validation errors."""
        # Mock common issues detection
        mock_detect_issues.return_value = [
            "Missing required field 'info'",
            "Missing required field 'paths'",
        ]

        invalid_spec = {"openapi": "3.0.0"}

        response = client.post("/api/openapi-tools/parse", json={"spec": invalid_spec})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert len(data["validation_errors"]) == 2

    def test_parse_spec_missing_spec_field_returns_400(self, client):
        """Test parsing without 'spec' field returns 400."""
        response = client.post("/api/openapi-tools/parse", json={})

        assert response.status_code == 400
        assert "Missing 'spec' field" in response.json()["detail"]


# Test Suite: POST /api/openapi-tools/test-connection


class TestTestConnectionEndpoint:
    """Tests for POST /api/openapi-tools/test-connection endpoint."""

    @patch("src.services.mcp_tool_generator.validate_openapi_connection", new_callable=AsyncMock)
    @patch("src.services.openapi_parser_service.extract_tool_metadata")
    @patch("src.services.openapi_parser_service.parse_openapi_spec")
    @patch("src.services.openapi_parser_service.detect_spec_version")
    def test_connection_success_200(
        self,
        mock_detect_version,
        mock_parse,
        mock_extract_metadata,
        mock_validate_connection,
        client,
        sample_openapi_spec,
        auth_config_bearer,
    ):
        """Test successful connection returns 200."""
        # Mock dependencies
        mock_detect_version.return_value = "3.0"
        mock_parse.return_value = MagicMock()
        mock_extract_metadata.return_value = {"base_url": "https://api.example.com"}

        # Mock async validate_openapi_connection
        # AsyncMock automatically makes return_value awaitable
        mock_validate_connection.return_value = {
            "success": True,
            "status_code": 200,
            "response_preview": '{"status": "ok"}',
            "test_endpoint": "/users",
        }

        payload = {
            "spec": sample_openapi_spec,
            "auth_config": auth_config_bearer,
        }

        response = client.post("/api/openapi-tools/test-connection", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status_code"] == 200
        assert "ok" in data["response_preview"]

    @patch("src.services.mcp_tool_generator.validate_openapi_connection", new_callable=AsyncMock)
    @patch("src.services.openapi_parser_service.extract_tool_metadata")
    @patch("src.services.openapi_parser_service.parse_openapi_spec")
    @patch("src.services.openapi_parser_service.detect_spec_version")
    def test_connection_401_unauthorized(
        self,
        mock_detect_version,
        mock_parse,
        mock_extract_metadata,
        mock_validate_connection,
        client,
        sample_openapi_spec,
        auth_config_bearer,
    ):
        """Test connection with invalid credentials returns 401 info."""
        # Mock dependencies
        mock_detect_version.return_value = "3.0"
        mock_parse.return_value = MagicMock()
        mock_extract_metadata.return_value = {"base_url": "https://api.example.com"}

        # Mock async validate_openapi_connection
        # AsyncMock automatically makes return_value awaitable
        mock_validate_connection.return_value = {
            "success": False,
            "error_message": "Authentication failed. Please verify your credentials.",
            "error_type": "HTTPStatusError",
            "status_code": 401,
            "test_endpoint": "/users",
        }

        payload = {
            "spec": sample_openapi_spec,
            "auth_config": auth_config_bearer,
        }

        response = client.post("/api/openapi-tools/test-connection", json=payload)

        assert response.status_code == 200  # Endpoint succeeds, error in response body
        data = response.json()
        assert data["success"] is False
        assert data["error_type"] == "HTTPStatusError"
        assert data["status_code"] == 401

    @patch("src.services.mcp_tool_generator.validate_openapi_connection", new_callable=AsyncMock)
    @patch("src.services.openapi_parser_service.extract_tool_metadata")
    @patch("src.services.openapi_parser_service.parse_openapi_spec")
    @patch("src.services.openapi_parser_service.detect_spec_version")
    def test_connection_timeout_error(
        self,
        mock_detect_version,
        mock_parse,
        mock_extract_metadata,
        mock_validate_connection,
        client,
        sample_openapi_spec,
        auth_config_bearer,
    ):
        """Test connection timeout returns proper error."""
        # Mock dependencies
        mock_detect_version.return_value = "3.0"
        mock_parse.return_value = MagicMock()
        mock_extract_metadata.return_value = {"base_url": "https://api.example.com"}

        # Mock async validate_openapi_connection
        # AsyncMock automatically makes return_value awaitable
        mock_validate_connection.return_value = {
            "success": False,
            "error_message": "Request timeout after 30.0s. The API may be slow or unreachable.",
            "error_type": "Timeout",
            "test_endpoint": "/users",
        }

        payload = {
            "spec": sample_openapi_spec,
            "auth_config": auth_config_bearer,
        }

        response = client.post("/api/openapi-tools/test-connection", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error_type"] == "Timeout"
        assert "timeout" in data["error_message"].lower()

    @patch("src.services.openapi_parser_service.parse_openapi_spec")
    def test_connection_invalid_spec_returns_400(
        self, mock_parse, client
    ):
        """Test connection test with invalid spec returns 400."""
        # Mock parse to raise error
        mock_parse.side_effect = ValueError("Invalid spec format")

        payload = {
            "spec": {"invalid": "spec"},
            "auth_config": {"type": "none"},
        }

        response = client.post("/api/openapi-tools/test-connection", json=payload)

        assert response.status_code == 400
        assert "Invalid spec" in response.json()["detail"]


# Test Suite: GET /api/openapi-tools (List Tools)


class TestListToolsEndpoint:
    """Tests for GET /api/openapi-tools endpoint."""

    @patch("src.api.openapi_tools.OpenAPIToolService")
    def test_list_tools_for_tenant(
        self, mock_service_class, client
    ):
        """Test listing all tools for a tenant."""
        # Mock service
        mock_service = AsyncMock()
        mock_tool1 = MagicMock()
        mock_tool1.id = 1
        mock_tool1.tenant_id = 1
        mock_tool1.tool_name = "GitHub API"
        mock_tool1.spec_version = "3.0"
        mock_tool1.base_url = "https://api.github.com"
        mock_tool1.status = "active"
        mock_tool1.created_at = MagicMock()
        mock_tool1.updated_at = MagicMock()

        mock_tool2 = MagicMock()
        mock_tool2.id = 2
        mock_tool2.tenant_id = 1
        mock_tool2.tool_name = "Stripe API"
        mock_tool2.spec_version = "3.0"
        mock_tool2.base_url = "https://api.stripe.com"
        mock_tool2.status = "active"
        mock_tool2.created_at = MagicMock()
        mock_tool2.updated_at = MagicMock()

        mock_service.get_tools.return_value = [mock_tool1, mock_tool2]
        mock_service_class.return_value = mock_service

        response = client.get("/api/openapi-tools", params={"tenant_id": 1})

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["tool_name"] == "GitHub API"
        assert data[1]["tool_name"] == "Stripe API"

    @patch("src.api.openapi_tools.OpenAPIToolService")
    def test_list_tools_with_status_filter(
        self, mock_service_class, client
    ):
        """Test listing tools filtered by status."""
        # Mock service - return only active tools
        mock_service = AsyncMock()
        mock_tool = MagicMock()
        mock_tool.id = 1
        mock_tool.tenant_id = 1
        mock_tool.tool_name = "Active API"
        mock_tool.status = "active"
        mock_tool.spec_version = "3.0"
        mock_tool.base_url = "https://api.example.com"
        mock_tool.created_at = MagicMock()
        mock_tool.updated_at = MagicMock()

        mock_service.get_tools.return_value = [mock_tool]
        mock_service_class.return_value = mock_service

        response = client.get("/api/openapi-tools", params={"tenant_id": 1, "status": "active"})

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "active"


# Test Suite: GET /api/openapi-tools/{id} (Get Tool)


class TestGetToolEndpoint:
    """Tests for GET /api/openapi-tools/{id} endpoint."""

    @patch("src.api.openapi_tools.OpenAPIToolService")
    def test_get_tool_by_id_success(
        self, mock_service_class, client
    ):
        """Test getting tool by ID returns tool details."""
        # Mock service
        mock_service = AsyncMock()
        mock_tool = MagicMock()
        mock_tool.id = 1
        mock_tool.tenant_id = 1
        mock_tool.tool_name = "GitHub API"
        mock_tool.spec_version = "3.0"
        mock_tool.base_url = "https://api.github.com"
        mock_tool.status = "active"
        mock_tool.created_at = MagicMock()
        mock_tool.updated_at = MagicMock()

        mock_service.get_tool_by_id.return_value = mock_tool
        mock_service_class.return_value = mock_service

        response = client.get("/api/openapi-tools/1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["tool_name"] == "GitHub API"

    @patch("src.api.openapi_tools.OpenAPIToolService")
    def test_get_tool_not_found_returns_404(
        self, mock_service_class, client
    ):
        """Test getting non-existent tool returns 404."""
        # Mock service - tool not found
        mock_service = AsyncMock()
        mock_service.get_tool_by_id.return_value = None
        mock_service_class.return_value = mock_service

        response = client.get("/api/openapi-tools/999")

        assert response.status_code == 404
        assert "Tool not found" in response.json()["detail"]
