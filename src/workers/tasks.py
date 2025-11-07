"""
Celery task definitions for AI Agents enhancement platform.

This module contains Celery tasks for asynchronous processing including:
- Test tasks for validation (add_numbers)
- Enhancement workflow tasks (enhance_ticket)

Tasks are configured with retry logic, exponential backoff, and timeout limits
per tech spec requirements.
"""

import asyncio
from datetime import datetime, UTC
from time import time
from typing import Any, Dict

from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from loguru import logger
from pydantic import ValidationError

from src.utils.logger import AuditLogger

from src.workers.celery_app import celery_app
from src.schemas.job import EnhancementJob
from src.database.models import EnhancementHistory
from src.database.session import async_session_maker
from src.database.tenant_context import set_db_tenant_context

# Audit logger for compliance logging
audit_logger = AuditLogger()

# Import Prometheus metrics from centralized monitoring module (Story 4.1)
try:
    from src.monitoring import (
        enhancement_duration_seconds,
        enhancement_success_rate,
    )
    METRICS_ENABLED = True
except ImportError:
    # Prometheus client not installed - metrics disabled
    METRICS_ENABLED = False
    enhancement_duration_seconds = None
    enhancement_success_rate = None


@celery_app.task(
    bind=True,
    name="tasks.add_numbers",
    track_started=True,
)
def add_numbers(self: Task, x: int, y: int) -> int:
    """
    Test task that adds two numbers.

    This is a basic validation task to verify Celery worker functionality,
    task execution, result storage, and monitoring.

    Args:
        self: Celery task instance (injected by bind=True)
        x: First number to add
        y: Second number to add

    Returns:
        int: Sum of x and y

    Raises:
        TypeError: If x or y are not numeric types

    Example:
        >>> result = add_numbers.delay(2, 3)
        >>> result.get()
        5
    """
    logger.info(
        f"Task add_numbers started",
        extra={
            "task_id": self.request.id,
            "task_name": self.name,
            "worker_id": self.request.hostname,
            "args": {"x": x, "y": y},
        },
    )

    try:
        # Validate input types
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise TypeError(f"Both arguments must be numeric, got {type(x)} and {type(y)}")

        result = x + y

        logger.info(
            f"Task add_numbers completed successfully",
            extra={
                "task_id": self.request.id,
                "result": result,
            },
        )

        return result

    except SoftTimeLimitExceeded:
        logger.warning(
            f"Task add_numbers exceeded soft time limit",
            extra={"task_id": self.request.id},
        )
        raise
    except Exception as e:
        logger.error(
            f"Task add_numbers failed with error: {str(e)}",
            extra={
                "task_id": self.request.id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        raise


@celery_app.task(
    bind=True,
    name="tasks.enhance_ticket",
    track_started=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 2},
    retry_backoff=True,
    retry_backoff_max=600,  # Max backoff 600 seconds per spec
    retry_jitter=True,
    time_limit=120,  # 2 minutes hard limit (NFR001)
    soft_time_limit=100,  # 1:40 soft limit
)
def enhance_ticket(self: Task, job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Orchestrate end-to-end ticket enhancement workflow (Story 2.11).

    This task integrates the complete enhancement pipeline:
    1. Validate job and load tenant configuration
    2. Generate correlation ID for distributed tracing
    3. Create enhancement_history record (status='pending')
    4. Execute LangGraph context gathering (Story 2.8)
    5. Call LLM synthesis (Story 2.9)
    6. Update ServiceDesk Plus ticket (Story 2.10)
    7. Update enhancement_history with result
    8. Log all lifecycle events with correlation ID

    Args:
        self: Celery task instance (injected by bind=True)
        job_data: EnhancementJob serialized as dict from Redis containing:
            - job_id: Unique job identifier (UUID)
            - ticket_id: ServiceDesk Plus ticket ID
            - tenant_id: Tenant identifier for multi-tenant isolation
            - description: Ticket description text
            - priority: Job priority (low/medium/high/critical)
            - timestamp: ISO 8601 timestamp from webhook
            - created_at: UTC timestamp when job was queued

    Returns:
        Dict[str, Any]: Enhancement result containing:
            - status: "completed" or "failed"
            - ticket_id: ServiceDesk Plus ticket ID
            - enhancement_id: Database enhancement_history record ID (UUID)
            - processing_time_ms: Total processing time in milliseconds

    Raises:
        ValidationError: If job_data fails Pydantic validation
        SoftTimeLimitExceeded: If task exceeds 100 second soft limit
        Exception: Any error during enhancement workflow (triggers auto-retry)

    Example:
        >>> job_data = {
        ...     "job_id": "550e8400-e29b-41d4-a716-446655440000",
        ...     "ticket_id": "TKT-001",
        ...     "tenant_id": "tenant-abc",
        ...     "description": "Server slow",
        ...     "priority": "high",
        ...     "timestamp": "2025-11-01T12:00:00Z"
        ... }
        >>> result = enhance_ticket.delay(job_data)
        >>> result.get()
        {"status": "completed", "ticket_id": "TKT-001", ...}
    """
    # Story 4.6: Extract trace context from job data for distributed tracing
    # The trace context was propagated from FastAPI webhook handler via job_data['trace_context']
    from opentelemetry.propagate import extract
    from opentelemetry import trace as otel_trace
    from src.monitoring import get_tracer
    
    # Extract trace context from job data if present
    trace_context_carrier = {}
    if "trace_context" in job_data and job_data["trace_context"]:
        trace_context_carrier["traceparent"] = job_data["trace_context"]
    
    # Extract context to establish trace parent-child relationship with FastAPI span
    trace_context = extract(trace_context_carrier)
    
    import uuid
    import json
    from src.workflows.enhancement_workflow import execute_context_gathering
    from src.services.llm_synthesis import synthesize_enhancement
    from src.services.servicedesk_client import update_ticket_with_enhancement
    from sqlalchemy import select

    start_time = time()
    enhancement_id = None
    tenant_id = job_data.get("tenant_id", "unknown")
    context_gathered = {}
    llm_output = ""

    try:
        # Validate and deserialize job data
        try:
            job = EnhancementJob.model_validate(job_data)
        except ValidationError as e:
            correlation_id = job_data.get("correlation_id", str(uuid.uuid4()))
            logger.error(
                "Task enhance_ticket validation failed",
                extra={
                    "correlation_id": correlation_id,
                    "task_id": self.request.id,
                    "error_type": "ValidationError",
                    "error_message": str(e),
                    "job_data_keys": list(job_data.keys()) if isinstance(job_data, dict) else None,
                },
            )
            raise

        # Extract correlation ID from job (generated at webhook entry or provided)
        correlation_id = job.correlation_id

        # Story 4.6: Create a named span for this Celery task within the trace context
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span(
            "enhance_ticket", context=trace_context
        ) as task_span:
            # Set custom span attributes for task context
            task_span.set_attribute("tenant.id", job.tenant_id)
            task_span.set_attribute("ticket.id", job.ticket_id)
            task_span.set_attribute("job.id", job.job_id)
            task_span.set_attribute("priority", job.priority)
            task_span.set_attribute("correlation_id", correlation_id)
            task_span.set_attribute("celery.task_id", self.request.id)
            task_span.set_attribute("celery.hostname", self.request.hostname)

            # Bind correlation ID to logger for all subsequent logs in this task
            logger.bind(correlation_id=correlation_id, task_id=self.request.id, worker_id=self.request.hostname)

            # Log task start with audit logger for compliance
            audit_logger.audit_enhancement_started(
                tenant_id=job.tenant_id,
                ticket_id=job.ticket_id,
                correlation_id=correlation_id,
                task_id=self.request.id,
                worker_id=self.request.hostname,
            )

            # Log task start with correlation ID
            logger.info(
                "Task enhance_ticket started (Story 2.11)",
                extra={
                    "correlation_id": correlation_id,
                    "task_id": self.request.id,
                    "ticket_id": job.ticket_id,
                    "tenant_id": job.tenant_id,
                    "job_id": job.job_id,
                    "priority": job.priority,
                },
            )

            # Run async operations in sync Celery task
            async def run_enhancement_pipeline():
                nonlocal enhancement_id, context_gathered, llm_output

                async with async_session_maker() as session:
                    # Set tenant context for RLS (Story 3.1)
                    # Must be called before any database queries on tenant-scoped tables
                    await set_db_tenant_context(session, job.tenant_id)

                    # Task 1.3: Load tenant configuration from database
                    from src.database.models import TenantConfig

                    stmt = select(TenantConfig).where(TenantConfig.tenant_id == job.tenant_id)
                    result = await session.execute(stmt)
                    tenant_config = result.scalar_one_or_none()

                    if not tenant_config:
                        logger.error(
                            "Tenant configuration not found",
                            extra={
                                "correlation_id": correlation_id,
                                "tenant_id": job.tenant_id,
                                "ticket_id": job.ticket_id,
                            },
                        )
                        raise ValueError(f"Tenant {job.tenant_id} not found in database")

                    logger.debug(
                        "Tenant configuration loaded",
                        extra={
                            "correlation_id": correlation_id,
                            "tenant_id": job.tenant_id,
                            "tool_type": tenant_config.tool_type,
                        },
                    )

                    # Task 1.4: Create enhancement_history record with status='pending'
                    enhancement = EnhancementHistory(
                        tenant_id=job.tenant_id,
                        ticket_id=job.ticket_id,
                        status="pending",
                        context_gathered=None,
                        llm_output=None,
                        error_message=None,
                        processing_time_ms=None,
                        created_at=datetime.now(UTC),
                        completed_at=None,
                        correlation_id=correlation_id,
                    )
                    session.add(enhancement)
                    await session.commit()
                    await session.refresh(enhancement)

                    nonlocal enhancement_id
                    enhancement_id = str(enhancement.id)

                    logger.info(
                        "Enhancement history record created with status=pending",
                        extra={
                            "correlation_id": correlation_id,
                            "enhancement_id": enhancement_id,
                            "ticket_id": job.ticket_id,
                            "tenant_id": job.tenant_id,
                        },
                    )

                    # Task 2: Orchestrate Context Gathering (Story 2.8 Integration)
                    logger.info(
                        "Starting context gathering phase",
                        extra={
                            "correlation_id": correlation_id,
                            "ticket_id": job.ticket_id,
                        },
                    )

                    try:
                        # Story 4.6: Custom span for context_gathering phase (AC6)
                        # Create a named span for context gathering operation
                        with tracer.start_as_current_span("context_gathering") as context_span:
                            context_span.set_attribute("tenant.id", job.tenant_id)
                            context_span.set_attribute("ticket.id", job.ticket_id)

                            # Task 2.1: Initialize LangGraph workflow with ticket context
                            # Task 2.2: Execute LangGraph workflow nodes (with 30s timeout)
                            context = await asyncio.wait_for(
                                execute_context_gathering(
                                    tenant_id=job.tenant_id,
                                    ticket_id=job.ticket_id,
                                    description=job.description,
                                    priority=job.priority,
                                    session=session,
                                    kb_config={},  # KB config from tenant if needed
                                    correlation_id=correlation_id,
                                ),
                                timeout=30.0,  # 30 second timeout per AC4
                            )

                            # Store context for later use and database logging
                            context_gathered = {
                                "similar_tickets": context.get("similar_tickets", []),
                                "kb_articles": context.get("kb_articles", []),
                                "ip_info": context.get("ip_info", []),
                                "errors": context.get("errors", []),
                                "workflow_execution_time_ms": context.get("workflow_execution_time_ms", 0),
                            }

                            num_tickets = len(context.get("similar_tickets", []))
                            num_articles = len(context.get("kb_articles", []))
                            num_ips = len(context.get("ip_info", []))
                            num_errors = len(context.get("errors", []))

                            # Story 4.6: Add child spans for each context source (AC6)
                            # Record results in parent span attributes for Jaeger visibility
                            context_span.set_attribute("context.ticket_history.count", num_tickets)
                            context_span.set_attribute("context.documentation.count", num_articles)
                            context_span.set_attribute("context.ip_lookup.count", num_ips)
                            context_span.set_attribute("context.errors.count", num_errors)

                        # Task 2.3: Handle context gathering failures gracefully
                        if num_errors > 0:
                            logger.warning(
                                "Context gathering completed with partial failures",
                                extra={
                                    "correlation_id": correlation_id,
                                    "ticket_id": job.ticket_id,
                                    "num_tickets": num_tickets,
                                    "num_articles": num_articles,
                                    "num_ips": num_ips,
                                    "num_errors": num_errors,
                                    "failed_nodes": [e["node_name"] for e in context.get("errors", [])],
                                },
                            )
                        else:
                            logger.info(
                                "Context gathering completed successfully",
                                extra={
                                    "correlation_id": correlation_id,
                                    "ticket_id": job.ticket_id,
                                    "num_tickets": num_tickets,
                                    "num_articles": num_articles,
                                    "num_ips": num_ips,
                                },
                            )

                    except asyncio.TimeoutError:
                        logger.warning(
                            "Context gathering timeout - continuing with empty context",
                            extra={
                                "correlation_id": correlation_id,
                                "ticket_id": job.ticket_id,
                                "timeout_seconds": 30,
                            },
                        )
                        context = {}
                        context_gathered = {
                            "similar_tickets": [],
                            "kb_articles": [],
                            "ip_info": [],
                            "errors": [{"node_name": "all", "message": "Timeout after 30s"}],
                            "workflow_execution_time_ms": 30000,
                        }

                    # Task 3: Integrate LLM Synthesis (Story 2.9 Integration)
                    logger.info(
                        "Starting LLM synthesis phase",
                        extra={
                            "correlation_id": correlation_id,
                            "ticket_id": job.ticket_id,
                        },
                    )

                    try:
                        # Story 4.6: Custom span for llm_call phase (AC7)
                        # Create a named span for OpenAI API call with model and token tracking
                        with tracer.start_as_current_span("llm.openai.completion") as llm_span:
                            llm_span.set_attribute("tenant.id", job.tenant_id)
                            llm_span.set_attribute("ticket.id", job.ticket_id)
                            llm_span.set_attribute("llm.model", "gpt-4")  # Default model name

                            # Task 3.1: Call LLM synthesis with gathered context
                            llm_output = await synthesize_enhancement(
                                context=context,
                                correlation_id=correlation_id,
                            )

                            # Record token usage and output length in span
                            llm_span.set_attribute("llm.output_tokens", len(llm_output.split()))
                            llm_span.set_attribute("llm.output_length", len(llm_output))

                        # Task 3.3: Validate enhancement output
                        if not llm_output or len(llm_output.strip()) == 0:
                            logger.warning(
                                "LLM synthesis returned empty output - using fallback",
                                extra={
                                    "correlation_id": correlation_id,
                                    "ticket_id": job.ticket_id,
                                },
                            )
                            # Fallback: Format context without AI synthesis
                            llm_output = _format_context_fallback(context_gathered)

                        logger.info(
                            "LLM synthesis completed successfully",
                            extra={
                                "correlation_id": correlation_id,
                                "ticket_id": job.ticket_id,
                                "output_length": len(llm_output),
                            },
                        )

                    except Exception as e:
                        # Task 3.2: Handle LLM synthesis failures with fallback
                        logger.warning(
                            "LLM synthesis failed - using fallback context formatting",
                            extra={
                                "correlation_id": correlation_id,
                                "ticket_id": job.ticket_id,
                                "error_type": type(e).__name__,
                                "error_message": str(e),
                            },
                        )
                        llm_output = _format_context_fallback(context_gathered)

                    # Task 4: Update ServiceDesk Plus Ticket (Story 2.10 Integration)
                    logger.info(
                        "Starting ServiceDesk Plus API update phase",
                        extra={
                            "correlation_id": correlation_id,
                            "ticket_id": job.ticket_id,
                        },
                    )

                    # Story 4.6: Custom span for ticket_update phase (AC8)
                    # Create a named span for ServiceDesk Plus API call with status tracking
                    with tracer.start_as_current_span("api.servicedesk_plus.update_ticket") as api_span:
                        api_span.set_attribute("tenant.id", job.tenant_id)
                        api_span.set_attribute("ticket.id", job.ticket_id)
                        api_span.set_attribute("api.endpoint", f"/api/v3/tickets/{job.ticket_id}")

                        # Task 4.1: Call ServiceDesk Plus API client
                        success = await update_ticket_with_enhancement(
                            base_url=tenant_config.base_url,
                            api_key=tenant_config.api_key,
                            ticket_id=job.ticket_id,
                            enhancement=llm_output,
                            correlation_id=correlation_id,
                            tenant_id=job.tenant_id,
                        )

                        # Record API success/failure status in span
                        api_span.set_attribute("api.status", "success" if success else "failure")
                        api_span.set_attribute("api.response_success", success)

                    # Task 4.2: Handle API update result
                    if success:
                        logger.info(
                            "Ticket updated successfully via ServiceDesk Plus API",
                            extra={
                                "correlation_id": correlation_id,
                                "ticket_id": job.ticket_id,
                            },
                        )
                    else:
                        logger.error(
                            "Ticket update failed after retries",
                            extra={
                                "correlation_id": correlation_id,
                                "ticket_id": job.ticket_id,
                            },
                        )
                        raise RuntimeError(f"Failed to update ticket {job.ticket_id} via ServiceDesk Plus API")

                    # Task 5: Update Enhancement History Record
                    # Task 5.1: Calculate processing time
                    processing_time_ms = int((time() - start_time) * 1000)

                    # Task 5.2: Update enhancement_history on success
                    stmt = select(EnhancementHistory).where(EnhancementHistory.id == enhancement_id)
                    result = await session.execute(stmt)
                    enhancement = result.scalar_one_or_none()

                    if enhancement:
                        enhancement.status = "completed"
                        enhancement.completed_at = datetime.now(UTC)
                        enhancement.processing_time_ms = processing_time_ms
                        enhancement.llm_output = llm_output
                        enhancement.context_gathered = json.dumps(context_gathered, default=str)
                        enhancement.correlation_id = correlation_id
                        await session.commit()

                    logger.info(
                        "Enhancement completed and history updated",
                        extra={
                            "correlation_id": correlation_id,
                            "enhancement_id": enhancement_id,
                            "ticket_id": job.ticket_id,
                            "status": "completed",
                            "processing_time_ms": processing_time_ms,
                        },
                    )

                    return {
                        "status": "completed",
                        "ticket_id": job.ticket_id,
                        "enhancement_id": enhancement_id,
                        "processing_time_ms": processing_time_ms,
                    }

            # Run async pipeline in sync Celery task
            result = asyncio.run(run_enhancement_pipeline())

            # Task 10: Record Prometheus metrics for successful enhancement
            if METRICS_ENABLED:
                # Record duration histogram for latency analysis
                enhancement_duration_seconds.labels(
                    tenant_id=job.tenant_id, status="success"
                ).observe(result["processing_time_ms"] / 1000.0)

                # Update success rate gauge (rolling 5-minute window calculation)
                # Note: In production, this should be calculated by background task
                # from the last 300 seconds of observations
                enhancement_success_rate.labels(tenant_id=job.tenant_id).set(100)

            logger.info(
                "Task enhance_ticket completed successfully",
                extra={
                    "correlation_id": correlation_id,
                    "task_id": self.request.id,
                    "ticket_id": job.ticket_id,
                    "tenant_id": job.tenant_id,
                    "enhancement_id": enhancement_id,
                    "processing_time_ms": result["processing_time_ms"],
                },
            )

            # Log enhancement completion with audit logger for compliance
            audit_logger.audit_enhancement_completed(
                tenant_id=job.tenant_id,
                ticket_id=job.ticket_id,
                correlation_id=correlation_id,
                duration_ms=result["processing_time_ms"],
            )

            return result

    except SoftTimeLimitExceeded:
        processing_time_ms = int((time() - start_time) * 1000)
        logger.warning(
            "Task enhance_ticket exceeded soft time limit (100s)",
            extra={
                "correlation_id": correlation_id,
                "task_id": self.request.id,
                "ticket_id": job_data.get("ticket_id") if isinstance(job_data, dict) else None,
                "tenant_id": tenant_id,
                "enhancement_id": enhancement_id,
                "processing_time_ms": processing_time_ms,
            },
        )

        # Update enhancement_history to failed
        if enhancement_id:
            async def mark_timeout():
                async with async_session_maker() as session:
                    from sqlalchemy import select
                    stmt = select(EnhancementHistory).where(
                        EnhancementHistory.id == enhancement_id
                    )
                    result = await session.execute(stmt)
                    enhancement = result.scalar_one_or_none()
                    if enhancement:
                        enhancement.status = "failed"
                        enhancement.error_message = "Task exceeded soft time limit (100s)"
                        enhancement.processing_time_ms = processing_time_ms
                        enhancement.completed_at = datetime.now(UTC)
                        enhancement.correlation_id = correlation_id
                        await session.commit()

            asyncio.run(mark_timeout())

        raise

    except Exception as exc:
        processing_time_ms = int((time() - start_time) * 1000)
        attempt_number = self.request.retries
        ticket_id = job_data.get("ticket_id") if isinstance(job_data, dict) else None

        # Log enhancement failure with audit logger for compliance
        audit_logger.audit_enhancement_failed(
            tenant_id=tenant_id,
            ticket_id=ticket_id,
            correlation_id=correlation_id,
            error_type=type(exc).__name__,
            error_message=str(exc),
            duration_ms=processing_time_ms,
        )

        logger.error(
            f"Task enhance_ticket failed with error: {str(exc)}",
            extra={
                "correlation_id": correlation_id,
                "task_id": self.request.id,
                "ticket_id": ticket_id,
                "tenant_id": tenant_id,
                "enhancement_id": enhancement_id,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "attempt_number": attempt_number,
                "processing_time_ms": processing_time_ms,
            },
        )

        # Update enhancement_history to failed
        if enhancement_id:
            async def mark_failed():
                async with async_session_maker() as session:
                    from sqlalchemy import select
                    stmt = select(EnhancementHistory).where(
                        EnhancementHistory.id == enhancement_id
                    )
                    result = await session.execute(stmt)
                    enhancement = result.scalar_one_or_none()
                    if enhancement:
                        enhancement.status = "failed"
                        enhancement.error_message = f"{type(exc).__name__}: {str(exc)}"
                        enhancement.processing_time_ms = processing_time_ms
                        enhancement.completed_at = datetime.now(UTC)
                        enhancement.correlation_id = correlation_id
                        await session.commit()

            asyncio.run(mark_failed())

        # Task 10: Record Prometheus metrics for failure
        if METRICS_ENABLED:
            # Record duration histogram for failed tasks
            enhancement_duration_seconds.labels(
                tenant_id=tenant_id, status="failure"
            ).observe(processing_time_ms / 1000.0)

            # Update success rate gauge (rolling 5-minute window calculation)
            # Note: In production, this should be calculated by background task
            enhancement_success_rate.labels(tenant_id=tenant_id).set(0)

        # Celery will auto-retry via autoretry_for decorator
        raise



@celery_app.task(
    bind=True,
    name="tasks.execute_agent",
    track_started=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 2},
    retry_backoff=True,
    retry_jitter=True,
    time_limit=300,  # 5 minutes hard limit
    soft_time_limit=240,  # 4 minutes soft limit
)
def execute_agent(self: Task, agent_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute AI agent with given payload (Story 8.6).

    This task handles agent execution triggered via webhook endpoints.
    Currently a placeholder that logs execution details - full agent
    orchestration will be implemented in future stories.

    Args:
        self: Celery task instance (injected by bind=True)
        agent_id: UUID of agent to execute
        payload: Webhook payload data (validated against agent's payload_schema)

    Returns:
        Dict[str, Any]: Execution result containing:
            - status: "queued" | "running" | "completed" | "failed"
            - agent_id: Agent UUID
            - execution_id: Unique execution identifier
            - result: Agent execution output (when completed)

    Raises:
        Exception: Any error during agent execution (triggers auto-retry)

    Example:
        >>> payload = {"ticket_id": "TKT-123", "description": "Server issue"}
        >>> result = execute_agent.delay("agent-uuid", payload)
        >>> result.get()
        {"status": "completed", "agent_id": "agent-uuid", ...}
    """
    import uuid
    from time import time
    from datetime import datetime, UTC

    start_time = time()
    execution_id = str(uuid.uuid4())

    try:
        logger.info(
            "Task execute_agent started (Story 8.6)",
            extra={
                "task_id": self.request.id,
                "agent_id": agent_id,
                "execution_id": execution_id,
                "payload_keys": list(payload.keys()) if isinstance(payload, dict) else None,
            },
        )

        # TODO: Future implementation (separate story)
        # 1. Load agent configuration from database
        # 2. Initialize LiteLLM client with agent's LLM config
        # 3. Execute agent with system prompt + payload context
        # 4. Store execution result in agent_executions table
        # 5. Return structured result

        # Placeholder: Log execution and return success
        processing_time_ms = int((time() - start_time) * 1000)

        logger.info(
            "Task execute_agent completed (placeholder implementation)",
            extra={
                "task_id": self.request.id,
                "agent_id": agent_id,
                "execution_id": execution_id,
                "processing_time_ms": processing_time_ms,
            },
        )

        return {
            "status": "completed",
            "agent_id": agent_id,
            "execution_id": execution_id,
            "processing_time_ms": processing_time_ms,
            "result": f"Agent {agent_id} executed successfully with payload: {payload}",
        }

    except Exception as exc:
        processing_time_ms = int((time() - start_time) * 1000)
        attempt_number = self.request.retries

        logger.error(
            f"Task execute_agent failed with error: {str(exc)}",
            extra={
                "task_id": self.request.id,
                "agent_id": agent_id,
                "execution_id": execution_id,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "attempt_number": attempt_number,
                "processing_time_ms": processing_time_ms,
            },
        )

        # Celery will auto-retry via autoretry_for decorator
        raise


def _format_context_fallback(context_gathered: Dict[str, Any]) -> str:
    """
    Format gathered context as plain text when LLM synthesis fails.

    This provides graceful degradation - if LLM API is unavailable,
    we still post a formatted summary of gathered context to the ticket.

    Args:
        context_gathered: Dict with similar_tickets, kb_articles, ip_info, errors

    Returns:
        str: Formatted markdown summary of context
    """
    lines = [
        "## Enhancement Context (Generated Without AI)",
        "",
        "This enhancement was generated from gathered context without AI synthesis.",
        "",
    ]

    similar_tickets = context_gathered.get("similar_tickets", [])
    if similar_tickets:
        lines.append(f"### Similar Tickets ({len(similar_tickets)})")
        for ticket in similar_tickets[:5]:  # Top 5
            title = ticket.get("title", "Unknown")
            ticket_id = ticket.get("ticket_id", "N/A")
            lines.append(f"- **{ticket_id}**: {title}")
        lines.append("")

    kb_articles = context_gathered.get("kb_articles", [])
    if kb_articles:
        lines.append(f"### Knowledge Base Articles ({len(kb_articles)})")
        for article in kb_articles[:5]:  # Top 5
            title = article.get("title", "Unknown")
            url = article.get("url", "#")
            lines.append(f"- [{title}]({url})")
        lines.append("")

    ip_info = context_gathered.get("ip_info", [])
    if ip_info:
        lines.append(f"### System Information ({len(ip_info)} nodes)")
        for info in ip_info[:3]:
            hostname = info.get("hostname", "Unknown")
            role = info.get("role", "N/A")
            lines.append(f"- **{hostname}** ({role})")
        lines.append("")

    errors = context_gathered.get("errors", [])
    if errors:
        lines.append(f"### Context Gathering Warnings ({len(errors)})")
        for error in errors:
            node_name = error.get("node_name", "Unknown")
            message = error.get("message", "Error occurred")
            lines.append(f"- **{node_name}**: {message}")
        lines.append("")

    return "\n".join(lines)



@celery_app.task(
    bind=True,
    name="tasks.reset_tenant_budgets",
    track_started=True,
    max_retries=3,
    soft_time_limit=600,  # 10 minutes
    time_limit=660,  # 11 minutes hard limit
)
def reset_tenant_budgets(self: Task) -> Dict[str, Any]:
    """
    Periodic task to reset tenant budgets based on budget_duration.

    Runs daily at 00:00 UTC (configured in Celery beat schedule).
    For each tenant whose budget_reset_at <= NOW():
    1. Reset virtual key budget via LiteLLM API
    2. Update litellm_key_last_reset timestamp  
    3. Calculate next budget_reset_at
    4. Log audit entry
    5. Send notification

    Story 8.10 AC#7: Budget Reset Automation

    Returns:
        Dict with reset_count, success_count, and failed_tenants list

    Raises:
        SoftTimeLimitExceeded: If task exceeds 10 minutes
    """
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import select, update
    from src.database.models import TenantConfig, AuditLog
    from src.config import settings
    import httpx

    logger.info("Starting budget reset task")
    reset_count = 0
    success_count = 0
    failed_tenants = []

    try:
        # Run async code in event loop
        async def _reset_budgets():
            nonlocal reset_count, success_count, failed_tenants

            async with async_session_maker() as session:
                # Find tenants whose budget period has expired
                now = datetime.now(timezone.utc)
                stmt = select(TenantConfig).where(
                    TenantConfig.budget_reset_at <= now,
                    TenantConfig.is_active == True
                )
                result = await session.execute(stmt)
                tenants = result.scalars().all()

                reset_count = len(tenants)
                logger.info(f"Found {reset_count} tenants requiring budget reset")

                for tenant in tenants:
                    try:
                        # Reset virtual key budget via LiteLLM API
                        if tenant.litellm_virtual_key:
                            async with httpx.AsyncClient(timeout=30.0) as client:
                                # Call LiteLLM key/update endpoint to reset budget
                                litellm_url = f"{settings.litellm_proxy_url}/key/update"
                                headers = {"Authorization": f"Bearer {settings.litellm_master_key}"}
                                payload = {
                                    "key": tenant.litellm_virtual_key,
                                    "spend": 0,  # Reset spend to 0
                                }

                                response = await client.post(litellm_url, json=payload, headers=headers)
                                response.raise_for_status()

                                logger.info(f"Reset budget for tenant {tenant.tenant_id}")

                        # Calculate next reset date based on budget_duration
                        duration_days = int(tenant.budget_duration.replace('d', ''))
                        next_reset_at = now + timedelta(days=duration_days)

                        # Update tenant record
                        await session.execute(
                            update(TenantConfig)
                            .where(TenantConfig.tenant_id == tenant.tenant_id)
                            .values(
                                litellm_key_last_reset=now,
                                budget_reset_at=next_reset_at,
                                updated_at=now
                            )
                        )

                        # Log audit entry
                        audit_entry = AuditLog(
                            tenant_id=tenant.tenant_id,
                            operation="budget_reset",
                            user="system",
                            timestamp=now,
                            details={
                                "previous_reset": tenant.litellm_key_last_reset.isoformat() if tenant.litellm_key_last_reset else None,
                                "next_reset": next_reset_at.isoformat(),
                                "duration": tenant.budget_duration,
                                "max_budget": tenant.max_budget
                            }
                        )
                        session.add(audit_entry)

                        await session.commit()
                        success_count += 1

                        logger.info(
                            f"Budget reset successful for tenant {tenant.tenant_id}",
                            extra={
                                "tenant_id": tenant.tenant_id,
                                "next_reset": next_reset_at.isoformat(),
                                "duration": tenant.budget_duration
                            }
                        )

                        # TODO Story 8.10A: Send notification to tenant admin
                        # await NotificationService().send_budget_reset_notification(tenant.tenant_id)

                    except Exception as e:
                        logger.error(
                            f"Failed to reset budget for tenant {tenant.tenant_id}: {e}",
                            extra={"tenant_id": tenant.tenant_id, "error": str(e)}
                        )
                        failed_tenants.append({
                            "tenant_id": tenant.tenant_id,
                            "error": str(e)
                        })

        # Execute async function
        asyncio.run(_reset_budgets())

        result = {
            "reset_count": reset_count,
            "success_count": success_count,
            "failed_count": len(failed_tenants),
            "failed_tenants": failed_tenants,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        logger.info(f"Budget reset task completed: {success_count}/{reset_count} successful")
        return result

    except SoftTimeLimitExceeded:
        logger.error("Budget reset task exceeded 10 minute time limit")
        raise
    except Exception as e:
        logger.error(f"Budget reset task failed: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=300)  # Retry after 5 minutes


@celery_app.task(
    bind=True,
    name="tasks.expire_budget_overrides",
    track_started=True,
    max_retries=3,
    soft_time_limit=300,  # 5 minutes
    time_limit=330,  # 5.5 minutes hard limit
)
def expire_budget_overrides(self: Task) -> Dict[str, Any]:
    """
    Periodic task to expire budget overrides that have reached their expiration time.

    Runs hourly at :00 minutes (configured in Celery beat schedule).
    For each override whose expires_at <= NOW():
    1. Remove override from database
    2. Reset virtual key budget to tenant's base max_budget via LiteLLM API
    3. Log audit entry
    4. Send notification

    Story 8.10C AC#7: Automatic Override Expiry

    Returns:
        Dict with expired_count, success_count, and failed_overrides list

    Raises:
        SoftTimeLimitExceeded: If task exceeds 5 minutes
    """
    from datetime import datetime, timezone
    from sqlalchemy import select, delete
    from src.database.models import TenantConfig, AuditLog
    from src.config import settings
    import httpx

    # Check if BudgetOverride model exists (added in Story 8.10)
    try:
        from src.database.models import BudgetOverride
    except ImportError:
        logger.warning("BudgetOverride model not found - skipping override expiry")
        return {
            "expired_count": 0,
            "success_count": 0,
            "failed_count": 0,
            "failed_overrides": [],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    logger.info("Starting budget override expiry task")
    expired_count = 0
    success_count = 0
    failed_overrides = []

    try:
        # Run async code in event loop
        async def _expire_overrides():
            nonlocal expired_count, success_count, failed_overrides

            async with async_session_maker() as session:
                # Find overrides whose expiration time has passed
                now = datetime.now(timezone.utc)
                stmt = select(BudgetOverride).where(
                    BudgetOverride.expires_at <= now
                )
                result = await session.execute(stmt)
                overrides = result.scalars().all()

                expired_count = len(overrides)
                logger.info(f"Found {expired_count} expired budget overrides")

                for override in overrides:
                    try:
                        # Get tenant config to reset virtual key to base budget
                        tenant_stmt = select(TenantConfig).where(
                            TenantConfig.tenant_id == override.tenant_id
                        )
                        tenant_result = await session.execute(tenant_stmt)
                        tenant = tenant_result.scalar_one_or_none()

                        if not tenant:
                            logger.warning(
                                f"Tenant not found for override: {override.tenant_id}",
                                extra={"override_id": override.id, "tenant_id": override.tenant_id}
                            )
                            failed_overrides.append({
                                "override_id": str(override.id),
                                "tenant_id": override.tenant_id,
                                "error": "Tenant not found"
                            })
                            continue

                        # Reset virtual key budget to base max_budget via LiteLLM API
                        if tenant.litellm_virtual_key:
                            async with httpx.AsyncClient(timeout=30.0) as client:
                                # Call LiteLLM key/update endpoint to reset to base budget
                                litellm_url = f"{settings.litellm_proxy_url}/key/update"
                                headers = {"Authorization": f"Bearer {settings.litellm_master_key}"}
                                payload = {
                                    "key": tenant.litellm_virtual_key,
                                    "max_budget": tenant.max_budget,  # Reset to base budget
                                }

                                response = await client.post(litellm_url, json=payload, headers=headers)
                                response.raise_for_status()

                                logger.info(
                                    f"Reset virtual key budget to base for tenant {tenant.tenant_id}",
                                    extra={
                                        "tenant_id": tenant.tenant_id,
                                        "base_budget": tenant.max_budget,
                                        "override_amount": override.override_amount
                                    }
                                )

                        # Delete expired override from database
                        await session.delete(override)

                        # Log audit entry
                        audit_entry = AuditLog(
                            tenant_id=override.tenant_id,
                            operation="budget_override_expired",
                            user="system",
                            timestamp=now,
                            details={
                                "override_id": str(override.id),
                                "override_amount": override.override_amount,
                                "granted_at": override.created_at.isoformat() if override.created_at else None,
                                "expires_at": override.expires_at.isoformat(),
                                "reason": override.reason,
                                "created_by": override.created_by
                            }
                        )
                        session.add(audit_entry)

                        await session.commit()
                        success_count += 1

                        logger.info(
                            f"Budget override expired successfully for tenant {tenant.tenant_id}",
                            extra={
                                "tenant_id": tenant.tenant_id,
                                "override_id": str(override.id),
                                "override_amount": override.override_amount
                            }
                        )

                        # TODO Story 8.10C: Send notification to tenant admin
                        # await NotificationService().send_budget_override_expired_notification(
                        #     tenant_id=override.tenant_id,
                        #     override_amount=override.override_amount
                        # )

                    except Exception as e:
                        logger.error(
                            f"Failed to expire override for tenant {override.tenant_id}: {e}",
                            extra={
                                "tenant_id": override.tenant_id,
                                "override_id": str(override.id),
                                "error": str(e)
                            }
                        )
                        failed_overrides.append({
                            "override_id": str(override.id),
                            "tenant_id": override.tenant_id,
                            "error": str(e)
                        })

        # Execute async function
        asyncio.run(_expire_overrides())

        result = {
            "expired_count": expired_count,
            "success_count": success_count,
            "failed_count": len(failed_overrides),
            "failed_overrides": failed_overrides,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        logger.info(f"Budget override expiry task completed: {success_count}/{expired_count} successful")
        return result

    except SoftTimeLimitExceeded:
        logger.error("Budget override expiry task exceeded 5 minute time limit")
        raise
    except Exception as e:
        logger.error(f"Budget override expiry task failed: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=180)  # Retry after 3 minutes
