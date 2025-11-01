"""
Logging configuration using Loguru.

This module configures structured logging for the application.
Loguru provides better formatting and easier configuration than standard logging.
"""

import sys

from loguru import logger

from src.config import settings


def configure_logging() -> None:
    """
    Configure application logging with Loguru.

    Sets up log formatting, rotation, and level based on settings.
    """
    # Remove default handler
    logger.remove()

    # Add custom handler with formatting
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>",
        level=settings.log_level,
        colorize=True,
    )

    # Add file handler for production
    if settings.environment != "development":
        logger.add(
            "logs/ai_agents_{time:YYYY-MM-DD}.log",
            rotation="00:00",  # Rotate at midnight
            retention="30 days",  # Keep logs for 30 days
            compression="zip",  # Compress old logs
            level=settings.log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
            "{name}:{function}:{line} | {message}",
        )

    logger.info(f"Logging configured at {settings.log_level} level")
