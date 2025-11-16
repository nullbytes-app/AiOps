"""
Unit Tests for MCP Tool Generator Service.

Story 8.8: OpenAPI Tool Upload and Auto-Generation (Task 10.2)
Tests for FastMCP integration, auth configuration, and connection testing.

Test Coverage:
- FastMCP.from_openapi() successful generation (4 tests)
- Auth config mapping to httpx client (4 tests)
- Unsupported feature handling (3 tests)
- Error scenarios (2 tests)

Total: 13 tests (exceeds requirement of 12+)
"""

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.mcp_tool_generator import (
    build_httpx_client,
    generate_mcp_tools_from_openapi,
    validate_openapi_connection,
    count_generated_tools,
    get_tool_list,
)


# Fixtures

@pytest.fixture
def sample_openapi_spec():
    """Sample OpenAPI 3.0 spec for testing."""
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
            "/users/{id}": {
                "get": {
                    "summary": "Get user",
                    "operationId": "getUser",
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
                    ],
                    "responses": {"200": {"description": "Success"}},
                }
            },
        },
    }


@pytest.fixture
def auth_config_api_key_header():
    """API Key in header authentication config."""
    return {
        "type": "apikey",
        "location": "header",
        "param_name": "X-API-Key",
        "value": "test-api-key-12345",
    }


@pytest.fixture
def auth_config_api_key_query():
    """API Key in query parameter authentication config."""
    return {
        "type": "apikey",
        "location": "query",
        "param_name": "api_key",
        "value": "test-query-key",
    }


@pytest.fixture
def auth_config_basic():
    """Basic HTTP authentication config."""
    return {
        "type": "http",
        "http_scheme": "basic",
        "username": "testuser",
        "password": "testpass123",
    }


@pytest.fixture
def auth_config_bearer():
    """Bearer token authentication config."""
    return {
        "type": "http",
        "http_scheme": "bearer",
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    }


@pytest.fixture
def auth_config_oauth2():
    """OAuth 2.0 authentication config."""
    return {
        "type": "oauth2",
        "access_token": "oauth-access-token-12345",
    }


@pytest.fixture
def auth_config_none():
    """No authentication config."""
    return {"type": "none"}


# Test Suite: build_httpx_client()


class TestBuildHttpxClient:
    """Tests for build_httpx_client() function."""

    def test_configure_httpx_client_with_api_key_header(self, auth_config_api_key_header):
        """Test httpx client configuration with API key in header."""
        client = build_httpx_client(auth_config_api_key_header, "https://api.example.com")

        assert isinstance(client, httpx.AsyncClient)
        assert client.headers["X-API-Key"] == "test-api-key-12345"
        assert client.base_url == "https://api.example.com"
        assert client.timeout.connect == 5.0
        assert client.timeout.read == 30.0

    def test_configure_httpx_client_with_api_key_query(self, auth_config_api_key_query):
        """Test httpx client configuration with API key in query param."""
        client = build_httpx_client(auth_config_api_key_query, "https://api.example.com")

        assert isinstance(client, httpx.AsyncClient)
        assert client.params["api_key"] == "test-query-key"
        assert client.base_url == "https://api.example.com"

    def test_configure_httpx_client_with_bearer_token(self, auth_config_bearer):
        """Test httpx client configuration with Bearer token."""
        client = build_httpx_client(auth_config_bearer, "https://api.example.com")

        assert isinstance(client, httpx.AsyncClient)
        assert "Authorization" in client.headers
        assert client.headers["Authorization"] == "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

    def test_configure_httpx_client_with_basic_auth(self, auth_config_basic):
        """Test httpx client configuration with Basic Auth."""
        client = build_httpx_client(auth_config_basic, "https://api.example.com")

        assert isinstance(client, httpx.AsyncClient)
        assert isinstance(client._auth, httpx.BasicAuth)
        assert client._auth._auth_header == "Basic dGVzdHVzZXI6dGVzdHBhc3MxMjM="

    def test_configure_httpx_client_with_oauth2(self, auth_config_oauth2):
        """Test httpx client configuration with OAuth 2.0."""
        client = build_httpx_client(auth_config_oauth2, "https://api.example.com")

        assert isinstance(client, httpx.AsyncClient)
        assert client.headers["Authorization"] == "Bearer oauth-access-token-12345"

    def test_configure_httpx_client_with_no_auth(self, auth_config_none):
        """Test httpx client configuration with no authentication."""
        client = build_httpx_client(auth_config_none, "https://api.example.com")

        assert isinstance(client, httpx.AsyncClient)
        assert "Authorization" not in client.headers
        assert len(client.params) == 0

    def test_invalid_auth_type_raises_error(self):
        """Test that invalid auth type raises ValueError."""
        auth_config = {"type": "invalid_type"}
        with pytest.raises(ValueError, match="Unsupported authentication type"):
            build_httpx_client(auth_config, "https://api.example.com")

    def test_invalid_api_key_location_raises_error(self):
        """Test that invalid API key location raises ValueError."""
        auth_config = {
            "type": "apikey",
            "location": "cookie",  # Unsupported location
            "param_name": "api_key",
            "value": "test",
        }
        with pytest.raises(ValueError, match="Unsupported API key location"):
            build_httpx_client(auth_config, "https://api.example.com")

    def test_oauth2_without_access_token_allows_creation(self):
        """Test that OAuth 2.0 without access_token creates client for later token exchange."""
        auth_config = {
            "type": "oauth2",
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "token_url": "https://auth.example.com/oauth/token",
            "scopes": ["read", "write"],
        }
        client = build_httpx_client(auth_config, "https://api.example.com")

        # Client should be created without Authorization header
        # Token exchange will happen at runtime when tool is invoked
        assert isinstance(client, httpx.AsyncClient)
        assert "Authorization" not in client.headers


