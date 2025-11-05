# Incident Response Playbook
**AI Agents Platform - Structured Incident Management**

**Document Version:** 1.0
**Last Updated:** 2025-11-04
**Target Audience:** Incident Commanders, On-Call Engineers, Support Team
**Status:** Production Ready
**Framework:** PICERL + Google SRE "Three Cs"

---

## Table of Contents

1. [Overview](#overview)
2. [Severity Level Definitions](#severity-level-definitions)
3. [Incident Response Workflow](#incident-response-workflow)
4. [Communication Templates](#communication-templates)
5. [Escalation Matrix](#escalation-matrix)
6. [Incident Commander Role](#incident-commander-role)
7. [Postmortem Template](#postmortem-template)

---

## Overview

### Purpose

This playbook defines **structured incident response procedures** for the AI Agents platform, ensuring consistent, effective responses to operational events using the **PICERL framework** (Preparation, Identification, Containment, Eradication, Recovery, Lessons Learned) and Google SRE's **"Three Cs"** (Coordinate, Communicate, Control).

### Incident Response Principles (2025 SRE Best Practices)

1. **Preparation Over Reaction:** Well-prepared teams respond faster and more effectively
2. **Communication is Critical:** Clear, timely communication prevents chaos and reduces MTTR (Mean Time To Resolve)
3. **Document Everything:** Incident timeline, decisions, and actions are learning opportunities
4. **Blameless Culture:** Focus on systems and processes, not individuals
5. **Continuous Improvement:** Every incident is a chance to improve systems and procedures

### PICERL Framework at a Glance

| Phase | Focus | Key Activities |
|-------|-------|----------------|
| **P**reparation | Proactive readiness | Runbooks, monitoring, training, drills |
| **I**dentification | Incident detection | Alerting, on-call notification, initial triage |
| **C**ontainment | Limit impact | Isolate affected components, prevent spread |
| **E**radication | Remove root cause | Fix bugs, patch systems, restore integrity |
| **R**ecovery | Return to normal | Restore services, validate functionality |
| **L**essons Learned | Prevent recurrence | Postmortem, action items, runbook updates |

### Google SRE "Three Cs"

- **Coordinate:** Assign clear roles (Incident Commander, Communication Lead, Technical Lead)
- **Communicate:** Keep all stakeholders informed (internal team, clients, executives)
- **Control:** Make decisions based on data, not panic; maintain incident timeline

---

## Severity Level Definitions

**Severity levels determine response urgency, escalation paths, and communication requirements.**

### P0 - Critical (Catastrophic)

**Definition:** Complete service outage or security breach affecting all clients

**Examples:**
- All webhooks failing (100% delivery failure)
- Database completely unavailable (all queries failing)
- Kubernetes cluster down (all pods unavailable)
- Security breach confirmed (cross-tenant data access, unauthorized intrusion)
- Data integrity violation (data loss, corruption across multiple tenants)

**Impact:**
- 🔴 All clients unable to receive enhancements
- 🔴 Business-critical operations halted
- 🔴 Revenue impact or SLA breach imminent
- 🔴 Security/compliance risk

**Response SLA:**
- **Detection:** <5 minutes (automated alerting)
- **Initial Response:** Immediate (on-call paged)
- **Engineering Escalation:** 15 minutes
- **Executive Notification:** Immediate
- **Communication to Clients:** Within 30 minutes

**Incident Commander:** Senior Support Engineer or Engineering Manager

**Postmortem:** Mandatory within 48 hours of resolution

---

### P1 - High (Major)

**Definition:** Significant service degradation affecting multiple clients or critical functionality

**Examples:**
- High queue depth (>100 jobs) causing enhancements delayed >10 minutes
- API latency p95 >10s (severe performance degradation)
- Worker failures causing >20% enhancement failure rate
- Single large client completely down (>100 technicians impacted)
- External API failures (ServiceDesk Plus, OpenAI) with no circuit breaker
- Database connection pool exhaustion (intermittent query failures)

**Impact:**
- 🟠 Multiple clients experiencing degraded service
- 🟠 SLA at risk if not resolved within 2 hours
- 🟠 Client complaints and support ticket volume increasing

**Response SLA:**
- **Detection:** <5 minutes
- **Initial Response:** 5 minutes
- **Engineering Escalation:** 30 minutes
- **Executive Notification:** If unresolved after 2 hours
- **Communication to Clients:** Within 1 hour (if client-impacting)

**Incident Commander:** On-Call Support Engineer or L2 Support

**Postmortem:** Mandatory if incident duration >2 hours or repeat occurrence

---

### P2 - Medium (Moderate)

**Definition:** Moderate service degradation affecting subset of clients or non-critical functionality

**Examples:**
- Queue depth 50-100 jobs (enhancements delayed 5-10 minutes)
- API latency p95 3-5s (noticeable but acceptable)
- Single small client affected (<50 technicians)
- Worker scaling issues (HPA not scaling fast enough, manual intervention required)
- Low enhancement quality for specific ticket types (client feedback <3/5)
- Feedback API intermittent errors (non-critical feature)

**Impact:**
- 🟡 Limited client impact
- 🟡 Workarounds available
- 🟡 No immediate SLA risk

**Response SLA:**
- **Detection:** <15 minutes
- **Initial Response:** 15 minutes
- **Engineering Escalation:** 4 hours (if L2 unable to resolve)
- **Executive Notification:** Not required
- **Communication to Clients:** If specifically requested or impact >2 hours

**Incident Commander:** On-Call Support Engineer

**Postmortem:** Optional (recommended if repeat occurrence or affects multiple clients)

---

### P3 - Low (Minor)

**Definition:** Minor issues with minimal client impact or cosmetic problems

**Examples:**
- Grafana dashboard display issues (data still accessible)
- Non-critical alert flapping (false positives)
- Documentation outdated or missing
- Low-priority feature requests
- Single enhancement failure (isolated, not pattern)
- Feedback API slow response (<5s, no errors)

**Impact:**
- 🟢 Minimal or no client impact
- 🟢 Internal observability or tooling affected
- 🟢 No urgency

**Response SLA:**
- **Detection:** Best effort
- **Initial Response:** 1 hour (business hours) or next business day
- **Engineering Escalation:** Next sprint planning
- **Executive Notification:** Not required
- **Communication to Clients:** Not required

**Incident Commander:** Not assigned (handled by on-call during regular troubleshooting)

**Postmortem:** Not required

---

## Incident Response Workflow

### Phase 1: Preparation (Proactive)

**Completed Activities (Epic 4-5):**
- ✅ Monitoring and alerting deployed (Prometheus, Grafana, Alertmanager)
- ✅ Runbooks created for 11 common scenarios
- ✅ On-call rotation established
- ✅ Distributed tracing implemented (OpenTelemetry)
- ✅ Support team training conducted
- ✅ Mock incident drill validated readiness

**Ongoing Preparation:**
- Monthly runbook review and updates
- Quarterly disaster recovery drills
- New hire incident response training
- Alert tuning based on postmortem findings

---

### Phase 2: Identification (Detection & Triage)

**Incident Detection Methods:**
1. **Automated Alerts** (Prometheus → Alertmanager → PagerDuty/Slack)
2. **Client Reports** (support tickets, emails, phone calls)
3. **Proactive Monitoring** (Grafana dashboards, health checks)
4. **Internal Discovery** (Engineer notices error patterns)

**Initial Triage Steps (First 5 Minutes):**

```
┌─────────────────────────────────────────────────┐
│  1. ALERT RECEIVED (On-Call Paged)              │
└──────────────────┬──────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────┐
│  2. ACKNOWLEDGE ALERT (Stop paging others)       │
│     - PagerDuty: Click "Acknowledge"             │
│     - Slack: React with 👀 emoji                 │
└──────────────────┬──────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────┐
│  3. ASSESS SEVERITY (P0, P1, P2, or P3)         │
│     - Check Grafana: How many clients affected? │
│     - Check scope: Partial or complete outage?  │
│     - Use Severity Definitions above            │
└──────────────────┬──────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────┐
│  4. DECLARE INCIDENT (If P0 or P1)              │
│     - Create incident in tracking system         │
│     - Post in #incidents-p0 or #incidents-p1     │
│     - Assign Incident Commander (self or senior) │
└──────────────────┬──────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────┐
│  5. INITIAL COMMUNICATION                        │
│     - Internal: Slack incident channel           │
│     - Client (if P0/P1): Status update email     │
│     - Executive (if P0): Direct notification     │
└──────────────────┬──────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────┐
│  6. START INCIDENT TIMELINE                      │
│     - Google Doc or incident.io timeline         │
│     - Log detection time, severity, initial obs. │
└─────────────────────────────────────────────────┘
```

**Triage Checklist:**
- [ ] Alert acknowledged and verified (not false positive)
- [ ] Severity assessed using definitions above
- [ ] Incident declared (P0/P1) or handled as routine troubleshooting (P2/P3)
- [ ] Incident Commander assigned (for P0/P1)
- [ ] Initial communication sent (internal + client if needed)
- [ ] Incident timeline started

---

### Phase 3: Containment (Limit Impact)

**Goal:** Prevent incident from spreading, minimize ongoing damage

**Common Containment Actions:**

| Incident Type | Containment Strategy | Example Commands |
|---------------|----------------------|------------------|
| **High Queue Depth** | Scale workers immediately | `kubectl scale deployment/ai-agents-worker --replicas=10` |
| **Worker Crashes** | Isolate bad workers, scale healthy ones | `kubectl delete pod <crashed-pod>; kubectl scale deployment/ai-agents-worker --replicas=8` |
| **Database Issues** | Kill long-running queries, increase pool | `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'active' AND query_start < now() - interval '5 minutes';` |
| **API Timeouts** | Enable circuit breaker, reduce load | Temporarily disable non-critical endpoints, scale API pods |
| **Security Breach** | Isolate affected tenant, disable access | Revoke API keys, block IP addresses, disable webhooks for tenant |
| **External API Failure** | Enable fallback/circuit breaker | Switch to backup provider (if available), queue jobs for retry |

**Containment Decision Framework:**

```
Is incident spreading to other components? ───── YES ──────> Isolate affected component immediately
       │                                                     (disable tenant, kill pods, circuit breaker)
      NO
       │
       v
Is impact increasing over time? ───────────────── YES ──────> Scale resources to handle load
       │                                                     (workers, API pods, database)
      NO
       │
       v
Can we fail over to backup? ────────────────────── YES ──────> Activate failover (standby database,
       │                                                      backup API provider, DR region)
      NO
       │
       v
Proceed to Eradication phase (fix root cause)
```

**Containment Documentation:**
- Log all containment actions in incident timeline
- Note any workarounds applied
- Track which clients/features are affected

---

### Phase 4: Eradication (Remove Root Cause)

**Goal:** Fix the underlying problem permanently

**Common Eradication Actions:**

| Root Cause | Eradication Strategy | Validation |
|------------|----------------------|------------|
| **Application Bug** | Deploy hotfix with bug fix | Run regression tests, monitor error logs |
| **Configuration Error** | Correct config, restart services | Verify config with kubectl/database query |
| **Resource Exhaustion** | Increase limits, optimize queries | Monitor resource utilization in Grafana |
| **Dependency Failure** | Update dependency version, patch CVE | Test integration, verify functionality |
| **Infrastructure Failure** | Replace failed nodes/pods, apply patches | Health checks pass, no alerts firing |

**Eradication Checklist:**
- [ ] Root cause identified with high confidence
- [ ] Fix implemented and tested in staging (if time permits)
- [ ] Fix deployed to production
- [ ] Monitoring confirms fix is effective (metrics improving)
- [ ] No new errors or regressions introduced
- [ ] Incident timeline updated with fix details

**Engineering Collaboration:**
- For P0/P1 incidents, Engineering should be actively involved in eradication
- For complex bugs, pair with Engineer to implement fix
- Use distributed tracing to pinpoint exact failure point

---

### Phase 5: Recovery (Return to Normal Operations)

**Goal:** Restore service to full functionality, validate all systems healthy

**Recovery Steps:**

**Step 1: Restore Services**
```bash
# Scale resources back to normal (if over-scaled during containment)
kubectl scale deployment/ai-agents-worker -n ai-agents-production --replicas=5

# Restart deployments if configuration changed
kubectl rollout restart deployment/ai-agents-api -n ai-agents-production
kubectl rollout status deployment/ai-agents-api -n ai-agents-production
```

**Step 2: Validate Functionality**
```bash
# Run health check script
bash scripts/health-check.sh

# Test end-to-end flow (webhook → enhancement → ticket update)
# Trigger test webhook from ServiceDesk Plus
# Monitor logs and traces for successful processing
```

**Step 3: Monitor for Stability (15-30 minutes)**
- Watch Grafana dashboards for anomalies
- Check error logs for recurring errors
- Verify queue depth returning to normal
- Confirm no new alerts firing

**Step 4: Declare Incident Resolved**
- Update incident status: "Resolved"
- Post resolution message in incident Slack channel
- Send "All Clear" email to clients (if notified of incident)
- Update incident timeline with resolution time

**Recovery Checklist:**
- [ ] All services restored to normal operation
- [ ] End-to-end functionality validated
- [ ] Monitoring shows stable metrics (30 minutes)
- [ ] No alerts firing
- [ ] Incident declared resolved
- [ ] Clients notified of resolution (if notified of incident)

---

### Phase 6: Lessons Learned (Postmortem)

**Goal:** Learn from incident, prevent recurrence

**When Required:**
- **Mandatory:** All P0 incidents, P1 incidents >2 hours duration
- **Recommended:** P1 incidents <2 hours, repeat P2 incidents
- **Optional:** P2 single-occurrence incidents

**Postmortem Timeline:**
- **Draft:** Within 24-48 hours of incident resolution
- **Review:** 3-5 business days (team review meeting)
- **Publish:** Within 1 week of incident
- **Action Items:** Assigned owners and due dates

**See:** [Postmortem Template](#postmortem-template) section below

---

## Communication Templates

### 1. Initial Incident Notification (Internal)

**Slack Post (#incidents-p0 or #incidents-p1):**

```
🚨 INCIDENT DECLARED: [P0/P1] [Brief Description]
─────────────────────────────────────────────────
Severity: P0 (Critical) / P1 (High)
Detected: 2025-11-04 10:30 UTC
Incident Commander: @jane.doe
Status: INVESTIGATING

IMPACT:
• [Number] clients affected
• [Specific functionality impacted]
• [Current error rate / queue depth / metric]

CURRENT ACTIONS:
• Investigating root cause
• [Containment action taken, if any]

TIMELINE:
https://docs.google.com/document/d/[incident-timeline-doc]

NEXT UPDATE: 30 minutes (or when status changes)

NEED HELP?
• Join #incident-[id] war room
• Engineers: @engineering-oncall
```

---

### 2. Client Incident Notification (Initial)

**Email Subject:** `[AI Agents] Service Impact Notice - [Brief Description]`

**Email Body:**

```
Dear [Client Name],

We are writing to inform you of a service impact affecting the AI Agents enhancement platform.

INCIDENT SUMMARY:
─────────────────
Severity: [P0 - Critical / P1 - High]
Detected: [Date Time UTC]
Impact: [Description of impact to client - e.g., "Enhancements delayed >10 minutes"]

CURRENT STATUS:
───────────────
Our engineering team is actively investigating and working to resolve the issue.
[Containment action taken, if any - e.g., "We have scaled up worker capacity to process backlog"]

EXPECTED RESOLUTION:
────────────────────
We expect to have service restored within [timeframe, or "investigating"].

WORKAROUNDS:
────────────
[If available, provide workaround - e.g., "Manual ticket updates available via ServiceDesk Plus"]
[If none: "No workarounds available at this time. We apologize for the inconvenience."]

NEXT UPDATE:
────────────
We will provide an update within [30 minutes / 1 hour] or when the status changes.

For urgent questions, please contact:
• Email: support@ai-agents.com
• Phone: [Support Hotline]

We apologize for the disruption and are working diligently to restore service.

Best regards,
AI Agents Support Team
```

---

### 3. Client Incident Update (In-Progress)

**Email Subject:** `[AI Agents] Service Impact Update - [Brief Description]`

**Email Body:**

```
Dear [Client Name],

UPDATE: [Summary of progress - e.g., "Root cause identified, fix being deployed"]

INCIDENT STATUS:
────────────────
Severity: [P0/P1]
Detected: [Date Time UTC]
Time Elapsed: [X hours Y minutes]

PROGRESS:
─────────
• [10:30 UTC] Incident detected, team mobilized
• [10:45 UTC] Root cause identified: [brief description]
• [11:00 UTC] Fix deployed to production
• [11:15 UTC] Monitoring for stability

CURRENT IMPACT:
───────────────
[Updated impact - e.g., "Queue backlog being processed, enhancements returning to normal latency"]

EXPECTED RESOLUTION:
────────────────────
[Updated estimate - e.g., "Service fully restored within 30 minutes"]

NEXT UPDATE:
────────────
[30 minutes or when incident is resolved]

Thank you for your patience.

Best regards,
AI Agents Support Team
```

---

### 4. Client Incident Resolution (All Clear)

**Email Subject:** `[AI Agents] RESOLVED - Service Impact Notice`

**Email Body:**

```
Dear [Client Name],

We are pleased to inform you that the service impact has been RESOLVED.

INCIDENT SUMMARY:
─────────────────
Severity: [P0/P1]
Detected: [Date Time UTC]
Resolved: [Date Time UTC]
Total Duration: [X hours Y minutes]
Impact: [Description]

ROOT CAUSE:
───────────
[Brief, non-technical explanation - e.g., "A configuration error caused worker processes to consume excessive resources, leading to delays"]

RESOLUTION:
───────────
[Brief explanation - e.g., "We corrected the configuration and scaled resources to process the backlog"]

VALIDATION:
───────────
✅ Service restored to full functionality
✅ Backlog processed (all delayed enhancements delivered)
✅ Monitoring confirms stable operation

NEXT STEPS:
───────────
• We will conduct a full postmortem to prevent recurrence
• [If applicable: Action items like "Configuration safeguards will be implemented"]
• Normal support operations have resumed

If you continue to experience issues, please contact support immediately.

We sincerely apologize for the disruption and appreciate your patience during this incident.

Best regards,
AI Agents Support Team
```

---

### 5. Executive Incident Notification (P0 Only)

**Email/Slack to CTO/Engineering Manager:**

```
🚨 P0 INCIDENT DECLARED

Severity: P0 (CRITICAL)
Detected: 2025-11-04 10:30 UTC
Incident Commander: Jane Doe (Senior Support Engineer)

IMPACT:
• Complete service outage
• All clients affected (100% enhancement delivery failure)
• Revenue impact: [Estimate, if known]
• SLA breach: Imminent

ROOT CAUSE:
• Investigating: Database completely unavailable (connection refused)

CURRENT ACTIONS:
• Engineering on-call paged
• Investigating database infrastructure (AWS RDS status, network connectivity)
• Client notification sent at 10:45 UTC

WAR ROOM:
• Slack: #incident-20251104-1030
• Timeline: https://docs.google.com/document/d/[doc-id]

NEXT UPDATE: 15 minutes or when status changes

ESCALATION NEEDED?
• If database unavailable >30 minutes, may need cloud provider escalation
```

---

## Escalation Matrix

### Escalation Tiers

| Tier | Role | Responsibility | Contact Method | Availability |
|------|------|----------------|----------------|--------------|
| **L1** | On-Call Support Engineer | First responder, triage, initial troubleshooting | PagerDuty, Slack | 24x7 |
| **L2** | Senior Support Engineer | Complex troubleshooting, client communication, IC for P1 | PagerDuty, Slack, Phone | 24x7 |
| **L3** | Engineering On-Call | Code fixes, infrastructure changes, IC for P0 | PagerDuty, Slack, Phone | 24x7 |
| **L4** | Engineering Manager | Resource allocation, vendor escalation, executive liaison | Phone, Email | On-demand |
| **L5** | CTO / Executive | Major incident oversight, client executive communication | Phone | P0 only |

---

### Escalation Triggers

**L1 → L2 Escalation:**
- Incident severity P1 or higher
- L1 unable to resolve within 30 minutes
- Client communication required
- Root cause unclear after initial diagnosis

**L2 → L3 (Engineering) Escalation:**
- Incident severity P0
- Application code fix required
- Infrastructure/database changes needed
- L2 unable to resolve within 1 hour

**L3 → L4 (Engineering Manager) Escalation:**
- P0 incident duration >1 hour
- Vendor escalation needed (cloud provider, ServiceDesk Plus, OpenAI)
- Additional engineering resources required
- Client executive escalation imminent

**L4 → L5 (CTO/Executive) Escalation:**
- P0 incident duration >2 hours
- Major client relationship risk
- Security breach confirmed
- Press/public relations concern

---

### Escalation Contact Flow

```
┌─────────────────────────────────────────────────┐
│  INCIDENT DETECTED                               │
│  (Alert, Client Report, Proactive Discovery)     │
└──────────────────┬──────────────────────────────┘
                   ▼
       ┌───────────────────────┐
       │   L1 On-Call Support  │ ◄──── First Responder
       │   (Acknowledge Alert)  │
       └───────────┬───────────┘
                   │
         ┌─────────▼─────────┐
         │  Severity P0/P1?  │
         └─────────┬─────────┘
                   │
        ┌──────────┴──────────┐
       YES                    NO (P2/P3)
        │                      │
        ▼                      ▼
  ┌──────────────┐      ┌────────────────┐
  │ L2 Support   │      │ L1 Handles     │
  │ (Incident    │      │ (Routine       │
  │  Commander)  │      │  Troubleshoot) │
  └──────┬───────┘      └────────────────┘
         │
    ┌────▼─────┐
    │ Code Fix │
    │ Needed?  │
    └────┬─────┘
         │
    ┌────┴────┐
   YES       NO
    │         │
    ▼         ▼
┌────────┐  ┌─────────────┐
│ L3 Eng │  │ L2 Resolves │
└────┬───┘  └─────────────┘
     │
┌────▼────────┐
│ Resolved in │
│  1 hour?    │
└────┬────────┘
     │
 ┌───┴────┐
NO       YES
 │         │
 ▼         ▼
┌────────┐  ┌──────────┐
│ L4 Eng │  │ Resolved │
│ Manager│  └──────────┘
└────┬───┘
     │
┌────▼────────┐
│ Resolved in │
│  2 hours?   │
└────┬────────┘
     │
 ┌───┴────┐
NO       YES
 │         │
 ▼         ▼
┌────────┐  ┌──────────┐
│ L5 CTO │  │ Resolved │
│/Exec   │  └──────────┘
└────────┘
```

---

## Incident Commander Role

### Responsibilities

The **Incident Commander (IC)** is the single point of coordination during P0/P1 incidents, responsible for:

1. **Coordinate:** Assign roles, manage resources, make decisions
2. **Communicate:** Internal updates, client notifications, executive briefings
3. **Control:** Maintain incident timeline, track actions, ensure resolution

**Who is IC:**
- **P0 Incidents:** Senior Support Engineer or Engineering Manager
- **P1 Incidents:** On-Call Support Engineer or L2 Support
- **P2/P3 Incidents:** No formal IC (handled by on-call troubleshooting)

---

### IC Duties During Incident

#### 1. Incident Declaration (First 5 Minutes)

- [ ] Acknowledge alert and assess severity
- [ ] Create incident tracking record (PagerDuty, incident.io, or Google Doc)
- [ ] Post incident declaration in Slack (#incidents-p0 or #incidents-p1)
- [ ] Assign roles:
  - **Technical Lead:** Investigates root cause, implements fix
  - **Communication Lead:** Drafts client notifications, posts updates
  - **Scribe:** Documents timeline, logs actions taken
- [ ] Start incident timeline document

---

#### 2. Ongoing Coordination (During Incident)

- [ ] Run war room (Slack channel or video call for P0)
- [ ] Make decisions on containment, escalation, and communication
- [ ] Provide updates every 15-30 minutes (internal + client if notified)
- [ ] Manage handoffs if incident spans multiple shifts
- [ ] Coordinate with Engineering on fix deployment
- [ ] Track action items and owners

**IC Commands (War Room):**
- "Who is investigating [component]?"
- "Status update: Where are we on [task]?"
- "Decision: We will [action] because [reason]"
- "Action item: [Person] will [task] by [time]"
- "Scribe: Please log [event] in timeline at [time]"

---

#### 3. Incident Resolution (Final Phase)

- [ ] Validate fix is effective (monitor metrics for 15-30 minutes)
- [ ] Declare incident resolved (post in Slack, update tracking system)
- [ ] Send "All Clear" notification to clients (if notified)
- [ ] Assign postmortem owner and due date
- [ ] Thank team members for response
- [ ] Hand off any follow-up work to normal support queue

---

### IC Handoff Procedures

**When to Hand Off:**
- Incident duration >4 hours (cross-shift)
- IC fatigue or unavailability
- Escalation requires different IC (e.g., L2 → Engineering Manager)

**Handoff Checklist:**
- [ ] Review incident timeline with incoming IC
- [ ] Summarize current status (containment, eradication progress)
- [ ] Brief on key decisions made and reasoning
- [ ] Identify outstanding action items and owners
- [ ] Transfer war room ownership (Slack channel, video call)
- [ ] Update incident tracking system with new IC
- [ ] Post handoff announcement in incident channel

---

## Postmortem Template

### Postmortem Document Structure

**Use this template in Google Docs, Confluence, or Markdown**

```markdown
# Incident Postmortem: [Brief Description]

**Incident ID:** INC-20251104-1030
**Date:** 2025-11-04
**Severity:** P0 (Critical)
**Duration:** 2 hours 15 minutes
**Incident Commander:** Jane Doe
**Participants:** [List of responders]
**Status:** RESOLVED

---

## Executive Summary

[2-3 sentences summarizing incident, impact, root cause, and resolution]

**Example:**
"On November 4, 2025, the AI Agents platform experienced a complete service outage from 10:30 UTC to 12:45 UTC, affecting all clients. The root cause was a PostgreSQL database connection pool exhaustion due to a slow query introduced in a recent deployment. The issue was resolved by killing long-running queries, increasing the connection pool size, and optimizing the query with an index."

---

## Incident Timeline

| Time (UTC) | Event | Actor |
|------------|-------|-------|
| 10:30 | Alert fired: DatabaseConnectionIssues | Prometheus |
| 10:32 | On-call acknowledged alert | John Smith (L1) |
| 10:35 | Severity assessed as P0, incident declared | John Smith |
| 10:40 | Incident Commander assigned (Jane Doe), Engineering paged | Jane Doe (L2) |
| 10:45 | Client notification email sent | Communication Lead |
| 10:50 | Root cause identified: slow query + pool exhaustion | Engineering |
| 11:00 | Containment: Killed long-running queries | Engineering |
| 11:10 | Eradication: Deployed query optimization patch | Engineering |
| 11:20 | Recovery: Service validated, monitoring for stability | IC |
| 11:50 | Declared resolved, "All Clear" email sent | IC |
| 12:45 | Postmortem draft started | IC |

---

## Impact Assessment

**Client Impact:**
- **Clients Affected:** All 1 production client (MSP Acme Corp)
- **Technicians Impacted:** ~150 technicians unable to receive enhancements
- **Enhancements Missed:** 87 tickets during outage window
- **Business Impact:** SLA breach (2 hour outage, SLA: 99.5% uptime = max 3.65 hours/month)

**Internal Impact:**
- **Engineering Hours:** 6 person-hours (3 engineers * 2 hours)
- **Support Hours:** 2.5 person-hours (IC + communication)
- **Revenue Impact:** [Estimate if applicable, or "Minimal - no client churn expected"]

---

## Root Cause Analysis

**What Happened:**
A database migration deployed on November 3, 2025, introduced a new query for fetching tenant configurations. This query lacked an index on the `tenant_id` column, causing full table scans and query durations >30 seconds. Under normal load (5-10 concurrent requests), this was not immediately noticeable. However, during peak hours on November 4 (10:00-11:00 UTC), concurrent requests increased to 50+, exhausting the connection pool (20 connections) and causing all new database queries to fail.

**Why It Happened:**
1. **Lack of Query Performance Testing:** Migration was tested with low-volume data (10 tenants), did not expose performance issue at scale
2. **Missing Index:** `tenant_configs` table lacked index on `tenant_id` column (frequently queried)
3. **Connection Pool Size:** Pool size (20) was tuned for previous query patterns, insufficient for slow queries
4. **Insufficient Monitoring:** No alert for query duration >5s (only connection pool exhaustion alert)

**Contributing Factors:**
- Peak hour traffic spike (50% above normal)
- Recent deployment did not have gradual rollout (deployed to 100% of traffic immediately)
- Lack of automated performance testing in CI/CD pipeline

---

## What Went Well

- ✅ **Fast Detection:** Alert fired within 2 minutes of connection pool exhaustion
- ✅ **Effective Triage:** On-call correctly assessed severity as P0 and escalated immediately
- ✅ **Clear Communication:** Client notified within 15 minutes, updates every 30 minutes
- ✅ **Successful Containment:** Killing long-running queries restored service temporarily while fix was deployed
- ✅ **Teamwork:** Engineering, Support, and IC collaborated effectively in war room

---

## What Went Wrong

- ❌ **Slow Root Cause Identification:** Took 20 minutes to identify slow query (expected <10 minutes)
  - **Why:** Distributed tracing not initially used, relied on log analysis first
- ❌ **No Gradual Rollout:** Deployment went to 100% traffic, amplifying impact
- ❌ **Insufficient Testing:** Migration performance testing only used 10 tenants, not representative of production load
- ❌ **Missing Alert:** No alert for query duration >5s (would have caught issue pre-outage)

---

## Action Items

| Action Item | Owner | Due Date | Priority | Status |
|-------------|-------|----------|----------|--------|
| Add index on `tenant_configs.tenant_id` column | Sarah Chen (Engineering) | 2025-11-05 | P0 | ✅ Done |
| Increase connection pool size from 20 → 40 | Sarah Chen | 2025-11-05 | P0 | ✅ Done |
| Add Prometheus alert for query duration >5s | Mike Johnson (SRE) | 2025-11-08 | P1 | In Progress |
| Implement gradual rollout for database migrations (10% → 50% → 100%) | DevOps Team | 2025-11-15 | P1 | Not Started |
| Add automated performance testing to CI/CD (test with 100+ tenants) | QA Team | 2025-11-20 | P2 | Not Started |
| Update runbook: Add "Check slow queries" step to DatabaseConnectionIssues | Jane Doe (Support) | 2025-11-06 | P2 | ✅ Done |
| Conduct distributed tracing training for L1/L2 Support | Training Team | 2025-11-12 | P2 | Scheduled |

---

## Lessons Learned

**For Engineering:**
1. **Performance testing must use production-scale data** - 10 tenants ≠ 100 tenants
2. **Gradual rollouts reduce blast radius** - Even database migrations should roll out incrementally
3. **Distributed tracing should be first tool** for performance investigations, not logs

**For Support:**
1. **Use distributed tracing early** - Would have identified slow query in <5 minutes
2. **Proactive communication worked well** - Client appreciated frequent updates despite outage

**For SRE:**
1. **Alert on leading indicators** (query duration) not just lagging indicators (connection pool exhaustion)
2. **Connection pool sizing** should account for worst-case query latency, not just average

---

## Follow-Up Review

**Review Meeting:**
- **Date:** 2025-11-06 (2 days after incident)
- **Attendees:** Engineering Team, Support Team, SRE Team, Engineering Manager
- **Outcome:** All action items reviewed, owners assigned, priorities confirmed

**Action Item Tracking:**
- Weekly review of action item progress in team standup
- P0/P1 items due within 1 week, P2 items due within 2 weeks
- Postmortem re-review after all action items complete (estimated 2025-11-20)

---

## Appendix

**Supporting Documents:**
- Incident Timeline: https://docs.google.com/document/d/[doc-id]
- Slack War Room: #incident-20251104-1030
- Prometheus Alerts: [Screenshot or link]
- Grafana Dashboard: [Link to dashboard with incident timeframe]
- Distributed Trace: [Link to Jaeger trace for slow query]

**Related Incidents:**
- None (first occurrence of this issue)
```

---

## Additional Resources

### Incident Response Best Practices

- [Production Support Guide](production-support-guide.md) - System troubleshooting reference
- [Alert Response Runbooks](../operations/alert-runbooks.md) - 11 scenario-specific runbooks
- [On-Call Rotation Documentation](on-call-rotation.md) - On-call procedures and responsibilities

### External Frameworks

- **NIST Incident Response Lifecycle:** Preparation → Detection/Analysis → Containment/Eradication/Recovery → Post-Incident Activity
- **Google SRE Incident Management:** Incident Command System, blameless postmortems, learning culture
- **PICERL Framework:** Comprehensive incident response with focus on preparation and learning

### Tools

- **Incident Tracking:** PagerDuty, incident.io, or Jira
- **Communication:** Slack (#incidents-p0, #incidents-p1), Email (templates above)
- **Timeline Documentation:** Google Docs, Confluence, or incident.io timeline
- **Monitoring:** Grafana dashboards, Prometheus alerts, distributed tracing (Jaeger/Uptrace)

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-04 | Initial incident response playbook created (Story 5.6) | Dev Agent (AI) |

---

**Document Maintenance:**
- **Review Frequency:** After every P0/P1 incident, or quarterly if no incidents
- **Owner:** Incident Management Lead (Support Team Lead or SRE Manager)
- **Update Triggers:** Postmortem findings, process improvements, organizational changes

**Feedback:** Report playbook gaps or improvements via `#incident-management-feedback` Slack channel.
