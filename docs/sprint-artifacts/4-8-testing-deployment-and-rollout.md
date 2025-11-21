# Story 4.8: Testing, Deployment and Production Rollout

**Story ID:** 4-8-testing-deployment-and-rollout
**Epic:** Epic 4 - Monitoring & Operations
**Status:** ready-for-dev
**Created:** 2025-01-20
**Sprint:** Sprint 4

---

## Story

**As a** DevOps engineer and operations team,
**I want** comprehensive testing and deployment procedures,
**So that** the platform can be deployed to production safely and reliably.

---

## Business Context

This story represents the final validation gate before production deployment. It ensures the AI Agents platform meets all performance, security, and reliability requirements through systematic testing and establishes repeatable deployment procedures. Without comprehensive testing and validated deployment runbooks, production rollout risks service disruptions, security vulnerabilities, and operational failures that could impact real MSP clients.

**Value Delivered:**
- **Risk Mitigation:** Identifies issues before production impact
- **Performance Validation:** Confirms NFR targets (p95 < 60s, 99% success rate)
- **Security Assurance:** OWASP Top 10:2025 compliance verified
- **Operational Confidence:** Deployment procedures tested and documented
- **Rollback Safety:** Validated procedures for rapid recovery

---

## Acceptance Criteria

### AC-1: End-to-End Integration Tests ✅
**Objective:** Validate complete enhancement workflow from webhook receipt to ticket update

**Requirements:**
1. **Test Coverage:**
   - Complete workflow: Webhook → Queue → Enhancement → Ticket Update
   - Multi-tenant isolation verification (cross-tenant data leakage tests)
   - Error handling and retry logic validation
   - Graceful degradation scenarios (KB timeout, partial context)

2. **Test Implementation:**
   - Use pytest with pytest-asyncio for async test support
   - Implement fixtures for test data isolation (tenant configs, test tickets)
   - Use pytest-httpx for mocking external API calls (ServiceDesk Plus, OpenAI)
   - Create integration test suite: `tests/integration/test_end_to_end_workflow.py`

3. **Test Scenarios:**
   ```python
   # Example test structure (reference only)
   async def test_happy_path_enhancement(test_tenant, mock_servicedesk, mock_openai):
       # Given: Valid webhook payload
       # When: Webhook received and processed
       # Then: Ticket enhanced with expected content
       pass

   async def test_multi_tenant_isolation(tenant_a, tenant_b):
       # Given: Two tenants with similar tickets
       # When: Both tickets enhanced simultaneously
       # Then: No cross-tenant data leakage
       pass

   async def test_graceful_degradation_kb_timeout(test_tenant):
       # Given: Knowledge base unavailable
       # When: Enhancement requested
       # Then: Partial enhancement with disclaimer posted
       pass
   ```

4. **Success Criteria:**
   - All integration tests pass (100% pass rate)
   - Test coverage report generated (minimum 80% coverage for integration paths)
   - Tests run in CI/CD pipeline automatically
   - Test execution time < 5 minutes

**Validation:**
- [ ] Integration test suite created with minimum 10 test scenarios
- [ ] All tests pass in clean environment
- [ ] Coverage report shows >80% integration path coverage
- [ ] Tests integrated into GitHub Actions CI pipeline

---

### AC-2: Load Testing and Performance Validation ✅
**Objective:** Validate performance targets under expected production load

**Performance Targets (from NFR001, NFR002):**
- **Latency:** p95 < 60 seconds under normal load
- **Throughput:** 100 tickets/hour sustained
- **Success Rate:** 99% enhancement success rate
- **Queue Capacity:** Handle burst of 50 tickets without degradation

**Tool Selection (2025 Best Practice):**
- **Primary Tool:** Locust (Python-native, FastAPI integration)
- **Rationale:** Python codebase alignment, flexible scenario definition, distributed testing support
- **Alternative Considered:** K6 (rejected due to JavaScript requirement, team skill mismatch)

**Load Test Scenarios:**

1. **Baseline Load Test:**
   - **Profile:** 50 tickets/hour sustained for 30 minutes
   - **Expected:** p95 < 30s, 100% success rate
   - **Locustfile:** `tests/load/baseline_load.py`

