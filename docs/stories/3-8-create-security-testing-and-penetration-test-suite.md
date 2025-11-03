# Story 3.8: Create Security Testing and Penetration Test Suite

**Status:** drafted

**Story ID:** 3.8
**Epic:** 3 (Multi-Tenancy & Security)
**Date Created:** 2025-11-03
**Story Key:** 3-8-create-security-testing-and-penetration-test-suite

---

## Change Log

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2025-11-03 | 1.0 | Story drafted by Scrum Master (Bob) in non-interactive mode | Bob (Scrum Master) |

---

## Story

As a security engineer,
I want automated security tests validating isolation and input handling,
So that security regressions are caught before production deployment.

---

## Technical Context

Implement comprehensive automated security testing suite covering OWASP Top 10 vulnerabilities, tenant isolation bypass attempts, webhook signature spoofing, and input sanitization edge cases. Security tests validate that Stories 3.1-3.7 protections (RLS, input validation, secrets management, webhook signature validation, audit logging) prevent common attack vectors. Tests integrate into CI/CD pipeline via GitHub Actions, automatically block deployment on failures, and provide quantified security posture metrics. Quarterly penetration testing procedure documents methodology for manual security assessment by external security team.

**Architecture Alignment:**
- Validates Stories 3.1 (RLS policies), 3.4 (input validation), 3.5 (webhook signature validation), 3.7 (audit logging)
- Integrates with GitHub Actions CI pipeline (Story 1.7)
- Generates security test reports for compliance tracking (FR024)
- Aligns with ADR-004 (security-first design patterns) and architecture.md Security section

**Prerequisites:** Stories 3.1-3.7 (all security features implemented and audit logging in place)

---

## Acceptance Criteria

### AC1: Security Test Suite with OWASP Top 10 Coverage

- Security test file created: `tests/security/test_owasp_vulnerabilities.py`
- Test scenarios for each vulnerability type:
  - **SQL Injection**: Query payloads in ticket description field, verify SQLAlchemy ORM prevents execution
  - **Cross-Site Scripting (XSS)**: HTML/JavaScript payloads in ticket notes, verify escaping before posting to ServiceDesk
  - **Broken Authentication**: Missing/invalid webhook signature headers, verify 401 rejection
  - **Broken Access Control**: Cross-tenant data access attempts, verify RLS policies deny queries
  - **Sensitive Data Exposure**: API key/password in logs, verify SensitiveDataFilter redaction
  - **XML External Entity (XXE)**: XML payloads in ticket description, verify parsing rejects external entities
  - **Broken Authorization**: Tenant config endpoint without authentication, verify 403 Forbidden
  - **Using Components with Known Vulnerabilities**: Dependency scanning via safety/snyk (AC3)
  - **Insufficient Logging & Monitoring**: Verify audit logs capture failed security events (Story 3.7)
  - **Broken Cryptography**: Webhook signature hashing, verify SHA256 strength
- Each test includes:
  - Vulnerability description comment
  - Attack payload
  - Expected safe response (status code, error type)
  - Assertion of rejection/redaction
- Minimum 2 test cases per vulnerability type (happy path for prevention, negative path for attack)
- All tests pass (0 vulnerabilities) on main branch
- Tests fully documented with references to OWASP Top 10 descriptions

### AC2: Tenant Isolation Bypass Tests

- Test file created: `tests/security/test_tenant_isolation.py`
- Test scenarios:
  - **Cross-tenant query attempt**: Tenant A uses Tenant B's tenant_id in query, verify RLS policy denies rows (0 results)
  - **Session context bypass**: Attempt query without setting app.current_tenant_id, verify 0 results returned (safe default)
  - **RLS policy circumvention**: Direct database query bypassing application layer, verify policy still applies
  - **Webhook signature with wrong tenant secret**: Webhook signed with Tenant B secret but sent to Tenant A endpoint, verify 401
  - **Row-level security policy existence**: Verify all tenant-related tables have RLS policies enabled
- Each test includes:
  - Setup: Create test data for multiple tenants
  - Attack: Attempt cross-tenant access
  - Verification: Confirm RLS policy blocks access
- All tests validate that tenant_id enforcement works at database layer (not just application)
- Zero cross-tenant data leakage in any scenario

### AC3: Input Validation and Sanitization Tests

