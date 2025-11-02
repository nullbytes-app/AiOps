"""
WorkflowState fixtures for testing context-dependent functionality.

This module provides reusable pytest fixtures that model different states of the
workflow context used by the enhancement workflow and LLM synthesis layers. Each
fixture returns a dict containing the following fields only:

- ticket_id: str
- description: str
- similar_tickets: list
- kb_articles: list
- ip_info: dict | None
- error: str | None

These fixtures are intentionally lightweight and focus on the pieces of state
typically required by downstream consumers (e.g., formatters, aggregators,
and synthesis). They are suitable for unit tests that don't require the full
workflow metadata.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import pytest


@pytest.fixture
def sample_workflow_state_full() -> Dict[str, Any]:
    """
    Complete context with all elements present.

    Returns a state that includes ticket information, a non-empty list of
    similar tickets, a non-empty list of KB articles, and IP/system context.
    The `error` field is None to represent a successful aggregation path.
    """
    return {
        "ticket_id": "TKT-1001",
        "description": "User unable to connect to VPN; error 720 observed on Windows 11.",
        "similar_tickets": [
            {
                "ticket_id": "TKT-0991",
                "description": "VPN connection fails with error 720",
                "resolution": "Reset WAN Miniport adapters and re-installed VPN client",
                "resolved_date": "2025-10-28",
            },
            {
                "ticket_id": "TKT-0977",
                "description": "Intermittent VPN disconnects",
                "resolution": "Updated NIC drivers and disabled power management",
                "resolved_date": "2025-10-22",
            },
        ],
        "kb_articles": [
            {
                "title": "Troubleshoot VPN Error 720",
                "summary": "Steps to reset WAN Miniports and repair L2TP/IPSec stack.",
                "url": "https://kb.example.com/vpn-error-720",
            },
            {
                "title": "Windows 11 VPN Known Issues",
                "summary": "Common VPN issues and mitigation steps on Windows 11.",
                "url": "https://kb.example.com/win11-vpn-issues",
            },
        ],
        # IP/system context present in the full scenario
        "ip_info": {
            "hostname": "vpn-gw1.acme.local",
            "ip_address": "10.0.0.8",
            "role": "VPN Gateway",
            "client": "Acme Corp",
            "location": "DC-1",
        },
        "error": None,
    }


@pytest.fixture
def sample_workflow_state_partial() -> Dict[str, Any]:
    """
    Partial context: KB search timed out; other elements present.

    Simulates a scenario where knowledge base lookup fails or times out while
    similar tickets and system context are still available. The `error` field
    records the KB timeout condition.
    """
    return {
        "ticket_id": "TKT-1002",
        "description": "Intermittent packet loss reported from branch office network.",
        "similar_tickets": [
            {
                "ticket_id": "TKT-0940",
                "description": "Packet loss due to duplex mismatch",
                "resolution": "Forced full-duplex on switch uplink",
                "resolved_date": "2025-10-12",
            }
        ],
        # KB timed out — keep list present but empty for consumers that iterate
        "kb_articles": [],
        # IP/system context still present
        "ip_info": {
            "hostname": "edge-sw1.branch.local",
            "ip_address": "192.168.50.2",
            "role": "Edge Switch",
            "client": "Acme Corp",
            "location": "Branch-12",
        },
        "error": "Knowledge base search timed out",
    }


@pytest.fixture
def sample_workflow_state_empty() -> Dict[str, Any]:
    """
    Minimal context: only ticket information present.

    Useful for testing fallback behavior where no related tickets, documentation,
    or system information could be gathered. All optional context fields are
    empty/None and error is None.
    """
    return {
        "ticket_id": "TKT-1003",
        "description": "Application launches to a blank screen after update.",
        "similar_tickets": [],
        "kb_articles": [],
        "ip_info": None,
        "error": None,
    }


@pytest.fixture
def sample_workflow_state_with_error() -> Dict[str, Any]:
    """
    Context with an explicit error recorded.

    Represents a scenario where context gathering encountered an unexpected
    error (e.g., service dependency failure). Optional context fields may be
    empty or missing data; `error` contains a human-readable description.
    """
    return {
        "ticket_id": "TKT-1004",
        "description": "Email delivery delays to external domains.",
        "similar_tickets": [],
        "kb_articles": [
            {
                "title": "Diagnose Email Queue Backlogs",
                "summary": "How to inspect and drain mail queues safely.",
                "url": "https://kb.example.com/email-queue-diagnosis",
            }
        ],
        # IP/system context unavailable in this error case
        "ip_info": None,
        "error": "Unexpected error while aggregating IP lookup context",
    }


__all__ = [
    "sample_workflow_state_full",
    "sample_workflow_state_partial",
    "sample_workflow_state_empty",
    "sample_workflow_state_with_error",
]

