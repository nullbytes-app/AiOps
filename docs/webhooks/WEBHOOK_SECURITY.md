# Webhook Security Configuration and Operations Guide

## Overview

This document describes the webhook signature validation and security features implemented in the AI Agents application. It covers multi-tenant webhook authentication, replay attack prevention, and rate limiting.

## Architecture

The webhook security system uses a **defense-in-depth** approach with 6 layers of protection:

```
┌──────────────────────────────────────────┐
│ 1. Rate Limiting (Redis sliding window)  │
├──────────────────────────────────────────┤
│ 2. Tenant ID Validation & Extraction     │
├──────────────────────────────────────────┤
│ 3. Timestamp Validation (Replay prevent) │
├──────────────────────────────────────────┤
│ 4. HMAC-SHA256 Signature Validation      │
├──────────────────────────────────────────┤
│ 5. Pydantic Input Validation             │
├──────────────────────────────────────────┤
│ 6. Database Row-Level Security (RLS)     │
└──────────────────────────────────────────┘
```

## Component: Signature Validation

### HMAC-SHA256 Signature Computation

**Function:** `compute_hmac_signature(secret: str, payload_bytes: bytes) -> str`

Computes the HMAC-SHA256 signature of a webhook payload using the tenant's webhook signing secret.

**Implementation Details:**
- **Algorithm:** HMAC-SHA256 (cryptographically secure)
- **Output Format:** 64-character hexadecimal string
- **Secret Encoding:** UTF-8
- **Payload:** Raw request body as bytes (JSON)

**Example:**
```python
from src.services.webhook_validator import compute_hmac_signature

secret = "your-webhook-secret-key"
payload = b'{"tenant_id":"acme-corp","event":"ticket_created"}'
signature = compute_hmac_signature(secret, payload)
# Returns: "abc123def456..." (64 hex chars)
```

### Constant-Time Signature Comparison

**Function:** `secure_compare(sig1: str, sig2: str) -> bool`

Compares two signatures using constant-time comparison to prevent timing attacks.

**Security Note:**
- Uses Python's `hmac.compare_digest()` for timing-safe comparison
- Prevents attackers from inferring correct signature bytes through timing analysis
- Always takes same time regardless of how many characters match

**Example:**
```python
from src.services.webhook_validator import secure_compare

expected_sig = compute_hmac_signature(secret, payload)
provided_sig = request.headers.get("X-ServiceDesk-Signature")
if secure_compare(expected_sig, provided_sig):
    # Signature is valid
else:
    # Signature is invalid
```

## Component: Tenant Identification

### Tenant ID Extraction and Validation

**Function:** `extract_tenant_id_from_payload(body: bytes) -> str`

Extracts and validates the tenant identifier from the webhook payload before signature validation.

**Validation Rules:**
- **Pattern:** `^[a-z0-9-]+$` (lowercase alphanumeric + dashes)
- **Examples of Valid IDs:**
  - `acme-corp`
  - `customer-123`
  - `prod-us-east-1`
- **Examples of Invalid IDs:**
  - `ACME-CORP` (uppercase not allowed)
  - `acme_corp` (underscores not allowed)
  - `acme corp` (spaces not allowed)

**Error Handling:**
- Raises `ValueError` if `tenant_id` field missing
- Raises `ValueError` if JSON is malformed
- Raises `ValueError` if tenant_id format is invalid

**Example:**
```python
from src.services.webhook_validator import extract_tenant_id_from_payload

body = b'{"tenant_id":"acme-corp","event":"ticket_created"}'
tenant_id = extract_tenant_id_from_payload(body)
# Returns: "acme-corp"
```

## Component: Replay Attack Prevention

### Timestamp Validation

**Function:** `validate_webhook_timestamp(created_at: datetime) -> None`

Validates webhook timestamps to prevent replay attacks. Ensures the webhook was created recently and hasn't been delayed or replayed.

**Validation Checks:**
1. **Timezone Required:** Timestamp must include timezone info (UTC or offset)
2. **Age Check:** Timestamp must be within tolerance window (default: 5 minutes)
3. **Future Check:** Timestamp cannot be in future (prevents clock skew issues, default: 30-second tolerance)

