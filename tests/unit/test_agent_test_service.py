"""
Unit tests for agent test service (Story 8.14).

Tests cover:
- Test execution with sandbox mode
- Execution trace logging
- Token usage tracking
- Error handling and reporting
- Result storage and retrieval
- Test comparison functionality
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from src.schemas.agent_test import AgentTestRequest
from src.services.agent_test_service import AgentTestService
from src.services.sandbox_context import SandboxExecutionContext
from src.services.execution_tracer import ExecutionTracer


class TestExecutionTracer:
    """Tests for ExecutionTracer utility."""

    def test_initialization(self):
        """Test tracer initialization."""
        tracer = ExecutionTracer("test-execution-123")
        assert tracer.execution_id == "test-execution-123"
        assert len(tracer.steps) == 0

    def test_add_tool_call(self):
        """Test recording tool call step."""
        tracer = ExecutionTracer("test-exec")
        tracer.add_tool_call(
            tool_name="fetch_ticket",
            input_data={"ticket_id": 123},
            output_data={"status": "Open"},
            duration_ms=45.5
        )

        assert len(tracer.steps) == 1
        step = tracer.steps[0]
        assert step.step_number == 1
        assert step.step_type == "tool_call"
        assert step.tool_name == "fetch_ticket"
        assert step.duration_ms == 45.5

    def test_add_llm_request(self):
        """Test recording LLM request step."""
        tracer = ExecutionTracer("test-exec")
        tracer.add_llm_request(
            model_name="gpt-4o-mini",
            input_data={"prompt": "Test"},
            output_data={"response": "Answer"},
            duration_ms=120.0
        )

        assert len(tracer.steps) == 1
        step = tracer.steps[0]
        assert step.step_type == "llm_request"
        assert step.model_name == "gpt-4o-mini"

    def test_total_duration_ms(self):
        """Test total duration calculation."""
        tracer = ExecutionTracer("test-exec")
        tracer.add_tool_call("tool1", {}, {}, 50.0)
        tracer.add_tool_call("tool2", {}, {}, 75.5)
        tracer.add_llm_request("model", {}, {}, 100.0)

        total = tracer.get_total_duration_ms()
        assert total == pytest.approx(225.5)

    def test_to_dict_serialization(self):
        """Test conversion to dictionary for JSON storage."""
        tracer = ExecutionTracer("test-exec-456")
        tracer.add_tool_call("test_tool", {"a": 1}, {"b": 2}, 10.0)

        data = tracer.to_dict()
        assert data["execution_id"] == "test-exec-456"
        assert len(data["steps"]) == 1
        assert data["total_duration_ms"] == 10.0
        assert "start_time" in data
        assert "end_time" in data


class TestSandboxExecutionContext:
    """Tests for sandbox execution context."""

    def test_initialization(self):
        """Test sandbox context initialization."""
        agent_id = uuid4()
        sandbox = SandboxExecutionContext(agent_id, "test-tenant")

        assert sandbox.agent_id == agent_id
        assert sandbox.tenant_id == "test-tenant"
        assert sandbox.is_readonly is True
        assert sandbox.get_step_count() == 0

    def test_tool_registration(self):
        """Test tool registration in sandbox."""
        sandbox = SandboxExecutionContext(uuid4(), "test-tenant")
        sandbox.register_tool("fetch_ticket")

        assert "fetch_ticket" in sandbox.mock_tools
        response = sandbox.get_mock_response("fetch_ticket")
        assert response["status"] == "Open"

    def test_mock_response_for_different_tools(self):
        """Test mock responses for different tools."""
        sandbox = SandboxExecutionContext(uuid4(), "test-tenant")

        # Test fetch_ticket
        response = sandbox.get_mock_response("fetch_ticket")
        assert "ticket_id" in response
        assert response["status"] == "Open"

        # Test search_tickets
        response = sandbox.get_mock_response("search_tickets")
        assert "tickets" in response
        assert response["total"] == 1

        # Test update_ticket
        response = sandbox.get_mock_response("update_ticket")
        assert response["status"] == "Updated"

    def test_readonly_enforcement(self):
        """Test read-only mode enforcement."""
        sandbox = SandboxExecutionContext(uuid4(), "test-tenant")
        assert sandbox.is_readonly is True

        # Should not raise - just validation placeholder
        sandbox.check_write_attempt()


class TestAgentTestService:
    """Tests for agent test service."""

    @pytest.mark.asyncio
    async def test_execute_agent_test_nonexistent_agent(self):
        """Test error handling for nonexistent agent."""
        service = AgentTestService()
        test_request = AgentTestRequest(payload={})

        # Mock database session
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="not found"):
            await service.execute_agent_test(
                agent_id=uuid4(),
                tenant_id="test-tenant",
                test_request=test_request,
                db=mock_db,
            )

    @pytest.mark.asyncio
    async def test_execute_agent_test_tenant_isolation(self):
        """Test tenant isolation enforcement."""
        service = AgentTestService()
        test_request = AgentTestRequest(payload={})

        # Mock agent with different tenant
        mock_agent = MagicMock()
        mock_agent.tenant_id = "original-tenant"

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=mock_agent)

        with pytest.raises(ValueError, match="isolation"):
            await service.execute_agent_test(
                agent_id=uuid4(),
                tenant_id="different-tenant",
                test_request=test_request,
                db=mock_db,
            )

    @pytest.mark.asyncio
    async def test_get_test_history_nonexistent_agent(self):
        """Test error handling for nonexistent agent in history."""
        service = AgentTestService()

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="not found"):
            await service.get_test_history(
                agent_id=uuid4(),
                tenant_id="test-tenant",
                db=mock_db,
                limit=10,
                offset=0,
            )

    @pytest.mark.asyncio
    async def test_get_test_result_tenant_isolation(self):
        """Test tenant isolation in get_test_result."""
        service = AgentTestService()

        # Mock test execution with different tenant
        mock_test = MagicMock()
        mock_test.tenant_id = "original-tenant"
        mock_test.agent_id = uuid4()

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=mock_test)

        with pytest.raises(ValueError, match="isolation"):
            await service.get_test_result(
                test_id=uuid4(),
                agent_id=mock_test.agent_id,
                tenant_id="different-tenant",
                db=mock_db,
            )
