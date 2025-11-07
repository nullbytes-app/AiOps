# BYOK (Bring Your Own Key) Setup Guide

**Story 8.13 - Documentation**

## Overview

BYOK (Bring Your Own Key) allows tenant administrators to use their own OpenAI and Anthropic API keys instead of relying on platform-managed keys. This provides:

- **Full cost control**: Track LLM costs in your own accounts
- **Data sovereignty**: Ensure API calls use your authentication
- **Flexible budget management**: Set your own rate limits per provider
- **Easy rotation**: Update keys without platform intervention

### When to Use BYOK

**Choose BYOK if:**
- You want detailed cost tracking per provider
- Your organization has strict data residency requirements
- You prefer to manage API key rotation independently
- You need separate billing for different teams/projects

**Use Platform Keys if:**
- You prefer simplified management
- You want consolidated billing through the platform
- You're getting started and want to minimize setup

---

## Getting Started

### Prerequisites

Before enabling BYOK, ensure you have:

1. **OpenAI API Key** (optional, if using OpenAI models)
   - Active OpenAI account: https://platform.openai.com
   - API key with access to chat completion models

2. **Anthropic API Key** (optional, if using Claude models)
   - Active Anthropic account: https://console.anthropic.com
   - API key with appropriate permissions

3. **Platform Admin Access**
   - Admin API key for authorizing BYOK configuration changes
   - Access to the Tenant Management interface

**Note:** You must provide at least one provider key (OpenAI or Anthropic).

---

## Step-by-Step Setup

### 1. Generate OpenAI API Key

If you plan to use OpenAI models:

1. Go to https://platform.openai.com/account/api-keys
2. Click "Create new secret key"
3. Name it (e.g., "AI Agents BYOK")
4. Copy the key (starts with `sk-`)
5. **Store securely** - you won't see it again

**Best Practice:** Create a dedicated API key for your AI Agents instance rather than reusing your primary key.

### 2. Generate Anthropic API Key

If you plan to use Claude models:

1. Go to https://console.anthropic.com/account/keys
2. Click "Create Key"
3. Name it (e.g., "AI Agents BYOK")
4. Copy the key (starts with `sk-ant-`)
5. **Store securely** - treat like a password

### 3. Access Tenant Management Interface

1. Navigate to Admin Panel → Tenants
2. Select the tenant to configure
3. Scroll to "LLM Configuration" section
4. Select radio button: "Use own keys (BYOK)"

### 4. Test Your Keys

Before saving, always test your API keys:

1. Enter your OpenAI API key (if using OpenAI)
2. Enter your Anthropic API key (if using Anthropic)
3. Click "Test Keys" button
4. Wait for validation results:
   - ✅ **Valid**: Shows list of available models
   - ❌ **Invalid**: Shows error (check key format and permissions)

**Example Output:**
```
✅ OpenAI: Valid (20 models available)
   - gpt-4, gpt-4-turbo, gpt-3.5-turbo, ...

✅ Anthropic: Valid (5 models available)
   - claude-3-5-sonnet, claude-3-opus, claude-3-sonnet, ...
```

### 5. Save BYOK Configuration

1. Once testing passes, click "Save BYOK Configuration"
2. System confirms: "BYOK enabled for tenant"
3. Your keys are encrypted and stored securely
4. Agents automatically use your keys for all LLM calls

**What Happens Next:**
- All agent LLM calls route through your API keys
- Usage costs appear in your OpenAI/Anthropic accounts
- Platform no longer tracks costs (shows "N/A" in dashboard)
- Cost tracking mode switches to "BYOK"

---

## Managing BYOK Configuration

### View Current Status

In Tenant Management → LLM Configuration section:

- **BYOK Mode:** Shows enabled/disabled status
- **Providers:** Lists which providers are configured
- **Enabled Since:** Timestamp when BYOK was activated
- **Cost Tracking:** Displays "Using own keys" with 🔑 badge

### Rotate Keys

To update your API keys (e.g., due to expiration or security):

1. Click "Rotate Keys" button (only visible if BYOK enabled)
2. Enter new OpenAI key (or skip to keep current)
3. Enter new Anthropic key (or skip to keep current)
4. Click "Test New Keys" to validate
5. Click "Confirm Rotation" after testing

**Important:** You must provide at least one key during rotation.

**Timeline:**
- Old key is immediately revoked
- New key takes effect for all subsequent requests
- In-flight requests may fail - agents will retry

### Revert to Platform Keys