**Configuration (src/config.py):**
```python
# Maximum age of webhook timestamp (5 minutes = 300 seconds)
webhook_timestamp_tolerance_seconds: int = Field(default=300, ge=60, le=3600)

# Maximum future drift for clock skew (30 seconds)
webhook_clock_skew_tolerance_seconds: int = Field(default=30, ge=1, le=300)
```

**Error Handling:**
- Raises `ValueError` if timestamp lacks timezone info
- Raises `ValueError` if timestamp older than tolerance window
- Raises `ValueError` if timestamp is in future beyond clock skew tolerance

**Timestamp Format:**
- Must use ISO 8601 format with timezone: `2025-11-03T08:43:40Z` or `2025-11-03T08:43:40+00:00`
- Invalid: `2025-11-03T08:43:40` (no timezone)

**Example:**
```python
from src.services.webhook_validator import validate_webhook_timestamp
from datetime import datetime, timezone

# Valid - current time with UTC timezone
now = datetime.now(timezone.utc)
validate_webhook_timestamp(now)  # Passes

# Invalid - naive datetime without timezone
naive_time = datetime.now()
validate_webhook_timestamp(naive_time)  # Raises ValueError

# Invalid - too old
old_time = datetime.now(timezone.utc) - timedelta(minutes=10)
validate_webhook_timestamp(old_time)  # Raises ValueError (older than 5 min)
```

## Component: Rate Limiting

### Redis-Based Sliding Window Rate Limiter

**Class:** `RateLimiter` in `src/services/rate_limiter.py`

Implements per-tenant, per-endpoint rate limiting using Redis sorted sets for efficient sliding window tracking.

**Algorithm Details:**
- **Data Structure:** Redis Sorted Sets (ZSET)
- **Key Format:** `webhook_rate_limit:{tenant_id}:{endpoint}`
- **Score:** Unix timestamp of request
- **Value:** Request ID (`{timestamp}_{tenant_id}`)

**Algorithm Steps:**
1. Remove expired entries from sorted set (older than window)
2. Count current requests in window
3. If under limit: add current request to sorted set
4. If at/over limit: calculate `retry_after` from oldest request timestamp

**Configuration:**
```python
# Per tenant, per endpoint
rate_limits = {
    "webhooks": {
        "ticket_created": 100,    # 100 requests per minute
        "ticket_resolved": 100,   # 100 requests per minute
        # Add more endpoints as needed
    }
}
```

**Usage Example:**
```python
from src.services.rate_limiter import RateLimiter
from redis.asyncio import Redis

redis_client = Redis(...)  # Async Redis client
limiter = RateLimiter(redis_client)

# Check if request is within rate limit
allowed, retry_after = await limiter.check_rate_limit(
    tenant_id="acme-corp",
    endpoint="ticket_created",
    limit=100,      # 100 requests
    window=60       # per 60 seconds
)

if not allowed:
    # Return 429 Too Many Requests with Retry-After header
    response.headers["Retry-After"] = str(retry_after)
    raise HTTPException(status_code=429, detail="Rate limit exceeded")

# Reset rate limit (admin operation)
await limiter.reset_limit("acme-corp", "ticket_created")
```

## Component: FastAPI Dependency Integration

### Webhook Signature Validation Dependency

**Function:** `async def validate_webhook_signature(...) -> str`

FastAPI dependency that performs complete webhook validation before the endpoint handler runs.

**Validation Flow:**
```python
@router.post("/webhooks/tickets")
async def handle_webhook(
    tenant_id: str = Depends(validate_webhook_signature),
    payload: WebhookPayload = Body(...),
):
    # tenant_id is already validated and extracted
    # signature, timestamp, and tenant already verified
    ...
```

**Validation Steps (in order):**
1. ✓ Check signature header present (`X-ServiceDesk-Signature`)
2. ✓ Extract and validate tenant_id from payload
3. ✓ Retrieve tenant's webhook signing secret
4. ✓ Compute expected signature from raw payload bytes
5. ✓ Compare provided signature with computed signature (constant-time)
6. ✓ Validate webhook creation timestamp
7. ✓ Check rate limits for tenant/endpoint
8. ✓ Return `tenant_id` if all validations pass

**Error Responses:**
- **401 Unauthorized:** Missing or invalid signature
- **404 Not Found:** Tenant not found in database
- **403 Forbidden:** Tenant is inactive
- **422 Unprocessable Entity:** Invalid payload (missing tenant_id, bad JSON, etc.)
- **429 Too Many Requests:** Rate limit exceeded

