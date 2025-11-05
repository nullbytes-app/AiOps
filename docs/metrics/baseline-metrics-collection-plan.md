# Baseline Metrics Collection Plan
## AI Agents - Ticket Enhancement Platform

**Story:** 5.5 - Establish Baseline Metrics and Success Criteria
**Purpose:** Document 7-day baseline measurement methodology to establish platform performance benchmarks, demonstrate ROI, and enable data-driven roadmap prioritization
**Collection Period:** [Start Date] - [End Date] (7 consecutive days, Monday-Sunday recommended)
**Environment:** Production (https://api.ai-agents.production/)
**Tenant ID:** [Primary production tenant UUID from Story 5.3]
**Plan Created:** 2025-11-04
**Plan Version:** 1.0

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Measurement Objectives](#measurement-objectives)
3. [Success Criteria Definitions](#success-criteria-definitions)
4. [Metrics Categories & Data Sources](#metrics-categories--data-sources)
5. [7-Day Collection Methodology](#7-day-collection-methodology)
6. [Data Quality & Validation](#data-quality--validation)
7. [Prometheus Queries Reference](#prometheus-queries-reference)
8. [Client Feedback Collection](#client-feedback-collection)
9. [Daily Health Checks](#daily-health-checks)
10. [Reporting Schedule](#reporting-schedule)
11. [Stakeholder Communication](#stakeholder-communication)
12. [Appendices](#appendices)

---

## Executive Summary

### Purpose of Baseline Measurement

This plan establishes the methodology for collecting 7-day baseline performance metrics for the AI Agents ticket enhancement platform (Epic 5, Story 5.5). The baseline measurement serves three strategic objectives:

1. **Performance Benchmarking:** Establish statistically significant performance baseline to track platform improvement over time
2. **ROI Justification:** Demonstrate measurable business value (time savings, quality improvement, technician satisfaction) to justify platform investment
3. **Roadmap Prioritization:** Identify improvement opportunities based on data-driven analysis of performance gaps and client feedback themes

### Why 7 Days?

**Statistical Significance:** 7-day period provides sufficient sample size for credible stakeholder reporting:
- Assuming 50-100 tickets/day (per NFR003 scalability requirement), 7 days yields 350-700 ticket samples
- Captures weekday vs weekend patterns, ticket volume fluctuations, technician work schedule variations
- Longer than validation testing (Story 5.4: 24-48h) ensures measured performance represents steady-state operations not temporary anomalies

**Industry Best Practice (2025):** SaaS product measurement best practices recommend:
- Baseline periods of 5-10 days for B2B SaaS products to capture business cycle variations
- Minimum 200+ data points for statistically significant performance metrics (latency, success rate)
- Combining quantitative metrics with qualitative feedback (surveys, ratings) for holistic understanding

### Measurement Scope

**Performance Metrics (Quantitative):**
- Latency: p50/p95/p99 percentile distribution over 7 days
- Success Rate: Enhancement success rate % (target >95%)
- Throughput: Tickets processed per day (scalability assessment)
- Queue Health: Redis queue depth, worker utilization, processing time
- Resource Consumption: CPU, memory, database performance

**Business Impact Metrics (Quantitative + Qualitative):**
- Resolution Time Reduction: Before/after enhancement (measured via surveys or client data export)
- Ticket Quality Improvement: Subjective quality score from technician feedback
- Technician Satisfaction: Average rating (1-5 Likert scale) from surveys
- Enhancement Utilization: % of tickets receiving enhancements

**Client Feedback (Qualitative):**
- 5-point Likert scale surveys: Relevance, accuracy, usefulness, overall quality
- Structured interviews: 3+ technicians (15-20 min phone/video)
- Open feedback themes: Categorize improvement requests, pain points, positive feedback

### Stakeholder Alignment

**Success Criteria Socialization (Task 2.4):**
- Before starting 7-day collection period, socialize success criteria definitions with stakeholders
- Required approvals: Product Manager (business impact criteria), Operations Lead (performance criteria), Engineering Lead (technical feasibility)
- Alignment meeting scheduled: [Date/Time] with attendees [names]

---

## Measurement Objectives

### Primary Objectives

**1. Establish Performance Baseline**
- Document current platform performance against NFR001 targets (p95 latency <60s, success rate >95%)
- Identify performance gaps and improvement opportunities
- Validate production readiness for scaled client onboarding (Epic 5 milestone)

**2. Demonstrate ROI to Stakeholders**
- Calculate time savings per ticket (technician research time reduction)
- Project cost savings (time saved × hourly rate × ticket volume)
- Measure technician satisfaction improvement (NPS/CSAT proxy)
- Quantify ticket quality improvement (faster resolution, fewer escalations)

**3. Prioritize Improvement Roadmap**
- Analyze baseline metrics to identify underperforming areas (latency bottlenecks, low satisfaction scores)
- Synthesize client feedback themes to understand improvement priorities
- Rank potential features/optimizations by impact on success criteria and client feedback frequency

### Secondary Objectives

**4. Establish Weekly Review Cadence**
- Document weekly metrics review process (Task 4.1) with agenda template, attendees, decision framework
- Conduct first dry-run review during baseline period (Day 5-6) to test process
- Refine review template based on participant feedback

**5. Validate Monitoring Infrastructure**
- Verify Prometheus metrics collection for 7-day period (no gaps, accurate data)
- Test Grafana dashboard queries with extended time ranges ([7d] vs [24h])
- Identify any infrastructure issues affecting long-term measurement

---

## Success Criteria Definitions

### Quantitative Success Criteria (AC2)

These criteria define "success" for the platform and will be used to measure performance improvement over time:

| **Criterion** | **Target** | **Measurement Method** | **Data Source** | **Rationale** |
|---------------|------------|------------------------|-----------------|---------------|
| **Technician Research Time Reduction** | >20% reduction per ticket | Survey question: "Compared to before AI enhancements, how much time do you save per ticket?" (estimate in minutes) OR client data export comparing pre/post enhancement resolution times | Client feedback surveys OR ServiceDesk Plus API data export | Primary business value metric - time savings directly correlates to cost reduction and technician productivity |
| **Technician Satisfaction Score** | >4/5 average (Likert scale) | Survey question: "Rate overall enhancement quality" (1-5 scale); Calculate average across all survey responses | Client feedback surveys (email + interview) | Customer success metric - high satisfaction indicates value delivery and reduces churn risk |
| **Enhancement Success Rate** | >95% | Prometheus metric: `rate(enhancement_success_rate_total[7d]) * 100` | Prometheus (existing metric from Epic 4) | Reliability metric - low success rate indicates system instability and poor user experience |
| **p95 Latency** | <60 seconds | Prometheus metric: `histogram_quantile(0.95, rate(enhancement_duration_seconds_bucket[7d]))` | Prometheus (existing metric from Epic 4) | Performance metric per NFR001 - ensures acceptable user experience and system responsiveness |

### Business Impact Success Criteria (AC2, Task 2.2)

Additional criteria measuring business value beyond technical performance:

| **Criterion** | **Target** | **Measurement Method** | **Data Source** | **Rationale** |
|---------------|------------|------------------------|-----------------|---------------|
| **ROI (Time Savings)** | Measurable positive ROI | Calculate: (Research time reduction × tickets/day × technician hourly rate × 7 days) - platform operating cost for 7 days | Survey data + cost analysis | Justifies platform investment - positive ROI demonstrates financial viability |
| **Client Retention Improvement** | Baseline documented, target TBD | Track client renewal likelihood, churn risk indicators (satisfaction scores, usage frequency) | Client satisfaction surveys, usage analytics | SaaS best practice: 5% retention increase = 25% revenue increase (2025 research) |
| **Ticket Quality Improvement** | Qualitative improvement documented | Survey question: "Has enhancement quality improved ticket resolution?" (Yes/No/Unsure) + open feedback | Client feedback surveys | Quality metric - improved resolution quality reduces rework and escalations |

### Success Criteria Rationale (AC2, Task 2.3)

**Why These Criteria?**

1. **Alignment with PRD Goals:** Success criteria directly map to PRD goals (improve ticket quality, reduce time-per-ticket, demonstrate ROI)
2. **Stakeholder Relevance:** Criteria address concerns of different stakeholders:
   - Executive team: ROI, client retention (business viability)
   - Operations lead: Success rate, latency (operational stability)
   - Product manager: Satisfaction, quality improvement (user value)
3. **Measurability:** All criteria have clear measurement methods with defined data sources
4. **Industry Benchmarks:** Targets align with 2025 SaaS best practices (>95% success rate, >4/5 satisfaction, <60s p95 latency for B2B SaaS products)

**Measurement Methodology:**

- **Quantitative metrics:** Automated collection via Prometheus, no manual intervention required
- **Qualitative feedback:** Structured surveys and interviews following Story 5.4 templates (proven methodology from validation testing)
- **Business impact:** Combination of survey data (time savings estimates) and financial analysis (cost per ticket, ROI calculation)

---

## Metrics Categories & Data Sources

### Performance Metrics (Prometheus)

**Source:** Prometheus server (operational from Epic 4)
**Scrape Interval:** 15 seconds (standard Prometheus configuration)
**Retention:** 30 days (sufficient for 7-day baseline + historical comparison)

| **Metric Name** | **Prometheus Query** | **Description** | **Target** |
|-----------------|----------------------|-----------------|------------|
| **Enhancement Success Rate** | `rate(enhancement_success_rate_total{tenant_id="<uuid>"}[7d]) * 100` | Percentage of enhancements completing successfully (no errors) | >95% |
| **p50 Latency** | `histogram_quantile(0.50, rate(enhancement_duration_seconds_bucket{tenant_id="<uuid>"}[5m]))` | Median request completion time (50th percentile) | <30s |
| **p95 Latency** | `histogram_quantile(0.95, rate(enhancement_duration_seconds_bucket{tenant_id="<uuid>"}[5m]))` | 95th percentile request completion time (NFR001 target) | <60s |
| **p99 Latency** | `histogram_quantile(0.99, rate(enhancement_duration_seconds_bucket{tenant_id="<uuid>"}[5m]))` | 99th percentile request completion time (tail latency) | <90s |
| **Queue Depth** | `queue_depth{queue_name="enhancement_queue"}` | Number of jobs waiting in Redis queue | <10 (healthy) |
| **Worker Utilization** | `worker_active_count{worker_type="celery_enhancement"} / worker_total_count * 100` | Percentage of Celery workers actively processing jobs | <80% (headroom) |
| **Throughput** | `rate(enhancement_requests_total{tenant_id="<uuid>"}[1d]) * 86400` | Tickets processed per day | 50-100/day |

**Note:** All queries use `tenant_id` label for multi-tenant isolation. Replace `<uuid>` with production tenant ID from Story 5.3.

### Business Impact Metrics (Mixed Sources)

**Resolution Time Reduction:**
- **Source:** Client feedback surveys OR ServiceDesk Plus API data export
- **Survey Question:** "Estimate time saved per ticket compared to before AI enhancements (in minutes)"
- **API Data:** Compare average resolution time for tickets with enhancements vs without enhancements (if available in ServiceDesk Plus reporting)
- **Calculation:** `(Avg time before - Avg time after) / Avg time before * 100`

**Ticket Quality Improvement:**
- **Source:** Client feedback surveys (qualitative + quantitative)
- **Survey Question:** "Rate enhancement impact on ticket resolution quality (1-5 scale: 1=No improvement, 5=Significant improvement)"
- **Calculation:** Average rating across all responses

**Technician Satisfaction:**
- **Source:** Client feedback surveys (5-point Likert scale)
- **Survey Questions (Story 5.4 template):**
  1. Relevance: How relevant was the enhancement to the ticket issue? (1-5)
  2. Accuracy: Was the enhancement information accurate? (1-5)
  3. Usefulness: Did the enhancement help resolve the ticket faster? (1-5)
  4. Overall Quality: Rate overall enhancement quality (1-5)
- **Calculation:** Average of all 4 question scores across all survey respondents

### Client Feedback (Qualitative)

**Source:** Email surveys + structured interviews (Story 5.4 templates)
**Target Responses:** 5+ email surveys, 3+ structured interviews
**Collection Period:** During 7-day baseline period (send surveys on Day 1, follow up on Day 4)

**Survey Questions:**
1. **Quantitative (1-5 Likert scale):**
   - Relevance: How relevant was the enhancement to the ticket issue?
   - Accuracy: Was the enhancement information accurate?
   - Usefulness: Did the enhancement help resolve the ticket faster?
   - Overall Quality: Rate overall enhancement quality
   - Time Savings: Estimate time saved per ticket (in minutes)

2. **Qualitative (Open-ended):**
   - What aspects of enhancements are most helpful?
   - What could be improved?
   - Any specific examples of particularly useful or unhelpful enhancements?

**Interview Script:**
- Follow Story 5.4 structured interview template (15-20 min duration)
- Focus on understanding context behind ratings, improvement priorities, pain points
- Document representative quotes for baseline report

---

## 7-Day Collection Methodology

### Collection Timeline

**Recommended Period:** Monday 00:00 UTC - Sunday 23:59 UTC (7 consecutive days)

**Rationale:**
- Captures full business week + weekend patterns
- Monday start aligns with weekly review cadence (Task 4.2)
- 7-day duration provides statistical significance (350-700 ticket sample)

### Pre-Collection Preparation (Day -2 to Day 0)

**Day -2: Stakeholder Alignment (AC2, Task 2.4)**
- Schedule alignment meeting with Product Manager, Operations Lead, Engineering Lead
- Present success criteria definitions (Table in section above)
- Gather feedback on targets, measurement methods, business priorities
- Document approval in baseline report (Appendix: Stakeholder Sign-off)

**Day -1: Infrastructure Validation**
- Verify Prometheus scraping production metrics (no gaps in last 48h)
- Test Grafana dashboards load with 7-day time range ([7d] queries)
- Confirm production tenant ID and validate tenant_id labels in Prometheus
- Prepare survey email templates and interview scripts (Story 5.4 assets)

**Day 0 (Collection Start):**
- Send initial email surveys to 10+ client technicians (target 5+ responses)
- Document collection period start time (UTC timestamp)
- Baseline snapshot: Run all Prometheus queries, screenshot current Grafana dashboards
- Create tracking spreadsheet for daily health checks (Template: Appendix B)

### During Collection (Day 1-7)

**Daily Health Checks (see section below):**
- Morning check (10:00 UTC): Verify Prometheus scraping, no infrastructure outages
- Evening check (22:00 UTC): Review daily metrics summary, document any anomalies

**Mid-Week Activities:**
- **Day 3:** Send survey reminder email to non-respondents
- **Day 4:** Schedule structured interviews with 3+ willing technicians (conduct Days 4-6)
- **Day 5-6:** Conduct first weekly review session dry-run (Task 4.5) to test review template

**Continuous Monitoring:**
- Monitor queue depth for spikes (alert if >50 jobs for >10 minutes)
- Track error rates (alert if success rate drops below 90% for >1 hour)
- Document any infrastructure incidents affecting baseline (e.g., KB timeout, database slowdown)

### Post-Collection (Day 8+)

**Day 8-9: Data Analysis**
- Export Prometheus metrics for 7-day period (CSV export or PromQL queries)
- Aggregate survey responses, calculate average scores
- Synthesize interview notes, identify common feedback themes
- Run statistical analysis (mean, median, standard deviation, trend analysis)

**Day 10-12: Report Creation (AC1, Task 1.6 and AC7, Task 7.1)**
- Create baseline-metrics-7-day-report.md (comprehensive findings report)
- Calculate ROI and business impact metrics (Task 7.2)
- Generate executive presentation slides (Task 7.3)

**Day 13-14: Stakeholder Communication (AC7, Task 7.4)**
- Email baseline report to executive team, operations, engineering, client account managers
- Schedule presentation meeting (30 min) for discussion and Q&A
- Publish report to internal knowledge base (docs/metrics/ directory)

---

## Data Quality & Validation

### Data Quality Checks

**Prometheus Metrics Integrity:**
- **No Gaps:** Verify continuous scraping throughout 7-day period (scrape interval = 15s, max gap = 1 min acceptable)
- **Outlier Detection:** Identify and document anomalous values (e.g., latency spike >300s, queue depth >100 jobs)
- **Tenant Isolation:** Confirm all metrics filtered by correct tenant_id label (prevent cross-tenant pollution)

**Survey Response Quality:**
- **Minimum Sample Size:** Target 5+ email survey responses (minimum 3 acceptable if <5 technicians using platform)
- **Response Rate:** Calculate and document (e.g., "7 responses from 12 surveys sent = 58% response rate")
- **Bias Mitigation:** Ensure survey invitations sent to diverse technician roles (not just heavy users or champions)

### Exclusion Criteria

**Events Requiring Baseline Adjustment:**

Events that significantly impact baseline validity should be documented and may require baseline period adjustment:

| **Event Type** | **Impact Threshold** | **Action** |
|----------------|---------------------|-----------|
| **Infrastructure Outage** | >4 hours downtime OR >10% of collection period | Exclude affected time window from calculations OR restart 7-day period |
| **Deployment/Upgrade** | Major version change with performance impact | Restart 7-day period after deployment OR document as "before upgrade" baseline |
| **Unusual Ticket Volume** | >3x normal daily volume (e.g., mass incident) | Exclude outlier day from throughput calculations, document in report |
| **External System Failure** | Knowledge Base timeout, ServiceDesk Plus API down | Exclude affected enhancements from success rate calculation |

**Documentation Template:**
```
Anomaly Log (Day X):
- Event: [Brief description, e.g., "Knowledge Base API timeout"]
- Duration: [Start time UTC] - [End time UTC]
- Impact: [Affected metrics, e.g., "15% success rate drop for 2 hours"]
- Action: [Excluded from baseline / Included with note / Triggered baseline restart]
- Rationale: [Why this action was taken]
```

---

## Prometheus Queries Reference

### Standard Queries (Reused from Story 5.4)

**Latency Percentiles:**
```promql
# p50 latency (median)
histogram_quantile(0.50, rate(enhancement_duration_seconds_bucket{tenant_id="<uuid>"}[5m]))

# p95 latency (NFR001 target)
histogram_quantile(0.95, rate(enhancement_duration_seconds_bucket{tenant_id="<uuid>"}[5m]))

# p99 latency (tail latency)
histogram_quantile(0.99, rate(enhancement_duration_seconds_bucket{tenant_id="<uuid>"}[5m]))
```

**Success Rate:**
```promql
# Success rate % (7-day average)
rate(enhancement_success_rate_total{tenant_id="<uuid>"}[7d]) * 100
```

**Throughput:**
```promql
# Tickets processed per day
rate(enhancement_requests_total{tenant_id="<uuid>"}[1d]) * 86400
```

**Queue Health:**
```promql
# Current queue depth
queue_depth{queue_name="enhancement_queue"}

# Average queue depth over 7 days
avg_over_time(queue_depth{queue_name="enhancement_queue"}[7d])

# Max queue depth over 7 days (peak load indicator)
max_over_time(queue_depth{queue_name="enhancement_queue"}[7d])
```

**Worker Utilization:**
```promql
# Current worker utilization %
(worker_active_count{worker_type="celery_enhancement"} / worker_total_count) * 100

# Average worker utilization over 7 days
avg_over_time((worker_active_count{worker_type="celery_enhancement"} / worker_total_count)[7d]) * 100
```

### Extended Queries for Business Impact Metrics

**Note:** These queries will be implemented in AC1 Task 1.3 (Add custom business impact metrics to Prometheus)

**Resolution Time (if instrumented in code):**
```promql
# Average resolution time before enhancement (manual baseline from surveys if not instrumented)
avg(resolution_time_before_enhancement{tenant_id="<uuid>"})

# Average resolution time after enhancement
avg(resolution_time_after_enhancement{tenant_id="<uuid>"})

# Resolution time reduction %
((avg(resolution_time_before_enhancement) - avg(resolution_time_after_enhancement)) / avg(resolution_time_before_enhancement)) * 100
```

**Ticket Quality Score (if instrumented via feedback mechanism in AC5):**
```promql
# Average quality rating from in-product feedback (1-5 scale)
avg(enhancement_feedback_rating_value{tenant_id="<uuid>"})

# Feedback sentiment distribution (thumbs up vs down)
count(enhancement_feedback{tenant_id="<uuid>", feedback_type="thumbs_up"}) / count(enhancement_feedback{tenant_id="<uuid>"}) * 100
```

---

## Client Feedback Collection

### Survey Deployment (AC1, Task 1.5)

**Email Survey Template (Story 5.4 asset):**

**Subject:** Help Us Improve AI Ticket Enhancements - Quick Feedback Survey (5 min)

**Body:**
```
Hi [Technician Name],

You've been using the AI Ticket Enhancement system for [X] weeks/months. We'd love your feedback to help us improve the platform and deliver even more value to your team.

This survey takes ~5 minutes and your responses will directly influence our product roadmap.

[Survey Link - Google Forms / SurveyMonkey / TypeForm]

Key Questions:
- How relevant are AI enhancements to your tickets? (1-5 scale)
- How much time do enhancements save you per ticket? (estimate in minutes)
- What could we improve?

Your feedback is invaluable. Thank you for helping us build a better tool!

Best regards,
[Product Team]
```

**Survey Questions:**

1. **Relevance (1-5 Likert scale):** How relevant are AI enhancements to your ticket issues?
   - 1 = Not relevant at all
   - 5 = Extremely relevant

2. **Accuracy (1-5 Likert scale):** How accurate is the information provided in enhancements?
   - 1 = Frequently inaccurate
   - 5 = Consistently accurate

3. **Usefulness (1-5 Likert scale):** Do AI enhancements help you resolve tickets faster?
   - 1 = No help
   - 5 = Significant help

4. **Overall Quality (1-5 Likert scale):** Rate overall AI enhancement quality
   - 1 = Poor quality
   - 5 = Excellent quality

5. **Time Savings (Open-ended):** Estimate time saved per ticket compared to before AI enhancements (in minutes)

6. **Improvement Suggestions (Open-ended):** What aspects of AI enhancements could be improved?

7. **Best Features (Open-ended):** What aspects are most helpful?

8. **Willingness to Interview (Yes/No):** Would you be willing to participate in a 15-20 min phone/video interview for deeper feedback?

### Structured Interview Script (Story 5.4 asset)

**Duration:** 15-20 minutes
**Format:** Phone or video call
**Participants:** 3+ client technicians who volunteered in survey

**Interview Outline:**

**Introduction (2 min):**
- Thank technician for time
- Explain purpose: understand how AI enhancements are working in real-world use
- Confirm consent to record notes (not audio, just written notes)

**Section 1: Current Experience (5 min)**
- Walk me through a recent ticket where AI enhancement was helpful. What made it useful?
- Can you recall a ticket where the enhancement wasn't helpful? What went wrong?
- How has the platform changed your daily workflow?

**Section 2: Quality & Accuracy (5 min)**
- How often do you find the enhancement information accurate? Any patterns in errors?
- Are there specific ticket types or issues where enhancements work particularly well/poorly?
- How do you verify enhancement accuracy before using it?

**Section 3: Improvement Priorities (5 min)**
- If you could change one thing about AI enhancements, what would it be?
- What additional data sources or context would be most valuable?
- Any features missing that would make the platform more useful?

**Closing (3 min)**
- Any other feedback not covered?
- Would you recommend this platform to technicians at other MSPs? Why/why not?
- Thank you + next steps (how feedback will be used)

**Note-Taking Template:**
- Document representative quotes verbatim (for inclusion in baseline report)
- Categorize feedback into themes (accuracy issues, feature requests, workflow impacts)
- Rate sentiment (positive, neutral, negative) for each topic

---

## Daily Health Checks

### Morning Check (10:00 UTC)

**Purpose:** Verify infrastructure health and catch issues early

**Checklist:**

| **Check Item** | **Method** | **Expected Result** | **Action if Fail** |
|----------------|------------|---------------------|-------------------|
| **Prometheus Scraping** | Grafana → System Status Dashboard → Prometheus "Up" status | Green (1 = up) | Check Prometheus pod logs, restart if needed |
| **API Health** | `curl https://api.ai-agents.production/health` | 200 OK, `{"status": "healthy"}` | Check API pod logs, review errors |
| **Queue Depth** | Grafana → Queue Health Dashboard → Current queue depth | <10 jobs | Investigate if >50 jobs (worker bottleneck?) |
| **Success Rate (24h)** | Prometheus query: `rate(enhancement_success_rate_total[24h]) * 100` | >95% | Review error logs, identify failure patterns |
| **Worker Count** | `kubectl get pods -n ai-agents | grep celery` | 3 pods running (per Story 5.2 deployment) | Scale up if demand exceeds capacity |

**Documentation:**
- Log results in Daily Health Check Spreadsheet (Appendix B: Template)
- If any check fails, document in Anomaly Log with timestamp, impact, remediation action

### Evening Check (22:00 UTC)

**Purpose:** Review daily metrics summary and prepare for next day

**Checklist:**

| **Check Item** | **Method** | **Expected Result** | **Action if Fail** |
|----------------|------------|---------------------|-------------------|
| **Daily Throughput** | Prometheus query: `rate(enhancement_requests_total{tenant_id="<uuid>"}[24h]) * 86400` | 50-100 tickets/day | Document if <50 (low usage?) or >200 (unusual spike?) |
| **Daily Success Rate** | Prometheus query: `rate(enhancement_success_rate_total{tenant_id="<uuid>"}[24h]) * 100` | >95% | If <90%, review error logs, identify root cause |
| **Max Latency (24h)** | Grafana → Per-Tenant Metrics Dashboard → p99 latency over 24h | <90s | If >120s, investigate slow tickets (KB timeout? LLM delay?) |
| **Error Rate** | Prometheus query: `rate(enhancement_errors_total[24h])` | <5% of total requests | Review error types, prioritize fixes |
| **Infrastructure Events** | Check Kubernetes events, alert history | No critical alerts | Document any alerts/incidents affecting baseline |

**Daily Summary Note (1-2 sentences):**
- Example: "Day 3: All health checks passed. Throughput = 78 tickets, success rate = 97.2%, p95 latency = 42s. No incidents. Survey responses: 4/12 (33% response rate so far)."

---

## Reporting Schedule

### Baseline Report Timeline (AC7)

| **Day** | **Activity** | **Deliverable** | **Owner** |
|---------|--------------|-----------------|-----------|
| **Day 0-7** | Execute 7-day baseline collection, daily health checks, client feedback surveys | Raw metrics data, survey responses, anomaly logs | Dev Agent (Amelia) |
| **Day 5-6** | Conduct first weekly review session dry-run (Task 4.5) | Weekly review template feedback, refined agenda | Product Manager + Dev Agent |
| **Day 8-9** | Analyze metrics data, aggregate surveys, synthesize interview themes | Data analysis spreadsheets, feedback categorization | Dev Agent |
| **Day 10** | Create baseline-metrics-7-day-report.md (Task 7.1) | Comprehensive findings report (sections 1-11) | Dev Agent |
| **Day 11** | Calculate ROI and business impact metrics (Task 7.2) | ROI analysis section in report | Dev Agent + Product Manager |
| **Day 12** | Create executive presentation (Task 7.3) | 10-15 slide deck summarizing key findings | Dev Agent |
| **Day 13** | Share baseline report with stakeholders (Task 7.4) | Email distribution, presentation meeting scheduled | Product Manager |
| **Day 14** | Publish to knowledge base (Task 7.5) | Report added to docs/metrics/, Confluence page created | Dev Agent |

### Weekly Review Schedule (AC4, Task 4.2)

**Cadence:** Weekly, every Monday 10:00 AM (30 minutes)
**Start Date:** [First Monday after baseline period completion]
**Recurrence:** Ongoing (continuous improvement)

**Required Attendees:**
- Product Manager (meeting owner)
- Operations Lead
- Engineering Lead

**Optional Attendees:**
- Executive Sponsor (quarterly attendance recommended)
- Client Account Manager (monthly attendance recommended)

**Agenda Template (Task 4.1 - weekly-metrics-review-template.md):**
1. Metrics Review (10 min): Review Grafana baseline dashboard, success criteria achievement
2. Trend Analysis (5 min): Compare current week to previous week, identify positive/negative trends
3. Client Feedback Discussion (5 min): Review recent in-product feedback ratings, themes
4. Roadmap Prioritization (5 min): Discuss top 3 improvement opportunities based on metrics + feedback
5. Action Items (5 min): Assign owners and due dates for follow-ups

---

## Stakeholder Communication

### Alignment Meeting (Pre-Collection)

**Purpose:** Socialize success criteria definitions and gather stakeholder buy-in before starting measurement

**Attendees:**
- Product Manager (decision authority on business criteria)
- Operations Lead (decision authority on performance criteria)
- Engineering Lead (decision authority on technical feasibility)
- Dev Agent (presenter, documenter)

**Agenda (30 minutes):**

1. **Introduction (5 min):** Purpose of baseline measurement, 7-day timeline, expected deliverables
2. **Success Criteria Review (15 min):**
   - Present Table from "Success Criteria Definitions" section
   - Discuss each criterion: target value, measurement method, rationale
   - Gather feedback: Are targets reasonable? Any criteria missing? Measurement methods acceptable?
3. **Feedback Collection Plan (5 min):** Review survey questions, interview script, target response rates
4. **Weekly Review Process (3 min):** Introduce weekly review cadence, confirm attendee availability
5. **Q&A and Approval (2 min):** Address questions, document approvals/objections

**Deliverable:** Meeting notes documenting stakeholder sign-off (Appendix in baseline report)

### Stakeholder Report Distribution (Post-Collection)

**Email Template (Task 7.4):**

**Subject:** AI Agents Platform - 7-Day Baseline Metrics Report [Date Range]

**To:** Executive Team, Operations Lead, Engineering Lead, Client Account Managers

**Body:**
```
Team,

I'm pleased to share the 7-day baseline metrics report for the AI Agents ticket enhancement platform (Epic 5, Story 5.5).

**Key Findings:**
- Enhancement Success Rate: [X]% (Target: >95%)
- p95 Latency: [X]s (Target: <60s)
- Technician Satisfaction: [X]/5 (Target: >4/5)
- Estimated Time Savings: [X] hours/week across [N] technicians

**ROI Analysis:**
- Projected annual time savings: [X] hours
- Estimated cost savings: $[X] (time saved × hourly rate)
- Payback period: [X] months

**Improvement Priorities (from client feedback):**
1. [Top requested feature/improvement]
2. [Second priority]
3. [Third priority]

Full report attached: baseline-metrics-7-day-report.md

**Next Steps:**
- Review roadmap prioritization based on findings (Week of [Date])
- Weekly metrics review meetings starting [Date] (recurring Mondays 10am)

Presentation meeting scheduled: [Date/Time] - [Calendar Invite]

Please review the report and come prepared with questions and feedback for the presentation.

Thank you,
[Product Manager Name]
```

---

## Appendices

### Appendix A: Prometheus Metric Definitions

**Metrics Instrumented in Epic 4 (Existing):**

| **Metric Name** | **Type** | **Labels** | **Description** | **Source Code** |
|-----------------|----------|------------|-----------------|-----------------|
| `enhancement_requests_total` | Counter | tenant_id, status | Total enhancement requests received | src/monitoring/metrics.py:45 |
| `enhancement_duration_seconds` | Histogram | tenant_id, status | End-to-end enhancement processing time | src/monitoring/metrics.py:52 |
| `enhancement_success_rate` | Gauge | tenant_id | Current success rate % (0-100) | src/monitoring/metrics.py:60 |
| `queue_depth` | Gauge | queue_name | Current jobs in Redis queue | src/monitoring/metrics.py:68 |
| `worker_active_count` | Gauge | worker_type | Number of active Celery workers | src/monitoring/metrics.py:75 |

**Metrics to Add in AC1 Task 1.3 (New - Business Impact):**

| **Metric Name** | **Type** | **Labels** | **Description** | **Implementation** |
|-----------------|----------|------------|-----------------|-------------------|
| `resolution_time_before_enhancement` | Gauge | tenant_id | Avg ticket resolution time before AI enhancement (minutes) | Calculated from ServiceDesk Plus data OR manual survey baseline |
| `resolution_time_after_enhancement` | Gauge | tenant_id | Avg ticket resolution time after AI enhancement (minutes) | Calculated from ServiceDesk Plus data OR manual survey baseline |
| `feedback_submissions_total` | Counter | tenant_id, feedback_type | Total feedback submissions (AC5 implementation) | src/api/feedback_routes.py (NEW) |
| `feedback_rating_avg` | Gauge | tenant_id | Average 1-5 rating from in-product feedback (AC5 implementation) | src/api/feedback_service.py (NEW) |

### Appendix B: Daily Health Check Spreadsheet Template

**File:** daily-health-check-tracking.csv (Create alongside baseline report)

| **Date** | **Day #** | **Prometheus Up?** | **API Health** | **Queue Depth** | **Success Rate (24h)** | **Throughput (24h)** | **Max p99 Latency** | **Incidents** | **Notes** |
|----------|-----------|-------------------|----------------|-----------------|------------------------|----------------------|---------------------|---------------|-----------|
| 2025-XX-XX | 1 | ✅ Yes | ✅ 200 OK | 3 jobs | 97.2% | 78 tickets | 55s | None | Survey sent to 12 technicians |
| 2025-XX-XX | 2 | ✅ Yes | ✅ 200 OK | 5 jobs | 96.8% | 82 tickets | 62s | None | 2 survey responses received |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

**Instructions:**
- Complete morning check (10:00 UTC) and evening check (22:00 UTC) daily
- Document any anomalies in "Incidents" column with brief description
- If incident occurred, create full Anomaly Log entry (see "Data Quality & Validation" section)

### Appendix C: Stakeholder Sign-Off (Template)

**Baseline Metrics Collection Plan - Stakeholder Approval**

**Meeting Date:** [YYYY-MM-DD]
**Attendees:** [Names and roles]

**Success Criteria Approved:**
- [x] Quantitative Success Criteria (Table: 4 criteria - research time reduction, satisfaction, success rate, latency)
- [x] Business Impact Success Criteria (Table: 3 criteria - ROI, retention, quality)
- [x] Measurement methodology and data sources

**Feedback Collection Plan Approved:**
- [x] Survey questions and deployment strategy
- [x] Interview script and target participant count
- [x] Timeline (send Day 1, follow-up Day 4, interviews Days 4-6)

**Weekly Review Process Approved:**
- [x] Cadence (weekly, Mondays 10am)
- [x] Required attendees (PM, Ops Lead, Eng Lead)
- [x] Agenda template (5 sections, 30 min duration)

**Concerns/Objections:** [None] OR [Document any concerns and resolutions]

**Approvals:**
- Product Manager: [Signature/Email approval] - [Date]
- Operations Lead: [Signature/Email approval] - [Date]
- Engineering Lead: [Signature/Email approval] - [Date]

---

## Version History

| **Version** | **Date** | **Changes** | **Author** |
|-------------|----------|-------------|------------|
| 1.0 | 2025-11-04 | Initial baseline metrics collection plan created for Story 5.5 | Dev Agent (Amelia) |

---

## References

**Story 5.4 Templates:**
- Performance Baseline Metrics Template: docs/testing/performance-baseline-metrics.md
- Client Feedback Survey Template: docs/testing/client-feedback-survey-results.md
- Production Validation Report: docs/operations/production-validation-report.md

**Epic 4 Monitoring Infrastructure:**
- Prometheus Setup: docs/operations/prometheus-setup.md
- Grafana Dashboards: docs/operations/grafana-setup.md
- Metrics Guide: docs/operations/metrics-guide.md

**2025 SaaS Best Practices Research:**
- AWS SaaS Lens Well-Architected Framework: https://docs.aws.amazon.com/wellarchitected/latest/saas-lens/
- SaaS Metrics Best Practices: WebSearch results (2025 benchmarking reports, customer success metrics)

**Product Requirements:**
- NFR001 (Performance): p95 latency <60s, success rate >95% (docs/PRD.md)
- Epic 5 Goals: Production deployment validation, ROI demonstration (docs/epics.md)
