# HMAC Proxy v2.0 - Dynamic Agent Routing Guide

**Status:** ✅ **READY FOR USE**
**Last Updated:** 2025-11-16
**Version:** 2.0.0

---

## What's New in v2.0

The HMAC Proxy has been upgraded with **dynamic agent routing**, eliminating the need to manually update configuration and restart the proxy when switching between agents.

### Key Features

✅ **Dynamic Agent Discovery** - Automatically looks up agents from the AI Ops API
✅ **Multiple Routing Strategies** - Route by agent ID, agent name, or use default agent
✅ **Agent Caching** - Caches agent lookups for 5 minutes to minimize API calls
✅ **Zero Downtime** - Switch agents without restarting the proxy
✅ **Backward Compatible** - Works with existing Jira webhooks

---

## Architecture

```
┌─────────────┐
│    Jira     │ Webhook Automation
└──────┬──────┘
       │ POST https://hmac.nullbytes.app/jira-webhook
       │ Payload: { "agent_id": "xxx" or "agent_name": "yyy" }
       ▼
┌─────────────────────┐
│  Cloudflare Tunnel  │ hmac.nullbytes.app → localhost:3000
└──────┬──────────────┘
       │
       ▼
┌────────────────────────────┐
│  HMAC Proxy v2.0           │ Port 3000
│                            │
│  1. Extract agent ID/name  │
│  2. Lookup via API         │
│  3. Cache result (5 min)   │
│  4. Compute HMAC signature │
│  5. Forward to agent       │
└──────┬─────────────────────┘
       │ POST with X-Hub-Signature-256
       │
       ▼
┌─────────────────────┐
│  AI Ops API         │ Port 8000
│  /webhook/agents/   │
│  {agent_id}/webhook │
└─────────────────────┘
```

---

## Configuration

### Environment Variables (docker-compose.yml)

```yaml
hmac-proxy:
  environment:
    - HMAC_SECRET=${TICKET_ENHANCER_HMAC_SECRET}  # HMAC signing key
    - API_BASE_URL=http://api:8000                 # AI Ops API base URL
    - DEFAULT_AGENT_ID=00bab7b6-...                # Fallback agent (optional)
    - TIMEOUT_SECONDS=30                           # API timeout
    - AGENT_CACHE_TTL=300                          # Cache duration (5 mins)
```

### What Changed from v1.0

**Before (v1.0):**
```yaml
- TARGET_WEBHOOK_URL=http://api:8000/webhook/agents/00bab7b6-.../webhook
```

**After (v2.0):**
```yaml
- API_BASE_URL=http://api:8000
- DEFAULT_AGENT_ID=00bab7b6-6335-4359-96b4-f48f3460b610
```

---

## Routing Strategies

### Strategy 1: Route by Agent ID (Recommended)

Include `agent_id` in your Jira webhook payload:

```json
{
  "issue_key": "PROJ-123",
  "agent_id": "550e8400-e29b-41d4-a716-446655440000",
  "issue": {
    "summary": "Fix login bug",
    "description": "..."
  }
}
```

The proxy will:
1. Extract `agent_id` from payload
2. Look up agent endpoint: `/api/agents/550e8400-...`
3. Route to: `/webhook/agents/550e8400-.../ webhook`

### Strategy 2: Route by Agent Name

Include `agent_name` in your Jira webhook payload:

```json
{
  "issue_key": "PROJ-123",
  "agent_name": "Ticket Enhancer",
  "issue": {
    "summary": "..."
  }
}
```

The proxy will:
1. Extract `agent_name` from payload
2. Search agents: `/api/agents?name=Ticket%20Enhancer`
3. Use first matching agent

### Strategy 3: Use Default Agent

If no `agent_id` or `agent_name` is provided, the proxy uses `DEFAULT_AGENT_ID`:

```json
{
  "issue_key": "PROJ-123",
  "issue": {
    "summary": "..."
  }
}
```

The proxy will:
1. No agent identifier found in payload
2. Fallback to `DEFAULT_AGENT_ID` from environment
3. Route to default agent

---

## Jira Configuration

### Option A: Route to Specific Agent (Recommended)

Use Jira Automation's "Send web request" action with custom payload:

```json
{
  "issue_key": "{{issue.key}}",
  "agent_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "jira:issue_created",
  "timestamp": "{{now}}",
  "issue": {
    "key": "{{issue.key}}",
    "fields": {
      "summary": "{{issue.summary}}",
      "description": "{{issue.description}}",
      "priority": {
        "name": "{{issue.priority.name}}"
      }
    }
  },
  "tenant_id": "4952b9b3-5909-4041-95a9-e068e01f7e13"
}
```