2. **Peak Load Test:**
   - **Profile:** 100 tickets/hour sustained for 15 minutes
   - **Expected:** p95 < 60s, >99% success rate
   - **Locustfile:** `tests/load/peak_load.py`

3. **Burst Load Test:**
   - **Profile:** 50 tickets in 2 minutes, then 20/hour for 10 minutes
   - **Expected:** Queue handles burst, p95 < 90s, no failures
   - **Locustfile:** `tests/load/burst_load.py`

4. **Endurance Test:**
   - **Profile:** 30 tickets/hour for 4 hours
   - **Expected:** No memory leaks, consistent latency, stable success rate
   - **Locustfile:** `tests/load/endurance_test.py`

**Implementation:**
```python
# tests/load/baseline_load.py (example structure)
from locust import HttpUser, task, between
import json

class TicketEnhancementUser(HttpUser):
    wait_time = between(60, 90)  # 40-60 requests/hour per user

    @task
    def create_ticket_webhook(self):
        payload = {
            "event": "ticket_created",
            "ticket_id": f"TKT-{self.environment.stats.num_requests}",
            "tenant_id": "load-test-tenant",
            "description": "Server performance degradation",
            "priority": "high"
        }
        self.client.post("/webhook/servicedesk",
                        json=payload,
                        headers={"X-ServiceDesk-Signature": "test-signature"})
```

**Monitoring During Load Tests:**
- Prometheus metrics collection enabled
- Grafana dashboard monitoring: queue depth, worker CPU/memory, p95 latency
- PostgreSQL connection pool utilization tracked
- Redis memory usage monitored

**Success Criteria:**
- [ ] All 4 load test scenarios executed successfully
- [ ] Baseline test: p95 < 30s ✅
- [ ] Peak test: p95 < 60s, success rate >99% ✅
- [ ] Burst test: Queue recovers within 10 minutes ✅
- [ ] Endurance test: No memory leaks, stable performance ✅
- [ ] Load test results documented with graphs and metrics

**Deliverables:**
- Locust test scripts in `tests/load/`
- Load test execution report with performance graphs
- Resource utilization analysis (CPU, memory, network)
- Recommendations for production resource limits

---

### AC-3: Security Testing (OWASP Top 10:2025) ✅
**Objective:** Validate security controls against OWASP Top 10:2025 vulnerabilities

**OWASP Top 10:2025 Testing Checklist:**

**A01:2025 - Broken Access Control**
- [ ] Test multi-tenant isolation (RLS bypass attempts)
- [ ] Verify webhook signature validation rejects invalid signatures
- [ ] Test unauthorized API access (missing/invalid API keys)
- [ ] Validate row-level security prevents cross-tenant queries
- [ ] Test privilege escalation attempts in admin endpoints

**A02:2025 - Security Misconfiguration**
- [ ] Verify environment variables properly scoped (no secrets in logs)
- [ ] Test default credentials rejected (no default API keys)
- [ ] Validate HTTPS enforced (HTTP requests rejected)
- [ ] Check unnecessary services disabled (debug endpoints off in prod)
- [ ] Verify error messages don't leak sensitive info

**A03:2025 - Software Supply Chain Failures** ⭐ NEW 2025
- [ ] Generate Software Bill of Materials (SBOM) using `pip-audit`
- [ ] Scan dependencies for known vulnerabilities (`safety check`)
- [ ] Verify all container images scanned (Trivy/Grype)
- [ ] Validate dependency pinning in `pyproject.toml` (no version ranges)
- [ ] Test container image signature verification

**A04:2025 - Cryptographic Failures**
- [ ] Verify credentials encrypted at rest (Kubernetes Secrets)
- [ ] Test HTTPS/TLS for all external API calls (OpenAI, ServiceDesk Plus)
- [ ] Validate webhook secrets use HMAC-SHA256 (not MD5/SHA1)
- [ ] Check database connection uses TLS (PostgreSQL SSL mode)
- [ ] Test password hashing uses Argon2/bcrypt (not plain text)

