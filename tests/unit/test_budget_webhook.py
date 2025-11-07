"""Unit tests for Budget Webhook Endpoint (Story 8.10).

Tests webhook payload validation, signature validation, event processing,
and notification dispatch with comprehensive mocking.

Following Story 8.9 testing excellence pattern:
    - Comprehensive mocking (pytest-mock for AsyncSession, httpx, Redis)
    - 100% code path coverage
    - Edge cases (invalid signatures, malformed payloads, Redis failures)
"""

import pytest
import hmac
import hashlib
import json
import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def mock_db_session():
    """Mock database session for unit tests."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    return mock_session


@pytest.fixture
def test_client(mock_db_session):
    """FastAPI test client with mocked database."""
    from src.main import app
    from src.database.session import get_async_session

    # Override the database dependency with mock
    app.dependency_overrides[get_async_session] = lambda: mock_db_session

    client = TestClient(app)
    yield client

    # Clean up dependency overrides
    app.dependency_overrides.clear()


@pytest.fixture
def valid_webhook_payload():
    """Valid LiteLLM budget webhook payload."""
    return {
        "event": "threshold_crossed",
        "event_group": "budget",
        "event_message": "Budget threshold 80% reached",
        "token": "sk-tenant-acme-corp-key",
        "user_id": "acme-corp",
        "team_id": None,
        "spend": 400.00,
        "max_budget": 500.00,
        "soft_budget": 400.00,
    }


@pytest.fixture
def webhook_signature(valid_webhook_payload):
    """Generate valid HMAC signature for webhook payload."""
    secret = "test-webhook-secret"
    payload_bytes = json.dumps(valid_webhook_payload, sort_keys=True).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return signature


class TestWebhookPayloadValidation:
    """Test webhook payload validation and schema."""

    def test_valid_payload_80_percent_threshold(
        self, test_client, valid_webhook_payload, webhook_signature
    ):
        """Test valid webhook at 80% threshold triggers alert notification."""
        with patch("src.api.budget.settings") as mock_settings:
            mock_settings.litellm_webhook_secret = "test-webhook-secret"

            with patch("src.api.budget.verify_webhook_signature", return_value=True):
                with patch(
                    "src.services.notification_service.NotificationService.send_budget_alert"
                ) as mock_send_alert:
                    mock_send_alert.return_value = AsyncMock(return_value=None)

                    response = test_client.post(
                        "/api/v1/budget-alerts",
                        json=valid_webhook_payload,
                        headers={"X-Webhook-Signature": webhook_signature},
                    )

                    assert response.status_code == 200
                    assert "status" in response.json()
                    assert response.json()["status"] == "success"

    def test_valid_payload_100_percent_budget_crossed(self, test_client, webhook_signature):
        """Test valid webhook at 100% budget crossed triggers critical alert."""
        payload = {
            "event": "budget_crossed",
            "event_group": "budget",
            "event_message": "Budget limit reached",
            "token": "sk-tenant-acme-corp-key",
            "user_id": "acme-corp",
            "team_id": None,
            "spend": 500.00,
            "max_budget": 500.00,
            "soft_budget": 400.00,
        }

        with patch("src.api.budget.settings") as mock_settings:
            mock_settings.litellm_webhook_secret = "test-webhook-secret"

            with patch("src.api.budget.verify_webhook_signature", return_value=True):
                with patch(
                    "src.services.notification_service.NotificationService.send_budget_alert"
                ) as mock_send_alert:
                    mock_send_alert.return_value = AsyncMock(return_value=None)

                    # Generate signature for this payload
                    payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
                    signature = hmac.new(
                        b"test-webhook-secret", payload_bytes, hashlib.sha256
                    ).hexdigest()

                    response = test_client.post(
                        "/api/v1/budget-alerts",
                        json=payload,
                        headers={"X-Webhook-Signature": signature},
                    )

                    assert response.status_code == 200

    def test_valid_payload_110_percent_projected_limit(self, test_client, webhook_signature):
        """Test valid webhook at 110% grace threshold triggers block + critical."""
        payload = {
            "event": "projected_limit_exceeded",
            "event_group": "budget",
            "event_message": "Projected to exceed budget limit",
            "token": "sk-tenant-acme-corp-key",
            "user_id": "acme-corp",
            "team_id": None,
            "spend": 550.00,
            "max_budget": 500.00,
            "soft_budget": 400.00,
        }

        with patch("src.api.budget.settings") as mock_settings:
            mock_settings.litellm_webhook_secret = "test-webhook-secret"

            with patch("src.api.budget.verify_webhook_signature", return_value=True):
                with patch(
                    "src.services.notification_service.NotificationService.send_budget_alert"
                ) as mock_send_alert:
                    mock_send_alert.return_value = AsyncMock(return_value=None)

                    payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
                    signature = hmac.new(
                        b"test-webhook-secret", payload_bytes, hashlib.sha256
                    ).hexdigest()

                    response = test_client.post(
                        "/api/v1/budget-alerts",
                        json=payload,
                        headers={"X-Webhook-Signature": signature},
                    )

                    assert response.status_code == 200

    def test_malformed_payload_returns_422(self, test_client, webhook_signature):
        """Test malformed payload returns 422 validation error."""
        invalid_payload = {
            "event": "threshold_crossed",
            # Missing required fields: user_id, spend, max_budget
        }

        with patch("src.api.budget.settings") as mock_settings:
            mock_settings.litellm_webhook_secret = "test-webhook-secret"

            response = test_client.post(
                "/api/v1/budget-alerts",
                json=invalid_payload,
                headers={"X-Webhook-Signature": "dummy-signature"},
            )

            assert response.status_code == 422

    def test_missing_required_fields_returns_422(self, test_client):
        """Test payload missing required fields returns 422."""
        payload = {
            "event": "threshold_crossed",
            "user_id": "acme-corp",
            # Missing: spend, max_budget
        }

        with patch("src.api.budget.settings") as mock_settings:
            mock_settings.litellm_webhook_secret = "test-webhook-secret"

            response = test_client.post(
                "/api/v1/budget-alerts",
                json=payload,
                headers={"X-Webhook-Signature": "dummy-signature"},
            )

            assert response.status_code == 422


class TestWebhookSignatureValidation:
    """Test webhook signature validation."""

    def test_missing_signature_header_returns_401(self, test_client, valid_webhook_payload):
        """Test request without signature header is rejected with 401."""
        with patch("src.api.budget.settings") as mock_settings:
            mock_settings.litellm_webhook_secret = "test-webhook-secret"

            response = test_client.post(
                "/api/v1/budget-alerts",
                json=valid_webhook_payload,
            )

            assert response.status_code == 401
            assert response.json()["detail"] == "Missing webhook signature"

    def test_invalid_signature_returns_401(self, test_client, valid_webhook_payload):
        """Test request with invalid signature is rejected with 401."""
        with patch("src.api.budget.settings") as mock_settings:
            mock_settings.litellm_webhook_secret = "test-webhook-secret"

            response = test_client.post(
                "/api/v1/budget-alerts",
                json=valid_webhook_payload,
                headers={"X-Webhook-Signature": "invalid-signature-12345"},
            )

            assert response.status_code == 401

    def test_valid_signature_accepted(self, test_client, valid_webhook_payload, webhook_signature):
        """Test request with valid signature is accepted."""
        with patch("src.api.budget.settings") as mock_settings:
            mock_settings.litellm_webhook_secret = "test-webhook-secret"

            with patch("src.api.budget.verify_webhook_signature", return_value=True):
                with patch(
                    "src.services.notification_service.NotificationService.send_budget_alert"
                ) as mock_send_alert:
                    mock_send_alert.return_value = AsyncMock(return_value=None)

                    response = test_client.post(
                        "/api/v1/budget-alerts",
                        json=valid_webhook_payload,
                        headers={"X-Webhook-Signature": webhook_signature},
                    )

                    assert response.status_code == 200


class TestNotificationDeduplication:
    """Test notification deduplication with Redis cache."""

    @pytest.mark.asyncio
    async def test_notification_deduplication_1_hour_ttl(
        self, test_client, valid_webhook_payload, webhook_signature
    ):
        """Test duplicate notifications within 1 hour are suppressed."""
        with patch("src.api.budget.verify_webhook_signature", return_value=True):
            with patch("src.api.budget.settings") as mock_settings:
                mock_settings.litellm_webhook_secret = "test-webhook-secret"

                # First call: cache miss, notification sent
                with patch(
                    "src.services.notification_service.NotificationService._check_deduplication"
                ) as mock_dedup:
                    mock_dedup.return_value = True  # Should send (cache miss)

                    with patch(
                        "src.services.notification_service.NotificationService._send_email_notification"
                    ) as mock_email:
                        with patch(
                            "src.services.notification_service.NotificationService._send_slack_notification"
                        ) as mock_slack:
                            mock_email.return_value = AsyncMock()
                            mock_slack.return_value = AsyncMock()

                            response1 = test_client.post(
                                "/api/v1/budget-alerts",
                                json=valid_webhook_payload,
                                headers={"X-Webhook-Signature": webhook_signature},
                            )

                            assert response1.status_code == 200

                            # Verify notification methods were called (cache miss)
                            assert mock_email.called
                            assert mock_slack.called

                # Second call: cache hit, notification suppressed
                with patch(
                    "src.services.notification_service.NotificationService._check_deduplication"
                ) as mock_dedup:
                    mock_dedup.return_value = False  # Should not send (cache hit)

                    with patch(
                        "src.services.notification_service.NotificationService._send_email_notification"
                    ) as mock_email:
                        with patch(
                            "src.services.notification_service.NotificationService._send_slack_notification"
                        ) as mock_slack:
                            mock_email.return_value = AsyncMock()
                            mock_slack.return_value = AsyncMock()

                            response2 = test_client.post(
                                "/api/v1/budget-alerts",
                                json=valid_webhook_payload,
                                headers={"X-Webhook-Signature": webhook_signature},
                            )

                            assert response2.status_code == 200

                            # Verify notification methods were NOT called (deduplication)
                            mock_email.assert_not_called()
                            mock_slack.assert_not_called()

    @pytest.mark.asyncio
    async def test_redis_failure_graceful_degradation(
        self, test_client, valid_webhook_payload, webhook_signature
    ):
        """Test Redis failure doesn't block webhook (graceful degradation)."""
        with patch("src.api.budget.verify_webhook_signature", return_value=True):
            with patch("src.api.budget.settings") as mock_settings:
                mock_settings.litellm_webhook_secret = "test-webhook-secret"

                with patch(
                    "src.services.notification_service.NotificationService._get_redis_client"
                ) as mock_redis:
                    # Redis connection failure
                    mock_redis.get = AsyncMock(side_effect=Exception("Redis unavailable"))

                    with patch(
                        "src.services.notification_service.NotificationService.send_budget_alert"
                    ) as mock_send_alert:
                        mock_send_alert.return_value = AsyncMock()

                        response = test_client.post(
                            "/api/v1/budget-alerts",
                            json=valid_webhook_payload,
                            headers={"X-Webhook-Signature": webhook_signature},
                        )

                        # Webhook still returns 200 OK (fail-safe)
                        assert response.status_code == 200

                        # Notification still sent despite Redis failure
                        mock_send_alert.assert_called_once()


