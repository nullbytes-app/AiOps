# CRITICAL: MCP Server Requires Tool Discovery

**Date**: 2025-11-16
**Status**: ⚠️ **BLOCKING** - Agent has ZERO tools loaded
**Action Required**: Trigger tool discovery via Streamlit UI

---

## Current Problem

The Jira MCP server configuration was successfully updated from the deprecated `sooperset/mcp-atlassian` to `fkesheh/jira-mcp-server` with API v3 support. However:

❌ **Agent execution `38eca40f` loaded 0 tools**
❌ **Agent cannot post comments without tools**
❌ **`discovered_tools` field is empty in database**

### Worker Logs Evidence
```
WARNING - Stale MCP tool excluded from agent 022e85cf: jira_batch_create_issues
INFO - Loaded 0 unified tools
INFO - Converted 0 total tools
INFO - Converted 0 tools to LangChain format  ← ZERO TOOLS!
```

---

## Root Cause

After updating the MCP server configuration:
1. ✅ Database `status` changed: `inactive` → `active` (manually fixed)
2. ✅ Database `command` changed: `docker` → `npx`
3. ✅ Database `args` changed to use `@fkesheh/jira-mcp-server@latest`
4. ❌ **`discovered_tools` is still empty** (not populated yet)

The agent service excludes tools from inactive servers AND requires `discovered_tools` to be populated.

---

## Why Tools Weren't Discovered

**Normal Flow (when creating MCP server via API)**:
1. POST `/api/mcp-servers` with configuration
2. API automatically triggers capability discovery
3. `discovered_tools`, `discovered_resources`, `discovered_prompts` get populated
4. Status set to `'active'` if discovery succeeds

**What Happened (manual SQL UPDATE)**:
1. Updated configuration directly in database via SQL
2. No automatic discovery triggered
3. `discovered_tools` remains empty (`[]`)
4. Agent loads 0 tools

---

## How to Fix

### Option 1: Use Streamlit UI (RECOMMENDED - Easiest)

1. Open Streamlit: `http://localhost:8501`
2. Navigate to **"MCP Servers"** page
3. Find "Jira Cloud MCP (API v3)"
4. Click **"Test Connection"** button
5. Verify:
   - ✅ Status shows "Success"
   - ✅ Tools count shows 30+ tools
   - ✅ No errors in output

**This will populate `discovered_tools` automatically.**

### Option 2: Use API Endpoint (If Streamlit Not Available)

```bash
curl -X POST 'http://localhost:8000/api/mcp-servers/test-connection' \
  -H 'Content-Type: application/json' \
  -H 'X-Tenant-ID: test1' \
  -d '{
    "name": "Jira Cloud MCP (API v3)",
    "description": "Test discovery",
    "transport_type": "stdio",
    "command": "npx",
    "args": ["-y", "@fkesheh/jira-mcp-server@latest"],
    "env": {
      "JIRA_URL": "https://aiopstest1.atlassian.net",
      "JIRA_USERNAME": "effect-datum8k@icloud.com",
      "JIRA_API_TOKEN": "YOUR_JIRA_API_TOKEN_HERE",
      "JIRA_API_VERSION": "3"
    }
  }'
```

**Then** manually copy the discovered tools to the database:
```sql
UPDATE mcp_servers
SET discovered_tools = '<tools_from_response>'
WHERE id = '77ee99f6-8f9f-4d24-aba7-830146e06c0e';
```

### Option 3: Delete & Recreate via API (Clean Slate)

```bash
# 1. Delete old server
curl -X DELETE 'http://localhost:8000/api/mcp-servers/77ee99f6-8f9f-4d24-aba7-830146e06c0e' \
  -H 'X-Tenant-ID: test1'

# 2. Create new with automatic discovery
curl -X POST 'http://localhost:8000/api/mcp-servers' \
  -H 'Content-Type: application/json' \
  -H 'X-Tenant-ID: test1' \
  -d '{
    "name": "Jira Cloud MCP (API v3)",
    "description": "Jira MCP server with API v3 support",
    "transport_type": "stdio",
    "command": "npx",
    "args": ["-y", "@fkesheh/jira-mcp-server@latest"],
    "env": {
      "JIRA_URL": "https://aiopstest1.atlassian.net",
      "JIRA_USERNAME": "effect-datum8k@icloud.com",
      "JIRA_API_TOKEN": "YOUR_JIRA_API_TOKEN_HERE",
      "JIRA_API_VERSION": "3"
    }
  }'
```

