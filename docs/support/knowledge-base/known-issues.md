# Known Issues (November 2025)

**Category:** Known Issues
**Last Updated:** 2025-11-04
**Status:** Active (Production MVP)
**Review Frequency:** Weekly

---

## Overview

This document tracks **known issues** in the AI Agents platform production environment, identified during Epic 4-5 deployment and validation. Each issue includes workarounds, planned fixes, and ownership.

**Issue Status Key:**
- 🔴 **Open** - Issue active, no fix deployed
- 🟡 **In Progress** - Fix being developed
- 🟢 **Resolved** - Fix deployed to production
- ⏸️ **Deferred** - Acknowledged, planned for future release

---

## Critical Issues (P0/P1)

### None Currently

---

## Important Issues (P2)

### 1. Network Troubleshooting Enhancements (Lower Quality)

**Status:** 🟡 In Progress
**Severity:** P2
**Discovered:** 2025-11-02 (Story 5.4 validation testing)
**Affects:** MVP Client (MSP Acme Corp)

**Description:**
Client feedback shows network-related tickets receive lower quality enhancements (average rating 3.2/5 vs. 4.4/5 overall). Technicians report suggestions are too generic or miss network-specific context.

**Root Cause:**
Knowledge base has limited network troubleshooting documentation. GPT-4 lacks sufficient network-specific context (VLAN configurations, routing tables, firewall rules) to provide actionable guidance.

**Impact:**
- ~15% of tickets (network issues) get lower satisfaction
- Technicians resort to manual research, reducing time savings
- Client feedback trending downward for network tickets

**Workaround:**
- Set client expectations: Acknowledge network enhancements are still improving
- Collect specific ticket examples for Engineering review
- Manual enhancement support available for critical network issues

**Planned Fix:**
- Engineering adding network troubleshooting documentation to knowledge base (ETA: 2025-11-15)
- Prompt tuning to prioritize network context sources (ETA: 2025-11-20)
- Validation testing with 20 network tickets post-fix

**Owner:** Engineering Team (Sarah Chen)
**Tracking:** JIRA-234

---

### 2. Peak Hour HPA Scaling Lag

**Status:** 🔴 Open
**Severity:** P2
**Discovered:** 2025-11-03 (Story 5.5 baseline metrics collection)
**Affects:** All Clients (during peak hours 9:00-11:00 AM EST)

**Description:**
During morning peak hours (client business start), queue depth spikes to 40-60 jobs before HPA scales workers. Enhancements delayed 5-10 minutes during this window, then return to normal as workers scale up.

**Root Cause:**
HPA scale-up threshold (5 jobs/worker) with 2-minute evaluation window causes delayed response to sudden traffic spikes. Current min workers (2) insufficient for peak hour traffic (20+ concurrent tickets).

**Impact:**
- 10-15 minute period of degraded performance (5-10 min latency)
- Occurs daily 9:00-11:00 AM EST
- Client aware, acceptable per SLA (p95 <60s overall maintained)

**Workaround:**
- Manual scaling before peak hours (temporarily increase min workers to 5)
- Monitor queue depth proactively, scale manually if >30 jobs

**Planned Fix:**
- Increase HPA min workers from 2 → 4 (ETA: 2025-11-10)
- Lower scale-up threshold from 5 jobs/worker → 3 jobs/worker for faster response
- Implement predictive scaling based on time-of-day patterns (future enhancement)

**Owner:** SRE Team (Mike Johnson)
**Tracking:** JIRA-245

---

### 3. ServiceDesk Plus API Rate Limiting (Occasional)

**Status:** 🔴 Open
**Severity:** P2
**Discovered:** 2025-11-02 (Story 5.3 client onboarding)
**Affects:** MVP Client (MSP Acme Corp) - intermittent

**Description:**
ServiceDesk Plus API occasionally rate-limits requests (429 Too Many Requests) during high-volume periods. Workers retry with exponential backoff (5s, 15s, 45s), causing some enhancements delayed up to 60s beyond normal latency.

**Root Cause:**
ServiceDesk Plus cloud instance has undocumented rate limit (~50 requests/minute). When multiple workers simultaneously update tickets, limit exceeded.

**Impact:**
- ~2-3% of enhancements experience retry delays
- Overall success rate unaffected (retries succeed)
- Minimal client impact (within p95 <60s SLA)

**Workaround:**
- Workers automatically retry with backoff (no manual intervention)
- Monitor success rate, escalate if <95%

**Planned Fix:**
- Implement request throttling/queuing in worker layer (ETA: 2025-11-25)
- Cache ServiceDesk Plus API responses where appropriate (reduce API calls)
- Work with client to upgrade ServiceDesk Plus tier for higher rate limits

**Owner:** Engineering Team (Tom Wilson)
**Tracking:** JIRA-256

---

## Minor Issues (P3)

### 4. Grafana Dashboard Load Time (Slow on First Access)

**Status:** ⏸️ Deferred
**Severity:** P3
**Discovered:** 2025-11-01 (Story 4.3 Grafana deployment)
**Affects:** All Users (first access after idle period)

