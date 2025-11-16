"""
MockTicketingToolPlugin for testing enhancement workflows without real tool dependencies.

This module provides a configurable mock implementation of the TicketingToolPlugin ABC
for testing purposes. It enables testing of enhancement workflows in isolation without
requiring actual API connections to ticketing tools.

Copyright (c) 2025 AI Agents Platform
License: MIT
Story: 7.6 - Plugin Testing Framework
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.plugins.base import TicketingToolPlugin, TicketMetadata
from src.plugins.servicedesk_plus.api_client import (
    ServiceDeskAPIError,
    ServiceDeskAuthenticationError,
)
from src.utils.exceptions import ValidationError

logger = logging.getLogger(__name__)


# Sentinel value to distinguish "not provided" from "explicitly None"
_UNSET = object()


class MockTicketingToolPlugin(TicketingToolPlugin):
    """
    Configurable mock plugin for testing ticketing tool integrations.

    Implements all four abstract methods from TicketingToolPlugin with configurable
    responses and failure modes. Supports call tracking for assertion utilities.

    Key Features:
        - Configurable success/failure behaviors (API errors, auth errors, timeouts)
        - Built-in call history tracking for test assertions
        - Factory methods for common test scenarios
        - No external API calls (all responses configurable)
        - Type-safe with mypy --strict compliance

    Attributes:
        _validate_response (bool): Whether validate_webhook should return True
        _get_ticket_response (Optional[Dict[str, Any]]): Response for get_ticket
        _update_ticket_response (bool): Whether update_ticket should return True
        _raise_api_error (bool): Whether to raise ServiceDeskAPIError
        _raise_auth_error (bool): Whether to raise auth ValidationError
        _raise_timeout (bool): Whether to raise asyncio.TimeoutError
        _call_history (List[Dict[str, Any]]): Record of all method calls

    Example:
        # Success mode
        plugin = MockTicketingToolPlugin.success_mode()
        valid = await plugin.validate_webhook(payload, signature)
        assert valid is True

        # API error mode
        plugin = MockTicketingToolPlugin.api_error_mode()
        with pytest.raises(ServiceDeskAPIError):
            await plugin.get_ticket("tenant-1", "ticket-123")

        # Custom configuration
        plugin = MockTicketingToolPlugin(
            _get_ticket_response={"id": "custom-123", "priority": "high"}
        )
        ticket = await plugin.get_ticket("tenant-1", "custom-123")
    """

    def __init__(
        self,
        _validate_response: bool = True,
        _get_ticket_response: Any = _UNSET,
        _update_ticket_response: bool = True,
        _raise_api_error: bool = False,
        _raise_auth_error: bool = False,
        _raise_timeout: bool = False,
    ):
        """
        Initialize MockTicketingToolPlugin with configurable behaviors.

        Args:
            _validate_response (bool): Whether validate_webhook returns True. Default: True.
            _get_ticket_response (Optional[Dict[str, Any]]): Ticket dict to return
                from get_ticket. None means ticket not found. Default: mock ticket.
            _update_ticket_response (bool): Whether update_ticket returns True. Default: True.
            _raise_api_error (bool): Whether to raise ServiceDeskAPIError in async methods.
                Default: False.
            _raise_auth_error (bool): Whether to raise ValidationError in validate_webhook.
                Default: False.
            _raise_timeout (bool): Whether to raise asyncio.TimeoutError in async methods.
                Default: False.

        Notes:
            - If _get_ticket_response is None, get_ticket returns None (ticket not found)
            - Default _get_ticket_response provides realistic mock ticket structure
            - Call history is automatically tracked for all method calls
        """
        self._validate_response = _validate_response

        # Use sentinel to distinguish "not provided" (use default) from "explicitly None" (not found)
        if _get_ticket_response is _UNSET:
            # Default ticket for success mode
            self._get_ticket_response: Optional[Dict[str, Any]] = {
                "id": "MOCK-123",
                "subject": "Mock ticket subject",
                "description": "Mock ticket description for testing",
                "status": {"name": "Open"},
                "priority": {"name": "High"},
                "created_time": {"value": str(int(datetime.now(timezone.utc).timestamp() * 1000))},
            }
        else:
            # Explicitly set value (including None for not_found_mode)
            self._get_ticket_response = _get_ticket_response

        self._update_ticket_response = _update_ticket_response
        self._raise_api_error = _raise_api_error
        self._raise_auth_error = _raise_auth_error
        self._raise_timeout = _raise_timeout
        self._call_history: List[Dict[str, Any]] = []

    async def validate_webhook(self, payload: Dict[str, Any], signature: str) -> bool:
        """
        Validate webhook request with configurable response.

        Records method call in history, then returns configured response or raises
        configured exception.

        Args:
            payload (Dict[str, Any]): Webhook JSON payload.
            signature (str): HMAC signature from webhook request header.

        Returns:
            bool: Value of _validate_response (True by default).

        Raises:
            asyncio.TimeoutError: If _raise_timeout is True (after 10s delay).
            ValidationError: If _raise_auth_error is True (mock authentication failure).

        Notes:
            - Call is recorded in _call_history before any exception
            - Timeout mode simulates network timeout (10s delay then raises)
            - Auth error mode simulates invalid webhook secret
        """
        # Record call history
        self._call_history.append(
            {
                "method": "validate_webhook",
                "args": [],
                "kwargs": {"payload": payload, "signature": signature},
                "timestamp": datetime.now(timezone.utc),
            }
        )
        logger.debug(f"MockPlugin: validate_webhook called (payload keys: {list(payload.keys())})")

        # Handle timeout scenario
        if self._raise_timeout:
            await asyncio.sleep(10)
            raise asyncio.TimeoutError("Mock timeout during webhook validation")

        # Handle authentication error scenario
        if self._raise_auth_error:
            raise ValidationError("Mock authentication failure - invalid webhook signature")

        # Return configured response
        return self._validate_response

    async def get_ticket(self, tenant_id: str, ticket_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve ticket with configurable response.

        Records method call in history, then returns configured ticket dict or raises
        configured exception.

        Args:
            tenant_id (str): Tenant identifier for config lookup.
            ticket_id (str): Ticket identifier to retrieve.

        Returns:
            Optional[Dict[str, Any]]: Value of _get_ticket_response. None if ticket not found.

        Raises:
            asyncio.TimeoutError: If _raise_timeout is True (after 10s delay).
            ServiceDeskAPIError: If _raise_api_error is True (mock API failure).

        Notes:
            - Call is recorded in _call_history before any exception
            - Returns None for not_found_mode (simulates 404 from API)
            - Default response mimics ServiceDesk Plus ticket structure
        """
        # Record call history
        self._call_history.append(
            {
                "method": "get_ticket",
                "args": [],
                "kwargs": {"tenant_id": tenant_id, "ticket_id": ticket_id},
                "timestamp": datetime.now(timezone.utc),
            }
        )
        logger.debug(f"MockPlugin: get_ticket called (tenant={tenant_id}, ticket={ticket_id})")

        # Handle timeout scenario
        if self._raise_timeout:
            await asyncio.sleep(10)
            raise asyncio.TimeoutError("Mock timeout during get_ticket")

        # Handle API error scenario
        if self._raise_api_error:
            raise ServiceDeskAPIError("Mock API error during get_ticket (status=500, retries=3)")

        # Return configured response (None for not found)
        return self._get_ticket_response

    async def update_ticket(self, tenant_id: str, ticket_id: str, content: str) -> bool:
        """
        Update ticket with configurable response.

        Records method call in history, then returns configured response or raises
        configured exception.

        Args:
            tenant_id (str): Tenant identifier for config lookup.
            ticket_id (str): Ticket identifier to update.
            content (str): Enhancement content to post to ticket.

        Returns:
            bool: Value of _update_ticket_response (True by default).

        Raises:
            asyncio.TimeoutError: If _raise_timeout is True (after 10s delay).
            ServiceDeskAPIError: If _raise_api_error is True (mock API failure).

        Notes:
            - Call is recorded in _call_history before any exception
            - Content parameter is stored in call history for assertions
            - Timeout mode simulates network timeout during update
        """
        # Record call history
        self._call_history.append(
            {
                "method": "update_ticket",
                "args": [],
                "kwargs": {"tenant_id": tenant_id, "ticket_id": ticket_id, "content": content},
                "timestamp": datetime.now(timezone.utc),
            }
        )
        logger.debug(f"MockPlugin: update_ticket called (tenant={tenant_id}, ticket={ticket_id})")

        # Handle timeout scenario
        if self._raise_timeout:
            await asyncio.sleep(10)
            raise asyncio.TimeoutError("Mock timeout during update_ticket")

        # Handle API error scenario
        if self._raise_api_error:
            raise ServiceDeskAPIError("Mock update failed - API error (status=500, retries=3)")

        # Return configured response
        return self._update_ticket_response

    async def test_connection(self, config: Dict[str, Any]) -> tuple[bool, str]:
        """
        Test connection with configurable response.

        Records method call in history, then returns configured response or raises
        configured exception.

        Args:
            config (Dict[str, Any]): Plugin configuration to test.

        Returns:
            tuple[bool, str]: (success, message) - success status and human-readable message.

        Raises:
            asyncio.TimeoutError: If _raise_timeout is True (after 10s delay).

        Notes:
            - Call is recorded in _call_history before any exception
            - Returns (True, "Connection successful") in success mode
            - Returns (False, error_message) in error modes
        """
        # Record call history
        self._call_history.append(
            {
                "method": "test_connection",
                "args": [],
                "kwargs": {"config": config},
                "timestamp": datetime.now(timezone.utc),
            }
        )
        logger.debug("MockPlugin: test_connection called")

        # Handle timeout scenario
        if self._raise_timeout:
            await asyncio.sleep(10)
            raise asyncio.TimeoutError("Mock timeout during test_connection")

        # Handle API error scenario
        if self._raise_api_error:
            return (False, "Connection failed: API error (status=500)")

        # Handle auth error scenario
        if self._raise_auth_error:
            return (False, "Authentication failed: Invalid credentials")

        # Return success
        return (True, "Connection successful")

    def extract_metadata(self, payload: Dict[str, Any]) -> TicketMetadata:
        """
        Extract standardized metadata from webhook payload.

        Handles malformed payloads gracefully by using defaults for missing fields.

        Args:
            payload (Dict[str, Any]): Raw webhook JSON payload.

        Returns:
            TicketMetadata: Standardized metadata with normalized priority.

        Notes:
            - Synchronous method (not async) as it only transforms data
            - Handles missing fields by providing sensible defaults
            - Priority is normalized to lowercase ("high", "medium", "low")
            - created_at uses current UTC time if not in payload
            - Call is NOT recorded in history (sync method, minimal overhead)
        """
        # Extract fields with fallback defaults
        tenant_id = payload.get("tenant_id", "mock-tenant-001")
        ticket_id = payload.get("ticket_id")

        # Try nested ticket structure (ServiceDesk Plus / Jira format)
        if not ticket_id and "data" in payload and "ticket" in payload["data"]:
            ticket_id = payload["data"]["ticket"].get("id", "MOCK-UNKNOWN")
        elif not ticket_id and "issue" in payload:
            ticket_id = payload["issue"].get("key", "MOCK-UNKNOWN")
        else:
            ticket_id = ticket_id or "MOCK-DEFAULT-123"

        # Extract description
        description = payload.get("description", "Mock ticket description")
        if "data" in payload and "ticket" in payload["data"]:
            description = payload["data"]["ticket"].get("description", description)
        elif "issue" in payload and "fields" in payload["issue"]:
            description = payload["issue"]["fields"].get("description", description)

        # Extract and normalize priority
        priority = payload.get("priority", "high")
        if "data" in payload and "ticket" in payload["data"]:
            priority = payload["data"]["ticket"].get("priority", "high")
        elif "issue" in payload and "fields" in payload["issue"]:
            priority_obj = payload["issue"]["fields"].get("priority", {})
            priority = (
                priority_obj.get("name", "high") if isinstance(priority_obj, dict) else "high"
            )

        # Normalize priority to lowercase
        priority = priority.lower()
        if priority in ["urgent", "critical"]:
            priority = "high"
        elif priority not in ["high", "medium", "low"]:
            priority = "medium"  # Default for unknown priorities

        # Extract created_at timestamp
        created_at = datetime.now(timezone.utc)
        if "created_at" in payload:
            # ISO format timestamp
            try:
                created_at = datetime.fromisoformat(payload["created_at"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass  # Use default
        elif "data" in payload and "ticket" in payload["data"]:
            created_time = payload["data"]["ticket"].get("created_time")
            if created_time:
                try:
                    created_at = datetime.fromisoformat(created_time.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    pass  # Use default

        return TicketMetadata(
            tenant_id=tenant_id,
            ticket_id=ticket_id,
            description=description,
            priority=priority,
            created_at=created_at,
        )

    def get_call_history(self) -> List[Dict[str, Any]]:
        """
        Retrieve recorded method call history.

        Returns:
            List[Dict[str, Any]]: List of call records with method, args, kwargs, timestamp.

        Example:
            history = plugin.get_call_history()
            assert len(history) == 3
            assert history[0]["method"] == "validate_webhook"
            assert history[1]["kwargs"]["ticket_id"] == "123"
        """
        return self._call_history.copy()

    def reset_call_history(self) -> None:
        """
        Clear recorded call history.

        Useful for resetting state between test cases or test phases.

        Example:
            plugin.reset_call_history()
            assert len(plugin.get_call_history()) == 0
        """
        self._call_history.clear()

    # Factory methods for common test scenarios

    @classmethod
    def success_mode(cls) -> "MockTicketingToolPlugin":
        """
        Create plugin configured for all success responses.

        Returns:
            MockTicketingToolPlugin: Plugin with all methods returning success.

        Example:
            plugin = MockTicketingToolPlugin.success_mode()
            assert await plugin.validate_webhook(payload, sig) is True
            assert await plugin.update_ticket(tid, ticket, content) is True
        """
        return cls(
            _validate_response=True,
            _update_ticket_response=True,
            _raise_api_error=False,
            _raise_auth_error=False,
            _raise_timeout=False,
        )

    @classmethod
    def api_error_mode(cls) -> "MockTicketingToolPlugin":
        """
        Create plugin configured to raise API errors.

        Returns:
            MockTicketingToolPlugin: Plugin that raises ServiceDeskAPIError in
                get_ticket and update_ticket methods.

        Example:
            plugin = MockTicketingToolPlugin.api_error_mode()
            with pytest.raises(ServiceDeskAPIError):
                await plugin.get_ticket("tenant-1", "ticket-123")
        """
        return cls(_raise_api_error=True)

    @classmethod
    def auth_error_mode(cls) -> "MockTicketingToolPlugin":
        """
        Create plugin configured to raise authentication errors.

        Returns:
            MockTicketingToolPlugin: Plugin that raises ValidationError in
                validate_webhook method.

        Example:
            plugin = MockTicketingToolPlugin.auth_error_mode()
            with pytest.raises(ValidationError):
                await plugin.validate_webhook(payload, "invalid-sig")
        """
        return cls(_raise_auth_error=True)

    @classmethod
    def timeout_mode(cls) -> "MockTicketingToolPlugin":
        """
        Create plugin configured to raise timeouts.

        Returns:
            MockTicketingToolPlugin: Plugin that raises asyncio.TimeoutError in
                all async methods after 10s delay.

        Example:
            plugin = MockTicketingToolPlugin.timeout_mode()
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(
                    plugin.get_ticket("tenant-1", "ticket-123"),
                    timeout=1.0
                )
        """
        return cls(_raise_timeout=True)

    @classmethod
    def not_found_mode(cls) -> "MockTicketingToolPlugin":
        """
        Create plugin configured to return None for get_ticket.

        Returns:
            MockTicketingToolPlugin: Plugin that returns None from get_ticket
                (simulates ticket not found / 404 response).

        Example:
            plugin = MockTicketingToolPlugin.not_found_mode()
            ticket = await plugin.get_ticket("tenant-1", "non-existent")
            assert ticket is None
        """
        return cls(_get_ticket_response=None)
