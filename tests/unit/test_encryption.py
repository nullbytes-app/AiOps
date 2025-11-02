"""Unit tests for encryption utilities.

Tests encryption/decryption functionality, error handling, and key management.
"""

import os
import pytest
from cryptography.fernet import Fernet

from src.utils.encryption import (
    encrypt,
    decrypt,
    EncryptionError,
    generate_encryption_key,
    is_encrypted,
)


@pytest.fixture
def valid_encryption_key():
    """Generate a valid encryption key for testing."""
    return Fernet.generate_key().decode()


@pytest.fixture
def setup_encryption_env(valid_encryption_key, monkeypatch):
    """Set up ENCRYPTION_KEY environment variable."""
    monkeypatch.setenv("ENCRYPTION_KEY", valid_encryption_key)
    return valid_encryption_key


class TestEncryptionBasics:
    """Test basic encryption/decryption functionality."""

    def test_encrypt_decrypt_roundtrip(self, setup_encryption_env):
        """Test that decrypt(encrypt(text)) == text."""
        plaintext = "my-secret-api-key-12345"
        encrypted = encrypt(plaintext)
        decrypted = decrypt(encrypted)

        assert decrypted == plaintext

    def test_encrypt_produces_different_output(self, setup_encryption_env):
        """Test that encrypt() produces different output each time (randomized)."""
        plaintext = "same-plaintext"
        encrypted1 = encrypt(plaintext)
        encrypted2 = encrypt(plaintext)

        # Fernet includes timestamp, so outputs should differ
        assert encrypted1 != encrypted2

        # But both should decrypt to the same value
        assert decrypt(encrypted1) == plaintext
        assert decrypt(encrypted2) == plaintext

    def test_encrypt_handles_special_characters(self, setup_encryption_env):
        """Test encryption of strings with special characters."""
        plaintext = "key!@#$%^&*()_+-=[]{}|;:',.<>?/~`"
        encrypted = encrypt(plaintext)
        decrypted = decrypt(encrypted)

        assert decrypted == plaintext

    def test_encrypt_handles_unicode(self, setup_encryption_env):
        """Test encryption of Unicode strings."""
        plaintext = "api_key_with_emoji_🔒_and_中文"
        encrypted = encrypt(plaintext)
        decrypted = decrypt(encrypted)

        assert decrypted == plaintext

    def test_encrypt_handles_long_strings(self, setup_encryption_env):
        """Test encryption of very long strings."""
        plaintext = "x" * 10000
        encrypted = encrypt(plaintext)
        decrypted = decrypt(encrypted)

        assert decrypted == plaintext


class TestEncryptionErrors:
    """Test error handling in encryption."""

    def test_decrypt_with_invalid_ciphertext(self, setup_encryption_env):
        """Test that decrypt() raises error for corrupted/invalid ciphertext."""
        with pytest.raises(EncryptionError, match="Failed to decrypt"):
            decrypt("this-is-not-valid-encrypted-data")

    def test_decrypt_with_wrong_key(self, valid_encryption_key, monkeypatch):
        """Test that decrypt fails when using wrong key."""
        # Setup with one key
        monkeypatch.setenv("ENCRYPTION_KEY", valid_encryption_key)
        plaintext = "secret"
        encrypted = encrypt(plaintext)

        # Setup with different key
        different_key = Fernet.generate_key().decode()
        monkeypatch.setenv("ENCRYPTION_KEY", different_key)

        # Decryption should fail
        with pytest.raises(EncryptionError, match="Failed to decrypt"):
            decrypt(encrypted)

    def test_encrypt_without_key(self, monkeypatch):
        """Test that encrypt() raises error when ENCRYPTION_KEY not set."""
        monkeypatch.delenv("ENCRYPTION_KEY", raising=False)

        with pytest.raises(EncryptionError, match="ENCRYPTION_KEY.*not set"):
            encrypt("plaintext")

    def test_decrypt_without_key(self, monkeypatch):
        """Test that decrypt() raises error when ENCRYPTION_KEY not set."""
        monkeypatch.delenv("ENCRYPTION_KEY", raising=False)

        with pytest.raises(EncryptionError, match="ENCRYPTION_KEY.*not set"):
            decrypt("ciphertext")

    def test_encrypt_with_invalid_key_format(self, monkeypatch):
        """Test that encrypt() raises error for invalid key format."""
        monkeypatch.setenv("ENCRYPTION_KEY", "not-a-valid-fernet-key")

        with pytest.raises(EncryptionError, match="Invalid ENCRYPTION_KEY"):
            encrypt("plaintext")

    def test_decrypt_empty_string(self, setup_encryption_env):
        """Test that decrypt() raises error for empty string."""
        with pytest.raises(EncryptionError):
            decrypt("")


