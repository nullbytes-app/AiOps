"""
Unit tests for execution details API endpoint.

Tests cover successful retrieval, tenant isolation, error handling,
sensitive data masking, and performance requirements.
"""

import time
from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.executions import get_execution_details
from src.database.models import AgentTestExecution
from src.schemas.execution import ExecutionDetailResponse


class TestSuccessfulRetrieval:
    """Tests for successful execution retrieval (AC1)."""

    @pytest.mark.asyncio
    async def test_get_execution_success(
        self, async_db_session: AsyncSession, mock_tenant_id: str
    ):
        """Test successful retrieval of execution details."""
        # Arrange
        execution_id = uuid4()
        agent_id = uuid4()
        mock_execution = MagicMock(spec=AgentTestExecution)
        mock_execution.id = execution_id
        mock_execution.agent_id = agent_id
        mock_execution.tenant_id = mock_tenant_id
        mock_execution.payload = {"test": "input"}
        mock_execution.execution_trace = {"steps": [{"step": 1, "action": "test"}]}
        mock_execution.status = "success"
        mock_execution.execution_time = {"total_duration_ms": 1500}
        mock_execution.created_at = datetime.now(timezone.utc)
        mock_execution.errors = None

        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_execution

        with patch.object(
            async_db_session, "execute", return_value=mock_result
        ) as mock_execute:
            # Act
            response = await get_execution_details(
                execution_id=execution_id,
                tenant_id=mock_tenant_id,
                db=async_db_session,
            )

            # Assert
            assert isinstance(response, ExecutionDetailResponse)
            assert response.id == execution_id
            assert response.agent_id == agent_id
            assert response.tenant_id == mock_tenant_id
            assert response.status == "completed"  # Normalized from DB "success"
            assert response.execution_time == 1500
            assert response.error_message is None
            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_execution_with_error(
        self, async_db_session: AsyncSession, mock_tenant_id: str
    ):
        """Test retrieval of failed execution with error message."""
        # Arrange
        execution_id = uuid4()
        agent_id = uuid4()
        error_message = "Tool invocation failed: timeout"
        mock_execution = MagicMock(spec=AgentTestExecution)
        mock_execution.id = execution_id
        mock_execution.agent_id = agent_id
        mock_execution.tenant_id = mock_tenant_id
        mock_execution.payload = {"test": "input"}
        mock_execution.execution_trace = {"steps": []}
        mock_execution.status = "failed"
        mock_execution.execution_time = {"total_duration_ms": 2000}
        mock_execution.created_at = datetime.now(timezone.utc)
        mock_execution.errors = {"message": error_message, "type": "TimeoutError"}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_execution

        with patch.object(async_db_session, "execute", return_value=mock_result):
            # Act
            response = await get_execution_details(
                execution_id=execution_id,
                tenant_id=mock_tenant_id,
                db=async_db_session,
            )

            # Assert
            assert response.status == "failed"
            assert response.error_message == error_message


class TestNotFoundHandling:
    """Tests for non-existent execution handling (AC3)."""

    @pytest.mark.asyncio
    async def test_get_execution_not_found(
        self, async_db_session: AsyncSession, mock_tenant_id: str
    ):
        """Test 404 response when execution doesn't exist."""
        # Arrange
        execution_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        with patch.object(async_db_session, "execute", return_value=mock_result):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_execution_details(
                    execution_id=execution_id,
                    tenant_id=mock_tenant_id,
                    db=async_db_session,
                )

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert exc_info.value.detail == "Execution not found"


class TestTenantIsolation:
    """Tests for tenant isolation and cross-tenant access prevention (AC4)."""

    @pytest.mark.asyncio
    async def test_cross_tenant_access_forbidden(
        self, async_db_session: AsyncSession, mock_tenant_id: str
    ):
        """Test 403 response when accessing execution from different tenant."""
        # Arrange
        execution_id = uuid4()
        other_tenant_id = "other-tenant-123"
        mock_execution = MagicMock(spec=AgentTestExecution)
        mock_execution.id = execution_id
        mock_execution.tenant_id = other_tenant_id

        # First query (with tenant filter) returns None
        mock_result_none = MagicMock()
        mock_result_none.scalar_one_or_none.return_value = None

        # Second query (without tenant filter) returns execution from different tenant
        mock_result_found = MagicMock()
        mock_result_found.scalar_one_or_none.return_value = mock_execution

        with patch.object(
            async_db_session,
            "execute",
            side_effect=[mock_result_none, mock_result_found],
        ):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_execution_details(
                    execution_id=execution_id,
                    tenant_id=mock_tenant_id,  # Different tenant
                    db=async_db_session,
                )

            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "Forbidden" in exc_info.value.detail


