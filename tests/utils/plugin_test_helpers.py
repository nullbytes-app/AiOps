"""
Plugin Testing Utilities for asserting plugin behavior and building test data.

This module provides helper functions for testing ticketing tool plugins:
- Assertion utilities for verifying plugin method calls
- Response capture utilities for async plugin methods
- Failure simulation utilities for configuring mock plugins
- TicketMetadata validation utilities
- Payload builder utilities for realistic test data

Copyright (c) 2025 AI Agents Platform
License: MIT
Story: 7.6 - Plugin Testing Framework
"""

import asyncio
import inspect
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from src.plugins.base import TicketMetadata


# ============================================================================
# Assertion Utilities
# ============================================================================


def assert_plugin_called(plugin: Any, method_name: str, times: int = 1) -> None:
    """
    Assert plugin method was called exactly N times.

    Args:
        plugin: MockTicketingToolPlugin instance with call tracking.
        method_name (str): Method name to check (e.g., "validate_webhook").
        times (int): Expected number of calls. Default: 1.

    Raises:
        AssertionError: If method was not called exactly `times` times.

    Example:
        plugin = MockTicketingToolPlugin.success_mode()
        await plugin.validate_webhook(payload, signature)
        assert_plugin_called(plugin, "validate_webhook", times=1)
    """
    call_count = get_plugin_call_count(plugin, method_name)
    assert call_count == times, (
        f"Expected {method_name} to be called {times} time(s), "
        f"but was called {call_count} time(s)"
    )


def assert_plugin_called_with(plugin: Any, method_name: str, **expected_kwargs: Any) -> None:
    """
    Assert plugin method was called with specific keyword arguments.

    Checks the LAST call to the method for matching kwargs.

    Args:
        plugin: MockTicketingToolPlugin instance with call tracking.
        method_name (str): Method name to check.
        **expected_kwargs: Keyword arguments expected in the last call.

    Raises:
        AssertionError: If method was never called or last call kwargs don't match.

    Example:
        await plugin.get_ticket("tenant-1", "ticket-123")
        assert_plugin_called_with(
            plugin,
            "get_ticket",
            tenant_id="tenant-1",
            ticket_id="ticket-123"
        )
    """
    last_call = get_plugin_last_call(plugin, method_name)
    assert last_call is not None, f"{method_name} was never called"

    actual_kwargs = last_call.get("kwargs", {})
    for key, expected_value in expected_kwargs.items():
        assert key in actual_kwargs, (
            f"Expected kwarg '{key}' not found in {method_name} call. "
            f"Available kwargs: {list(actual_kwargs.keys())}"
        )
        actual_value = actual_kwargs[key]
        assert actual_value == expected_value, (
            f"Expected {method_name}(${key}={expected_value!r}), " f"but got {key}={actual_value!r}"
        )


def get_plugin_call_count(plugin: Any, method_name: str) -> int:
    """
    Get number of times plugin method was called.

    Args:
        plugin: MockTicketingToolPlugin instance with call tracking.
        method_name (str): Method name to count.

    Returns:
        int: Number of times method was called.

    Example:
        count = get_plugin_call_count(plugin, "validate_webhook")
        assert count >= 1
    """
    history = plugin.get_call_history()
    return sum(1 for call in history if call["method"] == method_name)


def get_plugin_last_call(plugin: Any, method_name: str) -> Optional[Dict[str, Any]]:
    """
    Get details of the last call to a plugin method.

    Args:
        plugin: MockTicketingToolPlugin instance with call tracking.
        method_name (str): Method name to retrieve.

    Returns:
        Optional[Dict[str, Any]]: Call details dict with "method", "args", "kwargs",
            "timestamp" keys, or None if method was never called.

    Example:
        last_call = get_plugin_last_call(plugin, "get_ticket")
        if last_call:
            ticket_id = last_call["kwargs"]["ticket_id"]
    """
    history = plugin.get_call_history()
    matching_calls = [call for call in history if call["method"] == method_name]
    return matching_calls[-1] if matching_calls else None


# ============================================================================
# Response Capture Utilities
# ============================================================================


