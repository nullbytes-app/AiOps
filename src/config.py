"""
Application configuration management using Pydantic Settings.

This module defines the central configuration class that loads settings from
environment variables with the AI_AGENTS_ prefix. All application modules
should import the settings instance from this module.

Supports both local development (via .env file) and Kubernetes production
(via mounted environment variables from Secrets).
"""

import os
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def is_kubernetes_env() -> bool:
    """
    Detect if running in a Kubernetes environment.

    Returns:
        bool: True if running in Kubernetes (detected by KUBERNETES_SERVICE_HOST)
    """
    return bool(os.getenv("KUBERNETES_SERVICE_HOST"))


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
        webhook_secret: Shared secret for HMAC-SHA256 webhook signature validation (min 32 chars)

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
    celery_worker_concurrency: int = Field(
        default=4,
        description="Number of concurrent Celery workers per pod",
        ge=1,
        le=16,
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

    # Monitoring Configuration
    prometheus_url: str = Field(
        default="http://prometheus:9090",
        description="Prometheus server URL for metrics queries (HTTP API)",
    )

    # Kubernetes Configuration
    kubernetes_namespace: str = Field(
        default="ai-agents",
        description="Kubernetes namespace for worker operations",
    )
    kubernetes_in_cluster: bool = Field(
        default=True,
        description="Whether running inside Kubernetes cluster (use in-cluster config)",
    )
    worker_log_lines: int = Field(
        default=100,
        description="Number of log lines to fetch from worker pods",
        ge=10,
        le=1000,
    )
    celery_app_name: str = Field(
        default="ai_agents",
        description="Celery application name for worker discovery",
    )

    # Security Configuration
    webhook_secret: str = Field(
        ...,
        description="Shared secret for HMAC-SHA256 webhook signature validation",
        min_length=32,
    )
    webhook_timestamp_tolerance_seconds: int = Field(
        default=300,
        description="Webhook timestamp tolerance in seconds (default: 5 minutes)",
        ge=60,
        le=3600,
    )
    webhook_clock_skew_tolerance_seconds: int = Field(
        default=30,
        description="Webhook clock skew tolerance in seconds (default: 30 seconds)",
        ge=1,
        le=300,
    )
    admin_api_key: str = Field(
        ...,
        description="API key for admin endpoints (X-Admin-Key header)",
        min_length=32,
    )
    encryption_key: str = Field(
        ...,
        description="Encryption key for sensitive fields (Fernet symmetric key)",
    )

    # Secrets (Individual fields from Kubernetes Secrets / .env)
    postgres_password: str = Field(
        ...,
        description="PostgreSQL database password (minimum 12 characters)",
        min_length=12,
    )
    redis_password: str = Field(
        ...,
        description="Redis password (minimum 12 characters)",
        min_length=12,
    )
    openai_api_key: str = Field(
        ...,
        description="OpenAI API key for GPT models (sk-proj-... or sk-...)",
    )

    # OpenRouter/LLM Configuration
    openrouter_api_key: str = Field(
        ...,
        description="OpenRouter API key for LLM synthesis (sk-or-v1-...)",
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter API base URL",
    )
    openrouter_site_url: str = Field(
        ...,
        description="Site URL for HTTP-Referer header (for OpenRouter rankings)",
    )
    openrouter_app_name: str = Field(
        ...,
        description="App name for X-Title header (for OpenRouter rankings)",
    )
    llm_model: str = Field(
        default="openai/gpt-4o-mini",
        description="LLM model to use for synthesis (via OpenRouter)",
    )
    llm_max_tokens: int = Field(
        default=1000,
        description="Maximum tokens for LLM response (~500 words)",
        ge=100,
        le=4000,
    )
    llm_temperature: float = Field(
        default=0.3,
        description="LLM temperature for consistent, focused output",
        ge=0.0,
        le=1.0,
    )
    llm_timeout_seconds: int = Field(
        default=30,
        description="Timeout for LLM API calls (seconds)",
        ge=5,
        le=120,
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
# For tests, environment variables are set up by conftest.py
try:
    settings = Settings()
except Exception as e:
    # Settings instantiation may fail during testing without .env
    # Will be initialized by conftest.py with test environment variables
    import sys
    if "pytest" in sys.modules:
        # Running under pytest - settings will be initialized by conftest
        settings = None  # type: ignore
    else:
        # Running outside pytest - re-raise the exception
        raise
