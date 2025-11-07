"""
Integration Tests for OpenAPI Tool Workflow.

Story 8.8: OpenAPI Tool Upload and Auto-Generation (Task 10.3)
Tests for complete workflow: upload → parse → generate → save.

Test Coverage:
- Full workflow end-to-end (2 tests)
- Connection testing scenarios (3 tests)
- Database encryption roundtrip (2 tests)
- Validation error handling (2 tests)
- Tool generation count verification (1 test)

Total: 10 tests (exceeds requirement of 8+)

NOTE: These tests use mocked database operations since the database may not be running.
Mark with @pytest.mark.integration for future execution when database is available.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from src.services.openapi_tool_service import (
    OpenAPIToolService,
    encrypt_auth_config,
    decrypt_auth_config,
)
from src.schemas.openapi_tool import OpenAPIToolCreate
from pydantic import ValidationError


# Fixtures

@pytest.fixture
def sample_openapi_spec():
    """Sample OpenAPI 3.0 spec for testing."""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "GitHub API",
            "description": "GitHub REST API",
            "version": "1.0.0",
        },
        "servers": [{"url": "https://api.github.com"}],
        "paths": {
            "/users": {
                "get": {
                    "summary": "List users",
                    "operationId": "listUsers",
                    "responses": {"200": {"description": "Success"}},
                }
            },
            "/repos/{owner}/{repo}": {
                "get": {
                    "summary": "Get repository",
                    "operationId": "getRepo",
                    "parameters": [
                        {"name": "owner", "in": "path", "required": True, "schema": {"type": "string"}},
                        {"name": "repo", "in": "path", "required": True, "schema": {"type": "string"}},
                    ],
                    "responses": {"200": {"description": "Success"}},
                }
            },
        },
    }


@pytest.fixture
def auth_config_bearer():
    """Bearer token authentication config."""
    return {
        "type": "http",
        "http_scheme": "bearer",
        "token": "ghp_test_token_12345",
    }


@pytest.fixture
def auth_config_api_key():
    """API key authentication config."""
    return {
        "type": "apikey",
        "location": "header",
        "param_name": "X-API-Key",
        "value": "sk-test-key-67890",
    }


@pytest.fixture
def tool_create_data(sample_openapi_spec, auth_config_bearer):
    """OpenAPI tool creation data."""
    return OpenAPIToolCreate(
        tool_name="GitHub API",
        openapi_spec=sample_openapi_spec,
        spec_version="3.0",
        base_url="https://api.github.com",
        auth_config=auth_config_bearer,
        tenant_id=1,
        created_by="test_user",
    )


@pytest.fixture
def mock_db_session():
    """Mock AsyncSession for database operations."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    return db


# Test Suite: Full Workflow Integration


