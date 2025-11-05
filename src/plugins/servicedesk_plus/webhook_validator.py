"""
ServiceDesk Plus webhook signature validation helpers.

Migrated from src/services/webhook_validator.py for plugin architecture.
Implements HMAC-SHA256 signature validation with replay attack prevention.

Security Features:
    - Constant-time signature comparison (prevents timing attacks)
    - Timestamp validation with configurable tolerance
    - Tenant ID format validation
"""

import hmac
import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Dict, Any


def compute_hmac_signature(secret: str, payload_bytes: bytes) -> str:
    """
    Compute HMAC-SHA256 signature of payload.

    Args:
        secret: Shared secret key for HMAC computation
        payload_bytes: Raw request body as bytes

    Returns:
        Hex-encoded HMAC-SHA256 digest (64 characters)

    Raises:
        ValueError: If secret is empty or None

    Example:
        >>> secret = "my-webhook-secret"
        >>> payload = b'{"tenant_id": "acme", "ticket_id": "123"}'
        >>> sig = compute_hmac_signature(secret, payload)
        >>> len(sig)
        64
    """
    if not secret:
        raise ValueError("Secret cannot be empty or None")

    return hmac.new(
        key=secret.encode("utf-8"),
        msg=payload_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()


def secure_compare(sig1: str, sig2: str) -> bool:
    """
    Constant-time comparison of signatures.

    Uses hmac.compare_digest() to prevent timing attacks where an attacker
    could measure response time to deduce correct signature bytes.

    Args:
        sig1: First signature string
        sig2: Second signature string

    Returns:
        True if signatures are equal, False otherwise

    Security:
        - Constant-time comparison prevents timing attacks
        - Safe for cryptographic signature verification

    Example:
        >>> sig1 = "abc123"
        >>> sig2 = "abc123"
        >>> secure_compare(sig1, sig2)
        True
    """
    return hmac.compare_digest(sig1, sig2)


def extract_tenant_id_from_payload(body: bytes) -> str:
    """
    Extract tenant_id from webhook payload with validation.

    Performs lightweight JSON parsing to extract only tenant_id field.
    Validates format against tenant ID pattern.

    Args:
        body: Raw request body as bytes

    Returns:
        Extracted tenant_id string

    Raises:
        ValueError: If tenant_id missing, invalid format, or JSON parse fails

    Example:
        >>> payload = b'{"tenant_id": "acme-corp", "ticket_id": "123"}'
        >>> extract_tenant_id_from_payload(payload)
        'acme-corp'
    """
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in webhook payload: {str(e)}")

    tenant_id_raw = payload.get("tenant_id")
    if not tenant_id_raw:
        raise ValueError("tenant_id field is required in webhook payload")

    # Cast to string for type safety
    tenant_id: str = str(tenant_id_raw)

    # Validate tenant_id format: lowercase alphanumeric + dashes
    # Pattern from Story 3.4: ^[a-z0-9-]+$
    from src.utils.constants import TENANT_ID_PATTERN

    if not re.match(TENANT_ID_PATTERN, tenant_id):
        raise ValueError(
            f"tenant_id format invalid: {tenant_id}. Must match pattern: {TENANT_ID_PATTERN}"
        )

    return tenant_id


def validate_webhook_timestamp(
    created_at: datetime, tolerance_seconds: int = 300, clock_skew_seconds: int = 30
) -> None:
    """
    Validate webhook timestamp for replay attack prevention.

    Checks that timestamp is within tolerance window and has timezone info.
    Prevents replay attacks by rejecting old webhooks.

    Args:
        created_at: Timestamp from webhook payload
        tolerance_seconds: Maximum age of webhook in seconds (default: 300 = 5 minutes)
        clock_skew_seconds: Allowed clock skew for future timestamps (default: 30 seconds)

    Raises:
        ValueError: If timestamp is invalid, expired, or in future beyond clock skew

    Security:
        - Prevents replay attacks by rejecting expired webhooks
        - Allows small clock skew for distributed systems
        - Requires timezone-aware timestamps

    Example:
        >>> from datetime import datetime, timezone
        >>> now = datetime.now(timezone.utc)
        >>> validate_webhook_timestamp(now)  # Valid - recent timestamp
        >>> old = datetime(2020, 1, 1, tzinfo=timezone.utc)
        >>> validate_webhook_timestamp(old)  # Raises ValueError - expired
        Traceback (most recent call last):
        ...
        ValueError: Webhook timestamp expired (older than 300 seconds)
    """
    # Check timezone info
    if created_at.tzinfo is None:
        raise ValueError(
            "created_at must include timezone information "
            "(e.g., '2025-11-01T12:00:00Z' or '2025-11-01T12:00:00+00:00')"
        )

    # Get current time in UTC
    now = datetime.now(timezone.utc)

    # Convert created_at to UTC for comparison
    created_at_utc = created_at.astimezone(timezone.utc)

    # Check if too old (expired)
    time_diff = (now - created_at_utc).total_seconds()
    if time_diff > tolerance_seconds:
        raise ValueError(f"Webhook timestamp expired (older than {tolerance_seconds} seconds)")

    # Check if in future (clock skew tolerance)
    if time_diff < -clock_skew_seconds:
        raise ValueError(f"Webhook timestamp in future (clock skew > {clock_skew_seconds} seconds)")
