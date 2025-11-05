"""
Operations Core Functions for System Operations Controls.

This module provides core Redis-based system operation functions:
- Pause/Resume Celery worker processing
- Queue management (clear queue, get queue depth)
- Tenant configuration synchronization

Dependencies:
- redis: Synchronous Redis client for pause flags and queue operations
- celery: Celery control API for queue operations
- sqlalchemy: Database operations for tenant config sync

Part of Story 6.5 refactoring to comply with CLAUDE.md 500-line constraint.
"""

import streamlit as st
from loguru import logger

from admin.utils.db_helper import get_db_session
from admin.utils.redis_helper import get_sync_redis_client
from src.workers.celery_app import celery_app

# Constants
PAUSE_FLAG_KEY = "system:pause_processing"
PAUSE_FLAG_TTL = 86400  # 24 hours safety timeout
CELERY_QUEUE_NAME = "celery"


# ============================================================================
# REDIS CONTROL FUNCTIONS (AC#2, AC#3, AC#4)
# ============================================================================


def pause_processing() -> tuple[bool, str]:
    """
    Pause Celery worker processing by setting Redis pause flag.

    Sets Redis key 'system:pause_processing' with 24-hour TTL. Workers check
    this flag before executing tasks. If flag exists, tasks are requeued.

    AC#2: "Pause Processing" button stops Celery workers from picking up new jobs.

    Returns:
        tuple[bool, str]: (success, message)
            success: True if pause flag set, False on error
            message: User-friendly status message

    Examples:
        >>> pause_processing()
        (True, "✅ Processing paused. Workers will not pick up new tasks.")

        >>> pause_processing()  # Redis unavailable
        (False, "❌ Failed to set pause flag: Connection refused")
    """
    try:
        client = get_sync_redis_client()

        if client is None:
            return False, "❌ Redis client unavailable. Cannot pause processing."

        # Set pause flag with TTL (safety: auto-resume after 24 hours)
        client.setex(PAUSE_FLAG_KEY, PAUSE_FLAG_TTL, "true")

        logger.info("Processing paused via Redis flag")
        return True, "✅ Processing paused. Workers will not pick up new tasks."

    except Exception as e:
        logger.error(f"Failed to pause processing: {e}")
        return False, f"❌ Failed to set pause flag: {str(e)[:50]}"


def resume_processing() -> tuple[bool, str]:
    """
    Resume Celery worker processing by clearing Redis pause flag.

    Deletes Redis key 'system:pause_processing'. Workers will start processing
    tasks normally.

    AC#3: "Resume Processing" button clears pause flag.

    Returns:
        tuple[bool, str]: (success, message)
            success: True if pause flag cleared, False on error
            message: User-friendly status message

    Examples:
        >>> resume_processing()
        (True, "✅ Processing resumed. Workers can now pick up tasks.")

        >>> resume_processing()  # No flag set
        (True, "⚠️ Processing was not paused (no flag found).")
    """
    try:
        client = get_sync_redis_client()

        if client is None:
            return False, "❌ Redis client unavailable. Cannot resume processing."

        # Check if flag exists before deleting
        exists = client.exists(PAUSE_FLAG_KEY)

        if not exists:
            return True, "⚠️ Processing was not paused (no flag found)."

        # Delete pause flag
        client.delete(PAUSE_FLAG_KEY)

        logger.info("Processing resumed via Redis flag deletion")
        return True, "✅ Processing resumed. Workers can now pick up tasks."

    except Exception as e:
        logger.error(f"Failed to resume processing: {e}")
        return False, f"❌ Failed to clear pause flag: {str(e)[:50]}"


@st.cache_data(ttl=10)
def is_processing_paused() -> bool:
    """
    Check if Celery worker processing is currently paused.

    Queries Redis for 'system:pause_processing' key existence.

    Returns:
        bool: True if processing is paused, False otherwise

    Examples:
        >>> is_processing_paused()
        True  # Pause flag exists

        >>> is_processing_paused()
        False  # No pause flag
    """
    try:
        client = get_sync_redis_client()

        if client is None:
            logger.warning("Redis client unavailable, assuming not paused")
            return False

        return client.exists(PAUSE_FLAG_KEY) > 0

    except Exception as e:
        logger.error(f"Failed to check pause status: {e}")
        return False


# ============================================================================
# QUEUE MANAGEMENT (AC#4)
# ============================================================================


