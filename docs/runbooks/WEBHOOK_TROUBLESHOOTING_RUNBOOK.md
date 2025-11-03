# Webhook Troubleshooting Runbook

**Quick Reference**
- **Components:** Signature Validation (HMAC-SHA256), Timestamp Validation, Rate Limiting
- **Key Files:** `src/services/webhook_validator.py`, `src/services/rate_limiter.py`
- **Logs:** Check structured log output with `event_type` and `error_type` fields
- **Test Suite:** `tests/integration/test_webhook_security.py` (26 tests)

---

## Issue: 401 Unauthorized - "Invalid webhook signature"

### Symptoms
- Webhook requests returning `401 Unauthorized`
- Log message: `Webhook signature validation failed: Invalid signature`
- Customer reports: "Our webhooks are being rejected"

### Root Causes & Solutions

#### 1. Webhook Secret Mismatch

**Check:** The secret stored in database doesn't match the secret used by webhook source.

**Diagnosis:**
```bash
# 1. Get stored secret from database (encrypted)
psql $DATABASE_URL -c \
  "SELECT tenant_id, webhook_signing_secret_encrypted FROM tenant_configs
   WHERE tenant_id = 'acme-corp';"

# 2. Verify with customer:
# "Is this the secret we gave you?"
# (Only customer can decrypt their copy)
```

**Solution:**
```bash
# Step 1: Generate NEW secret
python -c "import secrets, base64; \
  print(base64.urlsafe_b64encode(secrets.token_bytes(48)).decode('utf-8'))"

# Step 2: Update tenant configuration
curl -X PATCH https://api.example.com/admin/tenants/acme-corp \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "webhook_signing_secret": "NEW_SECRET_FROM_STEP_1"
  }'

# Step 3: Share new secret with webhook source
# "Please update your ServiceDesk Plus webhook signing key to: NEW_SECRET"

# Step 4: Test webhook
curl -X POST https://api.example.com/webhooks/tickets \
  -H "X-ServiceDesk-Signature: $(python compute_sig.py)" \
  -d '{...webhook_payload...}'
```

#### 2. Payload Tampering or Format Change

**Check:** Webhook body is modified or formatted differently than when signed.

**Diagnosis:**
```bash
# Enable debug logging to see payload comparison
export LOG_LEVEL=DEBUG
# Capture webhook body and signature
# Manually compute signature and compare

python3 << 'EOF'
import hmac, hashlib, json

# From webhook request
provided_signature = "abc123def456..."
webhook_body = b'{"tenant_id":"acme-corp","event":"ticket_created"}'
secret = "webhook-secret-key"

# Compute expected signature
computed_sig = hmac.new(
    key=secret.encode('utf-8'),
    msg=webhook_body,
    digestmod=hashlib.sha256
).hexdigest()

print(f"Provided:  {provided_signature}")
print(f"Computed:  {computed_sig}")
print(f"Match: {computed_sig == provided_signature}")
EOF
```

**Common Issues:**
- JSON field reordering (after parsing and re-serializing)
- Whitespace normalization (extra spaces, tabs)
- Unicode normalization (ñ vs n-combining-tilde)
- Content-Type header changes affecting body encoding

**Solution:**
- **For customers:** "Sign the raw JSON body, do not modify or reformat"
- **Verify:** Check if source system parses and re-serializes JSON
- **Fix:** Source system must sign raw bytes received from database, not reparsed JSON

#### 3. Secret Character Encoding Issues

**Check:** Secret contains non-ASCII characters or encoding issues.

**Diagnosis:**
```bash
# Check secret in database (after decryption)
python3 << 'EOF'
from src.services.tenant_service import TenantService
from src.utils.encryption import decrypt

# Get encrypted secret from database
encrypted_secret = "eyJhbGciOiJIUzI1NiIs..."

# Decrypt and check
decrypted = decrypt(encrypted_secret, encryption_key)
print(f"Length: {len(decrypted)}")
print(f"Repr: {repr(decrypted)}")
print(f"Hex: {decrypted.encode('utf-8').hex()}")
EOF
```