async def capture_plugin_response(
    plugin: Any, method_name: str, *args: Any, timeout: float = 5.0, **kwargs: Any
) -> Tuple[Optional[Any], Optional[Exception], float]:
    """
    Call plugin method and capture result, exception, and duration.

    Wrapper that executes plugin method and returns detailed execution info
    for test assertions. Handles both async and sync methods.

    Args:
        plugin: MockTicketingToolPlugin instance.
        method_name (str): Method name to call.
        *args: Positional arguments for method.
        timeout (float): Timeout in seconds for async methods. Default: 5.0.
        **kwargs: Keyword arguments for method.

    Returns:
        Tuple[Optional[Any], Optional[Exception], float]: Tuple containing:
            - result: Method return value (None if exception raised)
            - exception: Exception raised (None if successful)
            - duration_ms: Execution duration in milliseconds

    Example:
        result, exception, duration = await capture_plugin_response(
            plugin, "get_ticket", "tenant-1", "ticket-123"
        )
        assert exception is None
        assert duration < 100  # < 100ms
        assert result is not None
    """
    method = getattr(plugin, method_name)
    start_time = datetime.now(timezone.utc)
    result: Optional[Any] = None
    exception: Optional[Exception] = None

    try:
        if inspect.iscoroutinefunction(method):
            # Async method - apply timeout
            result = await asyncio.wait_for(method(*args, **kwargs), timeout=timeout)
        else:
            # Sync method
            result = method(*args, **kwargs)
    except Exception as e:
        exception = e

    end_time = datetime.now(timezone.utc)
    duration_ms = (end_time - start_time).total_seconds() * 1000

    return result, exception, duration_ms


# ============================================================================
# Failure Simulation Utilities
# ============================================================================


def configure_plugin_failure(plugin: Any, failure_type: str) -> Any:
    """
    Configure mock plugin for specific failure mode.

    Mutates plugin instance to raise appropriate exceptions.

    Args:
        plugin: MockTicketingToolPlugin instance to configure.
        failure_type (str): One of: "api_error", "auth_error", "timeout", "not_found".

    Returns:
        Any: The same plugin instance (for method chaining).

    Raises:
        ValueError: If failure_type is invalid.

    Example:
        plugin = MockTicketingToolPlugin.success_mode()
        configure_plugin_failure(plugin, "api_error")
        with pytest.raises(ServiceDeskAPIError):
            await plugin.get_ticket("tenant-1", "ticket-123")
    """
    valid_types = {"api_error", "auth_error", "timeout", "not_found"}
    if failure_type not in valid_types:
        raise ValueError(
            f"Invalid failure_type: {failure_type!r}. " f"Must be one of {valid_types}"
        )

    # Reset all failure flags first
    plugin._raise_api_error = False
    plugin._raise_auth_error = False
    plugin._raise_timeout = False

    # Set appropriate failure flag
    if failure_type == "api_error":
        plugin._raise_api_error = True
    elif failure_type == "auth_error":
        plugin._raise_auth_error = True
    elif failure_type == "timeout":
        plugin._raise_timeout = True
    elif failure_type == "not_found":
        plugin._get_ticket_response = None

    return plugin  # Enable method chaining


# ============================================================================
# TicketMetadata Validation Utilities
# ============================================================================


def assert_ticket_metadata_valid(metadata: TicketMetadata) -> None:
    """
    Validate TicketMetadata structure and field values.

    Checks:
    - All required fields present and non-empty
    - Priority is normalized (lowercase: "high", "medium", "low")
    - created_at is datetime object with timezone

    Args:
        metadata (TicketMetadata): Metadata instance to validate.

    Raises:
        AssertionError: If any validation check fails with clear error message.

    Example:
        metadata = plugin.extract_metadata(payload)
        assert_ticket_metadata_valid(metadata)
    """
    # Check required fields present
    assert metadata.tenant_id, "tenant_id is empty"
    assert metadata.ticket_id, "ticket_id is empty"
    assert metadata.description, "description is empty"
    assert metadata.priority, "priority is empty"
    assert metadata.created_at, "created_at is None"

    # Validate priority is normalized
    valid_priorities = {"high", "medium", "low"}
    assert metadata.priority in valid_priorities, (
        f"Priority must be one of {valid_priorities}, " f"but got {metadata.priority!r}"
    )

    # Validate created_at is datetime with timezone
    assert isinstance(metadata.created_at, datetime), (
        f"created_at must be datetime object, " f"but got {type(metadata.created_at).__name__}"
    )
    assert (
        metadata.created_at.tzinfo is not None
    ), "created_at must have timezone info (use datetime with UTC)"


# ============================================================================
# Payload Builder Utilities
# ============================================================================