**This will create the server with automatic discovery.**

---

## Expected Results After Discovery

### Database Changes
```sql
SELECT
  name,
  status,
  jsonb_array_length(discovered_tools) as tool_count,
  jsonb_array_length(discovered_resources) as resource_count
FROM mcp_servers
WHERE id = '77ee99f6-8f9f-4d24-aba7-830146e06c0e';

-- Expected:
-- name: Jira Cloud MCP (API v3)
-- status: active
-- tool_count: 30+ (instead of 0)
-- resource_count: 0 or more
```

### Worker Logs (Next Execution)
```
INFO - Loaded X MCP tools from server Jira Cloud MCP (API v3)
INFO - Converted X tools to LangChain format  ← Should be 30+, not 0!
```

### Agent Behavior
- ✅ Can search Jira for related tickets
- ✅ Can post comments to Jira tickets
- ✅ No more "0 tools" warnings
- ✅ No more API v2 deprecation errors

---

## Verification Steps

After triggering discovery:

1. **Check Database**:
```sql
SELECT
  discovered_tools->0->>'name' as first_tool_name,
  jsonb_array_length(discovered_tools) as total_tools
FROM mcp_servers
WHERE id = '77ee99f6-8f9f-4d24-aba7-830146e06c0e';
```

Expected: `total_tools` should be 30+, `first_tool_name` might be something like `jira_get_issue`

2. **Trigger Test Execution**:
```bash
curl -X POST 'http://localhost:8000/api/agent-execution/execute' \
  -H 'Content-Type: application/json' \
  -H 'X-Tenant-ID: test1' \
  -d '{
    "agent_id": "022e85cf-e7b6-45d5-81c2-b0b6823cd8f3",
    "user_message": "Test with tools loaded",
    "timeout_seconds": 120
  }'
```

3. **Check Worker Logs**:
```bash
docker-compose logs -f worker | grep -i "converted.*tools"
```

Expected: `Converted 30+ tools to LangChain format` (not 0)

4. **Monitor Execution**:
- Agent should call tools like `jira_search_issues`, `jira_add_comment`
- No "Stale MCP tool excluded" warnings
- Comment should appear in Jira ticket

---

## Current MCP Server Configuration

```sql
-- Verified Configuration (from database)
ID: 77ee99f6-8f9f-4d24-aba7-830146e06c0e
Name: Jira Cloud MCP (API v3)
Status: active
Command: npx
Args: ["-y", "@fkesheh/jira-mcp-server@latest"]
Env: {
  "JIRA_URL": "https://aiopstest1.atlassian.net",
  "JIRA_USERNAME": "effect-datum8k@icloud.com",
  "JIRA_API_TOKEN": "***",
  "JIRA_API_VERSION": "3"  ← CRITICAL: Uses API v3
}
Discovered Tools: []  ← PROBLEM: Empty, needs discovery!
```

---

## Why This Matters

**Without Tools**:
- ❌ Agent loads with 0 tools
- ❌ Cannot search Jira
- ❌ Cannot post comments
- ❌ Fails to complete its mission
- ❌ System prompt updates are useless (can't call tools anyway)

**With Tools Discovered**:
- ✅ Agent has 30+ Jira tools available
- ✅ Can search for related tickets (using API v3, no deprecation errors)
- ✅ Can post enhancement comments
- ✅ System prompt anti-hallucination rules work (tools actually exist)
- ✅ Complete end-to-end workflow functional

---

## Next Steps

**IMMEDIATE ACTION REQUIRED**:

1. **Use Streamlit UI to trigger "Test Connection"** ← EASIEST
   OR
2. **Use API `/test-connection` endpoint** ← IF STREAMLIT DOWN
   OR
3. **Delete & recreate via API** ← CLEAN SLATE

2. **Verify tools discovered** (check database)

3. **Restart worker** (if needed):
```bash
docker-compose restart worker
```

4. **Trigger test execution** to verify agent works

5. **Monitor for**:
   - Tools loaded: 30+ (not 0)
   - Jira search calls work
   - Comments posted successfully
   - No API v2 deprecation errors

---

## Summary

✅ **MCP server configuration updated** (npx + API v3)
✅ **Status set to active**
✅ **Agent prompt updated** (anti-hallucination)
✅ **Worker restarted**
❌ **Tools NOT discovered** ← **BLOCKING ISSUE**

**One more step needed**: Trigger tool discovery via Streamlit UI "Test Connection" button.

Then the entire fix will be complete and the agent will work properly!
