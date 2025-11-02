"""
Reusable ServiceDesk Plus API response fixtures for tests.

This module provides a small, framework-agnostic HTTP response shape and a set
of ready-to-use fixtures that mirror common scenarios when integrating with the
ServiceDesk Plus API:

- Success (200)
- Unauthorized (401)
- Internal Server Error (500)
- Rate Limit Exceeded (429)
- Connection Timeout (no HTTP status; simulated)

Each fixture is a simple, immutable object exposing three attributes:
`status_code` (int | None), `headers` (dict[str, str]), and `body` (dict).

Usage in tests (example):

    from tests.fixtures.api_responses import (
        servicedesk_success_response,
        servicedesk_401_unauthorized,
        servicedesk_500_error,
        servicedesk_429_rate_limit,
        connection_timeout_response,
        make_servicedesk_response,
    )

    def test_handles_success():
        resp = servicedesk_success_response
        assert resp.status_code == 200
        assert resp.body["response_status"] == "success"

    def test_can_customize_response():
        resp = make_servicedesk_response(202, body={"ack": True})
        assert resp.status_code == 202
        assert resp.body["ack"] is True

Notes on timeouts:
HTTP connection timeouts do not yield an HTTP response in real life (no status
code or headers). For convenience, `connection_timeout_response` uses
`status_code = None` and empty headers, with a JSON `body` describing the
timeout. Adjust to your application's expectations as needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional


@dataclass(frozen=True)
class HTTPResponse:
    """
    Minimal representation of an HTTP response for tests.

    - status_code: The HTTP status code, or None for network-level failures
      (e.g., connection timeout) where no response was received.
    - headers: A mapping of HTTP response headers (lower/upper casing preserved
      as provided).
    - body: Parsed JSON response payload as a Python dict.
    """

    status_code: Optional[int]
    headers: Dict[str, str]
    body: Dict[str, Any]


DEFAULT_HEADERS: Dict[str, str] = {
    # Common, realistic defaults for a JSON API response.
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
    "Server": "ServiceDeskPlus",
}


def _merge_headers(base: Mapping[str, str], extra: Optional[Mapping[str, str]]) -> Dict[str, str]:
    if not extra:
        return dict(base)
    merged = dict(base)
    merged.update(extra)
    return merged


def make_servicedesk_response(
    status_code: Optional[int],
    body: Optional[Dict[str, Any]] = None,
    headers: Optional[Mapping[str, str]] = None,
) -> HTTPResponse:
    """
    Factory for creating custom ServiceDesk-like responses in tests.

    Parameters:
    - status_code: HTTP status code (e.g., 200, 401). Use None to simulate
      network-level failures (e.g., connection timeout).
    - body: JSON-compatible dict for the response body. Defaults to `{}`.
    - headers: Optional response headers. Merged with DEFAULT_HEADERS where
      provided; user-provided values take precedence.

    Returns:
    - HTTPResponse: Immutable response object suitable for asserting in tests
      or for feeding into client adapters/mocks.

    Example:
        resp = make_servicedesk_response(202, {"ack": True}, {"X-Request-ID": "t1"})
    """

    return HTTPResponse(
        status_code=status_code,
        headers=_merge_headers(DEFAULT_HEADERS, headers),
        body=dict(body or {}),
    )


# ---------------------------------------------------------------------------
# Predefined fixtures
# ---------------------------------------------------------------------------

servicedesk_success_response: HTTPResponse = make_servicedesk_response(
    200,
    body={
        "response_status": "success",
        "resource": "/api/v3/requests",
        "data": {
            "request": {
                "id": 123456789,
                "subject": "Test ticket from fixtures",
                "status": "Open",
                "priority": "High",
                "created_time": "2024-01-15T12:34:56Z",
                "requester": {"name": "QA User", "id": 98765},
            }
        },
    },
    headers={
        "X-Request-ID": "req_fixture_success_001",
        "ETag": 'W/"f00ba4-abc123"',
    },
)
servicedesk_success_response.__doc__ = (
    "Successful 200 OK response fixture for ServiceDesk Plus API.\n"
    "Use this to simulate a typical successful GET/POST with a JSON payload."
)


servicedesk_401_unauthorized: HTTPResponse = make_servicedesk_response(
    401,
    body={
        "response_status": "error",
        "error": {
            "code": "AUTHENTICATION_FAILED",
            "message": "Invalid or expired API token.",
            "details": {
                "hint": "Verify your API key or OAuth token.",
            },
        },
    },
    headers={
        "WWW-Authenticate": 'Bearer realm="ServiceDesk Plus", error="invalid_token"',
        "X-Request-ID": "req_fixture_unauthorized_401",
    },
)
servicedesk_401_unauthorized.__doc__ = (
    "401 Unauthorized fixture.\n"
    "Use to test handling of invalid/expired credentials and auth flows."
)


servicedesk_500_error: HTTPResponse = make_servicedesk_response(
    500,
    body={
        "response_status": "error",
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "Unexpected server error. Please try again later.",
            "request_id": "req_fixture_internal_500",
        },
    },
    headers={
        "X-Request-ID": "req_fixture_internal_500",
    },
)
servicedesk_500_error.__doc__ = (
    "500 Internal Server Error fixture.\n"
    "Use to validate retries and error handling for server-side failures."
)


servicedesk_429_rate_limit: HTTPResponse = make_servicedesk_response(
    429,
    body={
        "response_status": "error",
        "error": {
            "code": "RATE_LIMIT_EXCEEDED",
            "message": "Too many requests; please retry later.",
        },
    },
    headers={
        "Retry-After": "30",
        "X-RateLimit-Limit": "120",
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": "1730540400",
        "X-Request-ID": "req_fixture_rate_limit_429",
    },
)
servicedesk_429_rate_limit.__doc__ = (
    "429 Rate Limit Exceeded fixture.\n"
    "Use to test backoff, Retry-After compliance, and rate limit handling."
)


connection_timeout_response: HTTPResponse = make_servicedesk_response(
    None,
    body={
        "response_status": "error",
        "error": {
            "code": "TIMEOUT",
            "message": "Connection timed out while connecting to ServiceDesk Plus.",
        },
    },
    headers={},
)
connection_timeout_response.__doc__ = (
    "Simulated connection timeout (no HTTP response).\n"
    "status_code is None and headers are empty. Use to model network-level\n"
    "failures where no server response is received."
)


__all__ = [
    "HTTPResponse",
    "DEFAULT_HEADERS",
    "make_servicedesk_response",
    "servicedesk_success_response",
    "servicedesk_401_unauthorized",
    "servicedesk_500_error",
    "servicedesk_429_rate_limit",
    "connection_timeout_response",
]

