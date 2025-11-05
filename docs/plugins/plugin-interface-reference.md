# Plugin Interface Reference

[Plugin Docs](index.md) > Reference > Interface Specification

**Version:** 1.0
**Last Updated:** 2025-11-05
**Type:** Reference (Diátaxis Framework)

---

## Table of Contents

- [TicketingToolPlugin ABC](#ticketingtoolplugin-abc)
- [TicketMetadata Dataclass](#ticketmetadata-dataclass)
- [Abstract Methods](#abstract-methods)
- [Type Specifications](#type-specifications)
- [Exception Reference](#exception-reference)

---

## TicketingToolPlugin ABC

**Location:** `src/plugins/base.py`

### Class Definition

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class TicketingToolPlugin(ABC):
    """
    Abstract base class for ticketing tool integrations.

    All plugins must implement 4 abstract methods:
    - validate_webhook() - Authenticate incoming webhooks
    - get_ticket() - Fetch ticket details from tool API
    - update_ticket() - Post AI content back to ticket
    - extract_metadata() - Normalize payloads to TicketMetadata
    """

    @abstractmethod
    async def validate_webhook(
        self,
        payload: Dict[str, Any],
        signature: str
    ) -> bool:
        """Validate webhook request authenticity."""
        ...

    @abstractmethod
    async def get_ticket(
        self,
        tenant_id: str,
        ticket_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve ticket details from API."""
        ...

    @abstractmethod
    async def update_ticket(
        self,
        tenant_id: str,
        ticket_id: str,
        content: str
    ) -> bool:
        """Post enhancement content to ticket."""
        ...

    @abstractmethod
    def extract_metadata(
        self,
        payload: Dict[str, Any]
    ) -> TicketMetadata:
        """Extract standardized metadata from payload."""
        ...
```

### Inheritance Example

```python
class ServiceDeskPlusPlugin(TicketingToolPlugin):
    """ServiceDesk Plus implementation."""

    __tool_type__ = "servicedesk_plus"  # Optional identifier
    __version__ = "1.0.0"                # Optional version

    # Implement all 4 abstract methods...
```

---

## TicketMetadata Dataclass

**Location:** `src/plugins/base.py`

### Class Definition

```python
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TicketMetadata:
    """
    Standardized ticket metadata for enhancement workflow.
    """
    tenant_id: str
    ticket_id: str
    description: str
    priority: str        # Must be: "high", "medium", or "low"
    created_at: datetime  # Must be UTC timezone-aware
```

### Field Specifications

| Field | Type | Required | Validation | Example |
|-------|------|----------|------------|---------|
| `tenant_id` | `str` | Yes | `^[a-zA-Z0-9\-]+$` pattern | `"tenant-001"` |
| `ticket_id` | `str` | Yes | Max 100 characters | `"INC-123"` |
| `description` | `str` | Yes | Can be empty | `"User cannot access email"` |
| `priority` | `str` | Yes | `"high"`, `"medium"`, or `"low"` | `"high"` |
| `created_at` | `datetime` | Yes | UTC timezone-aware | `datetime(..., tzinfo=timezone.utc)` |

### Usage Example

```python
from datetime import datetime, timezone

metadata = TicketMetadata(
    tenant_id="tenant-001",
    ticket_id="INC-123",
    description="User login issue",
    priority="high",
    created_at=datetime(2025, 11, 5, 10, 0, 0, tzinfo=timezone.utc)
)
```

---

## Abstract Methods

### validate_webhook()

**Signature:**
```python
async def validate_webhook(
    self,
    payload: Dict[str, Any],
    signature: str
) -> bool
```

**Purpose:** Authenticate webhooks using HMAC-SHA256 or JWT

**Parameters:**
- `payload`: Webhook JSON payload
- `signature`: HMAC signature from request header

**Returns:** `True` if valid, `False` otherwise

**Performance:** <100ms (NFR001)

**Implementation Steps:**
1. Extract `tenant_id` from payload
2. Retrieve and decrypt webhook secret from `tenant_configs`
3. Compute expected signature (HMAC-SHA256 or JWT)
4. Use `secrets.compare_digest()` for constant-time comparison

**Example:**
```python
async def validate_webhook(self, payload: Dict[str, Any], signature: str) -> bool:
    tenant_id = payload.get("tenant_id")
    config = await self._get_tenant_config(tenant_id)
    secret = decrypt_value(config.webhook_secret_encrypted)

    payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    expected = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()

    return secrets.compare_digest(f"sha256={expected}", signature)
```

---

### get_ticket()

**Signature:**
```python
async def get_ticket(
    self,
    tenant_id: str,
    ticket_id: str
) -> Optional[Dict[str, Any]]
```

**Purpose:** Fetch ticket details via REST API for context gathering

**Parameters:**
- `tenant_id`: Tenant identifier
- `ticket_id`: Tool-specific ticket ID

**Returns:** Ticket JSON dict, or `None` if not found (404)

**Raises:** `APIError`, `AuthenticationError`

**Performance:** <2s (NFR001)

**Implementation Steps:**
1. Retrieve and decrypt API credentials from `tenant_configs`
2. Build tool-specific API URL
3. Execute async HTTP GET with `httpx.AsyncClient`
4. Implement 3-attempt retry with exponential backoff (2s, 4s, 8s)
5. Return raw JSON response

**Tool Endpoints:**
- ServiceDesk Plus: `GET /api/v3/tickets/{id}` (TECHNICIAN_KEY header)
- Jira: `GET /rest/api/3/issue/{key}` (Bearer token)
- Zendesk: `GET /api/v2/tickets/{id}.json` (API token)

---

### update_ticket()

**Signature:**
```python
async def update_ticket(
    self,
    tenant_id: str,
    ticket_id: str,
    content: str
) -> bool
```

**Purpose:** Post AI enhancement as internal note

**Parameters:**
- `tenant_id`: Tenant identifier
- `ticket_id`: Tool-specific ticket ID
- `content`: Markdown or HTML enhancement text

**Returns:** `True` on success, `False` on failure

**Raises:** `APIError`, `AuthenticationError`

**Performance:** <5s including retries (NFR001)

**Security:** Always post as **internal/private** note

**Implementation Steps:**
1. Retrieve and decrypt API credentials
2. Convert markdown to tool-specific format (HTML for ServiceDesk, ADF for Jira)
3. Build POST/PUT request with tool-specific payload
4. Implement retry logic (3 attempts, 2s/4s/8s delays)
5. Handle rate limiting (429 responses, respect Retry-After header)

**Tool Endpoints:**
- ServiceDesk Plus: `POST /api/v3/tickets/{id}/notes` (show_to_requester: false)
- Jira: `POST /rest/api/3/issue/{key}/comment` (internal visibility)
- Zendesk: `PUT /api/v2/tickets/{id}.json` (public: false)

---

### extract_metadata()

**Signature:**
```python
def extract_metadata(
    self,
    payload: Dict[str, Any]
) -> TicketMetadata
```

**Purpose:** Normalize tool-specific payloads to TicketMetadata

**Parameters:**
- `payload`: Raw webhook JSON

**Returns:** `TicketMetadata` dataclass

**Raises:** `ValidationError` if fields missing/invalid

**Performance:** <10ms (no I/O, pure Python)

**Synchronous:** No async/await (pure data transformation)

**Implementation Steps:**
1. Extract `tenant_id`, `ticket_id`, `description` from tool-specific paths
2. Normalize priority to `"high"`, `"medium"`, or `"low"`
3. Parse timestamp to UTC datetime
4. Validate all fields present and correct types
5. Return `TicketMetadata` instance

**Priority Normalization Maps:**

ServiceDesk Plus:
```python
{"Urgent": "high", "High": "high", "Medium": "medium", "Low": "low"}
```

Jira:
```python
{"Highest": "high", "Critical": "high", "High": "high",
 "Medium": "medium", "Low": "low", "Lowest": "low"}
```

Zendesk:
```python
{"urgent": "high", "high": "high", "normal": "medium", "low": "low"}
```

---

## Type Specifications

### Import Statements

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional
```

### Type Aliases

```python
Payload = Dict[str, Any]
Signature = str
TenantID = str
TicketID = str
Content = str
```

### Mypy Validation

All plugins must pass strict mode:

```bash
mypy src/plugins/ --strict
```

Expected: `Success: no issues found`

---

## Exception Reference

### Exception Hierarchy

```python
# src/plugins/exceptions.py

class PluginError(Exception):
    """Base exception for plugin errors."""
    pass

class ValidationError(PluginError):
    """Payload validation failed."""
    pass

class APIError(PluginError):
    """External API call failed."""
    def __init__(self, message: str, retry_count: int = 0, last_error: Exception = None):
        super().__init__(message)
        self.retry_count = retry_count
        self.last_error = last_error

class AuthenticationError(PluginError):
    """API authentication failed (401/403)."""
    pass

class RateLimitError(PluginError):
    """API rate limit exceeded (429)."""
    def __init__(self, message: str, retry_after: int = None):
        super().__init__(message)
        self.retry_after = retry_after

class ConfigurationError(PluginError):
    """Tenant configuration invalid/missing."""
    pass
```

### Exception Usage

```python
# Raise with context
raise ValidationError(f"Missing field 'ticket_id' in payload: {payload}")

# Raise after retries
raise APIError(
    f"Failed to get ticket after 3 attempts",
    retry_count=3,
    last_error=last_exception
)

# Handle authentication
try:
    ticket = await plugin.get_ticket(tenant_id, ticket_id)
except AuthenticationError as e:
    logger.error(f"Auth error: {e}")
    await send_alert("Plugin auth failure", str(e))
```

---

## See Also

- **How-To Guides:** [Plugin Manager](plugin-manager-guide.md), [Type Safety](plugin-type-safety.md), [Error Handling](plugin-error-handling.md)
- **Examples:** [ServiceDesk Plus](plugin-examples-servicedesk.md), [Jira](plugin-examples-jira.md)
- **Tutorial:** [Plugin Development Guide](../plugin-development-guide.md)
- **Support:** [Troubleshooting](plugin-troubleshooting.md)

---

**Version History:**
- 1.0 (2025-11-05): Initial concise reference from plugin-architecture.md split
