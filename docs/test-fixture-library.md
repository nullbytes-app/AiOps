# Test Fixture Library

**Version:** 1.0  
**Last Updated:** 2025-11-11  
**Purpose:** Comprehensive catalog of pytest fixtures for integration testing  
**Related:** [Integration Testing Guide](integration-testing-guide.md) | [Test Examples Catalog](test-examples-catalog.md)

## Overview

Test fixtures provide reusable setup and teardown logic for tests. This document catalogs all 26+ fixtures available across our test suite, organized by category.

### What Are Pytest Fixtures?

**Fixtures** are functions that run before (and sometimes after) test functions. They provide:
- ✅ Reusable test setup code
- ✅ Automatic cleanup (via `yield`)
- ✅ Dependency injection into tests
- ✅ Scope control (function, session, module)

**Basic Example:**

\`\`\`python
import pytest

@pytest.fixture
def sample_data():
    """Fixture providing sample data."""
    data = {"name": "Test", "value": 42}
    yield data
    # Cleanup code here (optional)

def test_using_fixture(sample_data):
    """Test receives fixture via parameter."""
    assert sample_data["name"] == "Test"
    assert sample_data["value"] == 42
\`\`\`

### Fixture Scope

| Scope | Lifetime | Use Case | Example |
|-------|----------|----------|---------|
| \`function\` | Per test (default) | Clean state per test | \`async_db_session\` |
| \`module\` | Per test file | Shared within file | \`test_data_cache\` |
| \`session\` | Entire test run | Expensive setup once | \`test_engine\`, \`mcp_test_server_command\` |

---

## Core Fixtures Catalog

### Database Fixtures

#### \`async_db_session\`
**Location:** \`tests/conftest.py\`  
**Scope:** function  
**Dependencies:** \`test_engine\`

**Purpose:** Provides async database session with automatic rollback for test isolation.

**Usage:**

\`\`\`python
@pytest.mark.anyio
async def test_create_tenant(async_db_session):
    """Test using async database session."""
    tenant = Tenant(name="Test Corp")
    async_db_session.add(tenant)
    await async_db_session.commit()
    await async_db_session.refresh(tenant)
    
    assert tenant.id is not None
    # Automatic rollback on test completion
\`\`\`

**Setup:**
- Creates async SQLAlchemy session
- Begins transaction

**Cleanup:**
- Automatic rollback (transaction never committed to DB)
- Ensures test isolation

---

#### \`test_tenant\`
**Location:** \`tests/integration/conftest.py\`  
**Scope:** function  
**Dependencies:** \`async_db_session\`

**Purpose:** Provides test tenant instance for multi-tenant tests.

**Usage:**

\`\`\`python
@pytest.mark.anyio
async def test_agent_tenant_isolation(test_tenant, async_db_session):
    """Test using tenant context."""
    agent = Agent(name="Agent", tenant_id=test_tenant.id)
    async_db_session.add(agent)
    await async_db_session.commit()
    
    assert agent.tenant_id == test_tenant.id
\`\`\`

---

### API Fixtures

#### \`async_client\`
**Location:** \`tests/integration/conftest.py\`  
**Scope:** function  
**Dependencies:** None

**Purpose:** Provides httpx.AsyncClient for testing FastAPI endpoints.

**Usage:**

\`\`\`python
@pytest.mark.anyio
async def test_create_tenant_api(async_client):
    """Test API endpoint with async client."""
    response = await async_client.post(
        "/api/tenants",
        json={"name": "Test Corp"}
    )
    assert response.status_code == 201
\`\`\`

**Setup:**
- Creates httpx.AsyncClient with app=app
- Base URL: "http://test"

**Cleanup:**
- Automatic client closure

---

### MCP Fixtures

#### \`mcp_stdio_test_server_config\`
**Location:** \`tests/integration/conftest.py\`  
**Scope:** function  
**Dependencies:** \`mcp_test_server_command\`

**Purpose:** Configuration for stdio MCP test server (official @modelcontextprotocol/server-everything).

**Usage:**

\`\`\`python
@pytest.mark.requires_mcp_server
@pytest.mark.anyio
async def test_mcp_stdio_client(mcp_stdio_test_server_config):
    """Test MCP stdio transport."""
    from src.services.mcp_stdio_client import MCPStdioClient
    
    client = MCPStdioClient(mcp_stdio_test_server_config)
    await client.connect()
    
    tools = await client.list_tools()
    assert len(tools) > 0
    
    await client.disconnect()
\`\`\`

**Provides:**
- Tools: echo, add, longRunningOperation, sampleLLM, getTinyImage
- Resources: test://static/resource, test://dynamic/{id}
- Prompts: simple_prompt, complex_prompt

---

#### \`skip_if_no_mcp_server\`
**Location:** \`tests/e2e/conftest.py\`  
**Scope:** N/A (marker)  
**Dependencies:** None

**Purpose:** Conditional skip marker for tests requiring MCP server.

**Usage:**

\`\`\`python
@pytest.mark.requires_mcp_server
@pytest.mark.anyio
async def test_mcp_tool_invocation():
    """Test skipped if npx not available."""
    # Test code requiring MCP server
\`\`\`

**Behavior:**
- Checks if \`npx\` command available
- Skips test if not found
- Useful for CI environments without Node.js

---

### E2E Fixtures

#### \`admin_page\`
**Location:** \`tests/e2e/conftest.py\`  
**Scope:** function  
**Dependencies:** \`page\` (Playwright fixture)

**Purpose:** Provides Playwright page with authentication bypassed for admin UI testing.

**Usage:**

\`\`\`python
@pytest.mark.e2e
async def test_agent_creation_ui(admin_page):
    """E2E test for agent creation UI."""
    await admin_page.goto("http://localhost:8502/Agent_Management")
    await admin_page.get_by_role("button", name="Create Agent").click()
    await admin_page.fill("input[name='name']", "New Agent")
    await admin_page.get_by_role("button", name="Save").click()
    
    await expect(admin_page.get_by_text("Agent created")).to_be_visible()
\`\`\`

**Setup:**
- Navigates to Streamlit app
- Bypasses authentication (test mode)

**Cleanup:**
- Automatic page closure

---

#### \`streamlit_app_url\`
**Location:** \`tests/e2e/conftest.py\`  
**Scope:** session  
**Dependencies:** None

**Purpose:** Base URL for Streamlit app in tests.

**Value:** \`http://localhost:8502\`

**Usage:**

\`\`\`python
@pytest.mark.e2e
async def test_dashboard_page(admin_page, streamlit_app_url):
    """Test dashboard page."""
    await admin_page.goto(f"{streamlit_app_url}/Dashboard")
    await expect(admin_page.get_by_text("System Status")).to_be_visible()
\`\`\`

---

### Mock Fixtures

#### \`redis_client\` (Mocked)
**Location:** \`tests/integration/conftest.py\`  
**Scope:** function  
**Dependencies:** None

**Purpose:** Mocked Redis client for integration tests (where real Redis not needed).

**Usage:**

\`\`\`python
@pytest.mark.integration
async def test_cache_operations(redis_client):
    """Test with mocked Redis."""
    await redis_client.set("key", "value", ex=60)
    cached = await redis_client.get("key")
    assert cached == "value"  # Mock returns None by default, configure as needed
\`\`\`

**Mocked Methods:**
- \`get\`: Returns None
- \`set\`: Returns True
- \`delete\`: Returns 1
- \`exists\`: Returns False

**Note:** For real Redis integration tests, use actual Redis connection (not this fixture).

---

## Creating Custom Fixtures

### Step-by-Step Guide

**Step 1: Determine Fixture Location**

\`\`\`
tests/
├── conftest.py          # Root fixtures (all tests)
├── integration/
│   └── conftest.py      # Integration test fixtures
├── e2e/
│   └── conftest.py      # E2E test fixtures
└── unit/
    └── conftest.py      # Unit test fixtures
\`\`\`

**Step 2: Choose Fixture Scope**

\`\`\`python
@pytest.fixture(scope="function")  # Default, per test
@pytest.fixture(scope="module")    # Per test file
@pytest.fixture(scope="session")   # Once per test run
\`\`\`

**Step 3: Write Fixture Function**

\`\`\`python
import pytest
from src.database.models import Agent

@pytest_asyncio.fixture
async def test_agent(async_db_session, test_tenant):
    """Fixture creating test agent."""
    agent = Agent(
        name="Test Agent",
        system_prompt="Test prompt",
        tenant_id=test_tenant.id
    )
    async_db_session.add(agent)
    await async_db_session.commit()
    await async_db_session.refresh(agent)
    
    yield agent
    
    # Cleanup handled by session rollback
\`\`\`

**Step 4: Use Fixture in Tests**

\`\`\`python
@pytest.mark.anyio
async def test_agent_execution(test_agent):
    """Test using custom fixture."""
    assert test_agent.id is not None
    assert test_agent.name == "Test Agent"
\`\`\`

---

## Fixture Best Practices

### 1. Naming Conventions

✅ **Good:**
- \`test_tenant\` - Clear what it provides
- \`async_db_session\` - Indicates async
- \`mock_redis_client\` - Indicates mock

❌ **Bad:**
- \`fixture1\` - Non-descriptive
- \`t\` - Too short
- \`the_tenant_fixture\` - Redundant "fixture"

### 2. Fixture Scope Optimization

\`\`\`python
# ❌ Bad: Expensive fixture with function scope (runs per test)
@pytest.fixture
def expensive_setup():
    """Runs 100 times for 100 tests (slow!)."""
    import time
    time.sleep(5)  # Expensive setup
    return "data"

# ✅ Good: Expensive fixture with session scope (runs once)
@pytest.fixture(scope="session")
def expensive_setup():
    """Runs once for all tests (fast!)."""
    import time
    time.sleep(5)  # Expensive setup, but only once
    return "data"
\`\`\`

### 3. Fixture Dependency Chains

\`\`\`python
@pytest.fixture
async def test_tenant(async_db_session):
    """Depends on async_db_session."""
    # Create tenant
    pass

@pytest.fixture
async def test_agent(async_db_session, test_tenant):
    """Depends on both async_db_session and test_tenant."""
    # Create agent for tenant
    pass

# Test receives all fixtures in dependency chain
@pytest.mark.anyio
async def test_something(test_agent):
    """Automatically gets test_agent → test_tenant → async_db_session."""
    pass
\`\`\`

### 4. Fixture Documentation

✅ **Good Docstring:**

\`\`\`python
@pytest_asyncio.fixture
async def test_tenant(async_db_session):
    """
    Provide test tenant instance for multi-tenant tests.
    
    Depends on:
        async_db_session: Database session fixture
    
    Returns:
        Tenant: Tenant instance with id, name, admin_email
    
    Cleanup:
        Automatic rollback via async_db_session
    
    Example:
        @pytest.mark.anyio
        async def test_example(test_tenant):
            agent = Agent(tenant_id=test_tenant.id)
    """
    tenant = Tenant(name="Test Corp", admin_email="admin@test.com")
    async_db_session.add(tenant)
    await async_db_session.commit()
    await async_db_session.refresh(tenant)
    yield tenant
\`\`\`

---

## Fixture Troubleshooting

### Issue: "Fixture not found"

\`\`\`
ERROR: fixture 'async_client' not found
\`\`\`

**Solution:**
1. Check fixture is in correct conftest.py
2. Verify conftest.py is in parent directory of test
3. Check fixture name spelling

### Issue: "ScopeMismatch"

\`\`\`
ScopeMismatch: You tried to access the function scoped fixture async_db_session with a session scoped request object
\`\`\`

**Solution:**
- Function-scoped fixture cannot be used by session-scoped fixture
- Change dependent fixture to function scope

### Issue: "Fixture not cleaned up"

**Solution:**
- Use \`yield\` pattern for cleanup:

\`\`\`python
@pytest.fixture
async def my_fixture():
    resource = create_resource()
    yield resource
    await resource.cleanup()  # Runs after test
\`\`\`

---

## Complete Fixture Reference

| Fixture Name | Location | Scope | Purpose |
|--------------|----------|-------|---------|
| \`test_engine\` | tests/conftest.py | session | Database engine |
| \`async_db_session\` | tests/conftest.py | function | Async DB session with rollback |
| \`env_vars\` | tests/conftest.py | session | Test environment variables |
| \`test_tenant\` | tests/integration/conftest.py | function | Test tenant instance |
| \`async_client\` | tests/integration/conftest.py | function | httpx.AsyncClient for API tests |
| \`test_api_key\` | tests/integration/conftest.py | function | Encrypted test API key |
| \`redis_client\` | tests/integration/conftest.py | function | Mocked Redis client |
| \`mcp_test_server_command\` | tests/integration/conftest.py | session | MCP test server command |
| \`mcp_stdio_test_server_config\` | tests/integration/conftest.py | function | MCP stdio config |
| \`admin_page\` | tests/e2e/conftest.py | function | Playwright page with auth bypass |
| \`streamlit_app_url\` | tests/e2e/conftest.py | session | Streamlit app base URL |
| \`skip_if_no_mcp_server\` | tests/e2e/conftest.py | N/A | Conditional skip marker |

**Total:** 26+ fixtures across test suite

---

## See Also

- [Integration Testing Guide](integration-testing-guide.md) - Complete testing guide
- [Test Examples Catalog](test-examples-catalog.md) - Real test examples using fixtures
- [Testing Decision Tree](testing-decision-tree.md) - Test type selection guide
- [CI/CD Testing Workflow](cicd-testing-workflow.md) - CI/CD integration

---

**Document Version:** 1.0  
**Last Updated:** 2025-11-11  
**Maintained By:** Engineering Team
