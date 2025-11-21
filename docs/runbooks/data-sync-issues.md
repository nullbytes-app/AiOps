# Runbook: Data Sync Issues

**Objective:** Diagnose and resolve missing or stale data in the Next.js UI

**Severity:** Medium-High (affects data accuracy and decision-making)

**Estimated Time:** 10-30 minutes

---

## Prerequisites

Before starting, ensure you have:
- [ ] User's tenant ID
- [ ] User's role (super_admin, tenant_admin, operator, developer, viewer)
- [ ] Access to PostgreSQL database
- [ ] Access to Redis cache
- [ ] Access to FastAPI logs
- [ ] Browser DevTools (Network tab)

---

## Common Scenarios

| Issue | Symptom | Root Cause | Solution |
|-------|---------|------------|----------|
| **Missing Agents** | Agent list empty, but data exists in DB | Wrong tenant context | Verify tenant switcher, check RLS session variable |
| **Stale Metrics** | Dashboard shows old data (> 5 min old) | Cache not invalidating | Clear Redis cache, check polling interval |
| **403 Forbidden** | "You don't have permission to view this" | Wrong role for current tenant | Check user_tenant_roles, verify RBAC middleware |
| **Execution Missing** | Recent execution not in history | Polling not enabled | Enable real-time polling, check API filters |
| **Data Discrepancy** | Different data in Streamlit vs Next.js | Cache inconsistency | Clear browser cache + Redis cache |

---

## Decision Tree

```
Data is missing or incorrect
├── Wrong Tenant Context
│   ├── User viewing Tenant A, data belongs to Tenant B
│   ├── Tenant switcher shows wrong tenant
│   └── Solution: Switch tenant, verify session variable
│
├── Permission Issue (RBAC)
│   ├── User has "viewer" role, trying to edit
│   ├── API returns 403 Forbidden
│   └── Solution: Check user_tenant_roles, verify permissions
│
├── Stale Cache
│   ├── Data updated in DB, not reflected in UI
│   ├── Redis cache not invalidated
│   └── Solution: Clear Redis cache, check TTL
│
├── API Filter Wrong
│   ├── User filtered by "failed" status, but looking for "success"
│   ├── Date range too narrow
│   └── Solution: Clear filters, expand date range
│
└── Database Issue
    ├── Row-Level Security blocking query
    ├── Data actually missing in DB
    └── Solution: Check RLS session variable, verify data
```

---

## Step-by-Step Troubleshooting

### Issue 1: Missing Data Due to Wrong Tenant Context

**Symptoms:**
- Agent list shows "No agents yet" but user has agents
- Dashboard metrics all show 0
- User recently switched tenants

**Diagnosis:**
1. **Check Current Tenant in UI:**
   - Look at tenant switcher dropdown (top-right header)
   - Verify correct tenant selected

2. **Check Network Requests:**
   ```
   DevTools → Network → XHR/Fetch
   Click on: GET /api/v1/agents
   Headers → tenant_id: "tenant-abc"  # Should match expected tenant
   ```

3. **Check Database (Verify Data Exists):**
   ```sql
   -- Check if agents exist for this tenant
   SELECT COUNT(*) FROM agents WHERE tenant_id = 'tenant-abc';
   -- If > 0: Data exists, issue is tenant context
   -- If = 0: Data actually missing
   ```

**Solution:**

**A. User Selected Wrong Tenant:**
1. Click tenant switcher (top-right dropdown)
2. Search for correct tenant name
3. Select correct tenant
4. UI refreshes with correct data

**B. Tenant Context Not Set in API:**
```python
# src/api/dependencies.py
async def get_tenant_db(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> AsyncSession:
    tenant_id = request.state.tenant_id  # From JWT or header
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID missing")

    # Set PostgreSQL session variable for RLS
    await db.execute(text(f"SELECT set_tenant_context('{tenant_id}')"))
    return db
```

**C. Check Row-Level Security:**
```sql
-- Check if RLS session variable set
SELECT current_setting('app.current_tenant_id', true);
-- Should return: tenant_id (e.g., 'tenant-abc')
-- If NULL: RLS session variable not set → no data returned

-- Test query manually
SELECT set_tenant_context('tenant-abc');
SELECT * FROM agents;  -- Should return agents for tenant-abc
```

