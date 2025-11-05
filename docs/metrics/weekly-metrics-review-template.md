# Weekly Metrics Review Template
## AI Agents - Ticket Enhancement Platform

**Purpose:** Structured agenda for weekly metrics review meetings to track success criteria achievement, identify trends, discuss client feedback, and prioritize roadmap improvements based on data-driven insights.

**Recurrence:** Weekly, every Monday 10:00 AM (30 minutes)
**Location:** [Video conference link / Meeting room]
**Created:** 2025-11-04 (Story 5.5 - AC4)
**Version:** 1.0

---

## Meeting Details

### Required Attendees

- **Product Manager** (meeting owner, decision authority on roadmap priorities)
- **Operations Lead** (performance criteria, SLA compliance, operational issues)
- **Engineering Lead** (technical feasibility, implementation capacity, architecture decisions)

### Optional Attendees

- **Executive Sponsor** (quarterly attendance recommended for strategic alignment)
- **Client Account Manager** (monthly attendance recommended for client feedback context)

### Meeting Preparation

**Before Meeting (Product Manager):**
1. Review Grafana Baseline Metrics Dashboard (7-day trend, current week vs previous week)
2. Export weekly metrics summary from Prometheus (success rate, latency, throughput)
3. Review in-product feedback submissions via GET /api/v1/feedback/stats (average rating, positive %)
4. Identify 1-2 key discussion topics (trends, issues, opportunities)

**Before Meeting (Operations Lead):**
1. Review operational alerts/incidents from past week (Alertmanager history)
2. Prepare any performance concerns or SLA violations for discussion
3. Identify capacity/scaling needs based on queue depth and worker utilization

**Before Meeting (Engineering Lead):**
1. Review engineering backlog and current sprint progress
2. Assess technical feasibility of potential improvement opportunities
3. Prepare resource capacity estimates for prioritized features

---

## Agenda (30 Minutes)

### 1. Metrics Review (10 minutes)

**Owner:** Product Manager

**Objectives:**
- Review success criteria achievement status (AC2 targets from baseline plan)
- Compare current week metrics to previous week (trend analysis)
- Identify positive trends (celebrate wins) and concerning patterns (investigate root causes)

**Discussion Points:**

| **Success Criterion** | **Target** | **Current Value** | **Trend (vs Last Week)** | **Status** |
|-----------------------|------------|-------------------|--------------------------|------------|
| **Technician Satisfaction Score** | >4/5 | [X.X]/5 | ↑/↓/→ [+/-X.X%] | ✅ PASS / ⚠️ MARGINAL / ❌ FAIL |
| **Enhancement Success Rate** | >95% | [X.X]% | ↑/↓/→ [+/-X.X%] | ✅ PASS / ⚠️ MARGINAL / ❌ FAIL |
| **p95 Latency** | <60s | [X]s | ↑/↓/→ [+/-Xs] | ✅ PASS / ⚠️ MARGINAL / ❌ FAIL |
| **Throughput** | 50-100 tickets/day | [X] tickets/day | ↑/↓/→ [+/-X] | ✅ PASS / ⚠️ MARGINAL / ❌ FAIL |

**Questions to Answer:**
- Are we meeting all success criteria targets?
- Which metric improved most this week? (celebrate)
- Which metric declined or is concerning? (investigate)
- Any unusual spikes or anomalies in the data?

**Dashboard Reference:** Grafana → Baseline Metrics & ROI Dashboard → [Screenshot or link]

---

### 2. Trend Analysis (5 minutes)

**Owner:** Product Manager + Operations Lead

**Objectives:**
- Identify week-over-week trends (improving, declining, stable)
- Correlate trends with recent changes (deployments, configuration updates, client behavior)
- Assess if trends are sustainable or require intervention

**Discussion Template:**

**Positive Trends (Celebrate):**
- [Metric name]: Improved by [X]% from [previous value] to [current value]
  - **Likely cause:** [Deployment X, Configuration change Y, Client adoption increase]
  - **Action:** Document success pattern for replication

