# Template Plugin Customization Guide

This template provides a starting point for implementing new ticketing tool plugins.

---

## Customization Checklist

### 1. Copy Template

```bash
cp -r src/plugins/_template src/plugins/YOUR_TOOL
cd src/plugins/YOUR_TOOL
```

### 2. Rename Files and Classes

- [ ] Rename `TemplatePlugin` → `YourToolPlugin` in `plugin.py`
- [ ] Rename `TemplateAPIClient` → `YourToolAPIClient` in `api_client.py`
- [ ] Update `__tool_type__` from `"template"` to `"your_tool"`
- [ ] Update imports in `__init__.py`

### 3. Implement Webhook Validation

- [ ] Choose validation method (HMAC-SHA256, JWT, custom)
- [ ] Implement `validate_signature()` in `webhook_validator.py`
- [ ] Implement `validate_webhook()` in `plugin.py`
- [ ] Write 5 unit tests for webhook validation

### 4. Implement API Client

- [ ] Update `api_url` format in `__init__()`
- [ ] Update authentication headers
- [ ] Implement `get_ticket()` with tool-specific endpoint
- [ ] Implement `add_note()` with tool-specific endpoint
- [ ] Add retry logic and error handling
- [ ] Write 5 unit tests for API client

### 5. Implement Metadata Extraction

- [ ] Parse tool-specific webhook payload structure
- [ ] Extract tenant_id (from payload or custom field)
- [ ] Extract ticket_id
- [ ] Extract description
- [ ] Normalize priority to standard values ("high", "medium", "low")
- [ ] Parse timestamp to UTC datetime
- [ ] Write 5 unit tests for metadata extraction

### 6. Add Configuration

Update `src/database/models.py` with tool-specific fields:

```python
# Example: Zendesk fields
zendesk_subdomain = Column(String(100), nullable=True)
zendesk_email = Column(String(255), nullable=True)
zendesk_api_token_encrypted = Column(Text, nullable=True)
```

Create Alembic migration:

```bash
alembic revision --autogenerate -m "Add YOUR_TOOL fields to tenant_configs"
```

### 7. Register Plugin

Update `src/plugins/__init__.py`:

```python
from src.plugins.YOUR_TOOL.plugin import YourToolPlugin

PluginRegistry.register("your_tool", YourToolPlugin)
```

### 8. Write Tests

- [ ] 15+ unit tests in `tests/unit/test_YOUR_TOOL_plugin.py`
- [ ] 5+ integration tests in `tests/integration/test_YOUR_TOOL_integration.py`
- [ ] Performance tests validate NFR001 targets
- [ ] Achieve 80%+ code coverage

### 9. Add Documentation

Create `docs/plugins/plugin-examples-YOUR_TOOL.md`:

- Complete implementation code
- Key implementation details
- API endpoints reference
- Testing examples
- Common issues

### 10. Type Checking

```bash
mypy src/plugins/YOUR_TOOL/ --strict
# Must pass with 0 errors
```

### 11. Code Formatting

```bash
black src/plugins/YOUR_TOOL/
# Ensure all files ≤500 lines
```

---

## Testing Your Plugin

```bash
# Run unit tests
pytest tests/unit/test_YOUR_TOOL_plugin.py -v

# Run integration tests
pytest tests/integration/test_YOUR_TOOL_integration.py -v

# Check coverage
pytest tests/ --cov=src/plugins/YOUR_TOOL --cov-fail-under=80

# Run performance tests
pytest tests/performance/test_YOUR_TOOL_performance.py -v
```

---

## Submission

Follow [Plugin Submission Guidelines](../../docs/plugins/plugin-submission-guidelines.md) to submit PR.

---

## Resources

- [Plugin Development Guide](../../docs/plugin-development-guide.md)
- [Plugin Interface Reference](../../docs/plugins/plugin-interface-reference.md)
- [ServiceDesk Plus Example](../../docs/plugins/plugin-examples-servicedesk.md)
- [Jira Example](../../docs/plugins/plugin-examples-jira.md)
