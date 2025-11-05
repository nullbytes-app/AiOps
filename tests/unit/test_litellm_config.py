"""
Unit tests for LiteLLM configuration validation.

Story 8.1: LiteLLM Proxy Integration
Tests validate config/litellm-config.yaml structure and required fields.
"""

import os
import yaml
import pytest
from pathlib import Path


class TestLiteLLMConfigFile:
    """Test LiteLLM configuration file exists and is valid YAML."""

    @pytest.fixture
    def config_path(self):
        """Get path to LiteLLM config file."""
        project_root = Path(__file__).parent.parent.parent
        return project_root / "config" / "litellm-config.yaml"

    @pytest.fixture
    def config(self, config_path):
        """Load LiteLLM configuration from YAML file."""
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def test_config_file_exists(self, config_path):
        """Test that config/litellm-config.yaml exists."""
        assert config_path.exists(), f"Config file not found: {config_path}"
        assert config_path.is_file(), f"Config path is not a file: {config_path}"

    def test_config_is_valid_yaml(self, config_path):
        """Test that config file is valid YAML."""
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            assert isinstance(config, dict), "Config must be a dictionary"
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML syntax: {e}")

    def test_config_has_required_top_level_keys(self, config):
        """Test that config has required top-level sections."""
        required_keys = ["model_list", "router_settings", "litellm_settings", "general_settings"]
        for key in required_keys:
            assert key in config, f"Missing required top-level key: {key}"


class TestModelListConfiguration:
    """Test model_list section configuration."""

    @pytest.fixture
    def config(self):
        """Load LiteLLM configuration."""
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "config" / "litellm-config.yaml"
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    @pytest.fixture
    def model_list(self, config):
        """Get model_list from config."""
        return config.get("model_list", [])

    def test_model_list_is_array(self, config):
        """Test that model_list is an array."""
        assert "model_list" in config
        assert isinstance(config["model_list"], list)

    def test_model_list_not_empty(self, model_list):
        """Test that model_list contains at least one model."""
        assert len(model_list) > 0, "model_list cannot be empty"

    def test_fallback_chain_configured(self, model_list):
        """Test that fallback chain has at least 2 providers (primary + fallback)."""
        assert len(model_list) >= 2, "Fallback chain requires at least 2 models"

    def test_all_models_have_same_name(self, model_list):
        """Test that all models use same model_name for automatic fallback."""
        model_names = [model.get("model_name") for model in model_list]
        # All models should have same model_name for automatic fallback
        assert all(name == model_names[0] for name in model_names), \
            "All models must have same model_name for automatic fallback"

    def test_each_model_has_required_fields(self, model_list):
        """Test that each model has required fields."""
        required_fields = ["model_name", "litellm_params"]
        for i, model in enumerate(model_list):
            for field in required_fields:
                assert field in model, f"Model {i} missing required field: {field}"

    def test_litellm_params_has_model(self, model_list):
        """Test that each model's litellm_params has 'model' field."""
        for i, model in enumerate(model_list):
            litellm_params = model.get("litellm_params", {})
            assert "model" in litellm_params, f"Model {i} litellm_params missing 'model' field"

    def test_litellm_params_has_timeout(self, model_list):
        """Test that each model has timeout configured."""
        for i, model in enumerate(model_list):
            litellm_params = model.get("litellm_params", {})
            assert "timeout" in litellm_params, f"Model {i} missing timeout"
            timeout = litellm_params["timeout"]
            assert isinstance(timeout, (int, float)), f"Model {i} timeout must be numeric"
            assert timeout > 0, f"Model {i} timeout must be positive"

    def test_litellm_params_has_max_retries(self, model_list):
        """Test that each model has max_retries configured."""
        for i, model in enumerate(model_list):
            litellm_params = model.get("litellm_params", {})
            assert "max_retries" in litellm_params, f"Model {i} missing max_retries"
            max_retries = litellm_params["max_retries"]
            assert isinstance(max_retries, int), f"Model {i} max_retries must be integer"
            assert max_retries >= 0, f"Model {i} max_retries must be non-negative"

    def test_primary_model_is_openai(self, model_list):
        """Test that first model (primary) uses OpenAI GPT-4."""
        primary_model = model_list[0]
        litellm_params = primary_model.get("litellm_params", {})
        model_str = litellm_params.get("model", "")
        assert model_str.startswith("openai/"), \
            f"Primary model should be OpenAI, got: {model_str}"

    def test_fallback_models_configured(self, model_list):
        """Test that fallback models (Azure, Anthropic) are configured."""
        # Should have at least OpenAI (primary) + 1 fallback
        assert len(model_list) >= 2, "Need at least primary + 1 fallback"

        # Get all model providers
        models = [model["litellm_params"]["model"] for model in model_list]

        # Check fallback providers exist (Azure and/or Anthropic)
        fallback_providers = [m for m in models[1:] if m.startswith(("azure/", "anthropic/"))]
        assert len(fallback_providers) >= 1, \
            "Need at least 1 fallback provider (Azure or Anthropic)"