**Verification:**
```bash
# API call should return data
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8000/api/v1/agents?tenant_id=tenant-abc"

# Should return: { "agents": [ {...}, {...} ] }
# NOT: { "agents": [] }
```

---

### Issue 2: Permission Denied (403 Forbidden)

**Symptoms:**
- Error: "You don't have permission to view this resource"
- API returns 403 status code
- User has viewer role, trying to edit agent

**Diagnosis:**
1. **Check User's Role for Current Tenant:**
   ```
   DevTools → Network → GET /api/v1/users/me/role?tenant_id=tenant-abc
   Response: { "role": "viewer" }
   ```

2. **Check Permission Matrix:**
   | Action | Super Admin | Tenant Admin | Operator | Developer | Viewer |
   |--------|-------------|--------------|----------|-----------|--------|
   | View Agents | ✅ | ✅ | ✅ | ✅ | ✅ |
   | Edit Agents | ✅ | ✅ | ❌ | ✅ | ❌ |
   | Delete Agents | ✅ | ✅ | ❌ | ❌ | ❌ |

3. **Verify in Database:**
   ```sql
   SELECT role FROM user_tenant_roles
   WHERE user_id = '<user-id>' AND tenant_id = 'tenant-abc';
   -- Returns: viewer, operator, developer, tenant_admin, or super_admin
   ```

**Solution:**

**A. User Has Wrong Role (Need Role Change):**
```sql
-- Update user's role for this tenant (requires super_admin)
UPDATE user_tenant_roles
SET role = 'operator'  -- Change viewer → operator
WHERE user_id = '<user-id>' AND tenant_id = 'tenant-abc';
```

**B. User Belongs to Wrong Tenant:**
```sql
-- Check which tenants user has access to
SELECT tenant_id, role FROM user_tenant_roles WHERE user_id = '<user-id>';
```

If user should access different tenant:
1. Switch to correct tenant via tenant switcher
2. Verify role for that tenant

**C. User Missing Role Assignment:**
```sql
-- Assign role to user for tenant (requires super_admin)
INSERT INTO user_tenant_roles (user_id, tenant_id, role)
VALUES ('<user-id>', 'tenant-abc', 'operator');
```

**Verification:**
```bash
# Get user's role for tenant
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8000/api/v1/users/me/role?tenant_id=tenant-abc"

# Should return: { "role": "operator" }

# Try edit action (should now succeed)
curl -X PUT -H "Authorization: Bearer <token>" \
     "http://localhost:8000/api/v1/agents/<agent-id>" \
     -d '{"name": "Updated Agent"}'

# Should return: 200 OK (not 403 Forbidden)
```

---

### Issue 3: Stale Data (Cache Not Invalidating)

**Symptoms:**
- Dashboard shows metrics from 10 minutes ago
- User created new agent, not visible in agent list
- Manual browser refresh doesn't help

**Diagnosis:**
1. **Check Polling Interval:**
   ```typescript
   // src/hooks/useDashboardMetrics.ts
   const { data } = useQuery({
     queryKey: ['dashboard-metrics', tenantId],
     queryFn: fetchMetrics,
     refetchInterval: 5000,  // Should be 5000 (5 seconds)
   });
   ```

2. **Check Redis Cache:**
   ```bash
   # Check if cache key exists
   docker exec -it ai-agents-redis redis-cli
   > KEYS metrics:dashboard:*
   > TTL metrics:dashboard:tenant-abc
   # Should return: time remaining (e.g., 25 seconds)
   # If -1: Cache never expires (BUG)
   ```

3. **Check API Response Headers:**
   ```
   DevTools → Network → GET /api/v1/metrics/summary
   Response Headers:
     X-Cache: HIT  # Data from cache
     Cache-Control: max-age=30
   ```

**Solution:**

**A. Clear Redis Cache (Immediate Fix):**
```bash
# Clear all dashboard metrics cache
docker exec -it ai-agents-redis redis-cli
> DEL metrics:dashboard:tenant-abc
> DEL metrics:agents:tenant-abc

# Or flush all cache (CAUTION: affects all users)
> FLUSHDB
```