### Option B: Route by Agent Name

```json
{
  "issue_key": "{{issue.key}}",
  "agent_name": "Ticket Enhancer",
  "event_type": "jira:issue_created",
  ...
}
```

### Option C: Use Default Agent

Omit `agent_id` and `agent_name` - proxy will use `DEFAULT_AGENT_ID`:

```json
{
  "issue_key": "{{issue.key}}",
  "event_type": "jira:issue_created",
  ...
}
```

---

## How to Switch Agents

### Method 1: Update Jira Webhook Payload (Recommended)

**No proxy changes needed!** Just update the `agent_id` in your Jira automation:

1. Go to Jira → Project Settings → Automation
2. Edit your webhook rule
3. Update `agent_id` in the payload
4. Save

Done! The proxy will automatically route to the new agent.

### Method 2: Change Default Agent

If using the default agent fallback:

1. Edit `docker-compose.yml`:
   ```yaml
   - DEFAULT_AGENT_ID=NEW_AGENT_ID_HERE
   ```

2. Restart proxy:
   ```bash
   docker-compose restart hmac-proxy
   ```

---

## API Endpoints

### Health Check

```bash
curl http://localhost:3000/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "hmac-proxy",
  "version": "2.0.0",
  "features": ["dynamic-routing", "agent-lookup", "caching"],
  "api_base_url": "http://api:8000",
  "default_agent_id": "00bab7b6-...",
  "cached_agents": 2
}
```

### Service Info

```bash
curl http://localhost:3000/
```

**Response:**
```json
{
  "service": "HMAC Webhook Proxy",
  "version": "2.0.0",
  "features": ["dynamic-routing", "agent-lookup", "caching"],
  "endpoints": {
    "health": "/health (GET)",
    "webhook": "/jira-webhook (POST)"
  },
  "routing": {
    "payload_fields": ["agent_id", "agent_name"],
    "fallback": "00bab7b6-..."
  },
  "cached_agents": 2
}
```

### Clear Agent Cache

```bash
curl -X POST http://localhost:3000/cache/clear
```

**Response:**
```json
{
  "status": "cache_cleared",
  "message": "All cached agents have been removed"
}
```

**When to use:** After creating/updating agents to force fresh lookup.

---

## Testing

### Test 1: Verify Proxy is Running

```bash
curl http://localhost:3000/health
```

**Expected:** HTTP 200 with `{"status":"healthy",...}`

### Test 2: Test Webhook with Default Agent

```bash
curl -X POST http://localhost:3000/jira-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "issue_key": "TEST-123",
    "event_type": "test",
    "tenant_id": "4952b9b3-5909-4041-95a9-e068e01f7e13",
    "issue": {
      "key": "TEST-123",
      "fields": {
        "summary": "Test webhook routing",
        "description": "Testing dynamic agent routing"
      }
    }
  }'
```

**Expected:** HTTP 202 with `{"status":"queued","execution_id":"..."}`

### Test 3: Test Routing to Specific Agent

```bash
curl -X POST http://localhost:3000/jira-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "issue_key": "TEST-456",
    "agent_id": "YOUR_AGENT_ID_HERE",
    "event_type": "test",
    "tenant_id": "4952b9b3-5909-4041-95a9-e068e01f7e13",
    "issue": {
      "key": "TEST-456",
      "fields": {
        "summary": "Test specific agent",
        "description": "Testing agent_id routing"
      }
    }
  }'
```

### Test 4: Test Routing by Agent Name

```bash
curl -X POST http://localhost:3000/jira-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "issue_key": "TEST-789",
    "agent_name": "Ticket Enhancer",
    "event_type": "test",
    "tenant_id": "4952b9b3-5909-4041-95a9-e068e01f7e13",
    "issue": {
      "key": "TEST-789",
      "fields": {
        "summary": "Test name routing",
        "description": "Testing agent_name routing"
      }
    }
  }'
```

---

## Troubleshooting

### Issue: "Agent not found"

**Error:**
```json
{
  "detail": "Agent not found: xxx"
}
```

**Causes:**
1. Invalid agent ID
2. Agent name mismatch
3. Agent doesn't exist

**Solutions:**
1. Verify agent ID in Admin UI
2. Check agent name spelling
3. Clear cache: `curl -X POST http://localhost:3000/cache/clear`

