# Quarterly Penetration Testing Procedure

**Date:** 2025-11-03  
**Schedule:** Quarterly (Q1, Q2, Q3, Q4)  
**Owner:** Security Lead  
**Duration:** 3-5 days per assessment

## Overview

This document defines the process for manual security penetration testing of the AI Agents application. Penetration testing complements automated security tests by validating real-world attack scenarios that automated tools may miss.

## Scope Definition

### In-Scope Components

- **FastAPI Webhook Endpoint** (`/webhooks/enhancement`)
  - Signature validation attacks
  - Replay attack prevention
  - Payload injection attempts

- **PostgreSQL Database**
  - Row-level security (RLS) policy bypass attempts
  - Cross-tenant data access attempts
  - Direct SQL injection via database connection

- **Kubernetes Cluster** (if deployed)
  - Network policy enforcement
  - Namespace isolation validation
  - Pod-to-pod communication security

- **Secrets Management**
  - Kubernetes Secrets access controls
  - Environment variable exposure
  - Encryption key management

### Out-of-Scope Components

- Third-party ServiceDesk Plus API (external to scope)
- OpenRouter API (external LLM service)
- Third-party infrastructure not under our control
- Social engineering or physical security

## Threat Model

### Attack Scenarios

#### 1. Insider Threat
**Attacker Profile**: Disgruntled employee with database access  
**Objectives**:
- Exfiltrate customer tenant data
- Modify audit logs
- Disable security controls

**Mitigation Testing**:
- Attempt to bypass RLS policies
- Attempt to modify logs directly
- Verify role-based access enforcement

#### 2. Network Compromise
**Attacker Profile**: Network attacker with MitM capability  
**Objectives**:
- Intercept webhook payloads
- Forge webhook signatures
- Inject malicious SQL/XSS

**Mitigation Testing**:
- Verify HMAC-SHA256 signature validation
- Test for plaintext secret leaks
- Validate TLS/HTTPS enforcement

#### 3. Supply Chain Attack
**Attacker Profile**: Compromised dependency with backdoor  
**Objectives**:
- Execute arbitrary code via library vulnerability
- Exfiltrate environment variables
- Establish persistence

**Mitigation Testing**:
- Review dependency manifest (requirements.txt)
- Check for known CVEs in dependencies
- Validate sandboxing/isolation

#### 4. Application Logic Attack
**Attacker Profile**: Skilled application attacker  
**Objectives**:
- Bypass input validation
- Exploit race conditions
- Abuse API endpoints

**Mitigation Testing**:
- Fuzzing with malformed inputs
- Concurrent request testing
- API endpoint enumeration

## Test Plan

### Manual Testing Procedures

#### Phase 1: Reconnaissance (Day 1)

1. **Document Enumeration**
   - Review architecture.md security section
   - Identify all API endpoints
   - Map data flow through system

2. **Environment Inspection**
   - List available network interfaces
   - Document Kubernetes cluster topology
   - Identify external dependencies

3. **Configuration Review**
   - Check for default credentials
   - Review environment variables
   - Examine security policies

#### Phase 2: Authentication & Authorization Testing (Days 1-2)

1. **Webhook Signature Bypass**
   ```bash
   # Test missing signature header
   curl -X POST http://localhost:8000/webhooks/enhancement \
     -H "Content-Type: application/json" \
     -d '{"event":"test"}'
   # Expected: 401 Unauthorized
   
   # Test invalid signature
   curl -X POST http://localhost:8000/webhooks/enhancement \
     -H "X-ServiceDesk-Signature: invalid_signature_here" \
     -d '{"event":"test"}'
   # Expected: 401 Unauthorized
   ```

2. **RLS Policy Testing**
   - Connect directly to PostgreSQL with application user
   - Set `app.current_tenant_id` to different tenant
   - Attempt to query other tenant's data
   - Expected: RLS policy denies access (0 rows)

3. **Privilege Escalation**
   - Attempt to access admin-only endpoints without auth
   - Try to modify other tenant's configuration
   - Verify audit logging of failed attempts

#### Phase 3: Input Validation Testing (Day 2-3)

