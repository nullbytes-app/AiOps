"""
Unit tests for ConfigGenerator service.

Tests YAML config generation, backup creation, validation,
and file writing operations for litellm-config.yaml.
"""

import pytest
import yaml
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.litellm_config_generator import ConfigGenerator
from src.database.models import LLMProvider, LLMModel, ProviderType
from src.utils.encryption import encrypt


@pytest.fixture
def mock_db() -> AsyncSession:
    """Mock AsyncSession for database operations."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def config_generator(mock_db: AsyncSession) -> ConfigGenerator:
    """Create ConfigGenerator instance with mocked database."""
    return ConfigGenerator(db=mock_db)


@pytest.fixture
def sample_providers_and_models():
    """Sample providers and models for config generation."""
    openai_provider = LLMProvider(
        id=1,
        name="OpenAI Production",
        provider_type=ProviderType.OPENAI,
        api_base_url="https://api.openai.com/v1",
        api_key_encrypted=encrypt("sk-test123"),
        enabled=True,
    )

    anthropic_provider = LLMProvider(
        id=2,
        name="Anthropic Production",
        provider_type=ProviderType.ANTHROPIC,
        api_base_url="https://api.anthropic.com",
        api_key_encrypted=encrypt("sk-ant-test456"),
        enabled=True,
    )

    models = [
        LLMModel(
            id=1,
            provider_id=1,
            model_name="gpt-4",
            display_name="GPT-4",
            enabled=True,
            cost_per_input_token=0.03,
            cost_per_output_token=0.06,
            context_window=8192,
        ),
        LLMModel(
            id=2,
            provider_id=1,
            model_name="gpt-3.5-turbo",
            display_name="GPT-3.5 Turbo",
            enabled=True,
            cost_per_input_token=0.0015,
            cost_per_output_token=0.002,
            context_window=4096,
        ),
        LLMModel(
            id=3,
            provider_id=2,
            model_name="claude-3-5-sonnet",
            display_name="Claude 3.5 Sonnet",
            enabled=True,
            cost_per_input_token=0.003,
            cost_per_output_token=0.015,
            context_window=200000,
        ),
    ]

    return openai_provider, anthropic_provider, models


# ============================================================================
# CONFIG GENERATION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_generate_config_yaml_success(
    config_generator: ConfigGenerator,
    mock_db: AsyncMock,
    sample_providers_and_models,
):
    """Test successful YAML config generation with providers and models."""
    openai_provider, anthropic_provider, models = sample_providers_and_models

    # CRITICAL: Set up the models relationship on providers (joinedload expects this)
    openai_provider.models = [m for m in models if m.provider_id == 1]
    anthropic_provider.models = [m for m in models if m.provider_id == 2]

    # Mock database query with unique() support for joinedload
    provider_result = MagicMock()
    mock_scalars = MagicMock()
    mock_unique = MagicMock()
    mock_unique.all.return_value = [openai_provider, anthropic_provider]
    mock_scalars.unique.return_value = mock_unique
    provider_result.scalars.return_value = mock_scalars

    mock_db.execute.return_value = provider_result

    # Generate config
    config_yaml = await config_generator.generate_config_yaml()

    # Parse generated YAML
    config = yaml.safe_load(config_yaml)

    # Assertions
    assert "model_list" in config
    assert "general_settings" in config
    assert len(config["model_list"]) == 3

    # Check OpenAI models
    gpt4_entry = next(m for m in config["model_list"] if m["model_name"] == "GPT-4")
    assert gpt4_entry["litellm_params"]["model"] == "openai/gpt-4"
    assert gpt4_entry["litellm_params"]["api_base"] == "https://api.openai.com/v1"

    # Check Anthropic model
    claude_entry = next(m for m in config["model_list"] if m["model_name"] == "Claude 3.5 Sonnet")
    assert claude_entry["litellm_params"]["model"] == "anthropic/claude-3-5-sonnet"

    # Check general settings
    assert "master_key" in config["general_settings"]
    assert "database_url" in config["general_settings"]


@pytest.mark.asyncio
async def test_generate_config_yaml_only_enabled(
    config_generator: ConfigGenerator,
    mock_db: AsyncMock,
):
    """Test that config generation raises error when no enabled models exist."""
    disabled_provider = LLMProvider(
        id=1,
        name="Disabled Provider",
        provider_type=ProviderType.OPENAI,
        api_base_url="https://api.openai.com/v1",
        api_key_encrypted=encrypt("sk-test123"),
        enabled=False,  # Disabled
    )
    disabled_provider.models = []  # No models

    # Since provider is disabled, WHERE clause filters it out - return empty list
    provider_result = MagicMock()
    mock_scalars = MagicMock()
    mock_unique = MagicMock()
    mock_unique.all.return_value = []  # No enabled providers
    mock_scalars.unique.return_value = mock_unique
    provider_result.scalars.return_value = mock_scalars

    mock_db.execute.return_value = provider_result

    # Generate config should raise error (no enabled providers)
    with pytest.raises(Exception, match="No enabled providers"):
        await config_generator.generate_config_yaml()


@pytest.mark.asyncio
async def test_generate_config_yaml_provider_specific_params(
    config_generator: ConfigGenerator,
    mock_db: AsyncMock,
):
    """Test Azure OpenAI provider-specific parameters in config."""
    azure_provider = LLMProvider(
        id=1,
        name="Azure OpenAI",
        provider_type=ProviderType.AZURE_OPENAI,
        api_base_url="https://myresource.openai.azure.com",
        api_key_encrypted=encrypt("azure-key-123"),
        enabled=True,
    )

    azure_model = LLMModel(
        id=1,
        provider_id=1,
        model_name="gpt-4",
        display_name="Azure GPT-4",
        enabled=True,
    )

    # Set up models relationship
    azure_provider.models = [azure_model]

    # Mock database query with unique() support
    provider_result = MagicMock()
    mock_scalars = MagicMock()
    mock_unique = MagicMock()
    mock_unique.all.return_value = [azure_provider]
    mock_scalars.unique.return_value = mock_unique
    provider_result.scalars.return_value = mock_scalars

    mock_db.execute.return_value = provider_result

    # Generate config
    config_yaml = await config_generator.generate_config_yaml()

    # Parse generated YAML
    config = yaml.safe_load(config_yaml)

    # Assertions - Azure-specific params should be present
    model_entry = config["model_list"][0]
    assert "api_version" in model_entry["litellm_params"]
    assert model_entry["litellm_params"]["model"].startswith("azure_openai/")


# ============================================================================
# BACKUP TESTS
# ============================================================================


def test_backup_current_config_success(config_generator: ConfigGenerator):
    """Test timestamped backup creation."""
    test_config_content = "test: config\n"

    with patch("builtins.open", mock_open(read_data=test_config_content)):
        with patch("os.path.exists", return_value=True):
            with patch("shutil.copy2") as mock_copy:
                backup_path = config_generator.backup_current_config()

                # Assertions
                assert backup_path is not None
                assert ".backup." in backup_path
                assert backup_path.endswith(".yaml")
                mock_copy.assert_called_once()


def test_backup_current_config_no_existing_file(config_generator: ConfigGenerator):
    """Test backup when config file doesn't exist yet."""
    with patch("pathlib.Path.exists", return_value=False):
        backup_path = config_generator.backup_current_config()

        # Assertions - should return empty string if file doesn't exist
        assert backup_path == ""


