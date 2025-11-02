"""Encryption and decryption utilities using Fernet symmetric encryption.

Provides symmetric encryption for sensitive data like API keys and webhook secrets.
Uses cryptography.fernet which handles key rotation and timing attacks.

Environment Variables:
    ENCRYPTION_KEY: Base64-encoded Fernet key (required for encrypt/decrypt)
                   Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Reason:
    Fernet provides authenticated symmetric encryption - simple, secure, and sufficient for
    credentials at rest. Stored in Kubernetes secrets (K8s) and never committed to git.
"""

import os
import base64
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from loguru import logger


class EncryptionError(Exception):
    """Raised when encryption/decryption operations fail."""

    pass


def _get_cipher() -> Fernet:
    """Get or initialize Fernet cipher from environment.

    Returns:
        Fernet: Initialized cipher object

    Raises:
        EncryptionError: If ENCRYPTION_KEY not set or invalid format
    """
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise EncryptionError(
            "ENCRYPTION_KEY environment variable not set. "
            "Generate with: python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        )

    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, TypeError) as e:
        raise EncryptionError(f"Invalid ENCRYPTION_KEY format: {str(e)}")


def encrypt(plaintext: str) -> str:
    """Encrypt plaintext using Fernet symmetric encryption.

    Args:
        plaintext: String to encrypt (e.g., API key, webhook secret)

    Returns:
        str: Base64-encoded encrypted ciphertext

    Raises:
        EncryptionError: If encryption fails or key not available

    Example:
        >>> encrypted = encrypt("my-secret-api-key")
        >>> # encrypted is a base64 string safe for storage
    """
    try:
        cipher = _get_cipher()
        ciphertext = cipher.encrypt(plaintext.encode("utf-8"))
        return ciphertext.decode("utf-8")
    except EncryptionError:
        raise
    except Exception as e:
        raise EncryptionError(f"Encryption failed: {str(e)}")


def decrypt(ciphertext: str) -> str:
    """Decrypt Fernet ciphertext to plaintext.

    Args:
        ciphertext: Base64-encoded encrypted data (from encrypt())

    Returns:
        str: Decrypted plaintext

    Raises:
        EncryptionError: If decryption fails (corrupted data, wrong key, etc.)

    Example:
        >>> plaintext = decrypt(encrypted)
        >>> plaintext == "my-secret-api-key"
        True
    """
    try:
        cipher = _get_cipher()
        plaintext = cipher.decrypt(ciphertext.encode("utf-8"))
        return plaintext.decode("utf-8")
    except InvalidToken:
        raise EncryptionError(
            "Failed to decrypt - corrupted data or wrong encryption key. "
            "Verify ENCRYPTION_KEY matches the key used for encryption."
        )
    except EncryptionError:
        raise
    except Exception as e:
        raise EncryptionError(f"Decryption failed: {str(e)}")


def generate_encryption_key() -> str:
    """Generate a new Fernet encryption key.

    Use this to initialize ENCRYPTION_KEY for the first time.
    Store the output in environment variables or Kubernetes secrets.

    Returns:
        str: Base64-encoded Fernet key

    Example:
        >>> key = generate_encryption_key()
        >>> print(f"ENCRYPTION_KEY={key}")
        ENCRYPTION_KEY=...
    """
    key = Fernet.generate_key()
    return key.decode("utf-8")


def is_encrypted(value: str) -> bool:
    """Check if a string appears to be Fernet-encrypted.

    Provides a heuristic check - actual validation only happens during decryption.

    Args:
        value: String to check

    Returns:
        bool: True if value looks like encrypted data (starts with specific pattern)
    """
    if not value or not isinstance(value, str):
        return False

    try:
        # Fernet tokens are base64-encoded and contain version + timestamp + ciphertext
        # They typically start with 'gAAAAA' when base64-decoded
        decoded = base64.urlsafe_b64decode(value + "==")  # Add padding for safety
        return len(decoded) > 32  # Min size for Fernet token
    except Exception:
        return False
