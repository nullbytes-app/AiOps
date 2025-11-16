"""
Unit tests for Agent Performance Service.

Tests core metrics calculation, aggregation logic, and service methods.
Includes tests for percentile calculations, error categorization, and tenant isolation.
"""

from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.agent_performance import AgentMetricsDTO, ExecutionRecordDTO, TrendDataDTO
from src.services.agent_performance_aggregations import AgentPerformanceAggregator
from src.services.agent_performance_service import AgentPerformanceService


class TestAgentPerformanceAggregator:
    """Tests for aggregation helper functions."""

    def test_calculate_success_rate_100_percent(self):
        """Test success rate calculation when all succeed."""
        rate = AgentPerformanceAggregator.calculate_success_rate(100, 100)
        assert rate == 100.0

    def test_calculate_success_rate_50_percent(self):
        """Test success rate calculation for 50% success."""
        rate = AgentPerformanceAggregator.calculate_success_rate(50, 100)
        assert rate == 50.0

    def test_calculate_success_rate_zero_executions(self):
        """Test success rate when no executions."""
        rate = AgentPerformanceAggregator.calculate_success_rate(0, 0)
        assert rate == 0.0

    def test_ms_to_seconds_conversion(self):
        """Test milliseconds to seconds conversion."""
        seconds = AgentPerformanceAggregator.ms_to_seconds(1000)
        assert seconds == 1.0

    def test_ms_to_seconds_decimal(self):
        """Test milliseconds to seconds with decimal."""
        seconds = AgentPerformanceAggregator.ms_to_seconds(1234)
        assert seconds == 1.234

    def test_categorize_error_timeout(self):
        """Test error categorization for timeout."""
        error = {"error_message": "Request timeout after 30s"}
        category = AgentPerformanceAggregator.categorize_error(error)
        assert category == "timeout"

    def test_categorize_error_rate_limit(self):
        """Test error categorization for rate limit."""
        error = {"error_message": "Rate limit exceeded"}
        category = AgentPerformanceAggregator.categorize_error(error)
        assert category == "rate_limit"

    def test_categorize_error_validation(self):
        """Test error categorization for validation."""
        error = {"error_type": "validation_error"}
        category = AgentPerformanceAggregator.categorize_error(error)
        assert category == "validation_error"

    def test_categorize_error_tool_failure(self):
        """Test error categorization for tool failure."""
        error = {"error_message": "Tool call failed", "failed_step": "Tool Call: fetch_ticket"}
        category = AgentPerformanceAggregator.categorize_error(error)
        assert category == "tool_failure"

    def test_categorize_error_other(self):
        """Test error categorization for unknown error."""
        error = {"error_message": "Some unexpected error"}
        category = AgentPerformanceAggregator.categorize_error(error)
        assert category == "other"

    def test_categorize_error_none(self):
        """Test error categorization with None."""
        category = AgentPerformanceAggregator.categorize_error(None)
        assert category == "other"

    def test_aggregate_error_analysis(self):
        """Test error aggregation from execution records."""
        executions = [
            {"status": "failed", "error_message": "timeout", "error_type": None},
            {"status": "failed", "error_message": "rate limit", "error_type": None},
            {"status": "success", "error_message": None, "error_type": None},
        ]
        counts = AgentPerformanceAggregator.aggregate_error_analysis(executions)
        assert counts["timeout"] == 1
        assert counts["rate_limit"] == 1
        assert counts["other"] == 0

    def test_calculate_optimization_recommendation_slow_p95(self):
        """Test optimization recommendation for slow P95."""
        rec = AgentPerformanceAggregator.calculate_optimization_recommendation(
            p95_latency_ms=20000, avg_duration_ms=5000, success_rate=95.0
        )
        assert "slow tool calls" in rec.lower()

    def test_calculate_optimization_recommendation_slow_avg(self):
        """Test optimization recommendation for slow average."""
        rec = AgentPerformanceAggregator.calculate_optimization_recommendation(
            p95_latency_ms=5000, avg_duration_ms=12000, success_rate=95.0
        )
        assert "prompt length" in rec.lower()

    def test_calculate_optimization_recommendation_low_success(self):
        """Test optimization recommendation for low success rate."""
        rec = AgentPerformanceAggregator.calculate_optimization_recommendation(
            p95_latency_ms=5000, avg_duration_ms=5000, success_rate=80.0
        )
        assert "failures" in rec.lower()

    def test_calculate_optimization_recommendation_ok(self):
        """Test optimization recommendation for good performance."""
        rec = AgentPerformanceAggregator.calculate_optimization_recommendation(
            p95_latency_ms=5000, avg_duration_ms=3000, success_rate=98.0
        )
        assert rec == "Performance OK"

    def test_normalize_metrics_from_query(self):
        """Test metric normalization from raw query results."""
        query_result = {
            "total_executions": 100,
            "successful_executions": 95,
            "failed_executions": 5,
            "average_duration_ms": 5000,
            "p50_latency_ms": 3000,
            "p95_latency_ms": 8000,
            "p99_latency_ms": 10000,
        }
        agent_id = uuid4()
        normalized = AgentPerformanceAggregator.normalize_metrics_from_query(
            agent_id,
            "TestAgent",
            query_result,
            date(2025, 1, 1),
            date(2025, 1, 7),
        )

        assert normalized["agent_id"] == agent_id
        assert normalized["agent_name"] == "TestAgent"
        assert normalized["total_executions"] == 100
        assert normalized["success_rate"] == 95.0
        assert normalized["average_duration_seconds"] == 5.0
        assert normalized["p95_latency_seconds"] == 8.0

    def test_normalize_execution_records(self):
        """Test execution record normalization."""
        records = [
            {
                "execution_id": uuid4(),
                "timestamp": datetime.now(),
                "status": "success",
                "duration_ms": 2000,
                "input_tokens": 100,
                "output_tokens": 50,
                "estimated_cost_usd": 0.0123,
                "error_message": None,
                "error_type": None,
            }
        ]
        normalized = AgentPerformanceAggregator.normalize_execution_records(records)
        assert len(normalized) == 1
        assert normalized[0]["duration_seconds"] == 2.0
        assert normalized[0]["total_tokens"] == 150
        assert normalized[0]["estimated_cost_usd"] == 0.0123

    def test_normalize_trend_data(self):
        """Test trend data normalization."""
        trends = [
            {
                "date": date(2025, 1, 7),
                "execution_count": 50,
                "successful": 48,
                "failed": 2,
                "average_duration_seconds": 3.5,
            }
        ]
        normalized = AgentPerformanceAggregator.normalize_trend_data(trends)
        assert len(normalized) == 1
        assert normalized[0]["success_rate"] == 96.0
        assert normalized[0]["execution_count"] == 50