- Test file created: `tests/security/test_input_validation.py`
- Test scenarios (from Story 3.4 implementation):
  - **SQL injection in description**: `'; DROP TABLE tenant_configs; --` → Verify safe storage, no execution
  - **XSS in ticket title**: `<script>alert('xss')</script>` → Verify HTML escaped in API responses
  - **Command injection in metadata**: `$(whoami)` in custom field → Verify treated as literal string
  - **Path traversal**: `../../etc/passwd` → Verify not processed as file path
  - **Oversized input**: 50,000-character description → Verify max length enforced (10,000 chars)
  - **Unicode/special characters**: Unicode, emoji, RTL text → Verify accepted but safe
  - **Null bytes**: Payload with `\x00` → Verify rejected or sanitized
  - **Invalid UTF-8**: Malformed UTF-8 sequences → Verify handled gracefully
- Validation rules tested:
  - Pydantic model strict typing prevents type confusion
  - String length limits enforced pre-storage
  - Special characters allowed but escaped on output
  - No executable patterns permitted in user input
- Edge cases covered:
  - Empty strings, null values, boundary values (max length)
  - Mixed payloads (SQL + XSS combined)
  - Unicode-based attack variations

### AC4: Webhook Signature Spoofing Tests

- Test file created: `tests/security/test_webhook_signature_validation.py`
- Test scenarios:
  - **Missing signature header**: Webhook POST without X-ServiceDesk-Signature header → Verify 401
  - **Invalid signature**: Correct payload + wrong signature value → Verify 401
  - **Signature mismatch**: Payload modified after signing → Verify 401 (signature no longer valid)
  - **Replay attack prevention**: Same valid webhook replayed twice → Verify timestamp validation rejects second attempt
  - **HMAC algorithm strength**: Verify HMAC-SHA256 is used (not MD5/SHA1)
  - **Secret rotation**: Update tenant webhook secret, verify old signature no longer works, new secret works
- Signature validation tested:
  - Per-tenant signing secrets correctly isolated
  - Comparison is constant-time (prevents timing attacks)
  - Payload must match exactly (no mutations between signing and verification)

### AC5: Dependency Scanning for Known CVEs

- Dependency scanner integrated into CI pipeline: `.github/workflows/ci.yml`
- Tools configured:
  - **safety**: Scans `requirements.txt` for known Python package vulnerabilities
  - **snyk** (optional): Cloud-based dependency scanning with remediation suggestions
  - **pip-audit**: Additional supply-chain scanning
- Scanning execution:
  - Runs on every pull request (blocking merge if vulnerabilities found)
  - Runs on main branch deployments
  - Generates vulnerability report with CVSS scores
  - Known CVEs listed with remediation version
- Thresholds:
  - CRITICAL or HIGH severity: Block deployment
  - MEDIUM: Warning in PR comments, can override with justification
  - LOW: Informational only
- Baseline established and tracked:
  - Current clean state documented
  - Any new dependencies require security review
  - Quarterly CVE review process to identify upgrades

### AC6: Security Test Results Documentation and Tracking

- Security test report generated: `docs/security/test-results-{{date}}.md`
- Report includes:
  - **Executive Summary**: Pass/fail status, total tests run, vulnerabilities found (0 expected)
  - **OWASP Top 10 Status**: Per-vulnerability coverage with test names
  - **Tenant Isolation Results**: Summary of RLS policy effectiveness
  - **Input Validation Summary**: Attack scenarios and rejection counts
  - **Webhook Signature Results**: Attack simulation results
  - **Dependency Scan Results**: Packages scanned, vulnerabilities (if any), remediation links
  - **Coverage Metrics**: % of codebase covered by security tests, growth over time
  - **Recommendations**: Any remediation needed, follow-up security work
- Tracking:
  - Test results stored with git history (committed to repo)
  - Continuous tracking of security metrics over time (weekly/monthly summaries)
  - Pre-penetration test baseline documented
- Documentation in `docs/security/`:
  - `security-testing-strategy.md`: Approach, tools, metrics
  - `owasp-mapping.md`: Mapping of tests to OWASP Top 10 requirements
  - Test coverage dashboard (future: Grafana panel showing security test status)

### AC7: Failed Security Tests Block Deployment

