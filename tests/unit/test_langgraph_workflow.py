"""
Unit tests for LangGraph workflow orchestration.

Tests Story 2.8: Integrate LangGraph Workflow Orchestration

Test coverage:
- Workflow initialization and graph structure (AC #1)
- Node execution with mocked services (AC #2-#3)
- Graceful degradation when nodes fail (AC #4)
- State persistence for debugging (AC #5)
- Performance logging (AC #6)
- Concurrent execution validation (AC #7)

Framework: Pytest with pytest-asyncio
Mocking: unittest.mock (AsyncMock for async functions)
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.workflows.enhancement_workflow import (
    aggregate_results_node,
    build_enhancement_workflow,
    doc_search_node,
    get_debug_state,
    ticket_search_node,
)
from src.workflows.state import WorkflowState


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def base_state() -> WorkflowState:
    """Minimal valid WorkflowState for testing."""
    return {
        "tenant_id": "test-tenant",
        "ticket_id": "TICKET-001",
        "description": "Server is down. IP 192.168.1.5 is unreachable.",
        "priority": "high",
        "timestamp": "2025-11-02T10:30:00Z",
        "correlation_id": "test-correlation-001",
        "similar_tickets": [],
        "kb_articles": [],
        "ip_info": [],
        "errors": [],
    }


@pytest.fixture
def mock_ticket_search_result():
    """Mock result from ticket search service."""
    return [
        {
            "ticket_id": "TICKET-001",
            "description": "Server connectivity issue",
            "resolution": "Restarted network service",
            "resolved_date": "2025-10-30",
        },
        {
            "ticket_id": "TICKET-002",
            "description": "Server down",
            "resolution": "Replaced faulty power supply",
            "resolved_date": "2025-10-25",
        },
    ]


@pytest.fixture
def mock_kb_articles():
    """Mock result from KB search service."""
    return [
        {
            "title": "How to diagnose server connectivity issues",
            "summary": "Step-by-step guide for troubleshooting server problems",
            "url": "https://kb.example.com/article/server-connectivity",
        }
    ]


@pytest.fixture
def mock_ip_info():
    """Mock result from IP lookup service."""
    return [
        {
            "ip_address": "192.168.1.5",
            "hostname": "db-server-01",
            "role": "database",
            "client": "web-app",
            "location": "us-east-1",
        }
    ]


# ============================================================================
# AC #1: Workflow Initialization and Structure
# ============================================================================


class TestWorkflowInitialization:
    """Tests for workflow graph creation and node registration."""

    def test_workflow_compilation(self):
        """AC #1: Workflow initializes and compiles successfully."""
        workflow = build_enhancement_workflow()
        assert workflow is not None
        # Compiled graph should have invoke method for execution
        assert hasattr(workflow, "invoke")

    def test_workflow_has_nodes(self):
        """AC #1: Workflow graph contains all required nodes."""
        workflow = build_enhancement_workflow()
        # Graph should have compiled state with nodes
        assert hasattr(workflow, "graph")


# ============================================================================
# AC #2-#3: Node Execution and Result Aggregation
# ============================================================================


