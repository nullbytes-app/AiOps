# FAQ: Slow Enhancements

**Category:** FAQ - Performance Issue
**Severity:** P2 (if <10min) / P1 (if >10min delay)
**Last Updated:** 2025-11-04
**Related Runbooks:** [High Queue Depth](../../runbooks/high-queue-depth.md), [API Timeout](../../runbooks/api-timeout.md), [Worker Failures](../../runbooks/worker-failures.md)

---

## Quick Answer

**Most common causes:** High queue depth (workers overloaded), external API latency (OpenAI/ServiceDesk Plus slow), or insufficient worker capacity (HPA not scaling fast enough). Check queue depth → worker count → API latencies in that order.

---

## Symptoms

**Client Reports:**
- "Enhancements taking 5-15 minutes to arrive"
- "Usually fast, but slow during morning hours"
- "Quality is good, just delayed"

**Observable Indicators:**
- Queue depth >20 jobs in Grafana
- p95 latency >60 seconds (target: <60s)
- Workers at max capacity (CPU >80%)
- HPA slow to scale up during traffic spikes

---

## Common Causes

### 1. High Queue Depth (45% of cases)

**Root Cause:** More jobs arriving than workers can process

**Possible Reasons:**
- Traffic spike (client peak hours: 8-10am, 1-3pm)
- Workers scaled down overnight, slow to scale up in morning
- Worker processing time increased (external API slow)

**How to Identify:**
```bash
# Check current queue depth
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- redis-cli -h redis LLEN celery

# Result: >50 jobs = high backlog, >20 jobs = moderate backlog
# Check Grafana Operations Dashboard → Queue Depth trend over time
```

**Resolution:**
```bash
# Immediate: Scale workers manually
kubectl scale deployment ai-agents-worker -n ai-agents-production --replicas=10

# Monitor queue draining in Grafana (should decrease within 5-10 minutes)

# Long-term: Review HPA configuration
kubectl get hpa -n ai-agents-production
# Ensure targetCPUUtilizationPercentage is 60-70% (not 80%) for faster scaling
```

---

### 2. External API Latency (30% of cases)

**Root Cause:** ServiceDesk Plus or OpenAI API responding slowly

**Possible Reasons:**
- ServiceDesk Plus server overloaded or network issues
- OpenAI rate limiting or regional outage
- Network connectivity issues between Kubernetes and external APIs

**How to Identify:**
```bash
# Check API latency metrics in Grafana
# Operations Dashboard → "External API Latency" panel
# Look for: ServiceDesk Plus p95 >2s, OpenAI p95 >5s

# Check worker logs for timeout patterns
kubectl logs deployment/ai-agents-worker -n ai-agents-production --tail=100 | grep -i "timeout\|slow"
```

**Resolution:**
```bash
# Check ServiceDesk Plus API health
curl -s -w "\nTime: %{time_total}s\n" "https://servicedesk-plus-url/api/v3/tickets?limit=1"
# Expected: <1 second. If >3 seconds, ServiceDesk Plus is slow.

# Check OpenAI API status: https://status.openai.com
# If degraded: Wait for recovery, enhancements will resume automatically

# Workaround: Increase timeout thresholds temporarily (requires Engineering)
```

---

### 3. Insufficient Worker Capacity (20% of cases)

**Root Cause:** HPA (Horizontal Pod Autoscaler) not scaling workers fast enough

**Possible Reasons:**
- HPA configured with high CPU threshold (>80%)
- HPA scaleUp policy too conservative (only adds 1 pod at a time)
- Worker resource requests too low (triggers scaling too late)

**How to Identify:**
```bash
# Check worker count vs desired count
kubectl get hpa -n ai-agents-production
# Look for: currentReplicas < desiredReplicas (scaling in progress)
# Look for: currentReplicas at max but queue still high (need higher max)

# Check worker CPU utilization
kubectl top pods -n ai-agents-production | grep worker
# If all workers >80% CPU → need more replicas
```

**Resolution:**
```bash
# Immediate: Manually scale to handle load
kubectl scale deployment ai-agents-worker -n ai-agents-production --replicas=<desired>

# Long-term: Adjust HPA policy (requires Engineering)
# - Lower CPU threshold: 60-70% instead of 80%
# - Increase maxReplicas: 15 instead of 10
# - Faster scaleUp: add 50% pods instead of 1 pod at a time
```

