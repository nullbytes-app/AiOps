"""Notification service for budget alerts.

This module provides email and Slack notification dispatch for budget alerts.
Includes deduplication (1-hour cache) and graceful failure handling.

TODO (Story 8.10 - remaining work):
    - Implement email template rendering
    - Add Slack webhook integration
    - Implement Redis-based deduplication cache
    - Add Celery task for async dispatch
    - Add notification failure retry logic

For now, this is a stub that logs notification intents.
"""

from typing import Optional
from datetime import datetime, timezone

from loguru import logger


"""Notification service for budget alerts.

This module provides email and Slack notification dispatch for budget alerts.
Includes deduplication (1-hour cache) and graceful failure handling.
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
import redis.asyncio as redis
from jinja2 import Template
from loguru import logger

from src.config import settings


# Email templates
EMAIL_80_TEMPLATE = Template("""
Subject: Budget Alert: 80% LLM Usage Reached

Hi {{ tenant_id }},

Your AI Agents platform account has reached 80% of your monthly LLM budget:

Current Spend: ${{ "%.2f"|format(spend) }}
Max Budget: ${{ "%.2f"|format(max_budget) }}
Usage: {{ percentage }}%
Days Remaining: {{ days_remaining }} days until reset

Recommended Actions:
1. Monitor usage closely over next few days
2. Review agent execution logs for unexpected activity
3. Contact support to increase budget if needed

Your agents will continue operating normally. You'll receive another alert at 100%, and enforcement begins at {{ grace_threshold }}% (${{ "%.2f"|format(max_budget * grace_threshold / 100) }}).

Best regards,
AI Agents Platform
""")

EMAIL_100_TEMPLATE = Template("""
Subject: CRITICAL: Budget Limit Reached

Hi {{ tenant_id }},

Your AI Agents platform account has reached 100% of your monthly LLM budget:

Current Spend: ${{ "%.2f"|format(spend) }}
Max Budget: ${{ "%.2f"|format(max_budget) }}
Usage: {{ percentage }}%

Grace Period Active: Agents will be blocked at ${{ "%.2f"|format(max_budget * grace_threshold / 100) }} ({{ grace_threshold }}%)
Reset Date: {{ reset_date }}

Action Required: Consider budget override or usage reduction to avoid service interruption.

Best regards,
AI Agents Platform
""")

# Slack message templates
SLACK_80_TEMPLATE = """
⚠️ *Budget Alert: 80% Usage Reached*

*Tenant:* {tenant_id}
*Current Spend:* ${spend:.2f}
*Max Budget:* ${max_budget:.2f}
*Usage:* {percentage}%

Reset Date: {reset_date} ({days_remaining} days)

*Recommended:* Monitor usage or contact support to increase budget
"""

SLACK_100_TEMPLATE = """
🚨 *CRITICAL: Budget Limit Reached*

*Tenant:* {tenant_id}
*Current Spend:* ${spend:.2f}
*Max Budget:* ${max_budget:.2f}
*Usage:* {percentage}%

Grace Period Active: Agents will be blocked at ${grace_limit:.2f} ({grace_threshold}%)
Reset Date: {reset_date}