- GitHub Actions workflow configured: `.github/workflows/ci.yml`
- Security test step:
  - Runs `pytest tests/security/` with strict failure mode
  - Exit code 0 = all tests pass (allow merge)
  - Exit code ≠ 0 = any test fails (block merge)
- Branch protection rule configured:
  - Status check: "Security Tests" must pass
  - Enforce on main branch and release branches
  - Require re-review if security tests change
- Deployment pipeline:
  - Kubernetes manifest deployment skipped if security tests fail
  - Production deployments require manual override (with audit log) to bypass security gate
- Test failure notifications:
  - Slack notification to #security channel on failure
  - PR comment posted with failed test details and remediation steps

### AC8: Quarterly Penetration Testing Procedure Documented

- Procedure document created: `docs/security/penetration-testing-procedure.md`
- Document includes:
  - **Scope Definition**: Which components/APIs tested (FastAPI webhook, database, Kubernetes), what excluded (third-party services)
  - **Threat Model**: High-level attack scenarios (insider threat, network compromise, supply chain)
  - **Test Plan**:
    - Manual authentication bypass attempts (if applicable future feature)
    - Network segmentation validation (Kubernetes network policies)
    - Data exfiltration scenarios (database access controls)
    - Privilege escalation attempts (RLS bypass, RBAC)
  - **Tools & Access**: Tools used (Burp Suite, sqlmap, nmap), access requirements, test environment designation
  - **Execution Steps**: Step-by-step manual testing procedures, expected outcomes
  - **Remediation**: Bug report template, severity classification, SLA for fixes (critical: 7 days, high: 30 days, medium: 90 days)
  - **Sign-off**: Dates of testing, tester credentials, findings summary, retesting proof
  - **Lessons Learned**: Post-penetration review, improvements to testing methodology
- Scheduling:
  - Calendar reminder: Q1, Q2, Q3, Q4 (annually)
  - Assigned owner for coordination (Security Lead)
  - External security firm booked in advance (3+ month lead time for major tests)
- Tool-specific guidance:
  - Burp Suite setup for endpoint testing
  - sqlmap command examples for SQL injection verification
  - Network policy testing with `curl` and Kubernetes networking tools

---

## Tasks / Subtasks

### Task 1: Implement OWASP Top 10 Security Test Suite (AC1)
- [ ] 1.1: Create `tests/security/` directory structure
- [ ] 1.2: Create `tests/security/test_owasp_vulnerabilities.py` with test class
- [ ] 1.3: Implement SQL injection tests (2+ variants)
- [ ] 1.4: Implement XSS prevention tests (HTML escaping verification)
- [ ] 1.5: Implement authentication bypass tests (invalid signatures)
- [ ] 1.6: Implement authorization tests (403 on missing credentials)
- [ ] 1.7: Implement sensitive data exposure tests (API key redaction in logs)
- [ ] 1.8: Implement XXE prevention tests (XML parser security)
- [ ] 1.9: Implement known vulnerability tests (dependency baseline)
- [ ] 1.10: Implement logging/monitoring tests (audit events for failures)
- [ ] 1.11: Add documentation comments linking each test to OWASP Top 10
- [ ] 1.12: Run test suite and verify all pass (0 vulnerabilities)
- [ ] 1.13: Add 2+ test cases per vulnerability type
- [ ] 1.14: Write unit tests with mocked/test database (no production data)

### Task 2: Implement Tenant Isolation Bypass Tests (AC2)
- [ ] 2.1: Create `tests/security/test_tenant_isolation.py`
- [ ] 2.2: Implement multi-tenant test setup (create 2-3 test tenants, test data)
- [ ] 2.3: Test cross-tenant query rejection via RLS policy
- [ ] 2.4: Test missing tenant context (unset app.current_tenant_id)
- [ ] 2.5: Test direct DB query with RLS policy (bypass attempt)
- [ ] 2.6: Test webhook signature with wrong tenant secret
- [ ] 2.7: Verify all tenant tables have RLS policies enabled (schema check)
- [ ] 2.8: Test that row-level security denies data access (assert 0 rows returned)
- [ ] 2.9: Add negative test: Verify authorized tenant CAN access their own data
- [ ] 2.10: Write unit tests (mock PostgreSQL/RLS)
- [ ] 2.11: Integration tests with real database (in CI runner)

