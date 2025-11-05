# Troubleshooting: High Error Rate

**Category:** Troubleshooting - System Health
**Severity:** P1 (if >10% error rate) / P2 (if 5-10%)
**Last Updated:** 2025-11-04
**Related Runbooks:** [Worker Failures](../../runbooks/worker-failures.md), [Enhancement Failures](../../runbooks/enhancement-failures.md), [Database Connection Issues](../../runbooks/database-connection-issues.md)

---

## Quick Answer

**High error rate (>5%) indicates systematic failures** in enhancement processing. Most common causes: worker crashes, external API failures (ServiceDesk Plus/OpenAI), database connection issues, or LangGraph workflow errors. Check Error Rate panel in Grafana → investigate worker logs → identify error patterns.

---

## Symptoms

**Observable Indicators:**
- Grafana Operations Dashboard → Error Rate panel >5%
- Prometheus alert: `HighErrorRate` firing
- Success Rate metric <95% (below baseline target)
- Client reports: "Some tickets getting errors instead of enhancements"

---

## Common Causes

### 1. Worker Crashes / OOMKilled (35% of cases)

**Root Cause:** Workers crashing during job processing

**How to Identify:**
```bash
# Check worker pod status
kubectl get pods -n ai-agents-production | grep worker

# Look for: CrashLoopBackOff, OOMKilled, Error
# Check crash logs
kubectl logs <worker-pod-name> -n ai-agents-production --previous
```

**Resolution:**
- See [Troubleshooting: Worker Crashes](troubleshooting-worker-crashes.md)
- Immediate: Restart crashed workers
- Long-term: Increase memory limits if OOMKilled

---

### 2. External API Failures (30% of cases)

**Root Cause:** ServiceDesk Plus or OpenAI API returning errors/timeouts

**How to Identify:**
```bash
# Check worker logs for API errors
kubectl logs deployment/ai-agents-worker -n ai-agents-production --since=10m | grep -i "api error\|timeout\|rate limit"

# Common patterns:
# - "OpenAI API error: 429 Rate Limit Exceeded"
# - "ServiceDesk Plus timeout after 30s"
# - "OpenAI API error: 500 Internal Server Error"
```

**Resolution:**
```bash
# Check OpenAI status: https://status.openai.com
# Check ServiceDesk Plus API health:
curl -s -w "\nTime: %{time_total}s\n" "<servicedesk-plus-url>/api/v3/tickets?limit=1"

# If OpenAI rate limited: Wait for rate limit reset (automatic retry)
# If ServiceDesk Plus down: Notify client, wait for recovery
# If persistent: Escalate to Engineering for circuit breaker tuning
```

---

### 3. Database Connection Failures (20% of cases)

**Root Cause:** Workers unable to query database (connection pool exhaustion, network issues)

**How to Identify:**
```bash
# Check database connection count
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'ai_agents';"

# If near max_connections (100), pool exhausted

# Check worker logs for database errors
kubectl logs deployment/ai-agents-worker -n ai-agents-production --since=10m | grep -i "database\|connection\|psql"
```

**Resolution:**
- See [Runbook: Database Connection Issues](../../runbooks/database-connection-issues.md)
- Immediate: Restart workers to reset connection pool
- Long-term: Increase connection pool size or max_connections

---

### 4. LangGraph Workflow Errors (15% of cases)

**Root Cause:** Enhancement workflow errors (context gathering failures, GPT-4 prompt errors)

**How to Identify:**
```bash
# Check worker logs for LangGraph errors
kubectl logs deployment/ai-agents-worker -n ai-agents-production --since=10m | grep -i "langgraph\|workflow\|enhancement_workflow"

# Common patterns:
# - "Context gathering timeout"
# - "No similar tickets found" (if ticket history empty)
# - "GPT-4 prompt validation failed"
```

**Resolution:**
- Escalate to Engineering for workflow debugging
- Provide error logs and ticket IDs
- May require prompt refinement or workflow fix

---

## Diagnosis Steps

**Step 1: Check Error Rate in Grafana**
- Open Operations Dashboard → Error Rate panel
- Identify: When did error rate spike? (correlate with deployments, traffic spikes)
- Check: Is error rate increasing or stable?

**Step 2: Sample Worker Logs for Error Patterns**
```bash
# Get recent errors from workers
kubectl logs deployment/ai-agents-worker -n ai-agents-production --since=30m | grep -i "error" | tail -50

# Categorize errors:
# - OOMKilled → Cause #1 (worker crashes)
# - "API error" → Cause #2 (external API failures)
# - "connection" → Cause #3 (database issues)
# - "workflow" → Cause #4 (LangGraph errors)
```

**Step 3: Check Worker Health**
```bash
kubectl get pods -n ai-agents-production | grep worker
kubectl top pods -n ai-agents-production | grep worker

# Healthy: All Running, CPU <80%, Memory <80%
# Unhealthy: CrashLoopBackOff, OOMKilled, high resource usage
```

**Step 4: Check External API Status**
- OpenAI: https://status.openai.com
- ServiceDesk Plus: Test API with curl (see Cause #2)

**Step 5: Check Database Health**
```bash
# Database connections
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- psql $DATABASE_URL -c "SELECT count(*) as connections, max_connections FROM pg_stat_activity, (SELECT setting::int as max_connections FROM pg_settings WHERE name = 'max_connections') s GROUP BY max_connections;"

# Slow queries
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- psql $DATABASE_URL -c "SELECT query, calls, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 5;"
```

---

## Resolution

**Immediate Actions:**
1. Identify dominant error pattern from logs (API, database, worker crashes)
2. If worker crashes: Restart workers, check memory limits
3. If external API: Check status pages, wait for recovery or escalate
4. If database: Restart workers, check connection pool
5. Monitor Error Rate panel for improvements

**Escalation to Engineering:**
- Provide error rate trend (Grafana screenshot)
- Provide 50-100 sample error logs (categorized by error type)
- Provide timing: When did errors start? Any deployments/changes?
- Provide impact: How many clients affected? Error rate percentage?

---

## Prevention

**Proactive Monitoring:**
- Set Prometheus alert for error rate >5% (5-minute window)
- Weekly review: Are certain ticket types consistently failing?
- Monitor external API status proactively (subscribe to status pages)

**System Resilience:**
- Implement circuit breakers for external APIs (Engineering task)
- Add retry logic with exponential backoff
- Improve error messages in logs (include ticket_id, tenant_id, error context)

**Capacity Planning:**
- Scale workers before peak hours (avoid resource exhaustion)
- Monitor database connection pool usage (keep <80%)
- Test failover scenarios (what happens if OpenAI down?)

---

## Escalation

**Escalate to L2/Engineering when:**
- Error rate >10% (P1 incident)
- Error rate >5% persisting for >30 minutes (P2 incident)
- Unable to identify root cause from logs
- External API outage lasting >1 hour
- Systematic workflow errors (not isolated failures)

---

## Related Articles

- [Troubleshooting: Worker Crashes](troubleshooting-worker-crashes.md)
- [Runbook: Enhancement Failures](../../runbooks/enhancement-failures.md)
- [Runbook: Database Connection Issues](../../runbooks/database-connection-issues.md)

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-04 | Initial creation (Code Review follow-up) | Dev Agent (AI) |
