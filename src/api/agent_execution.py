"""
Agent Execution API Endpoints

Provides REST API for executing agents with MCP tool support.

Endpoints:
- POST /api/agent-execution/execute - Execute agent with user message
- GET /api/agent-execution/{execution_id}/status - Get execution status (async)

Implements:
- Request validation with Pydantic schemas
- Tenant isolation via X-Tenant-ID header
- Budget enforcement (Story 8.10 integration)
- Structured response format
- Error handling with appropriate HTTP status codes

References:
- Story 11.1.7: MCP Tool Invocation in Agent Execution
- AC#8: REST API endpoint for agent execution
"""

from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header, status
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_tenant_db
from src.exceptions import BudgetExceededError
from src.services.agent_execution_service import (
    AgentExecutionError,
    AgentExecutionService,
)

router = APIRouter(prefix="/api/agent-execution", tags=["agent-execution"])


# ============================================================================
# Request/Response Schemas
# ============================================================================


class AgentExecutionRequest(BaseModel):
    """Request schema for agent execution."""

    agent_id: UUID = Field(..., description="Agent UUID to execute")
    user_message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="User's input message to the agent",
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional context dict for prompt variable substitution",
    )
    timeout_seconds: int = Field(
        default=120,
        ge=10,
        le=600,
        description="Maximum execution time in seconds (10-600)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_message": "Analyze ticket #123 and suggest resolution steps",
                "context": {"ticket_id": 123, "priority": "high"},
                "timeout_seconds": 120,
            }
        }


class ToolCall(BaseModel):
    """Tool call record in execution history."""

    tool_name: str = Field(..., description="Name of the tool invoked")
    tool_input: Dict[str, Any] = Field(..., description="Input arguments to the tool")
    tool_output: str = Field(..., description="Output returned by the tool")
    timestamp: str = Field(..., description="ISO 8601 timestamp of invocation")


class AgentExecutionResponse(BaseModel):
    """Response schema for agent execution."""

    success: bool = Field(..., description="Whether execution succeeded")
    response: str = Field(..., description="Agent's final response text")
    tool_calls: list[ToolCall] = Field(
        ..., description="History of tool invocations during execution"
    )
    execution_time_seconds: float = Field(..., description="Total execution time in seconds")
    model_used: str = Field(..., description="LLM model used (e.g., openai/gpt-4o-mini)")
    error: Optional[str] = Field(default=None, description="Error message if success=False")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "response": "I've analyzed ticket #123. Here are the resolution steps...",
                "tool_calls": [
                    {
                        "tool_name": "get_ticket_details",
                        "tool_input": {"ticket_id": 123},
                        "tool_output": '{"id": 123, "status": "open", ...}',
                        "timestamp": "2025-01-09T12:34:56.789Z",
                    }
                ],
                "execution_time_seconds": 3.45,
                "model_used": "openai/gpt-4o-mini",
                "error": None,
            }
        }


class BudgetExceededResponse(BaseModel):
    """Response schema for budget exceeded error."""

    detail: str = Field(..., description="Error message")
    tenant_id: str = Field(..., description="Tenant identifier")
    current_spend: float = Field(..., description="Current spend in USD")
    max_budget: float = Field(..., description="Maximum budget in USD")
    grace_threshold: float = Field(..., description="Grace threshold percentage (e.g., 110.0)")


# ============================================================================
# API Endpoints
# ============================================================================


