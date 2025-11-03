"""
ServiceDesk Plus API integration for ticket updates.

This module provides async integration with ManageEngine ServiceDesk Plus API v3
to post enhancements and resolutions to tickets. It handles API authentication,
retry logic with exponential backoff, and comprehensive error handling.

Key Functions:
- update_ticket_with_enhancement(): Main API function to post work notes
- convert_markdown_to_html(): Helper to format markdown for ServiceDesk Plus display
"""

import asyncio
import html as html_module
import logging
from typing import Optional

import httpx

from src.utils.logger import AuditLogger

logger = logging.getLogger(__name__)
audit_logger = AuditLogger()

# =============================================================================
# RETRY CONFIGURATION CONSTANTS
# =============================================================================

MAX_RETRIES = 3
RETRY_DELAYS = [2, 4, 8]  # Exponential backoff in seconds
RETRY_STATUS_CODES = [500, 502, 503, 504]  # Server errors eligible for retry
NO_RETRY_STATUS_CODES = [400, 401, 404]  # Client errors, don't retry
API_TIMEOUT = 30.0  # Total timeout per call (per NFR001 budget)


# =============================================================================
# MARKDOWN TO HTML CONVERSION
# =============================================================================


def convert_markdown_to_html(markdown: str) -> str:
    """
    Convert markdown to simple HTML for ServiceDesk Plus display.

    This function implements a simple MVP markdown-to-HTML converter that handles
    the output format from Story 2.9 LLM synthesis (headers, bullets, newlines).
    It does NOT attempt to handle complex markdown (tables, code blocks, links).

    Args:
        markdown (str): Markdown text from LLM synthesis output.

    Returns:
        str: HTML-formatted text suitable for ServiceDesk Plus display.

    Examples:
        >>> md = "## Similar Tickets\\n- Item 1\\n- Item 2"
        >>> html = convert_markdown_to_html(md)
        >>> assert "<h2>Similar Tickets</h2>" in html
        >>> assert "<ul>" in html
    """
    if not markdown:
        return ""

    # First escape HTML special characters to prevent injection
    html_content = html_module.escape(markdown)

    # Convert headers: ## Header → <h2>Header</h2>
    html_content = _convert_headers(html_content)

    # Convert bullet lists: - Item → <ul><li>Item</li></ul>
    html_content = _convert_bullet_lists(html_content)

    # Convert newlines to <br> tags
    html_content = html_content.replace("\n", "<br>\n")

    return html_content


def _convert_headers(text: str) -> str:
    """
    Convert markdown headers to HTML h2/h3 tags.

    Args:
        text (str): Text with escaped HTML containing markdown headers.

    Returns:
        str: Text with markdown headers converted to HTML tags.
    """
    import re

    # ## Header → <h2>Header</h2>
    text = re.sub(r"^## (.+?)$", r"<h2>\1</h2>", text, flags=re.MULTILINE)
    # ### Header → <h3>Header</h3>
    text = re.sub(r"^### (.+?)$", r"<h3>\1</h3>", text, flags=re.MULTILINE)

    return text


def _convert_bullet_lists(text: str) -> str:
    """
    Convert markdown bullet lists to HTML ul/li structure.

    Args:
        text (str): Text with escaped HTML containing markdown bullets.

    Returns:
        str: Text with markdown bullets converted to HTML lists.

    Reason:
    Simple regex-based list conversion (not nested support) is sufficient for
    LLM output which typically has flat bullet lists for each section.
    """
    import re

    # Find all lines that start with "- " and wrap them in <ul><li>...</li></ul>
    lines = text.split("\n")
    in_list = False
    result = []

    for line in lines:
        if line.strip().startswith("- "):
            # Remove the "- " prefix and wrap in <li>
            item = line.strip()[2:].strip()
            if not in_list:
                result.append("<ul>")
                in_list = True
            result.append(f"  <li>{item}</li>")
        else:
            if in_list:
                result.append("</ul>")
                in_list = False
            result.append(line)

    # Close any open list at end
    if in_list:
        result.append("</ul>")

    return "\n".join(result)


# =============================================================================
# RETRY DECISION LOGIC
# =============================================================================


def should_retry(status_code: Optional[int], exception: Optional[Exception]) -> bool:
    """
    Determine if an error is retryable based on status code and exception type.

    Rationale:
    - 5xx errors are transient server errors → retry
    - Timeouts and connection errors are transient → retry
    - 401/404/400 are permanent client errors → do NOT retry
    - Other exceptions are checked for timeout/connection patterns

    Args:
        status_code (Optional[int]): HTTP status code if available.
        exception (Optional[Exception]): Exception that occurred.

    Returns:
        bool: True if operation should be retried, False otherwise.
    """
    # Check status code first
    if status_code is not None:
        if status_code in NO_RETRY_STATUS_CODES:
            return False
        if status_code in RETRY_STATUS_CODES:
            return True

    # Check exception type
    if exception is None:
        return False

    exception_type_name = type(exception).__name__

    # Retry on timeout exceptions
    if any(
        timeout_type in exception_type_name
        for timeout_type in ["Timeout", "TimeoutError"]
    ):
        return True

    # Retry on connection errors
    if any(
        conn_type in exception_type_name
        for conn_type in ["ConnectError", "NetworkError"]
    ):
        return True

    return False


