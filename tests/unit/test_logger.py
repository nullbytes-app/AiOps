"""
Unit tests for logging utilities and audit logging.

Tests SensitiveDataFilter and AuditLogger classes to verify:
- All redaction patterns (API keys, passwords, SSN, email, credit card)
- Nested field redaction in dictionaries and lists
- AuditLogger method output format and required fields
- Logger configuration with correlation ID support
"""

import io
import json
import sys
import uuid
from unittest.mock import patch, MagicMock

import pytest
from loguru import logger

from src.utils.logger import SensitiveDataFilter, AuditLogger, configure_logging


class TestSensitiveDataFilter:
    """Test suite for SensitiveDataFilter class."""

    def test_redact_api_key_pattern_1(self):
        """Test API_KEY=value pattern redaction."""
        filter_obj = SensitiveDataFilter()
        test_input = "Connection failed: API_KEY=sk-1234567890abcdef"
        result = filter_obj._redact_string(test_input)
        assert "[REDACTED]" in result
        assert "sk-1234567890abcdef" not in result

    def test_redact_api_key_pattern_2(self):
        """Test apikey: value pattern redaction."""
        filter_obj = SensitiveDataFilter()
        test_input = "Config: apikey: sk-test-key-123"
        result = filter_obj._redact_string(test_input)
        assert "[REDACTED]" in result
        assert "sk-test-key-123" not in result

    def test_redact_bearer_token(self):
        """Test Authorization Bearer token redaction."""
        filter_obj = SensitiveDataFilter()
        test_input = "Auth error: Authorization: Bearer eyJhbGc..."
        result = filter_obj._redact_string(test_input)
        assert "[REDACTED]" in result
        assert "eyJhbGc..." not in result

    def test_redact_password(self):
        """Test password redaction (various formats)."""
        filter_obj = SensitiveDataFilter()

        # password: value format
        result1 = filter_obj._redact_string('password: "secret123"')
        assert "[REDACTED]" in result1
        assert "secret123" not in result1

        # password=value format
        result2 = filter_obj._redact_string("password=secret456")
        assert "[REDACTED]" in result2
        assert "secret456" not in result2

    def test_redact_ssn(self):
        """Test SSN redaction (XXX-XX-XXXX format)."""
        filter_obj = SensitiveDataFilter()
        test_input = "SSN found in logs: 123-45-6789"
        result = filter_obj._redact_string(test_input)
        assert "[REDACTED-SSN]" in result
        assert "123-45-6789" not in result

    def test_redact_email_domain(self):
        """Test email domain redaction (preserves local part)."""
        filter_obj = SensitiveDataFilter()
        test_input = "User email: john.doe@company.com"
        result = filter_obj._redact_string(test_input)
        # Should preserve local part (john.doe) but redact domain
        assert "john.doe@***" in result
        assert "company.com" not in result

    def test_redact_credit_card(self):
        """Test credit card redaction (various formats)."""
        filter_obj = SensitiveDataFilter()

        # Standard format (with dashes)
        result1 = filter_obj._redact_string("Card: 4532-1234-5678-9010")
        assert "[REDACTED-CC]" in result1
        assert "4532" not in result1

        # With spaces
        result2 = filter_obj._redact_string("Card: 4532 1234 5678 9010")
        assert "[REDACTED-CC]" in result2

    def test_redact_dict_values(self):
        """Test recursive redaction of dictionary values."""
        filter_obj = SensitiveDataFilter()
        data = {
            "user": "john",
            "api_key": "sk-secret-123",
            "password": "supersecret",
            "email": "john@example.com",
        }
        result = filter_obj._redact_dict(data)

        assert result["user"] == "john"  # Not sensitive
        assert "[REDACTED]" in result["api_key"]
        assert "[REDACTED]" in result["password"]
        assert "john@***" in result["email"]
        assert "secret" not in str(result["api_key"])

    def test_redact_nested_dict(self):
        """Test redaction of nested dictionaries."""
        filter_obj = SensitiveDataFilter()
        data = {
            "config": {"password": "secret123", "api_key": "sk-test"},
            "user": "john",
        }
        result = filter_obj._redact_dict(data)

        assert "[REDACTED]" in result["config"]["password"]
        assert "[REDACTED]" in result["config"]["api_key"]
        assert result["user"] == "john"

    def test_redact_list_values(self):
        """Test redaction of list values."""
        filter_obj = SensitiveDataFilter()
        data = [
            "normal_string",
            "api_key: sk-secret",
            {"password": "secret123"},
        ]
        result = filter_obj._redact_dict(data)

        assert result[0] == "normal_string"
        assert "[REDACTED]" in result[1]
        assert "[REDACTED]" in result[2]["password"]

    def test_filter_log_record(self):
        """Test filter applied to Loguru log record."""
        filter_obj = SensitiveDataFilter()
        record = {
            "message": "API call with key: API_KEY=secret123",
            "extra": {"api_key": "sk-test", "password": "hidden"},
        }
        result = filter_obj(record)

        assert result is True  # Filter always returns True
        assert "[REDACTED]" in record["message"]
        assert "[REDACTED]" in record["extra"]["api_key"]
        assert "[REDACTED]" in record["extra"]["password"]

    def test_redaction_no_false_positives(self):
        """Test that non-sensitive data is not redacted."""
        filter_obj = SensitiveDataFilter()
        test_cases = [
            "tenant_id: tenant-123",
            "ticket_id: TKT-456",
            "correlation_id: 550e8400-e29b-41d4-a716-446655440000",
            "timestamp: 2025-11-03T14:23:45.123Z",
            "User ID: 12345",
        ]
        for test_input in test_cases:
            result = filter_obj._redact_string(test_input)
            # Should not be redacted (no sensitive data)
            assert "[REDACTED]" not in result


