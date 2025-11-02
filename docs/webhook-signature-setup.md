# Webhook Signature Validation Setup

This guide explains how to configure and use HMAC-SHA256 signature validation for ServiceDesk Plus webhooks.

## Overview

The AI Agents application validates all incoming webhook requests using HMAC-SHA256 signatures to ensure requests are authentic and originated from ServiceDesk Plus. This prevents unauthorized parties from triggering enhancement jobs by spoofing webhook requests.

## Security Architecture

- **Algorithm:** HMAC-SHA256 (Hash-based Message Authentication Code with SHA-256)
- **Header:** `X-ServiceDesk-Signature`
- **Secret:** Shared secret key stored in environment variable `AI_AGENTS_WEBHOOK_SECRET`
- **Validation:** Computed HMAC of request body + secret compared with header value using constant-time comparison
- **Response:** Invalid signatures are rejected with `401 Unauthorized`

## Configuration

### 1. Generate a Strong Secret

Generate a strong random secret (minimum 32 characters) using OpenSSL:

```bash
openssl rand -hex 32
```

Example output:
```
a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
```

### 2. Configure the Secret

**Development (Local):**

Add to your `.env` file:
```bash
AI_AGENTS_WEBHOOK_SECRET=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
```

**Production (Kubernetes):**

Create a Kubernetes secret:
```bash
kubectl create secret generic ai-agents-secrets \
  --from-literal=webhook-secret='a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2' \
  -n ai-agents
```

Reference in deployment manifest (already configured in `k8s/deployment-api.yaml`):
```yaml
env:
  - name: AI_AGENTS_WEBHOOK_SECRET
    valueFrom:
      secretKeyRef:
        name: ai-agents-secrets
        key: webhook-secret
```

### 3. Configure ServiceDesk Plus

In your ServiceDesk Plus webhook configuration:

1. Set the webhook URL: `https://your-domain.com/webhook/servicedesk`
2. Configure the shared secret (same value as `AI_AGENTS_WEBHOOK_SECRET`)
3. ServiceDesk Plus will automatically compute and include the signature in the `X-ServiceDesk-Signature` header

**Note:** If ServiceDesk Plus doesn't support automatic signature generation, you'll need to implement a custom integration using the signature generation examples below.

## Testing

### Python Example

Generate a signature for a test payload:

```python
import hmac
import hashlib
import json

# Your webhook payload
payload = {
    "event": "ticket_created",
    "ticket_id": "TKT-001",
    "tenant_id": "tenant-abc",
    "description": "Server is slow and unresponsive",
    "priority": "high",
    "created_at": "2025-11-01T12:00:00Z"
}

# Your shared secret
secret = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2"

# Convert payload to JSON string (no spaces after separators)
payload_string = json.dumps(payload, separators=(',', ':'))

# Compute HMAC-SHA256 signature
signature = hmac.new(
    key=secret.encode('utf-8'),
    msg=payload_string.encode('utf-8'),
    digestmod=hashlib.sha256
).hexdigest()

print(f"Signature: {signature}")
```

### cURL Example

Send a test webhook request:

```bash
#!/bin/bash

# Configuration
URL="http://localhost:8000/webhook/servicedesk"
SECRET="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2"

# Payload (JSON)
PAYLOAD='{"event":"ticket_created","ticket_id":"TKT-001","tenant_id":"tenant-abc","description":"Server is slow and unresponsive","priority":"high","created_at":"2025-11-01T12:00:00Z"}'

# Compute signature
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | sed 's/^.* //')

# Send request
curl -X POST "$URL" \
  -H "Content-Type: application/json" \
  -H "X-ServiceDesk-Signature: $SIGNATURE" \
  -d "$PAYLOAD"
```

Expected response (202 Accepted):
```json
{
  "status": "accepted",
  "job_id": "job-550e8400-e29b-41d4-a716-446655440000",
  "message": "Enhancement job queued successfully"
}
```

## Error Responses

### Missing Signature Header

**Request:**
```bash
curl -X POST http://localhost:8000/webhook/servicedesk \
  -H "Content-Type: application/json" \
  -d '{"event":"ticket_created","ticket_id":"TKT-001",...}'
```

**Response (401 Unauthorized):**
```json
{
  "detail": "Missing signature header"
}
```

### Invalid Signature

**Request:**
```bash
curl -X POST http://localhost:8000/webhook/servicedesk \
  -H "Content-Type: application/json" \
  -H "X-ServiceDesk-Signature: invalid-signature" \
  -d '{"event":"ticket_created","ticket_id":"TKT-001",...}'
```

**Response (401 Unauthorized):**
```json
{
  "detail": "Invalid webhook signature"
}
```

## Troubleshooting

### Common Issues

1. **Whitespace differences:**
   - Ensure JSON payload has no extra whitespace
   - Use `json.dumps(payload, separators=(',', ':'))` in Python
   - Signature must be computed on the exact bytes sent in the request body

2. **Encoding issues:**
   - Always use UTF-8 encoding
   - Secret and payload must be encoded as UTF-8 before HMAC computation

3. **Wrong secret:**
   - Verify `AI_AGENTS_WEBHOOK_SECRET` matches the secret configured in ServiceDesk Plus
   - Check for typos or extra spaces in environment variables

4. **Signature format:**
   - Signature must be lowercase hexadecimal string
   - Example: `a1b2c3d4...` (64 characters for SHA-256)

### Debugging

Check application logs for failed validation attempts:

```bash
# Local development
tail -f logs/app.log | grep "Webhook signature validation failed"

# Kubernetes
kubectl logs -f deployment/ai-agents-api -n ai-agents | grep "Webhook signature validation failed"
```

Log entries include:
- Reason for failure (missing_header or invalid_signature)
- Source IP address
- Request body length

## Security Best Practices

1. **Secret Strength:**
   - Use strong random secrets (minimum 32 characters)
   - Generate with cryptographically secure random number generator
   - Never commit secrets to version control

2. **Secret Rotation:**
   - Rotate secrets periodically (recommended: every 90 days)
   - Update both application and ServiceDesk Plus configuration
   - Consider implementing gradual rollover for zero-downtime rotation

3. **Secret Storage:**
   - Store in environment variables or Kubernetes Secrets
   - Never hardcode in application code
   - Restrict access to secrets in production

4. **Monitoring:**
   - Monitor failed validation attempts for suspicious activity
   - Alert on high rates of 401 responses from webhook endpoint
   - Review source IPs for unexpected patterns

## Implementation Details

For developers working on the codebase:

- **Validation Module:** `src/services/webhook_validator.py`
- **FastAPI Dependency:** `validate_webhook_signature()` in webhook_validator.py
- **Endpoint:** `POST /webhook/servicedesk` in `src/api/webhooks.py`
- **Configuration:** `Settings.webhook_secret` in `src/config.py`
- **Tests:** `tests/unit/test_webhook_validator.py` and `tests/unit/test_webhook_endpoint.py`

Signature validation runs BEFORE Pydantic validation to ensure data integrity:
- Invalid signature → 401 Unauthorized
- Invalid payload → 422 Unprocessable Entity

The implementation uses constant-time comparison (`hmac.compare_digest()`) to prevent timing attacks.
