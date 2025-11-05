# Plugin Testing Guide

[Plugin Docs](index.md) > Support > Testing

**Last Updated:** 2025-11-05

---

## Overview

This guide references the comprehensive testing framework from Story 7.6. For full test implementation details, see `tests/README-plugins.md`.

**Minimum Requirements:**
- 15+ unit tests per plugin
- 5+ integration tests per plugin
- 80%+ code coverage
- Performance tests for NFR001 compliance

---

## Testing Strategy

### 3-Layer Test Pyramid

```
       ┌─────────────┐
       │  E2E Tests  │  (Fewest)
       │   1-2 tests │
       └─────────────┘
     ┌─────────────────┐
     │ Integration Tests│  (Some)
     │    5+ tests      │
     └─────────────────┘
   ┌─────────────────────┐
   │    Unit Tests        │  (Most)
   │     15+ tests        │
   └─────────────────────┘
```

---

## Unit Tests

### Test validate_webhook()

**Required Tests (5):**
1. Valid signature → Returns True
2. Invalid signature → Returns False
3. Missing tenant_id → Returns False
4. Inactive tenant → Returns False
5. Malformed signature header → Returns False

**Example:**
```python
@pytest.mark.asyncio
async def test_validate_webhook_valid_signature():
    plugin = ServiceDeskPlusPlugin()
    payload = {"tenant_id": "tenant-001", "data": {}}
    signature = "sha256=correct_hash"

    with patch.object(plugin, '_get_tenant_config') as mock:
        result = await plugin.validate_webhook(payload, signature)

    assert result is True
```

### Test extract_metadata()

**Required Tests (5):**
1. Success case with all fields
2. Missing optional fields → Uses defaults
3. Priority normalization (Urgent → high)
4. Null description → Raises ValidationError
5. Invalid timestamp → Raises ValidationError

### Test get_ticket()

**Required Tests (3):**
1. Success (200) → Returns ticket data
2. Not found (404) → Returns None
3. Auth error (401) → Raises AuthenticationError

### Test update_ticket()

**Required Tests (2):**
1. Success (200/201) → Returns True
2. Rate limited (429) → Retries with backoff

---

## Integration Tests

### Test 1: End-to-End Webhook Flow

```python
@pytest.mark.asyncio
async def test_webhook_to_enhancement_flow(test_db, test_redis):
    """Test complete flow: webhook → validation → metadata → enhancement."""
    # Setup
    tenant = await create_test_tenant(test_db, tool_type="servicedesk_plus")
    plugin = PluginManager.get_plugin("servicedesk_plus")

    # Simulate webhook
    payload = {...}
    signature = generate_test_signature(payload, tenant.webhook_secret)

    # Validate
    is_valid = await plugin.validate_webhook(payload, signature)
    assert is_valid

    # Extract metadata
    metadata = plugin.extract_metadata(payload)
    assert metadata.tenant_id == tenant.tenant_id

    # Trigger enhancement workflow
    enhancement_id = await trigger_enhancement(metadata)
    assert enhancement_id is not None
```

### Test 2: Plugin Manager Routing

```python
@pytest.mark.asyncio
async def test_plugin_manager_routes_to_correct_plugin(test_db):
    """Test Plugin Manager routes requests to correct plugin."""
    # Create tenants with different tools
    tenant_sd = await create_test_tenant(test_db, tool_type="servicedesk_plus")
    tenant_jira = await create_test_tenant(test_db, tool_type="jira")

    # Get plugins
    plugin_sd = await PluginManager.get_plugin_for_tenant(tenant_sd.tenant_id)
    plugin_jira = await PluginManager.get_plugin_for_tenant(tenant_jira.tenant_id)

    # Verify correct plugin types
    assert isinstance(plugin_sd, ServiceDeskPlusPlugin)
    assert isinstance(plugin_jira, JiraServiceManagementPlugin)
```

### Test 3-5: API Integration, Error Handling, Performance

See `tests/integration/test_plugin_integration.py` for implementations.

---

## Performance Tests

### Latency Validation

```python
import time

@pytest.mark.asyncio
async def test_validate_webhook_latency():
    """Validate webhook completes in <100ms (NFR001)."""
    plugin = ServiceDeskPlusPlugin()
    payload = {...}
    signature = "sha256=..."

    start = time.time()
    result = await plugin.validate_webhook(payload, signature)
    duration_ms = (time.time() - start) * 1000

    assert duration_ms < 100, f"Validation took {duration_ms:.2f}ms (target: <100ms)"
```

**Performance Targets (NFR001):**
- validate_webhook: <100ms
- get_ticket: <2s
- update_ticket: <3s

---

## Mock Plugin Usage

The Mock Plugin from Story 7.6 simulates API calls without external dependencies:

```python
from src.plugins.mocks.mock_plugin import MockTicketingPlugin

@pytest.mark.asyncio
async def test_enhancement_workflow_with_mock():
    """Test enhancement workflow using Mock Plugin."""
    plugin = MockTicketingPlugin()

    # Mock plugin returns predefined responses
    ticket = await plugin.get_ticket("tenant-001", "MOCK-123")
    assert ticket is not None
    assert ticket["id"] == "MOCK-123"
```

---

## Test Fixtures

**Location:** `tests/conftest.py`

```python
import pytest
from unittest.mock import AsyncMock


@pytest.fixture
async def test_db():
    """Mock database session."""
    session = AsyncMock()
    yield session


@pytest.fixture
async def test_redis():
    """Mock Redis client."""
    redis = AsyncMock()
    yield redis


@pytest.fixture
def plugin():
    """Create plugin instance."""
    from src.plugins.implementations.servicedesk_plus import ServiceDeskPlusPlugin
    return ServiceDeskPlusPlugin()
```

---

## Coverage Requirements

**Run Coverage:**
```bash
pytest tests/ --cov=src/plugins --cov-report=html
open htmlcov/index.html
```

**Minimum Coverage:**
- Overall: 80%
- Critical paths (webhook validation, API calls): 95%

**Check Coverage:**
```bash
pytest tests/ --cov=src/plugins --cov-fail-under=80
```

---

## CI/CD Integration

**GitHub Actions:** `.github/workflows/ci.yml`

```yaml
- name: Run plugin tests
  run: |
    pytest tests/unit/test_*_plugin.py -v
    pytest tests/integration/test_*_integration.py -v

- name: Check coverage
  run: |
    pytest tests/ --cov=src/plugins --cov-fail-under=80
```

---

## Testing Checklist

- [ ] 15+ unit tests (5 per method minimum)
- [ ] 5+ integration tests
- [ ] Performance tests validate NFR001
- [ ] All tests pass (pytest exit code 0)
- [ ] Coverage ≥80%
- [ ] Mock plugin tests pass
- [ ] No test warnings or deprecation notices
- [ ] Tests run in <30 seconds

---

## See Also

- [tests/README-plugins.md](../../tests/README-plugins.md) - Comprehensive testing framework
- [Plugin Development Guide](../plugin-development-guide.md)
- [Plugin Troubleshooting](plugin-troubleshooting.md)
