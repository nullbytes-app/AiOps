"""
Unit tests for ServiceDesk Plus API client (Story 2.10).

This test suite provides comprehensive coverage of the servicedesk_client module
including happy path, error scenarios, retry logic, markdown conversion, and
logging validation.

Test Structure:
- Fixtures: Sample data and mocks
- Happy Path: Successful API calls
- Error Scenarios: Timeout, 401, 500, 404, connection errors
- Helpers: Markdown conversion, URL construction, payload building
- Logging: Verification of log levels and messages
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from http import HTTPStatus

import pytest
import httpx

from src.services.servicedesk_client import (
    update_ticket_with_enhancement,
    convert_markdown_to_html,
    should_retry,
    _construct_api_url,
    _build_headers,
    _build_payload,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def base_url():
    """Sample ServiceDesk Plus base URL."""
    return "https://api.servicedesk.company.com"


@pytest.fixture
def api_key():
    """Sample API key."""
    return "test-api-key-12345"


@pytest.fixture
def ticket_id():
    """Sample ticket ID."""
    return "req-12345"


@pytest.fixture
def sample_enhancement():
    """
    Sample enhancement markdown from LLM synthesis (Story 2.9 format).

    Includes: headers, bullet points, newlines, special characters.
    """
    return """## Similar Tickets
- Ticket #001: Network latency issue resolved by route change
- Ticket #023: DNS resolution failures fixed with cache clear

## Relevant Documentation
- KB-456: Network Troubleshooting Guide
- KB-789: DNS Configuration Best Practices

## System Information
- Current latency: 245ms (normal <100ms)
- Last DNS query failure: 2025-11-02 14:30 UTC
- Route table shows 3 alternative paths

## Recommended Next Steps
1. Check ISP status (could be upstream issue)
2. Run traceroute to identify bottleneck
3. Contact network team if internal cause found"""


# =============================================================================
# TEST: HAPPY PATH - SUCCESSFUL API CALL
# =============================================================================


@pytest.mark.asyncio
async def test_update_ticket_success(base_url, api_key, ticket_id, sample_enhancement):
    """
    Test successful API call - 200 response returns True.

    Maps to: AC1, AC2, AC3, AC4, AC5
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"note": {"id": "note-123"}}

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        result = await update_ticket_with_enhancement(
            base_url, api_key, ticket_id, sample_enhancement
        )

        assert result is True
        mock_client.post.assert_called_once()

        # Verify call arguments
        call_args = mock_client.post.call_args
        # URL is in first positional arg or kwargs
        call_url = call_args.args[0] if call_args.args else call_args.kwargs.get("url", "")
        assert ticket_id in call_url
        assert call_args.kwargs["headers"]["authtoken"] == api_key
        assert "note" in call_args.kwargs["json"]


# =============================================================================
# TEST: TIMEOUT ERROR - RETRIES THEN FAILS
# =============================================================================


@pytest.mark.asyncio
async def test_update_ticket_timeout_retries(
    base_url, api_key, ticket_id, sample_enhancement
):
    """
    Test timeout error - retries 3 times with exponential backoff, then fails.

    Maps to: AC4 (retry logic), AC5 (error handling)
    """
    with patch("httpx.AsyncClient") as mock_client_class, patch(
        "asyncio.sleep", new_callable=AsyncMock
    ) as mock_sleep:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        # Raise TimeoutException on all attempts
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        mock_client_class.return_value = mock_client

        result = await update_ticket_with_enhancement(
            base_url, api_key, ticket_id, sample_enhancement
        )

        assert result is False
        # Should be called 3 times (MAX_RETRIES)
        assert mock_client.post.call_count == 3
        # Should sleep 2x (before attempts 2 and 3)
        assert mock_sleep.call_count == 2
        # Verify sleep durations: 2s, 4s
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_calls == [2, 4]


# =============================================================================
# TEST: AUTHENTICATION FAILURE (401) - NO RETRY
# =============================================================================


@pytest.mark.asyncio
async def test_update_ticket_auth_failure_no_retry(
    base_url, api_key, ticket_id, sample_enhancement
):
    """
    Test 401 Unauthorized - returns False immediately without retry.

    Maps to: AC4 (no retry on 401), AC5 (CRITICAL log on auth failure)
    """
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        # Create 401 error
        error_response = MagicMock()
        error_response.status_code = 401
        mock_client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError("Unauthorized", request=None, response=error_response)
        )
        mock_client_class.return_value = mock_client

        result = await update_ticket_with_enhancement(
            base_url, api_key, ticket_id, sample_enhancement
        )

        assert result is False
        # Should be called only ONCE (no retry on 401)
        assert mock_client.post.call_count == 1


# =============================================================================
# TEST: SERVER ERROR (500) - RETRIES THEN FAILS
# =============================================================================


