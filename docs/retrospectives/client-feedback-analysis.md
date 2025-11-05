# Client Feedback Analysis and Prioritization
**AI Agents Enhancement Platform - MVP v1.0 Post-Deployment**

**Analysis Date:** 2025-11-04
**Collection Period:** 2025-11-04 to 2025-11-11 (7-day baseline)
**Primary Client:** Acme Corp (MSP, 50 technicians)
**Analyst:** Product Team
**Status:** Framework Established, Awaiting Production Data

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Data Collection Methodology](#data-collection-methodology)
3. [Quantitative Feedback Analysis](#quantitative-feedback-analysis)
4. [Qualitative Feedback Synthesis](#qualitative-feedback-synthesis)
5. [Feature Request Prioritization](#feature-request-prioritization)
6. [Action Items and Next Steps](#action-items-and-next-steps)

---

## Executive Summary

### Context

The AI Agents Enhancement Platform was deployed to production on **2025-11-04** with the first MSP client (Acme Corp) onboarded. This document establishes the framework for collecting, analyzing, and prioritizing client feedback during the 7-day baseline metrics collection period and beyond.

**Key Success Criteria (from Story 5.5):**
- **>20% time reduction** per ticket (vs. manual research baseline)
- **>4/5 average satisfaction** rating from technicians
- **>95% enhancement success rate** (no errors, useful context provided)

### Current Status (2025-11-04)

**Feedback Infrastructure:**
- ✅ `enhancement_feedback` table operational (PostgreSQL with RLS)
- ✅ REST API endpoints deployed (POST /api/v1/feedback, GET /api/v1/feedback)
- ✅ Grafana dashboard "Baseline Metrics & Success Criteria" (9 panels, 686 lines)
- 🔄 **7-day baseline collection in progress** (completion date: 2025-11-11)

**Data Availability:**
- **Quantitative Metrics:** Awaiting 7-day production data (ticket volume, latency, success rate)
- **Qualitative Feedback:** Awaiting technician feedback submissions via API
- **Client Interviews:** Scheduled for 2025-11-12 (post-baseline collection)

### Framework Overview

This document provides:
1. **Data collection methodology** for quantitative and qualitative feedback
2. **Analysis templates** for metrics aggregation and sentiment analysis
3. **Prioritization framework** (RICE scoring) for feature requests
4. **Action plan** for continuous feedback integration

**Next Update:** 2025-11-12 (after 7-day baseline collection completes)

---

## Data Collection Methodology

### 1. **Quantitative Feedback (Automated)**

#### A. **Enhancement Feedback API**

**Data Source:** `enhancement_feedback` table (PostgreSQL)

**Schema:**
```sql
CREATE TABLE enhancement_feedback (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    ticket_id VARCHAR(255) NOT NULL,
    enhancement_id UUID,  -- Foreign key to enhancement_history
    technician_email VARCHAR(255),
    feedback_type VARCHAR(50) NOT NULL,  -- 'thumbs_up', 'thumbs_down', 'rating'
    rating_value INTEGER CHECK (rating_value BETWEEN 1 AND 5),
    feedback_comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- RLS policy: tenant_id isolation
    -- Indexes: (tenant_id), (tenant_id, created_at), (tenant_id, ticket_id)
);
```

**Collection Method:**
- **POST /api/v1/feedback:** Technicians submit feedback after enhancement delivery (in-app prompt)
- **Automatic logging:** System records enhancement success/failure in `enhancement_history` table

**Metrics Tracked:**
| Metric | Calculation | Target |
|--------|-------------|--------|
| **Average Rating** | `AVG(rating_value) WHERE feedback_type='rating'` | >4.0 / 5.0 |
| **Satisfaction Rate** | `COUNT(*) WHERE feedback_type='thumbs_up' / COUNT(*)` | >80% |
| **Sentiment Distribution** | `GROUP BY feedback_type` | Majority positive |
| **Enhancement Success Rate** | `COUNT(*) WHERE status='completed' / COUNT(*)` | >95% |
| **Time Reduction** | `AVG(manual_time - enhanced_time)` | >20% |

#### B. **Production Validation Metrics**

**Data Source:** Grafana dashboard "Baseline Metrics & Success Criteria"

**Metrics:**
1. **Ticket Volume:** Total tickets enhanced per day
2. **Latency (p50, p95, p99):** Enhancement processing time
3. **Success Rate:** Percentage of enhancements without errors
4. **Queue Depth:** Redis queue backlog
5. **LLM Token Usage:** OpenAI token consumption for cost attribution
6. **Cache Hit Ratio:** KB search cache effectiveness
7. **Context Gathering Time:** Parallel execution performance
8. **Technician Engagement:** Feedback submission rate

**Collection Period:** 7 days (2025-11-04 to 2025-11-11)

**Analysis Query (Example):**
```sql
-- Average rating by day
SELECT
    DATE(created_at) as feedback_date,
    AVG(rating_value) as avg_rating,
    COUNT(*) as feedback_count
FROM enhancement_feedback
WHERE tenant_id = 'acme-corp'
  AND feedback_type = 'rating'
  AND created_at >= '2025-11-04'
GROUP BY DATE(created_at)
ORDER BY feedback_date;

-- Sentiment distribution
SELECT
    feedback_type,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) as percentage
FROM enhancement_feedback
WHERE tenant_id = 'acme-corp'
  AND created_at >= '2025-11-04'
GROUP BY feedback_type;
```

### 2. **Qualitative Feedback (Manual)**

#### A. **In-App Feedback Comments**

**Data Source:** `enhancement_feedback.feedback_comment` (text field)

**Collection Trigger:**
- Technician submits thumbs_down or low rating (1-3 stars)
- Optional comment field for all feedback types

**Analysis Method:**
- **Theme extraction:** Manual categorization (UI/UX, accuracy, performance, missing features)
- **Sentiment analysis:** Positive/neutral/negative classification
- **Action item identification:** Extract specific improvement requests

**Example Categories:**
| Theme | Example Comment | Action Item |
|-------|-----------------|-------------|
| **UI/UX** | "Enhancement too long, hard to scan" | Implement collapsible sections, bullet points |
| **Accuracy** | "KB article not relevant to issue" | Improve KB search relevance scoring |
| **Performance** | "Takes too long to get enhancement" | Optimize LangGraph parallel execution |
| **Missing Features** | "Need RCA suggestions, not just context" | Add RCA agent to roadmap (Epic evaluation) |

#### B. **Client Stakeholder Interviews**

**Participants:**
- **Acme Corp Contacts:**
  - IT Director (decision-maker)
  - Support Manager (day-to-day owner)
  - 3-5 Technicians (end users)

**Interview Schedule:**
- **Date:** 2025-11-12 (after 7-day baseline collection)
- **Duration:** 30-45 minutes per interview
- **Format:** Semi-structured (prepared questions + open discussion)

**Interview Questions:**

**For IT Director:**
1. Has the platform met your expectations for ROI (time reduction, ticket quality)?
2. What's working well that we should double down on?
3. What's missing or underperforming that impacts adoption?
4. What features would make this platform indispensable for your team?
5. What concerns do you have about scaling this to more teams/clients?

**For Support Manager:**
1. How has technician adoption been (usage rate, resistance)?
2. What feedback have you heard from technicians (positive, negative)?
3. Have you seen measurable time savings or quality improvements?
4. What operational challenges have you encountered (configuration, troubleshooting)?
5. What features would improve your management/oversight of the system?

**For Technicians:**
1. How often do you use the enhancement feature (always, sometimes, rarely)?
2. What do you find most useful about the enhanced context?
3. What's frustrating or unhelpful about the current implementation?
4. What information is missing that you still have to look up manually?
5. If you could add one feature, what would it be?

**Analysis Method:**
- **Transcript notes:** Capture key quotes and themes
- **Affinity mapping:** Group similar feedback into themes
- **Prioritization:** Rank themes by frequency and impact

#### C. **Support Ticket Analysis**

**Data Source:** Production support tickets (if any) related to platform issues

**Categories:**
- **Bug reports:** Errors, crashes, unexpected behavior
- **Feature requests:** New capabilities, enhancements to existing features
- **Configuration issues:** Tenant setup, secret management, API integration
- **Performance complaints:** Slow responses, timeouts, queue backlogs

**Analysis Query:**
```sql
-- Support tickets by category (hypothetical)
SELECT
    category,
    COUNT(*) as ticket_count,
    AVG(resolution_time_hours) as avg_resolution_hours
FROM support_tickets
WHERE tenant_id = 'acme-corp'
  AND created_at >= '2025-11-04'
GROUP BY category
ORDER BY ticket_count DESC;
```

---

## Quantitative Feedback Analysis

### **NOTE:** This section will be populated with actual data after 7-day baseline collection (2025-11-12).

### Template: Metrics Aggregation

#### 1. **Average Rating Trend**

**Query:**
```sql
SELECT
    DATE(created_at) as feedback_date,
    AVG(rating_value) as avg_rating,
    STDDEV(rating_value) as rating_stddev,
    COUNT(*) as feedback_count
FROM enhancement_feedback
WHERE tenant_id = 'acme-corp'
  AND feedback_type = 'rating'
  AND created_at >= '2025-11-04'
GROUP BY DATE(created_at)
ORDER BY feedback_date;
```

**Expected Output:**
| Date | Avg Rating | StdDev | Feedback Count |
|------|-----------|--------|----------------|
| 2025-11-04 | [TBD] | [TBD] | [TBD] |
| 2025-11-05 | [TBD] | [TBD] | [TBD] |
| ... | ... | ... | ... |
| 2025-11-11 | [TBD] | [TBD] | [TBD] |

**Analysis:**
- **Trend:** Improving/stable/declining?
- **Target:** >4.0 / 5.0
- **Insights:** Low ratings correlated with specific days/times (e.g., high load)?

#### 2. **Sentiment Distribution**

**Query:**
```sql
SELECT
    feedback_type,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) as percentage
FROM enhancement_feedback
WHERE tenant_id = 'acme-corp'
  AND created_at >= '2025-11-04'
GROUP BY feedback_type;
```

**Expected Output:**
| Feedback Type | Count | Percentage |
|--------------|-------|------------|
| thumbs_up | [TBD] | [TBD]% |
| thumbs_down | [TBD] | [TBD]% |
| rating | [TBD] | [TBD]% |

**Analysis:**
- **Target:** >80% positive (thumbs_up)
- **Insights:** High thumbs_down rate? Investigate common themes in comments.

#### 3. **Enhancement Success Rate**

**Query:**
```sql
SELECT
    status,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*) OVER(), 2) as percentage
FROM enhancement_history
WHERE tenant_id = 'acme-corp'
  AND created_at >= '2025-11-04'
GROUP BY status;
```

**Expected Output:**
| Status | Count | Percentage |
|--------|-------|------------|
| completed | [TBD] | [TBD]% |
| failed | [TBD] | [TBD]% |
| pending | [TBD] | [TBD]% |

**Analysis:**
- **Target:** >95% completed
- **Insights:** Failure patterns (specific error types, time of day)?

#### 4. **Time Reduction Measurement**

**Approach:**
- **Baseline (Manual):** Average time spent on manual ticket research (from pre-deployment study)
- **Enhanced (Automated):** Average time spent with AI-generated context
- **Calculation:** `(manual_time - enhanced_time) / manual_time * 100%`

**Data Collection:**
- **Pre-deployment baseline:** Survey technicians for typical research time (5-15 minutes)
- **Post-deployment measurement:** Track time from enhancement delivery to ticket resolution

**Expected Output:**
| Metric | Value |
|--------|-------|
| Baseline Manual Time | [TBD] minutes |
| Enhanced Time | [TBD] minutes |
| Time Reduction | [TBD]% |
| **Target** | **>20%** |

**Note:** Accurate time reduction measurement requires technician self-reporting or screen time tracking integration (future feature).

#### 5. **Engagement Rate**

**Query:**
```sql
-- Feedback submission rate (percentage of enhancements with feedback)
SELECT
    COUNT(DISTINCT ef.enhancement_id) * 1.0 / COUNT(DISTINCT eh.id) * 100 as feedback_rate
FROM enhancement_history eh
LEFT JOIN enhancement_feedback ef ON eh.id = ef.enhancement_id
WHERE eh.tenant_id = 'acme-corp'
  AND eh.created_at >= '2025-11-04';
```

**Expected Output:**
| Metric | Value |
|--------|-------|
| Total Enhancements | [TBD] |
| Enhancements with Feedback | [TBD] |
| Feedback Rate | [TBD]% |

**Analysis:**
- **Target:** >30% feedback rate (industry benchmark for in-app feedback)
- **Insights:** Low feedback rate may indicate friction in submission flow or lack of awareness.

---

## Qualitative Feedback Synthesis

### **NOTE:** This section will be populated with actual data after client interviews (2025-11-12).

### Template: Theme Extraction & Analysis

#### 1. **Feedback Comment Analysis**

**Method:**
1. Export all `feedback_comment` text from database
2. Manually categorize into themes (UI/UX, accuracy, performance, missing features)
3. Count frequency of each theme
4. Extract representative quotes

**Expected Output:**

| Theme | Frequency | Example Quote | Severity |
|-------|-----------|---------------|----------|
| **UI/UX** | [TBD] | [TBD] | [TBD] |
| **Accuracy** | [TBD] | [TBD] | [TBD] |
| **Performance** | [TBD] | [TBD] | [TBD] |
| **Missing Features** | [TBD] | [TBD] | [TBD] |
| **Positive Feedback** | [TBD] | [TBD] | N/A |

#### 2. **Client Interview Synthesis**

**Method:**
1. Conduct interviews (2025-11-12)
2. Transcribe notes and extract key themes
3. Affinity mapping: Group similar feedback
4. Prioritize by impact (blocker, major pain point, nice-to-have)

**Expected Output:**

**Theme: [Theme Name]**
- **Source:** IT Director, Support Manager, Technician A, Technician B
- **Description:** [What is the issue/opportunity?]
- **Representative Quotes:**
  - "[Quote from IT Director]"
  - "[Quote from Technician A]"
- **Impact:** [High/Medium/Low]
- **Action Item:** [What should we do about it?]

**Example Themes (Hypothetical):**

**Theme: Enhancement Accuracy**
- **Source:** Support Manager, 3 Technicians
- **Description:** KB articles sometimes not relevant to ticket topic, technicians still need to search manually
- **Representative Quotes:**
  - "Sometimes the KB articles are generic, not specific to the issue" - Technician A
  - "I've seen enhancements with articles about networking when the ticket is about email" - Technician B
- **Impact:** High (undermines core value proposition)
- **Action Item:** Improve KB search relevance scoring, implement semantic search (vs. keyword matching)

**Theme: Missing RCA Suggestions**
- **Source:** IT Director, Support Manager, 2 Technicians
- **Description:** Technicians want suggested root causes, not just context
- **Representative Quotes:**
  - "The context is great, but I still have to figure out the root cause myself" - Technician C
  - "If the system could suggest 3 possible root causes, that would be a game-changer" - IT Director
- **Impact:** High (future differentiation opportunity)
- **Action Item:** Add RCA agent to roadmap (Epic evaluation in Task 4)

#### 3. **Common Patterns Across Feedback Sources**

**Method:**
- Cross-reference quantitative metrics (low ratings) with qualitative comments (specific complaints)
- Identify patterns: Do low-rated enhancements have common characteristics (e.g., ticket type, time of day, KB search failures)?

**Expected Analysis:**

**Pattern: Low Ratings Correlated with KB Search Timeouts**
- **Data:** 40% of thumbs_down feedback occurred when KB search timed out (10s limit)
- **Insight:** Technicians perceive enhancement as incomplete without KB articles
- **Action Item:** Increase KB search timeout to 15s OR implement fallback KB search (cached results)

---

## Feature Request Prioritization

### Prioritization Framework: RICE Scoring

**RICE Components (from 2025 research):**
1. **Reach:** Number of users affected per quarter (e.g., 50 technicians × 3 months = 150 user-months)
2. **Impact:** Contribution to goals (0.25 = minimal, 0.5 = low, 1 = medium, 2 = high, 3 = massive)
3. **Confidence:** Reliability of estimates (50% = low, 80% = medium, 100% = high)
4. **Effort:** Person-months required (denominator in RICE score)

**RICE Formula:**
```
RICE Score = (Reach × Impact × Confidence) / Effort
```

**Interpretation:**
- **High Priority:** RICE score >50
- **Medium Priority:** RICE score 20-50
- **Low Priority:** RICE score <20

### Top 5 Feature Requests (Hypothetical - Awaiting Feedback)

**NOTE:** These are PLACEHOLDER feature requests based on common SaaS feedback patterns. Will be replaced with actual client requests after interviews.

#### 1. **Collapsible Enhancement Sections**

**Description:** Allow technicians to collapse/expand sections (ticket history, KB articles, IP info) to reduce scrolling

**RICE Scoring:**
- **Reach:** 50 technicians × 4 tickets/day × 90 days = 18,000 interactions/quarter
- **Impact:** 0.5 (low impact - minor UX improvement)
- **Confidence:** 100% (straightforward UI change)
- **Effort:** 0.25 person-months (1 week of development)

**RICE Score:** (18,000 × 0.5 × 1.0) / 0.25 = **36,000**

**Priority:** High (easy win, high reach)

**Rationale:** Low effort, high reach, immediate UX improvement

#### 2. **RCA Suggestions**

**Description:** Generate 3-5 suggested root causes based on ticket context (new AI agent)

**RICE Scoring:**
- **Reach:** 50 technicians × 4 tickets/day × 90 days = 18,000 tickets/quarter
- **Impact:** 2 (high impact - core value proposition enhancement)
- **Confidence:** 70% (moderate confidence - new AI capability, untested)
- **Effort:** 2 person-months (Epic 8: RCA Agent)

**RICE Score:** (18,000 × 2 × 0.7) / 2 = **12,600**

**Priority:** High (high impact, aligns with product vision)

**Rationale:** High impact on technician productivity, but significant development effort (2 person-months)

#### 3. **Triage Automation (Priority + Assignment)**

**Description:** Automatically assign priority and suggested owner based on ticket context

**RICE Scoring:**
- **Reach:** 50 technicians × 4 tickets/day × 90 days = 18,000 tickets/quarter
- **Impact:** 2 (high impact - reduces manual triage time)
- **Confidence:** 60% (low confidence - complex business logic, requires training data)
- **Effort:** 2.5 person-months (Epic 9: Triage Agent)

**RICE Score:** (18,000 × 2 × 0.6) / 2.5 = **8,640**

**Priority:** Medium (high impact, but lower confidence and higher effort than RCA)

**Rationale:** High potential value, but requires significant training data and validation

#### 4. **Custom Tenant Prompts**

**Description:** Allow each tenant to customize LLM synthesis prompts (tone, length, sections)

**RICE Scoring:**
- **Reach:** 1 tenant now, 10 tenants by end of Q1 2026 = 10 tenants
- **Impact:** 1 (medium impact - differentiation, not core functionality)
- **Confidence:** 90% (high confidence - extends existing prompt system)
- **Effort:** 1 person-month (Epic 6 enhancement)

**RICE Score:** (10 × 1 × 0.9) / 1 = **9**

**Priority:** Low (low reach initially, medium impact)

**Rationale:** Important for enterprise sales, but limited reach until multi-tenant adoption scales

#### 5. **Advanced Monitoring (Uptrace Integration)**

**Description:** Replace Jaeger with Uptrace for unified metrics + traces + logs

**RICE Scoring:**
- **Reach:** 5 DevOps/SRE team members (internal users)
- **Impact:** 1 (medium impact - operational efficiency, not end-user facing)
- **Confidence:** 80% (medium confidence - vendor migration risk)
- **Effort:** 1.5 person-months (Epic 4 enhancement)

**RICE Score:** (5 × 1 × 0.8) / 1.5 = **2.67**

**Priority:** Low (low reach, internal-facing)

**Rationale:** Operational improvement, but doesn't directly impact end-user value

### Prioritization Summary Table

| # | Feature Request | RICE Score | Priority | Effort (PM) | Epic |
|---|-----------------|-----------|----------|-------------|------|
| 1 | Collapsible Enhancement Sections | 36,000 | High | 0.25 | 6 (Admin UI) |
| 2 | RCA Suggestions | 12,600 | High | 2.0 | 8 (New) |
| 3 | Triage Automation | 8,640 | Medium | 2.5 | 9 (New) |
| 4 | Custom Tenant Prompts | 9 | Low | 1.0 | 6 (Enhancement) |
| 5 | Advanced Monitoring (Uptrace) | 2.67 | Low | 1.5 | 4 (Enhancement) |

### Backlog Items Creation

**High Priority (Implement Next):**
1. **Backlog Item #1:** Collapsible enhancement sections (Epic 6, Story 6.4)
2. **Backlog Item #2:** RCA agent MVP (Epic 8, New)

**Medium Priority (Roadmap Q1 2026):**
3. **Backlog Item #3:** Triage agent MVP (Epic 9, New)

**Low Priority (Roadmap Q2 2026):**
4. **Backlog Item #4:** Custom tenant prompts (Epic 6, Enhancement)
5. **Backlog Item #5:** Uptrace integration (Epic 4, Enhancement)

---

## Action Items and Next Steps

### Immediate Actions (Week of 2025-11-04)

| # | Action Item | Owner | Deadline | Status |
|---|-------------|-------|----------|--------|
| 1 | Monitor 7-day baseline metrics collection | DevOps Lead | 2025-11-11 | 🔄 In Progress |
| 2 | Schedule client stakeholder interviews | Product Manager | 2025-11-08 | ⏳ Pending |
| 3 | Export feedback comments from database | Data Analyst | 2025-11-12 | ⏳ Pending |
| 4 | Prepare interview questions and scripts | Product Manager | 2025-11-08 | ⏳ Pending |
| 5 | Create feedback analysis dashboard (Grafana) | DevOps Lead | 2025-11-08 | ⏳ Pending |

### Post-Baseline Actions (Week of 2025-11-11)

| # | Action Item | Owner | Deadline | Status |
|---|-------------|-------|----------|--------|
| 6 | Analyze quantitative metrics (ratings, sentiment) | Data Analyst | 2025-11-12 | ⏳ Pending |
| 7 | Conduct client stakeholder interviews | Product Manager | 2025-11-12 | ⏳ Pending |
| 8 | Synthesize qualitative feedback themes | Product Team | 2025-11-13 | ⏳ Pending |
| 9 | Apply RICE scoring to feature requests | Product Manager | 2025-11-14 | ⏳ Pending |
| 10 | Create backlog items for top 5 features | Scrum Master | 2025-11-15 | ⏳ Pending |
| 11 | Update this document with actual data | Product Manager | 2025-11-15 | ⏳ Pending |
| 12 | Present findings to stakeholders | Product Manager | 2025-11-18 | ⏳ Pending |

### Continuous Actions (Ongoing)

| # | Action Item | Frequency | Owner |
|---|-------------|-----------|-------|
| 13 | Monitor feedback API submissions | Daily | DevOps Lead |
| 14 | Review low-rating feedback comments | Weekly | Product Manager |
| 15 | Update RICE scores based on new data | Monthly | Product Manager |
| 16 | Conduct quarterly client surveys | Quarterly | Product Team |
| 17 | Update roadmap based on feedback trends | Quarterly | Product Manager |

---

## Appendix: Data Collection Tools & Queries

### A. **Feedback Export Query (for Manual Analysis)**

```sql
-- Export all feedback with enhancement details
SELECT
    ef.id as feedback_id,
    ef.ticket_id,
    ef.feedback_type,
    ef.rating_value,
    ef.feedback_comment,
    ef.created_at as feedback_date,
    eh.status as enhancement_status,
    eh.context_summary as enhancement_context,
    eh.created_at as enhancement_date
FROM enhancement_feedback ef
LEFT JOIN enhancement_history eh ON ef.enhancement_id = eh.id
WHERE ef.tenant_id = 'acme-corp'
  AND ef.created_at >= '2025-11-04'
ORDER BY ef.created_at DESC;
```

### B. **Grafana Dashboard Panel (Average Rating Over Time)**

```json
{
  "title": "Average Technician Rating (7-Day Trend)",
  "targets": [
    {
      "rawSql": "SELECT DATE_TRUNC('day', created_at) as time, AVG(rating_value) as avg_rating FROM enhancement_feedback WHERE tenant_id = 'acme-corp' AND feedback_type = 'rating' AND created_at >= NOW() - INTERVAL '7 days' GROUP BY time ORDER BY time",
      "format": "time_series"
    }
  ],
  "yaxes": [
    {
      "min": 0,
      "max": 5,
      "label": "Rating (1-5)"
    }
  ],
  "alert": {
    "conditions": [
      {
        "evaluator": {
          "type": "lt",
          "params": [4.0]
        },
        "query": {
          "model": "avg_rating"
        }
      }
    ],
    "message": "Average rating below 4.0 threshold!"
  }
}
```

### C. **Python Script: Sentiment Analysis (NLP-based)**

```python
from textblob import TextBlob
import pandas as pd
from sqlalchemy import create_engine

# Connect to database
engine = create_engine('postgresql://...')
query = "SELECT feedback_comment FROM enhancement_feedback WHERE feedback_comment IS NOT NULL"
df = pd.read_sql(query, engine)

# Sentiment analysis
def analyze_sentiment(text):
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity  # -1 (negative) to 1 (positive)
    if polarity > 0.1:
        return 'positive'
    elif polarity < -0.1:
        return 'negative'
    else:
        return 'neutral'

df['sentiment'] = df['feedback_comment'].apply(analyze_sentiment)

# Summary
print(df['sentiment'].value_counts())
```

---

## Document Control

- **Version:** 1.0
- **Created:** 2025-11-04
- **Last Updated:** 2025-11-04
- **Next Update:** 2025-11-15 (post-baseline collection and interviews)
- **Status:** Framework Established, Awaiting Production Data
- **Related Documents:**
  - Epic 5 Retrospective: `docs/retrospectives/epic-5-retrospective.md`
  - Technical Debt Register: `docs/retrospectives/technical-debt-register.md`
  - Epic Evaluation Matrix: `docs/retrospectives/epic-evaluation-matrix.md`
  - 3-6 Month Roadmap: `docs/retrospectives/roadmap-2025-q4-2026-q1.md`
  - Baseline Metrics Dashboard: `k8s/grafana-dashboard-baseline-metrics.yaml`
  - Story 5.5 (Baseline Metrics): `docs/stories/5-5-establish-baseline-metrics-and-success-criteria.md`