**Logging:**
All security events are logged with structured context:
- `event_type`: `signature_mismatch`, `validation_error`, etc.
- `error_type`: `missing_header`, `invalid_signature`, etc.
- `tenant_id`: Extracted tenant identifier
- `source_ip`: Client IP address
- `endpoint`: Webhook endpoint path
- `body_length`: Size of request body (for debugging)

## Database Schema

### TenantConfig Table

The `tenant_configs` table stores per-tenant configuration including webhook secrets:

```sql
CREATE TABLE tenant_configs (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    servicedesk_url VARCHAR(500) NOT NULL,

    -- Encrypted fields (stored in encrypted form, decrypted on retrieval)
    servicedesk_api_key_encrypted TEXT NOT NULL,
    webhook_signing_secret_encrypted TEXT NOT NULL,

    -- JSON configuration
    enhancement_preferences JSONB NOT NULL,
    rate_limits JSONB NOT NULL,

    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

**Rate Limits Format (JSONB):**
```json
{
    "webhooks": {
        "ticket_created": 100,
        "ticket_resolved": 100,
        "ticket_updated": 150
    }
}
```

**Encryption:**
- Webhook signing secrets are encrypted at the application layer
- Uses Fernet symmetric encryption (AES-128 in CBC mode)
- Decryption happens transparently when retrieved via `TenantService.get_webhook_secret()`

## Operational Procedures

### Configuration Setup

1. **Generate Webhook Secret:**
   ```python
   import secrets
   import base64

   # Generate 64-character base64-encoded secret
   secret = base64.urlsafe_b64encode(secrets.token_bytes(48)).decode('utf-8')
   print(secret)  # e.g., "vF3x9K2mN8pL5qR2tU9...=="
   ```

2. **Store in Tenant Configuration:**
   ```python
   # Via admin API or database
   tenant_config = await tenant_service.create_tenant({
       "tenant_id": "acme-corp",
       "name": "ACME Corporation",
       "servicedesk_url": "https://sd.acme.com",
       "webhook_signing_secret": secret,  # Automatically encrypted
       "enhancement_preferences": {...},
       "rate_limits": {
           "webhooks": {
               "ticket_created": 100,
               "ticket_resolved": 100
           }
       }
   })
   ```

3. **Share with Webhook Source:**
   - Securely transmit the webhook signing secret to the ServiceDesk Plus instance
   - Secret should be stored securely on the source side
   - Never log or expose the secret in error messages

### Webhook Secret Rotation

Rotate webhook secrets regularly (recommended: every 90 days) to limit exposure if compromised:

```python
from src.services.tenant_service import TenantService

tenant_service = TenantService(db_session, redis_client, encryption_key)

# Generate new secret and update database
new_secret = await tenant_service.rotate_webhook_secret("acme-corp")

