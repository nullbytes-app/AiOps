"""
ServiceDesk Plus Plugin Implementation.

Implements TicketingToolPlugin interface for ManageEngine ServiceDesk Plus integration.
Migrated from monolithic architecture (src/services/webhook_validator.py) to plugin pattern
following Stories 7.1 and 7.2 design.

This plugin provides:
    - HMAC-SHA256 webhook signature validation with replay attack prevention
    - Ticket retrieval via ServiceDesk Plus REST API v3
    - Ticket updates via note posting
    - Metadata extraction from ServiceDesk Plus webhook payloads
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone

from src.plugins.base import TicketingToolPlugin, TicketMetadata
from src.plugins.servicedesk_plus.api_client import (
    ServiceDeskAPIClient,
    ServiceDeskAPIError,
    ServiceDeskAuthenticationError,
)
from src.plugins.servicedesk_plus import webhook_validator
from src.services.tenant_service import TenantService
from src.database.connection import get_db_session
from src.cache.redis_client import get_redis_client
from src.utils.logger import logger
from src.utils.exceptions import TenantNotFoundException


class ServiceDeskPlusPlugin(TicketingToolPlugin):
    """
    ServiceDesk Plus ticketing tool plugin implementation.

    Implements all four TicketingToolPlugin abstract methods for ServiceDesk Plus
    integration. Stateless design - retrieves tenant-specific credentials per-request.

    Tool Type: servicedesk_plus

    Usage:
        # Registration on startup (main.py, celery_app.py)
        from src.plugins import PluginManager
        from src.plugins.servicedesk_plus import ServiceDeskPlusPlugin

        manager = PluginManager()
        plugin = ServiceDeskPlusPlugin()
        manager.register_plugin("servicedesk_plus", plugin)

        # Usage in webhook endpoint
        plugin = manager.get_plugin(tenant.tool_type)  # Returns ServiceDeskPlusPlugin
        is_valid = await plugin.validate_webhook(payload, signature)
        metadata = plugin.extract_metadata(payload)

    Security Features:
        - HMAC-SHA256 signature validation with constant-time comparison
        - Replay attack prevention via timestamp validation
        - Tenant-specific webhook secrets (prevents cross-tenant spoofing)
        - No credential storage in plugin (stateless design)
        - API keys encrypted at rest in database (Epic 3)

    See Also:
        - docs/plugin-architecture.md for comprehensive guide
        - Story 7.3 for migration from monolithic to plugin architecture
        - ServiceDesk Plus API v3: https://www.manageengine.com/products/service-desk/sdpod-v3-api/
    """

    __tool_type__ = "servicedesk_plus"

    def __init__(self) -> None:
        """
        Initialize ServiceDesk Plus plugin.

        No-op constructor following stateless plugin design from Story 7.1.
        Plugin retrieves tenant-specific configuration per-request via TenantService.
        """
        pass

    async def validate_webhook(self, payload: Dict[str, Any], signature: str) -> bool:
        """
        Validate ServiceDesk Plus webhook signature using HMAC-SHA256.

        Implements multi-tenant webhook validation with replay attack prevention.
        Uses constant-time comparison to prevent timing attacks.

        Validation Steps:
            1. Extract tenant_id from payload
            2. Retrieve tenant-specific webhook secret from database
            3. Compute HMAC-SHA256 signature of payload
            4. Constant-time comparison with provided signature
            5. Validate timestamp (5 min tolerance, 30s clock skew)

        Args:
            payload: Webhook JSON payload from ServiceDesk Plus
            signature: HMAC-SHA256 signature from X-ServiceDesk-Signature header

        Returns:
            True if signature valid and timestamp within tolerance, False otherwise

        Security:
            - Constant-time comparison prevents timing attacks
            - Tenant-specific secrets prevent cross-tenant spoofing
            - Timestamp validation prevents replay attacks
            - Validates before full payload parsing (security priority)

        Example:
            >>> payload = {
            ...     "tenant_id": "acme",
            ...     "ticket_id": "TKT-001",
            ...     "created_at": "2025-11-05T12:00:00Z",
            ...     ...
            ... }
            >>> signature = "abc123..."
            >>> is_valid = await plugin.validate_webhook(payload, signature)
            >>> if not is_valid:
            ...     raise SecurityError("Invalid webhook signature")
        """
        try:
            # Extract tenant_id from payload (lightweight parsing)
            import json

            payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            tenant_id = webhook_validator.extract_tenant_id_from_payload(payload_bytes)

            # Retrieve tenant configuration to get webhook secret
            redis_client = await get_redis_client()
            async with get_db_session() as db:
                tenant_service = TenantService(db, redis_client)
                try:
                    tenant_config = await tenant_service.get_tenant_config(tenant_id)
                except TenantNotFoundException:
                    logger.error(
                        f"Tenant not found during webhook validation: {tenant_id}",
                        extra={"tenant_id": tenant_id, "event_type": "webhook_validation"},
                    )
                    return False

                # Check if tenant is active
                if not tenant_config.is_active:
                    logger.warning(
                        f"Webhook rejected: tenant inactive: {tenant_id}",
                        extra={"tenant_id": tenant_id, "event_type": "webhook_validation"},
                    )
                    return False

                # Compute expected signature using tenant-specific webhook secret
                expected_signature = webhook_validator.compute_hmac_signature(
                    secret=tenant_config.webhook_signing_secret, payload_bytes=payload_bytes
                )

                # Constant-time comparison (prevents timing attacks)
                if not webhook_validator.secure_compare(signature, expected_signature):
                    logger.error(
                        f"Webhook signature mismatch for tenant: {tenant_id}",
                        extra={"tenant_id": tenant_id, "event_type": "signature_mismatch"},
                    )
                    return False

                # Validate timestamp for replay attack prevention
                created_at_str = payload.get("created_at")
                if created_at_str:
                    try:
                        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                        webhook_validator.validate_webhook_timestamp(created_at)
                    except ValueError as e:
                        logger.error(
                            f"Webhook timestamp validation failed: {str(e)}",
                            extra={"tenant_id": tenant_id, "created_at": created_at_str},
                        )
                        return False

                # All validations passed
                logger.info(
                    f"Webhook signature validated successfully for tenant: {tenant_id}",
                    extra={"tenant_id": tenant_id, "event_type": "webhook_validation"},
                )
                return True

        except ValueError as e:
            # Payload parsing or validation errors
            logger.error(
                f"Webhook validation error: {str(e)}",
                extra={"error": str(e), "event_type": "webhook_validation"},
            )
            return False
        except Exception as e:
            # Unexpected errors - log and reject
            logger.error(
                f"Unexpected error during webhook validation: {str(e)}",
                extra={"error": str(e), "event_type": "webhook_validation"},
                exc_info=True,
            )
            return False

    async def get_ticket(self, tenant_id: str, ticket_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve ticket details from ServiceDesk Plus API.

        Makes GET request to /api/v3/requests/{ticket_id} using tenant-specific
        credentials. Implements retry logic with exponential backoff.

        Args:
            tenant_id: Tenant identifier for config lookup
            ticket_id: ServiceDesk Plus ticket identifier (e.g., "TKT-001", "123")

        Returns:
            Dict containing ticket data with ServiceDesk Plus structure, or None if not found

        Raises:
            ServiceDeskAuthenticationError: If tenant credentials invalid (401/403)
            ServiceDeskAPIError: If API call fails after retries

        API Response Structure:
            {
                "request": {
                    "id": "123",
                    "subject": "Cannot access email",
                    "description": "<p>User cannot login...</p>",
                    "status": {"name": "Open"},
                    "priority": {"name": "High"},
                    "created_time": {"value": "1699392000000"},
                    ...
                }
            }

        Example:
            >>> ticket = await plugin.get_ticket("acme", "TKT-001")
            >>> if ticket:
            ...     description = ticket["request"]["description"]
            ...     priority = ticket["request"]["priority"]["name"]
        """
        try:
            # Retrieve tenant configuration
            redis_client = await get_redis_client()
            async with get_db_session() as db:
                tenant_service = TenantService(db, redis_client)
                try:
                    tenant_config = await tenant_service.get_tenant_config(tenant_id)
                except TenantNotFoundException:
                    logger.error(
                        f"Tenant not found: {tenant_id}",
                        extra={"tenant_id": tenant_id, "ticket_id": ticket_id},
                    )
                    return None

                # Create API client with tenant-specific credentials
                api_client = ServiceDeskAPIClient(
                    base_url=tenant_config.servicedesk_url,
                    api_key=tenant_config.servicedesk_api_key,
                    timeout=30.0,
                )

                try:
                    # Call ServiceDesk Plus API
                    ticket_data = await api_client.get_ticket(ticket_id)
                    return ticket_data
                finally:
                    # Always close client to release resources
                    await api_client.close()

        except ServiceDeskAuthenticationError as e:
            logger.error(
                f"Authentication failed for tenant: {tenant_id}",
                extra={"tenant_id": tenant_id, "ticket_id": ticket_id, "error": str(e)},
            )
            return None
        except ServiceDeskAPIError as e:
            logger.error(
                f"API error retrieving ticket: {ticket_id}",
                extra={"tenant_id": tenant_id, "ticket_id": ticket_id, "error": str(e)},
            )
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error retrieving ticket: {ticket_id}",
                extra={"tenant_id": tenant_id, "ticket_id": ticket_id, "error": str(e)},
                exc_info=True,
            )
            return None

    async def update_ticket(self, tenant_id: str, ticket_id: str, content: str) -> bool:
        """
        Update ServiceDesk Plus ticket by adding enhancement note.

        Makes POST request to /api/v3/requests/{ticket_id}/notes using tenant-specific
        credentials. Implements retry logic with exponential backoff.

        Args:
            tenant_id: Tenant identifier for config lookup
            ticket_id: ServiceDesk Plus ticket identifier
            content: Enhancement content to post (markdown/plain text)

        Returns:
            True if update successful, False otherwise

        Raises:
            ServiceDeskAuthenticationError: If tenant credentials invalid (401/403)

        API Request:
            POST /api/v3/requests/{id}/notes
            Headers: authtoken={api_key}
            Body: {"description": content, "mark_first_response": false, ...}

        Example:
            >>> content = "**Similar Tickets:**\\n- TKT-100: Resolved by server restart"
            >>> success = await plugin.update_ticket("acme", "TKT-001", content)
            >>> if not success:
            ...     logger.error("Failed to update ticket after retries")
        """
        try:
            # Retrieve tenant configuration
            redis_client = await get_redis_client()
            async with get_db_session() as db:
                tenant_service = TenantService(db, redis_client)
                try:
                    tenant_config = await tenant_service.get_tenant_config(tenant_id)
                except TenantNotFoundException:
                    logger.error(
                        f"Tenant not found: {tenant_id}",
                        extra={"tenant_id": tenant_id, "ticket_id": ticket_id},
                    )
                    return False

                # Create API client with tenant-specific credentials
                api_client = ServiceDeskAPIClient(
                    base_url=tenant_config.servicedesk_url,
                    api_key=tenant_config.servicedesk_api_key,
                    timeout=30.0,
                )

                try:
                    # Call ServiceDesk Plus API to add note
                    success = await api_client.update_ticket(ticket_id, content)
                    return success
                finally:
                    # Always close client to release resources
                    await api_client.close()

        except ServiceDeskAuthenticationError as e:
            logger.error(
                f"Authentication failed for tenant: {tenant_id}",
                extra={"tenant_id": tenant_id, "ticket_id": ticket_id, "error": str(e)},
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error updating ticket: {ticket_id}",
                extra={"tenant_id": tenant_id, "ticket_id": ticket_id, "error": str(e)},
                exc_info=True,
            )
            return False

    def extract_metadata(self, payload: Dict[str, Any]) -> TicketMetadata:
        """
        Extract standardized metadata from ServiceDesk Plus webhook payload.

        Normalizes ServiceDesk Plus payload structure into TicketMetadata dataclass
        for uniform processing by core enhancement workflow.

        ServiceDesk Plus Payload Structure:
            {
                "tenant_id": "acme",
                "data": {
                    "ticket": {
                        "id": "123",
                        "description": "User cannot access email",
                        "priority": "Urgent",
                        "created_time": "2025-11-05T12:00:00Z"
                    }
                }
            }

        Priority Normalization:
            - "Urgent" or "Critical" → "high"
            - "High" → "high"
            - "Medium" or "Normal" → "medium"
            - "Low" → "low"
            - Default: "medium"

        Args:
            payload: Raw webhook JSON payload from ServiceDesk Plus

        Returns:
            TicketMetadata with standardized fields (tenant_id, ticket_id, description,
            priority, created_at)

        Raises:
            ValueError: If required fields missing or invalid format

        Example:
            >>> payload = {
            ...     "tenant_id": "acme",
            ...     "data": {
            ...         "ticket": {
            ...             "id": "123",
            ...             "description": "Cannot access email",
            ...             "priority": "Urgent",
            ...             "created_time": "2025-11-05T12:00:00Z"
            ...         }
            ...     }
            ... }
            >>> metadata = plugin.extract_metadata(payload)
            >>> assert metadata.tenant_id == "acme"
            >>> assert metadata.ticket_id == "123"
            >>> assert metadata.priority == "high"  # Normalized from "Urgent"
        """
        try:
            # Extract tenant_id (top-level field)
            tenant_id = payload.get("tenant_id")
            if not tenant_id:
                raise ValueError("tenant_id field is required in webhook payload")

            # Extract ticket data (nested in data.ticket for ServiceDesk Plus)
            data = payload.get("data", {})
            ticket = data.get("ticket", {})

            # Extract ticket_id
            ticket_id = ticket.get("id")
            if not ticket_id:
                raise ValueError("ticket.id field is required in webhook payload")

            # Convert to string (ServiceDesk Plus may send as int or str)
            ticket_id = str(ticket_id)

            # Extract description
            description = ticket.get("description", "")

            # Extract and normalize priority
            priority_raw = ticket.get("priority", "Medium")
            priority = self._normalize_priority(priority_raw)

            # Extract and parse created_at timestamp
            created_at_str = ticket.get("created_time")
            if not created_at_str:
                raise ValueError("ticket.created_time field is required")

            # Parse ISO 8601 timestamp
            try:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError) as e:
                raise ValueError(
                    f"Invalid created_time format: {created_at_str}. Expected ISO 8601."
                )

            # Return standardized TicketMetadata
            return TicketMetadata(
                tenant_id=tenant_id,
                ticket_id=ticket_id,
                description=description,
                priority=priority,
                created_at=created_at,
            )

        except KeyError as e:
            raise ValueError(f"Missing required field in webhook payload: {str(e)}")

    def _normalize_priority(self, priority: str) -> str:
        """
        Normalize ServiceDesk Plus priority to standard values.

        Args:
            priority: ServiceDesk Plus priority string (e.g., "Urgent", "High", "Normal")

        Returns:
            Normalized priority: "high", "medium", or "low"

        Example:
            >>> plugin._normalize_priority("Urgent")
            'high'
            >>> plugin._normalize_priority("Normal")
            'medium'
        """
        priority_lower = priority.lower()

        if priority_lower in ("urgent", "critical", "high"):
            return "high"
        elif priority_lower in ("medium", "normal"):
            return "medium"
        elif priority_lower == "low":
            return "low"
        else:
            # Default to medium for unknown priorities
            logger.warning(
                f"Unknown priority value: {priority}, defaulting to 'medium'",
                extra={"priority": priority},
            )
            return "medium"

    async def test_connection(self, config: Dict[str, Any]) -> tuple[bool, str]:
        """
        Test connection to ServiceDesk Plus API with provided configuration.

        Makes lightweight GET request to /api/v3/user (current user endpoint) to verify
        authentication without modifying any data. Validates URL reachability and
        API key validity.

        Args:
            config: Configuration to test with fields:
                - servicedesk_url: ServiceDesk Plus instance URL
                - api_key: ServiceDesk Plus API key
                - technician_key: Optional technician key

        Returns:
            tuple[bool, str]: (success, message) where:
                - success: True if connection successful
                - message: Result description or error message

        Example:
            >>> config = {
            ...     "servicedesk_url": "https://sdp.example.com",
            ...     "api_key": "test-key-12345",
            ...     "technician_key": "tech-key-67890"
            ... }
            >>> success, message = await plugin.test_connection(config)
            >>> if success:
            ...     print(f"✓ {message}")
            ... else:
            ...     print(f"✗ {message}")
        """
        try:
            # Validate required configuration fields
            servicedesk_url = config.get("servicedesk_url")
            api_key = config.get("api_key")

            if not servicedesk_url:
                return (False, "Missing required field: servicedesk_url")
            if not api_key:
                return (False, "Missing required field: api_key")

            # Create temporary API client with provided credentials
            from src.plugins.servicedesk_plus.api_client import ServiceDeskAPIClient

            api_client = ServiceDeskAPIClient(
                base_url=servicedesk_url,
                api_key=api_key,
                timeout=10.0,  # Shorter timeout for connection test
            )

            try:
                # Test connection by making lightweight API call
                # GET /api/v3/user - returns current user information
                import time

                start_time = time.time()

                # Simple API call to verify authentication
                # We'll use the API client's internal httpx client
                response = await api_client._client.get(
                    "/api/v3/user",
                    headers={"authtoken": api_key},
                )

                response_time_ms = int((time.time() - start_time) * 1000)

                # Check response status
                if response.status_code == 200:
                    return (
                        True,
                        f"Connection successful (response time: {response_time_ms}ms)",
                    )
                elif response.status_code == 401:
                    return (False, "Authentication failed: Invalid API key")
                elif response.status_code == 403:
                    return (False, "Authentication failed: Access forbidden")
                elif response.status_code == 404:
                    return (
                        False,
                        f"API endpoint not found: {servicedesk_url}/api/v3/user (verify URL)",
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
                    f"Connection timeout: Unable to reach {config.get('servicedesk_url', 'API endpoint')}",
                )
            elif "connection" in error_message.lower():
                return (
                    False,
                    f"Connection error: {error_message}",
                )
            else:
                return (False, f"Unexpected error: {error_message}")
