"""
Secrets validation utilities.

This module provides functions to validate that all required secrets are present
and properly formatted at application startup.
"""

import os
from cryptography.fernet import Fernet, InvalidToken


def validate_secrets() -> None:
    """
    Validate that all required secrets are present and properly formatted.

    Validates:
    - POSTGRES_PASSWORD: >= 12 characters
    - REDIS_PASSWORD: >= 12 characters
    - OPENAI_API_KEY: non-empty (format: sk-proj-... or sk-...)
    - ENCRYPTION_KEY: valid Fernet key format

    Raises:
        EnvironmentError: If any required secret is missing or invalid

    Examples:
        >>> validate_secrets()  # Raises EnvironmentError if validation fails
    """
    required_secrets = {
        "POSTGRES_PASSWORD": {"type": "password", "min_length": 12},
        "REDIS_PASSWORD": {"type": "password", "min_length": 12},
        "OPENAI_API_KEY": {"type": "api_key", "min_length": 20},
        "ENCRYPTION_KEY": {"type": "encryption_key"},
    }

    for secret_name, rules in required_secrets.items():
        # Prepend AI_AGENTS_ prefix for environment variable lookup
        env_var_name = f"AI_AGENTS_{secret_name}"
        value = os.getenv(env_var_name)

        if not value:
            raise EnvironmentError(
                f"Missing required secret: {secret_name}. "
                f"Set environment variable {env_var_name} or .env entry {secret_name}"
            )

        # Validate password minimum length
        if rules["type"] == "password":
            min_len = rules.get("min_length", 12)
            if len(value) < min_len:
                raise EnvironmentError(
                    f"{secret_name} is too short. "
                    f"Minimum {min_len} characters required, got {len(value)}"
                )

        # Validate API key minimum length
        if rules["type"] == "api_key":
            min_len = rules.get("min_length", 20)
            if len(value) < min_len:
                raise EnvironmentError(
                    f"{secret_name} is too short. "
                    f"Minimum {min_len} characters required, got {len(value)}"
                )

        # Validate Fernet encryption key format
        if rules["type"] == "encryption_key":
            try:
                # Attempt to instantiate Fernet with the key to validate format
                Fernet(value)
            except (InvalidToken, ValueError) as e:
                raise EnvironmentError(
                    f"{secret_name} is not a valid Fernet encryption key. "
                    f"Generate a new key with: "
                    f"python -c 'from src.utils.encryption import generate_encryption_key; "
                    f"print(generate_encryption_key())'"
                ) from e


async def validate_secrets_at_startup() -> None:
    """
    Async wrapper for secrets validation at FastAPI startup.

    Raises:
        EnvironmentError: If any required secret is missing or invalid
    """
    validate_secrets()
