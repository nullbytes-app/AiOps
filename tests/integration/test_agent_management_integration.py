"""
Integration tests for Agent Management UI workflows.

Tests full workflows:
- Create agent via form → list shows agent → edit agent → delete agent
- Form validation prevents invalid submissions
- List refresh on CRUD operations
- Error handling for API failures

Story: 8.4 - Agent Management UI (Basic)
Target: 8+ integration tests
Note: These are mock-based tests as Streamlit doesn't have real browser testing
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from admin.utils.agent_helpers import (
    activate_agent_async,
    create_agent_async,
    delete_agent_async,
    fetch_agent_detail_async,
    fetch_agents_async,
    update_agent_async,
)


@pytest.fixture
def mock_agent_response():
    """Sample agent API response."""
    return {
        "id": "agent-123",
        "tenant_id": "default",
        "name": "Test Agent",
        "description": "A test agent",
        "status": "draft",
        "system_prompt": "You are a helpful assistant...",
        "llm_config": {
            "provider": "litellm",
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 4096,
        },
        "created_at": "2025-11-05T19:30:45Z",
        "updated_at": "2025-11-05T19:30:45Z",
        "webhook_url": "https://example.com/agents/agent-123/webhook",
        "tool_ids": ["servicedesk_plus"],
        "triggers": [],
    }


@pytest.fixture
def mock_agents_list_response():
    """Sample agents list API response."""
    return {
        "items": [
            {
                "id": "agent-1",
                "name": "Agent 1",
                "status": "active",
                "tool_ids": ["servicedesk_plus"],
                "updated_at": "2025-11-05T10:00:00Z",
            },
            {
                "id": "agent-2",
                "name": "Agent 2",
                "status": "draft",
                "tool_ids": ["jira", "knowledge_base"],
                "updated_at": "2025-11-04T10:00:00Z",
            },
        ],
        "total": 2,
    }


@pytest.mark.asyncio
class TestFetchAgentsWorkflow:
    """Test agent fetching workflows."""

    async def test_fetch_agents_success(self, mock_agents_list_response):
        """Test successful agent list fetch."""
        with patch("admin.utils.agent_helpers.httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_agents_list_response
            mock_response.raise_for_status = MagicMock()

            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)

            mock_client_class.return_value = mock_client

            result = await fetch_agents_async(search="", status="All")

            assert result is not None
            assert "items" in result
            assert len(result["items"]) == 2
            assert result["items"][0]["name"] == "Agent 1"

    async def test_fetch_agents_with_search(self, mock_agents_list_response):
        """Test agent list fetch with search query."""
        filtered_response = {
            "items": [mock_agents_list_response["items"][0]],
            "total": 1,
        }

        with patch("admin.utils.agent_helpers.httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.json.return_value = filtered_response
            mock_response.raise_for_status = MagicMock()

            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)

            mock_client_class.return_value = mock_client

            result = await fetch_agents_async(search="Agent 1", status="All")

            assert result is not None
            assert len(result["items"]) == 1
            assert result["items"][0]["name"] == "Agent 1"

    async def test_fetch_agents_with_status_filter(self, mock_agents_list_response):
        """Test agent list fetch with status filter."""
        active_only = {
            "items": [mock_agents_list_response["items"][0]],
            "total": 1,
        }

        with patch("admin.utils.agent_helpers.httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.json.return_value = active_only
            mock_response.raise_for_status = MagicMock()

            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)

            mock_client_class.return_value = mock_client

            result = await fetch_agents_async(search="", status="active")

            assert result is not None
            assert len(result["items"]) == 1
            assert result["items"][0]["status"] == "active"


@pytest.mark.asyncio
class TestAgentDetailWorkflow:
    """Test agent detail fetching."""

    async def test_fetch_agent_detail_success(self, mock_agent_response):
        """Test successful agent detail fetch."""
        with patch("admin.utils.agent_helpers.httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_agent_response
            mock_response.raise_for_status = MagicMock()

            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)

            mock_client_class.return_value = mock_client

            result = await fetch_agent_detail_async("agent-123")

            assert result is not None
            assert result["id"] == "agent-123"
            assert result["name"] == "Test Agent"
            assert (
                result["webhook_url"] == "https://example.com/agents/agent-123/webhook"
            )


@pytest.mark.asyncio
class TestCreateAgentWorkflow:
    """Test agent creation workflow."""

    async def test_create_agent_success(self, mock_agent_response):
        """Test successful agent creation."""
        create_payload = {
            "name": "Test Agent",
            "description": "A test agent",
            "status": "draft",
            "system_prompt": "You are a helpful assistant...",
            "llm_config": {
                "provider": "litellm",
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 4096,
            },
            "tool_ids": ["servicedesk_plus"],
            "triggers": [],
        }

        with patch("admin.utils.agent_helpers.httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_agent_response
            mock_response.raise_for_status = MagicMock()

            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)

            mock_client_class.return_value = mock_client

            result = await create_agent_async(create_payload)

            assert result is not None
            assert result["id"] == "agent-123"
            assert result["name"] == "Test Agent"
            assert "webhook_url" in result

    async def test_create_agent_validation_error(self):
        """Test agent creation fails with validation error."""
        import httpx

        invalid_payload = {
            "name": "",  # Invalid: empty name
            "system_prompt": "short",  # Invalid: too short
        }

        with patch("admin.utils.agent_helpers.httpx.AsyncClient") as mock_client_class:
            # Create a mock HTTPStatusError
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.json.return_value = {"detail": "Validation failed"}

            # Simulate HTTPStatusError
            error = httpx.HTTPStatusError(
                "400 Validation Error", request=MagicMock(), response=mock_response
            )

            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(side_effect=error)

            mock_client_class.return_value = mock_client

            # Mock streamlit to prevent errors
            with patch("admin.utils.agent_helpers.st"):
                result = await create_agent_async(invalid_payload)
                # Function returns None on error
                assert result is None


@pytest.mark.asyncio
class TestUpdateAgentWorkflow:
    """Test agent update workflow."""

    async def test_update_agent_success(self, mock_agent_response):
        """Test successful agent update."""
        updates = {
            "name": "Updated Agent",
            "system_prompt": "Updated prompt with more content...",
        }

        updated_response = {**mock_agent_response, **updates}

        with patch("admin.utils.agent_helpers.httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.json.return_value = updated_response
            mock_response.raise_for_status = MagicMock()

            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.put = AsyncMock(return_value=mock_response)

            mock_client_class.return_value = mock_client

            result = await update_agent_async("agent-123", updates)

            assert result is not None
            assert result["name"] == "Updated Agent"
            assert result["system_prompt"] == updates["system_prompt"]


@pytest.mark.asyncio
class TestDeleteAgentWorkflow:
    """Test agent deletion workflow."""

    async def test_delete_agent_success(self):
        """Test successful agent deletion."""
        with patch("admin.utils.agent_helpers.httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()

            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.delete = AsyncMock(return_value=mock_response)

            mock_client_class.return_value = mock_client

            result = await delete_agent_async("agent-123")

            assert result is True


@pytest.mark.asyncio
class TestActivateAgentWorkflow:
    """Test agent activation workflow."""

    async def test_activate_agent_success(self, mock_agent_response):
        """Test successful agent activation (draft → active)."""
        active_response = {
            **mock_agent_response,
            "status": "active",
        }

        with patch("admin.utils.agent_helpers.httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.json.return_value = active_response
            mock_response.raise_for_status = MagicMock()

            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)

            mock_client_class.return_value = mock_client

            result = await activate_agent_async("agent-123")

            assert result is not None
            assert result["status"] == "active"


@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling in API calls."""

    async def test_fetch_agents_timeout(self):
        """Test handling of request timeout."""
        import httpx

        with patch("admin.utils.agent_helpers.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

            mock_client_class.return_value = mock_client

            with patch("admin.utils.agent_helpers.st"):
                result = await fetch_agents_async()
                # Function returns None on timeout
                assert result is None

    async def test_create_agent_server_error(self):
        """Test handling of 500 server error."""
        import httpx

        payload = {
            "name": "Test Agent",
            "system_prompt": "Valid prompt...",
            "model": "gpt-4",
            "tool_ids": ["servicedesk_plus"],
        }

        with patch("admin.utils.agent_helpers.httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 500

            error = httpx.HTTPStatusError(
                "500 Server Error", request=MagicMock(), response=mock_response
            )

            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(side_effect=error)

            mock_client_class.return_value = mock_client

            with patch("admin.utils.agent_helpers.st"):
                result = await create_agent_async(payload)
                # Function returns None on error
                assert result is None
