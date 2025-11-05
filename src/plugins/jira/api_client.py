"""
Jira REST API v3 Client

This module provides an async HTTP client for interacting with Jira Cloud Platform
REST API v3. Implements 2025 best practices for httpx AsyncClient:
- Granular timeout configuration
- Connection pooling
- Exponential backoff retry
- Proper resource cleanup

API Documentation: https://developer.atlassian.com/cloud/jira/platform/rest/v3/
"""

import asyncio
import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class JiraAPIError(Exception):
    """Jira API server error or rate limiting."""

    pass


class AuthenticationError(Exception):
    """Invalid API token."""

    pass


class NetworkError(Exception):
    """Connection failures or timeouts."""

    pass


def text_to_adf(text: str) -> Dict[str, Any]:
    """
    Convert plain text to Atlassian Document Format (ADF).

    ADF is the format required for Jira Cloud comment bodies. This function
    performs basic conversion, splitting text into paragraphs by newlines.

    Args:
        text: Plain text content to convert

    Returns:
        ADF structure as dictionary

    Example:
        >>> text = "Hello\\nWorld"
        >>> adf = text_to_adf(text)
        >>> adf["type"]
        'doc'
        >>> len(adf["content"])
        2
    """
    paragraphs = text.split("\n")

    content = []
    for para in paragraphs:
        if para.strip():  # Skip empty paragraphs
            content.append(
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": para}],
                }
            )

    # Handle case where text is all whitespace
    if not content:
        content.append(
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": ""}],
            }
        )

    return {"type": "doc", "version": 1, "content": content}


