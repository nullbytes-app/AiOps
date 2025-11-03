# Runbook Validation Report

**Report Date:** 2025-11-03
**Story:** 4.7 - Create Operational Runbooks and Dashboards
**Status:** Ready for Team Member Testing (Prepared by Amelia, Developer Agent)

---

## 🎯 Instructions for Tester

**You are receiving this document because you have been selected to validate our operational runbooks.** Your role is critical: you will test whether these runbooks are clear and actionable for someone unfamiliar with the system (which is you!).

**Your Background:** You should have minimal prior knowledge of this system. If you find instructions confusing or unclear, **that's valuable feedback** - it means the runbook needs improvement.

**Time Commitment:** ~1-2 hours for complete walkthrough of all 5 runbooks

**Success Criteria:** You can complete the diagnosis and remediation steps in each runbook **without asking for external help** (except clarifications about test environment setup)

**After Testing:** You'll document findings in the matrix below, and we'll use your feedback to improve the runbooks.

---

## Executive Summary

This document will capture the results of runbook validation testing conducted by team members with minimal prior system knowledge. The goal is to ensure all 5 operational runbooks are clear, accurate, and actionable during production incidents.

**Expected Timeline:** 1-2 hours for complete walkthrough of all 5 runbooks
**Success Criteria:** Team member successfully completes diagnosis and remediation procedures for each runbook without external assistance

---

## Runbook Testing Matrix

| Runbook | Test Scenario | Tester Name | Date Tested | Time to Complete | Success (Y/N) | Issues Found |
|---------|---------------|-------------|-------------|------------------|---------------|--------------|
| High Queue Depth | Manually enqueue 75 test jobs, diagnose queue age | TBD | TBD | TBD | TBD | TBD |
| Worker Failures | Kill worker process, analyze crash logs | TBD | TBD | TBD | TBD | TBD |
| Database Connection Issues | Reduce connection pool, diagnose exhaustion | TBD | TBD | TBD | TBD | TBD |
| API Timeout | Mock slow API, test timeout handling | TBD | TBD | TBD | TBD | TBD |
| Tenant Onboarding | Provision new tenant to staging | TBD | TBD | TBD | TBD | TBD |

---

## Test Scenarios and Procedures

### Test 1: High Queue Depth Runbook

**Objective:** Verify team member can diagnose queue depth between 50-100 jobs using runbook

**Setup:**
- Start with clean Redis queue (0 jobs)
- Using test script, enqueue 75 sample enhancement jobs
- Kubernetes: `kubectl exec -it redis-pod -- redis-cli RPUSH enhancement_queue '[job1]' '[job2]' ... '[job75]'`
- Docker Compose: `docker-compose exec redis redis-cli RPUSH enhancement_queue '[job1]' '[job2]' ... '[job75]'`

**Procedure:**
1. Have tester open `docs/runbooks/high-queue-depth.md`
2. Tester executes Diagnosis steps:
   - Check queue depth: `redis-cli LLEN enhancement_queue` (should return 75)
   - Analyze queue age distribution: `redis-cli LINDEX enhancement_queue 0` (oldest) and `-1` (newest)
   - Verify worker capacity: Check Prometheus for `worker_active_count` and `celery_tasks_active_total`
   - Check processing rate: Query `rate(enhancement_requests_total{status="success"}[5m])`
3. Tester executes Resolution steps:
   - If workers available: Scale workers horizontally
   - If specific tenant flooding: Implement per-tenant rate limiting
   - Review distributed tracing in Jaeger for bottleneck identification

**Expected Outcomes:**
- [ ] Tester identifies queue depth = 75 jobs
- [ ] Tester determines queue age distribution (all jobs <10 min old = healthy)
- [ ] Tester determines worker capacity (workers healthy, queue backed up)
- [ ] Tester understands resolution options without external guidance
- [ ] Tester can access Jaeger traces for slow job analysis

**Success Criteria:**
✅ Tester completes diagnosis and interprets results correctly
✅ Tester estimates time to clear queue based on processing rate
⚠️ Issues: [Document any ambiguous instructions or missing commands]

---

### Test 2: Worker Failures Runbook

**Objective:** Verify team member can analyze worker crashes and determine remediation

