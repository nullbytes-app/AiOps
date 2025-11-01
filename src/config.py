"""
Application configuration management using Pydantic Settings.

This module defines the central configuration class that loads settings from
environment variables with the AI_AGENTS_ prefix. All application modules
should import the settings instance from this module.
"""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings use the AI_AGENTS_ prefix for environment variables.
    For example, database_url is loaded from AI_AGENTS_DATABASE_URL.

    Args:
        database_url: PostgreSQL connection string (asyncpg driver)
        database_pool_size: Maximum number of database connections in pool
        redis_url: Redis connection string for caching
        redis_max_connections: Maximum number of Redis connections
        celery_broker_url: Redis URL for Celery broker
        celery_result_backend: Redis URL for Celery results
        environment: Deployment environment (development/staging/production)
        log_level: Logging level (DEBUG/INFO/WARNING/ERROR/CRITICAL)

    Returns:
        Settings: Configured settings instance
    """

    # Database Configuration
    database_url: str = Field(
        ...,
        description="PostgreSQL connection string with asyncpg driver",
    )
    database_pool_size: int = Field(
        default=20,
        description="Maximum number of database connections in pool",
        ge=1,
        le=100,
    )

    # Redis Configuration
    redis_url: str = Field(
        ...,
        description="Redis connection string for caching",
    )
    redis_max_connections: int = Field(
        default=10,
        description="Maximum number of Redis connections",
        ge=1,
        le=50,
    )

    # Celery Configuration
    celery_broker_url: str = Field(
        ...,
        description="Redis URL for Celery broker",
    )
    celery_result_backend: str = Field(
        ...,
        description="Redis URL for Celery results backend",
    )

    # Application Configuration
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Deployment environment",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AI_AGENTS_",
        case_sensitive=False,
        extra="ignore",
    )


def get_settings() -> Settings:
    """
    Get or create the global settings instance.

    Returns:
        Settings: The application settings instance
    """
    return Settings()


# Global settings instance for convenience
# Import this in other modules: from src.config import settings
# For tests, import Settings class and instantiate with env vars
try:
    settings = Settings()
except Exception:
    # Settings instantiation will fail during testing without .env
    # Tests should create their own Settings instances with test env vars
    settings = None  # type: ignore
