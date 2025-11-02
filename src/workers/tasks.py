"""
Celery task definitions for AI Agents enhancement platform.

This module contains Celery tasks for asynchronous processing including:
- Test tasks for validation (add_numbers)
- Enhancement workflow tasks (enhance_ticket)

Tasks are configured with retry logic, exponential backoff, and timeout limits
per tech spec requirements.
"""

import asyncio
from datetime import datetime
from time import time
from typing import Any, Dict

from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from loguru import logger
from pydantic import ValidationError

from src.workers.celery_app import celery_app
from src.schemas.job import EnhancementJob
from src.database.models import EnhancementHistory
from src.database.session import async_session_maker

# Prometheus metrics stubs (will be fully implemented in Story 4.1)
# For now, we just define placeholders to satisfy Story 2.4 requirements
try:
    from prometheus_client import Counter, Histogram

    # Counter for total enhancement tasks
    enhancement_tasks_total = Counter(
        'enhancement_tasks_total',
        'Total number of enhancement tasks processed',
        ['status', 'tenant_id']
    )

    # Histogram for task duration
    enhancement_task_duration_seconds = Histogram(
        'enhancement_task_duration_seconds',
        'Duration of enhancement task processing in seconds',
        ['status', 'tenant_id']
    )

    METRICS_ENABLED = True
