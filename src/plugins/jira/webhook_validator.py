"""
Jira Webhook Signature Validation

This module provides helper functions for validating Jira webhook signatures
using HMAC-SHA256. Implements constant-time comparison to prevent timing attacks.

The X-Hub-Signature header format: "sha256=<hex_digest>"

Security considerations:
- Uses hmac.compare_digest() for constant-time comparison
- Validates signature method (only sha256 supported)
- Never logs secrets or computed signatures
"""

import hmac
import hashlib
from typing import Tuple


def compute_hmac_signature(body: bytes, secret: str) -> str:
    """
    Compute HMAC-SHA256 signature for webhook body.

    Args:
        body: Raw webhook body as bytes
        secret: Webhook signing secret

    Returns:
        Hex digest string (e.g., "abc123def456...")

    Example:
        >>> body = b'{"issue": {"key": "PROJ-123"}}'
        >>> secret = "my_webhook_secret"
        >>> signature = compute_hmac_signature(body, secret)
        >>> len(signature)
        64
    """
    signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return signature


def parse_signature_header(signature_header: str) -> Tuple[str, str]:
    """
    Parse X-Hub-Signature header to extract method and signature.

    Args:
        signature_header: Header value in format "method=signature"
                         (e.g., "sha256=abc123...")

    Returns:
        Tuple of (method, signature)

    Raises:
        ValueError: If header format is invalid or method is not sha256

    Example:
        >>> parse_signature_header("sha256=abc123def")
        ('sha256', 'abc123def')
    """
    if "=" not in signature_header:
        raise ValueError(
            f"Invalid signature header format: {signature_header}. "
            "Expected format: 'sha256=<signature>'"
        )

    method, signature = signature_header.split("=", 1)

    # Only sha256 is supported (future-proof for other algorithms)
    if method != "sha256":
        raise ValueError(f"Unsupported signature method: {method}. Only 'sha256' is supported.")

    return method, signature


def secure_compare(signature_a: str, signature_b: str) -> bool:
    """
    Perform constant-time comparison of two signatures.

    Uses hmac.compare_digest() to prevent timing attacks where an attacker
    could determine the correct signature by measuring response times.

    Args:
        signature_a: First signature to compare
        signature_b: Second signature to compare

    Returns:
        True if signatures match, False otherwise

    Example:
        >>> secure_compare("abc123", "abc123")
        True
        >>> secure_compare("abc123", "def456")
        False
    """
    return hmac.compare_digest(signature_a, signature_b)