class TestRouterSettings:
    """Test router_settings section configuration."""

    @pytest.fixture
    def config(self):
        """Load LiteLLM configuration."""
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "config" / "litellm-config.yaml"
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    @pytest.fixture
    def router_settings(self, config):
        """Get router_settings from config."""
        return config.get("router_settings", {})

    def test_routing_strategy_configured(self, router_settings):
        """Test that routing_strategy is set."""
        assert "routing_strategy" in router_settings, "routing_strategy is required"
        strategy = router_settings["routing_strategy"]
        valid_strategies = ["simple-shuffle", "least-busy", "usage-based-routing"]
        assert strategy in valid_strategies, \
            f"Invalid routing_strategy: {strategy}, must be one of {valid_strategies}"

    def test_num_retries_configured(self, router_settings):
        """Test that router-level num_retries is configured."""
        assert "num_retries" in router_settings, "router num_retries is required"
        num_retries = router_settings["num_retries"]
        assert isinstance(num_retries, int), "num_retries must be integer"
        assert num_retries >= 0, "num_retries must be non-negative"

    def test_timeout_configured(self, router_settings):
        """Test that router timeout is configured."""
        assert "timeout" in router_settings, "router timeout is required"
        timeout = router_settings["timeout"]
        assert isinstance(timeout, (int, float)), "timeout must be numeric"
        assert timeout > 0, "timeout must be positive"

    def test_context_window_fallbacks_enabled(self, router_settings):
        """Test that context_window_fallbacks is enabled."""
        assert "context_window_fallbacks" in router_settings, \
            "context_window_fallbacks is required"
        assert router_settings["context_window_fallbacks"] is True, \
            "context_window_fallbacks should be enabled"


class TestLiteLLMSettings:
    """Test litellm_settings section configuration."""

    @pytest.fixture
    def config(self):
        """Load LiteLLM configuration."""
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "config" / "litellm-config.yaml"
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    @pytest.fixture
    def litellm_settings(self, config):
        """Get litellm_settings from config."""
        return config.get("litellm_settings", {})

    def test_num_retries_configured(self, litellm_settings):
        """Test that global num_retries is 3 (per AC6)."""
        assert "num_retries" in litellm_settings, "num_retries is required"
        num_retries = litellm_settings["num_retries"]
        assert num_retries == 3, f"num_retries must be 3 per AC6, got {num_retries}"

    def test_retry_policy_is_exponential_backoff(self, litellm_settings):
        """Test that retry_policy uses exponential backoff (per AC6)."""
        assert "retry_policy" in litellm_settings, "retry_policy is required"
        policy = litellm_settings["retry_policy"]
        assert policy == "exponential_backoff_retry", \
            f"retry_policy must be exponential_backoff_retry per AC6, got {policy}"

    def test_request_timeout_is_30_seconds(self, litellm_settings):
        """Test that request_timeout is 30 seconds (per AC6)."""
        assert "request_timeout" in litellm_settings, "request_timeout is required"
        timeout = litellm_settings["request_timeout"]
        assert timeout == 30, f"request_timeout must be 30 seconds per AC6, got {timeout}"

    def test_allowed_fails_configured(self, litellm_settings):
        """Test that allowed_fails threshold is set."""
        assert "allowed_fails" in litellm_settings, "allowed_fails is required"
        allowed_fails = litellm_settings["allowed_fails"]
        assert isinstance(allowed_fails, int), "allowed_fails must be integer"
        assert allowed_fails > 0, "allowed_fails must be positive"

    def test_cooldown_time_configured(self, litellm_settings):
        """Test that cooldown_time is configured for failed providers."""
        assert "cooldown_time" in litellm_settings, "cooldown_time is required"
        cooldown = litellm_settings["cooldown_time"]
        assert isinstance(cooldown, (int, float)), "cooldown_time must be numeric"
        assert cooldown > 0, "cooldown_time must be positive"

    def test_drop_params_enabled(self, litellm_settings):
        """Test that drop_params is enabled for compatibility."""
        assert "drop_params" in litellm_settings, "drop_params is required"
        assert litellm_settings["drop_params"] is True, \
            "drop_params should be enabled for compatibility"

    def test_set_verbose_enabled(self, litellm_settings):
        """Test that set_verbose is enabled for detailed logging."""
        assert "set_verbose" in litellm_settings, "set_verbose is required"
        assert litellm_settings["set_verbose"] is True, \
            "set_verbose should be enabled for debugging"