To disable BYOK and return to platform-managed keys:

1. Click "Revert to Platform Keys" button
2. Confirm dialog appears with warning
3. Check "I understand this action will clear my BYOK configuration"
4. Click "Confirm"

**What Happens:**
- BYOK is disabled
- Your encrypted keys are deleted from system
- Platform creates standard virtual key
- All agents switch to platform keys
- Cost tracking resumes in platform dashboard

---

## API Reference

### Test Keys Endpoint

```bash
curl -X POST https://your-api.com/api/tenants/{tenant_id}/byok/test-keys \
  -H "X-Admin-Key: your-admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "openai_key": "sk-...",
    "anthropic_key": "sk-ant-..."
  }'
```

**Response:**
```json
{
  "openai": {
    "valid": true,
    "models": ["gpt-4", "gpt-3.5-turbo"],
    "error": null
  },
  "anthropic": {
    "valid": true,
    "models": ["claude-3-5-sonnet"],
    "error": null
  }
}
```

### Enable BYOK Endpoint

```bash
curl -X POST https://your-api.com/api/tenants/{tenant_id}/byok/enable \
  -H "X-Admin-Key: your-admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "openai_key": "sk-...",
    "anthropic_key": "sk-ant-..."
  }'
```

### Get BYOK Status

```bash
curl -X GET https://your-api.com/api/tenants/{tenant_id}/byok/status \
  -H "X-Admin-Key: your-admin-key"
```

---

## Security Considerations

### Key Management

**✅ DO:**
- Store keys in secure password manager
- Use unique keys for each environment (dev/staging/prod)
- Rotate keys periodically (every 90 days recommended)
- Enable key expiration in your provider settings

**❌ DON'T:**
- Share API keys via email or chat
- Commit keys to version control
- Use personal/development keys in production
- Store keys in plain text files

### Encryption

All API keys are encrypted at rest using Fernet (symmetric encryption):

```python
# Keys stored as: encrypt(key) → encrypted value
# Keys retrieved as: decrypt(encrypted_value) → plaintext
```

- Encryption key: Managed by platform (from environment)
- Decryption: Only happens when keys are used for API calls
- Never logged: Plaintext keys never appear in logs

### Audit Trail

All BYOK operations are logged:

```
2025-11-07 10:30:15 - BYOK_ENABLED - tenant: acme-corp
2025-11-07 11:45:22 - BYOK_KEYS_ROTATED - tenant: acme-corp
2025-11-07 15:12:08 - BYOK_DISABLED - tenant: acme-corp
```

### Authorization

BYOK endpoints require admin authorization:

- Header: `X-Admin-Key: <your-admin-key>`
- Validates against `ADMIN_API_KEY` in environment
- Returns 403 Forbidden if unauthorized

---

## Troubleshooting

### "Invalid API Key" Error

**Cause:** Key format is wrong or key doesn't have required permissions

**Solutions:**
1. Verify key starts with `sk-` (OpenAI) or `sk-ant-` (Anthropic)
2. Check key hasn't been revoked in provider dashboard
3. Ensure key has access to required models
4. Try testing key in provider's documentation examples first

### "Key Validation Failed"

**Cause:** Network issue or provider API is down

**Solutions:**
1. Check internet connectivity
2. Verify provider status page (status.openai.com, status.anthropic.com)
3. Try again in a few minutes
4. Contact provider support if issue persists

### "Models Not Available"

**Cause:** Your API key doesn't have access to those models

**Solutions:**
1. Check your account tier (Pro, Enterprise, etc.)
2. Some models require specific account types
3. Ensure models are enabled in provider settings
4. Check for regional availability restrictions

### "Agent LLM Calls Failing After Enabling BYOK"

**Cause:** Key permissions or rate limits

**Solutions:**
1. Verify keys still work in test endpoint
2. Check provider account doesn't have usage limits exceeded
3. Review API key permissions in provider dashboard
4. Check agent logs for detailed error messages
5. Temporarily revert to platform keys to isolate issue

### "Can't Rotate Keys"

**Cause:** Missing required permission or invalid key format

**Solutions:**
1. Verify you're admin (have X-Admin-Key header)
2. Ensure at least one new key is provided
3. Test new keys before rotating
4. Check BYOK is actually enabled first

---

## Cost Tracking

### Platform Mode (Default)

```
Dashboard → Costs
+-------------------+
| Tenant: Acme Corp |
| Mode: Platform    |
| Total: $234.56    |
| Budget: $500/mo   |
+-------------------+
```