def build_servicedesk_payload(**overrides: Any) -> Dict[str, Any]:
    """
    Build realistic ServiceDesk Plus webhook payload with overrides.

    Provides default structure matching ServiceDesk Plus webhook format.
    Override specific fields via kwargs.

    Args:
        **overrides: Field overrides. Supported:
            - tenant_id: Tenant identifier
            - ticket_id: Ticket ID
            - description: Ticket description
            - priority: Priority level
            - created_time: ISO timestamp string

    Returns:
        Dict[str, Any]: ServiceDesk Plus webhook payload.

    Example:
        payload = build_servicedesk_payload(
            tenant_id="acme-corp",
            ticket_id="12345",
            priority="Urgent"
        )
        metadata = plugin.extract_metadata(payload)
    """
    current_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    default_payload: Dict[str, Any] = {
        "tenant_id": "test-tenant-001",
        "event": "ticket_created",
        "data": {
            "ticket": {
                "id": "SDPLUS-123",
                "description": "Test ticket description from ServiceDesk Plus",
                "priority": "High",
                "created_time": current_time,
            }
        },
        "created_at": current_time,
    }

    # Apply overrides to nested structure
    if "tenant_id" in overrides:
        default_payload["tenant_id"] = overrides["tenant_id"]
    if "ticket_id" in overrides:
        default_payload["data"]["ticket"]["id"] = overrides["ticket_id"]
    if "description" in overrides:
        default_payload["data"]["ticket"]["description"] = overrides["description"]
    if "priority" in overrides:
        default_payload["data"]["ticket"]["priority"] = overrides["priority"]
    if "created_time" in overrides:
        default_payload["data"]["ticket"]["created_time"] = overrides["created_time"]
        default_payload["created_at"] = overrides["created_time"]

    return default_payload


def build_jira_payload(**overrides: Any) -> Dict[str, Any]:
    """
    Build realistic Jira Service Management webhook payload with overrides.

    Provides default structure matching Jira webhook format.
    Override specific fields via kwargs.

    Args:
        **overrides: Field overrides. Supported:
            - tenant_id: Tenant identifier
            - ticket_id (key): Issue key
            - description: Issue description
            - priority: Priority level
            - created: ISO timestamp string

    Returns:
        Dict[str, Any]: Jira webhook payload.

    Example:
        payload = build_jira_payload(
            tenant_id="acme-corp",
            ticket_id="JIRA-456",
            priority="High"
        )
        metadata = plugin.extract_metadata(payload)
    """
    current_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "+0000")

    default_payload: Dict[str, Any] = {
        "tenant_id": "test-tenant-001",
        "webhookEvent": "jira:issue_created",
        "issue": {
            "id": "10123",
            "key": "JIRA-456",
            "fields": {
                "summary": "Test issue from Jira",
                "description": "Test ticket description from Jira Service Management",
                "status": {"name": "Open", "id": "1"},
                "priority": {"name": "High", "id": "2"},
                "created": current_time,
                "issuetype": {"name": "Incident", "id": "10001"},
            },
        },
    }

    # Apply overrides to nested structure
    if "tenant_id" in overrides:
        default_payload["tenant_id"] = overrides["tenant_id"]
    if "ticket_id" in overrides:
        default_payload["issue"]["key"] = overrides["ticket_id"]
    if "description" in overrides:
        default_payload["issue"]["fields"]["description"] = overrides["description"]
    if "priority" in overrides:
        # Jira priority is object with name and id
        priority_map = {"High": "2", "Medium": "3", "Low": "4"}
        priority_name = str(overrides["priority"])
        default_payload["issue"]["fields"]["priority"] = {
            "name": priority_name,
            "id": priority_map.get(priority_name, "3"),
        }
    if "created" in overrides:
        default_payload["issue"]["fields"]["created"] = overrides["created"]

    return default_payload


def build_generic_payload(**overrides: Any) -> Dict[str, Any]:
    """
    Build generic webhook payload for mock plugin testing.

    Provides simple flat structure suitable for basic tests.
    Override specific fields via kwargs.

    Args:
        **overrides: Field overrides. Supported:
            - tenant_id: Tenant identifier
            - ticket_id: Ticket ID
            - description: Ticket description
            - priority: Priority level (lowercase)
            - created_at: ISO timestamp string

    Returns:
        Dict[str, Any]: Generic webhook payload.

    Example:
        payload = build_generic_payload(
            tenant_id="test-tenant",
            ticket_id="GENERIC-789"
        )
        valid = await plugin.validate_webhook(payload, "test-signature")
    """
    current_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    default_payload: Dict[str, Any] = {
        "tenant_id": "test-tenant-001",
        "ticket_id": "GENERIC-123",
        "description": "Generic test ticket description",
        "priority": "high",
        "created_at": current_time,
    }

    # Apply overrides (flat structure, direct update)
    default_payload.update(overrides)

    return default_payload
