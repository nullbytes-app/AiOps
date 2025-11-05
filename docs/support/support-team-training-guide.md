# Support Team Training Guide
**AI Agents Platform - Knowledge Transfer & Onboarding**

**Document Version:** 1.0
**Last Updated:** 2025-11-04
**Target Audience:** New Support Team Members, Training Facilitators
**Training Duration:** 2-4 hours (initial session) + ongoing hands-on practice
**Status:** Production Ready

---

## Table of Contents

1. [Training Overview](#training-overview)
2. [Training Agenda](#training-agenda)
3. [Module 1: System Architecture](#module-1-system-architecture)
4. [Module 2: Monitoring & Alerting](#module-2-monitoring--alerting)
5. [Module 3: Common Issues & Troubleshooting](#module-3-common-issues--troubleshooting)
6. [Module 4: Hands-On Walkthrough](#module-4-hands-on-walkthrough)
7. [Module 5: Client-Specific Context (MVP Client)](#module-5-client-specific-context-mvp-client)
8. [Module 6: Escalation & Incident Response](#module-6-escalation--incident-response)
9. [Training Assessment](#training-assessment)
10. [Ongoing Learning Resources](#ongoing-learning-resources)

---

## Training Overview

### Training Objectives

By the end of this training, support team members will be able to:

1. **Explain** the AI Agents platform architecture and data flow
2. **Navigate** Grafana dashboards and Prometheus queries for troubleshooting
3. **Use** kubectl commands for pod management, log analysis, and scaling
4. **Diagnose** top 10 common issues using runbooks and decision trees
5. **Respond** to P0/P1 incidents following the incident response playbook
6. **Escalate** appropriately based on severity and root cause
7. **Support** MVP client with confidence (client-specific configurations, known issues)

### Training Prerequisites

**Technical Skills:**
- Basic Linux command-line knowledge (ls, cd, grep, tail)
- Familiarity with web applications (HTTP, APIs, webhooks)
- Understanding of databases (SQL queries, connections)
- No Kubernetes experience required (will be covered)

**Completed Before Training:**
- [ ] Read [Production Support Guide](production-support-guide.md) (at least skim)
- [ ] Access verified: VPN, kubectl, Grafana, Prometheus
- [ ] PagerDuty account created and tested

### Training Format

**Initial Session:** 3 hours (in-person or video call)
- **Part 1:** Presentation + Q&A (1 hour)
- **Part 2:** Hands-on walkthrough (1.5 hours)
- **Part 3:** Practice scenario + feedback (30 minutes)

**Ongoing:** Shadow experienced engineer for 1 week before first on-call shift

**Recording:** Session will be recorded for future team member onboarding

---

## Training Agenda

### Session Outline (3 Hours)

| Time | Duration | Module | Activity | Materials |
|------|----------|--------|----------|-----------|
| 0:00 | 10 min | Intro | Welcome, objectives, logistics | Slide deck |
| 0:10 | 20 min | Module 1 | System architecture overview | Architecture diagram |
| 0:30 | 20 min | Module 2 | Monitoring & alerting walkthrough | Grafana demo |
| 0:50 | 10 min | Break | - | - |
| 1:00 | 30 min | Module 3 | Common issues & troubleshooting | Runbook review |
| 1:30 | 45 min | Module 4 | Hands-on: Grafana, Prometheus, kubectl | Live environment |
| 2:15 | 10 min | Break | - | - |
| 2:25 | 20 min | Module 5 | MVP client context | Client config review |
| 2:45 | 10 min | Module 6 | Escalation & incident response | Playbook walkthrough |
| 2:55 | 5 min | Wrap-up | Q&A, feedback, next steps | Feedback form |

**Total:** 3 hours (with two 10-minute breaks)

---

## Module 1: System Architecture

**Duration:** 20 minutes
**Format:** Presentation with architecture diagram
**Objective:** Understand system components, data flow, and multi-tenancy model

### Key Concepts

#### High-Level Architecture

Present this diagram (use draw.io, Miro, or whiteboard):

```
┌─────────────────┐
│ ServiceDesk Plus│──── Webhook ────┐
│  (Client MSP)   │                  │
└─────────────────┘                  │
                                     ▼
                            ┌──────────────────┐
                            │   FastAPI API    │ (Port 8000)
                            │   Webhook        │
                            │   Receiver       │
                            └────────┬─────────┘
                                     │ Queue Job
                                     ▼
                            ┌──────────────────┐
                            │   Redis Queue    │ (Port 6379)
                            │  "celery" queue  │
                            └────────┬─────────┘
                                     │ Dequeue
                                     ▼
                            ┌──────────────────┐
                            │  Celery Workers  │ (5-10 pods)
                            │   LangGraph +    │
                            │   GPT-4 Synthesis│
                            └────────┬─────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
            ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
            │ PostgreSQL   │  │ ServiceDesk  │  │ OpenAI API   │
            │ (RLS for     │  │ Plus API     │  │ (via         │
            │  multi-tenant│  │              │  │  OpenRouter) │
            └──────────────┘  └──────────────┘  └──────────────┘
                    │
                    └──── Observability ────┐
                                            ▼
                                   ┌────────────────┐
                                   │ Prometheus     │
                                   │ Grafana        │
                                   │ Alertmanager   │
                                   │ OpenTelemetry  │
                                   └────────────────┘
```

**Explanation (5 minutes):**
1. **Webhook arrives** from ServiceDesk Plus (client's ticketing system)
2. **API validates** signature, queues job to Redis
3. **Worker picks up job**, runs LangGraph workflow:
   - Gathers context (ticket history, documentation, IP data)
   - Calls GPT-4 for enhancement synthesis
   - Updates ServiceDesk Plus ticket with enhancement
4. **Multi-tenant isolation** via Row-Level Security (PostgreSQL)
5. **Observability** via Prometheus metrics, Grafana dashboards, distributed tracing

---

#### Data Flow: Webhook to Enhancement (Step-by-Step)

**Walk through a real example:**

"When a technician creates ticket #12345 in ServiceDesk Plus..."

1. **T+0s:** ServiceDesk Plus sends webhook to `https://api.ai-agents.com/webhook`
2. **T+0.1s:** API validates HMAC signature using tenant-specific secret
3. **T+0.2s:** API queues job: `{"ticket_id": "12345", "tenant_id": "msp-acme-corp"}`
4. **T+0.5s:** Celery worker dequeues job, starts LangGraph workflow
5. **T+1s-10s:** Context gathering:
   - Query PostgreSQL for ticket history (previous tickets by same technician)
   - Search documentation knowledge base (related articles)
   - Cross-reference IP address (network topology, previous incidents)
6. **T+10s-45s:** GPT-4 API call (via OpenRouter):
   - Prompt: "Given this context, provide troubleshooting enhancement for ticket #12345"
   - Response: 500-word enhancement with step-by-step guidance
7. **T+45s-50s:** Update ServiceDesk Plus ticket via API (add comment with enhancement)
8. **T+50s:** Job complete, metrics recorded, trace captured

**Total Time:** ~50 seconds (p95 latency <60s per success criteria)

---

#### Multi-Tenancy & Row-Level Security

**Key Concept:** One platform, multiple clients, data isolation

**How RLS Works:**
```sql
-- Support engineer queries enhancements
SET app.current_tenant_id = 'msp-acme-corp';  -- MANDATORY
SELECT * FROM enhancements LIMIT 5;

-- PostgreSQL RLS policy automatically filters:
-- WHERE tenant_id = 'msp-acme-corp'

-- Result: Only Acme Corp enhancements returned
```

**Why This Matters for Support:**
- Always set `app.current_tenant_id` before queries
- Never access cross-tenant data without explicit authorization
- RLS protects against accidental data leakage

**Demo:** Show PostgreSQL RLS query in terminal

---

### Quiz (Module 1)

**Ask trainees:**
1. What is the first step when a webhook arrives? (Answer: Signature validation)
2. Which component processes enhancement jobs? (Answer: Celery workers)
3. Why do we use Row-Level Security? (Answer: Multi-tenant data isolation)
4. What is the target p95 latency for enhancements? (Answer: <60 seconds)

---

## Module 2: Monitoring & Alerting

**Duration:** 20 minutes
**Format:** Live demonstration in Grafana + Prometheus
**Objective:** Navigate monitoring tools, interpret dashboards, understand alerts

### Grafana Dashboards

**Open Grafana:** http://localhost:3000 (or production URL)

#### Dashboard 1: Operations Dashboard

**Purpose:** Real-time system health monitoring

**Key Panels to Show:**

1. **API Latency (p50, p95, p99)**
   - **What it shows:** HTTP request latency distribution
   - **Target:** p95 <1s
   - **Red flag:** p95 >5s (client impact)
   - **Use case:** Diagnose slow API responses

2. **Queue Depth**
   - **What it shows:** Number of pending jobs in Redis queue
   - **Target:** <20 jobs
   - **Red flag:** >100 jobs (backlog building)
   - **Use case:** Trigger worker scaling

3. **Worker Health**
   - **What it shows:** Active workers, crashed workers, worker CPU/memory
   - **Target:** All workers active, no crashes
   - **Red flag:** Workers in CrashLoopBackOff, high memory usage (OOMKilled risk)
   - **Use case:** Identify worker issues before they impact service

4. **Database Connections**
   - **What it shows:** Active database connections vs. pool size
   - **Target:** <80% of max connections
   - **Red flag:** >90% (pool exhaustion risk)
   - **Use case:** Detect connection leaks or slow queries

5. **Error Rate**
   - **What it shows:** Percentage of requests resulting in errors
   - **Target:** <1%
   - **Red flag:** >5% (systemic issue)
   - **Use case:** Identify API/worker failures

**Hands-On:** Ask trainees to find each panel, explain what it shows

---

#### Dashboard 2: Baseline Metrics Dashboard (Story 5.5)

**Purpose:** Success criteria tracking and client satisfaction

**Key Panels:**

1. **Average Feedback Rating**
   - **Target:** >4/5
   - **Use case:** Track technician satisfaction trends

2. **Feedback Sentiment** (Thumbs Up / Thumbs Down)
   - **Target:** >70% positive
   - **Use case:** Identify declining satisfaction early

3. **p95 Latency** (Enhancement processing time)
   - **Target:** <60s
   - **Use case:** Performance SLA monitoring

4. **Success Rate %**
   - **Target:** >95%
   - **Use case:** Detect enhancement pipeline issues

**Hands-On:** Show how to filter by tenant_id to view client-specific metrics

---

### Prometheus Queries

**Open Prometheus:** http://localhost:9090

**Basic Queries to Demonstrate:**

1. **Current Queue Depth:**
   ```promql
   celery_queue_length{queue="celery"}
   ```

2. **API Latency (p95):**
   ```promql
   histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
   ```

3. **Worker Count:**
   ```promql
   count(celery_worker_up == 1)
   ```

4. **Error Rate:**
   ```promql
   sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))
   ```

**Hands-On:** Trainees execute each query, explain results

---

### Alerting (Alertmanager)

**Open Alertmanager:** http://localhost:9093

**Show Active Alerts (if any):**
- Alert name (e.g., `HighQueueDepth`)
- Severity (critical, warning, info)
- Labels (instance, job, tenant_id)
- Annotations (summary, description, runbook link)

**Routing Configuration:**
- **Critical alerts** → PagerDuty phone call
- **Warning alerts** → PagerDuty SMS
- **Info alerts** → Slack #alerts channel

**Hands-On:** Show alert routing rules in `k8s/alertmanager-config.yaml`

---

## Module 3: Common Issues & Troubleshooting

**Duration:** 30 minutes
**Format:** Interactive runbook review
**Objective:** Recognize symptoms, use decision tree, apply runbooks

### Top 10 Common Issues

**Present this summary table (from Production Support Guide):**

| # | Issue | Symptom | Quick Fix | Runbook |
|---|-------|---------|-----------|---------|
| 1 | High Queue Depth | Queue >50, delays >5min | Scale workers: `kubectl scale deployment/ai-agents-worker --replicas=10` | [high-queue-depth.md](../runbooks/high-queue-depth.md) |
| 2 | Worker Crashes | Workers in CrashLoopBackOff | Check logs, restart: `kubectl rollout restart deployment/ai-agents-worker` | [worker-failures.md](../runbooks/worker-failures.md) |
| 3 | API Timeouts | p95 latency >5s | Scale API: `kubectl scale deployment/ai-agents-api --replicas=5` | [api-timeout.md](../runbooks/api-timeout.md) |
| 4 | Webhook Signature Failures | 403 Forbidden in logs | Verify secret: `kubectl get secret ai-agents-secrets -o yaml` | [WEBHOOK_TROUBLESHOOTING_RUNBOOK.md](../runbooks/WEBHOOK_TROUBLESHOOTING_RUNBOOK.md) |
| 5 | Enhancement Failures | Success rate <90% | Check worker logs for errors, review distributed traces | [enhancement-failures.md](../runbooks/enhancement-failures.md) |
| 6 | Database Connection Issues | Connection refused errors | Test connectivity: `psql $DATABASE_URL -c "SELECT 1"` | [database-connection-issues.md](../runbooks/database-connection-issues.md) |
| 7 | Alert Notification Failures | Alerts not received | Check Alertmanager logs, test PagerDuty integration | [alertmanager-setup.md](../operations/alertmanager-setup.md) |
| 8 | Low Enhancement Quality | Feedback rating <3/5 | Query feedback API, review traces, escalate to Engineering | [Weekly Metrics Review](../metrics/weekly-metrics-review-template.md) |
| 9 | Tenant Isolation Violations | Cross-tenant access in audit logs | **ESCALATE IMMEDIATELY** to Engineering + Security | [tenant-troubleshooting-guide.md](../operations/tenant-troubleshooting-guide.md) |
| 10 | Distributed Tracing Investigation | Slow/failing requests | Search by ticket_id in Jaeger, analyze spans | [distributed-tracing-setup.md](../operations/distributed-tracing-setup.md) |

**For each issue, cover:**
1. How to recognize symptoms (alerts, client reports, dashboard metrics)
2. Quick diagnosis commands
3. Immediate resolution steps
4. When to escalate

---

### Troubleshooting Decision Tree

**Walk through decision tree from Production Support Guide:**

```
Incident Reported
       |
       v
   Is system accessible? ───── NO ──────> P0 - Escalate immediately
       |
      YES
       |
       v
   Which component affected?
       |
       ├─> API → Check pod status, signature validation
       ├─> Workers → Check queue depth, worker health
       ├─> Database → Test connectivity, check pool
       ├─> External APIs → Check ServiceDesk/OpenAI status
       └─> Enhancements → Query feedback, review traces
```

**Hands-On:** Give trainees a scenario, ask them to walk through the decision tree

**Example Scenario:**
> "Client reports: 'Our technicians haven't received enhancements for the last hour. Tickets #100-110 all missing enhancements.'"

**Expected Response:**
1. Check if system accessible → Yes (API responding)
2. Component affected → Workers (enhancements not delivered)
3. Check queue depth → 75 jobs (elevated)
4. Check worker health → 2 of 5 workers crashed (CrashLoopBackOff)
5. Check worker logs → OOMKilled (memory limit exceeded)
6. Action: Scale healthy workers, investigate memory issue
7. Escalate to L2 if crashes persist

---

## Module 4: Hands-On Walkthrough

**Duration:** 45 minutes
**Format:** Live terminal + browser (trainees follow along)
**Objective:** Practice essential support tasks

### Section A: Grafana Dashboard Navigation (10 minutes)

**Exercise 1: Find Queue Depth**
1. Open Grafana → Operations Dashboard
2. Locate "Queue Depth" panel
3. What is the current queue depth?
4. Zoom to last 6 hours, identify any spikes
5. Screenshot and explain spike (if any)

**Exercise 2: Check API Latency**
1. Locate "API Latency" panel (p50, p95, p99)
2. What is the current p95 latency?
3. Is it within SLA (<1s)?
4. If not, what would you do next?

**Exercise 3: Filter by Tenant**
1. Open Baseline Metrics Dashboard
2. Filter by tenant_id = "msp-acme-corp"
3. What is the average feedback rating for this client?
4. What is the success rate?

---

### Section B: Prometheus Queries (10 minutes)

**Exercise 4: Query Queue Depth**
```promql
celery_queue_length{queue="celery"}
```
- Execute query, note result
- Click "Graph" tab, see historical trend
- What was the max queue depth in last 24 hours?

**Exercise 5: Calculate Error Rate**
```promql
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100
```
- Execute query, get percentage
- Is error rate <1% (target)?
- If not, what would you investigate?

**Exercise 6: Count Active Workers**
```promql
count(celery_worker_up == 1)
```
- How many workers are currently active?
- What is the expected number (check HPA min/max)?

---

### Section C: Kubectl Basics (15 minutes)

**Exercise 7: View Pod Status**
```bash
kubectl get pods -n ai-agents-production
```
- How many API pods are running?
- How many worker pods?
- Are any pods in Error/CrashLoopBackOff state?

**Exercise 8: View Pod Logs**
```bash
# API logs (last 50 lines)
kubectl logs deployment/ai-agents-api -n ai-agents-production --tail=50

# Worker logs (follow real-time)
kubectl logs deployment/ai-agents-worker -n ai-agents-production -f
```
- Find a log line showing "Webhook received"
- Find a log line showing "Enhancement complete"
- Press Ctrl+C to stop following logs

**Exercise 9: Scale Workers**
```bash
# Check current replica count
kubectl get deployment ai-agents-worker -n ai-agents-production

# Scale to 8 workers
kubectl scale deployment/ai-agents-worker -n ai-agents-production --replicas=8

# Verify scaling
kubectl get pods -n ai-agents-production | grep worker
```
- Wait 30 seconds, confirm 8 worker pods running
- When would you scale workers? (Answer: High queue depth, P1 incident)

**Exercise 10: Check HPA Status**
```bash
kubectl get hpa -n ai-agents-production
kubectl describe hpa ai-agents-worker-hpa -n ai-agents-production
```
- What is the current target metric? (queue depth per worker)
- What is the min/max replica count?
- Is HPA currently scaling up or down?

---

### Section D: Log Investigation (10 minutes)

**Exercise 11: Find Webhook for Specific Ticket**
```bash
# Search logs for ticket ID
kubectl logs deployment/ai-agents-api -n ai-agents-production --since=24h | grep "ticket_id: 12345"
```
- Did you find the webhook log?
- What timestamp was it received?
- What tenant_id does it belong to?

**Exercise 12: Investigate Worker Error**
```bash
# Search worker logs for errors
kubectl logs deployment/ai-agents-worker -n ai-agents-production --since=1h | grep -i error
```
- Are there any errors in the last hour?
- If yes, what type of error? (GPT-4 API, database, ServiceDesk Plus?)
- How would you resolve it?

---

## Module 5: Client-Specific Context (MVP Client)

**Duration:** 20 minutes
**Format:** Client configuration review
**Objective:** Understand MVP client setup, known issues, special considerations

### MVP Client Profile

**Client Details:**
- **Name:** MSP Acme Corp
- **Tenant ID:** `msp-acme-corp`
- **ServiceDesk Plus Instance:** https://acme.servicedeskplus.com
- **Technicians:** ~150 users
- **Ticket Volume:** ~200 tickets/day
- **Onboarded:** 2025-11-02 (Story 5.3)

### Client Configuration

**Show tenant_configs table:**
```sql
SET app.current_tenant_id = 'msp-acme-corp';
SELECT * FROM tenant_configs WHERE tenant_id = 'msp-acme-corp';
```

**Key Configuration Parameters:**
- `webhook_secret`: (encrypted, not displayed)
- `servicedesk_api_key`: (encrypted, not displayed)
- `servicedesk_base_url`: https://acme.servicedeskplus.com
- `max_concurrent_jobs`: 5
- `enhancement_timeout_seconds`: 120
- `gpt4_model`: gpt-4-turbo
- `enable_context_caching`: true

**Discuss:** What each parameter controls, when/why we'd change it

---

### Known Issues (MVP Client)

**From validation testing and onboarding (Story 5.3, 5.4):**

1. **Peak Hour Traffic Spikes**
   - **When:** 9:00-11:00 AM EST (client business hours start)
   - **Impact:** Queue depth can spike to 40-50 jobs
   - **Workaround:** HPA automatically scales workers (monitor for delayed scaling)

2. **ServiceDesk Plus API Rate Limiting**
   - **Symptom:** "429 Too Many Requests" errors in worker logs
   - **Impact:** Enhancement updates fail, require retry
   - **Resolution:** Workers automatically retry with exponential backoff
   - **Prevention:** Monitor enhancement success rate, escalate if <95%

3. **Network Troubleshooting Enhancements (Lower Quality)**
   - **Issue:** Client feedback shows network-related tickets get lower ratings
   - **Root Cause:** Knowledge base has limited network troubleshooting content
   - **Status:** Engineering adding more network documentation (in progress)
   - **Support Action:** Set expectations with client, collect feedback examples

4. **Webhook Secret Rotation (Quarterly)**
   - **Schedule:** Every 90 days (security policy)
   - **Next Rotation:** 2025-12-01
   - **Process:** See [Secret Rotation Runbook](../runbooks/secret-rotation.md)
   - **Support Involvement:** Coordinate with client, provide new secret securely

---

### Client Contacts

**Primary Support Contacts:**
- **Technical Contact:** John Doe, IT Manager (john.doe@acmecorp.com, +1-555-0100)
- **Executive Sponsor:** Jane Smith, CTO (jane.smith@acmecorp.com, +1-555-0101)
- **ServiceDesk Plus Admin:** Bob Johnson (bob.johnson@acmecorp.com)

**Escalation Path:**
- **L1/L2 Issues:** Contact John Doe (Technical Contact)
- **P0 Incidents:** Notify John Doe + Jane Smith (CTO)
- **Configuration Changes:** Coordinate with John Doe, approval required

---

### Client-Specific Monitoring

**Grafana Dashboard Filter:**
- Set tenant_id = "msp-acme-corp" in Baseline Metrics Dashboard
- Monitor:
  - Average feedback rating (target: >4/5)
  - Success rate (target: >95%)
  - p95 latency (target: <60s)

**Weekly Metrics Review:**
- Every Monday 10:00 AM
- Review last 7 days metrics with client
- Use [Weekly Metrics Review Template](../metrics/weekly-metrics-review-template.md)

---

## Module 6: Escalation & Incident Response

**Duration:** 10 minutes
**Format:** Playbook walkthrough
**Objective:** Know when/how to escalate, understand incident response basics

### Escalation Triggers

**Review from Production Support Guide:**

**L1 → L2 Escalation:**
- P1 or higher severity
- L1 unable to resolve within 30 minutes
- Client communication required
- Root cause unclear

**L2 → Engineering Escalation:**
- P0 severity
- Code fix required
- Infrastructure changes needed
- L2 unable to resolve within 1 hour

**Engineering → Executive Escalation:**
- P0 incident >2 hours
- Security breach confirmed
- Major client relationship risk

---

### Incident Response Quick Reference

**If P0/P1 Incident:**

1. **Declare Incident** (Slack #incidents-p0 or #incidents-p1)
2. **Page Appropriate Tier** (L2 for P1, Engineering for P0)
3. **Start Incident Timeline** (Google Doc)
4. **Follow Incident Response Playbook:** [incident-response-playbook.md](incident-response-playbook.md)
5. **Communicate** (internal updates every 30 min, client notification if impacted)

**Remember:** PICERL framework
- **P**reparation: Done (you're trained!)
- **I**dentification: Alert received, severity assessed
- **C**ontainment: Limit impact (scale resources, isolate component)
- **E**radication: Fix root cause (deploy patch, config change)
- **R**ecovery: Validate service restored
- **L**essons Learned: Postmortem within 48 hours

---

### Practice Scenario: P1 Incident Response

**Scenario:**
> "At 3:00 PM, PagerDuty pages you: **HighQueueDepth** alert firing. You check Grafana and see queue depth = 120 jobs, trending upward. Workers appear healthy (all 5 active). Client hasn't reported issues yet, but enhancements are delayed ~15 minutes."

**Question:** Walk through your response step-by-step.

**Expected Answer:**
1. **Acknowledge alert** (PagerDuty, Slack)
2. **Assess severity:** P1 (significant delay, multiple clients impacted)
3. **Immediate action:** Scale workers to 10: `kubectl scale deployment/ai-agents-worker --replicas=10`
4. **Monitor:** Watch queue drainage in Grafana (expect 10-20 jobs/minute decrease)
5. **Declare incident:** Post in #incidents-p1 (if queue not draining after 10 minutes)
6. **Investigate root cause:** Why did queue spike? (check logs for stuck jobs, external API issues)
7. **Escalate to L2** if queue reaches 200 or not draining after 15 minutes
8. **Document:** Log actions in support ticket, update incident timeline if escalated

**Discuss:** What went well? What could be improved?

---

## Training Assessment

### Knowledge Check (10 Questions)

**Test trainee understanding (verbal quiz or written):**

1. **Architecture:** Name the three main components of the enhancement pipeline. (API, Queue, Workers)
2. **Data Flow:** What happens immediately after a webhook is received? (Signature validation)
3. **Monitoring:** Which Grafana dashboard panel shows queue depth? (Operations Dashboard → Queue Depth)
4. **Troubleshooting:** What is the first command to check pod status? (`kubectl get pods -n ai-agents-production`)
5. **Escalation:** When should you escalate from L1 to L2? (P1+ severity, unable to resolve in 30 min, client communication needed)
6. **Client Context:** What is the MVP client's tenant_id? (`msp-acme-corp`)
7. **Multi-Tenancy:** Why must you set `app.current_tenant_id` before database queries? (RLS enforcement, data isolation)
8. **Incident Response:** What does PICERL stand for? (Preparation, Identification, Containment, Eradication, Recovery, Lessons Learned)
9. **Severity:** Describe a P0 incident. (Complete service outage, security breach, all clients affected)
10. **On-Call:** What is the first step when an alert fires? (Acknowledge alert within 5 minutes)

**Passing Score:** 8/10 correct answers

---

### Hands-On Assessment

**Scenario:** Trainee must complete this task independently

**Task:** "Client reports Ticket #99999 did not receive enhancement. Investigate and report findings."

**Expected Actions:**
1. Search API logs for ticket_id: `kubectl logs deployment/ai-agents-api --since=24h | grep "99999"`
2. Check if job queued (look for "Job queued" log)
3. Search worker logs: `kubectl logs deployment/ai-agents-worker --since=24h | grep "99999"`
4. Check for processing logs (Task started, Task completed, or errors)
5. Use distributed tracing (search by ticket_id in Jaeger)
6. Document findings:
   - Was webhook received? (Yes/No, timestamp)
   - Was job queued? (Yes/No, job_id)
   - Did worker process it? (Yes/No, result: success/failed/stuck)
   - Root cause identified? (or "needs escalation")

**Assessment Criteria:**
- ✅ Used correct kubectl commands
- ✅ Found relevant logs
- ✅ Documented timeline accurately
- ✅ Identified root cause or escalated appropriately

---

## Ongoing Learning Resources

### Documentation

**Required Reading (Within First Week):**
- [Production Support Guide](production-support-guide.md) - Complete read-through
- [Incident Response Playbook](incident-response-playbook.md) - Focus on P0/P1 procedures
- [On-Call Rotation](on-call-rotation.md) - Before first on-call shift

**Reference Documentation:**
- [Client Support Procedures](client-support-procedures.md) - Ticket investigation, config management
- [Runbooks](../runbooks/) - 11 scenario-specific troubleshooting guides
- [Operations Docs](../operations/) - Deployment, client onboarding, monitoring setup

---

### Shadowing & Mentorship

**Week 1 After Training:**
- Shadow experienced L1/L2 engineer for all support tasks
- Observe incident response (if incidents occur)
- Ask questions, take notes

**Before First On-Call Shift:**
- Complete 1 full week of shadowing
- Pass knowledge check and hands-on assessment
- Review on-call runbook with mentor
- Conduct practice mock incident drill

**Ongoing:**
- Weekly team meetings: Share learnings, review recent incidents
- Monthly training updates: New features, process changes
- Quarterly mock incident drills

---

### Training Feedback

**Post-Training Survey (Anonymous):**

1. **Content Clarity:** Was the training content clear and easy to understand? (1-5 scale)
2. **Hands-On Practice:** Was there enough hands-on practice time? (Yes/No/Comments)
3. **Confidence Level:** How confident do you feel supporting the platform after this training? (1-5 scale)
4. **Missing Topics:** What topics would you like more coverage on?
5. **Improvements:** What could be improved in future training sessions?
6. **Overall Rating:** How would you rate this training overall? (1-5 scale)

**Action Items from Feedback:**
- Reviewed by Training Lead within 1 week
- Common feedback themes incorporated into next training session
- Individual concerns addressed with 1-on-1 follow-up

---

## Training Recording

**Recording Details:**
- **Platform:** Zoom / Google Meet / Microsoft Teams
- **Recording:** Auto-record entire session
- **Storage:** Company shared drive (link provided to all team members)
- **Access:** Available for new hires, refresher training, reference

**Recording Sections:**
- 0:00-0:30 - System Architecture Overview
- 0:30-0:50 - Monitoring & Alerting Demo
- 1:00-1:30 - Common Issues & Troubleshooting
- 1:30-2:15 - Hands-On Walkthrough
- 2:25-2:45 - Client Context & Escalation

**Usage:** New support team members can watch recording before in-person shadowing

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-04 | Initial support team training guide created (Story 5.6) | Dev Agent (AI) |

---

**Document Maintenance:**
- **Review Frequency:** After each training session, or quarterly
- **Owner:** Training Lead / Support Team Lead
- **Update Triggers:** New features deployed, process changes, trainee feedback

**Feedback:** Report training improvements via `#support-training-feedback` Slack channel.
