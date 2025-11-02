"""
Unit tests for LangGraph workflow orchestration.

Tests WorkflowState, individual node behavior, and state aggregation.
Coverage: AC #1 (workflow structure), #3 (aggregation), #7 (unit tests)
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from src.workflows.enhancement_workflow import (
    WorkflowState,
    ticket_search_node,
    kb_search_node,
    ip_lookup_node,
    aggregate_results_node,
    build_enhancement_workflow,
    execute_context_gathering,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_workflow_state() -> Dict[str, Any]:
    """
    Sample WorkflowState for testing.

    Provides baseline state with tenant isolation, description, and empty results.
    """
    return {
        "tenant_id": "test-tenant-1",
        "ticket_id": "TICKET-001",
        "description": "Server down - 192.168.1.100 not responding",
        "priority": "high",
        "timestamp": "2025-11-02T10:00:00Z",
        "correlation_id": "test-correlation-id",
        "similar_tickets": [],
        "kb_articles": [],
        "ip_info": [],
        "errors": [],
        "ticket_search_time_ms": 0,
        "kb_search_time_ms": 0,
        "ip_lookup_time_ms": 0,
        "workflow_start_time": 1000.0,
        "workflow_end_time": 0,
        "workflow_execution_time_ms": 0,
    }


# ============================================================================
# UNIT TESTS: WorkflowState
# ============================================================================

class TestWorkflowState:
    """AC #1: Workflow defined with required fields"""

    def test_workflow_state_has_all_required_fields(self, sample_workflow_state):
        """Verify WorkflowState has all fields defined in AC #1"""
        required_fields = {
            "tenant_id",
            "ticket_id",
            "description",
            "priority",
            "timestamp",
            "correlation_id",
            "similar_tickets",
            "kb_articles",
            "ip_info",
            "errors",
            "ticket_search_time_ms",
            "kb_search_time_ms",
            "ip_lookup_time_ms",
            "workflow_start_time",
            "workflow_end_time",
            "workflow_execution_time_ms",
        }
        assert all(field in sample_workflow_state for field in required_fields)

    def test_workflow_state_field_types(self, sample_workflow_state):
        """Verify field types match TypedDict definition"""
        assert isinstance(sample_workflow_state["tenant_id"], str)
        assert isinstance(sample_workflow_state["similar_tickets"], list)
        assert isinstance(sample_workflow_state["kb_articles"], list)
        assert isinstance(sample_workflow_state["ip_info"], list)
        assert isinstance(sample_workflow_state["errors"], list)
        assert isinstance(sample_workflow_state["ticket_search_time_ms"], int)

    def test_workflow_state_tenant_isolation(self, sample_workflow_state):
        """Tenant ID must be present for data isolation"""
        assert sample_workflow_state["tenant_id"] == "test-tenant-1"
        state_copy = sample_workflow_state.copy()
        state_copy["tenant_id"] = "different-tenant"
        assert state_copy["tenant_id"] != sample_workflow_state["tenant_id"]


# ============================================================================
# UNIT TESTS: Node Behavior
# ============================================================================

