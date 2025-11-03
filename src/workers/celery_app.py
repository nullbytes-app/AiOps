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

from celery import Celery

from src.config import settings
from src.utils.secrets import validate_secrets

logger = logging.getLogger(__name__)

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
