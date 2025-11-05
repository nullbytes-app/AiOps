# Plugin Submission Guidelines

[Plugin Docs](index.md) > Planning > Submission Guidelines

**Last Updated:** 2025-11-05

---

## Overview

Requirements and process for submitting new plugins or updates to existing plugins.

---

## Code Review Checklist

### 1. Functionality (CRITICAL)

- [ ] All 4 abstract methods implemented (`validate_webhook`, `get_ticket`, `update_ticket`, `extract_metadata`)
- [ ] Plugin registered in `src/plugins/__init__.py`
- [ ] Works with Plugin Manager
- [ ] Handles all webhook event types
- [ ] API calls return correct data structures

### 2. Type Safety (CRITICAL)

- [ ] Type hints on all public methods
- [ ] Type hints on parameters and returns
- [ ] `mypy --strict src/plugins/YOUR_PLUGIN/` passes with 0 errors
- [ ] No `# type: ignore` without justification
- [ ] Optional used correctly for nullable returns

### 3. Documentation

- [ ] Google-style docstrings on all methods
- [ ] README.md in plugin directory
- [ ] API endpoint documentation
- [ ] Configuration requirements listed
- [ ] Example usage provided

### 4. Code Formatting

- [ ] Black formatting applied (`black src/plugins/YOUR_PLUGIN/`)
- [ ] Line length ≤100 characters
- [ ] Import statements organized (stdlib, third-party, local)
- [ ] No trailing whitespace

### 5. File Size (CRITICAL)

- [ ] No file >500 lines
- [ ] If >500 lines, split into modules
- [ ] API client in separate file
- [ ] Webhook validator in separate file

### 6. Security

- [ ] No hardcoded secrets or credentials
- [ ] Uses `secrets.compare_digest()` for signature validation
- [ ] Credentials decrypted just-in-time
- [ ] No sensitive data in logs
- [ ] Input validation on all external data

### 7. Testing (CRITICAL)

- [ ] 15+ unit tests
- [ ] 5+ integration tests
- [ ] 80%+ code coverage
- [ ] All tests pass
- [ ] Performance tests validate NFR001

### 8. Performance

- [ ] validate_webhook <100ms
- [ ] get_ticket <2s
- [ ] update_ticket <3s
- [ ] Connection pooling enabled
- [ ] No blocking I/O in async code

### 9. Error Handling

- [ ] try/except on all external API calls
- [ ] Retry logic with exponential backoff
- [ ] Specific exception types
- [ ] Comprehensive logging
- [ ] Graceful degradation

### 10. Backward Compatibility

- [ ] All existing tests pass
- [ ] No breaking changes to TicketingToolPlugin interface
- [ ] Database migrations provided if needed
- [ ] Deprecation warnings if removing features

---

## Documentation Requirements

### 1. Plugin README.md

**Location:** `src/plugins/YOUR_TOOL/README.md`

**Required Sections:**
- Overview
- Configuration (tenant_configs fields)
- API Documentation links
- Webhook setup instructions
- Testing instructions

### 2. Implementation Example

Add to `docs/plugins/plugin-examples-YOUR_TOOL.md`:
- Complete plugin code
- Key implementation details
- API endpoints
- Testing examples
- Common issues

### 3. Update docs/plugins/index.md

Add plugin to navigation:
```markdown
### Reference
- [Your Tool Plugin Example](plugin-examples-your-tool.md)
```

---

## Security Requirements

### 1. Credential Management

**NEVER:**
- Hardcode API keys in code
- Log full credentials
- Store decrypted credentials

**ALWAYS:**
- Store encrypted in database
- Decrypt just-in-time
- Use masked logging (`api_key[:4]***`)

### 2. Webhook Validation

**MUST USE:**
- `secrets.compare_digest()` for signature comparison
- Constant-time algorithms
- HMAC-SHA256 or stronger

**NEVER:**
- Regular `==` comparison (timing attacks)
- Weak algorithms (MD5, SHA1)

### 3. Input Validation

**VALIDATE:**
- Tenant ID format
- Ticket ID format
- Payload structure
- Field types

**SANITIZE:**
- User-provided content
- API responses
- Database queries (use parameterized)

---

## Performance Requirements

### NFR001: Latency Targets

