# Testing Guide

This guide explains how to run, write, and manage tests for the AI Agents enhancement pipeline.

## Overview

The test suite uses **pytest** with **pytest-asyncio** for async support. Tests are organized into:
- **Unit tests** (`tests/unit/`) - Fast, isolated component tests with mocked dependencies
- **Integration tests** (`tests/integration/`) - End-to-end tests with real Docker dependencies
- **E2E UI tests** (`tests/e2e/`) - Playwright browser automation for critical UI workflows
- **Fixtures** (`tests/fixtures/`) - Reusable test data

**Test Coverage Target:** >80% for all modules in `src/`
**Test Execution Time:** <5 minutes for all tests
**Naming Convention:** `test_<component>_<scenario>_<expected_result>`

## Running Tests

### All Tests
```bash
pytest
pytest -v  # Verbose output
```

### Unit Tests Only (Fast, No Docker Required)
```bash
pytest tests/unit/
pytest tests/unit/ -v
```

### Integration Tests Only (Requires Docker)
```bash
# Start dependencies first
docker-compose up -d postgres redis

# Run integration tests
pytest tests/integration/
```

### Specific Test File
```bash
pytest tests/unit/test_llm_synthesis.py -v
```

### Specific Test Function
```bash
pytest tests/unit/test_llm_synthesis.py::test_synthesis_timeout_returns_fallback -v
```

### With Coverage Report
```bash
pytest --cov=src --cov-report=html --cov-report=term-missing
# View HTML report: open htmlcov/index.html
```

### Run Specific Test and Stop on First Failure
```bash
pytest tests/unit/ -x  # Stop at first failure
pytest tests/unit/ --tb=short  # Short traceback format
```

## Test Structure

### Unit Tests (`tests/unit/`)

Unit tests isolate components and mock external dependencies (database, Redis, APIs).

```
tests/unit/
├── test_llm_synthesis.py          # Story 2.9: LLM synthesis tests
├── test_langgraph_workflow.py      # Story 2.8: Workflow orchestration tests
├── test_servicedesk_client.py      # Story 2.10: ServiceDesk API client (29 tests, 100% coverage)
├── test_celery_tasks.py            # Story 2.11: Celery task tests
├── test_ticket_search_service.py   # Story 2.5: Ticket history search
├── test_kb_search.py               # Story 2.6: Knowledge base search
├── test_ip_lookup.py               # Story 2.7: IP address extraction
└── ...
```

### Integration Tests (`tests/integration/`)

Integration tests run against real Docker-deployed services (PostgreSQL, Redis).

```
tests/integration/
├── test_end_to_end_workflow.py     # Full pipeline: webhook → context → LLM → update
├── test_celery_tasks.py            # Celery task execution with real queue
└── ...
```

### Fixtures (`tests/fixtures/`)

Reusable test data organized by domain:

```
tests/fixtures/
├── __init__.py
├── tickets.py           # Sample ticket payloads, history
├── context.py          # WorkflowState objects, context scenarios
├── llm_responses.py    # OpenRouter API response mocks
└── api_responses.py    # ServiceDesk Plus API response mocks
```

## Writing Tests

### Basic Unit Test Pattern

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_llm_synthesis_success():
    """Test successful LLM synthesis with valid context."""
    # Arrange
    context = {
        "similar_tickets": [{"title": "Similar issue"}],
        "kb_articles": [{"content": "Knowledge base"}],
    }

    # Act
    result = await synthesize_enhancement(context, correlation_id="test-123")

    # Assert
    assert len(result) <= 500  # 500-word limit
    assert "Similar issue" in result
```

### Mocking External APIs

```python
from unittest.mock import patch, AsyncMock

@patch('src.services.llm_synthesis.openrouter_client')
async def test_llm_timeout_fallback(mock_client):
    """Test fallback formatting when LLM times out."""
    # Setup mock to raise timeout
    mock_client.chat.completions.create = AsyncMock(
        side_effect=asyncio.TimeoutError()
    )

    # Act
    result = await synthesize_enhancement(context)

    # Assert
    assert "Similar Tickets:" in result  # Fallback format
```

### Async Test Pattern

```python
@pytest.mark.asyncio
async def test_async_function():
    """Use @pytest.mark.asyncio for async test functions."""
    result = await some_async_function()
    assert result is not None
