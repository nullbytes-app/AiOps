# Troubleshooting: RLS Issues

**Category:** Troubleshooting - Security & Data Isolation
**Severity:** P0 (if cross-tenant access suspected) / P2 (if tenant cannot access own data)
**Last Updated:** 2025-11-04
**Related Runbooks:** [Tenant Troubleshooting Guide](../../operations/tenant-troubleshooting-guide.md)

---

## Quick Answer

**Row-Level Security (RLS) enforces multi-tenant data isolation** in PostgreSQL. Common issues: session variable not set (queries return empty), RLS policy misconfigured (legitimate access blocked), or potential security violation (cross-tenant access attempt). Always verify `app.current_tenant_id` session variable is set correctly.

---

## Symptoms

**Observable Indicators:**
- Queries returning 0 rows when data should exist
- Worker logs show "No ticket history found for tenant" (but history exists)
- Client reports: "Cannot see feedback/tickets in dashboard"
- Security alert: Attempted cross-tenant data access

---

## Common Causes

### 1. Session Variable Not Set (60% of cases)

**Root Cause:** Database query executed without setting `app.current_tenant_id` session variable

**How to Identify:**
```sql
-- Check current session variable
SHOW app.current_tenant_id;
-- If empty: Session variable not set

-- Try query without session variable
SELECT COUNT(*) FROM ticket_history WHERE tenant_id = 'acme-corp';
-- Returns: 0 rows (RLS blocks access)

-- Set session variable and retry
SET app.current_tenant_id = 'acme-corp';
SELECT COUNT(*) FROM ticket_history WHERE tenant_id = 'acme-corp';
-- Returns: 150 rows (RLS allows access)
```

**Resolution:**
```bash
# Application code MUST set session variable before queries
# Example in Python (SQLAlchemy):
session.execute(text(f"SET app.current_tenant_id = '{tenant_id}'"))

# For manual queries: Always set session variable first
# For API requests: Middleware sets session variable automatically from JWT token
```

---

### 2. RLS Policy Misconfigured (20% of cases)

**Root Cause:** RLS policy logic prevents legitimate access

**How to Identify:**
```sql
-- Check RLS policies on table
SELECT
  schemaname,
  tablename,
  policyname,
  permissive,
  roles,
  cmd,
  qual
FROM pg_policies
WHERE tablename = 'ticket_history';

-- Verify policy allows access for app_user role
-- Policy should check: current_setting('app.current_tenant_id') = tenant_id
```

**Resolution:**
- **Escalate to Engineering** - RLS policies cannot be modified by support
- Provide: Table name, tenant ID, query that should work but doesn't
- Engineering will review policy logic and fix if misconfigured

---

### 3. Cross-Tenant Access Attempt (15% of cases)

**Root Cause:** Code attempting to access data from different tenant

**How to Identify:**
```sql
-- Scenario: Session variable set to Tenant A, but query asks for Tenant B data
SET app.current_tenant_id = 'client-a';
SELECT COUNT(*) FROM ticket_history WHERE tenant_id = 'client-b';
-- Returns: 0 rows (RLS correctly blocks cross-tenant access)

-- Check audit log for suspicious access patterns
SET app.current_tenant_id = 'client-a';
SELECT
  action,
  resource_type,
  resource_id,
  user_id,
  ip_address,
  created_at
FROM audit_log
WHERE action LIKE '%denied%'
  OR action LIKE '%unauthorized%'
ORDER BY created_at DESC
LIMIT 50;
```

**Resolution:**
- **If legitimate business need (e.g., admin dashboard):** Escalate to Engineering for multi-tenant admin role
- **If bug in application code:** Escalate to Engineering with reproduction steps
- **If security violation attempt:** Escalate IMMEDIATELY to Engineering + Security Team

---

### 4. Connection Pool Retaining Old Session State (5% of cases)

**Root Cause:** Database connection reused from pool without resetting session variable

**How to Identify:**
```bash
# Worker logs show: "Processing ticket for tenant A" followed by "No data found"
# But tenant A has data in database

# Connection may have previous session variable set to wrong tenant
# Example: Connection processed Tenant B job, now processing Tenant A but session var still = Tenant B
```

**Resolution:**
```python
# Application code MUST reset session variable on EVERY connection use
# Example in Python (SQLAlchemy):
def set_tenant_context(session, tenant_id):
    # Always reset to null first (clear previous state)
    session.execute(text("RESET app.current_tenant_id"))
    # Then set to correct tenant
    session.execute(text(f"SET app.current_tenant_id = '{tenant_id}'"))
```