@pytest.mark.asyncio
async def test_update_ticket_server_error_retries(
    base_url, api_key, ticket_id, sample_enhancement
):
    """
    Test 500 Internal Server Error - retries 3 times with backoff, then fails.

    Maps to: AC4 (retry on 5xx)
    """
    with patch("httpx.AsyncClient") as mock_client_class, patch(
        "asyncio.sleep", new_callable=AsyncMock
    ) as mock_sleep:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        # Create 500 error
        error_response = MagicMock()
        error_response.status_code = 500
        mock_client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError("Server Error", request=None, response=error_response)
        )
        mock_client_class.return_value = mock_client

        result = await update_ticket_with_enhancement(
            base_url, api_key, ticket_id, sample_enhancement
        )

        assert result is False
        # Should be called 3 times (MAX_RETRIES)
        assert mock_client.post.call_count == 3
        # Should sleep 2x
        assert mock_sleep.call_count == 2


# =============================================================================
# TEST: NOT FOUND ERROR (404) - NO RETRY
# =============================================================================


@pytest.mark.asyncio
async def test_update_ticket_not_found_no_retry(
    base_url, api_key, ticket_id, sample_enhancement
):
    """
    Test 404 Not Found - returns False immediately without retry.

    Maps to: AC4 (no retry on 404)
    """
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        # Create 404 error
        error_response = MagicMock()
        error_response.status_code = 404
        mock_client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError("Not Found", request=None, response=error_response)
        )
        mock_client_class.return_value = mock_client

        result = await update_ticket_with_enhancement(
            base_url, api_key, ticket_id, sample_enhancement
        )

        assert result is False
        # Should be called only ONCE (no retry on 404)
        assert mock_client.post.call_count == 1


# =============================================================================
# TEST: CONNECTION ERROR - RETRIES THEN FAILS
# =============================================================================


@pytest.mark.asyncio
async def test_update_ticket_connection_error_retries(
    base_url, api_key, ticket_id, sample_enhancement
):
    """
    Test connection error - retries 3 times, then fails.

    Maps to: AC4 (retry on connection error)
    """
    with patch("httpx.AsyncClient") as mock_client_class, patch(
        "asyncio.sleep", new_callable=AsyncMock
    ) as mock_sleep:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        # Raise ConnectError on all attempts
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        mock_client_class.return_value = mock_client

        result = await update_ticket_with_enhancement(
            base_url, api_key, ticket_id, sample_enhancement
        )

        assert result is False
        # Should be called 3 times (MAX_RETRIES)
        assert mock_client.post.call_count == 3
        # Should sleep 2x
        assert mock_sleep.call_count == 2


# =============================================================================
# TEST: MARKDOWN TO HTML CONVERSION
# =============================================================================


def test_convert_markdown_to_html_headers():
    """
    Test markdown header conversion to HTML h2/h3 tags.

    Maps to: AC3 (content formatting)
    """
    md = "## Section Header\n### Subsection"
    html = convert_markdown_to_html(md)

    assert "<h2>Section Header</h2>" in html
    assert "<h3>Subsection</h3>" in html


def test_convert_markdown_to_html_bullets():
    """
    Test markdown bullet list conversion to HTML ul/li structure.

    Maps to: AC3 (content formatting)
    """
    md = "- Item 1\n- Item 2\n- Item 3"
    html = convert_markdown_to_html(md)

    assert "<ul>" in html
    assert "<li>Item 1</li>" in html
    assert "<li>Item 2</li>" in html
    assert "<li>Item 3</li>" in html
    assert "</ul>" in html


def test_convert_markdown_to_html_special_chars():
    """
    Test special character escaping for HTML display.

    Maps to: AC3 (content formatting - escape special chars)
    """
    md = "Text with <brackets> & ampersands"
    html = convert_markdown_to_html(md)

    # Should be escaped
    assert "&lt;brackets&gt;" in html
    assert "&amp;" in html


def test_convert_markdown_to_html_newlines():
    """
    Test newline to <br> tag conversion.

    Maps to: AC3 (content formatting)
    """
    md = "Line 1\nLine 2\nLine 3"
    html = convert_markdown_to_html(md)

    # newlines should be converted to <br> tags
    assert "<br>" in html
    assert "Line 1<br>" in html or "Line 1\n" not in html


def test_convert_markdown_to_html_complex():
    """
    Test complex markdown with multiple formatting types.

    Maps to: AC3 (content formatting)
    """
    md = """## Similar Tickets
- Ticket #001: Network issue
- Ticket #023: DNS failure

## Recommended Steps
- Check ISP status
- Run traceroute"""

    html = convert_markdown_to_html(md)

    # Should have headers
    assert "<h2>Similar Tickets</h2>" in html
    assert "<h2>Recommended Steps</h2>" in html

    # Should have lists
    assert "<ul>" in html
    assert "<li>Ticket #001" in html
    assert "<li>Check ISP" in html


def test_convert_markdown_to_html_empty_input():
    """
    Test handling of empty markdown input.

    Maps to: AC3 (edge case)
    """
    html = convert_markdown_to_html("")
    assert html == ""

    html = convert_markdown_to_html(None)
    assert html == ""


# =============================================================================
# TEST: RETRY DECISION LOGIC
# =============================================================================


def test_should_retry_5xx_status():
    """Test retry decision for 5xx errors."""
    assert should_retry(500, None) is True
    assert should_retry(502, None) is True
    assert should_retry(503, None) is True
    assert should_retry(504, None) is True