except ImportError:
    # Prometheus client not installed - metrics disabled
    METRICS_ENABLED = False
    enhancement_tasks_total = None
    enhancement_task_duration_seconds = None


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
    Process enhancement job from Redis queue.

    This task orchestrates ticket enhancement workflow by:
    1. Validating and deserializing job data
    2. Creating enhancement_history record with status='pending'
    3. Processing enhancement (placeholder for Stories 2.5-2.9)
    4. Updating enhancement_history with result
    5. Logging all lifecycle events

    Future stories (2.5-2.9) will add context gathering, LLM synthesis,
    and ticket update integration.

    Job Flow:
        Webhook → Redis LPUSH → Celery BRPOP → enhance_ticket task
        Task receives deserialized job_data dict (Celery handles BRPOP)

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
            - error: Error message (if failed)

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
    start_time = time()
    enhancement_id = None
    # Extract tenant_id early for metrics (handles ValidationError case)
    tenant_id = job_data.get("tenant_id", "unknown")

    try:
        # Task 2: Validate and deserialize job data
        try:
            job = EnhancementJob.model_validate(job_data)
        except ValidationError as e:
            logger.error(
                "Task enhance_ticket validation failed",
                extra={
                    "task_id": self.request.id,
                    "task_name": self.name,
                    "worker_id": self.request.hostname,
                    "error_type": "ValidationError",
                    "error_message": str(e),
                    "job_data_keys": list(job_data.keys()) if isinstance(job_data, dict) else None,
                },
            )
            raise

        # Task 4: Log task start with structured logging
        logger.info(
            "Task enhance_ticket started",
            extra={
                "task_id": self.request.id,
                "task_name": self.name,
                "worker_id": self.request.hostname,
                "ticket_id": job.ticket_id,
                "tenant_id": job.tenant_id,
                "job_id": job.job_id,
                "priority": job.priority,
            },
        )

        # Task 5: Create enhancement_history record with status='pending'
        async def create_and_process_enhancement():
            async with async_session_maker() as session:
                # Create pending record
                enhancement = EnhancementHistory(
                    tenant_id=job.tenant_id,
                    ticket_id=job.ticket_id,
                    status="pending",
                    context_gathered=None,
                    llm_output=None,
                    error_message=None,
                    processing_time_ms=None,
                    created_at=datetime.utcnow(),
                    completed_at=None,
                )
                session.add(enhancement)
                await session.commit()
                await session.refresh(enhancement)

                # Convert UUID to string for JSON serialization compatibility
                nonlocal enhancement_id
                enhancement_id = str(enhancement.id)

                logger.debug(
                    "Enhancement history record created",
                    extra={
                        "task_id": self.request.id,
                        "ticket_id": job.ticket_id,
                        "tenant_id": job.tenant_id,
                        "enhancement_id": enhancement_id,
                        "status": "pending",
                    },
                )

                # Task 6: Placeholder enhancement logic
                # Real implementation in Stories 2.5-2.9 will add:
                # - Ticket history search (Story 2.5)
                # - Documentation search (Story 2.6)
                # - IP cross-reference (Story 2.7)
                # - LangGraph workflow (Story 2.8)
                # - OpenAI GPT-4 synthesis (Story 2.9)
                # - ServiceDesk API update (Story 2.10)
                logger.info(
                    f"Enhancement processing initiated for ticket {job.ticket_id} (placeholder until Stories 2.5-2.9)",
                    extra={
                        "task_id": self.request.id,
                        "ticket_id": job.ticket_id,
                        "tenant_id": job.tenant_id,
                        "enhancement_id": enhancement_id,
                    },
                )

                # Task 5: Update enhancement_history to completed
                processing_time_ms = int((time() - start_time) * 1000)
                enhancement.status = "completed"
                enhancement.processing_time_ms = processing_time_ms
                enhancement.completed_at = datetime.utcnow()
                enhancement.llm_output = f"Placeholder: Enhancement processing completed for ticket {job.ticket_id}"
                await session.commit()

                return {
                    "status": "completed",
                    "ticket_id": job.ticket_id,
                    "enhancement_id": enhancement_id,
                    "processing_time_ms": processing_time_ms,
                }

        # Run async database operations in sync Celery task
        result = asyncio.run(create_and_process_enhancement())

        # Task 4: Log task completion
        logger.info(
            "Task enhance_ticket completed successfully",
            extra={
                "task_id": self.request.id,
                "ticket_id": job.ticket_id,
                "tenant_id": job.tenant_id,
                "enhancement_id": enhancement_id,
                "status": "completed",
                "processing_time_ms": result["processing_time_ms"],
            },
        )

        # Task 10: Record Prometheus metrics
        if METRICS_ENABLED:
            enhancement_tasks_total.labels(status='completed', tenant_id=job.tenant_id).inc()
            enhancement_task_duration_seconds.labels(status='completed', tenant_id=job.tenant_id).observe(
                result["processing_time_ms"] / 1000.0
            )

        return result

    except SoftTimeLimitExceeded:
        # Task 7: Handle timeout
        processing_time_ms = int((time() - start_time) * 1000)
        logger.warning(
            "Task enhance_ticket exceeded soft time limit",
            extra={
                "task_id": self.request.id,
                "ticket_id": job_data.get("ticket_id") if isinstance(job_data, dict) else None,
                "tenant_id": job_data.get("tenant_id") if isinstance(job_data, dict) else None,
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
                        enhancement.completed_at = datetime.utcnow()
                        await session.commit()

            asyncio.run(mark_timeout())

        raise

    except Exception as exc:
        # Task 7: Handle errors with retry logic
        processing_time_ms = int((time() - start_time) * 1000)
        attempt_number = self.request.retries

        logger.error(
            f"Task enhance_ticket failed with error: {str(exc)}",
            extra={
                "task_id": self.request.id,
                "ticket_id": job_data.get("ticket_id") if isinstance(job_data, dict) else None,
                "tenant_id": job_data.get("tenant_id") if isinstance(job_data, dict) else None,
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
                        enhancement.completed_at = datetime.utcnow()
                        await session.commit()

            asyncio.run(mark_failed())

        # Task 10: Record Prometheus metrics for failure
        if METRICS_ENABLED:
            enhancement_tasks_total.labels(status='failed', tenant_id=tenant_id).inc()
            enhancement_task_duration_seconds.labels(status='failed', tenant_id=tenant_id).observe(
                processing_time_ms / 1000.0
            )

        # Celery will auto-retry via autoretry_for decorator
        raise
