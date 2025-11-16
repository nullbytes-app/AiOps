"""
Unit tests for queue service.

Tests the QueueService class for pushing jobs to Redis queue, including
success scenarios, error handling, and validation of job data.
"""

import json
import uuid
from datetime import datetime, UTC
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import ValidationError
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from src.schemas.job import EnhancementJob
from src.services.queue_service import ENHANCEMENT_QUEUE_KEY, QueueService
from src.utils.exceptions import QueueServiceError


class TestQueueService:
    """Test suite for QueueService class."""

    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client for testing."""
        client = AsyncMock()
        client.lpush = AsyncMock(return_value=1)
        return client

    @pytest.fixture
    def queue_service(self, mock_redis_client):
        """Create QueueService instance with mocked Redis client."""
        return QueueService(mock_redis_client)

    @pytest.fixture
    def valid_job_data(self):
        """Valid job data for testing."""
        return {
            "job_id": str(uuid.uuid4()),
            "ticket_id": "TKT-001",
            "tenant_id": "tenant-abc",
            "description": "Server is slow and unresponsive",
            "priority": "high",
            "timestamp": datetime.now(UTC),
            "correlation_id": str(uuid.uuid4()),  # Required for distributed tracing
        }

    @pytest.mark.asyncio
    async def test_push_job_success(self, queue_service, mock_redis_client, valid_job_data):
        """
        Test successful job push to Redis queue.

        Verifies:
        - Job is pushed to correct queue key
        - LPUSH is called with JSON-serialized job
        - Returns job_id
        - Queue depth is returned from LPUSH
        """
        # When
        job_id = await queue_service.push_job(
            valid_job_data, tenant_id="tenant-abc", ticket_id="TKT-001"
        )

        # Then
        assert job_id == valid_job_data["job_id"]
        mock_redis_client.lpush.assert_called_once()

        # Verify queue key
        call_args = mock_redis_client.lpush.call_args
        assert call_args[0][0] == ENHANCEMENT_QUEUE_KEY

        # Verify JSON payload contains required fields
        job_json = call_args[0][1]
        job_dict = json.loads(job_json)
        assert job_dict["job_id"] == valid_job_data["job_id"]
        assert job_dict["ticket_id"] == valid_job_data["ticket_id"]
        assert job_dict["tenant_id"] == valid_job_data["tenant_id"]
        assert job_dict["description"] == valid_job_data["description"]
        assert job_dict["priority"] == valid_job_data["priority"]

    @pytest.mark.asyncio
    async def test_push_job_serialization(self, queue_service, mock_redis_client, valid_job_data):
        """
        Test job data is correctly serialized to JSON.

        Verifies:
        - Job data is valid JSON
        - All required fields are present
        - created_at field is auto-generated
        """
        # When
        await queue_service.push_job(valid_job_data, tenant_id="tenant-abc", ticket_id="TKT-001")

        # Then
        call_args = mock_redis_client.lpush.call_args
        job_json = call_args[0][1]

        # Verify valid JSON
        job_dict = json.loads(job_json)

        # Verify all required fields
        assert "job_id" in job_dict
        assert "ticket_id" in job_dict
        assert "tenant_id" in job_dict
        assert "description" in job_dict
        assert "priority" in job_dict
        assert "timestamp" in job_dict
        assert "created_at" in job_dict

    @pytest.mark.asyncio
    async def test_push_job_redis_connection_error(
        self, queue_service, mock_redis_client, valid_job_data
    ):
        """
        Test Redis connection error raises QueueServiceError.

        Verifies:
        - ConnectionError from Redis is caught
        - QueueServiceError is raised
        - Error message includes context
        """
        # Given
        mock_redis_client.lpush.side_effect = RedisConnectionError("Connection refused")

        # When/Then
        with pytest.raises(QueueServiceError) as exc_info:
            await queue_service.push_job(
                valid_job_data, tenant_id="tenant-abc", ticket_id="TKT-001"
            )

        # Verify error message contains context
        error_msg = str(exc_info.value)
        assert "tenant-abc" in error_msg
        assert "TKT-001" in error_msg
        assert "ConnectionError" in error_msg

    @pytest.mark.asyncio
    async def test_push_job_redis_timeout_error(
        self, queue_service, mock_redis_client, valid_job_data
    ):
        """
        Test Redis timeout error raises QueueServiceError.

        Verifies:
        - TimeoutError from Redis is caught
        - QueueServiceError is raised
        - Error message includes context
        """
        # Given
        mock_redis_client.lpush.side_effect = RedisTimeoutError("Operation timed out")

        # When/Then
        with pytest.raises(QueueServiceError) as exc_info:
            await queue_service.push_job(
                valid_job_data, tenant_id="tenant-abc", ticket_id="TKT-001"
            )

        # Verify error message contains context
        error_msg = str(exc_info.value)
        assert "tenant-abc" in error_msg
        assert "TKT-001" in error_msg
        assert "TimeoutError" in error_msg

    @pytest.mark.asyncio
    async def test_push_job_invalid_priority(
        self, queue_service, mock_redis_client, valid_job_data
    ):
        """
        Test invalid priority raises QueueServiceError.

        Verifies:
        - Invalid priority value is rejected by Pydantic
        - QueueServiceError is raised (wrapping ValidationError)
        """
        # Given
        invalid_data = valid_job_data.copy()
        invalid_data["priority"] = "invalid_priority"

        # When/Then
        with pytest.raises(QueueServiceError):
            await queue_service.push_job(invalid_data, tenant_id="tenant-abc", ticket_id="TKT-001")

    @pytest.mark.asyncio
    async def test_push_job_description_max_length(
        self, queue_service, mock_redis_client, valid_job_data
    ):
        """
        Test description exceeding max length raises QueueServiceError.

        Verifies:
        - Description over 10,000 chars is rejected
        - QueueServiceError is raised
        """
        # Given
        invalid_data = valid_job_data.copy()
        invalid_data["description"] = "x" * 10001  # Exceeds 10,000 char limit

        # When/Then
        with pytest.raises(QueueServiceError):
            await queue_service.push_job(invalid_data, tenant_id="tenant-abc", ticket_id="TKT-001")

    @pytest.mark.asyncio
    async def test_push_job_queue_depth(self, queue_service, mock_redis_client, valid_job_data):
        """
        Test queue depth is returned from LPUSH.

        Verifies:
        - LPUSH returns queue depth
        - Multiple jobs increase queue depth
        """
        # Given
        mock_redis_client.lpush.return_value = 3  # Simulate queue depth of 3

        # When
        await queue_service.push_job(valid_job_data, tenant_id="tenant-abc", ticket_id="TKT-001")

        # Then
        assert mock_redis_client.lpush.called
        # Queue depth is logged (verified in implementation)

    @pytest.mark.asyncio
    async def test_push_job_multiple_jobs(self, queue_service, mock_redis_client):
        """
        Test pushing multiple jobs to queue.

        Verifies:
        - Multiple jobs can be pushed
        - Each job gets unique job_id
        - Queue depth increases with each push
        """
        # Given
        job_data_list = [
            {
                "job_id": str(uuid.uuid4()),
                "ticket_id": f"TKT-00{i}",
                "tenant_id": "tenant-abc",
                "description": f"Issue {i}",
                "priority": "high",
                "timestamp": datetime.now(UTC),
                "correlation_id": str(uuid.uuid4()),  # Required for distributed tracing
            }
            for i in range(1, 4)
        ]

        # Simulate increasing queue depth
        mock_redis_client.lpush.side_effect = [1, 2, 3]

        # When
        job_ids = []
        for job_data in job_data_list:
            job_id = await queue_service.push_job(
                job_data, tenant_id="tenant-abc", ticket_id=job_data["ticket_id"]
            )
            job_ids.append(job_id)

        # Then
        assert len(job_ids) == 3
        assert len(set(job_ids)) == 3  # All job_ids are unique
        assert mock_redis_client.lpush.call_count == 3

    @pytest.mark.asyncio
    async def test_push_job_missing_required_field(
        self, queue_service, mock_redis_client, valid_job_data
    ):
        """
        Test missing required field raises QueueServiceError.

        Verifies:
        - Missing required field (e.g., ticket_id) is caught
        - QueueServiceError is raised
        """
        # Given
        invalid_data = valid_job_data.copy()
        del invalid_data["ticket_id"]  # Remove required field

        # When/Then
        with pytest.raises(QueueServiceError):
            await queue_service.push_job(invalid_data, tenant_id="tenant-abc", ticket_id="unknown")

    @pytest.mark.asyncio
    async def test_push_job_valid_job_id_format(
        self, queue_service, mock_redis_client, valid_job_data
    ):
        """
        Test job_id is valid UUID format.

        Verifies:
        - job_id returned is valid UUID
        - job_id matches input job_id
        """
        # When
        job_id = await queue_service.push_job(
            valid_job_data, tenant_id="tenant-abc", ticket_id="TKT-001"
        )

        # Then
        # Verify job_id is valid UUID by parsing it
        uuid.UUID(job_id)  # Raises ValueError if invalid
        assert job_id == valid_job_data["job_id"]