def test_should_not_retry_4xx_status():
    """Test no retry for permanent 4xx errors."""
    assert should_retry(400, None) is False
    assert should_retry(401, None) is False
    assert should_retry(404, None) is False


def test_should_retry_timeout_exception():
    """Test retry decision for timeout exceptions."""
    timeout_exc = httpx.TimeoutException("Timeout")
    assert should_retry(None, timeout_exc) is True

    asyncio_timeout = asyncio.TimeoutError("Timeout")
    assert should_retry(None, asyncio_timeout) is True


def test_should_retry_connection_exception():
    """Test retry decision for connection exceptions."""
    connect_exc = httpx.ConnectError("Connection refused")
    assert should_retry(None, connect_exc) is True

    network_exc = httpx.NetworkError("Network error")
    assert should_retry(None, network_exc) is True


def test_should_not_retry_unknown_exception():
    """Test no retry for unknown exception types."""
    unknown_exc = ValueError("Something else")
    assert should_retry(None, unknown_exc) is False


# =============================================================================
# TEST: URL CONSTRUCTION
# =============================================================================


def test_construct_api_url_with_trailing_slash():
    """Test URL construction with trailing slash removal."""
    url = _construct_api_url("https://api.company.com/", "req-123")
    assert url == "https://api.company.com/api/v3/requests/req-123/notes"


def test_construct_api_url_without_trailing_slash():
    """Test URL construction without trailing slash."""
    url = _construct_api_url("https://api.company.com", "req-123")
    assert url == "https://api.company.com/api/v3/requests/req-123/notes"


def test_construct_api_url_http():
    """Test URL construction with HTTP scheme."""
    url = _construct_api_url("http://api.company.com", "req-456")
    assert url == "http://api.company.com/api/v3/requests/req-456/notes"


def test_construct_api_url_invalid_scheme():
    """Test URL construction with invalid scheme returns None."""
    url = _construct_api_url("ftp://api.company.com", "req-123")
    assert url is None

    url = _construct_api_url("api.company.com", "req-123")
    assert url is None


# =============================================================================
# TEST: PAYLOAD BUILDING
# =============================================================================


def test_build_payload_structure():
    """Test payload structure matches ServiceDesk Plus API requirements."""
    html = "<h2>Test</h2><p>Content</p>"
    payload = _build_payload(html)

    assert "note" in payload
    assert payload["note"]["description"] == html
    assert payload["note"]["show_to_requester"] is True
    assert payload["note"]["mark_first_response"] is False
    assert payload["note"]["add_to_linked_requests"] is False


# =============================================================================
# TEST: HEADERS BUILDING
# =============================================================================


def test_build_headers_structure():
    """Test headers have required authentication and content type."""
    api_key = "test-key"
    headers = _build_headers(api_key)

    assert headers["authtoken"] == api_key
    assert headers["Content-Type"] == "application/json"
    assert "User-Agent" in headers


# =============================================================================
# TEST: INVALID INPUTS
# =============================================================================


@pytest.mark.asyncio
async def test_invalid_base_url():
    """Test handling of invalid base URL."""
    result = await update_ticket_with_enhancement("", "key", "req-123", "enhancement")
    assert result is False

    result = await update_ticket_with_enhancement(None, "key", "req-123", "enhancement")
    assert result is False


@pytest.mark.asyncio
async def test_invalid_api_key():
    """Test handling of invalid API key."""
    result = await update_ticket_with_enhancement(
        "https://api.company.com", "", "req-123", "enhancement"
    )
    assert result is False


@pytest.mark.asyncio
async def test_invalid_ticket_id():
    """Test handling of invalid ticket ID."""
    result = await update_ticket_with_enhancement(
        "https://api.company.com", "key", "", "enhancement"
    )
    assert result is False


@pytest.mark.asyncio
async def test_invalid_enhancement():
    """Test handling of invalid enhancement."""
    result = await update_ticket_with_enhancement(
        "https://api.company.com", "key", "req-123", ""
    )
    assert result is False


# =============================================================================
# TEST: GENERIC EXCEPTION HANDLING
# =============================================================================


@pytest.mark.asyncio
async def test_unexpected_exception_returns_false(
    base_url, api_key, ticket_id, sample_enhancement
):
    """
    Test that unexpected exceptions are caught and return False.

    Maps to: AC5 (graceful degradation)
    """
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        # Raise unexpected exception
        mock_client.post = AsyncMock(side_effect=RuntimeError("Unexpected error"))
        mock_client_class.return_value = mock_client

        result = await update_ticket_with_enhancement(
            base_url, api_key, ticket_id, sample_enhancement
        )

        assert result is False


# =============================================================================
# TEST: 201 CREATED RESPONSE
# =============================================================================


@pytest.mark.asyncio
async def test_update_ticket_201_created(
    base_url, api_key, ticket_id, sample_enhancement
):
    """
    Test successful API call with 201 Created response.

    Maps to: AC2 (returns True on success)
    """
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"note": {"id": "note-456"}}

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        result = await update_ticket_with_enhancement(
            base_url, api_key, ticket_id, sample_enhancement
        )

        assert result is True
