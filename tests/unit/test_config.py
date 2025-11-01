"""
Unit tests for configuration module.

Tests the Settings class to ensure environment variables are loaded correctly,
defaults are applied, and the env_prefix is working as expected.
"""

import os
from typing import Any, Generator

import pytest
from pydantic import ValidationError

from src.config import Settings


@pytest.fixture
def clean_env() -> Generator[None, None, None]:
    """
    Clean environment variables before and after tests.

    Also temporarily renames the .env file to prevent Pydantic from loading
    defaults from it, allowing tests to verify that Settings raises errors
    when required environment variables are missing.

    Yields:
        None: Cleanup fixture
    """
    from pathlib import Path

    # Store original env vars
    original_env = os.environ.copy()

    # Clear AI_AGENTS_ prefixed vars
    for key in list(os.environ.keys()):
        if key.startswith("AI_AGENTS_"):
            del os.environ[key]

    # Temporarily rename .env file so Pydantic can't load from it
    env_file = Path(".env")
    env_file_backup = Path(".env.test_backup")
    env_exists = env_file.exists()

    if env_exists:
        env_file.rename(env_file_backup)

    try:
        yield
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)

        # Restore .env file
        if env_exists and env_file_backup.exists():
            env_file_backup.rename(env_file)


@pytest.fixture
def valid_env_vars() -> dict[str, str]:
    """
    Provide valid environment variables for testing.

    Returns:
        dict: Valid environment variables
    """
    return {
        "AI_AGENTS_DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test_db",
        "AI_AGENTS_REDIS_URL": "redis://localhost:6379/0",
        "AI_AGENTS_CELERY_BROKER_URL": "redis://localhost:6379/1",
        "AI_AGENTS_CELERY_RESULT_BACKEND": "redis://localhost:6379/1",
    }


def test_settings_loads_from_environment_variables(
    clean_env: None, valid_env_vars: dict[str, str]
) -> None:
    """
    Test that Settings correctly loads values from environment variables.

    Args:
        clean_env: Fixture to clean environment
        valid_env_vars: Fixture with valid environment variables
    """
    # Set environment variables
    for key, value in valid_env_vars.items():
        os.environ[key] = value

    # Create Settings instance
    settings = Settings()

    # Assert values match environment variables
    assert (
        settings.database_url
        == "postgresql+asyncpg://test:test@localhost:5432/test_db"
    )
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.celery_broker_url == "redis://localhost:6379/1"
    assert settings.celery_result_backend == "redis://localhost:6379/1"


def test_settings_uses_default_values_when_env_vars_missing(
    clean_env: None, valid_env_vars: dict[str, str]
) -> None:
    """
    Test that Settings applies default values for optional fields.

    Args:
        clean_env: Fixture to clean environment
        valid_env_vars: Fixture with valid environment variables
    """
    # Set only required env vars
    for key, value in valid_env_vars.items():
        os.environ[key] = value

    # Create Settings instance
    settings = Settings()

    # Assert defaults are applied
    assert settings.database_pool_size == 20
    assert settings.redis_max_connections == 10
    assert settings.environment == "development"
    assert settings.log_level == "INFO"


def test_settings_accepts_custom_values_for_optional_fields(
    clean_env: None, valid_env_vars: dict[str, str]
) -> None:
    """
    Test that Settings accepts custom values for optional fields.

    Args:
        clean_env: Fixture to clean environment
        valid_env_vars: Fixture with valid environment variables
    """
    # Set environment variables with custom values
    for key, value in valid_env_vars.items():
        os.environ[key] = value

    os.environ["AI_AGENTS_DATABASE_POOL_SIZE"] = "50"
    os.environ["AI_AGENTS_REDIS_MAX_CONNECTIONS"] = "25"
    os.environ["AI_AGENTS_ENVIRONMENT"] = "production"
    os.environ["AI_AGENTS_LOG_LEVEL"] = "DEBUG"

    # Create Settings instance
    settings = Settings()

    # Assert custom values are used
    assert settings.database_pool_size == 50
    assert settings.redis_max_connections == 25
    assert settings.environment == "production"
    assert settings.log_level == "DEBUG"


