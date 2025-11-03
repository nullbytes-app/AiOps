"""
Unit tests for secrets validation utilities.

Tests validate that required secrets are present, properly formatted, and validated
at application startup.
"""

import os
import pytest
from cryptography.fernet import Fernet

from src.config import is_kubernetes_env
from src.utils.secrets import validate_secrets


class TestValidateSecrets:
    """Test cases for the validate_secrets function."""

    def test_all_secrets_present_and_valid(self, monkeypatch):
        """Test: All secrets present and valid → passes without exception."""
        monkeypatch.setenv("AI_AGENTS_POSTGRES_PASSWORD", "test_secure_password_123")
        monkeypatch.setenv("AI_AGENTS_REDIS_PASSWORD", "redis_secure_pass_456")
        monkeypatch.setenv("AI_AGENTS_OPENAI_API_KEY", "sk-proj-test-api-key-123456789")
        
        # Generate a valid Fernet key
        fernet_key = Fernet.generate_key().decode()
        monkeypatch.setenv("AI_AGENTS_ENCRYPTION_KEY", fernet_key)
        
        # Should not raise any exception
        validate_secrets()

    def test_missing_postgres_password(self, monkeypatch):
        """Test: Missing POSTGRES_PASSWORD → raises EnvironmentError."""
        monkeypatch.delenv("AI_AGENTS_POSTGRES_PASSWORD", raising=False)
        monkeypatch.setenv("AI_AGENTS_REDIS_PASSWORD", "redis_secure_pass_456")
        monkeypatch.setenv("AI_AGENTS_OPENAI_API_KEY", "sk-proj-test-api-key")
        fernet_key = Fernet.generate_key().decode()
        monkeypatch.setenv("AI_AGENTS_ENCRYPTION_KEY", fernet_key)
        
        with pytest.raises(EnvironmentError) as exc_info:
            validate_secrets()
        assert "POSTGRES_PASSWORD" in str(exc_info.value)
        assert "Missing required secret" in str(exc_info.value)

    def test_postgres_password_too_short(self, monkeypatch):
        """Test: POSTGRES_PASSWORD < 12 chars → raises EnvironmentError."""
        monkeypatch.setenv("AI_AGENTS_POSTGRES_PASSWORD", "short")  # Only 5 chars
        monkeypatch.setenv("AI_AGENTS_REDIS_PASSWORD", "redis_secure_pass_456")
        monkeypatch.setenv("AI_AGENTS_OPENAI_API_KEY", "sk-proj-test-api-key")
        fernet_key = Fernet.generate_key().decode()
        monkeypatch.setenv("AI_AGENTS_ENCRYPTION_KEY", fernet_key)
        
        with pytest.raises(EnvironmentError) as exc_info:
            validate_secrets()
        assert "POSTGRES_PASSWORD" in str(exc_info.value)
        assert "too short" in str(exc_info.value)

    def test_missing_redis_password(self, monkeypatch):
        """Test: Missing REDIS_PASSWORD → raises EnvironmentError."""
        monkeypatch.setenv("AI_AGENTS_POSTGRES_PASSWORD", "test_secure_password_123")
        monkeypatch.delenv("AI_AGENTS_REDIS_PASSWORD", raising=False)
        monkeypatch.setenv("AI_AGENTS_OPENAI_API_KEY", "sk-proj-test-api-key")
        fernet_key = Fernet.generate_key().decode()
        monkeypatch.setenv("AI_AGENTS_ENCRYPTION_KEY", fernet_key)
        
        with pytest.raises(EnvironmentError) as exc_info:
            validate_secrets()
        assert "REDIS_PASSWORD" in str(exc_info.value)

    def test_redis_password_too_short(self, monkeypatch):
        """Test: REDIS_PASSWORD < 12 chars → raises EnvironmentError."""
        monkeypatch.setenv("AI_AGENTS_POSTGRES_PASSWORD", "test_secure_password_123")
        monkeypatch.setenv("AI_AGENTS_REDIS_PASSWORD", "short")  # Only 5 chars
        monkeypatch.setenv("AI_AGENTS_OPENAI_API_KEY", "sk-proj-test-api-key")
        fernet_key = Fernet.generate_key().decode()
        monkeypatch.setenv("AI_AGENTS_ENCRYPTION_KEY", fernet_key)
        
        with pytest.raises(EnvironmentError) as exc_info:
            validate_secrets()
        assert "REDIS_PASSWORD" in str(exc_info.value)

    def test_missing_openai_api_key(self, monkeypatch):
        """Test: Missing OPENAI_API_KEY → raises EnvironmentError."""
        monkeypatch.setenv("AI_AGENTS_POSTGRES_PASSWORD", "test_secure_password_123")
        monkeypatch.setenv("AI_AGENTS_REDIS_PASSWORD", "redis_secure_pass_456")
        monkeypatch.delenv("AI_AGENTS_OPENAI_API_KEY", raising=False)
        fernet_key = Fernet.generate_key().decode()
        monkeypatch.setenv("AI_AGENTS_ENCRYPTION_KEY", fernet_key)
        
        with pytest.raises(EnvironmentError) as exc_info:
            validate_secrets()
        assert "OPENAI_API_KEY" in str(exc_info.value)

    def test_openai_api_key_empty(self, monkeypatch):
        """Test: OPENAI_API_KEY empty string → raises EnvironmentError."""
        monkeypatch.setenv("AI_AGENTS_POSTGRES_PASSWORD", "test_secure_password_123")
        monkeypatch.setenv("AI_AGENTS_REDIS_PASSWORD", "redis_secure_pass_456")
        monkeypatch.setenv("AI_AGENTS_OPENAI_API_KEY", "")
        fernet_key = Fernet.generate_key().decode()
        monkeypatch.setenv("AI_AGENTS_ENCRYPTION_KEY", fernet_key)
        
        with pytest.raises(EnvironmentError) as exc_info:
            validate_secrets()
        assert "OPENAI_API_KEY" in str(exc_info.value)

    def test_openai_api_key_too_short(self, monkeypatch):
        """Test: OPENAI_API_KEY too short → raises EnvironmentError."""
        monkeypatch.setenv("AI_AGENTS_POSTGRES_PASSWORD", "test_secure_password_123")
        monkeypatch.setenv("AI_AGENTS_REDIS_PASSWORD", "redis_secure_pass_456")
        monkeypatch.setenv("AI_AGENTS_OPENAI_API_KEY", "sk-short")  # Only 8 chars
        fernet_key = Fernet.generate_key().decode()
        monkeypatch.setenv("AI_AGENTS_ENCRYPTION_KEY", fernet_key)
        
        with pytest.raises(EnvironmentError) as exc_info:
            validate_secrets()
        assert "OPENAI_API_KEY" in str(exc_info.value)

    def test_missing_encryption_key(self, monkeypatch):
        """Test: Missing ENCRYPTION_KEY → raises EnvironmentError."""
        monkeypatch.setenv("AI_AGENTS_POSTGRES_PASSWORD", "test_secure_password_123")
        monkeypatch.setenv("AI_AGENTS_REDIS_PASSWORD", "redis_secure_pass_456")
        monkeypatch.setenv("AI_AGENTS_OPENAI_API_KEY", "sk-proj-test-api-key")
        monkeypatch.delenv("AI_AGENTS_ENCRYPTION_KEY", raising=False)
        
        with pytest.raises(EnvironmentError) as exc_info:
            validate_secrets()
        assert "ENCRYPTION_KEY" in str(exc_info.value)

    def test_invalid_encryption_key(self, monkeypatch):
        """Test: Invalid ENCRYPTION_KEY format → raises EnvironmentError."""
        monkeypatch.setenv("AI_AGENTS_POSTGRES_PASSWORD", "test_secure_password_123")
        monkeypatch.setenv("AI_AGENTS_REDIS_PASSWORD", "redis_secure_pass_456")
        monkeypatch.setenv("AI_AGENTS_OPENAI_API_KEY", "sk-proj-test-api-key")
        monkeypatch.setenv("AI_AGENTS_ENCRYPTION_KEY", "not-a-valid-fernet-key")
        
        with pytest.raises(EnvironmentError) as exc_info:
            validate_secrets()
        assert "ENCRYPTION_KEY" in str(exc_info.value)
        assert "not a valid Fernet" in str(exc_info.value)

    def test_error_messages_include_secret_name(self, monkeypatch):
        """Test: Error messages are actionable and include secret name."""
        monkeypatch.setenv("AI_AGENTS_POSTGRES_PASSWORD", "short")
        monkeypatch.setenv("AI_AGENTS_REDIS_PASSWORD", "redis_secure_pass_456")
        monkeypatch.setenv("AI_AGENTS_OPENAI_API_KEY", "sk-proj-test-api-key")
        fernet_key = Fernet.generate_key().decode()
        monkeypatch.setenv("AI_AGENTS_ENCRYPTION_KEY", fernet_key)
        
        try:
            validate_secrets()
        except EnvironmentError as e:
            error_msg = str(e)
            # Verify error message includes requirements
            assert "POSTGRES_PASSWORD" in error_msg
            assert "12 characters" in error_msg or "minimum" in error_msg.lower()


class TestIsKubernetesEnv:
    """Test cases for the is_kubernetes_env detection function."""

    def test_kubernetes_env_detected(self, monkeypatch):
        """Test: KUBERNETES_SERVICE_HOST set → returns True."""
        monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "10.0.0.1")
        assert is_kubernetes_env() is True

    def test_kubernetes_env_not_detected(self, monkeypatch):
        """Test: KUBERNETES_SERVICE_HOST not set → returns False."""
        monkeypatch.delenv("KUBERNETES_SERVICE_HOST", raising=False)
        assert is_kubernetes_env() is False

    def test_kubernetes_env_empty_value(self, monkeypatch):
        """Test: KUBERNETES_SERVICE_HOST empty → returns False."""
        monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "")
        assert is_kubernetes_env() is False
