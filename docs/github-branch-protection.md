# GitHub Branch Protection Rules Configuration

**Story**: 12.6 - CI/CD Integration Quality Gates (AC8)
**Last Updated**: 2025-11-11
**Purpose**: Enforce quality gates before merging to main branch

---

## Overview

Branch protection rules prevent direct pushes to critical branches and enforce quality gates through required status checks. This configuration ensures that all code merged to `main` has passed CI/CD quality gates, been reviewed, and meets our baseline thresholds.

**Rationale** (from Epic 11 Retrospective):
- Story 11.2.5 required 3 BLOCKED reviews due to incomplete task execution
- Manual quality verification is error-prone and time-consuming
- Automated enforcement prevents quality regressions from reaching production
- Forces shift-left testing and clean-as-you-code practices

---

## Configuration Steps

### 1. Navigate to Branch Protection Settings

1. Go to your repository on GitHub
2. Click **Settings** → **Branches** (left sidebar)
3. Under "Branch protection rules", click **Add rule**
4. Enter branch name pattern: `main`

### 2. Configure Protection Settings

#### ✅ Require a pull request before merging
- **Enabled**: ✓
- **Required approvals**: 1 (adjust based on team size)
- **Dismiss stale pull request approvals when new commits are pushed**: ✓
- **Require review from Code Owners**: ✓ (if using CODEOWNERS file)

**Rationale**: Prevents direct commits to main, enforces peer review process.

---

#### ✅ Require status checks to pass before merging
- **Enabled**: ✓
- **Require branches to be up to date before merging**: ✓

**Required status checks** (must all pass before merge):

| Status Check Name | Source | Purpose | Fail-Fast Benefit |
|------------------|--------|---------|-------------------|
| `lint-and-test / lint-and-test` | `.github/workflows/ci.yml` | Code formatting, linting, type checking, unit tests, baseline enforcement | Catches style violations, type errors, test failures early (5-10 min) |
| `e2e-tests / e2e-tests` | `.github/workflows/ci.yml` | End-to-end UI workflow validation with Playwright | Validates critical user workflows (15-20 min) |
| `docker-build / docker-build` | `.github/workflows/ci.yml` | Docker image build verification | Ensures deployment artifacts are buildable (5-10 min) |

**Rationale**:
- **Require branches up to date**: Prevents integration issues by ensuring PR has latest main changes before merge
- **Status checks**: Automates quality gate enforcement, eliminating manual verification burden
- **Fail-fast ordering**: CI workflow runs lightweight checks (Black, Ruff) before heavyweight checks (tests, E2E) using `needs` keyword

---

#### ✅ Require conversation resolution before merging
- **Enabled**: ✓

**Rationale**: Ensures all review feedback is addressed or explicitly resolved before merge.

---

#### ✅ Require signed commits (optional, recommended for production)
- **Enabled**: (Depends on your security requirements)

**Rationale**: Prevents commit spoofing, ensures traceability. Enable for production environments.

---

#### ✅ Require linear history (optional, depends on team workflow)
- **Enabled**: (Depends on your merge strategy)

**Rationale**:
- **Enable if**: You want a clean commit history without merge commits (use squash or rebase)
- **Disable if**: You prefer preserving individual commit history with merge commits

---

#### ✅ Do not allow bypassing the above settings
- **Enabled**: ✓
- **Applies to administrators**: ✓ (Recommended for strict enforcement)

**Rationale**: Even admins must follow quality gate process. Prevents "emergency" bypasses that introduce technical debt.

---

#### ✅ Allow force pushes (DISABLED)
- **Enabled**: ✗ (Keep disabled)

**Rationale**: Force pushes can overwrite history and bypass protections. Never enable for main branch.

---

#### ✅ Allow deletions (DISABLED)
- **Enabled**: ✗ (Keep disabled)

**Rationale**: Prevents accidental deletion of main branch.

---

## 3. Verify Configuration

After saving the branch protection rules:

1. **Test with a dummy PR**:
   ```bash
   git checkout -b test-branch-protection
   echo "test" >> README.md
   git add README.md
   git commit -m "Test branch protection"
   git push origin test-branch-protection
   ```

2. **Create PR on GitHub** targeting `main`

3. **Verify expected behavior**:
   - ✓ Cannot merge until CI checks pass
   - ✓ Cannot merge until at least 1 approval
   - ✓ Cannot merge if conversations are unresolved
   - ✓ Cannot merge if branch is not up to date with main
   - ✓ Status checks show: `lint-and-test`, `e2e-tests`, `docker-build`

4. **Verify fail-fast behavior**:
   - Introduce a Black formatting error → CI should fail in <2 min (before running tests)
   - Fix formatting, introduce test failure → CI should fail in ~5 min (after linting)
   - Fix tests → CI should complete successfully in ~10-15 min

---

## Troubleshooting

### Status checks not appearing

**Problem**: Required status checks don't show up in branch protection settings.

**Solution**:
1. Status checks only appear after they've run at least once
2. Create a test PR and let CI run completely
3. Return to branch protection settings → status checks should now be visible
4. Search for and select: `lint-and-test`, `e2e-tests`, `docker-build`

---

### "Branch is out of date" preventing merge

**Problem**: PR shows as passing but merge button is disabled with message "Branch is out of date".

**Solution**:
```bash
# Update your branch with latest main
git checkout your-branch
git fetch origin
git merge origin/main

# Or use rebase for cleaner history
git rebase origin/main

# Push updated branch
git push origin your-branch --force-with-lease
```

