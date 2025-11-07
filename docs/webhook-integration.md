# Webhook Integration Guide

**Last Updated:** 2025-11-06
**Story:** 8.6 - Agent Webhook Endpoint Generation

## Overview

This guide explains how to integrate external systems with AI Agents using secure webhooks. Webhooks allow external systems (ServiceDesk Plus, Jira, custom applications) to trigger specific AI agents by sending HTTP requests.

### Key Features

- **Auto-Generated Webhook URLs**: Each agent gets a unique webhook endpoint
- **HMAC-SHA256 Signature Validation**: Industry-standard security using GitHub/Stripe convention
- **Payload Schema Validation**: Optional JSON Schema validation for type safety
- **Test Webhook UI**: Built-in testing interface for debugging
- **Secret Rotation**: Easy regeneration of HMAC secrets when compromised

---

## Quick Start

### Step 1: Create an Agent

Create an AI agent through the Admin UI (`http://localhost:3000`):

1. Navigate to "Agent Management"
2. Click "Create New Agent"
3. Fill in basic information (name, description, system prompt)
4. In the "Triggers" tab, enable "Enable Webhook"
5. **(Optional)** Define a payload schema for validation
6. Click "Create Agent"

### Step 2: Get Webhook URL and Secret

After creation, view the agent details:

1. Click on the agent name to open details
2. Locate "Webhook Configuration" section
3. **Webhook URL**: Copy using the "📋 Copy URL" button
   - Format: `http://localhost:8000/webhook/agents/{agent_id}/webhook`
4. **HMAC Secret**: Click "👁️ Show" to reveal, then copy
   - ⚠️ **Keep this secret secure!** Anyone with this key can trigger your agent.

---

## Sending Webhook Requests

### Basic cURL Example

```bash
# Set variables
WEBHOOK_URL="http://localhost:8000/webhook/agents/YOUR_AGENT_ID/webhook"
HMAC_SECRET="YOUR_BASE64_ENCODED_SECRET"

# Prepare payload
PAYLOAD='{"ticket_id": "T-12345", "priority": "high"}'

# Compute HMAC-SHA256 signature
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$HMAC_SECRET" | sed 's/^.* //')

# Send webhook request
curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=$SIGNATURE" \
  -d "$PAYLOAD"
```

**Expected Response (202 Accepted):**
```json
{
  "status": "queued",
  "execution_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "message": "Agent execution queued"
}
```

---

### Python Example

```python
import hmac
import hashlib
import json
import requests

# Configuration
WEBHOOK_URL = "http://localhost:8000/webhook/agents/YOUR_AGENT_ID/webhook"
HMAC_SECRET = "YOUR_BASE64_ENCODED_SECRET"

# Prepare payload
payload = {
    "ticket_id": "T-12345",
    "priority": "high",
    "description": "Customer cannot access portal"
}

# Convert payload to JSON string
payload_json = json.dumps(payload)

# Compute HMAC-SHA256 signature (constant-time comparison on server)
signature = hmac.new(
    HMAC_SECRET.encode('utf-8'),
    payload_json.encode('utf-8'),
    hashlib.sha256
).hexdigest()

# Send webhook request
headers = {
    "Content-Type": "application/json",
    "X-Hub-Signature-256": f"sha256={signature}"
}

response = requests.post(
    WEBHOOK_URL,
    data=payload_json,
    headers=headers,
    timeout=30  # 30-second timeout
)

# Handle response
if response.status_code == 202:
    data = response.json()
    print(f"✅ Webhook accepted! Execution ID: {data['execution_id']}")
elif response.status_code == 400:
    print(f"❌ Payload validation failed: {response.json()['detail']}")
elif response.status_code == 401:
    print(f"❌ Invalid HMAC signature: {response.json()['detail']}")
elif response.status_code == 403:
    print(f"⚠️ Agent is not active: {response.json()['detail']}")
else:
    print(f"⚠️ Unexpected response ({response.status_code}): {response.text}")
```

---

### JavaScript Example (Node.js)

