"""
ServiceDesk Plus API Client for ticket operations.

Provides async HTTP client for ServiceDesk Plus REST API v3 with retry logic,
error handling, and timeout configuration following 2025 best practices.

API Endpoints:
    - GET /api/v3/requests/{id} - Retrieve ticket details
    - POST /api/v3/requests/{id}/notes - Add note to ticket
"""

import asyncio
from typing import Dict, Any, Optional
import httpx

from src.utils.logger import logger


class ServiceDeskAPIError(Exception):
    """Base exception for ServiceDesk Plus API errors."""

    pass


class ServiceDeskAuthenticationError(ServiceDeskAPIError):
    """API authentication failed (401/403)."""

    pass


class ServiceDeskAPIClient:
    """
    Async HTTP client for ServiceDesk Plus REST API v3.

    Implements retry logic with exponential backoff for transient failures,
    proper timeout configuration, and comprehensive error handling.

    Usage:
        client = ServiceDeskAPIClient(
            base_url="https://acme.servicedesk.com",
            api_key="abc123..."
        )
        ticket = await client.get_ticket("TKT-001")
        success = await client.update_ticket("TKT-001", "Enhancement content")

    Security:
        - API key transmitted via authtoken header (ServiceDesk Plus standard)
        - HTTPS only (no HTTP fallback)
        - API key NOT logged in error messages
    """

    def __init__(self, base_url: str, api_key: str, timeout: float = 30.0, max_retries: int = 3):
        """
        Initialize ServiceDesk Plus API client.

        Args:
            base_url: ServiceDesk Plus instance URL (e.g., "https://acme.servicedesk.com")
            api_key: API authentication token
            timeout: Request timeout in seconds (default: 30.0)
            max_retries: Maximum retry attempts for transient failures (default: 3)

        Example:
            >>> client = ServiceDeskAPIClient(
            ...     base_url="https://acme.servicedesk.com",
            ...     api_key="abc123xyz",
            ...     timeout=30.0
            ... )
        """
        self.base_url = base_url.rstrip("/")  # Remove trailing slash
        self.api_key = api_key
        self.max_retries = max_retries

        # Configure timeout with granular control (2025 httpx best practice)
        self.timeout = httpx.Timeout(
            connect=5.0,  # Time to establish connection
            read=timeout,  # Time to read response data
            write=5.0,  # Time to send request data
            pool=5.0,  # Time to acquire connection from pool
        )

        # Create async client with connection pooling and retry transport
        transport = httpx.AsyncHTTPTransport(retries=1)  # Transport-level retry
        self.client = httpx.AsyncClient(
            transport=transport,
            timeout=self.timeout,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )

    async def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve ticket details from ServiceDesk Plus API.

        Makes GET request to /api/v3/requests/{ticket_id} with retry logic
        for transient failures.

        Args:
            ticket_id: ServiceDesk Plus ticket identifier (e.g., "TKT-001", "123")

        Returns:
            Dict containing ticket data, or None if ticket not found (404)

        Raises:
            ServiceDeskAuthenticationError: If API key is invalid (401/403)
            ServiceDeskAPIError: If API call fails after all retry attempts

        Example:
            >>> ticket = await client.get_ticket("TKT-001")
            >>> if ticket:
            ...     print(f"Description: {ticket.get('description')}")
            ... else:
            ...     print("Ticket not found")
        """
        endpoint = f"{self.base_url}/api/v3/requests/{ticket_id}"
        headers = {"authtoken": self.api_key}

        # Retry with exponential backoff: 2s, 4s, 8s
        for attempt in range(self.max_retries):
            try:
                response = await self.client.get(endpoint, headers=headers)

                # Handle specific status codes
                if response.status_code == 404:
                    logger.warning(
                        f"Ticket not found: {ticket_id}",
                        extra={"ticket_id": ticket_id, "endpoint": endpoint},
                    )
                    return None

                if response.status_code in (401, 403):
                    logger.error(
                        f"Authentication failed for ServiceDesk Plus API",
                        extra={"status_code": response.status_code, "endpoint": endpoint},
                    )
                    raise ServiceDeskAuthenticationError(
                        f"API authentication failed with status {response.status_code}"
                    )

                # Raise for other 4xx/5xx errors
                response.raise_for_status()

                # Success - parse and return ticket data
                ticket_data: Dict[str, Any] = response.json()
                logger.info(
                    f"Retrieved ticket: {ticket_id}",
                    extra={"ticket_id": ticket_id, "status_code": response.status_code},
                )
                return ticket_data

            except httpx.HTTPStatusError as e:
                # 5xx server errors - retry
                if e.response.status_code >= 500 and attempt < self.max_retries - 1:
                    delay = 2 ** (attempt + 1)  # Exponential backoff: 2s, 4s, 8s
                    logger.warning(
                        f"Server error (5xx), retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})",
                        extra={
                            "ticket_id": ticket_id,
                            "status_code": e.response.status_code,
                            "attempt": attempt + 1,
                        },
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(
                        f"Failed to retrieve ticket after {attempt + 1} attempts",
                        extra={
                            "ticket_id": ticket_id,
                            "status_code": e.response.status_code,
                            "error": str(e),
                        },
                    )
                    raise ServiceDeskAPIError(f"Failed to retrieve ticket {ticket_id}: {e}")

            except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as e:
                # Network/timeout errors - retry
                if attempt < self.max_retries - 1:
                    delay = 2 ** (attempt + 1)
                    logger.warning(
                        f"Network error, retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})",
                        extra={
                            "ticket_id": ticket_id,
                            "error_type": type(e).__name__,
                            "attempt": attempt + 1,
                        },
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(
                        f"Network error after {attempt + 1} attempts",
                        extra={"ticket_id": ticket_id, "error": str(e)},
                    )
                    raise ServiceDeskAPIError(f"Network error retrieving ticket {ticket_id}: {e}")

        # Should not reach here, but handle gracefully
        raise ServiceDeskAPIError(f"Failed to retrieve ticket {ticket_id} after retries")

    async def update_ticket(self, ticket_id: str, content: str) -> bool:
        """
        Update ticket by adding a note with enhancement content.

        Makes POST request to /api/v3/requests/{ticket_id}/notes with retry logic.

        Args:
            ticket_id: ServiceDesk Plus ticket identifier
            content: Enhancement content to post as note (markdown/plain text)

        Returns:
            True if update successful, False otherwise

        Raises:
            ServiceDeskAuthenticationError: If API key is invalid (401/403)
            ServiceDeskAPIError: If API call fails after all retry attempts

        Example:
            >>> content = "**Similar Tickets:**\\n- TKT-100: Server restart fixed issue"
            >>> success = await client.update_ticket("TKT-001", content)
            >>> if success:
            ...     print("Ticket updated successfully")
        """
        endpoint = f"{self.base_url}/api/v3/requests/{ticket_id}/notes"
        headers = {"authtoken": self.api_key, "Content-Type": "application/json"}
        payload = {
            "description": content,
            "mark_first_response": False,
            "add_to_linked_requests": False,
        }

        # Retry with exponential backoff: 2s, 4s, 8s
        for attempt in range(self.max_retries):
            try:
                response = await self.client.post(endpoint, headers=headers, json=payload)

                # Handle authentication errors
                if response.status_code in (401, 403):
                    logger.error(
                        f"Authentication failed for ServiceDesk Plus API",
                        extra={"status_code": response.status_code, "endpoint": endpoint},
                    )
                    raise ServiceDeskAuthenticationError(
                        f"API authentication failed with status {response.status_code}"
                    )

                # Raise for other 4xx/5xx errors
                response.raise_for_status()

                # Success (200/201)
                logger.info(
                    f"Updated ticket with note: {ticket_id}",
                    extra={
                        "ticket_id": ticket_id,
                        "status_code": response.status_code,
                        "content_length": len(content),
                    },
                )
                return True

            except httpx.HTTPStatusError as e:
                # 5xx server errors - retry
                if e.response.status_code >= 500 and attempt < self.max_retries - 1:
                    delay = 2 ** (attempt + 1)
                    logger.warning(
                        f"Server error (5xx), retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})",
                        extra={
                            "ticket_id": ticket_id,
                            "status_code": e.response.status_code,
                            "attempt": attempt + 1,
                        },
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(
                        f"Failed to update ticket after {attempt + 1} attempts",
                        extra={
                            "ticket_id": ticket_id,
                            "status_code": e.response.status_code,
                            "error": str(e),
                        },
                    )
                    return False

            except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as e:
                # Network/timeout errors - retry
                if attempt < self.max_retries - 1:
                    delay = 2 ** (attempt + 1)
                    logger.warning(
                        f"Network error, retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})",
                        extra={
                            "ticket_id": ticket_id,
                            "error_type": type(e).__name__,
                            "attempt": attempt + 1,
                        },
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(
                        f"Network error after {attempt + 1} attempts",
                        extra={"ticket_id": ticket_id, "error": str(e)},
                    )
                    return False

        # Should not reach here, but handle gracefully
        return False

    async def close(self) -> None:
        """
        Close the HTTP client and release resources.

        Should be called when done with the client to properly clean up
        connection pools and prevent resource leaks.

        Example:
            >>> client = ServiceDeskAPIClient(...)
            >>> try:
            ...     ticket = await client.get_ticket("TKT-001")
            ... finally:
            ...     await client.close()
        """
        await self.client.aclose()
