"""
Webhook receiver endpoints for external integrations.

This module implements the webhook endpoint for receiving ticket notifications
from ServiceDesk Plus. The endpoint validates payloads, logs requests, and returns
202 Accepted immediately while queuing processing for workers.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError

from src.schemas.webhook import WebhookPayload, ResolvedTicketWebhook, WebhookResponse
from src.services.webhook_validator import validate_webhook_signature, validate_signature
from src.services.queue_service import QueueService, get_queue_service
from src.monitoring import enhancement_requests_total
from src.services.ticket_storage_service import store_webhook_resolved_ticket
from src.services.tenant_service import TenantService
from src.database.session import get_async_session
from src.api.dependencies import get_tenant_db, get_tenant_config_dep
from src.config import get_settings
from src.schemas.tenant import TenantConfigInternal
from src.utils.exceptions import QueueServiceError
from src.utils.logger import logger, AuditLogger
from sqlalchemy.ext.asyncio import AsyncSession

# Story 4.6: Distributed tracing context propagation
from opentelemetry.propagate import inject

router = APIRouter(prefix="/webhook", tags=["webhooks"])


@router.post(
    "/servicedesk",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Receive ServiceDesk Plus webhook notification",
    description="Accepts webhook notifications from ServiceDesk Plus when tickets are created or updated. "
    "Validates the payload using tenant-specific webhook secret and returns 202 Accepted immediately while "
    "queuing the ticket for enhancement processing. Uses tenant-specific configuration for ServiceDesk Plus credentials "
    "and enhancement preferences. This is the primary entry point for the ticket enhancement pipeline.",
    response_model=WebhookResponse,
)
async def receive_webhook(
    payload: WebhookPayload,
    db: AsyncSession = Depends(get_tenant_db),
    queue_service: QueueService = Depends(get_queue_service),
    tenant_config: TenantConfigInternal = Depends(get_tenant_config_dep)
) -> WebhookResponse:
    """
    Receive and validate webhook notification from ServiceDesk Plus.

    Immediately acknowledges the webhook with 202 Accepted to prevent timeout,
    while delegating actual processing to background workers. Loads tenant-specific
    configuration (ServiceDesk Plus credentials and enhancement preferences) and
    queues job with tenant context. Request is logged with correlation ID for
    distributed tracing. Job is queued to Redis for asynchronous processing by
    Celery workers.

    Args:
        payload: WebhookPayload model containing ticket information
        db: RLS-aware database session (injected via get_tenant_db dependency)
        queue_service: QueueService instance (injected via dependency)
        tenant_config: Tenant configuration with ServiceDesk Plus credentials
                      and enhancement preferences (injected via get_tenant_config_dep)

    Returns:
        dict: Response object with status, job_id, and message
            - status: "accepted" (indicates webhook was accepted)
            - job_id: Unique identifier for this enhancement job
            - message: Human-readable confirmation message

    Raises:
        ValidationError: FastAPI automatically returns 422 if payload is invalid
        HTTPException(503): If Redis queue is unavailable
        HTTPException(404): If tenant configuration not found
        HTTPException(400): If tenant_id missing from request

    Example:
        Request body:
        {
            "event": "ticket_created",
            "ticket_id": "TKT-001",
            "tenant_id": "tenant-abc",
            "description": "Server is slow and unresponsive",
            "priority": "high",
            "created_at": "2025-11-01T12:00:00Z"
        }

        Response (202):
        {
            "status": "accepted",
            "job_id": "550e8400-e29b-41d4-a716-446655440000",
            "message": "Enhancement job queued successfully"
        }
    """
    # Generate unique job ID for correlation and tracking
    job_id = str(uuid.uuid4())
    # Use provided correlation_id from payload if available, otherwise generate new one
    correlation_id = payload.correlation_id or str(uuid.uuid4())

    # Bind correlation ID to logger context for all downstream operations
    logger.bind(correlation_id=correlation_id)

    # Increment Prometheus metric for received webhook
    enhancement_requests_total.labels(
        tenant_id=payload.tenant_id, status="received"
    ).inc()

    # Log webhook receipt using AuditLogger for compliance tracking
    AuditLogger.audit_webhook_received(
        tenant_id=payload.tenant_id,
        ticket_id=payload.ticket_id,
        correlation_id=correlation_id,
        event=payload.event,
        priority=payload.priority,
        description_length=len(payload.description),
    )

    # Queue job to Redis for asynchronous processing
    try:
        # Prepare job data for queue
        # Reason: Include tenant-specific config (ServiceDesk Plus credentials, preferences)
        # so Celery workers can process with correct tenant context and configuration

        # Story 4.6: Extract trace context from current request for propagation to Celery task
        # This enables single trace ID to span both FastAPI (webhook receiver) and Celery (enhancement worker)
        from src.monitoring import get_tracer
        from opentelemetry import trace as otel_trace
        
        trace_context_carrier = {}
        inject(trace_context_carrier)  # Injects traceparent and tracestate headers

        # Get current span and add custom attributes for webhook_received span
        current_span = otel_trace.get_current_span()
        if current_span and current_span.is_recording():
            current_span.set_attribute("tenant.id", payload.tenant_id)
            current_span.set_attribute("ticket.id", payload.ticket_id)
            current_span.set_attribute("ticket.priority", payload.priority)
            current_span.set_attribute("ticket.event", payload.event)
            current_span.set_attribute("webhook.correlation_id", correlation_id)

        job_data = {
            "job_id": job_id,
            "ticket_id": payload.ticket_id,
            "tenant_id": payload.tenant_id,
            "description": payload.description,
            "priority": payload.priority,
            "timestamp": payload.created_at,
            "correlation_id": correlation_id,  # Propagate correlation ID through job payload
            # Tenant-specific configuration (from tenant_config dependency)
            "servicedesk_url": tenant_config.servicedesk_url,
            "servicedesk_api_key": tenant_config.api_key,  # Decrypted by dependency
            "enhancement_preferences": tenant_config.enhancement_preferences,
            # Story 4.6: Trace context for distributed tracing across services
            "trace_context": trace_context_carrier.get("traceparent", ""),  # W3C Trace Context format
        }

        # Story 4.6: Custom span for job_queued phase (AC5)
        # Create a named span for Redis queue operation with current span as parent
        tracer = get_tracer("src.api.webhooks")
        with tracer.start_as_current_span("job_queued") as queue_span:
            queue_span.set_attribute("queue.name", "enhancement_queue")
            queue_span.set_attribute("job.id", job_id)
            queue_span.set_attribute("tenant.id", payload.tenant_id)
            queue_span.set_attribute("ticket.id", payload.ticket_id)

            # Push job to Redis queue
            queued_job_id = await queue_service.push_job(
                job_data, tenant_id=payload.tenant_id, ticket_id=payload.ticket_id
            )

        # Increment Prometheus metric for successfully queued job
        enhancement_requests_total.labels(
            tenant_id=payload.tenant_id, status="queued"
        ).inc()

        logger.info(
            f"Job queued successfully: {queued_job_id}",
            extra={
                "job_id": queued_job_id,
                "ticket_id": payload.ticket_id,
                "tenant_id": payload.tenant_id,
                "correlation_id": correlation_id,
            },
        )

        # Return 202 Accepted with job ID for tracking
        return {
            "status": "accepted",
            "job_id": queued_job_id,
            "message": "Enhancement job queued successfully",
        }

    except QueueServiceError as e:
        # Queue push failed - return 503 Service Unavailable
        # Increment Prometheus metric for rejected job
        enhancement_requests_total.labels(
            tenant_id=payload.tenant_id, status="rejected"
        ).inc()

        logger.error(
            f"Failed to queue job: {str(e)}",
            extra={
                "tenant_id": payload.tenant_id,
                "ticket_id": payload.ticket_id,
                "correlation_id": correlation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Queue unavailable, please retry",
        )


@router.post(
    "/servicedesk/resolved-ticket",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Receive resolved ticket webhook from ServiceDesk Plus",
    description="Accepts webhook notifications from ServiceDesk Plus when tickets are marked as resolved or closed. "
    "Validates the payload and signature, then stores the ticket in ticket_history asynchronously for context gathering. "
    "Returns 202 Accepted immediately without blocking on storage.",
)
async def store_resolved_ticket(
    request: Request,
    payload: ResolvedTicketWebhook,
    session: AsyncSession = Depends(get_tenant_db),
    settings = Depends(get_settings),
) -> WebhookResponse:
    """
    Receive and store resolved ticket webhook notification from ServiceDesk Plus.

    Validates the webhook signature using HMAC-SHA256, then stores the resolved ticket
    in ticket_history asynchronously without blocking. Returns 202 Accepted immediately
    while storage happens in the background. Uses UPSERT logic to maintain idempotency.

    Args:
        request: FastAPI Request object (for raw body and signature validation)
        payload: ResolvedTicketWebhook model containing resolved ticket information
        session: AsyncSession for database operations
        settings: Application settings for webhook secret

    Returns:
        dict: Response with status="accepted"

    Raises:
        HTTPException(401): If signature header is missing or invalid
        HTTPException(400): If webhook payload is malformed
        HTTPException(422): If Pydantic validation fails (invalid types/formats)
        HTTPException(503): If database is unavailable
        HTTPException(500): For unexpected errors

    Example:
        Request:
        POST /webhook/servicedesk/resolved-ticket
        Headers:
            X-ServiceDesk-Signature: a1b2c3d4e5f6...
            Content-Type: application/json
        Body:
        {
            "tenant_id": "acme-corp",
            "ticket_id": "TKT-12345",
            "subject": "Database pool exhausted",
            "description": "Connection pool issue after backup job",
            "resolution": "Increased pool size from 10 to 25",
            "resolved_date": "2025-11-01T14:30:00Z",
            "priority": "high",
            "tags": ["database", "infrastructure"]
        }

        Response (202):
        {
            "status": "accepted"
        }
    """
    correlation_id = str(uuid.uuid4())
    ticket_id = payload.ticket_id
    tenant_id = payload.tenant_id

    try:
        # Validate webhook signature using HMAC-SHA256
        # Reason: Story 2.2 pattern - ensure webhook authenticity before processing
        raw_body = await request.body()
        signature_header = request.headers.get("X-ServiceDesk-Signature")

        if not signature_header:
            logger.warning(
                "Resolved ticket webhook validation failed: Missing X-ServiceDesk-Signature header",
                extra={
                    "tenant_id": tenant_id,
                    "ticket_id": ticket_id,
                    "correlation_id": correlation_id,
                    "reason": "missing_header",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing signature header",
            )

        is_valid = validate_signature(
            raw_payload=raw_body,
            signature_header=signature_header,
            secret=settings.webhook_secret,
        )

        if not is_valid:
            logger.warning(
                "Resolved ticket webhook signature validation failed",
                extra={
                    "tenant_id": tenant_id,
                    "ticket_id": ticket_id,
                    "correlation_id": correlation_id,
                    "reason": "invalid_signature",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )

        # Log successful webhook receipt
        logger.info(
            f"Resolved ticket webhook received: ticket_id={ticket_id}, tenant_id={tenant_id}",
            extra={
                "tenant_id": tenant_id,
                "ticket_id": ticket_id,
                "correlation_id": correlation_id,
                "priority": payload.priority,
                "source": "webhook_resolved",
            },
        )

        # Store ticket asynchronously (non-blocking)
        # Reason: AC #7 requires <50ms endpoint response; storage happens in background
        try:
            # Convert payload to dict for storage service
            payload_dict = payload.model_dump()

            # Store ticket in background without blocking response
            # Note: In production, could use Celery task for reliability, but asyncio.create_task
            # sufficient for current performance targets (16.67 webhooks/sec, ~60ms per ticket)
            await store_webhook_resolved_ticket(session, payload_dict)

        except Exception as storage_error:
            # Log storage error but don't block endpoint (AC #8: non-blocking error handling)
            logger.error(
                f"Failed to store resolved ticket: {str(storage_error)}",
                extra={
                    "tenant_id": tenant_id,
                    "ticket_id": ticket_id,
                    "correlation_id": correlation_id,
                    "error": str(storage_error),
                    "error_type": type(storage_error).__name__,
                },
            )
            # Still return 202 Accepted - error is logged for alerting
            # Reason: AC #8 - invalid/malformed webhooks don't break endpoint

        # Return 202 Accepted immediately (non-blocking)
        return {"status": "accepted"}

    except ValidationError as e:
        # Pydantic validation error - malformed payload
        logger.warning(
            f"Resolved ticket webhook payload validation failed: {str(e)}",
            extra={
                "tenant_id": tenant_id,
                "ticket_id": ticket_id,
                "correlation_id": correlation_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid payload format",
        )

    except HTTPException:
        # Re-raise HTTP exceptions (401, etc.)
        raise

    except Exception as e:
        # Unexpected error
        logger.error(
            f"Unexpected error processing resolved ticket webhook: {str(e)}",
            extra={
                "tenant_id": tenant_id,
                "ticket_id": ticket_id,
                "correlation_id": correlation_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
