# CI/CD Testing Workflow Guide

**Version:** 1.0  
**Last Updated:** 2025-11-11  
**Purpose:** Comprehensive guide for integration test execution in CI/CD pipeline  
**Related:** [Integration Testing Guide](integration-testing-guide.md) | [CI/CD Pipeline Guide](ci-cd-pipeline-guide.md)

## Table of Contents

1. [CI/CD Pipeline Overview](#cicd-pipeline-overview)
2. [Integration Test Execution in CI](#integration-test-execution-in-ci)
3. [Test Health Monitoring](#test-health-monitoring)
4. [Debugging CI Test Failures](#debugging-ci-test-failures)
5. [Local Development Testing](#local-development-testing)

---

## CI/CD Pipeline Overview

### GitHub Actions Workflow Structure

**File:** \`.github/workflows/ci.yml\`

**Workflow Stages:**

\`\`\`
1. Lint & Format Check (Black, Ruff, mypy)
   ↓
2. Unit Tests (fast, no external dependencies)
   ↓
3. Integration Tests (Docker: postgres, redis)
   ↓
4. E2E Tests (Playwright + Streamlit)
   ↓
5. Test Health Check (pass rate validation)
   ↓
6. Coverage Upload (Codecov)
\`\`\`

### Test Execution Strategy

| Stage | Parallel | Duration | Dependencies |
|-------|----------|----------|--------------|
| **Lint** | Yes (Black, Ruff, mypy parallel) | ~30s | None |
| **Unit Tests** | Yes (pytest-xdist) | ~2min | None |
| **Integration Tests** | Sequential | ~5min | Docker services |
| **E2E Tests** | Sequential | ~3min | Docker + Streamlit + Browser |

**Total CI Duration:** ~10-12 minutes per run

---

### Caching Strategy

\`\`\`yaml
# .github/workflows/ci.yml caching
- name: Cache pip dependencies
  uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: \${{ runner.os }}-pip-\${{ hashFiles('requirements.txt') }}

- name: Cache npm packages
  uses: actions/setup-node@v4
  with:
    node-version: '20'
    cache: 'npm'  # Caches MCP test server

- name: Cache Playwright browsers
  uses: actions/cache@v4
  with:
    path: ~/.cache/ms-playwright
    key: \${{ runner.os }}-playwright-\${{ hashFiles('requirements.txt') }}
\`\`\`

**Cache Hit Rate:** ~85% (saves 2-3 minutes per run)

---

### Artifact Upload

\`\`\`yaml
- name: Upload test results
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: test-results
    path: |
      test-results.json
      coverage.xml
      pytest-report.html

- name: Upload E2E artifacts
  if: failure()
  uses: actions/upload-artifact@v4
  with:
    name: e2e-artifacts
    path: |
      test-results/screenshots/
      test-results/videos/
      test-results/traces/
\`\`\`

**Retention:** 30 days

---

## Integration Test Execution in CI

### Docker Compose Setup

\`\`\`yaml
# .github/workflows/ci.yml services configuration
jobs:
  integration-tests:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: aiagents
          POSTGRES_PASSWORD: password
          POSTGRES_DB: ai_agents_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379
\`\`\`

**Service Startup Time:** ~20-30 seconds

---

### Environment Variable Configuration

\`\`\`yaml
# .github/workflows/ci.yml environment variables
- name: Run integration tests
  env:
    DATABASE_URL: postgresql+asyncpg://aiagents:password@localhost:5432/ai_agents_test
    REDIS_URL: redis://localhost:6379/1
    LITELLM_MASTER_KEY: \${{ secrets.LITELLM_TEST_KEY }}
    DEFAULT_TENANT_ID: 00000000-0000-0000-0000-000000000001
    MCP_TEST_SERVER_PATH: /usr/local/bin/npx
    CI: true
  run: pytest tests/integration/ -v --cov=src --cov-report=xml
\`\`\`

**Secret Management:**
- Sensitive keys stored in GitHub Secrets
- Test keys use dedicated test accounts (not production)
- Keys rotated every 90 days

---

### Database Migration Execution

\`\`\`yaml
- name: Run database migrations
  env:
    DATABASE_URL: postgresql+asyncpg://aiagents:password@localhost:5432/ai_agents_test
  run: |
    alembic upgrade head
    # Verify migrations applied
    psql \$DATABASE_URL -c "SELECT version_num FROM alembic_version;"
\`\`\`

**Migration Verification:**
- ✅ Ensures schema matches codebase
- ✅ Catches migration errors before tests run
- ✅ Prevents "table not found" test failures

---

### Test Server Setup (MCP, Streamlit)

\`\`\`yaml
# MCP Test Server setup
- name: Setup MCP test server
  run: |
    npm install -g @modelcontextprotocol/server-everything
    npx @modelcontextprotocol/server-everything --help
  
# Streamlit app setup (for E2E tests)
- name: Start Streamlit app
  run: |
    streamlit run src/admin/app.py --server.port 8502 &
    sleep 10  # Wait for app to start
    curl -f http://localhost:8502 || exit 1  # Health check
\`\`\`

---

### Test Execution Command

\`\`\`yaml
- name: Run integration tests
  run: |
    pytest tests/integration/ \
      -v \
      --cov=src \
      --cov-report=xml \
      --cov-report=html \
      --json-report \
      --json-report-file=test-results.json \
      --tb=short \
      --maxfail=5
\`\`\`

**Flags Explained:**
- \`-v\`: Verbose output (show test names)
- \`--cov=src\`: Coverage for src/ directory
- \`--cov-report=xml\`: XML report for Codecov
- \`--json-report\`: Machine-readable test results
- \`--tb=short\`: Short traceback format
- \`--maxfail=5\`: Stop after 5 failures (fast fail)

---

### Test Result Parsing

\`\`\`yaml
- name: Parse test results
  if: always()
  run: |
    python scripts/ci-baseline-check.py test-results.json
    
    # Check pass rate
    pass_rate=\$(jq '.summary.pass_percentage' test-results.json)
    echo "Pass rate: \${pass_rate}%"
    
    if (( \$(echo "\$pass_rate < 95.0" | bc -l) )); then
      echo "::error::Pass rate below 95% threshold: \${pass_rate}%"
      exit 1
    fi
\`\`\`

**Baseline Enforcement:**
- ✅ Requires ≥95% pass rate (current: 89.6%, improving)
- ✅ Fails PR if below threshold
- ✅ Tracks regression over time

---

## Test Health Monitoring

### Test Health Check Script

**File:** \`scripts/test-health-check.py\`

**Features:**
- ✅ Pass rate calculation
- ✅ Failure categorization (Real Bugs, Environment, Flaky, Obsolete)
- ✅ Flaky test detection (multiple failures in last 10 runs)
- ✅ Test metrics tracking (count, duration, coverage)

**Usage:**

\`\`\`bash
# Run test health check
python scripts/test-health-check.py

# Output example:
# Test Health Report
# ==================
# Total Tests: 2,473
# Passing: 2,216 (89.6%)
# Failing: 257 (10.4%)
#
# Failure Categories:
# - Real Bugs: 42
# - Environment Issues: 98
# - Flaky Tests: 85
# - Obsolete Tests: 32
#
# Flaky Tests (failed 3+ times in last 10 runs):
# - tests/integration/test_agent_execution.py::test_timeout
# - tests/e2e/test_mcp_workflow.py::test_tool_invocation
\`\`\`

---

### Baseline Enforcement Script

**File:** \`scripts/ci-baseline-check.py\`

**Purpose:** Prevents regression below acceptable pass rate threshold.

**Configuration:**

\`\`\`yaml
# .github/baseline-config.yaml
baseline:
  total_tests: 2473
  min_pass_rate: 95.0  # Target (current: 89.6%)
  min_unit_pass_rate: 93.0  # Current: 93.93%
  min_integration_pass_rate: 89.0  # Current: 89.6%
  min_e2e_pass_rate: 85.0  # Current: ~90%
\`\`\`

**Usage in CI:**

\`\`\`yaml
- name: Enforce baseline
  run: python scripts/ci-baseline-check.py test-results.json
\`\`\`

**Behavior:**
- ✅ Passes if pass rate ≥ baseline
- ❌ Fails if pass rate < baseline
- 📊 Tracks historical pass rate trends

---

### Pass Rate Calculation

\`\`\`python
# scripts/test-health-check.py calculation
def calculate_pass_rate(results):
    total = results['summary']['total']
    passed = results['summary']['passed']
    pass_rate = (passed / total) * 100
    return round(pass_rate, 2)
\`\`\`

**Current Pass Rates (Story 12.9):**
- Overall: 89.6% (2,216/2,473)
- Unit Tests: 93.93% (1,625/1,730)
- Integration Tests: 89.6% (448/500)
- E2E Tests: ~90% (219/243)

**Target:** ≥95% across all test types

---

### Failure Categorization

| Category | Description | Count | Action |
|----------|-------------|-------|--------|
| **Real Bugs** | Legitimate bugs in code | 42 | Fix immediately |
| **Environment Issues** | Missing dependencies, config | 98 | Fix env setup |
| **Flaky Tests** | Non-deterministic failures | 85 | Fix async patterns |
| **Obsolete Tests** | Tests for removed features | 32 | Delete or update |

**Categorization Criteria:**

\`\`\`python
# scripts/test-health-check.py categorization
def categorize_failure(test_result):
    error_message = test_result['error']['message']
    
    if 'ModuleNotFoundError' in error_message:
        return 'Environment Issues'
    elif 'TimeoutError' in error_message:
        return 'Flaky Tests'
    elif 'AssertionError' in error_message:
        return 'Real Bugs'
    elif test_result['test_name'] in OBSOLETE_TESTS:
        return 'Obsolete Tests'
    else:
        return 'Unknown'
\`\`\`

---

### Flaky Test Detection

**Definition:** Test that fails 3+ times in last 10 runs (non-deterministic).

**Detection Logic:**

\`\`\`python
# scripts/test-health-check.py flaky detection
def detect_flaky_tests(test_history):
    flaky = []
    for test_name, runs in test_history.items():
        last_10_runs = runs[-10:]
        failures = sum(1 for run in last_10_runs if run['status'] == 'failed')
        
        if failures >= 3:
            flaky.append({
                'test': test_name,
                'failures': failures,
                'failure_rate': failures / 10
            })
    
    return sorted(flaky, key=lambda x: x['failure_rate'], reverse=True)
\`\`\`

**Current Flaky Tests:** 85 identified (Epic 12 Story 12.4 fixing)

---

### Test Metrics Tracking

**Metrics Collected:**

\`\`\`json
{
  "timestamp": "2025-11-11T12:00:00Z",
  "commit_sha": "abc123...",
  "metrics": {
    "total_tests": 2473,
    "passed": 2216,
    "failed": 257,
    "skipped": 0,
    "pass_rate": 89.6,
    "duration": 487.3,
    "coverage": 82.5
  },
  "by_type": {
    "unit": {"total": 1730, "passed": 1625, "pass_rate": 93.93},
    "integration": {"total": 500, "passed": 448, "pass_rate": 89.6},
    "e2e": {"total": 243, "passed": 219, "pass_rate": 90.1}
  }
}
\`\`\`

**Storage:** GitHub Actions artifacts (30-day retention)

---

## Debugging CI Test Failures

### Accessing GitHub Actions Logs

**Step 1: Navigate to Actions Tab**

\`\`\`
Repository → Actions → Select failed workflow run → Click failed job
\`\`\`

**Step 2: Expand Failed Test Step**

\`\`\`
Click "Run integration tests" step → View full logs
\`\`\`

**Step 3: Search for Failure**

\`\`\`
Ctrl+F → Search "FAILED" or "ERROR"
\`\`\`

---

### Downloading Test Artifacts

**Step 1: Navigate to Workflow Summary**

\`\`\`
Actions → Select workflow run → Scroll to "Artifacts" section
\`\`\`

**Step 2: Download Artifacts**

Available artifacts:
- \`test-results.json\` - Machine-readable test results
- \`coverage.xml\` - Coverage report
- \`pytest-report.html\` - Human-readable test report
- \`e2e-artifacts/\` - Screenshots, videos, traces (E2E failures only)

**Step 3: Open Locally**

\`\`\`bash
# Download test-results artifact
unzip test-results.zip

# View HTML report
open pytest-report.html

# View E2E screenshots
open e2e-artifacts/screenshots/test_failure.png
\`\`\`

---

### Reproducing CI Failures Locally

**Step 1: Match CI Environment**

\`\`\`bash
# Use same Python version as CI
pyenv install 3.12
pyenv local 3.12

# Use same dependencies
pip install -r requirements.txt
\`\`\`

**Step 2: Start Docker Services**

\`\`\`bash
# Start postgres + redis (same versions as CI)
docker compose up -d postgres redis

# Wait for health checks
docker compose ps
\`\`\`

**Step 3: Set CI Environment Variables**

\`\`\`bash
# .env.test file (matches CI env vars)
export DATABASE_URL=postgresql+asyncpg://aiagents:password@localhost:5432/ai_agents_test
export REDIS_URL=redis://localhost:6379/1
export CI=true
\`\`\`

**Step 4: Run Same Test Command**

\`\`\`bash
# Exact command from .github/workflows/ci.yml
pytest tests/integration/ -v --cov=src --cov-report=xml --tb=short
\`\`\`

---

### Common CI-Specific Failures

#### Failure: Database Connection Refused

\`\`\`
ERROR: could not connect to server: Connection refused
\`\`\`

**Cause:** Database service not started or unhealthy

**Solution:**

\`\`\`yaml
# .github/workflows/ci.yml - Add health check wait
- name: Wait for database
  run: |
    timeout 60 bash -c 'until pg_isready -h localhost -p 5432; do sleep 1; done'
\`\`\`

---

#### Failure: MCP Test Server Not Starting

\`\`\`
ERROR: Command 'npx' not found
\`\`\`

**Cause:** Node.js not installed or npx not in PATH

**Solution:**

\`\`\`yaml
# .github/workflows/ci.yml - Install Node.js
- name: Setup Node.js
  uses: actions/setup-node@v4
  with:
    node-version: '20'
    cache: 'npm'

- name: Install MCP test server
  run: npm install -g @modelcontextprotocol/server-everything
\`\`\`

---

#### Failure: Port Already in Use

\`\`\`
ERROR: Address already in use: bind() failed (port 8502)
\`\`\`

**Cause:** Previous test run didn't clean up processes

**Solution:**

\`\`\`yaml
# .github/workflows/ci.yml - Kill existing processes
- name: Cleanup ports
  if: always()
  run: |
    lsof -ti:8502 | xargs kill -9 || true
    lsof -ti:5432 | xargs kill -9 || true
\`\`\`

---

#### Failure: Timeout Errors

\`\`\`
ERROR: TimeoutError: Test exceeded 30s timeout
\`\`\`

**Cause:** CI runners slower than local machines

**Solution:**

\`\`\`python
# Increase timeout for CI
import os

TIMEOUT = 60 if os.getenv('CI') else 30

@pytest.mark.anyio
async def test_slow_operation():
    result = await asyncio.wait_for(slow_operation(), timeout=TIMEOUT)
\`\`\`

---

#### Failure: Flaky Tests

\`\`\`
ERROR: Test passed locally but failed in CI
\`\`\`

**Cause:** Async race conditions, timing issues

**Solution:**

\`\`\`python
# ❌ Bad: time.sleep() (flaky)
import time
time.sleep(5)

# ✅ Good: Proper async wait
import asyncio
await asyncio.wait_for(operation(), timeout=30)
\`\`\`

**See:** [Integration Testing Guide - Anti-Pattern #3 (Flaky Tests)](integration-testing-guide.md#anti-pattern-3-flaky-tests-timing-issues)

---

### Updating CI Baseline

**When to Update:**
- ✅ Tests intentionally removed (feature deprecated)
- ✅ Tests added (new features)
- ✅ Pass rate improved (Epic 12 fixes applied)

**How to Update:**

\`\`\`bash
# Update baseline config
vim .github/baseline-config.yaml

# Change:
baseline:
  total_tests: 2473  # Update this
  min_pass_rate: 95.0  # Update this

# Commit changes
git add .github/baseline-config.yaml
git commit -m "Update CI baseline: 2473 tests, 89.6% pass rate"
\`\`\`

**PR Description Template:**

\`\`\`markdown
## CI Baseline Update

**Reason:** Epic 12 Story 12.4 fixed 56 flaky tests

**Changes:**
- Total tests: 2,473 → 2,530 (+57 new tests)
- Pass rate: 84.6% → 89.6% (+5.0%)
- Integration tests: 448/500 passing (89.6%)

**Validation:**
- ✅ All tests passing locally
- ✅ CI green on this PR
- ✅ No regressions detected
\`\`\`

---

## Local Development Testing

### Running Full Test Suite Locally

\`\`\`bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Open coverage report
open htmlcov/index.html
\`\`\`

**Duration:** ~8-10 minutes (full suite)

---

### Running Integration Tests with Docker

\`\`\`bash
# Start Docker services
docker compose up -d postgres redis

# Wait for services
docker compose ps  # Check STATUS=Up (healthy)

# Run integration tests
pytest tests/integration/ -v

# Stop services
docker compose down
\`\`\`

**Duration:** ~5 minutes (integration tests only)

---

### Pre-Commit Testing Strategy

\`\`\`bash
# Quick test before commit (unit tests only)
pytest tests/unit/ -v --maxfail=1

# If passing, run integration tests
pytest tests/integration/ -v --maxfail=1

# If passing, commit
git add .
git commit -m "feat: Add new feature"
\`\`\`

**Recommendation:** Use \`pre-commit\` hooks for automated checks.

---

### Troubleshooting Local Failures

#### Issue: "Module not found"

\`\`\`bash
# Verify virtual environment activated
which python  # Should show .venv/bin/python

# Reinstall dependencies
pip install -r requirements.txt
\`\`\`

#### Issue: "Database connection failed"

\`\`\`bash
# Check Docker services running
docker compose ps

# Restart services
docker compose restart postgres

# Verify connection
psql postgresql://aiagents:password@localhost:5432/ai_agents_test -c "SELECT 1"
\`\`\`

#### Issue: "Port already in use"

\`\`\`bash
# Kill processes using ports
lsof -ti:5432 | xargs kill -9  # PostgreSQL
lsof -ti:6379 | xargs kill -9  # Redis
lsof -ti:8502 | xargs kill -9  # Streamlit
\`\`\`

---

## Summary: CI/CD Best Practices

### ✅ Do's

1. ✅ **Use Docker services** for integration tests
2. ✅ **Cache dependencies** (pip, npm, Playwright)
3. ✅ **Enforce baseline** with ci-baseline-check.py
4. ✅ **Upload artifacts** for debugging (test results, screenshots)
5. ✅ **Fail fast** (--maxfail=5) for quick feedback
6. ✅ **Health checks** for all services (postgres, redis, MCP)
7. ✅ **Clean up processes** after tests (kill stray processes)
8. ✅ **Reproduce locally** before merging

### ❌ Don'ts

1. ❌ **Don't skip tests** in CI (defeats the purpose)
2. ❌ **Don't ignore flaky tests** (fix or mark with \`@pytest.mark.skip\`)
3. ❌ **Don't hard-code secrets** (use GitHub Secrets)
4. ❌ **Don't rely on external APIs** without mocks (use respx)
5. ❌ **Don't commit failing tests** (fix before merge)
6. ❌ **Don't decrease baseline** without justification

---

## See Also

- [Integration Testing Guide](integration-testing-guide.md) - Complete testing guide
- [CI/CD Pipeline Guide](ci-cd-pipeline-guide.md) - Full CI/CD documentation (Story 12.6)
- [Test Examples Catalog](test-examples-catalog.md) - Real test examples
- [Testing Decision Tree](testing-decision-tree.md) - Test type selection guide

---

**Document Version:** 1.0  
**Last Updated:** 2025-11-11  
**Maintained By:** Engineering Team
