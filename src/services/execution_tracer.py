"""
Execution trace logging utility for agent testing (Story 8.14).

Captures step-by-step execution details including tool calls, LLM requests,
and timing information for debugging and analysis.
"""

from datetime import datetime, timezone
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
import json


@dataclass
class ExecutionStep:
    """Single step in execution trace."""

    step_number: int
    step_type: str  # "tool_call" or "llm_request"
    input_data: dict
    output_data: Any
    timestamp: datetime
    duration_ms: float
    tool_name: Optional[str] = None
    model_name: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        # Ensure output is JSON serializable
        if hasattr(self.output_data, '__dict__'):
            data['output_data'] = str(self.output_data)
        return data


class ExecutionTracer:
    """
    Traces step-by-step agent execution.

    Collects execution steps (tool calls, LLM requests) with timestamps,
    inputs, outputs, and timing information for analysis and debugging.
    """

    def __init__(self, execution_id: str):
        """
        Initialize tracer.

        Args:
            execution_id: Unique identifier for this execution trace
        """
        self.execution_id = execution_id
        self.steps: list[ExecutionStep] = []
        self.start_time = datetime.now(timezone.utc)

    def add_tool_call(
        self,
        tool_name: str,
        input_data: dict,
        output_data: Any,
        duration_ms: float
    ) -> None:
        """
        Record a tool call step.

        Args:
            tool_name: Name of tool that was called
            input_data: Input parameters
            output_data: Result from tool
            duration_ms: How long the call took in milliseconds
        """
        step = ExecutionStep(
            step_number=len(self.steps) + 1,
            step_type="tool_call",
            tool_name=tool_name,
            input_data=input_data,
            output_data=output_data,
            timestamp=datetime.now(timezone.utc),
            duration_ms=duration_ms
        )
        self.steps.append(step)

    def add_llm_request(
        self,
        model_name: str,
        input_data: dict,
        output_data: Any,
        duration_ms: float
    ) -> None:
        """
        Record an LLM request step.

        Args:
            model_name: LLM model name
            input_data: Prompt and parameters
            output_data: LLM response
            duration_ms: How long the request took in milliseconds
        """
        step = ExecutionStep(
            step_number=len(self.steps) + 1,
            step_type="llm_request",
            model_name=model_name,
            input_data=input_data,
            output_data=output_data,
            timestamp=datetime.now(timezone.utc),
            duration_ms=duration_ms
        )
        self.steps.append(step)

    def get_total_duration_ms(self) -> float:
        """
        Get total execution duration in milliseconds.

        Returns:
            float: Total duration
        """
        if not self.steps:
            return 0.0
        return sum(step.duration_ms for step in self.steps)

    def to_dict(self) -> dict:
        """
        Export trace as dictionary for JSON storage.

        Returns:
            dict: Execution trace with steps and timing
        """
        return {
            "execution_id": self.execution_id,
            "steps": [step.to_dict() for step in self.steps],
            "total_duration_ms": self.get_total_duration_ms(),
            "step_count": len(self.steps),
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now(timezone.utc).isoformat()
        }

    def __repr__(self) -> str:
        """String representation."""
        return f"<ExecutionTracer(id={self.execution_id}, steps={len(self.steps)})>"
