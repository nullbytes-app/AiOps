# FAQ: Database Queries for Support

**Category:** FAQ - Support Tools
**Severity:** P3 (informational/training)
**Last Updated:** 2025-11-04
**Related Runbooks:** [Tenant Troubleshooting](../../operations/tenant-troubleshooting-guide.md)

---

## Quick Answer

**Support engineers query PostgreSQL database** for investigating ticket history, feedback trends, and tenant configurations. **CRITICAL: Always set `app.current_tenant_id` session variable** before queries to enforce Row-Level Security (RLS). Never query cross-tenant data without explicit authorization.

---

## Database Access

### Connecting to Database (Production)
```bash
# Get database connection string
kubectl get secret postgres-credentials -n ai-agents-production -o jsonpath='{.data.DATABASE_URL}' | base64 -d

# Connect to database
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- psql $DATABASE_URL

# Set tenant context (REQUIRED for all queries)
SET app.current_tenant_id = '<tenant-id>';
```

### RLS (Row-Level Security) Enforcement

**CRITICAL:** All tables enforce RLS policies. Queries without `app.current_tenant_id` session variable will return NO DATA (not an error, but empty result set).

**Example:**
```sql
-- WRONG: No session variable set, returns empty
SELECT * FROM ticket_history;
-- Returns: 0 rows

-- CORRECT: Session variable set, returns tenant's data
SET app.current_tenant_id = 'acme-corp';
SELECT * FROM ticket_history;
-- Returns: 150 rows for acme-corp tenant
```

---

## Common Support Queries

### 1. Check Ticket History Count for Client
```sql
SET app.current_tenant_id = '<tenant-id>';
SELECT COUNT(*) as total_tickets,
       COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved_tickets,
       MIN(created_at) as oldest_ticket,
       MAX(created_at) as newest_ticket
FROM ticket_history
WHERE tenant_id = '<tenant-id>';
```

**Use Case:** Diagnose low-quality enhancements (insufficient history)
**Expected:** >50 resolved tickets for good context

---

### 2. Query Client Feedback Trends (Last 7 Days)
```sql
SET app.current_tenant_id = '<tenant-id>';
SELECT
  DATE(created_at) as date,
  AVG(rating) as avg_rating,
  COUNT(*) as total_feedback,
  COUNT(CASE WHEN feedback_type = 'thumbs_up' THEN 1 END) as thumbs_up,
  COUNT(CASE WHEN feedback_type = 'thumbs_down' THEN 1 END) as thumbs_down
FROM enhancement_feedback
WHERE tenant_id = '<tenant-id>'
  AND created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

**Use Case:** Investigate quality issues or client satisfaction trends
**Expected:** avg_rating >4.0 for healthy client

---

### 3. Find Recent Low-Rated Enhancements
```sql
SET app.current_tenant_id = '<tenant-id>';
SELECT
  ticket_id,
  rating,
  feedback_type,
  comment,
  created_at
FROM enhancement_feedback
WHERE tenant_id = '<tenant-id>'
  AND (rating < 3 OR feedback_type = 'thumbs_down')
  AND created_at >= NOW() - INTERVAL '7 days'
ORDER BY created_at DESC
LIMIT 20;
```

**Use Case:** Identify specific problem tickets for quality investigation
**Next Step:** Review enhancement logs for these ticket_ids

---

### 4. Check Tenant Configuration
```sql
SET app.current_tenant_id = '<tenant-id>';
SELECT
  tenant_id,
  servicedesk_plus_url,
  webhook_secret IS NOT NULL as has_webhook_secret,
  openai_api_key IS NOT NULL as has_openai_key,
  max_workers,
  created_at,
  updated_at
FROM tenant_configs
WHERE tenant_id = '<tenant-id>';
```

**Use Case:** Verify tenant configuration during onboarding or troubleshooting
**Security:** webhook_secret and openai_api_key are hashed, only check if present (not actual values)

---

### 5. Find Tickets for Specific Time Range
```sql
SET app.current_tenant_id = '<tenant-id>';
SELECT
  ticket_id,
  subject,
  status,
  priority,
  created_at,
  resolved_at
FROM ticket_history
WHERE tenant_id = '<tenant-id>'
  AND created_at BETWEEN '2025-11-01' AND '2025-11-04'
ORDER BY created_at DESC
LIMIT 50;
```

**Use Case:** Investigate tickets during specific incident time window
**Example:** "Client says enhancements stopped working on Nov 3rd at 2pm"

---

### 6. Check Audit Log for Tenant Operations
```sql
SET app.current_tenant_id = '<tenant-id>';
SELECT
  action,
  resource_type,
  resource_id,
  user_id,
  ip_address,
  created_at
FROM audit_log
WHERE tenant_id = '<tenant-id>'
  AND created_at >= NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC
LIMIT 50;
```

**Use Case:** Security investigation or forensics (who did what when)
**Example:** "Who rotated the webhook secret yesterday?"

---

### 7. Count Knowledge Base Documents for Client
```sql
SET app.current_tenant_id = '<tenant-id>';
SELECT
  COUNT(*) as total_documents,
  AVG(LENGTH(content)) as avg_document_size,
  MIN(created_at) as oldest_doc,
  MAX(updated_at) as newest_update
FROM knowledge_base
WHERE tenant_id = '<tenant-id>';
```

**Use Case:** Diagnose low-quality enhancements (missing documentation)
**Expected:** >10 documents for good context

---

## RLS Policy Verification

### Test RLS Enforcement
```sql
-- Test 1: Query without session variable (should return empty)
SELECT COUNT(*) FROM ticket_history;
-- Expected: 0 rows (RLS blocks access)

-- Test 2: Set session variable and query (should return data)
SET app.current_tenant_id = 'acme-corp';
SELECT COUNT(*) FROM ticket_history;
-- Expected: >0 rows (RLS allows tenant's data)

-- Test 3: Try to query another tenant's data (should return empty)
SET app.current_tenant_id = 'client-a';
SELECT COUNT(*) FROM ticket_history WHERE tenant_id = 'client-b';
-- Expected: 0 rows (RLS prevents cross-tenant access)
```

---

## Using Feedback API (Alternative to Direct SQL)

### Query Feedback via REST API (Recommended)
```bash
# More user-friendly than SQL, respects RLS automatically

# Get feedback statistics
curl -H "Authorization: Bearer $TOKEN" \
  "https://api-url/api/v1/feedback/stats?tenant_id=<tenant>&start_date=2025-11-01&end_date=2025-11-04"

# Get individual feedback entries
curl -H "Authorization: Bearer $TOKEN" \
  "https://api-url/api/v1/feedback?tenant_id=<tenant>&start_date=2025-11-01&rating_lte=3&limit=20"
```

**Advantages:**
- No need to set session variable (API handles RLS)
- JSON response (easier to parse than SQL output)
- Rate limiting and authentication built-in
- Can be called from scripts/dashboards

**When to Use SQL Instead:**
- Need to join multiple tables (ticket_history + enhancement_feedback)
- Complex aggregations not supported by API
- Debugging database-specific issues

---

## Security Guidelines

### DO NOT:
- ❌ Query without setting `app.current_tenant_id`
- ❌ Query cross-tenant data (setting session variable for Tenant A, then querying Tenant B's data)
- ❌ Share query results containing sensitive data (webhook secrets, API keys) via Slack/email
- ❌ Modify data without Engineering authorization (`UPDATE`, `DELETE`, `INSERT`)
- ❌ Export large datasets without data privacy approval

### DO:
- ✅ Always set session variable before queries
- ✅ Limit query results (use `LIMIT` clause)
- ✅ Use read-only connection when available
- ✅ Anonymize feedback comments before sharing (remove names, IPs, sensitive details)
- ✅ Log all database access in audit trail (automatic via psql connection logging)

---

## Troubleshooting Database Access

### "psql: FATAL: password authentication failed"
```bash
# Database credentials may have been rotated
# Get new credentials from Kubernetes secret
kubectl get secret postgres-credentials -n ai-agents-production -o jsonpath='{.data.DATABASE_URL}' | base64 -d

# Or contact Engineering to reset credentials
```

### "Query returns 0 rows but should have data"
```bash
# Likely forgot to set session variable
# Verify:
SHOW app.current_tenant_id;
-- If empty or wrong tenant, set it:
SET app.current_tenant_id = '<correct-tenant-id>';
```

### "Permission denied for table"
```bash
# Support role should have SELECT permission on all tables
# If denied, escalate to Engineering (role permissions may need update)
```

---

## Training Resources

**New Support Team Members:**
1. Watch recorded training session (Story 5.6) - includes database query walkthrough
2. Practice queries on staging environment first
3. Memorize "Common Support Queries" above (print cheat sheet)
4. Always test RLS enforcement before trusting query results

**Best Practices:**
- Keep query templates in personal notes (with `<tenant-id>` placeholder)
- Use `\x` in psql for expanded display (easier to read)
- Use `EXPLAIN ANALYZE` for slow queries (share with Engineering)
- Document unusual findings in incident timeline

---

## Related Articles

- [FAQ: Low Quality Enhancements](faq-low-quality-enhancements.md) - Use ticket history count query
- [Troubleshooting: RLS Issues](troubleshooting-rls-issues.md) - RLS policy verification
- [Tenant Troubleshooting Guide](../../operations/tenant-troubleshooting-guide.md) - Complete tenant diagnostics

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-04 | Initial creation (Code Review follow-up) | Dev Agent (AI) |
