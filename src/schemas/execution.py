"""
Execution detail schemas for API responses.

This module provides Pydantic v2 schemas for the execution details endpoint,
supporting retrieval of agent test execution records with tenant isolation
and sensitive data masking.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ExecutionDetailResponse(BaseModel):
    """
    Response schema for GET /api/executions/{execution_id}.

    Represents a single agent test execution record with full details including
    input payload, execution trace, token usage, timing, and errors. Sensitive
    data (API keys, passwords, tokens) is masked before returning.

    Attributes:
        id: Execution record UUID (globally unique)
        agent_id: UUID of the agent that was executed
        tenant_id: Tenant identifier for multi-tenant isolation
        input_data: Test payload (webhook data or trigger parameters)
        output_data: Execution trace with step-by-step details
        status: Execution status (success/failed)
        execution_time: Total execution duration in milliseconds
        created_at: Timestamp when execution was created
        updated_at: Timestamp when execution was last updated (nullable)
        error_message: Error details if execution failed (nullable)
        task_id: Celery task ID for correlation with webhook response (nullable)
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID = Field(..., description="Execution record ID (globally unique)")
    agent_id: UUID = Field(..., description="Agent ID that was executed")
    tenant_id: str = Field(..., description="Tenant identifier for isolation")
    input_data: dict = Field(..., description="Test payload or trigger parameters")
    output_data: dict = Field(
        ..., description="Execution trace with step-by-step execution details"
    )
    status: str = Field(..., description="Execution status: success or failed")
    execution_time: int = Field(
        ..., description="Total execution duration in milliseconds"
    )
    created_at: datetime = Field(..., description="Execution creation timestamp")
    updated_at: Optional[datetime] = Field(
        default=None, description="Last update timestamp (nullable)"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if execution failed (nullable)"
    )
    task_id: Optional[str] = Field(
        default=None, description="Celery task ID for correlation with webhook response (nullable)"
    )
