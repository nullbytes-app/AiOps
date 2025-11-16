"""
Tenant Field Encryption Helpers.

This module provides Fernet symmetric encryption functions for sensitive tenant data:
- API keys
- Webhook secrets
- Other encrypted fields

Security:
- Encryption key stored in environment variable or Streamlit secrets
- Sensitive fields masked in display (show only last 4 characters)
- No plaintext credentials logged or displayed
"""

import os
from typing import Optional

import streamlit as st
from cryptography.fernet import Fernet


def get_fernet_cipher() -> Fernet:
    """
    Get Fernet cipher instance using encryption key from secrets.

    The encryption key is loaded from environment variable or Streamlit secrets.
    Key must be 32 URL-safe base64-encoded bytes generated with Fernet.generate_key().

    Returns:
        Fernet: Cipher instance for encryption/decryption operations

    Raises:
        ValueError: If encryption key is not set or invalid format

    Environment Variables:
        TENANT_ENCRYPTION_KEY: 32-byte URL-safe base64-encoded encryption key

    Example:
        >>> cipher = get_fernet_cipher()
        >>> encrypted = cipher.encrypt(b"secret_value")
    """
    # Try Streamlit secrets first, then fall back to environment variable
    key = None
    if hasattr(st, "secrets") and "TENANT_ENCRYPTION_KEY" in st.secrets:
        key = st.secrets["TENANT_ENCRYPTION_KEY"]
    else:
        key = os.getenv("TENANT_ENCRYPTION_KEY")

    if not key:
        raise ValueError(
            "TENANT_ENCRYPTION_KEY not found in environment or Streamlit secrets. "
            "Generate with: from cryptography.fernet import Fernet; Fernet.generate_key()"
        )

    # Ensure key is bytes
    if isinstance(key, str):
        key = key.encode()

    return Fernet(key)


def encrypt_field(plaintext: str) -> str:
    """
    Encrypt sensitive field value using Fernet symmetric encryption.

    Args:
        plaintext: The plaintext value to encrypt (e.g., API key, webhook secret)

    Returns:
        str: Base64-encoded ciphertext

    Raises:
        ValueError: If encryption key is unavailable

    Example:
        >>> encrypted_key = encrypt_field("my_api_key_12345")
        >>> print(encrypted_key)
        'gAAAAABf...'  # Base64-encoded ciphertext
    """
    cipher = get_fernet_cipher()
    ciphertext = cipher.encrypt(plaintext.encode())
    return ciphertext.decode()


def decrypt_field(ciphertext: str) -> str:
    """
    Decrypt sensitive field value using Fernet symmetric encryption.

    Args:
        ciphertext: The base64-encoded ciphertext to decrypt

    Returns:
        str: Decrypted plaintext value

    Raises:
        ValueError: If encryption key is unavailable
        cryptography.fernet.InvalidToken: If ciphertext is corrupted or key is wrong

    Example:
        >>> plaintext = decrypt_field("gAAAAABf...")
        >>> print(plaintext)
        'my_api_key_12345'
    """
    cipher = get_fernet_cipher()
    plaintext = cipher.decrypt(ciphertext.encode())
    return plaintext.decode()


def mask_sensitive_field(value: str, visible_chars: int = 4) -> str:
    """
    Mask sensitive value showing only last N characters.

    Used for displaying encrypted fields in UI without exposing full value.
    If value is shorter than visible_chars, fully masks it.

    Args:
        value: The value to mask (usually decrypted sensitive field)
        visible_chars: Number of trailing characters to show (default: 4)

    Returns:
        str: Masked value with format "****xyz123" (last 4 chars visible)

    Example:
        >>> mask_sensitive_field("my_api_key_12345", 4)
        '*************2345'
        >>> mask_sensitive_field("abc", 4)
        '***'
    """
    if len(value) <= visible_chars:
        return "*" * len(value)
    return "*" * (len(value) - visible_chars) + value[-visible_chars:]