@pytest.mark.asyncio
class TestAgentPerformanceService:
    """Tests for the performance service facade."""

    @pytest.fixture
    def mock_db(self):
        """Create mock AsyncSession."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def service(self, mock_db):
        """Create service instance with mock DB."""
        return AgentPerformanceService(mock_db)

    async def test_get_agent_metrics(self, service, mock_db):
        """Test get_agent_metrics service method."""
        agent_id = uuid4()

        # Mock the query builder response
        with patch.object(
            service.query_builder,
            "get_agent_metrics",
            new_callable=AsyncMock,
        ) as mock_query:
            mock_query.return_value = {
                "total_executions": 100,
                "successful_executions": 95,
                "failed_executions": 5,
                "average_duration_ms": 5000,
                "p50_latency_ms": 3000,
                "p95_latency_ms": 8000,
                "p99_latency_ms": 10000,
            }

            metrics = await service.get_agent_metrics(
                agent_id,
                "TestAgent",
                date(2025, 1, 1),
                date(2025, 1, 7),
            )

            assert isinstance(metrics, AgentMetricsDTO)
            assert metrics.total_executions == 100
            assert metrics.success_rate == 95.0

    async def test_get_execution_history(self, service, mock_db):
        """Test get_execution_history service method."""
        agent_id = uuid4()

        with patch.object(
            service.query_builder,
            "get_execution_history",
            new_callable=AsyncMock,
        ) as mock_query:
            mock_query.return_value = (
                [
                    {
                        "execution_id": uuid4(),
                        "timestamp": datetime.now(),
                        "status": "success",
                        "duration_ms": 2000,
                        "input_tokens": 100,
                        "output_tokens": 50,
                        "estimated_cost_usd": 0.01,
                        "error_message": None,
                        "error_type": None,
                    }
                ],
                100,
            )

            records, total = await service.get_execution_history(agent_id, None, 50, 0)

            assert len(records) == 1
            assert isinstance(records[0], ExecutionRecordDTO)
            assert total == 100

    async def test_get_performance_trends(self, service, mock_db):
        """Test get_performance_trends service method."""
        agent_id = uuid4()

        with patch.object(
            service.query_builder,
            "get_performance_trends",
            new_callable=AsyncMock,
        ) as mock_query:
            mock_query.return_value = [
                {
                    "date": date(2025, 1, 7),
                    "execution_count": 50,
                    "successful": 48,
                    "failed": 2,
                    "average_duration_seconds": 3.5,
                }
            ]

            trends = await service.get_performance_trends(agent_id, 7)

            assert len(trends) == 1
            assert isinstance(trends[0], TrendDataDTO)
            assert trends[0].execution_count == 50

    async def test_get_error_analysis(self, service, mock_db):
        """Test get_error_analysis service method."""
        agent_id = uuid4()

        with patch.object(
            service.query_builder,
            "get_execution_history",
            new_callable=AsyncMock,
        ) as mock_query:
            mock_query.return_value = (
                [
                    {
                        "status": "failed",
                        "error_message": "timeout",
                        "error_type": None,
                    },
                    {
                        "status": "success",
                        "error_message": None,
                        "error_type": None,
                    },
                ],
                2,
            )

            error_counts = await service.get_error_analysis(
                agent_id,
                date(2025, 1, 1),
                date(2025, 1, 7),
            )

            assert error_counts["timeout"] == 1

    async def test_get_slowest_agents(self, service, mock_db):
        """Test get_slowest_agents service method."""
        tenant_id = "test-tenant"

        with patch.object(
            service.query_builder,
            "get_slowest_agents",
            new_callable=AsyncMock,
        ) as mock_query:
            mock_query.return_value = [
                {
                    "agent_id": uuid4(),
                    "agent_name": "SlowAgent",
                    "execution_count": 50,
                    "p95_latency_ms": 15000,
                    "average_duration_ms": 10000,
                    "success_rate": 90.0,
                }
            ]

            slowest = await service.get_slowest_agents(tenant_id, 10)

            assert len(slowest) == 1
            assert slowest[0].agent_name == "SlowAgent"
            assert slowest[0].optimization_recommendation != "Performance OK"
