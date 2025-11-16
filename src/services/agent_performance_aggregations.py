"""
Agent Performance Aggregations Module.

Specialized module for post-processing and aggregating query results.
Handles error categorization, calculations, and data transformations.

Following 2025 best practices:
- Pure functions for deterministic behavior
- Pandas for efficient aggregations
- Type hints with Optional, Dict, List
"""

import logging
from datetime import date
from typing import Dict, List, Optional, Tuple
from uuid import UUID

import pandas as pd

logger = logging.getLogger(__name__)


class AgentPerformanceAggregator:
    """Aggregation and calculation logic for performance metrics."""

    @staticmethod
    def calculate_success_rate(successful: int, total: int) -> float:
        """
        Calculate success rate as percentage.

        Args:
            successful: Number of successful executions
            total: Total number of executions

        Returns:
            Success rate as percentage (0-100), or 0.0 if no executions
        """
        if total == 0:
            return 0.0
        return (successful / total) * 100

    @staticmethod
    def ms_to_seconds(milliseconds: int) -> float:
        """
        Convert milliseconds to seconds.

        Args:
            milliseconds: Duration in milliseconds

        Returns:
            Duration in seconds (rounded to 3 decimal places)
        """
        return round(milliseconds / 1000, 3)

    @staticmethod
    def categorize_error(error_data: Optional[Dict]) -> str:
        """
        Categorize error from errors JSONB field.

        Maps error types to categories: timeout, rate_limit, validation_error,
        tool_failure, other.

        Args:
            error_data: Error dict from execution record

        Returns:
            Error category string
        """
        if not error_data:
            return "other"

        error_msg = (error_data.get("error_message") or "").lower()
        error_type = (error_data.get("error_type") or "").lower()
        failed_step = (error_data.get("failed_step") or "").lower()

        # Timeout detection
        if "timeout" in error_msg or "timeout" in error_type:
            return "timeout"

        # Rate limit detection
        if "rate limit" in error_msg or "rate_limit" in error_type or "429" in error_msg:
            return "rate_limit"

        # Validation error detection
        if "validation" in error_msg or "validation" in error_type:
            return "validation_error"

        # Tool failure detection
        if "tool" in error_msg or "tool_failure" in error_type or failed_step.startswith("tool call"):
            return "tool_failure"

        return "other"

    @staticmethod
    def aggregate_error_analysis(executions: List[dict]) -> Dict[str, int]:
        """
        Aggregate error types from execution history.

        Args:
            executions: List of execution records from get_execution_history

        Returns:
            Dict mapping error categories to counts
        """
        error_counts: Dict[str, int] = {
            "timeout": 0,
            "rate_limit": 0,
            "validation_error": 0,
            "tool_failure": 0,
            "other": 0,
        }

        for execution in executions:
            if execution.get("status") == "failed":
                error_data = {
                    "error_message": execution.get("error_message"),
                    "error_type": execution.get("error_type"),
                }
                category = AgentPerformanceAggregator.categorize_error(error_data)
                error_counts[category] += 1

        return error_counts

    @staticmethod
    def aggregate_token_usage_by_agent(
        executions: List[dict], tenant_agents: List[dict]
    ) -> List[dict]:
        """
        Aggregate token usage across executions per agent.

        Args:
            executions: List of execution records
            tenant_agents: List of available agents

        Returns:
            List of dicts with agent_id, agent_name, input_tokens, output_tokens, etc.
        """
        if not executions:
            return []

        # Create DataFrame for efficient aggregation
        df = pd.DataFrame(executions)

        # Filter for executions only (success status)
        df = df[df["status"] == "success"].copy()

        if df.empty:
            return []

        # Group by agent (need to join with agent info)
        # For now, aggregate by agent_id from executions if available
        # Note: execution records don't have agent_id, so this needs to be done
        # at query level or through join in service

        return []

    @staticmethod
    def calculate_optimization_recommendation(
        p95_latency_ms: int, avg_duration_ms: int, success_rate: float
    ) -> str:
        """
        Generate optimization recommendation based on metrics.

        Args:
            p95_latency_ms: P95 latency in milliseconds
            avg_duration_ms: Average duration in milliseconds
            success_rate: Success rate as percentage

        Returns:
            Recommendation string
        """
        p95_seconds = AgentPerformanceAggregator.ms_to_seconds(p95_latency_ms)

        if p95_seconds >= 15:
            return "Review slow tool calls, consider async execution or parallel processing"
        elif avg_duration_ms > 10000:  # > 10 seconds
            return "Optimize prompt length, reduce context size, consider caching"
        elif success_rate < 90:
            return "Investigate frequent failures, add error handling, review timeout settings"
        else:
            return "Performance OK"

    @staticmethod
    def normalize_metrics_from_query(
        agent_id: UUID,
        agent_name: str,
        query_result: dict,
        start_date: date,
        end_date: date,
    ) -> dict:
        """
        Normalize raw query results to DTO-compatible dict.

        Converts milliseconds to seconds, calculates success rate, etc.

        Args:
            agent_id: Agent UUID
            agent_name: Agent name
            query_result: Raw result from get_agent_metrics()
            start_date: Query start date
            end_date: Query end date

        Returns:
            Normalized dict ready for AgentMetricsDTO
        """
        total = query_result["total_executions"]
        successful = query_result["successful_executions"]

        return {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "total_executions": total,
            "successful_executions": successful,
            "failed_executions": query_result["failed_executions"],
            "success_rate": AgentPerformanceAggregator.calculate_success_rate(
                successful, total
            ),
            "average_duration_seconds": AgentPerformanceAggregator.ms_to_seconds(
                query_result["average_duration_ms"]
            ),
            "p50_latency_seconds": AgentPerformanceAggregator.ms_to_seconds(
                query_result["p50_latency_ms"]
            ),
            "p95_latency_seconds": AgentPerformanceAggregator.ms_to_seconds(
                query_result["p95_latency_ms"]
            ),
            "p99_latency_seconds": AgentPerformanceAggregator.ms_to_seconds(
                query_result["p99_latency_ms"]
            ),
            "start_date": start_date,
            "end_date": end_date,
        }

    @staticmethod
    def normalize_execution_records(
        raw_records: List[dict],
    ) -> List[dict]:
        """
        Normalize execution history records for response.

        Converts timestamps, formats tokens/cost, etc.

        Args:
            raw_records: Raw records from get_execution_history()

        Returns:
            List of normalized dicts
        """
        return [
            {
                "execution_id": record["execution_id"],
                "timestamp": record["timestamp"],
                "status": record["status"],
                "duration_ms": record["duration_ms"],
                "duration_seconds": AgentPerformanceAggregator.ms_to_seconds(
                    record["duration_ms"]
                ),
                "input_tokens": record["input_tokens"],
                "output_tokens": record["output_tokens"],
                "total_tokens": record["input_tokens"] + record["output_tokens"],
                "estimated_cost_usd": round(record["estimated_cost_usd"], 4),
                "error_message": record.get("error_message"),
                "error_type": record.get("error_type"),
                "error_category": (
                    AgentPerformanceAggregator.categorize_error(
                        {
                            "error_message": record.get("error_message"),
                            "error_type": record.get("error_type"),
                        }
                    )
                    if record["status"] == "failed"
                    else None
                ),
            }
            for record in raw_records
        ]

    @staticmethod
    def normalize_trend_data(raw_trends: List[dict]) -> List[dict]:
        """
        Normalize trend data for charting.

        Converts to consistent units (seconds, %).

        Args:
            raw_trends: Raw trends from get_performance_trends()

        Returns:
            List of normalized trend dicts
        """
        return [
            {
                "trend_date": trend["date"],
                "execution_count": trend["execution_count"],
                "successful": trend["successful"],
                "failed": trend["failed"],
                "success_rate": (
                    (trend["successful"] / trend["execution_count"] * 100)
                    if trend["execution_count"] > 0
                    else 0.0
                ),
                "average_duration_seconds": trend["average_duration_seconds"],
            }
            for trend in raw_trends
        ]

    @staticmethod
    def normalize_slowest_agents(raw_slowest: List[dict]) -> List[dict]:
        """
        Normalize slowest agents with recommendations.

        Args:
            raw_slowest: Raw results from get_slowest_agents()

        Returns:
            List of normalized slowest agent dicts
        """
        return [
            {
                "agent_id": agent["agent_id"],
                "agent_name": agent["agent_name"],
                "execution_count": agent["execution_count"],
                "p95_latency_seconds": AgentPerformanceAggregator.ms_to_seconds(
                    agent["p95_latency_ms"]
                ),
                "average_duration_seconds": AgentPerformanceAggregator.ms_to_seconds(
                    agent["average_duration_ms"]
                ),
                "success_rate": agent["success_rate"],
                "optimization_recommendation": (
                    AgentPerformanceAggregator.calculate_optimization_recommendation(
                        agent["p95_latency_ms"],
                        agent["average_duration_ms"],
                        agent["success_rate"],
                    )
                ),
            }
            for agent in raw_slowest
        ]