# =============================================================================
# MAIN API FUNCTION
# =============================================================================


async def update_ticket_with_enhancement(
    base_url: str, api_key: str, ticket_id: str, enhancement: str, correlation_id: str = None, tenant_id: str = None
) -> bool:
    """
    Post an enhancement to a ticket in ServiceDesk Plus via API.

    This function handles the complete API integration with ServiceDesk Plus,
    including URL construction, markdown-to-HTML conversion, retry logic, error
    handling, and comprehensive logging.

    **Integration Pattern:**
    This function returns a boolean success/failure indicator. The calling code
    (typically Story 2.11 Celery task) is responsible for updating the
    enhancement_history table based on this return value:
    - On True: Update status='completed', completed_at=NOW(), processing_time_ms
    - On False: Update status='failed', error_message

    Args:
        base_url (str): ServiceDesk Plus base URL (e.g., https://api.servicedesk.company.com)
        api_key (str): ServiceDesk Plus API key for authentication
        ticket_id (str): ServiceDesk Plus ticket/request ID
        enhancement (str): Markdown-formatted enhancement text from LLM synthesis
        correlation_id (str, optional): Correlation ID for distributed tracing (Story 2.11)

    Returns:
        bool: True if work note posted successfully, False on any failure.
              Never raises exceptions; always returns boolean for graceful degradation.

    Examples:
        >>> success = await update_ticket_with_enhancement(
        ...     "https://api.servicedesk.company.com",
        ...     "api-key-123",
        ...     "req-456",
        ...     "## Similar Tickets\n- Previously reported",
        ...     correlation_id="abc-123-def"
        ... )
        >>> if success:
        ...     # Caller updates enhancement_history with status='completed'
        ... else:
        ...     # Caller updates enhancement_history with status='failed'

    Raises:
        None: This function never raises exceptions. All errors are logged
              and converted to False return value for graceful degradation.
    """
    # Input validation
    if not base_url or not isinstance(base_url, str):
        logger.error(
            "Invalid base_url: must be non-empty string",
            extra={"ticket_id": ticket_id, "correlation_id": correlation_id, "type_": type(base_url)},
        )
        return False

    if not api_key or not isinstance(api_key, str):
        logger.error(
            "Invalid api_key: must be non-empty string",
            extra={"ticket_id": ticket_id, "correlation_id": correlation_id},
        )
        return False

    if not ticket_id or not isinstance(ticket_id, str):
        logger.error(
            "Invalid ticket_id: must be non-empty string",
            extra={"correlation_id": correlation_id},
        )
        return False

    if not enhancement or not isinstance(enhancement, str):
        logger.error(
            "Invalid enhancement: must be non-empty string",
            extra={"correlation_id": correlation_id},
        )
        return False

    # Construct API URL
    url = _construct_api_url(base_url, ticket_id)
    if not url:
        return False

    # Convert markdown to HTML
    html_enhancement = convert_markdown_to_html(enhancement)

    # Build request payload
    payload = _build_payload(html_enhancement)

    # Build headers
    headers = _build_headers(api_key)

    # Retry loop with exponential backoff
    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
                response = await client.post(url, json=payload, headers=headers)

                # Check for success
                if response.status_code in (200, 201):
                    logger.info(
                        "Ticket updated successfully",
                        extra={
                            "ticket_id": ticket_id,
                            "correlation_id": correlation_id,
                            "status_code": response.status_code,
                        },
                    )
                    # Log API call success for audit trail (AC3, AC5)
                    audit_logger.audit_api_call(
                        tenant_id=tenant_id,
                        ticket_id=ticket_id,
                        correlation_id=correlation_id,
                        endpoint="servicedesk/v3/requests",
                        method="POST",
                        status_code=response.status_code,
                    )
                    return True

                # Handle non-success responses
                _handle_http_error(response, ticket_id, attempt, correlation_id)
                response.raise_for_status()

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            logger.error(
                f"HTTP {status_code} error updating ticket",
                extra={
                    "ticket_id": ticket_id,
                    "correlation_id": correlation_id,
                    "status_code": status_code,
                },
                exc_info=True,
            )

            if not should_retry(status_code, e):
                return False

        except (httpx.TimeoutException, asyncio.TimeoutError) as e:
            logger.warning(
                f"Timeout updating ticket, attempt {attempt + 1}/{MAX_RETRIES}",
                extra={
                    "ticket_id": ticket_id,
                    "correlation_id": correlation_id,
                    "timeout_seconds": API_TIMEOUT,
                },
                exc_info=False,
            )

            if not should_retry(None, e):
                return False

        except (httpx.ConnectError, httpx.NetworkError) as e:
            logger.error(
                f"Network error updating ticket: {str(e)}",
                extra={"ticket_id": ticket_id, "correlation_id": correlation_id},
                exc_info=True,
            )

            if not should_retry(None, e):
                return False

        except Exception as e:
            logger.error(
                f"Unexpected error updating ticket: {str(e)}",
                extra={"ticket_id": ticket_id, "correlation_id": correlation_id},
                exc_info=True,
            )
            return False

        # If we get here, we're going to retry (unless this is the last attempt)
        if attempt < MAX_RETRIES - 1:
            delay = RETRY_DELAYS[attempt]
            logger.info(
                f"Retrying in {delay} seconds (attempt {attempt + 1}/{MAX_RETRIES})",
                extra={"ticket_id": ticket_id, "correlation_id": correlation_id},
            )
            await asyncio.sleep(delay)

    # Max retries exhausted
    logger.error(
        "Failed to update ticket after maximum retries",
        extra={
            "ticket_id": ticket_id,
            "correlation_id": correlation_id,
            "max_retries": MAX_RETRIES,
        },
    )
    return False


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _construct_api_url(base_url: str, ticket_id: str) -> Optional[str]:
    """
    Construct the full ServiceDesk Plus API URL for adding work notes.

    Args:
        base_url (str): ServiceDesk Plus base URL
        ticket_id (str): Ticket/request ID

    Returns:
        Optional[str]: Full API URL or None if construction fails
    """
    # Strip trailing slashes from base_url for consistency
    base_url = base_url.rstrip("/")

    # Validate URL format (basic check for http/https)
    if not base_url.startswith(("http://", "https://")):
        logger.error(
            "Invalid base_url: must start with http:// or https://",
            extra={"base_url": base_url},
        )
        return None

    # Construct full URL
    url = f"{base_url}/api/v3/requests/{ticket_id}/notes"

    logger.debug(
        "Constructed API URL",
        extra={"url": url.split("/api/v3")[0] + "/api/v3/..."},  # Hide full URL
    )

    return url


