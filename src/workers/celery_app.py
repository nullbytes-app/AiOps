"""
Celery application initialization and configuration.

This module configures the Celery application for distributed task processing
with Redis as the message broker and result backend. Configuration follows
tech spec requirements for concurrency, timeouts, and retry logic.

Configuration Details:
    - Broker: Redis DB 1 (separate from cache on DB 0)
    - Result Backend: Redis DB 1
    - Serialization: JSON for tasks and results
    - Concurrency: 4 workers per pod (configurable via Settings)
    - Time Limits: 120s hard, 100s soft
    - Retry: Max 3 attempts with exponential backoff
    - Prefetch: 1 task per worker (memory efficiency)
    - Acknowledgement: Late (after task completion for reliability)
"""

import logging

import redis
from celery import Celery
from celery.exceptions import Retry
from celery.signals import task_prerun, worker_process_init
from celery.schedules import crontab

from src.config import settings
from src.utils.secrets import validate_secrets

logger = logging.getLogger(__name__)

# Redis client for pause flag checking
# Uses synchronous Redis client for signal handler compatibility
_redis_client = None

# Story 4.6: OpenTelemetry Celery worker tracing initialization
# Using worker_process_init signal to initialize tracer AFTER worker fork
# This prevents BatchSpanProcessor threading issues in prefork worker model


@worker_process_init.connect(weak=False)
def init_celery_tracing(*args, **kwargs) -> None:  # type: ignore
    """
    Initialize OpenTelemetry tracing AFTER Celery worker process fork.

    This signal handler is critical for prefork worker model:
    - Celery creates child processes via fork
    - Background threads in parent don't survive fork
    - BatchSpanProcessor spawns threads that would break in child processes
    - Solution: Initialize tracer provider AFTER fork in child process

    This ensures each worker process has its own tracer provider with fresh threads.
    Also registers plugins for multi-tool support (Story 7.3).
    """
    from src.monitoring import init_tracer_provider
    from opentelemetry.instrumentation.celery import CeleryInstrumentor

    try:
        # Initialize tracer provider in child process
        init_tracer_provider()
        logger.info("Celery worker tracing initialized")

        # Instrument Celery for automatic task span creation
        CeleryInstrumentor().instrument()
        logger.info("Celery instrumentation enabled")
    except Exception as e:
        logger.error(f"Failed to initialize Celery tracing: {str(e)}", exc_info=True)
        # Continue startup despite tracing initialization failure
        # (tracing is optional, don't block worker startup)

    # Story 7.3: Register ServiceDesk Plus plugin in worker process
    try:
        from src.plugins import PluginManager
        from src.plugins.servicedesk_plus import ServiceDeskPlusPlugin

        manager = PluginManager()
        plugin = ServiceDeskPlusPlugin()
        manager.register_plugin("servicedesk_plus", plugin)
        logger.info("ServiceDesk Plus plugin registered in Celery worker")
    except Exception as e:
        logger.error(f"Failed to register ServiceDesk Plus plugin in worker: {str(e)}", exc_info=True)
        # Continue startup despite plugin registration failure
        # (worker can still process tasks without plugin)

    # Story 7.4: Register Jira Service Management plugin in worker process
    try:
        from src.plugins.jira import JiraServiceManagementPlugin

        jira_plugin = JiraServiceManagementPlugin()
        manager.register_plugin("jira", jira_plugin)
        logger.info("Jira Service Management plugin registered in Celery worker")
    except Exception as e:
        logger.error(f"Failed to register Jira plugin in worker: {str(e)}", exc_info=True)
        # Continue startup despite plugin registration failure

# Validate secrets before initializing Celery application
try:
    validate_secrets()
    logger.info("Celery worker secrets validated successfully")
except EnvironmentError as e:
    logger.error(f"Celery worker secrets validation failed: {str(e)}")
    raise

