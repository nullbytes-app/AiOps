"""
Integration tests for execution retrieval endpoint.

Tests end-to-end flow with real database interactions, verifying data
integrity, tenant isolation, and API contract compliance.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Agent, AgentTestExecution, TenantConfig


@pytest.mark.asyncio
class TestExecutionRetrievalIntegration:
    """Integration tests for execution retrieval API."""

    async def test_end_to_end_execution_flow(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """
        Test full flow: create tenant → create agent → create execution → retrieve via API.

        Verifies data integrity across the entire execution lifecycle.
        """
        # Step 1: Create tenant
        tenant_id = f"test-tenant-{uuid4()}"
        tenant = TenantConfig(
            id=tenant_id,
            name="Test Tenant",
            webhook_url="https://test.example.com/webhook",
            webhook_secret="test-secret",
        )
        async_db_session.add(tenant)
        await async_db_session.commit()

        try:
            # Step 2: Create agent
            agent_id = uuid4()
            agent = Agent(
                id=agent_id,
                tenant_id=tenant_id,
                name="Test Agent",
                description="Agent for integration testing",
                system_prompt="You are a test agent",
                model="gpt-4",
                temperature=0.7,
            )
            async_db_session.add(agent)
            await async_db_session.commit()

            # Step 3: Create test execution
            execution_id = uuid4()
            test_payload = {
                "webhook_data": {"ticket_id": "TEST-123"},
                "api_key": "sk-test1234567890abcdef1234567890",  # Should be masked
            }
            test_trace = {
                "steps": [
                    {"step_type": "llm_call", "input": "test input", "output": "test output", "duration_ms": 500},
                    {
                        "step_type": "tool_call",
                        "tool_name": "database_query",
                        "input": {"password": "secret123"},  # Should be masked
                        "output": {"result": "success"},
                        "duration_ms": 200,
                    },
                ],
                "total_duration_ms": 700,
            }
            execution = AgentTestExecution(
                id=execution_id,
                agent_id=agent_id,
                tenant_id=tenant_id,
                payload=test_payload,
                execution_trace=test_trace,
                token_usage={
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "total_tokens": 150,
                    "estimated_cost_usd": 0.003,
                },
                execution_time={"total_duration_ms": 700},
                errors=None,
                status="success",
            )
            async_db_session.add(execution)
            await async_db_session.commit()

            # Step 4: Retrieve execution via API
            # Mock tenant authentication
            headers = {"X-Tenant-ID": tenant_id}
            response = await async_client.get(
                f"/api/executions/{execution_id}", headers=headers
            )

            # Assert: Successful retrieval
            assert response.status_code == 200
            data = response.json()

            # Verify all fields present
            assert data["id"] == str(execution_id)
            assert data["agent_id"] == str(agent_id)
            assert data["tenant_id"] == tenant_id
            assert data["status"] == "success"
            assert data["execution_time"] == 700
            assert data["error_message"] is None

            # Verify data integrity
            assert data["input_data"]["webhook_data"]["ticket_id"] == "TEST-123"

            # Verify sensitive data masking
            assert "sk-test1234567890abcdef1234567890" not in str(data["input_data"])
            assert data["input_data"]["api_key"] == "***"

            assert "secret123" not in str(data["output_data"])
            step = data["output_data"]["steps"][1]
            assert step["input"]["password"] == "***"

        finally:
            # Cleanup: Delete test data
            await async_db_session.delete(execution)
            await async_db_session.delete(agent)
            await async_db_session.delete(tenant)
            await async_db_session.commit()

    async def test_tenant_isolation_with_real_db(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """
        Test tenant isolation enforcement with actual database records.

        Ensures Tenant A cannot access Tenant B's executions.
        """
        # Create Tenant A
        tenant_a_id = f"tenant-a-{uuid4()}"
        tenant_a = TenantConfig(
            id=tenant_a_id,
            name="Tenant A",
            webhook_url="https://tenant-a.example.com/webhook",
            webhook_secret="secret-a",
        )
        async_db_session.add(tenant_a)

        # Create Tenant B
        tenant_b_id = f"tenant-b-{uuid4()}"
        tenant_b = TenantConfig(
            id=tenant_b_id,
            name="Tenant B",
            webhook_url="https://tenant-b.example.com/webhook",
            webhook_secret="secret-b",
        )
        async_db_session.add(tenant_b)
        await async_db_session.commit()

        try:
            # Create agent for Tenant B
            agent_b_id = uuid4()
            agent_b = Agent(
                id=agent_b_id,
                tenant_id=tenant_b_id,
                name="Tenant B Agent",
                description="Agent for Tenant B",
                system_prompt="Test",
                model="gpt-4",
                temperature=0.7,
            )
            async_db_session.add(agent_b)
            await async_db_session.commit()

            # Create execution for Tenant B
            execution_b_id = uuid4()
            execution_b = AgentTestExecution(
                id=execution_b_id,
                agent_id=agent_b_id,
                tenant_id=tenant_b_id,
                payload={"data": "tenant b data"},
                execution_trace={"steps": []},
                token_usage={"total_tokens": 100},
                execution_time={"total_duration_ms": 500},
                errors=None,
                status="success",
            )
            async_db_session.add(execution_b)
            await async_db_session.commit()

            # Attempt to access Tenant B's execution as Tenant A
            headers = {"X-Tenant-ID": tenant_a_id}
            response = await async_client.get(
                f"/api/executions/{execution_b_id}", headers=headers
            )

            # Assert: Access denied
            assert response.status_code == 403
            assert "Forbidden" in response.json()["detail"]

        finally:
            # Cleanup
            await async_db_session.delete(execution_b)
            await async_db_session.delete(agent_b)
            await async_db_session.delete(tenant_a)
            await async_db_session.delete(tenant_b)
            await async_db_session.commit()

    async def test_not_found_with_real_db(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test 404 response for non-existent execution with real database."""
        # Create tenant for authentication
        tenant_id = f"test-tenant-{uuid4()}"
        tenant = TenantConfig(
            id=tenant_id,
            name="Test Tenant",
            webhook_url="https://test.example.com/webhook",
            webhook_secret="test-secret",
        )
        async_db_session.add(tenant)
        await async_db_session.commit()

        try:
            # Try to retrieve non-existent execution
            non_existent_id = uuid4()
            headers = {"X-Tenant-ID": tenant_id}
            response = await async_client.get(
                f"/api/executions/{non_existent_id}", headers=headers
            )

            # Assert: Not found
            assert response.status_code == 404
            assert response.json()["detail"] == "Execution not found"

        finally:
            # Cleanup
            await async_db_session.delete(tenant)
            await async_db_session.commit()
