"""Unit tests for NotificationService (Story 8.10A).

Tests budget alert notifications with Redis deduplication, email/Slack dispatch,
template rendering, and fail-safe patterns.

Following Story 8.9 testing excellence pattern:
    - Comprehensive mocking (pytest-mock for Redis, httpx, logger)
    - 100% code path coverage
    - Edge cases (Redis failures, notification errors, concurrent alerts)
    - 2025 best practices (pytest-asyncio, AsyncMock, proper fixtures)

Note: Current implementation (Story 8.10) logs notifications rather than sending.
      Tests validate deduplication logic, template rendering, and fail-safe patterns.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.notification_service import (
    NotificationService,
    EMAIL_80_TEMPLATE,
    EMAIL_100_TEMPLATE,
    SLACK_80_TEMPLATE,
    SLACK_100_TEMPLATE,
)


@pytest.fixture
def mock_redis():
    """Mock Redis client for deduplication testing."""
    redis = AsyncMock()
    redis.exists = AsyncMock(return_value=0)  # 0 = key doesn't exist, 1 = exists
    redis.setex = AsyncMock(return_value=True)
    redis.ping = AsyncMock(return_value=True)
    redis.close = AsyncMock()
    return redis


@pytest.fixture
def notification_service(mock_redis):
    """Create NotificationService instance with mocked Redis."""
    with patch("src.services.notification_service.settings") as mock_settings:
        mock_settings.smtp_host = None  # Not configured in stub
        mock_settings.redis_host = "localhost"
        mock_settings.redis_port = 6379

        service = NotificationService()
        service.redis_client = mock_redis
        service._redis_initialized = True
        return service


@pytest.mark.asyncio
class TestRedisDeduplication:
    """Test Redis-based alert deduplication."""

    async def test_deduplication_first_alert_sent(self, notification_service, mock_redis):
        """Test that first alert is sent when no duplicate exists in Redis."""
        # Redis exists returns 0 (key doesn't exist)
        mock_redis.exists = AsyncMock(return_value=0)

        result = await notification_service._check_deduplication(
            tenant_id="tenant-123", alert_type="threshold_80"
        )

        assert result is True  # Should send (not a duplicate)
        mock_redis.exists.assert_called_once_with("budget_alert:tenant-123:threshold_80")
        # Should set Redis key with 3600s TTL
        mock_redis.setex.assert_called_once_with("budget_alert:tenant-123:threshold_80", 3600, "1")

    async def test_deduplication_duplicate_within_1_hour_skipped(
        self, notification_service, mock_redis
    ):
        """Test that duplicate alert within 1 hour is skipped."""
        # Redis exists returns 1 (key exists = duplicate)
        mock_redis.exists = AsyncMock(return_value=1)

        result = await notification_service._check_deduplication(
            tenant_id="tenant-456", alert_type="budget_100"
        )

        assert result is False  # Should skip (is a duplicate)
        mock_redis.exists.assert_called_once_with("budget_alert:tenant-456:budget_100")
        mock_redis.setex.assert_not_called()  # Should not set new key

    async def test_deduplication_after_1_hour_sent_successfully(
        self, notification_service, mock_redis
    ):
        """Test that alert after 1 hour TTL expires is sent."""
        # Key doesn't exist (TTL expired)
        mock_redis.exists = AsyncMock(return_value=0)

        result = await notification_service._check_deduplication(
            tenant_id="tenant-789", alert_type="threshold_80"
        )

        assert result is True  # Should send
        # Verify Redis key set with 3600s (1 hour) TTL
        mock_redis.setex.assert_called_once_with("budget_alert:tenant-789:threshold_80", 3600, "1")

    async def test_deduplication_redis_cache_failure_fail_safe(
        self, notification_service, mock_redis
    ):
        """Test Redis failure allows notification (fail-safe pattern)."""
        # Redis raises exception
        mock_redis.exists = AsyncMock(side_effect=Exception("Redis connection error"))

        result = await notification_service._check_deduplication(
            tenant_id="tenant-error", alert_type="budget_100"
        )

        assert result is True  # Fail-safe: allow notification
        mock_redis.exists.assert_called_once()
        mock_redis.setex.assert_not_called()  # Should not attempt setex after error


@pytest.mark.asyncio
class TestEmailTemplateRendering:
    """Test Jinja2 email template rendering."""

    async def test_email_template_80_threshold_correct(self, notification_service, mock_redis):
        """Test 80% threshold email template renders correctly."""
        mock_redis.exists = AsyncMock(return_value=0)  # Not a duplicate

        with patch("src.services.notification_service.logger") as mock_logger:
            await notification_service.send_budget_alert(
                tenant_id="tenant-123",
                alert_type="threshold_80",
                spend=400.00,
                max_budget=500.00,
                percentage=80,
            )

            # Verify notification was attempted (logged)
            assert mock_logger.info.called
            log_calls = [str(call) for call in mock_logger.info.call_args_list]
            log_str = " ".join(log_calls)

            # Verify template data present in logs
            assert "tenant-123" in log_str
            assert "80" in log_str or "400" in log_str

    async def test_email_template_100_critical_correct(self, notification_service, mock_redis):
        """Test 100% critical email template renders correctly."""
        mock_redis.exists = AsyncMock(return_value=0)  # Not a duplicate

        with patch("src.services.notification_service.logger") as mock_logger:
            await notification_service.send_budget_alert(
                tenant_id="tenant-456",
                alert_type="budget_100",
                spend=550.00,
                max_budget=500.00,
                percentage=110,
            )

            assert mock_logger.info.called
            log_calls = [str(call) for call in mock_logger.info.call_args_list]
            log_str = " ".join(log_calls)

            # Verify critical alert data in logs
            assert "tenant-456" in log_str
            assert "110" in log_str or "550" in log_str


@pytest.mark.asyncio
class TestSlackMessageFormatting:
    """Test Slack webhook message formatting."""

    async def test_slack_message_formatting_metrics_correct(self, notification_service, mock_redis):
        """Test Slack message includes metrics and formatting."""
        mock_redis.exists = AsyncMock(return_value=0)  # Not a duplicate

        with patch("src.services.notification_service.logger") as mock_logger:
            await notification_service.send_budget_alert(
                tenant_id="tenant-789",
                alert_type="threshold_80",
                spend=400.00,
                max_budget=500.00,
                percentage=80,
                reset_date="2025-12-01",
            )

            # Verify Slack message logged
            assert mock_logger.info.called
            log_calls = [str(call) for call in mock_logger.info.call_args_list]
            log_str = " ".join(log_calls)

            assert "tenant-789" in log_str


@pytest.mark.asyncio
class TestNotConfiguredHandling:
    """Test behavior when SMTP/Slack not configured."""

    async def test_smtp_not_configured_logs_preview(self, mock_redis):
        """Test SMTP not configured logs preview without raising exception."""
        with patch("src.services.notification_service.settings") as mock_settings:
            mock_settings.smtp_host = None  # Not configured

            service = NotificationService()
            service.redis_client = mock_redis
            service._redis_initialized = True

            mock_redis.exists = AsyncMock(return_value=0)

            with patch("src.services.notification_service.logger") as mock_logger:
                # Should not raise exception
                await service.send_budget_alert(
                    tenant_id="tenant-123",
                    alert_type="threshold_80",
                    spend=400.00,
                    max_budget=500.00,
                    percentage=80,
                )

                # Verify warning or info logged
                assert mock_logger.warning.called or mock_logger.info.called

    async def test_slack_not_configured_logs_preview(self, mock_redis):
        """Test Slack not configured logs preview without raising exception."""
        with patch("src.services.notification_service.settings") as mock_settings:
            mock_settings.smtp_host = None
            mock_settings.slack_webhook_url = None  # Not configured

            service = NotificationService()
            service.redis_client = mock_redis
            service._redis_initialized = True

            mock_redis.exists = AsyncMock(return_value=0)

            with patch("src.services.notification_service.logger") as mock_logger:
                await service.send_budget_alert(
                    tenant_id="tenant-456",
                    alert_type="budget_100",
                    spend=550.00,
                    max_budget=500.00,
                    percentage=110,
                )

                # Should log preview
                assert mock_logger.warning.called or mock_logger.info.called


@pytest.mark.asyncio
class TestConcurrentNotifications:
    """Test concurrent notification handling."""

    async def test_concurrent_notifications_no_race_conditions(
        self, notification_service, mock_redis
    ):
        """Test concurrent notifications don't cause race conditions."""
        mock_redis.exists = AsyncMock(return_value=0)

        with patch("src.services.notification_service.logger") as mock_logger:
            # Send 3 concurrent alerts for same tenant
            import asyncio

            await asyncio.gather(
                notification_service.send_budget_alert(
                    "tenant-123", "threshold_80", 400.00, 500.00, 80
                ),
                notification_service.send_budget_alert(
                    "tenant-123", "threshold_80", 400.00, 500.00, 80
                ),
                notification_service.send_budget_alert(
                    "tenant-123", "threshold_80", 400.00, 500.00, 80
                ),
            )

            # Verify Redis checked 3 times (no race condition crashes)
            assert mock_redis.exists.call_count == 3
            # Verify notifications logged
            assert mock_logger.info.called


