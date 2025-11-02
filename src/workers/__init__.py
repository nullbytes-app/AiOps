"""
Workers package initialization.

This module imports and registers Celery tasks for automatic discovery.
All tasks defined in tasks.py are imported here to ensure they are
registered with the Celery application.
"""

from src.workers.celery_app import celery_app
from src.workers.tasks import add_numbers, enhance_ticket

# Export tasks for easy importing
__all__ = ["celery_app", "add_numbers", "enhance_ticket"]