```javascript
const crypto = require('crypto');
const https = require('https');

// Configuration
const WEBHOOK_URL = 'http://localhost:8000/webhook/agents/YOUR_AGENT_ID/webhook';
const HMAC_SECRET = 'YOUR_BASE64_ENCODED_SECRET';

// Prepare payload
const payload = {
  ticket_id: 'T-12345',
  priority: 'high',
  description: 'Customer cannot access portal'
};

const payloadJson = JSON.stringify(payload);

// Compute HMAC-SHA256 signature
const signature = crypto
  .createHmac('sha256', HMAC_SECRET)
  .update(payloadJson)
  .digest('hex');

// Send webhook request
const options = {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-Hub-Signature-256': `sha256=${signature}`,
    'Content-Length': Buffer.byteLength(payloadJson)
  }
};

const req = https.request(WEBHOOK_URL, options, (res) => {
  let body = '';
  res.on('data', (chunk) => { body += chunk; });
  res.on('end', () => {
    const data = JSON.parse(body);

    if (res.statusCode === 202) {
      console.log(`✅ Webhook accepted! Execution ID: ${data.execution_id}`);
    } else if (res.statusCode === 400) {
      console.log(`❌ Payload validation failed: ${data.detail}`);
    } else if (res.statusCode === 401) {
      console.log(`❌ Invalid HMAC signature: ${data.detail}`);
    } else if (res.statusCode === 403) {
      console.log(`⚠️ Agent is not active: ${data.detail}`);
    } else {
      console.log(`⚠️ Unexpected response (${res.statusCode}): ${body}`);
    }
  });
});

req.on('error', (error) => {
  console.error('❌ Network error:', error);
});

req.write(payloadJson);
req.end();
```

---

## Payload Schema Validation

Define JSON Schema (Draft 2020-12) to validate incoming webhook payloads. This ensures type safety and catches errors early.

### Example: ServiceDesk Plus Schema

```json
{
  "type": "object",
  "properties": {
    "ticket_id": {
      "type": "string",
      "description": "Ticket ID from ServiceDesk Plus"
    },
    "subject": {
      "type": "string",
      "description": "Ticket subject/title"
    },
    "priority": {
      "type": "string",
      "enum": ["low", "medium", "high", "urgent"]
    },
    "status": {
      "type": "string",
      "enum": ["open", "pending", "resolved", "closed"]
    },
    "description": {
      "type": "string",
      "description": "Ticket description/body"
    }
  },
  "required": ["ticket_id", "subject"]
}
```

### Schema Validation Errors

If payload doesn't match schema, you'll receive **400 Bad Request**:

```json
{
  "detail": "Payload validation failed: 'ticket_id' is a required property"
}
```

---

## Security Best Practices

### 1. HMAC Signature Validation

**ALWAYS** compute and include the `X-Hub-Signature-256` header. The server uses **constant-time comparison** (`hmac.compare_digest()`) to prevent timing attacks.

**Header Format:**
```
X-Hub-Signature-256: sha256=<hex_digest>
```

**Signature Computation Steps:**
1. Convert payload to JSON string (exact format matters!)
2. Compute HMAC-SHA256 using your secret key
3. Convert to hexadecimal digest
4. Prepend `sha256=` to the digest

### 2. Secret Management

- **DO NOT** commit HMAC secrets to version control
- **DO** store secrets in environment variables or secure vaults (AWS Secrets Manager, HashiCorp Vault)
- **DO** rotate secrets regularly (use "Regenerate Secret" button)
- **DO** use different secrets for dev/staging/production environments

### 3. HTTPS in Production

- **ALWAYS** use HTTPS for webhook URLs in production
- **NEVER** send HMAC secrets over unencrypted HTTP
- Webhook URLs should start with `https://` (not `http://`)

### 4. Timestamp Validation (Future)

> ⚠️ **Note:** Timestamp validation for replay attack prevention is planned for future release.

To prevent replay attacks, include a timestamp in your payload and reject requests older than 5 minutes.

### 5. Rate Limiting (Future)

> ⚠️ **Note:** Rate limiting (100 req/min per agent) is planned for future release.

Avoid sending excessive webhook requests. Current limit: No enforcement (best-effort processing).

---

## Response Codes

| Status Code | Meaning | Action Required |
|-------------|---------|-----------------|
| **202 Accepted** | Webhook accepted, agent execution queued | Track execution using `execution_id` |
| **400 Bad Request** | Payload validation failed | Fix payload to match schema |
| **401 Unauthorized** | Invalid HMAC signature | Verify secret and signature computation |
| **403 Forbidden** | Agent not active or tenant mismatch | Activate agent or check tenant configuration |
| **404 Not Found** | Agent does not exist | Verify `agent_id` in webhook URL |
| **429 Too Many Requests** | Rate limit exceeded (future) | Reduce request frequency |
| **500 Internal Server Error** | Server error | Contact support or check logs |

