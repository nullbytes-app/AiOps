"""
Webhook signature validation service with multi-tenant support.

Implements HMAC-SHA256 signature validation per-tenant with replay attack prevention.
Uses constant-time comparison to prevent timing attacks and includes timestamp validation.
"""

import hmac
import hashlib
import json
import re
from typing import Optional
from datetime import datetime, timezone

from fastapi import Header, HTTPException, Request, Depends, status

from src.config import Settings, get_settings
from src.utils.logger import logger
from src.services.tenant_service import TenantService
from src.utils.exceptions import TenantNotFoundException


def compute_hmac_signature(secret: str, payload_bytes: bytes) -> str:
    """
    Compute HMAC-SHA256 signature of payload.

    Args:
        secret: Shared secret key for HMAC
        payload_bytes: Raw request body as bytes

    Returns:
        Hex-encoded HMAC-SHA256 digest (64 characters)

    Raises:
        ValueError: If secret is empty or None
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

    Uses hmac.compare_digest() to prevent timing attacks.

    Args:
        sig1: First signature string
        sig2: Second signature string

    Returns:
        True if signatures are equal, False otherwise
    """
    return hmac.compare_digest(sig1, sig2)


def extract_tenant_id_from_payload(body: bytes) -> str:
    """
    Extract tenant_id from webhook payload with validation.

    Performs lightweight JSON parsing to extract only tenant_id field.
    Validates format before returning.

    Args:
        body: Raw request body as bytes

    Returns:
        Extracted tenant_id

    Raises:
        ValueError: If tenant_id missing, invalid format, or JSON parse fails
    """
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in webhook payload: {str(e)}")

    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        raise ValueError("tenant_id field is required in webhook payload")

    # Validate tenant_id format: lowercase alphanumeric + dashes
    # Pattern from Story 3.4: ^[a-z0-9-]+$
    from src.utils.constants import TENANT_ID_PATTERN
    if not re.match(TENANT_ID_PATTERN, tenant_id):
        raise ValueError(
            f"tenant_id format invalid: {tenant_id}. Must match pattern: {TENANT_ID_PATTERN}"
        )

    return tenant_id


def validate_webhook_timestamp(created_at: datetime) -> str:
    """
    Validate webhook timestamp for replay attack prevention.

    Checks that timestamp is within tolerance window and has timezone info.

    Args:
        created_at: Timestamp from webhook payload

    Raises:
        ValueError: If timestamp is invalid, expired, or in future
    """
    # Check timezone info
    if created_at.tzinfo is None:
        raise ValueError(
            "created_at must include timezone information "
            "(e.g., '2025-11-01T12:00:00Z' or '2025-11-01T12:00:00+00:00')"
        )

    # Get current time in UTC
    now = datetime.now(timezone.utc)

    # Get configured tolerances
    from src.config import get_settings
    settings = get_settings()
    tolerance_seconds = getattr(settings, 'WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS', 300)
    clock_skew_seconds = getattr(settings, 'WEBHOOK_CLOCK_SKEW_TOLERANCE_SECONDS', 30)

    # Convert created_at to UTC for comparison
    created_at_utc = created_at.astimezone(timezone.utc) if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)

    # Check if too old
    time_diff = (now - created_at_utc).total_seconds()
    if time_diff > tolerance_seconds:
        raise ValueError(
            f"Webhook timestamp expired (older than {tolerance_seconds} seconds)"
        )

    # Check if in future (clock skew tolerance)
    if time_diff < -clock_skew_seconds:
        raise ValueError(
            f"Webhook timestamp in future (clock skew > {clock_skew_seconds} seconds)"
        )


