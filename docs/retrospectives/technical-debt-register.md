# Technical Debt Register
**AI Agents Enhancement Platform - Post-MVP v1.0**

**Registry Owner:** Tech Lead
**Last Updated:** 2025-11-04
**Review Frequency:** Monthly (mid-epic checkpoints + retrospectives)
**Resource Allocation Target:** 20-30% of sprint capacity (per 2025 best practices)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Debt Categorization Framework](#debt-categorization-framework)
3. [High-Priority Debt (Blocks New Features)](#high-priority-debt-blocks-new-features)
4. [Medium-Priority Debt (Limits Scalability)](#medium-priority-debt-limits-scalability)
5. [Low-Priority Debt (Nice-to-Have)](#low-priority-debt-nice-to-have)
6. [Debt Paydown Roadmap](#debt-paydown-roadmap)
7. [Preventive Measures](#preventive-measures)

---

## Executive Summary

### Context

Technical debt is the implied cost of future rework caused by choosing expedient solutions today. The AI Agents Enhancement Platform MVP was delivered in 4 weeks with intentional shortcuts to meet time-to-market goals. This register tracks accumulated technical debt across 5 epics (42 stories) and prioritizes paydown work.

**2025 Best Practice (from research):** Dedicate **15-20% of each sprint to technical debt reduction**, with flexibility to increase during dedicated debt sprints.

### Total Debt Identified

| Category | High Priority | Medium Priority | Low Priority | Total |
|----------|--------------|-----------------|--------------|-------|
| **Code Quality** | 3 | 5 | 4 | 12 |
| **Architecture** | 2 | 4 | 3 | 9 |
| **Performance** | 1 | 6 | 2 | 9 |
| **Security** | 2 | 3 | 1 | 6 |
| **Testing** | 2 | 4 | 3 | 9 |
| **Documentation** | 0 | 2 | 3 | 5 |
| **TOTAL** | **10** | **24** | **16** | **50** |

### Resource Allocation Recommendation

**Sprint Capacity:** Assuming 2-week sprints with 5 developers = 50 person-days total capacity

**Recommended Allocation:**
- **70% Feature Development:** 35 person-days (new features, enhancements)
- **20% Technical Debt:** 10 person-days (~2 high-priority items/sprint)
- **10% Maintenance:** 5 person-days (bug fixes, operations)

**Paydown Timeline:**
- **High-Priority Debt (10 items):** 5 sprints (~10 weeks) at 2 items/sprint
- **Medium-Priority Debt (24 items):** 12 sprints (~24 weeks) at 2 items/sprint
- **Low-Priority Debt (16 items):** Opportunistic (20% of sprints)

**Total Estimated Paydown:** 12-18 months for all debt (assuming consistent 20% allocation)

### Key Insights

**Strategic Debt (Acceptable):**
- MVP shortcuts to meet time-to-market (e.g., delayed Kubernetes Secrets Manager, manual baseline collection)
- These were INTENTIONAL decisions with documented paydown plans

**Reckless Debt (Problematic):**
- None identified - all debt is documented with context and rationale

**Source of Debt:**
- **Epic 1 (Infrastructure):** Incomplete secret management, connection pooling gaps
- **Epic 2 (Core Agent):** Integration test infrastructure, LLM cost optimization
- **Epic 3 (Security):** Secret rotation, audit log retention policies
- **Epic 4 (Monitoring):** Custom span enhancements, trace sampling, alert threshold tuning
- **Epic 5 (Production):** Known issues (network troubleshooting, HPA scaling lag)

---

## Debt Categorization Framework

### Impact Levels

| Level | Definition | Examples |
|-------|------------|----------|
| **High** | **Blocks new features** or causes production incidents | Missing Secrets Manager, broken integration tests, HPA scaling lag |
| **Medium** | **Limits scalability** or increases operational overhead | Connection pooling, manual secret rotation, cache hit ratio analysis |
| **Low** | **Nice-to-have** improvements, minor technical improvements | Code style inconsistencies, missing inline comments, documentation gaps |

### Effort Estimation

| Effort | Person-Days | Examples |
|--------|-------------|----------|
| **XS** | 0.5-1 days | Configuration changes, documentation updates |
| **S** | 2-3 days | Simple feature additions, test coverage improvements |
| **M** | 5-7 days | Component refactoring, integration with external services |
| **L** | 10-15 days | Architecture changes, new service implementations |
| **XL** | 20+ days | Major refactoring, system-wide changes |

### ROI Calculation

**Formula:** `ROI = (Impact Score × Frequency) / Effort`

- **Impact Score:** High=10, Medium=5, Low=1
- **Frequency:** Daily=30, Weekly=4, Monthly=1, Rarely=0.25
- **Effort:** XS=1, S=2, M=5, L=10, XL=20

**Interpretation:**
- **ROI >10:** Immediate priority (quick win or critical blocker)
- **ROI 5-10:** High priority (significant value for effort)
- **ROI 1-5:** Medium priority (balanced trade-off)
- **ROI <1:** Low priority (defer until capacity available)

---

## High-Priority Debt (Blocks New Features)

### HD-001: Kubernetes Secrets Management (External Store)

**Category:** Security
**Epic:** 1 (Infrastructure)
**Impact:** High (blocks production multi-tenant scaling)
**Effort:** M (5-7 days)
**ROI:** (10 × 4) / 5 = **8.0** (High Priority)

**Description:**
Current implementation uses Kubernetes native Secrets for tenant API keys and OpenAI tokens. This has limitations:
- No automatic secret rotation
- Manual secret updates via kubectl (operational overhead)
- No audit trail for secret access
- Difficult to integrate with external identity providers (e.g., AWS IAM, Azure AD)

**Root Cause:**
MVP shortcut to meet time-to-market (Story 3.3). External secret store (Vault, AWS Secrets Manager) deferred to post-MVP.

**Impact on New Features:**
- **Blocks:** Epic 7 (Plugin Architecture) requires per-tenant API keys for multiple tools (Jira, ServiceNow, Zendesk)
- **Limits:** Multi-tenant scaling (manual secret provisioning doesn't scale)

**Proposed Solution:**
1. Integrate **AWS Secrets Manager** or **HashiCorp Vault** (depending on cloud provider)
2. Use **External Secrets Operator** (Kubernetes controller) to sync secrets from external store
3. Implement automatic secret rotation (30-90 day policy)
4. Add audit logging for secret access (CloudTrail or Vault audit logs)

**Acceptance Criteria:**
- All tenant secrets stored in external secret store
- Kubernetes Secrets automatically synced via External Secrets Operator
- Secret rotation policy implemented (30-day default, configurable per tenant)
- Audit logs available for secret access/rotation events

**Estimated Effort:** 5-7 person-days
**Priority:** 1 (Must-do before Epic 6)
**Assigned To:** DevOps Lead
**Target Sprint:** Epic 6, Sprint 1

---

### HD-002: Integration Test Infrastructure (Testcontainers)

**Category:** Testing
**Epic:** 2 (Core Agent)
**Impact:** High (blocks confident refactoring, slows development)
**Effort:** M (5-7 days)
**ROI:** (10 × 30) / 5 = **60.0** (Immediate Priority)

**Description:**
Integration tests currently require local Docker Compose running (PostgreSQL, Redis, Celery broker). Tests are skipped when Docker not available, leading to:
- Inconsistent test execution across team members
- CI/CD pipeline failures when Docker service unavailable
- Low confidence in integration test coverage

**Root Cause:**
Integration test infrastructure not established in Epic 1. Deferred to Epic 2, but never fully automated.

**Impact on New Features:**
- **Blocks:** Confident refactoring (fear of breaking integrations)
- **Slows:** Development velocity (manual Docker Compose setup, flaky tests)

**Proposed Solution:**
1. Integrate **testcontainers** Python library
2. Update `conftest.py` with testcontainer fixtures:
   - PostgreSQL container with test schema
   - Redis container for queue/cache
   - Celery worker container (if needed)
3. Remove all `pytest.skipif` for missing Docker
4. Ensure tests run in CI/CD without manual setup

**Acceptance Criteria:**
- All integration tests pass in CI/CD pipeline (no skipped tests)
- Local test execution requires zero manual Docker setup
- Test execution time <5 minutes for full suite
- Testcontainer fixtures reusable across test modules

**Estimated Effort:** 5-7 person-days
**Priority:** 1 (Must-do before Epic 6)
**Assigned To:** QA Lead
**Target Sprint:** Epic 6, Sprint 1

---

### HD-003: Performance Baseline Gaps (No Early Instrumentation)

**Category:** Performance
**Epic:** 1-3 (Foundation, Core Agent, Security)
**Impact:** High (no quantitative evidence of optimization impact)
**Effort:** S (2-3 days)
**ROI:** (10 × 4) / 2 = **20.0** (Immediate Priority)

**Description:**
Performance baselines not established until Epic 4 (Monitoring). Claims like "50-70% latency reduction" (Story 2.8) based on development testing, not production baseline. No quantitative evidence for:
- Database query latency improvements
- Cache hit ratio optimization
- LangGraph parallel execution speedup

**Root Cause:**
Performance testing deferred to Epic 4. No baseline measurement in Epic 1 (Infrastructure).

**Impact on New Features:**
- **Blocks:** Evidence-based optimization decisions
- **Limits:** ROI justification for performance work

**Proposed Solution:**
1. Create baseline test suite (Story template for Epic 1 pattern):
   - Webhook → Queue latency
   - Database query latency (common queries)
   - Redis cache hit ratio
   - Task processing time (empty task)
2. Run baseline tests after every epic, compare deltas
3. Document results in `docs/metrics/baseline-performance.md`
4. Add Grafana dashboard "Performance Baselines"

**Acceptance Criteria:**
- Baseline metrics documented for Epic 1-5 (retroactive)
- Automated baseline test suite runs on-demand
- Epic retrospectives include performance delta analysis
- Future epics have performance baseline story (Epic 6+)

**Estimated Effort:** 2-3 person-days
**Priority:** 2 (Before Epic 6 Start)
**Assigned To:** DevOps Lead
**Target Sprint:** Epic 5, Sprint 2 (Retrospective)

---

### HD-004: Known Issue #2 - HPA Scaling Lag During Peak Hours

**Category:** Performance
**Epic:** 5 (Production)
**Impact:** High (production service degradation during peak)
**Effort:** S (2-3 days)
**ROI:** (10 × 1) / 2 = **5.0** (High Priority)

**Description:**
Horizontal Pod Autoscaler (HPA) scaling lags during peak hours (8-10 AM, 1-3 PM). Pods take 3-5 minutes to scale up, causing queue backlog and increased latency. Workaround: Pre-warm pods during known peak hours (cron job).

**Root Cause:**
HPA metrics polling interval (30s default) + scale-up stabilization (3 minutes) = slow response to traffic spikes.

**Impact on New Features:**
- **Blocks:** Production SLA compliance (>120s latency during peaks)
- **Limits:** Client satisfaction (enhancement delays)

**Proposed Solution:**
1. Tune HPA thresholds:
   - Reduce target CPU utilization: 70% → 50%
   - Reduce target memory utilization: 80% → 60%
   - Decrease scale-up stabilization: 180s → 60s
2. Implement **KEDA** (Kubernetes Event-Driven Autoscaling) for queue-based scaling:
   - Scale based on Redis queue depth (not just CPU/memory)
   - Faster response to traffic spikes
3. Add predictive scaling based on historical patterns (optional)

**Acceptance Criteria:**
- HPA scales up within 60 seconds of traffic spike
- Queue depth remains <100 during peak hours
- P95 latency <120s during all hours (including peaks)
- Validation testing with simulated peak traffic

**Estimated Effort:** 2-3 person-days
**Priority:** 2 (Fix ETA 2025-11-10 per Story 5.6)
**Assigned To:** DevOps Lead
**Target Sprint:** Epic 5, Sprint 2 (Production Follow-up)

---

### HD-005: Code Quality - Story Context Files Missing (Epic 1)

**Category:** Code Quality
**Epic:** 1 (Infrastructure)
**Impact:** High (ambiguous implementation, increased rework)
**Effort:** S (2-3 days)
**ROI:** (10 × 0.25) / 2 = **1.25** (Medium Priority, but prevents future occurrences)

**Description:**
Epic 1 stories (1.1-1.8) did not have `.context.xml` files, leading to:
- Multiple clarification questions during implementation
- Some rework due to assumptions about patterns
- Inconsistent testing standards across stories

**Root Cause:**
Story Context workflow not yet established in Phase 1 (Foundation).

**Impact on New Features:**
- **Prevents:** Future ambiguity if pattern not established
- **Requires:** Retroactive context file creation for Epic 1 stories (documentation debt)

**Proposed Solution:**
1. Generate context files for Epic 1 stories (1.1-1.8) retroactively
2. Document learnings in `docs/process-improvements.md`
3. Update story creation workflow to mandate context files for ALL stories (no exceptions)

**Acceptance Criteria:**
- 8 context files created for Epic 1 stories
- Story creation workflow updated with context file requirement
- Process improvement documented in retrospective

**Estimated Effort:** 2-3 person-days
**Priority:** 3 (Nice-to-have for documentation completeness)
**Assigned To:** Documentation Lead
**Target Sprint:** Epic 6, Sprint 2 (Backlog)

---

## Medium-Priority Debt (Limits Scalability)

### MD-001: Database Connection Pooling (pgbouncer)

**Category:** Performance
**Epic:** 1 (Infrastructure)
**Impact:** Medium (limits scalability at >100 concurrent requests)
**Effort:** M (5-7 days)
**ROI:** (5 × 0.25) / 5 = **0.25** (Low ROI, but important for scale)

**Description:**
Current implementation uses SQLAlchemy connection pooling (default 5 connections/pod). At scale (100+ pods), this creates 500+ concurrent database connections, which exceeds PostgreSQL recommended limits (200-500 connections).

**Root Cause:**
MVP shortcut - direct database connections acceptable for single-tenant MVP. Connection pooler (pgbouncer) deferred to post-MVP.

**Impact on New Features:**
- **Limits:** Horizontal scaling beyond 50 pods (without database connection exhaustion)
- **Increases:** Database CPU utilization under high load

**Proposed Solution:**
1. Deploy **pgbouncer** as sidecar container in API/Worker pods
2. Configure transaction-level pooling (not session-level)
3. Set max connections per pod: 5 (unchanged), but pooled through pgbouncer
4. Monitor connection usage with Grafana dashboard

**Acceptance Criteria:**
- pgbouncer deployed and configured
- Database connections remain <200 under full load (100 pods)
- No increase in query latency vs. direct connections
- Grafana dashboard "Connection Pool Metrics"

**Estimated Effort:** 5-7 person-days
**Priority:** Medium (defer until >20 pods in production)
**Assigned To:** DevOps Lead
**Target Sprint:** Q2 2026 (after Epic 6-7)

---

### MD-002: LLM Cost Optimization (Context Summarization)

**Category:** Performance (Cost)
**Epic:** 2 (Core Agent)
**Impact:** Medium (limits profitability at scale)
**Effort:** M (5-7 days)
**ROI:** (5 × 30) / 5 = **30.0** (High Priority for cost reduction)

**Description:**
Current implementation sends full context to OpenAI (ticket history, KB articles, IP info). For tickets with 10+ related tickets, this can be 5,000-10,000 tokens, costing $0.15-$0.30 per enhancement (GPT-4o-mini).

**Root Cause:**
MVP prioritized quality (full context) over cost. Context summarization deferred to post-MVP.

**Impact on New Features:**
- **Limits:** Profitability at scale (100 tickets/day = $15-$30/day = $450-$900/month LLM costs)
- **Increases:** Latency (longer LLM synthesis time for large contexts)

**Proposed Solution:**
1. Implement context summarization:
   - Summarize ticket history: Keep most recent 5 tickets, summarize rest (1-2 sentences each)
   - Summarize KB articles: Extract key points (not full text)
2. Compress IP info: Only include unique systems (not duplicate entries)
3. Monitor token usage reduction (target: 30-50% reduction)
4. A/B test: Compare quality (ratings) with/without summarization

**Acceptance Criteria:**
- Token usage reduced by 30-50% (measured in production)
- No decrease in average rating (<4.0 threshold)
- LLM synthesis latency remains <10s
- Cost per enhancement: <$0.10 (down from $0.15-$0.30)

**Estimated Effort:** 5-7 person-days
**Priority:** Medium (defer until >1,000 enhancements/day)
**Assigned To:** AI/ML Engineer
**Target Sprint:** Q1 2026 (after Epic 6)

---

### MD-003: Cache Hit Ratio Analysis (KB Search)

**Category:** Performance
**Epic:** 2 (Core Agent)
**Impact:** Medium (suboptimal cache TTL, increased latency)
**Effort:** S (2-3 days)
**ROI:** (5 × 30) / 2 = **75.0** (High Priority for performance)

**Description:**
KB search cache TTL set to 1 hour (arbitrary choice). No analysis of cache hit ratio or optimal TTL based on production data. Potential issues:
- Too short TTL → Low cache hit ratio, increased external API calls
- Too long TTL → Stale KB articles, inaccurate enhancements

**Root Cause:**
MVP used default TTL without data-driven tuning.

**Impact on New Features:**
- **Limits:** Performance (cache misses increase latency)
- **Increases:** KB API costs (external API calls)

**Proposed Solution:**
1. Add Prometheus metrics: `kb_cache_hit_ratio`, `kb_cache_ttl_effectiveness`
2. Analyze 7-day production data:
   - Cache hit ratio by TTL (test 30min, 1hr, 4hr, 8hr)
   - Cache staleness: How often KB articles change (API versioning)
3. Tune TTL based on data (e.g., 4 hours if hit ratio 80%+ and low staleness)
4. Document findings in `docs/metrics/cache-optimization.md`

**Acceptance Criteria:**
- Cache hit ratio measured in production (Grafana dashboard)
- Optimal TTL determined from 7-day analysis
- TTL updated based on data (not arbitrary)
- Cache hit ratio >70% (industry benchmark)

**Estimated Effort:** 2-3 person-days
**Priority:** Medium (defer until 7-day baseline complete)
**Assigned To:** Backend Engineer
**Target Sprint:** Epic 5, Sprint 3 (Post-Baseline)

---

### MD-004: Secret Rotation Automation

**Category:** Security
**Epic:** 3 (Multi-Tenancy)
**Impact:** Medium (operational overhead, security risk)
**Effort:** M (5-7 days, after HD-001 complete)
**ROI:** (5 × 1) / 5 = **1.0** (Medium Priority)

**Description:**
Tenant API keys and OpenAI tokens currently require manual rotation. No automatic expiration or rotation policy. Security risk if secrets compromised (no automatic invalidation).

**Root Cause:**
MVP shortcut - manual secret management acceptable for single tenant. Automatic rotation requires external secret store (HD-001).

**Impact on New Features:**
- **Blocks:** Compliance requirements (SOC 2, GDPR require regular secret rotation)
- **Increases:** Operational overhead (manual rotation doesn't scale)

**Proposed Solution:**
1. **Prerequisite:** Complete HD-001 (External Secrets Manager)
2. Implement rotation policy:
   - Default: 30-day expiration for all secrets
   - Configurable per tenant (14-90 days)
3. Automatic rotation workflow:
   - Generate new secret in external store
   - Update Kubernetes Secret via External Secrets Operator
   - Notify tenant admin (email) 7 days before expiration
4. Rollback mechanism if new secret fails validation

**Acceptance Criteria:**
- All secrets automatically rotated every 30 days (or tenant-configured period)
- Tenant admins notified 7 days before expiration
- Zero-downtime secret rotation (no service interruption)
- Audit logs for all rotation events

**Estimated Effort:** 5-7 person-days (after HD-001 complete)
**Priority:** Medium (after HD-001)
**Assigned To:** Security Engineer
**Target Sprint:** Epic 6, Sprint 3

---

### MD-005: Audit Log Retention Policy

**Category:** Security
**Epic:** 3 (Multi-Tenancy)
**Impact:** Medium (compliance risk, storage costs)
**Effort:** S (2-3 days)
**ROI:** (5 × 0.25) / 2 = **0.625** (Medium Priority)

**Description:**
`audit_log` table grows indefinitely (no retention policy). Potential issues:
- Database storage costs increase over time
- Compliance risk (GDPR requires data retention limits)
- Query performance degrades (full table scans on large audit logs)

**Root Cause:**
MVP focused on audit logging implementation (Story 3.7), not long-term retention strategy.

**Impact on New Features:**
- **Limits:** Compliance certification (SOC 2, GDPR audits)
- **Increases:** Database storage costs

**Proposed Solution:**
1. Define retention policy:
   - Default: 90 days (configurable per tenant: 30-365 days)
   - Archive old logs to object storage (S3, GCS) for long-term retention (7 years)
2. Implement automatic archival:
   - Daily cron job: SELECT * FROM audit_log WHERE created_at < NOW() - INTERVAL '90 days'
   - Export to Parquet files (compressed), upload to S3
   - DELETE archived rows from PostgreSQL
3. Create read-only view for archived logs (query S3 via Athena or BigQuery)

**Acceptance Criteria:**
- Audit logs archived after 90 days (configurable)
- Archived logs accessible via read-only interface (S3 + Athena)
- Database audit_log table remains <10GB (steady state)
- Archival cron job monitored (Prometheus alert on failures)

**Estimated Effort:** 2-3 person-days
**Priority:** Medium (defer until >1GB audit logs)
**Assigned To:** Backend Engineer
**Target Sprint:** Q1 2026

---

### MD-006: Custom Span Implementation Enhancements

**Category:** Performance (Observability)
**Epic:** 4 (Monitoring)
**Impact:** Medium (limited trace context for troubleshooting)
**Effort:** S (2-3 days)
**ROI:** (5 × 4) / 2 = **10.0** (High Priority for observability)

**Description:**
OpenTelemetry custom spans (Story 4.6, AC12) have minimal contextual attributes. Troubleshooting requires correlating multiple traces manually. Missing attributes:
- Ticket metadata (ticket type, priority, category)
- Context source status (which sources succeeded/failed)
- LLM metadata (model, prompt tokens, completion tokens)
- Business metrics (cost per enhancement, time saved)

**Root Cause:**
MVP focused on basic span creation. Contextual attributes deferred to code review follow-ups (partially addressed).

**Impact on New Features:**
- **Limits:** Root cause analysis efficiency (missing context)
- **Reduces:** Value of distributed tracing investment

**Proposed Solution:**
1. Enhance custom spans with contextual attributes:
   - `ticket.type`, `ticket.priority`, `ticket.category`
   - `context.ticket_history.success`, `context.kb_search.success`, `context.ip_lookup.success`
   - `llm.model`, `llm.prompt_tokens`, `llm.completion_tokens`, `llm.cost`
2. Add business metric spans:
   - `enhancement.time_saved` (manual vs enhanced time)
   - `enhancement.technician_rating`
3. Document attribute standards in `docs/observability/span-attributes.md`

**Acceptance Criteria:**
- All custom spans include recommended contextual attributes
- Trace queries can filter by ticket type, priority, context source status
- Business metrics visible in Jaeger UI (custom attributes)
- Documentation updated with attribute standards

**Estimated Effort:** 2-3 person-days
**Priority:** Medium (after Epic 4)
**Assigned To:** Backend Engineer
**Target Sprint:** Epic 6, Sprint 2

---

### MD-007: Trace Sampling Strategy (Adaptive Sampling)

**Category:** Performance (Observability)
**Epic:** 4 (Monitoring)
**Impact:** Medium (trace overhead at scale, storage costs)
**Effort:** S (2-3 days)
**ROI:** (5 × 1) / 2 = **2.5** (Medium Priority)

**Description:**
Current tracing configuration uses 100% sampling (all requests traced). At scale (1,000+ enhancements/day), this creates:
- High trace storage costs (Jaeger backend)
- Increased overhead (span creation, context propagation)
- Difficult to find relevant traces (signal-to-noise ratio)

**Root Cause:**
MVP used 100% sampling for visibility. Sampling strategy deferred to post-MVP.

**Impact on New Features:**
- **Limits:** Scalability (trace storage costs grow linearly)
- **Increases:** Observability overhead (latency, CPU)

**Proposed Solution:**
1. Implement adaptive sampling strategy:
   - **Always sample:** Errors, slow requests (>120s), low-rated enhancements (<3 stars)
   - **Sample 10%:** Successful requests (random selection)
   - **Sample 1%:** Health checks, monitoring probes
2. Use OpenTelemetry **tail-based sampling** (sample after request completes, not before)
3. Monitor trace coverage with Grafana dashboard

**Acceptance Criteria:**
- Trace sampling configured with adaptive strategy
- 100% of errors and slow requests traced
- 10% of successful requests traced
- Trace storage costs reduced by 80-90%

**Estimated Effort:** 2-3 person-days
**Priority:** Medium (defer until >1,000 enhancements/day)
**Assigned To:** DevOps Lead
**Target Sprint:** Q2 2026

---

### MD-008: Alert Threshold Tuning (Production Baseline)

**Category:** Performance (Observability)
**Epic:** 4 (Monitoring)
**Impact:** Medium (alert fatigue, missed critical alerts)
**Effort:** XS (0.5-1 day)
**ROI:** (5 × 30) / 1 = **150.0** (Immediate Priority)

**Description:**
Prometheus alert thresholds set to arbitrary values (Story 4.4):
- High error rate: >5% (should be >1% based on 99.9% SLA)
- High queue depth: >1000 (should be >500 based on processing capacity)
- High latency: >180s (should be >120s based on NFR001)

**Root Cause:**
MVP used default thresholds without production baseline data.

**Impact on New Features:**
- **Limits:** Incident detection reliability (false positives, false negatives)
- **Increases:** Alert fatigue (too many low-priority alerts)

**Proposed Solution:**
1. Analyze 7-day production baseline data (Story 5.5):
   - Error rate distribution (p50, p95, p99)
   - Queue depth patterns (peak hours vs. off-hours)
   - Latency distribution (p50, p95, p99)
2. Tune alert thresholds based on data:
   - Error rate: p99 + 20% (e.g., if p99 = 0.8%, threshold = 1%)
   - Queue depth: 80% of processing capacity
   - Latency: NFR001 threshold (120s)
3. Document threshold rationale in `docs/observability/alert-thresholds.md`

**Acceptance Criteria:**
- Alert thresholds updated based on 7-day baseline
- Rationale documented for each threshold
- Alert fatigue reduced (false positive rate <10%)
- Critical alerts detected within 5 minutes

**Estimated Effort:** 0.5-1 person-day
**Priority:** High (after 7-day baseline complete)
**Assigned To:** DevOps Lead
**Target Sprint:** Epic 5, Sprint 3 (Post-Baseline)

---

### MD-009: Known Issue #1 - Network Troubleshooting Enhancements Quality

**Category:** Code Quality
**Epic:** 5 (Production)
**Impact:** Medium (affects technician satisfaction for network tickets)
**Effort:** M (5-7 days)
**ROI:** (5 × 4) / 5 = **4.0** (Medium Priority)

**Description:**
Network troubleshooting enhancements sometimes lack actionable next steps. KB articles returned are generic ("check DNS settings") rather than specific to the ticket context. Affects ~20% of network-related tickets.

**Root Cause:**
KB search relevance scoring insufficiently tuned for network domain. LLM prompt lacks network-specific guidelines.

**Impact on New Features:**
- **Limits:** Client satisfaction (technicians still need to research manually)
- **Reduces:** Value proposition for network-heavy MSPs

**Proposed Solution:**
1. Improve KB search relevance for network tickets:
   - Add domain-specific keywords (DNS, routing, firewall, VPN)
   - Boost KB articles tagged "network" or "troubleshooting"
2. Enhance LLM prompt with network-specific guidelines:
   - "For network issues, prioritize diagnostic steps (ping, traceroute, DNS lookup)"
   - "Suggest specific commands to run, not generic advice"
3. A/B test prompt changes with network tickets (measure rating improvement)

**Acceptance Criteria:**
- Network ticket average rating increases from <3.5 to >4.0
- KB search returns network-specific articles (not generic)
- LLM synthesis includes actionable diagnostic commands
- Validation testing with 50+ network tickets

**Estimated Effort:** 5-7 person-days
**Priority:** Medium (Fix ETA 2025-11-15 per Story 5.6)
**Assigned To:** AI/ML Engineer
**Target Sprint:** Epic 5, Sprint 3

---

### MD-010: CI/CD Pipeline - Canary Deployments

**Category:** Architecture
**Epic:** 1 (Infrastructure)
**Impact:** Medium (production deployment risk)
**Effort:** M (5-7 days)
**ROI:** (5 × 0.25) / 5 = **0.25** (Low ROI, but important for production safety)

**Description:**
Current CI/CD pipeline deploys directly to production (no canary or blue-green deployment). Risky for breaking changes:
- All users affected immediately if deployment fails
- No gradual rollout to detect issues early
- Manual rollback required (no automatic rollback on failure)

**Root Cause:**
MVP prioritized simple deployment pipeline. Canary deployments deferred to post-MVP.

**Impact on New Features:**
- **Limits:** Production deployment confidence (fear of breaking changes)
- **Increases:** Incident risk (no gradual rollout)

**Proposed Solution:**
1. Implement canary deployment with **Flagger** (Kubernetes controller):
   - Deploy new version to 10% of pods (canary)
   - Monitor error rate, latency, success rate for 5 minutes
   - Automatically promote (100%) or rollback (0%) based on metrics
2. Add automated rollback on failure (no manual intervention)
3. Document canary deployment workflow in `docs/deployment/canary-workflow.md`

**Acceptance Criteria:**
- Canary deployment configured with Flagger
- New versions deployed to 10% of pods first (5-minute canary period)
- Automatic rollback on failure (error rate >1%, latency >120s)
- Zero-downtime deployments (gradual pod replacement)

**Estimated Effort:** 5-7 person-days
**Priority:** Medium (defer until >10 deployments/month)
**Assigned To:** DevOps Lead
**Target Sprint:** Q2 2026

---

## Low-Priority Debt (Nice-to-Have)

### LD-001: Code Style Inconsistencies (Black, Ruff, Mypy)

**Category:** Code Quality
**Epic:** 1-5 (All)
**Impact:** Low (minor readability issues)
**Effort:** XS (0.5-1 day)
**ROI:** (1 × 30) / 1 = **30.0** (High ROI, easy win)

**Description:**
Some code files have inconsistent formatting (line length >88 characters, missing type hints, unused imports). Not caught by pre-commit hooks due to configuration gaps.

**Root Cause:**
Pre-commit hooks configured but not enforced in all environments (some devs disabled locally).

**Impact on New Features:**
- **Minor:** Code readability, maintenance

**Proposed Solution:**
1. Run Black, Ruff, Mypy on entire codebase: `black . && ruff . --fix && mypy .`
2. Fix all warnings and errors
3. Enforce pre-commit hooks in CI/CD (fail PR if violations)

**Acceptance Criteria:**
- Zero Black/Ruff/Mypy violations
- CI/CD pipeline enforces style checks (fails PR on violations)

**Estimated Effort:** 0.5-1 person-day
**Priority:** Low (opportunistic during refactoring)
**Assigned To:** Development Team
**Target Sprint:** Anytime

---

### LD-002: Missing Inline Comments (Complex Logic)

**Category:** Code Quality
**Epic:** 2 (Core Agent)
**Impact:** Low (minor maintainability)
**Effort:** XS (0.5-1 day)
**ROI:** (1 × 4) / 1 = **4.0** (Medium ROI)

**Description:**
Some complex logic (e.g., LangGraph state reducers, LLM prompt engineering) lacks inline comments explaining "why" (not just "what").

**Root Cause:**
MVP prioritized functionality over code documentation.

**Impact on New Features:**
- **Minor:** Onboarding time for new developers, maintenance

**Proposed Solution:**
1. Add inline comments to complex logic:
   - LangGraph state management (Annotated reducers)
   - LLM prompt engineering (why specific instructions)
   - Error handling logic (graceful degradation rationale)
2. Follow pattern: `# Reason: [why this approach was chosen]`

**Acceptance Criteria:**
- Complex logic has inline comments explaining "why"
- New developers can understand code without asking questions

**Estimated Effort:** 0.5-1 person-day
**Priority:** Low (opportunistic during refactoring)
**Assigned To:** Development Team
**Target Sprint:** Anytime

---

### LD-003: Documentation Gaps (LLM Configuration, Cost Tracking)

**Category:** Documentation
**Epic:** 2 (Core Agent)
**Impact:** Low (minor operational friction)
**Effort:** XS (0.5-1 day)
**ROI:** (1 × 1) / 1 = **1.0** (Medium Priority)

**Description:**
Missing documentation:
- `docs/llm-configuration.md`: How to configure LLM models, prompts, timeouts
- `docs/cost-tracking.md`: How to track LLM token usage, costs, budgets

**Root Cause:**
Documentation deferred to post-MVP (Story 2.9 completion notes).

**Impact on New Features:**
- **Minor:** Onboarding time for operators, troubleshooting

**Proposed Solution:**
1. Create `docs/llm-configuration.md`:
   - Environment variables for LLM configuration
   - Prompt customization instructions
   - Model selection guidelines (GPT-4o vs GPT-4o-mini vs Claude)
2. Create `docs/cost-tracking.md`:
   - Token logging patterns (from Story 2.9)
   - Cost calculation formulas
   - Budget alert configuration

**Acceptance Criteria:**
- Documentation files created
- Operators can configure LLM settings without developer assistance

**Estimated Effort:** 0.5-1 person-day
**Priority:** Low (before Epic 6 Admin UI)
**Assigned To:** Documentation Lead
**Target Sprint:** Epic 6, Sprint 1

---

## Debt Paydown Roadmap

### Sprint Allocation Strategy

**Principle:** Dedicate 20% of each sprint to technical debt reduction (per 2025 best practices).

**Sprint Capacity:** 2-week sprints, 5 developers = 50 person-days total
- **Feature Development:** 70% = 35 person-days
- **Technical Debt:** 20% = 10 person-days
- **Maintenance (Bugs):** 10% = 5 person-days

**Paydown Rate:** ~2 high-priority debt items per sprint (10 person-days effort)

### Epic 6 (Admin UI & Configuration Management) - Sprint 1-3

**Sprint 1 (Weeks 1-2):**
- **HD-001:** Kubernetes Secrets Management (External Store) - 7 person-days - **MUST-DO**
- **HD-002:** Integration Test Infrastructure (Testcontainers) - 5 person-days - **MUST-DO**
- **Total:** 12 person-days (exceeds 20% allocation, justified as blockers for Epic 6)

**Sprint 2 (Weeks 3-4):**
- **MD-008:** Alert Threshold Tuning (Production Baseline) - 1 person-day
- **MD-006:** Custom Span Implementation Enhancements - 3 person-days
- **LD-003:** Documentation Gaps (LLM Configuration, Cost Tracking) - 1 person-day
- **Total:** 5 person-days (below 20% allocation, catch-up from Sprint 1 overrun)

**Sprint 3 (Weeks 5-6):**
- **HD-004:** Known Issue #2 - HPA Scaling Lag During Peak Hours - 3 person-days
- **MD-009:** Known Issue #1 - Network Troubleshooting Quality - 7 person-days
- **Total:** 10 person-days (at 20% allocation target)

### Epic 7 (Plugin Architecture) - Sprint 4-6

**Sprint 4 (Weeks 7-8):**
- **HD-003:** Performance Baseline Gaps (No Early Instrumentation) - 3 person-days
- **MD-003:** Cache Hit Ratio Analysis (KB Search) - 3 person-days
- **LD-001:** Code Style Inconsistencies - 1 person-day
- **Total:** 7 person-days (below target, focus on Epic 7 delivery)

**Sprint 5 (Weeks 9-10):**
- **MD-004:** Secret Rotation Automation - 7 person-days (after HD-001 complete)
- **Total:** 7 person-days

**Sprint 6 (Weeks 11-12):**
- **MD-002:** LLM Cost Optimization (Context Summarization) - 7 person-days
- **LD-002:** Missing Inline Comments (Complex Logic) - 1 person-day
- **Total:** 8 person-days

### Q2 2026 (Post-Epic 7) - Continuous Paydown

**Focus:** Medium and Low Priority debt items

**Estimated Timeline:**
- **MD-001:** Database Connection Pooling (pgbouncer) - Sprint 7
- **MD-005:** Audit Log Retention Policy - Sprint 8
- **MD-007:** Trace Sampling Strategy (Adaptive Sampling) - Sprint 9
- **MD-010:** CI/CD Pipeline - Canary Deployments - Sprint 10
- **HD-005:** Code Quality - Story Context Files Missing (Epic 1) - Sprint 11 (Documentation sprint)

**Total Paydown Timeline:** 12-18 months for all identified debt (assuming consistent 20% allocation)

---

## Preventive Measures

### 1. **Mid-Epic Checkpoints**

**Objective:** Catch technical debt early before it accumulates

**Process:**
- **Checkpoint 1 (After 50% stories):** Review progress, identify emerging debt
- **Checkpoint 2 (After 80% stories):** Retrospective mini-session, prioritize debt items
- **Gate Check (Between epics):** Formal debt assessment before next epic

**Acceptance Criteria:**
- No epic starts with >5 high-priority debt items outstanding
- Debt register updated at every checkpoint

**Owner:** Scrum Master

---

### 2. **Definition of Done Includes Debt Assessment**

**Objective:** Prevent reckless debt (undocumented shortcuts)

**Process:**
- Every story DoD checklist includes: "Technical debt identified and documented?"
- If debt created (intentional shortcut), add to debt register with:
  - Rationale (why shortcut taken)
  - Paydown plan (when will it be addressed)
  - Impact assessment (what's at risk)

**Acceptance Criteria:**
- Zero undocumented technical debt
- All debt items have paydown plans

**Owner:** Tech Lead

---

### 3. **Code Review Focus on Debt Prevention**

**Objective:** Catch architectural shortcuts before merge

**Process:**
- Code review checklist includes:
  - "Does this introduce technical debt?"
  - "Is the debt documented with rationale and paydown plan?"
  - "Are there alternatives with less debt but acceptable trade-offs?"

**Acceptance Criteria:**
- Code reviewers flag undocumented debt
- PRs with new debt require explicit approval (not auto-approved)

**Owner:** Senior Developers

---

### 4. **Automated Debt Detection (SonarQube, CodeClimate)**

**Objective:** Detect code quality debt automatically

**Process:**
- Integrate **SonarQube** or **CodeClimate** into CI/CD pipeline
- Track code quality metrics:
  - Code smells (complexity, duplication)
  - Security vulnerabilities (OWASP Top 10)
  - Test coverage (target: 80%+)
- Alert on regressions (quality score decreases)

**Acceptance Criteria:**
- SonarQube integrated into CI/CD
- Quality gate enforced (PRs fail if quality score decreases)
- Weekly quality report generated

**Owner:** DevOps Lead
**Timeline:** Q1 2026

---

## Document Control

- **Version:** 1.0
- **Created:** 2025-11-04
- **Last Updated:** 2025-11-04
- **Review Frequency:** Monthly (mid-epic checkpoints + retrospectives)
- **Next Review:** 2025-12-01 (Epic 6, Sprint 2)
- **Status:** Final
- **Related Documents:**
  - Epic 5 Retrospective: `docs/retrospectives/epic-5-retrospective.md`
  - Client Feedback Analysis: `docs/retrospectives/client-feedback-analysis.md`
  - Epic Evaluation Matrix: `docs/retrospectives/epic-evaluation-matrix.md`
  - 3-6 Month Roadmap: `docs/retrospectives/roadmap-2025-q4-2026-q1.md`