```

## Fixtures

### Using Fixtures

```python
@pytest.fixture
def sample_context():
    """Fixture providing sample context."""
    return {
        "ticket_id": "TKT-001",
        "similar_tickets": [...]
    }

def test_with_fixture(sample_context):
    """Test that uses the fixture."""
    assert sample_context["ticket_id"] == "TKT-001"
```

### Creating Custom Fixtures

Add to `tests/conftest.py`:

```python
@pytest.fixture
def my_fixture():
    """Custom test fixture."""
    # Setup
    data = {"key": "value"}
    yield data
    # Teardown (optional)
```

## Common Issues & Troubleshooting

### Docker Not Running
```
Error: Database connection refused
Solution: docker-compose up -d postgres redis
```

### Environment Variables Missing
```
Error: AttributeError: 'NoneType' object has no attribute 'celery_broker_url'
Solution: conftest.py sets defaults, or set manually: export AI_AGENTS_REDIS_URL=...
```

### Test Collection Errors
```
Error: Import error when collecting tests
Solution: Ensure PYTHONPATH includes project root: export PYTHONPATH=.
```

### Async Test Issues
```
Error: RuntimeError: no running event loop
Solution: Use @pytest.mark.asyncio decorator on async test functions
```

### Flaky Tests (Timing Issues)
```
Problem: Tests pass sometimes, fail other times
Solution: Use mocks instead of real sleep(), use pytest.mark.timeout(5)
```

## Debugging Tests

### Verbose Output
```bash
pytest -vv tests/unit/test_llm_synthesis.py
```

### Detailed Failure Information
```bash
pytest --tb=long tests/unit/test_llm_synthesis.py
```

### Drop into Debugger on Failure
```bash
pytest --pdb tests/unit/test_llm_synthesis.py
# Use 'c' to continue, 'q' to quit, 'n' to next line
```

### Capture Print Statements
```bash
pytest -s tests/unit/test_llm_synthesis.py  # Show print() output
```

## Coverage

### Generate Coverage Report
```bash
pytest --cov=src --cov-report=html --cov-report=term-missing
open htmlcov/index.html
```

### Check Coverage for Specific Module
```bash
pytest --cov=src.services.llm_synthesis tests/unit/test_llm_synthesis.py --cov-report=term-missing
```

### Coverage Requirements
- **Overall:** >80% across `src/`
- **Critical modules:** `src/enhancement/`, `src/services/`, `src/workers/` must be >80%
- **Exclusions:** `__init__.py` files, explicit `# pragma: no cover` comments

## CI/CD Integration

Tests run automatically in GitHub Actions for every PR:

1. **Lint Stage** - Black, Ruff, Mypy (must pass)
2. **Unit Tests** - `pytest tests/unit/` (must pass, <2 min)
3. **Integration Tests** - `pytest tests/integration/` (must pass, <5 min)
4. **Coverage Report** - Enforce >80% threshold

Check `.github/workflows/ci.yml` for pipeline configuration.

## Best Practices

1. **Test Naming:** Use descriptive names that explain what's being tested
   - ✅ `test_llm_synthesis_timeout_returns_fallback_text`
   - ❌ `test_llm_fails`

2. **Arrange-Act-Assert:** Structure tests clearly
   ```python
   # Arrange - setup test data
   # Act - perform action
   # Assert - verify results
   ```

3. **Mock External Dependencies:** Unit tests must mock APIs, databases
   ```python
   @patch('src.services.external_api.client')
   def test_with_mock(mock_client):
       ...
   ```

4. **Test Edge Cases:** Include happy path, edge cases, error scenarios
   - Empty results
   - Timeout
   - Invalid input
   - Partial failures

5. **Keep Tests Fast:** Use mocks, avoid real I/O in unit tests
   - Integration tests <5s each
   - Full suite <5 minutes

6. **Document Complex Setups:** Add comments for non-obvious test logic
   ```python
   # Mock response structure matches OpenRouter API format
   ```

## MCP Integration Testing (Story 11.2.6)

### MCP Test Server Setup

Integration tests for MCP (Model Context Protocol) require a test server that implements all three MCP primitives: tools, resources, and prompts.

#### Quick Start

```bash
# Install MCP test server (only needed once)
npm install

# Run MCP integration tests
pytest tests/integration/test_mcp_*.py -v
```

#### Test Server Details