# Share new secret with webhook source
# Old webhooks will fail validation with 401 Unauthorized
# After source is updated, webhooks will succeed again
```

### Monitoring and Alerting

**Key Metrics to Monitor:**

1. **Signature Validation Failures:**
   ```
   Rate Limit Exceeded: {tenant_id}/{endpoint} - {current_count} > {limit}
   Event Type: signature_mismatch
   ```
   - Alert if signature failures spike (indicates attack or misconfiguration)

2. **Timestamp Validation Failures:**
   ```
   Webhook timestamp expired (older than 300 seconds)
   Webhook timestamp in future (clock skew > 30 seconds)
   ```
   - Alert if timestamp validation failures spike (indicates clock sync issues)

3. **Rate Limit Breaches:**
   ```
   Rate limit exceeded: {tenant_id}/{endpoint}
   Retry-After: {seconds}
   ```
   - Monitor per-tenant rate limit usage
   - Alert if consistently hitting limits (may need adjustment)

4. **Tenant Configuration Errors:**
   ```
   Tenant not found: {tenant_id}
   Tenant inactive: {tenant_id}
   Invalid payload: {error_message}
   ```
   - Alert if tenant lookup failures increase

### Troubleshooting

**Problem: "Invalid webhook signature" errors**

1. **Verify secret is correct:**
   ```bash
   # Get stored secret (via database or admin API)
   SELECT webhook_signing_secret_encrypted FROM tenant_configs
   WHERE tenant_id = 'acme-corp';
   ```

2. **Verify JSON is not modified:**
   - Webhook body must be identical to what was signed
   - No whitespace modifications
   - No field reordering
   - Check for Unicode normalization issues

3. **Verify secret encoding:**
   - Secret should be UTF-8 encoded string
   - Payload should be raw bytes (not decoded JSON)

4. **Verify timestamp is recent:**
   - Check if webhook timestamp is within 5 minutes of server time
   - Check server clock synchronization (NTP)

**Problem: "Webhook timestamp expired" errors**

1. **Check source system clock:**
   - Verify source system has correct time (via NTP)
   - Check timezone configuration

2. **Verify tolerance settings:**
   ```python
   from src.config import get_settings
   settings = get_settings()
   print(f"Tolerance: {settings.webhook_timestamp_tolerance_seconds}s")
   print(f"Clock skew: {settings.webhook_clock_skew_tolerance_seconds}s")
   ```

3. **Consider adjusting tolerance** (if appropriate):
   - Edit `src/config.py` to adjust `webhook_timestamp_tolerance_seconds`
   - Values: 60-3600 seconds (1 minute to 1 hour)
   - Higher values = more permissive but less secure

**Problem: "Rate limit exceeded" errors**

1. **Check current rate limits:**
   ```python
   rate_limits = await tenant_service.get_rate_limits("acme-corp")
   print(rate_limits)  # {'webhooks': {'ticket_created': 100, ...}}
   ```

2. **Adjust rate limits if needed:**
   ```python
   await tenant_service.update_tenant(
       "acme-corp",
       rate_limits={
           "webhooks": {
               "ticket_created": 200,  # Increased from 100
               "ticket_resolved": 200
           }
       }
   )
   ```

3. **Reset rate limit counter:**
   ```python
   limiter = RateLimiter(redis_client)
   await limiter.reset_limit("acme-corp", "ticket_created")
   ```

## Security Best Practices

### For Application Operators

1. **Secret Management:**
   - Store webhook secrets in secure vault (Kubernetes Secrets, AWS Secrets Manager)
   - Rotate secrets every 90 days
   - Never log secrets in error messages or debug output
   - Never include secrets in configuration files checked into version control

2. **Network Security:**
   - Require HTTPS/TLS for all webhook endpoints
   - Validate SSL certificates on webhook source
   - Use firewall rules to restrict webhook source IPs (if possible)

3. **Monitoring:**
   - Monitor signature validation failures
   - Monitor rate limit usage per tenant
   - Set up alerts for anomalous webhook patterns
   - Log all validation failures with context for debugging

4. **Clock Synchronization:**
   - Ensure all servers have accurate time (use NTP)
   - Monitor clock skew between systems
   - Alert if clock sync issues detected

### For Webhook Source Integration

1. **Signature Computation:**
   - Use HMAC-SHA256 algorithm only
   - Sign raw request body as bytes (before any JSON parsing)
   - Include signature in `X-ServiceDesk-Signature` header
   - Compute fresh signature for each request

2. **Timestamp Handling:**
   - Include `created_at` field in webhook payload
   - Use current UTC time in ISO 8601 format: `2025-11-03T08:43:40Z`
   - Ensure source system clock is synchronized

3. **Error Handling:**
   - Handle 401, 403, 404 errors (authentication/authorization)
   - Handle 422 errors (validation errors - fix webhook format)
   - Handle 429 errors (rate limited - back off and retry)
   - Implement exponential backoff for retries

4. **Testing:**
   - Test webhook signature generation with known examples
   - Test with different timestamps (recent, expired, future)
   - Test with invalid tenant IDs
   - Test rate limiting by sending many requests quickly

## Related Documentation

- **Database Models:** See `src/database/models.py` for TenantConfig schema
- **Configuration:** See `src/config.py` for Settings with webhook tolerance fields
- **Tenant Service:** See `src/services/tenant_service.py` for webhook secret management
- **Test Suite:** See `tests/integration/test_webhook_security.py` for comprehensive test examples
- **API Schema:** See `src/schemas/webhook.py` for webhook payload validation

## Version History

| Date | Changes | Author |
|------|---------|--------|
| 2025-11-03 | Initial webhook security documentation | AI Ops Team |

