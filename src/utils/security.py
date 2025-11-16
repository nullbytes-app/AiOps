"""
Security utilities for data masking and sanitization.

This module provides utilities for masking sensitive data in API responses
and logs, ensuring API keys, passwords, and authentication tokens are not
exposed in execution traces or debug output.
"""

import json
import re
from typing import Any, Union


def mask_sensitive_data(data: Union[dict, str]) -> Union[dict, str]:
    """
    Mask sensitive data (API keys, passwords, tokens) in text or JSON.

    Applies regex patterns to detect and mask sensitive patterns including:
    - API keys (patterns: sk-, pk-, rk-, etc.)
    - Bearer tokens
    - Password fields in JSON
    - Authorization headers

    Args:
        data: Input data as dict or string to be masked

    Returns:
        Masked data in the same format as input (dict or str)

    Examples:
        >>> mask_sensitive_data({"api_key": "sk-1234567890abcdef"})
        {"api_key": "sk-***"}

        >>> mask_sensitive_data("Bearer abc123def456")
        "Bearer ***"

        >>> mask_sensitive_data('{"password": "secret123"}')
        '{"password": "***"}'
    """
    if isinstance(data, dict):
        return _mask_dict(data)
    elif isinstance(data, str):
        return _mask_string(data)
    else:
        # For other types (int, float, bool, None), return as-is
        return data


def _mask_dict(data: dict) -> dict:
    """
    Recursively mask sensitive fields in a dictionary.

    Args:
        data: Dictionary to mask

    Returns:
        New dictionary with masked sensitive values
    """
    masked = {}
    for key, value in data.items():
        if isinstance(value, dict):
            # Recursively mask nested dicts
            masked[key] = _mask_dict(value)
        elif isinstance(value, list):
            # Mask items in lists
            masked[key] = [
                _mask_dict(item) if isinstance(item, dict) else _mask_value(key, item)
                for item in value
            ]
        else:
            # Mask individual values based on key name or content
            masked[key] = _mask_value(key, value)
    return masked


def _mask_value(key: str, value: Any) -> Any:
    """
    Mask a single value if it contains sensitive data.

    Args:
        key: Field name (used to detect sensitive fields by name)
        value: Field value to check and potentially mask

    Returns:
        Masked value or original value if not sensitive
    """
    # Check if key indicates sensitive field
    sensitive_keys = {
        "password",
        "api_key",
        "apikey",
        "secret",
        "token",
        "authorization",
        "auth",
        "bearer",
        "api_token",
        "access_token",
        "refresh_token",
        "private_key",
        "secret_key",
    }

    if isinstance(key, str) and any(
        sensitive in key.lower() for sensitive in sensitive_keys
    ):
        return "***"

    # If value is string, apply regex masking
    if isinstance(value, str):
        return _mask_string(value)

    return value


def _mask_string(text: str) -> str:
    """
    Apply regex patterns to mask sensitive data in strings.

    Args:
        text: String to mask

    Returns:
        String with sensitive patterns masked
    """
    # Mask API keys (sk-, pk-, rk-, etc. followed by 20+ alphanumeric chars)
    text = re.sub(
        r"\b(sk-|pk-|rk-|api-|key-)[a-zA-Z0-9]{20,}\b",
        r"\1***",
        text,
        flags=re.IGNORECASE,
    )

    # Mask Bearer tokens
    text = re.sub(
        r"\bBearer\s+[a-zA-Z0-9\-._~+/]+=*\b",
        "Bearer ***",
        text,
        flags=re.IGNORECASE,
    )

    # Mask Basic auth (Base64 after "Basic ")
    text = re.sub(
        r"\bBasic\s+[a-zA-Z0-9+/]+=*\b", "Basic ***", text, flags=re.IGNORECASE
    )

    # Mask password fields in JSON-like strings
    text = re.sub(
        r'(["\']password["\']\s*:\s*["\'])[^"\']+(["\'])',
        r"\1***\2",
        text,
        flags=re.IGNORECASE,
    )

    # Mask AWS-style credentials
    text = re.sub(
        r"\bAKIA[0-9A-Z]{16}\b",
        "AKIA***",
        text,
    )

    # Mask generic secret patterns (40+ hex characters, common in tokens)
    text = re.sub(
        r"\b[a-f0-9]{40,}\b",
        "***",
        text,
    )

    return text


def mask_json_string(json_str: str) -> str:
    """
    Parse JSON string, mask sensitive fields, and return masked JSON string.

    Useful for masking JSON payloads in logs or API responses.

    Args:
        json_str: JSON string to mask

    Returns:
        Masked JSON string

    Raises:
        json.JSONDecodeError: If input is not valid JSON
    """
    try:
        data = json.loads(json_str)
        masked = mask_sensitive_data(data)
        return json.dumps(masked)
    except json.JSONDecodeError:
        # If not valid JSON, apply string masking
        return _mask_string(json_str)
