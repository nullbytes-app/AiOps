"""
IP Address Cross-Reference Service.

Extracts IP addresses (IPv4 and IPv6) from ticket descriptions and looks up
corresponding system information from the system_inventory table. Provides
context about which systems are affected by reported issues.

Architecture:
    - IP Extraction: Uses regex patterns to extract IPv4 and IPv6 addresses
    - Deduplication: Converts to set to remove duplicate IPs
    - Database Lookup: Queries system_inventory with tenant isolation
    - Error Handling: Graceful degradation - returns empty list on any error

Usage:
    results = await extract_and_lookup_ips(session, tenant_id, description)
    # Returns: [{"ip_address": "...", "hostname": "...", "role": "...", ...}, ...]

Patterns (from tech-spec Section 5):
    - IPv4: \\b(?:[0-9]{1,3}\\.){3}[0-9]{1,3}\\b
    - IPv6: \\b(?:[A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4}\\b
"""

import re
import time
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import SystemInventory
from src.utils.logger import logger

# IPv4 regex pattern: Matches standard dotted-decimal notation
# Example: 192.168.1.1, 10.0.0.1
IPV4_PATTERN = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"

# IPv6 regex pattern: Matches full IPv6 addresses (8 groups of hex)
# Example: 2001:0db8:85a3:0000:0000:8a2e:0370:7334
# Note: Simplified pattern for full addresses; compressed formats like ::1 covered separately
IPV6_PATTERN = r"\b(?:[A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4}\b"


async def extract_and_lookup_ips(
    session: AsyncSession,
    tenant_id: str,
    description: str,
    correlation_id: Optional[str] = None,
) -> List[dict]:
    """
    Extract IP addresses from ticket description and lookup system details.

    Implements Story 2.7 Acceptance Criteria:
    - AC #1: Extracts IPv4 and IPv6 addresses using regex patterns
    - AC #2-#3: Queries system_inventory table for matching IPs (tenant-isolated)
    - AC #4: Handles multiple IPs in single description
    - AC #5: Returns empty list on no matches (graceful degradation)
    - AC #6: Supports both IPv4 and IPv6 patterns

    Args:
        session: Async SQLAlchemy session for database access
        tenant_id: Tenant identifier for data isolation
        description: Ticket description to extract IPs from
        correlation_id: Optional request ID for distributed tracing

    Returns:
        List[dict]: List of system info dicts with keys:
            - ip_address: The matched IP address
            - hostname: System hostname
            - role: System role/function
            - client: Client/project name
            - location: Physical or logical location
        Returns empty list on:
            - No IPs found in description
            - No matching systems in inventory
            - Database error
            - Invalid input
    """
    start_time = time.time()
    ips_extracted = set()
    systems_found = 0
    error_occurred = None

    try:
        # Validate inputs
        if not isinstance(description, str) or not description.strip():
            logger.warning(
                "IP lookup: Empty or invalid description",
                extra={
                    "tenant_id": tenant_id,
                    "correlation_id": correlation_id,
                    "description_type": type(description).__name__,
                },
            )
            return []

        if not isinstance(tenant_id, str) or not tenant_id.strip():
            logger.warning(
                "IP lookup: Invalid tenant_id",
                extra={
                    "tenant_id": tenant_id,
                    "correlation_id": correlation_id,
                },
            )
            return []

        # Extract IPv4 addresses
        ipv4_matches = re.findall(IPV4_PATTERN, description)
        ips_extracted.update(ipv4_matches)

        # Extract IPv6 addresses
        ipv6_matches = re.findall(IPV6_PATTERN, description)
        ips_extracted.update(ipv6_matches)

        # Log extraction results
        logger.info(
            f"IP extraction completed: extracted={len(ips_extracted)} unique IPs",
            extra={
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
                "ips_extracted": len(ips_extracted),
                "ipv4_count": len(ipv4_matches),
                "ipv6_count": len(ipv6_matches),
            },
        )

        # If no IPs found, return empty list (AC #5: not an error)
        if not ips_extracted:
            return []

        # Query system_inventory for matching IPs with tenant isolation (AC #2, #3)
        # Build WHERE clause: tenant_id = ? AND ip_address IN (...)
        stmt = select(
            SystemInventory.ip_address,
            SystemInventory.hostname,
            SystemInventory.role,
            SystemInventory.client,
            SystemInventory.location,
        ).where(
            SystemInventory.tenant_id == tenant_id,
            SystemInventory.ip_address.in_(list(ips_extracted)),
        )

        result = await session.execute(stmt)
        rows = result.fetchall()

        # Convert rows to list of dicts
        systems = [
            {
                "ip_address": row[0],
                "hostname": row[1],
                "role": row[2],
                "client": row[3],
                "location": row[4],
            }
            for row in rows
        ]
        systems_found = len(systems)

        # Log lookup results
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(
            f"IP lookup completed: found={systems_found} systems",
            extra={
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
                "ips_extracted": len(ips_extracted),
                "systems_found": systems_found,
                "lookup_latency_ms": elapsed_ms,
            },
        )

        return systems

    except Exception as e:
        # AC #5: Graceful degradation on any error
        error_occurred = str(e)
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.error(
            f"IP lookup error: {error_occurred}",
            extra={
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
                "error": error_occurred,
                "ips_extracted": len(ips_extracted),
                "lookup_latency_ms": elapsed_ms,
            },
        )
        # Return empty list instead of raising exception
        return []