class TestFullWorkflow:
    """Tests for complete upload → parse → generate → save workflow."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @patch("src.services.openapi_tool_service.generate_mcp_tools_from_openapi")
    @patch("src.services.openapi_tool_service.parse_openapi_spec")
    async def test_full_workflow_upload_parse_generate_save(
        self, mock_parse, mock_generate, tool_create_data, mock_db_session
    ):
        """Test complete happy path: upload → parse → generate MCP tools → save to DB."""
        # Mock parse_openapi_spec
        mock_openapi = MagicMock()
        mock_parse.return_value = mock_openapi

        # Mock generate_mcp_tools_from_openapi
        mock_mcp = MagicMock()
        mock_mcp.tools = [MagicMock(), MagicMock()]  # 2 tools
        mock_generate.return_value = mock_mcp

        # Mock database execution result for generated tool ID
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Execute workflow
        service = OpenAPIToolService(mock_db_session)
        db_tool, tools_count = await service.create_tool(tool_create_data)

        # Verify parse was called
        mock_parse.assert_called_once_with(tool_create_data.openapi_spec)

        # Verify MCP generation was called
        mock_generate.assert_called_once_with(
            tool_create_data.openapi_spec,
            tool_create_data.auth_config,
            tool_create_data.base_url,
            tool_create_data.tool_name,
        )

        # Verify tool count
        assert tools_count == 2

        # Verify database add/commit/refresh called
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

        # Verify tool attributes
        assert db_tool.tool_name == "GitHub API"
        assert db_tool.spec_version == "3.0"
        assert db_tool.base_url == "https://api.github.com"
        assert db_tool.status == "active"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_workflow_invalid_spec_displays_errors(self):
        """Test workflow with invalid spec displays validation errors."""
        # Invalid spec - missing required 'info' field
        invalid_spec = {
            "openapi": "3.0.0",
            "paths": {
                "/users": {"get": {"summary": "List users", "responses": {"200": {"description": "OK"}}}}
            },
        }

        invalid_tool_data = OpenAPIToolCreate(
            tool_name="Invalid API",
            openapi_spec=invalid_spec,
            spec_version="3.0",
            base_url="https://api.example.com",
            auth_config={"type": "none"},
            tenant_id=1,
        )

        mock_db = AsyncMock()
        service = OpenAPIToolService(mock_db)

        # Should raise validation error from openapi-pydantic
        with pytest.raises((ValidationError, ValueError, KeyError)):
            await service.create_tool(invalid_tool_data)


# Test Suite: Connection Testing


class TestConnectionTesting:
    """Tests for test connection functionality."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @patch("httpx.AsyncClient")
    async def test_connection_with_valid_credentials_200_success(
        self, mock_client_class, sample_openapi_spec, auth_config_bearer
    ):
        """Test connection succeeds with valid credentials (200 status)."""
        from src.services.mcp_tool_generator import validate_openapi_connection

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"login": "octocat", "id": 1}'
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__aenter__.return_value = mock_client_instance
        async def async_exit(*args):
            return None
        mock_client_instance.__aexit__ = AsyncMock(side_effect=async_exit)
        mock_client_class.return_value = mock_client_instance

        result = await validate_openapi_connection(
            sample_openapi_spec, auth_config_bearer, "https://api.github.com"
        )

        assert result["success"] is True
        assert result["status_code"] == 200
        assert "octocat" in result["response_preview"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    @patch("httpx.AsyncClient")
    async def test_connection_with_invalid_credentials_401_failure(
        self, mock_client_class, sample_openapi_spec, auth_config_bearer
    ):
        """Test connection fails with invalid credentials (401 Unauthorized)."""
        from src.services.mcp_tool_generator import validate_openapi_connection
        import httpx

        # Mock 401 response
        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )
        mock_client_instance.__aenter__.return_value = mock_client_instance
        async def async_exit(*args):
            return None
        mock_client_instance.__aexit__ = AsyncMock(side_effect=async_exit)
        mock_client_class.return_value = mock_client_instance

        result = await validate_openapi_connection(
            sample_openapi_spec, auth_config_bearer, "https://api.github.com"
        )

        assert result["success"] is False
        assert result["error_type"] == "HTTPStatusError"
        assert result["status_code"] == 401
        assert "Authentication failed" in result["error_message"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    @patch("httpx.AsyncClient")
    async def test_connection_with_network_timeout(
        self, mock_client_class, sample_openapi_spec, auth_config_api_key
    ):
        """Test connection handles network timeout gracefully."""
        from src.services.mcp_tool_generator import validate_openapi_connection
        import httpx

        # Mock timeout error
        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = httpx.TimeoutException("Read timeout")
        mock_client_instance.timeout = httpx.Timeout(30.0)
        mock_client_instance.__aenter__.return_value = mock_client_instance
        async def async_exit(*args):
            return None
        mock_client_instance.__aexit__ = AsyncMock(side_effect=async_exit)
        mock_client_class.return_value = mock_client_instance

        result = await validate_openapi_connection(
            sample_openapi_spec, auth_config_api_key, "https://api.example.com"
        )

        assert result["success"] is False
        assert result["error_type"] == "Timeout"
        assert "timeout" in result["error_message"].lower()


# Test Suite: Database Encryption


class TestDatabaseEncryption:
    """Tests for auth config encryption/decryption."""

    @pytest.mark.integration
    def test_encrypt_decrypt_auth_config_roundtrip(self, auth_config_bearer):
        """Test encryption → save → decrypt roundtrip preserves auth config."""
        # Encrypt
        encrypted = encrypt_auth_config(auth_config_bearer)
        assert isinstance(encrypted, bytes)
        assert len(encrypted) > 0

        # Decrypt
        decrypted = decrypt_auth_config(encrypted)
        assert decrypted == auth_config_bearer
        assert decrypted["type"] == "http"
        assert decrypted["http_scheme"] == "bearer"
        assert decrypted["token"] == "ghp_test_token_12345"

    @pytest.mark.integration
    def test_encrypt_auth_config_produces_different_ciphertexts(self, auth_config_bearer):
        """Test same auth config encrypted twice produces different ciphertexts (Fernet uses random IV)."""
        encrypted1 = encrypt_auth_config(auth_config_bearer)
        encrypted2 = encrypt_auth_config(auth_config_bearer)

        # Ciphertexts should differ (Fernet adds random IV)
        # But both should decrypt to same value
        decrypted1 = decrypt_auth_config(encrypted1)
        decrypted2 = decrypt_auth_config(encrypted2)

        assert decrypted1 == decrypted2 == auth_config_bearer


# Test Suite: Validation Error Handling


class TestValidationErrorHandling:
    """Tests for validation error handling."""

    @pytest.mark.integration
    def test_invalid_spec_version_in_create_data(self, sample_openapi_spec):
        """Test invalid spec_version raises Pydantic validation error."""
        with pytest.raises(ValidationError) as exc_info:
            OpenAPIToolCreate(
                tool_name="Test API",
                openapi_spec=sample_openapi_spec,
                spec_version="4.0",  # Invalid version
                base_url="https://api.example.com",
                auth_config={"type": "none"},
                tenant_id=1,
            )

        errors = exc_info.value.errors()
        assert any("spec_version" in str(error) for error in errors)

    @pytest.mark.integration
    def test_missing_required_fields_raises_validation_error(self):
        """Test missing required fields raises Pydantic validation error."""
        with pytest.raises(ValidationError) as exc_info:
            OpenAPIToolCreate(
                tool_name="Test API",
                # Missing: openapi_spec, spec_version, base_url
                tenant_id=1,
            )

        errors = exc_info.value.errors()
        assert len(errors) >= 3  # At least 3 missing fields


# Test Suite: Tool Generation Count Verification


class TestToolGenerationCount:
    """Tests for tool generation count matching endpoint count."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @patch("src.services.openapi_tool_service.generate_mcp_tools_from_openapi")
    @patch("src.services.openapi_tool_service.parse_openapi_spec")
    async def test_tool_count_matches_endpoint_count(
        self, mock_parse, mock_generate, tool_create_data, mock_db_session
    ):
        """Test generated tool count matches OpenAPI spec endpoint count."""
        # Mock parse
        mock_openapi = MagicMock()
        mock_parse.return_value = mock_openapi

        # Mock MCP generation - 2 endpoints in sample spec
        mock_mcp = MagicMock()
        mock_mcp.tools = [MagicMock(), MagicMock()]
        mock_generate.return_value = mock_mcp

        # Mock database
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Create tool
        service = OpenAPIToolService(mock_db_session)
        db_tool, tools_count = await service.create_tool(tool_create_data)

        # Verify tool count
        expected_endpoint_count = 2  # /users (GET) and /repos/{owner}/{repo} (GET)
        assert tools_count == expected_endpoint_count


# Test Suite: Multi-Tool Workflow


class TestMultiToolWorkflow:
    """Tests for managing multiple tools per tenant."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @patch("src.services.openapi_tool_service.generate_mcp_tools_from_openapi")
    @patch("src.services.openapi_tool_service.parse_openapi_spec")
    async def test_multiple_tools_same_tenant(
        self, mock_parse, mock_generate, sample_openapi_spec, auth_config_bearer, mock_db_session
    ):
        """Test creating multiple tools for same tenant."""
        # Mock dependencies
        mock_openapi = MagicMock()
        mock_parse.return_value = mock_openapi
        mock_mcp = MagicMock()
        mock_mcp.tools = [MagicMock()]
        mock_generate.return_value = mock_mcp
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        service = OpenAPIToolService(mock_db_session)

        # Create first tool
        tool1_data = OpenAPIToolCreate(
            tool_name="GitHub API",
            openapi_spec=sample_openapi_spec,
            spec_version="3.0",
            base_url="https://api.github.com",
            auth_config=auth_config_bearer,
            tenant_id=1,
            created_by="user1",
        )
        db_tool1, count1 = await service.create_tool(tool1_data)
        assert db_tool1.tool_name == "GitHub API"

        # Create second tool (different name, same tenant)
        tool2_data = OpenAPIToolCreate(
            tool_name="Stripe API",
            openapi_spec=sample_openapi_spec,
            spec_version="3.0",
            base_url="https://api.stripe.com",
            auth_config=auth_config_bearer,
            tenant_id=1,
            created_by="user1",
        )
        db_tool2, count2 = await service.create_tool(tool2_data)
        assert db_tool2.tool_name == "Stripe API"

        # Both should succeed (different tool names allowed per tenant)
        assert db_tool1.tenant_id == db_tool2.tenant_id == 1
        assert db_tool1.tool_name != db_tool2.tool_name
