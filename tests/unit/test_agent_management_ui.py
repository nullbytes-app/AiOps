"""
Unit tests for Agent Management UI components.

Tests form validation, status formatting, datetime formatting, and helper functions.

Story: 8.4 - Agent Management UI (Basic)
Target: 12+ unit tests
"""

import pytest
from admin.utils.agent_helpers import (
    AVAILABLE_MODELS,
    AVAILABLE_TOOLS,
    format_datetime,
    format_status_badge,
    validate_form_data,
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
        is_valid, errors = validate_form_data(form_data)
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
        is_valid, errors = validate_form_data(form_data)
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
        is_valid, errors = validate_form_data(form_data)
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
        is_valid, errors = validate_form_data(form_data)
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
        is_valid, errors = validate_form_data(form_data)
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
        is_valid, errors = validate_form_data(form_data)
        assert is_valid is False
        assert any("model" in error.lower() for error in errors)

    def test_validate_no_tools_selected(self):
        """Test validation fails when no tools are selected."""
        form_data = {
            "name": "Valid Name",
            "system_prompt": "Valid system prompt with enough text...",
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 4096,
            "tools": [],
        }
        is_valid, errors = validate_form_data(form_data)
        assert is_valid is False
        assert any("tool" in error.lower() for error in errors)

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
        is_valid, errors = validate_form_data(form_data)
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
        is_valid, errors = validate_form_data(form_data)
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
        is_valid, errors = validate_form_data(form_data)
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
        is_valid, errors = validate_form_data(form_data)
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
    """Test suite for helper configuration constants."""

    def test_available_models_list(self):
        """Test AVAILABLE_MODELS contains expected models."""
        assert "gpt-4" in AVAILABLE_MODELS
        assert "claude-3-5-sonnet" in AVAILABLE_MODELS
        assert len(AVAILABLE_MODELS) >= 5

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
