# Pull Request

## Summary

**Story ID:** <!-- e.g., Story 12.6 -->

**Brief Description:**
<!-- 1-2 sentences describing what this PR changes -->

**Related Links:**
- Story File: <!-- Link to story markdown file in docs/stories/ or .bmad-ephemeral/stories/ -->
- Tech Spec: <!-- Link to epic tech spec if applicable -->
- Issue: <!-- Link to GitHub issue if applicable -->

---

## Pre-Merge Integration Checklist

Please verify ALL items below before requesting code review. This checklist enforces Epic 11 retrospective insights to prevent quality issues discovered during code review.

### ✅ Story Completion
- [ ] **All acceptance criteria (ACs) implemented and verified**
  - ⚠️ NO partial ACs allowed (must fully meet or descope to new story)
  - Link to self-review using [Pre-Review Self-Check Checklist](#pre-review-self-check)
- [ ] **All tasks/subtasks completed and verified**
  - ⚠️ Tasks must NOT be marked complete without actual verification
  - Spot check recommended: Pick 3 random tasks and verify implementation

### 🧪 Testing
- [ ] **Unit tests written and passing** (pass rate ≥95%)
- [ ] **Integration tests written/updated and passing** (pass rate ≥90%)
- [ ] **E2E tests passing if UI changes made** (pass rate 100%)
- [ ] **Code coverage ≥80% for new/modified code**
- [ ] **Security tests passing** (100% pass rate required)

### 🔍 Code Quality
- [ ] **Black formatting applied** (`black src/ tests/`)
- [ ] **Ruff linting passed** (`ruff check src/ tests/`)
- [ ] **Mypy type hints added** (`mypy src/ --ignore-missing-imports`)
- [ ] **Bandit security scan passed** (`bandit -r src/ -ll`)
- [ ] **No hardcoded secrets or credentials in code**

### 📚 Documentation
- [ ] **Documentation updated** (README, docstrings, tests/README.md)
- [ ] **Database migrations tested** (if schema changes made)
- [ ] **Manual smoke test performed locally** (critical workflows verified)

### 🐳 Build & Deploy
- [ ] **Docker images build successfully**
  - API image: `docker build -f docker/backend.dockerfile .`
  - Worker image: `docker build -f docker/celeryworker.dockerfile .`

---

## Testing Notes

**Test Pass Rate Metrics:**
- Unit tests: <!-- e.g., 285/287 passing (99.3%) -->
- Integration tests: <!-- e.g., 45/49 passing (91.8%) -->
- E2E tests: <!-- e.g., 3/3 passing (100%) -->
- Overall: <!-- e.g., 333/339 passing (98.2%) -->

**New Tests Added:**
- <!-- Count of new test files/functions -->

**Modified Tests:**
- <!-- Count of modified test files/functions -->

**Coverage Change:**
- Before: <!-- e.g., 82% -->
- After: <!-- e.g., 84% (+2%) -->

---

## Code Review Notes

### Pre-Review Self-Check
- [ ] **Self-review completed** using [Pre-Review Self-Check Checklist](#pre-review-self-check)
- [ ] **Story completion DoD verified** (all acceptance criteria fully met)

### Notable Implementation Decisions
<!-- Explain any significant technical choices, architectural patterns, or trade-offs -->

### Known Limitations or Follow-up Items
<!-- List any deferred work, known issues, or future improvements needed -->

---

## Pre-Review Self-Check

**Epic 9 Action Item #1: Pre-Review Self-Check Checklist**
- Run all quality checks locally before creating PR
- Verify all ACs met (no "partial" compliance)
- Verify all tasks marked complete have been implemented
- Review code for security issues, hardcoded secrets, TODO comments
- Test critical user workflows manually

**Story Completion Definition of Done (DoD):**
1. All acceptance criteria fully satisfied (100%, not partial)
2. All tasks/subtasks checked and verified
3. All tests passing (unit ≥95%, integration ≥90%, E2E 100%)
4. Code coverage ≥80%
5. Black formatting + Ruff linting + Mypy type checking passed
6. Bandit security scan passed (0 high/medium issues)
7. Documentation complete (README, docstrings, inline comments)
8. Database migrations tested (if applicable)
9. Docker images build successfully
10. Manual smoke test of critical workflows performed

**Local Quality Check Commands:**
```bash
# Format code
black src/ tests/

# Check linting
ruff check src/ tests/

# Type check
mypy src/ --ignore-missing-imports

# Security scan
bandit -r src/ -ll

# Run tests with coverage
pytest tests/ --cov=src --cov-report=term --cov-fail-under=80

# Run specific test suites
pytest tests/unit/ -v         # Unit tests only
pytest tests/integration/ -v  # Integration tests only
pytest tests/e2e/ -v          # E2E tests only
pytest tests/smoke/ -v        # Smoke tests only (Story 12.6+)

# Build Docker images
docker build -f docker/backend.dockerfile -t ai-agents-api:test .
docker build -f docker/celeryworker.dockerfile -t ai-agents-worker:test .
```

---

## Epic 11 Retrospective Enforcement

**Critical Insights from Epic 11 Retrospective (2025-11-10):**

1. **Task Completion Discipline**: Story 11.2.5 required 3 BLOCKED reviews due to tasks marked complete without implementation verification. **Action**: All tasks must be verified before marking complete.

2. **UI Integration Review**: Story 11.2.5 had 2 CRITICAL bugs (UI integration never done) discovered only during code review. **Action**: E2E test pass rate 100% enforced to prevent UI regressions.

3. **Partial AC Implementation**: Story 11.1.7 had AC7 "PARTIALLY COMPLIANT" which normalized "good enough" culture. **Action**: All ACs must be fully met (no "partial" ACs allowed - descope or defer to new story).

**Story 12.6 Philosophy:** Automate quality checks pre-merge so issues are caught by CI, not by reviewers. Branch protection + quality gates + this PR template = systematic quality improvement.

---

**Reviewer Guidance:**
- Focus on architecture, business logic correctness, security implications
- Quality gates have already validated formatting, linting, type safety, test coverage
- Verify acceptance criteria are fully met (not partially compliant)
- Verify tasks marked complete have been actually implemented
- Check for proper error handling, edge cases, and test coverage