**B. Fix Cache TTL (Permanent Fix):**
```python
# src/services/metrics_service.py
async def get_dashboard_metrics(tenant_id: str):
    cache_key = f"metrics:dashboard:{tenant_id}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    metrics = await fetch_from_db(tenant_id)

    # Cache for 30 seconds (was: 300 seconds / 5 minutes)
    await redis_client.setex(cache_key, 30, json.dumps(metrics))
    return metrics
```

**C. Invalidate Cache on Mutations:**
```typescript
// src/lib/api/agents.ts
export const createAgent = useMutation({
  mutationFn: (data: AgentCreate) => axios.post('/api/v1/agents', data),
  onSuccess: () => {
    // Invalidate agents list cache
    queryClient.invalidateQueries({ queryKey: ['agents', tenantId] });
  },
});
```

**Verification:**
```bash
# Check cache expiration
docker exec -it ai-agents-redis redis-cli TTL metrics:dashboard:tenant-abc
# Should return: 30 or less (expires in 30 seconds)

# Wait 30 seconds, check cache again
docker exec -it ai-agents-redis redis-cli TTL metrics:dashboard:tenant-abc
# Should return: -2 (key doesn't exist, expired)

# Fetch API, verify fresh data
curl "http://localhost:8000/api/v1/metrics/summary?tenant_id=tenant-abc"
```

---

### Issue 4: Data Not Appearing in Execution History

**Symptoms:**
- User executed agent 5 minutes ago
- Execution not visible in execution history page
- User checked "All statuses" filter

**Diagnosis:**
1. **Check Filters:**
   ```
   DevTools → Network → GET /api/v1/executions
   Query params:
     status=success  # User may have filtered by status
     date_from=2025-01-15  # Date range may be too narrow
     agent_id=xxx  # Agent filter may exclude this execution
   ```

2. **Check Polling:**
   ```typescript
   // Execution history should poll every 10 seconds
   const { data } = useQuery({
     queryKey: ['executions', filters],
     queryFn: fetchExecutions,
     refetchInterval: 10000,  # Should be enabled
   });
   ```

3. **Verify Execution in Database:**
   ```sql
   SELECT id, agent_id, status, created_at
   FROM agent_executions
   WHERE tenant_id = 'tenant-abc'
   ORDER BY created_at DESC
   LIMIT 10;
   ```

**Solution:**

**A. Clear All Filters:**
1. Click "Clear filters" button
2. Set date range to "Last 7 days"
3. Set status to "All statuses"
4. Click "Search"

**B. Manual Refresh:**
1. Click refresh icon (top-right of table)
2. Or press `Cmd+R` / `Ctrl+R` to reload page

**C. Enable Polling (if disabled):**
```typescript
// src/hooks/useExecutions.ts
const { data, refetch } = useQuery({
  queryKey: ['executions', filters],
  queryFn: () => fetchExecutions(filters),
  refetchInterval: 10000,  // Enable 10s polling
  enabled: true,  // Ensure query enabled
});
```

**Verification:**
```bash
# Check if execution exists
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8000/api/v1/executions?tenant_id=tenant-abc&limit=10"

# Should include recent execution:
# {
#   "executions": [
#     { "id": "exec-123", "agent_id": "agent-456", "status": "success", "created_at": "2025-01-20T10:30:00Z" }
#   ]
# }
```

---

### Issue 5: Discrepancy Between Streamlit and Next.js

**Symptoms:**
- Streamlit shows 10 agents
- Next.js shows 8 agents
- User confused which is correct

**Diagnosis:**
1. **Check Source of Truth (Database):**
   ```sql
   SELECT COUNT(*) FROM agents WHERE tenant_id = 'tenant-abc';
   -- This is the truth (e.g., returns 10)
   ```

2. **Check Streamlit Data:**
   - Log into Streamlit UI at `/admin-legacy`
   - Navigate to Agent Management
   - Count agents displayed

3. **Check Next.js Data:**
   - Log into Next.js UI at `/agents`
   - Count agents displayed
   - Check if pagination hiding some agents (scroll to see all pages)

**Solution:**

