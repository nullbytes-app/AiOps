"""
Reusable ticket fixtures for testing webhook ingestion and search results.

This module provides realistic, framework-agnostic dictionaries that match the
expected payload shapes for:
- Webhook payloads (ticket created/updated) used by `/webhook/servicedesk`
- Resolved ticket history search results used by context gathering

Each function returns a dict suitable for tests that validate parsing,
priority handling, IP extraction, and ticket history formatting.
"""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Any, Dict, List


def sample_webhook_payload() -> Dict[str, Any]:
    """Basic ServiceDesk webhook payload (ticket created).

    Returns a minimal, valid payload matching src.schemas.webhook.WebhookPayload:
    - event, ticket_id, tenant_id, description, priority, created_at (ISO8601)
    Use in tests that exercise webhook validation, queuing, and parsing.
    """

    return {
        "event": "ticket_created",
        "ticket_id": "TKT-1001",
        "tenant_id": "acme-corp",
        "description": "User reports intermittent latency accessing the dashboard.",
        "priority": "medium",
        "created_at": datetime(2025, 1, 15, 10, 30, tzinfo=UTC).isoformat(),
    }


def high_priority_ticket() -> Dict[str, Any]:
    """High-priority webhook payload for escalation logic tests.

    Mirrors WebhookPayload structure with `priority = "high"`.
    Useful for verifying priority routing and alerting behaviors.
    """

    return {
        "event": "ticket_created",
        "ticket_id": "TKT-2001",
        "tenant_id": "acme-corp",
        "description": (
            "Production API error rates spiking after deploy. Investigate logs and "
            "rollback if necessary."
        ),
        "priority": "high",
        "created_at": datetime(2025, 2, 10, 8, 5, tzinfo=UTC).isoformat(),
    }


def low_priority_ticket() -> Dict[str, Any]:
    """Low-priority webhook payload for de-prioritization tests.

    Mirrors WebhookPayload structure with `priority = "low"`.
    Useful for verifying scheduling and throttling of non-urgent work.
    """

    return {
        "event": "ticket_updated",
        "ticket_id": "TKT-2002",
        "tenant_id": "acme-corp",
        "description": (
            "Minor UI glitch reported on settings page; reproducible only on Safari."
        ),
        "priority": "low",
        "created_at": datetime(2025, 2, 11, 14, 45, tzinfo=UTC).isoformat(),
    }


def ticket_with_ip_addresses() -> Dict[str, Any]:
    """Webhook payload whose description contains IPv4 and IPv6 addresses.

    Matches WebhookPayload shape and embeds multiple IPs to exercise
    src.services.ip_lookup.extract_and_lookup_ips, which supports both
    IPv4 and IPv6 extraction.
    """

    description = (
        "Connection resets observed between app and DB. Affected endpoints: "
        "web-01 (10.0.1.42), cache-02 (192.168.1.10), and ipv6 host "
        "db-v6 (2001:0db8:85a3:0000:0000:8a2e:0370:7334). "
        "Please verify network ACLs and TLS settings."
    )

    return {
        "event": "ticket_created",
        "ticket_id": "TKT-3001",
        "tenant_id": "acme-corp",
        "description": description,
        "priority": "high",
        "created_at": datetime(2025, 3, 5, 9, 0, tzinfo=UTC).isoformat(),
    }


def ticket_without_ip_addresses() -> Dict[str, Any]:
    """Webhook payload without any IP addresses in description.

    Used to validate the graceful-degradation path of IP extraction logic,
    which should return an empty list when no IPs are present.
    """

    return {
        "event": "ticket_created",
        "ticket_id": "TKT-3002",
        "tenant_id": "acme-corp",
        "description": (
            "Users report slow page loads during peak hours. No specific hosts or "
            "addresses mentioned. Investigate database query performance and cache hit rates."
        ),
        "priority": "medium",
        "created_at": datetime(2025, 3, 5, 9, 30, tzinfo=UTC).isoformat(),
    }


def sample_ticket_history() -> Dict[str, Any]:
    """Search results fixture: 5 realistic resolved tickets with metadata.

    Returns a dict that mirrors the logical output structure often consumed by
    higher-level code when wrapping TicketSearchService outputs:
    - results: List of 5 tickets with fields matching TicketSearchResult
      (ticket_id, description, resolution, resolved_date, similarity_score)
    - metadata: Summary info like num_results, method, and timing
    """

    results: List[Dict[str, Any]] = [
        {
            "ticket_id": "TKT-81234",
            "description": (
                "Database connection pool exhausted during nightly backup window; "
                "application threads blocked."
            ),
            "resolution": (
                "Increased pool size from 10 to 25 and added circuit breaker to "
                "queue requests under load."
            ),
            "resolved_date": "2025-01-10T23:45:00Z",
            "similarity_score": 0.94,
        },
        {
            "ticket_id": "TKT-84567",
            "description": (
                "Cache server evictions spiked causing cold starts and elevated latency."
            ),
            "resolution": (
                "Raised memory allocation, tuned eviction policy, and prewarmed keys for "
                "top endpoints."
            ),
            "resolved_date": "2025-01-20T16:10:00Z",
            "similarity_score": 0.88,
        },
        {
            "ticket_id": "TKT-87777",
            "description": (
                "Intermittent TLS handshake timeouts between web and app tier after deploy."
            ),
            "resolution": (
                "Rolled back to prior image, rotated certificates, and increased handshake "
                "timeout by 2s under load."
            ),
            "resolved_date": "2025-01-28T05:22:11Z",
            "similarity_score": 0.81,
        },
        {
            "ticket_id": "TKT-89990",
            "description": (
                "Read replica lag exceeded 60s during analytics job, impacting reads."
            ),
            "resolution": (
                "Throttled analytics batch, adjusted replica IOPS, and added alerting at 20s."
            ),
            "resolved_date": "2025-02-02T11:05:33Z",
            "similarity_score": 0.73,
        },
        {
            "ticket_id": "TKT-90210",
            "description": (
                "Elevated p95 latency correlated with cache miss bursts during config reloads."
            ),
            "resolution": (
                "Staggered reloads, increased cache TTL for hot keys, and added warmup job."
            ),
            "resolved_date": "2025-02-07T19:40:12Z",
            "similarity_score": 0.67,
        },
    ]

    metadata = {
        "num_results": len(results),
        "search_time_ms": 145,
        "fallback_method_used": False,
        "method": "fts",
    }

    return {"results": results, "metadata": metadata}


__all__ = [
    "sample_webhook_payload",
    "high_priority_ticket",
    "low_priority_ticket",
    "ticket_with_ip_addresses",
    "ticket_without_ip_addresses",
    "sample_ticket_history",
]

