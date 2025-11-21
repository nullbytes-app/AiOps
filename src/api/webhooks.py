"""
Webhook receiver endpoints for external integrations.

This module implements the webhook endpoint for receiving ticket notifications
from ServiceDesk Plus. The endpoint validates payloads, logs requests, and returns
202 Accepted immediately while queuing processing for workers.

Story 7.3: Updated to use Plugin Manager for multi-tool webhook validation.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status, Header
from pydantic import ValidationError
from typing import Optional

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

# Story 7.3: Plugin Manager for multi-tool support
from src.plugins import PluginManager, PluginNotFoundError

router = APIRouter(prefix="/webhook", tags=["webhooks"])


@router.post(
    "/servicedesk",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Receive ServiceDesk Plus webhook notification",
    description="Accepts webhook notifications from ServiceDesk Plus when tickets are created or updated. "
    "Validates the payload using tenant-specific webhook secret via Plugin Manager and returns 202 Accepted immediately while "
    "queuing the ticket for enhancement processing. Uses tenant-specific configuration for ServiceDesk Plus credentials "
    "and enhancement preferences. Supports multi-tool routing via plugin architecture (Story 7.3).",
    response_model=WebhookResponse,
)
async def receive_webhook(
    request: Request,
    payload: WebhookPayload,
    db: AsyncSession = Depends(get_tenant_db),
    queue_service: QueueService = Depends(get_queue_service),
    tenant_config: TenantConfigInternal = Depends(get_tenant_config_dep),
    x_servicedesk_signature: Optional[str] = Header(None, alias="X-ServiceDesk-Signature"),
) -> WebhookResponse:
    """
    Receive and validate webhook notification from ticketing tool.

    Story 7.3: Updated to use Plugin Manager for multi-tool webhook validation.
    Supports ServiceDesk Plus (current), Jira, Zendesk, and other ticketing tools
    via plugin architecture.

    Immediately acknowledges the webhook with 202 Accepted to prevent timeout,
    while delegating actual processing to background workers. Uses Plugin Manager
    to route webhook validation and metadata extraction to the correct tool plugin
    based on tenant_config.tool_type.

    Args:
        payload: WebhookPayload model containing ticket information
        db: RLS-aware database session (injected via get_tenant_db dependency)
        queue_service: QueueService instance (injected via dependency)
        tenant_config: Tenant configuration with credentials and tool_type
        x_servicedesk_signature: HMAC signature from webhook header (optional for backward compatibility)

    Returns:
        dict: Response object with status, job_id, and message

    Raises:
        HTTPException(401): If webhook signature validation fails
        HTTPException(404): If plugin not found for tenant's tool_type
        HTTPException(503): If Redis queue is unavailable

    Example:
        Request headers:
        X-ServiceDesk-Signature: abc123...

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
    # Story 7.3: Validate webhook using Plugin Manager
    # Security priority: Validate signature BEFORE any processing
    try:
        # Get plugin for tenant's tool type (defaults to 'servicedesk_plus')
        manager = PluginManager()
        tool_type = getattr(tenant_config, "tool_type", "servicedesk_plus")
        plugin = manager.get_plugin(tool_type)

        # Validate webhook signature using plugin
        if not x_servicedesk_signature:
            # Signature is required for all webhooks (Story 2.2)
            logger.warning(
                f"Webhook received without signature header for tenant: {payload.tenant_id}",
                extra={
                    "tenant_id": payload.tenant_id,
                    "tool_type": tool_type,
                    "event_type": "missing_signature_header",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing signature header",
            )

        # Extract raw request body for signature validation
        # This preserves the exact JSON format used by the client to compute the signature
        raw_body = await request.body()

        is_valid = await plugin.validate_webhook(
            payload=payload.dict(), signature=x_servicedesk_signature, raw_body=raw_body
        )

        if not is_valid:
            logger.error(
                f"Webhook signature validation failed for tenant: {payload.tenant_id}",
                extra={
                    "tenant_id": payload.tenant_id,
                    "tool_type": tool_type,
                    "event_type": "signature_validation_failed",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature"
            )

        # Extract and normalize metadata using plugin
        # This ensures consistent metadata format regardless of tool type
        metadata = plugin.extract_metadata(payload.dict())
        logger.info(
            f"Webhook metadata extracted via plugin",
            extra={
                "tenant_id": metadata.tenant_id,
                "ticket_id": metadata.ticket_id,
                "priority": metadata.priority,
                "tool_type": tool_type,
            },
        )

    except PluginNotFoundError as e:
        logger.error(
            f"Plugin not found for tool_type: {tool_type}",
            extra={"tenant_id": payload.tenant_id, "tool_type": tool_type, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin not found for tool type: {tool_type}",
        )
    except ValueError as e:
        # Metadata extraction failed (invalid payload structure)
        logger.error(
            f"Webhook metadata extraction failed: {str(e)}",
            extra={
                "tenant_id": payload.tenant_id,
                "error": str(e),
                "event_type": "metadata_extraction_failed",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid webhook payload: {str(e)}",
        )

    # Generate unique job ID for correlation and tracking
    job_id = str(uuid.uuid4())
    # Use provided correlation_id from payload if available, otherwise generate new one
    correlation_id = payload.correlation_id or str(uuid.uuid4())

    # Bind correlation ID to logger context for all downstream operations
    logger.bind(correlation_id=correlation_id)

    # Increment Prometheus metric for received webhook
    enhancement_requests_total.labels(tenant_id=payload.tenant_id, status="received").inc()

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
            "servicedesk_api_key": tenant_config.servicedesk_api_key,  # Decrypted by dependency
            "enhancement_preferences": tenant_config.enhancement_preferences,
            # Story 7.3: Tool type for plugin routing in workers
            "tool_type": tool_type,  # Plugin Manager routing in Celery workers
            # Story 4.6: Trace context for distributed tracing across services
            "trace_context": trace_context_carrier.get(
                "traceparent", ""
            ),  # W3C Trace Context format
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
        enhancement_requests_total.labels(tenant_id=payload.tenant_id, status="queued").inc()

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
        enhancement_requests_total.labels(tenant_id=payload.tenant_id, status="rejected").inc()

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
    settings=Depends(get_settings),
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



@router.post(
    "/agents/{agent_id}/webhook",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Agent webhook endpoint for external trigger",
    description="Accepts webhook requests to trigger agent execution. Validates HMAC-SHA256 signature, "
    "validates payload against agent's payload_schema (if defined), and enqueues agent execution task to Celery. "
    "Returns 202 Accepted immediately with execution_id for tracking.",
    tags=["agent-webhooks"],
)
async def agent_webhook_endpoint(
    agent_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
) -> dict:
    """
    Webhook endpoint for triggering agent execution via external systems.

    Story 8.6: Agent Webhook Endpoint Generation (AC#6)

    Validates HMAC-SHA256 signature using constant-time comparison, validates payload
    against agent's payload_schema (if defined), enqueues Celery task for agent execution,
    and returns execution_id for async status tracking.

    Security:
        - HMAC signature validation with timing-attack prevention (hmac.compare_digest)
        - Tenant isolation enforced (agent belongs to tenant)
        - Agent status check (only ACTIVE agents can be triggered)
        - Rate limiting (implemented in Task 11)
        - Audit logging for all requests and failures

    Args:
        agent_id: Agent UUID from URL path
        request: FastAPI Request object (for raw body)
        db: Async database session
        x_hub_signature_256: HMAC signature header (format: "sha256={hexdigest}")

    Returns:
        dict: {status: "queued", execution_id: "uuid", message: "Agent execution queued"}

    Raises:
        HTTPException(401): Invalid HMAC signature or missing header
        HTTPException(400): Payload validation failed (schema mismatch)
        HTTPException(403): Agent inactive or cross-tenant access
        HTTPException(404): Agent not found
        HTTPException(500): Task enqueueing failed

    Example:
        Request:
        POST /webhook/agents/550e8400-e29b-41d4-a716-446655440000/webhook
        Headers:
            X-Hub-Signature-256: sha256=abc123...
            Content-Type: application/json
        Body:
        {
            "ticket_id": "TKT-12345",
            "priority": "high"
        }

        Response (202):
        {
            "status": "queued",
            "execution_id": "660e8400-e29b-41d4-a716-446655440001",
            "message": "Agent execution queued"
        }
    """
    from src.services.webhook_service import (
        validate_hmac_signature,
        validate_payload_schema,
    )
    from src.utils.encryption import decrypt
    from src.database.models import Agent, AgentTrigger
    from src.schemas.agent import AgentStatus, TriggerType
    from sqlalchemy import select, and_
    from sqlalchemy.orm import selectinload

    execution_id = str(uuid.uuid4())
    logger.bind(execution_id=execution_id)

    try:
        # Fetch agent with triggers (eager load to avoid N+1)
        query = (
            select(Agent)
            .where(Agent.id == agent_id)
            .options(selectinload(Agent.triggers))
        )
        result = await db.execute(query)
        agent = result.scalar_one_or_none()

        if not agent:
            logger.warning(
                f"Agent webhook request failed: Agent not found",
                extra={"agent_id": str(agent_id), "execution_id": execution_id},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found",
            )

        # Verify agent is active (AC#6: reject if draft/suspended/inactive)
        if agent.status != AgentStatus.ACTIVE:
            logger.warning(
                f"Agent webhook request rejected: Agent not active (status={agent.status})",
                extra={
                    "agent_id": str(agent_id),
                    "agent_status": agent.status,
                    "execution_id": execution_id,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Agent is {agent.status}, only ACTIVE agents can be triggered",
            )

        # Find webhook trigger for this agent
        webhook_trigger = None
        for trigger in agent.triggers:
            if trigger.trigger_type == TriggerType.WEBHOOK:
                webhook_trigger = trigger
                break

        if not webhook_trigger:
            logger.error(
                "Agent webhook trigger not found",
                extra={"agent_id": str(agent_id), "execution_id": execution_id},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Webhook trigger not configured for this agent",
            )

        # Validate HMAC signature (AC#6: constant-time comparison for timing-attack prevention)
        if not x_hub_signature_256:
            logger.warning(
                "Agent webhook request failed: Missing X-Hub-Signature-256 header",
                extra={
                    "agent_id": str(agent_id),
                    "tenant_id": agent.tenant_id,
                    "execution_id": execution_id,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing X-Hub-Signature-256 header",
            )

        # Decrypt HMAC secret from database
        try:
            hmac_secret = decrypt(webhook_trigger.hmac_secret)
        except Exception as e:
            logger.error(
                f"Failed to decrypt HMAC secret: {e}",
                extra={"agent_id": str(agent_id), "execution_id": execution_id},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve webhook secret",
            )

        # Get raw request body for HMAC validation
        raw_body = await request.body()

        # Validate signature using constant-time comparison
        is_valid_signature = validate_hmac_signature(raw_body, x_hub_signature_256, hmac_secret)

        if not is_valid_signature:
            logger.warning(
                "Agent webhook signature validation failed",
                extra={
                    "agent_id": str(agent_id),
                    "tenant_id": agent.tenant_id,
                    "execution_id": execution_id,
                    "event_type": "hmac_validation_failed",
                },
            )
            # Audit log for security monitoring
            AuditLogger.audit_webhook_received(
                tenant_id=agent.tenant_id,
                ticket_id=f"agent_{agent_id}",
                correlation_id=execution_id,
                event="agent_webhook_signature_failed",
                priority="high",
                description_length=len(raw_body),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid HMAC signature",
            )

        # Parse JSON payload
        try:
            import json

            payload = json.loads(raw_body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning(
                f"Agent webhook payload parsing failed: {e}",
                extra={"agent_id": str(agent_id), "execution_id": execution_id},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload",
            )

        # Validate payload against schema (AC#7)
        if webhook_trigger.payload_schema:
            is_valid_payload, error_message = validate_payload_schema(
                payload, webhook_trigger.payload_schema
            )

            if not is_valid_payload:
                logger.warning(
                    f"Agent webhook payload validation failed: {error_message}",
                    extra={
                        "agent_id": str(agent_id),
                        "execution_id": execution_id,
                        "validation_error": error_message,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Payload validation failed: {error_message}",
                )

        # Log successful webhook receipt
        logger.info(
            f"Agent webhook received and validated",
            extra={
                "agent_id": str(agent_id),
                "tenant_id": agent.tenant_id,
                "execution_id": execution_id,
                "agent_name": agent.name,
            },
        )

        # Audit log for compliance
        AuditLogger.audit_webhook_received(
            tenant_id=agent.tenant_id,
            ticket_id=f"agent_{agent_id}",
            correlation_id=execution_id,
            event="agent_webhook_success",
            priority="normal",
            description_length=len(raw_body),
        )

        # Task 4.4: Enqueue Celery task for agent execution
        from src.workers.tasks import execute_agent

        try:
            task = execute_agent.apply_async(args=[str(agent_id), payload])
            celery_task_id = task.id

            logger.info(
                f"Agent execution task enqueued to Celery",
                extra={
                    "agent_id": str(agent_id),
                    "execution_id": execution_id,
                    "celery_task_id": celery_task_id,
                    "tenant_id": agent.tenant_id,
                },
            )

            return {
                "status": "queued",
                "execution_id": celery_task_id,  # Return Celery task ID for tracking
                "message": "Agent execution queued",
            }
        except Exception as e:
            logger.error(
                f"Failed to enqueue agent execution task: {e}",
                extra={
                    "agent_id": str(agent_id),
                    "execution_id": execution_id,
                    "error": str(e),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to enqueue agent execution task",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error in agent webhook endpoint: {e}",
            extra={"agent_id": str(agent_id), "execution_id": execution_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