---

## Troubleshooting

### Problem: 401 Unauthorized (Invalid HMAC Signature)

**Causes:**
1. Incorrect HMAC secret
2. Payload modified after signature computation
3. Character encoding mismatch (UTF-8 required)
4. Whitespace differences in JSON payload

**Solutions:**
- Re-copy HMAC secret from Admin UI (click "Show Secret")
- Ensure payload JSON is **identical** to what you signed
- Use UTF-8 encoding for all strings
- Use `json.dumps()` (Python) or `JSON.stringify()` (JavaScript) for consistent formatting

**Debug Steps:**
```python
# Print exact payload being sent
print(f"Payload: {payload_json}")

# Print signature
print(f"Signature: {signature}")

# Verify secret format (should be base64)
import base64
try:
    decoded = base64.b64decode(HMAC_SECRET)
    print(f"Secret length: {len(decoded)} bytes")  # Should be 32 bytes
except Exception as e:
    print(f"Secret is not valid base64: {e}")
```

---

### Problem: 400 Bad Request (Payload Validation Failed)

**Causes:**
1. Missing required fields in payload
2. Incorrect field types (string vs number)
3. Invalid enum values
4. Nested object structure mismatch

**Solutions:**
- Review payload schema in Agent Management UI
- Validate payload against JSON Schema before sending
- Use example payloads from schema dropdown

**Example Error:**
```json
{
  "detail": "Payload validation failed: 'ticket_id' is a required property"
}
```

**Fix:**
```python
# Before (missing required field)
payload = {"priority": "high"}  # ❌ Missing ticket_id

# After (includes required field)
payload = {"ticket_id": "T-12345", "priority": "high"}  # ✅ Valid
```

---

### Problem: 403 Forbidden (Agent Not Active)

**Cause:** Agent status is "draft", "suspended", or "inactive"

**Solution:**
1. Go to Agent Management UI
2. Find the agent
3. Click "Activate" or change status to "active"
4. Retry webhook request

---

### Problem: Network Timeout

**Causes:**
1. Agent execution taking longer than webhook timeout (30 seconds)
2. Network connectivity issues
3. Server overload

**Solutions:**
- Increase client timeout to 60 seconds
- Check agent execution history for long-running tasks
- Monitor server logs for performance issues

---

## Testing Webhooks

### Using Built-In Test UI

1. Go to Agent Management UI
2. Open agent details
3. Expand "🧪 Test Webhook" section
4. Enter test payload (JSON)
5. Click "🚀 Send Test Webhook"
6. View results (202 Accepted, 400 Validation Error, etc.)

**Advantages:**
- Auto-computes HMAC signature
- No need to manage secrets manually
- Instant feedback with detailed error messages

### Using External Tools

**Postman:**
1. Create new POST request
2. URL: `http://localhost:8000/webhook/agents/{agent_id}/webhook`
3. Headers:
   - `Content-Type: application/json`
   - `X-Hub-Signature-256: sha256=<computed_signature>`
4. Body: Raw JSON payload
5. Send request

**curl (see Quick Start above)**

---

## Integration Examples

### ServiceDesk Plus Webhook

Configure ServiceDesk Plus to call your webhook when tickets are created/updated:

1. Go to ServiceDesk Plus **Admin** → **Automation** → **Custom Triggers**
2. Create new trigger: "On Ticket Create"
3. Action: "Execute Custom API"
4. Method: POST
5. URL: `http://your-server:8000/webhook/agents/{agent_id}/webhook`
6. Headers: `X-Hub-Signature-256: sha256=<signature>` (computed server-side)
7. Body Template:
```json
{
  "ticket_id": "${ticketId}",
  "subject": "${subject}",
  "description": "${description}",
  "priority": "${priority}",
  "status": "${status}"
}
```

**Note:** ServiceDesk Plus may not support HMAC signature computation in trigger templates. Consider using a middleware proxy to add signatures.

---

### Jira Service Management Webhook

Configure Jira to call your webhook on issue events:

1. Go to Jira **Settings** → **System** → **WebHooks**
2. Click "Create a WebHook"
3. Name: "AI Agent Trigger"
4. Status: Enabled
5. URL: `http://your-server:8000/webhook/agents/{agent_id}/webhook`
6. Events: Issue created, Issue updated
7. JQL Filter: `project = SUPPORT AND status = Open` (optional)
8. Custom Headers: `X-Hub-Signature-256: sha256=<signature>`

