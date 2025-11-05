# Plugin Troubleshooting Guide

[Plugin Docs](index.md) > Support > Troubleshooting

**Last Updated:** 2025-11-05

---

## Common Development Errors

### Error: "TypeError: Can't instantiate abstract class"

**Full Error:**
```
TypeError: Can't instantiate abstract class 'MyPlugin' with abstract methods 'get_ticket', 'update_ticket'
```

**Cause:** Plugin class doesn't implement all 4 abstract methods

**Solution:** Implement all required methods:

```python
class MyPlugin(TicketingToolPlugin):
    async def validate_webhook(self, payload, signature) -> bool:
        ...

    async def get_ticket(self, tenant_id, ticket_id) -> Optional[Dict]:
        ...

    async def update_ticket(self, tenant_id, ticket_id, content) -> bool:
        ...

    def extract_metadata(self, payload) -> TicketMetadata:
        ...
```

### Error: "coroutine was never awaited"

**Full Error:**
```
RuntimeWarning: coroutine 'MyPlugin.get_ticket' was never awaited
```

**Cause:** Missing `await` keyword when calling async function

**Solution:**
```python
# ❌ BAD: Missing await
ticket = plugin.get_ticket("tenant-001", "123")

# ✅ GOOD: Use await
ticket = await plugin.get_ticket("tenant-001", "123")
```

### Error: "ModuleNotFoundError: No module named 'plugins'"

**Cause:** Missing `__init__.py` file in plugin directory

**Solution:**
```bash
# Create __init__.py files
touch src/plugins/__init__.py
touch src/plugins/implementations/__init__.py
```

---

## Type Checking Issues

### Error: "Missing return statement"

**Mypy Output:**
```
error: Missing return statement  [return]
```

**Cause:** Function declares return type but some paths don't return

**Solution:**
```python
# ❌ BAD: Missing return
async def get_ticket(...) -> Dict[str, Any]:
    if condition:
        return data
    # Missing return here

# ✅ GOOD: All paths return
async def get_ticket(...) -> Dict[str, Any]:
    if condition:
        return data
    raise ValueError("Condition not met")
```

### Error: "Incompatible return value type"

**Mypy Output:**
```
error: Incompatible return value type (got "None", expected "Dict[str, Any]")
```

**Solution:** Use `Optional` for nullable returns:

```python
# ✅ GOOD: Optional return type
async def get_ticket(...) -> Optional[Dict[str, Any]]:
    if not found:
        return None
    return data
```

### Error: "Argument has incompatible type"

**Mypy Output:**
```
error: Argument 1 to "hmac.new" has incompatible type "str"; expected "bytes"
```

**Solution:** Encode strings to bytes:

```python
# ❌ BAD: Passing str
hmac.new(secret, payload, hashlib.sha256)

# ✅ GOOD: Encode to bytes
hmac.new(secret.encode('utf-8'), payload, hashlib.sha256)
```

---

## Testing Issues

### Error: "AssertionError: assert False is True"

**Cause:** Mock not configured correctly

**Solution:**
```python
# ✅ GOOD: Configure mock return value
with patch.object(plugin, '_get_tenant_config') as mock:
    mock.return_value = MockConfig(...)  # Set return value
    result = await plugin.validate_webhook(payload, signature)
```

### Error: "RuntimeError: Event loop is closed"

**Cause:** Test not marked as async or using wrong pytest plugin

**Solution:**
```python
# Install pytest-asyncio
# pip install pytest-asyncio

# Mark test as async
@pytest.mark.asyncio
async def test_get_ticket():
    result = await plugin.get_ticket("tenant-001", "123")
    assert result is not None
```

### Error: "fixture 'db_session' not found"

**Cause:** Missing conftest.py or fixture not defined

**Solution:** Create `tests/conftest.py`:

```python
import pytest
from unittest.mock import AsyncMock


@pytest.fixture
async def db_session():
    """Mock database session."""
    session = AsyncMock()
    yield session


@pytest.fixture
def plugin():
    """Create plugin instance."""
    from src.plugins.implementations.servicedesk_plus import ServiceDeskPlusPlugin
    return ServiceDeskPlusPlugin()
```

---

## Plugin Registration Problems

### Error: "PluginNotFoundError: No plugin for tool_type 'jira'"

**Cause:** Plugin not registered in Plugin Manager

**Solution:** Register plugin in `src/plugins/__init__.py`:

```python
from src.plugins.registry import PluginRegistry
from src.plugins.implementations.servicedesk_plus import ServiceDeskPlusPlugin
from src.plugins.jira.plugin import JiraServiceManagementPlugin

# Register plugins
PluginRegistry.register("servicedesk_plus", ServiceDeskPlusPlugin)
PluginRegistry.register("jira", JiraServiceManagementPlugin)
```

### Error: "Multiple plugins registered for same tool_type"

**Cause:** Duplicate plugin registration

**Solution:** Check for duplicate `PluginRegistry.register()` calls. Each tool_type should be registered once.

---

## Webhook Validation Failures

### Issue: "Signature validation always fails"

**Debugging Steps:**