**Solution:**
- Regenerate secret using proper base64 encoding:
  ```bash
  python -c "import secrets, base64; \
    print(base64.urlsafe_b64encode(secrets.token_bytes(48)).decode('utf-8'))"
  ```
- Share as plain ASCII string (no special characters)

---

## Issue: 422 Unprocessable Entity - "tenant_id field is required"

### Symptoms
- Webhook requests returning `422 Unprocessable Entity`
- Log message: `Webhook validation failed: tenant_id field is required`

### Root Causes & Solutions

#### 1. Missing tenant_id in Payload

**Check:** Webhook payload doesn't include `tenant_id` field.

**Diagnosis:**
```bash
# Check webhook payload format
curl -X POST https://api.example.com/webhooks/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "event": "ticket_created",
    "ticket_id": "TKT-001"
    # MISSING: "tenant_id": "acme-corp"
  }'
```

**Solution:**
```bash
# Verify tenant_id is included in payload
curl -X POST https://api.example.com/webhooks/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "acme-corp",   # <-- ADD THIS
    "event": "ticket_created",
    "ticket_id": "TKT-001"
  }'
```

#### 2. Invalid tenant_id Format

**Check:** tenant_id doesn't match pattern `^[a-z0-9-]+$`

**Diagnosis:**
```bash
# Check webhook payload - invalid formats:
# ❌ "ACME-CORP"     (uppercase)
# ❌ "acme_corp"     (underscore)
# ❌ "acme corp"     (space)
# ✓ "acme-corp"     (valid)
# ✓ "customer-123"  (valid)
```

**Solution:**
- Use lowercase alphanumeric + dashes only
- Fix source system to generate valid tenant_id
- Verify tenant_id matches one in database:
  ```sql
  SELECT tenant_id FROM tenant_configs;
  ```

#### 3. Malformed JSON

**Check:** Webhook payload is not valid JSON.

**Diagnosis:**
```bash
# Test JSON validity
echo '{"tenant_id":"acme-corp"' | python -m json.tool
# Error: JSONDecodeError: Expecting '}' delimiter

# Check for common issues:
# - Missing closing brace }
# - Unquoted strings
# - Trailing commas
# - Newlines in strings without \n escape
```

**Solution:**
- Validate JSON before sending webhook
- Use `jsonlint` or similar tool to check format
- Check for special characters that need escaping

---

## Issue: 422 Unprocessable Entity - "invalid format"

### Symptoms
- Log message: `tenant_id format invalid: ACME-CORP. Must match pattern: ^[a-z0-9-]+$`

### Root Causes & Solutions

#### 1. Uppercase in tenant_id

**Check:** tenant_id contains uppercase letters.

**Examples:**
```bash
# ❌ Invalid
"tenant_id": "ACME-CORP"
"tenant_id": "Acme-Corp"
"tenant_id": "Customer_123"  # Also has underscore

# ✓ Valid
"tenant_id": "acme-corp"
"tenant_id": "customer-123"
"tenant_id": "prod-us-east-1"
```

**Solution:**
- Convert tenant_id to lowercase
- Replace underscores with dashes
- Remove spaces
- Example: `"ACME_CORP "` → `"acme-corp"`

---

## Issue: 401 Unauthorized - "Missing X-ServiceDesk-Signature header"

### Symptoms
- Log message: `Missing X-ServiceDesk-Signature header`
- Webhook requests failing immediately

### Root Causes & Solutions

#### 1. Header Not Included in Request

**Check:** Webhook request doesn't include signature header.

**Diagnosis:**
```bash
# Check request headers
curl -v -X POST https://api.example.com/webhooks/tickets \
  -H "Content-Type: application/json" \
  -d '{...}'

# Expected header in output:
# X-ServiceDesk-Signature: abc123def456...
```

**Solution:**
```bash
# Add signature header to webhook request
curl -X POST https://api.example.com/webhooks/tickets \
  -H "Content-Type: application/json" \
  -H "X-ServiceDesk-Signature: $(compute_signature)" \
  -d '{...webhook_payload...}'
```

#### 2. Header Name Mismatch

**Check:** Header is named differently than `X-ServiceDesk-Signature`.