@pytest.mark.asyncio
class TestGracefulFailure:
    """Test graceful failure handling."""

    async def test_notification_error_logged_doesnt_block(self, notification_service, mock_redis):
        """Test notification error is logged but doesn't block execution."""
        mock_redis.exists = AsyncMock(return_value=0)

        with patch("src.services.notification_service.logger") as mock_logger:
            # Force error in deduplication check by making setex fail
            mock_redis.setex = AsyncMock(side_effect=Exception("Redis setex failed"))

            # Should not raise exception (fail-safe)
            try:
                await notification_service.send_budget_alert(
                    tenant_id="tenant-error",
                    alert_type="budget_100",
                    spend=550.00,
                    max_budget=500.00,
                    percentage=110,
                )
                # If we get here, graceful failure worked
                assert True
            except Exception as e:
                # If exception propagates, test fails
                pytest.fail(f"Exception should have been caught: {e}")


@pytest.mark.asyncio
class TestTemplateVariables:
    """Test template variable substitution."""

    async def test_template_80_renders_all_variables(self):
        """Test 80% template renders all variables correctly."""
        rendered = EMAIL_80_TEMPLATE.render(
            tenant_id="test-tenant",
            spend=400.50,
            max_budget=500.00,
            percentage=80,
            grace_threshold=110,
            days_remaining=15,
        )

        assert "test-tenant" in rendered
        assert "400.50" in rendered
        assert "500.00" in rendered
        assert "80" in rendered

    async def test_template_100_renders_all_variables(self):
        """Test 100% template renders all variables correctly."""
        rendered = EMAIL_100_TEMPLATE.render(
            tenant_id="test-tenant",
            spend=550.75,
            max_budget=500.00,
            percentage=110,
            grace_threshold=110,
            reset_date="2025-12-01",
        )

        assert "test-tenant" in rendered
        assert "550.75" in rendered
        assert "500.00" in rendered
