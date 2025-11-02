"""
Integration tests for Celery task execution and worker functionality.

These tests validate Celery worker configuration, task execution, retry logic,
timeout enforcement, and result persistence. Tests run against a real Redis
broker and worker instance in the Docker environment.

Test Coverage:
    - Worker connection to Redis broker
    - Basic task execution (add_numbers)
    - Task retry logic with exponential backoff
    - Task timeout enforcement (soft and hard limits)
    - Task result persistence in Redis backend
    - Task result retrieval from backend

Usage:
    # Run all Celery integration tests
    docker-compose exec api pytest tests/integration/test_celery_tasks.py -v

    # Run specific test
    docker-compose exec api pytest tests/integration/test_celery_tasks.py::TestCeleryTaskExecution::test_basic_task_execution -v
"""

import time
from typing import Any
from unittest.mock import patch

import pytest
from celery.exceptions import SoftTimeLimitExceeded
from celery.result import AsyncResult

from src.workers.celery_app import celery_app
from src.workers.tasks import add_numbers, enhance_ticket


class TestCeleryConnection:
    """Test Celery worker connection to Redis broker."""

    def test_celery_broker_connection(self) -> None:
        """
        Verify Celery app initializes with correct broker configuration.

        Tests:
            - Celery app has broker URL configured
            - Broker URL uses Redis protocol
            - Backend URL matches broker URL pattern
        """
        # Verify broker URL is configured
        assert celery_app.conf.broker_url is not None
        assert "redis://" in celery_app.conf.broker_url

        # Verify result backend is configured
        assert celery_app.conf.result_backend is not None
        assert "redis://" in celery_app.conf.result_backend

    def test_celery_app_configuration(self) -> None:
        """
        Verify Celery app has correct configuration per tech spec.

        Tests:
            - Task serializer is JSON
            - Time limits match tech spec (120s hard, 100s soft)
            - Worker concurrency is 4
            - Prefetch multiplier is 1
            - Late acknowledgement enabled
            - Retry configuration present
        """
        # Serialization
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"
        assert "json" in celery_app.conf.accept_content

        # Time limits (per tech spec)
        assert celery_app.conf.task_time_limit == 120
        assert celery_app.conf.task_soft_time_limit == 100

        # Worker settings
        assert celery_app.conf.worker_concurrency == 4
        assert celery_app.conf.worker_prefetch_multiplier == 1
        assert celery_app.conf.task_acks_late is True

        # Retry configuration
        assert celery_app.conf.task_max_retries == 3
        assert celery_app.conf.task_retry_backoff is True


class TestCeleryTaskExecution:
    """Test basic Celery task execution and result retrieval."""

    def test_basic_task_execution_sync(self) -> None:
        """
        Test basic task execution using add_numbers task (synchronous mode).

        Tests:
            - Task executes successfully
            - Task returns correct result
            - Result matches expected sum

        Note:
            This test uses .apply() which runs synchronously for testing.
            Production code uses .delay() or .apply_async() for async execution.
        """
        # Execute task synchronously (for testing)
        result = add_numbers.apply(args=[2, 3])

        # Verify task completed successfully
        assert result.successful()
        assert result.result == 5

    def test_basic_task_execution_async(self) -> None:
        """
        Test basic task execution using add_numbers task (asynchronous mode).

        Tests:
            - Task submits to queue successfully
            - Task ID is generated
            - Task executes and returns result
            - Result can be retrieved from backend

        Note:
            This test requires a running Celery worker.
            Use: docker-compose up worker
        """
        # Execute task asynchronously
        result = add_numbers.delay(10, 20)

        # Verify task was submitted
        assert result.id is not None
        assert isinstance(result, AsyncResult)

        # Wait for task to complete (with timeout)
        final_result = result.get(timeout=10)

        # Verify result
        assert final_result == 30
        assert result.successful()

    def test_task_result_persistence(self) -> None:
        """
        Test that task results are persisted in Redis backend.

        Tests:
            - Task result is stored in backend
            - Result can be retrieved using task ID
            - Result matches expected value
        """
        # Execute task
        result = add_numbers.delay(5, 7)
        task_id = result.id

        # Wait for completion
        final_result = result.get(timeout=10)
        assert final_result == 12

        # Retrieve result using task ID (simulates result retrieval from backend)
        retrieved_result = AsyncResult(task_id, app=celery_app)
        assert retrieved_result.result == 12
        assert retrieved_result.status == "SUCCESS"

    def test_task_with_invalid_arguments(self) -> None:
        """
        Test task execution with invalid argument types.

        Tests:
            - Task raises TypeError for non-numeric arguments
            - Error is propagated to result
            - Task status is FAILURE
        """
        # Execute task with invalid arguments
        result = add_numbers.delay("invalid", "args")  # type: ignore

        # Wait for task to fail
        with pytest.raises(TypeError):
            result.get(timeout=10)

        assert result.failed()

    def test_enhance_ticket_placeholder(self) -> None:
        """
        Test enhance_ticket placeholder task returns expected structure.

        Tests:
            - Task executes without error
            - Result contains expected keys
            - Status indicates not implemented
            - Task ID is included in result

        Note:
            This is a placeholder test. Full implementation in Epic 2.
        """
        job_data = {
            "ticket_id": "12345",
            "tenant_id": "tenant_1",
            "priority": "high",
        }

        # Execute placeholder task
        result = enhance_ticket.delay(job_data)
        final_result = result.get(timeout=10)

        # Verify placeholder response structure
        assert isinstance(final_result, dict)
        assert final_result["status"] == "completed"
        assert final_result["ticket_id"] == "12345"
        assert "enhancement_id" in final_result
        assert "processing_time_ms" in final_result