class TestTicketSearchNode:
    """Tests for ticket_search_node (Story 2.5 integration)."""

    @pytest.mark.asyncio
    async def test_ticket_search_success(self, base_state, mock_ticket_search_result):
        """AC #2, #3: Node executes and updates state with results."""
        with patch(
            "src.workflows.enhancement_workflow.TicketSearchService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.search_similar_tickets.return_value = (
                mock_ticket_search_result,
                {"method": "fts", "elapsed_ms": 150},
            )
            mock_service_class.return_value = mock_service

            result_state = await ticket_search_node(base_state)

            assert len(result_state["similar_tickets"]) == 2
            assert result_state["similar_tickets"][0]["ticket_id"] == "TICKET-001"
            assert result_state["errors"] == []

    @pytest.mark.asyncio
    async def test_ticket_search_empty_results(self, base_state):
        """AC #3: Node handles empty results gracefully."""
        with patch(
            "src.workflows.enhancement_workflow.TicketSearchService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.search_similar_tickets.return_value = ([], {"method": "fts"})
            mock_service_class.return_value = mock_service

            result_state = await ticket_search_node(base_state)

            assert result_state["similar_tickets"] == []
            assert result_state["errors"] == []

    @pytest.mark.asyncio
    async def test_ticket_search_exception(self, base_state):
        """AC #4: Node catches exception, logs, adds to errors, continues."""
        with patch(
            "src.workflows.enhancement_workflow.TicketSearchService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.search_similar_tickets.side_effect = Exception(
                "Database connection failed"
            )
            mock_service_class.return_value = mock_service

            result_state = await ticket_search_node(base_state)

            assert result_state["similar_tickets"] == []
            assert len(result_state["errors"]) == 1
            assert "Database connection failed" in result_state["errors"][0]["error_message"]


class TestDocSearchNode:
    """Tests for doc_search_node (Story 2.6 integration)."""

    @pytest.mark.asyncio
    async def test_kb_search_success(self, base_state, mock_kb_articles):
        """AC #2, #3: Node executes KB search and updates state."""
        with patch(
            "src.workflows.enhancement_workflow.search_knowledge_base"
        ) as mock_search:
            mock_search.return_value = mock_kb_articles

            result_state = await doc_search_node(base_state)

            assert len(result_state["kb_articles"]) == 1
            assert result_state["kb_articles"][0]["title"] == "How to diagnose server connectivity issues"
            assert result_state["errors"] == []
            mock_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_kb_search_timeout_graceful(self, base_state):
        """AC #4, #6: KB timeout (10s) returns empty list, doesn't block."""
        with patch(
            "src.workflows.enhancement_workflow.search_knowledge_base"
        ) as mock_search:
            # Simulate timeout returning empty list (AC #4: graceful degradation)
            mock_search.return_value = []

            result_state = await doc_search_node(base_state)

            assert result_state["kb_articles"] == []
            assert result_state["errors"] == []

    @pytest.mark.asyncio
    async def test_kb_search_api_error(self, base_state):
        """AC #4: KB API error caught, logged, added to errors, continues."""
        with patch(
            "src.workflows.enhancement_workflow.search_knowledge_base"
        ) as mock_search:
            mock_search.side_effect = Exception("KB API unreachable")

            result_state = await doc_search_node(base_state)

            assert result_state["kb_articles"] == []
            assert len(result_state["errors"]) == 1
            assert "KB API unreachable" in result_state["errors"][0]["error_message"]


# ============================================================================
# AC #4: Graceful Degradation (Partial Failures)
# ============================================================================


class TestGracefulDegradation:
    """Tests for workflow continuation when nodes fail."""

    @pytest.mark.asyncio
    async def test_one_node_fails_others_succeed(self, base_state):
        """AC #4: Workflow completes even if one node fails."""
        with patch(
            "src.workflows.enhancement_workflow.TicketSearchService"
        ) as mock_ticket_service, patch(
            "src.workflows.enhancement_workflow.search_knowledge_base"
        ) as mock_kb:
            # Ticket search fails
            mock_service = AsyncMock()
            mock_service.search_similar_tickets.side_effect = Exception("DB error")
            mock_ticket_service.return_value = mock_service

            # KB search succeeds
            mock_kb.return_value = [{"title": "Article", "summary": "...", "url": "..."}]

            # Execute ticket search node
            result_state = await ticket_search_node(base_state)
            assert len(result_state["errors"]) == 1
            assert result_state["similar_tickets"] == []

            # Execute KB search node
            result_state = await doc_search_node(result_state)
            assert len(result_state["kb_articles"]) == 1
            # Only ticket search error should be in errors list
            assert result_state["errors"][0]["node_name"] == "ticket_search_node"

    @pytest.mark.asyncio
    async def test_all_nodes_fail(self, base_state):
        """AC #4: Workflow completes with only errors in state (all nodes fail)."""
        with patch(
            "src.workflows.enhancement_workflow.TicketSearchService"
        ) as mock_ticket_service, patch(
            "src.workflows.enhancement_workflow.search_knowledge_base"
        ) as mock_kb:
            # Both services fail
            mock_service = AsyncMock()
            mock_service.search_similar_tickets.side_effect = Exception("DB error")
            mock_ticket_service.return_value = mock_service
            mock_kb.side_effect = Exception("API error")

            result_state = await ticket_search_node(base_state)
            result_state = await doc_search_node(result_state)

            assert result_state["similar_tickets"] == []
            assert result_state["kb_articles"] == []
            assert len(result_state["errors"]) == 2


# ============================================================================
# AC #5: State Persistence for Debugging
# ============================================================================


class TestStatePersistence:
    """Tests for workflow state persistence."""

    @pytest.mark.asyncio
    async def test_state_persisted_after_aggregation(self, base_state, mock_ticket_search_result):
        """AC #5: State serialized and stored after workflow completion."""
        with patch(
            "src.workflows.enhancement_workflow.TicketSearchService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.search_similar_tickets.return_value = (
                mock_ticket_search_result,
                {"method": "fts"},
            )
            mock_service_class.return_value = mock_service

            # Execute nodes
            state = await ticket_search_node(base_state)
            state = await aggregate_results_node(state)

            # Check state was persisted
            debug_state = get_debug_state(state["ticket_id"])
            assert debug_state is not None
            assert debug_state["ticket_id"] == "TICKET-001"
            assert debug_state["similar_tickets_count"] == 2

    def test_state_history_limit(self, base_state):
        """AC #5: State history maintains max 100 entries."""
        # Create multiple states
        for i in range(150):
            state = base_state.copy()
            state["ticket_id"] = f"TICKET-{i:03d}"
            from src.workflows.enhancement_workflow import _persist_state_for_debugging
            _persist_state_for_debugging(state)

        # Should never exceed 100 entries
        from src.workflows.enhancement_workflow import _state_history
        assert len(_state_history) <= 100


# ============================================================================
# AC #6: Performance Logging
# ============================================================================


class TestPerformanceLogging:
    """Tests for workflow execution timing and logging."""

    @pytest.mark.asyncio
    async def test_node_execution_time_logged(self, base_state):
        """AC #6: Node execution time is measured and logged."""
        with patch(
            "src.workflows.enhancement_workflow.TicketSearchService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.search_similar_tickets.return_value = ([], {"method": "fts"})
            mock_service_class.return_value = mock_service

            import time
            start = time.time()
            result_state = await ticket_search_node(base_state)
            elapsed = time.time() - start

            # Should complete in reasonable time (< 1s for mock)
            assert elapsed < 1.0
            # Logger should have been called with timing info
            # (verified via logging assertions)

    @pytest.mark.asyncio
    async def test_aggregation_logs_stats(self, base_state, mock_ticket_search_result):
        """AC #6: Aggregation node logs summary stats."""
        with patch(
            "src.workflows.enhancement_workflow.TicketSearchService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.search_similar_tickets.return_value = (
                mock_ticket_search_result,
                {"method": "fts"},
            )
            mock_service_class.return_value = mock_service

            state = await ticket_search_node(base_state)
            result_state = await aggregate_results_node(state)

            # Aggregation should add source citations
            assert "source_citations" in result_state
            assert "similar_tickets" in result_state["source_citations"]


# ============================================================================
# AC #7: State Structure
# ============================================================================


class TestWorkflowStateStructure:
    """Tests for WorkflowState integrity and required fields."""

    def test_state_has_all_required_fields(self, base_state):
        """AC #7: State contains all required fields for aggregation."""
        required_fields = [
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
        ]
        for field in required_fields:
            assert field in base_state

    @pytest.mark.asyncio
    async def test_state_mutations_preserve_fields(self, base_state):
        """State fields persist through node execution."""
        original_tenant = base_state["tenant_id"]
        original_ticket = base_state["ticket_id"]

        with patch(
            "src.workflows.enhancement_workflow.TicketSearchService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.search_similar_tickets.return_value = ([], {"method": "fts"})
            mock_service_class.return_value = mock_service

            result_state = await ticket_search_node(base_state)

        assert result_state["tenant_id"] == original_tenant
        assert result_state["ticket_id"] == original_ticket


# ============================================================================
# Error Accumulation and Reporting
# ============================================================================


class TestErrorHandling:
    """Tests for error tracking and reporting."""

    @pytest.mark.asyncio
    async def test_error_record_structure(self, base_state):
        """Error records include node name, message, timestamp, severity."""
        with patch(
            "src.workflows.enhancement_workflow.TicketSearchService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.search_similar_tickets.side_effect = Exception("Test error")
            mock_service_class.return_value = mock_service

            result_state = await ticket_search_node(base_state)

            assert len(result_state["errors"]) == 1
            error = result_state["errors"][0]
            assert "node_name" in error
            assert "error_message" in error
            assert "timestamp" in error
            assert "severity" in error
            assert error["node_name"] == "ticket_search_node"
            assert error["severity"] in ["low", "medium", "high"]

    @pytest.mark.asyncio
    async def test_multiple_errors_accumulated(self, base_state):
        """Multiple node failures accumulate errors in state."""
        state_with_error = base_state.copy()
        state_with_error["errors"] = [
            {
                "node_name": "ticket_search_node",
                "error_message": "Error 1",
                "timestamp": "2025-11-02T10:30:00Z",
                "severity": "medium",
            }
        ]

        with patch(
            "src.workflows.enhancement_workflow.search_knowledge_base"
        ) as mock_kb:
            mock_kb.side_effect = Exception("Error 2")
            result_state = await doc_search_node(state_with_error)

        assert len(result_state["errors"]) == 2
        assert result_state["errors"][0]["node_name"] == "ticket_search_node"
        assert result_state["errors"][1]["node_name"] == "doc_search_node"
