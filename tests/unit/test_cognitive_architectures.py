"""
Unit tests for Cognitive Architecture Factory in AgentExecutionService.

Verifies that the correct agent executor graph is created based on the
configured cognitive architecture (REACT, SINGLE_STEP, PLAN_AND_SOLVE).
"""

import pytest
from unittest.mock import MagicMock, patch
from src.services.agent_execution_service import AgentExecutionService
from src.schemas.agent import CognitiveArchitecture

@pytest.fixture
def mock_service():
    """Create a mock AgentExecutionService."""
    db = MagicMock()
    return AgentExecutionService(db)

@pytest.fixture
def mock_llm():
    """Create a mock LLM."""
    return MagicMock()

@pytest.fixture
def mock_tools():
    """Create a list of mock tools."""
    return [MagicMock()]

def test_create_react_agent_executor(mock_service, mock_llm, mock_tools):
    """Test that REACT architecture creates a ReAct agent."""
    with patch("src.services.agent_execution_service.create_react_agent") as mock_create:
        mock_service._create_agent_executor(
            architecture=CognitiveArchitecture.REACT,
            llm=mock_llm,
            tools=mock_tools
        )
        
        mock_create.assert_called_once_with(model=mock_llm, tools=mock_tools)

def test_create_single_step_agent_executor(mock_service, mock_llm, mock_tools):
    """Test that SINGLE_STEP architecture calls the single step creator."""
    # For now, single step also calls create_react_agent (as per implementation)
    # but we want to verify it goes through the right path
    with patch("src.services.agent_execution_service.create_react_agent") as mock_create:
        mock_service._create_agent_executor(
            architecture=CognitiveArchitecture.SINGLE_STEP,
            llm=mock_llm,
            tools=mock_tools
        )
        
        mock_create.assert_called_once_with(model=mock_llm, tools=mock_tools)

def test_create_plan_and_solve_agent_executor(mock_service, mock_llm, mock_tools):
    """Test that PLAN_AND_SOLVE architecture calls the plan and solve creator."""
    # For now, plan and solve also calls create_react_agent (as per implementation placeholder)
    with patch("src.services.agent_execution_service.create_react_agent") as mock_create:
        mock_service._create_agent_executor(
            architecture=CognitiveArchitecture.PLAN_AND_SOLVE,
            llm=mock_llm,
            tools=mock_tools
        )
        
        mock_create.assert_called_once_with(model=mock_llm, tools=mock_tools)

def test_default_architecture(mock_service, mock_llm, mock_tools):
    """Test that unknown architecture defaults to REACT."""
    with patch("src.services.agent_execution_service.create_react_agent") as mock_create:
        mock_service._create_agent_executor(
            architecture="unknown_arch",
            llm=mock_llm,
            tools=mock_tools
        )
        
        mock_create.assert_called_once_with(model=mock_llm, tools=mock_tools)