1. **SQL Injection Testing**
   ```bash
   # Test SQL injection in description field
   curl -X POST http://localhost:8000/webhooks/enhancement \
     -H "X-ServiceDesk-Signature: $(compute_valid_sig)" \
     -d '{"description":"'; DROP TABLE enhancement_history; --"}'
   # Expected: Safe storage, no table deletion
   ```

2. **XSS Testing**
   - Send HTML/JavaScript payloads in input fields
   - Verify output escaping
   - Check for script execution in responses

3. **Command Injection Testing**
   - Send shell metacharacters in input
   - Verify commands not executed
   - Check error message disclosure

4. **Path Traversal Testing**
   - Attempt `../../etc/passwd` in file paths
   - Verify path normalization
   - Check for directory traversal

#### Phase 4: Data Security Testing (Day 3-4)

1. **Sensitive Data in Logs**
   - Generate security events (failed auth, etc.)
   - Review logs for API keys, passwords, secrets
   - Verify SensitiveDataFilter is working

2. **Encryption Validation**
   - Verify TLS/HTTPS usage
   - Check certificate validity
   - Test for plaintext secrets in environment

3. **Data Exfiltration Scenarios**
   - Attempt to download large datasets
   - Verify rate limiting
   - Check audit logging of data access

#### Phase 5: Network & Infrastructure Testing (Day 4-5)

1. **Network Policy Validation** (if Kubernetes deployed)
   ```bash
   # Test network segmentation
   kubectl get networkpolicies
   
   # Attempt pod-to-pod communication across namespaces
   kubectl exec -n tenant-a pod -- curl http://service.tenant-b
   # Expected: Connection timeout or denied
   ```

2. **Secrets Management Testing**
   ```bash
   # Verify Kubernetes Secrets are encrypted at rest
   kubectl get secrets -A
   
   # Check for exposed environment variables
   kubectl exec pod -- env | grep -i secret
   ```

3. **Dependency Scanning Validation**
   ```bash
   safety check -r requirements.txt
   pip-audit
   # Verify no critical vulnerabilities
   ```

## Tools & Access

### Required Tools

- **Burp Suite Community** or **OWASP ZAP** - Web API testing
- **sqlmap** - SQL injection testing
  ```bash
  sqlmap -u "http://localhost:8000/webhooks/enhancement" \
    --data='{"event":"test"}' -p event
  ```

- **curl** & **jq** - API testing and response parsing
- **nmap** - Network scanning (if infrastructure accessible)
- **Kubernetes CLI** (`kubectl`) - Cluster inspection
- **PostgreSQL Client** (`psql`) - Database testing

### Access Requirements

- **Database Access**: Read-only PostgreSQL user for test database
- **Kubernetes Access**: View access to cluster (no delete permissions)
- **API Access**: Test tenant credentials with webhook endpoint access
- **File System**: Read access to logs and configuration

### Test Environment

- **Database**: Test database (not production)
- **API Server**: Staging/test environment instance
- **Kubernetes**: Test cluster or namespace isolation
- **Network**: Isolated test network if possible

## Execution Steps

### Pre-Test Checklist

- [ ] Notify development team of testing window
- [ ] Backup production data
- [ ] Ensure test environment isolated from production
- [ ] Document baseline metrics (response times, error counts)
- [ ] Set up log aggregation for testing session
- [ ] Establish communication channel for critical findings

### During Testing

1. **Day-by-Day Execution**
   - Follow Phase 1-5 testing procedures above
   - Document all test steps and results
   - Capture screenshots of vulnerabilities
   - Note any system failures or anomalies

2. **Finding Documentation**
   - Severity: CRITICAL, HIGH, MEDIUM, LOW
   - Description: What was tested, what failed
   - Reproduction steps: Exact steps to reproduce
   - Impact: Potential business/security impact
   - Recommendation: How to remediate

3. **Communication**
   - Daily debrief with development team
   - Report critical findings immediately
   - Request clarification on security controls

### Post-Test Activities

- [ ] Complete full test report
- [ ] Remediation recommendations ranked by severity
- [ ] Schedule retesting after fixes applied
- [ ] Lessons learned review
- [ ] Archive test evidence

## Remediation Process

### Severity Classification