### Issue: "Missing agent_id or agent_name in payload"

**Error:**
```json
{
  "detail": "Missing agent_id or agent_name in payload, and no DEFAULT_AGENT_ID configured"
}
```

**Cause:** No agent identifier in payload and no default configured

**Solution:** Either:
1. Add `agent_id` or `agent_name` to Jira payload
2. Set `DEFAULT_AGENT_ID` in docker-compose.yml

### Issue: Proxy always routes to same agent

**Cause:** Agent cache is stale

**Solution:**
```bash
curl -X POST http://localhost:3000/cache/clear
```

### Issue: "Failed to lookup agent"

**Cause:** AI Ops API is unreachable

**Check:**
1. API is running: `docker-compose ps api`
2. API is healthy: `curl http://localhost:8000/health`
3. Network connectivity: `docker-compose logs hmac-proxy`

---

## Migration from v1.0

### Before (v1.0)

```yaml
# docker-compose.yml
environment:
  - TARGET_WEBHOOK_URL=http://api:8000/webhook/agents/00bab7b6-.../webhook
```

### After (v2.0)

```yaml
# docker-compose.yml
environment:
  - API_BASE_URL=http://api:8000
  - DEFAULT_AGENT_ID=00bab7b6-6335-4359-96b4-f48f3460b610
```

### Migration Steps

1. **Update docker-compose.yml:**
   ```bash
   # Remove TARGET_WEBHOOK_URL
   # Add API_BASE_URL and DEFAULT_AGENT_ID
   ```

2. **Rebuild proxy:**
   ```bash
   docker-compose build hmac-proxy
   docker-compose up -d --force-recreate hmac-proxy
   ```

3. **Verify:**
   ```bash
   curl http://localhost:3000/health
   # Check version: "2.0.0"
   ```

4. **Test:**
   ```bash
   # Send test webhook (see Testing section)
   ```

**No Jira changes required!** Existing webhooks will use the default agent.

---

## Performance

### Agent Caching

- **Cache TTL:** 5 minutes (configurable via `AGENT_CACHE_TTL`)
- **Cache Key:** Agent ID or agent name
- **Cache Invalidation:** Manual via `/cache/clear` endpoint

### API Call Optimization

- **First request:** Lookup agent via API (~50-100ms)
- **Cached requests:** No API call (~1-5ms)
- **Cache miss:** Automatic re-lookup

---

## Security

### HMAC Signature Validation

- Same HMAC secret for all agents
- Signature computed using agent-specific webhook payload
- Constant-time comparison prevents timing attacks

### Agent Access Control

- Agent must exist in database
- Agent status must be `ACTIVE`
- Tenant isolation enforced by AI Ops API

---

## FAQ

### Q: Do I need to update Jira configuration?

**A:** No! Jira webhook URL stays the same: `https://hmac.nullbytes.app/jira-webhook`

### Q: Can I route different issue types to different agents?

**A:** Yes! Create multiple Jira automation rules with different conditions and `agent_id` values.

**Example:**
- **Rule 1:** `issue.type = Bug` → agent_id: "bug-analyzer-agent"
- **Rule 2:** `issue.type = Story` → agent_id: "story-enhancer-agent"

### Q: What happens if agent lookup fails?

**A:** The proxy returns HTTP 404 "Agent not found" to Jira. The webhook fails, and Jira will show the error in automation logs.

### Q: Can I use the same proxy for multiple tenants?

**A:** Yes, but each tenant should include their `tenant_id` in the webhook payload (already done in the examples above).

### Q: How do I add a new agent without downtime?

**A:** Just create the agent in the Admin UI. The proxy will automatically discover it when you include the `agent_id` in your Jira webhook.

---

## Summary

### What You Gained

✅ **Zero-downtime agent switching** - Change agents via Jira payload
✅ **Multi-agent support** - Route different issues to different agents
✅ **Automatic agent discovery** - No manual endpoint configuration
✅ **Performance optimization** - 5-minute agent caching
✅ **Backward compatibility** - Existing webhooks work with default agent

### Next Steps

1. ✅ Update Jira webhook payloads to include `agent_id`
2. ✅ Test routing to different agents
3. ✅ Create multiple automation rules for different issue types
4. ✅ Monitor proxy logs for successful routing

---

**Status:** 🚀 **PRODUCTION READY (v2.0)**
**Documentation:** ✅ **Complete**
**Testing:** ✅ **Verified**