**Setup:**
- Stop all worker containers/pods
- OR kill one worker process to simulate crash
- Leave error in logs (e.g., Python exception)

**Procedure:**
1. Have tester open `docs/runbooks/worker-failures.md`
2. Tester executes Diagnosis steps:
   - Check worker status
   - Review restart history
   - Analyze crash logs
   - Check resource usage
3. Based on findings, tester executes Resolution:
   - If OOMKilled: Scale memory
   - If exception: Review error
   - If stuck: Restart workers

**Expected Outcomes:**
- [ ] Tester identifies worker status (CrashLoopBackOff or Unhealthy)
- [ ] Tester finds crash logs with error message
- [ ] Tester determines root cause (OOM, Python exception, etc.)
- [ ] Tester executes appropriate remediation

**Success Criteria:**
✅ Tester troubleshoots to root cause and suggests fix
⚠️ Issues: [Document if logs were unclear, commands failed, etc.]

---

### Test 3: Database Connection Issues Runbook

**Objective:** Verify team member can diagnose database connectivity and pool issues

**Setup:**
- Reduce SQLAlchemy connection pool size (e.g., 2 connections instead of 10)
- Run heavy enhancement load to exhaust connection pool
- OR temporarily block database port to simulate connectivity issue

**Procedure:**
1. Have tester open `docs/runbooks/database-connection-issues.md`
2. Tester executes Diagnosis steps:
   - Verify database pod health
   - Test basic connectivity
   - Check active connections
   - Identify long-running queries
   - Check connection pool config
3. Based on findings, execute Resolution:
   - If pool exhausted: Increase pool size
   - If slow query: Terminate long runner
   - If RLS issue: Verify policies

**Expected Outcomes:**
- [ ] Tester confirms database pod is running
- [ ] Tester identifies connection pool exhaustion (active connections near limit)
- [ ] Tester determines resolution (increase pool size)
- [ ] Tester executes fix and verifies queue processing resumes

**Success Criteria:**
✅ Tester identifies pool exhaustion and increases capacity
⚠️ Issues: [Document if SQL queries were unfamiliar, RLS confusing, etc.]

---

### Test 4: API Timeout Runbook

**Objective:** Verify team member can identify external API issues and test fixes

**Setup:**
- Mock slow ServiceDesk Plus API (add 15+ second delay)
- OR mock OpenAI API returning 429 (rate limited)
- Enqueue enhancements that will timeout

**Procedure:**
1. Have tester open `docs/runbooks/api-timeout.md`
2. Tester executes Diagnosis steps:
   - Check external API status pages
   - Test API manually with curl
   - Review worker logs for timeout pattern
   - Check distributed traces for slow spans
3. Based on findings, execute Resolution:
   - If external service degraded: Wait or implement backoff
   - If rate limited: Reduce request rate
   - If credentials invalid: Update API keys

**Expected Outcomes:**
- [ ] Tester identifies which API is slow (ServiceDesk Plus vs OpenAI)
- [ ] Tester tests API connectivity manually
- [ ] Tester reviews worker logs for timeout pattern
- [ ] Tester suggests remediation (if possible with available tools)

**Success Criteria:**
✅ Tester isolates problem to specific external API
⚠️ Issues: [Document if curl commands were unclear, trace analysis difficult, etc.]

---

### Test 5: Tenant Onboarding Runbook

**Objective:** Verify team member can provision new tenant following documented steps

**Setup:**
- Provide test credentials for staging ServiceDesk Plus instance
- Clear any previous test tenant from database

**Procedure:**
1. Have tester open `docs/runbooks/tenant-onboarding.md`
2. Tester executes all steps:
   - Create tenant database entry
   - Configure API credentials in Kubernetes secret
   - Test API connectivity
   - Configure webhook in ServiceDesk Plus
   - Validate webhook delivery
   - Add tenant to Grafana
3. Tester creates test ticket and verifies enhancement is generated

**Expected Outcomes:**
- [ ] Tenant entry created in database
- [ ] API credentials configured
- [ ] API connectivity test succeeds
- [ ] Webhook configured in SDP and active
- [ ] Test ticket webhook delivered to platform
- [ ] Test ticket updated with enhancement content