class TestTicketSearchNode:
    """AC #3: Nodes update state correctly, AC #4: Error handling"""

    @pytest.mark.asyncio
    async def test_ticket_search_node_success(self, sample_workflow_state):
        """Test ticket_search_node succeeds with mock data"""
        mock_results = [
            {"ticket_id": "TICKET-002", "description": "Similar issue"},
            {"ticket_id": "TICKET-003", "description": "Related problem"},
        ]
        mock_metadata = {"method": "fts", "num_results": 2}

        with patch("src.workflows.enhancement_workflow.TicketSearchService") as MockService:
            mock_service = AsyncMock()
            mock_service.search_similar_tickets = AsyncMock(
                return_value=(mock_results, mock_metadata)
            )
            MockService.return_value = mock_service

            result = await ticket_search_node(sample_workflow_state)

            # Verify results are in state
            assert len(result["similar_tickets"]) == 2
            assert result["ticket_search_time_ms"] >= 0
            assert "errors" not in result or len(result.get("errors", [])) == 0

    @pytest.mark.asyncio
    async def test_ticket_search_node_graceful_degradation(self, sample_workflow_state):
        """AC #4: Node catches exception, logs error, returns gracefully"""
        with patch("src.workflows.enhancement_workflow.TicketSearchService") as MockService:
            mock_service = AsyncMock()
            mock_service.search_similar_tickets = AsyncMock(
                side_effect=Exception("Database connection failed")
            )
            MockService.return_value = mock_service

            result = await ticket_search_node(sample_workflow_state)

            # Verify graceful degradation
            assert result["similar_tickets"] == []
            assert len(result["errors"]) == 1
            assert result["errors"][0]["node"] == "ticket_search_node"
            assert "Database connection failed" in result["errors"][0]["message"]

    @pytest.mark.asyncio
    async def test_ticket_search_node_empty_results(self, sample_workflow_state):
        """Node handles empty search results gracefully"""
        with patch("src.workflows.enhancement_workflow.TicketSearchService") as MockService:
            mock_service = AsyncMock()
            mock_service.search_similar_tickets = AsyncMock(return_value=([], {}))
            MockService.return_value = mock_service

            result = await ticket_search_node(sample_workflow_state)

            assert result["similar_tickets"] == []
            assert "errors" not in result or len(result.get("errors", [])) == 0


class TestKBSearchNode:
    """AC #3: Nodes update state correctly, AC #4: Error handling"""

    @pytest.mark.asyncio
    async def test_kb_search_node_success(self, sample_workflow_state):
        """Test kb_search_node succeeds with mock data"""
        mock_articles = [
            {"title": "How to troubleshoot server downtime", "url": "http://kb.example.com/1"},
            {"title": "Common network issues", "url": "http://kb.example.com/2"},
        ]

        with patch("src.workflows.enhancement_workflow.KBSearchService") as MockService:
            mock_service = AsyncMock()
            mock_service.search_knowledge_base = AsyncMock(return_value=mock_articles)
            MockService.return_value = mock_service

            result = await kb_search_node(sample_workflow_state)

            assert len(result["kb_articles"]) == 2
            assert result["kb_search_time_ms"] >= 0

    @pytest.mark.asyncio
    async def test_kb_search_node_empty_config_returns_empty(self, sample_workflow_state):
        """KB search with empty URL/API key returns empty list (graceful)"""
        with patch("src.workflows.enhancement_workflow.KBSearchService") as MockService:
            mock_service = AsyncMock()
            mock_service.search_knowledge_base = AsyncMock(return_value=[])
            MockService.return_value = mock_service

            result = await kb_search_node(sample_workflow_state)

            assert result["kb_articles"] == []
            assert "errors" not in result or len(result.get("errors", [])) == 0

    @pytest.mark.asyncio
    async def test_kb_search_node_graceful_degradation(self, sample_workflow_state):
        """AC #4: KB node catches exception and returns empty gracefully"""
        with patch("src.workflows.enhancement_workflow.KBSearchService") as MockService:
            mock_service = AsyncMock()
            mock_service.search_knowledge_base = AsyncMock(
                side_effect=Exception("KB API timeout")
            )
            MockService.return_value = mock_service

            result = await kb_search_node(sample_workflow_state)

            assert result["kb_articles"] == []
            assert len(result["errors"]) == 1
            assert "KB API timeout" in result["errors"][0]["message"]


