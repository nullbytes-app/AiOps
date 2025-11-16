"""
MCP HTTP Response Handlers

Internal helper module for handling HTTP and SSE responses in MCP Streamable HTTP client.
This module contains response parsing and error handling logic extracted for modularity.
"""

import json
from typing import Any, cast

import httpx
from httpx_sse import aconnect_sse
from loguru import logger

from src.services.mcp_stdio_client import (
    MCPError,
    InvalidJSONError,
    TimeoutError as MCPTimeoutError,
)


# HTTP-specific exceptions (re-exported from main client)
class MCPConnectionError(MCPError):
    """Raised when HTTP connection fails."""

    pass


class MCPClientError(MCPError):
    """Raised for HTTP 4xx client errors."""

    pass


class MCPServerError(MCPError):
    """Raised for HTTP 5xx server errors."""

    pass


async def handle_sse_stream(
    client: httpx.AsyncClient, url: str, jsonrpc_payload: dict[str, Any]
) -> tuple[dict[str, Any], str | None]:
    """
    Handle SSE stream response mode (text/event-stream).

    Args:
        client: httpx.AsyncClient instance for making requests.
        url: MCP server URL endpoint.
        jsonrpc_payload: JSON-RPC request payload to send.

    Returns:
        Tuple of (JSON-RPC result dict, last event ID).

    Raises:
        InvalidJSONError: If SSE event data is not valid JSON.
        MCPError: If no matching response found or JSON-RPC error.
    """
    request_id = jsonrpc_payload.get("id")
    cumulative_events = 0
    last_event_id: str | None = None

    try:
        async with aconnect_sse(client, "POST", url, json=jsonrpc_payload) as event_source:
            async for event in event_source.aiter_sse():
                cumulative_events += 1

                # Store event ID for resumability
                if event.id:
                    last_event_id = event.id

                # Log SSE event
                logger.debug(
                    "SSE event received",
                    event_id=event.id,
                    event_type=event.event,
                    data_size=len(event.data) if event.data else 0,
                    cumulative=cumulative_events,
                )

                # Parse event data as JSON-RPC
                try:
                    data = json.loads(event.data)
                except json.JSONDecodeError as e:
                    logger.warning(f"Skipping non-JSON SSE event: {e}")
                    continue

                # Check if this is the matching response
                if data.get("id") == request_id:
                    # Check for JSON-RPC error
                    if "error" in data:
                        error = data["error"]
                        raise MCPError(f"JSON-RPC error: {error.get('message', 'Unknown error')}")

                    # Return result and last event ID
                    return cast(dict[str, Any], data.get("result", {})), last_event_id

            # No matching response found in stream
            raise MCPError(f"No response found for request ID {request_id} in SSE stream")

    except httpx.HTTPStatusError as e:
        # Handle SSE connection errors
        logger.error("SSE stream error", status_code=e.response.status_code)
        raise


def handle_json_response(response: httpx.Response) -> dict[str, Any]:
    """
    Handle single JSON response mode (application/json).

    Args:
        response: httpx.Response with application/json Content-Type.

    Returns:
        JSON-RPC result dict.

    Raises:
        InvalidJSONError: If response is not valid JSON-RPC.
        MCPError: If JSON-RPC error response.
    """
    try:
        data = response.json()
    except json.JSONDecodeError as e:
        raise InvalidJSONError(f"Invalid JSON response: {e}") from e

    # Validate JSON-RPC structure
    if "jsonrpc" not in data or data["jsonrpc"] != "2.0":
        raise InvalidJSONError(f"Invalid JSON-RPC response: {data}")

    # Check for JSON-RPC error
    if "error" in data:
        error = data["error"]
        raise MCPError(f"JSON-RPC error: {error.get('message', 'Unknown error')}")

    # Extract result
    return cast(dict[str, Any], data.get("result", {}))


async def post_request(
    client: httpx.AsyncClient,
    url: str,
    jsonrpc_payload: dict[str, Any],
    headers: dict[str, str],
    redact_func: callable,
) -> httpx.Response:
    """
    Send HTTP POST request to MCP server with comprehensive error handling.

    Args:
        client: httpx.AsyncClient instance for making requests.
        url: MCP server URL endpoint.
        jsonrpc_payload: JSON-RPC request payload.
        headers: HTTP headers dict.
        redact_func: Function to redact sensitive headers for logging.

    Returns:
        httpx.Response object.

    Raises:
        MCPConnectionError: On connection failures or timeouts.
        MCPClientError: On HTTP 4xx errors.
        MCPServerError: On HTTP 5xx errors.
    """
    request_id = jsonrpc_payload.get("id")
    method = jsonrpc_payload.get("method")

    # Log request (redact sensitive headers)
    logger.info(
        "MCP HTTP POST request",
        url=url,
        method=method,
        request_id=request_id,
        headers=redact_func(headers),
    )

    try:
        response = await client.post(url, json=jsonrpc_payload)
        response.raise_for_status()

        # Log response
        logger.info(
            "MCP HTTP response",
            status_code=response.status_code,
            content_type=response.headers.get("content-type"),
            http_version=response.http_version,
            request_id=request_id,
        )

        return response

    except httpx.ConnectTimeout as e:
        logger.error("Connection timeout", url=url, error=str(e))
        raise MCPConnectionError(f"Connection timeout to {url}") from e

    except httpx.ReadTimeout as e:
        logger.error("Read timeout", url=url, error=str(e))
        raise MCPConnectionError(f"Read timeout from {url}") from e

    except httpx.WriteTimeout as e:
        logger.error("Write timeout", url=url, error=str(e))
        raise MCPConnectionError(f"Write timeout to {url}") from e

    except httpx.PoolTimeout as e:
        logger.error("Pool timeout", url=url, error=str(e))
        raise MCPConnectionError("Connection pool exhausted") from e

    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        response_body = e.response.text[:500]  # Limit log size

        logger.error(
            "HTTP status error",
            status_code=status_code,
            url=url,
            response=response_body,
        )

        if 400 <= status_code < 500:
            raise MCPClientError(f"HTTP {status_code}: {response_body}") from e
        else:  # 500-599
            raise MCPServerError(f"HTTP {status_code}: {response_body}") from e

    except httpx.NetworkError as e:
        logger.error("Network error", url=url, error=str(e))
        raise MCPConnectionError(f"Network error: {e}") from e

    except httpx.TimeoutException as e:
        logger.error("Generic timeout", url=url, error=str(e))
        raise MCPTimeoutError(f"Request timeout: {e}") from e


def redact_sensitive_headers(headers: dict[str, str]) -> dict[str, str]:
    """
    Redact sensitive header values for logging.

    Args:
        headers: Original headers dict.

    Returns:
        Headers dict with sensitive values redacted.
    """
    redacted = headers.copy()

    sensitive_keys = [
        "authorization",
        "x-api-key",
        "api-key",
        "auth-token",
        "bearer",
    ]

    for key in redacted:
        if key.lower() in sensitive_keys:
            redacted[key] = "***REDACTED***"

    return redacted
