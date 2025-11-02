"""
Webhook signature validation service for authenticating requests.

This module implements HMAC-SHA256 signature validation to ensure webhook
requests are authentic and originated from ServiceDesk Plus. Uses constant-time
comparison to prevent timing attacks.
"""

import hmac
import hashlib
from typing import Optional

from fastapi import Header, HTTPException, Request, Depends, status

from src.config import Settings, get_settings
from src.utils.logger import logger


def validate_signature(
    raw_payload: bytes,
    signature_header: str,
    secret: str,
) -> bool:
    """
    Validate HMAC-SHA256 signature of webhook payload.

    Computes HMAC-SHA256 hash of the raw payload using the shared secret,
    then compares with the signature provided in the request header using
    constant-time comparison to prevent timing attacks.

    Args:
        raw_payload: Raw request body as bytes (before JSON parsing)
        signature_header: Hex-encoded signature from X-ServiceDesk-Signature header
        secret: Shared secret key for HMAC computation

    Returns:
        bool: True if signature is valid, False otherwise

    Raises:
        ValueError: If secret is empty or None

    Example:
        >>> payload = b'{"event":"ticket_created","ticket_id":"TKT-001"}'
        >>> secret = "my-secret-key"
        >>> signature = "a1b2c3..."  # Pre-computed HMAC-SHA256 hex digest
        >>> validate_signature(payload, signature, secret)
        True

    Security Notes:
        - Uses hmac.compare_digest() for constant-time comparison
        - Prevents timing attacks that could leak signature information
        - Raw payload bytes used to ensure integrity before parsing
        - Secret should be strong random value (min 32 chars recommended)
    """
    # Validate inputs
    if not secret:
        raise ValueError("Secret cannot be empty or None")

    if not signature_header:
        return False

    # Compute HMAC-SHA256 of payload with shared secret
    # Reason: HMAC provides cryptographically secure message authentication
    computed_signature = hmac.new(
        key=secret.encode("utf-8"),
        msg=raw_payload,
        digestmod=hashlib.sha256,
    ).hexdigest()

    # Use constant-time comparison to prevent timing attacks
    # Reason: hmac.compare_digest() prevents attackers from determining
    # signature validity by measuring response time differences
    return hmac.compare_digest(computed_signature, signature_header)


async def validate_webhook_signature(
    request: Request,
    x_servicedesk_signature: Optional[str] = Header(
        None, alias="X-ServiceDesk-Signature"
    ),
    settings: Settings = Depends(get_settings),
) -> None:
    """
    FastAPI dependency for validating webhook request signatures.

    Extracts the signature header and raw request body, validates the HMAC-SHA256
    signature, and raises HTTPException(401) if validation fails. This dependency
    runs before the endpoint function, ensuring only authenticated requests proceed.

    Args:
        request: FastAPI Request object containing raw body
        x_servicedesk_signature: HMAC-SHA256 signature from X-ServiceDesk-Signature header
        settings: Application settings containing webhook_secret

    Returns:
        None: Passes silently if validation succeeds

    Raises:
        HTTPException(401): If signature header is missing or signature is invalid

    Example Usage:
        @router.post("/webhook/servicedesk", dependencies=[Depends(validate_webhook_signature)])
        async def receive_webhook(payload: WebhookPayload):
            # Only executed if signature validation passes
            ...

    Security Notes:
        - Validates signature BEFORE Pydantic parsing (ensures data integrity)
        - Logs failed validation attempts with WARNING level for security monitoring
        - Returns 401 Unauthorized for both missing and invalid signatures
        - Does not expose signature details in error messages
    """
    # Check if signature header is present
    if not x_servicedesk_signature:
        logger.warning(
            "Webhook signature validation failed: Missing X-ServiceDesk-Signature header",
            extra={
                "reason": "missing_header",
                "source_ip": request.client.host if request.client else "unknown",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing signature header",
        )

    # Read raw request body for signature computation
    # Reason: Signature must be computed on raw bytes before any parsing
    raw_body = await request.body()

    # Validate signature using HMAC-SHA256
    is_valid = validate_signature(
        raw_payload=raw_body,
        signature_header=x_servicedesk_signature,
        secret=settings.webhook_secret,
    )

    if not is_valid:
        logger.warning(
            "Webhook signature validation failed: Invalid signature",
            extra={
                "reason": "invalid_signature",
                "source_ip": request.client.host if request.client else "unknown",
                "body_length": len(raw_body),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )
