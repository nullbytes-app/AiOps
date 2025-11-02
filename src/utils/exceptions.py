"""
Custom exceptions for the AI Agents application.

This module defines custom exception classes for specific error scenarios
across different services and modules. Custom exceptions provide better
error handling, logging context, and API responses.
"""


class QueueServiceError(Exception):
    """
    Exception raised when queue operations fail.

    This exception is raised by QueueService when Redis queue push operations
    fail due to connection errors, timeouts, or other Redis-related issues.
    The exception message should include context about the failed operation.

    Example:
        raise QueueServiceError(
            f"Failed to queue job {job_id} for tenant {tenant_id}: {error}"
        )
    """

    pass


class ValidationError(Exception):
    """
    Exception raised for input validation failures.

    This exception is raised when input validation fails, such as invalid
    tenant_id, empty query description, or other constraint violations.
    Used by services to provide clear error messages for client handling.

    Example:
        raise ValidationError("query_description cannot be empty")
    """

    pass


class DatabaseError(Exception):
    """
    Exception raised for database operation failures.

    This exception is raised when database queries fail due to connection
    errors, timeouts, or other database-related issues. Wraps underlying
    database exceptions to prevent information leakage.

    Example:
        raise DatabaseError(f"Failed to search tickets for tenant {tenant_id}")
    """

    pass
