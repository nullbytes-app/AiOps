# CI/CD Pipeline Guide

**Story 12.6: Integration Quality Gates**
**Last Updated:** 2025-11-11

This guide provides comprehensive documentation for the AI Agents CI/CD pipeline, quality gate enforcement, and developer workflows.

---

## Table of Contents

1. [Pipeline Architecture Overview](#pipeline-architecture-overview)
2. [Quality Gate Definitions](#quality-gate-definitions)
3. [Job Dependency Graph](#job-dependency-graph)
4. [Branch Protection Rules](#branch-protection-rules)
5. [Developer Workflow](#developer-workflow)
6. [Troubleshooting Guide](#troubleshooting-guide)
7. [Smoke Tests](#smoke-tests)
8. [Monitoring Alerts](#monitoring-alerts)
9. [Best Practices](#best-practices)

---

## Pipeline Architecture Overview

### Design Philosophy (2025 Best Practices)

The AI Agents CI/CD pipeline follows modern quality gate best practices:

- **Shift-Left Testing:** Move quality checks earlier in development cycle (pre-merge vs post-merge)
- **Progressive Quality Gates:** Lightweight checks first (lint, format), heavyweight after (E2E, smoke)
- **Fail Fast:** Block merge immediately on critical failures (`continue-on-error: false`)
- **Parallel Execution:** Run independent checks in parallel for speed
- **Clean as You Code:** Focus quality gates on new/modified code (SonarQube standard)

### Pipeline Stages

```
┌─────────────────────────────────────────────────────────────────────┐
│ GitHub Pull Request Created                                         │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Job 1: lint-and-test (runs first)                                   │
│ - Black formatting check                                            │
│ - Ruff linting check                                                │
│ - Mypy type checking                                                │
│ - Bandit security scan                                              │
│ - Unit tests + coverage (≥80%)                                      │
│ - Integration tests                                                 │
│ - Security tests                                                    │
│ - Dependency scans (safety, pip-audit)                              │
│ - Baseline threshold enforcement (Story 12.6)                       │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ (pass) │ (fail → block merge)
                                ▼
                ┌───────────────────────────────┐
                │ Parallel execution            │
                ├───────────────┬───────────────┤
                ▼               ▼
┌───────────────────────┐ ┌────────────────────────┐
│ Job 2: e2e-tests      │ │ Job 3: docker-build    │
│ - 3 UI workflows      │ │ - Build API image      │
│ (Story 12.5)          │ │ - Build Worker image   │
└───────┬───────────────┘ └────────┬───────────────┘
        │ (pass)                   │ (pass)
        │                          │
        │ (fail → block merge)     │ (fail → block merge)
        └──────────┬───────────────┘
                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Merge Allowed (all quality gates passed)                            │
└─────────────────────────────────────────────────────────────────────┘
```

### Workflow File Location

- **Path:** `.github/workflows/ci.yml`
- **Triggers:** Push to `main`, Pull requests to `main`
- **Total Execution Time:** <20 minutes (Story 12.6 constraint C2)

---

## Quality Gate Definitions

### 1. Code Quality Gates (lint-and-test job)

#### Black Formatting Check
- **Purpose:** Enforce consistent Python code formatting (PEP8-compliant)
- **Configuration:** `pyproject.toml` → `[tool.black]` (line-length=100)
- **Pass Criteria:** 0 formatting violations
- **Failure Action:** Block merge
- **Remediation:** Run `black src/ tests/` locally before pushing

#### Ruff Linting Check
- **Purpose:** Fast linter checking code quality, security patterns, unused imports
- **Configuration:** `pyproject.toml` → `[tool.ruff]` (select: E, F, I, N, W)
- **Pass Criteria:** 0 critical/high violations (warnings allowed)
- **Failure Action:** Block merge
- **Remediation:**
  - Auto-fix: `ruff check --fix src/`
  - Manual fix: Review error messages in CI logs

#### Mypy Type Checking
- **Purpose:** Static type checking to catch type errors before runtime
- **Configuration:** `pyproject.toml` → `[tool.mypy]` (disallow_untyped_defs=true)
- **Pass Criteria:** 0 type errors
- **Failure Action:** Block merge
- **Remediation:** Add type hints to function signatures, use `mypy src/ --ignore-missing-imports` locally

#### Bandit Security Scan
- **Purpose:** Static analysis security linter for Python (OWASP best practices)
- **Configuration:** `pyproject.toml` → `[tool.bandit]`
- **Pass Criteria:** 0 high/medium severity issues
- **Failure Action:** Block merge
- **Remediation:** Review Bandit output, fix security issues, add `# nosec` with justification for false positives

### 2. Test Quality Gates (lint-and-test job)

#### Unit Tests with Coverage
- **Purpose:** Validate code functionality and ensure adequate test coverage
- **Pass Criteria:**
  - Unit test pass rate ≥95% (Story 12.6 AC7)
  - Code coverage ≥80% (tech spec requirement)
- **Failure Action:** Block merge
- **Execution Time:** <2 minutes
- **Remediation:** Fix failing tests, add tests for uncovered code paths

#### Integration Tests
- **Purpose:** Validate API/service integration with real dependencies (Docker services)
- **Pass Criteria:** Integration test pass rate ≥90% (Story 12.6 AC7)
- **Failure Action:** Warning if 85-90%, block if <85%
- **Execution Time:** <10 minutes
- **Remediation:** Review integration test logs, verify Docker services healthy

#### E2E UI Workflow Tests (e2e-tests job)
- **Purpose:** Validate critical UI workflows with Playwright (Story 12.5)
- **Pass Criteria:** 100% pass rate (all 3 workflows must pass)
- **Failure Action:** Block merge
- **Workflows Tested:**
  1. MCP Server Registration and Discovery
  2. Agent Tool Assignment
  3. Agent Execution with Tools
- **Execution Time:** <5 minutes
- **Remediation:** Review Playwright screenshots/videos/traces in CI artifacts

#### Security Tests
- **Purpose:** Automated security testing (OWASP Top 10, tenant isolation)
- **Pass Criteria:** 100% pass rate (any failure blocks merge)
- **Failure Action:** Block merge (critical threshold)
- **Remediation:** Review security test logs, fix vulnerabilities before merge

#### Smoke Tests (Story 12.6)
- **Purpose:** Fast validation of critical business workflows (API + DB + Workers)
- **Pass Criteria:** 100% pass rate (Story 12.6 AC7)
- **Failure Action:** Block merge
- **Workflows Tested:**
  1. Agent Creation Workflow
  2. MCP Server Workflow (placeholder)
  3. Webhook Workflow (placeholder)
  4. Budget Tracking Workflow (placeholder)
- **Execution Time:** <2 minutes total
- **Remediation:** Review smoke test output, verify end-to-end system health

### 3. Security Vulnerability Scans (lint-and-test job)

#### Safety Dependency Scan
- **Purpose:** Identify known vulnerabilities in Python dependencies
- **Pass Criteria:** 0 critical/high CVEs
- **Failure Action:** Block merge
- **Database:** Python Packaging Advisory Database
- **Remediation:** Update vulnerable dependencies, review safety output for patched versions

#### Pip-Audit Supply Chain Scan
- **Purpose:** Additional supply chain security scanning (OSV database)
- **Pass Criteria:** 0 critical/high CVEs
- **Failure Action:** Block merge
- **Remediation:** Update vulnerable dependencies, review pip-audit output

### 4. Build Quality Gates (docker-build job)

#### Docker Image Builds
- **Purpose:** Validate Dockerfile syntax and ensure images build successfully
- **Pass Criteria:**
  - API image builds without errors
  - Worker image builds without errors
- **Failure Action:** Block merge
- **Images Built:**
  - `ai-agents-api` (backend.dockerfile)
  - `ai-agents-worker` (celeryworker.dockerfile)
- **Remediation:** Review Docker build logs, fix Dockerfile syntax errors

### 5. Baseline Threshold Enforcement (Story 12.6)

#### Configurable Quality Gate Thresholds
- **Purpose:** Progressive quality improvement with configurable thresholds
- **Configuration:** `scripts/ci-baseline-config.yaml`
- **Implementation:** `scripts/ci-baseline-check.py`
- **Enforcement Logic:**
  - **CRITICAL thresholds:** Block merge (exit code 1)
  - **WARNING thresholds:** Merge allowed with annotation (exit code 0)
  - **PASS:** All thresholds met

#### Current Thresholds (Story 12.6 AC7)

| Metric | Critical Min | Warning Min | Description |
|--------|--------------|-------------|-------------|
| **Unit Tests** | 90% | 95% | Block if <90%, warn if 90-95% |
| **Integration Tests** | 85% | 90% | Block if <85%, warn if 85-90% |
| **E2E Tests** | 100% | 100% | Block if <100% (all workflows must pass) |
| **Smoke Tests** | 100% | 100% | Block if <100% (critical workflows must work) |
| **Security Tests** | 100% | 100% | Block on any failure (strict enforcement) |
| **Overall Pass Rate** | 85% | 92% | Block if <85%, warn if 85-92% (target: 8% improvement) |
| **Code Coverage** | 70% | 80% | Block if <70%, warn if 70-80% |
| **Black Violations** | 0 | 0 | Block on any violation |
| **Ruff Critical** | 0 | 0 | Block on critical/high issues |
| **Mypy Errors** | 0 | 0 | Block on any type error |
| **Bandit High** | 0 | 0 | Block on high severity |
| **Bandit Medium** | 0 | 0 | Block on medium severity |
| **Safety Critical CVEs** | 0 | 0 | Block on critical vulnerabilities |
| **Safety High CVEs** | 0 | 0 | Block on high vulnerabilities |
| **Test Count Decrease** | -10 | N/A | Block if >10 tests deleted |

---

## Job Dependency Graph

The pipeline uses GitHub Actions `needs` keyword for job dependencies (2025 best practice):

```yaml
jobs:
  lint-and-test:
    # Runs first (no dependencies)
    # Contains all quality gates

  e2e-tests:
    needs: lint-and-test  # Runs after lint-and-test passes
    # UI workflow validation

  docker-build:
    needs: lint-and-test  # Runs after lint-and-test passes
    # Can run in parallel with e2e-tests
```

**Execution Flow:**
1. `lint-and-test` runs first (all quality gates)
2. If `lint-and-test` passes → `e2e-tests` and `docker-build` run in parallel
3. If any job fails → merge blocked

**Performance Optimization:**
- Sequential: 30 minutes (if jobs ran one after another)
- Parallel: 15 minutes (with `needs` keyword optimization)

---

## Branch Protection Rules

See [Branch Protection Configuration Guide](./github-branch-protection.md) for detailed setup instructions.

**Quick Summary:**
- Required status checks: `lint-and-test`, `e2e-tests`, `docker-build`
- Require branches to be up-to-date before merging: ✅ Enabled
- Require conversation resolution before merging: ✅ Enabled
- Dismiss stale PR approvals when new commits pushed: ✅ Enabled
- Allow force pushes: ❌ Disabled
- Allow deletions: ❌ Disabled

---

## Developer Workflow

### Before Creating a Pull Request

**Run all quality checks locally to catch issues early:**

```bash
# 1. Format code
black src/ tests/

# 2. Check linting
ruff check src/ tests/

# 3. Type check
mypy src/ --ignore-missing-imports

# 4. Security scan
bandit -r src/ -ll

# 5. Run tests with coverage
pytest tests/ --cov=src --cov-report=term --cov-fail-under=80

# 6. Run specific test suites
pytest tests/unit/ -v         # Unit tests only
pytest tests/integration/ -v  # Integration tests only
pytest tests/e2e/ -v          # E2E tests only (requires Streamlit app running)
pytest tests/smoke/ -v        # Smoke tests only

# 7. Build Docker images
docker build -f docker/backend.dockerfile -t ai-agents-api:test .
docker build -f docker/celeryworker.dockerfile -t ai-agents-worker:test .
```

### Creating a Pull Request

1. **Use the PR Template:** GitHub auto-populates `.github/PULL_REQUEST_TEMPLATE.md`
2. **Complete the Pre-Merge Integration Checklist:** Verify all 18 items
3. **Self-Review:** Use Epic 9 Pre-Review Self-Check Checklist
4. **Verify Story Completion:**
   - All acceptance criteria fully met (no "partial" ACs)
   - All tasks verified (not marked complete without implementation)
   - Manual smoke test of critical workflows performed

### Handling CI Failures

#### If CI Fails on Your PR:

1. **Click on the failed job** in GitHub PR checks
2. **Review the error logs** to identify the issue
3. **Apply the remediation** from the table below
4. **Push the fix** to your PR branch
5. **CI will automatically re-run**

#### Common Failures and Fixes:

| Failure | Cause | Remediation |
|---------|-------|-------------|
| **Black formatting** | Code not formatted | Run `black src/ tests/` and push |
| **Ruff linting** | Code quality issues | Review errors, run `ruff check --fix src/` or fix manually |
| **Mypy type errors** | Missing type hints | Add type hints to function signatures |
| **Bandit security** | Security vulnerabilities | Review Bandit output, fix issues, justify false positives with `# nosec` |
| **Unit tests** | Test failures | Run `pytest tests/unit/ -v`, fix failing tests |
| **Integration tests** | Test failures or Docker issues | Run `pytest tests/integration/ -v`, verify Docker services healthy |
| **E2E tests** | UI workflow failures | Review Playwright artifacts (screenshots/videos/traces) in CI |
| **Security tests** | Security vulnerabilities | Fix security issues in code, update vulnerable dependencies |
| **Coverage <80%** | Insufficient test coverage | Add tests for uncovered code paths |
| **Baseline thresholds** | Pass rate below threshold | Review pytest JSON report, fix failing tests |
| **Docker build** | Dockerfile syntax errors | Review Docker build logs, fix Dockerfile |
| **Dependency scans** | Vulnerable dependencies | Update dependencies to patched versions |

### Requesting Code Review

1. **Verify PR Template Checklist:** All items marked complete
2. **Verify CI Passes:** All checks green
3. **Assign Reviewer:** Tag relevant team member
4. **Respond to Feedback:** Address reviewer comments, push updates
5. **Re-request Review:** After addressing all feedback

---

## Troubleshooting Guide

### Issue: Black Formatting Failures

**Symptoms:** CI fails with "Files would be reformatted by Black"

**Solution:**
```bash
# Auto-format all Python files
black src/ tests/

# Verify formatting
black --check src/ tests/

# Push formatted code
git add .
git commit -m "Fix: Apply Black formatting"
git push
```

### Issue: Ruff Linting Failures

**Symptoms:** CI fails with Ruff errors (unused imports, line too long, etc.)

**Solution:**
```bash
# Auto-fix some issues
ruff check --fix src/ tests/

# Review remaining errors
ruff check src/ tests/

# Fix manually or adjust pyproject.toml if needed
# Push fixes
git add .
git commit -m "Fix: Resolve Ruff linting issues"
git push
```

### Issue: Mypy Type Errors

**Symptoms:** CI fails with "error: Function is missing a type annotation"

**Solution:**
```bash
# Run mypy locally
mypy src/ --ignore-missing-imports

# Add type hints to functions
# Example:
def my_function(param: str) -> int:
    return len(param)

# Push fixes
git add .
git commit -m "Fix: Add type hints for Mypy compliance"
git push
```

### Issue: Test Failures

**Symptoms:** CI shows failing tests

**Solution:**
```bash
# Run tests locally to reproduce
pytest tests/ -v --tb=short

# Run specific test file
pytest tests/path/to/test_file.py -v

# Debug with print statements or breakpoints
pytest tests/path/to/test_file.py -v -s

# Fix test or implementation code
# Push fixes
git add .
git commit -m "Fix: Resolve test failures"
git push
```

### Issue: Baseline Threshold Violations

**Symptoms:** CI fails with "CRITICAL: Overall pass rate below threshold"

**Solution:**
```bash
# Run baseline check locally
python scripts/ci-baseline-check.py \
  --config scripts/ci-baseline-config.yaml \
  --results pytest-results.json

# Review threshold violations
# Fix failing tests to improve pass rate
# Verify pass rate meets thresholds
pytest tests/ --json-report --json-report-file=pytest-results.json

# Push fixes
git add .
git commit -m "Fix: Improve test pass rate to meet baseline thresholds"
git push
```

### Issue: Docker Build Failures

**Symptoms:** CI fails building Docker images

**Solution:**
```bash
# Build API image locally
docker build -f docker/backend.dockerfile -t ai-agents-api:test .

# Build Worker image locally
docker build -f docker/celeryworker.dockerfile -t ai-agents-worker:test .

# Review build logs for errors
# Common issues:
# - Missing dependencies in requirements.txt
# - Incorrect file paths in COPY commands
# - Python syntax errors preventing build

# Fix Dockerfile or dependencies
# Push fixes
git add .
git commit -m "Fix: Resolve Docker build errors"
git push
```

---

## Smoke Tests

### Purpose

Smoke tests validate critical business workflows end-to-end (API + DB + Workers) to catch integration issues that unit/integration tests might miss.

### Distinction from E2E Tests

| Aspect | Smoke Tests | E2E Tests (Story 12.5) |
|--------|-------------|------------------------|
| **Purpose** | Business logic validation | UI integration validation |
| **Scope** | API + DB + Workers | Browser + UI |
| **Tool** | pytest + fixtures | Playwright |
| **Execution Time** | <2 minutes | <5 minutes |
| **Example** | Create agent via API → Execute via Celery → Verify result in DB | Navigate to Agent Management → Fill form → Verify UI update |

### Smoke Test Workflows (Story 12.6 AC3)

1. **Agent Creation Workflow** (`tests/smoke/test_agent_creation_workflow.py`)
   - Create agent → Assign tool → Test execution → Verify result
   - Status: ✅ Implemented

2. **MCP Server Workflow** (`tests/smoke/test_mcp_server_workflow.py`)
   - Register MCP server → Discover tools → Assign to agent
   - Status: ⚠️ Placeholder (implement in follow-up if needed)

3. **Webhook Workflow** (`tests/smoke/test_webhook_workflow.py`)
   - Configure webhook → Receive payload → Trigger agent
   - Status: ⚠️ Placeholder (implement in follow-up if needed)

4. **Budget Tracking Workflow** (`tests/smoke/test_budget_tracking_workflow.py`)
   - Create tenant → Set budget → Execute agent → Verify cost tracking
   - Status: ⚠️ Placeholder (implement in follow-up if needed)

### Running Smoke Tests

```bash
# Run all smoke tests
pytest tests/smoke/ -v -m smoke

# Run specific smoke test
pytest tests/smoke/test_agent_creation_workflow.py -v

# Run smoke tests with coverage
pytest tests/smoke/ -v -m smoke --cov=src
```

---

## Monitoring Alerts

### Alert Configuration (Story 12.6 AC4)

**Threshold Monitoring:**
- **Tool:** `scripts/ci-baseline-check.py`
- **Configuration:** `scripts/ci-baseline-config.yaml`
- **Execution:** Runs automatically in `lint-and-test` job (Step 16)

**Alert Behavior:**

| Condition | Action | Exit Code | PR Status |
|-----------|--------|-----------|-----------|
| All thresholds met | ✅ PASS | 0 | Merge allowed |
| WARNING threshold breached | ⚠️ WARNING | 0 | Merge allowed (investigation recommended) |
| CRITICAL threshold breached | ❌ FAIL | 1 | Merge blocked |

**Alert Content:**
- Test pass rate (current vs baseline)
- Number of failing tests
- List of failing test names
- Recent pass rate trend (via test-baseline.json)
- Link to pytest JSON report artifact

**Alert Recipients:**
- Visible in GitHub Actions workflow summary
- Visible in PR checks (red X or yellow warning)
- Viewable in CI logs

---

## Best Practices

### 1. Shift-Left Testing
- **Run quality checks locally before pushing**
- **Catch issues early** (faster feedback, lower cost to fix)
- **Use pre-commit hooks** (optional but recommended)

### 2. Clean as You Code
- **Focus on new/modified code** (don't fail on existing issues)
- **Progressive improvement** (baseline thresholds allow gradual improvement)
- **Prevent regressions** (critical thresholds block new issues)

### 3. Fail Fast
- **All quality gates use `continue-on-error: false`**
- **Immediate feedback** on critical failures
- **Prevents cascading failures** (don't run E2E if unit tests fail)

### 4. Parallel Execution
- **Independent jobs run in parallel** (e2e-tests and docker-build)
- **Reduces total CI time** (15 min vs 30 min sequential)
- **Uses `needs` keyword** for job dependencies

### 5. Clear Failure Messages
- **All quality gate failures include remediation guidance**
- **PR template provides troubleshooting guide**
- **CI logs include actionable error messages**

### 6. Security First
- **Security tests block merge** (100% pass rate required)
- **Dependency scans block merge** on critical/high CVEs
- **No bypass of branch protection rules**

### 7. Documentation Complete
- **All quality gates documented** with purpose and remediation
- **PR template guides developers** through checklist
- **Troubleshooting guide covers common failures**

---

## Additional Resources

- **PR Template:** `.github/PULL_REQUEST_TEMPLATE.md`
- **Branch Protection Guide:** `docs/github-branch-protection.md`
- **Testing Guide:** `tests/README.md`
- **CI/CD Workflow:** `.github/workflows/ci.yml`
- **Baseline Config:** `scripts/ci-baseline-config.yaml`
- **Baseline Enforcement:** `scripts/ci-baseline-check.py`
- **Test Health Monitoring:** `scripts/test-health-check.py`

---

## Feedback and Improvements

This guide is a living document. If you encounter issues not covered here or have suggestions for improvement:

1. Create a GitHub issue with the `documentation` label
2. Propose changes in a PR with updates to this guide
3. Discuss in team retrospectives

**Last Updated:** 2025-11-11 (Story 12.6)
