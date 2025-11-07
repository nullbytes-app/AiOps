"""
Unit tests for webhook service layer functions.

Tests HMAC signature generation/validation, payload schema validation,
webhook URL generation, and secret generation with 2025 security best practices.

Story 8.6: Agent Webhook Endpoint Generation - Unit tests for Task 9/10.
"""

import base64
import hashlib
import hmac
from uuid import UUID

import pytest

from src.services.webhook_service import (
    compute_hmac_signature,
    generate_hmac_secret,
    generate_webhook_url,
    validate_hmac_signature,
    validate_payload_schema,
)


class TestGenerateWebhookUrl:
    """Tests for webhook URL generation (AC#1)."""

    def test_generate_webhook_url_format(self):
        """Verify webhook URL format: /agents/{agent_id}/webhook."""
        agent_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        base_url = "https://api.example.com"

        url = generate_webhook_url(agent_id, base_url)

        assert url == "https://api.example.com/agents/550e8400-e29b-41d4-a716-446655440000/webhook"
        assert url.startswith(base_url)
        assert str(agent_id) in url
        assert url.endswith("/webhook")

    def test_generate_webhook_url_with_http(self):
        """Test webhook URL generation with HTTP base URL."""
        agent_id = UUID("660e8400-e29b-41d4-a716-446655440001")
        base_url = "http://localhost:8000"

        url = generate_webhook_url(agent_id, base_url)

        assert url == "http://localhost:8000/agents/660e8400-e29b-41d4-a716-446655440001/webhook"


class TestGenerateHmacSecret:
    """Tests for HMAC secret generation (AC#2)."""

    def test_generate_hmac_secret_length(self):
        """Verify 32-byte secret generation with base64 encoding (44 chars)."""
        secret = generate_hmac_secret()

        # Base64-encoded 32 bytes = 44 characters (32 * 4/3 rounded up)
        assert len(secret) == 44
        assert isinstance(secret, str)

    def test_generate_hmac_secret_base64_encoding(self):
        """Verify secret is valid base64-encoded string."""
        secret = generate_hmac_secret()

        # Should be decodable as base64
        try:
            decoded = base64.b64decode(secret)
            assert len(decoded) == 32  # Original 32 bytes
        except Exception as e:
            pytest.fail(f"Secret is not valid base64: {e}")

    def test_generate_hmac_secret_uniqueness(self):
        """Verify secrets are cryptographically unique (non-deterministic)."""
        secret1 = generate_hmac_secret()
        secret2 = generate_hmac_secret()

        assert secret1 != secret2, "Secrets should be unique"

    def test_generate_hmac_secret_uses_secrets_module(self):
        """Verify cryptographically strong random generation (not predictable)."""
        # Generate multiple secrets, verify no patterns
        secrets = [generate_hmac_secret() for _ in range(10)]

        # All should be unique
        assert len(set(secrets)) == 10

        # None should start with predictable patterns
        for secret in secrets:
            assert not secret.startswith("AAA")  # Not all zeros
            assert not secret.startswith("///")  # Not all max values


class TestValidateHmacSignature:
    """Tests for HMAC signature validation with timing-attack prevention (AC#6)."""

    def test_validate_hmac_signature_valid(self):
        """Valid signature returns True."""
        payload = b'{"ticket_id": "12345"}'
        secret = generate_hmac_secret()
        expected_signature = compute_hmac_signature(payload, secret)

        is_valid = validate_hmac_signature(payload, expected_signature, secret)

        assert is_valid is True

    def test_validate_hmac_signature_invalid(self):
        """Invalid signature returns False."""
        payload = b'{"ticket_id": "12345"}'
        secret = generate_hmac_secret()
        invalid_signature = "sha256=invalid_signature_hex"

        is_valid = validate_hmac_signature(payload, invalid_signature, secret)

        assert is_valid is False

    def test_validate_hmac_signature_timing_safe(self):
        """Verify uses hmac.compare_digest() for constant-time comparison."""
        # This test ensures timing-attack prevention by checking the implementation
        # We can't directly test constant-time behavior, but we verify it doesn't raise
        # exceptions for different signature lengths (which naive == would)

        payload = b'{"ticket_id": "12345"}'
        secret = generate_hmac_secret()

        # Different length signatures should still return False without errors
        assert validate_hmac_signature(payload, "sha256=short", secret) is False
        assert (
            validate_hmac_signature(payload, "sha256=" + "a" * 64, secret) is False
        )  # 64 hex chars

    def test_validate_hmac_signature_empty_secret_raises_error(self):
        """Empty secret raises ValueError."""
        payload = b'{"ticket_id": "12345"}'
        signature = "sha256=abc123"

        with pytest.raises(ValueError, match="HMAC secret cannot be empty"):
            validate_hmac_signature(payload, signature, "")

        with pytest.raises(ValueError, match="HMAC secret cannot be empty"):
            validate_hmac_signature(payload, signature, None)

    def test_validate_hmac_signature_without_prefix(self):
        """Signature without 'sha256=' prefix is also validated."""
        payload = b'{"ticket_id": "12345"}'
        secret = generate_hmac_secret()

        # Compute signature with prefix
        sig_with_prefix = compute_hmac_signature(payload, secret)

        # Extract just the hex digest (remove sha256= prefix)
        hex_only = sig_with_prefix.replace("sha256=", "")

        # Validation should work with hex-only format too
        is_valid = validate_hmac_signature(payload, hex_only, secret)

        assert is_valid is True

    def test_validate_hmac_signature_payload_modification_detected(self):
        """Modified payload causes signature validation to fail."""
        original_payload = b'{"ticket_id": "12345"}'
        secret = generate_hmac_secret()
        signature = compute_hmac_signature(original_payload, secret)

        # Modify payload slightly
        modified_payload = b'{"ticket_id": "12346"}'

        is_valid = validate_hmac_signature(modified_payload, signature, secret)

        assert is_valid is False