### Task 3: Implement Input Validation and Sanitization Tests (AC3)
- [ ] 3.1: Create `tests/security/test_input_validation.py`
- [ ] 3.2: Implement SQL injection payload tests (5+ payloads)
- [ ] 3.3: Implement XSS payload tests (script tags, event handlers)
- [ ] 3.4: Implement command injection tests (shell metacharacters)
- [ ] 3.5: Implement path traversal tests (../ patterns)
- [ ] 3.6: Implement oversized input tests (max length enforcement)
- [ ] 3.7: Implement Unicode/special character tests (emoji, RTL)
- [ ] 3.8: Implement null byte and invalid UTF-8 tests
- [ ] 3.9: Implement mixed attack payload tests (SQL + XSS)
- [ ] 3.10: Test Pydantic model strict typing prevents type confusion
- [ ] 3.11: Verify input is escaped on output (not just storage)
- [ ] 3.12: Test boundary cases (empty string, max length exactly, max+1)
- [ ] 3.13: Write unit tests for validation functions
- [ ] 3.14: Integration tests with FastAPI endpoints

### Task 4: Implement Webhook Signature Validation Tests (AC4)
- [ ] 4.1: Create `tests/security/test_webhook_signature_validation.py`
- [ ] 4.2: Implement missing signature header test (expect 401)
- [ ] 4.3: Implement invalid signature test (garbage signature)
- [ ] 4.4: Implement signature mismatch test (payload altered)
- [ ] 4.5: Implement replay attack prevention test (timestamp validation)
- [ ] 4.6: Verify HMAC-SHA256 algorithm used (not weaker variants)
- [ ] 4.7: Test per-tenant signing secret isolation (Tenant A ≠ Tenant B secrets)
- [ ] 4.8: Verify constant-time comparison (prevents timing attacks)
- [ ] 4.9: Test secret rotation (old secret fails, new secret works)
- [ ] 4.10: Write unit tests with mocked HMAC
- [ ] 4.11: Integration tests with real webhook endpoint
- [ ] 4.12: Test valid signature passes (happy path)

### Task 5: Integrate Dependency Scanning into CI Pipeline (AC5)
- [ ] 5.1: Install safety: `pip install safety`
- [ ] 5.2: Install pip-audit: `pip install pip-audit`
- [ ] 5.3: Create `.github/workflows/security-scan.yml` GitHub Actions workflow
- [ ] 5.4: Configure safety to scan requirements.txt (blocking on CRITICAL/HIGH)
- [ ] 5.5: Configure pip-audit for supply chain scanning
- [ ] 5.6: Set thresholds: CRITICAL/HIGH = block, MEDIUM = warn, LOW = info
- [ ] 5.7: Generate vulnerability report with CVSS scores and remediation links
- [ ] 5.8: Integrate into main CI workflow (run on every PR)
- [ ] 5.9: Document known/acceptable vulnerabilities with justification (if any)
- [ ] 5.10: Test workflow by adding/removing vulnerable package (verify blocking)
- [ ] 5.11: Set up Slack notification for scan failures
- [ ] 5.12: Establish baseline: Current clean state documented

### Task 6: Create Security Test Results Documentation (AC6)
- [ ] 6.1: Create `docs/security/` directory
- [ ] 6.2: Create `docs/security/security-testing-strategy.md`
- [ ] 6.3: Create `docs/security/owasp-mapping.md` (tests → OWASP Top 10)
- [ ] 6.4: Create template: `docs/security/test-results-template.md`
- [ ] 6.5: Generate first security test report with current results
- [ ] 6.6: Document coverage metrics (% of codebase covered, growth tracking)
- [ ] 6.7: Create Grafana dashboard panel for security test metrics (future)
- [ ] 6.8: Document how to interpret results and identify trends
- [ ] 6.9: Add pre-penetration testing baseline documentation
- [ ] 6.10: Set up quarterly report generation process