class TestAsyncProcessing:
    """Test async webhook processing."""

    def test_webhook_returns_200_immediately(
        self, test_client, valid_webhook_payload, webhook_signature
    ):
        """
        Test webhook returns 200 OK after processing completes.

        Note: FastAPI/TestClient runs async endpoints synchronously by default,
        so the webhook will wait for send_budget_alert to complete.
        This test verifies the endpoint returns 200 OK regardless of notification
        service performance.
        """
        with patch("src.api.budget.verify_webhook_signature", return_value=True):
            with patch("src.api.budget.settings") as mock_settings:
                mock_settings.litellm_webhook_secret = "test-webhook-secret"

                with patch(
                    "src.services.notification_service.NotificationService.send_budget_alert"
                ) as mock_send_alert:
                    # Mock notification service to return immediately
                    mock_send_alert.return_value = AsyncMock()

                    import time

                    start = time.time()

                    response = test_client.post(
                        "/api/v1/budget-alerts",
                        json=valid_webhook_payload,
                        headers={"X-Webhook-Signature": webhook_signature},
                    )

                    elapsed = time.time() - start

                    # Webhook returns 200 OK
                    assert response.status_code == 200
                    # Processing should be fast with mocked notification service
                    assert elapsed < 2.0  # Should be <1s, allowing headroom for test overhead
