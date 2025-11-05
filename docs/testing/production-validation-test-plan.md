# Production Validation Test Plan
## AI Agents - Ticket Enhancement Platform

**Version:** 1.0
**Date:** 2025-11-04
**Story:** 5.4 - Conduct Production Validation Testing
**Status:** Active
**Test Environment:** Production (https://api.ai-agents.production/)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Test Objectives](#test-objectives)
3. [Test Scope](#test-scope)
4. [Test Environment](#test-environment)
5. [Test Data Requirements](#test-data-requirements)
6. [Test Scenarios](#test-scenarios)
7. [Performance Benchmarks](#performance-benchmarks)
8. [Security Validation](#security-validation)
9. [Error Scenario Testing](#error-scenario-testing)
10. [Alert Verification](#alert-verification)
11. [Test Execution Schedule](#test-execution-schedule)
12. [Success Criteria](#success-criteria)
13. [Roles and Responsibilities](#roles-and-responsibilities)
14. [Test Deliverables](#test-deliverables)

---

## Executive Summary

This production validation test plan defines comprehensive testing procedures to validate the AI Agents ticket enhancement platform in production conditions with real client data. The testing follows 2025 SaaS multi-tenant best practices including continuous production testing, noisy-neighbor simulations, security isolation validation, and performance baseline establishment.

**Key Validation Focus Areas:**
- End-to-end ticket processing with 10+ real production tickets
- Multi-tenant security isolation (Row-Level Security validation)
- Performance baseline metrics (p50/p95/p99 latency, success rate, throughput)
- Error resilience (graceful degradation under failure conditions)
- Monitoring and alerting operational readiness
- Client feedback on enhancement quality

**Testing Duration:** 3-4 days (72-96 hours including 24-48h metric collection period)

**Prerequisites:**
- Production cluster operational (Story 5.1-5.2 complete)
- First production client onboarded (Story 5.3 complete)
- Monitoring stack operational (Epic 4 complete: Prometheus, Grafana, Alertmanager, Jaeger)
- Operational runbooks available (client-onboarding-runbook.md, tenant-troubleshooting-guide.md, alert-runbooks.md)

---

## Test Objectives

### Primary Objectives

1. **Validate End-to-End Functionality** (AC1)
   - Confirm webhook → queue → enhancement → ServiceDesk Plus update workflow functions correctly
   - Process 10+ real production tickets successfully
   - Verify enhancement quality and relevance to ticket issues

2. **Establish Performance Baseline** (AC3)
   - Measure p50/p95/p99 latency for ticket processing
   - Calculate enhancement success rate (target >95%)
   - Analyze queue depth trends and processing bottlenecks
   - Compare results against NFR001 target (p95 <60s)

3. **Confirm Multi-Tenant Isolation** (AC5)
   - Validate Row-Level Security (RLS) prevents cross-tenant data access
   - Test tenant context enforcement at database and API layers
   - Verify Grafana dashboard tenant filtering (if applicable)
   - Confirm Kubernetes namespace isolation (Premium tier)

4. **Validate Error Resilience** (AC4)
   - Test graceful degradation when dependencies fail
   - Verify retry logic and dead-letter queue functionality
   - Confirm error logging and observability
   - Validate webhook signature rejection

5. **Verify Operational Readiness** (AC6)
   - Confirm alert system triggers and routes correctly
   - Validate runbook procedures work as documented
   - Test incident response workflows
   - Verify notification channels (Slack, PagerDuty)

6. **Gather Client Feedback** (AC2)
   - Collect structured feedback from 3+ client technicians
   - Measure enhancement quality (relevance, accuracy, usefulness)
   - Identify improvement opportunities
   - Validate business value proposition

### Secondary Objectives

7. **Noisy Neighbor Testing** (2025 Best Practice)
   - Load one tenant to 90% capacity
   - Measure latency impact on other tenants
   - Verify resource isolation prevents performance degradation

8. **Trace-Based Validation** (2025 Best Practice)
   - Use OpenTelemetry traces for end-to-end request visibility
   - Validate trace propagation across all services
   - Identify performance bottlenecks via distributed tracing

9. **Continuous Testing Foundation**
   - Establish automated regression test suite
   - Document repeatable validation procedures
   - Enable daily/weekly production health checks

---

## Test Scope

### In Scope

**Functional Testing:**
- Webhook reception and signature validation
- Redis queue message processing
- Celery worker enhancement workflow execution
- LangGraph context gathering (ticket history, knowledge base, monitoring data)
- OpenAI GPT-4o-mini enhancement generation
- ServiceDesk Plus API ticket update
- Tenant configuration management
- Row-Level Security enforcement

**Performance Testing:**
- Request latency measurement (p50/p95/p99)
- Throughput and success rate analysis
- Queue depth and worker utilization trends
- Resource consumption monitoring (CPU, memory, network)
- Database query performance

**Security Testing:**
- Multi-tenant data isolation (RLS validation)
- Cross-tenant access prevention
- Webhook signature validation
- API authentication and authorization
- Kubernetes namespace isolation (if applicable)
- Credential encryption verification

**Observability Testing:**
- Prometheus metrics collection
- Grafana dashboard visualization
- Alertmanager notification routing
- Jaeger distributed tracing
- Log aggregation and analysis

**Error Scenario Testing:**
- Knowledge Base timeout (>30s)
- ServiceDesk Plus API failure
- Partial context availability
- Invalid webhook signatures
- Redis connection loss
- PostgreSQL connection failure
- Worker crashes and recovery

**Client Experience Testing:**
- Enhancement quality assessment
- Technician feedback collection
- Business value validation
- Support workflow effectiveness

### Out of Scope

**Explicitly Excluded:**
- Code changes or application modifications
- New feature development
- Infrastructure provisioning (already complete)
- Database schema migrations
- UI/UX development (no admin UI in MVP v1.0)
- Load testing beyond noisy-neighbor validation (separate effort)
- Disaster recovery testing (separate effort)
- Penetration testing (separate security audit)

---

## Test Environment

### Production Environment Details

**Kubernetes Cluster:**
- Cluster Name: ai-agents-production
- Node Count: 3+ (auto-scaling enabled)
- Region: [To be documented based on actual deployment]
- Kubernetes Version: 1.28+

**Deployed Services:**
- **API:** FastAPI webhook receiver (2 replicas)
- **Worker:** Celery workers (3 replicas)
- **Database:** PostgreSQL 17 (RDS Multi-AZ with encryption at rest)
- **Cache:** Redis 7 (ElastiCache or equivalent)
- **Monitoring:** Prometheus, Grafana, Alertmanager, Jaeger

**Network Access:**
- Production API: https://api.ai-agents.production/
- Grafana Dashboard: https://grafana.ai-agents.production/
- Jaeger UI: https://jaeger.ai-agents.production/
- Prometheus: https://prometheus.ai-agents.production/ (internal only)

**Monitoring Stack:**
- Prometheus scrape interval: 15s
- Metric retention: 15 days
- Grafana refresh interval: 5s (configurable per dashboard)
- Jaeger trace retention: 7 days

**Tenant Configuration:**
- Tenant ID: [UUID from Story 5.3 onboarding]
- ServiceDesk Plus Instance: [Client URL]
- Webhook Secret: [Encrypted in Kubernetes secret]
- Knowledge Base: [Configured source]

### Test Tooling

**Automated Test Scripts:**
- `scripts/production-smoke-test.sh` (7 infrastructure health tests)
- `scripts/tenant-onboarding-test.sh` (8 tenant validation tests)
- `scripts/tenant-isolation-validation.sh` (7 RLS security tests)
- `scripts/production-validation-test.sh` (NEW - comprehensive validation suite)

**Command-Line Tools:**
- `curl` - HTTP requests for API testing
- `jq` - JSON parsing in test scripts
- `kubectl` - Kubernetes cluster inspection
- `psql` - PostgreSQL RLS validation queries
- `redis-cli` - Redis queue inspection

**Monitoring Tools:**
- Prometheus (PromQL queries for metrics)
- Grafana (dashboard visualization)
- Jaeger (distributed trace inspection)
- Alertmanager (alert status verification)

### Access Requirements

**Required Credentials:**
- Kubernetes cluster admin access (`kubectl` context configured)
- PostgreSQL superuser credentials (for RLS testing)
- Grafana admin account (for dashboard access)
- ServiceDesk Plus API credentials (for ticket verification)
- Slack workspace access (for alert verification)
- PagerDuty account (for critical alert verification)

**Network Access:**
- VPN connection to production environment (if required)
- Allowlist IP for API access (if IP restrictions enabled)
- SSH access to bastion host (if cluster not publicly accessible)

---

## Test Data Requirements

### Real Production Tickets (MANDATORY)

**Ticket Selection Criteria:**
- **Quantity:** Minimum 10 tickets, recommended 15-20 for statistical significance
- **Source:** Real client ServiceDesk Plus instance (not synthetic test data)
- **Variety:** Diverse ticket types covering common support scenarios
- **Complexity:** Mix of simple (1-2 min resolution) and complex (10+ min investigation)
- **Freshness:** Recent tickets (within last 30 days) for relevant context

**Ticket Type Distribution:**

| Ticket Type | Count | Example Scenarios |
|-------------|-------|-------------------|
| Network Issues | 3-4 | DNS resolution failures, connectivity problems, firewall rules |
| Database Errors | 2-3 | Connection timeouts, query performance, backup/restore issues |
| User Access | 2-3 | Password resets, permission issues, account lockouts |
| Configuration | 2-3 | Application settings, integration configs, system parameters |
| Performance | 1-2 | Slow response times, high CPU/memory, resource exhaustion |
| Hardware | 1-2 | Disk space, server failures, hardware replacement |

### Ticket Data Structure

Each test ticket should include:
```json
{
  "ticket_id": "12345",
  "tenant_id": "uuid-from-story-5.3",
  "title": "Descriptive ticket title",
  "description": "Detailed issue description",
  "category": "Network|Database|Access|Config|Performance|Hardware",
  "priority": "Low|Medium|High|Critical",
  "created_at": "2025-11-04T10:00:00Z",
  "assigned_to": "technician-name",
  "status": "Open|In Progress|Resolved",
  "complexity_estimate": "simple|moderate|complex"
}
```

### Test Tenant Configuration

**Tenant Setup (from Story 5.3):**
- Tenant ID: [UUID documented in Story 5.3 deliverables]
- Tenant Name: [Client organization name]
- ServiceDesk Plus Instance: [Base URL]
- Webhook URL: https://api.ai-agents.production/api/v1/webhook
- Webhook Secret: [HMAC-SHA256 key stored in K8s secret]
- Knowledge Base Sources: [Configured KB endpoints]

**Additional Test Tenant (if available):**
- For cross-tenant isolation testing, a second tenant configuration is highly recommended
- Tenant B ID: [Secondary tenant UUID]
- Ensures realistic multi-tenant validation

### Synthetic Error Scenarios

**Intentional Failure Conditions (for AC4 testing):**

1. **Knowledge Base Timeout Simulation:**
   - Mock KB API with 35s response delay
   - Expected: System continues with partial context, logs warning, completes <75s

2. **ServiceDesk Plus API Failure:**
   - Temporarily disable ServiceDesk Plus API (coordination required)
   - Expected: 3 retry attempts (1s, 2s, 4s backoff), dead-letter queue, alert fires

3. **Partial Context Scenario:**
   - Limit ticket history to 1 result, remove KB matches
   - Expected: Enhancement generated with available data, quality may be reduced

4. **Invalid Webhook Signature:**
   - Send webhook with incorrect HMAC-SHA256 signature
   - Expected: 401 Unauthorized response, no job queued, security log entry

---

## Test Scenarios

### Scenario 1: End-to-End Ticket Processing (AC1)

**Objective:** Validate complete ticket enhancement workflow with real production tickets

**Prerequisites:**
- Production cluster operational
- Tenant configured with valid ServiceDesk Plus credentials
- Monitoring stack collecting metrics
- 10+ real production tickets identified

**Test Steps:**

1. **Webhook Submission**
   - Send webhook POST request to `/api/v1/webhook` for each test ticket
   - Include valid HMAC-SHA256 signature in `X-ServiceDesk-Signature` header
   - Payload: `{tenant_id, ticket_id, event_type: "created", payload: {...}}`
   - Expected: HTTP 202 Accepted response

2. **Queue Validation**
   - Check Redis queue for enqueued job: `redis-cli LLEN ai_agents:queue`
   - Expected: Job count increases by 1 per webhook
   - Verify job payload contains tenant_id and ticket_id

3. **Worker Processing**
   - Monitor Celery worker logs: `kubectl logs -f deployment/worker -n ai-agents`
   - Expected: Worker picks up job within 5 seconds
   - Verify context gathering executes (ticket history, KB search, monitoring data)

4. **LangGraph Workflow Execution**
   - Observe LangGraph enhancement workflow execution
   - Expected: All workflow nodes execute successfully (gather_context → synthesize → format)
   - Verify OpenAI API call returns enhancement text

5. **ServiceDesk Plus Update**
   - Check ServiceDesk Plus ticket notes via API or UI
   - Expected: Enhancement posted to ticket within 60s (p95 latency target)
   - Verify enhancement content is relevant and formatted correctly (HTML)

6. **Distributed Tracing Validation**
   - Query Jaeger for trace ID: Search by `ticket_id` tag
   - Expected: Complete trace with spans (webhook → queue → worker → KB → LLM → ServiceDesk)
   - Verify no error spans, latency breakdown visible

7. **Metrics Collection**
   - Query Prometheus for metrics:
     - `enhancement_requests_total{tenant_id="<uuid>"}` (increments by 1)
     - `enhancement_duration_seconds{tenant_id="<uuid>"}` (histogram bucket counts increase)
     - `enhancement_success_rate{tenant_id="<uuid>"}` (should be 1.0 for success)
   - Expected: All metrics updated within 30 seconds of completion

**Repeat for All 10+ Test Tickets**

**Success Criteria:**
- ✅ All 10+ tickets processed successfully (100% success rate)
- ✅ p95 latency <60s (per NFR001)
- ✅ Enhancements posted to ServiceDesk Plus tickets
- ✅ Complete distributed traces available in Jaeger
- ✅ Prometheus metrics accurately reflect processing

**Documentation:**
- Record ticket IDs, processing times, enhancement summaries
- Capture Jaeger trace IDs for reference
- Screenshot Grafana dashboard showing real-time processing
- Document any failures or anomalies

---

### Scenario 2: Performance Baseline Collection (AC3)

**Objective:** Establish performance baseline metrics for future monitoring and SLO definition

**Prerequisites:**
- 10+ tickets processed successfully (Scenario 1 complete)
- 24-48 hour metric collection period allocated
- Grafana dashboards operational

**Test Steps:**

1. **Configure 24-48 Hour Collection Period**
   - Start time: [YYYY-MM-DD HH:MM:SS UTC]
   - End time: [YYYY-MM-DD HH:MM:SS UTC] (24-48 hours later)
   - Ensure continuous production traffic during collection period

2. **Measure p50/p95/p99 Latency**
   - PromQL Query:
     ```promql
     # p50 latency
     histogram_quantile(0.50, rate(enhancement_duration_seconds_bucket{tenant_id="<uuid>"}[5m]))

     # p95 latency
     histogram_quantile(0.95, rate(enhancement_duration_seconds_bucket{tenant_id="<uuid>"}[5m]))

     # p99 latency
     histogram_quantile(0.99, rate(enhancement_duration_seconds_bucket{tenant_id="<uuid>"}[5m]))
     ```
   - Execute queries hourly and document results
   - Export Grafana dashboard graphs (Per-Tenant Metrics Dashboard)

3. **Calculate Enhancement Success Rate**
   - PromQL Query:
     ```promql
     # Success rate percentage over 1h window
     (rate(enhancement_success_rate_total{tenant_id="<uuid>",status="success"}[1h])
      / rate(enhancement_success_rate_total{tenant_id="<uuid>"}[1h])) * 100
     ```
   - Expected: >95% success rate (per NFR001)
   - Document hourly success rate, identify any dips

4. **Analyze Queue Depth Trends**
   - PromQL Query:
     ```promql
     # Current queue depth
     queue_depth{queue="ai_agents:queue"}

     # Average queue depth over 1h
     avg_over_time(queue_depth{queue="ai_agents:queue"}[1h])

     # Max queue depth over 1h
     max_over_time(queue_depth{queue="ai_agents:queue"}[1h])
     ```
   - Identify peak queue periods (business hours vs off-hours)
   - Correlate queue depth with latency spikes
   - Export Grafana Queue Health Dashboard graphs

5. **Measure Processing Time Per Ticket**
   - PromQL Query:
     ```promql
     # Average processing time
     rate(enhancement_duration_seconds_sum{tenant_id="<uuid>"}[5m])
       / rate(enhancement_duration_seconds_count{tenant_id="<uuid>"}[5m])
     ```
   - Break down by ticket complexity (if labeled)
   - Document typical vs outlier processing times

6. **Worker Utilization Analysis**
   - PromQL Query:
     ```promql
     # Active worker count
     worker_active_count

     # Worker utilization percentage
     (worker_active_count / 3) * 100  # 3 = total worker replicas
     ```
   - Identify if workers are saturated (100% utilization)
   - Determine if auto-scaling is required

**Success Criteria:**
- ✅ p95 latency <60s (NFR001 compliance)
- ✅ Success rate >95% sustained over 24-48h
- ✅ Queue depth averages <10 during normal load
- ✅ Worker utilization <80% (headroom for spikes)
- ✅ Baseline metrics documented with graphs

**Documentation:**
- Create `performance-baseline-metrics.md` with:
  - Latency distribution (p50/p95/p99) graphs from Grafana
  - Success rate trends over collection period
  - Queue depth analysis with peak identification
  - Processing time breakdown by ticket type
  - Comparison to NFR001 targets with compliance assessment

---

### Scenario 3: Multi-Tenant Security Isolation (AC5)

**Objective:** Validate Row-Level Security and tenant isolation at all layers

**Prerequisites:**
- Two tenant configurations available (Tenant A and Tenant B preferred)
- PostgreSQL superuser access for RLS validation
- API credentials for both tenants

**Test Steps:**

1. **Execute Automated RLS Tests**
   - Run existing test script:
     ```bash
     cd /Users/ravi/Documents/nullBytes_Apps/Ai_Agents/AI\ Ops
     ./scripts/tenant-isolation-validation.sh
     ```
   - Expected: All 7 tests pass
   - Tests validate:
     - Session context enforcement (`set_tenant_context` function)
     - Row visibility with different tenant contexts
     - INSERT/UPDATE/DELETE isolation
     - Cross-tenant query prevention
   - Document test output, screenshot pass/fail results

2. **Manual RLS Validation Queries**
   - Connect to PostgreSQL: `psql -h <db-host> -U ai_agents -d ai_agents_db`
   - Test Tenant A context:
     ```sql
     -- Set Tenant A context
     SELECT set_tenant_context('<tenant-a-uuid>');

     -- Query enhancement history (should only return Tenant A data)
     SELECT COUNT(*) FROM enhancement_history;
     SELECT tenant_id, ticket_id, created_at FROM enhancement_history LIMIT 5;
     ```
   - Verify all returned rows have `tenant_id = <tenant-a-uuid>`

   - Test Tenant B context:
     ```sql
     -- Set Tenant B context
     SELECT set_tenant_context('<tenant-b-uuid>');

     -- Query enhancement history (should only return Tenant B data)
     SELECT COUNT(*) FROM enhancement_history;
     SELECT tenant_id, ticket_id, created_at FROM enhancement_history LIMIT 5;
     ```
   - Verify all returned rows have `tenant_id = <tenant-b-uuid>`

   - Test cross-tenant access attempt:
     ```sql
     -- Set Tenant A context
     SELECT set_tenant_context('<tenant-a-uuid>');

     -- Attempt to query Tenant B's data (should return 0 rows)
     SELECT COUNT(*) FROM enhancement_history WHERE tenant_id = '<tenant-b-uuid>';
     ```
   - Expected: COUNT = 0 (RLS prevents cross-tenant visibility)

3. **API-Level Cross-Tenant Access Test**
   - Attempt to query Tenant A data with Tenant B credentials:
     ```bash
     # Use Tenant B's API token to query Tenant A's enhancements
     curl -X GET "https://api.ai-agents.production/api/v1/enhancements?tenant_id=<tenant-a-uuid>" \
       -H "Authorization: Bearer <tenant-b-token>" \
       -H "Content-Type: application/json"
     ```
   - Expected: HTTP 403 Forbidden response
   - Verify error message indicates insufficient permissions
   - Confirm no Tenant A data returned in response

4. **Grafana Dashboard Tenant Filtering (if applicable)**
   - Login to Grafana as Tenant A user
   - Access Per-Tenant Metrics Dashboard
   - Verify dashboard shows only Tenant A metrics (tenant_id label filter applied)
   - Attempt to modify dashboard filter to show Tenant B data
   - Expected: Either filter change blocked or Tenant B data not visible (RLS enforced)

   - Repeat for Tenant B user login
   - Confirm isolation is bidirectional

5. **Kubernetes Namespace Isolation (Premium Tier, if applicable)**
   - Check if tenants have dedicated namespaces:
     ```bash
     kubectl get namespaces | grep tenant
     ```
   - If Premium tier with dedicated namespaces:
     - Test pod-to-pod communication across namespaces:
       ```bash
       # Exec into Tenant A pod
       kubectl exec -it -n tenant-a <pod-name> -- /bin/sh

       # Attempt to curl Tenant B service (should fail)
       curl http://api-service.tenant-b.svc.cluster.local/health
       ```
     - Expected: Connection timeout or network policy block
     - Verify Kubernetes NetworkPolicy prevents cross-namespace communication

6. **Secrets and ConfigMap Isolation**
   - Verify Tenant A cannot access Tenant B secrets:
     ```bash
     # Exec into Tenant A pod
     kubectl exec -it -n tenant-a <pod-name> -- /bin/sh

     # Attempt to read Tenant B secret (should fail)
     kubectl get secret tenant-b-webhook-secret -n tenant-b
     ```
   - Expected: Permission denied error
   - Confirm RBAC policies prevent cross-tenant secret access

**Success Criteria:**
- ✅ All 7 automated RLS tests pass (tenant-isolation-validation.sh)
- ✅ Manual SQL queries confirm row-level isolation
- ✅ API cross-tenant access blocked with 403 Forbidden
- ✅ Grafana dashboards filter by tenant (no cross-tenant visibility)
- ✅ Kubernetes namespace isolation functional (if applicable)
- ✅ No security vulnerabilities identified

**Documentation:**
- Document test results with pass/fail status
- Screenshot SQL query outputs showing RLS enforcement
- Capture API error responses (403 Forbidden)
- Security posture assessment: "Multi-tenant isolation VERIFIED at database, API, and infrastructure layers"

---

### Scenario 4: Error Scenario Testing (AC4)

**Objective:** Validate graceful degradation and error handling under failure conditions

**Prerequisites:**
- Coordination with infrastructure team for controlled failures
- Access to modify service configurations temporarily
- Monitoring dashboards active for observability

**Test Steps:**

#### Test 4.1: Knowledge Base Timeout

**Setup:**
- Configure Knowledge Base API mock to respond after 35 seconds (simulating timeout)
- OR use network policy to introduce 35s delay

**Execution:**
1. Send webhook for test ticket requiring KB search
2. Monitor worker logs for KB timeout warning
3. Verify enhancement completes with partial context (no KB results)
4. Measure total processing time

**Expected Results:**
- ⏱️ Total processing time: 60-75 seconds (KB timeout 30s + fallback processing)
- ⚠️ Warning logged: "Knowledge Base search timed out after 30s, proceeding with partial context"
- ✅ Enhancement generated using available context (ticket history, monitoring data)
- ✅ ServiceDesk Plus ticket updated successfully (degraded quality acceptable)
- 📊 Prometheus metric `kb_timeout_total` increments

**Documentation:**
- Log entries showing timeout and fallback behavior
- Enhancement content comparison (with KB vs without KB)
- Processing time breakdown from Jaeger trace

---

#### Test 4.2: ServiceDesk Plus API Failure

**Setup:**
- Temporarily disable ServiceDesk Plus API endpoint (coordination with client)
- OR use network policy to block ServiceDesk Plus API traffic
- Duration: 5-10 minutes

**Execution:**
1. Send webhook for test ticket during ServiceDesk Plus API outage
2. Monitor worker logs for retry attempts
3. Verify dead-letter queue receives failed job
4. Check alert firing in Alertmanager
5. Restore ServiceDesk Plus API access
6. Verify failed jobs reprocessed from dead-letter queue (if auto-retry configured)

**Expected Results:**
- 🔄 3 retry attempts with exponential backoff (1s, 2s, 4s delays)
- 📝 Each retry logged: "ServiceDesk Plus API error, retry attempt 1/3"
- ❌ After 3 failures, job moved to dead-letter queue
- 🚨 Alert fires: "EnhancementFailureRateHigh" (after 3 consecutive failures)
- 📬 Notification sent to Slack #alerts channel
- 🔧 Dead-letter queue job: `redis-cli LLEN ai_agents:dead_letter` shows +1

**Documentation:**
- Worker log entries showing retry logic
- Retry delay timing verification (1s → 2s → 4s)
- Alertmanager alert screenshot (firing state)
- Slack notification screenshot
- Dead-letter queue inspection output

---

#### Test 4.3: Partial Context Availability

**Setup:**
- Configure test ticket with limited ticket history (only 1 previous ticket)
- Ensure no Knowledge Base matches for ticket keywords
- Remove/disable monitoring data source temporarily

**Execution:**
1. Send webhook for test ticket with minimal context
2. Monitor context gathering phase in worker logs
3. Verify enhancement generated despite limited context
4. Compare enhancement quality to full-context scenarios

**Expected Results:**
- 📉 Context gathering finds only 1 ticket history result
- 🔍 Knowledge Base search returns 0 matches
- 📊 Monitoring data unavailable or empty
- ✅ Enhancement still generated with available context
- ⚠️ Enhancement quality may be lower (less specific recommendations)
- ℹ️ Log entry: "Partial context available: 1 ticket history, 0 KB results, 0 monitoring events"

**Documentation:**
- Context gathering results summary
- Enhancement content generated with partial context
- Quality comparison: partial context vs full context
- Latency comparison (should be faster with less context gathering)

---

#### Test 4.4: Invalid Webhook Signature

**Setup:**
- Prepare test webhook payload with incorrect HMAC-SHA256 signature
- Use different webhook secret or omit signature header

**Execution:**
1. Send POST request to `/api/v1/webhook` with invalid signature:
   ```bash
   curl -X POST "https://api.ai-agents.production/api/v1/webhook" \
     -H "Content-Type: application/json" \
     -H "X-ServiceDesk-Signature: sha256=INVALID_SIGNATURE_HERE" \
     -d '{"tenant_id": "<uuid>", "ticket_id": "12345", "event_type": "created", "payload": {...}}'
   ```
2. Verify HTTP 401 Unauthorized response
3. Check security logs for rejected webhook attempt
4. Confirm no job queued in Redis

**Expected Results:**
- 🚫 HTTP 401 Unauthorized response
- 🔒 Error message: "Invalid webhook signature"
- 📝 Security log entry with IP address, timestamp, tenant_id
- ❌ Redis queue count unchanged (no job enqueued)
- 📊 Prometheus metric `webhook_signature_failures_total` increments

**Documentation:**
- curl command and HTTP 401 response
- Error response JSON payload
- Security log entry screenshot
- Redis queue verification (`LLEN` before/after shows no change)

---

#### Test 4.5: Additional Error Scenarios (Optional)

**Redis Connection Loss:**
- Temporarily stop Redis container: `docker-compose stop redis`
- Send webhook, verify API returns 503 Service Unavailable
- Restart Redis, verify service recovers

**PostgreSQL Connection Failure:**
- Block PostgreSQL network traffic temporarily
- Verify worker logs show database connection errors
- Confirm graceful degradation (service attempts reconnection)

**Worker Crash Recovery:**
- Kill worker pod: `kubectl delete pod <worker-pod-name>`
- Verify Kubernetes restarts pod automatically (Deployment controller)
- Confirm in-flight jobs recover (Celery task acknowledgment)

**Success Criteria:**
- ✅ KB timeout: System continues with partial context, <75s total processing
- ✅ ServiceDesk Plus failure: 3 retries, dead-letter queue, alert fires
- ✅ Partial context: Enhancement generated with available data
- ✅ Invalid signature: 401 response, no job queued, security logged
- ✅ All error scenarios handled gracefully (no crashes)

**Documentation:**
- Create section in `production-validation-report.md`:
  - Error Scenario Testing Results
  - Response codes, retry attempts, recovery time
  - Graceful degradation assessment: PASSED

---

### Scenario 5: Alert Verification (AC6)

**Objective:** Validate monitoring alerts trigger correctly and route to appropriate notification channels

**Prerequisites:**
- Alertmanager configured with Slack and PagerDuty integrations
- Access to Slack #alerts channel
- PagerDuty on-call schedule configured
- Grafana Alert History dashboard operational

**Test Steps:**

#### Test 6.1: High Latency Alert

**Setup:**
- Inject artificial delay in Celery worker processing
- Modify worker code temporarily OR use network delay simulation

**Execution:**
1. Inject 3+ minute delay in enhancement workflow:
   ```python
   # Temporary code injection in worker
   import time
   time.sleep(180)  # 3 minute delay
   ```
2. Send webhook for test ticket
3. Monitor Alertmanager for alert firing
4. Check Slack #alerts channel for notification

**Expected Results:**
- ⏱️ Processing time exceeds 120s (alert threshold)
- 🚨 Alert fires: "HighLatencyP95" within 5 minutes of threshold breach
- 📬 Slack notification received in #alerts channel
- 📊 Grafana Alert History dashboard shows alert in "Firing" state
- ℹ️ Alert includes: Severity (warning), Latency value (e.g., 185s), Runbook URL

**Verification:**
- Screenshot Slack notification with timestamp
- Verify runbook URL links to `docs/operations/alert-runbooks.md`
- Confirm alert auto-resolves after latency returns to normal

---

#### Test 6.2: Failed Enhancement Alert

**Setup:**
- Send intentionally malformed webhook causing enhancement failure
- Invalid tenant_id or corrupted payload

**Execution:**
1. Send webhook with invalid tenant_id:
   ```bash
   curl -X POST "https://api.ai-agents.production/api/v1/webhook" \
     -H "Content-Type: application/json" \
     -H "X-ServiceDesk-Signature: <valid-signature>" \
     -d '{"tenant_id": "00000000-0000-0000-0000-000000000000", "ticket_id": "99999", "event_type": "created", "payload": {}}'
   ```
2. Repeat 3 times consecutively (alert threshold)
3. Monitor Alertmanager for alert firing
4. Check Slack and PagerDuty for notifications

**Expected Results:**
- ❌ 3 consecutive enhancement failures
- 🚨 Alert fires: "EnhancementFailureRateHigh" (critical severity)
- 📬 Slack notification sent to #alerts
- 📟 PagerDuty incident created and assigned to on-call engineer
- 📊 Alert includes: Failure count, Error type, Runbook link

**Verification:**
- Screenshot PagerDuty incident with details
- Confirm escalation policy triggered (if configured)
- Verify alert acknowledges correctly in PagerDuty
- Check alert resolution after sending successful webhooks

---

#### Test 6.3: Queue Backup Alert

**Setup:**
- Stop Celery workers temporarily: `kubectl scale deployment/worker --replicas=0`
- Send 50+ webhook requests to queue jobs

**Execution:**
1. Scale down workers: `kubectl scale deployment/worker --replicas=0 -n ai-agents`
2. Send 50 webhook requests rapidly:
   ```bash
   for i in {1..50}; do
     curl -X POST "https://api.ai-agents.production/api/v1/webhook" \
       -H "Content-Type: application/json" \
       -H "X-ServiceDesk-Signature: <valid-signature>" \
       -d '{"tenant_id": "<uuid>", "ticket_id": "QUEUE_TEST_'$i'", "event_type": "created", "payload": {}}'
   done
   ```
3. Monitor Redis queue depth: `redis-cli LLEN ai_agents:queue`
4. Wait for alert to fire (threshold: queue_depth >25)
5. Check Slack notification

**Expected Results:**
- 📈 Queue depth increases to 50+
- 🚨 Alert fires: "QueueDepthHigh" when depth exceeds 25
- 📬 Slack notification: "Queue backup detected, depth: 50+"
- ⏱️ Alert fires within 5 minutes of threshold breach
- 🔧 Alert includes recommended action: "Scale worker replicas"

**Verification:**
- Screenshot Redis queue depth output
- Slack notification with queue depth value
- Grafana Queue Health dashboard showing queue spike
- Restore workers: `kubectl scale deployment/worker --replicas=3`
- Verify alert auto-resolves as queue drains

---

#### Test 6.4: Notification Routing Verification

**Objective:** Confirm alerts route to correct channels based on severity

**Test Matrix:**

| Alert Name | Severity | Slack | PagerDuty | Email |
|------------|----------|-------|-----------|-------|
| HighLatencyP95 | Warning | ✅ #alerts | ❌ No | ✅ Ops team |
| EnhancementFailureRateHigh | Critical | ✅ #alerts | ✅ On-call | ✅ Ops team + Manager |
| QueueDepthHigh | Warning | ✅ #alerts | ❌ No | ✅ Ops team |
| WorkerDown | Critical | ✅ #alerts | ✅ On-call | ✅ Ops team + Manager |

**Execution:**
- Trigger each alert type (methods described above)
- Verify routing matches expected channels
- Document actual vs expected routing

**Expected Results:**
- ✅ All warning alerts → Slack only (no PagerDuty escalation)
- ✅ All critical alerts → Slack + PagerDuty incident creation
- ✅ Email notifications sent to configured recipients
- ✅ PagerDuty incidents respect escalation policy

---

#### Test 6.5: Alert Resolution and History

**Objective:** Verify alert resolution workflow and historical tracking

**Execution:**
1. Trigger High Latency alert (Test 6.1)
2. Wait for alert to fire
3. Resolve condition (remove artificial delay)
4. Verify alert auto-resolves in Alertmanager
5. Check Grafana Alert History dashboard

**Expected Results:**
- ✅ Alert transitions from "Firing" to "Resolved" state
- ⏱️ Resolution time documented in Alert History
- 📊 Grafana shows alert duration graph
- 📬 Resolution notification sent to Slack (optional)
- 📈 Historical alert data retained for trend analysis

**Verification:**
- Screenshot Alertmanager showing alert lifecycle (Pending → Firing → Resolved)
- Grafana Alert History dashboard with alert timeline
- Calculate Mean Time to Resolve (MTTR) from alert data

---

**Success Criteria (AC6 - Overall):**
- ✅ High latency alert fires within 5 minutes, Slack notification received
- ✅ Failed enhancement alert fires after 3 failures, PagerDuty incident created
- ✅ Queue backup alert fires at threshold (depth >25), actionable message
- ✅ Routing verified: Warning → Slack, Critical → Slack + PagerDuty
- ✅ Alerts resolve automatically when conditions normalize
- ✅ Alert history tracked in Grafana for retrospective analysis

**Documentation:**
- Create alert verification summary table
- Screenshot all triggered alerts (Alertmanager, Slack, PagerDuty)
- Document alert response times (time to fire, time to notify)
- Validate runbook links work correctly
- Include in `production-validation-report.md` Alert System section

---

## Performance Benchmarks

### Target Performance Metrics (from NFR001)

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| p50 Latency | <30s | `histogram_quantile(0.50, rate(enhancement_duration_seconds_bucket[5m]))` |
| p95 Latency | <60s | `histogram_quantile(0.95, rate(enhancement_duration_seconds_bucket[5m]))` |
| p99 Latency | <90s | `histogram_quantile(0.99, rate(enhancement_duration_seconds_bucket[5m]))` |
| Success Rate | >95% | `(success_count / total_count) * 100` |
| Queue Depth (avg) | <10 | `avg_over_time(queue_depth[1h])` |
| Worker Utilization | <80% | `(active_workers / total_workers) * 100` |

### Baseline Collection Requirements

- **Collection Period:** 24-48 hours minimum for statistical significance
- **Traffic Volume:** Minimum 50 tickets processed during period (natural production traffic preferred)
- **Monitoring Resolution:** 15-second scrape interval (Prometheus default)
- **Visualization:** Export Grafana dashboard graphs for executive summary

### Expected Performance Ranges

Based on architecture design and Epic 2-4 implementation:

- **Webhook → Queue:** <1s (synchronous HTTP + Redis LPUSH)
- **Queue → Worker Pickup:** 1-5s (Celery polling interval)
- **Context Gathering:** 5-15s (ticket history query + KB search + monitoring data fetch)
- **LLM Synthesis:** 10-25s (OpenAI GPT-4o-mini API call)
- **ServiceDesk Plus Update:** 2-5s (HTTP POST with retry logic)
- **Total End-to-End:** 20-50s typical, <60s p95 target

### Noisy Neighbor Testing (2025 Best Practice)

**Test Procedure:**
1. Load Tenant A to 90% capacity (queue 100+ jobs)
2. Measure Tenant B latency during Tenant A load spike
3. Expected: Tenant B latency increase <20% (resource isolation effective)
4. Document: RLS performance impact, database query isolation overhead

**Resource Isolation Validation:**
- No single tenant should consume >40% CPU of shared node
- Memory isolation via Kubernetes resource limits (if configured)
- Database connection pooling per tenant (if configured)

---

## Security Validation

### Multi-Tenant Isolation Testing

**Critical Security Controls:**

1. **Row-Level Security (RLS) - Database Layer**
   - Enforcement: PostgreSQL RLS policies on all tenant tables
   - Validation: `tenant-isolation-validation.sh` (7 automated tests)
   - Manual testing: Cross-tenant SQL queries (expected: 0 rows returned)

2. **API Authentication - Application Layer**
   - Enforcement: Bearer token validation with tenant_id claim
   - Validation: Cross-tenant API requests (expected: HTTP 403 Forbidden)
   - Test invalid tokens (expected: HTTP 401 Unauthorized)

3. **Webhook Signature Validation - Entry Point**
   - Enforcement: HMAC-SHA256 signature verification
   - Validation: Invalid signature test (expected: HTTP 401 Unauthorized, no job queued)
   - Replay attack prevention (timestamp validation)

4. **Kubernetes Namespace Isolation - Infrastructure Layer** (Premium tier)
   - Enforcement: NetworkPolicy restricting pod-to-pod communication
   - Validation: Cross-namespace curl attempts (expected: connection timeout)
   - RBAC validation: Tenant A ServiceAccount cannot access Tenant B secrets

5. **Data Encryption**
   - At Rest: PostgreSQL RDS encryption enabled (AWS KMS)
   - In Transit: TLS 1.2+ for all API endpoints (HTTPS)
   - Secrets: Kubernetes Secrets encrypted at rest (etcd encryption)

### Security Test Coverage

| Security Control | Test Method | Expected Result | Priority |
|------------------|-------------|-----------------|----------|
| RLS Enforcement | tenant-isolation-validation.sh | All 7 tests pass | CRITICAL |
| Cross-Tenant API Access | curl with wrong tenant token | HTTP 403 Forbidden | CRITICAL |
| Invalid Webhook Signature | curl with bad HMAC | HTTP 401 Unauthorized | HIGH |
| TLS Certificate Validity | curl https://api.ai-agents.production/ | Valid cert, no warnings | HIGH |
| Secret Encryption | kubectl get secret -o yaml | base64 encoded data | MEDIUM |
| Namespace Isolation | Cross-namespace pod curl | Connection timeout | MEDIUM (Premium) |

### 2025 Security Best Practices Applied

- **Zero Trust Architecture:** All requests authenticated and authorized (no implicit trust)
- **Least Privilege Access:** RBAC policies grant minimum required permissions
- **Defense in Depth:** Multiple isolation layers (RLS + API auth + namespace isolation)
- **Audit Logging:** All tenant operations logged with tenant_id for accountability
- **Secret Rotation:** Support for webhook secret rotation without downtime (manual process documented)

---

## Error Scenario Testing

### Fault Injection Test Matrix

| Error Scenario | Trigger Method | Expected Behavior | Validation Method |
|----------------|----------------|-------------------|-------------------|
| KB Timeout (>30s) | Mock KB API with 35s delay | Continue with partial context, <75s total | Worker logs + Jaeger trace |
| ServiceDesk Plus API Failure | Disable API temporarily | 3 retries (1s, 2s, 4s), dead-letter queue, alert | Worker logs + Redis inspection |
| Partial Context | Limit ticket history to 1 result | Enhancement generated with available data | Compare enhancement quality |
| Invalid Webhook Signature | Send webhook with bad HMAC | HTTP 401, no job queued, security log | curl response + Redis count |
| Redis Connection Loss | Stop Redis container | API returns 503, jobs lost warning | API health endpoint |
| PostgreSQL Connection Failure | Block DB traffic | Worker retry logic, circuit breaker | Worker logs + metrics |
| Worker Crash | Kill worker pod | Kubernetes restarts pod, jobs requeued | kubectl logs + Celery acknowledgment |
| Rate Limiting (OpenAI) | Send 100 requests rapidly | Queue backlog, retry after rate limit window | OpenAI API error logs |

### Graceful Degradation Requirements

**Acceptable Degradation:**
- ✅ KB timeout → Enhancement quality reduced but still useful
- ✅ Partial context → Enhancement generated with disclaimers
- ✅ Monitoring data unavailable → Enhancement focuses on ticket history

**Unacceptable Failures:**
- ❌ Worker crash → No enhancement posted (must recover via retry)
- ❌ Invalid signature → Job queued anyway (security violation)
- ❌ RLS bypass → Cross-tenant data visible (critical security failure)

### Error Handling Validation

**Retry Logic Testing:**
- Verify exponential backoff delays (1s → 2s → 4s)
- Confirm max retry limit (3 attempts)
- Validate dead-letter queue receives failed jobs
- Test idempotency (duplicate webhook with same ticket_id should not create duplicate enhancement)

**Circuit Breaker Pattern (if implemented):**
- Test circuit opens after 5 consecutive failures
- Verify circuit closes after success threshold met
- Confirm fallback behavior during open circuit

---

## Alert Verification

### Alert Definitions from Epic 4

| Alert Name | Condition | Threshold | Severity | Routing |
|------------|-----------|-----------|----------|---------|
| HighLatencyP95 | p95 latency >120s | 120s | Warning | Slack #alerts |
| EnhancementFailureRateHigh | Success rate <95% | 95% | Critical | Slack + PagerDuty |
| QueueDepthHigh | Queue depth >100 | 100 jobs | Warning | Slack #alerts |
| WorkerDown | Worker count = 0 | 0 workers | Critical | Slack + PagerDuty |
| DatabaseConnectionFailure | DB connection errors >5/min | 5/min | Critical | Slack + PagerDuty |

### Alert Testing Procedures

**For Each Alert:**
1. **Trigger Condition:** Intentionally cause alert threshold breach
2. **Verify Firing:** Confirm alert appears in Alertmanager (Firing state)
3. **Check Notification:** Verify message received in Slack/PagerDuty
4. **Validate Content:** Alert includes severity, metric value, runbook URL
5. **Test Resolution:** Resolve condition, verify alert auto-resolves
6. **Check History:** Confirm alert logged in Grafana Alert History dashboard

### Runbook Validation

**For Each Alert Runbook:**
- Follow diagnostic steps documented in `docs/operations/alert-runbooks.md`
- Verify commands execute without errors
- Confirm diagnostic steps identify root cause
- Test resolution procedures resolve issue
- Document any gaps or inaccuracies in runbook

### Notification Channel Testing

**Slack Integration:**
- Verify webhook URL configured correctly
- Test message formatting (readable, actionable)
- Confirm #alerts channel receives notifications
- Validate mentions/tags for critical alerts (if configured)

**PagerDuty Integration:**
- Verify Events API v2 integration key configured
- Test incident creation for critical alerts
- Confirm on-call schedule assignment
- Validate escalation policy triggers (if multi-tier)
- Test incident acknowledgment and resolution

**Email Notifications (if configured):**
- Verify recipient list includes operations team
- Test email delivery (check spam filters)
- Confirm email formatting includes alert details

---

## Test Execution Schedule

### Day 1: End-to-End Validation & Alert Testing

**Morning (9:00 AM - 12:00 PM):**
- Execute Scenario 1: End-to-End Ticket Processing
  - Process 10+ real production tickets
  - Monitor via Jaeger distributed tracing
  - Verify ServiceDesk Plus updates
  - Document results

**Afternoon (1:00 PM - 5:00 PM):**
- Execute Scenario 5: Alert Verification
  - Test 6.1: High Latency Alert
  - Test 6.2: Failed Enhancement Alert
  - Test 6.3: Queue Backup Alert
  - Test 6.4: Notification Routing
  - Test 6.5: Alert Resolution
- Execute Scenario 4: Error Scenario Testing
  - Test 4.1: KB Timeout
  - Test 4.2: ServiceDesk Plus API Failure
  - Test 4.3: Partial Context
  - Test 4.4: Invalid Webhook Signature

**Evening (5:00 PM - 6:00 PM):**
- Review Day 1 test results
- Document any failures or anomalies
- Initiate 24-48 hour metric collection period (Scenario 2)

---

### Day 2: Security Validation & Continuous Monitoring

**Morning (9:00 AM - 12:00 PM):**
- Execute Scenario 3: Multi-Tenant Security Isolation
  - Test 5.1: Automated RLS tests (tenant-isolation-validation.sh)
  - Test 5.2: Manual RLS validation queries
  - Test 5.3: API cross-tenant access test
  - Test 5.4: Grafana dashboard tenant filtering
  - Test 5.5: Kubernetes namespace isolation (if applicable)

**Afternoon (1:00 PM - 5:00 PM):**
- Execute 2025 Best Practice Tests:
  - Noisy Neighbor Simulation (load Tenant A to 90%, measure Tenant B impact)
  - Trace-Based Validation (Jaeger trace inspection for all processed tickets)
  - Continuous Testing Setup (automate production-validation-test.sh)
- Monitor ongoing 24-48h metric collection
- Review Grafana dashboards for anomalies

**Evening (5:00 PM - 6:00 PM):**
- Document Day 2 security validation results
- Check metric collection progress (12-24h into collection period)

---

### Day 3: Client Feedback & Metric Analysis

**Morning (9:00 AM - 12:00 PM):**
- Coordinate with client for technician feedback
  - Send client feedback survey (Task 2.1 deliverable)
  - Schedule 15-20 min interviews with 3+ technicians
  - Collect structured responses (5-point scale + qualitative)

**Afternoon (1:00 PM - 5:00 PM):**
- Execute Scenario 2: Performance Baseline Collection
  - Analyze 24-48h metric collection data
  - Calculate p50/p95/p99 latency from Prometheus
  - Measure success rate over collection period
  - Analyze queue depth trends
  - Export Grafana dashboard graphs
- Document performance baseline in `performance-baseline-metrics.md`

**Evening (5:00 PM - 6:00 PM):**
- Compile client feedback results
- Create `client-feedback-survey-results.md`
- Begin drafting `production-validation-report.md`

---

### Day 4: Report Generation & Stakeholder Review

**Morning (9:00 AM - 12:00 PM):**
- Complete `production-validation-report.md`:
  - Executive summary (1-2 pages)
  - Test results overview (all ACs)
  - Performance data analysis
  - Client feedback summary
  - Issues found and remediation plan
  - Recommendations for improvements

**Afternoon (1:00 PM - 3:00 PM):**
- Review report with internal stakeholders:
  - Operations team
  - Engineering lead
  - Product manager
- Address any questions or clarifications

**Late Afternoon (3:00 PM - 5:00 PM):**
- Finalize all deliverables:
  - `production-validation-test-plan.md` (this document)
  - `production-validation-test.sh` (automated test script)
  - `performance-baseline-metrics.md` (24-48h data)
  - `client-feedback-survey-results.md` (technician feedback)
  - `production-validation-report.md` (comprehensive findings)
- Share report with client account manager (as appendix to client review)
- Mark Story 5.4 as complete

---

## Success Criteria

### Acceptance Criteria Mapping

| AC | Description | Success Criteria | Validation Method |
|----|-------------|------------------|-------------------|
| AC1 | Validation Test Plan Executed | 10+ real tickets processed end-to-end (100% success) | Scenario 1 results |
| AC2 | Enhancement Quality Reviewed | 3+ technicians surveyed, feedback documented | client-feedback-survey-results.md |
| AC3 | Performance Metrics Measured | p50/p95/p99 latency, success rate, queue depth documented | performance-baseline-metrics.md |
| AC4 | Error Scenarios Tested | 4+ error scenarios validated, graceful degradation confirmed | Scenario 4 results |
| AC5 | Multi-Tenant Isolation Validated | RLS tests pass, cross-tenant access blocked | Scenario 3 results |
| AC6 | Monitoring Alerts Verified | 3+ alerts triggered, notifications received | Scenario 5 results |
| AC7 | Validation Report Documented | Comprehensive report created with findings | production-validation-report.md |

### Overall Success Criteria

**MUST PASS (Blocking):**
- ✅ All 10+ test tickets processed successfully (AC1)
- ✅ p95 latency <60s (NFR001 compliance) (AC3)
- ✅ Success rate >95% sustained over 24-48h (AC3)
- ✅ All 7 RLS isolation tests pass (AC5 - CRITICAL SECURITY)
- ✅ Cross-tenant API access blocked with 403 Forbidden (AC5)
- ✅ Invalid webhook signature rejected with 401 (AC4 - CRITICAL SECURITY)
- ✅ All critical alerts fire and route to Slack + PagerDuty (AC6)

**SHOULD PASS (Important):**
- ✅ KB timeout: System continues with partial context, <75s (AC4)
- ✅ ServiceDesk Plus failure: 3 retries, dead-letter queue, alert fires (AC4)
- ✅ Queue backup alert fires at threshold (queue >25) (AC6)
- ✅ Client feedback average score >3.5/5 across all categories (AC2)
- ✅ Noisy neighbor test: Tenant B latency impact <20% (2025 best practice)

**NICE TO HAVE (Optional):**
- ✅ Worker utilization <80% (headroom for growth)
- ✅ Queue depth averages <10 during normal load
- ✅ Trace-based validation: All processed tickets have complete Jaeger traces
- ✅ Alert runbooks validated (diagnostic steps work correctly)

### Failure Handling

**If Critical Tests Fail:**
- HALT validation testing
- Document failure details (logs, metrics, screenshots)
- Create remediation plan with engineering team
- Re-test after fixes applied
- DO NOT proceed to report generation until critical issues resolved

**If Non-Critical Tests Fail:**
- Document failure as "Issue Found" in validation report
- Assess severity: High/Medium/Low
- Create remediation plan with timeline
- Continue validation testing (non-blocking)
- Include in recommendations section of report

---

## Roles and Responsibilities

### QA Engineer (Test Executor)

**Responsibilities:**
- Execute all test scenarios per this test plan
- Document test results in real-time
- Monitor Grafana dashboards during testing
- Coordinate with infrastructure team for controlled failures
- Collect client feedback via surveys/interviews
- Create all test deliverables (test results, performance baselines, feedback summaries)

### Operations Engineer (Infrastructure Support)

**Responsibilities:**
- Grant access to production environment (Kubernetes, databases)
- Assist with controlled failure scenarios (e.g., disable ServiceDesk Plus API temporarily)
- Monitor production health during testing
- Validate alert configurations
- Assist with incident response if production issues occur

### Engineering Lead (Technical Review)

**Responsibilities:**
- Review test plan before execution
- Provide technical guidance on complex test scenarios
- Review test results and validation report
- Approve remediation plans for issues found
- Sign off on Story 5.4 completion

### Product Manager (Business Validation)

**Responsibilities:**
- Coordinate client feedback collection
- Review client feedback results
- Assess business value validation
- Approve recommendations for future improvements
- Present validation findings to stakeholders

### Client Account Manager (Client Coordination)

**Responsibilities:**
- Facilitate access to client technicians for feedback
- Coordinate ServiceDesk Plus API access for testing
- Share validation report findings with client (executive summary)
- Gather client satisfaction feedback post-validation

---

## Test Deliverables

### Deliverable 1: Production Validation Test Plan
- **File:** `docs/testing/production-validation-test-plan.md` (this document)
- **Status:** Complete
- **Owner:** QA Engineer
- **Description:** Comprehensive test plan covering 10+ ticket scenarios, performance benchmarks, security tests, error scenarios, alert verification

### Deliverable 2: Automated Validation Test Script
- **File:** `scripts/production-validation-test.sh`
- **Status:** To be created (Task 1.1 continuation)
- **Owner:** QA Engineer
- **Description:** Bash script automating key validation checks (ticket processing, metrics queries, RLS tests, alert triggering)

### Deliverable 3: Performance Baseline Metrics Report
- **File:** `docs/testing/performance-baseline-metrics.md`
- **Status:** To be created (Scenario 2 execution)
- **Owner:** QA Engineer
- **Description:** 24-48h metric collection data with p50/p95/p99 latency, success rate, queue depth trends, Grafana dashboard graphs

### Deliverable 4: Client Feedback Survey Results
- **File:** `docs/testing/client-feedback-survey-results.md`
- **Status:** To be created (Scenario AC2 execution)
- **Owner:** QA Engineer + Product Manager
- **Description:** Structured technician feedback with quantitative scores (5-point scale) and representative qualitative quotes

### Deliverable 5: Production Validation Report
- **File:** `docs/operations/production-validation-report.md`
- **Status:** To be created (Day 4 completion)
- **Owner:** QA Engineer
- **Description:** Comprehensive validation findings with executive summary, test results, performance data, client feedback, issues found, recommendations

### Deliverable 6: Test Execution Evidence
- **Location:** To be stored in `docs/testing/evidence/` (screenshots, logs, traces)
- **Status:** To be collected during test execution
- **Owner:** QA Engineer
- **Contents:**
  - Jaeger trace screenshots (10+ ticket processing)
  - Grafana dashboard screenshots (metrics trends)
  - Slack/PagerDuty alert notifications
  - RLS validation SQL query outputs
  - API error responses (401, 403)
  - Worker log excerpts (retry logic, error handling)

---

## Appendices

### Appendix A: Prometheus PromQL Queries

**Latency Percentiles:**
```promql
# p50 latency
histogram_quantile(0.50, rate(enhancement_duration_seconds_bucket{tenant_id="<uuid>"}[5m]))

# p95 latency
histogram_quantile(0.95, rate(enhancement_duration_seconds_bucket{tenant_id="<uuid>"}[5m]))

# p99 latency
histogram_quantile(0.99, rate(enhancement_duration_seconds_bucket{tenant_id="<uuid>"}[5m]))
```

**Success Rate:**
```promql
# Success rate percentage
(rate(enhancement_success_rate_total{tenant_id="<uuid>",status="success"}[1h])
 / rate(enhancement_success_rate_total{tenant_id="<uuid>"}[1h])) * 100
```

**Queue Metrics:**
```promql
# Current queue depth
queue_depth{queue="ai_agents:queue"}

# Average queue depth over 1h
avg_over_time(queue_depth{queue="ai_agents:queue"}[1h])

# Max queue depth over 24h
max_over_time(queue_depth{queue="ai_agents:queue"}[24h])
```

**Worker Utilization:**
```promql
# Active worker count
worker_active_count

# Worker utilization percentage
(worker_active_count / 3) * 100  # 3 = total worker replicas
```

---

### Appendix B: RLS Validation SQL Queries

**Set Tenant Context:**
```sql
-- Set tenant context for testing
SELECT set_tenant_context('<tenant-uuid>');

-- Verify context set correctly
SELECT current_setting('app.current_tenant_id', true);
```

**Cross-Tenant Access Test:**
```sql
-- Set Tenant A context
SELECT set_tenant_context('<tenant-a-uuid>');

-- Attempt to query Tenant B data (should return 0 rows)
SELECT COUNT(*) FROM enhancement_history WHERE tenant_id = '<tenant-b-uuid>';

-- Expected: COUNT = 0 (RLS enforcement working)
```

**RLS Policy Verification:**
```sql
-- View RLS policies on enhancement_history table
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE tablename = 'enhancement_history';
```

---

### Appendix C: API Testing curl Commands

**Valid Webhook Submission:**
```bash
curl -X POST "https://api.ai-agents.production/api/v1/webhook" \
  -H "Content-Type: application/json" \
  -H "X-ServiceDesk-Signature: sha256=$(echo -n '{"tenant_id":"<uuid>","ticket_id":"12345"}' | openssl dgst -sha256 -hmac '<webhook-secret>' | cut -d' ' -f2)" \
  -d '{
    "tenant_id": "<uuid>",
    "ticket_id": "12345",
    "event_type": "created",
    "payload": {
      "title": "Test ticket",
      "description": "Network connectivity issue",
      "priority": "High"
    }
  }'
```

**Invalid Webhook Signature:**
```bash
curl -X POST "https://api.ai-agents.production/api/v1/webhook" \
  -H "Content-Type: application/json" \
  -H "X-ServiceDesk-Signature: sha256=INVALID_SIGNATURE_HERE" \
  -d '{
    "tenant_id": "<uuid>",
    "ticket_id": "99999",
    "event_type": "created",
    "payload": {}
  }'

# Expected: HTTP 401 Unauthorized
```

**Cross-Tenant API Access:**
```bash
# Use Tenant B credentials to access Tenant A data
curl -X GET "https://api.ai-agents.production/api/v1/enhancements?tenant_id=<tenant-a-uuid>" \
  -H "Authorization: Bearer <tenant-b-api-token>" \
  -H "Content-Type: application/json"

# Expected: HTTP 403 Forbidden
```

---

### Appendix D: References

**Story and Epic Documentation:**
- Story 5.4: `docs/stories/5-4-conduct-production-validation-testing.md`
- Story 5.4 Context: `docs/stories/5-4-conduct-production-validation-testing.context.xml`
- Epic 5: `docs/epics.md` (Lines 1001-1017)
- PRD: `docs/PRD.md` (NFR001 performance targets)
- Architecture: `docs/architecture.md` (multi-tenant design, monitoring stack)

**Operational Documentation (from Story 5.3):**
- Client Onboarding Runbook: `docs/operations/client-onboarding-runbook.md`
- Tenant Troubleshooting Guide: `docs/operations/tenant-troubleshooting-guide.md`
- Client Handoff Guide: `docs/operations/client-handoff-guide.md`
- Alert Runbooks: `docs/operations/alert-runbooks.md`

**Existing Test Scripts:**
- Production Smoke Tests: `scripts/production-smoke-test.sh` (7 tests)
- Tenant Onboarding Tests: `scripts/tenant-onboarding-test.sh` (8 tests)
- Tenant Isolation Tests: `scripts/tenant-isolation-validation.sh` (7 RLS tests)

**Monitoring Configuration (Epic 4):**
- Prometheus Alert Rules: `k8s/prometheus-alert-rules.yaml`
- Prometheus Configuration: `k8s/prometheus-config.yaml`
- Grafana Dashboards: Configured in Epic 4 (Story 4.3)
- OpenTelemetry Configuration: `src/monitoring/tracing.py` (Story 4.6)

**2025 Best Practices Sources:**
- SaaS Multi-Tenant Testing: QAwerk, BrowserStack, AWS Well-Architected SaaS Lens
- Production Validation: Microsoft Reliability Testing Strategy, TestGrid, SCNSoft
- Performance Monitoring: Prometheus + Grafana documentation (2025 updates)
- Security Testing: Nile Tenant Isolation docs, OWASP SaaS guidelines

---

**Document Version History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-04 | Amelia (Dev Agent) | Initial comprehensive test plan created following 2025 SaaS best practices |

---

**Approval Signatures:**

| Role | Name | Signature | Date |
|------|------|-----------|------|
| QA Engineer | [To be signed] | | |
| Engineering Lead | [To be signed] | | |
| Product Manager | [To be signed] | | |
| Operations Lead | [To be signed] | | |

---

**END OF PRODUCTION VALIDATION TEST PLAN**
