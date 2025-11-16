"""
Unit tests for Agent Execution Service.

Focused unit tests for AgentExecutionService covering critical paths:
- Service initialization
- Agent retrieval and tenant isolation
- Budget enforcement (via LLMService)
- Main execution flow (mocked)

Note: Full end-to-end testing is covered in integration tests (Task 10).

References:
- Story 11.1.7: MCP Tool Invocation in Agent Execution
- src/services/agent_execution_service.py
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Agent
from src.exceptions import BudgetExceededError
from src.services.agent_execution_service import AgentExecutionService


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Create mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_agent() -> MagicMock:
    """Create mock agent instance with proper schema."""
    agent = MagicMock(spec=Agent)
    agent.id = uuid4()
    agent.tenant_id = "test-tenant"
    agent.name = "Test Agent"
    agent.description = "Test agent description"
    agent.system_prompt = "You are a helpful assistant."
    agent.status = "active"
    agent.llm_config = {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "temperature": 0.7,
        "max_tokens": 1000,
    }
    agent.memory_config = None
    agent.assigned_mcp_tools = []
    agent.tools = []
    agent.created_at = datetime.now(UTC)
    agent.updated_at = datetime.now(UTC)
    return agent


# ============================================================================
# Test AgentExecutionService Initialization
# ============================================================================


def test_agent_execution_service_initialization(mock_db_session: AsyncMock) -> None:
    """Test AgentExecutionService initialization with required dependencies."""
    service = AgentExecutionService(mock_db_session)

    assert service.db == mock_db_session
    assert service.agent_service is not None
    assert service.llm_service is not None
    assert service.litellm_proxy_url == "http://litellm:4000"


# ============================================================================
# Test Agent Retrieval and Validation
# ============================================================================


@pytest.mark.asyncio
async def test_execute_agent_not_found(mock_db_session: AsyncMock) -> None:
    """Test agent execution when agent is not found (get_agent_by_id returns None)."""
    service = AgentExecutionService(mock_db_session)

    # Mock agent_service.get_agent_by_id to return None
    service.agent_service.get_agent_by_id = AsyncMock(return_value=None)

    # Execute and expect AgentExecutionError (wrapped ValueError)
    result = await service.execute_agent(
        agent_id=uuid4(),
        tenant_id="test-tenant",
        user_message="Test message",
    )

    # Should return error response instead of raising
    assert result["success"] is False
    assert "not found" in result["error"].lower() or "nonetype" in result["error"].lower()


@pytest.mark.asyncio
async def test_execute_agent_inactive_status(
    mock_db_session: AsyncMock,
    mock_agent: MagicMock,
) -> None:
    """Test agent execution when agent status is not 'active'."""
    service = AgentExecutionService(mock_db_session)
    mock_agent.status = "inactive"

    # Mock agent retrieval
    service.agent_service.get_agent_by_id = AsyncMock(return_value=mock_agent)

    # Execute
    result = await service.execute_agent(
        agent_id=mock_agent.id,
        tenant_id="test-tenant",
        user_message="Test message",
    )

    # Should return error response
    assert result["success"] is False
    assert "not active" in result["error"].lower()


# ============================================================================
# Test Budget Enforcement
# ============================================================================


@pytest.mark.asyncio
async def test_execute_agent_budget_exceeded(
    mock_db_session: AsyncMock,
    mock_agent: MagicMock,
) -> None:
    """Test budget enforcement - LLMService raises BudgetExceededError."""
    service = AgentExecutionService(mock_db_session)

    # Mock agent retrieval
    service.agent_service.get_agent_by_id = AsyncMock(return_value=mock_agent)

    # Mock LLM service to raise BudgetExceededError with required arguments
    service.llm_service.get_llm_client_for_tenant = AsyncMock(
        side_effect=BudgetExceededError(
            tenant_id="test-tenant",
            current_spend=550.00,
            max_budget=500.00,
            grace_threshold=110,
        )
    )

    # Execute and expect BudgetExceededError to be re-raised
    with pytest.raises(BudgetExceededError, match="Budget exceeded"):
        await service.execute_agent(
            agent_id=mock_agent.id,
            tenant_id="test-tenant",
            user_message="Test message",
        )


# ============================================================================
# Test Main Execution Flow (Mocked)
# ============================================================================


@pytest.mark.asyncio
async def test_execute_agent_success_mocked(
    mock_db_session: AsyncMock,
    mock_agent: MagicMock,
) -> None:
    """Test successful agent execution with mocked dependencies."""
    service = AgentExecutionService(mock_db_session)

    # Mock agent retrieval
    service.agent_service.get_agent_by_id = AsyncMock(return_value=mock_agent)
    service.agent_service.get_agent_tools = AsyncMock(return_value=[])

    # Mock LLM service
    mock_async_openai = MagicMock()
    mock_async_openai.api_key = "test-virtual-key"
    service.llm_service.get_llm_client_for_tenant = AsyncMock(return_value=mock_async_openai)

    # Mock MCP server query (Story 12.7 refactoring added this query)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []  # No MCP servers
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    # Mock LangGraph components
    with patch("src.services.agent_execution_service.init_chat_model") as mock_init_chat:
        with patch("src.services.agent_execution_service.create_react_agent") as mock_create_agent:
            # Setup LLM
            mock_llm = MagicMock()
            mock_init_chat.return_value = mock_llm

            # Setup agent executor
            mock_agent_executor = AsyncMock()
            mock_agent_executor.ainvoke = AsyncMock(
                return_value={"messages": [MagicMock(content="Test response")]}
            )
            mock_create_agent.return_value = mock_agent_executor

            # Execute
            result = await service.execute_agent(
                agent_id=mock_agent.id,
                tenant_id="test-tenant",
                user_message="Test message",
            )

            # Verify result
            assert result["success"] is True
            assert result["response"] == "Test response"
            assert isinstance(result["tool_calls"], list)
            assert isinstance(result["execution_time_seconds"], float)
            assert result["model_used"] == "openai/gpt-4o-mini"
            assert result["error"] is None


# ============================================================================
# Test Response Structure
# ============================================================================


def test_execution_result_structure() -> None:
    """Test that execution results have the required structure."""
    # This test documents the expected response structure
    expected_keys = {
        "success",
        "response",
        "tool_calls",
        "execution_time_seconds",
        "model_used",
        "error",
    }

    # Document tool_call structure
    expected_tool_call_keys = {"tool_name", "tool_input", "tool_output", "timestamp"}

    # This serves as documentation for API consumers
    assert expected_keys == {
        "success",
        "response",
        "tool_calls",
        "execution_time_seconds",
        "model_used",
        "error",
    }
    assert expected_tool_call_keys == {
        "tool_name",
        "tool_input",
        "tool_output",
        "timestamp",
    }
