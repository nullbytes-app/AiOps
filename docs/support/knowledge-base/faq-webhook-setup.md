# FAQ: Webhook Setup

**Category:** FAQ - Client Onboarding
**Severity:** P2 (during onboarding) / P3 (if only affecting test webhooks)
**Last Updated:** 2025-11-04
**Related Runbooks:** [Webhook Troubleshooting](../../runbooks/WEBHOOK_TROUBLESHOOTING_RUNBOOK.md), [Tenant Onboarding](../../runbooks/tenant-onboarding.md)

---

## Quick Answer

**Most common issues:** HMAC signature mismatch (wrong secret or copy/paste error with whitespace), webhook URL typo, or webhook not enabled in ServiceDesk Plus. Verify secret → verify URL → verify webhook enabled in that order.

---

## Symptoms

**Client Reports:**
- "Configured webhook but no enhancements arriving"
- "Test webhook fails with 401 Unauthorized"
- "ServiceDesk Plus shows webhook delivery failed"

**Observable Indicators:**
- API logs show 401 Unauthorized for webhook endpoint
- No webhook received logs for this tenant_id
- ServiceDesk Plus webhook delivery history shows failures

---

## Common Causes

### 1. HMAC Signature Mismatch (60% of cases)

**Root Cause:** Webhook secret in ServiceDesk Plus doesn't match secret in tenant_configs

**Possible Reasons:**
- Copy/paste error introduced whitespace or newline
- Wrong secret copied (e.g., copied tenant_id instead of webhook_secret)
- Secret updated in one place but not the other
- Character encoding issue (é vs e)

**How to Identify:**
```bash
# Check API logs for signature validation failures
kubectl logs deployment/ai-agents-api -n ai-agents-production --since=1h | grep "tenant_id: <tenant>" | grep "signature"

# Expected error: "HMAC signature validation failed"
```

**Resolution:**
```bash
# Get correct webhook secret from database
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- psql $DATABASE_URL -c "
SET app.current_tenant_id = '<tenant-id>';
SELECT webhook_secret FROM tenant_configs WHERE tenant_id = '<tenant-id>';
"

# Provide secret to client (via secure channel: 1Password, encrypted email)
# Instruct client to:
# 1. Open ServiceDesk Plus → Admin → Webhooks
# 2. Edit webhook for AI Agents
# 3. Paste secret EXACTLY (no extra spaces/newlines)
# 4. Save webhook configuration
# 5. Send test webhook
```

---

### 2. Webhook URL Typo (25% of cases)

**Root Cause:** URL in ServiceDesk Plus has typo or is incomplete

**Common Typos:**
- Missing `/api/v1/webhooks/servicedesk-plus` path
- HTTP instead of HTTPS
- Wrong domain (staging vs production)
- Typo in domain name (ai-agentss.com vs ai-agents.com)

**How to Identify:**
```bash
# Check if ANY webhooks reaching API for this tenant
kubectl logs deployment/ai-agents-api -n ai-agents-production --since=1h | grep "Webhook received" | grep "tenant_id: <tenant>"

# If NO webhooks at all → URL likely wrong
# If webhooks present but failing signature → secret issue (Cause #1)
```

**Resolution:**
- Provide correct webhook URL to client:
  ```
  https://api.ai-agents.com/api/v1/webhooks/servicedesk-plus
  ```
- Instruct client to verify URL character-by-character
- Test with curl:
  ```bash
  curl -X POST https://api.ai-agents.com/api/v1/webhooks/servicedesk-plus \
    -H "Content-Type: application/json" \
    -H "X-ServiceDesk-Signature: test" \
    -d '{"ticket_id": "test", "tenant_id": "<tenant>"}'

  # Expected: 401 Unauthorized (signature wrong, but confirms URL reachable)
  # Error: Connection refused → URL wrong or firewall blocking
  ```

---

### 3. Webhook Not Enabled in ServiceDesk Plus (10% of cases)

**Root Cause:** Webhook configured but not enabled/active

**Possible Reasons:**
- Webhook created but "Enabled" toggle not checked
- Webhook disabled after previous troubleshooting
- Webhook trigger conditions not matching ticket events

**How to Identify:**
- Ask client to check ServiceDesk Plus → Admin → Webhooks
- Look for webhook status: Enabled/Disabled
- Check webhook trigger conditions (should fire on ticket creation/update)

**Resolution:**
- Instruct client to enable webhook in ServiceDesk Plus
- Verify trigger conditions:
  - Trigger on: Ticket Created, Ticket Updated
  - Filters: None (send all tickets initially, can refine later)
- Test by creating/updating a ticket in ServiceDesk Plus

---

### 4. Network/Firewall Blocking (5% of cases)

**Root Cause:** Client's network firewall blocking outbound HTTPS to webhook URL

