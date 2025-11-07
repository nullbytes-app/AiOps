"""
MCP Tool Generator Service - Generate MCP tools from OpenAPI specifications using FastMCP.

Story 8.8: OpenAPI Tool Upload and Auto-Generation (Task 4)
Provides:
- Automatic MCP tool generation from OpenAPI specs using FastMCP.from_openapi()
- httpx client configuration with authentication
- Support for API Key, OAuth 2.0, Basic Auth, Bearer Token
- Connection testing with sample endpoints
- Error handling for unsupported OpenAPI features

Architecture:
- FastMCP 2.0+ for automatic tool generation from OpenAPI specs
- httpx.AsyncClient for HTTP requests with auth configuration
- Granular timeout configuration (connect, read, write, pool)

Constraints:
- File size ≤ 500 lines
- All functions include type hints and Google-style docstrings
- Async patterns for all HTTP operations
"""

from typing import Any, Optional

import httpx
from fastmcp import FastMCP


def build_httpx_client(auth_config: dict[str, Any], base_url: str) -> httpx.AsyncClient:
    """
    Build configured httpx.AsyncClient with authentication.

    Args:
        auth_config: Authentication configuration dictionary
        base_url: Base URL for API requests

    Returns:
        Configured httpx.AsyncClient instance

    Raises:
        ValueError: If auth configuration is invalid or unsupported
    """
    auth_type = auth_config.get("type", "none").lower()

    # Base client configuration with granular timeouts
    timeout = httpx.Timeout(
        connect=5.0,  # Connection establishment timeout
        read=30.0,  # Read timeout for response
        write=5.0,  # Write timeout for request body
        pool=5.0,  # Pool connection acquisition timeout
    )

    headers: dict[str, str] = {}
    params: dict[str, str] = {}
    auth: Optional[httpx.BasicAuth] = None

    # Configure authentication based on type
    if auth_type == "none":
        pass  # No authentication required

    elif auth_type == "apikey":
        # API Key authentication
        location = auth_config.get("location", "header")
        param_name = auth_config.get("param_name", "api_key")
        value = auth_config.get("value", "")

        if location == "header":
            headers[param_name] = value
        elif location == "query":
            params[param_name] = value
        else:
            raise ValueError(f"Unsupported API key location: {location}")

    elif auth_type == "http":
        # HTTP authentication (Basic or Bearer)
        http_scheme = auth_config.get("http_scheme", "").lower()

        if http_scheme == "basic":
            # Basic authentication
            username = auth_config.get("username", "")
            password = auth_config.get("password", "")
            auth = httpx.BasicAuth(username, password)

        elif http_scheme == "bearer":
            # Bearer token authentication
            token = auth_config.get("token", "")
            headers["Authorization"] = f"Bearer {token}"

        else:
            raise ValueError(f"Unsupported HTTP auth scheme: {http_scheme}")

    elif auth_type == "oauth2":
        # OAuth 2.0 - assume token already obtained
        # In production, implement token exchange flow here
        # For now, expect pre-obtained access token
        access_token = auth_config.get("access_token", "")
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        else:
            raise ValueError("OAuth 2.0 requires access_token in auth_config")

    else:
        raise ValueError(f"Unsupported authentication type: {auth_type}")

    # Create and return configured client
    return httpx.AsyncClient(
        base_url=base_url,
        headers=headers,
        params=params,
        auth=auth,
        timeout=timeout,
        follow_redirects=True,
    )


async def generate_mcp_tools_from_openapi(
    openapi_spec: dict[str, Any],
    auth_config: dict[str, Any],
    base_url: str,
    tool_name: Optional[str] = None,
) -> FastMCP:
    """
    Generate MCP tools from OpenAPI specification using FastMCP.

    Args:
        openapi_spec: OpenAPI specification dictionary (2.0, 3.0, or 3.1)
        auth_config: Authentication configuration dictionary
        base_url: Base URL for API requests
        tool_name: Optional custom name for MCP server (defaults to spec title)

    Returns:
        FastMCP instance with auto-generated tools (one per API endpoint)

    Raises:
        ValueError: If spec is invalid or contains unsupported features
        RuntimeError: If FastMCP.from_openapi() fails
    """
    # Build HTTP client with auth
    client = build_httpx_client(auth_config, base_url)

    # Extract tool name from spec if not provided
    if not tool_name:
        tool_name = openapi_spec.get("info", {}).get("title", "Generated API Tools")

    try:
        # Generate MCP server from OpenAPI spec
        # FastMCP.from_openapi() automatically:
        # - Creates one tool per API endpoint
        # - Generates parameter schemas from path/query/body params
        # - Handles request/response validation
        # - Manages authentication via configured httpx client
        mcp = FastMCP.from_openapi(
            openapi_spec=openapi_spec,
            client=client,
            name=tool_name,
        )

        return mcp

    except Exception as e:
        # Handle FastMCP errors
        error_msg = str(e)

        # Check for common unsupported features
        if "callback" in error_msg.lower():
            raise ValueError(
                "OpenAPI callbacks are not supported by FastMCP. "
                "Please remove callback definitions from your spec."
            )
        elif "webhook" in error_msg.lower():
            raise ValueError(
                "OpenAPI webhooks are not supported by FastMCP. "
                "Please remove webhook definitions from your spec."
            )
        elif "link" in error_msg.lower():
            raise ValueError(
                "OpenAPI links are not fully supported. "
                "Generated tools may not include link relationships."
            )
        else:
            raise RuntimeError(f"Failed to generate MCP tools: {error_msg}")