class TestSensitiveDataMasking:
    """Tests for sensitive data masking in responses (AC5)."""

    @pytest.mark.asyncio
    async def test_api_key_masking_in_payload(
        self, async_db_session: AsyncSession, mock_tenant_id: str
    ):
        """Test that API keys in payload are masked."""
        # Arrange
        execution_id = uuid4()
        mock_execution = MagicMock(spec=AgentTestExecution)
        mock_execution.id = execution_id
        mock_execution.agent_id = uuid4()
        mock_execution.tenant_id = mock_tenant_id
        mock_execution.payload = {
            "api_key": "sk-1234567890abcdef1234567890abcdef",
            "data": "test",
        }
        mock_execution.execution_trace = {"steps": []}
        mock_execution.status = "success"
        mock_execution.execution_time = {"total_duration_ms": 100}
        mock_execution.created_at = datetime.now(timezone.utc)
        mock_execution.errors = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_execution

        with patch.object(async_db_session, "execute", return_value=mock_result):
            # Act
            response = await get_execution_details(
                execution_id=execution_id,
                tenant_id=mock_tenant_id,
                db=async_db_session,
            )

            # Assert - API key should be masked
            assert "sk-1234567890abcdef1234567890abcdef" not in str(
                response.input_data
            )
            assert response.input_data["api_key"] == "***"
            assert response.input_data["data"] == "test"  # Non-sensitive data unchanged

    @pytest.mark.asyncio
    async def test_password_masking_in_trace(
        self, async_db_session: AsyncSession, mock_tenant_id: str
    ):
        """Test that passwords in execution trace are masked."""
        # Arrange
        execution_id = uuid4()
        mock_execution = MagicMock(spec=AgentTestExecution)
        mock_execution.id = execution_id
        mock_execution.agent_id = uuid4()
        mock_execution.tenant_id = mock_tenant_id
        mock_execution.payload = {}
        mock_execution.execution_trace = {
            "steps": [
                {
                    "tool": "database_query",
                    "input": {"password": "super_secret_password"},
                }
            ]
        }
        mock_execution.status = "success"
        mock_execution.execution_time = {"total_duration_ms": 100}
        mock_execution.created_at = datetime.now(timezone.utc)
        mock_execution.errors = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_execution

        with patch.object(async_db_session, "execute", return_value=mock_result):
            # Act
            response = await get_execution_details(
                execution_id=execution_id,
                tenant_id=mock_tenant_id,
                db=async_db_session,
            )

            # Assert - Password should be masked
            assert "super_secret_password" not in str(response.output_data)
            step = response.output_data["steps"][0]
            assert step["input"]["password"] == "***"

    @pytest.mark.asyncio
    async def test_bearer_token_masking(
        self, async_db_session: AsyncSession, mock_tenant_id: str
    ):
        """Test that Bearer tokens in strings are masked."""
        # Arrange
        execution_id = uuid4()
        mock_execution = MagicMock(spec=AgentTestExecution)
        mock_execution.id = execution_id
        mock_execution.agent_id = uuid4()
        mock_execution.tenant_id = mock_tenant_id
        mock_execution.payload = {}
        mock_execution.execution_trace = {
            "headers": "Authorization: Bearer abc123def456ghi789"
        }
        mock_execution.status = "success"
        mock_execution.execution_time = {"total_duration_ms": 100}
        mock_execution.created_at = datetime.now(timezone.utc)
        mock_execution.errors = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_execution

        with patch.object(async_db_session, "execute", return_value=mock_result):
            # Act
            response = await get_execution_details(
                execution_id=execution_id,
                tenant_id=mock_tenant_id,
                db=async_db_session,
            )

            # Assert - Bearer token should be masked
            assert "abc123def456ghi789" not in str(response.output_data)
            assert "Bearer ***" in response.output_data["headers"]


class TestPerformance:
    """Tests for performance requirements (AC2)."""

    @pytest.mark.asyncio
    async def test_response_time_under_500ms(
        self, async_db_session: AsyncSession, mock_tenant_id: str
    ):
        """Test that endpoint logic completes under 500ms (with mocked DB)."""
        # Arrange
        execution_id = uuid4()
        mock_execution = MagicMock(spec=AgentTestExecution)
        mock_execution.id = execution_id
        mock_execution.agent_id = uuid4()
        mock_execution.tenant_id = mock_tenant_id
        mock_execution.payload = {"test": "data"}
        mock_execution.execution_trace = {"steps": []}
        mock_execution.status = "success"
        mock_execution.execution_time = {"total_duration_ms": 100}
        mock_execution.created_at = datetime.now(timezone.utc)
        mock_execution.errors = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_execution

        with patch.object(async_db_session, "execute", return_value=mock_result):
            # Act
            start_time = time.perf_counter()
            response = await get_execution_details(
                execution_id=execution_id,
                tenant_id=mock_tenant_id,
                db=async_db_session,
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            # Assert - Endpoint logic should be fast (<500ms even with masking)
            assert elapsed_ms < 500
            assert isinstance(response, ExecutionDetailResponse)


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_database_error_returns_500(
        self, async_db_session: AsyncSession, mock_tenant_id: str
    ):
        """Test 500 response when database query fails."""
        # Arrange
        execution_id = uuid4()

        with patch.object(
            async_db_session,
            "execute",
            side_effect=Exception("Database connection lost"),
        ):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_execution_details(
                    execution_id=execution_id,
                    tenant_id=mock_tenant_id,
                    db=async_db_session,
                )

            assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to retrieve execution" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_execution_without_errors_field(
        self, async_db_session: AsyncSession, mock_tenant_id: str
    ):
        """Test handling execution with null errors field."""
        # Arrange
        execution_id = uuid4()
        mock_execution = MagicMock(spec=AgentTestExecution)
        mock_execution.id = execution_id
        mock_execution.agent_id = uuid4()
        mock_execution.tenant_id = mock_tenant_id
        mock_execution.payload = {}
        mock_execution.execution_trace = {}
        mock_execution.status = "success"
        mock_execution.execution_time = {"total_duration_ms": 100}
        mock_execution.created_at = datetime.now(timezone.utc)
        mock_execution.errors = None  # Explicitly None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_execution

        with patch.object(async_db_session, "execute", return_value=mock_result):
            # Act
            response = await get_execution_details(
                execution_id=execution_id,
                tenant_id=mock_tenant_id,
                db=async_db_session,
            )

            # Assert - Should handle None errors gracefully
            assert response.error_message is None
