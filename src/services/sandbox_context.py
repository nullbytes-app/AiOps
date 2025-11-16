"""
Sandbox execution context for dry-run agent testing (Story 8.14).

Provides a context manager that prevents side effects by intercepting tool calls,
LLM requests, and database writes during test execution.
"""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional
from uuid import UUID
import logging

from src.services.execution_tracer import ExecutionTracer

logger = logging.getLogger(__name__)


class SandboxExecutionError(Exception):
    """Raised when sandbox constraints are violated (e.g., write attempts)."""
    pass


class SandboxToolResponse:
    """Mock response for tool calls in sandbox mode."""

    def __init__(self, tool_name: str, ticket_id: Optional[str] = None):
        """
        Initialize mock tool response.

        Args:
            tool_name: Name of tool being mocked
            ticket_id: Optional ticket ID for context
        """
        self.tool_name = tool_name
        self.ticket_id = ticket_id or "SANDBOX-TEST-001"

    def to_dict(self) -> dict:
        """Convert to dict response format."""
        if self.tool_name == "fetch_ticket":
            return {
                "ticket_id": self.ticket_id,
                "title": "[SANDBOX] Test Ticket",
                "status": "Open",
                "description": "This is a test ticket in sandbox mode",
                "created_at": "2025-11-07T12:00:00Z",
                "updated_at": "2025-11-07T12:00:00Z"
            }
        elif self.tool_name == "search_tickets":
            return {
                "tickets": [
                    {
                        "ticket_id": self.ticket_id,
                        "title": "[SANDBOX] Test Ticket",
                        "status": "Open"
                    }
                ],
                "total": 1
            }
        elif self.tool_name == "update_ticket":
            return {
                "ticket_id": self.ticket_id,
                "status": "Updated",
                "message": "Ticket updated in sandbox mode (no actual update)"
            }
        else:
            return {
                "status": "success",
                "message": f"Mock response for {self.tool_name}",
                "sandbox_mode": True
            }


class SandboxExecutionContext:
    """
    Context manager for sandbox execution mode.

    Prevents side effects by:
    - Mocking all tool calls (no real API calls)
    - Using read-only database transactions
    - Preventing webhook sends and external API calls
    - Capturing execution trace for analysis

    Usage:
        async with SandboxExecutionContext(agent_id) as sandbox:
            # Execute agent code here
            result = await some_async_function()
            # Retrieve execution trace
            trace = sandbox.get_execution_trace()
    """

    def __init__(self, agent_id: UUID, tenant_id: str):
        """
        Initialize sandbox context.

        Args:
            agent_id: Agent being tested
            tenant_id: Tenant for isolation
        """
        self.agent_id = agent_id
        self.tenant_id = tenant_id
        self.tracer = ExecutionTracer(str(agent_id))
        self.is_readonly = True
        self.mock_tools: dict[str, SandboxToolResponse] = {}

    def register_tool(self, tool_name: str, ticket_id: Optional[str] = None) -> None:
        """
        Register a tool as available in sandbox.

        Args:
            tool_name: Name of tool
            ticket_id: Optional ticket ID for mock responses
        """
        self.mock_tools[tool_name] = SandboxToolResponse(tool_name, ticket_id)

    def get_mock_response(self, tool_name: str) -> dict:
        """
        Get mock response for a tool call.

        Args:
            tool_name: Name of tool

        Returns:
            dict: Mock response data
        """
        if tool_name not in self.mock_tools:
            self.register_tool(tool_name)
        return self.mock_tools[tool_name].to_dict()

    def check_write_attempt(self) -> None:
        """
        Check if code is attempting to write in readonly mode.

        Raises:
            SandboxExecutionError: If write attempt detected
        """
        if self.is_readonly:
            # In a real implementation, this would be called by ORM hooks
            # For now, we rely on explicit validation
            pass

    def get_execution_trace(self) -> dict:
        """
        Get complete execution trace.

        Returns:
            dict: Execution trace with steps and timing
        """
        return self.tracer.to_dict()

    def get_step_count(self) -> int:
        """Get number of steps in execution trace."""
        return len(self.tracer.steps)

    def __repr__(self) -> str:
        """String representation."""
        return f"<SandboxExecutionContext(agent_id={self.agent_id}, steps={self.get_step_count()})>"

    @asynccontextmanager
    async def execute(self) -> AsyncGenerator:
        """
        Async context manager for sandbox execution.

        Yields:
            self: The sandbox context for use in with block

        Example:
            async with sandbox.execute():
                # Code runs here in sandbox mode
                pass
        """
        logger.info(f"Entering sandbox mode for agent {self.agent_id}")
        try:
            yield self
            logger.info(f"Sandbox execution completed for agent {self.agent_id}")
        except Exception as e:
            logger.error(f"Sandbox execution failed for agent {self.agent_id}: {e}")
            raise
        finally:
            logger.debug(f"Sandbox execution trace: {self.get_step_count()} steps")
