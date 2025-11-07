"""Integration tests for Budget Enforcement Workflow (Story 8.10).

Tests end-to-end budget enforcement scenarios including webhook processing,
notification dispatch, budget blocking, and fail-safe behavior.

Architecture:
    LiteLLM → Webhook Endpoint → BudgetService → Notifications
    → Agent Execution (budget check) → LLMService

Test Scenarios (Story 8.10A):
    1. Webhook → Alert notification at 80% threshold
    2. Webhook → Critical alert at 100% threshold
    3. Budget blocking → Agent execution fails at 110%
    4. Notification deduplication (1-hour cache)
    5. Fail-safe behavior (API failures don't block execution)
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call
from fastapi.testclient import TestClient

from src.main import app  # FastAPI app for integration testing
from src.services.budget_service import BudgetStatus
from src.services.llm_service import LLMService
from src.exceptions import BudgetExceededError
from src.database.session import get_async_session


class TestBudgetWebhookToNotificationWorkflow:
    """Test webhook-to-notification workflow (AC3, AC4)."""

    def test_webhook_at_80_percent_triggers_alert_notification(self):
        """
        Test: LiteLLM sends webhook at 80% → endpoint processes → notification sent.

        Story 8.10 AC4: "at 80%, send email/Slack notification to tenant admin"
        """
        # Arrange: Mock dependencies
        webhook_payload = {
            "event": "threshold_crossed",
            "event_group": "user",
            "event_message": "Budget threshold 80% reached",
            "token": "sk-tenant-acme-key",
            "user_id": "acme-corp",
            "spend": 400.00,
            "max_budget": 500.00,
        }

        with patch("src.api.budget.settings") as mock_settings:
            mock_settings.litellm_webhook_secret = "test-secret"

            with patch(
                "src.services.notification_service.NotificationService.send_budget_alert"
            ) as mock_send_alert:
                mock_send_alert.return_value = AsyncMock()

                with patch(
                    "src.services.notification_service.NotificationService._get_redis_client"
                ) as mock_redis:
                    mock_redis.get = AsyncMock(return_value=None)  # No cached alert
                    mock_redis.setex = AsyncMock()

                    # Act: Send webhook
                    # Generate valid signature
                    import hmac
                    import hashlib
                    import json

                    payload_str = json.dumps(webhook_payload, sort_keys=True)
                    signature = hmac.new(
                        b"test-secret",
                        payload_str.encode("utf-8"),
                        hashlib.sha256,
                    ).hexdigest()

                    client = TestClient(app)
                    response = client.post(
                        "/api/v1/budget-alerts",
                        json=webhook_payload,
                        headers={"X-Webhook-Signature": signature},
                    )

                    # Assert: Webhook accepted
                    assert response.status_code == 200
                    assert response.json()["status"] == "success"

                    # Assert: Notification was sent
                    mock_send_alert.assert_called_once()
                    call_args = mock_send_alert.call_args
                    assert call_args[1]["tenant_id"] == "acme-corp"
                    assert call_args[1]["alert_type"] == "threshold_80"

                    # Note: Redis caching is mocked at _check_deduplication level in unit tests
                    # Integration tests focus on end-to-end workflow

    def test_webhook_at_100_percent_triggers_critical_alert(self):
        """
        Test: LiteLLM sends webhook at 100% → critical alert notification sent.

        Story 8.10 AC4: "at 100%+: Send critical alert, log event"
        """
        webhook_payload = {
            "event": "budget_crossed",
            "event_group": "user",
            "event_message": "Budget limit reached",
            "token": "sk-tenant-acme-key",
            "user_id": "acme-corp",
            "spend": 500.00,
            "max_budget": 500.00,
        }

        with patch("src.api.budget.settings") as mock_settings:
            mock_settings.litellm_webhook_secret = "test-secret"

            with patch(
                "src.services.notification_service.NotificationService.send_budget_alert"
            ) as mock_send_alert:
                mock_send_alert.return_value = AsyncMock()

                with patch(
                    "src.services.notification_service.NotificationService._get_redis_client"
                ) as mock_redis:
                    mock_redis.get = AsyncMock(return_value=None)
                    mock_redis.setex = AsyncMock()

                    with patch("src.api.budget.db") as mock_db:
                        mock_db.add = MagicMock()
                        mock_db.flush = AsyncMock()

                        import hmac
                        import hashlib
                        import json

                        payload_str = json.dumps(webhook_payload, sort_keys=True)
                        signature = hmac.new(
                            b"test-secret",
                            payload_str.encode("utf-8"),
                            hashlib.sha256,
                        ).hexdigest()

                        client = TestClient(app)
                        response = client.post(
                            "/api/v1/budget-alerts",
                            json=webhook_payload,
                            headers={"X-Webhook-Signature": signature},
                        )

                        assert response.status_code == 200

                        # Assert: Critical notification sent
                        mock_send_alert.assert_called_once()
                        call_args = mock_send_alert.call_args
                        assert "critical" in call_args[0][1].lower()  # alert_type

                        # Assert: Event logged to audit_log
                        assert mock_db.add.called

    def test_notification_deduplication_1_hour_cache(self):
        """
        Test: Duplicate webhook within 1 hour doesn't send duplicate notification.

        Story 8.10 AC4 + Constraint C6: "Notification deduplication 1-hour TTL"
        """
        webhook_payload = {
            "event": "threshold_crossed",
            "event_group": "user",
            "event_message": "Budget threshold reached",
            "token": "sk-tenant-acme-key",
            "user_id": "acme-corp",
            "spend": 400.00,
            "max_budget": 500.00,
        }

        with patch("src.api.budget.settings") as mock_settings:
            mock_settings.litellm_webhook_secret = "test-secret"

            with patch(
                "src.services.notification_service.NotificationService.send_budget_alert"
            ) as mock_send_alert:
                mock_send_alert.return_value = AsyncMock()

                with patch(
                    "src.services.notification_service.NotificationService._get_redis_client"
                ) as mock_redis:
                    # First webhook: cache miss
                    mock_redis.get = AsyncMock(return_value=None)
                    mock_redis.setex = AsyncMock()

                    import hmac
                    import hashlib
                    import json

                    payload_str = json.dumps(webhook_payload, sort_keys=True)
                    signature = hmac.new(
                        b"test-secret",
                        payload_str.encode("utf-8"),
                        hashlib.sha256,
                    ).hexdigest()

                    # First webhook
                    client = TestClient(app)
                    response1 = client.post(
                        "/api/v1/budget-alerts",
                        json=webhook_payload,
                        headers={"X-Webhook-Signature": signature},
                    )

                    assert response1.status_code == 200
                    assert mock_send_alert.call_count == 1

                    # Second webhook: cache hit (duplicate)
                    mock_redis.get = AsyncMock(return_value=b"1")

                    response2 = client.post(
                        "/api/v1/budget-alerts",
                        json=webhook_payload,
                        headers={"X-Webhook-Signature": signature},
                    )

                    assert response2.status_code == 200

                    # Assert: Notification sent only once (deduplication worked)
                    assert mock_send_alert.call_count == 1  # Still 1, not 2


class TestBudgetEnforcementInAgentExecution:
    """Test budget blocking in agent execution (AC5)."""

    @pytest.mark.asyncio
    async def test_agent_execution_blocked_at_110_percent_grace_threshold(self):
        """
        Test: Agent call fails gracefully when budget at 110% (grace threshold).

        Story 8.10 AC5: "at 110%, LiteLLM blocks requests, agent calls fail
        gracefully with 'budget exceeded' error"
        """
        # Arrange: Mock budget status at 110% (blocked)
        mock_status = BudgetStatus(
            tenant_id="acme-corp",
            spend=550.00,
            max_budget=500.00,
            percentage_used=110.0,
            grace_remaining=0.00,
            days_until_reset=10,
            alert_threshold=80,
            grace_threshold=110,
            is_blocked=True,
        )

        with patch("src.services.budget_service.BudgetService") as MockBudgetService:
            mock_budget_service = MockBudgetService.return_value
            mock_budget_service.check_budget_exceeded = AsyncMock(
                return_value=(True, "Budget exceeded: $550.00 / $500.00 (110%)")
            )

            llm_service = LLMService(db=AsyncMock())

            # Act & Assert: Agent execution raises BudgetExceededError
            with pytest.raises(BudgetExceededError) as exc_info:
                await llm_service.get_llm_client_for_tenant("acme-corp")

            assert exc_info.value.tenant_id == "acme-corp"
            assert exc_info.value.current_spend == 550.00
            assert exc_info.value.max_budget == 500.00

    @pytest.mark.asyncio
    async def test_agent_execution_allowed_under_grace_threshold(self):
        """
        Test: Agent call succeeds when budget under 110% grace threshold.

        Validates that budget check doesn't block execution when within limits.
        """
        # Arrange: Mock budget status at 90% (under threshold)
        with patch("src.services.budget_service.BudgetService") as MockBudgetService:
            mock_budget_service = MockBudgetService.return_value
            mock_budget_service.check_budget_exceeded = AsyncMock(return_value=(False, ""))

            with patch("src.services.llm_service.settings") as mock_settings:
                mock_settings.litellm_proxy_url = "http://litellm:4000"
                mock_settings.litellm_master_key = "sk-master-key"

                with patch("src.database.models.TenantConfig") as MockTenantConfig:
                    mock_tenant = MagicMock()
                    mock_tenant.litellm_virtual_key = "sk-tenant-acme-key"
                    MockTenantConfig.return_value = mock_tenant

                    llm_service = LLMService(db=AsyncMock())

                    # Act: Get LLM client (should succeed)
                    client = await llm_service.get_llm_client_for_tenant("acme-corp")

                    # Assert: Client returned successfully
                    assert client is not None


class TestBudgetFailSafeBehavior:
    """Test fail-safe behavior when budget checks fail (AC5)."""

    @pytest.mark.asyncio
    async def test_budget_check_failure_allows_execution_failsafe(self):
        """
        Test: Budget check API failure doesn't block agent execution (fail-safe).

        Story 8.10 Constraint C7: "Graceful degradation - budget check failures
        allow execution (fail-safe)"
        """
        # Arrange: Mock budget service API failure
        with patch("src.services.budget_service.BudgetService") as MockBudgetService:
            mock_budget_service = MockBudgetService.return_value
            mock_budget_service.check_budget_exceeded = AsyncMock(
                side_effect=Exception("LiteLLM API timeout")
            )

            with patch("src.services.llm_service.settings") as mock_settings:
                mock_settings.litellm_proxy_url = "http://litellm:4000"
                mock_settings.litellm_master_key = "sk-master-key"

                with patch("src.database.models.TenantConfig") as MockTenantConfig:
                    mock_tenant = MagicMock()
                    mock_tenant.litellm_virtual_key = "sk-tenant-acme-key"
                    MockTenantConfig.return_value = mock_tenant

                    llm_service = LLMService(db=AsyncMock())

                    # Act: Get LLM client (should succeed despite budget check failure)
                    client = await llm_service.get_llm_client_for_tenant("acme-corp")

                    # Assert: Client returned (fail-safe allowed execution)
                    assert client is not None

    def test_redis_failure_graceful_degradation_no_deduplication(self):
        """
        Test: Redis failure doesn't block webhook, but deduplication disabled.

        Validates graceful degradation when Redis is unavailable.
        """
        webhook_payload = {
            "event": "threshold_crossed",
            "event_group": "user",
            "event_message": "Budget threshold reached",
            "token": "sk-tenant-acme-key",
            "user_id": "acme-corp",
            "spend": 400.00,
            "max_budget": 500.00,
        }

        with patch("src.api.budget.settings") as mock_settings:
            mock_settings.litellm_webhook_secret = "test-secret"

            with patch(
                "src.services.notification_service.NotificationService.send_budget_alert"
            ) as mock_send_alert:
                mock_send_alert.return_value = AsyncMock()

                with patch(
                    "src.services.notification_service.NotificationService._get_redis_client"
                ) as mock_redis:
                    # Redis connection failure
                    mock_redis.get = AsyncMock(side_effect=Exception("Redis unavailable"))
                    mock_redis.setex = AsyncMock()

                    import hmac
                    import hashlib
                    import json

                    payload_str = json.dumps(webhook_payload, sort_keys=True)
                    signature = hmac.new(
                        b"test-secret",
                        payload_str.encode("utf-8"),
                        hashlib.sha256,
                    ).hexdigest()

                    client = TestClient(app)
                    response = client.post(
                        "/api/v1/budget-alerts",
                        json=webhook_payload,
                        headers={"X-Webhook-Signature": signature},
                    )

                    # Assert: Webhook still returns 200 OK (graceful)
                    assert response.status_code == 200

                    # Assert: Notification still sent despite Redis failure
                    mock_send_alert.assert_called_once()