**Description:**
Grafana dashboards take 10-15 seconds to load on first access after 30+ minutes of inactivity. Subsequent accesses fast (<2s).

**Root Cause:**
Grafana datasource query cache expires after 30 minutes. First query re-fetches all metric series from Prometheus.

**Impact:**
- Cosmetic issue, no functional impact
- Affects observability during urgent incidents (slower initial dashboard load)

**Workaround:**
- Keep Grafana tabs open to prevent cache expiration
- Use Prometheus directly for urgent queries during incidents

**Planned Fix:**
- Deferred to v1.1 (low priority)
- Consider Grafana query caching configuration tuning
- Alternative: Pre-warm cache with periodic background queries

**Owner:** SRE Team (backlog)
**Tracking:** JIRA-267

---

### 5. Feedback API Response Time (Slow with Large Date Ranges)

**Status:** 🔴 Open
**Severity:** P3
**Discovered:** 2025-11-03 (Story 5.5 feedback API testing)
**Affects:** Support Engineers (when querying >30 days feedback)

**Description:**
`GET /api/v1/feedback` endpoint slow (5-10s response) when querying date ranges >30 days, especially for high-volume tenants.

**Root Cause:**
Missing database index on `enhancement_feedback.created_at` column. Full table scans for date range queries.

**Impact:**
- Support investigations delayed (waiting for API response)
- No client impact (client-facing API performant)
- Workaround available (use smaller date ranges)

**Workaround:**
- Query smaller date ranges (7-14 days) for faster responses
- Use Grafana dashboard instead of API for trend analysis

**Planned Fix:**
- Add index on `enhancement_feedback.created_at` column (ETA: 2025-11-08)
- Add query result caching for common date ranges
- Migration execution scheduled during low-traffic window

**Owner:** Engineering Team (Sarah Chen)
**Tracking:** JIRA-278

---

## Resolved Issues

### ✅ 1. Database Connection Pool Exhaustion (Resolved 2025-11-04)

**Original Issue:**
Slow database queries caused connection pool exhaustion during peak hours, leading to API/worker errors.

**Resolution:**
- Added index on `tenant_configs.tenant_id` (eliminated full table scans)
- Increased connection pool size from 20 → 40
- Optimized slow query (migration deployment configuration query)

**Validation:**
- No connection pool errors since fix deployed
- Database connection utilization <60% during peak hours
- Postmortem: INC-20251104-1030

**Related:** See [Incident Postmortem Template](../../support/incident-response-playbook.md#postmortem-template) for full details

---

### ✅ 2. Worker Memory Leaks (OOMKilled) (Resolved 2025-10-28)

**Original Issue:**
Workers crashed with OOMKilled after processing 50-100 jobs, causing service degradation.

**Resolution:**
- Fixed memory leak in LangGraph workflow context cleanup
- Increased worker memory limit from 512MB → 1GB (safety buffer)
- Added memory utilization monitoring

**Validation:**
- Workers now process 500+ jobs without restart
- No OOMKilled events since fix deployed (7 days uptime)

---

## Issue Reporting & Tracking

### How to Report New Issues

**Support Engineers:**
1. **Verify issue reproducible** (not one-time glitch)
2. **Check if already documented** (search this page)
3. **Create JIRA ticket** with template:
   - Title: [Component] Brief description
   - Severity: P0/P1/P2/P3
   - Impact: Who/what affected
   - Reproduction steps: How to reproduce
   - Workaround: If available
4. **Add to Known Issues doc:** Create PR or notify Support Team Lead
5. **Communicate** in #support-team Slack channel

**Engineering:**
- Add issue during postmortem process
- Update this doc within 48 hours of issue discovery

---

### Issue Lifecycle

```
Discovered → Triaged → In Progress → Testing → Resolved → Archived
     ↓           ↓           ↓            ↓         ↓         ↓
  This doc   Assigned    Fixing    Staging   Production  Postmortem
```

**SLAs:**
- **P2 Issues:** Fix within 2 weeks or provide updated ETA
- **P3 Issues:** Fix within 1 month or defer to next release
- **Resolved Issues:** Archive to "Resolved" section after 30 days in production

---

## Client Communication

### MVP Client (MSP Acme Corp)

**Known Issues Shared:**
- Issue #1 (Network troubleshooting quality) - Acknowledged, improvement timeline communicated
- Issue #2 (Peak hour scaling lag) - Client aware, within SLA tolerance
- Issue #3 (ServiceDesk Plus rate limiting) - Client contacted about tier upgrade

**Weekly Update:**
- Monday 10:00 AM: Metrics review includes known issues status
- Template: [Weekly Metrics Review](../../metrics/weekly-metrics-review-template.md)

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-04 | Initial known issues from Epic 4-5 learnings (Story 5.6) | Dev Agent (AI) |

---

**Document Owner:** Support Team Lead
**Review Frequency:** Weekly (Monday before client metrics review)
**Update Triggers:** New issue discovered, issue resolved, ETA changed
**Feedback:** #support-docs-feedback Slack channel
