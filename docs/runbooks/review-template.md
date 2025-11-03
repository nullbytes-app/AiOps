# Runbook Quarterly Review Checklist

**Review Date:** [YYYY-MM-DD]
**Reviewer Name:** [Name]
**Runbook(s) Reviewed:** [List runbooks]
**Review Duration:** [Time spent]

---

## Pre-Review Context

**Last Review Date:** [Previous review date or "Initial creation"]
**Changes Since Last Review:** [Any deployments, code changes, or incidents since last review]
**Trigger for This Review:** [ ] Quarterly schedule [ ] After major incident [ ] After deployment [ ] Team feedback

---

## Command Validation Checklist

For each command listed in the runbook, verify it still works:

- [ ] **Command 1:** [Command]
  - [ ] Executes without syntax errors
  - [ ] Returns expected output
  - [ ] Notes: [Any variations in output?]

- [ ] **Command 2:** [Command]
  - [ ] Executes without syntax errors
  - [ ] Returns expected output
  - [ ] Notes: [Any variations in output?]

- [ ] **Additional Commands:**
  - [ ] All diagnostic commands execute successfully
  - [ ] All resolution procedures work as documented
  - [ ] Notes: [List any failed commands]

---

## Technical Accuracy Review

### Symptoms Section
- [ ] Observable indicators match current system behavior
- [ ] Alerts/metrics mentioned are still valid
- [ ] Any new symptoms discovered not in runbook?
  - [ ] Yes - Action: [Document new symptom]
  - [ ] No

### Diagnosis Section
- [ ] All commands execute and work as documented
- [ ] Query outputs match expected examples
- [ ] Kubernetes/Docker commands still valid for current infrastructure version
- [ ] Database queries still applicable
- [ ] Notes: [Any commands that need updates?]

### Resolution Section
- [ ] All remediation procedures still apply
- [ ] Configuration paths/filenames still correct
- [ ] Any deprecated procedures that should be removed?
  - [ ] Yes - Action: [Remove/update procedure]
  - [ ] No
- [ ] Are there new resolution options since last review?
  - [ ] Yes - Action: [Add new procedures]
  - [ ] No

### Escalation Section
- [ ] On-call contact information current
- [ ] SLA thresholds still appropriate
- [ ] Escalation paths still valid
- [ ] Notes: [Any changes needed?]

---

## External Links and References

Verify all links in the runbook still work:

- [ ] Internal documentation links (docs/operations/*, docs/runbooks/*)
- [ ] Jaeger UI links correct
- [ ] Prometheus dashboard links correct
- [ ] External references (Grafana, GitHub, vendor docs) still active
- [ ] Notes: [Any broken links found?]

---

## Screenshots and Examples

If runbook includes screenshots or example outputs:

- [ ] Screenshots are current and match actual UI
- [ ] Example command outputs match current system behavior
- [ ] UI elements haven't changed significantly
- [ ] Notes: [Need to update screenshots?]

---

## New Failure Modes

Based on incidents/operations since last review, are there new failure scenarios not covered?

- [ ] No new failure modes discovered
- [ ] Yes - New failure modes found:
  - [ ] **Failure Mode:** [Description]
    - [ ] Action: Add to runbook
    - [ ] Action: Create new runbook
    - [ ] Notes: [Details]
  - [ ] **Failure Mode:** [Description]
    - [ ] Action: Add to runbook
    - [ ] Action: Create new runbook
    - [ ] Notes: [Details]

---

## Clarity and Usability

If possible, have a new team member (or colleague unfamiliar with this specific runbook) review:

- [ ] All instructions are clear and unambiguous
- [ ] Runbook can be followed without external assistance
- [ ] Expected outcomes are clearly stated
- [ ] Error cases and troubleshooting guidance provided
- [ ] Time estimate accurate
- [ ] Feedback: [Any suggested improvements for clarity?]

---

## Infrastructure Changes

Have there been significant infrastructure changes since last review?

- [ ] Kubernetes version upgrade
  - [ ] Action: Update kubectl commands
- [ ] Docker version change
  - [ ] Action: Update docker-compose syntax
- [ ] Database version upgrade
  - [ ] Action: Verify SQL query compatibility
- [ ] Tool versions (Grafana, Jaeger, Prometheus)
  - [ ] Action: Update URLs/query syntax
- [ ] Notes: [Any compatibility issues?]

---

## Post-Incident Learnings

If this runbook was used during an incident since last review:

- [ ] Runbook was accurate and helpful
- [ ] Issues discovered during incident:
  - [ ] **Issue:** [Description]
    - [ ] Action: Update runbook
    - [ ] Priority: [High/Medium/Low]
    - [ ] Notes: [Details]
- [ ] Time to resolution using runbook: [Minutes]
- [ ] Would runbook have helped prevent incident?
  - [ ] Yes - this was proactive investigation runbook
  - [ ] Partially - runbook accelerated resolution
  - [ ] No - incident caught by alerts

---

## Version Control

- [ ] Update "Last Updated" field in runbook header: [Date]
- [ ] Update git history:
  - [ ] Commit message: `Runbook review: [runbook name] - [summary of changes]`
  - [ ] Tag major revision: `git tag runbooks-v[X.Y]`
- [ ] Related issue/ticket: [Link to issue tracking]

---

## Action Items

List all improvements identified during this review:

| Priority | Action | Owner | Target Date | Status |
|----------|--------|-------|-------------|--------|
| High | [Action] | [Name] | [Date] | [ ] Pending |
| Medium | [Action] | [Name] | [Date] | [ ] Pending |
| Low | [Action] | [Name] | [Date] | [ ] Pending |

---

## Overall Assessment

### Runbook Health: [ ] Green / [ ] Yellow / [ ] Red

**Summary:** [Brief assessment of runbook quality and readiness]

**Recommendation:**
- [ ] Approved for production use as-is
- [ ] Approved with minor updates applied
- [ ] Requires updates before next production incident
- [ ] Requires significant revision

---

## Sign-Off

**Reviewer:** _________________ **Date:** _____________

**Secondary Reviewer (if applicable):** _________________ **Date:** _____________

**Operations Team Lead Approval:** _________________ **Date:** _____________

---

## Notes Section

Additional observations, insights, or context:

[Free-form notes section]

---

**Document Version:** 1.0
**Template Last Updated:** 2025-11-03
