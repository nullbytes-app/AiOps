# Plugin Test Utilities API Reference

**Story:** 7.6 - Plugin Testing Framework and Mock Plugins
**Last Updated:** 2025-11-05

Complete reference for all test utility functions in `tests/utils/plugin_test_helpers.py`.

## Table of Contents

1. [Assertion Utilities](#assertion-utilities)
2. [Response Capture Utilities](#response-capture-utilities)
3. [Failure Simulation Utilities](#failure-simulation-utilities)
4. [TicketMetadata Validation](#ticketmetadata-validation)
5. [Payload Builders](#payload-builders)

---

## Assertion Utilities

### assert_plugin_called

```python
def assert_plugin_called(plugin, method_name: str, times: int = 1)
```

Assert plugin method was called exactly N times.

**Parameters:**
- `plugin` (MockTicketingToolPlugin): Plugin instance to check
- `method_name` (str): Name of method to check ("validate_webhook", "get_ticket", etc.)
- `times` (int): Expected number of calls (default: 1)

**Raises:**
- `AssertionError`: If call count doesn't match expected

**Example:**
```python
await plugin.validate_webhook(payload, sig)
assert_plugin_called(plugin, "validate_webhook", times=1)
```

---

### assert_plugin_called_with

```python
def assert_plugin_called_with(plugin, method_name: str, **expected_kwargs)
```

Assert last call to method had specific kwargs.

**Parameters:**
- `plugin` (MockTicketingToolPlugin): Plugin instance to check
- `method_name` (str): Name of method to check
- `**expected_kwargs`: Expected keyword arguments from last call

**Raises:**
- `AssertionError`: If kwargs don't match or method wasn't called

**Example:**
```python
await plugin.get_ticket("tenant-1", "ticket-123")
assert_plugin_called_with(
    plugin,
    "get_ticket",
    tenant_id="tenant-1",
    ticket_id="ticket-123"
)
```

---

### get_plugin_call_count

```python
def get_plugin_call_count(plugin, method_name: str) -> int
```

Get number of times method was called.

**Parameters:**
- `plugin` (MockTicketingToolPlugin): Plugin instance to check
- `method_name` (str): Name of method to count

**Returns:**
- `int`: Number of times method was called

**Example:**
```python
count = get_plugin_call_count(plugin, "get_ticket")
assert count == 3
```

---

### get_plugin_last_call

```python
def get_plugin_last_call(plugin, method_name: str) -> Optional[Dict]
```

Get details of last call to method.

**Parameters:**
- `plugin` (MockTicketingToolPlugin): Plugin instance to check
- `method_name` (str): Name of method to retrieve

**Returns:**
- `Optional[Dict]`: Call details with keys: "method", "args", "kwargs", "timestamp"
- `None`: If method was never called

**Example:**
```python
last_call = get_plugin_last_call(plugin, "update_ticket")
assert last_call["kwargs"]["content"] == "enhancement"
```

---

## Response Capture Utilities

### capture_plugin_response

```python
async def capture_plugin_response(
    plugin,
    method_name: str,
    *args,
    timeout: float = 5.0,
    **kwargs
) -> Tuple[result, exception, duration_ms]
```

Call plugin method and capture result, exception, duration.

**Parameters:**
- `plugin` (MockTicketingToolPlugin): Plugin instance to call
- `method_name` (str): Name of method to call
- `*args`: Positional arguments to pass to method
- `timeout` (float): Maximum wait time in seconds (default: 5.0)
- `**kwargs`: Keyword arguments to pass to method

**Returns:**
- `Tuple[Any, Optional[Exception], float]`:
  - `result`: Method return value (None if exception raised)
  - `exception`: Exception raised (None if successful)
  - `duration_ms`: Execution time in milliseconds

**Example:**
```python
result, exception, duration = await capture_plugin_response(
    plugin, "get_ticket", "tenant-1", "ticket-123"
)
assert exception is None
assert duration < 100  # < 100ms
assert result["id"] == "ticket-123"
```

---

## Failure Simulation Utilities

### configure_plugin_failure

```python
def configure_plugin_failure(plugin, failure_type: str) -> plugin
```

Configure mock plugin for specific failure mode.

**Parameters:**
- `plugin` (MockTicketingToolPlugin): Plugin instance to configure
- `failure_type` (str): Type of failure to simulate

**Failure Types:**
- `"api_error"`: Raises `ServiceDeskAPIError` in get_ticket/update_ticket
- `"auth_error"`: Raises `ValidationError` in validate_webhook
- `"timeout"`: Raises `asyncio.TimeoutError` in async methods
- `"not_found"`: Returns `None` from get_ticket (404 scenario)

**Returns:**
- `MockTicketingToolPlugin`: Same plugin instance (for method chaining)

**Raises:**
- `ValueError`: If failure_type is invalid

**Example:**
```python
plugin = MockTicketingToolPlugin.success_mode()
configure_plugin_failure(plugin, "api_error")
with pytest.raises(ServiceDeskAPIError):
    await plugin.get_ticket("tenant-1", "ticket-123")
```

---

## TicketMetadata Validation

### assert_ticket_metadata_valid

```python
def assert_ticket_metadata_valid(metadata: TicketMetadata)
```

Validate TicketMetadata structure and field values.

**Parameters:**
- `metadata` (TicketMetadata): Metadata instance to validate

**Validation Checks:**
1. All required fields present and non-empty:
   - `tenant_id` (str, non-empty)
   - `ticket_id` (str, non-empty)
   - `description` (str, non-empty)
   - `priority` (str, non-empty)
   - `created_at` (datetime)

2. Priority normalized to lowercase: "high", "medium", or "low"

3. `created_at` is datetime object with timezone info

**Raises:**
- `AssertionError`: If any validation check fails (with descriptive message)

**Example:**
```python
metadata = plugin.extract_metadata(payload)
assert_ticket_metadata_valid(metadata)
# If assertion passes, metadata structure is valid
```

---

## Payload Builders

### build_servicedesk_payload

```python
def build_servicedesk_payload(**overrides) -> Dict[str, Any]
```

Build realistic ServiceDesk Plus webhook payload.

**Parameters:**
- `**overrides`: Optional field overrides

**Available Overrides:**
- `tenant_id` (str): Tenant identifier (default: "tenant-test-001")
- `ticket_id` (str): Ticket ID (default: "12345")
- `description` (str): Ticket description (default: "Test ticket description")
- `priority` (str): Priority level (default: "High")
- `created_time` (str): Epoch milliseconds (default: current time)

**Returns:**
- `Dict[str, Any]`: ServiceDesk Plus-formatted webhook payload

**Payload Structure:**
```json
{
  "tenant_id": "tenant-test-001",
  "event": "request.created",
  "data": {
    "ticket": {
      "id": "12345",
      "description": "Test ticket description",
      "priority": "High",
      "created_time": "1699200000000"
    }
  },
  "created_at": "1699200000000"
}
```

**Example:**
```python
payload = build_servicedesk_payload(
    tenant_id="acme-corp",
    ticket_id="98765",
    priority="Urgent"
)
# Use in tests
metadata = plugin.extract_metadata(payload)
assert metadata.priority == "urgent"
```

---

### build_jira_payload

```python
def build_jira_payload(**overrides) -> Dict[str, Any]
```

Build realistic Jira webhook payload.

**Parameters:**
- `**overrides`: Optional field overrides

**Available Overrides:**
- `tenant_id` (str): Tenant identifier (default: "tenant-test-001")
- `ticket_id` (str): Jira issue key (default: "JIRA-456")
- `description` (str): Issue description (default: "Test Jira issue")
- `priority` (str): Priority name (default: "High", maps to id "2")
- `created` (str): ISO 8601 timestamp (default: current time)

**Returns:**
- `Dict[str, Any]`: Jira-formatted webhook payload

**Payload Structure:**
```json
{
  "tenant_id": "tenant-test-001",
  "webhookEvent": "jira:issue_created",
  "issue": {
    "key": "JIRA-456",
    "fields": {
      "description": "Test Jira issue",
      "priority": {"name": "High", "id": "2"},
      "created": "2025-11-05T10:00:00.000+0000"
    }
  }
}
```

**Priority Mapping:**
- "High" → id "2"
- "Medium" → id "3"
- "Low" → id "4"

**Example:**
```python
payload = build_jira_payload(
    tenant_id="acme-corp",
    ticket_id="ACME-123",
    priority="Medium"
)
# Use in tests
assert payload["issue"]["fields"]["priority"]["id"] == "3"
```

---

### build_generic_payload

```python
def build_generic_payload(**overrides) -> Dict[str, Any]
```

Build simple generic webhook payload for basic testing.

**Parameters:**
- `**overrides`: Optional field overrides

**Available Overrides:**
- `tenant_id` (str): Tenant identifier (default: "tenant-test-001")
- `ticket_id` (str): Ticket ID (default: "GENERIC-789")
- `description` (str): Ticket description (default: "Generic test ticket")
- `priority` (str): Priority level (default: "medium")
- `created_at` (datetime): Creation timestamp (default: current time UTC)

**Returns:**
- `Dict[str, Any]`: Generic webhook payload

**Payload Structure:**
```json
{
  "tenant_id": "tenant-test-001",
  "ticket_id": "GENERIC-789",
  "description": "Generic test ticket",
  "priority": "medium",
  "created_at": "2025-11-05T10:00:00+00:00"
}
```

**Example:**
```python
payload = build_generic_payload(tenant_id="test-tenant")
metadata = plugin.extract_metadata(payload)
assert metadata.tenant_id == "test-tenant"
```

---

## References

- [Plugin Testing Guide](../README-plugins.md) - Main testing guide with overview and fixtures
- [Plugin Testing Best Practices](./plugin-testing-best-practices.md) - Best practices, examples, troubleshooting
- [Plugin Architecture Guide](../../docs/plugin-architecture.md) - Overview of plugin system architecture
- [MockTicketingToolPlugin Implementation](../mocks/mock_plugin.py) - Source code for mock plugin

---

**Quick Links:**
- [← Back to Plugin Testing Guide](../README-plugins.md)
- [Best Practices →](./plugin-testing-best-practices.md)