We use the official `@modelcontextprotocol/server-everything` package which provides:

**Tools:**
- `echo` - Echo back input text
- `add` - Add two numbers
- `longRunningOperation` - Simulate long-running task
- `sampleLLM` - Mock LLM call
- `getTinyImage` - Return a small test image

**Resources:**
- `test://static/resource` - Static test resource
- `test://dynamic/{id}` - Dynamic resource with parameter

**Prompts:**
- `simple_prompt` - Basic prompt template
- `complex_prompt` - Multi-argument prompt

#### Test Fixtures

Integration tests use fixtures from `tests/integration/conftest.py`:

```python
@pytest.mark.usefixtures("skip_if_no_mcp_server")
async def test_tool_invocation(mcp_stdio_client):
    """Test calling MCP tools via stdio transport."""
    tools = await mcp_stdio_client.list_tools()
    assert len(tools) > 0

    # Call echo tool
    result = await mcp_stdio_client.call_tool("echo", {"message": "test"})
    assert "test" in str(result)
```

**Available Fixtures:**
- `mcp_stdio_test_server_config` - Config for stdio test server
- `mcp_stdio_client` - Initialized stdio client
- `skip_if_no_mcp_server` - Skip test if npx not available

#### Running Tests Without npx

If `npx` is not available, MCP integration tests will be automatically skipped:

```bash
$ pytest tests/integration/test_mcp_*.py
================= 15 skipped (npx not available) =================
```