1. **Verify signature header:**
```python
logger.debug(f"Received signature: {signature}")
logger.debug(f"Expected format: sha256=<hexdigest>")
```

2. **Check payload serialization:**
```python
# ServiceDesk Plus: Compact JSON, no sorting
payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')

# Jira: Sorted keys
payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
```

3. **Verify secret:**
```python
logger.debug(f"Secret (masked): {webhook_secret[:4]}***")
```

4. **Test with known good signature:**
```python
# Generate test signature
test_signature = hmac.new(
    b"test-secret",
    b'{"test": "payload"}',
    hashlib.sha256
).hexdigest()
print(f"Test signature: sha256={test_signature}")
```

### Issue: "Webhook payload missing tenant_id"

**ServiceDesk Plus:**
```python
# tenant_id should be at top level
{"tenant_id": "tenant-001", "data": {...}}
```

**Jira:**
```python
# tenant_id in custom field
{"issue": {"fields": {"customfield_10000": "tenant-001"}}}
```

---

## API Integration Issues

### Issue: "Authentication Error (401)"

**Debugging:**
```python
# Verify API key is correct
logger.info(f"Using API key: {api_key[:4]}***")

# Test API key manually
curl -H "TECHNICIAN_KEY: your-key" https://servicedesk.example.com/api/v3/tickets/123

# Check tenant config in database
SELECT tenant_id, api_key_encrypted FROM tenant_configs WHERE tenant_id = 'tenant-001';
```

**Common Causes:**
- API key expired
- User account disabled
- Wrong API key for environment (dev vs prod)

### Issue: "Rate Limiting (429)"

**Solution:** Implement proper backoff:

```python
if e.response.status_code == 429:
    retry_after = int(e.response.headers.get("Retry-After", 5))
    logger.warning(f"Rate limited, waiting {retry_after}s")
    await asyncio.sleep(retry_after)
```

**Prevention:**
- Implement request throttling
- Use connection pooling
- Cache frequently accessed data

### Issue: "Timeout errors"

**Debugging:**
```python
# Increase timeout for slow APIs
timeout = httpx.Timeout(
    connect=10.0,  # Default: 5.0
    read=60.0,     # Default: 30.0
)

client = httpx.AsyncClient(timeout=timeout)
```

**Common Causes:**
- Network latency
- API server overloaded
- Large response payloads

---

## Debugging Techniques

### 1. Logging

```python
import logging

# Enable DEBUG logging
logging.basicConfig(level=logging.DEBUG)

# Add detailed logs
logger.debug(f"Calling API: {url}")
logger.debug(f"Headers: {headers}")
logger.debug(f"Payload: {payload}")
```

### 2. Python Debugger (pdb)

```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or use Python 3.7+ built-in
breakpoint()
```

### 3. pytest --pdb

```bash
# Drop into debugger on test failure
pytest tests/unit/test_plugin.py --pdb

# Drop into debugger on first failure
pytest tests/unit/test_plugin.py -x --pdb
```

### 4. Mypy Error Codes

```bash
# Show specific error codes
mypy src/plugins/ --show-error-codes

# Ignore specific error
result = some_call()  # type: ignore[no-untyped-call]
```

---

## Performance Issues

### Issue: "Slow webhook validation (>100ms)"

**Debugging:**
```python
import time

start = time.time()
is_valid = await plugin.validate_webhook(payload, signature)
duration = (time.time() - start) * 1000
logger.info(f"Validation took {duration:.2f}ms")
```

**Common Causes:**
- Database query not cached
- Complex HMAC computation
- Network call in validation path

### Issue: "Memory leak"

**Debugging:**
```python
from memory_profiler import profile

@profile
async def get_ticket(self, tenant_id, ticket_id):
    ...

# Run and check for growing memory
```

**Common Causes:**
- Unbounded cache
- Unclosed httpx clients
- Circular references

---

## Testing Coverage Issues

### Issue: "Coverage below 80%"

**Check coverage:**
```bash
pytest tests/ --cov=src/plugins --cov-report=html
open htmlcov/index.html
```

**Find untested code:**
```bash
# Show lines missing coverage
pytest tests/ --cov=src/plugins --cov-report=term-missing
```

---

## Getting Help

### 1. Check Documentation
- [Plugin Interface Reference](plugin-interface-reference.md)
- [Plugin Examples](plugin-examples-servicedesk.md)
- [Plugin Testing Guide](plugin-testing-guide.md)

### 2. Search Issues
- GitHub Issues: Search for similar problems
- Stack Overflow: Search for error messages

### 3. Ask for Help
- Open GitHub Issue with:
  * Error message (full traceback)
  * Minimal reproducible example
  * Environment details (Python version, OS)
  * What you've tried

### 4. Debugging Checklist
- [ ] Read error message carefully
- [ ] Check logs for more context
- [ ] Verify configuration (DB, secrets)
- [ ] Test with minimal example
- [ ] Check mypy for type errors
- [ ] Run tests in isolation
- [ ] Review recent code changes

---

## See Also

- [Plugin Development Guide](../plugin-development-guide.md)
- [Plugin Testing Guide](plugin-testing-guide.md)
- [Plugin Submission Guidelines](plugin-submission-guidelines.md)
