"""
Integration tests for audit logging with correlation ID tracing.

Tests end-to-end correlation ID propagation from webhook receipt through
worker task completion, verifying audit logs at each stage include required fields.
"""

import uuid
from unittest.mock import patch, MagicMock

import pytest

from src.utils.logger import AuditLogger
from src.schemas.job import EnhancementJob


class TestCorrelationIdFlow:
    """Test correlation ID flow through the system."""

    def test_correlation_id_in_enhancement_job(self):
        """Test EnhancementJob includes and validates correlation_id."""
        correlation_id = str(uuid.uuid4())

        job = EnhancementJob(
            job_id=str(uuid.uuid4()),
            ticket_id="TKT-123",
            tenant_id="tenant-abc",
            description="Test ticket",
            priority="high",
            timestamp="2025-11-01T12:00:00Z",
            correlation_id=correlation_id,
        )

        # Verify correlation_id is preserved
        assert job.correlation_id == correlation_id
        assert len(job.correlation_id) == 36  # UUID format

    def test_correlation_id_serialization(self):
        """Test correlation_id serializes correctly to JSON."""
        correlation_id = str(uuid.uuid4())

        job = EnhancementJob(
            job_id=str(uuid.uuid4()),
            ticket_id="TKT-123",
            tenant_id="tenant-abc",
            description="Test ticket",
            priority="high",
            timestamp="2025-11-01T12:00:00Z",
            correlation_id=correlation_id,
        )

        job_json = job.model_dump_json()
        # Verify correlation_id is in the JSON
        assert correlation_id in job_json
        assert '"correlation_id"' in job_json

    def test_audit_logs_include_correlation_id(self):
        """Test audit log calls properly structure correlation_id."""
        correlation_id = str(uuid.uuid4())

        # Mock the logger to capture calls
        with patch("src.utils.logger.logger") as mock_logger:
            AuditLogger.audit_webhook_received(
                tenant_id="tenant-abc",
                ticket_id="TKT-123",
                correlation_id=correlation_id,
            )

            # Verify logger.info was called
            assert mock_logger.info.called
            call_args = mock_logger.info.call_args

            # Check extra dict includes correlation_id
            extra = call_args[1]["extra"]
            assert extra["correlation_id"] == correlation_id
            assert extra["tenant_id"] == "tenant-abc"
            assert extra["ticket_id"] == "TKT-123"

    def test_audit_webhook_received_structure(self):
        """Test webhook audit log has correct structure."""
        correlation_id = str(uuid.uuid4())

        with patch("src.utils.logger.logger") as mock_logger:
            AuditLogger.audit_webhook_received(
                tenant_id="tenant-abc",
                ticket_id="TKT-123",
                correlation_id=correlation_id,
            )

            call_args = mock_logger.info.call_args
            extra = call_args[1]["extra"]

            # Check required fields
            assert extra["operation"] == "webhook_received"
            assert extra["status"] == "received"
            assert extra["service"] == "api"

    def test_audit_enhancement_started_structure(self):
        """Test enhancement start audit log has correct structure."""
        correlation_id = str(uuid.uuid4())
        task_id = str(uuid.uuid4())

        with patch("src.utils.logger.logger") as mock_logger:
            AuditLogger.audit_enhancement_started(
                tenant_id="tenant-abc",
                ticket_id="TKT-123",
                correlation_id=correlation_id,
                task_id=task_id,
                worker_id="worker-01",
            )

            call_args = mock_logger.info.call_args
            extra = call_args[1]["extra"]

            # Check required fields
            assert extra["operation"] == "enhancement_started"
            assert extra["status"] == "started"
            assert extra["service"] == "worker"
            assert extra["task_id"] == task_id
            assert extra["worker_id"] == "worker-01"

    def test_audit_enhancement_completed_structure(self):
        """Test enhancement completion audit log has correct structure."""
        correlation_id = str(uuid.uuid4())
        duration_ms = 1234.5

        with patch("src.utils.logger.logger") as mock_logger:
            AuditLogger.audit_enhancement_completed(
                tenant_id="tenant-abc",
                ticket_id="TKT-123",
                correlation_id=correlation_id,
                duration_ms=duration_ms,
            )

            call_args = mock_logger.info.call_args
            extra = call_args[1]["extra"]

            # Check required fields
            assert extra["operation"] == "enhancement_completed"
            assert extra["status"] == "success"
            assert extra["duration_ms"] == duration_ms

    def test_audit_enhancement_failed_structure(self):
        """Test enhancement failure audit log has correct structure."""
        correlation_id = str(uuid.uuid4())

        with patch("src.utils.logger.logger") as mock_logger:
            AuditLogger.audit_enhancement_failed(
                tenant_id="tenant-abc",
                ticket_id="TKT-123",
                correlation_id=correlation_id,
                error_type="TimeoutError",
                error_message="Request timed out",
            )

            # Should use error level
            assert mock_logger.error.called
            call_args = mock_logger.error.call_args
            extra = call_args[1]["extra"]

            # Check required fields
            assert extra["operation"] == "enhancement_failed"
            assert extra["status"] == "failure"
            assert extra["error_type"] == "TimeoutError"
            assert extra["error_message"] == "Request timed out"

    def test_audit_api_call_structure(self):
        """Test API call audit log has correct structure."""
        correlation_id = str(uuid.uuid4())

        with patch("src.utils.logger.logger") as mock_logger:
            AuditLogger.audit_api_call(
                tenant_id="tenant-abc",
                ticket_id="TKT-123",
                correlation_id=correlation_id,
                endpoint="/api/tickets/TKT-123",
                method="GET",
                status_code=200,
            )

            call_args = mock_logger.info.call_args
            extra = call_args[1]["extra"]

            # Check required fields
            assert extra["operation"] == "api_call"
            assert extra["status"] == "success"
            assert extra["endpoint"] == "/api/tickets/TKT-123"
            assert extra["method"] == "GET"
            assert extra["status_code"] == 200

    def test_audit_api_retry_structure(self):
        """Test API retry audit log has correct structure."""
        correlation_id = str(uuid.uuid4())

        with patch("src.utils.logger.logger") as mock_logger:
            AuditLogger.audit_api_retry(
                tenant_id="tenant-abc",
                ticket_id="TKT-123",
                correlation_id=correlation_id,
                attempt_number=2,
                status_code=429,
            )

            # Should use warning level
            assert mock_logger.warning.called
            call_args = mock_logger.warning.call_args
            extra = call_args[1]["extra"]

            # Check required fields
            assert extra["operation"] == "api_retry"
            assert extra["status"] == "retrying"
            assert extra["attempt_number"] == 2
            assert extra["status_code"] == 429

    def test_audit_api_call_failed_structure(self):
        """Test API call failure audit log has correct structure."""
        correlation_id = str(uuid.uuid4())

        with patch("src.utils.logger.logger") as mock_logger:
            AuditLogger.audit_api_call_failed(
                tenant_id="tenant-abc",
                ticket_id="TKT-123",
                correlation_id=correlation_id,
                endpoint="/api/tickets",
                method="POST",
                final_status_code=500,
                error_message="Internal server error",
            )

            # Should use error level
            assert mock_logger.error.called
            call_args = mock_logger.error.call_args
            extra = call_args[1]["extra"]

            # Check required fields
            assert extra["operation"] == "api_call"
            assert extra["status"] == "failure"
            assert extra["endpoint"] == "/api/tickets"
            assert extra["method"] == "POST"
            assert extra["final_status_code"] == 500

    def test_correlation_id_consistency_across_operations(self):
        """Test same correlation_id is used across multiple audit operations."""
        correlation_id = str(uuid.uuid4())

        with patch("src.utils.logger.logger") as mock_logger:
            # Simulate webhook → job → task execution flow
            AuditLogger.audit_webhook_received(
                tenant_id="tenant-abc",
                ticket_id="TKT-123",
                correlation_id=correlation_id,
            )

            AuditLogger.audit_api_call(
                tenant_id="tenant-abc",
                ticket_id="TKT-123",
                correlation_id=correlation_id,
                endpoint="/queue",
                method="POST",
                status_code=200,
            )

            AuditLogger.audit_enhancement_started(
                tenant_id="tenant-abc",
                ticket_id="TKT-123",
                correlation_id=correlation_id,
                task_id=str(uuid.uuid4()),
                worker_id="worker-01",
            )

            AuditLogger.audit_enhancement_completed(
                tenant_id="tenant-abc",
                ticket_id="TKT-123",
                correlation_id=correlation_id,
                duration_ms=500,
            )

            # Verify all calls have same correlation_id
            assert mock_logger.info.call_count == 4
            for call in mock_logger.info.call_args_list:
                extra = call[1]["extra"]
                assert extra["correlation_id"] == correlation_id

    def test_correlation_id_uniqueness(self):
        """Test each generated correlation ID is unique."""
        ids = [str(uuid.uuid4()) for _ in range(10)]
        assert len(ids) == len(set(ids)), "Correlation IDs should be unique"