def test_env_prefix_correctly_prepends_to_variable_names(
    clean_env: None, valid_env_vars: dict[str, str]
) -> None:
    """
    Test that the AI_AGENTS_ prefix is correctly applied.

    Args:
        clean_env: Fixture to clean environment
        valid_env_vars: Fixture with valid environment variables
    """
    # Set environment variable WITH prefix
    os.environ["AI_AGENTS_DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test_db"
    os.environ["AI_AGENTS_REDIS_URL"] = "redis://localhost:6379/0"
    os.environ["AI_AGENTS_CELERY_BROKER_URL"] = "redis://localhost:6379/1"
    os.environ["AI_AGENTS_CELERY_RESULT_BACKEND"] = "redis://localhost:6379/1"

    # Create Settings instance
    settings = Settings()

    # Assert it loads correctly
    assert settings.database_url == "postgresql+asyncpg://test:test@localhost:5432/test_db"

    # Try setting without prefix (should NOT work)
    os.environ.clear()
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://wrong:wrong@localhost:5432/wrong"
    os.environ["AI_AGENTS_REDIS_URL"] = "redis://localhost:6379/0"
    os.environ["AI_AGENTS_CELERY_BROKER_URL"] = "redis://localhost:6379/1"
    os.environ["AI_AGENTS_CELERY_RESULT_BACKEND"] = "redis://localhost:6379/1"

    # Should raise validation error because DATABASE_URL (without prefix) is ignored
    with pytest.raises(ValidationError):
        Settings()


def test_settings_raises_error_when_required_vars_missing(clean_env: None) -> None:
    """
    Test that Settings raises ValidationError when required vars are missing.

    Args:
        clean_env: Fixture to clean environment
    """
    # Don't set any environment variables
    with pytest.raises(ValidationError) as exc_info:
        Settings()

    # Assert error mentions missing fields
    error_str = str(exc_info.value)
    assert "database_url" in error_str.lower()


def test_settings_validates_pool_size_constraints(
    clean_env: None, valid_env_vars: dict[str, str]
) -> None:
    """
    Test that Settings enforces constraints on pool_size.

    Args:
        clean_env: Fixture to clean environment
        valid_env_vars: Fixture with valid environment variables
    """
    # Set environment variables
    for key, value in valid_env_vars.items():
        os.environ[key] = value

    # Test valid pool size
    os.environ["AI_AGENTS_DATABASE_POOL_SIZE"] = "50"
    settings = Settings()
    assert settings.database_pool_size == 50

    # Test pool size too low (should fail)
    os.environ["AI_AGENTS_DATABASE_POOL_SIZE"] = "0"
    with pytest.raises(ValidationError):
        Settings()

    # Test pool size too high (should fail)
    os.environ["AI_AGENTS_DATABASE_POOL_SIZE"] = "150"
    with pytest.raises(ValidationError):
        Settings()


def test_settings_validates_environment_values(
    clean_env: None, valid_env_vars: dict[str, str]
) -> None:
    """
    Test that Settings only accepts valid environment values.

    Args:
        clean_env: Fixture to clean environment
        valid_env_vars: Fixture with valid environment variables
    """
    # Set environment variables
    for key, value in valid_env_vars.items():
        os.environ[key] = value

    # Test valid environments
    for env in ["development", "staging", "production"]:
        os.environ["AI_AGENTS_ENVIRONMENT"] = env
        settings = Settings()
        assert settings.environment == env

    # Test invalid environment (should fail)
    os.environ["AI_AGENTS_ENVIRONMENT"] = "invalid"
    with pytest.raises(ValidationError):
        Settings()


def test_settings_validates_log_level_values(
    clean_env: None, valid_env_vars: dict[str, str]
) -> None:
    """
    Test that Settings only accepts valid log level values.

    Args:
        clean_env: Fixture to clean environment
        valid_env_vars: Fixture with valid environment variables
    """
    # Set environment variables
    for key, value in valid_env_vars.items():
        os.environ[key] = value

    # Test valid log levels
    for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        os.environ["AI_AGENTS_LOG_LEVEL"] = level
        settings = Settings()
        assert settings.log_level == level

    # Test invalid log level (should fail)
    os.environ["AI_AGENTS_LOG_LEVEL"] = "INVALID"
    with pytest.raises(ValidationError):
        Settings()
