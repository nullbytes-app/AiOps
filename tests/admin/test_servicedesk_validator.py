"""
Unit tests for servicedesk_validator.py.

Tests ServiceDesk Plus API connection validation with mocked HTTP responses.
Uses pytest-httpx for mocking httpx requests.
"""

import pytest
from httpx import HTTPStatusError, RequestError, TimeoutException

from admin.utils.servicedesk_validator import (
    validate_servicedesk_connection,
    validate_servicedesk_url_format,
)


# ============================================================================
# URL Format Validation Tests
# ============================================================================


def test_validate_url_format_success():
    """Test URL format validation with valid URLs."""
    valid_urls = [
        "https://acme.servicedesk.com",
        "http://demo.servicedesk.local",
        "https://servicedesk.example.com:8080",
    ]

    for url in valid_urls:
        is_valid, error = validate_servicedesk_url_format(url)
        assert is_valid is True
        assert error == ""


def test_validate_url_format_missing_protocol():
    """Test validation fails for URLs without http/https."""
    is_valid, error = validate_servicedesk_url_format("acme.servicedesk.com")
    assert is_valid is False
    assert "http" in error.lower()


def test_validate_url_format_empty():
    """Test validation fails for empty URL."""
    is_valid, error = validate_servicedesk_url_format("")
    assert is_valid is False
    assert "empty" in error.lower()


def test_validate_url_format_typos():
    """Test validation catches common protocol typos."""
    typo_urls = [
        "htp://acme.servicedesk.com",
        "htps://acme.servicedesk.com",
    ]

    for url in typo_urls:
        is_valid, error = validate_servicedesk_url_format(url)
        assert is_valid is False
        assert "typo" in error.lower() or "invalid" in error.lower() or "http" in error.lower()


# ============================================================================
# Connection Test with Mocked HTTP Responses
# ============================================================================


def test_connection_success_200(httpx_mock):
    """Test successful connection with HTTP 200 and valid JSON."""
    url = "https://demo.servicedesk.com"
    api_key = "valid_key_123"

    # Mock successful API response
    httpx_mock.add_response(
        url=f"{url}/api/v3/requests?limit=1",
        method="GET",
        json={"requests": []},
        status_code=200,
    )

    success, message = validate_servicedesk_connection(url, api_key)

    assert success is True
    assert "success" in message.lower()
    assert "valid" in message.lower()


def test_connection_401_unauthorized(httpx_mock):
    """Test connection failure with HTTP 401 (invalid API key)."""
    url = "https://demo.servicedesk.com"
    api_key = "invalid_key"

    httpx_mock.add_response(
        url=f"{url}/api/v3/requests?limit=1",
        method="GET",
        status_code=401,
        json={"error": "Unauthorized"},
    )

    success, message = validate_servicedesk_connection(url, api_key)

    assert success is False
    assert "401" in message
    assert "invalid api key" in message.lower() or "authentication failed" in message.lower()


def test_connection_403_forbidden(httpx_mock):
    """Test connection failure with HTTP 403 (insufficient permissions)."""
    url = "https://demo.servicedesk.com"
    api_key = "limited_key"

    httpx_mock.add_response(
        url=f"{url}/api/v3/requests?limit=1",
        method="GET",
        status_code=403,
        json={"error": "Forbidden"},
    )

    success, message = validate_servicedesk_connection(url, api_key)

    assert success is False
    assert "403" in message
    assert "forbidden" in message.lower() or "permissions" in message.lower()


def test_connection_404_not_found(httpx_mock):
    """Test connection failure with HTTP 404 (invalid URL)."""
    url = "https://wrong.servicedesk.com"
    api_key = "valid_key"

    httpx_mock.add_response(
        url=f"{url}/api/v3/requests?limit=1",
        method="GET",
        status_code=404,
        text="Not Found",
    )

    success, message = validate_servicedesk_connection(url, api_key)

    assert success is False
    assert "404" in message
    assert "invalid url" in message.lower() or "not found" in message.lower()


def test_connection_timeout(httpx_mock):
    """Test connection failure with timeout."""
    url = "https://slow.servicedesk.com"
    api_key = "valid_key"

    # Mock timeout exception
    httpx_mock.add_exception(
        TimeoutException("Connection timeout"),
        url=f"{url}/api/v3/requests?limit=1",
    )

    success, message = validate_servicedesk_connection(url, api_key)

    assert success is False
    assert "timeout" in message.lower()


def test_connection_network_error(httpx_mock):
    """Test connection failure with network error."""
    url = "https://unreachable.servicedesk.com"
    api_key = "valid_key"

    # Mock network request error
    httpx_mock.add_exception(
        RequestError("Network unreachable"),
        url=f"{url}/api/v3/requests?limit=1",
    )

    success, message = validate_servicedesk_connection(url, api_key)

    assert success is False
    assert "network error" in message.lower() or "connection failed" in message.lower()


def test_connection_invalid_json_response(httpx_mock):
    """Test connection handles invalid JSON response."""
    url = "https://demo.servicedesk.com"
    api_key = "valid_key"

    # Mock 200 response but with invalid JSON
    httpx_mock.add_response(
        url=f"{url}/api/v3/requests?limit=1",
        method="GET",
        text="<html>Not JSON</html>",
        status_code=200,
    )

    success, message = validate_servicedesk_connection(url, api_key)

    assert success is False
    assert "json" in message.lower() or "format" in message.lower()


def test_connection_unexpected_status_code(httpx_mock):
    """Test connection handles unexpected status codes."""
    url = "https://demo.servicedesk.com"
    api_key = "valid_key"

    httpx_mock.add_response(
        url=f"{url}/api/v3/requests?limit=1",
        method="GET",
        status_code=500,
        text="Internal Server Error",
    )

    success, message = validate_servicedesk_connection(url, api_key)

    assert success is False
    assert "500" in message


def test_connection_strips_trailing_slash(httpx_mock):
    """Test URL trailing slash is handled correctly."""
    url = "https://demo.servicedesk.com/"  # Note trailing slash
    api_key = "valid_key"

    # Mock expects URL without trailing slash
    httpx_mock.add_response(
        url="https://demo.servicedesk.com/api/v3/requests?limit=1",
        method="GET",
        json={"requests": []},
        status_code=200,
    )

    success, message = validate_servicedesk_connection(url, api_key)

    assert success is True


def test_connection_includes_auth_header(httpx_mock):
    """Test API request includes correct authentication header."""
    import httpx

    url = "https://demo.servicedesk.com"
    api_key = "test_key_12345"

    def check_headers(request):
        # Verify authtoken header is present
        assert "authtoken" in request.headers
        assert request.headers["authtoken"] == api_key
        return httpx.Response(200, json={"requests": []})

    # Match with query parameters
    httpx_mock.add_callback(check_headers, url=f"{url}/api/v3/requests?limit=1")

    success, message = validate_servicedesk_connection(url, api_key)

    assert success is True
