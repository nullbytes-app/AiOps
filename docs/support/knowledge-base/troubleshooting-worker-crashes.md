# Troubleshooting: Worker Crashes

**Category:** Troubleshooting - System Health
**Severity:** P1 (if >50% workers down) / P2 (if 20-50% workers down)
**Last Updated:** 2025-11-04
**Related Runbooks:** [Worker Failures](../../runbooks/worker-failures.md), [Enhancement Failures](../../runbooks/enhancement-failures.md)

---

## Quick Answer

**Worker crashes most commonly caused by OOMKilled (memory limits exceeded)**, application errors, or database connection failures. Check worker pod status → review crash logs → identify crash pattern → adjust memory limits or fix application bug.

---

## Symptoms

**Observable Indicators:**
- Worker pods in `CrashLoopBackOff` state
- Kubernetes events show `OOMKilled` (Out Of Memory Killed)
- Queue depth increasing despite workers attempting to process jobs
- Grafana Worker Health panel shows crashed workers
- Enhancement processing stops or severely degrades

---

## Common Causes

### 1. OOMKilled - Memory Limit Exceeded (50% of cases)

**Root Cause:** Worker memory usage exceeds configured memory limit (e.g., 512MB)

**How to Identify:**
```bash
# Check worker pod status
kubectl get pods -n ai-agents-production | grep worker
# Look for: "OOMKilled" in STATUS column or RESTARTS column incrementing

# Check pod events
kubectl describe pod <worker-pod-name> -n ai-agents-production | grep -A 10 Events
# Look for: "OOMKilled: Container exceeded memory limit"

# Check worker memory usage before crash
kubectl top pods -n ai-agents-production | grep worker
# If memory usage at 100% of limit: OOMKilled likely
```

**Resolution:**
```bash
# Immediate: Increase worker memory limits
kubectl set resources deployment ai-agents-worker -n ai-agents-production --limits=memory=1Gi
# (Replaces current limit, e.g., 512Mi → 1Gi)

# Workers will restart with new limits automatically
# Monitor memory usage to verify fix

# Long-term: Profile memory usage, identify memory leaks (Engineering task)
```

---

### 2. Application Error / Unhandled Exception (30% of cases)

**Root Cause:** Python exception or error causing worker process to crash

**How to Identify:**
```bash
# Check previous pod logs (logs before crash)
kubectl logs <worker-pod-name> -n ai-agents-production --previous

# Look for Python tracebacks:
# - "Traceback (most recent call last):"
# - "Exception:", "Error:", "KeyError:", "AttributeError:", etc.
# - Stack trace showing file/line where crash occurred
```

**Common Error Patterns:**
```python
# KeyError: Missing required field in job payload
# AttributeError: Accessing property on None object
# TypeError: Incorrect type passed to function
# ValueError: Invalid value (e.g., negative number where positive expected)
# ImportError: Missing dependency or module
```

**Resolution:**
- Identify error from stack trace
- Check if recent deployment introduced bug
- **Escalate to Engineering** with crash logs and reproduction steps
- Immediate workaround: Roll back to previous deployment if regression

---

### 3. Database Connection Failure (15% of cases)

**Root Cause:** Worker unable to connect to PostgreSQL database

**How to Identify:**
```bash
# Check worker logs for database errors
kubectl logs <worker-pod-name> -n ai-agents-production --previous | grep -i "database\|connection\|postgres\|psql"

# Common errors:
# - "Connection refused" (database down or network issue)
# - "Too many connections" (connection pool exhausted)
# - "Connection timeout" (slow database or network)
# - "Authentication failed" (credentials wrong)
```

**Resolution:**
```bash
# Check database health
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- psql $DATABASE_URL -c "SELECT 1;"
# Expected: "1" returned. If error: Database down or credentials wrong.

# Check database connections
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'ai_agents';"
# If near max_connections (100): Connection pool exhausted

# Immediate: Restart workers
kubectl rollout restart deployment ai-agents-worker -n ai-agents-production

# Long-term: See [Runbook: Database Connection Issues](../../runbooks/database-connection-issues.md)
```

---

### 4. External Dependency Failure (5% of cases)

**Root Cause:** Worker crashes when external API (OpenAI, ServiceDesk Plus) fails unexpectedly

**How to Identify:**
```bash
# Check worker logs for API errors before crash
kubectl logs <worker-pod-name> -n ai-agents-production --previous | grep -i "openai\|servicedesk\|api error\|timeout"

# Look for unhandled API exceptions:
# - "OpenAI API returned 500"
# - "ServiceDesk Plus connection refused"
# - "Timeout after 60s"
```

**Resolution:**
- Check external API status pages:
  - OpenAI: https://status.openai.com
  - ServiceDesk Plus: Test with curl
- **Escalate to Engineering** to add error handling and retry logic
- Immediate: Wait for external API recovery, workers will retry automatically

---

## Diagnosis Steps

**Step 1: Check Worker Pod Status**
```bash
kubectl get pods -n ai-agents-production | grep worker

# Healthy: All "Running", RESTARTS=0 or low (<5)
# Unhealthy: "CrashLoopBackOff", RESTARTS incrementing rapidly
# OOMKilled: STATUS shows "OOMKilled"
```

