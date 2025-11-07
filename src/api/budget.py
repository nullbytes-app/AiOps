"""Budget webhook endpoint for LiteLLM alerts.

This module provides the webhook endpoint that receives budget alerts from
LiteLLM proxy when tenants cross budget thresholds (80%, 100%, projected).
Handles async notification dispatch and audit logging.

Webhook Events:
    - threshold_crossed: Soft budget reached (default: 80%)
    - budget_crossed: Hard budget exceeded (100%)
    - projected_limit_exceeded: Projected to exceed based on trends

Architecture:
    LiteLLM Proxy → POST /api/v1/budget-alerts → Webhook Handler
    → Notification Service (async) → Email/Slack alerts

References:
    - LiteLLM Webhook Docs: https://docs.litellm.ai/docs/proxy/alerting
    - Story 2.2: Webhook signature validation pattern
    - Story 8.10: Budget enforcement with grace period
"""

import hmac
import hashlib
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Request, HTTPException, Depends, Header
from pydantic import BaseModel, Field, field_validator
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_async_session
from src.database.models import BudgetAlertHistory, AuditLog
from src.config import settings
from src.services.notification_service import NotificationService


# Pydantic schema for LiteLLM budget webhook payload
class BudgetWebhookPayload(BaseModel):
    """
    LiteLLM budget webhook payload schema.

    Matches the webhook payload structure sent by LiteLLM proxy when
    budget thresholds are crossed. See LiteLLM docs for field details.

    Attributes:
        spend: Current spend in USD
        max_budget: Maximum budget in USD
        token: LiteLLM virtual key token (hashed for security)
        user_id: User ID (maps to tenant_id in our system)
        team_id: Team ID (optional, not used in our implementation)
        user_email: User email (optional)
        key_alias: Key alias for identification
        projected_exceeded_date: Projected date when budget will be exceeded (optional)
        projected_spend: Projected spend at end of period (optional)
        event: Event type (threshold_crossed, budget_crossed, projected_limit_exceeded)
        event_group: Event group (user, team, key)
        event_message: Human-readable event message
    """

    spend: float = Field(..., description="Current spend in USD", ge=0)
    max_budget: float = Field(..., description="Maximum budget in USD", gt=0)
    token: str = Field(..., description="LiteLLM virtual key token (hashed)")
    user_id: str = Field(..., description="User ID (tenant_id in our system)")
    team_id: Optional[str] = Field(None, description="Team ID (optional)")
    user_email: Optional[str] = Field(None, description="User email (optional)")
    key_alias: Optional[str] = Field(None, description="Key alias for identification")
    projected_exceeded_date: Optional[str] = Field(
        None, description="Projected date when budget will be exceeded"
    )
    projected_spend: Optional[float] = Field(
        None, description="Projected spend at end of period"
    )
    event: str = Field(
        ...,
        description="Event type: threshold_crossed, budget_crossed, projected_limit_exceeded",
    )
    event_group: str = Field(..., description="Event group: user, team, key")
    event_message: str = Field(..., description="Human-readable event message")

    @field_validator("event")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Validate event type is one of expected values."""
        valid_events = [
            "threshold_crossed",
            "budget_crossed",
            "projected_limit_exceeded",
            "spend_tracked",
        ]
        if v not in valid_events:
            raise ValueError(
                f"Invalid event type: {v}. Must be one of {valid_events}"
            )
        return v


router = APIRouter(prefix="/api/v1", tags=["budget"])


def verify_webhook_signature(
    payload_body: bytes, signature: str, secret: str
) -> bool:
    """
    Verify HMAC signature for webhook payload.

    Uses constant-time comparison to prevent timing attacks.
    Follows same pattern as Story 2.2 webhook signature validation.

    Args:
        payload_body: Raw request body bytes
        signature: Signature from X-Webhook-Signature header
        secret: Webhook signing secret (from settings)

    Returns:
        bool: True if signature is valid, False otherwise
    """
    expected_signature = hmac.new(
        key=secret.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected_signature, signature)


@router.post(
    "/budget-alerts",
    status_code=200,
    summary="Receive LiteLLM budget alert webhooks",
    description=(
        "Webhook endpoint for LiteLLM proxy budget alerts. Receives alerts when "
        "tenants cross budget thresholds (80%, 100%, projected). Handles async "
        "notification dispatch and audit logging. Returns 200 OK immediately to "
        "avoid LiteLLM retry storms."
    ),
)
async def receive_budget_alert(
    request: Request,
    payload: BudgetWebhookPayload,
    x_webhook_signature: Optional[str] = Header(None, alias="X-Webhook-Signature"),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """
    Receive and process LiteLLM budget alert webhook.

    Processing flow:
        1. Validate webhook signature (HMAC SHA256)
        2. Parse event type and extract tenant_id
        3. Store alert in budget_alert_history table
        4. Dispatch notifications asynchronously (80% alert, 100% critical)
        5. Create audit log entry
        6. Return 200 OK immediately

    Args:
        request: FastAPI request object (for raw body access)
        payload: Parsed webhook payload
        x_webhook_signature: Webhook signature header
        db: Database session

    Returns:
        dict: Success response with alert_id

    Raises:
        HTTPException 401: Invalid signature
        HTTPException 400: Invalid payload or missing tenant

    Example:
        POST /api/v1/budget-alerts
        X-Webhook-Signature: abc123...
        {
            "spend": 450.00,
            "max_budget": 500.00,
            "user_id": "acme-corp",
            "event": "threshold_crossed",
            "event_message": "User Budget: Threshold Crossed at 80%"
        }
    """
    # Webhook signature validation (if configured)
    webhook_secret = getattr(settings, "litellm_webhook_secret", None)
    if webhook_secret and x_webhook_signature:
        # Get raw request body for signature validation
        body = await request.body()
        if not verify_webhook_signature(body, x_webhook_signature, webhook_secret):
            logger.warning(
                f"Invalid webhook signature for budget alert (user_id: {payload.user_id})"
            )
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    elif webhook_secret and not x_webhook_signature:
        logger.warning(
            f"Missing webhook signature for budget alert (user_id: {payload.user_id})"
        )
        raise HTTPException(status_code=401, detail="Missing webhook signature")

    # Extract tenant_id from user_id (LiteLLM user_id = our tenant_id)
    tenant_id = payload.user_id

    logger.info(
        f"Budget alert received: tenant={tenant_id}, event={payload.event}, "
        f"spend=${payload.spend:.2f}, budget=${payload.max_budget:.2f}"
    )

    try:
        # Calculate percentage used
        percentage = int((payload.spend / payload.max_budget) * 100)

        # Store alert in budget_alert_history table
        alert = BudgetAlertHistory(
            tenant_id=tenant_id,
            event_type=payload.event,
            spend=payload.spend,
            max_budget=payload.max_budget,
            percentage=percentage,
        )
        db.add(alert)
        await db.flush()

        # Create audit log entry
        audit_entry = AuditLog(
            user="system",
            operation=f"budget_alert_{payload.event}",
            details={
                "tenant_id": tenant_id,
                "event": payload.event,
                "spend": payload.spend,
                "max_budget": payload.max_budget,
                "percentage": percentage,
                "event_message": payload.event_message,
            },
            status="received",
        )
        db.add(audit_entry)
        await db.commit()

        # Dispatch notifications based on event type (async, non-blocking)
        notification_service = NotificationService()
        percentage = int((payload.spend / payload.max_budget) * 100) if payload.max_budget > 0 else 0

        if payload.event == "threshold_crossed":
            logger.info(
                f"Sending 80% threshold alert to tenant {tenant_id} "
                f"(spend: ${payload.spend:.2f})"
            )
            await notification_service.send_budget_alert(
                tenant_id=tenant_id,
                alert_type="threshold_80",
                spend=payload.spend,
                max_budget=payload.max_budget,
                percentage=percentage,
            )
        elif payload.event == "budget_crossed":
            logger.warning(
                f"Sending 100% budget crossed critical alert to tenant {tenant_id} "
                f"(spend: ${payload.spend:.2f})"
            )
            await notification_service.send_budget_alert(
                tenant_id=tenant_id,
                alert_type="budget_100",
                spend=payload.spend,
                max_budget=payload.max_budget,
                percentage=percentage,
            )
        elif payload.event == "projected_limit_exceeded":
            logger.info(
                f"Sending projected limit warning to tenant {tenant_id} "
                f"(projected: ${payload.projected_spend:.2f})"
            )
            await notification_service.send_budget_alert(
                tenant_id=tenant_id,
                alert_type="projected",
                spend=payload.spend,
                max_budget=payload.max_budget,
                percentage=percentage,
            )

        # Return 200 OK immediately to avoid LiteLLM retry storms
        return {
            "status": "success",
            "alert_id": alert.id,
            "message": f"Budget alert received and processed for tenant {tenant_id}",
        }

    except Exception as e:
        logger.error(f"Error processing budget alert for tenant {tenant_id}: {str(e)}")
        # Still return 200 OK to avoid retry storms (error is logged)
        return {
            "status": "error",
            "message": f"Error processing alert: {str(e)}",
        }
