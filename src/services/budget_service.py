"""Budget enforcement service for LiteLLM cost control.

This module provides budget status tracking and enforcement for tenant LLM usage.
Works in conjunction with LiteLLM proxy's native budget webhooks to provide:
- Real-time budget status queries
- Budget exceeded detection (grace threshold enforcement)
- Budget blocking with clear error messages
- Budget status caching for performance

Architecture:
    - LiteLLM Proxy: Tracks spend via virtual keys, sends webhook alerts
    - Budget Service: Queries current spend, enforces grace threshold locally
    - Budget Webhooks: Async alerts at 80%, 100%, 110% thresholds (see budget.py)

References:
    - LiteLLM Budget API: https://docs.litellm.ai/docs/proxy/users#budget-api
    - Story 8.9: Virtual key management (prerequisite)
    - Story 8.10: Budget enforcement with grace period
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass

import httpx
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.config import settings
from src.database.models import TenantConfig as TenantConfigModel
from src.exceptions import BudgetExceededError


@dataclass
class ModelSpend:
    """
    Per-model spend breakdown.

    Attributes:
        model: Model name (e.g., 'gpt-4', 'claude-3-opus')
        spend: Spend in USD for this model
        percentage: Percentage of total spend
        requests: Number of requests to this model
    """

    model: str
    spend: float
    percentage: float
    requests: int


@dataclass
class TenantSpend:
    """
    Real-time spend data from LiteLLM for a tenant.

    Attributes:
        tenant_id: Tenant identifier
        current_spend: Current spend in USD
        max_budget: Maximum budget in USD
        utilization_pct: Budget utilization percentage (0-100+)
        models_breakdown: List of per-model spend details
        last_updated: Timestamp of last LiteLLM API query
        budget_duration: Budget period (e.g., '30d')
        budget_reset_at: When budget resets (ISO 8601)
    """

    tenant_id: str
    current_spend: float
    max_budget: float
    utilization_pct: float
    models_breakdown: List[ModelSpend]
    last_updated: datetime
    budget_duration: Optional[str] = None
    budget_reset_at: Optional[str] = None


@dataclass
class BudgetStatus:
    """
    Budget status information for a tenant.

    Attributes:
        tenant_id: Tenant identifier
        spend: Current spend in USD
        max_budget: Maximum budget in USD
        percentage_used: Percentage of budget used (0-100+)
        grace_remaining: USD remaining before grace threshold blocks (can be negative)
        days_until_reset: Days remaining until budget resets (None if no reset scheduled)
        alert_threshold: Alert threshold percentage (e.g., 80)
        grace_threshold: Blocking threshold percentage (e.g., 110)
        is_blocked: True if spend >= grace threshold
    """

    tenant_id: str
    spend: float
    max_budget: float
    percentage_used: float
    grace_remaining: float
    days_until_reset: Optional[int]
    alert_threshold: int
    grace_threshold: int
    is_blocked: bool


class BudgetService:
    """
    Service for budget status tracking and enforcement.

    Provides methods to query tenant budget status from LiteLLM proxy and
    enforce grace threshold blocking. Designed to be called by LLMService
    before provisioning AsyncOpenAI clients.

    Attributes:
        db: AsyncSession for database operations
        litellm_proxy_url: LiteLLM proxy base URL (from settings)
        master_key: LiteLLM master key for admin operations (from settings)
    """

    # Retry configuration (exponential backoff: 2s, 4s, 8s)
    RETRY_ATTEMPTS = 3
    RETRY_DELAYS = [2.0, 4.0, 8.0]

    # Timeout configuration (granular: connect, read, write, pool)
    TIMEOUT_CONFIG = httpx.Timeout(
        connect=5.0,  # Connection establishment
        read=30.0,  # Reading response
        write=5.0,  # Writing request
        pool=5.0,  # Acquiring connection from pool
    )

    def __init__(
        self,
        db: AsyncSession,
        litellm_proxy_url: Optional[str] = None,
        master_key: Optional[str] = None,
    ):
        """
        Initialize BudgetService with database session and LiteLLM credentials.

        Args:
            db: AsyncSession for database operations
            litellm_proxy_url: LiteLLM proxy URL (defaults to settings)
            master_key: LiteLLM master key (defaults to settings)

        Raises:
            ValueError: If required configuration missing
        """
        self.db = db
        self.litellm_proxy_url = litellm_proxy_url or getattr(
            settings, "litellm_proxy_url", None
        )
        self.master_key = master_key or getattr(settings, "litellm_master_key", None)

        if not self.litellm_proxy_url:
            raise ValueError(
                "LITELLM_PROXY_URL not configured. Set AI_AGENTS_LITELLM_PROXY_URL environment variable."
            )

        if not self.master_key:
            raise ValueError(
                "LITELLM_MASTER_KEY not configured. Set AI_AGENTS_LITELLM_MASTER_KEY environment variable."
            )

        # Remove trailing slash for consistent URL construction
        self.litellm_proxy_url = self.litellm_proxy_url.rstrip("/")

    async def get_budget_status(self, tenant_id: str) -> BudgetStatus:
        """
        Get comprehensive budget status for tenant.

        Queries LiteLLM proxy for current spend and combines with tenant
        configuration (max_budget, thresholds, reset date) to return
        complete budget status.

        Args:
            tenant_id: Tenant identifier

        Returns:
            BudgetStatus: Comprehensive budget status

        Raises:
            ValueError: If tenant not found
            Exception: If LiteLLM API call fails (logged, returns safe defaults)

        Example:
            >>> budget_service = BudgetService(db)
            >>> status = await budget_service.get_budget_status("acme-corp")
            >>> print(f"Spend: ${status.spend}, Budget: ${status.max_budget}")
            >>> print(f"Usage: {status.percentage_used}%, Blocked: {status.is_blocked}")
        """
        # Fetch tenant config from database
        stmt = select(TenantConfigModel).where(
            TenantConfigModel.tenant_id == tenant_id,
            TenantConfigModel.is_active == True,
        )
        result = await self.db.execute(stmt)
        tenant_config = result.scalar_one_or_none()

        if not tenant_config:
            raise ValueError(f"Tenant not found or inactive: {tenant_id}")

        # Get budget configuration from tenant_config
        max_budget = tenant_config.max_budget or 500.00
        alert_threshold = tenant_config.alert_threshold or 80
        grace_threshold = tenant_config.grace_threshold or 110
        budget_reset_at = tenant_config.budget_reset_at

        # Calculate days until reset
        days_until_reset = None
        if budget_reset_at:
            delta = budget_reset_at - datetime.now(timezone.utc)
            days_until_reset = max(0, delta.days)

        try:
            # Query LiteLLM proxy for current spend
            # Use /user/info endpoint with user_id=tenant_id to get spend data
            headers = {
                "Authorization": f"Bearer {self.master_key}",
                "Content-Type": "application/json",
            }

            transport = httpx.AsyncHTTPTransport(retries=1)
            async with httpx.AsyncClient(
                transport=transport,
                timeout=self.TIMEOUT_CONFIG,
                follow_redirects=True,
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            ) as client:
                response = await client.get(
                    f"{self.litellm_proxy_url}/user/info",
                    headers=headers,
                    params={"user_id": tenant_id},
                )

                if response.status_code == 200:
                    data = response.json()
                    spend = float(data.get("spend", 0.0))
                else:
                    logger.warning(
                        f"Failed to fetch budget status for tenant {tenant_id}: "
                        f"HTTP {response.status_code}. Using spend=0.0"
                    )
                    spend = 0.0

        except Exception as e:
            logger.error(f"Error fetching budget status for tenant {tenant_id}: {str(e)}")
            # Fail-safe: Allow execution if budget check fails
            spend = 0.0

        # Calculate budget metrics
        percentage_used = (spend / max_budget * 100) if max_budget > 0 else 0
        grace_limit = max_budget * (grace_threshold / 100)
        grace_remaining = grace_limit - spend
        is_blocked = spend >= grace_limit

        return BudgetStatus(
            tenant_id=tenant_id,
            spend=spend,
            max_budget=max_budget,
            percentage_used=percentage_used,
            grace_remaining=grace_remaining,
            days_until_reset=days_until_reset,
            alert_threshold=alert_threshold,
            grace_threshold=grace_threshold,
            is_blocked=is_blocked,
        )

    async def check_budget_exceeded(self, tenant_id: str) -> Tuple[bool, str]:
        """
        Check if tenant has exceeded grace threshold budget.

        Lightweight check used by LLMService before provisioning client.
        Returns boolean exceeded flag and formatted error message.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Tuple[bool, str]: (exceeded, error_message)
                - exceeded: True if budget >= grace threshold
                - error_message: Formatted message with spend, budget, remediation

        Example:
            >>> budget_service = BudgetService(db)
            >>> exceeded, msg = await budget_service.check_budget_exceeded("acme-corp")
            >>> if exceeded:
            >>>     raise BudgetExceededError(msg)
        """
        try:
            status = await self.get_budget_status(tenant_id)

            if status.is_blocked:
                error_message = (
                    f"Budget exceeded for tenant {tenant_id}. "
                    f"Current spend: ${status.spend:.2f}, "
                    f"Max budget: ${status.max_budget:.2f}, "
                    f"Grace limit: ${status.max_budget * (status.grace_threshold / 100):.2f} "
                    f"({status.grace_threshold}%). "
                    f"Remediation: Contact your administrator to increase budget or "
                    f"wait for monthly reset. Agent execution is blocked."
                )
                return (True, error_message)
            else:
                return (False, "")

        except Exception as e:
            # Fail-safe: Allow execution if budget check fails
            logger.error(
                f"Error checking budget for tenant {tenant_id}: {str(e)}. "
                "Allowing execution (fail-safe)."
            )
            return (False, "")

    async def handle_budget_block(
        self, tenant_id: str, current_spend: float
    ) -> None:
        """
        Handle budget block by logging, auditing, and raising exception.

        Called when a tenant attempts LLM call but budget is exceeded.
        Logs event, creates audit entry, and raises BudgetExceededError.

        Args:
            tenant_id: Tenant identifier
            current_spend: Current spend in USD

        Raises:
            BudgetExceededError: Always raises to block execution

        Example:
            >>> budget_service = BudgetService(db)
            >>> exceeded, msg = await budget_service.check_budget_exceeded("acme-corp")
            >>> if exceeded:
            >>>     await budget_service.handle_budget_block("acme-corp", 550.00)
        """
        # Fetch tenant config for budget details
        stmt = select(TenantConfigModel).where(
            TenantConfigModel.tenant_id == tenant_id,
            TenantConfigModel.is_active == True,
        )
        result = await self.db.execute(stmt)
        tenant_config = result.scalar_one_or_none()

        if not tenant_config:
            raise ValueError(f"Tenant not found: {tenant_id}")

        max_budget = tenant_config.max_budget or 500.00
        grace_threshold = tenant_config.grace_threshold or 110

        # Log budget block event
        logger.warning(
            f"Budget block: tenant={tenant_id}, spend=${current_spend:.2f}, "
            f"max_budget=${max_budget:.2f}, grace_threshold={grace_threshold}%"
        )

        # Create audit log entry (will be handled by LLMService.log_audit_entry)
        from src.database.models import AuditLog

        audit_entry = AuditLog(
            user="system",
            operation="budget_block",
            details={
                "tenant_id": tenant_id,
                "current_spend": current_spend,
                "max_budget": max_budget,
                "grace_threshold": grace_threshold,
                "blocked_at": datetime.now(timezone.utc).isoformat(),
            },
            status="blocked",
        )
        self.db.add(audit_entry)
        await self.db.flush()

        # Raise BudgetExceededError with detailed message
        raise BudgetExceededError(
            tenant_id=tenant_id,
            current_spend=current_spend,
            max_budget=max_budget,
            grace_threshold=grace_threshold,
        )

    async def get_tenant_spend_from_litellm(self, tenant_id: str) -> TenantSpend:
        """
        Query LiteLLM /key/info API for real-time tenant spend and model breakdown.

        Retrieves current spend, max budget, and per-model spend from LiteLLM
        virtual key. Used by dashboard to display real-time cost visibility.

        Args:
            tenant_id: Tenant identifier

        Returns:
            TenantSpend: Real-time spend data with model breakdown

        Raises:
            ValueError: If tenant not found or has no virtual key
            Exception: If LiteLLM API call fails (logged and re-raised)

        Example:
            >>> budget_service = BudgetService(db)
            >>> spend = await budget_service.get_tenant_spend_from_litellm("acme-corp")
            >>> print(f"Spend: ${spend.current_spend}, Budget: ${spend.max_budget}")
            >>> for model in spend.models_breakdown:
            >>>     print(f"{model.model}: ${model.spend} ({model.percentage}%)")
        """
        # Fetch tenant config from database
        stmt = select(TenantConfigModel).where(
            TenantConfigModel.tenant_id == tenant_id,
            TenantConfigModel.is_active == True,
        )
        result = await self.db.execute(stmt)
        tenant_config = result.scalar_one_or_none()

        if not tenant_config:
            raise ValueError(f"Tenant not found or inactive: {tenant_id}")

        # Determine virtual key to use (BYOK takes precedence)
        virtual_key = None
        if tenant_config.byok_enabled and tenant_config.byok_virtual_key:
            virtual_key = tenant_config.byok_virtual_key
            logger.debug(f"Using BYOK virtual key for tenant {tenant_id}")
        elif tenant_config.litellm_virtual_key:
            virtual_key = tenant_config.litellm_virtual_key
            logger.debug(f"Using platform virtual key for tenant {tenant_id}")

        if not virtual_key:
            raise ValueError(
                f"No LiteLLM virtual key configured for tenant {tenant_id}. "
                "Configure BYOK or platform keys first."
            )

        # Get budget configuration
        max_budget = tenant_config.max_budget or 500.00
        budget_duration = tenant_config.budget_duration or "30d"
        budget_reset_at = (
            tenant_config.budget_reset_at.isoformat()
            if tenant_config.budget_reset_at
            else None
        )

        try:
            # Query LiteLLM /key/info endpoint for spend data
            headers = {
                "Authorization": f"Bearer {self.master_key}",
                "Content-Type": "application/json",
            }

            transport = httpx.AsyncHTTPTransport(retries=1)
            async with httpx.AsyncClient(
                transport=transport,
                timeout=self.TIMEOUT_CONFIG,
                follow_redirects=True,
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            ) as client:
                response = await client.get(
                    f"{self.litellm_proxy_url}/key/info",
                    headers=headers,
                    params={"key": virtual_key},
                )

                if response.status_code != 200:
                    logger.error(
                        f"Failed to fetch spend data from LiteLLM for tenant {tenant_id}: "
                        f"HTTP {response.status_code}"
                    )
                    raise Exception(
                        f"LiteLLM API returned {response.status_code}: {response.text}"
                    )

                data = response.json()
                info = data.get("info", {})
                current_spend = float(info.get("spend", 0.0))

                # Parse model breakdown from LiteLLM response
                models_breakdown = []
                litellm_models = info.get("models", [])

                if litellm_models and current_spend > 0:
                    # Calculate per-model percentages
                    for model_data in litellm_models:
                        if isinstance(model_data, dict):
                            model_name = model_data.get("model", "unknown")
                            spend = float(model_data.get("spend", 0.0))
                            requests = int(model_data.get("requests", 0))
                            percentage = (
                                (spend / current_spend * 100) if current_spend > 0 else 0
                            )

                            models_breakdown.append(
                                ModelSpend(
                                    model=model_name,
                                    spend=spend,
                                    percentage=percentage,
                                    requests=requests,
                                )
                            )

                    # Sort by spend descending (most expensive first)
                    models_breakdown.sort(key=lambda x: x.spend, reverse=True)

                # Calculate utilization percentage
                utilization_pct = (
                    (current_spend / max_budget * 100) if max_budget > 0 else 0
                )

                logger.debug(
                    f"Spend data retrieved for tenant {tenant_id}: "
                    f"${current_spend:.2f}/${max_budget:.2f} ({utilization_pct:.1f}%)"
                )

                return TenantSpend(
                    tenant_id=tenant_id,
                    current_spend=current_spend,
                    max_budget=max_budget,
                    utilization_pct=utilization_pct,
                    models_breakdown=models_breakdown,
                    last_updated=datetime.now(timezone.utc),
                    budget_duration=budget_duration,
                    budget_reset_at=budget_reset_at,
                )

        except Exception as e:
            logger.error(
                f"Error fetching spend data from LiteLLM for tenant {tenant_id}: {str(e)}"
            )
            raise