**Concerning Trends (Investigate):**
- [Metric name]: Declined by [X]% from [previous value] to [current value]
  - **Likely cause:** [Infrastructure issue, External system slowdown, Ticket volume spike]
  - **Action:** [Investigate root cause, Create improvement task, Escalate to engineering]

**Stable Performance (Monitor):**
- [Metrics that are flat week-over-week]
  - **Action:** Continue monitoring, no immediate action required

**Example:**
- **Positive:** Satisfaction score improved from 4.2/5 to 4.5/5 (+7%). Likely cause: Improved KB search relevance from Story 2.6 deployment.
- **Concerning:** p95 latency increased from 42s to 58s (+38%). Likely cause: External KB API timeout spikes. Action: Engineering to investigate timeout handling.

---

### 3. Client Feedback Discussion (5 minutes)

**Owner:** Product Manager + Client Account Manager (if attending)

**Objectives:**
- Review recent in-product feedback (thumbs up/down distribution, rating scores, comments)
- Identify recurring themes from technician feedback (positive patterns, pain points)
- Extract actionable insights for roadmap prioritization

**Discussion Points:**

**Quantitative Feedback Summary:**
- **Total feedback submissions this week:** [N] submissions
- **Thumbs up vs thumbs down:** [N] up ([X]%) / [N] down ([X]%)
- **Average rating (1-5 scale):** [X.X]/5 across [N] rating submissions
- **Positive feedback percentage:** [X]% (target: >80% for healthy satisfaction)

**Qualitative Feedback Themes:**

Extract top 3 themes from feedback_comment field (via manual review or keyword analysis):

1. **Theme 1 - [Brief description]:**
   - Frequency: Mentioned in [N] comments ([X]% of total)
   - Sentiment: Positive / Negative / Mixed
   - Example quotes: "[Representative technician quote]"
   - Action: [Prioritize feature, Fix issue, Document best practice]

2. **Theme 2 - [Brief description]:**
   - [Same structure as above]

3. **Theme 3 - [Brief description]:**
   - [Same structure as above]

**Example:**
- **Theme 1 - IP Address Context Helpful:** Mentioned in 12 comments (40%). Sentiment: Positive. Quote: "IP cross-reference saved me 15 minutes identifying affected systems." Action: Promote this feature in onboarding materials.
- **Theme 2 - KB Search Misses Specific Vendor Docs:** Mentioned in 8 comments (27%). Sentiment: Negative. Quote: "Enhancement doesn't include Cisco-specific commands." Action: Engineering to investigate KB coverage gaps for Cisco equipment.

---

### 4. Roadmap Prioritization (5 minutes)

**Owner:** Product Manager + Engineering Lead

**Objectives:**
- Review improvement opportunity backlog (from baseline findings + ongoing feedback)
- Prioritize top 3 improvements using data-driven framework (impact on success criteria + client feedback frequency + effort estimate)
- Assign ownership and target completion dates for prioritized items

**Prioritization Framework:**

| **Improvement Opportunity** | **Impact on Success Criteria** | **Client Feedback Frequency** | **Effort Estimate** | **Priority Score** |
|----------------------------|-------------------------------|------------------------------|---------------------|-------------------|
| [Feature/Fix name] | High/Med/Low (which criterion?) | [N] mentions ([X]% of feedback) | Story points / T-shirt size | High / Medium / Low |

**Priority Score Calculation:**
- **High Priority:** High impact + High frequency OR High impact + Low effort (quick win)
- **Medium Priority:** Medium impact + Medium/High frequency OR High impact + High effort (strategic bet)
- **Low Priority:** Low impact OR Low frequency OR High effort without justification

**Top 3 Prioritized Improvements:**

