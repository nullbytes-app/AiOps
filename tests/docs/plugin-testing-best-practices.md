# Plugin Testing Best Practices

**Story:** 7.6 - Plugin Testing Framework and Mock Plugins
**Last Updated:** 2025-11-05

This guide covers best practices, example test cases, CI/CD integration, and troubleshooting for plugin testing.

## Table of Contents

1. [Best Practices](#best-practices)
2. [Example Test Cases](#example-test-cases)
3. [CI/CD Integration](#cicd-integration)
4. [Troubleshooting](#troubleshooting)

---

## Best Practices

### 1. Test Isolation

**Always use fixtures over creating instances directly** to ensure test isolation.

✅ **Good:**
```python
def test_webhook(mock_generic_plugin):
    # Fresh instance per test
    await mock_generic_plugin.validate_webhook(payload, sig)
```

❌ **Bad:**
```python
plugin = MockTicketingToolPlugin.success_mode()  # Shared across tests
```

### 2. Test Both Success and Failure Paths

**Every plugin method should have tests for:**
- Success case
- Failure case (API error, timeout, auth error)
- Edge case (empty response, malformed payload)

```python
# Success
async def test_get_ticket_success(mock_generic_plugin):
    ticket = await mock_generic_plugin.get_ticket("t1", "123")
    assert ticket is not None

# Failure
async def test_get_ticket_api_error():
    plugin = MockTicketingToolPlugin.api_error_mode()
    with pytest.raises(ServiceDeskAPIError):
        await plugin.get_ticket("t1", "123")

# Edge case
async def test_get_ticket_not_found():
    plugin = MockTicketingToolPlugin.not_found_mode()
    ticket = await plugin.get_ticket("t1", "non-existent")
    assert ticket is None
```

### 3. Use Call Tracking for Integration Points

**Verify plugin methods were called** with correct arguments.

```python
async def test_workflow(mock_generic_plugin):
    # Perform workflow
    await run_enhancement_workflow(mock_generic_plugin)

    # Verify plugin was called correctly
    assert_plugin_called(mock_generic_plugin, "validate_webhook", times=1)
    assert_plugin_called(mock_generic_plugin, "get_ticket", times=1)
    assert_plugin_called_with(
        mock_generic_plugin,
        "update_ticket",
        content="enhancement content"
    )
```

### 4. Validate TicketMetadata in extract_metadata Tests

**Always validate metadata structure:**

```python
def test_extract_metadata(mock_generic_plugin):
    payload = build_generic_payload()
    metadata = mock_generic_plugin.extract_metadata(payload)

    # Use helper for comprehensive validation
    assert_ticket_metadata_valid(metadata)

    # Then assert specific values
    assert metadata.tenant_id == "expected"
```

### 5. Test Edge Cases

**Test malformed payloads, missing fields:**

```python
def test_extract_metadata_missing_fields(mock_generic_plugin):
    payload = {"tenant_id": "test"}  # Missing most fields
    metadata = mock_generic_plugin.extract_metadata(payload)
    # Should not raise exception, uses defaults
    assert_ticket_metadata_valid(metadata)
```

### 6. Keep Unit Tests Fast

**Target: <100ms per unit test**

✅ Use mock plugin (no I/O)
✅ Test plugin methods in isolation
❌ Don't make real API calls in unit tests

### 7. Follow Pytest Naming Conventions

**File names:** `test_*.py` or `*_test.py`
**Test classes:** `Test*`
**Test functions:** `test_*`

```python
# File: tests/unit/test_mock_plugin.py
class TestFactoryMethods:
    def test_success_mode(self):
        ...
```

---

## Example Test Cases

### Example 1: Unit Test for Plugin Method

```python
import pytest
from tests.mocks.mock_plugin import MockTicketingToolPlugin

@pytest.mark.unit
@pytest.mark.plugin
@pytest.mark.asyncio
async def test_validate_webhook_success():
    """Test validate_webhook returns True in success mode."""
    plugin = MockTicketingToolPlugin.success_mode()

    valid = await plugin.validate_webhook(
        payload={"ticket": "data"},
        signature="test-signature"
    )

    assert valid is True
```

### Example 2: Integration Test with Mock Plugin Manager

```python
@pytest.mark.integration
@pytest.mark.plugin
def test_plugin_routing(mock_plugin_manager):
    """Test PluginManager routes to correct plugin."""
    from src.plugins.registry import PluginManager
    from tests.mocks.mock_plugin import MockTicketingToolPlugin

    plugin = PluginManager().get_plugin("servicedesk_plus")
    assert isinstance(plugin, MockTicketingToolPlugin)
```

### Example 3: Parameterized Test with Failure Modes

```python
@pytest.mark.asyncio
@pytest.mark.plugin
async def test_handle_failures(plugin_failure_mode):
    """Test handles all plugin failure modes gracefully."""
    plugin = plugin_failure_mode

    # Test that workflow handles failure appropriately
    # (implementation depends on failure type)
    try:
        await plugin.get_ticket("tenant-1", "ticket-123")
    except Exception as e:
        # Log error and continue workflow
        assert e is not None
```

### Example 4: Testing Backward Compatibility

```python
@pytest.mark.asyncio
async def test_backward_compatibility_with_existing_tests():
    """Ensure new mock plugin doesn't break existing tests."""
    # Existing tests should still pass
    from tests.unit.test_servicedesk_plugin import test_validate_webhook_success

    # Run existing test (should not raise)
    await test_validate_webhook_success()
```

---

## CI/CD Integration

### Pytest Markers

Define in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "unit: Unit tests (fast, isolated)",
    "integration: Integration tests (database, Redis)",
    "plugin: Plugin-related tests (all layers)",
]
```

### Running Plugin Tests

```bash
# Run all plugin tests
pytest -m plugin -v

# Run only plugin unit tests
pytest -m "unit and plugin" -v

# Run only plugin integration tests
pytest -m "integration and plugin" -v

# Run specific test file
pytest tests/unit/test_mock_plugin.py -v

# Run with coverage
pytest -m plugin --cov=src/plugins --cov=tests/mocks --cov-report=html
```

### GitHub Actions Workflow

```yaml
# .github/workflows/ci.yml
jobs:
  test-plugins:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run plugin unit tests
        run: pytest -m "unit and plugin" -v

      - name: Run plugin integration tests
        run: pytest -m "integration and plugin" -v

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Troubleshooting

### Issue: Mock plugin not registering in PluginManager

**Symptoms:** `PluginNotFoundError` when calling `PluginManager().get_plugin()`

**Solution:** Use `mock_plugin_manager` fixture which patches singleton:

```python
def test_routing(mock_plugin_manager):
    # mock_plugin_manager fixture handles patching
    plugin = PluginManager().get_plugin("tool_type")
```

### Issue: Async tests hanging

**Symptoms:** Test never completes, pytest hangs

**Solutions:**
1. Ensure `@pytest.mark.asyncio` decorator present
2. Check for unawaited coroutines (use `await` for async calls)
3. Verify pytest-asyncio installed: `pip install pytest-asyncio`

```python
# ✅ Correct
@pytest.mark.asyncio
async def test_async_method():
    result = await plugin.get_ticket("t1", "123")

# ❌ Incorrect (missing await)
async def test_async_method():
    result = plugin.get_ticket("t1", "123")  # Returns coroutine!
```

### Issue: Call history not tracking

**Symptoms:** `get_call_history()` returns empty list

**Solutions:**
1. Only async methods tracked (extract_metadata is sync, not tracked)
2. Ensure `reset_call_history()` not called before assertions
3. Use fixture to get fresh plugin instance

```python
# ✅ Fixture provides fresh instance
def test_tracking(mock_generic_plugin):
    # Clean call history
    assert len(mock_generic_plugin.get_call_history()) == 0
```

### Issue: Type errors with mypy

**Symptoms:** `mypy --strict` reports type errors

**Solutions:**
1. Import types from `typing` module
2. Use `Optional[]` for nullable fields
3. Add type hints to all function signatures

```python
from typing import Optional, Dict, Any

def get_ticket_response() -> Optional[Dict[str, Any]]:
    return {"id": "123"} if condition else None
```

---

## References

- [Plugin Testing Guide](../README-plugins.md) - Main testing guide with overview and fixtures
- [Plugin API Reference](./plugin-api-reference.md) - Complete test utilities API documentation
- [Plugin Architecture Guide](../../docs/plugin-architecture.md) - Overview of plugin system architecture
- [Existing Plugin Tests](../unit/test_servicedesk_plugin.py) - ServiceDesk Plus plugin test examples
- [Pytest Documentation](https://docs.pytest.org) - Official pytest documentation
- [Pytest Async](https://pytest-asyncio.readthedocs.io) - pytest-asyncio plugin documentation
- [CLAUDE.md Project Conventions](../../.claude/CLAUDE.md) - Project coding standards

---

**Quick Links:**
- [← Back to Plugin Testing Guide](../README-plugins.md)
- [API Reference →](./plugin-api-reference.md)