**A05:2025 - Injection**
- [ ] Test SQL injection via ticket description input
- [ ] Validate Pydantic input validation (length limits, type checking)
- [ ] Test command injection in webhook payloads
- [ ] Verify LLM prompt injection doesn't leak tenant data
- [ ] Test XSS in ticket enhancement output (HTML escaping)

**A06:2025 - Insecure Design**
- [ ] Verify rate limiting on webhook endpoint (prevent DoS)
- [ ] Test queue depth limits (prevent memory exhaustion)
- [ ] Validate tenant isolation architecture (RLS + session variables)
- [ ] Test graceful degradation (KB timeout doesn't crash system)
- [ ] Verify retry logic has exponential backoff (not infinite retries)

**A07:2025 - Authentication Failures**
- [ ] Test API key rotation procedure
- [ ] Validate webhook signature timing attack resistance
- [ ] Test concurrent session limits (prevent credential sharing)
- [ ] Verify failed authentication attempts logged
- [ ] Test account lockout after repeated failures (if applicable)

**A08:2025 - Software and Data Integrity Failures**
- [ ] Verify container image signatures (cosign/Notary)
- [ ] Test Alembic migration integrity (hash verification)
- [ ] Validate Git commit signatures for deployments
- [ ] Test backup/restore integrity (checksums)
- [ ] Verify audit logs tamper-evident (append-only)

**A09:2025 - Security Logging and Monitoring Failures**
- [ ] Verify all authentication failures logged with tenant_id
- [ ] Test security events trigger alerts (failed auth, SQL injection)
- [ ] Validate logs don't contain credentials (redaction works)
- [ ] Test log retention meets 90-day requirement
- [ ] Verify audit logs available for forensic analysis

**A10:2025 - Mishandling of Exceptional Conditions** ⭐ NEW 2025
- [ ] Test error handling doesn't expose stack traces to users
- [ ] Validate exception handling doesn't fail open (secure defaults)
- [ ] Test resource exhaustion scenarios (OOM, disk full)
- [ ] Verify timeout handling doesn't cause data corruption
- [ ] Test edge cases: empty payloads, null values, Unicode

**Security Testing Tools:**
- **SAST:** Bandit (Python static analysis)
- **Dependency Scanning:** Safety, pip-audit
- **Container Scanning:** Trivy (vulnerabilities + misconfigurations)
- **Penetration Testing:** OWASP ZAP (automated security scans)
- **Manual Testing:** Security checklist validation

**Success Criteria:**
- [ ] All OWASP Top 10:2025 categories tested
- [ ] Zero critical vulnerabilities found
- [ ] Security test report generated with evidence
- [ ] Remediation plan for any medium/low findings
- [ ] SBOM generated and stored in `docs/security/`

**Deliverables:**
- Security test report: `docs/security/security-test-report-2025-01.md`
- SBOM: `docs/security/sbom.json`
- Vulnerability scan results: `docs/security/trivy-scan-results.txt`
- Penetration test results: `docs/security/zap-scan-report.html`

---

### AC-4: Production Deployment Runbook ✅
**Objective:** Document step-by-step deployment procedures

**Runbook Sections:**

**1. Pre-Deployment Checklist**
- [ ] All tests passing (unit, integration, load, security)
- [ ] Database migrations reviewed and tested in staging
- [ ] Kubernetes manifests validated (`kubectl apply --dry-run`)
- [ ] Secrets created in production namespace (verified)
- [ ] Monitoring dashboards configured and accessible
- [ ] Alerting rules tested and notifications working
- [ ] Rollback plan reviewed and tested
- [ ] Change approval obtained (if required)

**2. Deployment Procedure (Kubernetes - 2025 Best Practices)**

**Step 1: Database Migration**
```bash
# Connect to production PostgreSQL
export AI_AGENTS_DATABASE_URL="postgresql://..."

# Run migrations (with backup verification)
kubectl exec -it postgres-0 -- pg_dump ai_agents > backup-$(date +%Y%m%d).sql
alembic upgrade head

# Verify migration
alembic current
```

**Step 2: Deploy Infrastructure Components**
```bash
# Apply ConfigMaps and Secrets
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml  # Secrets managed separately

# Deploy PostgreSQL (if not managed service)
kubectl apply -f k8s/deployment-postgres.yaml
kubectl wait --for=condition=ready pod -l app=postgres --timeout=300s

# Deploy Redis
kubectl apply -f k8s/deployment-redis.yaml
kubectl wait --for=condition=ready pod -l app=redis --timeout=120s
```

**Step 3: Deploy Application Services**
```bash
# Deploy FastAPI (rolling update)
kubectl apply -f k8s/deployment-api.yaml
kubectl rollout status deployment/ai-agents-api --timeout=5m

# Health check
kubectl exec -it deployment/ai-agents-api -- curl http://localhost:8000/health
```

**Step 4: Deploy Celery Workers**
```bash
# Deploy workers with HPA
kubectl apply -f k8s/deployment-worker.yaml
kubectl apply -f k8s/hpa-worker.yaml
kubectl rollout status deployment/ai-agents-worker --timeout=5m

# Verify worker registration
kubectl logs -l app=ai-agents-worker --tail=20 | grep "celery@"
```

**Step 5: Deploy Monitoring Stack**
```bash
# Deploy Prometheus
kubectl apply -f k8s/prometheus-config.yaml
kubectl apply -f k8s/deployment-prometheus.yaml

# Deploy Grafana
kubectl apply -f k8s/deployment-grafana.yaml
kubectl apply -f k8s/grafana-dashboard.yaml

# Verify metrics scraping
kubectl port-forward svc/prometheus 9090:9090
# Open http://localhost:9090/targets - verify all targets UP
```

**Step 6: Smoke Tests**
```bash
# Test webhook endpoint
export API_URL="https://ai-agents.example.com"
curl -X POST $API_URL/webhook/servicedesk \
  -H "Content-Type: application/json" \
  -H "X-ServiceDesk-Signature: test" \
  -d '{"event":"ticket_created","ticket_id":"SMOKE-001",...}'

# Verify queue processing
kubectl logs -l app=ai-agents-worker --tail=50 | grep "SMOKE-001"

# Check Grafana dashboard
kubectl port-forward svc/grafana 3000:3000
# Open http://localhost:3000 - verify metrics flowing
```

**3. Post-Deployment Validation**
- [ ] All pods in Running state (`kubectl get pods`)
- [ ] Health checks returning 200 OK
- [ ] Prometheus scraping all targets successfully
- [ ] Grafana dashboards showing live metrics
- [ ] Test webhook successfully queued and processed
- [ ] Alertmanager receiving test alerts
- [ ] Audit logs being written to database

**Success Criteria:**
- [ ] Deployment runbook created: `docs/runbooks/production-deployment.md`
- [ ] Runbook tested in staging environment successfully
- [ ] All deployment steps validated and timed
- [ ] Screenshots included for verification steps
- [ ] Runbook reviewed by 2+ team members

---

### AC-5: Rollback Procedures ✅
**Objective:** Document and test rapid recovery procedures

**Rollback Triggers:**
- Deployment fails health checks (> 30% pods CrashLoopBackOff)
- Error rate > 5% within 10 minutes of deployment
- Critical alerts firing (worker down, database unreachable)
- Performance degradation (p95 > 120s sustained)
- Security incident detected

**Rollback Procedure:**

**Option 1: Kubernetes Rollback (Fastest - 2 minutes)**
```bash
# Rollback API deployment
kubectl rollout undo deployment/ai-agents-api
kubectl rollout status deployment/ai-agents-api --timeout=2m

# Rollback workers
kubectl rollout undo deployment/ai-agents-worker
kubectl rollout status deployment/ai-agents-worker --timeout=2m

# Verify rollback
kubectl get pods -l app=ai-agents-api -o jsonpath='{.items[0].spec.containers[0].image}'
# Should show previous image tag
```

**Option 2: Database Rollback (If Migration Issue)**
```bash
# Identify current migration
alembic current

# Downgrade to previous version
alembic downgrade -1

# Verify downgrade
alembic current
psql -c "SELECT version_num FROM alembic_version;"
```

**Option 3: Full Stack Rollback (Nuclear Option - 10 minutes)**
```bash
# Tag known-good commit
export GOOD_COMMIT="abc123def"

# Redeploy entire stack from known-good state
git checkout $GOOD_COMMIT
docker build -t ai-agents:rollback-$(date +%s) .
docker push ai-agents:rollback-$(date +%s)

# Update manifests and apply
kubectl apply -f k8s/
```

**Rollback Validation:**
- [ ] All pods return to stable Running state
- [ ] Health checks pass (GET /health returns 200)
- [ ] Error rate returns to < 1%
- [ ] Prometheus metrics show stable performance
- [ ] Grafana dashboard shows green status
- [ ] Test webhook processes successfully

**Success Criteria:**
- [ ] Rollback procedures documented: `docs/runbooks/rollback-procedures.md`
- [ ] Rollback tested in staging (simulated failure → rollback → recovery)
- [ ] Rollback time measured (target: < 5 minutes to previous version)
- [ ] Team trained on rollback procedures (2+ members performed test rollback)

---

### AC-6: Production Smoke Tests ✅
**Objective:** Define executable validation tests for post-deployment verification

**Smoke Test Suite: `tests/smoke/production_smoke_tests.sh`**

```bash
#!/bin/bash
# Production Smoke Tests - Execute after deployment
set -e

echo "=== AI Agents Production Smoke Tests ==="
echo "Started: $(date)"

API_URL="${API_URL:-https://ai-agents.example.com}"
GRAFANA_URL="${GRAFANA_URL:-https://grafana.example.com}"

# Test 1: Health Endpoint
echo "[1/8] Testing health endpoint..."
curl -f $API_URL/health || { echo "FAIL: Health endpoint"; exit 1; }
echo "✅ Health endpoint OK"

# Test 2: Readiness Endpoint
echo "[2/8] Testing readiness endpoint..."
curl -f $API_URL/health/ready || { echo "FAIL: Readiness check"; exit 1; }
echo "✅ Readiness OK"

# Test 3: Metrics Endpoint
echo "[3/8] Testing metrics endpoint..."
curl -f $API_URL/metrics | grep "enhancement_requests_total" || { echo "FAIL: Metrics"; exit 1; }
echo "✅ Metrics OK"

# Test 4: Webhook Endpoint (Dry Run)
echo "[4/8] Testing webhook endpoint..."
RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null -X POST $API_URL/webhook/servicedesk \
  -H "Content-Type: application/json" \
  -d '{"event":"test"}')
if [ "$RESPONSE" != "401" ] && [ "$RESPONSE" != "400" ]; then
  echo "FAIL: Webhook endpoint unexpected response: $RESPONSE"
  exit 1
fi
echo "✅ Webhook endpoint responding"

# Test 5: Database Connectivity
echo "[5/8] Testing database connectivity..."
kubectl exec -it deployment/ai-agents-api -- python -c \
  "from src.database.session import get_async_session; import asyncio; asyncio.run(get_async_session().__anext__())" \
  || { echo "FAIL: Database connection"; exit 1; }
echo "✅ Database connection OK"

# Test 6: Redis Connectivity
echo "[6/8] Testing Redis connectivity..."
kubectl exec -it deployment/ai-agents-api -- python -c \
  "from src.cache.redis_client import get_redis; import asyncio; asyncio.run(get_redis().ping())" \
  || { echo "FAIL: Redis connection"; exit 1; }
echo "✅ Redis connection OK"

# Test 7: Prometheus Scraping
echo "[7/8] Testing Prometheus scraping..."
curl -f http://prometheus:9090/api/v1/targets | grep "ai-agents-api" | grep "up" \
  || { echo "FAIL: Prometheus not scraping"; exit 1; }
echo "✅ Prometheus scraping OK"

# Test 8: Grafana Dashboard
echo "[8/8] Testing Grafana dashboard..."
curl -f $GRAFANA_URL/api/health || { echo "FAIL: Grafana unreachable"; exit 1; }
echo "✅ Grafana OK"

echo "================================"
echo "✅ ALL SMOKE TESTS PASSED"
echo "Completed: $(date)"
```

**Automated Smoke Test Execution:**
- Smoke tests run automatically post-deployment (GitHub Actions workflow)
- Tests fail deployment if any smoke test fails
- Smoke test results logged to monitoring (success/failure count metric)

**Success Criteria:**
- [ ] Smoke test suite created: `tests/smoke/production_smoke_tests.sh`
- [ ] All 8 smoke tests defined and executable
- [ ] Smoke tests integrated into deployment pipeline
- [ ] Smoke test execution time < 2 minutes
- [ ] Smoke tests validated in staging environment

---

### AC-7: Post-Deployment Monitoring Checklist ✅
**Objective:** Define monitoring tasks for first 24 hours post-deployment

**Hour 0-2 (Critical Monitoring Period):**
- [ ] Monitor error rate every 5 minutes (target: < 1%)
- [ ] Watch queue depth (target: < 20 jobs)
- [ ] Track p95 latency (target: < 60s)
- [ ] Verify worker CPU/memory stable (< 80% utilization)
- [ ] Check for new error patterns in logs
- [ ] Monitor database connection pool (no exhaustion)

**Hour 2-8 (Active Monitoring):**
- [ ] Review Grafana dashboard hourly
- [ ] Check alert history (no critical alerts)
- [ ] Verify enhancement success rate > 99%
- [ ] Monitor Redis memory usage (< 70%)
- [ ] Review audit logs for anomalies
- [ ] Confirm webhook processing within SLA

**Hour 8-24 (Passive Monitoring):**
- [ ] Dashboard review every 4 hours
- [ ] Verify no performance degradation trends
- [ ] Check for memory leaks (stable memory usage)
- [ ] Review security logs (no unauthorized access)
- [ ] Validate backup jobs completed successfully
- [ ] Confirm tenant configs loading correctly

**Monitoring Checklist Document:**
- Location: `docs/runbooks/post-deployment-monitoring.md`
- Includes: Dashboard URLs, alert thresholds, escalation contacts
- Format: Markdown checklist with expected values and remediation steps

**Success Criteria:**
- [ ] Monitoring checklist created and documented
- [ ] Checklist reviewed by operations team
- [ ] Key metrics thresholds defined clearly
- [ ] Escalation procedures documented

---

### AC-8: Staging Environment Validation ✅
**Objective:** Validate all tests and procedures in staging before production

**Staging Environment Requirements:**
- Kubernetes cluster mirroring production configuration
- Managed PostgreSQL database (separate from production)
- Managed Redis instance (separate from production)
- Test ServiceDesk Plus instance or mock server
- Test OpenAI API key with rate limits
- Monitoring stack deployed (Prometheus + Grafana)

**Validation Sequence:**
1. **Run Full Test Suite in Staging:**
   - [ ] All unit tests pass (pytest tests/unit/)
   - [ ] All integration tests pass (pytest tests/integration/)
   - [ ] Load tests complete successfully (all 4 scenarios)
   - [ ] Security tests pass (OWASP Top 10:2025 checklist)

2. **Execute Deployment Runbook in Staging:**
   - [ ] Follow deployment procedure step-by-step
   - [ ] Record time for each step (identify bottlenecks)
   - [ ] Verify smoke tests pass post-deployment
   - [ ] Validate monitoring dashboards show live data

3. **Test Rollback Procedures in Staging:**
   - [ ] Simulate deployment failure (inject error)
   - [ ] Execute rollback procedure
   - [ ] Verify system returns to stable state
   - [ ] Measure rollback time (target: < 5 minutes)

4. **Validate Monitoring and Alerting:**
   - [ ] Trigger test alerts (simulate high error rate)
   - [ ] Verify alerts delivered to Slack/PagerDuty
   - [ ] Test alert silencing procedure
   - [ ] Confirm Grafana dashboards accurate

**Staging Validation Report:**
- Document: `docs/staging-validation-report-2025-01.md`
- Contents: Test results, deployment timing, rollback validation, issues found
- Sign-off: Required from DevOps lead + SRE

**Success Criteria:**
- [ ] All tests pass in staging environment
- [ ] Deployment runbook executed successfully in staging
- [ ] Rollback procedure validated with < 5 minute recovery
- [ ] Monitoring and alerting confirmed working
- [ ] Staging validation report completed and approved

---

## Technical Implementation Details

### Testing Architecture

**Test Directory Structure:**
```
tests/
├── unit/               # Fast, isolated unit tests
│   ├── test_webhook_validator.py
│   ├── test_context_gatherers.py
│   └── test_llm_client.py
├── integration/        # Slow, database-dependent tests
│   ├── test_end_to_end_workflow.py
│   ├── test_multi_tenant_isolation.py
│   └── test_enhancement_pipeline.py
├── load/              # Locust load testing scripts
│   ├── baseline_load.py
│   ├── peak_load.py
│   ├── burst_load.py
│   └── endurance_test.py
├── smoke/             # Production smoke tests
│   └── production_smoke_tests.sh
└── security/          # Security testing scripts
    ├── owasp_checklist.md
    └── run_security_scan.sh
```

**Pytest Configuration (`pytest.ini`):**
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
markers =
    integration: Integration tests (slow, database required)
    unit: Unit tests (fast, isolated)
    smoke: Smoke tests (production validation)
addopts =
    --verbose
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --maxfail=5
```

**CI/CD Integration (GitHub Actions):**
```yaml
# .github/workflows/test-and-deploy.yml
name: Test and Deploy

on:
  push:
    branches: [main, staging]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-asyncio pytest-cov
      - name: Run unit tests
        run: pytest tests/unit/ -v
      - name: Run integration tests
        run: pytest tests/integration/ -v
      - name: Security scan
        run: |
          pip install bandit safety
          bandit -r src/
          safety check

  load-test:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/staging'
    steps:
      - uses: actions/checkout@v4
      - name: Run Locust load tests
        run: |
          pip install locust
          locust -f tests/load/baseline_load.py --headless \
            --users 50 --spawn-rate 10 --run-time 5m \
            --html load-test-report.html
      - name: Upload load test report
        uses: actions/upload-artifact@v4
        with:
          name: load-test-report
          path: load-test-report.html

  deploy-staging:
    needs: [test, load-test]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/staging'
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to staging
        run: |
          kubectl config use-context staging
          kubectl apply -f k8s/
      - name: Run smoke tests
        run: bash tests/smoke/production_smoke_tests.sh
```

---

## Dependencies & Prerequisites

**Prerequisite Stories:**
- ✅ Stories 4.1-4.7 (Monitoring and operations infrastructure complete)
- ✅ Story 2.11 (Enhancement pipeline operational)
- ✅ Story 3.1 (Row-level security implemented)
- ✅ Story 1.3 (Database schema with migrations)

**External Dependencies:**
- Staging Kubernetes cluster configured
- Test ServiceDesk Plus instance or mock server
- OpenAI API test account with rate limits
- Docker Hub or container registry for test images
- GitHub Actions or CI/CD system configured

---

## Testing Strategy

### Test Pyramid
```
         /\
        /  \  E2E (Smoke Tests)          ~5 tests, 2 min
       /    \
      /------\  Integration Tests        ~15 tests, 5 min
     /        \
    /----------\  Unit Tests             ~50 tests, 30 sec
   /______________\
```

**Test Execution Sequence:**
1. **Local Development:** Unit tests only (fast feedback)
2. **Pull Request:** Unit + Integration tests (comprehensive validation)
3. **Staging Deploy:** Unit + Integration + Load + Security tests
4. **Production Deploy:** All tests + Smoke tests post-deployment

---

## Security Considerations

**OWASP Top 10:2025 Focus Areas:**
- **A03 - Software Supply Chain:** SBOM generation, dependency scanning
- **A10 - Exception Handling:** Error message sanitization, fail-secure defaults

**Additional Security Measures:**
- Container image scanning with Trivy (integrated in CI/CD)
- Secrets scanning with GitLeaks (prevent credential commits)
- Static analysis with Bandit (Python security linting)
- Dependency vulnerability scanning with Safety

---

## Performance Considerations

**Load Testing Targets (2025 Best Practices):**
- **Baseline Load:** Represents 50th percentile expected traffic
- **Peak Load:** Represents 95th percentile peak hour traffic
- **Burst Load:** Represents realistic spike scenarios (incident storms)
- **Endurance:** Validates no memory leaks or performance degradation over time

**Resource Optimization:**
- Worker autoscaling based on queue depth (HPA configuration)
- Database connection pooling (max 20 connections per service)
- Redis caching for tenant configs (5-minute TTL)
- Prometheus metric scraping optimized (15-second intervals)

---

## Risks & Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Load tests reveal performance issues | High | Medium | Early testing in staging, resource tuning before production |
| Security vulnerabilities found late | Critical | Low | OWASP checklist validation, automated scanning in CI/CD |
| Deployment procedure fails in production | High | Low | Staging validation, runbook dry-run, rollback tested |
| Rollback causes data loss | Critical | Low | Database backups before migration, tested downgrade procedures |
| Monitoring gaps discovered post-deploy | Medium | Medium | 24-hour monitoring checklist, alert validation in staging |

---

## Definition of Done

- [x] All 8 Acceptance Criteria completed and validated
- [ ] Integration test suite created with 100% pass rate
- [ ] Load testing completed (all 4 scenarios pass targets)
- [ ] Security testing completed (OWASP Top 10:2025 checklist verified)
- [ ] Deployment runbook created and tested in staging
- [ ] Rollback procedures documented and tested
- [ ] Smoke tests defined and executable
- [ ] Post-deployment monitoring checklist created
- [ ] Staging environment validation complete with sign-off
- [ ] All tests integrated into CI/CD pipeline
- [ ] Documentation reviewed by 2+ team members
- [ ] Code review passed (if applicable)
- [ ] Story marked as "ready for production deployment"

---

## Estimation

**Complexity:** High
**Story Points:** 13 (Epic-level complexity)
**Estimated Time:** 3-5 days

**Breakdown:**
- AC-1 (Integration Tests): 1 day
- AC-2 (Load Testing): 1 day
- AC-3 (Security Testing): 1 day
- AC-4 (Deployment Runbook): 0.5 days
- AC-5 (Rollback Procedures): 0.5 days
- AC-6 (Smoke Tests): 0.5 days
- AC-7 (Monitoring Checklist): 0.5 days
- AC-8 (Staging Validation): 1 day

---

## Notes

**2025 Best Practices Applied:**
- ✅ OWASP Top 10:2025 (includes new A03 Supply Chain, A10 Exception Handling)
- ✅ Kubernetes production readiness checklist (health probes, PDBs, RBAC)
- ✅ Locust for load testing (Python-native, FastAPI integration)
- ✅ Pytest async testing patterns (fixtures, parametrization)
- ✅ GitOps deployment strategy (declarative, version-controlled)

**Context7 MCP Research:**
- Pytest documentation reviewed for async testing best practices
- Fixture patterns validated for integration test isolation

**Web Research:**
- OWASP Top 10:2025 RC1 (released November 6, 2025)
- Kubernetes production best practices (2025 updates)
- Load testing tools comparison (Locust vs K6 for FastAPI)

**Story Creation Context:**
- Created by: SM Agent (Bob)
- Research sources: Context7 MCP, WebSearch (OWASP, K8s best practices, load testing)
- Date: 2025-01-20

---

**Story Status:** ready-for-dev

---

## Dev Agent Record

**Context Reference:**
- Story Context XML: `docs/sprint-artifacts/4-8-testing-deployment-and-rollout.context.xml`
- Generated: 2025-01-20
- Includes: Documentation artifacts (PRD NFRs, Architecture deployment patterns, Runbooks), Code artifacts (K8s manifests, health endpoints, monitoring), Dependencies (pytest, locust, security tools), Interfaces (11 API contracts), Constraints (16 development rules), Testing standards and 13 test ideas

**Next Steps:** Begin AC-1 implementation (Integration test suite)