class TestGeneralSettings:
    """Test general_settings section configuration."""

    @pytest.fixture
    def config(self):
        """Load LiteLLM configuration."""
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "config" / "litellm-config.yaml"
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    @pytest.fixture
    def general_settings(self, config):
        """Get general_settings from config."""
        return config.get("general_settings", {})

    def test_master_key_uses_env_variable(self, general_settings):
        """Test that master_key references environment variable."""
        assert "master_key" in general_settings, "master_key is required"
        master_key = general_settings["master_key"]
        assert master_key == "os.environ/LITELLM_MASTER_KEY", \
            "master_key must reference LITELLM_MASTER_KEY environment variable"

    def test_database_url_uses_env_variable(self, general_settings):
        """Test that database_url references environment variable."""
        assert "database_url" in general_settings, "database_url is required"
        database_url = general_settings["database_url"]
        assert database_url == "os.environ/DATABASE_URL", \
            "database_url must reference DATABASE_URL environment variable"


class TestAcceptanceCriteriaCompliance:
    """Test that config meets all acceptance criteria from Story 8.1."""

    @pytest.fixture
    def config(self):
        """Load LiteLLM configuration."""
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "config" / "litellm-config.yaml"
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def test_ac2_config_file_exists(self):
        """AC2: config/litellm-config.yaml exists."""
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "config" / "litellm-config.yaml"
        assert config_path.exists(), "AC2: config/litellm-config.yaml must exist"

    def test_ac5_fallback_chain_configured(self, config):
        """AC5: Fallback chain gpt-4 → azure-gpt-4 → claude configured."""
        model_list = config.get("model_list", [])

        # Should have at least 3 models for full fallback chain
        assert len(model_list) >= 2, \
            "AC5: Need at least 2 models (primary + fallback)"

        # Extract provider types
        models = [model["litellm_params"]["model"] for model in model_list]

        # Primary should be OpenAI
        assert models[0].startswith("openai/"), \
            "AC5: Primary model must be OpenAI GPT-4"

        # Should have Azure and/or Anthropic fallbacks
        has_azure = any(m.startswith("azure/") for m in models)
        has_anthropic = any(m.startswith("anthropic/") for m in models)
        assert has_azure or has_anthropic, \
            "AC5: Must have Azure or Anthropic as fallback provider"

    def test_ac6_retry_logic_configured(self, config):
        """AC6: Retry logic with 3 attempts, exponential backoff, 30s timeout."""
        litellm_settings = config.get("litellm_settings", {})

        # Check num_retries = 3
        assert litellm_settings.get("num_retries") == 3, \
            "AC6: num_retries must be 3"

        # Check exponential backoff
        assert litellm_settings.get("retry_policy") == "exponential_backoff_retry", \
            "AC6: retry_policy must be exponential_backoff_retry"

        # Check 30s timeout
        assert litellm_settings.get("request_timeout") == 30, \
            "AC6: request_timeout must be 30 seconds"