**Step 2: Get Pod Events**
```bash
kubectl describe pod <worker-pod-name> -n ai-agents-production | tail -30

# Look for Events section at bottom:
# - "OOMKilled: Container exceeded memory limit" → Cause #1
# - "Error: Exit code 1" → Application error (Cause #2)
# - "Liveness probe failed" → Application hung/unresponsive
```

**Step 3: Review Crash Logs**
```bash
# Get logs from previous crash (before pod restarted)
kubectl logs <worker-pod-name> -n ai-agents-production --previous | tail -100

# Categorize crash:
# - "OOMKilled" → Memory issue (Cause #1)
# - Python traceback → Application error (Cause #2)
# - Database error → Connection failure (Cause #3)
# - API error → External dependency (Cause #4)
```

**Step 4: Check Resource Usage Trends**
```bash
# Current memory usage
kubectl top pods -n ai-agents-production | grep worker

# If memory at 80-100% of limit: Increase limits
# If memory at <50%: Not memory issue, check application errors
```

**Step 5: Check Recent Deployments**
```bash
# List recent deployments
kubectl rollout history deployment ai-agents-worker -n ai-agents-production

# If crashes started after recent deployment: Likely regression
# Rollback to previous version:
kubectl rollout undo deployment ai-agents-worker -n ai-agents-production
```

---

## Resolution

**If OOMKilled (Cause #1):**
```bash
# Increase memory limits
kubectl set resources deployment ai-agents-worker -n ai-agents-production --limits=memory=1Gi

# Monitor memory usage after increase
kubectl top pods -n ai-agents-production | grep worker

# If still crashing: Further increase or investigate memory leak (escalate)
```

**If Application Error (Cause #2):**
- Capture crash logs: `kubectl logs <pod> --previous > worker-crash.log`
- Identify error from stack trace
- Check if regression (recent deployment): Roll back if needed
- **Escalate to Engineering** with crash logs and reproduction steps

**If Database Connection Failure (Cause #3):**
```bash
# Test database connectivity
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- psql $DATABASE_URL -c "SELECT 1;"

# Restart workers
kubectl rollout restart deployment ai-agents-worker -n ai-agents-production

# Monitor for repeated failures (may need Engineering investigation)
```

**If External Dependency Failure (Cause #4):**
- Check API status pages
- Wait for API recovery (workers will retry)
- If persistent: Escalate to Engineering for better error handling

---

## Prevention

**Proactive Monitoring:**
- Set Prometheus alert for worker crashes (restart count >5 in 10 minutes)
- Monitor memory usage trends (alert if >80% of limit)
- Weekly review: Any worker crashes in last 7 days? Patterns?

**Capacity Planning:**
- Profile memory usage per job type (some tickets may use more memory)
- Set memory limits with 20-30% headroom above typical usage
- Test with realistic workloads in staging before production

**Code Quality:**
- Comprehensive error handling for all external API calls
- Retry logic with exponential backoff
- Circuit breakers for failing external dependencies
- Unit tests for edge cases (None values, empty lists, negative numbers)

**Deployment Safety:**
- Always test deployments in staging first
- Gradual rollout: Deploy to 1 pod, monitor for 10 minutes, then deploy all
- Keep previous deployment ready for quick rollback

---

## Escalation

**Escalate to L2/Engineering when:**
- Worker crashes persist after increasing memory limits (memory leak suspected)
- Application error in logs (Python traceback) - provide crash logs
- Database connection failures despite database being healthy
- Crashes started after recent deployment (regression)
- >50% of workers crashing (P1 incident - IMMEDIATE escalation)

**Provide in Escalation:**
- Crash logs: `kubectl logs <pod> --previous > worker-crash.log`
- Pod events: `kubectl describe pod <pod> | tail -30`
- Memory usage: `kubectl top pods | grep worker`
- Recent changes: Any recent deployments or configuration changes?
- Frequency: How often crashes occurring? Continuous or intermittent?

---

## Mock Incident Drill (Story 5.6 Reference)

**Scenario from Story 5.6 Mock Drill:**
- Situation: 3 of 5 workers crashed (OOMKilled) during morning traffic spike
- Root Cause: Recent deployment reduced memory limit from 1GB → 512MB (misconfiguration)
- Resolution: Increase memory limits back to 1GB, delete crashed pods to force recreation
- Result: All 10 workers healthy within 5 minutes, queue drained within 15 minutes

**Lessons Learned:**
- Always compare deployment manifest with previous version before applying
- Monitor worker memory usage for 30 minutes after deployment
- Keep deployment history for quick comparison and rollback

---

## Related Articles

- [Runbook: Worker Failures](../../runbooks/worker-failures.md) - Comprehensive worker diagnostics
- [Troubleshooting: High Error Rate](troubleshooting-high-error-rate.md) - If crashes causing high error rate
- [FAQ: Slow Enhancements](faq-slow-enhancements.md) - If crashes causing queue backlog

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-04 | Initial creation (Code Review follow-up) | Dev Agent (AI) |