*Action Required:* Consider budget override or usage reduction
"""


class NotificationService:
    """
    Service for dispatching budget alert notifications.

    Handles email and Slack notifications with Redis-based deduplication (1-hour TTL)
    and graceful failure handling.

    Args:
        redis_client: Optional Redis client for deduplication cache
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize notification service.

        Args:
            redis_client: Optional Redis client (will create if not provided)
        """
        self.redis_client = redis_client
        self._redis_initialized = redis_client is not None

    async def _get_redis_client(self) -> redis.Redis:
        """Get or create Redis client for deduplication."""
        if not self._redis_initialized:
            self.redis_client = redis.from_url(
                settings.redis_url,
                password=settings.redis_password,
                max_connections=settings.redis_max_connections,
                decode_responses=True,
            )
            self._redis_initialized = True
        return self.redis_client

    async def _check_deduplication(
        self, tenant_id: str, alert_type: str
    ) -> bool:
        """
        Check if alert was recently sent (deduplication).

        Args:
            tenant_id: Tenant identifier
            alert_type: Alert type (threshold_80, budget_100, projected)

        Returns:
            bool: True if alert should be sent, False if duplicate
        """
        try:
            redis_client = await self._get_redis_client()
            cache_key = f"budget_alert:{tenant_id}:{alert_type}"

            # Check if key exists
            exists = await redis_client.exists(cache_key)
            if exists:
                logger.info(
                    f"Skipping duplicate alert: tenant={tenant_id}, type={alert_type}"
                )
                return False

            # Set key with 1-hour TTL
            await redis_client.setex(cache_key, 3600, "1")
            return True

        except Exception as e:
            logger.error(f"Deduplication check failed: {e}, allowing notification")
            return True  # Fail-safe: allow notification if cache fails

    async def send_budget_alert(
        self,
        tenant_id: str,
        alert_type: str,
        spend: float,
        max_budget: float,
        percentage: int,
        grace_threshold: int = 110,
        reset_date: Optional[str] = None,
        days_remaining: Optional[int] = None,
    ) -> None:
        """
        Send budget alert notification (email/Slack).

        Args:
            tenant_id: Tenant identifier
            alert_type: Alert type (threshold_80, budget_100, projected)
            spend: Current spend in USD
            max_budget: Maximum budget in USD
            percentage: Percentage used
            grace_threshold: Grace threshold percentage (default: 110)
            reset_date: Budget reset date string (optional)
            days_remaining: Days until reset (optional)
        """
        try:
            # Deduplication check
            should_send = await self._check_deduplication(tenant_id, alert_type)
            if not should_send:
                return

            # Determine template based on alert type
            if alert_type == "threshold_80" or percentage >= 80:
                email_body = EMAIL_80_TEMPLATE.render(
                    tenant_id=tenant_id,
                    spend=spend,
                    max_budget=max_budget,
                    percentage=percentage,
                    grace_threshold=grace_threshold,
                    days_remaining=days_remaining or "N/A",
                )
                slack_message = SLACK_80_TEMPLATE.format(
                    tenant_id=tenant_id,
                    spend=spend,
                    max_budget=max_budget,
                    percentage=percentage,
                    reset_date=reset_date or "N/A",
                    days_remaining=days_remaining or "N/A",
                )
            else:  # budget_100 or projected
                email_body = EMAIL_100_TEMPLATE.render(
                    tenant_id=tenant_id,
                    spend=spend,
                    max_budget=max_budget,
                    percentage=percentage,
                    grace_threshold=grace_threshold,
                    reset_date=reset_date or "N/A",
                )
                slack_message = SLACK_100_TEMPLATE.format(
                    tenant_id=tenant_id,
                    spend=spend,
                    max_budget=max_budget,
                    percentage=percentage,
                    grace_threshold=grace_threshold,
                    grace_limit=max_budget * grace_threshold / 100,
                    reset_date=reset_date or "N/A",
                )

            # Send notifications (async, fire-and-forget)
            await self._send_email_notification(tenant_id, email_body)
            await self._send_slack_notification(tenant_id, slack_message)

            logger.info(
                f"Budget alert sent: tenant={tenant_id}, type={alert_type}, "
                f"spend=${spend:.2f}, budget=${max_budget:.2f}, percentage={percentage}%"
            )

        except Exception as e:
            # Graceful failure: log error, don't block webhook
            logger.error(
                f"Notification dispatch failed for tenant={tenant_id}: {e}",
                exc_info=True,
            )

    async def _send_email_notification(
        self, tenant_id: str, email_body: str
    ) -> None:
        """
        Send email notification.

        Args:
            tenant_id: Tenant identifier
            email_body: Rendered email body with subject

        Note:
            Requires SMTP configuration in settings. If not configured,
            logs intent only.
        """
        try:
            # Check if SMTP is configured
            if not hasattr(settings, "smtp_host") or not settings.smtp_host:
                logger.warning(
                    f"SMTP not configured, skipping email for tenant={tenant_id}"
                )
                logger.info(f"[EMAIL PREVIEW]\n{email_body}")
                return

            # TODO: Implement SMTP email dispatch
            # For now, log the email content
            logger.info(
                f"[EMAIL] Would send to tenant={tenant_id}:\n{email_body}"
            )

            # Future implementation:
            # import aiosmtplib
            # from email.message import EmailMessage
            #
            # msg = EmailMessage()
            # msg["From"] = settings.smtp_from_email
            # msg["To"] = tenant_email  # Need to look up tenant email
            # msg["Subject"] = email_body.split("\n")[0].replace("Subject: ", "")
            # msg.set_content(email_body)
            #
            # await aiosmtplib.send(
            #     msg,
            #     hostname=settings.smtp_host,
            #     port=settings.smtp_port,
            #     username=settings.smtp_username,
            #     password=settings.smtp_password,
            #     use_tls=settings.smtp_use_tls,
            # )

        except Exception as e:
            logger.error(f"Email send failed for tenant={tenant_id}: {e}")

    async def _send_slack_notification(
        self, tenant_id: str, slack_message: str
    ) -> None:
        """
        Send Slack webhook notification.

        Args:
            tenant_id: Tenant identifier
            slack_message: Formatted Slack message (Markdown)

        Note:
            Requires Slack webhook URL in settings. If not configured,
            logs intent only.
        """
        try:
            # Check if Slack webhook is configured
            if (
                not hasattr(settings, "slack_webhook_url")
                or not settings.slack_webhook_url
            ):
                logger.warning(
                    f"Slack webhook not configured, skipping for tenant={tenant_id}"
                )
                logger.info(f"[SLACK PREVIEW]\n{slack_message}")
                return

            # Send Slack webhook
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    settings.slack_webhook_url,
                    json={"text": slack_message},
                )
                response.raise_for_status()

            logger.info(f"Slack notification sent: tenant={tenant_id}")

        except Exception as e:
            logger.error(
                f"Slack send failed for tenant={tenant_id}: {e}"
            )

    async def close(self) -> None:
        """Close Redis client connection."""
        if self._redis_initialized and self.redis_client:
            await self.redis_client.close()

        # TODO: Check deduplication cache (Redis, 1-hour TTL)
        # TODO: Render email template
        # TODO: Send via SMTP or email service
        # TODO: Send Slack webhook if configured
        # TODO: Store in cache to prevent duplicates
        # TODO: Handle failures gracefully (log, don't block)