1. **[Feature/Fix name]** - Priority: High
   - **Rationale:** Addresses success criterion [X] gap (current [Y], target [Z]), mentioned in [N]% of feedback
   - **Expected Outcome:** Improve [metric] by [X]% based on impact analysis
   - **Owner:** [Engineering Lead / Product Manager]
   - **Target Completion:** [Sprint X / YYYY-MM-DD]

2. **[Feature/Fix name]** - Priority: High/Medium
   - [Same structure as above]

3. **[Feature/Fix name]** - Priority: Medium/Low
   - [Same structure as above]

**Example:**
1. **Add Cisco Command Library to KB Search** - Priority: High
   - Rationale: Addresses satisfaction criterion gap (current 4.3/5, target >4/5), mentioned in 27% of negative feedback
   - Expected Outcome: Improve satisfaction to 4.6/5 by reducing KB search gaps
   - Owner: Engineering Lead
   - Target Completion: Sprint 12 (2025-11-18)

---

### 5. Action Items (5 minutes)

**Owner:** Product Manager (documenter)

**Objectives:**
- Assign specific action items with owners and due dates
- Ensure accountability for follow-ups from discussion
- Schedule escalations or deeper investigations if needed

**Action Item Template:**

| **#** | **Action Item** | **Owner** | **Due Date** | **Status** |
|-------|-----------------|-----------|--------------|------------|
| 1 | Investigate p95 latency spike (42s → 58s) - root cause analysis | Operations Lead | 2025-11-08 | Open |
| 2 | Create story for Cisco KB integration (High priority improvement) | Product Manager | 2025-11-06 | Open |
| 3 | Document IP cross-reference success pattern for client onboarding materials | Client Account Manager | 2025-11-11 | Open |
| 4 | Review Alertmanager configuration for KB timeout alerts | Engineering Lead | 2025-11-09 | Open |

**Escalation Path:**

If critical issues identified during review require executive attention:
- **Severity Definition:**
  - **Critical:** Success rate <90%, p95 latency >120s, major client escalation, security incident
  - **High:** Success criterion failure (e.g., satisfaction <4/5), consistent week-over-week decline (>20%), operational capacity concerns
  - **Medium:** Single metric marginal performance, minor client feedback theme, technical debt accumulation

- **Escalation Process:**
  - **Critical/High issues:** Product Manager escalates to Executive Sponsor within 24 hours via email with summary + proposed action plan
  - **Medium issues:** Document in meeting notes, monitor for 2 weeks, escalate if worsens
  - **Communication Template:** See Appendix B

---

## Post-Meeting Actions

**Product Manager:**
1. Distribute meeting notes to all attendees within 24 hours (use template below)
2. Update action items in project management tool (JIRA/Linear/GitHub Issues)
3. Update roadmap prioritization in product backlog based on discussion
4. Prepare summary slide for executive sponsor (if quarterly attendance cadence)

**Operations Lead:**
1. Investigate assigned action items (root cause analysis, performance issues)
2. Update operational runbooks if new patterns or procedures identified
3. Communicate capacity/scaling needs to engineering if thresholds exceeded

**Engineering Lead:**
1. Create engineering stories for prioritized improvements
2. Assign owners and add to sprint planning backlog
3. Provide technical feasibility assessments for roadmap items

---

## Appendices

### Appendix A: Meeting Notes Template

```markdown
# Weekly Metrics Review - [YYYY-MM-DD]

**Attendees:** [Names]
**Date:** [YYYY-MM-DD]
**Duration:** 30 minutes

## Success Criteria Status
- Satisfaction: [X.X]/5 (target >4/5) - [PASS/FAIL]
- Success Rate: [X.X]% (target >95%) - [PASS/FAIL]
- p95 Latency: [X]s (target <60s) - [PASS/FAIL]
- Throughput: [X] tickets/day (target 50-100) - [PASS/FAIL]

## Key Trends
- **Positive:** [Brief summary]
- **Concerning:** [Brief summary]

## Client Feedback Themes
1. [Theme 1]: [Summary]
2. [Theme 2]: [Summary]
3. [Theme 3]: [Summary]

## Top 3 Prioritized Improvements
1. [Feature/Fix name] - Priority: High - Owner: [Name] - Due: [Date]
2. [Feature/Fix name] - Priority: Medium - Owner: [Name] - Due: [Date]
3. [Feature/Fix name] - Priority: Low - Owner: [Name] - Due: [Date]

## Action Items
| # | Action | Owner | Due Date | Status |
|---|--------|-------|----------|--------|
| 1 | [Action] | [Owner] | [Date] | Open |

## Next Meeting
**Date:** [Next Monday, 10:00 AM]
**Pre-work:** [Any specific preparation needed]
```

