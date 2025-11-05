"""
ServiceDesk Plus API Connection Validator for Streamlit Admin UI.

This module provides synchronous HTTP client for testing ServiceDesk Plus API connectivity
before saving tenant configurations. Validates credentials by making a test API call.

Key Features:
- Synchronous httpx client compatible with Streamlit
- Test connection to ServiceDesk Plus API v3
- User-friendly error messages for different failure scenarios
- Timeout handling for network issues

Security:
- Uses authentication token in header (ServiceDesk Plus API pattern)
- SSL verification enabled (verify=True)
- No credentials logged or exposed

API Endpoint:
    GET {servicedesk_url}/api/v3/requests?limit=1
    Header: authtoken: {api_key}
"""

from typing import Literal, Optional

import httpx
from loguru import logger


def validate_servicedesk_connection(url: str, api_key: str) -> tuple[bool, str]:
    """
    Test connectivity to ServiceDesk Plus API with provided credentials.

    Makes a lightweight API call to verify:
    - ServiceDesk URL is accessible
    - API key is valid
    - Authentication succeeds

    Args:
        url: ServiceDesk Plus instance URL (e.g., "https://acme.servicedesk.com")
        api_key: ServiceDesk Plus API key (authtoken)

    Returns:
        tuple[bool, str]: (success, message)
            success: True if connection succeeds, False otherwise
            message: User-friendly status message describing result

    Raises:
        None: All exceptions are caught and converted to (False, error_message) tuples

    Example:
        >>> success, message = test_servicedesk_connection(
        ...     "https://demo.servicedesk.com",
        ...     "valid_api_key_123"
        ... )
        >>> if success:
        ...     st.success(message)
        ... else:
        ...     st.error(message)
    """
    try:
        # Ensure URL doesn't have trailing slash
        url = url.rstrip("/")

        # ServiceDesk Plus API v3 endpoint - lightweight test query
        test_endpoint = f"{url}/api/v3/requests"
        params = {"limit": 1}  # Minimal response size
        headers = {
            "authtoken": api_key,
            "Accept": "application/json",
        }

        # Use synchronous httpx client (Streamlit compatible)
        with httpx.Client(timeout=10.0, verify=True) as client:
            response = client.get(test_endpoint, params=params, headers=headers)

            # Check HTTP status code
            if response.status_code == 200:
                # Verify response is valid JSON (basic sanity check)
                try:
                    data = response.json()
                    # ServiceDesk API returns {"requests": [...]} for successful query
                    if isinstance(data, dict):
                        return (True, "✅ Connection successful - API credentials valid")
                    else:
                        return (
                            False,
                            "⚠️ Connection succeeded but response format unexpected",
                        )
                except Exception as json_error:
                    logger.warning(f"JSON parse error: {json_error}")
                    return (False, "⚠️ Response is not valid JSON")

            elif response.status_code == 401:
                return (False, "❌ Authentication failed - Invalid API key (HTTP 401)")

            elif response.status_code == 403:
                return (
                    False,
                    "❌ Access forbidden - API key lacks required permissions (HTTP 403)",
                )

            elif response.status_code == 404:
                return (
                    False,
                    f"❌ Invalid URL - Endpoint not found (HTTP 404)\n"
                    f"Verify ServiceDesk URL: {url}",
                )

            else:
                return (
                    False,
                    f"❌ Connection failed - HTTP {response.status_code}\n"
                    f"Response: {response.text[:100]}",
                )

    except httpx.TimeoutException as timeout_error:
        logger.error(f"Connection timeout: {timeout_error}")
        return (
            False,
            "❌ Connection timeout (10 seconds exceeded)\n"
            "Check network connectivity and firewall rules",
        )

    except httpx.RequestError as request_error:
        logger.error(f"Request error: {request_error}")
        return (
            False,
            f"❌ Connection failed - Network error\n"
            f"Error: {str(request_error)[:100]}",
        )

    except Exception as e:
        logger.error(f"Unexpected error during connection test: {e}")
        return (False, f"❌ Unexpected error: {str(e)[:100]}")


def validate_servicedesk_url_format(url: str) -> tuple[bool, str]:
    """
    Validate ServiceDesk URL format before connection test.

    Checks:
    - URL starts with http:// or https://
    - URL is not empty
    - URL doesn't contain obvious typos (e.g., "htp://")

    Args:
        url: ServiceDesk Plus instance URL to validate

    Returns:
        tuple[bool, str]: (is_valid, error_message)
            is_valid: True if URL format is acceptable
            error_message: Empty string if valid, error description if invalid

    Example:
        >>> is_valid, error = validate_servicedesk_url_format("https://demo.servicedesk.com")
        >>> if not is_valid:
        ...     st.error(error)
    """
    if not url:
        return (False, "ServiceDesk URL cannot be empty")

    if not url.startswith("http://") and not url.startswith("https://"):
        return (False, "ServiceDesk URL must start with http:// or https://")

    # Basic sanity checks for common typos
    if url.startswith("htp://") or url.startswith("htps://"):
        return (False, "Invalid URL protocol - check for typos (http/https)")

    return (True, "")