**A. Next.js Has Stale Cache:**
```bash
# Clear browser cache
Cmd+Shift+Delete → Clear cookies and site data

# Clear Redis cache
docker exec -it ai-agents-redis redis-cli FLUSHDB

# Force re-fetch in UI
Cmd+Shift+R (hard refresh)
```

**B. Next.js Has Filters Applied:**
- Check if status filter set to "Active" (may hide "Inactive" agents)
- Clear search box
- Set pagination to "Show all"

**C. Streamlit Has Old Cache:**
- Streamlit caches data for longer (no polling)
- Click "Rerun" button in Streamlit
- Or restart Streamlit container

**Verification:**
```sql
-- Count should match across all UIs
SELECT COUNT(*) FROM agents WHERE tenant_id = 'tenant-abc';
-- e.g., Returns: 10

-- Streamlit should show: 10 agents
-- Next.js should show: 10 agents (across all pages)
```

---

## Data Consistency Checks

### Quick Validation Script
```sql
-- Run these queries to verify data consistency

-- 1. Count agents per tenant
SELECT tenant_id, COUNT(*) as agent_count
FROM agents
GROUP BY tenant_id
ORDER BY tenant_id;

-- 2. Count executions per tenant (last 24 hours)
SELECT tenant_id, COUNT(*) as execution_count
FROM agent_executions
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY tenant_id
ORDER BY tenant_id;

-- 3. Check user-tenant-role assignments
SELECT u.email, utr.tenant_id, utr.role
FROM users u
JOIN user_tenant_roles utr ON u.id = utr.user_id
ORDER BY u.email, utr.tenant_id;

-- 4. Check for orphaned data (agent without tenant)
SELECT COUNT(*) as orphaned_agents
FROM agents a
LEFT JOIN tenant_configs tc ON a.tenant_id = tc.tenant_id
WHERE tc.tenant_id IS NULL;
```

---

## Diagnostic Commands

```bash
# Check tenant context in PostgreSQL session
docker exec -it ai-agents-postgres psql -U aiagents -d ai_agents -c \
  "SELECT current_setting('app.current_tenant_id', true);"

# Check user's roles across all tenants
docker exec -it ai-agents-postgres psql -U aiagents -d ai_agents -c \
  "SELECT tenant_id, role FROM user_tenant_roles WHERE user_id = '<user-id>';"

# Check Redis cache keys
docker exec -it ai-agents-redis redis-cli KEYS "*"

# Check Redis cache TTL for specific key
docker exec -it ai-agents-redis redis-cli TTL "metrics:dashboard:tenant-abc"

# Clear specific Redis cache key
docker exec -it ai-agents-redis redis-cli DEL "metrics:dashboard:tenant-abc"

# Check API response (with auth token)
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8000/api/v1/agents?tenant_id=tenant-abc"

# Check API logs for errors
docker logs ai-agents-api --tail 100 | grep -i "error\|exception"
```

---

## Common Cache Keys

| Cache Key Pattern | Purpose | TTL |
|-------------------|---------|-----|
| `metrics:dashboard:{tenant_id}` | Dashboard metrics | 30s |
| `metrics:agents:{tenant_id}` | Agent performance metrics | 60s |
| `llm-costs:{tenant_id}:{date}` | LLM cost summary | 1h |
| `tenant-config:{tenant_id}` | Tenant configuration | 5m |
| `revoked:{token_hash}` | Revoked JWT tokens | Token expiry |

To clear all cache for a tenant:
```bash
docker exec -it ai-agents-redis redis-cli KEYS "*tenant-abc*" | xargs redis-cli DEL
```

---

## Escalation

If issue persists after following this runbook:

1. **Collect Diagnostic Data:**
   - User's tenant ID and role
   - Database query results (agent count, execution count)
   - Redis cache dump (`redis-cli KEYS "*tenant-id*"`)
   - API response (curl output)
   - Browser console errors

2. **Contact:**
   - **Database Team:** Slack #database-support
   - **Backend Team:** Slack #backend-support
   - **On-Call Engineer:** PagerDuty escalation

3. **Temporary Workaround:**
   - Advise user to use Streamlit UI temporarily (`/admin-legacy`)
   - Provide direct database query results
   - Manual data export (CSV)

---

**Last Updated:** January 2025
**Version:** 1.0
**Owner:** Operations Team