**Rationale**: This is expected behavior when "Require branches to be up to date" is enabled. It prevents integration issues.

---

### Status check stuck on "pending"

**Problem**: CI check shows "pending" or "queued" for extended period.

**Solution**:
1. Check GitHub Actions tab for workflow status
2. If workflow failed to start, re-run by pushing an empty commit:
   ```bash
   git commit --allow-empty -m "Trigger CI"
   git push
   ```
3. If workflow is stuck, cancel and re-run from GitHub Actions UI

---

### Admin needs to bypass protection temporarily

**Problem**: Emergency hotfix needed, but status checks are failing on unrelated changes.

**Solution** (Use sparingly):
1. If "Do not allow bypassing" is **disabled for admins**:
   - Admin can check "Use your administrator privileges to merge this pull request"
2. If "Do not allow bypassing" is **enabled**:
   - Temporarily disable the protection rule
   - Merge the hotfix
   - Re-enable protection immediately
   - Create follow-up ticket to fix quality gate failures

**Best Practice**: Avoid bypassing. If bypass is needed, document reason in PR description and create follow-up issue to fix root cause.

---

## Quality Gate Philosophy

Our branch protection configuration enforces a **shift-left, fail-fast** approach:

### Shift-Left Testing
- Quality checks run **before** code review, not after
- Developers see failures immediately upon pushing
- Reduces back-and-forth review cycles

### Fail-Fast Execution
- Lightweight checks (Black, Ruff, Mypy) run first (1-2 min)
- Medium checks (unit tests, security scans) run next (5-10 min)
- Heavyweight checks (E2E, smoke tests) run last (15-20 min)
- Pipeline stops at first failure → fast feedback loop

### Progressive Quality Gates
- **CRITICAL thresholds** (block merge):
  - Integration test pass rate ≥85%
  - Code coverage ≥70%
  - Zero high/medium Bandit findings
  - Zero Black/Ruff/Mypy violations
- **WARNING thresholds** (allow merge with annotation):
  - Integration test pass rate 85-90%
  - Code coverage 70-80%

See `scripts/ci-baseline-config.yaml` for full threshold definitions.

---

## Integration with PR Template

Our PR template (`.github/PULL_REQUEST_TEMPLATE.md`) includes an 18-item **Pre-Merge Integration Checklist** that aligns with branch protection requirements:

```markdown
### Pre-Merge Integration Checklist (Story 12.6)
- [ ] All acceptance criteria (ACs) fully implemented
- [ ] Unit tests added/updated for new code (target coverage: 80%)
- [ ] Integration tests pass locally
- [ ] Black formatting applied (`black src/ tests/`)
- [ ] Ruff linting passed (`ruff check src/ tests/`)
- [ ] Type checking clean (`mypy src/ --strict`)
- [ ] Security scan passed (`bandit -r src/`)
- [ ] Baseline thresholds verified (`python scripts/ci-baseline-check.py`)
...
```

**Workflow**:
1. Developer completes checklist items locally **before** creating PR
2. CI runs same checks automatically when PR is created
3. Branch protection prevents merge until all checks pass
4. Reviewer verifies checklist items are checked off

This creates a **double validation** layer: developer self-verification + automated enforcement.

---

## Monitoring and Metrics

Track branch protection effectiveness via:

### GitHub Insights
- **Settings → Insights → Pulse**: View PR merge rate, time-to-merge
- **Settings → Insights → Code frequency**: Track commit patterns
- Filter by "Merged Pull Requests" to see quality gate pass rate

### CI/CD Metrics
Our baseline enforcement script (`scripts/ci-baseline-check.py`) generates metrics:

```bash
# Run locally to check current quality metrics
python scripts/ci-baseline-check.py \
  --config scripts/ci-baseline-config.yaml \
  --results pytest-results.json
```

**Tracked metrics** (from `ci-baseline-config.yaml`):
- Test pass rates by category (unit, integration, E2E, smoke)
- Code coverage percentage
- Code quality violations (Black, Ruff, Mypy, Bandit)
- Baseline threshold compliance (CRITICAL vs WARNING)

### Prometheus Alerts (AC5 - deferred to Story 12.6A)
Integration with Prometheus/Grafana for:
- CI failure rate alerts (>20% failures in 1 hour)
- Baseline threshold violations
- E2E test stability tracking

---

## Related Documentation

- **[CI/CD Pipeline Guide](./ci-cd-pipeline-guide.md)**: Complete pipeline architecture, troubleshooting, developer workflow
- **[PR Template](../.github/PULL_REQUEST_TEMPLATE.md)**: Pre-merge integration checklist
- **[Baseline Configuration](../scripts/ci-baseline-config.yaml)**: Quality gate thresholds
- **[Admin UI Guide](./admin-ui-guide.md)**: Agent management and testing workflows

---

## References

- **GitHub Docs**: [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- **Context7 Research**: `/websites/github_en_actions` (2025 best practices)
- **Epic 11 Retrospective**: [docs/retrospectives/epic-11-retro-2025-11-10.md](./retrospectives/epic-11-retro-2025-11-10.md)
- **Story 12.6**: [.bmad-ephemeral/stories/12-6-cicd-integration-quality-gates.md](../.bmad-ephemeral/stories/12-6-cicd-integration-quality-gates.md)

---

## Revision History

| Date | Change | Author |
|------|--------|--------|
| 2025-11-11 | Initial documentation (Story 12.6 - AC8) | Amelia (Dev Agent) |

---

**Questions?** See [CI/CD Pipeline Guide](./ci-cd-pipeline-guide.md) troubleshooting section or create an issue.