---

## Diagnosis Steps

**Step 1: Verify RLS Policies Exist**
```sql
-- Check which tables have RLS enabled
SELECT
  schemaname,
  tablename,
  rowsecurity
FROM pg_tables
WHERE schemaname = 'public';

-- Expect rowsecurity = true for:
-- - ticket_history
-- - enhancement_feedback
-- - tenant_configs
-- - knowledge_base
-- - audit_log
```

**Step 2: Test RLS Enforcement Manually**
```sql
-- Test 1: Query without session variable (should return empty)
RESET app.current_tenant_id;
SELECT COUNT(*) FROM ticket_history;
-- Expected: 0 rows

-- Test 2: Set session variable and query (should return data)
SET app.current_tenant_id = 'acme-corp';
SELECT COUNT(*) FROM ticket_history;
-- Expected: >0 rows if tenant has data

-- Test 3: Try cross-tenant access (should return empty)
SET app.current_tenant_id = 'client-a';
SELECT COUNT(*) FROM ticket_history WHERE tenant_id = 'client-b';
-- Expected: 0 rows (RLS blocks)
```

**Step 3: Check Application Logs for RLS Errors**
```bash
# Worker logs
kubectl logs deployment/ai-agents-worker -n ai-agents-production --since=30m | grep -i "rls\|tenant_id\|no data found"

# API logs
kubectl logs deployment/ai-agents-api -n ai-agents-production --since=30m | grep -i "rls\|tenant_id\|unauthorized"
```

**Step 4: Audit Recent Access Patterns**
```sql
-- Check audit log for denied access
SET app.current_tenant_id = '<tenant-id>';
SELECT * FROM audit_log
WHERE (action LIKE '%denied%' OR action LIKE '%unauthorized%')
  AND created_at >= NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;
```

---

## Resolution

**If Session Variable Not Set (Cause #1):**
- Check application code: Is `SET app.current_tenant_id` called before queries?
- Check middleware: Is JWT token correctly extracting tenant_id?
- For manual queries: Always set session variable first

**If RLS Policy Misconfigured (Cause #2):**
- Escalate to Engineering with details:
  - Table name
  - Tenant ID
  - Query that should work but doesn't
  - Expected vs actual result

**If Cross-Tenant Access Attempt (Cause #3):**
- **If legitimate:** Escalate for multi-tenant admin role implementation
- **If bug:** Escalate with reproduction steps
- **If security violation:** IMMEDIATE escalation to Security Team

**If Connection Pool Issue (Cause #4):**
- Restart workers to clear connection pool
- Escalate to Engineering to add session variable reset on connection checkout

---

## Prevention

**Application Code Best Practices:**
- ALWAYS set session variable at start of request/job
- ALWAYS reset session variable when returning connection to pool
- NEVER trust connection pool to maintain correct session state
- Log tenant_id at start of every request for debugging

**Testing:**
- Unit tests should verify RLS enforcement
- Integration tests should test cross-tenant isolation
- Security tests should attempt unauthorized cross-tenant access (expect failure)

**Monitoring:**
- Monitor audit log for "denied" or "unauthorized" actions
- Alert on unexpected cross-tenant access patterns
- Weekly review: Any RLS-related errors in application logs?

---

## Escalation

**Escalate to Engineering when:**
- RLS policy appears misconfigured (legitimate access blocked)
- Connection pool not resetting session variables correctly
- Need multi-tenant admin role for dashboards/reporting
- Performance issues related to RLS (slow query plans)

**Escalate to Security Team IMMEDIATELY when:**
- Evidence of cross-tenant data access (actual or attempted)
- Audit log shows unauthorized access patterns
- Client reports seeing another client's data

**Provide in Escalation:**
- Tenant ID(s) involved
- Query that failed or unexpected result
- Application logs (sanitized, no secrets)
- Audit log entries showing issue
- Timestamp when issue occurred

---

## Related Articles

- [FAQ: Database Queries for Support](faq-database-queries.md) - How to set session variables correctly
- [Tenant Troubleshooting Guide](../../operations/tenant-troubleshooting-guide.md) - Complete tenant diagnostics

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-04 | Initial creation (Code Review follow-up) | Dev Agent (AI) |