### Appendix B: Executive Escalation Email Template

```
Subject: [CRITICAL/HIGH] Weekly Metrics Review - Issue Escalation [YYYY-MM-DD]

[Executive Sponsor Name],

During today's weekly metrics review, we identified a [critical/high severity] issue requiring your awareness and potential strategic intervention.

**Issue Summary:**
[1-2 sentence description of the problem]

**Impact:**
- Success Criterion Affected: [Which criterion: satisfaction, success rate, latency, throughput]
- Current Performance: [X.X] (Target: [Y.Y])
- Trend: [Declining X% week-over-week for N weeks]
- Client Impact: [Number of clients affected, severity of user experience degradation]

**Root Cause (Preliminary Analysis):**
[Brief description of suspected root cause, or "Under investigation - analysis in progress"]

**Proposed Action Plan:**
1. [Immediate action - timeline]
2. [Short-term fix - timeline]
3. [Long-term resolution - timeline]

**Resource Requirements:**
[Any additional budget, headcount, vendor support, or executive decisions needed]

**Next Steps:**
- [Product Manager] will coordinate action plan execution
- [Operations Lead] will provide daily status updates until resolved
- [Engineering Lead] will deliver root cause analysis by [Date]

Please let me know if you need additional context or if this warrants a dedicated escalation meeting.

Best regards,
[Product Manager Name]
```

### Appendix C: Data Sources Reference

**Grafana Dashboards:**
- **Baseline Metrics & ROI Dashboard:** http://localhost:3000/d/baseline-metrics (or production Grafana URL)
- **System Status Dashboard:** [Operational health, queue depth, worker status]
- **Per-Tenant Metrics Dashboard:** [Tenant-specific latency, throughput, errors]

**Prometheus Queries (for manual export if needed):**
```promql
# Success rate (7-day average)
rate(enhancement_success_rate_total{tenant_id="<uuid>"}[7d]) * 100

# p95 latency (current week)
histogram_quantile(0.95, rate(enhancement_duration_seconds_bucket{tenant_id="<uuid>"}[7d]))

# Throughput (tickets/day, current week)
rate(enhancement_requests_total{tenant_id="<uuid>"}[1d]) * 86400

# Average rating (current week)
avg(enhancement_feedback_rating_value{tenant_id="<uuid>"})
```

**Feedback API Endpoints:**
- **GET /api/v1/feedback/stats:** Aggregated statistics (average rating, counts by type, positive %)
- **GET /api/v1/feedback:** Individual feedback records with comments for theme analysis

---

## Version History

| **Version** | **Date** | **Changes** | **Author** |
|-------------|----------|-------------|------------|
| 1.0 | 2025-11-04 | Initial weekly metrics review template created for Story 5.5 (AC4) | Dev Agent (Amelia) |

---

## References

**Story 5.5 Documentation:**
- Baseline Metrics Collection Plan: docs/metrics/baseline-metrics-collection-plan.md
- Success Criteria Definitions: docs/metrics/baseline-metrics-collection-plan.md (Section: Success Criteria Definitions)

**Monitoring Infrastructure:**
- Grafana Setup: docs/operations/grafana-setup.md
- Prometheus Queries: docs/operations/metrics-guide.md
- Alert Runbooks: docs/operations/alert-runbooks.md
