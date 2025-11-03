"""
Text sanitization utilities for input validation and XSS prevention.

Provides functions to sanitize user input by removing dangerous characters,
normalizing Unicode, and applying HTML entity encoding per OWASP best practices.
Implements defense-in-depth security layer for AC2 and AC5.
"""

import html
import re
import unicodedata
from typing import Optional

from src.utils.constants import DANGEROUS_CONTROL_CHARS_PATTERN, NULL_BYTE


def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize text input by removing dangerous characters and normalizing Unicode.

    Implements allowlist validation strategy per OWASP Input Validation Cheat Sheet.
    Removes null bytes, dangerous control characters, and normalizes Unicode to
    prevent injection attacks and ensure consistent text processing.

    Args:
        text: Input text to sanitize
        max_length: Optional maximum length to truncate to (None = no truncation)

    Returns:
        Sanitized text with dangerous characters removed and Unicode normalized

    Example:
        >>> sanitize_text("Hello\\x00World")
        'HelloWorld'
        >>> sanitize_text("Test\\x0BData\\x1F", max_length=5)
        'TestD'
    """
    if not text:
        return text

    # Remove null bytes (AC5: reject null bytes)
    sanitized = text.replace(NULL_BYTE, "")

    # Remove dangerous control characters except newline (\n) and tab (\t)
    # Pattern: [\x00-\x08\x0B\x0C\x0E-\x1F] excludes \n (0x0A) and \t (0x09)
    sanitized = re.sub(DANGEROUS_CONTROL_CHARS_PATTERN, "", sanitized)

    # Normalize Unicode to NFC form for consistent representation (AC5)
    # NFC = Canonical Decomposition followed by Canonical Composition
    # Ensures characters like é are consistently represented
    sanitized = unicodedata.normalize("NFC", sanitized)

    # Truncate to max length if specified (AC3)
    if max_length is not None and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized


def escape_html(text: str) -> str:
    """
    Escape HTML special characters to prevent XSS attacks.

    Converts dangerous HTML characters to their entity equivalents per OWASP XSS
    Prevention Cheat Sheet. Applied when returning content in API responses (AC5).

    Args:
        text: Input text that may contain HTML special characters

    Returns:
        Text with HTML characters escaped to entities

    Example:
        >>> escape_html("<script>alert(1)</script>")
        '&lt;script&gt;alert(1)&lt;/script&gt;'
        >>> escape_html("AT&T costs < $100")
        'AT&amp;T costs &lt; $100'
    """
    if not text:
        return text

    # Use Python stdlib html.escape() for safe HTML entity encoding
    # Escapes: < > & " ' to &lt; &gt; &amp; &quot; &#x27;
    return html.escape(text, quote=True)


def contains_dangerous_chars(text: str) -> bool:
    """
    Check if text contains dangerous characters that should be rejected.

    Used for validation at input boundaries to fail fast on obviously malicious input.

    Args:
        text: Input text to check for dangerous characters

    Returns:
        True if dangerous characters found, False otherwise

    Example:
        >>> contains_dangerous_chars("Normal text")
        False
        >>> contains_dangerous_chars("Malicious\\x00data")
        True
    """
    if not text:
        return False

    # Check for null bytes (AC5: null bytes rejected)
    if NULL_BYTE in text:
        return True

    # Check for dangerous control characters (except \n, \t)
    if re.search(DANGEROUS_CONTROL_CHARS_PATTERN, text):
        return True

    return False


def sanitize_for_logging(text: str, max_length: int = 200) -> str:
    """
    Sanitize text for safe logging by truncating and escaping special chars.

    Prevents log injection attacks and keeps logs readable.

    Args:
        text: Text to log
        max_length: Maximum length for log entry (default 200 chars)

    Returns:
        Sanitized text safe for logging

    Example:
        >>> sanitize_for_logging("Sensitive data" * 100)
        'Sensitive dataSensitive dataSensitive data... (truncated)'
    """
    if not text:
        return text

    # Remove dangerous characters
    sanitized = sanitize_text(text, max_length=max_length)

    # Add truncation indicator if text was cut
    if len(text) > max_length:
        sanitized = sanitized + "... (truncated)"

    return sanitized
