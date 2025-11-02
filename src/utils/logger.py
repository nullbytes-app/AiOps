"""
Logging configuration using Loguru.

This module configures structured logging for the application with support
for both API and Celery worker contexts. Provides colorized console output
for development and JSON serialization for production environments.

Configuration:
    - Development: Colorized console output with readable formatting
    - Production: JSON serialization for log aggregation and analysis
    - Worker Context: Automatically includes worker_id, task_name, task_id
      when used from Celery tasks (via logger.bind() or extra parameter)
"""

import sys

from loguru import logger

from src.config import settings


def configure_logging() -> None:
    """
    Configure application logging with Loguru.

    Sets up log formatting, rotation, serialization, and level based on settings.
    Supports both development (colorized) and production (JSON) outputs.

    Development Mode:
        - Colorized console output for easy reading
        - Human-readable timestamp and formatting
        - Outputs to stderr

    Production Mode:
        - JSON serialization for structured log aggregation
        - File rotation at midnight with 30-day retention
        - Compressed log archives
        - Includes all context fields (worker_id, task_id, etc.)

    Usage in Celery Tasks:
        logger.info("Task started", extra={
            "task_id": self.request.id,
            "task_name": self.name,
            "worker_id": self.request.hostname
        })
    """
    # Remove default handler
    logger.remove()

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
        )
    else:
        # Production: JSON serialization for log aggregation
        logger.add(
            sys.stderr,
            format="{message}",
            level=settings.log_level,
            serialize=True,  # JSON output for production
            colorize=False,
        )

    # Add file handler for production with JSON serialization
    if settings.environment != "development":
        logger.add(
            "logs/ai_agents_{time:YYYY-MM-DD}.log",
            rotation="00:00",  # Rotate at midnight
            retention="30 days",  # Keep logs for 30 days
            compression="zip",  # Compress old logs
            level=settings.log_level,
            serialize=True,  # JSON format for structured logging
        )

    logger.info(
        f"Logging configured at {settings.log_level} level",
        extra={"environment": settings.environment},
    )