- Costs tracked centrally by platform
- Costs appear in platform dashboard
- Budget enforced by platform

### BYOK Mode

```
Dashboard → Costs
+-------------------+
| Tenant: Acme Corp |
| Mode: BYOK        |
| Total: N/A        |
| Status: Own Keys  |
+-------------------+
```

- Costs tracked in your provider accounts
- Platform dashboard shows "N/A"
- You manage budget per provider
- Check OpenAI/Anthropic dashboards for costs

---

## Best Practices

### 1. Key Rotation Strategy

**Monthly Rotation:**
- Week 1: Create new keys in provider dashboard
- Week 2: Test new keys via test endpoint
- Week 3: Rotate keys in BYOK configuration
- Week 4: Audit usage, confirm rotation successful

### 2. Multi-Team Setup

For organizations with multiple teams:

```
✓ Create separate tenant per team
✓ Each team has their own API keys
✓ Teams can manage keys independently
✓ Easy cost allocation by team
```

### 3. Development vs. Production

```
Development Tenant
├─ API keys with lower rate limits
├─ Separate from production keys
└─ Can be reset without production impact

Production Tenant
├─ API keys with production rate limits
├─ Separate encryption key/vault
├─ Audit logging enabled
└─ Key rotation schedule: every 90 days
```

### 4. Monitoring

Regularly check:

1. **Usage:** `openai.com/account/usage` and `console.anthropic.com/account/usage`
2. **Costs:** Compare with platform estimates
3. **Rate limits:** Ensure you're not hitting API limits
4. **Key expiration:** Set calendar reminders for rotations

---

## Architecture

### How BYOK Works

```
┌─────────────┐
│   Agent     │
│  (Executes  │
│  LLM Call)  │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────┐
│ LLMService.get_llm_client()  │
├──────────────────────────────┤
│ 1. Check byok_enabled flag   │
│ 2. Select virtual key:       │
│    - BYOK: byok_virtual_key  │
│    - Platform: standard key  │
│ 3. Decrypt key               │
│ 4. Return AsyncOpenAI client │
└──────────┬───────────────────┘
           │
           ▼ (uses either BYOK or platform key)
┌──────────────────────────────┐
│  LiteLLM Proxy Gateway       │
│  (Routes to provider)        │
└──────────┬───────────────────┘
           │
    ┌──────┴────────┐
    ▼               ▼
┌─────────────┐  ┌────────────┐
│  OpenAI API │  │ Anthropic  │
│  (if BYOK)  │  │ API (BYOK) │
└─────────────┘  └────────────┘
```

### Key Storage

```
Database (Encrypted)
├─ byok_enabled: boolean flag
├─ byok_openai_key_encrypted: Fernet(key)
├─ byok_anthropic_key_encrypted: Fernet(key)
├─ byok_virtual_key: encrypted LiteLLM key
└─ byok_enabled_at: timestamp

Memory (Runtime Only)
├─ decrypted openai_key (used for API call)
├─ decrypted anthropic_key (used for API call)
└─ virtual key (never decrypted in logs)
```

---

## Frequently Asked Questions

**Q: Can I use BYOK for just one provider?**
A: Yes! Provide OpenAI key only, or Anthropic only, or both.

**Q: What happens if my key expires?**
A: Agent LLM calls will fail with 401 Unauthorized. Rotate to new key immediately.

**Q: Can I switch back to platform keys?**
A: Yes, click "Revert to Platform Keys" anytime.

**Q: Are my keys encrypted?**
A: Yes, all keys encrypted at rest with Fernet. Only decrypted when making API calls.

**Q: Can platform admins see my keys?**
A: No. Keys are encrypted. Only your agents can decrypt and use them.

**Q: How often should I rotate keys?**
A: Industry standard: every 90 days. More often if suspected compromise.

**Q: What if I lose my key?**
A: Revoke in provider dashboard, generate new key, use rotate endpoint.

**Q: Does platform still track budget?**
A: No. In BYOK mode, costs aren't tracked by platform (shown as "N/A").

---

## Support

For issues or questions:

1. **Check Troubleshooting** section above
2. **Review API Reference** for correct endpoint usage
3. **Contact Platform Support** with:
   - Tenant ID
   - Error message
   - Steps to reproduce
   - Recent API key rotation dates

---

**Last Updated:** 2025-11-07
**Story:** 8.13 - BYOK (Bring Your Own Key)
**Version:** 1.0