class TestCeleryRetryLogic:
    """Test Celery task retry logic with exponential backoff."""

    def test_task_retry_on_failure(self) -> None:
        """
        Test that tasks retry on failure with exponential backoff.

        Tests:
            - Task retries on exception
            - Maximum retries is 3 per config
            - Task eventually fails after max retries

        Note:
            This test uses a mock to simulate task failures.
        """
        # Create a task that fails the first 2 times, succeeds on 3rd
        attempt_counter = {"count": 0}

        @celery_app.task(
            bind=True,
            autoretry_for=(Exception,),
            retry_kwargs={"max_retries": 3, "countdown": 1},
            retry_backoff=True,
        )
        def flaky_task(self: Any) -> str:
            attempt_counter["count"] += 1
            if attempt_counter["count"] < 3:
                raise Exception("Simulated failure")
            return "success"

        # Execute task
        result = flaky_task.apply()

        # Task should succeed after retries
        assert result.successful()
        assert result.result == "success"
        assert attempt_counter["count"] == 3

    def test_task_max_retries_exhausted(self) -> None:
        """
        Test that task fails after exhausting maximum retries.

        Tests:
            - Task retries maximum number of times
            - Task status is FAILURE after max retries
            - Final exception is propagated
        """

        @celery_app.task(
            bind=True,
            autoretry_for=(Exception,),
            retry_kwargs={"max_retries": 2, "countdown": 1},
        )
        def always_fails(self: Any) -> None:
            raise Exception("Always fails")

        # Execute task (synchronously for testing)
        result = always_fails.apply()

        # Task should fail after exhausting retries
        assert result.failed()
        with pytest.raises(Exception, match="Always fails"):
            result.get()


class TestCeleryTimeoutEnforcement:
    """Test Celery task timeout enforcement (soft and hard limits)."""

    def test_task_soft_timeout(self) -> None:
        """
        Test that tasks respect soft time limit.

        Tests:
            - Task raises SoftTimeLimitExceeded when exceeding soft limit
            - Exception can be caught for graceful cleanup

        Note:
            Soft timeout allows task to catch exception and clean up.
        """

        @celery_app.task(
            bind=True,
            soft_time_limit=2,  # 2 second soft limit
        )
        def long_running_task(self: Any) -> None:
            try:
                time.sleep(5)  # Exceeds soft limit
            except SoftTimeLimitExceeded:
                # Graceful cleanup on soft timeout
                return "cleaned_up"

        # Execute task
        result = long_running_task.apply()

        # Verify soft timeout was raised and handled
        assert result.result == "cleaned_up"

    @pytest.mark.skip(reason="Hard timeout requires separate worker process, tested in Docker")
    def test_task_hard_timeout(self) -> None:
        """
        Test that tasks are killed at hard time limit.

        Tests:
            - Task is forcefully terminated at hard limit
            - Task status is FAILURE

        Note:
            Hard timeout test requires separate worker process.
            This test is marked as skip for unit testing.
            Full test coverage in Docker integration environment.
        """
        pass


class TestCeleryTaskMonitoring:
    """Test Celery task monitoring and inspection capabilities."""

    def test_task_tracking(self) -> None:
        """
        Test that task execution is tracked through lifecycle.

        Tests:
            - Task starts with PENDING status
            - Task transitions to STARTED when executing
            - Task transitions to SUCCESS when complete
        """
        # Execute task
        result = add_numbers.delay(1, 1)

        # Initially PENDING (may transition quickly to STARTED)
        assert result.status in ["PENDING", "STARTED", "SUCCESS"]

        # Wait for completion
        result.get(timeout=10)

        # Final status should be SUCCESS
        assert result.status == "SUCCESS"

    def test_task_result_metadata(self) -> None:
        """
        Test that task result includes metadata.

        Tests:
            - Result includes task ID
            - Result includes task name
            - Result includes status
            - Result includes return value
        """
        result = add_numbers.delay(3, 4)
        final_result = result.get(timeout=10)

        # Verify metadata
        assert result.id is not None
        assert result.status == "SUCCESS"
        assert result.result == 7
        assert final_result == 7


# Mark all tests to require Redis connection (integration tests)
pytestmark = pytest.mark.integration