def clear_celery_queue(queue_name: str = CELERY_QUEUE_NAME) -> tuple[bool, int, str]:
    """
    Clear all pending tasks from Celery queue.

    Uses celery_app.control.purge() to delete all pending tasks. This operation
    is destructive and cannot be undone. Requires confirmation dialog (AC#8).

    AC#4: "Clear Queue" button removes all pending jobs from Redis.

    Args:
        queue_name: Celery queue name to purge (default: "celery")

    Returns:
        tuple[bool, int, str]: (success, count, message)
            success: True if purge succeeded, False on error
            count: Number of tasks deleted
            message: User-friendly status message

    Examples:
        >>> clear_celery_queue()
        (True, 42, "✅ Cleared 42 pending tasks from queue 'celery'")

        >>> clear_celery_queue()  # Empty queue
        (True, 0, "✅ Queue 'celery' was already empty (0 tasks deleted)")
    """
    try:
        # Use Celery control API to purge queue
        result = celery_app.control.purge()

        # purge() returns count of deleted tasks
        count = result if result is not None else 0

        if count == 0:
            message = f"✅ Queue '{queue_name}' was already empty (0 tasks deleted)"
        else:
            message = f"✅ Cleared {count:,} pending tasks from queue '{queue_name}'"

        logger.info(f"Queue purged: {count} tasks deleted from '{queue_name}'")
        return True, count, message

    except Exception as e:
        logger.error(f"Failed to clear queue '{queue_name}': {e}")
        return False, 0, f"❌ Failed to clear queue: {str(e)[:50]}"


@st.cache_data(ttl=10)
def get_queue_length(queue_name: str = CELERY_QUEUE_NAME) -> int:
    """
    Get current depth of Celery queue.

    Queries Redis list length for Celery queue. Cached for 10 seconds.

    Args:
        queue_name: Redis list key name (default: "celery")

    Returns:
        int: Number of pending tasks in queue, or 0 if unavailable

    Examples:
        >>> get_queue_length()
        42

        >>> get_queue_length("custom_queue")
        7
    """
    try:
        client = get_sync_redis_client()

        if client is None:
            logger.warning("Redis client unavailable, returning queue depth 0")
            return 0

        depth = client.llen(queue_name)
        return int(depth) if depth is not None else 0

    except Exception as e:
        logger.error(f"Failed to get queue length for '{queue_name}': {e}")
        return 0


# ============================================================================
# TENANT CONFIG SYNC (AC#5)
# ============================================================================


def sync_tenant_configs() -> tuple[bool, dict, str]:
    """
    Reload tenant configurations from database to Redis cache.

    Queries all active tenant_config records and updates Redis cache keys
    'tenant_config:{tenant_id}' for each tenant.

    AC#5: "Sync Tenant Configs" button reloads tenant configurations.

    Returns:
        tuple[bool, dict, str]: (success, sync_results, message)
            success: True if sync completed, False on critical error
            sync_results: Dict mapping tenant_id -> sync status
            message: User-friendly summary message

    Examples:
        >>> sync_tenant_configs()
        (True, {"tenant-1": "✅", "tenant-2": "✅"}, "✅ Synced 2 tenant configs")

        >>> sync_tenant_configs()  # Partial failure
        (False, {"tenant-1": "✅", "tenant-2": "❌"}, "⚠️ Synced 1/2 configs")
    """
    try:
        from src.database.models import TenantConfig

        redis_client = get_sync_redis_client()

        if redis_client is None:
            return False, {}, "❌ Redis client unavailable. Cannot sync configs."

        sync_results = {}
        success_count = 0
        total_count = 0

        with get_db_session() as session:
            # Query all active tenant configs
            configs = session.query(TenantConfig).filter(TenantConfig.is_active == True).all()

            total_count = len(configs)

            if total_count == 0:
                return True, {}, "⚠️ No active tenant configs found to sync"

            for config in configs:
                try:
                    # Build Redis key
                    cache_key = f"tenant_config:{config.tenant_id}"

                    # Serialize config to dict (simplified - adjust based on your schema)
                    config_data = {
                        "tenant_id": config.tenant_id,
                        "webhook_url": config.webhook_url,
                        "api_key": config.api_key[:10] + "..." if config.api_key else None,
                        "is_active": config.is_active,
                    }

                    # Store in Redis with expiration (1 hour)
                    redis_client.setex(
                        cache_key,
                        3600,  # 1 hour TTL
                        str(config_data),  # Simple string serialization
                    )

                    sync_results[config.tenant_id] = "✅"
                    success_count += 1

                except Exception as e:
                    logger.error(f"Failed to sync config for tenant {config.tenant_id}: {e}")
                    sync_results[config.tenant_id] = "❌"

        # Generate summary message
        if success_count == total_count:
            message = f"✅ Synced {success_count} tenant config(s) to Redis cache"
            return True, sync_results, message
        elif success_count > 0:
            message = f"⚠️ Synced {success_count}/{total_count} configs (partial success)"
            return False, sync_results, message
        else:
            message = f"❌ Failed to sync any tenant configs ({total_count} attempted)"
            return False, sync_results, message

    except Exception as e:
        logger.error(f"Failed to sync tenant configs: {e}")
        return False, {}, f"❌ Sync failed: {str(e)[:50]}"
