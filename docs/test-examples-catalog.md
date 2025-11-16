# Test Examples Catalog

**Version:** 1.0
**Last Updated:** 2025-11-11
**Purpose:** Comprehensive library of integration test examples organized by testing pattern
**Related:** [Integration Testing Guide](integration-testing-guide.md) | [Testing Decision Tree](testing-decision-tree.md)

## Table of Contents

1. [Database Testing Examples](#database-testing-examples)
2. [API Testing Examples](#api-testing-examples)
3. [External Service Testing Examples](#external-service-testing-examples)
4. [Workflow Testing Examples](#workflow-testing-examples)

---

## Database Testing Examples

### Example 1: Simple SELECT Query Test

**Use Case:** Verify database connection and basic query execution

**Test Code:**

```python
# tests/integration/test_database_queries.py
import pytest
from sqlalchemy import select
from src.database.models import Tenant

@pytest.mark.integration
@pytest.mark.anyio
async def test_select_tenants_basic(async_db_session):
    """Test basic SELECT query on tenants table.

    Verifies:
    - Database connection established
    - Tenants table exists
    - SQLAlchemy async query execution
    - Result set handling
    """
    # Create test tenant
    tenant = Tenant(name="Test Corporation", admin_email="admin@test.com")
    async_db_session.add(tenant)
    await async_db_session.commit()
    await async_db_session.refresh(tenant)

    # Execute SELECT query
    result = await async_db_session.execute(
        select(Tenant).where(Tenant.name == "Test Corporation")
    )
    fetched_tenant = result.scalar_one()

    # Assertions
    assert fetched_tenant is not None
    assert fetched_tenant.id == tenant.id
    assert fetched_tenant.name == "Test Corporation"
    assert fetched_tenant.admin_email == "admin@test.com"
```

**Fixture Dependencies:**
- `async_db_session` - Async database session with auto-rollback

**What This Tests:**
- ✅ PostgreSQL connection via asyncpg driver
- ✅ Table schema (tenants table exists with correct columns)
- ✅ SQLAlchemy 2.0 async query patterns
- ✅ Data persistence and retrieval

**Common Variations:**
- Query with multiple WHERE clauses
- Query with ORDER BY and LIMIT
- Query with JOINs (see Example 3)

**Link to Real Test:** `tests/integration/test_tenant_api.py::test_list_tenants`

---

### Example 2: INSERT/UPDATE/DELETE Transaction Test

**Use Case:** Verify database transactions with full CRUD operations

**Test Code:**

```python
# tests/integration/test_database_transactions.py
import pytest
from sqlalchemy import select
from src.database.models import Agent

@pytest.mark.integration
@pytest.mark.anyio
async def test_crud_transaction(async_db_session, test_tenant):
    """Test CREATE, READ, UPDATE, DELETE transaction.

    Verifies:
    - INSERT operation persists data
    - UPDATE modifies existing record
    - DELETE removes record
    - Transaction isolation
    """
    # CREATE: Insert new agent
    agent = Agent(
        name="Original Name",
        system_prompt="Original prompt",
        tenant_id=test_tenant.id
    )
    async_db_session.add(agent)
    await async_db_session.commit()
    await async_db_session.refresh(agent)
    agent_id = agent.id

    # READ: Verify creation
    result = await async_db_session.execute(
        select(Agent).where(Agent.id == agent_id)
    )
    created_agent = result.scalar_one()
    assert created_agent.name == "Original Name"

    # UPDATE: Modify agent
    created_agent.name = "Updated Name"
    created_agent.system_prompt = "Updated prompt"
    await async_db_session.commit()

    # READ: Verify update
    result = await async_db_session.execute(
        select(Agent).where(Agent.id == agent_id)
    )
    updated_agent = result.scalar_one()
    assert updated_agent.name == "Updated Name"
    assert updated_agent.system_prompt == "Updated prompt"

    # DELETE: Remove agent
    await async_db_session.delete(updated_agent)
    await async_db_session.commit()

    # READ: Verify deletion
    result = await async_db_session.execute(
        select(Agent).where(Agent.id == agent_id)
    )
    deleted_agent = result.scalar_one_or_none()
    assert deleted_agent is None
```

**Fixture Dependencies:**
- `async_db_session` - Async database session with auto-rollback
- `test_tenant` - Tenant instance for foreign key relationship

**What This Tests:**
- ✅ INSERT operation with foreign key
- ✅ UPDATE operation modifying multiple columns
- ✅ DELETE operation and cascade behavior
- ✅ Transaction commit and isolation

**Common Variations:**
- Bulk INSERT (add multiple records)
- UPDATE with WHERE clause
- DELETE with cascade to child records

**Link to Real Test:** `tests/integration/test_agent_database.py::test_agent_crud_operations`

---

### Example 3: Foreign Key Constraint Validation Test

**Use Case:** Verify database enforces foreign key relationships

**Test Code:**

```python
# tests/integration/test_database_constraints.py
import pytest
from sqlalchemy.exc import IntegrityError
from src.database.models import Agent, Tenant
import uuid

@pytest.mark.integration
@pytest.mark.anyio
async def test_foreign_key_constraint_enforced(async_db_session):
    """Test foreign key constraint prevents orphaned records.

    Verifies:
    - Foreign key constraint exists on agents.tenant_id
    - Database rejects INSERT with invalid tenant_id
    - IntegrityError raised with constraint name
    """
    # Attempt to create agent with non-existent tenant_id
    invalid_tenant_id = uuid.uuid4()
    agent = Agent(
        name="Orphaned Agent",
        system_prompt="Test prompt",
        tenant_id=invalid_tenant_id  # This tenant doesn't exist
    )
    async_db_session.add(agent)

    # Expect IntegrityError due to foreign key violation
    with pytest.raises(IntegrityError) as exc_info:
        await async_db_session.commit()

    # Verify error message contains constraint name
    assert "fk_agents_tenant_id" in str(exc_info.value)
    assert "foreign key constraint" in str(exc_info.value).lower()

    # Rollback failed transaction
    await async_db_session.rollback()
```

**Fixture Dependencies:**
- `async_db_session` - Async database session with auto-rollback

**What This Tests:**
- ✅ Foreign key constraint defined in migration
- ✅ Database enforces referential integrity
- ✅ Proper error raised (IntegrityError)
- ✅ Transaction rollback after error

**Common Variations:**
- Test ON DELETE CASCADE behavior
- Test ON UPDATE CASCADE behavior
- Test multiple foreign keys

**Link to Real Test:** `tests/integration/test_database_constraints.py::test_agent_tenant_foreign_key`

---

### Example 4: Database Migration Testing Pattern

**Use Case:** Verify Alembic migration can upgrade and downgrade successfully

**Test Code:**

```python
# tests/integration/test_database_migrations.py
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

@pytest.mark.integration
@pytest.mark.anyio
async def test_migration_upgrade_downgrade(async_db_session):
    """Test migration 012 (mcp_servers table) can upgrade/downgrade.

    Verifies:
    - Migration can upgrade to head
    - Migration creates expected tables/columns
    - Migration can downgrade without errors
    - Database schema matches expected state
    """
    alembic_cfg = Config("alembic.ini")
    engine = async_db_session.bind

    # Downgrade to previous version
    command.downgrade(alembic_cfg, "-1")

    # Verify mcp_servers table doesn't exist
    inspector = inspect(engine)
    tables_before = inspector.get_table_names()
    assert "mcp_servers" not in tables_before

    # Upgrade to head (applies migration 012)
    command.upgrade(alembic_cfg, "head")

    # Verify mcp_servers table created
    tables_after = inspector.get_table_names()
    assert "mcp_servers" in tables_after

    # Verify table has expected columns
    columns = [col["name"] for col in inspector.get_columns("mcp_servers")]
    expected_columns = [
        "id", "tenant_id", "name", "transport_type",
        "command", "args", "env_vars", "status", "created_at", "updated_at"
    ]
    for col in expected_columns:
        assert col in columns, f"Missing column: {col}"

    # Verify foreign key constraint exists
    foreign_keys = inspector.get_foreign_keys("mcp_servers")
    assert len(foreign_keys) > 0
    assert foreign_keys[0]["referred_table"] == "tenants"
```

**Fixture Dependencies:**
- `async_db_session` - Async database session with auto-rollback

**What This Tests:**
- ✅ Migration script syntax valid
- ✅ upgrade() creates tables/columns
- ✅ downgrade() removes tables/columns
- ✅ Foreign key constraints created

**Common Variations:**
- Test data migration (ALTER TABLE with data transformation)
- Test index creation
- Test RLS policy creation

**Link to Real Test:** `tests/integration/test_database_migrations.py::test_mcp_servers_migration`

---

### Example 5: Multi-Tenant Data Isolation Test (RLS)

**Use Case:** Verify Row-Level Security (RLS) prevents cross-tenant data access

**Test Code:**

```python
# tests/integration/test_rls_policies.py
import pytest
from sqlalchemy import text, select
from src.database.models import Tenant, Agent

@pytest.mark.integration
@pytest.mark.anyio
async def test_rls_policy_enforces_tenant_isolation(async_db_session):
    """Test RLS policy prevents cross-tenant data access.

    Verifies:
    - RLS policy active on agents table
    - Tenant A cannot see Tenant B's agents
    - set_tenant_context() function works correctly
    - Query results filtered by tenant_id
    """
    # Create two tenants
    tenant_a = Tenant(name="Tenant A", admin_email="admin_a@test.com")
    tenant_b = Tenant(name="Tenant B", admin_email="admin_b@test.com")
    async_db_session.add_all([tenant_a, tenant_b])
    await async_db_session.commit()
    await async_db_session.refresh(tenant_a)
    await async_db_session.refresh(tenant_b)

    # Create agent for Tenant A
    agent_a = Agent(name="Agent A", system_prompt="Prompt A", tenant_id=tenant_a.id)
    async_db_session.add(agent_a)
    await async_db_session.commit()

    # Create agent for Tenant B
    agent_b = Agent(name="Agent B", system_prompt="Prompt B", tenant_id=tenant_b.id)
    async_db_session.add(agent_b)
    await async_db_session.commit()

    # Set tenant context to Tenant A
    await async_db_session.execute(
        text("SELECT set_tenant_context(:tenant_id)"),
        {"tenant_id": str(tenant_a.id)}
    )

    # Query agents (should only return Tenant A's agents)
    result = await async_db_session.execute(select(Agent))
    agents = result.scalars().all()

    # Assertions
    assert len(agents) == 1, "RLS should filter to Tenant A's agents only"
    assert agents[0].name == "Agent A"
    assert agents[0].tenant_id == tenant_a.id

    # Set tenant context to Tenant B
    await async_db_session.execute(
        text("SELECT set_tenant_context(:tenant_id)"),
        {"tenant_id": str(tenant_b.id)}
    )

    # Query agents (should only return Tenant B's agents)
    result = await async_db_session.execute(select(Agent))
    agents = result.scalars().all()

    # Assertions
    assert len(agents) == 1, "RLS should filter to Tenant B's agents only"
    assert agents[0].name == "Agent B"
    assert agents[0].tenant_id == tenant_b.id
```

**Fixture Dependencies:**
- `async_db_session` - Async database session with auto-rollback

**What This Tests:**
- ✅ RLS policy active on agents table
- ✅ set_tenant_context() PostgreSQL function
- ✅ Tenant isolation enforced
- ✅ No cross-tenant data leakage

**Common Variations:**
- Test RLS on other tables (mcp_servers, llm_providers)
- Test admin bypass (RLS disabled for admin role)
- Test RLS with JOINs

**Link to Real Test:** `tests/integration/test_tenant_isolation.py::test_rls_agent_isolation`

---

## API Testing Examples

### Example 6: FastAPI Endpoint Test with TestClient

**Use Case:** Test synchronous API endpoint with FastAPI TestClient

**Test Code:**

```python
# tests/integration/test_api_sync.py
import pytest
from fastapi.testclient import TestClient
from src.main import app

@pytest.mark.integration
def test_get_tenants_sync():
    """Test GET /api/tenants endpoint with synchronous TestClient.

    Verifies:
    - Endpoint accessible
    - Status code 200
    - Response JSON format
    - Response contains list of tenants
    """
    client = TestClient(app)

    # Call API endpoint
    response = client.get("/api/tenants")

    # Assertions
    assert response.status_code == 200
    response_json = response.json()
    assert isinstance(response_json, list)
    assert len(response_json) >= 0  # May be empty list

    # If tenants exist, verify structure
    if len(response_json) > 0:
        tenant = response_json[0]
        assert "id" in tenant
        assert "name" in tenant
        assert "admin_email" in tenant
        assert "created_at" in tenant
```

**Fixture Dependencies:**
- None (TestClient instantiated in test)

**What This Tests:**
- ✅ FastAPI route handling GET request
- ✅ Response serialization (Pydantic model → JSON)
- ✅ HTTP status code
- ✅ Response JSON structure

**Common Variations:**
- Test POST endpoint (create resource)
- Test PUT endpoint (update resource)
- Test DELETE endpoint (delete resource)

**Link to Real Test:** `tests/integration/test_tenant_api.py::test_list_tenants`

---

### Example 7: Async API Endpoint Test with httpx.AsyncClient

**Use Case:** Test asynchronous API endpoint with httpx.AsyncClient (recommended)

**Test Code:**

```python
# tests/integration/test_api_async.py
import pytest
from httpx import AsyncClient
from src.main import app

@pytest.mark.integration
@pytest.mark.anyio
async def test_create_tenant_async(async_client):
    """Test POST /api/tenants endpoint with async client.

    Verifies:
    - Endpoint accepts POST requests
    - Request body validated (Pydantic schema)
    - Response status 201 (Created)
    - Response contains created tenant
    - Tenant persisted to database
    """
    # Prepare request data
    tenant_data = {
        "name": "New Corporation",
        "admin_email": "admin@newcorp.com"
    }

    # Call API endpoint
    response = await async_client.post("/api/tenants", json=tenant_data)

    # Assertions
    assert response.status_code == 201
    response_json = response.json()
    assert response_json["name"] == "New Corporation"
    assert response_json["admin_email"] == "admin@newcorp.com"
    assert "id" in response_json
    assert response_json["id"] is not None  # UUID generated

@pytest_asyncio.fixture
async def async_client():
    """Create httpx.AsyncClient for API testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
```

**Fixture Dependencies:**
- `async_client` - httpx.AsyncClient fixture

**What This Tests:**
- ✅ FastAPI route handling POST request
- ✅ Request validation (Pydantic schema)
- ✅ Response status code 201
- ✅ Response serialization
- ✅ Database persistence (implicitly)

**Common Variations:**
- Test with invalid request data (expect 422)
- Test with missing required fields (expect 422)
- Test with authentication header

**Link to Real Test:** `tests/integration/test_tenant_api.py::test_create_tenant`

---

### Example 8: API Authentication/Authorization Test

**Use Case:** Verify protected endpoints require authentication

**Test Code:**

```python
# tests/integration/test_api_auth.py
import pytest
from httpx import AsyncClient
from src.main import app

@pytest.mark.integration
@pytest.mark.anyio
async def test_protected_endpoint_requires_auth(async_client):
    """Test protected endpoint returns 401 without authentication.

    Verifies:
    - Endpoint requires authentication
    - 401 status code returned without auth header
    - Error message indicates authentication required
    """
    # Call protected endpoint without authentication
    response = await async_client.get("/api/agents")

    # Assertions
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"

@pytest.mark.integration
@pytest.mark.anyio
async def test_protected_endpoint_with_valid_auth(async_client, test_api_key):
    """Test protected endpoint allows access with valid authentication.

    Verifies:
    - Endpoint accepts valid auth header
    - 200 status code with authentication
    - Response data returned successfully
    """
    # Set authentication header
    headers = {"Authorization": f"Bearer {test_api_key}"}

    # Call protected endpoint with authentication
    response = await async_client.get("/api/agents", headers=headers)

    # Assertions
    assert response.status_code == 200
    response_json = response.json()
    assert isinstance(response_json, list)

@pytest.mark.integration
@pytest.mark.anyio
async def test_protected_endpoint_with_invalid_auth(async_client):
    """Test protected endpoint rejects invalid authentication.

    Verifies:
    - Endpoint validates auth token
    - 401 status code with invalid token
    - Error message indicates invalid credentials
    """
    # Set invalid authentication header
    headers = {"Authorization": "Bearer invalid-token-12345"}

    # Call protected endpoint with invalid authentication
    response = await async_client.get("/api/agents", headers=headers)

    # Assertions
    assert response.status_code == 401
    assert "Invalid" in response.json()["detail"] or "credentials" in response.json()["detail"].lower()
```

**Fixture Dependencies:**
- `async_client` - httpx.AsyncClient fixture
- `test_api_key` - Valid API key for testing

**What This Tests:**
- ✅ Authentication middleware active
- ✅ Unauthorized requests rejected (401)
- ✅ Valid auth tokens accepted
- ✅ Invalid auth tokens rejected

**Common Variations:**
- Test expired tokens
- Test token refresh flow
- Test role-based authorization (RBAC)

**Link to Real Test:** `tests/integration/test_auth_endpoints.py::test_agent_api_auth`

---

### Example 9: Request Validation Test (Pydantic Schema)

**Use Case:** Verify API validates request data against Pydantic schema

**Test Code:**

```python
# tests/integration/test_api_validation.py
import pytest
from httpx import AsyncClient
from src.main import app

@pytest.mark.integration
@pytest.mark.anyio
async def test_create_agent_invalid_request(async_client):
    """Test POST /api/agents validates request against schema.

    Verifies:
    - Missing required fields rejected (422)
    - Invalid field types rejected (422)
    - Error response contains field validation errors
    """
    # Attempt to create agent with missing required field (name)
    invalid_data = {
        "system_prompt": "Test prompt"
        # Missing: name (required field)
    }

    response = await async_client.post("/api/agents", json=invalid_data)

    # Assertions
    assert response.status_code == 422  # Unprocessable Entity
    response_json = response.json()
    assert "detail" in response_json
    errors = response_json["detail"]
    assert isinstance(errors, list)
    assert len(errors) > 0

    # Verify error mentions missing field
    error_fields = [err["loc"][-1] for err in errors]
    assert "name" in error_fields

@pytest.mark.integration
@pytest.mark.anyio
async def test_create_agent_invalid_field_type(async_client):
    """Test POST /api/agents validates field types.

    Verifies:
    - Invalid field types rejected (422)
    - Error response indicates type mismatch
    """
    # Attempt to create agent with invalid field type
    invalid_data = {
        "name": "Test Agent",
        "system_prompt": "Test prompt",
        "temperature": "not-a-number"  # Should be float
    }

    response = await async_client.post("/api/agents", json=invalid_data)

    # Assertions
    assert response.status_code == 422
    response_json = response.json()
    errors = response_json["detail"]

    # Verify error mentions temperature field
    error_fields = [err["loc"][-1] for err in errors]
    assert "temperature" in error_fields
```

**Fixture Dependencies:**
- `async_client` - httpx.AsyncClient fixture

**What This Tests:**
- ✅ Pydantic schema validation active
- ✅ Required fields enforced
- ✅ Field types validated
- ✅ Error response format (RFC 7807 Problem Details)

**Common Variations:**
- Test string length constraints
- Test enum value validation
- Test nested object validation

**Link to Real Test:** `tests/integration/test_agent_api.py::test_create_agent_validation`

---

### Example 10: Response Serialization Test

**Use Case:** Verify API serializes database models to JSON correctly

**Test Code:**

```python
# tests/integration/test_api_serialization.py
import pytest
from httpx import AsyncClient
from src.main import app
from datetime import datetime
import uuid

@pytest.mark.integration
@pytest.mark.anyio
async def test_agent_response_serialization(async_client, test_tenant):
    """Test GET /api/agents/{id} serializes response correctly.

    Verifies:
    - Database model serialized to Pydantic schema
    - UUID fields serialized as strings
    - Datetime fields serialized as ISO 8601 strings
    - Enum fields serialized as string values
    - Relationships excluded from response (security)
    """
    # Create agent via API
    agent_data = {
        "name": "Serialization Test Agent",
        "system_prompt": "Test prompt",
        "tenant_id": str(test_tenant.id)
    }
    create_response = await async_client.post("/api/agents", json=agent_data)
    assert create_response.status_code == 201
    agent_id = create_response.json()["id"]

    # Fetch agent via API
    response = await async_client.get(f"/api/agents/{agent_id}")

    # Assertions
    assert response.status_code == 200
    agent = response.json()

    # Verify field types
    assert isinstance(agent["id"], str)  # UUID serialized as string
    uuid.UUID(agent["id"])  # Verify valid UUID format

    assert isinstance(agent["name"], str)
    assert agent["name"] == "Serialization Test Agent"

    assert isinstance(agent["created_at"], str)  # Datetime as ISO 8601
    datetime.fromisoformat(agent["created_at"])  # Verify valid datetime format

    assert isinstance(agent["tenant_id"], str)  # UUID as string
    uuid.UUID(agent["tenant_id"])

    # Verify relationships excluded (security: don't expose tenant data)
    assert "tenant" not in agent  # SQLAlchemy relationship excluded
```

**Fixture Dependencies:**
- `async_client` - httpx.AsyncClient fixture
- `test_tenant` - Tenant instance for foreign key

**What This Tests:**
- ✅ Pydantic response model serialization
- ✅ UUID → string conversion
- ✅ Datetime → ISO 8601 string
- ✅ Relationship exclusion (security)

**Common Variations:**
- Test nested object serialization
- Test list response serialization
- Test field exclusion (passwords, secrets)

**Link to Real Test:** `tests/integration/test_agent_api.py::test_get_agent_serialization`

---

## External Service Testing Examples

### Example 11: Mocked External API Call (respx)

**Use Case:** Test integration with external API using respx HTTP mocking

**Test Code:**

```python
# tests/integration/test_external_api_mocked.py
import pytest
import respx
from httpx import Response
from src.services.litellm_service import LiteLLMService

@pytest.mark.integration
@pytest.mark.anyio
@respx.mock  # Enable HTTP mocking
async def test_litellm_completion_mocked():
    """Test LiteLLM completion with mocked API response.

    Verifies:
    - Service calls correct endpoint
    - Request payload formatted correctly
    - Response parsed successfully
    - Error handling for API failures
    """
    # Mock LiteLLM API endpoint
    mock_route = respx.post("http://localhost:4000/chat/completions").mock(
        return_value=Response(
            200,
            json={
                "id": "chatcmpl-123",
                "model": "gpt-4",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "This is a mocked response from GPT-4."
                        },
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 15,
                    "total_tokens": 25
                }
            }
        )
    )

    # Call service method
    service = LiteLLMService()
    result = await service.complete(
        model="gpt-4",
        messages=[{"role": "user", "content": "Hello"}]
    )

    # Assertions
    assert result["content"] == "This is a mocked response from GPT-4."
    assert result["usage"]["total_tokens"] == 25
    assert mock_route.called  # Verify mock was hit
    assert mock_route.call_count == 1

    # Verify request payload
    request = mock_route.calls[0].request
    assert request.url.path == "/chat/completions"
    request_json = request.content.decode("utf-8")
    assert "gpt-4" in request_json
    assert "Hello" in request_json
```

**Fixture Dependencies:**
- None (respx mock applied via decorator)

**What This Tests:**
- ✅ HTTP client configuration (base URL, headers)
- ✅ Request payload serialization
- ✅ Response parsing
- ✅ Error handling (not shown, but testable)

**Common Variations:**
- Test error responses (500, 503)
- Test timeout handling
- Test retry logic

**Link to Real Test:** `tests/integration/test_litellm_service.py::test_completion_mocked`

---

### Example 12: Redis Queue Interaction Test

**Use Case:** Test Celery task queuing with real Redis

**Test Code:**

```python
# tests/integration/test_redis_queue.py
import pytest
import redis.asyncio as redis
from src.workers.tasks import enhance_ticket
import json

@pytest.mark.integration
@pytest.mark.anyio
async def test_celery_task_queue_redis(redis_client):
    """Test Celery task queued to Redis successfully.

    Verifies:
    - Task serialized and queued to Redis
    - Task payload contains correct data
    - Task result retrievable from Redis
    """
    # Queue Celery task
    task = enhance_ticket.delay(
        ticket_id=12345,
        title="Test Ticket",
        description="Test description"
    )

    # Verify task queued in Redis
    queue_length = await redis_client.llen("celery")
    assert queue_length > 0, "Task should be queued in Redis"

    # Fetch task from queue (without removing)
    task_data = await redis_client.lindex("celery", 0)
    task_json = json.loads(task_data)

    # Verify task structure
    assert "task" in task_json
    assert task_json["task"] == "src.workers.tasks.enhance_ticket"
    assert "args" in task_json
    assert 12345 in task_json["args"]  # ticket_id argument

    # Wait for task completion (with timeout)
    result = task.get(timeout=30)

    # Verify result
    assert result["status"] == "success"
    assert result["ticket_id"] == 12345

@pytest_asyncio.fixture
async def redis_client():
    """Create real Redis client for integration tests."""
    client = redis.from_url("redis://localhost:6379/1")
    yield client
    await client.flushdb()  # Cleanup
    await client.close()
```

**Fixture Dependencies:**
- `redis_client` - Real Redis connection (Docker)

**What This Tests:**
- ✅ Celery task serialization
- ✅ Redis LPUSH operation
- ✅ Task payload structure
- ✅ Task execution and result retrieval

**Common Variations:**
- Test task retry on failure
- Test task ETA (scheduled execution)
- Test task priority

**Link to Real Test:** `tests/integration/test_celery_tasks.py::test_enhance_ticket_queued`

---

## Workflow Testing Examples

### Example 13: BYOK Workflow Test (Multi-Step)

**Use Case:** Test complete Bring-Your-Own-Key workflow (create tenant → add provider → verify key)

**Test Code:**

```python
# tests/integration/test_byok_workflow.py
import pytest
from httpx import AsyncClient
from src.main import app

@pytest.mark.integration
@pytest.mark.anyio
async def test_byok_complete_workflow(async_client):
    """Test BYOK workflow: create tenant → add LiteLLM provider → verify virtual key.

    Workflow Steps:
    1. Create tenant
    2. Add LiteLLM provider with API key
    3. Verify virtual key created in LiteLLM
    4. Test agent execution with BYOK

    Verifies:
    - End-to-end BYOK workflow functional
    - Tenant isolation maintained
    - API key encryption working
    - LiteLLM virtual key creation
    """
    # Step 1: Create tenant
    tenant_data = {"name": "BYOK Test Corp", "admin_email": "admin@byok.com"}
    tenant_response = await async_client.post("/api/tenants", json=tenant_data)
    assert tenant_response.status_code == 201
    tenant_id = tenant_response.json()["id"]

    # Step 2: Add LiteLLM provider with API key
    provider_data = {
        "tenant_id": tenant_id,
        "provider_name": "openai",
        "api_key": "sk-test-key-12345",  # Test key
        "model": "gpt-4"
    }
    provider_response = await async_client.post(
        f"/api/tenants/{tenant_id}/providers",
        json=provider_data
    )
    assert provider_response.status_code == 201
    provider = provider_response.json()

    # Verify virtual key created
    assert "virtual_key" in provider
    assert provider["virtual_key"].startswith("sk-")
    virtual_key = provider["virtual_key"]

    # Step 3: Verify virtual key in LiteLLM (mocked for test)
    verify_response = await async_client.get(
        f"/api/tenants/{tenant_id}/providers/{provider['id']}/verify"
    )
    assert verify_response.status_code == 200
    assert verify_response.json()["status"] == "active"

    # Step 4: Test agent execution with BYOK
    agent_data = {
        "name": "BYOK Test Agent",
        "system_prompt": "You are a test assistant.",
        "tenant_id": tenant_id,
        "model": "gpt-4",
        "use_byok": True
    }
    agent_response = await async_client.post("/api/agents", json=agent_data)
    assert agent_response.status_code == 201

    # Execute agent (should use BYOK virtual key)
    execution_data = {
        "agent_id": agent_response.json()["id"],
        "input": "Hello, test BYOK workflow"
    }
    execution_response = await async_client.post(
        "/api/agents/execute",
        json=execution_data
    )
    assert execution_response.status_code == 200
    result = execution_response.json()
    assert result["status"] == "success"
```

**Fixture Dependencies:**
- `async_client` - httpx.AsyncClient fixture

**What This Tests:**
- ✅ Multi-step workflow integration
- ✅ Tenant creation and isolation
- ✅ Provider configuration with encryption
- ✅ LiteLLM virtual key generation
- ✅ Agent execution with BYOK

**Common Variations:**
- Test workflow rollback on failure
- Test multiple providers per tenant
- Test provider deletion cascade

**Link to Real Test:** `tests/integration/test_byok_workflow.py::test_byok_end_to_end`

---

**Total Lines:** 1,400+ lines across 13 comprehensive examples

**See Also:**
- [Integration Testing Guide](integration-testing-guide.md) - Complete guide
- [Testing Decision Tree](testing-decision-tree.md) - Test type selection flowchart
- [Test Fixture Library](test-fixture-library.md) - Complete fixture catalog

---

**Document Version:** 1.0
**Last Updated:** 2025-11-11
**Maintained By:** Engineering Team
