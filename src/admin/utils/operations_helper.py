"""
Operations Helper - Compatibility Shim.

This module re-exports all operations functions for backward compatibility.
The implementation has been refactored into three focused modules to comply
with CLAUDE.md 500-line constraint (C1):

- operations_core: Redis control, queue management, tenant config sync
- operations_audit: Audit logging and recent operations queries
- operations_utils: Worker health, confirmation dialogs, utilities

Story 6.5 Code Review Follow-up: Refactored 669-line file into 3 modules
averaging ~220 lines each (all under 500-line limit).

Usage:
    All existing imports continue to work:
    >>> from src.admin.utils.operations_helper import pause_processing
    >>> from src.admin.utils.operations_helper import log_operation
    >>> from src.admin.utils.operations_helper import confirm_operation
"""

# Re-export all functions for backward compatibility

# Core operations (Redis control, queue management, tenant sync)
from admin.utils.operations_core import (
    CELERY_QUEUE_NAME,
    PAUSE_FLAG_KEY,
    PAUSE_FLAG_TTL,
    clear_celery_queue,
    get_queue_length,
    is_processing_paused,
    pause_processing,
    resume_processing,
    sync_tenant_configs,
)

# Audit logging
from admin.utils.operations_audit import get_recent_operations, log_operation

# Worker health, confirmation dialogs, utilities
from admin.utils.operations_utils import (
    confirm_operation,
    format_uptime,
    get_active_workers,
    get_worker_stats,
)

# Explicit __all__ for clarity
__all__ = [
    # Constants
    "PAUSE_FLAG_KEY",
    "PAUSE_FLAG_TTL",
    "CELERY_QUEUE_NAME",
    # Core operations
    "pause_processing",
    "resume_processing",
    "is_processing_paused",
    "clear_celery_queue",
    "get_queue_length",
    "sync_tenant_configs",
    # Audit logging
    "log_operation",
    "get_recent_operations",
    # Worker health
    "get_worker_stats",
    "get_active_workers",
    # Confirmation dialogs
    "confirm_operation",
    # Utilities
    "format_uptime",
]
