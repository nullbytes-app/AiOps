"""
Webhook service layer for HMAC signature generation and validation.

Provides utility functions for webhook URL generation, HMAC secret management,
signature validation (with timing-attack prevention), and payload schema validation.

Story 8.6: Agent Webhook Endpoint Generation - Service layer for webhook operations.
"""

import base64
import hashlib
import hmac
import secrets
from typing import Optional
from uuid import UUID

import jsonschema
from jsonschema import Draft7Validator

from src.utils.logger import logger


def generate_webhook_url(agent_id: UUID, base_url: str) -> str:
    """
    Generate webhook URL for agent.

    Args:
        agent_id: Agent UUID
        base_url: Base URL for webhook (e.g., "https://api.example.com")

    Returns:
        str: Full webhook URL (e.g., "https://api.example.com/agents/{uuid}/webhook")

    Example:
        >>> url = generate_webhook_url(UUID("550e8400-e29b-41d4-a716-446655440000"), "https://api.example.com")
        >>> url
        'https://api.example.com/agents/550e8400-e29b-41d4-a716-446655440000/webhook'
    """
    return f"{base_url}/agents/{agent_id}/webhook"


def generate_hmac_secret() -> str:
    """
    Generate cryptographically strong 32-byte HMAC secret.

    Uses secrets.token_bytes(32) for cryptographically secure random generation
    (256 bits). Returns base64-encoded string safe for storage and transmission.

    Returns:
        str: Base64-encoded 32-byte HMAC secret (44 characters after encoding)

    Reason:
        Use secrets module (not random) for cryptographic strength. HMAC-SHA256
        requires 256-bit (32-byte) keys for optimal security. Base64 encoding
        ensures safe string representation for database storage.

    Example:
        >>> secret = generate_hmac_secret()
        >>> len(secret)
        44
        >>> # Secret is base64-encoded 32 bytes
    """
    secret_bytes = secrets.token_bytes(32)
    return base64.b64encode(secret_bytes).decode("utf-8")


def validate_hmac_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Validate HMAC-SHA256 signature using constant-time comparison.

    Computes expected signature from payload and secret, then uses
    hmac.compare_digest() for constant-time comparison to prevent
    timing attacks (2025 security best practice).

    Args:
        payload: Raw request body bytes (e.g., request.body from FastAPI)
        signature: Signature from request header (e.g., "sha256=abc123...")
        secret: HMAC secret (base64-encoded, decrypted from database)

    Returns:
        bool: True if signature valid, False otherwise

    Raises:
        ValueError: If secret is empty or None

    Reason:
        MUST use hmac.compare_digest() instead of == operator to prevent
        timing attacks. Constant-time comparison ensures attackers cannot
        measure response times to brute-force valid signatures.

    Example:
        >>> payload = b'{"ticket_id": "12345"}'
        >>> secret = "base64_encoded_secret_here"
        >>> signature = "sha256=computed_hmac_hex"
        >>> validate_hmac_signature(payload, signature, secret)
        True
    """
    if not secret:
        raise ValueError("HMAC secret cannot be empty")

    # Decode base64 secret to bytes for HMAC computation
    try:
        secret_bytes = base64.b64decode(secret)
    except Exception as e:
        logger.error(f"Failed to decode HMAC secret: {e}")
        return False

    # Compute expected signature
    expected = hmac.new(secret_bytes, payload, hashlib.sha256).hexdigest()

    # Extract hex digest from signature header (e.g., "sha256=abc123" -> "abc123")
    if signature.startswith("sha256="):
        signature = signature[7:]  # Remove "sha256=" prefix

    # Use constant-time comparison to prevent timing attacks
    # Reason: hmac.compare_digest() is cryptographically secure
    return hmac.compare_digest(expected, signature)


def validate_payload_schema(payload: dict, schema: dict) -> tuple[bool, Optional[str]]:
    """
    Validate JSON payload against JSON Schema Draft 7.

    Uses jsonschema library to validate payload structure. Returns detailed
    error message if validation fails to help webhook senders debug issues.

    Args:
        payload: JSON payload to validate (parsed dict)
        schema: JSON Schema Draft 7 format (dict with "type", "properties", "required", etc.)

    Returns:
        tuple[bool, Optional[str]]: (True, None) if valid, (False, error_message) if invalid

    Reason:
        JSON Schema provides standard, well-supported validation format.
        Draft 7 is widely adopted with mature libraries. Detailed error
        messages help external systems fix invalid webhook requests.

    Example:
        >>> schema = {"type": "object", "properties": {"ticket_id": {"type": "string"}}, "required": ["ticket_id"]}
        >>> payload = {"ticket_id": "12345"}
        >>> validate_payload_schema(payload, schema)
        (True, None)
        >>> invalid_payload = {}
        >>> validate_payload_schema(invalid_payload, schema)
        (False, "'ticket_id' is a required property")
    """
    try:
        # Validate schema format first (raises SchemaError if invalid)
        Draft7Validator.check_schema(schema)

        # Validate payload against schema
        jsonschema.validate(instance=payload, schema=schema)
        return (True, None)

    except jsonschema.exceptions.ValidationError as e:
        # Payload validation failed - return detailed error message
        error_msg = e.message
        if e.path:
            # Include path to failed field (e.g., "data.ticket.id")
            path = ".".join(str(p) for p in e.path)
            error_msg = f"Validation failed at '{path}': {error_msg}"
        return (False, error_msg)

    except jsonschema.exceptions.SchemaError as e:
        # Schema itself is invalid
        logger.error(f"Invalid payload schema: {e}")
        return (False, f"Invalid schema definition: {e.message}")

    except Exception as e:
        # Unexpected error during validation
        logger.error(f"Payload validation error: {e}")
        return (False, f"Validation error: {str(e)}")


def compute_hmac_signature(payload: bytes, secret: str) -> str:
    """
    Compute HMAC-SHA256 signature for webhook payload.

    Helper function for generating signatures in test webhook UI and
    documentation examples. Returns signature in GitHub/Stripe format
    (sha256={hexdigest}).

    Args:
        payload: Raw request body bytes
        secret: Base64-encoded HMAC secret

    Returns:
        str: Signature in format "sha256={hexdigest}"

    Raises:
        ValueError: If secret is empty or invalid

    Example:
        >>> payload = b'{"ticket_id": "12345"}'
        >>> secret = "base64_encoded_secret_here"
        >>> signature = compute_hmac_signature(payload, secret)
        >>> signature.startswith("sha256=")
        True
    """
    if not secret:
        raise ValueError("HMAC secret cannot be empty")

    try:
        secret_bytes = base64.b64decode(secret)
    except Exception as e:
        raise ValueError(f"Invalid HMAC secret format: {e}")

    # Compute HMAC-SHA256 signature
    signature = hmac.new(secret_bytes, payload, hashlib.sha256).hexdigest()

    # Return in GitHub/Stripe format
    return f"sha256={signature}"
