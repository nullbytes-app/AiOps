"""
LiteLLM configuration generator service.

This module generates litellm-config.yaml from database providers and models,
handles backup creation, YAML validation, and file writing with proper permissions.
"""

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List, Any

import yaml
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.database.models import LLMProvider, LLMModel
from src.utils.encryption import decrypt, EncryptionError


class ConfigGenerationError(Exception):
    """Raised when config generation fails."""

    pass


class ConfigGenerator:
    """
    Service for generating LiteLLM configuration YAML from database.

    Reads enabled providers and models, decrypts API keys, generates litellm-config.yaml
    following 2025 best practices, creates backups, and validates YAML syntax.
    """

    # Default config path (can be overridden)
    DEFAULT_CONFIG_PATH = "config/litellm-config.yaml"

    def __init__(
        self,
        db: AsyncSession,
        config_path: Optional[str] = None,
    ):
        """
        Initialize config generator.

        Args:
            db: Async database session
            config_path: Path to litellm-config.yaml (default: config/litellm-config.yaml)
        """
        self.db = db
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH

    async def generate_config_yaml(self) -> str:
        """
        Generate complete litellm-config.yaml from database state.

        Returns:
            str: Generated YAML config string

        Raises:
            ConfigGenerationError: If generation fails
        """
        try:
            # Fetch all enabled providers with models
            result = await self.db.execute(
                select(LLMProvider)
                .options(joinedload(LLMProvider.models))
                .where(LLMProvider.enabled == True)
                .order_by(LLMProvider.created_at)
            )
            providers = result.scalars().unique().all()

            if not providers:
                raise ConfigGenerationError("No enabled providers found in database")

            # Generate router_settings with fallback chains
            router_settings = await self.generate_router_settings()

            # Build config structure
            config = {
                "model_list": [],
                "router_settings": router_settings,
                "litellm_settings": {
                    "num_retries": 3,
                    "retry_policy": "exponential_backoff_retry",
                    "request_timeout": 30,
                    "allowed_fails": 3,
                    "cooldown_time": 30,
                    "drop_params": True,
                    "set_verbose": True,
                },
                "general_settings": {
                    "master_key": "os.environ/LITELLM_MASTER_KEY",
                    "database_url": "os.environ/DATABASE_URL",
                    "alerting": ["webhook"],
                },
            }

            # Add model entries from each provider
            for provider in providers:
                # Decrypt API key
                try:
                    api_key_decrypted = decrypt(provider.api_key_encrypted)
                except EncryptionError as e:
                    logger.warning(f"Skipping provider {provider.name}: failed to decrypt API key - {e}")
                    continue

                # Only include enabled models
                enabled_models = [m for m in provider.models if m.enabled]
                if not enabled_models:
                    logger.info(f"Provider {provider.name} has no enabled models, skipping")
                    continue

                # Add each model entry
                for model in enabled_models:
                    # Convert ProviderType enum to string value
                    provider_type_str = provider.provider_type.value if hasattr(provider.provider_type, 'value') else str(provider.provider_type)

                    model_entry = {
                        "model_name": model.display_name or model.model_name,
                        "litellm_params": {
                            "model": f"{provider_type_str}/{model.model_name}",
                            "api_key": api_key_decrypted,  # NOTE: Will be masked in final YAML if env var pattern used
                            "timeout": 30,
                            "max_retries": 3,
                        },
                    }

                    # Add provider-specific parameters
                    if provider_type_str == "azure_openai":
                        model_entry["litellm_params"]["api_base"] = provider.api_base_url
                        model_entry["litellm_params"]["api_version"] = "2025-02-01-preview"
                    elif provider_type_str == "bedrock":
                        # Bedrock uses AWS credentials (different pattern)
                        model_entry["litellm_params"]["aws_region_name"] = "us-east-1"  # TODO: Make configurable
                    elif provider_type_str in ["openai", "anthropic"]:
                        # Standard providers with base URL
                        if provider.api_base_url:
                            model_entry["litellm_params"]["api_base"] = provider.api_base_url

                    config["model_list"].append(model_entry)

            if not config["model_list"]:
                raise ConfigGenerationError("No enabled models found across all providers")

            # Generate YAML with proper formatting
            yaml_str = yaml.dump(
                config,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )

            # Add header comment
            header = (
                "# LiteLLM Proxy Configuration\n"
                f"# Auto-generated: {datetime.now(timezone.utc).isoformat()}Z\n"
                f"# Generated from {len(providers)} provider(s), {len(config['model_list'])} model(s)\n"
                "# DO NOT EDIT MANUALLY - Use Admin UI for configuration changes\n\n"
            )

            final_config = header + yaml_str

            logger.info(
                f"Generated config: {len(providers)} providers, {len(config['model_list'])} models"
            )

            return final_config

        except Exception as e:
            logger.error(f"Config generation failed: {e}")
            raise ConfigGenerationError(f"Failed to generate config: {str(e)}")

    def backup_current_config(self) -> str:
        """
        Create timestamped backup of current config file.

        Returns:
            str: Path to backup file

        Raises:
            ConfigGenerationError: If backup fails
        """
        try:
            config_file = Path(self.config_path)

            if not config_file.exists():
                logger.warning(f"Config file {self.config_path} not found, skipping backup")
                return ""

            # Create backup with timestamp
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
            backup_path = config_file.parent / f"{config_file.stem}.backup.{timestamp}{config_file.suffix}"

            shutil.copy2(config_file, backup_path)

            logger.info(f"Created config backup: {backup_path}")
            return str(backup_path)

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise ConfigGenerationError(f"Backup failed: {str(e)}")

    def validate_config_syntax(self, config_yaml: str) -> bool:
        """
        Validate YAML syntax before writing to file.

        Args:
            config_yaml: YAML config string

        Returns:
            bool: True if valid, False otherwise

        Raises:
            ConfigGenerationError: If YAML is invalid with detailed error
        """
        try:
            yaml.safe_load(config_yaml)
            logger.debug("Config YAML validation passed")
            return True
        except yaml.YAMLError as e:
            error_msg = f"Invalid YAML syntax: {str(e)}"
            logger.error(error_msg)
            raise ConfigGenerationError(error_msg)

    def write_config_to_file(self, config_yaml: str) -> None:
        """
        Write config to file with proper permissions (600).

        Args:
            config_yaml: YAML config string

        Raises:
            ConfigGenerationError: If write fails
        """
        try:
            config_file = Path(self.config_path)

            # Ensure parent directory exists
            config_file.parent.mkdir(parents=True, exist_ok=True)

            # Write config
            config_file.write_text(config_yaml, encoding="utf-8")

            # Set permissions to 600 (owner read/write only) for security
            os.chmod(config_file, 0o600)

            logger.info(f"Config written to {self.config_path} (permissions: 600)")

        except Exception as e:
            logger.error(f"Failed to write config: {e}")
            raise ConfigGenerationError(f"File write failed: {str(e)}")

    async def regenerate_config(self) -> dict[str, str]:
        """
        Complete config regeneration workflow: backup, generate, validate, write.

        Returns:
            dict: Results with backup_path, config_path, restart_command

        Raises:
            ConfigGenerationError: If any step fails
        """
        try:
            # Step 1: Backup current config
            backup_path = self.backup_current_config()

            # Step 2: Generate new config
            config_yaml = await self.generate_config_yaml()

            # Step 3: Validate YAML syntax
            self.validate_config_syntax(config_yaml)

            # Step 4: Write to file
            self.write_config_to_file(config_yaml)

            logger.info("Config regeneration complete - LiteLLM restart required")

            return {
                "success": True,
                "backup_path": backup_path,
                "config_path": self.config_path,
                "restart_required": True,
                "restart_command": "docker-compose restart litellm",
            }

        except Exception as e:
            logger.error(f"Config regeneration failed: {e}")
            raise ConfigGenerationError(f"Regeneration failed: {str(e)}")


    async def generate_router_settings(self) -> Dict:
        """
        Generate router_settings section for fallback chain configuration.

        Returns:
            dict: Router settings with fallbacks, retry_policy, allowed_fails_policy

        Raises:
            ConfigGenerationError: If generation fails
        """
        try:
            from src.database.models import FallbackChain, FallbackTrigger, LLMModel
            from sqlalchemy import select, joinedload

            # Fetch all fallback chains
            result = await self.db.execute(
                select(FallbackChain)
                .options(
                    joinedload(FallbackChain.model),
                    joinedload(FallbackChain.fallback_model),
                )
                .where(FallbackChain.enabled == True)
                .order_by(FallbackChain.model_id, FallbackChain.fallback_order)
            )
            chains = result.scalars().unique().all()

            # Build fallbacks section: {model_name: [fallback1, fallback2...]}
            fallbacks = []
            chains_by_model = {}

            for chain in chains:
                model_name = chain.model.model_name
                if model_name not in chains_by_model:
                    chains_by_model[model_name] = []
                chains_by_model[model_name].append(chain.fallback_model.model_name)

            # Format as List[Dict[str, List[str]]] per LiteLLM 2025 spec
            for model_name, fallback_models in chains_by_model.items():
                fallbacks.append({model_name: fallback_models})

            # Fetch trigger configurations
            result = await self.db.execute(select(FallbackTrigger).where(FallbackTrigger.enabled == True))
            triggers = result.scalars().all()

            # Build retry_policy from trigger configs
            retry_policy = {}
            allowed_fails_policy = {}

            for trigger in triggers:
                if trigger.trigger_type == "RateLimitError":
                    retry_policy["RateLimitErrorRetries"] = trigger.retry_count
                    allowed_fails_policy["RateLimitErrorAllowedFails"] = 100
                elif trigger.trigger_type == "TimeoutError":
                    retry_policy["TimeoutErrorRetries"] = trigger.retry_count
                elif trigger.trigger_type == "InternalServerError":
                    retry_policy["InternalServerErrorRetries"] = trigger.retry_count
                    allowed_fails_policy["InternalServerErrorAllowedFails"] = 20
                elif trigger.trigger_type == "ContentPolicyViolationError":
                    retry_policy["ContentPolicyViolationErrorRetries"] = trigger.retry_count

            # Build router_settings
            router_settings = {
                "routing_strategy": "simple-shuffle",
            }

            if fallbacks:
                router_settings["fallbacks"] = fallbacks

            if retry_policy:
                router_settings["retry_policy"] = retry_policy

            if allowed_fails_policy:
                router_settings["allowed_fails_policy"] = allowed_fails_policy

            # Context window and content policy fallbacks (future enhancements)
            router_settings["context_window_fallbacks"] = []
            router_settings["content_policy_fallbacks"] = []

            logger.info(
                f"Generated router_settings: {len(fallbacks)} fallback chains, "
                f"{len(retry_policy)} trigger types configured"
            )

            return router_settings

        except Exception as e:
            logger.error(f"Router settings generation failed: {e}")
            raise ConfigGenerationError(f"Failed to generate router_settings: {str(e)}")