| Severity | CVSS Score | SLA | Examples |
|----------|-----------|-----|----------|
| CRITICAL | 9.0-10.0 | 7 days | RLS bypass, auth bypass |
| HIGH | 7.0-8.9 | 30 days | XSS/injection, secret leak |
| MEDIUM | 4.0-6.9 | 90 days | Unvalidated redirect, weak crypto |
| LOW | 0.1-3.9 | 180 days | Info disclosure, typos |

### Remediation SLA

1. **CRITICAL** (7 day SLA)
   - Immediate notification to CISO
   - Begin fix within 24 hours
   - Deploy fix within 7 days
   - Retest immediately after fix

2. **HIGH** (30 day SLA)
   - Schedule fix in current/next sprint
   - Deploy within 30 days
   - Retest within one week of deployment

3. **MEDIUM** (90 day SLA)
   - Include in next quarterly release
   - Deploy within 90 days
   - Retest within one month of deployment

4. **LOW** (180 day SLA)
   - Include in backlog
   - Deploy with next release
   - Retest in next penetration test

### Bug Report Template

```markdown
## Security Finding: [Title]

**Severity**: [CRITICAL/HIGH/MEDIUM/LOW]  
**CVSS Score**: [X.X]  
**Category**: [OWASP Category]  

### Description
[What was tested and what failed]

### Reproduction Steps
1. [Step 1]
2. [Step 2]
3. [Step 3]

### Technical Details
[Screenshots, logs, code references]

### Impact
[Potential business/security impact]

### Remediation
[Recommended fix]

### References
- [OWASP Reference]
- [CWE Reference]
```

## Sign-Off and Evidence

### Evidence Collection

- Screenshots of each vulnerability
- Network traffic captures (where applicable)
- Database query logs
- Audit log entries
- Test execution timeline

### Sign-Off Requirements

**Tester Information**:
- Name: [Tester Name]
- Organization: [External firm or Internal]
- Credentials: [Certifications, experience]
- Date: [Test completion date]

**Finding Summary**:
- Total vulnerabilities: [Count]
- CRITICAL: [Count]
- HIGH: [Count]
- MEDIUM: [Count]
- LOW: [Count]

**Sign-Off**:
- Tester signature: ________________
- Product owner signature: ________________
- Security lead signature: ________________
- Date: ________________

## Lessons Learned

### Post-Test Review

1. **Findings Analysis**
   - Were vulnerabilities known? (gap in automated tests)
   - Could automated tests detect this?
   - What patterns emerged?

2. **Testing Methodology**
   - What worked well?
   - What was inefficient?
   - Any tools or techniques to add?

3. **Process Improvements**
   - New automated test to add?
   - Architecture changes needed?
   - Security training topics?

4. **Documentation**
   - Update this procedure with lessons learned
   - Add new test scenarios to automated suite
   - Document mitigation patterns for team

## Scheduling and Coordination

### Calendar Schedule

| Quarter | Month | Week | Owner |
|---------|-------|------|-------|
| Q1 | January | Week of Jan 8-12 | Security Lead |
| Q2 | April | Week of Apr 8-12 | Security Lead |
| Q3 | July | Week of Jul 8-12 | Security Lead |
| Q4 | October | Week of Oct 8-12 | Security Lead |

### Booking External Firm

**Lead Time**: 3+ months in advance

**Process**:
1. Identify security firm (first week of quarter - 3 months prior)
2. Scope and contract negotiation (month 1)
3. Access provisioning and coordination (month 2)
4. Testing execution (month 3)

**Contact Template**:
```
Subject: Penetration Testing Engagement - Q[X] [YEAR]

We are seeking a qualified security firm for a 3-5 day penetration
test of our AI Agents application scheduled for [DATE RANGE].

Scope:
- FastAPI webhook endpoints
- PostgreSQL database security
- Kubernetes cluster isolation (if applicable)
- Input validation and injection prevention

Please provide:
- Quote and timeline
- Tester credentials and experience
- Sample report format
- NDA requirements
```

## References

- [OWASP Penetration Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [NIST Penetration Testing Standard](https://csrc.nist.gov/publications/detail/sp/800-115/final)
- [CIS Controls - Security Testing](https://www.cisecurity.org/cis-controls/)
- [PTES Penetration Testing Execution Standard](http://www.ptes.com/)

---

**Last Updated:** 2025-11-03  
**Next Scheduled Test:** Q1 2026 (January 8-12, 2026)  
**Owner Contact:** [Security Lead Email]
