"""
Celery application initialization.

This module configures and initializes the Celery application for
distributed task processing. Full implementation in Story 1.5.
"""

from celery import Celery

from src.config import settings

# Initialize Celery application
celery_app = Celery(
    "ai_agents",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
)

# Task discovery will be configured in Story 1.5
# celery_app.autodiscover_tasks(['src.workers.tasks'])
