"""
Plugin Base Interface for Ticketing Tool Integrations.

This module defines the abstract base class for all ticketing tool plugins,
establishing a standardized contract for webhook validation, ticket retrieval,
ticket updates, and metadata extraction. New ticketing tools can be integrated
by implementing this interface without modifying core enhancement logic.

Copyright (c) 2025 AI Agents Platform
License: MIT
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class TicketMetadata:
    """
    Standardized ticket metadata structure for enhancement workflow.

    This dataclass normalizes ticket information from different ticketing tools
    into a consistent format used throughout the enhancement pipeline.

    Attributes:
        tenant_id (str): Multi-tenant identifier for data isolation and config lookup.
        ticket_id (str): Tool-specific ticket identifier (e.g., "INC-123" for ServiceDesk Plus,
            "JIRA-456" for Jira Service Management).
        description (str): Ticket description text used for context gathering and enhancement.
        priority (str): Priority level (e.g., "high", "medium", "low") for processing decisions.
        created_at (datetime): Ticket creation timestamp in UTC for audit and tracking.

    Example:
        metadata = TicketMetadata(
            tenant_id="tenant-001",
            ticket_id="INC-123",
            description="User cannot access email",
            priority="high",
            created_at=datetime.now(timezone.utc)
        )
    """

    tenant_id: str
    ticket_id: str
    description: str
    priority: str
    created_at: datetime


class TicketingToolPlugin(ABC):
    """
    Abstract base class defining the plugin interface for ticketing tool integrations.

    This ABC establishes a standardized contract that all ticketing tool plugins must
    implement, enabling the platform to support multiple ITSM tools (ServiceDesk Plus,
    Jira Service Management, Zendesk, etc.) through a unified interface.

    Plugins decouple tool-specific logic from core enhancement workflow, allowing new
    integrations to be added without modifying existing code. The interface defines
    four abstract methods covering webhook validation, ticket retrieval, ticket updates,
    and metadata extraction.

    Usage:
        To create a new ticketing tool plugin:

        1. Subclass TicketingToolPlugin
        2. Implement all four abstract methods with tool-specific logic
        3. Register plugin with PluginManager (Story 7.2)
        4. Configure tenant to use plugin via tool_type (Story 7.5)

        Example:
            class ServiceDeskPlusPlugin(TicketingToolPlugin):
                async def validate_webhook(self, payload, signature):
                    # ServiceDesk Plus HMAC-SHA256 validation
                    ...

                async def get_ticket(self, tenant_id, ticket_id):
                    # Call ServiceDesk Plus API /api/v3/tickets/{id}
                    ...

                async def update_ticket(self, tenant_id, ticket_id, content):
                    # Post work note to ServiceDesk Plus ticket
                    ...

                def extract_metadata(self, payload):
                    # Extract from ServiceDesk Plus webhook structure
                    ...

    See Also:
        - docs/plugin-architecture.md for comprehensive implementation guide
        - Story 7.3 for ServiceDesk Plus plugin implementation reference
        - Story 7.4 for Jira Service Management plugin implementation

    Notes:
        - Three methods are async (validate_webhook, get_ticket, update_ticket) to support
          concurrent plugin operations and external API calls.
        - extract_metadata is synchronous as it only transforms data without I/O.
        - Plugins retrieve tenant-specific configuration (API keys, URLs, secrets) via
          tenant_id lookup in tenant_configs table.
        - Type hints enforce compile-time correctness via mypy static analysis.
    """

    @abstractmethod
    async def validate_webhook(self, payload: Dict[str, Any], signature: str) -> bool:
        """
        Validate webhook request authenticity using tool-specific signature algorithm.

        Each ticketing tool uses different webhook signature mechanisms for security.
        Implementations must verify the signature matches the payload using the tool's
        algorithm (e.g., HMAC-SHA256 for ServiceDesk Plus, HMAC-SHA256 with different
        header for Jira).

        Args:
            payload (Dict[str, Any]): Webhook JSON payload received from ticketing tool.
                Structure varies by tool but typically contains ticket data and event type.
            signature (str): HMAC signature from webhook request header (e.g.,
                X-ServiceDesk-Signature for ServiceDesk Plus, X-Hub-Signature for Jira).
                Used to verify payload authenticity.

        Returns:
            bool: True if signature is valid and request is authentic, False otherwise.
                False indicates potential security issue or misconfigured webhook secret.

        Raises:
            ValidationError: If payload is malformed (e.g., missing required fields,
                invalid JSON structure, or cannot be processed).

        Notes:
            - Implementations must use constant-time comparison (secrets.compare_digest)
              to prevent timing attacks.
            - Signature validation uses webhook_secret from tenant_configs (encrypted).
            - Expected latency: <100ms for HMAC computation.
            - Tool-specific signature algorithms:
                * ServiceDesk Plus: HMAC-SHA256(payload, webhook_secret)
                * Jira: HMAC-SHA256(payload, webhook_secret) with X-Hub-Signature header
                * Zendesk: JWT-based signature verification

        Example:
            valid = await plugin.validate_webhook(
                payload={"ticket": {"id": "123", ...}},
                signature="sha256=abc123..."
            )
            if not valid:
                raise SecurityError("Invalid webhook signature")
        """
        ...

    @abstractmethod
    async def get_ticket(self, tenant_id: str, ticket_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve ticket details from ticketing tool API.

        Fetches complete ticket information from the tool's REST API for context gathering
        in the enhancement workflow. Implementations handle tool-specific API endpoints,
        authentication methods, and response structures.

        Args:
            tenant_id (str): Tenant identifier for config lookup. Used to retrieve
                tenant-specific API credentials (api_key, servicedesk_url) from
                tenant_configs table.
            ticket_id (str): Tool-specific ticket identifier to retrieve (e.g., "INC-123"
                for ServiceDesk Plus, "JIRA-456" for Jira). Format depends on tool.

        Returns:
            Optional[Dict[str, Any]]: Dictionary containing ticket data with tool-specific
                structure, or None if ticket not found. Typical fields include:
                - id: Ticket identifier
                - description: Ticket description text
                - priority: Priority level
                - status: Current ticket status
                - created_time: Creation timestamp
                - custom_fields: Tool-specific additional data

                Returns None if ticket does not exist (404 from API).

        Raises:
            APIError: If API call fails after retry attempts (network errors, 500 errors,
                timeout). Includes original error and retry count in exception.
            AuthenticationError: If API credentials are invalid (401/403 from API).
                Indicates tenant_configs may have incorrect or expired api_key.

        Notes:
            - Implementations should use exponential backoff for transient failures.
            - Expected latency: <2s for API call (per NFR001 requirements).
            - API endpoints by tool:
                * ServiceDesk Plus: GET /api/v3/tickets/{id}
                * Jira: GET /rest/api/3/issue/{key}
                * Zendesk: GET /api/v2/tickets/{id}.json
            - Response should be returned as-is (not normalized) for tool-specific processing.

        Example:
            ticket = await plugin.get_ticket(
                tenant_id="tenant-001",
                ticket_id="INC-123"
            )
            if ticket:
                description = ticket.get("description", "")
                priority = ticket.get("priority", "medium")
        """
        ...

    @abstractmethod
    async def update_ticket(self, tenant_id: str, ticket_id: str, content: str) -> bool:
        """
        Update ticket with enhancement content.

        Posts AI-generated enhancement content back to the ticket in the ticketing tool.
        Implementations handle tool-specific update mechanisms (comments, work notes,
        internal notes) and retry logic for reliability.

        Args:
            tenant_id (str): Tenant identifier for config lookup. Used to retrieve
                tenant-specific API credentials and preferences (e.g., whether to post
                as public comment or internal note).
            ticket_id (str): Tool-specific ticket identifier to update (e.g., "INC-123").
            content (str): Enhancement content to post to ticket. Formatted as markdown
                or HTML depending on tool requirements. Typically includes:
                - Similar ticket references with resolution links
                - Knowledge base article suggestions
                - IP address cross-reference data
                - Suggested resolution steps

        Returns:
            bool: True if update successful, False otherwise. False indicates partial
                failure after all retry attempts (e.g., persistent network issues, rate
                limiting, ticket locked).

        Raises:
            APIError: If update fails after retries due to API errors (network failures,
                500 errors, timeout). Includes retry count and last error in exception.
            AuthenticationError: If API credentials invalid (401/403 from API). Indicates
                tenant_configs may have incorrect or expired api_key.

        Notes:
            - Implementations MUST implement retry logic: 3 attempts with exponential backoff
              (1s, 2s, 4s delays) for transient failures (429, 500, 503, network errors).
            - Expected latency: <5s including retries (per NFR001 requirements).
            - Update mechanisms by tool:
                * ServiceDesk Plus: POST /api/v3/tickets/{id}/notes (work note)
                * Jira: POST /rest/api/3/issue/{key}/comment (comment)
                * Zendesk: PUT /api/v2/tickets/{id}.json (internal note)
            - Some tools require markdown-to-HTML conversion (handle in implementation).
            - Enhancement content should be posted as internal/private note (not public
              comment) per security best practices.

        Example:
            success = await plugin.update_ticket(
                tenant_id="tenant-001",
                ticket_id="INC-123",
                content="**Similar Tickets:**\\n- INC-100: Resolution link\\n..."
            )
            if not success:
                logger.error(f"Failed to update ticket {ticket_id} after retries")
        """
        ...

    @abstractmethod
    def extract_metadata(self, payload: Dict[str, Any]) -> TicketMetadata:
        """
        Extract standardized metadata from webhook payload.

        Normalizes tool-specific webhook payload structures into the standardized
        TicketMetadata dataclass. This abstraction allows core enhancement workflow
        to process tickets from different tools uniformly without tool-specific logic.

        Args:
            payload (Dict[str, Any]): Raw webhook JSON payload from ticketing tool.
                Structure varies significantly by tool:
                - ServiceDesk Plus: {"data": {"ticket": {"id": "123", ...}}}
                - Jira: {"issue": {"key": "JIRA-456", ...}}
                - Zendesk: {"ticket": {"id": 789, ...}}

        Returns:
            TicketMetadata: Dataclass with standardized fields:
                - tenant_id: Extracted from payload or request context
                - ticket_id: Tool-specific ticket identifier (normalized to string)
                - description: Ticket description text
                - priority: Priority level (normalized to lowercase: "high", "medium", "low")
                - created_at: Ticket creation timestamp (converted to UTC datetime)

        Raises:
            ValidationError: If required fields are missing from payload or cannot be
                parsed (e.g., invalid timestamp format, missing ticket ID). Includes
                details about which field is invalid in exception message.

        Notes:
            - This method is SYNCHRONOUS (not async) as it only transforms data without I/O.
            - Expected latency: <10ms for pure Python data transformation.
            - Implementations must handle tool-specific field mappings:
                * ServiceDesk Plus: data.ticket.id, data.ticket.description, data.ticket.priority
                * Jira: issue.key, issue.fields.description, issue.fields.priority.name
                * Zendesk: ticket.id, ticket.description, ticket.priority
            - Priority normalization: Convert tool-specific values to standard "high",
              "medium", "low" (e.g., ServiceDesk Plus "Urgent" → "high").
            - Timestamp conversion: Parse tool-specific timestamp formats to UTC datetime.
            - tenant_id extraction: May come from payload, request header, or URL path
              (implementation-specific).

        Example:
            metadata = plugin.extract_metadata(payload={
                "data": {
                    "ticket": {
                        "id": "123",
                        "description": "Cannot access email",
                        "priority": "Urgent",
                        "created_time": "2025-11-04T10:00:00Z"
                    }
                },
                "tenant_id": "tenant-001"
            })
            # metadata.tenant_id == "tenant-001"
            # metadata.ticket_id == "123"
            # metadata.priority == "high" (normalized)
        """
        ...

    @abstractmethod
    async def test_connection(self, config: Dict[str, Any]) -> tuple[bool, str]:
        """
        Test connection to ticketing tool API with provided configuration.

        Validates that the plugin can successfully authenticate and communicate with
        the ticketing tool's API using the provided configuration (URL, credentials).
        Used by admin UI to verify configuration before saving to database.

        Args:
            config (Dict[str, Any]): Plugin configuration to test. Contains tool-specific
                fields such as:
                - ServiceDesk Plus: servicedesk_url, api_key, technician_key
                - Jira: jira_url, jira_api_token, jira_project_key
                - Zendesk: zendesk_url, zendesk_api_token, zendesk_email

        Returns:
            tuple[bool, str]: (success, message) where:
                - success (bool): True if connection successful, False otherwise
                - message (str): Human-readable result message:
                    * Success: "Connection successful" or detailed success info
                    * Failure: Specific error message (e.g., "Authentication failed: Invalid API key",
                      "Connection timeout: Unable to reach API endpoint")

        Raises:
            ValidationError: If config is malformed (missing required fields, invalid types).
                Should not raise for connection failures - return (False, error_message) instead.

        Notes:
            - This method MUST complete within 30 seconds (enforced by API endpoint timeout).
            - Recommended test: Make lightweight API call (e.g., GET /api/v3/user for
              ServiceDesk Plus, GET /rest/api/3/myself for Jira) to verify authentication.
            - Do NOT create/modify any tickets during testing - use read-only API calls only.
            - Expected latency: <5s for successful connection, up to 30s for timeout scenarios.
            - Connection failures should return (False, message) not raise exceptions:
                * Authentication errors: (False, "Authentication failed: Invalid credentials")
                * Network errors: (False, "Connection timeout: Unable to reach {url}")
                * API errors: (False, "API error: {status_code} - {error_message}")
            - Success message may include additional details like API version, response time:
                * (True, "Connection successful (response time: 234ms, API version: v3)")

        Example:
            # ServiceDesk Plus plugin
            success, message = await plugin.test_connection({
                "servicedesk_url": "https://sdp.example.com",
                "api_key": "test-key-12345",
                "technician_key": "tech-key-67890"
            })
            if success:
                logger.info(f"Connection test passed: {message}")
            else:
                logger.error(f"Connection test failed: {message}")

            # Jira plugin
            success, message = await plugin.test_connection({
                "jira_url": "https://company.atlassian.net",
                "jira_api_token": "api-token-abc123",
                "jira_project_key": "PROJ"
            })
        """
        ...