### Task 7: Configure Security Tests to Block Deployment (AC7)
- [ ] 7.1: Update `.github/workflows/ci.yml` to include security test step
- [ ] 7.2: Add `pytest tests/security/` with strict failure (exit on first failure)
- [ ] 7.3: Configure branch protection rule: "Security Tests" status check required
- [ ] 7.4: Enforce rule on main and release branches
- [ ] 7.5: Set up PR comment posting with failed test details (via GitHub Actions)
- [ ] 7.6: Implement production deployment gate: security tests must pass
- [ ] 7.7: Add manual override capability (with audit logging) for emergency deployments
- [ ] 7.8: Configure Slack notification on security test failure
- [ ] 7.9: Document exception process for security test bypassing
- [ ] 7.10: Test workflow by introducing deliberate test failure (verify blocking)

### Task 8: Document Quarterly Penetration Testing Procedure (AC8)
- [ ] 8.1: Create `docs/security/penetration-testing-procedure.md`
- [ ] 8.2: Define scope (in-scope/out-of-scope components)
- [ ] 8.3: Document threat model (insider, network, supply chain)
- [ ] 8.4: Write manual test plan with attack scenarios
- [ ] 8.5: Document tools (Burp Suite, sqlmap, nmap) with setup instructions
- [ ] 8.6: Create step-by-step execution checklist
- [ ] 8.7: Define remediation SLAs (critical: 7d, high: 30d, medium: 90d)
- [ ] 8.8: Create bug report template for findings
- [ ] 8.9: Document sign-off process and evidence requirements
- [ ] 8.10: Establish quarterly schedule with calendar reminders
- [ ] 8.11: Document lessons learned process post-penetration test
- [ ] 8.12: Identify external security firm or appoint internal test coordinator

### Task 9: Integration Testing and CI/CD Validation (All ACs)
- [ ] 9.1: Run full security test suite locally: `pytest tests/security/ -v`
- [ ] 9.2: Verify all tests pass (0 vulnerabilities)
- [ ] 9.3: Check code coverage: `pytest tests/security/ --cov=src`
- [ ] 9.4: Coverage target: >85% for security-related code
- [ ] 9.5: Test CI workflow: Push PR, verify security tests run
- [ ] 9.6: Test blocking behavior: Introduce failing test, verify merge blocked
- [ ] 9.7: Test remediation: Fix failing test, verify merge allowed
- [ ] 9.8: Dependency scan: Verify safety and pip-audit run and report correctly
- [ ] 9.9: Documentation review: Ensure all docs complete and clear
- [ ] 9.10: Final verification: All ACs demonstrated working in CI/CD pipeline

---

## Dev Notes

### Architecture Patterns and Constraints

**Security Testing Architecture:**
- Security tests use pytest framework (shared with Story 2.12)
- Tests run in CI pipeline via GitHub Actions (Story 1.7 infrastructure)
- Tests exercise mocked services and test database (no production data)
- RLS policy testing uses real PostgreSQL with test tenant isolation
- Sensitive data in logs verified through audit logging (Story 3.7)

**Multi-Tenant Isolation Testing:**
- RLS policies tested at database layer (PostgreSQL constraints)
- Application-layer access control also verified
- Both positive (authorized access works) and negative (unauthorized blocked) cases tested

**CI/CD Integration:**
- Security tests run on every PR (blocking merge on failure)
- Dependency scanning integrated into standard CI pipeline
- Failed security tests generate PR comments with remediation steps
- Production deployments require manual intervention if security tests fail

**Best Practices from 2025 Security Research:**
- OWASP Top 10 2024 edition awareness (AI/LLM risks, security governance added)
- Shift-left security: Tests run early in development (not just pre-deployment)
- Automated compliance: Security tests provide audit trail for compliance reviews
- Continuous monitoring: Penetration testing quarterly (not annual)
- Supply chain security: Dependency scanning covers direct and transitive dependencies

### Source Tree Components to Touch

**Core Security Test Files:**
- `tests/security/__init__.py` - New package initialization
- `tests/security/test_owasp_vulnerabilities.py` - OWASP Top 10 tests
- `tests/security/test_tenant_isolation.py` - RLS bypass prevention tests
- `tests/security/test_input_validation.py` - Input sanitization tests
- `tests/security/test_webhook_signature_validation.py` - Signature validation tests

**CI/CD Integration:**
- `.github/workflows/ci.yml` - Update to include security test step and dependency scanning
- `.github/workflows/security-scan.yml` - Optional dedicated security scanning workflow

