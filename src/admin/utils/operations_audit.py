"""
Operations Audit Logging Functions.

This module provides audit logging capabilities for system operations:
- Log operation execution to audit_log table
- Query recent operations for compliance reporting

Dependencies:
- sqlalchemy: Database operations for audit_log table
- streamlit: Caching for query optimization

Part of Story 6.5 refactoring to comply with CLAUDE.md 500-line constraint.
"""

from datetime import datetime, timezone

import streamlit as st
from loguru import logger
from sqlalchemy import desc

from admin.utils.db_helper import get_db_session


# ============================================================================
# AUDIT LOGGING (AC#7, AC#9)
# ============================================================================


def log_operation(user: str, operation: str, details: dict, status: str) -> bool:
    """
    Create audit log entry for system operation.

    Inserts record into audit_log table with timestamp, user, operation name,
    details (JSON), and status. Required for compliance (AC#9).

    AC#9: Audit log entry created for each operation.

    Args:
        user: Username or identifier performing operation
        operation: Operation name (e.g., "pause_processing", "clear_queue")
        details: Additional details as dict (will be stored as JSON)
        status: Operation status ("success", "failure", "in_progress")

    Returns:
        bool: True if log entry created successfully, False on error

    Examples:
        >>> log_operation(
        ...     user="admin@example.com",
        ...     operation="pause_processing",
        ...     details={"queue": "celery", "flag_ttl": 86400},
        ...     status="success"
        ... )
        True

        >>> log_operation("admin", "clear_queue", {}, "failure")
        False  # Database unavailable
    """
    try:
        from src.database.models import AuditLog

        with get_db_session() as session:
            # Create audit log record
            log_entry = AuditLog(
                timestamp=datetime.now(timezone.utc),
                user=user,
                operation=operation,
                details=details,  # SQLAlchemy JSON column
                status=status,
            )

            session.add(log_entry)
            session.commit()

            logger.info(f"Audit log created: {operation} by {user} ({status})")
            return True

    except Exception as e:
        logger.error(f"Failed to create audit log entry: {e}")
        # Don't block operation if logging fails
        return False


@st.cache_data(ttl=5)
def get_recent_operations(limit: int = 20) -> list[dict]:
    """
    Query recent system operations from audit log.

    Returns last N operations ordered by timestamp DESC. Cached for 5 seconds
    for near-real-time updates.

    AC#7: Operation logs displayed (last 20 operations).

    Args:
        limit: Maximum number of operations to return (default: 20)

    Returns:
        list[dict]: List of operation dicts, or empty list if unavailable
            Each dict contains: id, timestamp, user, operation, details, status

    Examples:
        >>> get_recent_operations(limit=10)
        [
            {
                "id": "uuid-1",
                "timestamp": "2025-11-04 10:30:00",
                "user": "admin",
                "operation": "pause_processing",
                "details": {"queue": "celery"},
                "status": "success"
            },
            ...
        ]

        >>> get_recent_operations()  # No operations logged yet
        []
    """
    try:
        from src.database.models import AuditLog

        with get_db_session() as session:
            # Query last N operations ordered by timestamp DESC
            operations = (
                session.query(AuditLog)
                .order_by(desc(AuditLog.timestamp))
                .limit(limit)
                .all()
            )

            if not operations:
                return []

            # Convert to list of dicts
            results = []
            for op in operations:
                results.append(
                    {
                        "id": str(op.id),
                        "timestamp": op.timestamp,
                        "user": op.user,
                        "operation": op.operation,
                        "details": op.details,
                        "status": op.status,
                    }
                )

            return results

    except Exception as e:
        logger.error(f"Failed to get recent operations: {e}")
        return []