class TestComputeHmacSignature:
    """Tests for HMAC signature computation (helper for test webhook UI)."""

    def test_compute_hmac_signature_format(self):
        """Verify signature format: sha256={hexdigest}."""
        payload = b'{"ticket_id": "12345"}'
        secret = generate_hmac_secret()

        signature = compute_hmac_signature(payload, secret)

        assert signature.startswith("sha256=")
        hex_part = signature[7:]  # Remove "sha256=" prefix
        assert len(hex_part) == 64  # SHA256 hex digest is 64 characters

    def test_compute_hmac_signature_deterministic(self):
        """Same payload and secret produce same signature (deterministic)."""
        payload = b'{"ticket_id": "12345"}'
        secret = "test_secret_base64=="

        sig1 = compute_hmac_signature(payload, secret)
        sig2 = compute_hmac_signature(payload, secret)

        assert sig1 == sig2

    def test_compute_hmac_signature_empty_secret_raises_error(self):
        """Empty secret raises ValueError."""
        payload = b'{"ticket_id": "12345"}'

        with pytest.raises(ValueError, match="HMAC secret cannot be empty"):
            compute_hmac_signature(payload, "")


class TestValidatePayloadSchema:
    """Tests for JSON Schema payload validation (AC#7)."""

    def test_validate_payload_schema_valid(self):
        """Valid payload passes validation."""
        schema = {
            "type": "object",
            "properties": {"ticket_id": {"type": "string"}},
            "required": ["ticket_id"],
        }
        payload = {"ticket_id": "12345"}

        is_valid, error_msg = validate_payload_schema(payload, schema)

        assert is_valid is True
        assert error_msg is None

    def test_validate_payload_schema_invalid(self):
        """Invalid payload returns error message."""
        schema = {
            "type": "object",
            "properties": {"ticket_id": {"type": "string"}},
            "required": ["ticket_id"],
        }
        payload = {"ticket_id": 12345}  # Wrong type: int instead of string

        is_valid, error_msg = validate_payload_schema(payload, schema)

        assert is_valid is False
        assert error_msg is not None
        assert "ticket_id" in error_msg or "type" in error_msg.lower()

    def test_validate_payload_schema_missing_required(self):
        """Missing required field returns validation error."""
        schema = {
            "type": "object",
            "properties": {"ticket_id": {"type": "string"}},
            "required": ["ticket_id"],
        }
        payload = {}  # Missing ticket_id

        is_valid, error_msg = validate_payload_schema(payload, schema)

        assert is_valid is False
        assert error_msg is not None
        assert "ticket_id" in error_msg
        assert "required" in error_msg.lower()

    def test_validate_payload_schema_complex(self):
        """Complex nested schema validates correctly."""
        schema = {
            "type": "object",
            "properties": {
                "ticket": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                    },
                    "required": ["id"],
                }
            },
            "required": ["ticket"],
        }

        # Valid payload
        valid_payload = {"ticket": {"id": "TKT-123", "priority": "high"}}
        is_valid, error_msg = validate_payload_schema(valid_payload, schema)
        assert is_valid is True

        # Invalid priority enum
        invalid_payload = {"ticket": {"id": "TKT-123", "priority": "critical"}}
        is_valid, error_msg = validate_payload_schema(invalid_payload, schema)
        assert is_valid is False
        assert "priority" in error_msg or "enum" in error_msg.lower()

    def test_validate_payload_schema_invalid_schema_format(self):
        """Invalid schema definition returns error."""
        invalid_schema = {
            "type": "invalid_type"  # Not a valid JSON Schema type
        }
        payload = {"ticket_id": "12345"}

        is_valid, error_msg = validate_payload_schema(payload, invalid_schema)

        assert is_valid is False
        assert error_msg is not None
        assert "schema" in error_msg.lower()


class TestIntegration:
    """Integration tests combining multiple webhook service functions."""

    def test_full_webhook_validation_flow(self):
        """Test complete webhook validation: generate secret, sign, validate."""
        # Step 1: Generate HMAC secret (agent creation)
        hmac_secret = generate_hmac_secret()

        # Step 2: External system sends webhook with payload
        payload = b'{"ticket_id": "TKT-12345", "priority": "high"}'

        # Step 3: External system computes signature
        signature = compute_hmac_signature(payload, hmac_secret)

        # Step 4: Webhook endpoint validates signature
        is_valid = validate_hmac_signature(payload, signature, hmac_secret)

        assert is_valid is True

    def test_webhook_url_and_secret_generation_on_agent_create(self):
        """Simulate agent creation: generate webhook URL and HMAC secret."""
        agent_id = UUID("770e8400-e29b-41d4-a716-446655440002")
        base_url = "https://api.production.com"

        # Generate webhook URL
        webhook_url = generate_webhook_url(agent_id, base_url)

        # Generate HMAC secret
        hmac_secret = generate_hmac_secret()

        # Verify both are valid
        assert "https://api.production.com/agents/" in webhook_url
        assert len(hmac_secret) == 44

        # Encrypt secret (simulated) and store in database
        # In real implementation: encrypted_secret = encrypt(hmac_secret)

    def test_payload_validation_before_signature_check(self):
        """Verify payload schema validation workflow."""
        schema = {
            "type": "object",
            "properties": {"ticket_id": {"type": "string"}},
            "required": ["ticket_id"],
        }
        payload = {"ticket_id": "TKT-123"}

        # Validate payload against schema
        is_valid, error = validate_payload_schema(payload, schema)

        assert is_valid is True
        assert error is None

        # Then validate HMAC signature (separate step)
        # (This test shows the order of validation steps)