**Success Criteria:**
✅ Tester successfully provisions new tenant end-to-end
⚠️ Issues: [Document if any steps were unclear, commands had permissions issues, etc.]

---

## Findings Summary

### By Runbook

#### High Queue Depth Runbook
- **Clarity:** [Excellent / Good / Fair / Poor]
- **Completeness:** [All steps covered / Missing [X] / ]
- **Command Accuracy:** [All worked / Failed: [command] ]
- **Issues Found:** [None / List ambiguities]
- **Improvements Needed:** [List suggestions]

#### Worker Failures Runbook
- **Clarity:** [Excellent / Good / Fair / Poor]
- **Completeness:** [All steps covered / Missing [X] / ]
- **Command Accuracy:** [All worked / Failed: [command] ]
- **Issues Found:** [None / List ambiguities]
- **Improvements Needed:** [List suggestions]

#### Database Connection Issues Runbook
- **Clarity:** [Excellent / Good / Fair / Poor]
- **Completeness:** [All steps covered / Missing [X] / ]
- **Command Accuracy:** [All worked / Failed: [command] ]
- **Issues Found:** [None / List ambiguities]
- **Improvements Needed:** [List suggestions]

#### API Timeout Runbook
- **Clarity:** [Excellent / Good / Fair / Poor]
- **Completeness:** [All steps covered / Missing [X] / ]
- **Command Accuracy:** [All worked / Failed: [command] ]
- **Issues Found:** [None / List ambiguities]
- **Improvements Needed:** [List suggestions]

#### Tenant Onboarding Runbook
- **Clarity:** [Excellent / Good / Fair / Poor]
- **Completeness:** [All steps covered / Missing [X] / ]
- **Command Accuracy:** [All worked / Failed: [command] ]
- **Issues Found:** [None / List ambiguities]
- **Improvements Needed:** [List suggestions]

---

## Overall Assessment

### Runbook Quality Metrics

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| All runbooks completable without external help | 100% | TBD | TBD |
| Average time to complete per runbook | <15 min | TBD | TBD |
| Command success rate (no failures) | 100% | TBD | TBD |
| Clarity issues requiring fix | 0 | TBD | TBD |

### Tester Feedback

**Strengths:**
- [TBD: What worked well]

**Improvement Areas:**
- [TBD: What was confusing]

**Overall Experience:**
- [TBD: Would tester recommend runbooks for production incidents?]

---

## Action Items

| Issue | Priority | Action | Owner | Status |
|-------|----------|--------|-------|--------|
| TBD | TBD | TBD | TBD | TBD |

---

## Sign-Off

**Tester Name:** TBD
**Date Tested:** TBD
**Testing Duration:** TBD
**Approved for Production:** [ ] Yes [ ] No

**Reviewer Name:** TBD
**Review Date:** TBD
**Comments:** TBD

---

## Appendix: Testing Environment Setup