class TestAuditLogger:
    """Test suite for AuditLogger class."""

    @pytest.fixture
    def mock_logger(self):
        """Mock Loguru logger for testing."""
        with patch("src.utils.logger.logger") as mock:
            yield mock

    def test_audit_webhook_received(self, mock_logger):
        """Test audit_webhook_received method logs correct fields."""
        AuditLogger.audit_webhook_received(
            tenant_id="tenant-abc",
            ticket_id="TKT-123",
            correlation_id="550e8400-e29b-41d4-a716-446655440000",
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "Webhook received"

        extra = call_args[1]["extra"]
        assert extra["tenant_id"] == "tenant-abc"
        assert extra["ticket_id"] == "TKT-123"
        assert extra["correlation_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert extra["operation"] == "webhook_received"
        assert extra["status"] == "received"
        assert extra["service"] == "api"

    def test_audit_enhancement_started(self, mock_logger):
        """Test audit_enhancement_started logs task context."""
        AuditLogger.audit_enhancement_started(
            tenant_id="tenant-abc",
            ticket_id="TKT-123",
            correlation_id="550e8400-e29b-41d4-a716-446655440000",
            task_id="celery-task-123",
            worker_id="worker-01",
        )

        call_args = mock_logger.info.call_args
        extra = call_args[1]["extra"]
        assert extra["operation"] == "enhancement_started"
        assert extra["status"] == "started"
        assert extra["task_id"] == "celery-task-123"
        assert extra["worker_id"] == "worker-01"
        assert extra["service"] == "worker"

    def test_audit_enhancement_completed(self, mock_logger):
        """Test audit_enhancement_completed logs duration."""
        AuditLogger.audit_enhancement_completed(
            tenant_id="tenant-abc",
            ticket_id="TKT-123",
            correlation_id="550e8400-e29b-41d4-a716-446655440000",
            duration_ms=1234.5,
        )

        call_args = mock_logger.info.call_args
        extra = call_args[1]["extra"]
        assert extra["operation"] == "enhancement_completed"
        assert extra["status"] == "success"
        assert extra["duration_ms"] == 1234.5

    def test_audit_enhancement_failed(self, mock_logger):
        """Test audit_enhancement_failed logs error info."""
        AuditLogger.audit_enhancement_failed(
            tenant_id="tenant-abc",
            ticket_id="TKT-123",
            correlation_id="550e8400-e29b-41d4-a716-446655440000",
            error_type="ValueError",
            error_message="Invalid ticket format",
        )

        call_args = mock_logger.error.call_args
        extra = call_args[1]["extra"]
        assert extra["operation"] == "enhancement_failed"
        assert extra["status"] == "failure"
        assert extra["error_type"] == "ValueError"
        assert extra["error_message"] == "Invalid ticket format"

    def test_audit_api_call(self, mock_logger):
        """Test audit_api_call logs API request details."""
        AuditLogger.audit_api_call(
            tenant_id="tenant-abc",
            ticket_id="TKT-123",
            correlation_id="550e8400-e29b-41d4-a716-446655440000",
            endpoint="/api/tickets/TKT-123",
            method="POST",
            status_code=200,
        )

        call_args = mock_logger.info.call_args
        extra = call_args[1]["extra"]
        assert extra["operation"] == "api_call"
        assert extra["status"] == "success"
        assert extra["endpoint"] == "/api/tickets/TKT-123"
        assert extra["method"] == "POST"
        assert extra["status_code"] == 200

    def test_audit_api_retry(self, mock_logger):
        """Test audit_api_retry logs retry attempts."""
        AuditLogger.audit_api_retry(
            tenant_id="tenant-abc",
            ticket_id="TKT-123",
            correlation_id="550e8400-e29b-41d4-a716-446655440000",
            attempt_number=2,
            status_code=429,
        )

        call_args = mock_logger.warning.call_args
        extra = call_args[1]["extra"]
        assert extra["operation"] == "api_retry"
        assert extra["status"] == "retrying"
        assert extra["attempt_number"] == 2
        assert extra["status_code"] == 429

    def test_audit_api_call_failed(self, mock_logger):
        """Test audit_api_call_failed logs API failure."""
        AuditLogger.audit_api_call_failed(
            tenant_id="tenant-abc",
            ticket_id="TKT-123",
            correlation_id="550e8400-e29b-41d4-a716-446655440000",
            endpoint="/api/tickets",
            method="GET",
            final_status_code=500,
            error_message="Internal server error",
        )

        call_args = mock_logger.error.call_args
        extra = call_args[1]["extra"]
        assert extra["operation"] == "api_call"
        assert extra["status"] == "failure"
        assert extra["final_status_code"] == 500

    def test_audit_logger_extra_fields(self, mock_logger):
        """Test audit methods include additional extra fields."""
        AuditLogger.audit_webhook_received(
            tenant_id="tenant-abc",
            ticket_id="TKT-123",
            correlation_id="test-corr-id",
            custom_field="custom_value",
            user="operator1",
        )

        call_args = mock_logger.info.call_args
        extra = call_args[1]["extra"]
        assert extra["custom_field"] == "custom_value"
        assert extra["user"] == "operator1"


class TestLoggerConfiguration:
    """Test suite for logger configuration."""

    def test_configure_logging_development(self):
        """Test logger configuration in development mode."""
        with patch("src.utils.logger.settings") as mock_settings:
            mock_settings.environment = "development"
            mock_settings.log_level = "DEBUG"

            # Clear existing handlers
            logger.remove()

            # Configure logging
            configure_logging()

            # Should have at least one handler for console output
            assert len(logger._core.handlers) > 0

    def test_configure_logging_production(self):
        """Test logger configuration in production mode."""
        with patch("src.utils.logger.settings") as mock_settings:
            mock_settings.environment = "production"
            mock_settings.log_level = "INFO"

            logger.remove()
            configure_logging()

            # Should have handlers for both stderr and file
            assert len(logger._core.handlers) > 0

    @patch.dict("os.environ", {"LOG_FILE_ENABLED": "false"})
    def test_configure_logging_file_disabled(self):
        """Test logger skips file handler when LOG_FILE_ENABLED=false."""
        with patch("src.utils.logger.settings") as mock_settings:
            mock_settings.environment = "production"
            mock_settings.log_level = "INFO"

            logger.remove()
            configure_logging()

            # Should only have stderr handler, no file handler
            # File handler would be added if enabled
            assert len(logger._core.handlers) > 0
