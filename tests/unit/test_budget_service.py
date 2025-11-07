"""Unit tests for BudgetService (Story 8.10).

Tests budget status tracking, budget exceeded detection, and budget blocking
with comprehensive mocking of LiteLLM API calls and database operations.

Following Story 8.9 testing excellence pattern:
    - Comprehensive mocking (pytest-mock for AsyncSession, httpx)
    - 100% code path coverage
    - Edge cases (API failures, timeouts, empty values)
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.budget_service import BudgetService, BudgetStatus
from src.exceptions import BudgetExceededError


@pytest.fixture
def mock_db():
    """Mock AsyncSession for database operations."""
    db = AsyncMock()
    return db


@pytest.fixture
def budget_service(mock_db):
    """Create BudgetService instance with mocked dependencies."""
    with patch("src.services.budget_service.settings") as mock_settings:
        mock_settings.litellm_proxy_url = "http://litellm:4000"
        mock_settings.litellm_master_key = "sk-test-master-key"
        service = BudgetService(
            db=mock_db,
            litellm_proxy_url="http://litellm:4000",
            master_key="sk-test-master-key",
        )
        return service


class TestBudgetServiceInit:
    """Test BudgetService initialization."""

    def test_init_with_explicit_params(self, mock_db):
        """Test initialization with explicit URL and master key."""
        service = BudgetService(
            db=mock_db,
            litellm_proxy_url="http://custom:4000",
            master_key="sk-custom-key",
        )
        assert service.litellm_proxy_url == "http://custom:4000"
        assert service.master_key == "sk-custom-key"

    def test_init_strips_trailing_slash(self, mock_db):
        """Test that trailing slash is removed from URL."""
        service = BudgetService(
            db=mock_db,
            litellm_proxy_url="http://litellm:4000/",
            master_key="sk-test-key",
        )
        assert service.litellm_proxy_url == "http://litellm:4000"

    def test_init_missing_url_raises_error(self, mock_db):
        """Test that missing LiteLLM URL raises ValueError."""
        with patch("src.services.budget_service.settings") as mock_settings:
            mock_settings.litellm_proxy_url = None
            mock_settings.litellm_master_key = "sk-key"
            with pytest.raises(ValueError, match="LITELLM_PROXY_URL not configured"):
                BudgetService(db=mock_db, litellm_proxy_url=None, master_key="sk-key")

    def test_init_missing_master_key_raises_error(self, mock_db):
        """Test that missing master key raises ValueError."""
        with patch("src.services.budget_service.settings") as mock_settings:
            mock_settings.litellm_proxy_url = "http://litellm:4000"
            mock_settings.litellm_master_key = None
            with pytest.raises(ValueError, match="LITELLM_MASTER_KEY not configured"):
                BudgetService(db=mock_db, litellm_proxy_url="http://litellm:4000", master_key=None)


@pytest.mark.asyncio
class TestGetBudgetStatus:
    """Test get_budget_status method."""

    async def test_get_budget_status_success(self, budget_service, mock_db):
        """Test successful budget status retrieval."""
        # Mock database query
        mock_tenant = MagicMock()
        mock_tenant.max_budget = 500.00
        mock_tenant.alert_threshold = 80
        mock_tenant.grace_threshold = 110
        mock_tenant.budget_reset_at = datetime.now(timezone.utc) + timedelta(days=15)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tenant
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Mock LiteLLM API response
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"spend": 400.00}
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            status = await budget_service.get_budget_status("acme-corp")

            assert isinstance(status, BudgetStatus)
            assert status.tenant_id == "acme-corp"
            assert status.spend == 400.00
            assert status.max_budget == 500.00
            assert status.percentage_used == 80.0
            assert status.grace_remaining == 150.00  # (500 * 1.1) - 400 = 150
            assert status.is_blocked == False
            assert status.days_until_reset == 14  # timedelta.days truncates, 15 days future results in 14

    async def test_get_budget_status_tenant_not_found(self, budget_service, mock_db):
        """Test budget status query with nonexistent tenant."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="Tenant not found or inactive"):
            await budget_service.get_budget_status("nonexistent-tenant")

    async def test_get_budget_status_litellm_api_failure_failsafe(
        self, budget_service, mock_db
    ):
        """Test fail-safe behavior when LiteLLM API fails (allows execution)."""
        # Mock database query success
        mock_tenant = MagicMock()
        mock_tenant.max_budget = 500.00
        mock_tenant.alert_threshold = 80
        mock_tenant.grace_threshold = 110
        mock_tenant.budget_reset_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tenant
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Mock LiteLLM API failure
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("Connection timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            status = await budget_service.get_budget_status("acme-corp")

            # Fail-safe: Returns spend=0.0 to allow execution
            assert status.spend == 0.0
            assert status.percentage_used == 0.0
            assert status.is_blocked == False


@pytest.mark.asyncio
class TestCheckBudgetExceeded:
    """Test check_budget_exceeded method."""

    async def test_check_budget_exceeded_under_grace_threshold(
        self, budget_service, mock_db
    ):
        """Test budget check when under grace threshold (not exceeded)."""
        # Mock get_budget_status to return under-threshold status
        mock_status = BudgetStatus(
            tenant_id="acme-corp",
            spend=400.00,
            max_budget=500.00,
            percentage_used=80.0,
            grace_remaining=150.00,
            days_until_reset=15,
            alert_threshold=80,
            grace_threshold=110,
            is_blocked=False,
        )

        with patch.object(budget_service, "get_budget_status", return_value=mock_status):
            exceeded, message = await budget_service.check_budget_exceeded("acme-corp")

            assert exceeded == False
            assert message == ""

    async def test_check_budget_exceeded_at_grace_threshold(
        self, budget_service, mock_db
    ):
        """Test budget check at exactly grace threshold (110% = $550)."""
        mock_status = BudgetStatus(
            tenant_id="acme-corp",
            spend=550.00,
            max_budget=500.00,
            percentage_used=110.0,
            grace_remaining=0.00,
            days_until_reset=15,
            alert_threshold=80,
            grace_threshold=110,
            is_blocked=True,
        )

        with patch.object(budget_service, "get_budget_status", return_value=mock_status):
            exceeded, message = await budget_service.check_budget_exceeded("acme-corp")

            assert exceeded == True
            assert "Budget exceeded" in message
            assert "$550.00" in message
            assert "$500.00" in message
            assert "110%" in message

    async def test_check_budget_exceeded_api_failure_failsafe(
        self, budget_service, mock_db
    ):
        """Test fail-safe behavior when budget check fails (allows execution)."""
        with patch.object(
            budget_service, "get_budget_status", side_effect=Exception("API error")
        ):
            exceeded, message = await budget_service.check_budget_exceeded("acme-corp")

            # Fail-safe: Returns False to allow execution
            assert exceeded == False
            assert message == ""


@pytest.mark.asyncio
class TestHandleBudgetBlock:
    """Test handle_budget_block method."""

    async def test_handle_budget_block_raises_exception(self, budget_service, mock_db):
        """Test that budget block raises BudgetExceededError with audit log."""
        # Mock database query
        mock_tenant = MagicMock()
        mock_tenant.max_budget = 500.00
        mock_tenant.grace_threshold = 110

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tenant
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(BudgetExceededError) as exc_info:
            await budget_service.handle_budget_block("acme-corp", 550.00)

        # Verify exception details
        assert exc_info.value.tenant_id == "acme-corp"
        assert exc_info.value.current_spend == 550.00
        assert exc_info.value.max_budget == 500.00
        assert exc_info.value.grace_threshold == 110

        # Verify audit log was created
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()

    async def test_handle_budget_block_tenant_not_found(self, budget_service, mock_db):
        """Test budget block with nonexistent tenant."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="Tenant not found"):
            await budget_service.handle_budget_block("nonexistent-tenant", 550.00)


class TestBudgetStatus:
    """Test BudgetStatus dataclass."""

    def test_budget_status_creation(self):
        """Test BudgetStatus dataclass instantiation."""
        status = BudgetStatus(
            tenant_id="acme-corp",
            spend=450.00,
            max_budget=500.00,
            percentage_used=90.0,
            grace_remaining=100.00,
            days_until_reset=10,
            alert_threshold=80,
            grace_threshold=110,
            is_blocked=False,
        )

        assert status.tenant_id == "acme-corp"
        assert status.spend == 450.00
        assert status.max_budget == 500.00
        assert status.percentage_used == 90.0
        assert status.grace_remaining == 100.00
        assert status.days_until_reset == 10
        assert status.alert_threshold == 80
        assert status.grace_threshold == 110
        assert status.is_blocked == False