| Method | Target | How to Measure |
|--------|--------|----------------|
| validate_webhook() | <100ms | Performance test |
| get_ticket() | <2s | API call timing |
| update_ticket() | <3s | API call timing |

**Test Command:**
```bash
pytest tests/performance/test_YOUR_PLUGIN_performance.py -v
```

### Connection Pooling

**Required Configuration:**
```python
limits = httpx.Limits(
    max_connections=100,
    max_keepalive_connections=20
)
```

---

## Submission Process

### 1. Create Feature Branch

```bash
git checkout -b feature/plugin-YOUR_TOOL
```

### 2. Implement Plugin

Follow [Plugin Development Guide](../plugin-development-guide.md)

### 3. Run Quality Checks

```bash
# Format code
black src/plugins/YOUR_TOOL/

# Type check
mypy src/plugins/YOUR_TOOL/ --strict

# Run tests
pytest tests/unit/test_YOUR_TOOL_plugin.py -v
pytest tests/integration/test_YOUR_TOOL_integration.py -v

# Check coverage
pytest tests/ --cov=src/plugins/YOUR_TOOL --cov-fail-under=80
```

### 4. Create Pull Request

**PR Title Format:**
```
[Plugin] Add YOUR_TOOL plugin implementation
```

**PR Description Template:**
```markdown
## Summary
Implements YOUR_TOOL plugin for Epic 7 multi-tool support.

## Changes
- Plugin implementation (validate_webhook, get_ticket, update_ticket, extract_metadata)
- API client with retry logic
- Webhook validator
- 20 unit tests, 5 integration tests
- Documentation

## Testing
- [ ] All tests pass (pytest exit code 0)
- [ ] Coverage ≥80%
- [ ] mypy --strict passes
- [ ] Performance tests validate NFR001

## Checklist
- [ ] Code review checklist completed
- [ ] Documentation added
- [ ] Tests added
- [ ] No breaking changes

## Related Issues
Closes #123
```

### 5. Code Review

- Minimum 2 approvals required
- Address all review comments
- CI/CD must pass

### 6. Merge

- Squash and merge to main
- Delete feature branch
- Plugin released in next version

---

## PR Review Process

### Reviewer Responsibilities

**Check:**
1. All checklist items completed
2. Code follows patterns from existing plugins
3. Tests are comprehensive
4. Documentation is clear
5. No security vulnerabilities

**Provide:**
- Constructive feedback
- Specific suggestions
- Code examples
- References to docs

### Author Responsibilities

**Respond to:**
- All review comments
- Requested changes
- Questions

**Update:**
- Code based on feedback
- Tests if coverage gaps found
- Documentation if unclear

---

## Release Process

### Version Numbering

Follow semantic versioning (MAJOR.MINOR.PATCH):
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

### Release Checklist

- [ ] All tests pass on main branch
- [ ] CHANGELOG.md updated
- [ ] Version bumped in `pyproject.toml`
- [ ] Git tag created (`v1.2.0`)
- [ ] Release notes published
- [ ] Deployment to staging successful
- [ ] Deployment to production successful

---

## Deprecation Policy

### Deprecating Features

**Timeline:**
1. **Announcement** (6 months before removal)
   - Add deprecation warning
   - Update documentation
   - Notify users

2. **Migration Period** (6 months)
   - Provide migration guide
   - Support both old and new methods
   - Log deprecation warnings

3. **Removal** (After 6 months)
   - Remove deprecated code
   - Update major version
   - Update documentation

**Example:**
```python
from deprecated import deprecated

@deprecated(
    version='2.0.0',
    reason="Use get_ticket_batch() instead. Will be removed in v3.0.0"
)
async def get_ticket(self, ticket_id: str) -> Dict:
    warnings.warn("get_ticket() is deprecated", DeprecationWarning)
    ...
```

---

## Support

### Questions During Development

- Review [Plugin Development Guide](../plugin-development-guide.md)
- Check [Plugin Troubleshooting](plugin-troubleshooting.md)
- Search GitHub Issues
- Ask in GitHub Discussions

### Post-Submission Support

- Respond to issues within 1 week
- Fix bugs within 2 weeks
- Maintain compatibility with platform updates

---

## See Also

- [Plugin Development Guide](../plugin-development-guide.md)
- [Plugin Testing Guide](plugin-testing-guide.md)
- [Plugin Interface Reference](plugin-interface-reference.md)
