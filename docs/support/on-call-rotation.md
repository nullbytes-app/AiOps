# On-Call Rotation Schedule
**AI Agents Platform - 24x7 Support Coverage**

**Document Version:** 1.0
**Last Updated:** 2025-11-04
**Target Audience:** On-Call Engineers, Support Team
**Status:** Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [On-Call Coverage Model](#on-call-coverage-model)
3. [Rotation Schedule Template](#rotation-schedule-template)
4. [On-Call Responsibilities](#on-call-responsibilities)
5. [On-Call Notification System](#on-call-notification-system)
6. [Handoff Procedures](#handoff-procedures)
7. [On-Call Runbook (P0/P1 Scenarios)](#on-call-runbook-p0p1-scenarios)

---

## Overview

### Purpose

This document defines the **24x7 on-call rotation** for the AI Agents platform, ensuring continuous support coverage, rapid incident response, and clear handoff procedures between shifts.

### On-Call Principles

1. **Always Available:** On-call engineer must be reachable within 5 minutes during their shift
2. **Always Prepared:** Laptop with VPN access, PagerDuty/Slack notifications enabled
3. **Escalate Early:** Better to wake someone up unnecessarily than delay resolution
4. **Document Everything:** All actions logged in incident timeline or support tickets
5. **Take Care of Yourself:** Sleep, rest, and self-care between shifts

### Support Coverage Scope

**What On-Call Covers:**
- P0/P1 incidents requiring immediate response
- Client-reported critical issues (complete service down, data loss)
- Automated alert responses (Prometheus alerts via Alertmanager)
- Emergency escalations from clients or internal stakeholders

**What On-Call Does NOT Cover:**
- P2/P3 issues (handled during business hours)
- Feature requests or enhancements (routed to product team)
- General questions or "how-to" support (knowledge base or email support)
- Planned maintenance or deployments (scheduled with Engineering)

---

## On-Call Coverage Model

### Coverage Structure: 24x7 Primary + Backup

**Model:** Follow-the-sun + backup coverage

**Primary On-Call Tiers:**
- **Tier 1 (L1):** Support Engineer (first responder)
- **Tier 2 (L2):** Senior Support Engineer (escalation for P0/P1)
- **Tier 3 (Engineering):** Engineering On-Call (code fixes, infrastructure changes)

**Backup Coverage:**
- Each tier has a designated backup on-call
- Backup receives escalation if primary does not respond within 10 minutes
- Backup is on "shadow" rotation (not actively monitoring unless escalated)

### Rotation Duration

**Primary On-Call:**
- **Duration:** 7 days (Monday 9:00 AM → Monday 9:00 AM, local time)
- **Rationale:** Longer rotations reduce handoff frequency, provide continuity
- **Exceptions:** Holiday weeks may have shorter rotations (3-4 days) with volunteer coverage

**Backup On-Call:**
- **Duration:** 7 days (same as primary, but different person)
- **Overlap:** Backup rotates opposite schedule from primary (week A primary = week B backup)

### Team Size and Rotation Frequency

**Current Team Size:**
- **L1 Support Engineers:** 4 people
- **L2 Senior Support Engineers:** 2 people
- **L3 Engineering On-Call:** 5 people (Engineering team)

**Rotation Frequency (per person):**
- **L1:** On-call every 4 weeks (1 week on, 3 weeks off)
- **L2:** On-call every 2 weeks (1 week on, 1 week off)
- **L3:** On-call every 5 weeks (Engineering team rotates separately)

**Rationale:** Balances workload distribution, prevents burnout, ensures team coverage

---

## Rotation Schedule Template

### Monthly Schedule Example (December 2025)

**L1 Primary On-Call:**

| Week | Dates | Primary On-Call | Backup On-Call | Notes |
|------|-------|-----------------|----------------|-------|
| 1 | Dec 1-7 | Alice Johnson | Bob Smith | - |
| 2 | Dec 8-14 | Bob Smith | Charlie Lee | - |
| 3 | Dec 15-21 | Charlie Lee | Dana Martinez | Holiday week - short shifts available |
| 4 | Dec 22-28 | Dana Martinez | Alice Johnson | Holiday week - volunteer coverage |
| 5 | Dec 29-31 | Alice Johnson | Bob Smith | Partial week (3 days) |

**L2 Escalation On-Call:**

| Week | Dates | Primary On-Call | Backup On-Call | Notes |
|------|-------|-----------------|----------------|-------|
| 1-2 | Dec 1-14 | Emma Wilson | Frank Davis | - |
| 3-4 | Dec 15-28 | Frank Davis | Emma Wilson | Holiday coverage coordinated |
| 5 | Dec 29-31 | Emma Wilson | Frank Davis | Partial week |

**L3 Engineering On-Call:**
- Managed by Engineering team separately
- Always available for L1/L2 escalation
- Typical rotation: 1 week on-call, 4 weeks off

---

### Schedule Management Tools

**Recommended Tools:**
- **PagerDuty:** Automated on-call scheduling with rotation rules
- **Opsgenie:** Alternative with similar features
- **Google Calendar:** Shared calendar with on-call shifts (backup to PagerDuty)
- **Confluence/Notion:** On-call schedule wiki page

**Manual Schedule (Spreadsheet):**
- Use above template in Google Sheets if no dedicated tool available
- Share publicly with team (read-only)
- Owner: Support Team Lead updates schedule monthly

---

## On-Call Responsibilities

### Pre-Shift Preparation (Before Your Shift Starts)

**24 Hours Before Shift:**
- [ ] **Review recent incidents:** Read postmortems, check #incidents-* Slack channels
- [ ] **Check handoff notes:** Review previous on-call's handoff (if available)
- [ ] **Test access:**
  - VPN connected
  - kubectl access verified: `kubectl get pods -n ai-agents-production`
  - Grafana login tested: http://localhost:3000
  - Database access tested: `psql $DATABASE_URL -c "SELECT 1"`
- [ ] **Verify notifications:**
  - PagerDuty app installed, notifications enabled
  - Slack notifications enabled (#incidents-*, DMs)
  - Phone ringer volume UP, not on silent
- [ ] **Prepare laptop:** Fully charged, not in repair, ready to use

**1 Hour Before Shift:**
- [ ] **Read handoff from previous on-call** (see Handoff Procedures below)
- [ ] **Acknowledge on-call status** in PagerDuty or Slack (#on-call channel)
- [ ] **Review current system status:**
  - Check Grafana dashboards (any anomalies?)
  - Check active alerts in Prometheus
  - Check queue depth, worker health, API latency

---

### During Your Shift

#### Active Monitoring (Proactive)

**Periodic Health Checks (2-3 times per day during waking hours):**
```bash
# Quick health check script (5 minutes)
bash /Users/ravi/Documents/nullBytes_Apps/Ai_Agents/AI\ Ops/scripts/health-check.sh

# Manual checks:
# 1. Grafana Operations Dashboard - any red metrics?
# 2. Prometheus - any firing alerts?
# 3. Slack #alerts channel - any recent alerts?
# 4. PagerDuty - any open incidents?
```

**Proactive Actions:**
- Monitor queue depth trends (scale workers proactively if increasing)
- Review error logs for patterns (are certain errors increasing?)
- Check upcoming scheduled maintenance (deployments, database patches)

---

#### Reactive Response (Incident Response)

**When Alert Fires:**

**Step 1: Acknowledge Alert (Within 5 Minutes)**
- PagerDuty: Click "Acknowledge" button
- Slack: React with 👀 emoji to alert message
- This stops escalation to backup on-call

**Step 2: Initial Triage (First 5 Minutes)**
1. **Read alert details:** What metric triggered? Which component?
2. **Check Grafana:** How severe is the issue? Trending worse or stable?
3. **Assess severity:** Is this P0, P1, P2, or P3? (Use [Severity Definitions](incident-response-playbook.md#severity-level-definitions))
4. **Determine urgency:** Does this require immediate action or can wait until morning?

**Step 3: Respond According to Severity**
- **P0/P1:** Declare incident, follow [Incident Response Workflow](incident-response-playbook.md#incident-response-workflow)
- **P2:** Investigate and resolve using runbooks, escalate to L2 if stuck >30 minutes
- **P3:** Acknowledge alert, create ticket for business hours, resolve if quick (<15 min)

**Step 4: Document Actions**
- Log actions in support ticket or incident timeline
- Update alert status (acknowledged, investigating, resolved)
- If escalated, provide handoff summary

---

#### Client-Reported Issues

**When Client Emails/Calls:**

**Step 1: Gather Information**
- Client name, tenant ID
- Issue description (specific ticket ID, error message, timeframe)
- Severity assessment (is this P0/P1 or can wait?)

**Step 2: Verify Issue**
- Check monitoring: Is this systemic issue or isolated to one client?
- Review logs: Can you reproduce the issue?
- Check recent deployments: Was there a recent change?

**Step 3: Respond and Resolve**
- **P0/P1:** Declare incident, follow incident response playbook
- **P2/P3:** Investigate using [Client Support Procedures](client-support-procedures.md), resolve or create ticket for business hours
- **Client communication:** Send acknowledgement email within 30 minutes (use templates from [Incident Response Playbook](incident-response-playbook.md#communication-templates))

---

### End-of-Shift Handoff

**1 Hour Before Shift Ends:**
- [ ] **Document handoff notes** (use template below)
- [ ] **Review open incidents/tickets** - what is in-progress?
- [ ] **Check pending escalations** - anything requiring follow-up?
- [ ] **Post handoff notes** in Slack #on-call channel or PagerDuty
- [ ] **Optional: Schedule brief sync call** with incoming on-call (15 minutes)

---

## On-Call Notification System

### PagerDuty Setup (Recommended)

**Configuration:**
1. **Service:** `ai-agents-production`
2. **Escalation Policy:**
   - **Level 1 (L1):** Primary on-call → Notify immediately
   - **Level 2 (L1 Backup):** If no response after 10 minutes → Page backup
   - **Level 3 (L2):** If no response after 20 minutes → Page L2 on-call
   - **Level 4 (Engineering):** If no response after 30 minutes → Page Engineering on-call

**Alert Routing:**
- **Prometheus Alerts** → Alertmanager → PagerDuty webhook
- **Client-Reported P0/P1** → Support creates PagerDuty incident manually
- **Manual Trigger:** PagerDuty mobile app or web UI

**Notification Methods:**
- **Phone Call:** For P0 incidents (immediate response required)
- **SMS:** For P1 incidents
- **Push Notification:** For P2/P3 incidents (acknowledge within 30 minutes)

---

### Alertmanager Integration

**Configuration File:** `k8s/alertmanager-config.yaml`

**Routing Rules:**
```yaml
routes:
  - match:
      severity: critical  # P0
    receiver: pagerduty-critical
    continue: true
  - match:
      severity: warning   # P1
    receiver: pagerduty-warning
  - match:
      severity: info      # P2/P3
    receiver: slack-alerts
```

**Receivers:**
- `pagerduty-critical`: Phone call + SMS to L1 on-call
- `pagerduty-warning`: SMS to L1 on-call
- `slack-alerts`: Post to #alerts Slack channel (no page)

**Reference:** [docs/operations/alertmanager-setup.md](../operations/alertmanager-setup.md)

---

### Slack Notifications

**Channels:**
- **#alerts:** All Prometheus alerts (P2/P3, informational)
- **#incidents-p0:** P0 incidents only
- **#incidents-p1:** P1 incidents only
- **#on-call:** On-call handoff notes, schedule updates

**Notification Settings (for on-call):**
- **#incidents-p0, #incidents-p1:** 🔔 All messages notify
- **#alerts:** 🔕 Muted (check manually, don't notify)
- **DMs from PagerDuty bot:** 🔔 Notify

---

### Testing Notification System

**Monthly Test (First Monday of Month):**
```bash
# Trigger test alert via Alertmanager
curl -X POST http://localhost:9093/api/v1/alerts -d '[{
  "labels": {
    "alertname": "TestAlert",
    "severity": "warning",
    "instance": "test"
  },
  "annotations": {
    "summary": "Monthly on-call notification test"
  }
}]'
```

**Validation:**
- [ ] PagerDuty incident created
- [ ] On-call receives SMS/push notification within 2 minutes
- [ ] Slack #alerts channel receives message
- [ ] On-call acknowledges alert
- [ ] Incident auto-resolves after acknowledgement

**If Test Fails:** Escalate to Engineering to fix Alertmanager configuration

---

## Handoff Procedures

### Handoff Note Template

**Post in Slack #on-call channel or PagerDuty notes:**

```
🔄 ON-CALL HANDOFF: [Outgoing Name] → [Incoming Name]
─────────────────────────────────────────────────────
Shift: [Start Date Time] → [End Date Time]
Outgoing: [Your Name]
Incoming: [Next On-Call Name]

INCIDENT SUMMARY:
─────────────────
• Total Alerts: [Number]
• P0 Incidents: [Number] ([List incident IDs or "None"])
• P1 Incidents: [Number] ([List incident IDs or "None"])
• P2/P3 Issues: [Number] (all resolved or ticketed)

OPEN INCIDENTS:
───────────────
[If none: "None - all incidents resolved ✅"]
[If open:]
• INC-20251104-1030 (P1) - High queue depth
  Status: Resolved, monitoring for recurrence
  Follow-up: Watch queue depth trend next 24 hours

PENDING ESCALATIONS:
────────────────────
[If none: "None"]
[If pending:]
• Client: MSP Acme Corp - Ticket #12345 investigation
  Status: Waiting for Engineering root cause analysis
  Expected: Resolution by EOD tomorrow
  Action: Follow up with Engineering in AM

SYSTEM STATUS:
──────────────
• Queue Depth: [Current value, trend]
• Worker Health: [All healthy / X workers crashed - see note]
• API Latency: [p95 latency value]
• Active Alerts: [Number firing, list if any]
• Recent Deployments: [Any deployments in last 24 hours?]

NOTABLE EVENTS:
───────────────
[If none: "Quiet shift, no major events"]
[If notable:]
• 2025-11-04 14:30 - Worker scaling triggered due to queue spike (resolved)
• 2025-11-04 18:00 - Client reported slow enhancements (investigated, ServiceDesk Plus API slow)

UPCOMING:
─────────
[If nothing: "No scheduled maintenance or known issues"]
[If upcoming:]
• 2025-11-05 02:00 - Scheduled database maintenance (expected downtime: 15 minutes)
• High ticket volume expected tomorrow (client onboarding new technicians)

HANDOFF COMPLETE: [Time]
Incoming on-call: Please acknowledge ✅
```

---

### Handoff Checklist

**Outgoing On-Call:**
- [ ] Complete handoff note (use template above)
- [ ] Post in #on-call Slack channel
- [ ] Tag incoming on-call: @[name]
- [ ] Offer sync call if complex handoff (>2 open incidents or escalations)
- [ ] Transfer open incident ownership in PagerDuty

**Incoming On-Call:**
- [ ] Read handoff note thoroughly
- [ ] Acknowledge handoff with ✅ emoji or reply
- [ ] Review open incidents (read timelines, understand current status)
- [ ] Check Grafana dashboards (validate system status)
- [ ] Accept incident ownership in PagerDuty
- [ ] Ask questions if anything unclear

---

### Handoff Scenarios

#### Scenario 1: Clean Handoff (No Open Incidents)

```
🔄 ON-CALL HANDOFF: Alice → Bob
Shift: Nov 4 9:00 AM → Nov 11 9:00 AM
Outgoing: Alice Johnson
Incoming: Bob Smith

INCIDENT SUMMARY:
• Total Alerts: 3 (all resolved)
• P0/P1 Incidents: None ✅
• P2/P3 Issues: 2 (both resolved)

OPEN INCIDENTS: None ✅

PENDING ESCALATIONS: None

SYSTEM STATUS:
• Queue Depth: 12 jobs (normal, trending stable)
• Worker Health: All 5 workers healthy
• API Latency: p95 = 850ms (within SLA)
• Active Alerts: 0
• Recent Deployments: None

NOTABLE EVENTS:
• Nov 6 - Routine worker restart (HPA scale-down during low traffic)
• Nov 9 - Client feedback API query slow (resolved, added index)

UPCOMING: None

HANDOFF COMPLETE: Nov 11 9:00 AM
@Bob Smith - please acknowledge ✅
```

**Bob's Response:** ✅ Acknowledged, thanks Alice! Have a great week off.

---

#### Scenario 2: Active Incident Handoff

```
🔄 ON-CALL HANDOFF: Charlie → Dana
Shift: Nov 11 9:00 AM → Nov 18 9:00 AM
Outgoing: Charlie Lee
Incoming: Dana Martinez

⚠️ ACTIVE INCIDENT IN PROGRESS ⚠️

INCIDENT SUMMARY:
• Total Alerts: 12
• P0 Incidents: 0
• P1 Incidents: 1 (ACTIVE - INC-20251118-0800)
• P2/P3 Issues: 5 (all resolved)

OPEN INCIDENTS:
• INC-20251118-0800 (P1) - Database slow queries causing API latency >5s
  Status: IN PROGRESS
  Root Cause: Identified - missing index on enhancements.created_at
  Current Action: Engineering deploying index creation (ETA: 30 minutes)
  Timeline: https://docs.google.com/document/d/[doc-id]
  Incident Commander: Emma Wilson (L2)
  Client Impact: MSP Acme Corp experiencing delays (notified at 8:15 AM)

  🚨 ACTION REQUIRED: Monitor index creation completion, validate query performance, send "All Clear" to client

PENDING ESCALATIONS: None (Engineering already engaged)

SYSTEM STATUS:
• Queue Depth: 45 jobs (elevated due to slow processing)
• Worker Health: All healthy, scaled to 8 workers (from 5)
• API Latency: p95 = 6.2s (degraded, expect improvement after index)
• Active Alerts: 1 (HighAPILatency - will resolve after fix)
• Recent Deployments: None

UPCOMING:
• Index creation deployment ETA: 9:30 AM
• Post-incident monitoring: Watch latency trend for 1 hour after fix

HANDOFF COMPLETE: Nov 18 9:00 AM

🔴 RECOMMEND: 15-minute sync call with Dana before I sign off
@Dana Martinez - Let's hop on a quick call?
```

**Dana's Response:** ✅ Acknowledged. Joining incident timeline now. Let's sync in 5 minutes.

---

## On-Call Runbook (P0/P1 Scenarios)

**Quick reference for critical scenarios during on-call shift**

### Scenario 1: Complete Service Outage (P0)

**Symptoms:**
- All webhooks failing (100% delivery failure)
- Database completely unavailable
- All pods in CrashLoopBackOff

**Immediate Actions (First 5 Minutes):**
1. **Declare P0 incident** (PagerDuty, Slack #incidents-p0)
2. **Page L2 on-call** (will become Incident Commander)
3. **Page Engineering on-call** (infrastructure/code fix required)
4. **Post initial status** in Slack:
   ```
   🚨 P0 INCIDENT DECLARED: Complete service outage
   All clients affected. Engineering paged.
   War room: #incident-[timestamp]
   ```
5. **Start incident timeline** (Google Doc)
6. **Follow Incident Response Playbook:** [incident-response-playbook.md](incident-response-playbook.md)

**Do NOT:**
- ❌ Attempt complex fixes alone (escalate immediately)
- ❌ Restart all services without understanding root cause
- ❌ Delay client notification (send within 30 minutes)

---

### Scenario 2: High Queue Depth (P1)

**Symptoms:**
- Queue depth >100 jobs
- Enhancements delayed >10 minutes
- Client complaints increasing

**Immediate Actions:**
1. **Check queue depth trend** (Grafana - is it increasing or stable?)
   ```bash
   kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- redis-cli -h redis LLEN celery
   ```
2. **Check worker health** (are workers processing or crashed?)
   ```bash
   kubectl get pods -n ai-agents-production | grep worker
   kubectl top pods -n ai-agents-production | grep worker
   ```
3. **Scale workers immediately** (double current count)
   ```bash
   kubectl scale deployment/ai-agents-worker -n ai-agents-production --replicas=10
   ```
4. **Monitor queue drainage** (Grafana, expect 5-10 jobs/minute decrease)
5. **If queue NOT draining:** Check for stuck jobs (worker logs), escalate to L2

**Detailed Runbook:** [docs/runbooks/high-queue-depth.md](../runbooks/high-queue-depth.md)

---

### Scenario 3: Database Connection Failures (P1)

**Symptoms:**
- API/workers unable to query database
- Logs show "connection refused" or "too many clients"

**Immediate Actions:**
1. **Test database connectivity:**
   ```bash
   kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- psql $DATABASE_URL -c "SELECT version();"
   ```
2. **Check connection pool status:**
   ```bash
   kubectl logs deployment/ai-agents-api -n ai-agents-production | grep "connection pool"
   ```
3. **If connection pool exhausted:** Kill idle connections
   ```sql
   SELECT pg_terminate_backend(pid) FROM pg_stat_activity
   WHERE state = 'idle' AND state_change < now() - interval '10 minutes';
   ```
4. **If database unavailable:** **Escalate to Engineering immediately** (P0 if complete outage)
5. **Monitor recovery:** Validate queries succeed, check error logs

**Detailed Runbook:** [docs/runbooks/database-connection-issues.md](../runbooks/database-connection-issues.md)

---

### Scenario 4: Client Reports Security Concern (P0)

**Symptoms:**
- Client reports seeing other client's data
- Unauthorized access suspected
- Cross-tenant data leak

**Immediate Actions:**
1. **DO NOT DISMISS** - treat all security reports as P0 until proven otherwise
2. **Declare P0 incident** (security breach)
3. **Page L2 + Engineering + Engineering Manager** (all hands)
4. **Isolate affected tenant immediately:**
   ```bash
   # Disable webhook access for tenant (if needed)
   kubectl scale deployment/ai-agents-api -n ai-agents-production --replicas=0
   # (Drastic measure - only if active breach confirmed)
   ```
5. **Preserve evidence:**
   - Collect audit logs
   - Export API logs
   - Screenshot client-reported issue
6. **Follow Incident Response Playbook** with security focus
7. **Notify Executive immediately** (CTO, Security Officer)

**Do NOT:**
- ❌ Investigate alone (this requires Engineering + Security)
- ❌ Downplay client concern (take seriously until proven false positive)
- ❌ Modify audit logs or evidence

---

### Scenario 5: Late-Night Non-Urgent Alert (P3)

**Symptoms:**
- Alert fires at 2:00 AM
- Severity: P3 (info)
- Example: "GrafanaDashboardLoadSlow"

**Decision Framework:**

**Option 1: Resolve Immediately (If Quick)**
- If fix is obvious and takes <10 minutes (e.g., restart Grafana pod)
- Document action, resolve alert, go back to sleep

**Option 2: Acknowledge and Ticket for Morning**
- If fix requires investigation or is non-urgent
- Acknowledge alert (stop paging)
- Create support ticket: "P3: [Alert Name] - investigate during business hours"
- Add note to on-call handoff
- Resolve alert, go back to sleep

**Option 3: Escalate If Uncertain**
- If you're unsure whether it's actually urgent
- Better to escalate and be wrong than ignore a real issue
- Page L2 for second opinion

**Guideline:** Preserve sleep for real emergencies. P3 alerts can wait until morning unless trivial fix.

---

## Additional Resources

### Documentation

- [Production Support Guide](production-support-guide.md) - Comprehensive troubleshooting reference
- [Incident Response Playbook](incident-response-playbook.md) - Structured incident management
- [Client Support Procedures](client-support-procedures.md) - Client-facing support operations
- [Alert Response Runbooks](../operations/alert-runbooks.md) - 11 scenario-specific runbooks

### Tools and Access

- **PagerDuty:** https://ai-agents.pagerduty.com
- **Grafana:** http://localhost:3000 (local) or production URL
- **Prometheus:** http://localhost:9090
- **Alertmanager:** http://localhost:9093
- **Slack Channels:** #incidents-p0, #incidents-p1, #alerts, #on-call

### Training and Onboarding

- **New On-Call Onboarding:** Shadow experienced on-call for 1 week before first solo shift
- **Incident Response Training:** Completed before first on-call shift (see [Support Team Training](TODO))
- **Mock Incident Drills:** Quarterly practice drills (see [Mock Incident Drill](TODO))

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-04 | Initial on-call rotation documentation created (Story 5.6) | Dev Agent (AI) |

---

**Document Maintenance:**
- **Review Frequency:** Monthly or after rotation process changes
- **Owner:** Support Team Lead
- **Update Triggers:** Team size changes, new tools adopted, process improvements from postmortems

**Feedback:** Report on-call process issues via `#on-call-feedback` Slack channel.