**Documentation:**
- `docs/security/` - New directory for security documentation
- `docs/security/security-testing-strategy.md` - Overall strategy and metrics
- `docs/security/owasp-mapping.md` - OWASP Top 10 coverage mapping
- `docs/security/penetration-testing-procedure.md` - Quarterly pen test procedure
- `docs/security/test-results-{{date}}.md` - Test result reports (generated)

**Configuration Files:**
- `requirements.txt` or `pyproject.toml` - Add safety, pip-audit
- `pytest.ini` - Ensure security tests configured correctly

**Files Modified (Minimal):**
- None - Security tests are additive, no existing code changes required

**Referenced Architecture:**
- Story 3.1: RLS policy implementation (validate via tests)
- Story 3.4: Input validation implementation (validate via tests)
- Story 3.5: Webhook signature validation (validate via tests)
- Story 3.7: Audit logging (verify security events logged)
- architecture.md Security Section: RLS, encryption, input validation patterns

### Project Structure Notes

**Alignment with Unified Project Structure:**
- Follows existing test organization: `tests/security/` mirrors `tests/unit/`, `tests/integration/`
- Uses established naming conventions: `test_*.py` files, PascalCase test classes
- Adheres to PEP8 and Black formatting
- New `docs/security/` directory logically groups security documentation (similar to `docs/operations/`)

**Directory Layout:**
```
tests/
├── security/
│   ├── __init__.py
│   ├── conftest.py (security-specific fixtures)
│   ├── test_owasp_vulnerabilities.py
│   ├── test_tenant_isolation.py
│   ├── test_input_validation.py
│   └── test_webhook_signature_validation.py

docs/
├── security/
│   ├── security-testing-strategy.md
│   ├── owasp-mapping.md
│   ├── penetration-testing-procedure.md
│   └── test-results-{{date}}.md
```

**Detected Variances:**
- None. Story aligns with existing architecture patterns and project structure.

### References

