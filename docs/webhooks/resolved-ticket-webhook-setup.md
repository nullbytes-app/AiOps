# ServiceDesk Plus Resolved Ticket Webhook Configuration

This guide explains how to configure ServiceDesk Plus to send resolved ticket notifications to the AI Agents platform via webhook.

## Overview

The AI Agents platform provides a webhook endpoint that automatically ingests resolved tickets from ServiceDesk Plus. This enables the enhancement agent to access fresh ticket context without requiring manual bulk imports.

**Webhook Endpoint:**
```
POST https://your-domain.com/webhook/servicedesk/resolved-ticket
```

**Trigger Event:** Ticket status changes to "Resolved" or "Closed"

**Processing Mode:** Asynchronous (202 Accepted response returned immediately; storage happens in background)

---

## Configuration Steps

### Step 1: Configure Webhook in ServiceDesk Plus Admin

1. Log in to ServiceDesk Plus as an administrator
2. Navigate to **Admin → Workflows → Webhooks** (or **Admin → Webhooks** depending on version)
3. Click **Create Webhook** or **Add New**
4. Fill in the following fields:

| Field | Value |
|-------|-------|
| **Webhook Name** | AI Agents - Resolved Ticket Ingestion |
| **Event Trigger** | Ticket Status Change → "Resolved" or "Closed" |
| **Webhook URL** | `https://your-domain.com/webhook/servicedesk/resolved-ticket` |
| **HTTP Method** | POST |
| **Content-Type** | application/json |
| **Authentication** | HMAC-SHA256 (see below) |

### Step 2: Generate Shared Secret

The webhook endpoint validates all requests using HMAC-SHA256 signatures to ensure authenticity.

**On the AI Agents platform:**
- The webhook secret is configured via environment variable: `AI_AGENTS_WEBHOOK_SECRET`
- Minimum recommended length: 32 characters (alphanumeric)
- Example: `"your-secure-webhook-secret-min-32-chars"`

**In ServiceDesk Plus:**
- Store the same secret in a secure location (e.g., password manager, vault)
- Use this secret to compute signatures (see **Signature Computation** below)

### Step 3: Configure HTTP Headers

Add the following header to the webhook request:

```
X-ServiceDesk-Signature: <HMAC-SHA256 signature>
```

**Signature Computation:**

1. Take the raw webhook payload (JSON string, before any encoding)
2. Compute HMAC-SHA256 using:
   - **Key:** Your shared secret (from Step 2)
   - **Message:** Raw JSON payload
   - **Algorithm:** SHA256
3. Convert result to hexadecimal
4. Include in `X-ServiceDesk-Signature` header

**Example (Python):**
```python
import json
import hmac
import hashlib

payload = {
    "tenant_id": "acme-corp",
    "ticket_id": "TKT-12345",
    "subject": "Issue title",
    "description": "Detailed description",
    "resolution": "Solution applied",
    "resolved_date": "2025-11-01T14:30:00Z",
    "priority": "high",
    "tags": ["tag1", "tag2"]
}

secret = "your-secure-webhook-secret-min-32-chars"
payload_bytes = json.dumps(payload).encode("utf-8")
signature = hmac.new(
    key=secret.encode("utf-8"),
    msg=payload_bytes,
    digestmod=hashlib.sha256
).hexdigest()

# Use signature in header: X-ServiceDesk-Signature: {signature}
```

---

## Webhook Payload Structure

The webhook sends the following JSON payload when a ticket is resolved:

