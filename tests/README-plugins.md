# Plugin Testing Guide

**Story:** 7.6 - Plugin Testing Framework and Mock Plugins
**Last Updated:** 2025-11-05

## Table of Contents

1. [Overview](#overview)
2. [MockTicketingToolPlugin Usage](#mockticketingtoolplugin-usage)
3. [Plugin Test Fixtures](#plugin-test-fixtures)
4. [Related Documentation](#related-documentation)

For additional guidance, see:
- **[Plugin Testing Best Practices](./docs/plugin-testing-best-practices.md)** - Best practices, examples, CI/CD integration, troubleshooting
- **[Plugin API Reference](./docs/plugin-api-reference.md)** - Complete test utilities reference

---

## Overview

The plugin testing framework enables testing of ticketing tool integrations without real API dependencies. It provides:

- **MockTicketingToolPlugin**: Configurable mock implementing `TicketingToolPlugin` ABC
- **Test Fixtures**: Reusable pytest fixtures for common scenarios
- **Test Utilities**: Helper functions for assertions and test data generation
- **Integration Tests**: End-to-end workflow validation
- **CI Integration**: Isolated test execution with pytest markers

### Testing Philosophy

**Three-Layer Testing Strategy:**

1. **Unit Tests** (Plugin Methods in Isolation)
   - Test each method independently
   - Focus on plugin logic correctness
   - Speed: <100ms per test
   - Example: `test_servicedesk_plugin.py`

2. **Integration Tests** (Multi-Component Workflows)
   - Test plugin with PluginManager, TenantService
   - Use mock plugin to avoid real APIs
   - Speed: 100-500ms per test
   - Example: `test_mock_plugin_workflow.py`

3. **E2E Tests** (Real Tool Integration - Optional)
   - Test against real ticketing tool sandboxes
   - Validate API compatibility
   - Speed: 1-5s per test
   - Run on-demand, not in CI

---

## MockTicketingToolPlugin Usage

### When to Use Mock vs Real Plugins

**Use MockTicketingToolPlugin when:**
- Testing enhancement workflow logic (routing, context gathering)
- Testing error handling (API failures, timeouts, auth errors)
- Developing new plugin integrations (prototype without API access)
- Running tests in CI/CD (no external dependencies)

**Use Real Plugins when:**
- Validating API client implementation
- Testing vendor-specific payload formats
- Performing integration tests with sandbox environments
- Investigating production issues

### Basic Usage

```python
from tests.mocks.mock_plugin import MockTicketingToolPlugin

# Success mode (all methods return success)
plugin = MockTicketingToolPlugin.success_mode()
valid = await plugin.validate_webhook(payload, signature)
assert valid is True

# API error mode (raises ServiceDeskAPIError)
plugin = MockTicketingToolPlugin.api_error_mode()
with pytest.raises(ServiceDeskAPIError):
    await plugin.get_ticket("tenant-1", "ticket-123")
```

### Factory Methods

| Factory Method | Behavior | Use Case |
|----------------|----------|----------|
| `success_mode()` | All methods return success | Happy path testing |
| `api_error_mode()` | Raises `ServiceDeskAPIError` in get_ticket/update_ticket | API failure handling |
| `auth_error_mode()` | Raises `ValidationError` in validate_webhook | Authentication failure |
| `timeout_mode()` | Raises `asyncio.TimeoutError` in async methods | Timeout handling |
| `not_found_mode()` | Returns `None` from get_ticket | Ticket not found (404) |

### Custom Configuration

```python
# Custom ticket response
custom_ticket = {
    "id": "CUSTOM-123",
    "priority": "critical",
    "description": "Custom test ticket"
}
plugin = MockTicketingToolPlugin(_get_ticket_response=custom_ticket)

# Custom validation response
plugin = MockTicketingToolPlugin(_validate_response=False)
valid = await plugin.validate_webhook(payload, sig)
assert valid is False  # Always returns False
```

### Call Tracking

```python
plugin = MockTicketingToolPlugin.success_mode()

await plugin.validate_webhook(payload, signature)
await plugin.get_ticket("tenant-1", "ticket-123")

# Assert method was called
from tests.utils.plugin_test_helpers import assert_plugin_called
assert_plugin_called(plugin, "validate_webhook", times=1)

# Assert method called with specific args
from tests.utils.plugin_test_helpers import assert_plugin_called_with
assert_plugin_called_with(
    plugin,
    "get_ticket",
    tenant_id="tenant-1",
    ticket_id="ticket-123"
)

# Get call history directly
history = plugin.get_call_history()
assert len(history) == 2
assert history[0]["method"] == "validate_webhook"
```

---

## Plugin Test Fixtures

All fixtures defined in `tests/conftest.py`. Use by including fixture name as test function argument.

### mock_generic_plugin

**Purpose:** Provides clean MockTicketingToolPlugin in success mode
**Scope:** Function (fresh instance per test)
**Returns:** `MockTicketingToolPlugin.success_mode()`

```python
@pytest.mark.asyncio
async def test_webhook_validation(mock_generic_plugin):
    valid = await mock_generic_plugin.validate_webhook(payload, sig)
    assert valid is True
```

### mock_servicedesk_plugin

**Purpose:** Mock plugin with ServiceDesk Plus-specific response structure
**Scope:** Function
**Returns:** `MockTicketingToolPlugin` configured with ServiceDesk Plus ticket format

**Response Structure:**
```json
{
  "request": {
    "id": "12345",
    "subject": "Mock ServiceDesk Plus ticket",
    "priority": {"name": "High"},
    "created_time": {"value": "epoch_milliseconds"}
  }
}
```

```python
@pytest.mark.asyncio
async def test_servicedesk_workflow(mock_servicedesk_plugin):
    ticket = await mock_servicedesk_plugin.get_ticket("tenant", "123")
    assert "request" in ticket  # ServiceDesk Plus wraps in "request"
```

### mock_jira_plugin

**Purpose:** Mock plugin with Jira-specific response structure
**Scope:** Function
**Returns:** `MockTicketingToolPlugin` configured with Jira issue format

**Response Structure:**
```json
{
  "key": "JIRA-456",
  "fields": {
    "summary": "Mock Jira ticket",
    "priority": {"name": "High", "id": "2"},
    "created": "2025-11-05T10:00:00.000+0000"
  }
}
```

```python
@pytest.mark.asyncio
async def test_jira_workflow(mock_jira_plugin):
    ticket = await mock_jira_plugin.get_ticket("tenant", "JIRA-456")
    assert ticket["key"] == "JIRA-456"
    assert "fields" in ticket
```

### plugin_failure_mode

**Purpose:** Parameterized fixture for testing all failure scenarios
**Scope:** Function
**Parameters:** `["api_error", "auth_error", "timeout", "not_found"]`
**Returns:** `MockTicketingToolPlugin` in specified failure mode

```python
@pytest.mark.asyncio
async def test_handle_failures(plugin_failure_mode):
    # This test runs 4 times, once for each failure mode
    plugin = plugin_failure_mode
    # Test error handling logic...
```

### mock_plugin_manager

**Purpose:** Mocked PluginManager singleton for routing tests
**Scope:** Function
**Returns:** `MagicMock` with `get_plugin()` returning MockTicketingToolPlugin

```python
def test_plugin_routing(mock_plugin_manager):
    from src.plugins.registry import PluginManager
    plugin = PluginManager().get_plugin("servicedesk_plus")
    assert isinstance(plugin, MockTicketingToolPlugin)
```

---

## Related Documentation

### Plugin Architecture and Testing
- **[Plugin Testing Best Practices](./docs/plugin-testing-best-practices.md)** - Best practices, example test cases, CI/CD integration, troubleshooting
- **[Plugin API Reference](./docs/plugin-api-reference.md)** - Complete test utilities API documentation
- [Plugin Architecture Guide](../docs/plugin-architecture.md) - Overview of plugin system architecture
- [Existing Plugin Tests](./unit/test_servicedesk_plugin.py) - ServiceDesk Plus plugin test examples

### Project Documentation
- [Pytest Documentation](https://docs.pytest.org) - Official pytest documentation
- [Pytest Async](https://pytest-asyncio.readthedocs.io) - pytest-asyncio plugin documentation
- [CLAUDE.md Project Conventions](../.claude/CLAUDE.md) - Project coding standards
- [Architecture Document](../docs/architecture.md) - System architecture overview
- [PRD Document](../docs/PRD.md) - Product requirements

### Story Context
- Story 7.6 context file: `docs/stories/7-6-create-plugin-testing-framework-and-mock-plugins.context.xml`
- Plugin base interface: `src/plugins/base.py`
- MockTicketingToolPlugin implementation: `tests/mocks/mock_plugin.py`
- Test utilities: `tests/utils/plugin_test_helpers.py`

---

**Quick Links:**
- [Best Practices →](./docs/plugin-testing-best-practices.md)
- [API Reference →](./docs/plugin-api-reference.md)
- [Plugin Architecture →](../docs/plugin-architecture.md)