**Source Documents:**
- [Source: docs/PRD.md#Requirements] FR022 (security tests), NFR004 (security requirements)
- [Source: docs/epics.md#Story-3.8] Original story definition and acceptance criteria
- [Source: docs/architecture.md#Security-Architecture] RLS, webhook validation, input validation patterns
- [Source: docs/architecture.md#Cross-Cutting-Concerns] Error handling patterns for security tests

**From Previous Story (3.7 - Audit Logging):**
- Audit logging infrastructure complete (Story 3.7 status: done)
- Sensitive data redaction in logs (SensitiveDataFilter class)
- Correlation ID tracing for security event tracking
- 90-day log retention for compliance audits
- Note: Security tests can verify that failed security events ARE logged

**OWASP Top 10 2024 References:**
- A01:2021 Broken Access Control → Tests in AC2 (RLS validation)
- A02:2021 Cryptographic Failures → Tests in AC4 (HMAC-SHA256)
- A03:2021 Injection → Tests in AC1, AC3 (SQL injection, command injection)
- A04:2021 Insecure Design → Architectural pattern validation (ADR compliance)
- A05:2021 Security Misconfiguration → Dependency scanning (AC5)
- A06:2021 Vulnerable Components → Dependency scanning (AC5)
- A07:2021 Authentication Failure → Tests in AC4 (signature validation)
- A08:2021 Data Integrity Failure → RLS + webhook validation (AC2, AC4)
- A09:2021 Logging & Monitoring Failure → Tests in AC1 (audit events logged)
- A10:2021 SSRF → Input validation tests (AC3)

**External Documentation (2025 Best Practices):**
- [Source: OWASP Top 10 2024](https://owasp.org/Top10/)
- [Source: pytest Documentation - Security Testing](https://docs.pytest.org/)
- [Source: GitHub Actions - Security Best Practices](https://docs.github.com/en/actions/security-guides)
- [Source: CWE Top 25 - 2024](https://cwe.mitre.org/)

**Tools Documentation:**
- [safety - Python vulnerability scanner](https://github.com/Lucas-C/pre-commit-hooks)
- [pip-audit - Python dependency auditor](https://github.com/pypa/pip-audit)
- [pytest - Python testing framework](https://docs.pytest.org/)

---

## Learnings from Previous Story

**From Story 3.7 (Implement Audit Logging for All Operations) - Status: done**

**New Infrastructure Created:**
- `src/utils/logger.py`: Enhanced with `AuditLogger` class for operation-specific audit logging
- `SensitiveDataFilter`: Regex-based filtering for API keys, passwords, SSN, email, credit cards
- Correlation ID pattern: UUID v4 for distributed tracing through FastAPI → Redis → Celery → LangGraph
- `docs/operations/log-queries.md`: Log query examples and schema reference
- `docs/operations/logging-infrastructure.md`: Kubernetes log collection architecture

**Architectural Decisions Applied:**
- ADR-005: Loguru for structured JSON logging (all logs searchable)
- Correlation IDs propagate through entire async workflow
- Multi-tenant safe: All logs include tenant_id, no cross-tenant leakage
- 90-day retention meets NFR005 compliance requirement

**Services Available for Reuse:**
- `AuditLogger` methods for logging security events (webhook, API calls, failures)
- `SensitiveDataFilter` patterns can validate that API keys/passwords not in unredacted logs
- Correlation ID tracking enables security event tracing through entire system

**Warnings for Security Testing:**
- Story 3.7 implementation is ~75% test-covered (integration tests for correlation ID flow exist)
- Security tests (this story) should verify audit logging captures failed security events correctly
- Consider adding test for: "When malicious payload rejected, is event logged with full details?"

**Testing Patterns Established:**
- `tests/integration/test_audit_logging.py`: End-to-end correlation ID tracing model
- `tests/unit/test_logger.py`: SensitiveDataFilter pattern validation examples
- Mock fixtures for testing without real dependencies (mock Redis, PostgreSQL)

**Files to Reuse/Reference:**
- `src/utils/logger.py` - Use AuditLogger for security event logging in tests
- `src/schemas/job.py`, `webhook.py` - correlation_id field available for security event tracking
- `src/workflows/enhancement_workflow.py` - Understand correlation_id propagation pattern

**Recommendations:**
- Leverage existing AuditLogger infrastructure to log security test failures with correlation IDs
- Use established test patterns (mocking, fixtures) from Story 3.7 tests
- Document that security tests verify audit logging captures attack attempts

---

## Dev Agent Record

### Context Reference

Context XML file: `docs/stories/3-8-create-security-testing-and-penetration-test-suite.context.xml` (to be generated by story-context workflow)

### Agent Model Used

Claude Haiku 4.5 (claude-haiku-4-5-20251001)

### Debug Log References

- Workflow execution: `/bmad:bmm:workflows:create-story`
- Documentation sources used:
  - epics.md (lines 776-791: Story 3.8 definition)
  - PRD.md (lines 78-85: FR026-FR039 security requirements)
  - architecture.md Security section (lines 485-606: RLS, webhook validation, input validation patterns)
  - OWASP Top 10 2024 (external reference)

### Completion Notes List

- Story drafted in non-interactive (#yolo) mode by Scrum Master (Bob)
- Requirements extracted from epics.md acceptance criteria
- Acceptance criteria expanded from 7 items in epics to detailed ACs with specific test scenarios
- Previous story (3.7) learnings incorporated: use AuditLogger for security event logging
- Architecture alignment verified: references Stories 1.7, 3.1, 3.4, 3.5, 3.7
- Testing standards aligned with existing patterns from Story 2.12 and Story 3.7

### File List

**Files to Create:**
- `tests/security/__init__.py`
- `tests/security/conftest.py` (security-specific fixtures)
- `tests/security/test_owasp_vulnerabilities.py`
- `tests/security/test_tenant_isolation.py`
- `tests/security/test_input_validation.py`
- `tests/security/test_webhook_signature_validation.py`
- `docs/security/security-testing-strategy.md`
- `docs/security/owasp-mapping.md`
- `docs/security/penetration-testing-procedure.md`
- `.github/workflows/security-scan.yml` (optional dedicated workflow)

**Files to Modify:**
- `.github/workflows/ci.yml` (add security test step + dependency scanning)
- `requirements.txt` or `pyproject.toml` (add safety, pip-audit)
- `pytest.ini` (security test configuration if needed)

**Files to Reference (No Modification):**
- `src/utils/logger.py` (AuditLogger for logging security events)
- `src/api/webhooks.py` (webhook signature validation testing)
- `src/services/webhook_validator.py` (signature validation implementation)
- `src/database/models.py` (RLS policy structure)
- `docs/architecture.md` (security patterns reference)

---
