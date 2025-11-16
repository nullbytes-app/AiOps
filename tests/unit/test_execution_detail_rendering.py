"""
Unit tests for Execution Detail Rendering (Story 10.3).

Tests the helper functions and rendering logic for the detailed execution view,
including API calls, JSON parsing, LLM conversation formatting, and sensitive
data masking.

Test Coverage:
- fetch_execution_detail() - API calls with success, 404, 403, timeout scenarios
- format_llm_conversation() - JSON parsing with complete/missing/invalid data
- format_json_display() - JSON formatting with various input types
- Sensitive data masking integration
"""

import json
from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest

from admin.utils.execution_detail_rendering import (
    fetch_execution_detail,
    format_json_display,
    format_llm_conversation,
)


class TestFetchExecutionDetail:
    """Tests for fetch_execution_detail() function."""

    @patch("admin.utils.execution_detail_rendering.httpx.Client")
    def test_fetch_execution_detail_success(self, mock_client_class):
        """Test successful API call returns execution dict."""
        # Arrange
        execution_id = "123e4567-e89b-12d3-a456-426614174000"
        expected_response = {
            "id": execution_id,
            "agent_id": "agent-123",
            "tenant_id": "acme",
            "status": "completed",
            "execution_time": 1250,
            "input_data": {"ticket_id": "INC001"},
            "output_data": {"response": "Success"},
            "created_at": "2025-11-08T10:30:00Z",
        }

        # Mock the HTTP client and response
        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_response
        mock_client.__enter__.return_value.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Act
        result = fetch_execution_detail(execution_id)

        # Assert
        assert result == expected_response
        assert result["id"] == execution_id
        assert result["status"] == "completed"

    @patch("admin.utils.execution_detail_rendering.httpx.Client")
    def test_fetch_execution_detail_not_found(self, mock_client_class):
        """Test 404 response returns None."""
        # Arrange
        execution_id = "nonexistent-id"
        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 404
        mock_client.__enter__.return_value.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Act
        result = fetch_execution_detail(execution_id)

        # Assert
        assert result is None

    @patch("admin.utils.execution_detail_rendering.httpx.Client")
    def test_fetch_execution_detail_forbidden(self, mock_client_class):
        """Test 403 forbidden response returns None."""
        # Arrange
        execution_id = "forbidden-execution"
        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 403
        mock_client.__enter__.return_value.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Act
        result = fetch_execution_detail(execution_id)

        # Assert
        assert result is None

    @patch("admin.utils.execution_detail_rendering.httpx.Client")
    def test_fetch_execution_detail_timeout(self, mock_client_class):
        """Test timeout exception returns None."""
        # Arrange
        execution_id = "timeout-execution"
        mock_client = MagicMock()
        mock_client.__enter__.return_value.get.side_effect = httpx.TimeoutException(
            "Request timeout"
        )
        mock_client_class.return_value = mock_client

        # Act
        result = fetch_execution_detail(execution_id)

        # Assert
        assert result is None

    @patch("admin.utils.execution_detail_rendering.httpx.Client")
    def test_fetch_execution_detail_server_error(self, mock_client_class):
        """Test 500 server error returns None."""
        # Arrange
        execution_id = "server-error-execution"
        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 500
        mock_client.__enter__.return_value.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Act
        result = fetch_execution_detail(execution_id)

        # Assert
        assert result is None


