"""
Pydantic schemas for agent testing and sandbox execution (Story 8.14).

Defines data validation schemas for test execution requests/responses, execution traces,
token usage tracking, and timing breakdowns. Following 2025 Pydantic v2 best practices.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ExecutionStep(BaseModel):
    """
    Single step in agent execution trace.

    Attributes:
        step_number: Sequence number in execution
        step_type: "tool_call" or "llm_request"
        tool_name: Name of tool called (for tool_call steps)
        model: Model name (for llm_request steps)
        input: Input parameters
        output: Result/response
        timestamp: ISO 8601 timestamp with nanosecond precision
        duration_ms: How long this step took
    """

    step_number: int = Field(..., ge=1, description="Sequence number in execution")
    step_type: str = Field(..., description="'tool_call' or 'llm_request'")
    tool_name: Optional[str] = Field(None, description="Name of tool (for tool calls)")
    model: Optional[str] = Field(None, description="Model name (for LLM requests)")
    input: dict = Field(..., description="Input parameters")
    output: Any = Field(..., description="Result or response")
    timestamp: datetime = Field(..., description="When this step executed")
    duration_ms: float = Field(..., ge=0, description="Execution time in milliseconds")

    model_config = ConfigDict(from_attributes=True)


class ExecutionTrace(BaseModel):
    """
    Complete execution trace with all steps.

    Attributes:
        steps: List of execution steps
        total_duration_ms: Total execution time
        status: success or failed
    """

    steps: list[ExecutionStep] = Field(..., description="List of execution steps")
    total_duration_ms: float = Field(..., ge=0, description="Total execution time")
    status: str = Field(..., description="'success' or 'failed'")

    model_config = ConfigDict(from_attributes=True)


class TokenUsage(BaseModel):
    """
    Token usage and cost tracking.

    Attributes:
        input_tokens: Tokens in LLM prompts
        output_tokens: Tokens in LLM responses
        total_tokens: Sum of input + output
        estimated_cost_usd: Estimated cost based on model pricing
    """

    input_tokens: int = Field(..., ge=0, description="Input tokens used")
    output_tokens: int = Field(..., ge=0, description="Output tokens generated")
    total_tokens: int = Field(..., ge=0, description="Total tokens")
    estimated_cost_usd: float = Field(..., ge=0, description="Estimated cost in USD")

    model_config = ConfigDict(from_attributes=True)


class ExecutionTiming(BaseModel):
    """
    Execution timing breakdown.

    Attributes:
        total_duration_ms: Total execution time
        steps: Breakdown by step (name and duration)
    """

    total_duration_ms: float = Field(..., ge=0, description="Total duration in ms")
    steps: list[dict] = Field(
        default_factory=list,
        description="Breakdown: [{name: str, duration_ms: float}]"
    )

    model_config = ConfigDict(from_attributes=True)


class ErrorDetails(BaseModel):
    """
    Error information if execution failed.

    Attributes:
        error_type: Type of error
        message: Error message
        stack_trace: Full stack trace for debugging
    """

    error_type: str = Field(..., description="Type of error")
    message: str = Field(..., description="Error message")
    stack_trace: Optional[str] = Field(None, description="Full stack trace")

    model_config = ConfigDict(from_attributes=True)


class AgentTestRequest(BaseModel):
    """
    Request to execute agent test.

    Attributes:
        payload: Test payload (webhook data or trigger parameters)
        simulate_webhook: True to simulate webhook trigger (False for scheduled)
    """

    payload: dict = Field(..., description="Test payload: webhook data or trigger params")
    simulate_webhook: bool = Field(
        default=True,
        description="True for webhook simulation, False for scheduled trigger"
    )

    model_config = ConfigDict(from_attributes=True)


class AgentTestResponse(BaseModel):
    """
    Response from agent test execution.

    Attributes:
        test_id: UUID of this test execution
        agent_id: Agent being tested
        status: success or failed
        execution_trace: Step-by-step execution details
        token_usage: Token tracking
        execution_time: Timing breakdown
        errors: Error details if failed
        created_at: When test was executed
    """

    test_id: UUID = Field(..., description="Test execution ID")
    agent_id: UUID = Field(..., description="Agent being tested")
    status: str = Field(..., description="'success' or 'failed'")
    execution_trace: ExecutionTrace = Field(..., description="Step-by-step execution")
    token_usage: TokenUsage = Field(..., description="Token usage and cost")
    execution_time: ExecutionTiming = Field(..., description="Timing breakdown")
    errors: Optional[ErrorDetails] = Field(None, description="Error details if failed")
    created_at: datetime = Field(..., description="When test was executed")

    model_config = ConfigDict(from_attributes=True)


class AgentTestHistoryResponse(BaseModel):
    """
    Response for paginated test history.

    Attributes:
        test_id: UUID of this test execution
        agent_id: Agent being tested
        status: success or failed
        token_usage: Token usage summary
        created_at: When test was executed
    """

    test_id: UUID = Field(..., description="Test execution ID")
    agent_id: UUID = Field(..., description="Agent being tested")
    status: str = Field(..., description="'success' or 'failed'")
    token_usage: TokenUsage = Field(..., description="Token usage summary")
    created_at: datetime = Field(..., description="When test was executed")

    model_config = ConfigDict(from_attributes=True)


class TestComparisonRequest(BaseModel):
    """
    Request to compare two test results.

    Attributes:
        test_id_1: First test execution ID
        test_id_2: Second test execution ID
    """

    test_id_1: UUID = Field(..., description="First test execution ID")
    test_id_2: UUID = Field(..., description="Second test execution ID")

    model_config = ConfigDict(from_attributes=True)


class TestComparisonResult(BaseModel):
    """
    Result of comparing two test executions.

    Attributes:
        test_id_1: First test ID
        test_id_2: Second test ID
        status_changed: True if status differs
        token_delta: Difference in tokens (test2 - test1)
        cost_delta: Difference in cost (test2 - test1)
        timing_delta: Difference in duration (test2 - test1)
        trace_differences: List of differences in execution trace
    """

    test_id_1: UUID = Field(..., description="First test ID")
    test_id_2: UUID = Field(..., description="Second test ID")
    status_changed: bool = Field(..., description="True if status differs")
    token_delta: int = Field(..., description="Difference in total tokens")
    cost_delta: float = Field(..., description="Difference in estimated cost")
    timing_delta: float = Field(..., description="Difference in duration ms")
    trace_differences: list[str] = Field(
        default_factory=list,
        description="List of differences in execution trace"
    )

    model_config = ConfigDict(from_attributes=True)
