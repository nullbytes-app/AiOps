# Tenant Onboarding

**Last Updated:** 2025-11-03
**Author:** Amelia (Developer Agent)
**Related Alerts:** None (procedural, not alert-triggered)
**Severity:** Medium (business-critical, but not system emergency)

## Quick Links

- [Prerequisites](#prerequisites)
- [Onboarding Procedure](#onboarding-procedure)
- [Validation and Testing](#validation-and-testing)
- [Rollback Procedure](#rollback-procedure)
- [Post-Onboarding Checklist](#post-onboarding-checklist)
- [Troubleshooting](#troubleshooting)

---

## Overview

**When to Use This Runbook:**
- Adding new MSP customer to production platform
- Migrating tenant from staging to production
- Re-onboarding tenant after data restore or migration

**Scope:** Complete tenant onboarding workflow from database entry through webhook validation

**Prerequisites:**
- Kubernetes cluster admin or docker-compose access
- PostgreSQL write access
- Grafana admin access (for monitoring)
- ServiceDesk Plus instance information from customer
- Access to customer's ServiceDesk Plus admin panel (for webhook setup)

**Timeline:** 15-20 minutes for complete onboarding

---

## Prerequisites

### Information Required from Customer

Collect from customer BEFORE starting onboarding:

1. **ServiceDesk Plus Instance Details**
   - Fully qualified domain: `https://customer-instance.servicedeskplus.com`
   - API-enabled: Yes (verify in SDP → Admin → API)
   - Admin access: Available for webhook configuration

2. **API Credentials**
   - Service Desk Plus API Key (admin-level access)
   - Generate new key in SDP → Admin → API → API Keys
   - Verify permissions include: Read Tickets, Write Tickets, Read Work Notes

3. **Tenant Identifier**
   - Company/tenant name: "Acme Corporation"
   - Unique tenant_id: "acme-corp" (lowercase, no spaces, max 50 chars)
   - Will be used in database entries and Kubernetes resources

4. **Webhook Signature Secret**
   - Generate random webhook secret (min 32 chars): Use `openssl rand -hex 32`
   - Will be used to validate webhook requests from SDP

### Access Required

- [ ] Kubernetes cluster admin (or kubectl access to apply resources)
- [ ] PostgreSQL write access (psql client)
- [ ] ServiceDesk Plus admin console access (for webhook configuration)
- [ ] Grafana admin access (http://localhost:3000, admin credentials)
- [ ] Secure secret management (Kubernetes secrets or vault)

---

## Onboarding Procedure

### Step 1: Create Tenant Database Entry

**Docker:**
```bash
# Create tenant in PostgreSQL
docker-compose exec postgres psql -U aiagents -d ai_agents -c \
  "INSERT INTO tenants (tenant_id, name, created_at) VALUES
   ('acme-corp', 'Acme Corporation', NOW());"
```

**Kubernetes:**
```bash
# Create tenant in PostgreSQL
kubectl exec -it postgres-0 -- psql -U aiagents -d ai_agents -c \
  "INSERT INTO tenants (tenant_id, name, created_at) VALUES
   ('acme-corp', 'Acme Corporation', NOW());"
```

**Validation:**
```bash
# Verify tenant created
docker-compose exec postgres psql -U aiagents -d ai_agents -c \
  "SELECT * FROM tenants WHERE tenant_id = 'acme-corp';"

# Expected Output:
#  tenant_id  |       name       |         created_at
# -----------+-----------------+-----------------------
#  acme-corp | Acme Corporation | 2025-11-03 14:30:00
```

### Step 2: Configure ServiceDesk Plus API Credentials

**Docker - Create Secret:**
```bash
# Create Kubernetes secret with API credentials
kubectl create secret generic tenant-acme-corp-sdp \
  --from-literal=api_key="SDP_API_KEY_HERE" \
  --from-literal=webhook_secret="WEBHOOK_SECRET_HERE" \
  --namespace=default

# Or if using Docker only:
# Store in .env.local and reference in code
```

**Kubernetes - Create Secret:**
```bash
# Create secret for tenant
kubectl create secret generic tenant-acme-corp-sdp \
  --from-literal=api_key="SDP_API_KEY_HERE" \
  --from-literal=webhook_secret="WEBHOOK_SECRET_HERE"

# Verify secret created
kubectl get secret tenant-acme-corp-sdp
kubectl get secret tenant-acme-corp-sdp -o jsonpath='{.data.api_key}' | base64 -d
```

**Update Tenant Configuration in Database:**
```bash
# Docker
docker-compose exec postgres psql -U aiagents -d ai_agents -c \
  "UPDATE tenants SET
    sdp_url = 'https://acme-corp.servicedeskplus.com',
    sdp_credentials_secret = 'tenant-acme-corp-sdp',
    status = 'configured'
   WHERE tenant_id = 'acme-corp';"

# Kubernetes
kubectl exec -it postgres-0 -- psql -U aiagents -d ai_agents -c \
  "UPDATE tenants SET
    sdp_url = 'https://acme-corp.servicedeskplus.com',
    sdp_credentials_secret = 'tenant-acme-corp-sdp',
    status = 'configured'
   WHERE tenant_id = 'acme-corp';"
```

**Validation:**
```bash
# Verify configuration stored
docker-compose exec postgres psql -U aiagents -d ai_agents -c \
  "SELECT tenant_id, sdp_url, status FROM tenants WHERE tenant_id = 'acme-corp';"

# Expected:
#  tenant_id  |          sdp_url              | status
# -----------+-------------------------------+-----------
#  acme-corp | https://acme-corp.service... | configured
```

### Step 3: Test API Connectivity

**Docker:**
```bash
# Test API connectivity using secret
API_KEY=$(kubectl get secret tenant-acme-corp-sdp -o jsonpath='{.data.api_key}' | base64 -d)

docker-compose exec worker curl -i \
  https://acme-corp.servicedeskplus.com/api/v3/tickets \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json"

# Expected Output: HTTP 200 OK with ticket data
```

**Kubernetes:**
```bash
# Test from worker pod
kubectl exec -it deployment/celery-worker -- bash -c \
  'API_KEY=$(cat /var/run/secrets/tenant-acme-corp-sdp/api_key);
   curl -i https://acme-corp.servicedeskplus.com/api/v3/tickets \
   -H "Authorization: Bearer $API_KEY"'

# Expected: HTTP 200 OK
```

**Success Indicators:**
- HTTP 200 OK response
- JSON response with ticket list
- No "401 Unauthorized" errors

**If Test Fails:**
- Verify API key copied correctly (no extra spaces, truncation)
- Confirm customer ServiceDesk Plus instance URL
- Check if API is enabled in SDP admin console
- Verify customer's firewall allows API access

### Step 4: Configure ServiceDesk Plus Webhook

**Manual Setup in ServiceDesk Plus Admin Console:**

1. **Login to ServiceDesk Plus**
   - URL: `https://acme-corp.servicedeskplus.com`
   - Credentials: Customer provides

2. **Navigate to Webhooks**
   - Admin → Automation → Webhooks → Add Webhook
   - Or: Admin → Settings → Webhooks (varies by SDP version)

3. **Configure Webhook**
   - **Name:** "AI Agents Enhancement Bot"
   - **URL:** `https://your-platform.com/webhook/servicedesk?tenant_id=acme-corp`
   - **Replace `your-platform.com`** with your actual domain
   - **Trigger Event:** Select "On Ticket Creation" (new tickets)
   - Or add additional triggers: "On Ticket Status Change" if desired

4. **Security Configuration**
   - **Signature Method:** HMAC-SHA256
   - **Shared Secret:** Paste webhook_secret created in Step 2
   - **Signature Header:** `X-SDP-Signature`

5. **HTTP Configuration**
   - **Method:** POST
   - **Headers:** Content-Type: application/json
   - **Retry on Failure:** Enabled (3 retries recommended)
   - **Timeout:** 30 seconds

6. **Save Webhook**
   - Click "Save" and verify webhook is "Active"
   - Note the webhook ID for reference

### Step 5: Validate Webhook Delivery

**Create Test Ticket in ServiceDesk Plus:**

1. In ServiceDesk Plus, create new ticket:
   - Subject: "Test ticket for AI Agents integration"
   - Description: "This is a test ticket"
   - Category: (any category)
   - Click "Save"

2. **Check FastAPI Logs for Webhook Receipt:**

   **Docker:**
   ```bash
   # View API logs (last 30 seconds)
   docker-compose logs api --tail=100 | grep -i "POST /webhook\|acme-corp"

   # Expected Output:
   # api_1  | POST /webhook/servicedesk?tenant_id=acme-corp HTTP/1.1" 200
   ```

   **Kubernetes:**
   ```bash
   # View API pod logs
   kubectl logs -l app=api --tail=100 | grep -i "webhook\|acme-corp"

   # Expected: Log entry showing POST /webhook request
   ```

3. **Verify Enhancement Job Queued:**

   **Docker:**
   ```bash
   # Check queue depth increased
   docker-compose exec redis redis-cli LLEN enhancement_queue

   # Expected: Number increased from previous count (e.g., 1 new job)
   ```

   **Kubernetes:**
   ```bash
   # Check queue
   kubectl exec -it redis-0 -- redis-cli LLEN enhancement_queue
   ```

4. **Wait for Enhancement Processing (2-3 minutes):**

   **Monitor Worker Logs:**
   ```bash
   # Docker
   docker-compose logs worker --tail=50 | grep -i "acme-corp\|enhancement"

   # Kubernetes
   kubectl logs -f -l app=celery-worker | grep acme-corp
   ```

5. **Verify Ticket Updated in ServiceDesk Plus:**

   - Refresh ServiceDesk Plus ticket in browser
   - Check "Work Notes" section for enhancement content
   - Expected: AI-generated enhancement summary added to ticket

### Step 6: Add Tenant to Grafana Monitoring

**Kubernetes:**
```bash
# Create Grafana dashboard variable for tenant filtering
# If using dashboard provisioning, add tenant to dashboard filters

# Verify tenant metrics visible
kubectl exec -it prometheus-0 -- promtool query instant \
  'enhancement_requests_total{tenant_id="acme-corp"}'

# Expected: Metric visible in Prometheus (may be 0 if no traffic yet)
```

**Docker:**
```bash
# Check metrics in Prometheus UI
curl -s http://localhost:9090/api/v1/query \
  --data-urlencode 'query=enhancement_requests_total{tenant_id="acme-corp"}'

# Expected: JSON response with metric (may have 0 value)
```

---

## Validation and Testing

### Comprehensive Validation Checklist

- [ ] **Database:** Tenant entry exists with correct configuration
- [ ] **Secrets:** Kubernetes secret created with API key and webhook secret
- [ ] **API Connectivity:** Test curl call to SDP API succeeds
- [ ] **Webhook:** Test ticket created in SDP reaches platform (logs show receipt)
- [ ] **Enhancement Processing:** Worker processes webhook and generates enhancement
- [ ] **Grafana:** Tenant_id appears in metrics/dashboards
- [ ] **Status:** Tenant status = 'active' in database

### Test Scenario: Full Enhancement Workflow

1. **Create test ticket in customer's ServiceDesk Plus**
   - Subject: "Test enhancement request"
   - Include relevant details for AI enhancement

2. **Wait 2-3 minutes for processing**

3. **Verify enhancement in ticket work notes**
   - Open ticket in SDP
   - Check "Work Notes" for AI-generated content
   - Verify quality and format of enhancement

4. **Monitor metrics in Grafana**
   - Check enhancement_requests_total for tenant (should increment)
   - Verify success_rate (should be 100% if tests successful)
   - Check latency (should be <60s)

---

## Rollback Procedure

### If Webhook Not Responding or Causing Issues

**Option 1 - Disable Webhook in ServiceDesk Plus (Fast):**

1. Login to ServiceDesk Plus admin console
2. Admin → Webhooks → Find "AI Agents Enhancement Bot"
3. Click "Disable" or "Delete"
4. Save changes

**Option 2 - Delete Tenant from Platform (If Complete Rollback Needed):**

**Docker:**
```bash
# Delete tenant from database
docker-compose exec postgres psql -U aiagents -d ai_agents -c \
  "DELETE FROM tenants WHERE tenant_id = 'acme-corp';"

# Delete Kubernetes secret
kubectl delete secret tenant-acme-corp-sdp

# Verify deleted
docker-compose exec postgres psql -U aiagents -d ai_agents -c \
  "SELECT * FROM tenants WHERE tenant_id = 'acme-corp';"

# Expected: No rows returned
```

**Kubernetes:**
```bash
# Delete tenant configuration
kubectl exec -it postgres-0 -- psql -U aiagents -d ai_agents -c \
  "DELETE FROM tenants WHERE tenant_id = 'acme-corp';"

# Delete secret
kubectl delete secret tenant-acme-corp-sdp

# Verify
kubectl get secret tenant-acme-corp-sdp  # Should show "not found"
```

---

## Post-Onboarding Checklist

### Immediate (Day 1)

- [ ] Customer confirms enhancement quality is acceptable
- [ ] Monitor dashboard for 24 hours - alert on failures
- [ ] Document tenant configuration in internal wiki

### Short-Term (Within 1 Week)

- [ ] Schedule 1-week follow-up call with customer
- [ ] Review enhancement success rate and latency
- [ ] Gather customer feedback on enhancement quality
- [ ] Identify any SDP-specific customizations needed

### Medium-Term (Within 30 Days)

- [ ] Quarterly metrics review with customer (success rate, processing time)
- [ ] Add tenant to quarterly review list (for ongoing monitoring)
- [ ] Performance optimization if latency high

### Ongoing

- [ ] Monitor tenant metrics in Grafana dashboard
- [ ] Alert on failures (high error rate, webhook failures)
- [ ] Update contact information if SDP credentials change

---

## Troubleshooting

### Common Issues and Solutions

#### Issue: Webhook Not Received (No logs in API)

**Diagnosis:**
```bash
# Verify webhook configured correctly in SDP
# Check: URL, tenant_id parameter, signature secret, method=POST

# Test webhook from command line (simulate SDP)
curl -X POST https://your-platform.com/webhook/servicedesk?tenant_id=acme-corp \
  -H "Content-Type: application/json" \
  -d '{"ticket_id":"TEST-123"}'

# Expected: 200 OK response
```

**Solutions:**
1. Verify customer's firewall allows HTTPS to your platform
2. Check firewall rules on your infrastructure (allow SDP IP range)
3. Verify URL correct: No typos, includes `/webhook/servicedesk` path
4. Confirm webhook "Active" status in SDP admin console
5. Test webhook with simple request (SDP → Test Webhook option)

#### Issue: API Authentication Fails (401 Unauthorized)

**Diagnosis:**
```bash
# Verify API key format and permissions
curl -H "Authorization: Bearer WRONG_KEY" https://sdp/api/v3/tickets | head
# Should show 401 error

# Verify correct API key
curl -H "Authorization: Bearer CORRECT_KEY" https://sdp/api/v3/tickets | head
# Should show 200 with data
```

**Solutions:**
1. Verify API key copied exactly (check for spaces, truncation)
2. Confirm API key has correct permissions in SDP (Read/Write Tickets)
3. Generate new API key in SDP if old one may be revoked
4. Update Kubernetes secret with new key, restart workers

#### Issue: Row-Level Security Blocks Access

**Symptom:** Enhancement fails with "new row violates row-level security policy"

**Diagnosis:**
```bash
# Check if tenant row exists
docker-compose exec postgres psql -U aiagents -d ai_agents -c \
  "SELECT * FROM tenants WHERE tenant_id = 'acme-corp';"

# If exists, check RLS policy on tickets table
docker-compose exec postgres psql -U aiagents -d ai_agents -c \
  "\d+ tickets"  # Look for Policies section
```

**Solution:**
1. Verify tenant_id in database matches tenant_id in webhook URL
2. Check RLS policy uses correct column to filter (should be tenant_id)
3. Verify application sets `app.current_tenant_id` context before queries
4. Escalate to engineering if RLS policy issue

#### Issue: Webhook Received But Ticket Not Updated

**Symptom:** Logs show webhook received, but no enhancement in SDP ticket

**Diagnosis:**
```bash
# Check if job queued
docker-compose exec redis redis-cli LLEN enhancement_queue

# Check worker logs for errors
docker-compose logs worker --tail=200 | grep -i "acme-corp\|error"

# Verify SDP update credentials have write permission
# (from Step 3, re-test with same API key)
```

**Solutions:**
1. Verify worker pods are running: `kubectl get pods -l app=celery-worker`
2. Check if API credentials have "Write Tickets" permission in SDP
3. Review worker logs for specific error (credential, permission, timeout)
4. If API write permission issue, regenerate API key with admin role

#### Issue: Enhancement Processing Slow (>2 minutes)

**Diagnosis:**
```bash
# Check queue depth - is processing backed up?
docker-compose exec redis redis-cli LLEN enhancement_queue

# Check worker count
kubectl get pods -l app=celery-worker

# Check recent processing time in distributed traces
# (See Distributed Tracing section in [API Timeout Runbook](./api-timeout.md))
```

**Solutions:**
1. If queue depth high: Scale workers (`kubectl scale deployment/celery-worker --replicas=4`)
2. If single worker slow: Check logs for errors
3. If SDP API slow: Check customer's SDP performance (contact customer)
4. If OpenAI slow: Check API status at https://status.openai.com

---

## Related Documentation

- **[High Queue Depth Runbook](./high-queue-depth.md)** - If processing backed up after onboarding
- **[API Timeout Runbook](./api-timeout.md)** - If SDP or OpenAI APIs slow
- **[Database Connection Issues Runbook](./database-connection-issues.md)** - If database connectivity issues
- **[Distributed Tracing Setup](../operations/distributed-tracing-setup.md)** - For performance analysis of enhancements
- **[Grafana Dashboards](../operations/grafana-setup.md)** - Monitoring tenant metrics

---

**Status:** ✅ Complete with comprehensive troubleshooting guide
**Test Status:** Awaiting team member validation (Task 10)
**Last Review:** 2025-11-03