# Initialize Celery application with Redis broker and backend
# Redis connection uses secrets loaded from Kubernetes Secrets (production) or .env (development)
celery_app = Celery(
    "ai_agents",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Celery configuration per tech spec requirements
celery_app.conf.update(
    # Serialization (JSON only for security and compatibility)
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone configuration
    timezone="UTC",
    enable_utc=True,

    # Task execution settings
    task_track_started=True,
    task_time_limit=120,  # 120 seconds hard limit (per tech spec)
    task_soft_time_limit=100,  # 100 seconds soft limit (per tech spec)
    task_acks_late=True,  # Acknowledge after completion (prevents message loss)
    task_reject_on_worker_lost=True,  # Reject tasks if worker crashes

    # Worker settings
    worker_prefetch_multiplier=1,  # Process one task at a time (memory efficiency)
    worker_concurrency=settings.celery_worker_concurrency,  # 4 workers per pod (default)
    worker_send_task_events=True,  # Enable worker events for monitoring
    task_send_sent_event=True,  # Track task sent events

    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_extended=True,  # Store additional result metadata

    # Retry configuration (defaults for all tasks)
    task_autoretry_for=(Exception,),  # Retry on any exception
    task_max_retries=3,  # Maximum 3 retry attempts
    task_default_retry_delay=2,  # Base delay: 2 seconds
    task_retry_backoff=True,  # Exponential backoff (2s, 4s, 8s)
    task_retry_backoff_max=8,  # Max backoff: 8 seconds
    task_retry_jitter=True,  # Add jitter to prevent thundering herd
)

# ============================================================================
# PERIODIC TASK SCHEDULE (Story 8.10C - Budget Automation)
# ============================================================================

celery_app.conf.beat_schedule = {
    # Budget reset task - runs daily at 00:00 UTC
    'reset-tenant-budgets-daily': {
        'task': 'tasks.reset_tenant_budgets',
        'schedule': crontab(hour=0, minute=0),  # Daily at 00:00 UTC
        'options': {
            'expires': 3600,  # Task expires after 1 hour if not executed
        },
    },
    # Budget override expiry task - runs hourly at :00 minutes
    'expire-budget-overrides-hourly': {
        'task': 'tasks.expire_budget_overrides',
        'schedule': crontab(minute=0),  # Every hour at :00
        'options': {
            'expires': 1800,  # Task expires after 30 minutes if not executed
        },
    },
}


# ============================================================================
# PAUSE/RESUME MECHANISM (Story 6.5 - Task 7)
# ============================================================================


def get_redis_client_for_pause_check() -> redis.Redis:
    """
    Get or create Redis client for pause flag checking.

    Uses module-level _redis_client singleton for efficiency.
    Signal handlers are called frequently, so we cache the client.

    Returns:
        redis.Redis: Synchronous Redis client

    Raises:
        redis.ConnectionError: If Redis connection fails
    """
    global _redis_client

    if _redis_client is None:
        _redis_client = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            retry_on_timeout=True,
        )

    return _redis_client


@task_prerun.connect
def check_pause_flag_before_task(sender=None, **kwargs):
    """
    Check Redis pause flag before executing any Celery task.

    Signal handler for task_prerun (called before EVERY task execution).
    If pause flag exists, raises Retry exception to requeue the task.

    This implements the pause/resume mechanism for Story 6.5:
    - Admin sets 'system:pause_processing' Redis key to pause workers
    - Workers check this flag before executing each task
    - If flag exists: Task is requeued with 30-second countdown (graceful pause)
    - If flag absent: Task executes normally

    Design decisions:
    - Non-destructive: Tasks are requeued, not lost
    - No worker restart required: Takes effect immediately
    - Graceful: Currently executing tasks complete, new tasks wait
    - Safe: Auto-resume after 24 hours (flag TTL) if admin forgets

    Args:
        sender: Task class (provided by Celery)
        **kwargs: Additional signal arguments (task_id, args, kwargs, etc.)

    Raises:
        Retry: If pause flag is set (requeues task with 30s countdown)

    Examples:
        # Admin pauses processing
        redis_client.setex("system:pause_processing", 86400, "true")

        # Worker checks flag before task
        # -> Raises Retry, task requeued
        # -> Task will retry in 30 seconds

        # Admin resumes processing
        redis_client.delete("system:pause_processing")

        # Worker checks flag again
        # -> No flag, task executes normally
    """
    try:
        client = get_redis_client_for_pause_check()

        # Check if pause flag exists
        if client.exists("system:pause_processing"):
            task_name = sender.name if sender else "unknown"
            logger.warning(
                f"Processing paused - requeueing task '{task_name}' "
                f"(task_id: {kwargs.get('task_id', 'unknown')})"
            )

            # Requeue task with 30-second countdown
            # This raises Retry exception which Celery handles by requeueing
            raise Retry(
                exc=Exception("Processing paused by administrator"),
                countdown=30,  # Retry in 30 seconds
            )

    except redis.ConnectionError as e:
        # Redis unavailable - log error but allow task to execute
        # (Fail open for availability, fail closed would block all tasks)
        logger.error(
            f"Failed to check pause flag (Redis unavailable): {e}. "
            "Allowing task to execute."
        )

    except Retry:
        # Re-raise Retry exception (this is expected behavior when paused)
        raise

    except Exception as e:
        # Unexpected error - log but don't block task execution
        logger.error(
            f"Unexpected error checking pause flag: {e}. Allowing task to execute."
        )


# Log Celery configuration on module load
logger.info(
    f"Celery application initialized: broker={settings.celery_broker_url[:20]}..., "
    f"concurrency={settings.celery_worker_concurrency}, "
    f"time_limit={celery_app.conf.task_time_limit}s"
)
