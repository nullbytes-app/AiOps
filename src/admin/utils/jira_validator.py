"""
Jira API Connection Validator for Streamlit Admin UI.

This module provides synchronous HTTP client for testing Jira API connectivity
before saving tenant configurations. Validates credentials by making a test API call.

Key Features:
- Synchronous httpx client compatible with Streamlit
- Test connection to Jira REST API v3
- User-friendly error messages for different failure scenarios
- Timeout handling for network issues

Security:
- Uses Bearer token or Basic authentication
- SSL verification enabled (verify=True)
- No credentials logged or exposed

API Endpoint:
    GET {jira_url}/rest/api/3/myself
    Header: Authorization: Bearer {api_token}
"""

from typing import Literal, Optional

import httpx
from loguru import logger


def validate_jira_connection(url: str, api_token: str) -> tuple[bool, str]:
    """
    Test connectivity to Jira API with provided credentials.

    Makes a lightweight API call to verify:
    - Jira URL is accessible
    - API token is valid
    - Authentication succeeds

    Args:
        url: Jira instance URL (e.g., "https://company.atlassian.net")
        api_token: Jira API token or Basic auth credentials

    Returns:
        tuple[bool, str]: (success, message)
            success: True if connection succeeds, False otherwise
            message: User-friendly status message describing result

    Raises:
        None: All exceptions are caught and converted to (False, error_message) tuples

    Example:
        >>> success, message = validate_jira_connection(
        ...     "https://company.atlassian.net",
        ...     "valid_api_token_123"
        ... )
        >>> if success:
        ...     st.success(message)
        ... else:
        ...     st.error(message)
    """
    try:
        # Ensure URL doesn't have trailing slash
        url = url.rstrip("/")

        # Jira REST API v3 endpoint - lightweight test query
        test_endpoint = f"{url}/rest/api/3/myself"
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json",
        }

        # Use synchronous httpx client (Streamlit compatible)
        with httpx.Client(timeout=10.0, verify=True) as client:
            response = client.get(test_endpoint, headers=headers)

            # Check HTTP status code
            if response.status_code == 200:
                # Verify response is valid JSON (basic sanity check)
                try:
                    data = response.json()
                    # Jira API returns user object with displayName, emailAddress, etc.
                    user_name = data.get("displayName", "Unknown")
                    email = data.get("emailAddress", "")

                    if user_name:
                        return (
                            True,
                            f"✅ Connection successful - Authenticated as {user_name}" +
                            (f" ({email})" if email else "")
                        )
                    else:
                        return (
                            True,
                            "✅ Connection successful - API credentials valid"
                        )
                except Exception as json_error:
                    logger.warning(f"JSON parse error: {json_error}")
                    return (False, "⚠️ Response is not valid JSON")

            elif response.status_code == 401:
                return (False, "❌ Authentication failed - Invalid API token (HTTP 401)")

            elif response.status_code == 403:
                return (
                    False,
                    "❌ Access forbidden - API token lacks required permissions (HTTP 403)",
                )

            elif response.status_code == 404:
                return (
                    False,
                    f"❌ Invalid URL - Endpoint not found (HTTP 404)\n"
                    f"Verify Jira URL: {url}\n"
                    f"Expected format: https://yourcompany.atlassian.net",
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


def validate_jira_url_format(url: str) -> tuple[bool, str]:
    """
    Validate Jira URL format before connection test.

    Checks:
    - URL starts with http:// or https://
    - URL is not empty
    - URL doesn't contain obvious typos (e.g., "htp://")
    - URL looks like an Atlassian URL

    Args:
        url: Jira instance URL to validate

    Returns:
        tuple[bool, str]: (is_valid, error_message)
            is_valid: True if URL format is acceptable
            error_message: Empty string if valid, error description if invalid

    Example:
        >>> is_valid, error = validate_jira_url_format("https://company.atlassian.net")
        >>> if not is_valid:
        ...     st.error(error)
    """
    if not url:
        return (False, "Jira URL cannot be empty")

    if not url.startswith("http://") and not url.startswith("https://"):
        return (False, "Jira URL must start with http:// or https://")

    # Basic sanity checks for common typos
    if url.startswith("htp://") or url.startswith("htps://"):
        return (False, "Invalid URL protocol - check for typos (http/https)")

    # Helpful warning if URL doesn't look like Atlassian
    if "atlassian.net" not in url.lower() and "jira" not in url.lower():
        return (
            False,
            "⚠️ URL doesn't appear to be a Jira instance\n"
            "Expected format: https://yourcompany.atlassian.net"
        )

    return (True, "")
