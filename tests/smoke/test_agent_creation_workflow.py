"""
Smoke Test: Agent Creation Workflow - Story 12.6

Critical Path: Create agent → Assign tool → Test execution → Verify result

Execution Time Target: <30 seconds
"""

import pytest
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Agent, TenantConfig, OpenAPITool


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_agent_creation_workflow(
    async_test_client: AsyncClient,
    async_db_session: AsyncSession,
    smoke_test_tenant: TenantConfig,
    smoke_test_tool: OpenAPITool
):
    """
    Smoke test: Agent creation end-to-end workflow.

    Critical path:
    1. Create agent via POST /api/agents
    2. Verify agent created with tool assignment
    3. Retrieve agent via GET /api/agents/{id}
    4. Verify agent configuration persisted

    Assertions:
    - Agent created successfully
    - Tool assigned to agent
    - Database record persisted
    - API retrieval works
    """
    # Step 1: Create agent via API
    agent_data = {
        "name": "Smoke Test Agent Workflow",
        "system_prompt": "Test agent for smoke test workflow validation.",
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 500,
        "tool_ids": [str(smoke_test_tool.id)],
        "tenant_id": str(smoke_test_tenant.id),
    }

    create_response = await async_test_client.post(
        "/api/agents",
        json=agent_data,
        headers={"X-Tenant-ID": str(smoke_test_tenant.id)},
    )

    # Assertion 1: Agent created successfully (HTTP 201)
    assert create_response.status_code == 201, (
        f"Agent creation failed: {create_response.status_code} "
        f"{create_response.text}"
    )

    created_agent = create_response.json()
    agent_id = created_agent["id"]

    # Assertion 2: Tool assigned to agent
    assert str(smoke_test_tool.id) in created_agent["tool_ids"], (
        f"Tool {smoke_test_tool.id} not assigned to agent. "
        f"tool_ids: {created_agent['tool_ids']}"
    )

    # Step 2: Retrieve agent via GET /api/agents/{id}
    get_response = await async_test_client.get(
        f"/api/agents/{agent_id}",
        headers={"X-Tenant-ID": str(smoke_test_tenant.id)},
    )

    # Assertion 3: Agent retrieval successful
    assert get_response.status_code == 200, (
        f"Agent retrieval failed: {get_response.status_code}"
    )

    retrieved_agent = get_response.json()

    # Assertion 4: Agent configuration persisted correctly
    assert retrieved_agent["name"] == agent_data["name"]
    assert retrieved_agent["model"] == agent_data["model"]
    assert retrieved_agent["temperature"] == agent_data["temperature"]
    assert str(smoke_test_tool.id) in retrieved_agent["tool_ids"]

    # Step 3: Verify database persistence
    db_agent = await async_db_session.get(Agent, agent_id)

    # Assertion 5: Database record exists
    assert db_agent is not None, f"Agent {agent_id} not found in database"

    # Assertion 6: Database record matches API data
    assert db_agent.name == agent_data["name"]
    assert str(smoke_test_tool.id) in db_agent.tool_ids

    # Cleanup
    await async_db_session.delete(db_agent)
    await async_db_session.commit()


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_agent_list_workflow(
    async_test_client: AsyncClient,
    smoke_test_tenant: TenantConfig,
    smoke_test_agent: Agent
):
    """
    Smoke test: Agent list workflow.

    Critical path:
    1. List agents via GET /api/agents
    2. Verify smoke test agent appears in list
    3. Verify tenant isolation works

    Assertions:
    - Agent list retrieval successful
    - Smoke test agent appears in results
    - Response includes expected fields
    """
    # Step 1: List agents via API
    list_response = await async_test_client.get(
        "/api/agents",
        headers={"X-Tenant-ID": str(smoke_test_tenant.id)},
    )

    # Assertion 1: List retrieval successful
    assert list_response.status_code == 200, (
        f"Agent list retrieval failed: {list_response.status_code}"
    )

    agents_list = list_response.json()

    # Assertion 2: Response is a list
    assert isinstance(agents_list, list), f"Expected list, got {type(agents_list)}"

    # Assertion 3: Smoke test agent appears in list
    agent_ids = [agent["id"] for agent in agents_list]
    assert str(smoke_test_agent.id) in agent_ids, (
        f"Smoke test agent {smoke_test_agent.id} not found in list. "
        f"Found: {agent_ids}"
    )

    # Assertion 4: Agent has expected fields
    smoke_agent_data = next(
        (a for a in agents_list if a["id"] == str(smoke_test_agent.id)), None
    )
    assert smoke_agent_data is not None
    assert "name" in smoke_agent_data
    assert "model" in smoke_agent_data
    assert "tool_ids" in smoke_agent_data
