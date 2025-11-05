"""
Template Webhook Validator.

TODO: Implement tool-specific webhook signature validation.
"""

import hmac
import hashlib
import secrets
import logging

logger = logging.getLogger(__name__)


def validate_signature(payload_bytes: bytes, signature: str, secret: str) -> bool:
    """
    Validate webhook signature.

    TODO: Implement tool-specific validation algorithm.

    Common algorithms:
    - HMAC-SHA256 (ServiceDesk Plus, Jira): hmac.new(secret, payload, sha256)
    - JWT (Zendesk): jwt.decode(token, secret, algorithms=['HS256'])
    - Custom signature schemes

    Args:
        payload_bytes: Raw webhook payload as bytes
        signature: Signature from webhook header
        secret: Webhook signing secret

    Returns:
        True if valid, False otherwise

    Example (HMAC-SHA256):
        expected = hmac.new(
            secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        return secrets.compare_digest(f"sha256={expected}", signature)
    """
    # TODO: Implement validation logic
    raise NotImplementedError("TODO: Implement validate_signature()")


def parse_signature_header(signature: str) -> tuple[str, str]:
    """
    Parse signature header.

    TODO: Implement header parsing for your tool.

    Args:
        signature: Signature header value

    Returns:
        Tuple of (method, signature_value)

    Example:
        Input: "sha256=abc123..."
        Output: ("sha256", "abc123...")
    """
    # TODO: Implement header parsing
    if "=" not in signature:
        raise ValueError(f"Invalid signature format: {signature}")

    method, sig = signature.split("=", 1)
    return method, sig
```