class TestKeyGeneration:
    """Test encryption key generation."""

    def test_generate_encryption_key_returns_string(self):
        """Test that generate_encryption_key() returns a valid string."""
        key = generate_encryption_key()

        assert isinstance(key, str)
        assert len(key) > 0

    def test_generated_key_is_valid_fernet_key(self):
        """Test that generated key can be used for encryption."""
        key = generate_encryption_key()

        # Should be able to create Fernet with this key
        cipher = Fernet(key.encode())
        assert cipher is not None

    def test_generated_keys_are_unique(self):
        """Test that each generated key is unique."""
        key1 = generate_encryption_key()
        key2 = generate_encryption_key()

        assert key1 != key2

    def test_generated_key_encrypts_and_decrypts(self, monkeypatch):
        """Test full workflow with generated key."""
        key = generate_encryption_key()
        monkeypatch.setenv("ENCRYPTION_KEY", key)

        plaintext = "test-secret"
        encrypted = encrypt(plaintext)
        decrypted = decrypt(encrypted)

        assert decrypted == plaintext


class TestEncryptedDataDetection:
    """Test is_encrypted() heuristic function."""

    def test_is_encrypted_with_encrypted_data(self, setup_encryption_env):
        """Test is_encrypted() returns True for actual encrypted data."""
        plaintext = "secret-api-key"
        encrypted = encrypt(plaintext)

        assert is_encrypted(encrypted) is True

    def test_is_encrypted_with_plaintext(self, setup_encryption_env):
        """Test is_encrypted() returns False for plaintext."""
        plaintext = "just-a-regular-string"

        assert is_encrypted(plaintext) is False

    def test_is_encrypted_with_empty_string(self):
        """Test is_encrypted() handles empty strings."""
        assert is_encrypted("") is False

    def test_is_encrypted_with_none(self):
        """Test is_encrypted() handles None."""
        assert is_encrypted(None) is False

    def test_is_encrypted_with_short_string(self):
        """Test is_encrypted() handles very short strings."""
        assert is_encrypted("a") is False
        assert is_encrypted("ab") is False


class TestRealWorldScenarios:
    """Test real-world encryption scenarios."""

    def test_api_key_encryption(self, setup_encryption_env):
        """Test encryption of typical API keys."""
        api_keys = [
            "sk_live_abc123def456",
            "ghp_1234567890abcdefghijklmnopqrstuvwxyz",
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        ]

        for api_key in api_keys:
            encrypted = encrypt(api_key)
            decrypted = decrypt(encrypted)
            assert decrypted == api_key

    def test_webhook_secret_encryption(self, setup_encryption_env):
        """Test encryption of webhook secrets."""
        secrets = [
            "webhook_secret_value_xyz",
            "a" * 64,  # Common HMAC secret length
        ]

        for secret in secrets:
            encrypted = encrypt(secret)
            decrypted = decrypt(encrypted)
            assert decrypted == secret

    def test_database_field_simulation(self, setup_encryption_env):
        """Test storing encrypted values in database-like structure."""
        config = {
            "tenant_id": "tenant-123",
            "api_key_encrypted": encrypt("real-api-key"),
            "webhook_secret_encrypted": encrypt("real-secret"),
        }

        # Verify encrypted values are stored
        assert is_encrypted(config["api_key_encrypted"])
        assert is_encrypted(config["webhook_secret_encrypted"])

        # Verify decryption works
        api_key = decrypt(config["api_key_encrypted"])
        secret = decrypt(config["webhook_secret_encrypted"])

        assert api_key == "real-api-key"
        assert secret == "real-secret"