**Examples:**
```bash
# ❌ Wrong header names
"X-Signature: ..."
"Signature: ..."
"Authorization: Bearer ..."

# ✓ Correct header name
"X-ServiceDesk-Signature: ..."
```

**Solution:**
- Update webhook source to use exact header name: `X-ServiceDesk-Signature`
- Note: Header names are case-insensitive in HTTP, but use exact name for clarity

---

## Issue: 400 Bad Request - "Webhook timestamp expired"

### Symptoms
- Webhook requests returning `400 Bad Request` or `422 Unprocessable Entity`
- Log message: `Webhook timestamp expired (older than 300 seconds)`

### Root Causes & Solutions

#### 1. Source System Clock is Behind

**Check:** ServiceDesk Plus server clock is not synchronized with API server.

**Diagnosis:**
```bash
# Check current time on source system
# Get webhook timestamp and compare with current time

# API Server time
date -u "+%Y-%m-%dT%H:%M:%SZ"

# Calculate age of webhook timestamp
# If webhook timestamp is >5 minutes old, it's rejected
```

**Solution:**
```bash
# 1. Check NTP status on source system
ntpstat
# Should show "synchronized" or similar

# 2. Sync time
sudo systemctl restart ntpd
# or
sudo ntpdate -s time.nist.gov

# 3. Verify time sync
date -u "+%Y-%m-%dT%H:%M:%SZ"
```

#### 2. Clock Skew Too Large

**Check:** Time difference between systems exceeds tolerance (30 seconds).

**Diagnosis:**
```bash
# On source system
SOURCE_TIME=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
echo "Source: $SOURCE_TIME"

# On API server (via test request)
# Compare timestamps - difference should be <30 seconds
```

**Solution:**
- Increase clock skew tolerance (if appropriate):
  ```python
  # In src/config.py
  webhook_clock_skew_tolerance_seconds: int = Field(default=30, ge=1, le=300)
  # Change to: default=60 (60 seconds tolerance)
  ```
- Or fix source system clock (preferred solution)

#### 3. Timestamp Format Invalid

**Check:** Webhook payload has malformed timestamp.

**Examples:**
```bash
# ❌ Invalid formats
"created_at": "2025-11-03 08:43:40"     # Missing Z or timezone
"created_at": "2025-11-03T08:43:40"     # Missing timezone
"created_at": "11/03/2025 08:43:40"     # Wrong date format

# ✓ Valid formats
"created_at": "2025-11-03T08:43:40Z"           # UTC with Z
"created_at": "2025-11-03T08:43:40+00:00"     # UTC with offset
"created_at": "2025-11-03T08:43:40-05:00"     # US Eastern offset
```

**Solution:**
- Update webhook payload to use ISO 8601 format with timezone
- Use UTC timezone (Z or +00:00) for simplicity

---

## Issue: 429 Too Many Requests - Rate Limit Exceeded

### Symptoms
- Webhook requests returning `429 Too Many Requests`
- Log message: `Rate limit exceeded: acme-corp/ticket_created - 100 > 100`
- Response header: `Retry-After: 45`

### Root Causes & Solutions

#### 1. Tenant Hitting Configured Rate Limit

**Check:** Tenant is sending webhooks faster than rate limit allows.

**Diagnosis:**
```bash
# Check current rate limits for tenant
curl -X GET https://api.example.com/admin/tenants/acme-corp \
  -H "X-Admin-Key: $ADMIN_KEY" \
  | jq '.rate_limits'

# Expected output:
# {
#   "webhooks": {
#     "ticket_created": 100,
#     "ticket_resolved": 100
#   }
# }

# Check current request rate (from logs)
# Count 429 responses in last minute
```

**Solution:**
```bash
# Option 1: Increase rate limit for tenant
curl -X PATCH https://api.example.com/admin/tenants/acme-corp \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "rate_limits": {
      "webhooks": {
        "ticket_created": 200,    # Increased from 100
        "ticket_resolved": 200
      }
    }
  }'

# Option 2: Reset rate limit counter (if spike is temporary)
# Implementation depends on admin API - see admin API docs
```

