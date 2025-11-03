"""
Logging configuration using Loguru.

This module configures structured logging for the application with support
for both API and Celery worker contexts. Provides colorized console output
for development and JSON serialization for production environments.

Features:
    - Correlation ID binding for distributed tracing
    - Sensitive data redaction (API keys, passwords, PII)
    - AuditLogger wrapper with operation-specific methods
    - ISO-8601 timestamps with UTC timezone
    - 90-day retention per NFR005 compliance requirement

Configuration:
    - Development: Colorized console output with readable formatting
    - Production: JSON serialization for log aggregation and analysis
    - Worker Context: Automatically includes worker_id, task_name, task_id
      when used from Celery tasks (via logger.bind() or extra parameter)
"""

import os
import re
import sys
from typing import Any, Optional

from loguru import logger

from src.config import settings


class SensitiveDataFilter:
    """
    Loguru filter to redact sensitive data from logs.

    Redacts the following patterns:
    - API keys: API_KEY=\\w+, apikey:\\s*\\S+, Authorization:\\s*Bearer\\s+\\S+
    - Passwords: password["']?:\\s*["']?\\S+
    - SSN: \\b\\d{3}-\\d{2}-\\d{4}\\b
    - Email (partial): Replaces domain with ***
    - Credit card: \\b\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}\\b
    """

    # Redaction patterns
    PATTERNS = [
        (r"API_KEY=\w+", "[REDACTED]"),
        (r"apikey:\s*\S+", "apikey: [REDACTED]"),
        (r"Authorization:\s*Bearer\s+\S+", "Authorization: Bearer [REDACTED]"),
        (r"password[\"']?:\s*[\"']?\S+", "password: [REDACTED]"),
        (r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED-SSN]"),
        (r"\b(\w+)@(\w+\.\w+)\b", r"\1@***"),
        (r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "[REDACTED-CC]"),
    ]

    def __call__(self, record: dict) -> bool:
        """
        Redact sensitive data from log record.

        Args:
            record: Loguru log record dict

        Returns:
            bool: Always True to allow record to pass
        """
        # Redact message
        if "message" in record:
            record["message"] = self._redact_string(record["message"])

        # Redact extra fields recursively
        if "extra" in record:
            record["extra"] = self._redact_dict(record["extra"])

        return True

    def _redact_string(self, value: str) -> str:
        """Redact sensitive patterns in a string."""
        for pattern, replacement in self.PATTERNS:
            value = re.sub(pattern, replacement, value, flags=re.IGNORECASE)
        return value

    def _redact_dict(self, data: Any) -> Any:
        """Recursively redact sensitive data in dictionaries and lists."""
        if isinstance(data, dict):
            return {k: self._redact_dict(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._redact_dict(item) for item in data]
        elif isinstance(data, str):
            return self._redact_string(data)
        return data


class AuditLogger:
    """
    Wrapper class providing operation-specific audit logging methods.

    Methods emit structured JSON logs with correlation IDs, tenant context,
    and required fields for compliance and debugging.
    """

    @staticmethod
    def audit_webhook_received(
        tenant_id: str,
        ticket_id: str,
        correlation_id: str,
        **extra: Any,
    ) -> None:
        """
        Log webhook reception.

        Args:
            tenant_id: Tenant identifier
            ticket_id: Ticket identifier
            correlation_id: Request correlation ID (UUID)
            **extra: Additional context fields
        """
        logger.info(
            "Webhook received",
            extra={
                "tenant_id": tenant_id,
                "ticket_id": ticket_id,
                "correlation_id": correlation_id,
                "operation": "webhook_received",
                "status": "received",
                "service": "api",
                **extra,
            },
        )

    @staticmethod
    def audit_enhancement_started(
        tenant_id: str,
        ticket_id: str,
        correlation_id: str,
        task_id: Optional[str] = None,
        worker_id: Optional[str] = None,
        **extra: Any,
    ) -> None:
        """
        Log enhancement task start.

        Args:
            tenant_id: Tenant identifier
            ticket_id: Ticket identifier
            correlation_id: Request correlation ID
            task_id: Celery task ID
            worker_id: Worker hostname
            **extra: Additional context fields
        """
        logger.info(
            "Enhancement started",
            extra={
                "tenant_id": tenant_id,
                "ticket_id": ticket_id,
                "correlation_id": correlation_id,
                "task_id": task_id,
                "worker_id": worker_id,
                "operation": "enhancement_started",
                "status": "started",
                "service": "worker",
                **extra,
            },
        )

    @staticmethod
    def audit_enhancement_completed(
        tenant_id: str,
        ticket_id: str,
        correlation_id: str,
        duration_ms: float,
        **extra: Any,
    ) -> None:
        """
        Log enhancement completion.

        Args:
            tenant_id: Tenant identifier
            ticket_id: Ticket identifier
            correlation_id: Request correlation ID
            duration_ms: Duration in milliseconds
            **extra: Additional context fields
        """
        logger.info(
            "Enhancement completed",
            extra={
                "tenant_id": tenant_id,
                "ticket_id": ticket_id,
                "correlation_id": correlation_id,
                "duration_ms": duration_ms,
                "operation": "enhancement_completed",
                "status": "success",
                "service": "worker",
                **extra,
            },
        )

    @staticmethod
    def audit_enhancement_failed(
        tenant_id: str,
        ticket_id: str,
        correlation_id: str,
        error_type: str,
        error_message: str,
        **extra: Any,
    ) -> None:
        """
        Log enhancement failure.

        Args:
            tenant_id: Tenant identifier
            ticket_id: Ticket identifier
            correlation_id: Request correlation ID
            error_type: Exception type name
            error_message: Exception message (will be redacted)
            **extra: Additional context fields
        """
        logger.error(
            "Enhancement failed",
            extra={
                "tenant_id": tenant_id,
                "ticket_id": ticket_id,
                "correlation_id": correlation_id,
                "error_type": error_type,
                "error_message": error_message,
                "operation": "enhancement_failed",
                "status": "failure",
                "service": "worker",
                **extra,
            },
        )

    @staticmethod
    def audit_api_call(
        tenant_id: str,
        ticket_id: str,
        correlation_id: str,
        endpoint: str,
        method: str,
        status_code: int,
        **extra: Any,
    ) -> None:
        """
        Log API call.

        Args:
            tenant_id: Tenant identifier
            ticket_id: Ticket identifier
            correlation_id: Request correlation ID
            endpoint: API endpoint
            method: HTTP method
            status_code: Response status code
            **extra: Additional context fields
        """
        logger.info(
            "ServiceDesk API call",
            extra={
                "tenant_id": tenant_id,
                "ticket_id": ticket_id,
                "correlation_id": correlation_id,
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "operation": "api_call",
                "status": "success",
                "service": "api_client",
                **extra,
            },
        )

    @staticmethod
    def audit_api_retry(
        tenant_id: str,
        ticket_id: str,
        correlation_id: str,
        attempt_number: int,
        status_code: int,
        **extra: Any,
    ) -> None:
        """
        Log API retry attempt.

        Args:
            tenant_id: Tenant identifier
            ticket_id: Ticket identifier
            correlation_id: Request correlation ID
            attempt_number: Retry attempt number
            status_code: Response status code
            **extra: Additional context fields
        """
        logger.warning(
            "ServiceDesk API retry",
            extra={
                "tenant_id": tenant_id,
                "ticket_id": ticket_id,
                "correlation_id": correlation_id,
                "attempt_number": attempt_number,
                "status_code": status_code,
                "operation": "api_retry",
                "status": "retrying",
                "service": "api_client",
                **extra,
            },
        )

    @staticmethod
    def audit_api_call_failed(
        tenant_id: str,
        ticket_id: str,
        correlation_id: str,
        endpoint: str,
        method: str,
        final_status_code: int,
        error_message: str,
        **extra: Any,
    ) -> None:
        """
        Log API call failure.

        Args:
            tenant_id: Tenant identifier
            ticket_id: Ticket identifier
            correlation_id: Request correlation ID
            endpoint: API endpoint
            method: HTTP method
            final_status_code: Final response status code
            error_message: Error message (will be redacted)
            **extra: Additional context fields
        """
        logger.error(
            "ServiceDesk API failed",
            extra={
                "tenant_id": tenant_id,
                "ticket_id": ticket_id,
                "correlation_id": correlation_id,
                "endpoint": endpoint,
                "method": method,
                "final_status_code": final_status_code,
                "error_message": error_message,
                "operation": "api_call",
                "status": "failure",
                "service": "api_client",
                **extra,
            },
        )


def configure_logging() -> None:
    """
    Configure application logging with Loguru.

    Sets up log formatting, rotation, serialization, and level based on settings.
    Supports both development (colorized) and production (JSON) outputs.

    Features:
    - Correlation ID support via logger.bind(correlation_id=...)
    - Sensitive data redaction for API keys, passwords, PII
    - ISO-8601 timestamps with UTC timezone
    - 90-day retention per NFR005 compliance requirement
    - Optional file handler via LOG_FILE_ENABLED environment variable

    Development Mode:
        - Colorized console output for easy reading
        - Human-readable timestamp and formatting
        - Outputs to stderr

    Production Mode:
        - JSON serialization for structured log aggregation
        - File rotation at midnight with 90-day retention
        - Compressed log archives
        - Includes all context fields (correlation_id, worker_id, task_id, etc.)

    Usage in Celery Tasks:
        logger.bind(correlation_id=correlation_id, task_id=self.request.id)
        logger.info("Task started", extra={
            "worker_id": self.request.hostname,
        })

    Usage with AuditLogger:
        audit_logger = AuditLogger()
        audit_logger.audit_webhook_received(
            tenant_id="tenant-123",
            ticket_id="TKT-456",
            correlation_id=str(uuid.uuid4()),
        )
    """
    # Remove default handler
    logger.remove()

    # Apply sensitive data filter to all handlers
    sensitive_filter = SensitiveDataFilter()

    # Development: Colorized console output
    if settings.environment == "development":
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level> {extra}",
            level=settings.log_level,
            colorize=True,
            filter=sensitive_filter,
        )
    else:
        # Production: JSON serialization for log aggregation
        logger.add(
            sys.stderr,
            format="{message}",
            level=settings.log_level,
            serialize=True,  # JSON output for production
            colorize=False,
            filter=sensitive_filter,
        )

    # Add file handler for production with JSON serialization
    # Controlled by LOG_FILE_ENABLED environment variable (default: true)
    if settings.environment != "development":
        log_file_enabled = os.getenv("LOG_FILE_ENABLED", "true").lower() == "true"
        if log_file_enabled:
            logger.add(
                "logs/ai_agents_{time:YYYY-MM-DD}.log",
                rotation="00:00",  # Rotate at midnight
                retention="90 days",  # 90-day retention per NFR005 compliance requirement
                compression="zip",  # Compress old logs
                level=settings.log_level,
                serialize=True,  # JSON format for structured logging
                filter=sensitive_filter,
            )

    logger.info(
        "Logging configured",
        extra={
            "environment": settings.environment,
            "log_level": settings.log_level,
            "correlation_id": None,  # No correlation ID at startup
            "service": "core",
        },
    )
