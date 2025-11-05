# Plugin Manager Guide

**Last Updated:** 2025-11-05
**Version:** 1.0
**Type:** How-To Guide (Diátaxis)
**Epic:** 7 - Plugin Architecture & Multi-Tool Support
**Story:** 7.7 - Document Plugin Architecture

[Plugin Docs](index.md) > How-To Guides > Plugin Manager Guide

---

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Plugin Registration](#plugin-registration)
  - [Programmatic Registration](#programmatic-registration)
  - [Auto-Discovery](#auto-discovery)
- [Plugin Retrieval](#plugin-retrieval)
- [Dynamic Routing](#dynamic-routing)
- [Helper Methods](#helper-methods)
- [Error Handling](#error-handling)
- [Testing with Plugin Manager](#testing-with-plugin-manager)
- [See Also](#see-also)

---

## Overview

The Plugin Manager (`PluginManager`) provides centralized registration, validation, and retrieval of ticketing tool plugins. It implements the **singleton pattern** to ensure a single registry instance exists application-wide.

**Key Capabilities:**
- Plugin registration with validation
- Plugin retrieval by `tool_type`
- Auto-discovery from directory structure
- Singleton pattern (one registry instance)
- Full type safety with mypy
- Clear error messages

**Location:** `src/plugins/registry.py`
**Story:** 7.2 - Implement Plugin Manager and Registry

---

## Quick Start

```python
from src.plugins import PluginManager
from src.plugins.servicedesk_plus.plugin import ServiceDeskPlusPlugin

# Get singleton instance
manager = PluginManager()

# Register a plugin
plugin = ServiceDeskPlusPlugin()
manager.register_plugin("servicedesk_plus", plugin)

# Retrieve plugin for use
plugin = manager.get_plugin("servicedesk_plus")

# Use plugin methods
metadata = plugin.extract_metadata(payload)
ticket = await plugin.get_ticket(tenant_id, ticket_id)
```

---

## Plugin Registration

### Programmatic Registration

Register plugins explicitly in your code:

```python
from src.plugins import PluginManager
from src.plugins.jira.plugin import JiraPlugin

manager = PluginManager()
plugin = JiraPlugin()
manager.register_plugin("jira", plugin)
```

**Registration Validation:**

The Plugin Manager validates plugins during registration:

1. **tool_type validation:** Must be non-empty string
2. **Type checking:** Plugin must be instance of `TicketingToolPlugin`
3. **ABC validation:** All abstract methods must be implemented

```python
# ❌ Invalid: empty tool_type
manager.register_plugin("", plugin)
# Raises: PluginValidationError

# ❌ Invalid: not a plugin instance
manager.register_plugin("test", {"invalid": "dict"})
# Raises: PluginValidationError

# ✅ Valid registration
manager.register_plugin("jira", JiraPlugin())
```

### Auto-Discovery

The Plugin Manager can automatically discover and register plugins from the directory structure.

**Directory Structure Convention:**

```
src/plugins/
├── __init__.py                    # Package exports
├── base.py                        # TicketingToolPlugin ABC
├── registry.py                    # PluginManager
├── servicedesk_plus/              # ServiceDesk Plus plugin
│   ├── __init__.py
│   ├── plugin.py                  # ServiceDeskPlusPlugin class
│   ├── api_client.py
│   └── webhook_validator.py
└── jira/                          # Jira plugin
    ├── __init__.py
    ├── plugin.py                  # JiraPlugin class
    ├── api_client.py
    └── webhook_validator.py
```

**Discovery Process:**

1. Scan `src/plugins/*/` for subdirectories
2. Look for `plugin.py` file in each subdirectory
3. Dynamically import module using `importlib.import_module()`
4. Inspect module for classes inheriting from `TicketingToolPlugin`
5. Instantiate discovered plugin classes
6. Auto-register using directory name as `tool_type`
7. Log warnings for import failures but continue discovery

**Auto-Loading on Startup:**

```python
from src.plugins import PluginManager

# In main.py
@app.on_event("startup")
async def startup_event():
    manager = PluginManager()
    manager.load_plugins_on_startup()
    logger.info(f"Loaded plugins: {manager.list_registered_plugins()}")
```

**Plugin Metadata (Optional):**

Plugins can define explicit `tool_type` using class attribute:

```python
class ServiceDeskPlusPlugin(TicketingToolPlugin):
    __tool_type__ = "servicedesk_plus"  # Explicit tool_type
    __version__ = "1.0.0"
    __author__ = "AI Agents Team"

    # ... implement abstract methods ...
```

If `__tool_type__` is not defined, the directory name is used (e.g., `servicedesk_plus/` → `"servicedesk_plus"`).

---

## Plugin Retrieval

Retrieve registered plugins by `tool_type`:

```python
# Get plugin for routing
plugin = manager.get_plugin("servicedesk_plus")

# Use plugin methods
metadata = plugin.extract_metadata(webhook_payload)
ticket_data = await plugin.get_ticket(tenant_id, ticket_id)
```

**Check Before Retrieval:**

```python
if manager.is_plugin_registered("jira"):
    plugin = manager.get_plugin("jira")
else:
    logger.warning("Jira plugin not available")
```

---

## Dynamic Routing

Route requests to the correct plugin based on tenant configuration:

```python
async def process_webhook(tenant_id: str, payload: dict, signature: str):
    # 1. Query tenant configuration
    tenant = await get_tenant_config(tenant_id)

    # 2. Get appropriate plugin based on tenant's tool_type
    manager = PluginManager()
    plugin = manager.get_plugin(tenant.tool_type)

    # 3. Validate webhook using correct plugin
    if not await plugin.validate_webhook(payload, signature):
        raise HTTPException(401, "Invalid webhook signature")

    # 4. Extract metadata
    metadata = plugin.extract_metadata(payload)

    # 5. Queue enhancement job
    await queue_enhancement(metadata)
```

**Multi-Tenant Routing:**

```python
async def handle_webhook(request: Request):
    payload = await request.json()
    signature = request.headers.get("X-Webhook-Signature")
    tenant_id = payload.get("tenant_id")

    # Get tenant configuration
    tenant = await db.query(TenantConfig).filter_by(tenant_id=tenant_id).first()

    # Get appropriate plugin
    manager = PluginManager()
    plugin = manager.get_plugin(tenant.tool_type)  # Routes to correct plugin

    # Validate webhook
    if not await plugin.validate_webhook(payload, signature):
        return JSONResponse({"error": "Invalid signature"}, status_code=401)

    # Extract metadata
    metadata = plugin.extract_metadata(payload)

    # Queue enhancement job
    job_id = await queue_enhancement(metadata)

    return JSONResponse({"job_id": job_id, "status": "queued"})
```

---

## Helper Methods

### list_registered_plugins()

Returns list of all registered `tool_types`:

```python
manager = PluginManager()
plugins = manager.list_registered_plugins()
print(f"Available plugins: {plugins}")
# Output: Available plugins: ['servicedesk_plus', 'jira']
```

### is_plugin_registered()

Check if plugin is registered:

```python
if manager.is_plugin_registered("jira"):
    plugin = manager.get_plugin("jira")
else:
    logger.warning("Jira plugin not available")
```

### unregister_plugin()

Remove plugin from registry (primarily for testing/hot-reload):

```python
manager.unregister_plugin("test_plugin")
# Plugin can now be re-registered with updated implementation
```

---

## Error Handling

### PluginValidationError

Raised when plugin fails validation during registration:

```python
from src.plugins import PluginValidationError

try:
    manager.register_plugin("test", invalid_object)
except PluginValidationError as e:
    # Error: "Plugin 'dict' must be an instance of TicketingToolPlugin"
    logger.error(f"Registration failed: {e}")
```

### PluginNotFoundError

Raised when retrieving unregistered plugin:

```python
from src.plugins import PluginNotFoundError

try:
    plugin = manager.get_plugin("zendesk")
except PluginNotFoundError as e:
    # Error: "Plugin for tool_type 'zendesk' not registered.
    #         Available plugins: ['servicedesk_plus', 'jira']"
    logger.error(f"Plugin not found: {e}")
```

**Error Message Benefits:**
- Includes requested `tool_type`
- Lists all available plugins
- Helps identify configuration errors

### Non-Fatal Discovery Failures

Import errors during discovery are logged as warnings but don't stop the application:

```python
# One broken plugin doesn't prevent discovery of other plugins
try:
    module = importlib.import_module(f"src.plugins.{plugin_dir}.plugin")
    # ... discover and register plugin ...
except Exception as e:
    logger.warning(f"Failed to import plugin from {plugin_dir}: {e}. Skipping.")
    continue  # Continue discovering other plugins
```

**Rationale:** One malfunctioning plugin shouldn't break the entire application. Valid plugins can still be used while the broken plugin is fixed.

---

## Testing with Plugin Manager

### Unit Testing

```python
from src.plugins import PluginManager
from tests.mocks import MockTicketingToolPlugin

def test_enhancement_workflow():
    # Reset singleton for test isolation
    PluginManager._instance = None
    manager = PluginManager()

    # Register mock plugin
    mock_plugin = MockTicketingToolPlugin(
        validate_webhook_response=True,
        get_ticket_response={"id": "TEST-123", "description": "Test ticket"}
    )
    manager.register_plugin("mock_tool", mock_plugin)

    # Test workflow with mock plugin
    plugin = manager.get_plugin("mock_tool")
    assert plugin is mock_plugin

    # Verify plugin methods can be called
    metadata = plugin.extract_metadata({"ticket_id": "TEST-123"})
    assert metadata.ticket_id == "TEST-123"
```

### Singleton Pattern Testing

```python
from src.plugins import PluginManager

def test_singleton_pattern():
    # All references point to same instance
    manager1 = PluginManager()
    manager2 = PluginManager()
    assert manager1 is manager2  # True
```

---

## See Also

- [Plugin Interface Reference](plugin-interface-reference.md) - TicketingToolPlugin ABC details
- [Plugin Examples](plugin-examples-servicedesk.md) - Complete implementations
- [Plugin Testing Guide](plugin-testing-guide.md) - Mock plugin usage
- [Plugin Troubleshooting](plugin-troubleshooting.md) - Common issues

---

## Next Steps

- **Implementing a Plugin:** See [Plugin Development Guide](../plugin-development-guide.md)
- **Understanding the Interface:** See [Plugin Interface Reference](plugin-interface-reference.md)
- **Testing Your Plugin:** See [Plugin Testing Guide](plugin-testing-guide.md)