#### 2. Temporary Spike in Webhook Volume

**Check:** Tenant suddenly sending many webhooks (e.g., during bulk import).

**Diagnosis:**
```bash
# Check request rate in logs
# Sample: 50 webhook requests in 10 seconds = 5 requests/sec = 300/min
# (Limit is 100/min = 1.67 requests/sec)
```

**Solution:**
```bash
# Option 1: Temporarily increase limit
curl -X PATCH https://api.example.com/admin/tenants/acme-corp \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -d '{"rate_limits": {"webhooks": {"ticket_created": 500}}}'

# Option 2: Implement back-off on source side
# When receiving 429, wait for Retry-After seconds before retrying
# Implement exponential backoff: wait, 2*wait, 4*wait, etc.

# Option 3: Batch webhooks on source side
# Instead of sending 100 webhooks individually,
# group into 10 batches of 10 and space out delivery
```

#### 3. Rate Limiter Not Resetting

**Check:** Redis sliding window counter stuck or not expiring.

**Diagnosis:**
```bash
# Connect to Redis
redis-cli -h $REDIS_HOST -p $REDIS_PORT

# Check rate limit key
KEYS webhook_rate_limit:acme-corp:ticket_created

# Check contents
ZRANGE webhook_rate_limit:acme-corp:ticket_created 0 -1 WITHSCORES

# Should be empty or have timestamps < 1 minute old
```

**Solution:**
```bash
# Option 1: Reset rate limit manually (via admin API)
# Implementation depends on admin API

# Option 2: Clear Redis key directly (if API not available)
redis-cli -h $REDIS_HOST DEL webhook_rate_limit:acme-corp:ticket_created

# Option 3: Check Redis connection and expiration
redis-cli -h $REDIS_HOST INFO
# Verify connected_clients, used_memory, etc.
# Check TTL on keys: TTL webhook_rate_limit:acme-corp:ticket_created
```

---

## Issue: 404 Not Found - Tenant Not Found

### Symptoms
- Log message: `Tenant not found in database`
- Webhook requests returning `404 Not Found`

### Root Causes & Solutions

#### 1. Tenant Not Provisioned

**Check:** Tenant configuration doesn't exist in database.

**Diagnosis:**
```bash
# Check if tenant exists
psql $DATABASE_URL -c \
  "SELECT tenant_id, name FROM tenant_configs
   WHERE tenant_id = 'acme-corp';"

# If no results, tenant doesn't exist
```

**Solution:**
```bash
# Provision tenant via admin API
curl -X POST https://api.example.com/admin/tenants \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "acme-corp",
    "name": "ACME Corporation",
    "servicedesk_url": "https://sd.acme.com",
    "webhook_signing_secret": "YOUR_SECRET_HERE",
    "enhancement_preferences": {...},
    "rate_limits": {
      "webhooks": {
        "ticket_created": 100,
        "ticket_resolved": 100
      }
    }
  }'

# Verify tenant created
psql $DATABASE_URL -c \
  "SELECT tenant_id FROM tenant_configs WHERE tenant_id = 'acme-corp';"
```

#### 2. Tenant ID Mismatch

**Check:** Webhook payload tenant_id doesn't match any configured tenant.

**Diagnosis:**
```bash
# Check which tenants exist
psql $DATABASE_URL -c "SELECT tenant_id FROM tenant_configs ORDER BY tenant_id;"

# Check webhook payload
# Webhook: {"tenant_id": "acme-corp", ...}
# Database: "customer-acme", "acme-solutions", etc.
```

**Solution:**
- Verify correct tenant_id in webhook payload
- Update webhook source to use correct tenant_id
- Or provision missing tenant

#### 3. Tenant ID Typo or Casing

**Check:** tenant_id has typo or wrong casing.

**Examples:**
```bash
# Configured
"acme-corp"

# Webhook sends (wrong)
"acme-co"        # Typo (missing 'rp')
"ACME-CORP"      # Wrong casing (uppercase)
"acme corp"      # Wrong separator (space instead of dash)
```