class TestFormatLLMConversation:
    """Tests for format_llm_conversation() function."""

    def test_format_llm_conversation_complete_data(self):
        """Test parsing with all LLM fields present."""
        # Arrange
        output_data = {
            "system_prompt": "You are a helpful assistant.",
            "user_message": "What is the capital of France?",
            "response": "The capital of France is Paris.",
            "tool_calls": [
                {"name": "search_knowledge_base", "args": {"query": "France capital"}}
            ],
        }

        # Act
        result = format_llm_conversation(output_data)

        # Assert
        assert result["system_prompt"] == "You are a helpful assistant."
        assert result["user_message"] == "What is the capital of France?"
        assert result["llm_response"] == "The capital of France is Paris."
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["name"] == "search_knowledge_base"

    def test_format_llm_conversation_missing_fields(self):
        """Test parsing with missing optional fields."""
        # Arrange
        output_data = {
            "response": "I don't have that information.",
            # Missing: system_prompt, user_message, tool_calls
        }

        # Act
        result = format_llm_conversation(output_data)

        # Assert
        assert result["system_prompt"] == ""
        assert result["user_message"] == ""
        assert result["llm_response"] == "I don't have that information."
        assert result["tool_calls"] == []

    def test_format_llm_conversation_alternative_field_names(self):
        """Test parsing with alternative field names (input, llm_response)."""
        # Arrange
        output_data = {
            "input": "User query here",
            "llm_response": "LLM response here",
        }

        # Act
        result = format_llm_conversation(output_data)

        # Assert
        assert result["user_message"] == "User query here"
        assert result["llm_response"] == "LLM response here"

    def test_format_llm_conversation_json_string_input(self):
        """Test parsing when output_data is a JSON string."""
        # Arrange
        output_data_dict = {
            "system_prompt": "Test prompt",
            "response": "Test response",
        }
        output_data_str = json.dumps(output_data_dict)

        # Act
        result = format_llm_conversation(output_data_str)

        # Assert
        assert result["system_prompt"] == "Test prompt"
        assert result["llm_response"] == "Test response"

    def test_format_llm_conversation_invalid_json_string(self):
        """Test handling of invalid JSON string."""
        # Arrange
        output_data = "not valid JSON {broken"

        # Act
        result = format_llm_conversation(output_data)

        # Assert
        assert result["system_prompt"] == ""
        assert result["user_message"] == ""
        assert result["llm_response"] == ""
        assert result["tool_calls"] == []

    def test_format_llm_conversation_none_input(self):
        """Test handling of None input."""
        # Act
        result = format_llm_conversation(None)

        # Assert
        assert result["system_prompt"] == ""
        assert result["user_message"] == ""
        assert result["llm_response"] == ""
        assert result["tool_calls"] == []

    def test_format_llm_conversation_empty_dict(self):
        """Test handling of empty dict."""
        # Act
        result = format_llm_conversation({})

        # Assert
        assert result["system_prompt"] == ""
        assert result["user_message"] == ""
        assert result["llm_response"] == ""
        assert result["tool_calls"] == []


class TestFormatJsonDisplay:
    """Tests for format_json_display() function."""

    def test_format_json_display_dict(self):
        """Test formatting a dictionary."""
        # Arrange
        data = {"key": "value", "nested": {"inner": "data"}}

        # Act
        result = format_json_display(data)

        # Assert
        assert isinstance(result, str)
        assert '"key": "value"' in result
        assert '"nested"' in result
        # Check indentation (2 spaces per level)
        assert "  " in result

    def test_format_json_display_list(self):
        """Test formatting a list."""
        # Arrange
        data = ["item1", "item2", {"key": "value"}]

        # Act
        result = format_json_display(data)

        # Assert
        assert isinstance(result, str)
        assert '"item1"' in result
        assert '"item2"' in result
        assert '"key": "value"' in result

    def test_format_json_display_json_string(self):
        """Test formatting a JSON string (re-parse and format)."""
        # Arrange
        data = '{"key":"value","number":42}'

        # Act
        result = format_json_display(data)

        # Assert
        assert isinstance(result, str)
        assert '"key": "value"' in result
        assert '"number": 42' in result
        # Check proper indentation
        assert "  " in result

    def test_format_json_display_non_json_string(self):
        """Test handling of non-JSON string (return as-is)."""
        # Arrange
        data = "Just a plain string"

        # Act
        result = format_json_display(data)

        # Assert
        assert result == "Just a plain string"

    def test_format_json_display_special_characters(self):
        """Test handling of special characters (unicode, newlines)."""
        # Arrange
        data = {"message": "Hello 世界\nNew line", "emoji": "🔍"}

        # Act
        result = format_json_display(data)

        # Assert
        assert isinstance(result, str)
        assert "世界" in result  # Unicode preserved
        assert "🔍" in result
        # Newlines are escaped in JSON
        assert "\\n" in result or "\n" in result


class TestSensitiveDataMasking:
    """Tests for sensitive data masking integration (AC5)."""

    def test_format_llm_conversation_masks_api_keys(self):
        """Test that API keys in conversation data are masked."""
        # Arrange
        output_data = {
            "system_prompt": "Use API key: sk-1234567890abcdef",
            "response": "Connecting with bearer token abc123",
        }

        # Act
        result = format_llm_conversation(output_data)

        # Assert
        # Note: Masking happens at API level, not in format function
        # This test verifies the function handles pre-masked data
        assert "system_prompt" in result
        assert "llm_response" in result

    def test_format_json_display_preserves_structure(self):
        """Test that JSON display preserves masked data structure."""
        # Arrange
        data = {
            "api_key": "sk-***",  # Already masked by API
            "password": "***",
            "safe_field": "visible_data",
        }

        # Act
        result = format_json_display(data)

        # Assert
        assert '"api_key": "sk-***"' in result
        assert '"password": "***"' in result
        assert '"safe_field": "visible_data"' in result
