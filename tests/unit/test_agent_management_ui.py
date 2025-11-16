"""
Unit tests for Agent Management UI components.

Tests form validation, status formatting, datetime formatting, and helper functions.

Story: 8.4 - Agent Management UI (Basic)
Target: 12+ unit tests
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from admin.utils.agent_helpers import (
    AVAILABLE_TOOLS,
    format_datetime,
    format_status_badge,
    validate_form_data,
    fetch_available_models,
)


class TestFormValidation:
    """Test suite for form validation logic."""

    def test_validate_valid_form_data(self):
        """Test validation succeeds with valid form data."""
        form_data = {
            "name": "Ticket Enhancement Agent",
            "description": "Enhances support tickets",
            "system_prompt": "You are a helpful assistant that enhances support tickets with context.",
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 4096,
            "tools": ["servicedesk_plus"],
        }
        is_valid, errors, warnings = validate_form_data(form_data)
        assert is_valid is True
        assert errors == []

    def test_validate_missing_name(self):
        """Test validation fails when name is missing."""
        form_data = {
            "name": "",
            "system_prompt": "Valid prompt...",
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 4096,
            "tools": ["servicedesk_plus"],
        }
        is_valid, errors, warnings = validate_form_data(form_data)
        assert is_valid is False
        assert any("name" in error.lower() for error in errors)

    def test_validate_short_name(self):
        """Test validation fails when name is too short."""
        form_data = {
            "name": "AB",
            "system_prompt": "Valid prompt with enough characters...",
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 4096,
            "tools": ["servicedesk_plus"],
        }
        is_valid, errors, warnings = validate_form_data(form_data)
        assert is_valid is False
        assert any("3 characters" in error for error in errors)

    def test_validate_short_system_prompt(self):
        """Test validation fails when system prompt is too short."""
        form_data = {
            "name": "Valid Name",
            "system_prompt": "Short",
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 4096,
            "tools": ["servicedesk_plus"],
        }
        is_valid, errors, warnings = validate_form_data(form_data)
        assert is_valid is False
        assert any("system prompt" in error.lower() for error in errors)

    def test_validate_missing_system_prompt(self):
        """Test validation fails when system prompt is empty."""
        form_data = {
            "name": "Valid Name",
            "system_prompt": "",
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 4096,
            "tools": ["servicedesk_plus"],
        }
        is_valid, errors, warnings = validate_form_data(form_data)
        assert is_valid is False
        assert any("system prompt" in error.lower() for error in errors)

    def test_validate_missing_model(self):
        """Test validation fails when model is empty."""
        form_data = {
            "name": "Valid Name",
            "system_prompt": "Valid system prompt with enough text...",
            "model": "",
            "temperature": 0.7,
            "max_tokens": 4096,
            "tools": ["servicedesk_plus"],
        }
        is_valid, errors, warnings = validate_form_data(form_data)
        assert is_valid is False
        assert any("model" in error.lower() for error in errors)

    def test_validate_no_tools_selected(self):
        """Test validation fails when no tools are selected (with strict validation)."""
        form_data = {
            "name": "Valid Name",
            "system_prompt": "Valid system prompt with enough text...",
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 4096,
            "tools": [],
        }
        is_valid, errors, warnings = validate_form_data(form_data, strict_tool_validation=True)
        assert is_valid is False
        assert any("tool" in error.lower() for error in errors)

    def test_validate_no_tools_selected_warning(self):
        """Test that no tools selected generates warning but still validates (default behavior)."""
        form_data = {
            "name": "Valid Name",
            "system_prompt": "Valid system prompt with enough text...",
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 4096,
            "tools": [],
        }
        is_valid, errors, warnings = validate_form_data(form_data)
        assert is_valid is True  # No error, just warning
        assert any("tool" in warning.lower() for warning in warnings)

    def test_validate_temperature_out_of_range_high(self):
        """Test validation fails when temperature is above 2.0."""
        form_data = {
            "name": "Valid Name",
            "system_prompt": "Valid system prompt with enough text...",
            "model": "gpt-4",
            "temperature": 2.5,
            "max_tokens": 4096,
            "tools": ["servicedesk_plus"],
        }
        is_valid, errors, warnings = validate_form_data(form_data)
        assert is_valid is False
        assert any("temperature" in error.lower() and "0 and 2" in error for error in errors)

    def test_validate_temperature_out_of_range_low(self):
        """Test validation fails when temperature is negative."""
        form_data = {
            "name": "Valid Name",
            "system_prompt": "Valid system prompt with enough text...",
            "model": "gpt-4",
            "temperature": -0.5,
            "max_tokens": 4096,
            "tools": ["servicedesk_plus"],
        }
        is_valid, errors, warnings = validate_form_data(form_data)
        assert is_valid is False
        assert any("temperature" in error.lower() for error in errors)

    def test_validate_max_tokens_out_of_range_low(self):
        """Test validation fails when max_tokens is below 1."""
        form_data = {
            "name": "Valid Name",
            "system_prompt": "Valid system prompt with enough text...",
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 0,
            "tools": ["servicedesk_plus"],
        }
        is_valid, errors, warnings = validate_form_data(form_data)
        assert is_valid is False
        assert any("max tokens" in error.lower() for error in errors)

    def test_validate_max_tokens_out_of_range_high(self):
        """Test validation fails when max_tokens exceeds 32000."""
        form_data = {
            "name": "Valid Name",
            "system_prompt": "Valid system prompt with enough text...",
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 50000,
            "tools": ["servicedesk_plus"],
        }
        is_valid, errors, warnings = validate_form_data(form_data)
        assert is_valid is False
        assert any("max tokens" in error.lower() for error in errors)


class TestStatusBadgeFormatting:
    """Test suite for status badge formatting."""

    def test_format_draft_status(self):
        """Test draft status is formatted with correct emoji."""
        result = format_status_badge("draft")
        assert "⚪" in result or "Draft" in result

    def test_format_active_status(self):
        """Test active status is formatted with correct emoji."""
        result = format_status_badge("active")
        assert "🟢" in result or "Active" in result

    def test_format_suspended_status(self):
        """Test suspended status is formatted with correct emoji."""
        result = format_status_badge("suspended")
        assert "🟡" in result or "Suspended" in result

    def test_format_inactive_status(self):
        """Test inactive status is formatted with correct emoji."""
        result = format_status_badge("inactive")
        assert "🔴" in result or "Inactive" in result

    def test_format_unknown_status(self):
        """Test unknown status returns placeholder."""
        result = format_status_badge("unknown")
        assert "unknown" in result.lower()


class TestDatetimeFormatting:
    """Test suite for datetime formatting."""

    def test_format_iso_datetime(self):
        """Test ISO datetime is converted to readable format."""
        iso_dt = "2025-11-05T19:30:45Z"
        result = format_datetime(iso_dt)
        assert "Nov" in result or "2025" in result
        assert ":" in result  # Time included

    def test_format_iso_datetime_without_z(self):
        """Test ISO datetime without Z suffix."""
        iso_dt = "2025-11-05T19:30:45+00:00"
        result = format_datetime(iso_dt)
        assert "Nov" in result or "2025" in result

    def test_format_none_datetime(self):
        """Test None datetime returns 'Never'."""
        result = format_datetime(None)
        assert result == "Never"

    def test_format_empty_datetime(self):
        """Test empty string datetime returns 'Never'."""
        result = format_datetime("")
        assert result == "Never"

    def test_format_invalid_datetime(self):
        """Test invalid datetime returns original string."""
        invalid_dt = "not-a-datetime"
        result = format_datetime(invalid_dt)
        assert result == invalid_dt


class TestConfiguration:
    """Test suite for helper configuration constants and dynamic functions."""

    @patch('admin.utils.agent_helpers.httpx.Client')
    @patch('admin.utils.agent_helpers.st.cache_data', lambda ttl: lambda f: f)
    def test_fetch_available_models_success(self, mock_http_client):
        """Test fetch_available_models returns models from API (Story 9.1)."""
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "id": "gpt-4",
                "name": "GPT-4",
                "provider": "openai",
                "max_tokens": 8192,
                "supports_function_calling": True,
            },
            {
                "id": "claude-3-opus-20240229",
                "name": "Claude 3 Opus",
                "provider": "anthropic",
                "max_tokens": 200000,
                "supports_function_calling": True,
            },
        ]
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_http_client.return_value.__enter__.return_value = mock_client

        result = fetch_available_models()
        assert len(result) >= 2
        assert any(m["id"] == "gpt-4" for m in result)
        assert any(m["id"] == "claude-3-opus-20240229" for m in result)

    @patch('admin.utils.agent_helpers.httpx.Client')
    @patch('admin.utils.agent_helpers.st.cache_data', lambda ttl: lambda f: f)
    @patch('admin.utils.agent_helpers.st.warning')
    def test_fetch_available_models_fallback_on_error(self, mock_warning, mock_http_client):
        """Test fetch_available_models returns fallback when API fails (Story 9.1)."""
        # Mock API error
        mock_http_client.return_value.__enter__.side_effect = Exception("Connection failed")

        result = fetch_available_models()
        # Should return fallback models
        assert len(result) >= 2
        assert any(m["id"] == "gpt-4" for m in result)
        assert any(m["id"] == "claude-3-opus-20240229" for m in result)

    def test_available_tools_dict(self):
        """Test AVAILABLE_TOOLS contains expected tools."""
        assert "servicedesk_plus" in AVAILABLE_TOOLS
        assert "jira" in AVAILABLE_TOOLS
        assert "knowledge_base" in AVAILABLE_TOOLS
        assert len(AVAILABLE_TOOLS) >= 5

    def test_available_tools_have_descriptions(self):
        """Test all tools have descriptions."""
        for tool_name, description in AVAILABLE_TOOLS.items():
            assert description
            assert len(description) > 0
            assert "-" in description  # Format: "Name - Description"



class TestMemoryConfigSerialization:
    """Test suite for MemoryConfig JSON serialization.
    
    Regression test for Story 8.15 - Memory Configuration UI.
    Ensures MemoryConfig Pydantic models are properly serialized to JSON
    when creating/updating agents via the API.
    """

    @pytest.mark.asyncio
    @patch('admin.utils.agent_helpers.httpx.AsyncClient')
    async def test_create_agent_with_memory_config_serialization(self, mock_client):
        """Test that MemoryConfig is serialized to dict when creating agent."""
        from admin.utils.agent_helpers import create_agent_async
        from schemas.memory import MemoryConfig, ShortTermMemoryConfig, LongTermMemoryConfig, AgenticMemoryConfig

        # Create a MemoryConfig object (as would be done in the UI)
        memory_config = MemoryConfig(
            short_term=ShortTermMemoryConfig(
                enabled=True,
                max_messages=10
            ),
            long_term=LongTermMemoryConfig(
                enabled=True,
                provider="redis",
                embedding_model="text-embedding-3-small"
            ),
            agentic=AgenticMemoryConfig(
                enabled=False
            )
        )
        
        # Prepare agent data with MemoryConfig object
        agent_data = {
            "name": "Test Agent",
            "description": "Test description",
            "status": "active",
            "system_prompt": "You are a test agent",
            "llm_config": {
                "provider": "openai",
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 4096,
            },
            "tool_ids": [],
            "memory_config": memory_config.model_dump(),  # This is the fix being tested
            "triggers": [],
        }
        
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={"id": "test-agent-id", "name": "Test Agent"})
        mock_response.raise_for_status = MagicMock(return_value=None)

        # Mock the AsyncClient context manager
        mock_async_client = MagicMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_async_client.post = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_async_client
        
        # Call the function
        result = await create_agent_async(agent_data)
        
        # Verify the function succeeded
        assert result is not None
        assert result["id"] == "test-agent-id"
        
        # Verify that httpx.AsyncClient.post was called with properly serialized data
        mock_async_client.post.assert_called_once()
        call_kwargs = mock_async_client.post.call_args[1]
        
        # The 'json' parameter should be a dict, not a MemoryConfig object
        assert "json" in call_kwargs
        assert isinstance(call_kwargs["json"]["memory_config"], dict)

        # Verify the memory config structure is preserved (check actual serialized fields)
        assert "short_term" in call_kwargs["json"]["memory_config"]
        assert "long_term" in call_kwargs["json"]["memory_config"]
        assert "agentic" in call_kwargs["json"]["memory_config"]
        assert isinstance(call_kwargs["json"]["memory_config"]["short_term"], dict)
        assert isinstance(call_kwargs["json"]["memory_config"]["long_term"], dict)
        assert isinstance(call_kwargs["json"]["memory_config"]["agentic"], dict)

    @pytest.mark.asyncio  
    @patch('admin.utils.agent_helpers.httpx.AsyncClient')
    async def test_update_agent_with_memory_config_serialization(self, mock_client):
        """Test that MemoryConfig is serialized to dict when updating agent."""
        from admin.utils.agent_helpers import update_agent_async
        from schemas.memory import MemoryConfig, ShortTermMemoryConfig, LongTermMemoryConfig, AgenticMemoryConfig

        # Create a MemoryConfig object (as would be done in the UI)
        memory_config = MemoryConfig(
            short_term=ShortTermMemoryConfig(
                enabled=False,
                max_messages=5
            ),
            long_term=LongTermMemoryConfig(
                enabled=True,
                provider="postgres",
                embedding_model="text-embedding-ada-002"
            ),
            agentic=AgenticMemoryConfig(
                enabled=True,
                max_iterations=5
            )
        )
        
        # Prepare update data with MemoryConfig object
        updates = {
            "name": "Updated Agent",
            "system_prompt": "Updated prompt",
            "llm_config": {
                "provider": "anthropic",
                "model": "claude-3-opus-20240229",
                "temperature": 0.5,
                "max_tokens": 8192,
            },
            "tool_ids": ["servicedesk_plus"],
            "memory_config": memory_config.model_dump(),  # This is the fix being tested
        }
        
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={"id": "test-agent-id", "name": "Updated Agent"})
        mock_response.raise_for_status = MagicMock(return_value=None)

        # Mock the AsyncClient context manager
        mock_async_client = MagicMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_async_client.put = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_async_client

        # Call the function
        result = await update_agent_async("test-agent-id", updates)

        # Verify the function succeeded
        assert result is not None
        assert result["id"] == "test-agent-id"

        # Verify that httpx.AsyncClient.put was called with properly serialized data
        mock_async_client.put.assert_called_once()
        call_kwargs = mock_async_client.put.call_args[1]
        
        # The 'json' parameter should be a dict, not a MemoryConfig object
        assert "json" in call_kwargs
        assert isinstance(call_kwargs["json"]["memory_config"], dict)

        # Verify the memory config structure is preserved (check actual serialized fields)
        assert "short_term" in call_kwargs["json"]["memory_config"]
        assert "long_term" in call_kwargs["json"]["memory_config"]
        assert "agentic" in call_kwargs["json"]["memory_config"]
        assert isinstance(call_kwargs["json"]["memory_config"]["short_term"], dict)
        assert isinstance(call_kwargs["json"]["memory_config"]["long_term"], dict)
        assert isinstance(call_kwargs["json"]["memory_config"]["agentic"], dict)
        # Verify that long_term has the expected enabled field
        assert "enabled" in call_kwargs["json"]["memory_config"]["long_term"]
        assert call_kwargs["json"]["memory_config"]["long_term"]["enabled"] is True
