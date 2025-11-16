"""
Unit tests for Jira connection validator.

Tests the synchronous Jira API connection validator used by Streamlit admin UI.
Validates behavior for success, authentication failures, and network errors.
"""

import pytest
from httpx import ConnectError, RequestError, TimeoutException

from admin.utils.jira_validator import validate_jira_connection, validate_jira_url_format


# ============================================================================
# Connection Tests
# ============================================================================


def test_connection_success_200(httpx_mock):
    """Test successful connection with HTTP 200 and valid JSON."""
    url = "https://company.atlassian.net"
    api_token = "valid_token_123"

    # Mock successful API response
    httpx_mock.add_response(
        url=f"{url}/rest/api/3/myself",
        method="GET",
        json={
            "displayName": "John Doe",
            "emailAddress": "john@example.com",
            "accountId": "abc123"
        },
        status_code=200,
    )

    success, message = validate_jira_connection(url, api_token)

    assert success is True
    assert "success" in message.lower()
    assert "John Doe" in message


def test_connection_401_unauthorized(httpx_mock):
    """Test connection failure with HTTP 401 (invalid API token)."""
    url = "https://company.atlassian.net"
    api_token = "invalid_token"

    httpx_mock.add_response(
        url=f"{url}/rest/api/3/myself",
        method="GET",
        status_code=401,
        json={"errorMessages": ["Unauthorized"]},
    )

    success, message = validate_jira_connection(url, api_token)

    assert success is False
    assert "401" in message
    assert "invalid api token" in message.lower() or "authentication failed" in message.lower()


def test_connection_403_forbidden(httpx_mock):
    """Test connection failure with HTTP 403 (insufficient permissions)."""
    url = "https://company.atlassian.net"
    api_token = "limited_token"

    httpx_mock.add_response(
        url=f"{url}/rest/api/3/myself",
        method="GET",
        status_code=403,
        json={"errorMessages": ["Forbidden"]},
    )

    success, message = validate_jira_connection(url, api_token)

    assert success is False
    assert "403" in message
    assert "forbidden" in message.lower() or "permissions" in message.lower()


def test_connection_404_not_found(httpx_mock):
    """Test connection failure with HTTP 404 (invalid URL)."""
    url = "https://wrong.atlassian.net"
    api_token = "valid_token"

    httpx_mock.add_response(
        url=f"{url}/rest/api/3/myself",
        method="GET",
        status_code=404,
        text="Not Found",
    )

    success, message = validate_jira_connection(url, api_token)

    assert success is False
    assert "404" in message
    assert "invalid url" in message.lower() or "not found" in message.lower()


def test_connection_timeout(httpx_mock):
    """Test connection failure with timeout."""
    url = "https://slow.atlassian.net"
    api_token = "valid_token"

    # Mock timeout exception
    httpx_mock.add_exception(
        TimeoutException("Connection timeout"),
        url=f"{url}/rest/api/3/myself",
    )

    success, message = validate_jira_connection(url, api_token)

    assert success is False
    assert "timeout" in message.lower()


def test_connection_network_error(httpx_mock):
    """Test connection failure with network error."""
    url = "https://unreachable.atlassian.net"
    api_token = "valid_token"

    # Mock network request error
    httpx_mock.add_exception(
        RequestError("Network unreachable"),
        url=f"{url}/rest/api/3/myself",
    )

    success, message = validate_jira_connection(url, api_token)

    assert success is False
    assert "network error" in message.lower() or "connection failed" in message.lower()


def test_connection_invalid_json_response(httpx_mock):
    """Test connection handles invalid JSON response."""
    url = "https://company.atlassian.net"
    api_token = "valid_token"

    # Mock 200 response but with invalid JSON
    httpx_mock.add_response(
        url=f"{url}/rest/api/3/myself",
        method="GET",
        text="<html>Not JSON</html>",
        status_code=200,
    )

    success, message = validate_jira_connection(url, api_token)

    assert success is False
    assert "json" in message.lower() or "format" in message.lower()


def test_connection_unexpected_status_code(httpx_mock):
    """Test connection handles unexpected status codes."""
    url = "https://company.atlassian.net"
    api_token = "valid_token"

    httpx_mock.add_response(
        url=f"{url}/rest/api/3/myself",
        method="GET",
        status_code=500,
        text="Internal Server Error",
    )

    success, message = validate_jira_connection(url, api_token)

    assert success is False
    assert "500" in message


def test_connection_strips_trailing_slash(httpx_mock):
    """Test URL trailing slash is handled correctly."""
    url = "https://company.atlassian.net/"  # Note trailing slash
    api_token = "valid_token"

    # Mock expects URL without trailing slash
    httpx_mock.add_response(
        url="https://company.atlassian.net/rest/api/3/myself",
        method="GET",
        json={"displayName": "Test User"},
        status_code=200,
    )

    success, message = validate_jira_connection(url, api_token)

    assert success is True


def test_connection_includes_auth_header(httpx_mock):
    """Test API request includes correct authentication header."""
    import httpx

    url = "https://company.atlassian.net"
    api_token = "test_token_12345"

    def check_headers(request):
        # Verify Bearer token is present
        assert "Authorization" in request.headers
        assert request.headers["Authorization"] == f"Bearer {api_token}"
        return httpx.Response(200, json={"displayName": "Test User"})

    httpx_mock.add_callback(check_headers, url=f"{url}/rest/api/3/myself")

    success, message = validate_jira_connection(url, api_token)

    assert success is True


# ============================================================================
# URL Format Validation Tests
# ============================================================================


def test_url_format_valid_atlassian():
    """Test valid Atlassian URL format."""
    is_valid, error = validate_jira_url_format("https://company.atlassian.net")
    assert is_valid is True
    assert error == ""


def test_url_format_valid_custom_jira():
    """Test valid custom Jira URL format."""
    is_valid, error = validate_jira_url_format("https://jira.example.com")
    assert is_valid is True
    assert error == ""


def test_url_format_empty():
    """Test empty URL is rejected."""
    is_valid, error = validate_jira_url_format("")
    assert is_valid is False
    assert "cannot be empty" in error.lower()


def test_url_format_missing_protocol():
    """Test URL without protocol is rejected."""
    is_valid, error = validate_jira_url_format("company.atlassian.net")
    assert is_valid is False
    assert "http" in error.lower()


def test_url_format_typo_in_protocol():
    """Test URL with protocol typo is rejected."""
    is_valid, error = validate_jira_url_format("htp://company.atlassian.net")
    assert is_valid is False
    assert "http" in error.lower()


def test_url_format_non_jira_warning():
    """Test warning for URLs that don't look like Jira."""
    is_valid, error = validate_jira_url_format("https://example.com")
    assert is_valid is False
    assert "not appear to be" in error.lower() or "jira" in error.lower()


def test_url_format_http_allowed():
    """Test HTTP (non-HTTPS) URLs are accepted."""
    is_valid, error = validate_jira_url_format("http://jira.internal.company.com")
    assert is_valid is True
    assert error == ""