To install Node.js/npx:
- **macOS**: `brew install node`
- **Ubuntu**: `sudo apt install nodejs npm`
- **Windows**: Download from [nodejs.org](https://nodejs.org/)

#### Troubleshooting

**Test Server Won't Start:**
```
Error: Command 'npx' not found
Solution: Install Node.js (see above)
```

**Test Server Times Out:**
```
Error: TimeoutError during client.initialize()
Solution: Increase timeout in test or check firewall settings
```

**Permission Denied:**
```
Error: EACCES: permission denied, mkdir '/Users/.../.npm/_npx'
Solution: Fix npm permissions: npm config set cache ~/.npm --global
```

## Test Health Monitoring (Story 12.1)

### Test Health Check Script

The test health check script (`scripts/test-health-check.py`) calculates test metrics and enforces quality thresholds:

```bash
# Run tests and generate health report
python scripts/test-health-check.py --run-tests --markdown-output docs/test-health-report.md

# Check existing test results
python scripts/test-health-check.py --json-report test-results.json

# Track metrics over time
python scripts/test-health-check.py --run-tests --save-history test-metrics-history.json
```

**Metrics Calculated:**
- **Pass Rate**: (passing / non-skipped) × 100
- **Skip Rate**: (skipped / total) × 100
- **Failure Rate**: (failed + error) / total × 100
- **Test Counts**: PASSED, FAILED, ERROR, SKIPPED

**Threshold Enforcement:**
- Exits with code 0 if pass rate ≥ 95%
- Exits with code 1 if pass rate < 95% (fails CI/CD pipeline)

### CI/CD Baseline Enforcement

The baseline check script (`scripts/ci-baseline-check.py`) prevents test regressions:

```bash
# Create baseline from current test results (main branch only)
python scripts/ci-baseline-check.py --update-baseline

# Check PR against baseline (feature branches)
python scripts/ci-baseline-check.py --baseline test-baseline.json
```

**Enforcement Rules:**
1. ❌ FAIL if new test failures introduced (tests passing in baseline now fail)
2. ❌ FAIL if pass rate drops below 95%
3. ❌ FAIL if total test count decreases unexpectedly (>10 tests deleted)
4. ✅ PASS if all baseline-passing tests still pass and pass rate ≥95%

**Workflow:**
- **Main branch**: Updates baseline after successful merge
- **Feature branches**: Compared against baseline, blocks merge if violations detected

### Test Plugins

The test suite uses additional pytest plugins for reporting and coverage:

```bash
# HTML test report
pytest --html=test-report.html --self-contained-html

# JSON report for automation
pytest --json-report --json-report-file=test-results.json

# Coverage report
pytest --cov=src --cov-report=html --cov-report=term-missing
```

**Plugin Dependencies** (in `pyproject.toml`):
- `pytest-html>=4.1.1` - HTML test reports
- `pytest-json-report>=1.5.0` - JSON reports for CI/CD automation
- `pytest-cov>=7.0.0` - Code coverage analysis

## E2E UI Testing with Playwright (Story 12.5)

### Overview

E2E (end-to-end) UI tests use Playwright for browser automation to validate complete user workflows in the Streamlit admin interface. These tests prevent UI integration bugs where functions exist but are never called (Story 11.2.5 regression).

**What E2E Tests Validate:**
- Actual UI rendering (not mocked)
- Navigation between pages
- Form interactions (fill, select, click)
- Data persistence after submission
- Full user workflows from start to finish

**3 Critical Workflows Tested:**
1. **MCP Server Registration & Discovery** - Create MCP server, trigger tool discovery
2. **Agent Tool Assignment** - Assign MCP tools to agent via UI tabs
3. **Agent Execution with MCP Tools** - Execute agent, verify MCP tool invoked, check history

### Setup Instructions

#### 1. Install Playwright and Dependencies

```bash
# Install Playwright Python package
pip install playwright pytest-playwright

# Install Playwright browser binaries (Chromium)
playwright install chromium

# Verify installation
playwright --version
```

#### 2. Verify Node.js Installed (Required for MCP Test Server)

```bash
# Check Node.js version (18+ required)
node --version

# Install if needed:
# macOS: brew install node
# Ubuntu: sudo apt install nodejs npm
# Windows: Download from nodejs.org
```

#### 3. Install MCP Test Dependencies

```bash
npm install
```

### Running E2E Tests Locally

#### Basic Execution

```bash
# Step 1: Start Streamlit app on test port
TESTING=true streamlit run src/admin/app.py --server.port=8502

# Step 2: Run E2E tests (in separate terminal)
pytest tests/e2e/ -v
```

#### Run Specific Workflow Test

```bash
pytest tests/e2e/test_mcp_server_registration_workflow.py -v
pytest tests/e2e/test_agent_tool_assignment_workflow.py -v
pytest tests/e2e/test_agent_execution_mcp_workflow.py -v
```

#### Run in Headed Mode (See Browser)

```bash
# Watch test execute in visible browser window
pytest tests/e2e/ --headed
```

#### Run with Slow Motion (Debug Mode)

```bash
# Slow down test execution (1000ms = 1 second per action)
pytest tests/e2e/ --headed --slowmo=1000
```

#### Run with Screenshots and Videos

```bash
# Capture screenshots on failure
pytest tests/e2e/ --screenshot=only-on-failure

# Record video of failed tests
pytest tests/e2e/ --video=retain-on-failure

# Enable tracing for debugging
pytest tests/e2e/ --tracing=retain-on-failure
```

### Debugging Failed E2E Tests

#### View Test Artifacts

E2E test artifacts are saved automatically on test failure:

```bash
# Screenshots
open tests/e2e/screenshots/

# Videos
open tests/e2e/videos/

# Traces (detailed execution logs)
playwright show-trace tests/e2e/traces/trace.zip
```

#### Run Single Test with Debugging

```bash
# Run specific test in headed mode with slow motion
pytest tests/e2e/test_agent_tool_assignment_workflow.py::test_agent_tool_assignment_workflow --headed --slowmo=500
```

#### Enable Debug Logging

```bash
# Show Playwright debug logs
DEBUG=pw:api pytest tests/e2e/ -v

# Show Streamlit app logs
streamlit run src/admin/app.py --server.port=8502 --logger.level=debug
```

### Writing New E2E Tests

#### Test Structure

```python
import pytest
from playwright.sync_api import Page, expect

@pytest.mark.e2e
@pytest.mark.slow
def test_my_workflow(
    admin_page: Page,
    streamlit_app_url: str,
    test_tenant: Tenant
) -> None:
    """Test description."""
    page = admin_page

    # Step 1: Navigate to page
    page.goto(f"{streamlit_app_url}/My_Page")

    # Step 2: Interact with UI
    page.get_by_role("button", name="Submit").click()

    # Step 3: Verify results
    expect(page.locator("text=Success")).to_be_visible()
```

#### Playwright 2025 Best Practices

**✅ DO: Use Accessibility-Based Selectors**

```python
# GOOD: Robust, accessible selectors
page.get_by_role("button", name="Submit").click()
page.get_by_label("Email").fill("user@example.com")
page.get_by_text("Welcome back").click()
```

**❌ DON'T: Use Fragile CSS Selectors**

```python
# BAD: Streamlit auto-generates CSS classes (breaks easily)
page.locator(".css-1234abcd").click()
page.locator("#submit-button-id").click()
```

**✅ DO: Use Auto-Waiting Assertions**

```python
# GOOD: Automatically waits for condition or timeout
expect(page.locator("text=Success")).to_be_visible()
expect(page).to_have_url("**/dashboard")
```

**❌ DON'T: Use Manual Timeouts**

```python
# BAD: Flaky, slow, unreliable
page.wait_for_timeout(5000)
time.sleep(5)
```

**✅ DO: Take Screenshots on Specific Components**

```python
# GOOD: Screenshot specific section for debugging
page.locator(".mcp-tools-section").screenshot(path="mcp-tools.png")
```

**❌ DON'T: Take Full Page Screenshots**

```python
# BAD: Slow, large file size
page.screenshot(path="full-page.png", full_page=True)
```

#### Available Fixtures

E2E tests have access to fixtures from `tests/e2e/conftest.py`:

```python
# Streamlit app fixtures
streamlit_app_url: str             # Base URL (http://localhost:8502)
admin_page: Page                   # Playwright page with auth bypassed

# Database fixtures
async_db_session: AsyncSession     # Async database session
test_tenant: Tenant                # Test tenant (auto-cleanup)
test_mcp_server: MCPServer         # Test MCP server (auto-cleanup)
test_agent: Agent                  # Test agent (auto-cleanup)
```

#### Test Data Cleanup

Test fixtures automatically clean up data after each test:

```python
@pytest.fixture
async def test_mcp_server(async_db_session, test_tenant):
    """Create test MCP server, auto-delete after test."""
    server = MCPServer(...)
    async_db_session.add(server)
    await async_db_session.commit()

    yield server

    # Automatic cleanup via rollback (handled by async_db_session fixture)
```

### Troubleshooting

#### Streamlit App Not Responding

```
Error: TimeoutError: page.goto: Timeout 30000ms exceeded
Solution: Ensure Streamlit app is running on port 8502
  TESTING=true streamlit run src/admin/app.py --server.port=8502
```

#### Browser Binaries Not Installed

```
Error: Executable doesn't exist at /path/to/chromium
Solution: Install Playwright browsers
  playwright install chromium
```

#### Port Already in Use

```
Error: OSError: [Errno 48] Address already in use
Solution: Kill process on port 8502 or use different port
  lsof -i :8502 | grep LISTEN | awk '{print $2}' | xargs kill
```

#### MCP Test Server Not Found

```
Error: Command 'npx' not found
Solution: Install Node.js (see Node.js installation above)
```

#### Test Data Not Cleaned Up

```
Problem: Test creates data but doesn't delete it
Solution: Fixtures handle cleanup automatically via rollback
  Ensure test uses test_tenant, test_mcp_server, test_agent fixtures
```

### CI/CD Integration

E2E tests run automatically in GitHub Actions (`.github/workflows/ci.yml`):

**Job: e2e-tests** (runs after lint-and-test)
1. Install Playwright and browsers
2. Start Streamlit app in background
3. Wait for app healthy (health check endpoint)
4. Run E2E tests
5. Upload artifacts (screenshots, videos, traces) on failure

**E2E Test Failures Block PR Merge** - If any E2E test fails, PR cannot be merged until fixed.

### Performance

E2E tests are designed for fast execution:

- **Target:** <5 minutes for all 3 workflow tests
- **Individual test:** <90 seconds per workflow
- **Headless mode:** ~30% faster than headed mode
- **Parallel execution:** NOT recommended (Streamlit app state conflicts)

### References

- [Playwright Python Documentation](https://playwright.dev/python/)
- [Playwright Locators Guide](https://playwright.dev/python/docs/locators)
- [Playwright Assertions](https://playwright.dev/python/docs/test-assertions)
- [pytest-playwright Plugin](https://pytest-playwright.readthedocs.io/)
- [Streamlit Testing Best Practices](https://docs.streamlit.io/develop/concepts/app-testing)

## References

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [FastAPI Testing](https://fastapi.tiangolo.com/advanced/testing-dependencies/)
- [Model Context Protocol (MCP)](https://spec.modelcontextprotocol.io/)