**Jira Body Template** (automatically includes):
```json
{
  "issue_key": "${issue.key}",
  "summary": "${issue.summary}",
  "description": "${issue.description}",
  "issue_type": "${issue.issueType.name}",
  "priority": "${issue.priority.name}"
}
```

**Note:** Jira webhooks require middleware for HMAC signature computation.

---

## Advanced Topics

### Multi-Tenancy

All webhook requests are scoped to tenants. Include `X-Tenant-ID` header for tenant isolation:

```bash
curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: tenant-001" \
  -H "X-Hub-Signature-256: sha256=$SIGNATURE" \
  -d "$PAYLOAD"
```

Cross-tenant webhook requests are **rejected with 403 Forbidden**.

---

### Execution Tracking

Use the `execution_id` returned in the 202 response to track agent execution:

**Response:**
```json
{
  "status": "queued",
  "execution_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Track Execution:** (Future feature)
```
GET /api/executions/{execution_id}
```

**Expected Response:**
```json
{
  "execution_id": "a1b2c3d4-...",
  "agent_id": "123e4567-...",
  "status": "completed",
  "result": {
    "enhanced_description": "...",
    "suggested_actions": [...]
  },
  "created_at": "2025-11-06T10:30:00Z",
  "completed_at": "2025-11-06T10:30:15Z"
}
```

---

## API Reference

### POST /webhook/agents/{agent_id}/webhook

Trigger agent execution via webhook.

**Path Parameters:**
- `agent_id` (UUID, required): Agent identifier

**Headers:**
- `Content-Type: application/json` (required)
- `X-Hub-Signature-256: sha256=<hexdigest>` (required): HMAC-SHA256 signature
- `X-Tenant-ID: <tenant_id>` (optional): Tenant identifier for multi-tenancy

**Request Body:**
- JSON payload (validated against `payload_schema` if defined)

**Success Response (202 Accepted):**
```json
{
  "status": "queued",
  "execution_id": "uuid",
  "message": "Agent execution queued"
}
```

**Error Responses:**
- `400 Bad Request`: Payload validation failed
- `401 Unauthorized`: Invalid HMAC signature
- `403 Forbidden`: Agent not active or cross-tenant access denied
- `404 Not Found`: Agent does not exist
- `500 Internal Server Error`: Server error during task enqueueing

---

### GET /api/agents/{agent_id}/webhook-secret

Fetch unmasked HMAC secret for agent. **Use with caution - secret is sensitive!**

**Path Parameters:**
- `agent_id` (UUID, required): Agent identifier

**Headers:**
- `X-Tenant-ID: <tenant_id>` (required): Tenant identifier

**Success Response (200 OK):**
```json
{
  "hmac_secret": "base64encodedstring..."
}
```

**Error Responses:**
- `403 Forbidden`: Cross-tenant access denied
- `404 Not Found`: Agent does not exist

---

### POST /api/agents/{agent_id}/regenerate-webhook-secret

Generate new HMAC secret and invalidate old webhooks.

**Path Parameters:**
- `agent_id` (UUID, required): Agent identifier

**Headers:**
- `X-Tenant-ID: <tenant_id>` (required): Tenant identifier

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "HMAC secret regenerated",
  "new_secret_masked": "Abc123...Xyz789"
}
```

**Error Responses:**
- `403 Forbidden`: Cross-tenant access denied
- `404 Not Found`: Agent does not exist

---

## Support & Feedback

**Issues:** Report bugs at `https://github.com/your-org/ai-agents/issues`
**Documentation:** Full API docs at `http://localhost:8000/docs` (FastAPI Swagger UI)
**Community:** Join our Discord/Slack for questions and discussions

---

## Changelog

**2025-11-06 (Story 8.6):**
- Initial release of webhook integration
- HMAC-SHA256 signature validation (constant-time comparison)
- Payload schema validation (JSON Schema Draft 2020-12)
- Test webhook UI in Admin interface
- Secret regeneration functionality
- Comprehensive code examples (Python, JavaScript, cURL)

**Future Enhancements:**
- Timestamp validation for replay attack prevention
- Rate limiting (100 req/min per agent)
- Execution history tracking UI
- Webhook retry mechanism with exponential backoff
- Custom HTTP headers support