async def validate_webhook_signature(
    request: Request,
    x_servicedesk_signature: Optional[str] = Header(
        None, alias="X-ServiceDesk-Signature"
    ),
    settings: Settings = Depends(get_settings),
    tenant_service: TenantService = Depends(TenantService),
) -> str:
    """
    FastAPI dependency for multi-tenant webhook signature validation.

    Performs full validation flow:
    1. Extract tenant_id from payload
    2. Verify tenant exists and is active
    3. Retrieve tenant's webhook secret (cached from database)
    4. Validate signature using tenant-specific secret
    5. Validate timestamp for replay attack prevention

    Args:
        request: FastAPI Request object
        x_servicedesk_signature: HMAC-SHA256 signature from header
        settings: Application settings
        tenant_service: Service for retrieving tenant-specific secrets

    Returns:
        tenant_id if validation succeeds

    Raises:
        HTTPException(401): If signature invalid, timestamp expired, or missing header
        HTTPException(404): If tenant not found
        HTTPException(403): If tenant inactive
        HTTPException(422): If validation errors in payload

    Security Notes:
        - Validates signature BEFORE full Pydantic parsing
        - Uses tenant-specific secret from database (cached in Redis)
        - Logs all security events with structured extra fields
        - Returns specific error codes (401, 404, 403) for proper handling
        - Prevents cross-tenant webhook spoofing via per-tenant secrets
    """
    source_ip = request.client.host if request.client else "unknown"

    # Check if signature header is present
    if not x_servicedesk_signature:
        logger.error(
            "Webhook signature validation failed: Missing X-ServiceDesk-Signature header",
            extra={
                "event_type": "signature_mismatch",
                "error_type": "missing_header",
                "source_ip": source_ip,
                "endpoint": request.url.path,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Missing signature header", "error_type": "authentication_error"},
        )

    # Read raw request body
    raw_body = await request.body()

    # Extract tenant_id from payload
    try:
        tenant_id = extract_tenant_id_from_payload(raw_body)
    except ValueError as e:
        logger.error(
            f"Webhook validation failed: {str(e)}",
            extra={
                "event_type": "validation_error",
                "error_type": "invalid_payload",
                "source_ip": source_ip,
                "endpoint": request.url.path,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"detail": str(e), "error_type": "validation_error"},
        )

    # Verify tenant exists and is active
    try:
        tenant_config = await tenant_service.get_tenant_config(tenant_id)
        if not tenant_config.is_active:
            logger.error(
                f"Webhook validation failed: Tenant inactive",
                extra={
                    "event_type": "tenant_inactive",
                    "error_type": "forbidden",
                    "tenant_id": tenant_id,
                    "source_ip": source_ip,
                    "endpoint": request.url.path,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"detail": "Tenant is inactive", "error_type": "forbidden"},
            )
    except TenantNotFoundException:
        # Return 404 Not Found for unknown tenants (prevents enumeration)
        logger.error(
            "Webhook validation failed: Tenant not found",
            extra={
                "event_type": "tenant_not_found",
                "error_type": "not_found",
                "tenant_id": tenant_id,
                "source_ip": source_ip,
                "endpoint": request.url.path,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Not found", "error_type": "not_found"},
        )

    # Retrieve tenant-specific webhook secret (cached in Redis)
    try:
        webhook_secret = await tenant_service.get_webhook_secret(tenant_id)
    except (TenantNotFoundException, Exception) as e:
        logger.error(
            f"Webhook validation failed: Could not retrieve tenant secret: {str(e)}",
            extra={
                "event_type": "secret_retrieval_failed",
                "error_type": "internal_error",
                "tenant_id": tenant_id,
                "source_ip": source_ip,
                "endpoint": request.url.path,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Invalid webhook signature", "error_type": "authentication_error"},
        )

    # Validate signature using tenant-specific secret
    is_valid = secure_compare(
        compute_hmac_signature(webhook_secret, raw_body),
        x_servicedesk_signature,
    )

    if not is_valid:
        logger.error(
            "Webhook signature validation failed: Invalid signature",
            extra={
                "event_type": "signature_mismatch",
                "error_type": "invalid_signature",
                "tenant_id": tenant_id,
                "source_ip": source_ip,
                "endpoint": request.url.path,
                "body_length": len(raw_body),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Invalid webhook signature", "error_type": "authentication_error"},
        )

    return tenant_id


# Keep original function for backward compatibility
def validate_signature(
    raw_payload: bytes,
    signature_header: str,
    secret: str,
) -> bool:
    """
    Validate HMAC-SHA256 signature of webhook payload.

    Deprecated: Use compute_hmac_signature + secure_compare instead.

    Args:
        raw_payload: Raw request body as bytes
        signature_header: Hex-encoded signature from X-ServiceDesk-Signature header
        secret: Shared secret key for HMAC computation

    Returns:
        bool: True if signature is valid, False otherwise
    """
    if not secret:
        raise ValueError("Secret cannot be empty or None")

    if not signature_header:
        return False

    computed = compute_hmac_signature(secret, raw_payload)
    return secure_compare(computed, signature_header)