async def validate_openapi_connection(
    openapi_spec: dict[str, Any],
    auth_config: dict[str, Any],
    base_url: str,
) -> dict[str, Any]:
    """
    Test API connection by calling a sample endpoint.

    Strategy:
    1. Find first GET endpoint in spec (preferring /health, /ping, /status)
    2. Make test request with configured auth
    3. Return success/failure with details

    Args:
        openapi_spec: OpenAPI specification dictionary
        auth_config: Authentication configuration dictionary
        base_url: Base URL for API requests

    Returns:
        Test result dictionary with:
        - success: bool
        - status_code: int (if successful)
        - response_preview: str (first 200 chars of response)
        - error_message: str (if failed)
        - error_type: str (Timeout, ConnectError, HTTPStatusError, etc.)
    """
    # Build HTTP client
    client = build_httpx_client(auth_config, base_url)

    # Find a suitable test endpoint
    test_endpoint: Optional[str] = None
    test_method = "GET"

    paths = openapi_spec.get("paths", {})

    # Priority order: health/ping/status endpoints, then first GET endpoint
    priority_paths = ["/health", "/ping", "/status", "/healthz", "/ready"]

    for path in priority_paths:
        if path in paths and "get" in paths[path]:
            test_endpoint = path
            break

    # If no priority endpoint, find first GET endpoint
    if not test_endpoint:
        for path, methods in paths.items():
            if "get" in methods:
                test_endpoint = path
                break

    if not test_endpoint:
        return {
            "success": False,
            "error_message": "No GET endpoints found in spec for connection testing",
            "error_type": "NoTestEndpoint",
        }

    # Make test request
    try:
        async with client:
            response = await client.get(test_endpoint)
            response.raise_for_status()

            # Get response preview (first 200 chars)
            response_text = response.text
            preview = response_text[:200]
            if len(response_text) > 200:
                preview += "..."

            return {
                "success": True,
                "status_code": response.status_code,
                "response_preview": preview,
                "test_endpoint": test_endpoint,
            }

    except httpx.TimeoutException as e:
        return {
            "success": False,
            "error_message": f"Request timeout after {client.timeout.read}s. "
            f"The API may be slow or unreachable.",
            "error_type": "Timeout",
            "test_endpoint": test_endpoint,
        }

    except httpx.ConnectError as e:
        return {
            "success": False,
            "error_message": f"Connection failed: {str(e)}. "
            f"Check that the base URL is correct and the API is reachable.",
            "error_type": "ConnectError",
            "test_endpoint": test_endpoint,
        }

    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code

        # Provide specific guidance based on status code
        if status_code == 401:
            suggestion = "Authentication failed. Please verify your credentials."
        elif status_code == 403:
            suggestion = "Access forbidden. Check API permissions and scopes."
        elif status_code == 404:
            suggestion = f"Endpoint {test_endpoint} not found. Verify the spec matches the actual API."
        elif status_code >= 500:
            suggestion = "Server error. The API may be experiencing issues."
        else:
            suggestion = f"HTTP {status_code} error."

        return {
            "success": False,
            "error_message": f"{suggestion} Status: {status_code}",
            "error_type": "HTTPStatusError",
            "status_code": status_code,
            "test_endpoint": test_endpoint,
        }

    except Exception as e:
        return {
            "success": False,
            "error_message": f"Unexpected error: {str(e)}",
            "error_type": type(e).__name__,
            "test_endpoint": test_endpoint,
        }

    # Defensive: Should never reach here, but return error dict if we do
    return {
        "success": False,
        "error_message": "Unknown error: function completed without returning result",
        "error_type": "UnknownError",
        "test_endpoint": test_endpoint if 'test_endpoint' in locals() else None,
    }


def count_generated_tools(mcp: FastMCP) -> int:
    """
    Count the number of tools generated by FastMCP.

    Args:
        mcp: FastMCP instance

    Returns:
        Number of generated tools
    """
    # FastMCP exposes tools via .tools attribute
    if hasattr(mcp, "tools"):
        return len(mcp.tools)
    return 0


async def get_tool_list(mcp: FastMCP) -> list[dict[str, Any]]:
    """
    Get list of tools with metadata from FastMCP instance.

    Args:
        mcp: FastMCP instance

    Returns:
        List of tool dictionaries [{name, description, parameters}, ...]
    """
    tools_list: list[dict[str, Any]] = []

    if hasattr(mcp, "tools"):
        for tool in mcp.tools:
            tools_list.append(
                {
                    "name": getattr(tool, "name", "Unknown"),
                    "description": getattr(tool, "description", ""),
                    "parameters": getattr(tool, "parameters", {}),
                }
            )

    return tools_list