def _build_headers(api_key: str) -> dict:
    """
    Build HTTP headers for ServiceDesk Plus API request.

    Args:
        api_key (str): ServiceDesk Plus API key

    Returns:
        dict: Headers dict with authtoken and Content-Type
    """
    return {
        "authtoken": api_key,
        "Content-Type": "application/json",
        "User-Agent": "AI-Agents-Enhancement-Platform",
    }


def _build_payload(html_content: str) -> dict:
    """
    Build the JSON payload for ServiceDesk Plus work note creation.

    Args:
        html_content (str): HTML-formatted enhancement content

    Returns:
        dict: Payload ready for JSON serialization
    """
    return {
        "note": {
            "description": html_content,
            "show_to_requester": True,
            "mark_first_response": False,
            "add_to_linked_requests": False,
        }
    }


def _handle_http_error(response: httpx.Response, ticket_id: str, attempt: int, correlation_id: str = None) -> None:
    """
    Log HTTP error responses with appropriate detail levels.

    Args:
        response (httpx.Response): HTTP response with error status
        ticket_id (str): Ticket ID for logging context
        attempt (int): Current retry attempt number
        correlation_id (str, optional): Correlation ID for distributed tracing

    Reason:
    Centralized error logging ensures consistent log levels and message formats
    across all HTTP error scenarios.
    """
    status_code = response.status_code

    if status_code == 401:
        logger.critical(
            "Authentication failed for ticket (invalid API key)",
            extra={
                "ticket_id": ticket_id,
                "correlation_id": correlation_id,
                "status_code": status_code,
            },
        )
    elif status_code == 404:
        logger.warning(
            "Ticket not found in ServiceDesk Plus",
            extra={
                "ticket_id": ticket_id,
                "correlation_id": correlation_id,
                "status_code": status_code,
            },
        )
    elif 500 <= status_code < 600:
        logger.error(
            f"ServiceDesk Plus server error (HTTP {status_code})",
            extra={
                "ticket_id": ticket_id,
                "correlation_id": correlation_id,
                "status_code": status_code,
            },
        )
    else:
        logger.warning(
            f"Unexpected HTTP {status_code} response",
            extra={
                "ticket_id": ticket_id,
                "correlation_id": correlation_id,
                "status_code": status_code,
            },
        )