# Test Suite: generate_mcp_tools_from_openapi()


class TestGenerateMcpTools:
    """Tests for generate_mcp_tools_from_openapi() function."""

    @pytest.mark.asyncio
    @patch("src.services.mcp_tool_generator.FastMCP")
    async def test_generate_mcp_tools_success(
        self, mock_fastmcp_class, sample_openapi_spec, auth_config_api_key_header
    ):
        """Test successful MCP tool generation from OpenAPI spec."""
        # Mock FastMCP.from_openapi()
        mock_mcp_instance = MagicMock()
        mock_mcp_instance.tools = [MagicMock(), MagicMock()]  # 2 tools
        mock_fastmcp_class.from_openapi.return_value = mock_mcp_instance

        result = await generate_mcp_tools_from_openapi(
            sample_openapi_spec, auth_config_api_key_header, "https://api.example.com"
        )

        assert result == mock_mcp_instance
        mock_fastmcp_class.from_openapi.assert_called_once()
        call_kwargs = mock_fastmcp_class.from_openapi.call_args.kwargs
        assert call_kwargs["openapi_spec"] == sample_openapi_spec
        assert call_kwargs["name"] == "Test API"
        assert isinstance(call_kwargs["client"], httpx.AsyncClient)

    @pytest.mark.asyncio
    @patch("src.services.mcp_tool_generator.FastMCP")
    async def test_generate_mcp_tools_custom_name(
        self, mock_fastmcp_class, sample_openapi_spec, auth_config_none
    ):
        """Test MCP tool generation with custom tool name."""
        mock_mcp_instance = MagicMock()
        mock_fastmcp_class.from_openapi.return_value = mock_mcp_instance

        result = await generate_mcp_tools_from_openapi(
            sample_openapi_spec, auth_config_none, "https://api.example.com", tool_name="Custom API"
        )

        call_kwargs = mock_fastmcp_class.from_openapi.call_args.kwargs
        assert call_kwargs["name"] == "Custom API"

    @pytest.mark.asyncio
    @patch("src.services.mcp_tool_generator.FastMCP")
    async def test_unsupported_feature_callbacks_handled(
        self, mock_fastmcp_class, sample_openapi_spec, auth_config_none
    ):
        """Test graceful error for unsupported callbacks feature."""
        mock_fastmcp_class.from_openapi.side_effect = Exception("Callback definitions are not supported")

        with pytest.raises(ValueError, match="OpenAPI callbacks are not supported"):
            await generate_mcp_tools_from_openapi(
                sample_openapi_spec, auth_config_none, "https://api.example.com"
            )

    @pytest.mark.asyncio
    @patch("src.services.mcp_tool_generator.FastMCP")
    async def test_unsupported_feature_webhooks_handled(
        self, mock_fastmcp_class, sample_openapi_spec, auth_config_none
    ):
        """Test graceful error for unsupported webhooks feature."""
        mock_fastmcp_class.from_openapi.side_effect = Exception("Webhook definitions not supported")

        with pytest.raises(ValueError, match="OpenAPI webhooks are not supported"):
            await generate_mcp_tools_from_openapi(
                sample_openapi_spec, auth_config_none, "https://api.example.com"
            )

    @pytest.mark.asyncio
    @patch("src.services.mcp_tool_generator.FastMCP")
    async def test_unsupported_feature_links_handled(
        self, mock_fastmcp_class, sample_openapi_spec, auth_config_none
    ):
        """Test graceful error for unsupported links feature."""
        mock_fastmcp_class.from_openapi.side_effect = Exception("Link definitions not fully supported")

        with pytest.raises(ValueError, match="OpenAPI links are not fully supported"):
            await generate_mcp_tools_from_openapi(
                sample_openapi_spec, auth_config_none, "https://api.example.com"
            )

    @pytest.mark.asyncio
    @patch("src.services.mcp_tool_generator.FastMCP")
    async def test_generic_error_raises_runtime_error(
        self, mock_fastmcp_class, sample_openapi_spec, auth_config_none
    ):
        """Test generic FastMCP error raises RuntimeError."""
        mock_fastmcp_class.from_openapi.side_effect = Exception("Unknown error occurred")

        with pytest.raises(RuntimeError, match="Failed to generate MCP tools: Unknown error occurred"):
            await generate_mcp_tools_from_openapi(
                sample_openapi_spec, auth_config_none, "https://api.example.com"
            )