```json
{
    "tenant_id": "acme-corp",
    "ticket_id": "TKT-12345",
    "subject": "Database connection pool exhausted",
    "description": "Connection pool exhausted after office hours backup job.",
    "resolution": "Increased pool size from 10 to 25. Added monitoring alert.",
    "resolved_date": "2025-11-01T14:30:00Z",
    "priority": "high",
    "tags": ["database", "performance", "infrastructure"]
}
```

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tenant_id` | string | Yes | Client/tenant identifier for multi-tenant isolation |
| `ticket_id` | string | Yes | Unique ticket ID from ServiceDesk Plus |
| `subject` | string | Yes | Ticket title or subject |
| `description` | string | Yes | Full ticket description (max 10,000 chars) |
| `resolution` | string | Yes | Resolution or solution applied |
| `resolved_date` | ISO 8601 datetime | Yes | When ticket was resolved (UTC) |
| `priority` | enum | Yes | Priority level: `low`, `medium`, `high`, `critical` |
| `tags` | array of strings | No | Optional tags/categories (defaults to empty) |

---

## Response Codes

### Success (202 Accepted)
The webhook was received and queued for processing. Ticket will be stored asynchronously.

```json
{
    "status": "accepted"
}
```

### Client Errors

| Status | Reason | Action |
|--------|--------|--------|
| **401 Unauthorized** | Missing or invalid signature | Verify shared secret and signature computation |
| **422 Unprocessable Entity** | Invalid payload (missing field, wrong type, etc.) | Review payload structure against schema |
| **400 Bad Request** | Malformed JSON | Ensure JSON is valid |

### Server Errors

| Status | Reason | Action |
|--------|--------|--------|
| **503 Service Unavailable** | Database connection unavailable | Retry webhook delivery after service is restored |
| **500 Internal Server Error** | Unexpected error | Contact platform support with correlation ID |

**Note:** Even if storage fails (5xx response), the webhook endpoint will log the error and alert monitoring systems. Retry delivery according to your webhook configuration.

---

## Testing the Webhook

### Using cURL

```bash
#!/bin/bash

# Configuration
WEBHOOK_URL="https://your-domain.com/webhook/servicedesk/resolved-ticket"
SHARED_SECRET="your-secure-webhook-secret-min-32-chars"

# Payload
PAYLOAD='{"tenant_id":"acme-corp","ticket_id":"TKT-TEST-001","subject":"Test issue","description":"Testing webhook integration","resolution":"Test resolved","resolved_date":"2025-11-01T14:30:00Z","priority":"medium","tags":["test"]}'

# Compute signature
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SHARED_SECRET" -hex | awk '{print $2}')

# Send webhook
curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -H "X-ServiceDesk-Signature: $SIGNATURE" \
  -d "$PAYLOAD"
```

### Using ServiceDesk Plus Webhook Log Viewer

1. Navigate to **Admin → Webhooks**
2. Select your webhook
3. Click **View Deliveries** or **View Logs**
4. Check:
   - Request timestamp
   - Response status code
   - Response body (for error details)
   - Number of retries (if applicable)

---

## Monitoring and Debugging

### Webhook Delivery Monitoring

The AI Agents platform logs all webhook events with:
- Timestamp
- Correlation ID (for tracing)
- Tenant ID
- Ticket ID
- Event type (received, stored, error)
- Error details (if applicable)

**Log Example:**
```
2025-11-01 14:30:45 [INFO] Resolved ticket webhook received: ticket_id=TKT-12345, tenant_id=acme-corp, correlation_id=550e8400-e29b-41d4-a716-446655440000
2025-11-01 14:30:46 [INFO] Resolved ticket stored: ticket_id=TKT-12345, tenant_id=acme-corp, action=inserted
```

### Troubleshooting

**Webhook fails with 401 Unauthorized:**
- Verify shared secret matches configuration
- Verify signature computation uses **raw JSON payload** (not URL-encoded)
- Check header name is exactly `X-ServiceDesk-Signature` (case-sensitive in some systems)

**Webhook fails with 422 Unprocessable Entity:**
- Verify all required fields are present
- Verify `resolved_date` is valid ISO8601 format
- Verify `priority` is one of: low, medium, high, critical
- Verify `description` does not exceed 10,000 characters

**Webhook fails with 503 Service Unavailable:**
- Platform database is temporarily unavailable
- Webhook will be retried automatically by ServiceDesk Plus
- Check platform status page or monitoring system

**Ticket not stored after successful 202 response:**
- Background processing may take a few seconds
- Check platform logs for storage errors (see above)
- Verify tenant_id exists in platform tenant configuration

---

## Performance Characteristics

- **Endpoint Response Time:** <50ms (202 Accepted returned immediately)
- **Storage Completion:** <1 second per ticket (background processing)
- **Throughput:** Supports 1000+ webhooks/minute
- **Idempotency:** If webhook is delivered twice (network retry), the second delivery updates existing ticket instead of creating duplicate

---

## Related Documentation

- [Story 2.5B: Store Resolved Tickets Automatically](../stories/2-5B-store-resolved-tickets-automatically.md)
- [Story 2.2: Implement Webhook Signature Validation](../stories/2-2-implement-webhook-signature-validation.md)
- [Story 2.5: Implement Ticket History Search](../stories/2-5-implement-ticket-history-search-context-gathering.md)
- [API Endpoint Reference](/docs/api-reference.md#post-webhookservicedeskresolved-ticket)
