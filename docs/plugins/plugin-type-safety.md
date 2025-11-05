# Plugin Type Safety Guide

[Plugin Docs](index.md) > How-To Guides > Type Safety

**Last Updated:** 2025-11-05

---

## Overview

This guide covers type hints, mypy validation, and best practices for maintaining type safety in plugin development. Type safety prevents runtime errors and improves code maintainability.

---

## Why Type Safety Matters

**Benefits:**
1. **Compile-time validation** - Catch errors before runtime
2. **IDE support** - Autocomplete, refactoring, inline documentation
3. **Self-documenting code** - Type signatures clarify intent
4. **Refactoring safety** - Mypy catches breaking changes
5. **Plugin contract enforcement** - Mypy verifies all abstract methods implemented

---

## Type Hints Basics

### Function Signatures

```python
from typing import Dict, Any, Optional

# ✅ GOOD: Fully typed function
async def get_ticket(
    self,
    tenant_id: str,
    ticket_id: str
) -> Optional[Dict[str, Any]]:
    """Retrieve ticket from API."""
    ...

# ❌ BAD: Missing type hints
async def get_ticket(self, tenant_id, ticket_id):
    ...
```

### Return Types

```python
# ✅ GOOD: Explicit Optional for nullable returns
async def get_ticket(...) -> Optional[Dict[str, Any]]:
    if not found:
        return None
    return ticket_data

# ❌ BAD: Implicit None return (mypy error)
async def get_ticket(...) -> Dict[str, Any]:
    if not found:
        return None  # Type error: None not compatible with Dict
```

### Async Functions

```python
# ✅ GOOD: async with proper return type
async def validate_webhook(...) -> bool:
    result = await some_async_operation()
    return result

# ❌ BAD: Missing async keyword
def validate_webhook(...) -> bool:
    result = await some_async_operation()  # SyntaxError
```

---

## Common Type Issues and Solutions

### Issue 1: Missing Return Type

**Problem:**
```python
async def get_ticket(self, tenant_id: str, ticket_id: str):
    return await api_call()
```

**Solution:**
```python
async def get_ticket(
    self,
    tenant_id: str,
    ticket_id: str
) -> Optional[Dict[str, Any]]:
    return await api_call()
```

### Issue 2: Using Any Excessively

**Problem:**
```python
def process_payload(self, data: Any) -> Any:
    ...
```

**Solution:**
```python
def process_payload(self, data: Dict[str, Any]) -> TicketMetadata:
    ...
```

### Issue 3: Incorrect Optional Usage

**Problem:**
```python
def extract_metadata(self, payload: Dict[str, Any]) -> Optional[TicketMetadata]:
    return TicketMetadata(...)  # Never returns None
```

**Solution:**
```python
def extract_metadata(self, payload: Dict[str, Any]) -> TicketMetadata:
    return TicketMetadata(...)
```

### Issue 4: Dict vs dict (Python 3.9+)

**Modern (Python 3.9+):**
```python
def get_ticket(self, ...) -> dict[str, Any]:
    ...
```

**Legacy (Python 3.8):**
```python
from typing import Dict

def get_ticket(self, ...) -> Dict[str, Any]:
    ...
```

### Issue 5: Missing Import for Type Hints

**Problem:**
```python
def get_config(self) -> TenantConfig:  # NameError
    ...
```

**Solution:**
```python
from src.database.models import TenantConfig

def get_config(self) -> TenantConfig:
    ...
```

---

## Mypy Validation

### Basic Commands

```bash
# Validate single file
mypy src/plugins/base.py

# Validate entire plugins module
mypy src/plugins/

# Validate with strict mode
mypy --strict src/plugins/

# Show error codes (useful for # type: ignore comments)
mypy --show-error-codes src/plugins/
```

### Expected Output (Success)

```bash
$ mypy src/plugins/base.py
Success: no issues found in 1 source file
```

### Expected Output (Failure)

```bash
$ mypy src/plugins/implementations/jira_sm.py
src/plugins/implementations/jira_sm.py:45: error: Missing return statement  [return]
src/plugins/implementations/jira_sm.py:60: error: Argument 1 has incompatible type "str"; expected "bytes"  [arg-type]
Found 2 errors in 1 file (checked 1 source file)
```

---

## Mypy Configuration

**File:** `mypy.ini` (project root)

```ini
[mypy]
python_version = 3.12
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = False  # Global setting

# Strict settings for plugins module
[mypy-src.plugins.*]
disallow_untyped_defs = True
disallow_any_unimported = True
warn_return_any = True
warn_unused_ignores = True
check_untyped_defs = True
no_implicit_optional = True
strict_optional = True

# Ignore type hints for third-party libraries without stubs
[mypy-httpx.*]
ignore_missing_imports = True

[mypy-markdown.*]
ignore_missing_imports = True
```

---

## Resolving Common Mypy Errors

### Error: "Missing return statement"

**Mypy Output:**
```
error: Missing return statement  [return]
```

**Cause:** Function declares return type but some code paths don't return

**Solution:**
```python
# ❌ BAD: Missing return in if branch
async def get_ticket(...) -> Dict[str, Any]:
    if condition:
        return data
    # Missing return here

# ✅ GOOD: All paths return or raise
async def get_ticket(...) -> Dict[str, Any]:
    if condition:
        return data
    raise ValueError("Condition not met")
```

### Error: "Incompatible return value type"