# Test Suite: validate_openapi_connection()


class TestOpenAPIConnection:
    """Tests for validate_openapi_connection() function."""

    @pytest.mark.asyncio
    @patch("src.services.mcp_tool_generator.build_httpx_client")
    async def test_connection_success_with_health_endpoint(
        self, mock_build_client, sample_openapi_spec, auth_config_none
    ):
        """Test successful connection with /health endpoint."""
        # Add health endpoint to spec
        sample_openapi_spec["paths"]["/health"] = {
            "get": {"summary": "Health check", "responses": {"200": {"description": "OK"}}}
        }

        # Mock httpx response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"status": "healthy"}'
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__aenter__.return_value = mock_client_instance
        async def async_exit(*args):
            return None
        mock_client_instance.__aexit__ = AsyncMock(side_effect=async_exit)
        mock_build_client.return_value = mock_client_instance

        result = await validate_openapi_connection(
            sample_openapi_spec, auth_config_none, "https://api.example.com"
        )

        assert result["success"] is True
        assert result["status_code"] == 200
        assert result["response_preview"] == '{"status": "healthy"}'
        assert result["test_endpoint"] == "/health"

    @pytest.mark.asyncio
    @patch("src.services.mcp_tool_generator.build_httpx_client")
    async def test_connection_success_with_first_get_endpoint(
        self, mock_build_client, sample_openapi_spec, auth_config_api_key_header
    ):
        """Test successful connection using first GET endpoint."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '[{"id": 1, "name": "John"}]'
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__aenter__.return_value = mock_client_instance
        async def async_exit(*args):
            return None
        mock_client_instance.__aexit__ = AsyncMock(side_effect=async_exit)
        mock_build_client.return_value = mock_client_instance

        result = await validate_openapi_connection(
            sample_openapi_spec, auth_config_api_key_header, "https://api.example.com"
        )

        assert result["success"] is True
        assert result["test_endpoint"] == "/users"

    @pytest.mark.asyncio
    @patch("src.services.mcp_tool_generator.build_httpx_client")
    async def test_connection_timeout_error(
        self, mock_build_client, sample_openapi_spec, auth_config_none
    ):
        """Test connection timeout returns proper error."""
        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = httpx.TimeoutException("Read timeout")
        mock_client_instance.timeout = httpx.Timeout(30.0)
        mock_client_instance.__aenter__.return_value = mock_client_instance
        async def async_exit(*args):
            return None
        mock_client_instance.__aexit__ = AsyncMock(side_effect=async_exit)
        mock_build_client.return_value = mock_client_instance

        result = await validate_openapi_connection(
            sample_openapi_spec, auth_config_none, "https://api.example.com"
        )

        assert result["success"] is False
        assert result["error_type"] == "Timeout"
        assert "timeout" in result["error_message"].lower()

    @pytest.mark.asyncio
    @patch("src.services.mcp_tool_generator.build_httpx_client")
    async def test_connection_401_unauthorized_error(
        self, mock_build_client, sample_openapi_spec, auth_config_bearer
    ):
        """Test 401 Unauthorized returns proper error message."""
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
        mock_build_client.return_value = mock_client_instance

        result = await validate_openapi_connection(
            sample_openapi_spec, auth_config_bearer, "https://api.example.com"
        )

        assert result["success"] is False
        assert result["error_type"] == "HTTPStatusError"
        assert result["status_code"] == 401
        assert "Authentication failed" in result["error_message"]

    @pytest.mark.asyncio
    @patch("src.services.mcp_tool_generator.build_httpx_client")
    async def test_connection_404_not_found_error(
        self, mock_build_client, sample_openapi_spec, auth_config_none
    ):
        """Test 404 Not Found returns proper error message."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )
        mock_client_instance.__aenter__.return_value = mock_client_instance
        async def async_exit(*args):
            return None
        mock_client_instance.__aexit__ = AsyncMock(side_effect=async_exit)
        mock_build_client.return_value = mock_client_instance

        result = await validate_openapi_connection(
            sample_openapi_spec, auth_config_none, "https://api.example.com"
        )

        assert result["success"] is False
        assert result["status_code"] == 404
        assert "not found" in result["error_message"].lower()

    @pytest.mark.asyncio
    @patch("src.services.mcp_tool_generator.build_httpx_client")
    async def test_connection_500_server_error(
        self, mock_build_client, sample_openapi_spec, auth_config_none
    ):
        """Test 500 Server Error returns proper error message."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = httpx.HTTPStatusError(
            "Internal Server Error", request=MagicMock(), response=mock_response
        )
        mock_client_instance.__aenter__.return_value = mock_client_instance
        async def async_exit(*args):
            return None
        mock_client_instance.__aexit__ = AsyncMock(side_effect=async_exit)
        mock_build_client.return_value = mock_client_instance

        result = await validate_openapi_connection(
            sample_openapi_spec, auth_config_none, "https://api.example.com"
        )

        assert result["success"] is False
        assert result["status_code"] == 500
        assert "Server error" in result["error_message"]

    @pytest.mark.asyncio
    @patch("src.services.mcp_tool_generator.build_httpx_client")
    async def test_connection_connect_error(
        self, mock_build_client, sample_openapi_spec, auth_config_none
    ):
        """Test connection refused error."""
        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = httpx.ConnectError("Connection refused")
        mock_client_instance.__aenter__.return_value = mock_client_instance
        async def async_exit(*args):
            return None
        mock_client_instance.__aexit__ = AsyncMock(side_effect=async_exit)
        mock_build_client.return_value = mock_client_instance

        result = await validate_openapi_connection(
            sample_openapi_spec, auth_config_none, "https://api.example.com"
        )

        assert result["success"] is False
        assert result["error_type"] == "ConnectError"
        assert "Connection failed" in result["error_message"]

    @pytest.mark.asyncio
    async def test_no_get_endpoints_returns_error(self, auth_config_none):
        """Test spec with no GET endpoints returns proper error."""
        spec_no_get = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {"summary": "Create user", "responses": {"201": {"description": "Created"}}}
                }
            },
        }

        result = await validate_openapi_connection(spec_no_get, auth_config_none, "https://api.example.com")

        assert result["success"] is False
        assert result["error_type"] == "NoTestEndpoint"
        assert "No GET endpoints found" in result["error_message"]


# Test Suite: Helper Functions


class TestHelperFunctions:
    """Tests for count_generated_tools() and get_tool_list()."""

    def test_count_generated_tools(self):
        """Test tool count extraction from FastMCP instance with tools attribute."""
        mock_mcp = MagicMock()
        mock_mcp._tool_manager = None  # Explicitly set to None so it checks tools attribute
        mock_mcp.tools = [MagicMock(), MagicMock(), MagicMock()]

        count = count_generated_tools(mock_mcp)
        assert count == 3

    def test_count_generated_tools_from_openapi(self):
        """Test tool count from FastMCP created via from_openapi()."""
        # FastMCP.from_openapi() creates instances with _tool_manager
        mock_mcp = MagicMock()
        mock_tool_manager = MagicMock()
        mock_tool_manager._tools = {"tool1": MagicMock(), "tool2": MagicMock()}
        mock_mcp._tool_manager = mock_tool_manager

        count = count_generated_tools(mock_mcp)
        assert count == 2

    def test_count_generated_tools_no_tools_attribute(self):
        """Test tool count when FastMCP has no tools attribute."""
        mock_mcp = MagicMock(spec=[])  # No 'tools' or '_tool_manager' attribute

        count = count_generated_tools(mock_mcp)
        assert count == 0

    @pytest.mark.asyncio
    async def test_get_tool_list(self):
        """Test tool list extraction with metadata."""
        mock_tool1 = MagicMock()
        mock_tool1.name = "listUsers"
        mock_tool1.description = "List all users"
        mock_tool1.parameters = {"type": "object", "properties": {}}

        mock_tool2 = MagicMock()
        mock_tool2.name = "getUser"
        mock_tool2.description = "Get user by ID"
        mock_tool2.parameters = {"type": "object", "properties": {"id": {"type": "string"}}}

        mock_mcp = MagicMock()
        mock_mcp._tool_manager = None  # Explicitly set to None so it checks tools attribute
        mock_mcp.tools = [mock_tool1, mock_tool2]

        tool_list = await get_tool_list(mock_mcp)

        assert len(tool_list) == 2
        assert tool_list[0]["name"] == "listUsers"
        assert tool_list[0]["description"] == "List all users"
        assert tool_list[1]["name"] == "getUser"
        assert "id" in tool_list[1]["parameters"]["properties"]