**Solution:**
- Verify exact tenant_id in database
- Update webhook source to use exact ID
- Remember: tenant_id is case-sensitive and must be lowercase

---

## Issue: 403 Forbidden - Tenant Inactive

### Symptoms
- Log message: `Tenant is inactive`
- Webhook requests returning `403 Forbidden`

### Root Causes & Solutions

#### 1. Tenant Status Set to Inactive

**Check:** Tenant configuration is marked as inactive.

**Diagnosis:**
```bash
# Check tenant status
psql $DATABASE_URL -c \
  "SELECT tenant_id, is_active FROM tenant_configs
   WHERE tenant_id = 'acme-corp';"
```

**Solution:**
```bash
# Activate tenant via admin API
curl -X PATCH https://api.example.com/admin/tenants/acme-corp \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"is_active": true}'

# Or via database
psql $DATABASE_URL -c \
  "UPDATE tenant_configs SET is_active = true
   WHERE tenant_id = 'acme-corp';"
```

---

## Debugging Checklist

### 1. Gather Information
- [ ] Exact error message from webhook response
- [ ] HTTP status code (401, 422, 429, etc.)
- [ ] Webhook payload (JSON body)
- [ ] Request headers (especially X-ServiceDesk-Signature)
- [ ] Server logs with structured fields
- [ ] Source system information (IP, hostname)

### 2. Test Signature Computation
- [ ] Manually compute signature using provided secret
- [ ] Verify payload hasn't been modified
- [ ] Check secret encoding (UTF-8)
- [ ] Use constant-time comparison for testing

### 3. Check Configuration
- [ ] Verify tenant exists in database
- [ ] Verify tenant is active
- [ ] Verify webhook secret matches
- [ ] Verify rate limits aren't exceeded
- [ ] Verify timestamp is recent

### 4. Verify Environment
- [ ] Check API server clock synchronization
- [ ] Check source system clock synchronization
- [ ] Verify Redis connection (for rate limiting)
- [ ] Verify database connection
- [ ] Check network connectivity

### 5. Review Logs
- [ ] Search logs for tenant_id
- [ ] Look for security events (event_type, error_type fields)
- [ ] Check for repeated failures (pattern)
- [ ] Review timing of issues (correlation analysis)

---

## Testing Webhooks

### Manual Test

```bash
#!/bin/bash

WEBHOOK_SECRET="your-webhook-secret"
TENANT_ID="acme-corp"
API_URL="https://api.example.com"
ENDPOINT="/webhooks/tickets"

# 1. Create webhook payload
PAYLOAD='{
  "tenant_id": "'$TENANT_ID'",
  "event": "ticket_created",
  "ticket_id": "TKT-001",
  "description": "Test webhook",
  "priority": "high",
  "created_at": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
}'

# 2. Compute signature
SIGNATURE=$(echo -n "$PAYLOAD" | \
  openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | \
  cut -d' ' -f2)

# 3. Send webhook
curl -X POST "$API_URL$ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "X-ServiceDesk-Signature: $SIGNATURE" \
  -d "$PAYLOAD" \
  -v
```

### Automated Test

See `tests/integration/test_webhook_security.py` for comprehensive test examples covering:
- Signature validation
- Timestamp validation
- Rate limiting
- Tenant isolation
- Error handling

Run tests:
```bash
pytest tests/integration/test_webhook_security.py -v
```

---

## Escalation

If unable to resolve:

1. **Collect diagnostic information:**
   - Webhook request/response (headers + body)
   - Server logs (past 5 minutes around failure)
   - Database state (tenant config, secrets)
   - Redis state (rate limit counters)

2. **Contact Development Team:**
   - Include diagnostic information above
   - Include reproduction steps
   - Include timeline of issue

3. **Temporary Mitigation:**
   - Increase rate limits temporarily
   - Disable signature validation (if security policy allows)
   - Increase timestamp tolerance temporarily

---

## Related Documentation

- **Configuration:** `docs/webhooks/WEBHOOK_SECURITY.md`
- **Test Suite:** `tests/integration/test_webhook_security.py`
- **Source Code:** `src/services/webhook_validator.py`, `src/services/rate_limiter.py`

