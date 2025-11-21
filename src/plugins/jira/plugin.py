"""
Jira Service Management Plugin

This module implements the TicketingToolPlugin interface for Jira Service Management
Cloud. It enables AI-powered ticket enhancement for MSPs using Jira.

The plugin provides:
- Webhook signature validation using HMAC-SHA256 with X-Hub-Signature header
- Ticket retrieval via Jira REST API v3
- Comment posting using Atlassian Document Format (ADF)
- Metadata extraction from Jira webhook payloads

Usage:
    >>> from src.plugins.jira import JiraServiceManagementPlugin
    >>> plugin = JiraServiceManagementPlugin()
    >>> manager.register_plugin("jira", plugin)
    >>>
    >>> # Webhook validation
    >>> valid = await plugin.validate_webhook(payload, signature)
    >>>
    >>> # Extract metadata
    >>> metadata = plugin.extract_metadata(payload)
    >>>
    >>> # Get ticket
    >>> ticket = await plugin.get_ticket("tenant-abc", "PROJ-123")
    >>>
    >>> # Update ticket with enhancement
    >>> success = await plugin.update_ticket("tenant-abc", "PROJ-123", "Enhancement content")
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from src.plugins.base import TicketingToolPlugin, TicketMetadata
from src.plugins.jira.api_client import JiraAPIClient
from src.plugins.jira.webhook_validator import (
    compute_hmac_signature,
    parse_signature_header,
    secure_compare,
)
from src.services.tenant_service import TenantService
from src.database.session import get_db_session
from src.cache.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class JiraServiceManagementPlugin(TicketingToolPlugin):
    """
    Jira Service Management ticketing tool plugin implementation.

    Implements the TicketingToolPlugin interface for Jira Cloud Platform,
    enabling multi-tool support in the AI ticket enhancement platform.

    This plugin follows the architecture established in Story 7.1 (Plugin Base Interface)
    and validated in Story 7.3 (ServiceDesk Plus Plugin). It demonstrates the plugin
    pattern scales to different tool APIs and authentication mechanisms.

    Attributes:
        __tool_type__ (str): Plugin identifier "jira" for registration and routing

    Example:
        >>> plugin = JiraServiceManagementPlugin()
        >>> manager.register_plugin("jira", plugin)
        >>>
        >>> # Full workflow
        >>> payload = {"issue": {"key": "PROJ-123", ...}}
        >>> signature = request.headers["X-Hub-Signature"]
        >>>
        >>> if await plugin.validate_webhook(payload, signature):
        ...     metadata = plugin.extract_metadata(payload)
        ...     ticket = await plugin.get_ticket(metadata.tenant_id, metadata.ticket_id)
        ...     enhanced_content = await enhance_ticket(ticket)
        ...     await plugin.update_ticket(metadata.tenant_id, metadata.ticket_id, enhanced_content)
    """

    __tool_type__ = "jira"

    def __init__(self) -> None:
        """Initialize Jira Service Management plugin (stateless design)."""
        pass

    async def validate_webhook(
        self, payload: Dict[str, Any], signature: str, raw_body: Optional[bytes] = None
    ) -> bool:
        """
        Validate Jira webhook signature using HMAC-SHA256.

        Validates X-Hub-Signature header to ensure webhook authenticity and prevent
        spoofing attacks. Uses constant-time comparison to prevent timing attacks.

        Args:
            payload: Jira webhook JSON payload containing issue data
            signature: X-Hub-Signature header value (format: "sha256=abc123...")
            raw_body: Optional raw request body bytes for signature validation (preserves exact JSON format)

        Returns:
            True if signature is valid and tenant is active, False otherwise

        Example:
            >>> payload = {"issue": {"key": "PROJ-123", ...}}
            >>> signature = "sha256=abc123def456..."
            >>> valid = await plugin.validate_webhook(payload, signature)
            >>> if not valid:
            ...     raise SecurityError("Invalid webhook signature")
        """
        try:
            # Parse signature header (validates format and method)
            method, provided_signature = parse_signature_header(signature)

            # Extract tenant_id from Jira webhook payload
            # Jira custom field (e.g., customfield_10000) stores tenant identifier
            tenant_id = payload.get("issue", {}).get("fields", {}).get("customfield_10000")

            if not tenant_id:
                logger.warning("Tenant ID not found in Jira webhook payload (customfield_10000)")
                return False

            # Retrieve tenant configuration
            redis_client = await get_redis_client()
            async with get_db_session() as db:
                tenant_service = TenantService(db, redis_client)
                tenant = await tenant_service.get_tenant_config(tenant_id)

                # Check if tenant is active
                if not tenant.is_active:
                    logger.warning(f"Webhook rejected: Tenant {tenant_id} is inactive")
                    return False

                # Get webhook signing secret (decrypted by TenantService)
                webhook_secret = tenant.webhook_signing_secret

                # Use raw body if provided (preserves exact JSON format for signature validation)
                # Otherwise re-serialize the payload dict (backward compatibility)
                if raw_body:
                    payload_bytes = raw_body
                else:
                    # Convert payload back to JSON bytes for HMAC computation
                    # Use sort_keys=True for consistent ordering
                    payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")

                # Compute expected signature
                expected_signature = compute_hmac_signature(payload_bytes, webhook_secret)

                # Constant-time comparison (prevents timing attacks)
                is_valid = secure_compare(expected_signature, provided_signature)

                if is_valid:
                    logger.info(f"Webhook signature validated successfully for tenant {tenant_id}")
                else:
                    logger.warning(f"Webhook signature validation failed for tenant {tenant_id}")

                return is_valid

        except ValueError as e:
            # Invalid signature header format
            logger.error(f"Webhook validation failed: {str(e)}")
            return False
        except Exception as e:
            # Handle tenant not found or other errors
            logger.error(f"Unexpected error during webhook validation: {str(e)}")
            return False

    def extract_metadata(self, payload: Dict[str, Any]) -> TicketMetadata:
        """
        Extract standardized metadata from Jira webhook payload.

        Normalizes Jira-specific payload structure into TicketMetadata dataclass
        for uniform processing in the enhancement workflow.

        Args:
            payload: Jira webhook JSON payload

        Returns:
            TicketMetadata with standardized fields

        Raises:
            ValueError: If required fields are missing or invalid

        Example:
            >>> payload = {
            ...     "issue": {
            ...         "key": "PROJ-123",
            ...         "fields": {
            ...             "summary": "Server performance issue",
            ...             "description": "High CPU usage",
            ...             "priority": {"name": "High"},
            ...             "created": "2025-11-05T14:30:00.000+0000",
            ...             "customfield_10000": "tenant-abc"
            ...         }
            ...     }
            ... }
            >>> metadata = plugin.extract_metadata(payload)
            >>> metadata.ticket_id
            'PROJ-123'
            >>> metadata.priority
            'high'
        """
        try:
            issue = payload.get("issue", {})
            fields = issue.get("fields", {})

            # Extract required fields
            tenant_id = fields.get("customfield_10000")
            issue_key = issue.get("key")
            summary = fields.get("summary")
            description = fields.get("description")
            priority_obj = fields.get("priority", {})
            priority_name = priority_obj.get("name") if isinstance(priority_obj, dict) else None
            created_str = fields.get("created")

            # Validate required fields
            if not tenant_id:
                raise ValueError("Missing required field: customfield_10000 (tenant_id)")
            if not issue_key:
                raise ValueError("Missing required field: issue.key")
            if not summary:
                raise ValueError("Missing required field: issue.fields.summary")

            # Handle null description (use summary as fallback)
            if not description or description.strip() == "":
                description = summary

            # Normalize priority to lowercase standard values
            # Jira priorities: "Highest", "High", "Medium", "Low", "Lowest"
            priority_map = {
                "highest": "high",
                "critical": "high",
                "high": "high",
                "medium": "medium",
                "low": "low",
                "lowest": "low",
            }

            priority_normalized = "medium"  # Default
            if priority_name:
                priority_normalized = priority_map.get(priority_name.lower(), "medium")

            # Parse ISO 8601 timestamp with timezone
            if not created_str:
                raise ValueError("Missing required field: issue.fields.created")

            try:
                # Parse ISO 8601 format: "2025-11-05T14:30:00.000+0000"
                created_at = datetime.fromisoformat(created_str.replace("+0000", "+00:00"))
            except ValueError as e:
                raise ValueError(f"Invalid datetime format for created field: {created_str}") from e

            # Return standardized metadata
            return TicketMetadata(
                tenant_id=tenant_id,
                ticket_id=issue_key,
                description=description,
                priority=priority_normalized,
                created_at=created_at,
            )

        except KeyError as e:
            raise ValueError(f"Missing required field in Jira webhook payload: {str(e)}") from e
        except Exception as e:
            raise ValueError(f"Failed to extract metadata from Jira payload: {str(e)}") from e

    async def get_ticket(self, tenant_id: str, ticket_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve Jira issue details via REST API.

        GET /rest/api/3/issue/{issueKey}

        Args:
            tenant_id: Tenant identifier for config lookup
            ticket_id: Jira issue key (e.g., "PROJ-123")

        Returns:
            Issue data dict, or None if not found or on error

        Example:
            >>> ticket = await plugin.get_ticket("tenant-abc", "PROJ-123")
            >>> if ticket:
            ...     summary = ticket["fields"]["summary"]
            ...     description = ticket["fields"]["description"]
        """
        try:
            # Retrieve tenant configuration
            redis_client = await get_redis_client()
            async with get_db_session() as db:
                tenant_service = TenantService(db, redis_client)
                tenant = await tenant_service.get_tenant_config(tenant_id)

                # Get Jira-specific credentials
                jira_url = tenant.jira_url
                jira_api_token = tenant.jira_api_token  # Decrypted by TenantService

                if not jira_url or not jira_api_token:
                    logger.error(f"Jira credentials not configured for tenant {tenant_id}")
                    return None

                # Create API client
                api_client = JiraAPIClient(jira_url, jira_api_token)

                try:
                    # Get issue
                    issue = await api_client.get_issue(ticket_id)
                    return issue
                finally:
                    # Always cleanup API client
                    await api_client.close()

        except Exception as e:
            logger.error(
                f"Error retrieving Jira issue {ticket_id} for tenant {tenant_id}: {str(e)}"
            )
            return None

    async def update_ticket(self, tenant_id: str, ticket_id: str, content: str) -> bool:
        """
        Post enhancement comment to Jira issue.

        POST /rest/api/3/issue/{issueKey}/comment

        Converts plain text to Atlassian Document Format (ADF) automatically.

        Args:
            tenant_id: Tenant identifier for config lookup
            ticket_id: Jira issue key (e.g., "PROJ-123")
            content: Enhancement content as plain text

        Returns:
            True on success (201 Created), False on error

        Example:
            >>> content = "**Similar Tickets:**\\n- PROJ-100: Resolved by restarting service"
            >>> success = await plugin.update_ticket("tenant-abc", "PROJ-123", content)
            >>> if not success:
            ...     logger.error("Failed to post enhancement comment")
        """
        try:
            # Retrieve tenant configuration
            redis_client = await get_redis_client()
            async with get_db_session() as db:
                tenant_service = TenantService(db, redis_client)
                tenant = await tenant_service.get_tenant_config(tenant_id)

                # Get Jira-specific credentials
                jira_url = tenant.jira_url
                jira_api_token = tenant.jira_api_token  # Decrypted

                if not jira_url or not jira_api_token:
                    logger.error(f"Jira credentials not configured for tenant {tenant_id}")
                    return False

                # Create API client
                api_client = JiraAPIClient(jira_url, jira_api_token)

                try:
                    # Add comment (API client handles ADF conversion)
                    success = await api_client.add_comment(ticket_id, content)
                    return success
                finally:
                    # Always cleanup API client
                    await api_client.close()

        except Exception as e:
            logger.error(f"Error updating Jira issue {ticket_id} for tenant {tenant_id}: {str(e)}")
            return False

    async def test_connection(self, config: Dict[str, Any]) -> tuple[bool, str]:
        """
        Test connection to Jira API with provided configuration.

        Makes lightweight GET request to /rest/api/3/myself (current user endpoint) to
        verify authentication without modifying any data. Validates URL reachability,
        API token validity, and project access.

        Args:
            config: Configuration to test with fields:
                - jira_url: Jira instance URL (e.g., https://company.atlassian.net)
                - jira_api_token: Jira API token (Base64 encoded email:token)
                - jira_project_key: Optional project key to validate access

        Returns:
            tuple[bool, str]: (success, message) where:
                - success: True if connection successful
                - message: Result description or error message

        Example:
            >>> config = {
            ...     "jira_url": "https://company.atlassian.net",
            ...     "jira_api_token": "api-token-abc123",
            ...     "jira_project_key": "PROJ"
            ... }
            >>> success, message = await plugin.test_connection(config)
            >>> if success:
            ...     print(f"✓ {message}")
            ... else:
            ...     print(f"✗ {message}")
        """
        try:
            # Validate required configuration fields
            jira_url = config.get("jira_url")
            jira_api_token = config.get("jira_api_token")

            if not jira_url:
                return (False, "Missing required field: jira_url")
            if not jira_api_token:
                return (False, "Missing required field: jira_api_token")

            # Create temporary API client with provided credentials
            from src.plugins.jira.api_client import JiraAPIClient

            api_client = JiraAPIClient(
                base_url=jira_url,
                api_token=jira_api_token,
                timeout=10.0,  # Shorter timeout for connection test
            )

            try:
                # Test connection by making lightweight API call
                # GET /rest/api/3/myself - returns current user information
                import time

                start_time = time.time()

                # Simple API call to verify authentication
                response = await api_client._client.get("/rest/api/3/myself")

                response_time_ms = int((time.time() - start_time) * 1000)

                # Check response status
                if response.status_code == 200:
                    user_data = response.json()
                    user_name = user_data.get("displayName", "Unknown")

                    # Optionally test project access if project_key provided
                    project_key = config.get("jira_project_key")
                    if project_key:
                        project_response = await api_client._client.get(
                            f"/rest/api/3/project/{project_key}"
                        )
                        if project_response.status_code == 200:
                            return (
                                True,
                                f"Connection successful (user: {user_name}, project: {project_key}, "
                                f"response time: {response_time_ms}ms)",
                            )
                        elif project_response.status_code == 404:
                            return (
                                False,
                                f"Project '{project_key}' not found or inaccessible",
                            )
                        else:
                            return (
                                True,
                                f"Connection successful (user: {user_name}) but project access check failed "
                                f"(HTTP {project_response.status_code})",
                            )
                    else:
                        return (
                            True,
                            f"Connection successful (user: {user_name}, response time: {response_time_ms}ms)",
                        )

                elif response.status_code == 401:
                    return (False, "Authentication failed: Invalid API token")
                elif response.status_code == 403:
                    return (False, "Authentication failed: Access forbidden")
                elif response.status_code == 404:
                    return (
                        False,
                        f"API endpoint not found: {jira_url}/rest/api/3/myself (verify URL)",
                    )
                else:
                    return (
                        False,
                        f"API error: HTTP {response.status_code} - {response.text[:200]}",
                    )

            finally:
                # Always close client to release resources
                await api_client.close()

        except Exception as e:
            error_message = str(e)

            # Categorize error for helpful message
            if "timeout" in error_message.lower():
                return (
                    False,
                    f"Connection timeout: Unable to reach {config.get('jira_url', 'API endpoint')}",
                )
            elif "connection" in error_message.lower():
                return (
                    False,
                    f"Connection error: {error_message}",
                )
            else:
                return (False, f"Unexpected error: {error_message}")
