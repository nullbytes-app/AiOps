# Testing Guide

This guide explains how to run, write, and manage tests for the AI Agents enhancement pipeline.

## Overview

The test suite uses **pytest** with **pytest-asyncio** for async support. Tests are organized into:
- **Unit tests** (`tests/unit/`) - Fast, isolated component tests with mocked dependencies
- **Integration tests** (`tests/integration/`) - End-to-end tests with real Docker dependencies
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

## References

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [FastAPI Testing](https://fastapi.tiangolo.com/advanced/testing-dependencies/)