---

### 4. Database Query Slow (5% of cases)

**Root Cause:** Database queries taking longer than expected

**Possible Reasons:**
- Missing indexes on frequently queried columns
- Connection pool exhaustion (too many concurrent queries)
- RLS policies causing slow query plans

**How to Identify:**
```bash
# Check database connection pool
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'ai_agents';"
# Result: >80% of max_connections indicates pool exhaustion

# Check slow queries in database
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- psql $DATABASE_URL -c "SELECT query, calls, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"
# Look for queries with mean_exec_time >100ms
```

**Resolution:**
- **Escalate to Engineering** for slow query optimization
- Provide slow query results from pg_stat_statements
- Short-term: Restart workers to reset connection pool
- Long-term: Add indexes, optimize RLS policies

---

## Diagnosis Steps

**Step 1: Check Queue Depth**
```bash
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- redis-cli -h redis LLEN celery
```
Expected result: <20 jobs = healthy, 20-50 = elevated, >50 = high backlog

**Step 2: Check Worker Health and Count**
```bash
kubectl get pods -n ai-agents-production | grep worker
kubectl top pods -n ai-agents-production | grep worker
```
Expected result: All workers Running, CPU <80%, count matches expected load

**Step 3: Check External API Latencies**
- Open Grafana Operations Dashboard
- Check "External API Latency" panel
- Look for spikes in ServiceDesk Plus or OpenAI response times

**Step 4: Check p95 Enhancement Latency Trend**
- Open Grafana Baseline Metrics Dashboard
- Check "p95 Enhancement Latency" panel
- Identify when slowdown started and correlate with queue depth / worker changes

---

## Resolution

**If High Queue Depth (Cause #1):**
- Scale workers immediately: `kubectl scale deployment ai-agents-worker -n ai-agents-production --replicas=10`
- Monitor queue draining over 10-15 minutes
- Scale back down once queue <20: `kubectl scale deployment ai-agents-worker -n ai-agents-production --replicas=5`

**If External API Latency (Cause #2):**
- Check ServiceDesk Plus API health with test request
- Check OpenAI status page: https://status.openai.com
- If degraded: Wait for recovery (no action needed)
- Communicate to client: "Temporary delays due to external API provider, resolving automatically"

**If Insufficient Worker Capacity (Cause #3):**
- Manually scale workers to handle current load
- Escalate to Engineering to adjust HPA policy
- Provide metrics: current CPU %, queue depth trend, latency impact

**If Database Query Slow (Cause #4):**
- Escalate to Engineering with slow query diagnostics
- Provide pg_stat_statements output
- Short-term: Restart workers if connection pool exhausted

---

## Prevention

**Proactive Monitoring:**
- Set Prometheus alert for queue depth >50 (5-minute window)
- Review weekly metrics: Are peak hours consistently causing slowdowns?
- Monitor HPA scaling behavior: Is it scaling fast enough?

**Capacity Planning:**
- Adjust HPA maxReplicas based on client growth
- Review worker resource requests/limits quarterly
- Test scaling behavior during simulated traffic spikes

**External API Resilience:**
- Implement circuit breaker patterns (requires Engineering)
- Cache ServiceDesk Plus API responses where possible
- Monitor OpenAI API status proactively

---

## Escalation

**Escalate to L2/Engineering when:**
- Queue depth remains high (>50) despite manual worker scaling
- External API latencies persist for >30 minutes
- HPA not scaling despite high CPU utilization
- Database queries consistently slow (>100ms mean time)
- Client reporting >15 minute delays (P1 incident)

**Provide in Escalation:**
- Queue depth trend (screenshot from Grafana)
- Worker count and CPU utilization
- External API latency metrics
- Time when slowdown started
- Client impact (how many tickets affected)

---

## Related Articles

- [FAQ: Enhancements Not Received](faq-enhancements-not-received.md) - If enhancements not arriving at all
- [Troubleshooting: Worker Crashes](troubleshooting-worker-crashes.md) - If workers crashing under load
- [Troubleshooting: High Error Rate](troubleshooting-high-error-rate.md) - If slow enhancements also failing

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-04 | Initial creation (Code Review follow-up) | Dev Agent (AI) |
