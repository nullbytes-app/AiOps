"""
Integration tests for End-to-End Agent Execution with MCP Tools.

Tests the complete agent execution workflow from API endpoint to agent execution service.

Note: These tests verify API endpoint integration. Full end-to-end testing with real
MCP servers and LLMs should be done in manual QA or staging environment.

References:
- Story 11.1.7: MCP Tool Invocation in Agent Execution
- AC#8: REST API endpoint for agent execution
- src/api/agent_execution.py
- src/services/agent_execution_service.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from httpx import AsyncClient, ASGITransport

from src.main import app


# ============================================================================
# Test API Endpoint Integration
# ============================================================================


@pytest.mark.asyncio
async def test_agent_execution_api_endpoint_success() -> None:
    """Test successful agent execution through API endpoint."""
    mock_agent_id = uuid4()

    # Mock successful execution result
    mock_result = {
        "success": True,
        "response": "Integration test response from agent",
        "tool_calls": [
            {
                "tool_name": "test_tool",
                "tool_input": {"arg": "value"},
                "tool_output": "tool result",
                "timestamp": "2025-01-09T12:34:56.789Z",
            }
        ],
        "execution_time_seconds": 1.23,
        "model_used": "openai/gpt-4o-mini",
        "error": None,
    }

    with patch("src.services.agent_execution_service.AgentExecutionService.execute_agent", new_callable=AsyncMock) as mock_execute:
        mock_execute.return_value = mock_result

        # Make API request
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/agent-execution/execute",
                json={
                    "agent_id": str(mock_agent_id),
                    "user_message": "Test message for integration",
                    "context": {"test_key": "test_value"},
                    "timeout_seconds": 120,
                },
                headers={"X-Tenant-ID": "test-tenant"},
            )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["response"] == "Integration test response from agent"
        assert isinstance(data["tool_calls"], list)
        assert len(data["tool_calls"]) == 1
        assert data["tool_calls"][0]["tool_name"] == "test_tool"
        assert data["execution_time_seconds"] == 1.23
        assert data["model_used"] == "openai/gpt-4o-mini"
        assert data["error"] is None


@pytest.mark.asyncio
async def test_agent_execution_api_endpoint_missing_tenant_header() -> None:
    """Test API endpoint requires X-Tenant-ID header."""
    mock_agent_id = uuid4()

    # Make API request WITHOUT X-Tenant-ID header
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/agent-execution/execute",
            json={
                "agent_id": str(mock_agent_id),
                "user_message": "Test message",
            },
        )

    # FastAPI returns 400 for missing required headers (not 422)
    # See: https://github.com/tiangolo/fastapi/discussions/8859
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_agent_execution_health_endpoint() -> None:
    """Test agent execution health endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/agent-execution/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "agent-execution"
    assert "version" in data
    assert "features" in data
    assert "langgraph-react-agent" in data["features"]
    assert "mcp-tool-support" in data["features"]
    assert "budget-enforcement" in data["features"]
    assert "multi-tenant-isolation" in data["features"]


# ============================================================================
# Test Request Validation
# ============================================================================


@pytest.mark.asyncio
async def test_agent_execution_api_endpoint_agent_not_found() -> None:
    """Test API endpoint handles agent not found (500)."""
    mock_agent_id = uuid4()

    with patch("src.services.agent_execution_service.AgentExecutionService.execute_agent", new_callable=AsyncMock) as mock_execute:
        # Mock service to return error response for agent not found
        mock_execute.return_value = {
            "success": False,
            "response": "",
            "tool_calls": [],
            "execution_time_seconds": 0.0,
            "model_used": None,
            "error": f"Agent {mock_agent_id} not found",
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/agent-execution/execute",
                json={
                    "agent_id": str(mock_agent_id),
                    "user_message": "Test message",
                },
                headers={"X-Tenant-ID": "test-tenant"},
            )

        # When service returns success=False, endpoint returns 500
        assert response.status_code == 500


# Note: Budget exceeded (402) and context parameter tests would require
# more complex mocking of the service layer. These scenarios are covered
# in unit tests for AgentExecutionService. The integration tests above
# focus on API-level contract testing with mocked service layer.