### Prerequisites for Tester
- [ ] Access to Kubernetes cluster or docker-compose environment
- [ ] kubectl/docker-compose installed and configured
- [ ] Access to PostgreSQL database
- [ ] Access to Redis CLI
- [ ] curl or similar HTTP testing tool
- [ ] Git access to codebase
- [ ] Grafana access (http://localhost:3000)
- [ ] Jaeger access (http://localhost:16686)

### Test Data Setup
- [ ] Sample enhancement jobs queued (for Queue Depth test)
- [ ] Test credentials for external APIs (if applicable)
- [ ] Staging ServiceDesk Plus instance access (for Tenant Onboarding)

### After Testing
- [ ] Clean up test data from database
- [ ] Restore original configurations
- [ ] Document any permanent changes needed

---

---

## Integration Testing Checklist (Task 13)

Complete these checks after individual runbooks are validated to ensure all operational components work together:

### Grafana Dashboard Links

- [ ] **Main Dashboard Panel Descriptions:**
  - [ ] Navigate to Grafana: http://localhost:3000/d/ai-agents-dashboard
  - [ ] Success Rate panel: Click info icon, verify runbook links display
  - [ ] Queue Depth panel: Click info icon, verify High Queue Depth runbook link works
  - [ ] Worker Count panel: Click info icon, verify Worker Failures runbook link works
  - [ ] Latency panel: Click info icon, verify API Timeout runbook link works
  - [ ] Click each runbook link and verify navigation works
  - [ ] Notes: [Any broken links or formatting issues?]

- [ ] **Operations Center Dashboard:**
  - [ ] Navigate to Grafana: http://localhost:3000/d/operations-center
  - [ ] All stat panels display metrics correctly
  - [ ] Quick actions section has runbook links
  - [ ] Click each runbook link from Operations Center dashboard
  - [ ] Verify "Operational Runbooks" table displays all 5 runbooks
  - [ ] Verify Jaeger UI link works: http://localhost:16686
  - [ ] Notes: [Any issues?]

### Prometheus Alert Annotations

- [ ] **Alert Annotations Verification:**
  - [ ] Navigate to Prometheus: http://localhost:9090/alerts
  - [ ] Expand alert: EnhancementSuccessRateLow
    - [ ] Verify `operational_context` annotation present
    - [ ] Annotation links to relevant runbooks
  - [ ] Expand alert: QueueDepthHigh
    - [ ] Verify operational_context annotation present
  - [ ] Expand alert: WorkerDown
    - [ ] Verify operational_context annotation present
  - [ ] Expand alert: HighLatency
    - [ ] Verify operational_context annotation present
  - [ ] Notes: [Any missing or broken annotations?]

### End-to-End Incident Response Test

Simulate a production incident to verify the complete operational workflow:

- [ ] **Simulate Queue Depth Alert:**
  - [ ] Action: Enqueue 120+ jobs to trigger QueueDepthHigh alert
  - [ ] Verify alert fires in Prometheus
  - [ ] Follow `operational_context` annotation to High Queue Depth runbook
  - [ ] Execute runbook diagnosis steps
  - [ ] Execute resolution (scale workers or reduce load)
  - [ ] Verify queue drains and alert clears
  - [ ] **Time to Resolution:** [Minutes]
  - [ ] **Runbook Effectiveness:** [ ] Excellent [ ] Good [ ] Fair [ ] Poor
  - [ ] Notes: [What worked? What could be improved?]

- [ ] **Simulate Worker Failure:**
  - [ ] Action: Stop all worker containers/pods
  - [ ] Verify WorkerDown alert fires in Prometheus
  - [ ] Follow operational_context annotation to Worker Failures runbook
  - [ ] Execute runbook diagnosis (check logs, status)
  - [ ] Execute remediation (restart workers)
  - [ ] Verify enhancement processing resumes
  - [ ] Verify alert clears
  - [ ] **Time to Resolution:** [Minutes]
  - [ ] **Runbook Effectiveness:** [ ] Excellent [ ] Good [ ] Fair [ ] Poor
  - [ ] Notes: [What worked? What could be improved?]

- [ ] **Simulate API Timeout:**
  - [ ] Action: Mock slow OpenAI API (add 30+ second delay)
  - [ ] Enqueue enhancements that will hit timeout
  - [ ] Verify HighLatency alert may fire
  - [ ] Follow operational_context annotation to API Timeout runbook
  - [ ] Execute diagnosis steps (test API, check logs, review traces)
  - [ ] Review distributed traces in Jaeger (http://localhost:16686)
  - [ ] Verify runbook guidance on circuit breaker/retry configuration
  - [ ] **Trace Analysis Effectiveness:** [ ] Excellent [ ] Good [ ] Fair [ ] Poor
  - [ ] Notes: [Was Jaeger guidance helpful?]

### Final Assessment

- [ ] **All Integration Tests Passed:** [ ] Yes [ ] No (issues found)
- [ ] **Grafana Dashboard Integration:** [ ] Working [ ] Issues (see notes)
- [ ] **Prometheus Alert Integration:** [ ] Working [ ] Issues (see notes)
- [ ] **End-to-End Incident Response:** [ ] Effective [ ] Needs refinement
- [ ] **Runbook Accessibility During Incident:** [ ] Easy [ ] Moderate [ ] Difficult
- [ ] **Overall Story Completion:** [ ] Ready for production [ ] Minor fixes needed [ ] Significant work needed

**Integration Test Results:**
- [Document overall findings, any issues discovered, recommendations for improvement]

---

**Report Status:** ⏳ Pending
**Last Updated:** 2025-11-03
**Next Review:** After team member validation and integration testing complete