@router.post(
    "/execute",
    response_model=AgentExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute agent with user message",
    description="""
    Execute an agent with LangGraph ReAct workflow and MCP tool support.

    Features:
    - Multi-tenant execution with budget enforcement
    - OpenAPI + MCP tool invocation
    - Structured response with tool call history
    - Graceful error handling

    Authorization:
    - Requires X-Tenant-ID header for tenant isolation

    Budget Enforcement:
    - Checks tenant budget before execution (Story 8.10)
    - Returns 402 Payment Required if budget exceeded

    Errors:
    - 400 Bad Request: Invalid input (agent_id, timeout, etc.)
    - 402 Payment Required: Budget exceeded
    - 404 Not Found: Agent not found or belongs to different tenant
    - 500 Internal Server Error: Execution failed
    """,
    responses={
        200: {
            "description": "Agent executed successfully",
            "model": AgentExecutionResponse,
        },
        400: {"description": "Invalid request parameters"},
        402: {
            "description": "Budget exceeded",
            "model": BudgetExceededResponse,
        },
        404: {"description": "Agent not found or tenant mismatch"},
        500: {"description": "Agent execution failed"},
    },
)
async def execute_agent(
    request: AgentExecutionRequest,
    x_tenant_id: str = Header(..., description="Tenant identifier for isolation"),
    db: AsyncSession = Depends(get_tenant_db),
) -> AgentExecutionResponse:
    """
    Execute agent with user message and return structured response.

    Args:
        request: AgentExecutionRequest with agent_id, user_message, context, timeout
        x_tenant_id: Tenant identifier from X-Tenant-ID header
        db: Database session dependency

    Returns:
        AgentExecutionResponse with success, response, tool_calls, execution_time, model_used, error

    Raises:
        HTTPException(400): Invalid request parameters
        HTTPException(402): Budget exceeded (BudgetExceededError)
        HTTPException(404): Agent not found or tenant mismatch
        HTTPException(500): Agent execution failed
    """
    logger.info(
        f"Agent execution request",
        extra={
            "agent_id": str(request.agent_id),
            "tenant_id": x_tenant_id,
            "message_length": len(request.user_message),
            "timeout_seconds": request.timeout_seconds,
        },
    )

    try:
        # Initialize execution service
        execution_service = AgentExecutionService(db)

        # Execute agent with tenant isolation
        result = await execution_service.execute_agent(
            agent_id=request.agent_id,
            tenant_id=x_tenant_id,
            user_message=request.user_message,
            context=request.context,
            timeout_seconds=request.timeout_seconds,
        )

        # Convert tool_calls to ToolCall schema
        tool_calls_response = [
            ToolCall(
                tool_name=tc["tool_name"],
                tool_input=tc["tool_input"],
                tool_output=tc["tool_output"],
                timestamp=tc["timestamp"],
            )
            for tc in result["tool_calls"]
        ]

        # Build response
        response = AgentExecutionResponse(
            success=result["success"],
            response=result["response"],
            tool_calls=tool_calls_response,
            execution_time_seconds=result["execution_time_seconds"],
            model_used=result["model_used"],
            error=result.get("error"),
        )

        # If execution failed internally, return 500
        if not result["success"]:
            logger.error(
                f"Agent execution failed",
                extra={
                    "agent_id": str(request.agent_id),
                    "tenant_id": x_tenant_id,
                    "error": result.get("error"),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Agent execution failed"),
            )

        logger.info(
            f"Agent execution completed successfully",
            extra={
                "agent_id": str(request.agent_id),
                "tenant_id": x_tenant_id,
                "execution_time_seconds": result["execution_time_seconds"],
                "tool_calls_count": len(tool_calls_response),
            },
        )

        return response

    except BudgetExceededError as e:
        # Budget exceeded - return 402 Payment Required
        logger.warning(
            f"Budget exceeded for tenant {x_tenant_id}",
            extra={
                "tenant_id": x_tenant_id,
                "agent_id": str(request.agent_id),
            },
        )

        # Extract budget details from exception if available
        budget_details = {
            "detail": str(e),
            "tenant_id": x_tenant_id,
            "current_spend": 0.0,
            "max_budget": 0.0,
            "grace_threshold": 110.0,
        }

        # Try to parse budget info from exception message
        # (BudgetService adds this info to the exception)
        if hasattr(e, "current_spend"):
            budget_details["current_spend"] = e.current_spend
        if hasattr(e, "max_budget"):
            budget_details["max_budget"] = e.max_budget
        if hasattr(e, "grace_threshold"):
            budget_details["grace_threshold"] = e.grace_threshold

        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=budget_details,
        )

    except HTTPException:
        # Re-raise HTTPExceptions (404, etc.)
        raise

    except ValueError as e:
        # ValueError from agent not found or tenant mismatch
        error_msg = str(e)
        if "not found" in error_msg.lower():
            logger.warning(
                f"Agent not found: {request.agent_id}",
                extra={"agent_id": str(request.agent_id), "tenant_id": x_tenant_id},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent not found: {request.agent_id}",
            )
        else:
            logger.error(
                f"Invalid request: {error_msg}",
                extra={"agent_id": str(request.agent_id), "tenant_id": x_tenant_id},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )

    except AgentExecutionError as e:
        # Agent execution error - return 500
        error_msg = str(e)
        logger.error(
            f"Agent execution error: {error_msg}",
            extra={
                "agent_id": str(request.agent_id),
                "tenant_id": x_tenant_id,
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg,
        )

    except Exception as e:
        # Unexpected error - return 500
        error_msg = f"Unexpected error during agent execution: {str(e)}"
        logger.error(
            error_msg,
            extra={
                "agent_id": str(request.agent_id),
                "tenant_id": x_tenant_id,
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during agent execution",
        )


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health check for agent execution service",
    description="Returns service health status and version info",
)
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for agent execution service.

    Returns:
        Dict with service status and version info
    """
    return {
        "status": "healthy",
        "service": "agent-execution",
        "version": "1.0.0",
        "features": [
            "langgraph-react-agent",
            "mcp-tool-support",
            "budget-enforcement",
            "multi-tenant-isolation",
        ],
    }
