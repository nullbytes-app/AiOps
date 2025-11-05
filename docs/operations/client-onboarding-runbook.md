# Client Onboarding Runbook

**Version:** 1.0
**Last Updated:** 2025-11-03
**Owner:** Operations Team
**Status:** Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Onboarding Workflow](#onboarding-workflow)
4. [Step-by-Step Procedures](#step-by-step-procedures)
5. [Validation Checklist](#validation-checklist)
6. [Rollback Procedures](#rollback-procedures)
7. [Troubleshooting](#troubleshooting)
8. [Post-Onboarding](#post-onboarding)
9. [References](#references)

---

## Overview

### Purpose

This runbook provides comprehensive procedures for onboarding new MSP clients to the AI Agents Ticket Enhancement Platform. It follows AWS Well-Architected SaaS Lens principles for frictionless tenant provisioning while ensuring security, isolation, and operational excellence.

### Scope

- Multi-tenant client provisioning
- ServiceDesk Plus integration configuration
- Row-Level Security (RLS) validation
- Kubernetes namespace management (tier-based)
- End-to-end validation testing

### Architecture Context

The platform uses a **pool-based multi-tenant architecture** with:
- **Shared infrastructure:** Single Kubernetes cluster, PostgreSQL database, Redis queue
- **Tenant isolation:** PostgreSQL Row-Level Security (RLS) enforces data boundaries
- **Tier-based provisioning:** Basic (shared namespace + RLS) vs Premium (dedicated namespace + RLS + resource quotas)

### Estimated Time

- **Basic Tier Client:** 2-3 hours (shared infrastructure)
- **Premium Tier Client:** 4-6 hours (dedicated namespace + testing)

---

## Prerequisites

### Required Access

- [ ] **Database Access:** PostgreSQL production instance with admin/superuser privileges
- [ ] **Kubernetes Access:** `kubectl` access to production cluster with cluster-admin or namespace-admin role
- [ ] **ServiceDesk Plus Access:** Admin credentials to client's ServiceDesk Plus instance
- [ ] **Secrets Management:** Access to Kubernetes secrets or AWS KMS/Azure Key Vault
- [ ] **Monitoring Access:** Grafana and Prometheus for metrics validation

### Required Information from Client

Collect the following information from the client before starting onboarding:

| Information | Example | Purpose |
|-------------|---------|---------|
| **Company Name** | Acme Corp MSP | Tenant identification |
| **Tenant ID (Generated)** | `550e8400-e29b-41d4-a716-446655440000` | Unique UUID for tenant |
| **ServiceDesk Plus URL** | `https://servicedesk.acmecorp.com` | API base URL |
| **ServiceDesk Plus API Key** | `SDPAPI_ABC123...` | Authentication |
| **Admin Contact Email** | `admin@acmecorp.com` | Escalation contact |
| **Support Tier** | Basic or Premium | Determines namespace strategy |
| **Enhancement Preferences** | Context sources, output format | LLM behavior customization |
| **Rate Limits** | 100 req/min (optional) | Throttling configuration |

### System Prerequisites

Before onboarding any client, verify production infrastructure health:

```bash
# 1. Check all pods running
kubectl get pods -n production
# Expected: All pods Running and Ready (2/2, 1/1, etc.)

# 2. Verify database connectivity
psql -h <RDS_ENDPOINT> -U aiagents -d ai_agents -c "SELECT version();"
# Expected: PostgreSQL 17.x version string

# 3. Check Redis connectivity
redis-cli -h <ELASTICACHE_ENDPOINT> PING
# Expected: PONG

# 4. Verify API health
curl -s https://api.ai-agents.production/health | jq
# Expected: {"status": "healthy"}

# 5. Validate RLS policies active (CRITICAL)
psql -h <RDS_ENDPOINT> -U aiagents -d ai_agents -c "
SELECT tablename, policyname, cmd
FROM pg_policies
WHERE tablename IN ('tenant_configs', 'enhancement_history', 'ticket_history', 'system_inventory')
ORDER BY tablename, policyname;"
# Expected: 3+ policies returned with expressions containing current_setting('app.current_tenant_id')
```

**HALT if any health check fails.** Resolve infrastructure issues before proceeding.

---

## Onboarding Workflow

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Client Onboarding Workflow                      │
└─────────────────────────────────────────────────────────────────────┘

1. Pre-Onboarding
   ├── Collect client information
   ├── Determine support tier (Basic/Premium)
   └── Verify infrastructure health

2. Tenant Configuration
   ├── Generate tenant_id (UUID)
   ├── Generate webhook signing secret
   ├── Encrypt credentials (Fernet or K8s secrets)
   └── Insert tenant_configs record

3. Kubernetes Configuration (Tier-Based)
   ├── Basic Tier: Use shared 'production' namespace
   └── Premium Tier: Create dedicated namespace with RBAC + quotas

4. ServiceDesk Plus Integration
   ├── Configure webhook endpoint URL
   ├── Set HMAC-SHA256 signing secret
   ├── Configure triggers (ticket creation events)
   └── Test webhook delivery

5. Validation Testing
   ├── Send test webhook (signature validation)
   ├── Verify job queued to Redis
   ├── Monitor Celery worker processing
   ├── Validate enhancement posted to ServiceDesk Plus
   └── Verify RLS isolation with multi-tenant test

6. Production Activation
   ├── Process first real ticket
   ├── Monitor metrics in Grafana
   ├── Collect client feedback
   └── Document completion
```

---

## Step-by-Step Procedures

### Step 1: Generate Tenant Configuration Data

**Duration:** 10 minutes

#### 1.1 Generate Unique Tenant ID

```bash
# Generate UUID v4 for tenant_id
TENANT_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
echo "Generated Tenant ID: $TENANT_ID"
# Example output: 550e8400-e29b-41d4-a716-446655440000
```

#### 1.2 Generate Webhook Signing Secret

```bash
# Generate cryptographically secure 32-character secret
WEBHOOK_SECRET=$(openssl rand -hex 32)
echo "Generated Webhook Secret: $WEBHOOK_SECRET"
# Example output: 7f3e9a2b1c4d5e6f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f
```

#### 1.3 Prepare Enhancement Preferences (JSON)

```json
{
  "context_sources": ["ticket_history", "kb", "monitoring"],
  "output_format": "markdown",
  "max_tokens": 500,
  "llm_model": "openai/gpt-4o-mini",
  "include_confidence_score": true
}
```

Save this as `tenant-preferences.json` for use in database INSERT.

---

### Step 2: Create Tenant Database Record

**Duration:** 15 minutes

#### 2.1 Encrypt ServiceDesk Plus API Key

**Option A: Application-Level Encryption (Fernet)**

```python
# encrypt_credentials.py
from cryptography.fernet import Fernet
import os

# Load encryption key from environment or generate new one
# IMPORTANT: Store this key securely in Kubernetes secret or KMS
ENCRYPTION_KEY = os.getenv('TENANT_ENCRYPTION_KEY')  # Base64-encoded Fernet key
cipher = Fernet(ENCRYPTION_KEY.encode())

# Encrypt ServiceDesk Plus API key
servicedesk_api_key = "SDPAPI_ABC123XYZ456"  # From client
encrypted_api_key = cipher.encrypt(servicedesk_api_key.encode()).decode()

# Encrypt webhook signing secret
webhook_secret = "7f3e9a2b1c4d5e6f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f"
encrypted_webhook_secret = cipher.encrypt(webhook_secret.encode()).decode()

print(f"Encrypted API Key: {encrypted_api_key}")
print(f"Encrypted Webhook Secret: {encrypted_webhook_secret}")
```

**Option B: Kubernetes Secrets (Recommended for Production)**

```bash
# Store credentials in Kubernetes secret
kubectl create secret generic tenant-${TENANT_ID}-credentials \
  --from-literal=SERVICEDESK_API_KEY="SDPAPI_ABC123XYZ456" \
  --from-literal=WEBHOOK_SECRET="$WEBHOOK_SECRET" \
  --namespace=production

# Verify secret created
kubectl describe secret tenant-${TENANT_ID}-credentials -n production
```

#### 2.2 Insert Tenant Configuration Record

```sql
-- tenant_insert.sql
-- Connect to production database
-- psql -h <RDS_ENDPOINT> -U aiagents -d ai_agents

INSERT INTO tenant_configs (
    id,
    tenant_id,
    name,
    servicedesk_url,
    servicedesk_api_key_encrypted,
    webhook_signing_secret_encrypted,
    enhancement_preferences,
    rate_limits,
    created_at,
    updated_at
) VALUES (
    gen_random_uuid(),  -- Auto-generate primary key ID
    '550e8400-e29b-41d4-a716-446655440000',  -- tenant_id from Step 1.1
    'Acme Corp MSP',  -- Client company name
    'https://servicedesk.acmecorp.com',  -- ServiceDesk Plus URL
    'gAAAAABhKq...',  -- Encrypted API key from Step 2.1
    'gAAAAABhKr...',  -- Encrypted webhook secret from Step 2.1
    '{
        "context_sources": ["ticket_history", "kb", "monitoring"],
        "output_format": "markdown",
        "max_tokens": 500,
        "llm_model": "openai/gpt-4o-mini",
        "include_confidence_score": true
    }'::jsonb,  -- Enhancement preferences
    '{"requests_per_minute": 100}'::jsonb,  -- Rate limits (optional)
    NOW(),
    NOW()
);
```

#### 2.3 Verify Tenant Configuration

```sql
-- Verify tenant record created successfully
SELECT
    tenant_id,
    name,
    servicedesk_url,
    created_at,
    enhancement_preferences->>'llm_model' as llm_model
FROM tenant_configs
WHERE tenant_id = '550e8400-e29b-41d4-a716-446655440000';
```

**Expected Output:**
```
           tenant_id            |      name      |          servicedesk_url           |        created_at         |     llm_model
--------------------------------+----------------+-----------------------------------+---------------------------+--------------------
 550e8400-e29b-41d4-a716-446655440000 | Acme Corp MSP | https://servicedesk.acmecorp.com | 2025-11-03 10:30:00+00 | openai/gpt-4o-mini
```

---

### Step 3: Configure Kubernetes Resources (Tier-Based)

**Duration:** 15 minutes (Basic) | 45 minutes (Premium)

#### 3.1 Determine Client Tier

- **Basic Tier:** Shared `production` namespace, RLS isolation only
- **Premium Tier:** Dedicated namespace with RBAC, network policies, resource quotas

#### 3.2 Basic Tier Configuration (Default)

For Basic tier clients, no additional Kubernetes configuration required. The shared `production` namespace already has:
- FastAPI API pods (2 replicas)
- Celery worker pods (3 replicas)
- Prometheus monitoring
- Network policies allowing ingress from ingress-controller

**Verification:**
```bash
kubectl get pods -n production
# Expected: ai-agents-api and ai-agents-worker pods Running
```

#### 3.3 Premium Tier Configuration (Optional)

For Premium tier clients requiring dedicated resources and enhanced isolation:

**3.3a. Create Dedicated Namespace**

```bash
# Create namespace
kubectl create namespace tenant-acmecorp

# Label namespace for tenant tracking
kubectl label namespace tenant-acmecorp \
  tenant-id=550e8400-e29b-41d4-a716-446655440000 \
  tier=premium
```

**3.3b. Apply RBAC Policies**

```yaml
# tenant-rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: tenant-acmecorp-sa
  namespace: tenant-acmecorp
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: tenant-worker-role
  namespace: tenant-acmecorp
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps", "secrets"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tenant-worker-rolebinding
  namespace: tenant-acmecorp
subjects:
- kind: ServiceAccount
  name: tenant-acmecorp-sa
  namespace: tenant-acmecorp
roleRef:
  kind: Role
  name: tenant-worker-role
  apiGroup: rbac.authorization.k8s.io
```

```bash
kubectl apply -f tenant-rbac.yaml
```

**3.3c. Configure Network Policies**

```yaml
# tenant-network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tenant-isolation
  namespace: tenant-acmecorp
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  # Allow traffic from ingress controller only
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
  egress:
  # Allow DNS resolution
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: UDP
      port: 53
  # Allow database and Redis connections
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
  # Allow external HTTPS (for ServiceDesk Plus API, OpenAI API)
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443
```

```bash
kubectl apply -f tenant-network-policy.yaml
```

**3.3d. Set Resource Quotas**

```yaml
# tenant-resource-quota.yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-quota
  namespace: tenant-acmecorp
spec:
  hard:
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.cpu: "8"
    limits.memory: 16Gi
    pods: "10"
    services: "5"
    persistentvolumeclaims: "2"
```

```bash
kubectl apply -f tenant-resource-quota.yaml

# Verify quota applied
kubectl describe resourcequota tenant-quota -n tenant-acmecorp
```

---

### Step 4: Configure ServiceDesk Plus Webhook

**Duration:** 20 minutes

#### 4.1 Generate Production Webhook URL

```bash
# Format: https://api.ai-agents.production/webhook/servicedesk?tenant_id=<UUID>
WEBHOOK_URL="https://api.ai-agents.production/webhook/servicedesk?tenant_id=$TENANT_ID"
echo "Webhook URL: $WEBHOOK_URL"
# Example: https://api.ai-agents.production/webhook/servicedesk?tenant_id=550e8400-e29b-41d4-a716-446655440000
```

#### 4.2 Access Client's ServiceDesk Plus Admin Console

1. Navigate to client's ServiceDesk Plus URL: `https://servicedesk.acmecorp.com`
2. Login with admin credentials (provided by client)
3. Go to: **Admin** → **Automation** → **Webhooks** → **Add New Webhook**

#### 4.3 Configure Webhook Settings

| Setting | Value |
|---------|-------|
| **Name** | AI Agents Ticket Enhancement |
| **Description** | Sends ticket events to AI enhancement platform |
| **URL** | `https://api.ai-agents.production/webhook/servicedesk?tenant_id=550e8400-e29b-41d4-a716-446655440000` |
| **Method** | POST |
| **Content-Type** | application/json |
| **Custom Header 1** | `X-ServiceDesk-Signature: ${HMAC_SHA256}` |
| **Signing Secret** | `7f3e9a2b1c4d5e6f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f` (from Step 1.2) |
| **Trigger Events** | Ticket Created, Ticket Updated (Priority/Status changes) |
| **Enabled** | Yes |

**IMPORTANT:** Ensure `X-ServiceDesk-Signature` header is configured with HMAC-SHA256 signature using the webhook secret. This is critical for security validation.

#### 4.4 Test Webhook Delivery

After configuration, ServiceDesk Plus provides a "Test Webhook" button:

1. Click **Test Webhook** in ServiceDesk Plus admin
2. Monitor FastAPI logs for incoming request:

```bash
kubectl logs -n production deployment/ai-agents-api -f | grep "webhook_received"
# Expected: INFO: Webhook received from tenant_id=550e8400-e29b-41d4-a716-446655440000
```

3. Verify signature validation succeeded:

```bash
kubectl logs -n production deployment/ai-agents-api -f | grep "signature_valid"
# Expected: INFO: Webhook signature valid for tenant_id=550e8400-e29b-41d4-a716-446655440000
```

**If test fails, see [Troubleshooting](#troubleshooting) section.**

---

### Step 5: Validation Testing

**Duration:** 30-45 minutes

#### 5.1 Test Webhook Processing (End-to-End)

**Option A: Send Test Webhook via curl**

```bash
# Create test ticket payload
cat > test_webhook_payload.json <<'EOF'
{
  "ticket_id": "TKT-12345",
  "subject": "Database connection timeout error",
  "description": "Application reports 'Connection timeout' when querying PostgreSQL database. Error started at 10:30 AM. All other services operational.",
  "priority": "High",
  "status": "Open",
  "requester_email": "user@acmecorp.com",
  "created_at": "2025-11-03T10:30:00Z"
}
EOF

# Compute HMAC-SHA256 signature
PAYLOAD=$(cat test_webhook_payload.json)
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | awk '{print $2}')

# Send webhook
curl -X POST "https://api.ai-agents.production/webhook/servicedesk?tenant_id=$TENANT_ID" \
  -H "Content-Type: application/json" \
  -H "X-ServiceDesk-Signature: $SIGNATURE" \
  -d @test_webhook_payload.json

# Expected Response: {"status": "accepted", "job_id": "abc-123-def"}
```

**Option B: Create Test Ticket in ServiceDesk Plus**

1. Login to client's ServiceDesk Plus
2. Create new ticket: **Subject:** "Test - Database connectivity issue", **Description:** "Testing enhancement workflow"
3. Submit ticket
4. Monitor webhook delivery in FastAPI logs (see Step 4.4)

#### 5.2 Verify Job Queued to Redis

```bash
# Check Redis queue depth
redis-cli -h <ELASTICACHE_ENDPOINT> LLEN enhancement_queue
# Expected: 1 (or more if multiple tests)

# Inspect job details
redis-cli -h <ELASTICACHE_ENDPOINT> LRANGE enhancement_queue 0 0
# Expected: JSON job payload with ticket_id and tenant_id
```

#### 5.3 Monitor Celery Worker Processing

```bash
# Watch Celery worker logs
kubectl logs -n production deployment/ai-agents-worker -f | grep "task_processing"

# Expected log sequence:
# INFO: Task enhance_ticket received: ticket_id=TKT-12345, tenant_id=550e8400...
# INFO: Setting tenant context: tenant_id=550e8400...
# INFO: Gathering ticket history for ticket_id=TKT-12345
# INFO: Querying knowledge base for context
# INFO: Synthesizing enhancement with LLM (model: openai/gpt-4o-mini)
# INFO: Enhancement generated: 150 tokens
# INFO: Posting enhancement to ServiceDesk Plus
# SUCCESS: Task enhance_ticket completed: ticket_id=TKT-12345, duration=8.2s
```

#### 5.4 Verify Enhancement Posted to ServiceDesk Plus

1. Login to client's ServiceDesk Plus
2. Open test ticket (TKT-12345)
3. Check **Notes** or **Comments** section
4. Verify enhancement content visible:

```
🤖 AI-Generated Enhancement (2025-11-03 10:35:00)

Based on ticket history and knowledge base:

**Likely Cause:** Database connection pool exhaustion
**Suggested Actions:**
1. Check active connections: SELECT count(*) FROM pg_stat_activity;
2. Verify connection pool settings in application config
3. Review recent schema changes that may have introduced slow queries

**Related Tickets:** TKT-10203 (similar timeout), TKT-11405 (connection pool fix)

Confidence: 85%
```

#### 5.5 Validate RLS Isolation (Multi-Tenant Test)

**Critical Security Validation:**

```bash
# Run tenant isolation validation script (created in Step 6)
./scripts/tenant-isolation-validation.sh

# Expected output:
# ✅ Tenant A query returned 5 records (all tenant_id = A)
# ✅ Tenant B query returned 3 records (all tenant_id = B)
# ✅ No cross-tenant data leakage detected
# ✅ RLS isolation verified successfully
```

---

### Step 6: Production Activation

**Duration:** 30 minutes

#### 6.1 Process First Real Ticket

Coordinate with client to create a **real production ticket** (not test data):

1. Client creates ticket in ServiceDesk Plus with genuine issue
2. Monitor enhancement workflow via **Jaeger distributed tracing**:

```bash
# Access Jaeger UI
kubectl port-forward -n production svc/jaeger-query 16686:16686
# Open http://localhost:16686 in browser

# Search for traces:
# - Service: ai-agents-api
# - Operation: webhook_received
# - Tag: tenant_id=550e8400-e29b-41d4-a716-446655440000
```

3. Verify trace spans:
   - `webhook_received` (FastAPI)
   - `signature_validation` (WebhookValidator)
   - `job_queued` (Redis)
   - `ticket_enhanced` (Celery worker)
   - `enhancement_posted` (ServiceDesk Plus API)

**Expected total latency:** < 15 seconds from webhook receipt to enhancement posted

#### 6.2 Monitor Metrics in Grafana

```bash
# Access Grafana dashboard
kubectl port-forward -n production svc/grafana 3000:3000
# Open http://localhost:3000 in browser (admin/admin)
```

**Metrics to monitor (filter by tenant_id label):**

| Metric | Expected Value | Dashboard Panel |
|--------|---------------|-----------------|
| `enhancement_requests_total{tenant_id="550e8400..."}` | 1+ | Request Count |
| `enhancement_request_duration_seconds{tenant_id="550e8400..."}` | < 15s | Latency (p95) |
| `enhancement_success_rate{tenant_id="550e8400..."}` | 100% | Success Rate |
| `redis_queue_depth` | 0 (after processing) | Queue Depth |
| `celery_worker_active_tasks` | 0 (idle) | Worker Status |

**HALT if any metric shows failures.** Investigate logs before marking onboarding complete.

#### 6.3 Collect Client Feedback

Survey client technicians on first enhancement:

**Questions:**
1. Was the enhancement relevant to the ticket issue? (Yes/No)
2. Did the suggested actions help resolve the ticket? (Yes/No/Partially)
3. Quality rating: 1-5 stars
4. Accuracy rating: 1-5 stars
5. Additional feedback (free text)

**Target metrics:**
- Relevance: 80%+ "Yes"
- Quality: 4+ stars average
- Accuracy: 4+ stars average

Document feedback in `docs/operations/client-feedback/acmecorp-initial-feedback.md`

---

## Validation Checklist

Before marking onboarding complete, verify all items:

### Database Validation
- [ ] Tenant record exists in `tenant_configs` table
- [ ] `tenant_id` is unique (no duplicates)
- [ ] Credentials encrypted (check `servicedesk_api_key_encrypted` and `webhook_signing_secret_encrypted` fields are not plaintext)
- [ ] Enhancement preferences valid JSON
- [ ] RLS policies active on all tenant-scoped tables

### Kubernetes Validation
- [ ] Namespace exists (Premium tier only)
- [ ] RBAC policies applied (Premium tier only)
- [ ] Network policies configured (Premium tier only)
- [ ] Resource quotas set (Premium tier only)
- [ ] Secrets created and accessible

### ServiceDesk Plus Validation
- [ ] Webhook configured with correct URL and tenant_id parameter
- [ ] HMAC-SHA256 signing secret configured
- [ ] Triggers enabled for ticket creation/update events
- [ ] Test webhook delivery successful
- [ ] Signature validation passed

### End-to-End Validation
- [ ] Test webhook processed successfully (202 Accepted response)
- [ ] Job queued to Redis (`LLEN enhancement_queue` returns 1+)
- [ ] Celery worker processed job without errors
- [ ] Enhancement posted to ServiceDesk Plus ticket
- [ ] Technicians can view enhancement in ticket notes

### Security Validation
- [ ] RLS isolation verified (multi-tenant test passed)
- [ ] Webhook signature validation enforced (reject unsigned requests)
- [ ] Credentials encrypted at rest
- [ ] No cross-tenant data leakage

### Monitoring Validation
- [ ] Prometheus scraping metrics from tenant (`enhancement_requests_total` increments)
- [ ] Grafana dashboard shows tenant-specific metrics
- [ ] Jaeger traces visible for tenant
- [ ] Alertmanager rules active (if configured)

---

## Rollback Procedures

If onboarding must be aborted or rolled back:

### Rollback Step 1: Remove Tenant Configuration

```sql
-- Delete tenant record from database
DELETE FROM tenant_configs WHERE tenant_id = '550e8400-e29b-41d4-a716-446655440000';

-- Verify deletion
SELECT * FROM tenant_configs WHERE tenant_id = '550e8400-e29b-41d4-a716-446655440000';
-- Expected: 0 rows
```

### Rollback Step 2: Delete Kubernetes Resources (Premium Tier Only)

```bash
# Delete tenant namespace (this deletes all resources in namespace)
kubectl delete namespace tenant-acmecorp

# Delete tenant secrets (if created in shared namespace)
kubectl delete secret tenant-550e8400-e29b-41d4-a716-446655440000-credentials -n production
```

### Rollback Step 3: Disable ServiceDesk Plus Webhook

1. Login to client's ServiceDesk Plus admin
2. Navigate to **Admin** → **Automation** → **Webhooks**
3. Find "AI Agents Ticket Enhancement" webhook
4. Click **Disable** or **Delete**

### Rollback Step 4: Cleanup Monitoring Data

```bash
# Remove tenant-specific Grafana panels (optional)
# Manual step: Edit Grafana dashboard JSON to remove tenant_id filters

# Clear Redis queue if jobs pending (use with caution)
redis-cli -h <ELASTICACHE_ENDPOINT> DEL enhancement_queue
```

---

## Troubleshooting

### Issue 1: Webhook Signature Validation Fails

**Symptoms:**
- FastAPI returns `403 Forbidden: Invalid webhook signature`
- Logs show: `ERROR: Signature mismatch for tenant_id=...`

**Causes:**
1. Signing secret mismatch between tenant_configs and ServiceDesk Plus configuration
2. Incorrect HMAC computation algorithm (must be HMAC-SHA256)
3. Payload modified in transit (encoding issues)

**Resolution:**

```bash
# 1. Verify signing secret in database
psql -h <RDS_ENDPOINT> -U aiagents -d ai_agents -c "
SELECT tenant_id, webhook_signing_secret_encrypted
FROM tenant_configs
WHERE tenant_id = '550e8400-e29b-41d4-a716-446655440000';"

# 2. Decrypt secret (if using Fernet)
python3 -c "
from cryptography.fernet import Fernet
cipher = Fernet(b'<ENCRYPTION_KEY>')
encrypted = b'<ENCRYPTED_SECRET_FROM_DB>'
decrypted = cipher.decrypt(encrypted).decode()
print(f'Decrypted secret: {decrypted}')
"

# 3. Compare with ServiceDesk Plus configuration
# Ensure exact match (no extra spaces, newlines, or special characters)

# 4. Recompute HMAC locally to verify algorithm
echo -n '{"ticket_id":"TKT-123"}' | openssl dgst -sha256 -hmac "SECRET_HERE"
# Compare with X-ServiceDesk-Signature header from failed request
```

### Issue 2: Jobs Not Processed (Queue Stuck)

**Symptoms:**
- Redis queue depth increasing (`LLEN enhancement_queue` > 10)
- Celery workers idle (no log activity)
- Tickets not receiving enhancements

**Causes:**
1. Celery workers crashed or not running
2. Database connection issues (RLS context setting fails)
3. ServiceDesk Plus API unreachable (network or credentials)

**Resolution:**

```bash
# 1. Check Celery worker status
kubectl get pods -n production -l app=worker
# Expected: All pods Running (not CrashLoopBackOff or Error)

# 2. Check worker logs for errors
kubectl logs -n production deployment/ai-agents-worker --tail=50

# 3. Verify database connectivity from worker
kubectl exec -n production deployment/ai-agents-worker -- psql -h <RDS_ENDPOINT> -U aiagents -d ai_agents -c "SELECT 1;"
# Expected: 1 row returned

# 4. Test ServiceDesk Plus API from worker
kubectl exec -n production deployment/ai-agents-worker -- curl -H "Authorization: Bearer <API_KEY>" https://servicedesk.acmecorp.com/api/v3/tickets/12345
# Expected: 200 OK with ticket JSON

# 5. Restart workers if needed
kubectl rollout restart deployment/ai-agents-worker -n production
```

### Issue 3: RLS Isolation Fails (Cross-Tenant Data Leak)

**Symptoms:**
- Tenant A sees data belonging to Tenant B
- `tenant-isolation-validation.sh` script fails
- Enhancement_history query returns multiple tenant_ids

**Causes:**
1. RLS policies not enabled on tables
2. Session variable `app.current_tenant_id` not set before queries
3. Superuser/admin role bypassing RLS (postgres superuser ignores RLS by default)

**Resolution (CRITICAL - HALT PRODUCTION IMMEDIATELY):**

```sql
-- 1. Verify RLS enabled on all tenant tables
SELECT tablename, rowsecurity
FROM pg_tables
WHERE tablename IN ('tenant_configs', 'enhancement_history', 'ticket_history', 'system_inventory');
-- Expected: rowsecurity = true for all tables

-- 2. Check RLS policies exist
SELECT tablename, policyname, cmd, qual
FROM pg_policies
WHERE tablename IN ('tenant_configs', 'enhancement_history', 'ticket_history', 'system_inventory');
-- Expected: Policies with qual like "tenant_id = current_setting('app.current_tenant_id')"

-- 3. Test RLS enforcement manually
SET app.current_tenant_id = '550e8400-e29b-41d4-a716-446655440000';
SELECT * FROM enhancement_history WHERE tenant_id != '550e8400-e29b-41d4-a716-446655440000';
-- Expected: 0 rows (RLS should filter out other tenants)

-- 4. If RLS not enabled, HALT and enable immediately
ALTER TABLE tenant_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE enhancement_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE ticket_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_inventory ENABLE ROW LEVEL SECURITY;

-- 5. Verify application code calls set_tenant_context() before queries
-- Review src/database/tenant_context.py and src/workers/tasks.py
```

**Escalation:** If RLS isolation fails, **immediately disable all client access** and escalate to security team.

### Issue 4: Enhancement Quality Low (Client Complaints)

**Symptoms:**
- Client feedback reports irrelevant enhancements
- Enhancement suggestions don't match ticket issue
- Low quality/accuracy ratings (< 3 stars)

**Causes:**
1. Insufficient ticket history data
2. Knowledge base not populated
3. LLM model inappropriate for use case
4. Enhancement preferences misconfigured

**Resolution:**

```sql
-- 1. Check ticket_history data volume
SELECT COUNT(*) FROM ticket_history WHERE tenant_id = '550e8400-e29b-41d4-a716-446655440000';
-- Expected: 100+ resolved tickets for good context

-- 2. Review enhancement preferences
SELECT enhancement_preferences FROM tenant_configs WHERE tenant_id = '550e8400-e29b-41d4-a716-446655440000';

-- 3. Adjust preferences if needed
UPDATE tenant_configs
SET enhancement_preferences = jsonb_set(
    enhancement_preferences,
    '{context_sources}',
    '["ticket_history", "kb", "monitoring", "recent_alerts"]'::jsonb
)
WHERE tenant_id = '550e8400-e29b-41d4-a716-446655440000';

-- 4. Consider upgrading LLM model (e.g., gpt-4o-mini → gpt-4o)
UPDATE tenant_configs
SET enhancement_preferences = jsonb_set(
    enhancement_preferences,
    '{llm_model}',
    '"openai/gpt-4o"'
)
WHERE tenant_id = '550e8400-e29b-41d4-a716-446655440000';
```

---

## Post-Onboarding

### Documentation

After successful onboarding, document the following:

1. **Client Profile:** `docs/clients/acmecorp/profile.md`
   - Company name, contact info, support tier
   - Onboarding date, onboarding engineer
   - ServiceDesk Plus URL, tenant_id

2. **Configuration Summary:** `docs/clients/acmecorp/config.md`
   - Enhancement preferences
   - Rate limits and quotas
   - Custom configurations

3. **Initial Metrics:** `docs/clients/acmecorp/baseline-metrics.md`
   - First week success rate, latency, volume
   - Client feedback ratings
   - Issues encountered and resolutions

### Handoff to Support Team

Schedule handoff meeting with support team (30 minutes):

**Agenda:**
1. Client overview (company, support tier, contact)
2. Onboarding summary (date, engineer, any issues)
3. Enhancement preferences and customizations
4. Monitoring dashboards (Grafana links)
5. Escalation procedures (how to investigate failures)
6. Client feedback channels (how technicians report issues)

**Deliverables:**
- Handoff deck (slides or document)
- Access provisioned for support team (Grafana, Kubernetes read-only)
- Client contact sheet (admin email, escalation phone)

### Follow-Up Schedule

- **Week 1:** Daily check-ins (monitor metrics, ensure no issues)
- **Week 2:** 3x/week check-ins (reduce frequency as stability proven)
- **Month 1:** Weekly review meeting with client (collect feedback, adjust preferences)
- **Month 3:** Quarterly business review (metrics, ROI, expansion opportunities)

---

## References

### Internal Documentation

- [Production Deployment Runbook](production-deployment-runbook.md) - Infrastructure deployment procedures
- [Tenant Troubleshooting Guide](tenant-troubleshooting-guide.md) - Common tenant-specific issues
- [Architecture Documentation](../architecture.md) - System design and RLS implementation
- [PRD](../PRD.md) - Product requirements and multi-tenancy features

### External Resources

- [AWS Well-Architected SaaS Lens: Tenant Onboarding](https://docs.aws.amazon.com/wellarchitected/latest/saas-lens/tenant-onboarding.html)
- [AWS Well-Architected SaaS Lens: Tenant Isolation](https://docs.aws.amazon.com/wellarchitected/latest/saas-lens/tenant-isolation.html)
- [PostgreSQL Row-Level Security Documentation](https://www.postgresql.org/docs/17/ddl-rowsecurity.html)
- [PostgreSQL RLS Best Practices 2025](https://docs.aws.amazon.com/prescriptive-guidance/latest/saas-multitenant-managed-postgresql/rls.html)
- [Kubernetes Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Kubernetes Resource Quotas](https://kubernetes.io/docs/concepts/policy/resource-quotas/)

### Code References

- `src/services/tenant_service.py` - TenantService.create_tenant() method
- `src/database/tenant_context.py` - set_db_tenant_context() helper
- `src/api/webhooks.py` - Webhook receiver endpoint
- `src/services/webhook_validator.py` - HMAC signature validation
- `alembic/versions/168c9b67e6ca_add_row_level_security_policies.py` - RLS migration

---

**Document Version History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-03 | Operations Team | Initial release (Story 5.3) |

**Review Schedule:** Quarterly review, next due 2026-02-03