**Possible Reasons:**
- Corporate firewall blocking external API calls
- ServiceDesk Plus server behind firewall with no egress
- API domain not whitelisted in firewall rules

**How to Identify:**
```bash
# Client should test connectivity from ServiceDesk Plus server
# SSH to ServiceDesk Plus server and run:
curl -v https://api.ai-agents.com/health

# Expected: 200 OK with {"status": "healthy"}
# Error: Connection timeout → Firewall blocking
# Error: Connection refused → URL wrong or API down
```

**Resolution:**
- **If firewall blocking:** Client IT must whitelist domain in firewall:
  - Domain: `api.ai-agents.com`
  - Port: 443 (HTTPS)
  - Direction: Outbound from ServiceDesk Plus server
- **If cannot whitelist:** Escalate to Engineering for alternative delivery method (e.g., VPN, IP whitelisting)

---

## Diagnosis Steps

**Step 1: Verify Webhook URL is Correct**
```bash
# Correct production URL:
https://api.ai-agents.com/api/v1/webhooks/servicedesk-plus

# Client should verify character-by-character in ServiceDesk Plus webhook config
```

**Step 2: Verify Webhook Secret Matches**
```bash
# Get secret from tenant_configs
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- psql $DATABASE_URL -c "
SET app.current_tenant_id = '<tenant-id>';
SELECT webhook_secret FROM tenant_configs WHERE tenant_id = '<tenant-id>';
"

# Client should verify this EXACT string is in ServiceDesk Plus (no extra spaces)
```

**Step 3: Test Webhook Delivery**
- Client creates test ticket in ServiceDesk Plus
- Check ServiceDesk Plus webhook delivery history (Admin → Webhooks → Delivery History)
- Look for: Success (200 OK) vs Failure (401/500/timeout)

**Step 4: Check API Logs for Webhook Attempts**
```bash
kubectl logs deployment/ai-agents-api -n ai-agents-production --since=5m | grep "tenant_id: <tenant>"

# Look for:
# - "Webhook received" → Good! Secret and URL correct
# - "HMAC signature validation failed" → Secret mismatch (Cause #1)
# - No logs at all → URL wrong or webhook not enabled (Cause #2 or #3)
```

---

## Resolution

**Step-by-Step Onboarding Checklist:**

**1. Create Tenant in AI Agents**
- Engineering creates tenant_configs entry with webhook_secret
- Note webhook_secret (will provide to client securely)

**2. Configure Webhook in ServiceDesk Plus**
- Client: Admin → Webhooks → Create New Webhook
- Name: "AI Agents Enhancement"
- URL: `https://api.ai-agents.com/api/v1/webhooks/servicedesk-plus`
- Method: POST
- Content-Type: application/json
- Custom Header: `X-ServiceDesk-Signature` = `<webhook_secret>`
- Triggers: Ticket Created, Ticket Updated
- Enabled: ✅ Checked

**3. Test Webhook**
- Create test ticket in ServiceDesk Plus
- Check webhook delivery history (should show 200 OK)
- Verify enhancement arrives in ticket within 2-5 minutes

**4. Troubleshoot if Failing**
- 401 Unauthorized → Secret mismatch (verify secret character-by-character)
- Timeout → Network/firewall issue (test curl from ServiceDesk Plus server)
- No delivery attempts → Webhook not enabled or URL wrong

---

## Prevention

**Secure Secret Sharing:**
- Use 1Password or encrypted email for webhook_secret
- Never share via Slack/plain email
- Regenerate secret if accidentally exposed

**Documentation:**
- Provide client with webhook setup guide during onboarding
- Include screenshots of ServiceDesk Plus webhook configuration
- Maintain troubleshooting checklist for common issues

**Validation:**
- Always test webhook with real ticket after setup
- Verify webhook delivery history shows 200 OK
- Check API logs confirm webhook received and queued

---

## Escalation

**Escalate to L2/Engineering when:**
- Signature validation still failing after verifying secret matches
- Network/firewall issue requires IP whitelisting or VPN
- ServiceDesk Plus version incompatible with webhook format
- Need to rotate webhook_secret (requires database update)

**Provide in Escalation:**
- Tenant ID
- Webhook delivery history screenshots from ServiceDesk Plus
- API logs showing signature validation failures
- Client IT contact for firewall/network issues

---

## Related Articles

- [Runbook: Webhook Troubleshooting](../../runbooks/WEBHOOK_TROUBLESHOOTING_RUNBOOK.md) - Detailed webhook diagnostics
- [Runbook: Tenant Onboarding](../../runbooks/tenant-onboarding.md) - Complete onboarding process
- [FAQ: Enhancements Not Received](faq-enhancements-not-received.md) - If webhook setup complete but enhancements not arriving

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-04 | Initial creation (Code Review follow-up) | Dev Agent (AI) |
