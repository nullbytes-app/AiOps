# Client Support Procedures
**AI Agents Platform - Client-Facing Support Operations**

**Document Version:** 1.0
**Last Updated:** 2025-11-04
**Target Audience:** Support Engineers (Client-Facing)
**Status:** Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Ticket Investigation Workflow](#ticket-investigation-workflow)
3. [Configuration Management](#configuration-management)
4. [Performance Tuning](#performance-tuning)
5. [Client Onboarding Support](#client-onboarding-support)
6. [Tenant Troubleshooting Cheatsheet](#tenant-troubleshooting-cheatsheet)
7. [Data Access Procedures](#data-access-procedures)

---

## Overview

### Purpose

This document provides **client-facing support procedures** for the AI Agents platform. These procedures focus on supporting active clients with ticket investigation, configuration changes, performance optimization, and troubleshooting tenant-specific issues.

### Key Principles

1. **Client Privacy:** Always respect Row-Level Security (RLS) constraints - never access cross-tenant data without explicit authorization
2. **Proactive Communication:** Keep clients informed during investigations and service changes
3. **Configuration Changes:** All tenant configuration changes require client approval and documentation
4. **Escalation Awareness:** Know when to escalate to Engineering vs. handling within Support

### Client Context

**Current Clients:** 1 production client (MVP client from Story 5.3)
**Planned Growth:** 3-5 additional clients in next 6 months
**Support Model:** 24x7 support via on-call rotation (established in Story 5.6)

---

## Ticket Investigation Workflow

**Use Case:** Client reports issue with specific ticket enhancement (e.g., "Ticket #12345 enhancement was not helpful" or "Ticket #67890 never received enhancement")

### Step-by-Step Investigation Procedure

#### Step 1: Gather Client Information

**Information Needed:**
- **Client Name / Tenant ID** (e.g., `msp-acme-corp`)
- **ServiceDesk Plus Ticket ID** (e.g., `12345`)
- **Issue Description** (e.g., "Enhancement not received", "Enhancement inaccurate", "Webhook failed")
- **Timestamp** (approximate time when issue occurred)

**Questions to Ask Client:**
1. What is the ServiceDesk Plus ticket number?
2. When was the ticket created/updated?
3. Did the technician receive any enhancement? If yes, what was wrong with it?
4. Have you experienced this issue with other tickets?

---

#### Step 2: Verify Webhook Delivery

**Check if webhook was received:**

```bash
# Search API logs for webhook with ticket ID
kubectl logs deployment/ai-agents-api -n ai-agents-production --since=24h | grep "ticket_id: <ticket_id>"

# Expected log: "Webhook received: ticket_id=12345, tenant_id=msp-acme-corp, timestamp=2025-11-04T10:30:00Z"
```

**Possible Outcomes:**
1. ✅ **Webhook found:** Proceed to Step 3 (check job queuing)
2. ❌ **Webhook NOT found:** Webhook delivery failure
   - Check ServiceDesk Plus webhook configuration (correct URL, active webhook)
   - Review API logs for 403 Forbidden errors (signature validation failure)
   - See [Webhook Signature Validation Failures](production-support-guide.md#4-webhook-signature-validation-failures)

---

#### Step 3: Check Job Queuing

**Verify job was queued to Redis:**

```bash
# Search API logs for job queuing confirmation
kubectl logs deployment/ai-agents-api -n ai-agents-production --since=24h | grep -A5 "ticket_id: <ticket_id>" | grep "Job queued"

# Expected log: "Job queued: job_id=abc123, ticket_id=12345, queue=celery"
```

**Possible Outcomes:**
1. ✅ **Job queued:** Proceed to Step 4 (check worker processing)
2. ❌ **Job NOT queued:** API error during job creation
   - Review API logs for exceptions around webhook timestamp
   - Check database connectivity (RLS enforcement, connection pool)
   - Escalate to Engineering if API-level bug suspected

---

#### Step 4: Check Worker Processing

**Verify worker picked up and processed job:**

```bash
# Search worker logs for job processing
kubectl logs deployment/ai-agents-worker -n ai-agents-production --since=24h | grep "job_id: abc123"

# Expected logs:
# "Task started: job_id=abc123, ticket_id=12345"
# "LangGraph workflow initiated"
# "Context gathered: ticket_history=Yes, docs=Yes, ip_data=Yes"
# "GPT-4 API call: status=200, tokens=1500"
# "ServiceDesk Plus ticket updated: ticket_id=12345, status=success"
# "Task completed: job_id=abc123, duration=45s"
```

**Possible Outcomes:**

1. ✅ **Job completed successfully:**
   - Enhancement was delivered to ServiceDesk Plus
   - If client says "not received", investigate ServiceDesk Plus side (ticket comments, API response)
   - Check if enhancement was low quality → See Step 6 (Quality Investigation)

2. ❌ **Job failed during processing:**
   - Review error message in worker logs
   - Common failure modes:
     - **GPT-4 API timeout/error:** OpenAI service issue or rate limit
     - **ServiceDesk Plus API error:** Invalid ticket ID, API credentials expired, rate limiting
     - **Context gathering timeout:** Slow database queries, external API unavailable
   - See [Enhancement Pipeline Failures](production-support-guide.md#5-enhancement-pipeline-failures)

3. ⏳ **Job stuck/not processed:**
   - Check queue depth: `kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- redis-cli -h redis LLEN celery`
   - If queue depth high: See [High Queue Depth](production-support-guide.md#1-high-queue-depth)
   - If queue depth normal but job not processed: Check worker health (crashes, OOMKilled)

---

#### Step 5: Use Distributed Tracing (End-to-End View)

**Access Jaeger/Uptrace:**
- **Local:** http://localhost:16686
- **Production:** [Production Jaeger URL]

**Search for Trace:**
1. Search by **ticket_id tag:** `ticket_id=12345`
2. Search by **timestamp:** Use client-provided approximate time window
3. Search by **tenant_id tag:** `tenant_id=msp-acme-corp`

**Analyze Trace:**
- **View all spans:** Webhook → Queue → Worker → Context Gathering → GPT-4 → ServiceDesk Update
- **Identify slow spans:** Look for spans >10s (e.g., GPT-4 API call taking 40s)
- **Check for errors:** Red error indicators on spans
- **Review span attributes:** Error messages, HTTP status codes, retry attempts

**Benefit:** Provides complete end-to-end visibility, especially useful when logs are fragmented across API and worker pods

---

#### Step 6: Quality Investigation (Low-Rated Enhancements)

**Use Case:** Enhancement was delivered but client reports it was not helpful

**Query Feedback API:**

```bash
# Get feedback for specific ticket (if technician submitted feedback)
curl -H "Authorization: Bearer <api_token>" \
  "http://api.ai-agents.internal/api/v1/feedback?tenant_id=<tenant>&ticket_id=<ticket_id>"

# Example response:
# {
#   "feedback": [{
#     "ticket_id": "12345",
#     "rating": 2,
#     "feedback_type": "rating",
#     "comment": "Enhancement suggested wrong solution, not applicable to this issue",
#     "submitted_at": "2025-11-04T10:35:00Z"
#   }]
# }
```

**Review Enhancement Content:**
1. **Access ticket in ServiceDesk Plus** (with client permission or via client-shared screenshot)
2. **Review enhancement details:**
   - Was context accurate? (ticket history, related documentation)
   - Was recommendation relevant to the ticket type?
   - Was enhancement too generic or too specific?
3. **Use distributed trace** to view:
   - Which context sources were used (ticket_history, docs, ip_data)
   - GPT-4 prompt and response (logged in worker logs)
   - Token count and processing time

**Share Findings with Engineering:**
- If pattern identified (e.g., "Network troubleshooting enhancements always rated low"):
  - Document pattern in support notes
  - Share example ticket IDs with Engineering
  - Suggest prompt improvements or additional context sources
- Track improvement via [Weekly Metrics Review](../metrics/weekly-metrics-review-template.md)

---

### Investigation Summary Template

**Use this template when documenting investigation findings:**

```
TICKET INVESTIGATION SUMMARY
============================
Date: 2025-11-04
Support Engineer: [Your Name]
Ticket ID: 12345
Client: MSP Acme Corp (tenant_id: msp-acme-corp)
Issue Reported: Enhancement not received

FINDINGS:
---------
1. Webhook Received: ✅ Yes (2025-11-04 10:30:00 UTC)
2. Job Queued: ✅ Yes (job_id: abc123)
3. Worker Processing: ❌ Failed
   - Error: "ServiceDesk Plus API timeout after 30s"
   - Root Cause: ServiceDesk Plus API experiencing high latency
4. Distributed Trace ID: 7f8e9d0c1b2a3456

ROOT CAUSE:
-----------
ServiceDesk Plus API was slow (p95 latency >20s) during incident window.
Worker timeout threshold is 30s, causing ticket update to fail.

RESOLUTION:
-----------
1. Manually re-queued job after ServiceDesk Plus API recovered
2. Enhancement successfully delivered to ticket at 11:15 UTC
3. Client notified of resolution via email

FOLLOW-UP:
----------
- Escalated to Engineering: Increase ServiceDesk Plus API timeout to 60s
- Monitoring: Added alert for ServiceDesk Plus API latency >10s
```

---

## Configuration Management

**Use Case:** Client requests configuration changes (webhook secret rotation, API credential updates, performance tuning)

### Configuration Change Types

#### 1. Webhook Secret Rotation

**When Required:**
- Scheduled rotation (every 90 days per security policy)
- Security incident (suspected secret compromise)
- Client-requested rotation

**Procedure:**

**Step 1: Generate New Secret**
```bash
# Generate new HMAC secret (256-bit)
NEW_SECRET=$(openssl rand -hex 32)
echo "New secret: $NEW_SECRET"
```

**Step 2: Update Kubernetes Secret**
```bash
# Update secret in Kubernetes
kubectl create secret generic ai-agents-secrets \
  --from-literal=WEBHOOK_SECRET_MSP_ACME_CORP=$NEW_SECRET \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart API deployment to load new secret
kubectl rollout restart deployment/ai-agents-api -n ai-agents-production
kubectl rollout status deployment/ai-agents-api -n ai-agents-production
```

**Step 3: Update ServiceDesk Plus Webhook Configuration**
- Share new secret with client securely (1Password, encrypted email, or secure portal)
- Client updates webhook secret in ServiceDesk Plus admin panel
- Coordinate update timing to minimize downtime (recommend off-hours)

**Step 4: Validate New Secret**
```bash
# Trigger test webhook from ServiceDesk Plus
# Monitor API logs for successful signature validation
kubectl logs deployment/ai-agents-api -n ai-agents-production --tail=20 | grep "Webhook signature validated"
```

**Detailed Runbook:** [docs/runbooks/secret-rotation.md](../runbooks/secret-rotation.md)

---

#### 2. ServiceDesk Plus API Credential Updates

**When Required:**
- Credential expiration
- Security incident
- ServiceDesk Plus instance migration

**Procedure:**

**Step 1: Obtain New Credentials from Client**
- Request new API key/token from client
- Verify credentials work by testing API call:
  ```bash
  curl -H "Authorization: Bearer <new_token>" \
    https://client.servicedeskplus.com/api/v3/requests/12345
  ```

**Step 2: Update tenant_configs Table**
```bash
# Connect to database with RLS context
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- psql $DATABASE_URL

# Set tenant context
SET app.current_tenant_id = 'msp-acme-corp';

# Update API credentials (encrypted at rest)
UPDATE tenant_configs
SET servicedesk_api_key = '<new_encrypted_key>',
    updated_at = NOW()
WHERE tenant_id = 'msp-acme-corp';

# Commit transaction
COMMIT;
```

**Step 3: Validate New Credentials**
- Trigger test enhancement job
- Monitor worker logs for successful ServiceDesk Plus API calls
- Verify ticket update succeeds

**Rollback Plan:**
- Keep old credentials in secure backup for 7 days
- If new credentials fail, revert `tenant_configs` update immediately

---

#### 3. Tenant Configuration Parameters

**Configurable Parameters (tenant_configs table):**

| Parameter | Description | Default | Client-Configurable |
|-----------|-------------|---------|---------------------|
| `webhook_secret` | HMAC secret for webhook validation | Generated | No (Support only) |
| `servicedesk_api_key` | ServiceDesk Plus API credentials | Client-provided | No (Support only) |
| `servicedesk_base_url` | ServiceDesk Plus instance URL | Client-provided | No (Support only) |
| `max_concurrent_jobs` | Max parallel enhancement jobs | 5 | Yes (with approval) |
| `enhancement_timeout_seconds` | Job timeout threshold | 120 | Yes (30-300 range) |
| `enable_context_caching` | Cache context gathering results | true | Yes |
| `gpt4_model` | OpenAI model selection | gpt-4-turbo | Yes (gpt-4, gpt-4-turbo) |
| `gpt4_temperature` | LLM creativity parameter | 0.7 | Yes (0.0-1.0 range) |

**Change Request Process:**
1. **Client submits request** via support ticket
2. **Support reviews** feasibility and impact
3. **Engineering approval** required for `max_concurrent_jobs`, `enhancement_timeout_seconds` (resource impact)
4. **Support implements** change in `tenant_configs` table
5. **Validation** by testing with sample tickets
6. **Client notification** of change completion

---

## Performance Tuning

**Use Case:** Client reports slow enhancements, high latency, or queue backlogs

### Performance Tuning Strategies

#### 1. Queue Depth Optimization

**Symptoms:**
- Tickets taking >5 minutes to receive enhancement
- Queue depth consistently >20 jobs
- Client complaints about slow turnaround

**Diagnosis:**
```bash
# Check current queue depth
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- redis-cli -h redis LLEN celery

# Check historical queue depth trend in Grafana
# Operations Dashboard → Queue Depth panel (last 24 hours)
```

**Tuning Options:**

**Option 1: Increase Worker Count**
```bash
# Temporary scaling (immediate)
kubectl scale deployment/ai-agents-worker -n ai-agents-production --replicas=10

# Permanent scaling (update HPA target)
kubectl edit hpa ai-agents-worker-hpa -n ai-agents-production
# Change minReplicas: 5 → 8
# Change maxReplicas: 10 → 15
```

**Option 2: Adjust HPA Target Queue Depth**
```bash
# Current HPA target: 5 jobs per worker (scale up if >5 jobs/worker)
# Lower threshold for faster scaling: 3 jobs per worker

kubectl edit hpa ai-agents-worker-hpa -n ai-agents-production
# Update targetAverageValue in metrics section
```

**Option 3: Optimize Job Processing Time**
- Review slow enhancement traces (distributed tracing)
- Identify bottlenecks: context gathering, GPT-4 API calls, ServiceDesk Plus updates
- Implement caching for frequently-accessed context (documentation, ticket history)

**Detailed Runbook:** [docs/runbooks/high-queue-depth.md](../runbooks/high-queue-depth.md)

---

#### 2. Worker Scaling Strategy

**Current Configuration:**
- **Min Workers:** 2 (off-hours)
- **Max Workers:** 10 (peak hours)
- **Scaling Metric:** Queue depth (target: 5 jobs per worker)
- **Scale-Up Threshold:** Queue depth >10 for >2 minutes
- **Scale-Down Threshold:** Queue depth <3 for >10 minutes

**Client-Specific Scaling:**

For high-volume clients (>500 tickets/day):
- Increase min workers to 5
- Increase max workers to 20
- Adjust HPA target to 3 jobs per worker (faster response)

**Implementation:**
```bash
# Update HPA for specific client tenant namespace (if using namespace isolation)
kubectl edit hpa ai-agents-worker-hpa -n ai-agents-<tenant>

# If shared namespace, increase global capacity
kubectl edit hpa ai-agents-worker-hpa -n ai-agents-production
```

**Cost Consideration:**
- Each worker: ~1 CPU, 2GB RAM
- Calculate cost: 10 workers * $0.05/hour = $0.50/hour = $360/month
- Get client approval for increased costs if scaling beyond defaults

---

#### 3. Database Performance Tuning

**Symptoms:**
- Slow query logs showing queries >1s
- Database connection pool exhaustion warnings
- High database CPU/memory utilization

**Diagnosis:**
```bash
# Check slow queries in PostgreSQL
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- psql $DATABASE_URL -c \
  "SELECT query, calls, mean_exec_time, max_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Check active connections
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- psql $DATABASE_URL -c \
  "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';"

# Check connection pool utilization (application logs)
kubectl logs deployment/ai-agents-api -n ai-agents-production | grep "connection pool"
```

**Tuning Options:**

**Option 1: Optimize Slow Queries**
- Add indexes for frequently-queried columns
- Example: Index on `enhancements.ticket_id` for fast ticket lookup
- Work with Engineering to implement schema changes

**Option 2: Increase Connection Pool Size**
```python
# Current pool size: 20 connections per API/worker pod
# For high-concurrency clients: increase to 30-40

# Update in application config (requires Engineering deployment)
# src/database/connection.py
# engine = create_async_engine(DATABASE_URL, pool_size=40, max_overflow=10)
```

**Option 3: Vertical Scaling (Database Instance)**
- Upgrade managed database instance (more CPU/RAM)
- Coordinate with cloud provider for zero-downtime scaling
- Typical upgrade: 2 vCPU/8GB → 4 vCPU/16GB

**Detailed Runbook:** [docs/runbooks/database-connection-issues.md](../runbooks/database-connection-issues.md)

---

## Client Onboarding Support

**Use Case:** Supporting new clients after initial onboarding (Story 5.3), troubleshooting onboarding issues

### Post-Onboarding Support Checklist

**Client has been onboarded when:**
- ✅ Tenant created in `tenant_configs` table
- ✅ ServiceDesk Plus webhook configured and validated
- ✅ Test enhancements successfully delivered
- ✅ Kubernetes namespace created (if using namespace isolation)
- ✅ Resource limits configured (API pods, worker pods, queue depth)
- ✅ Grafana dashboards accessible with tenant filter
- ✅ Support contacts exchanged and documented

**Reference:** [docs/operations/client-onboarding-runbook.md](../operations/client-onboarding-runbook.md)

---

### Common Post-Onboarding Issues

#### 1. Webhook Delivery Failures After Onboarding

**Symptoms:**
- Test webhooks worked during onboarding
- Production webhooks now failing (403 Forbidden)

**Common Causes:**
- Webhook secret mismatch (copy/paste error)
- ServiceDesk Plus webhook URL incorrect (typo, wrong environment)
- Network firewall blocking webhook traffic

**Resolution:**
```bash
# Verify webhook secret matches
kubectl get secret ai-agents-secrets -n ai-agents-production -o jsonpath='{.data.WEBHOOK_SECRET_<TENANT>}' | base64 -d

# Share secret with client securely, verify ServiceDesk Plus config
# Test webhook delivery manually (ServiceDesk Plus admin panel → "Test Webhook")
```

---

#### 2. Enhancement Quality Issues (First Week)

**Symptoms:**
- Client reports enhancements not relevant
- Low feedback ratings (<3/5)

**Common Causes:**
- Insufficient ticket history (new ServiceDesk Plus instance)
- Missing documentation in knowledge base
- GPT-4 prompt not tuned for client's specific domain (network, database, etc.)

**Resolution:**
1. **Gather feedback examples:**
   - Ask client for 5-10 specific ticket IDs with issues
   - Review enhancements and identify patterns
2. **Collaborate with Engineering:**
   - Share findings with Engineering team
   - Request prompt tuning or context source additions
3. **Set expectations:**
   - Explain learning curve (system improves with more ticket history)
   - Recommend weekly feedback reviews for first month

---

#### 3. Performance Concerns (High Volume Clients)

**Symptoms:**
- Queue depth high (>50 jobs) during peak hours
- Enhancements delayed >5 minutes

**Resolution:**
1. **Review client ticket volume:**
   - How many tickets/day? (Expected vs. actual)
   - Are there traffic patterns? (9am-5pm peaks)
2. **Adjust worker scaling:**
   - Increase min workers for high-volume clients
   - Configure HPA for faster scale-up during peaks
3. **Resource allocation:**
   - If dedicated namespace: increase resource limits
   - If shared: consider namespace isolation for large clients

---

## Tenant Troubleshooting Cheatsheet

**Quick reference for tenant-specific issues**

### Common Scenarios

| Scenario | Quick Diagnosis | Quick Fix | Escalation |
|----------|----------------|-----------|------------|
| **Enhancements stopped for one tenant** | Check webhook logs: `kubectl logs deployment/ai-agents-api -n ai-agents-production \| grep "tenant_id: <tenant>"` | Verify webhook secret, restart API deployment | If webhook config correct, escalate to Engineering |
| **Slow enhancements for one tenant** | Check queue depth filtered by tenant: review worker logs | Scale workers, check ServiceDesk Plus API latency | If persistent, escalate for dedicated resources |
| **Low enhancement quality for one tenant** | Query feedback API for tenant | Review with client, gather examples | Escalate to Engineering for prompt tuning |
| **Tenant cannot access feedback API** | Test API auth: `curl -H "Authorization: Bearer <token>" /api/v1/feedback` | Verify API token, check RLS enforcement | Escalate if authentication issue |
| **Tenant-specific configuration not applied** | Query `tenant_configs` table: `SELECT * FROM tenant_configs WHERE tenant_id = '<tenant>'` | Verify config values, restart workers to reload | Escalate if config not persisting |

---

### RLS Enforcement Verification

**Always verify RLS is working correctly for tenant data isolation:**

```bash
# Test RLS enforcement
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- psql $DATABASE_URL

# Should return ONLY tenant-specific data
SET app.current_tenant_id = 'msp-acme-corp';
SELECT count(*) FROM enhancements;  -- Should show only Acme Corp enhancements

# Should return NO data (different tenant)
SET app.current_tenant_id = 'msp-different-corp';
SELECT count(*) FROM enhancements WHERE tenant_id = 'msp-acme-corp';  -- Should return 0
```

**If RLS not enforcing:**
1. **IMMEDIATE ESCALATION to Engineering + Security**
2. Isolate affected tenant (disable API access if necessary)
3. Collect audit logs for forensic analysis

**Reference:** [docs/operations/tenant-troubleshooting-guide.md](../operations/tenant-troubleshooting-guide.md)

---

## Data Access Procedures

**Use Case:** Support engineers need to query client data for troubleshooting (adhering to RLS constraints)

### RLS Access Principles

**CRITICAL SECURITY RULES:**
1. **Always set `app.current_tenant_id` before querying** - Never query without RLS context
2. **Never access cross-tenant data** without explicit multi-tenant admin privileges
3. **Document all data access** in audit logs and support ticket
4. **Client consent required** for accessing sensitive data (ticket content, feedback comments)

---

### Safe Database Query Procedures

#### 1. Connecting to Database with RLS Context

```bash
# Connect to database via API pod
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- psql $DATABASE_URL

# FIRST STEP: Set tenant context (MANDATORY)
SET app.current_tenant_id = 'msp-acme-corp';

# Now all queries automatically filtered by RLS
SELECT * FROM enhancements LIMIT 5;  -- Returns only Acme Corp enhancements
```

---

#### 2. Querying Enhancement Status for Client

**Use Case:** Client asks "How many enhancements succeeded today?"

```sql
-- Set tenant context
SET app.current_tenant_id = 'msp-acme-corp';

-- Query enhancement status counts for today
SELECT status, count(*) as count
FROM enhancements
WHERE created_at >= CURRENT_DATE
GROUP BY status;

-- Expected output:
--   status   | count
-- -----------+-------
--  success   |   45
--  failed    |    2
--  pending   |    1
```

---

#### 3. Querying Feedback for Client

**Use Case:** Client asks "What was the average rating last week?"

```sql
-- Set tenant context
SET app.current_tenant_id = 'msp-acme-corp';

-- Query feedback statistics for last 7 days
SELECT
  count(*) as total_feedback,
  avg(rating) as average_rating,
  sum(CASE WHEN feedback_type = 'thumbs_up' THEN 1 ELSE 0 END) as thumbs_up_count,
  sum(CASE WHEN feedback_type = 'thumbs_down' THEN 1 ELSE 0 END) as thumbs_down_count
FROM enhancement_feedback
WHERE created_at >= CURRENT_DATE - INTERVAL '7 days';

-- Expected output:
--  total_feedback | average_rating | thumbs_up_count | thumbs_down_count
-- ----------------+----------------+-----------------+-------------------
--       52        |      4.2       |        42       |         10
```

**Alternative:** Use Feedback API (preferred for Support):
```bash
curl -H "Authorization: Bearer <api_token>" \
  "http://api.ai-agents.internal/api/v1/feedback/stats?tenant_id=msp-acme-corp&start_date=2025-10-28&end_date=2025-11-04"
```

---

#### 4. Investigating Specific Enhancement by Ticket ID

**Use Case:** Client reports "Ticket #12345 enhancement failed, please investigate"

```sql
-- Set tenant context
SET app.current_tenant_id = 'msp-acme-corp';

-- Find enhancement record
SELECT id, ticket_id, status, error_message, created_at, updated_at
FROM enhancements
WHERE ticket_id = '12345'
ORDER BY created_at DESC
LIMIT 1;

-- If failed, review error_message for root cause
-- Example output:
--   id   | ticket_id | status |         error_message          |      created_at       |      updated_at
-- -------+-----------+--------+--------------------------------+-----------------------+-----------------------
--  1234  |   12345   | failed | ServiceDesk Plus API timeout   | 2025-11-04 10:30:00   | 2025-11-04 10:31:00
```

**Follow-Up:** Use distributed tracing (ticket_id tag) for detailed investigation

---

### Data Access Audit Trail

**All database access must be documented:**

```
DATA ACCESS LOG
===============
Date: 2025-11-04 11:00 UTC
Support Engineer: Jane Doe
Client: MSP Acme Corp (tenant_id: msp-acme-corp)
Purpose: Investigate failed enhancement for Ticket #12345 (Support Ticket #SUP-567)
Query Executed: SELECT * FROM enhancements WHERE ticket_id = '12345'
Result: Found failed enhancement (error: ServiceDesk Plus API timeout)
Action Taken: Re-queued job, notified client of resolution
```

**Retention:** Data access logs retained for 90 days per compliance policy

---

### Using Feedback API (Preferred for Support)

**Benefits:**
- No direct database access required
- RLS automatically enforced by API
- Structured JSON responses
- Audit logging built-in

**Common Queries:**

```bash
# Get all feedback for tenant (last 30 days)
curl -H "Authorization: Bearer <api_token>" \
  "http://api.ai-agents.internal/api/v1/feedback?tenant_id=msp-acme-corp&start_date=2025-10-05"

# Get feedback for specific ticket
curl -H "Authorization: Bearer <api_token>" \
  "http://api.ai-agents.internal/api/v1/feedback?tenant_id=msp-acme-corp&ticket_id=12345"

# Get aggregated statistics
curl -H "Authorization: Bearer <api_token>" \
  "http://api.ai-agents.internal/api/v1/feedback/stats?tenant_id=msp-acme-corp"
```

**API Documentation:** [src/api/feedback.py](../../src/api/feedback.py)

---

## Additional Resources

### Client-Specific Documentation

- [Client Onboarding Runbook](../operations/client-onboarding-runbook.md) - Full onboarding procedures
- [Tenant Troubleshooting Guide](../operations/tenant-troubleshooting-guide.md) - In-depth multi-tenant troubleshooting
- [Client Handoff Guide](../operations/client-handoff-guide.md) - Post-onboarding handoff procedures

### Technical References

- [Production Support Guide](production-support-guide.md) - System-wide troubleshooting
- [Incident Response Playbook](incident-response-playbook.md) - Handling client-impacting incidents
- [Weekly Metrics Review Template](../metrics/weekly-metrics-review-template.md) - Client health monitoring

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-04 | Initial client support procedures created (Story 5.6) | Dev Agent (AI) |

---

**Document Maintenance:**
- **Review Frequency:** Monthly or after onboarding new client
- **Owner:** Support Team Lead
- **Update Triggers:** New client onboarding, configuration parameters added, common issue patterns

**Feedback:** Report documentation gaps or inaccuracies via `#support-docs-feedback` Slack channel.
