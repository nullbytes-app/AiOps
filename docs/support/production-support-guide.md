# Production Support Guide
**AI Agents Platform - Support Engineering Reference**

**Document Version:** 1.0
**Last Updated:** 2025-11-04
**Target Audience:** Support Engineers (L1, L2), SRE Team
**Status:** Production Ready

---

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [System Architecture Overview](#system-architecture-overview)
3. [Common Issues & Solutions](#common-issues--solutions)
4. [Troubleshooting Decision Tree](#troubleshooting-decision-tree)
5. [Escalation Paths](#escalation-paths)
6. [System Health Checks](#system-health-checks)
7. [Kubernetes Operations Quick Reference](#kubernetes-operations-quick-reference)
8. [Additional Resources](#additional-resources)

---

## Quick Reference

### Emergency Contacts

| Role | Primary Contact | Backup Contact | Availability |
|------|----------------|----------------|--------------|
| **L1 Support** | On-Call Rotation | Support Manager | 24x7 |
| **L2 Support** | Senior Support Engineer | Support Team Lead | Business Hours + On-Call |
| **Engineering** | Platform Engineering Team | Engineering Manager | On-Call for P0/P1 |
| **Executive Escalation** | Engineering Manager | CTO | P0 incidents only |

### Critical Dashboards

- **Real-Time Operations:** http://localhost:3000 (Grafana - Operations Dashboard)
- **Baseline Metrics:** http://localhost:3000 (Grafana - Baseline Metrics Dashboard)
- **Prometheus Metrics:** http://localhost:9090
- **Alertmanager:** http://localhost:9093

### Critical Kubectl Commands

```bash
# Pod status and health
kubectl get pods -n ai-agents-production
kubectl describe pod <pod-name> -n ai-agents-production
kubectl logs <pod-name> -n ai-agents-production --tail=100

# Worker scaling (during high load)
kubectl scale deployment ai-agents-worker -n ai-agents-production --replicas=5

# Check HPA status
kubectl get hpa -n ai-agents-production

# Database connection verification
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- psql $DATABASE_URL -c "SELECT 1"

# Redis queue depth check
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- redis-cli -h redis LLEN celery
```

---

## System Architecture Overview

### High-Level Architecture

The AI Agents platform is a **multi-tenant AI-powered ticket enhancement system** built on a microservices architecture:

```
┌─────────────────┐
│ ServiceDesk Plus│──── Webhook ────┐
└─────────────────┘                  │
                                     ▼
                            ┌──────────────────┐
                            │   FastAPI API    │ (Webhook Receiver + Feedback API)
                            │   (Gunicorn +    │
                            │    Uvicorn)      │
                            └────────┬─────────┘
                                     │ Queue Job
                                     ▼
                            ┌──────────────────┐
                            │   Redis Queue    │ (Message Broker)
                            └────────┬─────────┘
                                     │ Dequeue
                                     ▼
                            ┌──────────────────┐
                            │  Celery Workers  │ (Enhancement Processing)
                            │   + LangGraph    │
                            │   + OpenAI GPT-4 │
                            └────────┬─────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
            ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
            │ PostgreSQL   │  │ ServiceDesk  │  │ OpenAI API   │
            │ (Multi-tenant│  │ Plus API     │  │ (via         │
            │  with RLS)   │  │              │  │  OpenRouter) │
            └──────────────┘  └──────────────┘  └──────────────┘
```

### Key Components

#### 1. **API Layer** (`src/api/`)
- **Webhook Receiver** (`webhooks.py`): Receives ServiceDesk Plus webhook events
- **Feedback API** (`feedback.py`): Collects technician feedback for success metrics
- **Technology:** FastAPI + Gunicorn + Uvicorn workers
- **Deployment:** Kubernetes deployment with HPA (2-10 replicas)

#### 2. **Queue Layer** (Redis + Celery)
- **Redis 7.x**: Message broker for async job processing
- **Celery 5.x**: Distributed task queue with retry logic
- **Queue Name:** `celery` (default queue for enhancement jobs)

#### 3. **Worker Layer** (`src/workers/`)
- **Enhancement Worker** (`enhancement_worker.py`): Processes enhancement jobs
- **LangGraph Workflow** (`src/workflows/enhancement_workflow.py`): Orchestrates AI pipeline
  - Context gathering (ticket history, documentation search, IP cross-reference)
  - OpenAI GPT-4 synthesis via OpenRouter
  - ServiceDesk Plus ticket update
- **Scaling:** HPA scales based on queue depth (target: 5 jobs per worker)

#### 4. **Database Layer** (PostgreSQL 17)
- **Multi-Tenancy:** Row-Level Security (RLS) enforced via `app.current_tenant_id` session variable
- **Key Tables:**
  - `tenant_configs`: Per-client configuration (API credentials, webhook secrets)
  - `enhancement_feedback`: Technician feedback data (Story 5.5)
  - `audit_log`: All operations tracking with tenant_id
- **Managed Service:** Cloud-provider managed PostgreSQL (AWS RDS, GCP Cloud SQL, or Azure Database)

#### 5. **Observability Stack** (Epic 4)
- **Prometheus**: Metrics collection (scraping API, workers, Redis)
- **Grafana**: Dashboards for operational metrics and baseline metrics
- **Alertmanager**: Alert routing to email, Slack, PagerDuty
- **OpenTelemetry**: Distributed tracing (Story 4.6) for end-to-end request debugging
- **Loguru**: Structured logging with JSON output

#### 6. **Infrastructure** (Kubernetes 1.28+)
- **Namespace:** `ai-agents-production`
- **Auto-scaling:** Horizontal Pod Autoscaler (HPA) for API and workers
- **Secrets:** Kubernetes Secrets for sensitive data (database credentials, API keys, webhook secrets)
- **Ingress:** TLS-terminated ingress controller for HTTPS traffic

### Data Flow: Webhook to Enhancement

1. **Webhook Received** → FastAPI validates signature, queues job to Redis
2. **Celery Worker** → Dequeues job, initiates LangGraph workflow
3. **Context Gathering** → Queries ticket history, searches docs, cross-references IP
4. **AI Synthesis** → OpenAI GPT-4 (via OpenRouter) generates enhancement
5. **Ticket Update** → ServiceDesk Plus API receives enhanced ticket
6. **Metrics & Logging** → Prometheus metrics recorded, traces captured, logs written

### Multi-Tenancy & Security (Epic 3)

- **Row-Level Security (RLS):** All database queries automatically filtered by `app.current_tenant_id`
- **Tenant Isolation:** Kubernetes namespaces, separate resource limits
- **Audit Logging:** All operations tracked in `audit_log` table with tenant_id
- **Webhook Validation:** HMAC signature verification using tenant-specific secrets

---

## Common Issues & Solutions

**⚠️ Important:** This section consolidates the top 20 most frequent issues encountered during Epic 4-5 operations. For detailed troubleshooting procedures, refer to the [scenario-specific runbooks](#additional-resources).

### 1. High Queue Depth (>50 jobs)

**Symptoms:**
- Prometheus alert: `HighQueueDepth` firing
- Grafana dashboard shows increasing queue depth trend
- Tickets delayed in ServiceDesk Plus (no enhancements within SLA)

**Quick Diagnosis:**
```bash
# Check current queue depth
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- redis-cli -h redis LLEN celery

# Check worker count
kubectl get pods -n ai-agents-production | grep worker

# Check worker resource utilization
kubectl top pods -n ai-agents-production | grep worker
```

**Resolution:**
1. **Scale workers immediately:**
   ```bash
   kubectl scale deployment ai-agents-worker -n ai-agents-production --replicas=5
   ```
2. **Monitor queue drainage** via Grafana Operations Dashboard
3. **If not draining:** Check worker logs for stuck jobs or errors
4. **Long-term:** Review HPA configuration, consider permanent worker increase

**Escalation:** If queue depth >200 or not draining after 15 minutes, escalate to L2 → Engineering

**Detailed Runbook:** [docs/runbooks/high-queue-depth.md](../runbooks/high-queue-depth.md)

---

### 2. Worker Failures / Crashes

**Symptoms:**
- Prometheus alert: `WorkerFailures` firing
- Worker pods in `CrashLoopBackOff` or `Error` state
- Queue depth increasing despite workers running

**Quick Diagnosis:**
```bash
# Check worker pod status
kubectl get pods -n ai-agents-production | grep worker

# Get crash logs
kubectl logs <worker-pod-name> -n ai-agents-production --previous --tail=50

# Check for OOMKilled (memory issues)
kubectl describe pod <worker-pod-name> -n ai-agents-production | grep -i oom
```

**Resolution:**
1. **Memory issues (OOMKilled):**
   - Increase worker memory limits in deployment manifest
   - Restart deployment: `kubectl rollout restart deployment/ai-agents-worker -n ai-agents-production`
2. **Application errors:**
   - Check logs for stack traces, investigate error root cause
   - If transient: restart worker deployment
   - If persistent: escalate to Engineering with logs
3. **Database connection errors:**
   - See [Database Connection Issues](#7-database-connection-issues)

**Escalation:** Escalate to L2 if >3 consecutive crashes or unidentified root cause

**Detailed Runbook:** [docs/runbooks/worker-failures.md](../runbooks/worker-failures.md)

---

### 3. API Timeouts / High Latency

**Symptoms:**
- Prometheus alert: `HighAPILatency` firing
- Grafana shows p95 latency >5s (target: <1s)
- ServiceDesk Plus webhook delivery failures (timeout)

**Quick Diagnosis:**
```bash
# Check API pod status and resource usage
kubectl top pods -n ai-agents-production | grep api

# Check recent API logs for slow requests
kubectl logs deployment/ai-agents-api -n ai-agents-production --tail=100 | grep "took"

# Check if database is slow
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- psql $DATABASE_URL -c "SELECT now()"
```

**Resolution:**
1. **External API timeouts (ServiceDesk Plus, OpenAI):**
   - Check Grafana for external API latency metrics
   - Review circuit breaker status (logs show `CircuitBreakerOpen`)
   - If OpenAI rate-limited: reduce concurrent requests, add backoff
2. **Database slow queries:**
   - Run `EXPLAIN ANALYZE` on slow queries (logs show query details)
   - Check database connection pool exhaustion
   - See [Database Connection Issues](#7-database-connection-issues)
3. **API pod resource exhaustion:**
   - Scale API pods: `kubectl scale deployment/ai-agents-api -n ai-agents-production --replicas=5`

**Escalation:** If latency remains >10s for >5 minutes, escalate to L2 (P1 incident)

**Detailed Runbook:** [docs/runbooks/api-timeout.md](../runbooks/api-timeout.md)

---

### 4. Webhook Signature Validation Failures

**Symptoms:**
- ServiceDesk Plus reports webhook delivery failures
- API logs show `403 Forbidden` errors with "Invalid signature"
- Enhancement jobs not queued despite webhook attempts

**Quick Diagnosis:**
```bash
# Check API logs for signature validation errors
kubectl logs deployment/ai-agents-api -n ai-agents-production --tail=100 | grep "signature"

# Verify tenant webhook secret is correct
kubectl get secret ai-agents-secrets -n ai-agents-production -o jsonpath='{.data.WEBHOOK_SECRET_<TENANT>}' | base64 -d
```

**Resolution:**
1. **Secret mismatch:**
   - Verify ServiceDesk Plus webhook configuration matches Kubernetes secret
   - If rotated: update Kubernetes secret, restart API deployment
   - See [Secret Rotation Runbook](../runbooks/secret-rotation.md)
2. **Timestamp validation failure:**
   - Check server time drift: `kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- date`
   - If >5 minutes skew: investigate NTP synchronization
3. **Payload tampering / malformed webhook:**
   - Review raw webhook payload in ServiceDesk Plus logs
   - Validate against expected schema

**Escalation:** If unable to resolve within 30 minutes, escalate to Engineering (impacts client)

**Detailed Runbook:** [docs/runbooks/WEBHOOK_TROUBLESHOOTING_RUNBOOK.md](../runbooks/WEBHOOK_TROUBLESHOOTING_RUNBOOK.md)

---

### 5. Enhancement Pipeline Failures

**Symptoms:**
- Prometheus alert: `LowSuccessRate` firing (success rate <95%)
- Grafana shows increasing failed enhancement count
- Tickets not updated in ServiceDesk Plus despite job completion

**Quick Diagnosis:**
```bash
# Check worker logs for enhancement failures
kubectl logs deployment/ai-agents-worker -n ai-agents-production --tail=50 | grep -i error

# Check LangGraph workflow errors
kubectl logs deployment/ai-agents-worker -n ai-agents-production --tail=50 | grep "LangGraph"

# Query failed enhancements in database (requires RLS session variable)
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- psql $DATABASE_URL -c "SET app.current_tenant_id = '<tenant_id>'; SELECT id, error_message FROM enhancements WHERE status = 'failed' ORDER BY created_at DESC LIMIT 10;"
```

**Common Failure Modes:**
1. **GPT-4 API failures:**
   - Check OpenRouter API status
   - Review rate limit errors in logs
   - Verify API key validity
2. **Context gathering timeouts:**
   - ServiceDesk Plus API slow/unavailable
   - Documentation search index issues
   - Database query timeouts
3. **ServiceDesk Plus ticket update failures:**
   - Invalid ticket ID (ticket closed/deleted)
   - API credential expiration
   - Rate limiting

**Resolution:**
- **Transient failures:** Workers automatically retry with exponential backoff
- **Persistent failures:** Investigate root cause, escalate if external API issue
- **Client-reported failures:** Use distributed tracing to debug end-to-end flow

**Escalation:** If success rate <90% for >10 minutes, escalate to L2

**Detailed Runbook:** [docs/runbooks/enhancement-failures.md](../runbooks/enhancement-failures.md)

---

### 6. Tenant Isolation Violations

**Symptoms:**
- Prometheus alert: `TenantIsolationViolation` firing
- Audit logs show cross-tenant data access attempts
- Security incident suspected

**Quick Diagnosis:**
```bash
# Check audit logs for cross-tenant access
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- psql $DATABASE_URL -c "SELECT * FROM audit_log WHERE action = 'cross_tenant_access' ORDER BY created_at DESC LIMIT 10;"

# Verify RLS is active
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- psql $DATABASE_URL -c "SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';"
```

**Resolution:**
1. **RLS enforcement failure:**
   - Verify RLS policies are enabled: `ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;`
   - Check `app.current_tenant_id` session variable is set correctly
   - Review application code for RLS bypass (direct SQL without session variable)
2. **Malicious access attempt:**
   - **IMMEDIATE ESCALATION to Engineering + Security**
   - Isolate affected tenant (disable API access if necessary)
   - Collect forensic evidence (audit logs, API logs, traces)
3. **Misconfiguration:**
   - Review tenant_configs table for incorrect tenant_id assignments
   - Verify webhook signature validation per tenant

**Escalation:** **P0 INCIDENT - IMMEDIATE ESCALATION** to Engineering + Executive

**Detailed Runbook:** [docs/runbooks/tenant-isolation-violations.md](../runbooks/tenant-isolation-violations.md)

---

### 7. Database Connection Issues

**Symptoms:**
- Prometheus alert: `DatabaseConnectionIssues` firing
- Application logs show `connection refused` or `too many clients`
- API/workers unable to query database

**Quick Diagnosis:**
```bash
# Test database connectivity
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- psql $DATABASE_URL -c "SELECT version();"

# Check active connections
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"

# Check connection pool settings
kubectl logs deployment/ai-agents-api -n ai-agents-production | grep "connection pool"
```

**Resolution:**
1. **Connection pool exhaustion:**
   - Increase pool size in application config (default: 20)
   - Scale down workers if over-provisioned
   - Review slow queries causing long-held connections
2. **Database unavailable:**
   - Check managed database status in cloud provider console
   - Review recent database maintenance windows
   - Check network connectivity (security group, firewall rules)
3. **Max connections exceeded:**
   - Identify and terminate idle connections: `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND state_change < now() - interval '10 minutes';`
   - Increase database `max_connections` parameter (requires restart)

**Escalation:** If database unavailable >5 minutes, escalate to L2 → Engineering (P0 incident)

**Detailed Runbook:** [docs/runbooks/database-connection-issues.md](../runbooks/database-connection-issues.md)

---

### 8. Alert Notification Failures

**Symptoms:**
- Alerts firing in Prometheus but not received (email, Slack, PagerDuty)
- Alertmanager dashboard shows delivery failures
- On-call engineer not paged for P0 incident

**Quick Diagnosis:**
```bash
# Check Alertmanager status
kubectl get pods -n ai-agents-production | grep alertmanager

# View Alertmanager logs
kubectl logs deployment/alertmanager -n ai-agents-production --tail=100

# Check routing configuration
kubectl get configmap alertmanager-config -n ai-agents-production -o yaml
```

**Resolution:**
1. **Email delivery failures:**
   - Verify SMTP configuration in Alertmanager config
   - Check email provider logs (SendGrid, SES, etc.)
   - Test email connectivity: manual send via SMTP
2. **Slack webhook failures:**
   - Verify Slack webhook URL is correct and not expired
   - Test webhook manually: `curl -X POST -H 'Content-type: application/json' --data '{"text":"Test"}' <slack_webhook_url>`
3. **PagerDuty integration issues:**
   - Verify PagerDuty integration key is correct
   - Check PagerDuty service status
   - Review Alertmanager routing rules for PagerDuty routing

**Escalation:** If on-call notifications broken, **IMMEDIATE manual escalation** via phone/SMS

**Detailed Runbook:** [docs/operations/alertmanager-setup.md](../operations/alertmanager-setup.md)

---

### 9. Client-Reported Low Enhancement Quality

**Symptoms:**
- Client feedback shows low rating (<3/5) or thumbs down
- Technicians report enhancements not helpful or inaccurate
- Grafana Baseline Metrics dashboard shows declining satisfaction trend

**Quick Diagnosis:**
```bash
# Query recent feedback for tenant
curl -H "Authorization: Bearer <api_token>" \
  "http://api.ai-agents.internal/api/v1/feedback?tenant_id=<tenant>&start_date=2025-11-01&end_date=2025-11-04"

# Get feedback statistics
curl -H "Authorization: Bearer <api_token>" \
  "http://api.ai-agents.internal/api/v1/feedback/stats?tenant_id=<tenant>"
```

**Investigation Steps:**
1. **Review specific low-rated enhancements:**
   - Identify ticket IDs from feedback API
   - Use distributed tracing to view end-to-end processing
   - Analyze context sources used (ticket history, docs, IP data)
   - Review GPT-4 prompt and response (logs contain prompt/response)
2. **Identify patterns:**
   - Specific ticket types (e.g., network issues, database problems)
   - Time-of-day patterns (off-hours processing)
   - Context source gaps (missing documentation, stale ticket history)
3. **Collaborate with Engineering:**
   - Share findings with Engineering team
   - Propose prompt improvements or context source additions
   - Track improvement via weekly metrics review

**Escalation:** If satisfaction <3/5 for >5 consecutive enhancements, escalate to Engineering for review

**Reference:** [docs/metrics/weekly-metrics-review-template.md](../metrics/weekly-metrics-review-template.md)

---

### 10. Distributed Tracing Investigation (OpenTelemetry)

**Use Case:** Debugging slow or failing requests end-to-end

**Access Traces:**
- **Jaeger UI:** http://localhost:16686 (local) or production Jaeger URL
- **Uptrace UI:** (if configured) production Uptrace URL

**Common Trace Queries:**
1. **Find traces for specific ticket:**
   - Search by tag: `ticket_id=<ServiceDesk_Plus_ticket_id>`
2. **Find slow requests:**
   - Filter by duration: `duration > 30s`
   - Sort by duration descending
3. **Find failed enhancements:**
   - Filter by status: `error=true`
   - Search by tag: `status=failed`

**Analyzing Traces:**
- **Identify bottleneck:** Look for longest span duration (e.g., GPT-4 API call, database query)
- **Check span attributes:** Tenant ID, ticket ID, worker ID, error messages
- **Follow parent-child relationships:** Webhook → queue → worker → context gathering → GPT-4 → ticket update

**Escalation:** Use traces to provide detailed context when escalating to Engineering

**Reference:** [docs/operations/distributed-tracing-setup.md](../operations/distributed-tracing-setup.md)

---

## Troubleshooting Decision Tree

**First Response Flowchart:**

```
Incident Reported
       |
       v
   Is system accessible? ───── NO ──────> P0 - Complete Outage
       |                                    └─> Escalate to Engineering immediately
      YES                                       Check infrastructure (K8s, DB, Redis)
       |
       v
   Which component affected?
       |
       ├─> API (webhook failures)
       |     ├─> Check API pod status
       |     ├─> Review signature validation logs
       |     └─> See [Webhook Signature Validation Failures](#4-webhook-signature-validation-failures)
       |
       ├─> Workers (queue backlog)
       |     ├─> Check queue depth
       |     ├─> Check worker count and health
       |     └─> See [High Queue Depth](#1-high-queue-depth) or [Worker Failures](#2-worker-failures)
       |
       ├─> Database (connection errors)
       |     ├─> Test database connectivity
       |     ├─> Check connection pool status
       |     └─> See [Database Connection Issues](#7-database-connection-issues)
       |
       ├─> External APIs (timeout errors)
       |     ├─> Check ServiceDesk Plus API status
       |     ├─> Check OpenAI/OpenRouter status
       |     └─> See [API Timeouts / High Latency](#3-api-timeouts--high-latency)
       |
       └─> Enhancements (quality issues)
             ├─> Query feedback API
             ├─> Review distributed traces
             └─> See [Client-Reported Low Enhancement Quality](#9-client-reported-low-enhancement-quality)
```

---

## Escalation Paths

### L1 → L2 Escalation Triggers

**Escalate to L2 Support when:**
- Issue not resolved within 30 minutes using runbooks
- Root cause unclear after initial diagnosis
- Multiple alerts firing simultaneously
- Client-impacting issue (P1 or higher)
- Database or infrastructure issues suspected

### L2 → Engineering Escalation Triggers

**Escalate to Engineering when:**
- Application code changes required
- Database schema modifications needed
- Infrastructure configuration changes required
- Security incident suspected (tenant isolation violations, unauthorized access)
- Persistent failures after L2 troubleshooting (>1 hour)

### Engineering → Executive Escalation Triggers

**Escalate to Executive when:**
- **P0 incident:** Complete system outage affecting all clients
- **Security breach confirmed:** Cross-tenant data access, unauthorized intrusion
- **SLA violation imminent:** Unable to restore service within SLA window
- **Major client impact:** Large client (>100 users) completely down

### Escalation SLA Targets

| Severity | L1 Response | L2 Response | Engineering Response | Executive Notification |
|----------|-------------|-------------|---------------------|----------------------|
| **P0** (Critical) | Immediate | 5 minutes | 15 minutes | Immediate |
| **P1** (High) | 5 minutes | 15 minutes | 30 minutes | If >2 hours unresolved |
| **P2** (Medium) | 15 minutes | 1 hour | 4 hours | Not required |
| **P3** (Low) | 1 hour | Next business day | Next sprint | Not required |

### Escalation Contact Methods

**Order of Contact:**
1. **On-Call System** (PagerDuty/Opsgenie): Automated alert routing
2. **Slack Channels:**
   - `#incidents-p0` - Critical incidents
   - `#incidents-p1` - High priority
   - `#support-escalations` - General escalations
3. **Phone/SMS:** For P0 when on-call system fails
4. **Email:** For P2/P3 or documentation sharing

**Handoff Requirements:**
- **Incident summary:** What happened, when, which clients affected
- **Troubleshooting performed:** Steps taken, diagnostics run, results
- **Current status:** System state, workarounds applied, ongoing issues
- **Supporting evidence:** Logs, traces, metrics screenshots, error messages

---

## System Health Checks

**Use Case:** Proactive monitoring to prevent incidents, post-deployment validation, shift handoff verification

### Quick Health Check (5 minutes)

```bash
#!/bin/bash
# health-check.sh - Quick system health validation

NAMESPACE="ai-agents-production"

echo "=== AI Agents Platform Health Check ==="
echo "Timestamp: $(date)"
echo ""

# 1. Pod Status
echo "1. Pod Status:"
kubectl get pods -n $NAMESPACE
echo ""

# 2. Queue Depth
echo "2. Redis Queue Depth:"
kubectl exec -it deployment/ai-agents-api -n $NAMESPACE -- redis-cli -h redis LLEN celery
echo ""

# 3. Database Connectivity
echo "3. Database Connectivity:"
kubectl exec -it deployment/ai-agents-api -n $NAMESPACE -- psql $DATABASE_URL -c "SELECT 1 AS db_alive"
echo ""

# 4. API Health Endpoint
echo "4. API Health Check:"
kubectl exec -it deployment/ai-agents-api -n $NAMESPACE -- curl -s http://localhost:8000/health
echo ""

# 5. Recent Errors (last 5 minutes)
echo "5. Recent Errors (last 5 minutes):"
kubectl logs deployment/ai-agents-api -n $NAMESPACE --since=5m | grep -i error | tail -10
echo ""

# 6. Active Alerts
echo "6. Active Prometheus Alerts:"
curl -s http://localhost:9090/api/v1/alerts | grep -i firing
echo ""

echo "=== Health Check Complete ==="
```

**Success Criteria:**
- ✅ All pods in `Running` state
- ✅ Queue depth <50 jobs
- ✅ Database responds with `db_alive = 1`
- ✅ API health endpoint returns `{"status": "healthy"}`
- ✅ No `ERROR` level logs in last 5 minutes
- ✅ No `firing` alerts in Prometheus

**If Failed:** Investigate specific failure area using runbooks

---

### Grafana Dashboard Health Indicators

**Operations Dashboard Panels:**
1. **API Latency (p50, p95, p99):** Target p95 <1s
2. **Queue Depth:** Target <20 jobs
3. **Worker Health:** All workers active, no crashes
4. **Database Connections:** <80% of max connections
5. **Error Rate:** <1% of requests
6. **Success Rate:** >95% enhancements successful

**Baseline Metrics Dashboard Panels (Story 5.5):**
1. **Average Feedback Rating:** Target >4/5
2. **Feedback Sentiment:** >70% positive (thumbs up)
3. **p95 Latency:** <60s (target from success criteria)
4. **Enhancement Throughput:** Stable trend, no sudden drops
5. **Success Rate %:** >95%

**Red Flags (Immediate Investigation):**
- 🚨 API latency p95 >5s
- 🚨 Queue depth >100 jobs
- 🚨 Error rate >5%
- 🚨 Success rate <90%
- 🚨 Worker pods in `CrashLoopBackOff`
- 🚨 Database connection pool >90% utilized
- 🚨 Average feedback rating <3/5 for >1 hour

---

## Kubernetes Operations Quick Reference

**Common Support Tasks:**

### Viewing Logs

```bash
# API logs (last 100 lines)
kubectl logs deployment/ai-agents-api -n ai-agents-production --tail=100

# Worker logs (specific pod)
kubectl logs <worker-pod-name> -n ai-agents-production --tail=100

# Follow logs in real-time
kubectl logs deployment/ai-agents-worker -n ai-agents-production -f

# Previous container logs (after crash)
kubectl logs <pod-name> -n ai-agents-production --previous
```

### Scaling Resources

```bash
# Scale API pods
kubectl scale deployment/ai-agents-api -n ai-agents-production --replicas=5

# Scale workers
kubectl scale deployment/ai-agents-worker -n ai-agents-production --replicas=10

# Check HPA (auto-scaling) status
kubectl get hpa -n ai-agents-production
kubectl describe hpa ai-agents-worker-hpa -n ai-agents-production
```

### Pod Management

```bash
# Restart deployment (rolling restart, zero downtime)
kubectl rollout restart deployment/ai-agents-api -n ai-agents-production

# Check rollout status
kubectl rollout status deployment/ai-agents-api -n ai-agents-production

# Delete stuck pod (will auto-recreate)
kubectl delete pod <pod-name> -n ai-agents-production

# Execute command in pod
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- bash
```

### Resource Utilization

```bash
# Pod CPU and memory usage
kubectl top pods -n ai-agents-production

# Node resource usage
kubectl top nodes

# Describe pod for resource limits and requests
kubectl describe pod <pod-name> -n ai-agents-production
```

### Secrets Management

```bash
# List secrets
kubectl get secrets -n ai-agents-production

# View secret (base64 encoded)
kubectl get secret ai-agents-secrets -n ai-agents-production -o yaml

# Decode specific secret key
kubectl get secret ai-agents-secrets -n ai-agents-production -o jsonpath='{.data.DATABASE_PASSWORD}' | base64 -d

# Update secret (requires API restart)
kubectl create secret generic ai-agents-secrets \
  --from-literal=DATABASE_PASSWORD=<new_password> \
  --dry-run=client -o yaml | kubectl apply -f -
```

**⚠️ Security Note:** Always follow secret rotation procedures in [docs/runbooks/secret-rotation.md](../runbooks/secret-rotation.md)

### Database Access

```bash
# Connect to database via API pod
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- psql $DATABASE_URL

# Run single query
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- psql $DATABASE_URL -c "SELECT version();"

# Set RLS context for tenant-scoped queries
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- psql $DATABASE_URL -c "SET app.current_tenant_id = '<tenant_id>'; SELECT * FROM enhancements LIMIT 5;"
```

**⚠️ RLS Reminder:** Always set `app.current_tenant_id` session variable before querying tenant data. Support engineers should never query cross-tenant data without explicit authorization.

---

## Additional Resources

### Operational Documentation

**Setup and Configuration:**
- [Prometheus Setup Guide](../operations/prometheus-setup.md) - Metrics collection configuration
- [Grafana Setup Guide](../operations/grafana-setup.md) - Dashboard and datasource setup
- [Alertmanager Setup](../operations/alertmanager-setup.md) - Alert routing and notification configuration
- [Distributed Tracing Setup](../operations/distributed-tracing-setup.md) - OpenTelemetry instrumentation (Story 4.6)
- [Logging Infrastructure](../operations/logging-infrastructure.md) - Loguru configuration and log aggregation

**Deployment and Client Management:**
- [Production Cluster Setup](../operations/production-cluster-setup.md) - Kubernetes cluster provisioning (Story 5.1)
- [Production Deployment Runbook](../operations/production-deployment-runbook.md) - Application deployment procedures (Story 5.2)
- [Client Onboarding Runbook](../operations/client-onboarding-runbook.md) - Tenant provisioning process (Story 5.3)
- [Client Handoff Guide](../operations/client-handoff-guide.md) - Post-onboarding handoff procedures (Story 5.3)
- [Tenant Troubleshooting Guide](../operations/tenant-troubleshooting-guide.md) - Multi-tenant specific issues (Story 5.3)

**Alert Response:**
- [Alert Response Runbooks](../operations/alert-runbooks.md) - Comprehensive 11-scenario alert response guide (Epic 4)

### Scenario-Specific Runbooks

**Troubleshooting Guides:**
- [High Queue Depth](../runbooks/high-queue-depth.md) - Queue backlog investigation and resolution
- [Worker Failures](../runbooks/worker-failures.md) - Celery worker crash diagnostics
- [Database Connection Issues](../runbooks/database-connection-issues.md) - PostgreSQL connectivity troubleshooting
- [API Timeout](../runbooks/api-timeout.md) - External API performance issues
- [Enhancement Failures](../runbooks/enhancement-failures.md) - LangGraph workflow debugging
- [Webhook Troubleshooting](../runbooks/WEBHOOK_TROUBLESHOOTING_RUNBOOK.md) - Signature validation and delivery issues

**Operational Procedures:**
- [Tenant Onboarding](../runbooks/tenant-onboarding.md) - Step-by-step client provisioning
- [Secret Rotation](../runbooks/secret-rotation.md) - Webhook secret and API credential rotation
- [Secrets Setup](../runbooks/secrets-setup.md) - Kubernetes Secrets initial configuration

### Metrics and Success Criteria

**Baseline Metrics (Story 5.5):**
- [Baseline Metrics Collection Plan](../metrics/baseline-metrics-collection-plan.md) - 7-day measurement methodology
- [Weekly Metrics Review Template](../metrics/weekly-metrics-review-template.md) - Stakeholder review process

**Success Criteria:**
- >20% research time reduction for technicians
- >4/5 average feedback rating (technician satisfaction)
- >95% enhancement success rate
- p95 latency <60s

### Architecture and Design

**Technical Reference:**
- [Architecture Decision Document](../architecture.md) - Technology stack and design decisions
- [Product Requirements Document](../PRD.md) - Epic 5 production deployment requirements
- [Epic Definitions](../epics.md) - Epic 5 story breakdown

### External Best Practices

**SRE Industry Standards (2025):**
- **AWS Well-Architected Framework - Operational Excellence:** Responding to events, runbook best practices, escalation patterns
- **NIST Incident Response Lifecycle:** Preparation, Detection, Analysis, Containment, Eradication, Recovery
- **Google SRE "Three Cs" Framework:** Coordinate, Communicate, Control
- **Runbook Five Principles:** Actionable, Accessible, Accurate, Authoritative, Adaptable

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-04 | Initial production support guide created (Story 5.6) | Dev Agent (AI) |

---

**Document Maintenance:**
- **Review Frequency:** Monthly or after major incidents
- **Owner:** Support Team Lead
- **Update Triggers:** New alert types, architecture changes, common issue patterns, runbook additions

**Feedback:** Report documentation gaps or inaccuracies to Support Team Lead or via `#support-docs-feedback` Slack channel.