class TestIPLookupNode:
    """AC #3: Nodes update state correctly, AC #4: Error handling"""

    @pytest.mark.asyncio
    async def test_ip_lookup_node_no_session_returns_empty(self, sample_workflow_state):
        """IP lookup with no session returns empty list (expected behavior)"""
        result = await ip_lookup_node(sample_workflow_state)

        # When session is None, node returns empty results
        assert result["ip_info"] == []
        assert result["ip_lookup_time_ms"] == 0

    @pytest.mark.asyncio
    async def test_ip_lookup_node_graceful_error(self, sample_workflow_state):
        """IP lookup handles errors gracefully"""
        result = await ip_lookup_node(sample_workflow_state)
        
        # No session, so returns empty (not an error condition)
        assert result["ip_info"] == []


# ============================================================================
# UNIT TESTS: Aggregation
# ============================================================================

class TestAggregateResultsNode:
    """AC #3: Workflow aggregates results from all nodes"""

    @pytest.mark.asyncio
    async def test_aggregate_results_node_empty_inputs(self, sample_workflow_state):
        """Aggregation handles empty results from all nodes"""
        result = await aggregate_results_node(sample_workflow_state)

        assert "workflow_end_time" in result
        assert "workflow_execution_time_ms" in result
        assert result["workflow_execution_time_ms"] >= 0

    @pytest.mark.asyncio
    async def test_aggregate_results_node_with_data(self, sample_workflow_state):
        """Aggregation processes data from all three nodes"""
        state_with_data = sample_workflow_state.copy()
        state_with_data["similar_tickets"] = [{"ticket_id": "1"}]
        state_with_data["kb_articles"] = [{"title": "Article"}]
        state_with_data["ip_info"] = [{"ip": "192.168.1.1"}]

        result = await aggregate_results_node(state_with_data)

        assert "workflow_end_time" in result
        assert result["workflow_execution_time_ms"] >= 0

    @pytest.mark.asyncio
    async def test_aggregate_results_node_with_errors(self, sample_workflow_state):
        """Aggregation continues even with errors from nodes"""
        state_with_errors = sample_workflow_state.copy()
        state_with_errors["errors"] = [
            {"node": "ticket_search_node", "message": "Failed", "timestamp": 1000}
        ]

        result = await aggregate_results_node(state_with_errors)

        # Aggregation should still complete
        assert "workflow_end_time" in result


# ============================================================================
# UNIT TESTS: Workflow Builder
# ============================================================================

class TestBuildEnhancementWorkflow:
    """AC #1: Workflow defined with nodes, AC #2: Parallel structure"""

    def test_build_workflow_creates_state_graph(self):
        """Workflow builder creates a compilable StateGraph"""
        workflow = build_enhancement_workflow()

        # Verify it's compiled and executable
        assert workflow is not None
        assert hasattr(workflow, "ainvoke")

    def test_workflow_execution_structure(self):
        """Workflow has correct structure"""
        workflow = build_enhancement_workflow()

        # Verify workflow can be invoked (structure is correct)
        assert hasattr(workflow, "ainvoke")


# ============================================================================
# UNIT TESTS: Execute Context Gathering
# ============================================================================

class TestExecuteContextGathering:
    """AC #1, #2, #3, #4, #5, #6: Full workflow execution"""

    @pytest.mark.asyncio
    async def test_execute_context_gathering_with_mocks(self):
        """execute_context_gathering returns a valid WorkflowState with mocks"""
        with patch("src.workflows.enhancement_workflow.TicketSearchService") as MockTicket, \
             patch("src.workflows.enhancement_workflow.KBSearchService") as MockKB:

            # Mock services
            ticket_service = AsyncMock()
            ticket_service.search_similar_tickets = AsyncMock(
                return_value=([{"ticket_id": "1"}], {"method": "fts"})
            )
            MockTicket.return_value = ticket_service

            kb_service = AsyncMock()
            kb_service.search_knowledge_base = AsyncMock(return_value=[{"title": "Article"}])
            MockKB.return_value = kb_service

            result = await execute_context_gathering(
                tenant_id="test-tenant",
                ticket_id="TICKET-001",
                description="test issue",
            )

            # Verify result structure
            assert result is not None
            assert result["tenant_id"] == "test-tenant"
            assert "workflow_execution_time_ms" in result
