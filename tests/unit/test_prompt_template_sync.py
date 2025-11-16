"""Unit tests for prompt template synchronization between System Prompt Editor and Agent Management."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import streamlit as st

# Test the new fetch_prompt_templates function


@pytest.fixture
def mock_streamlit_state():
    """Mock Streamlit session state."""
    with patch("streamlit.session_state", new_callable=MagicMock) as mock_state:
        mock_state.get = Mock(return_value="test-tenant")
        yield mock_state


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for API calls."""
    with patch("httpx.Client") as mock_client:
        yield mock_client


def test_fetch_prompt_templates_success(mock_streamlit_state, mock_httpx_client):
    """Test successful template fetch from API."""
    from admin.utils.agent_helpers import fetch_prompt_templates

    # Mock API response
    mock_response = Mock()
    mock_response.json.return_value = {
        "data": [
            {
                "id": "template-1",
                "name": "Test Template",
                "description": "A test template",
                "template_text": "You are a test agent.",
                "is_builtin": True,
            }
        ],
        "total": 1,
    }
    mock_response.raise_for_status = Mock()

    # Setup mock client context manager
    mock_client_instance = Mock()
    mock_client_instance.get.return_value = mock_response
    mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

    # Clear cache before test
    fetch_prompt_templates.clear()

    # Call function
    templates = fetch_prompt_templates()

    # Assertions
    assert len(templates) == 1
    assert templates[0]["name"] == "Test Template"
    assert templates[0]["template_text"] == "You are a test agent."
    mock_client_instance.get.assert_called_once()


def test_fetch_prompt_templates_api_error(mock_streamlit_state):
    """Test graceful fallback when API is unavailable."""
    from admin.utils.agent_helpers import fetch_prompt_templates, PROMPT_TEMPLATES
    import httpx

    # Clear cache before test
    fetch_prompt_templates.clear()

    # Mock httpx.Client to raise an exception
    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.side_effect = httpx.HTTPError(
            "API Error"
        )

        # Mock st.warning to avoid actual Streamlit calls
        with patch("streamlit.warning"):
            # Call function
            templates = fetch_prompt_templates()

    # Should return fallback templates
    assert len(templates) > 0
    assert len(templates) == len(PROMPT_TEMPLATES)
    # Check that hardcoded templates are returned in correct format
    template_names = [t["name"] for t in templates]
    for name in PROMPT_TEMPLATES.keys():
        assert name in template_names


def test_fetch_prompt_templates_empty_response(mock_streamlit_state, mock_httpx_client):
    """Test handling of empty API response."""
    from admin.utils.agent_helpers import fetch_prompt_templates

    # Mock empty API response
    mock_response = Mock()
    mock_response.json.return_value = {"data": [], "total": 0}
    mock_response.raise_for_status = Mock()

    mock_client_instance = Mock()
    mock_client_instance.get.return_value = mock_response
    mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

    # Clear cache before test
    fetch_prompt_templates.clear()

    # Mock st.warning to avoid actual Streamlit calls
    with patch("streamlit.warning"):
        # Call function
        templates = fetch_prompt_templates()

    # Should return fallback templates
    assert len(templates) > 0


def test_agent_form_uses_dynamic_templates():
    """Test that create_agent_form uses fetch_prompt_templates instead of hardcoded dict."""
    import inspect
    from admin.components.agent_forms import create_agent_form

    # Get source code of create_agent_form
    source = inspect.getsource(create_agent_form)

    # Verify it calls fetch_prompt_templates
    assert "fetch_prompt_templates()" in source

    # Verify the template selector uses the fetched templates
    assert "available_templates" in source
    assert (
        'help="Start with a pre-built template or write custom. Templates sync with System Prompt Editor."'
        in source
    )