**Mypy Output:**
```
error: Incompatible return value type (got "None", expected "Dict[str, Any]")  [return-value]
```

**Cause:** Function returns None but return type doesn't include Optional

**Solution:**
```python
# ❌ BAD: Returns None but type is Dict
async def get_ticket(...) -> Dict[str, Any]:
    if not found:
        return None

# ✅ GOOD: Use Optional
async def get_ticket(...) -> Optional[Dict[str, Any]]:
    if not found:
        return None
    return data
```

### Error: "Argument has incompatible type"

**Mypy Output:**
```
error: Argument 1 to "hmac.new" has incompatible type "str"; expected "bytes"  [arg-type]
```

**Cause:** Passing wrong type to function

**Solution:**
```python
# ❌ BAD: Passing str instead of bytes
hmac.new(secret, payload, hashlib.sha256)

# ✅ GOOD: Encode str to bytes
hmac.new(secret.encode('utf-8'), payload, hashlib.sha256)
```

### Error: "Need type annotation"

**Mypy Output:**
```
error: Need type annotation for "config"  [var-annotated]
```

**Cause:** Variable type cannot be inferred

**Solution:**
```python
# ❌ BAD: Type unclear
config = None

# ✅ GOOD: Explicit type annotation
config: Optional[TenantConfig] = None
```

---

## Async Type Hints

### Async Function Returns

```python
# Return value type, not coroutine type
async def get_ticket(...) -> Optional[Dict[str, Any]]:
    ...

# NOT: async def get_ticket(...) -> Coroutine[Any, Any, Optional[Dict[str, Any]]]:
```

### Awaitable Type Hints

```python
from typing import Awaitable

def create_task() -> Awaitable[bool]:
    return asyncio.create_task(some_async_function())
```

### AsyncIterator/AsyncGenerator

```python
from typing import AsyncIterator

async def stream_tickets() -> AsyncIterator[Dict[str, Any]]:
    for ticket_id in ticket_ids:
        ticket = await get_ticket(ticket_id)
        yield ticket
```

---

## Type Checking in Tests

### Mocking with Type Hints

```python
from unittest.mock import AsyncMock
from typing import cast

# Type-safe mock
mock_client = AsyncMock()
mock_client.get.return_value = {"id": "123"}

# Cast to satisfy mypy
client = cast(httpx.AsyncClient, mock_client)
```

### Parametrized Tests

```python
import pytest
from typing import Tuple

@pytest.mark.parametrize(
    "priority_input,expected",
    [
        ("Urgent", "high"),
        ("Medium", "medium"),
        ("Low", "low"),
    ]
)
def test_priority_normalization(
    priority_input: str,
    expected: str
) -> None:
    ...
```

---

## CI/CD Integration

**GitHub Actions Workflow:** `.github/workflows/ci.yml`

```yaml
- name: Run mypy type checking
  run: |
    mypy src/plugins/ --strict
    if [ $? -ne 0 ]; then
      echo "❌ Mypy type checking failed"
      exit 1
    fi
    echo "✅ Mypy type checking passed"
```

**Pre-commit Hook:** `.pre-commit-config.yaml`

```yaml
- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v1.7.0
  hooks:
    - id: mypy
      args: [--strict, --show-error-codes]
      additional_dependencies: [types-all]
      files: ^src/plugins/
```

---

## Type Ignore Comments (Use Sparingly)

When you must bypass mypy (e.g., third-party library issues):

```python
# Use specific error codes, not blanket ignores
result = some_untyped_library_call()  # type: ignore[no-untyped-call]

# NOT: result = some_untyped_library_call()  # type: ignore
```

**Valid reasons for type: ignore:**
- Third-party library without type stubs
- Known mypy bug
- Complex dynamic behavior mypy can't infer

**Invalid reasons:**
- "Too lazy to fix type error"
- "Type hints are annoying"

---

## Type Stubs for Plugin Interface

**File:** `src/plugins/base.pyi` (optional stub file)

```python
from typing import Any, Dict, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

class TicketingToolPlugin(ABC):
    @abstractmethod
    async def validate_webhook(
        self, payload: Dict[str, Any], signature: str
    ) -> bool: ...

    @abstractmethod
    async def get_ticket(
        self, tenant_id: str, ticket_id: str
    ) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    async def update_ticket(
        self, tenant_id: str, ticket_id: str, content: str
    ) -> bool: ...

    @abstractmethod
    def extract_metadata(self, payload: Dict[str, Any]) -> TicketMetadata: ...

@dataclass
class TicketMetadata:
    tenant_id: str
    ticket_id: str
    description: str
    priority: str
    created_at: datetime
```

---

## Best Practices Checklist

- [ ] All public methods have type hints (parameters + return)
- [ ] Use Optional[T] for nullable returns
- [ ] Use Dict[str, Any] instead of bare Any
- [ ] Async functions use async def, not def
- [ ] Import type hints from typing module
- [ ] Run mypy --strict before committing
- [ ] Zero mypy errors in CI/CD
- [ ] Use type: ignore sparingly with error codes
- [ ] Type hints match actual runtime behavior
- [ ] Test code also uses type hints

---

## See Also

- [Plugin Interface Reference](plugin-interface-reference.md)
- [Python Type Hints (PEP 484)](https://peps.python.org/pep-0484/)
- [Mypy Documentation](https://mypy.readthedocs.io/)
- [Python typing Module](https://docs.python.org/3/library/typing.html)
