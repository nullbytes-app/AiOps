# Plugin Development Guide

**Tutorial:** Building Your First Plugin (Zendesk Example)

**Last Updated:** 2025-11-05

---

## Overview

This step-by-step tutorial guides you through building a complete Zendesk plugin. Follow along to understand the plugin development process.

**Prerequisites:**
- Python 3.12+
- Basic understanding of async/await
- Familiarity with REST APIs
- Zendesk account for testing

**Time Required:** 2-3 hours

---

## Step 1: Set Up Development Environment

### Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
pip install httpx==0.25.0
pip install pydantic==2.4.2
pip install pytest==7.4.3
pip install pytest-asyncio==0.21.1
pip install mypy==1.7.0
```

### Create Plugin Directory

```bash
mkdir -p src/plugins/zendesk
cd src/plugins/zendesk
touch __init__.py plugin.py api_client.py webhook_validator.py
```

---

## Step 2: Implement Plugin Base Class

**File:** `src/plugins/zendesk/plugin.py`

```python
from src.plugins.base import TicketingToolPlugin, TicketMetadata
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ZendeskPlugin(TicketingToolPlugin):
    """
    Zendesk Support plugin implementation.

    API Docs: https://developer.zendesk.com/api-reference/
    """

    __tool_type__ = "zendesk"

    async def validate_webhook(
        self, payload: Dict[str, Any], signature: str
    ) -> bool:
        """Validate Zendesk webhook JWT token."""
        # TODO: Implement JWT validation
        pass

    async def get_ticket(
        self, tenant_id: str, ticket_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve ticket from Zendesk API."""
        # TODO: Implement ticket retrieval
        pass

    async def update_ticket(
        self, tenant_id: str, ticket_id: str, content: str
    ) -> bool:
        """Add internal note to Zendesk ticket."""
        # TODO: Implement ticket update
        pass

    def extract_metadata(self, payload: Dict[str, Any]) -> TicketMetadata:
        """Extract metadata from Zendesk webhook."""
        # TODO: Implement metadata extraction
        pass
```

---

## Step 3: Implement Webhook Validation

Zendesk uses JWT (JSON Web Tokens) for webhook authentication.

**File:** `src/plugins/zendesk/webhook_validator.py`

```python
import jwt
from typing import Optional


def validate_jwt_token(token: str, secret: str) -> bool:
    """
    Validate Zendesk JWT webhook token.

    Args:
        token: JWT token from Authorization header
        secret: Webhook signing secret from tenant config

    Returns:
        True if valid, False otherwise
    """
    try:
        # Decode and verify JWT
        jwt.decode(
            token,
            secret,
            algorithms=['HS256'],
            options={"verify_exp": True}
        )
        return True

    except jwt.ExpiredSignatureError:
        logger.error("JWT token expired")
        return False

    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid JWT token: {e}")
        return False
```

**Update plugin.py:**

```python
from src.plugins.zendesk.webhook_validator import validate_jwt_token

async def validate_webhook(
    self, payload: Dict[str, Any], signature: str
) -> bool:
    """Validate Zendesk webhook JWT token."""
    try:
        # Extract tenant_id from payload
        tenant_id = payload.get("tenant_id")
        if not tenant_id:
            return False

        # Get tenant config
        config = await self._get_tenant_config(tenant_id)
        if not config:
            return False

        # Validate JWT
        return validate_jwt_token(signature, config.webhook_secret_encrypted)

    except Exception as e:
        logger.error(f"Webhook validation error: {e}")
        return False
```

---

## Step 4: Implement API Client

**File:** `src/plugins/zendesk/api_client.py`

```python
import httpx
from typing import Any, Dict, Optional

class ZendeskAPIClient:
    """Async Zendesk API v2 client."""

    def __init__(self, subdomain: str, api_token: str, email: str):
        self.base_url = f"https://{subdomain}.zendesk.com"
        timeout = httpx.Timeout(connect=5.0, read=30.0)
        self.client = httpx.AsyncClient(
            timeout=timeout,
            auth=(f"{email}/token", api_token)
        )

    async def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """GET /api/v2/tickets/{id}.json"""
        url = f"{self.base_url}/api/v2/tickets/{ticket_id}.json"
        response = await self.client.get(url)
        return response.json() if response.status_code == 200 else None

    async def add_internal_note(self, ticket_id: str, text: str) -> bool:
        """PUT /api/v2/tickets/{id}.json - Adds internal note."""
        url = f"{self.base_url}/api/v2/tickets/{ticket_id}.json"
        payload = {"ticket": {"comment": {"body": text, "public": False}}}
        response = await self.client.put(url, json=payload)
        return response.status_code == 200

    async def close(self):
        await self.client.aclose()
```

See [ServiceDesk Plus Example](plugins/plugin-examples-servicedesk.md) for retry logic and error handling patterns.

---

## Step 5: Implement Metadata Extraction

**Update plugin.py:**

```python
from datetime import datetime

def extract_metadata(self, payload: Dict[str, Any]) -> TicketMetadata:
    """
    Extract metadata from Zendesk webhook payload.

    Zendesk payload structure:
    {
        "ticket": {
            "id": 123,
            "subject": "...",
            "description": "...",
            "priority": "high",
            "created_at": "2025-11-05T14:30:00Z"
        },
        "tenant_id": "tenant-001"
    }
    """
    try:
        ticket = payload.get("ticket", {})

        tenant_id = payload.get("tenant_id", "")
        ticket_id = str(ticket["id"])
        description = ticket.get("description", "")
        priority_raw = ticket.get("priority", "normal")
        created_at_str = ticket.get("created_at")

        # Normalize priority
        priority_map = {
            "urgent": "high",
            "high": "high",
            "normal": "medium",
            "low": "low",
        }
        priority = priority_map.get(priority_raw, "medium")

        # Parse ISO 8601 timestamp
        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))

        return TicketMetadata(
            tenant_id=tenant_id,
            ticket_id=ticket_id,
            description=description,
            priority=priority,
            created_at=created_at
        )

    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Metadata extraction error: {e}")
        raise ValidationError(f"Failed to extract Zendesk metadata: {e}")
```

---

## Step 6: Complete Plugin Implementation

Connect API client to plugin methods. See full implementation in [ServiceDesk Plus Example](plugins/plugin-examples-servicedesk.md).

```python
async def get_ticket(self, tenant_id: str, ticket_id: str) -> Optional[Dict]:
    config = await self._get_tenant_config(tenant_id)
    client = ZendeskAPIClient(config.zendesk_subdomain, config.api_token, config.email)
    try:
        return await client.get_ticket(ticket_id)
    finally:
        await client.close()

async def update_ticket(self, tenant_id: str, ticket_id: str, content: str) -> bool:
    config = await self._get_tenant_config(tenant_id)
    client = ZendeskAPIClient(config.zendesk_subdomain, config.api_token, config.email)
    try:
        return await client.add_internal_note(ticket_id, content)
    finally:
        await client.close()
```

---

## Step 7: Write Unit Tests

**File:** `tests/unit/test_zendesk_plugin.py`

```python
import pytest
from unittest.mock import AsyncMock, patch
from src.plugins.zendesk.plugin import ZendeskPlugin


@pytest.mark.asyncio
async def test_validate_webhook_success():
    """Test successful JWT validation."""
    plugin = ZendeskPlugin()
    payload = {"tenant_id": "tenant-001", "ticket": {"id": 123}}
    token = "valid.jwt.token"

    with patch('src.plugins.zendesk.webhook_validator.validate_jwt_token') as mock:
        mock.return_value = True
        result = await plugin.validate_webhook(payload, token)

    assert result is True


def test_extract_metadata_success():
    """Test metadata extraction."""
    plugin = ZendeskPlugin()
    payload = {
        "tenant_id": "tenant-001",
        "ticket": {
            "id": 123,
            "description": "Email issue",
            "priority": "urgent",
            "created_at": "2025-11-05T14:30:00Z"
        }
    }

    metadata = plugin.extract_metadata(payload)

    assert metadata.tenant_id == "tenant-001"
    assert metadata.ticket_id == "123"
    assert metadata.priority == "high"
```

---

## Step 8: Register Plugin

**File:** `src/plugins/__init__.py`

```python
from src.plugins.registry import PluginRegistry
from src.plugins.zendesk.plugin import ZendeskPlugin

# Register Zendesk plugin
PluginRegistry.register("zendesk", ZendeskPlugin)
```

---

## Step 9: Type Checking

```bash
# Run mypy
mypy src/plugins/zendesk/ --strict

# Expected output:
# Success: no issues found in 3 source files
```

---

## Step 10: Run Tests

```bash
# Run unit tests
pytest tests/unit/test_zendesk_plugin.py -v

# Run with coverage
pytest tests/unit/test_zendesk_plugin.py --cov=src/plugins/zendesk
```

---

## Step 11: Test Integration

Create test tenant config in database and test webhook endpoint. See [Plugin Testing Guide](plugins/plugin-testing-guide.md) for integration test patterns.

---

## Step 12: Documentation

**File:** `src/plugins/zendesk/README.md`

```markdown
# Zendesk Plugin

Zendesk Support integration for AI Agents Platform.

## Configuration

Required tenant config fields:
- `zendesk_subdomain`: Zendesk subdomain (e.g., "mycompany" for mycompany.zendesk.com)
- `zendesk_email`: Agent email for API authentication
- `zendesk_api_token_encrypted`: API token (encrypted)
- `webhook_secret_encrypted`: Webhook signing secret (encrypted)

## API Documentation

- [Zendesk API Reference](https://developer.zendesk.com/api-reference/)
- [Webhook Security](https://developer.zendesk.com/documentation/webhooks/verifying/)

## Testing

See tests/unit/test_zendesk_plugin.py for examples.
```

---

## Step 13: Code Review Checklist

- [ ] All 4 abstract methods implemented
- [ ] Type hints on all public methods
- [ ] Mypy --strict passes with 0 errors
- [ ] 15+ unit tests, 80%+ coverage
- [ ] Error handling with retries
- [ ] Logging for debugging
- [ ] Connection pooling enabled
- [ ] Constant-time comparison for security
- [ ] Documentation complete

---

## Step 14: Submit for Review

See [Plugin Submission Guidelines](plugins/plugin-submission-guidelines.md) for PR process.

---

## Step 15: Deploy

After approval:

```bash
# Build
python -m build

# Deploy to staging
kubectl apply -f k8s/staging/

# Run smoke tests
./scripts/smoke-test.sh

# Deploy to production
kubectl apply -f k8s/production/
```

---

## Congratulations!

You've built a complete plugin. Next steps:

- [ ] Review [Plugin Testing Guide](plugins/plugin-testing-guide.md)
- [ ] Check [Plugin Performance Guide](plugins/plugin-performance.md)
- [ ] Read [Plugin Troubleshooting Guide](plugins/plugin-troubleshooting.md)

---

## See Also

- [Plugin Interface Reference](plugins/plugin-interface-reference.md)
- [Plugin Examples](plugins/plugin-examples-servicedesk.md)
- [Plugin Submission Guidelines](plugins/plugin-submission-guidelines.md)