# ============================================================================
# YAML VALIDATION TESTS
# ============================================================================


def test_validate_config_syntax_valid_yaml(config_generator: ConfigGenerator):
    """Test validation of syntactically correct YAML."""
    valid_yaml = """
model_list:
  - model_name: gpt-4
    litellm_params:
      model: openai/gpt-4
      api_key: sk-test123
general_settings:
  master_key: sk-master
    """

    result = config_generator.validate_config_syntax(valid_yaml)

    # Assertions
    assert result is True


def test_validate_config_syntax_invalid_yaml(config_generator: ConfigGenerator):
    """Test validation of syntactically incorrect YAML raises exception."""
    invalid_yaml = """
model_list:
  - model_name: gpt-4
    litellm_params:
      model: openai/gpt-4
      api_key: sk-test123
    invalid indentation
    """

    # Implementation raises ConfigGenerationError for invalid YAML
    from src.services.litellm_config_generator import ConfigGenerationError
    with pytest.raises(ConfigGenerationError, match="Invalid YAML syntax"):
        config_generator.validate_config_syntax(invalid_yaml)


def test_validate_config_syntax_empty_yaml(config_generator: ConfigGenerator):
    """Test validation of empty YAML."""
    empty_yaml = ""

    result = config_generator.validate_config_syntax(empty_yaml)

    # Assertions
    assert result is True  # Empty YAML is technically valid


# ============================================================================
# FILE WRITING TESTS
# ============================================================================


def test_write_config_to_file_success(config_generator: ConfigGenerator):
    """Test writing config to file with correct permissions."""
    test_config = "model_list: []\ngeneral_settings:\n  master_key: sk-test\n"

    with patch("pathlib.Path.write_text") as mock_write:
        with patch("os.chmod") as mock_chmod:
            config_generator.write_config_to_file(test_config)

            # Assertions
            mock_write.assert_called_once_with(test_config, encoding="utf-8")
            mock_chmod.assert_called_once()


def test_write_config_to_file_permission_error(config_generator: ConfigGenerator):
    """Test handling of permission errors during file write."""
    test_config = "model_list: []\n"

    from src.services.litellm_config_generator import ConfigGenerationError
    with patch("pathlib.Path.write_text", side_effect=PermissionError("Access denied")):
        with pytest.raises(ConfigGenerationError, match="File write failed"):
            config_generator.write_config_to_file(test_config)


# ============================================================================
# REGENERATE CONFIG WORKFLOW TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_regenerate_config_full_workflow(
    config_generator: ConfigGenerator,
    mock_db: AsyncMock,
    sample_providers_and_models,
):
    """Test complete config regeneration workflow."""
    openai_provider, anthropic_provider, models = sample_providers_and_models

    # Set up models relationship
    openai_provider.models = [m for m in models if m.provider_id == 1]
    anthropic_provider.models = [m for m in models if m.provider_id == 2]

    # Mock database query with unique() support
    provider_result = MagicMock()
    mock_scalars = MagicMock()
    mock_unique = MagicMock()
    mock_unique.all.return_value = [openai_provider, anthropic_provider]
    mock_scalars.unique.return_value = mock_unique
    provider_result.scalars.return_value = mock_scalars

    mock_db.execute.return_value = provider_result

    # Mock file operations
    with patch("pathlib.Path.exists", return_value=True):
        with patch("pathlib.Path.write_text"):
            with patch("shutil.copy2"):
                with patch("os.chmod"):
                    result = await config_generator.regenerate_config()

                    # Assertions
                    assert result["success"] is True
                    assert "backup_path" in result
                    assert "config_path" in result
                    assert result["restart_required"] is True
                    assert "docker-compose restart" in result["restart_command"]