class JiraAPIClient:
    """
    Async HTTP client for Jira Cloud Platform REST API v3.

    Implements 2025 httpx best practices:
    - Granular timeouts (connect=5s, read=30s, write=5s, pool=5s)
    - Connection pooling (max_connections=100, max_keepalive_connections=20)
    - Exponential backoff retry (2s, 4s, 8s delays)
    - Proper resource cleanup with aclose()

    Example:
        >>> client = JiraAPIClient(
        ...     "https://company.atlassian.net",
        ...     "api_token_here"
        ... )
        >>> issue = await client.get_issue("PROJ-123")
        >>> success = await client.add_comment("PROJ-123", "Enhancement added")
        >>> await client.close()
    """

    def __init__(self, base_url: str, api_token: str):
        """
        Initialize Jira API client.

        Args:
            base_url: Jira Cloud base URL (e.g., "https://company.atlassian.net")
            api_token: API token for Bearer authentication
        """
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token

        # Context7 best practice: Granular timeout configuration
        timeout = httpx.Timeout(
            connect=5.0,  # Time to establish connection
            read=30.0,  # Time to read response data
            write=5.0,  # Time to send request data
            pool=5.0,  # Time to acquire connection from pool
        )

        # Connection pooling configuration
        limits = httpx.Limits(max_connections=100, max_keepalive_connections=20)

        # Initialize AsyncClient with best practices
        self.client = httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

    async def get_issue(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve issue details from Jira.

        GET /rest/api/3/issue/{issueKey}

        Args:
            issue_key: Issue key (e.g., "PROJ-123")

        Returns:
            Issue data dict, or None if not found or on error

        Raises:
            No exceptions raised - errors are logged and return None

        Example:
            >>> issue = await client.get_issue("PROJ-123")
            >>> if issue:
            ...     print(issue["fields"]["summary"])
        """
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"
        headers = {"Authorization": f"Bearer {self.api_token}"}

        # Exponential backoff retry: 3 attempts with delays 2s, 4s, 8s
        for attempt in range(3):
            try:
                logger.debug(f"GET issue {issue_key} (attempt {attempt + 1}/3)")
                response = await self.client.get(url, headers=headers)

                if response.status_code == 200:
                    logger.info(f"Successfully retrieved issue {issue_key}")
                    return response.json()  # type: ignore[no-any-return]
                elif response.status_code == 404:
                    logger.warning(f"Issue not found: {issue_key}")
                    return None
                elif response.status_code == 401:
                    logger.error(f"Authentication failed for issue {issue_key}: Invalid API token")
                    return None
                elif response.status_code == 403:
                    logger.error(
                        f"Permission denied for issue {issue_key}: Insufficient permissions"
                    )
                    return None
                elif response.status_code in (500, 502, 503):
                    # Server error - retry with backoff
                    delay = 2**attempt  # 1, 2, 4 seconds (but we start at 2)
                    if attempt < 2:  # Don't sleep on last attempt
                        logger.warning(
                            f"Server error {response.status_code} for issue {issue_key}, "
                            f"retrying in {delay * 2}s..."
                        )
                        await asyncio.sleep(delay * 2)
                        continue
                    else:
                        logger.error(
                            f"Server error {response.status_code} for issue {issue_key} "
                            f"after 3 attempts"
                        )
                        return None
                else:
                    logger.error(f"Unexpected status {response.status_code} for issue {issue_key}")
                    return None

            except httpx.ConnectTimeout:
                logger.error(f"Connection timeout for issue {issue_key} (attempt {attempt + 1}/3)")
                if attempt < 2:
                    await asyncio.sleep(2 ** (attempt + 1))
                    continue
                return None
            except httpx.ReadTimeout:
                logger.error(f"Read timeout for issue {issue_key} (attempt {attempt + 1}/3)")
                if attempt < 2:
                    await asyncio.sleep(2 ** (attempt + 1))
                    continue
                return None
            except httpx.ConnectError as e:
                logger.error(
                    f"Connection error for issue {issue_key}: {str(e)} (attempt {attempt + 1}/3)"
                )
                if attempt < 2:
                    await asyncio.sleep(2 ** (attempt + 1))
                    continue
                return None
            except Exception as e:
                logger.error(f"Unexpected error retrieving issue {issue_key}: {str(e)}")
                return None

        return None

    async def add_comment(self, issue_key: str, comment_text: str) -> bool:
        """
        Add comment to Jira issue.

        POST /rest/api/3/issue/{issueKey}/comment

        Converts plain text to Atlassian Document Format (ADF) automatically.

        Args:
            issue_key: Issue key (e.g., "PROJ-123")
            comment_text: Comment content as plain text

        Returns:
            True on success (201 Created), False on error

        Example:
            >>> success = await client.add_comment(
            ...     "PROJ-123",
            ...     "Ticket enhanced with AI analysis"
            ... )
            >>> if success:
            ...     print("Comment posted successfully")
        """
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/comment"
        headers = {"Authorization": f"Bearer {self.api_token}"}

        # Convert plain text to ADF format
        adf_body = text_to_adf(comment_text)
        payload = {"body": adf_body}

        # Exponential backoff retry: 3 attempts
        for attempt in range(3):
            try:
                logger.debug(f"POST comment to {issue_key} (attempt {attempt + 1}/3)")
                response = await self.client.post(url, headers=headers, json=payload)

                if response.status_code == 201:
                    logger.info(f"Successfully added comment to issue {issue_key}")
                    return True
                elif response.status_code == 404:
                    logger.error(f"Issue not found: {issue_key}")
                    return False
                elif response.status_code == 401:
                    logger.error(f"Authentication failed for issue {issue_key}: Invalid API token")
                    return False
                elif response.status_code == 400:
                    logger.error(f"Invalid comment body for issue {issue_key}: {response.text}")
                    return False
                elif response.status_code in (500, 502, 503):
                    # Server error - retry with backoff
                    delay = 2**attempt
                    if attempt < 2:
                        logger.warning(
                            f"Server error {response.status_code} adding comment to {issue_key}, "
                            f"retrying in {delay * 2}s..."
                        )
                        await asyncio.sleep(delay * 2)
                        continue
                    else:
                        logger.error(
                            f"Server error {response.status_code} adding comment to {issue_key} "
                            f"after 3 attempts"
                        )
                        return False
                else:
                    logger.error(
                        f"Unexpected status {response.status_code} adding comment to {issue_key}"
                    )
                    return False

            except httpx.ConnectTimeout:
                logger.error(
                    f"Connection timeout adding comment to {issue_key} (attempt {attempt + 1}/3)"
                )
                if attempt < 2:
                    await asyncio.sleep(2 ** (attempt + 1))
                    continue
                return False
            except httpx.ReadTimeout:
                logger.error(
                    f"Read timeout adding comment to {issue_key} (attempt {attempt + 1}/3)"
                )
                if attempt < 2:
                    await asyncio.sleep(2 ** (attempt + 1))
                    continue
                return False
            except httpx.ConnectError as e:
                logger.error(
                    f"Connection error adding comment to {issue_key}: {str(e)} "
                    f"(attempt {attempt + 1}/3)"
                )
                if attempt < 2:
                    await asyncio.sleep(2 ** (attempt + 1))
                    continue
                return False
            except Exception as e:
                logger.error(f"Unexpected error adding comment to {issue_key}: {str(e)}")
                return False

        return False

    async def close(self) -> None:
        """
        Close HTTP client and release connections.

        Should be called in finally blocks or when using async context manager.

        Example:
            >>> try:
            ...     issue = await client.get_issue("PROJ-123")
            ... finally:
            ...     await client.close()
        """
        await self.client.aclose()
        logger.debug("Jira API client closed")
