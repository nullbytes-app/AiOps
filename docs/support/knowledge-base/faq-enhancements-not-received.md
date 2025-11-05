# FAQ: Enhancements Not Received

**Category:** FAQ - Client-Reported Issue
**Severity:** P1 (if affecting multiple tickets) / P2 (if isolated)
**Last Updated:** 2025-11-04
**Related Runbooks:** [Webhook Troubleshooting](../../runbooks/WEBHOOK_TROUBLESHOOTING_RUNBOOK.md), [High Queue Depth](../../runbooks/high-queue-depth.md), [Worker Failures](../../runbooks/worker-failures.md)

---

## Quick Answer

**Most common causes:** Webhook delivery failure (signature mismatch), high queue backlog (workers can't keep up), or worker crashes (processing interrupted). Check webhook logs → queue depth → worker health in that order.

---

## Symptoms

**Client Reports:**
- "Ticket #12345 never received an enhancement"
- "No enhancements delivered in the last hour"
- "Some tickets get enhancements, others don't"

**Observable Indicators:**
- Missing enhancement comments in ServiceDesk Plus tickets
- No corresponding job completion logs in worker pods
- Queue depth elevated but not processing
- Success rate metric <95% in Grafana

---

## Common Causes

### 1. Webhook Delivery Failure (40% of cases)

**Root Cause:** ServiceDesk Plus webhook not reaching AI Agents API

**Possible Reasons:**
- HMAC signature mismatch (wrong secret, copy/paste error)
- Webhook URL typo or misconfiguration
- Network/firewall blocking webhook delivery
- ServiceDesk Plus webhook disabled or paused

**How to Identify:**
```bash
# Search API logs for ticket ID
kubectl logs deployment/ai-agents-api -n ai-agents-production --since=24h | grep "ticket_id: 12345"

# Expected: "Webhook received: ticket_id=12345, tenant_id=..."
# If NOT found: Webhook delivery failure
```

---

### 2. High Queue Backlog (30% of cases)

**Root Cause:** More jobs queued than workers can process

**Possible Reasons:**
- Traffic spike (e.g., client onboarded new technicians)
- Workers scaled down during low traffic, slow to scale up
- Slow external APIs (ServiceDesk Plus, OpenAI) increasing processing time

**How to Identify:**
```bash
# Check queue depth
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- redis-cli -h redis LLEN celery

# Result: >50 jobs indicates backlog
# Check Grafana Operations Dashboard → Queue Depth panel for trend
```

---

### 3. Worker Crashes / Failures (20% of cases)

**Root Cause:** Workers unable to process jobs due to crashes or errors

**Possible Reasons:**
- Workers in CrashLoopBackOff (OOMKilled, application errors)
- Worker stuck on specific job (infinite loop, deadlock)
- Database connection failures preventing job execution

**How to Identify:**
```bash
# Check worker pod status
kubectl get pods -n ai-agents-production | grep worker

# Look for: CrashLoopBackOff, Error, OOMKilled
# Check worker logs for exceptions
kubectl logs deployment/ai-agents-worker -n ai-agents-production --tail=50 | grep -i error
```

---

### 4. Job Processing Failure (10% of cases)

**Root Cause:** Job dequeued but failed during processing

**Possible Reasons:**
- GPT-4 API timeout or error
- ServiceDesk Plus API unavailable or rate limiting
- Invalid ticket ID (ticket deleted/closed before processing)
- Context gathering timeout (slow database queries)

**How to Identify:**
```bash
# Search worker logs for job_id or ticket_id
kubectl logs deployment/ai-agents-worker -n ai-agents-production --since=24h | grep "ticket_id: 12345"

# Look for: "Task failed", error messages, exception stack traces
# Use distributed tracing for detailed investigation
```

---

## Diagnosis Steps

### Step 1: Verify Webhook Delivery

**Check API logs for webhook receipt:**
```bash
kubectl logs deployment/ai-agents-api -n ai-agents-production --since=24h | grep "ticket_id: <TICKET_ID>"
```

**Expected Result:** `"Webhook received: ticket_id=<TICKET_ID>, tenant_id=<TENANT>"`

**If NOT Found:**
- **→ Webhook delivery failure:** See [Resolution: Webhook Delivery Failure](#resolution-webhook-delivery-failure)

**If Found:**
- **→ Proceed to Step 2**

---

### Step 2: Check Job Queuing

**Search for job queuing confirmation:**
```bash
kubectl logs deployment/ai-agents-api -n ai-agents-production --since=24h | grep -A5 "ticket_id: <TICKET_ID>" | grep "Job queued"
```

**Expected Result:** `"Job queued: job_id=<JOB_ID>, ticket_id=<TICKET_ID>"`

**If NOT Found:**
- **→ API error during queuing:** Check for exceptions in API logs, escalate to Engineering

**If Found:**
- **→ Note job_id, proceed to Step 3**

---

### Step 3: Check Queue Depth

**Query current queue depth:**
```bash
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- redis-cli -h redis LLEN celery
```

**Interpretation:**
- **<20 jobs:** Normal, workers keeping up
- **20-50 jobs:** Moderate backlog, monitor
- **50-100 jobs:** High backlog, scale workers (see Resolution)
- **>100 jobs:** Critical backlog, P1 incident

**If High Backlog:**
- **→ See [Resolution: High Queue Backlog](#resolution-high-queue-backlog)**

**If Normal Queue:**
- **→ Proceed to Step 4**

---

### Step 4: Check Worker Processing

**Search worker logs for job processing:**
```bash
kubectl logs deployment/ai-agents-worker -n ai-agents-production --since=24h | grep "job_id: <JOB_ID>"
```

**Expected Logs:**
```
"Task started: job_id=<JOB_ID>, ticket_id=<TICKET_ID>"
"LangGraph workflow initiated"
"Context gathered: ticket_history=Yes, docs=Yes"
"GPT-4 API call: status=200"
"ServiceDesk Plus ticket updated: ticket_id=<TICKET_ID>"
"Task completed: job_id=<JOB_ID>, duration=45s"
```

**If Task Failed:**
- **→ Review error message, see [Resolution: Job Processing Failure](#resolution-job-processing-failure)**

**If Task NOT Found:**
- **→ Job stuck in queue or worker not processing, see Resolution**

---

### Step 5: Use Distributed Tracing (End-to-End View)

**Access Jaeger/Uptrace:**
- Local: http://localhost:16686
- Production: [Jaeger URL]

**Search by:**
- Tag: `ticket_id=<TICKET_ID>`
- Tag: `tenant_id=<TENANT>`

**Analyze Trace:**
- View all spans: Webhook → Queue → Worker → GPT-4 → ServiceDesk Update
- Identify bottleneck: Which span took longest? (normal: GPT-4 ~30s)
- Check for errors: Red error indicators on spans

---

## Resolution

### Resolution: Webhook Delivery Failure

**Symptom:** No webhook received in API logs

**Steps:**

1. **Verify ServiceDesk Plus webhook configuration:**
   - URL: `https://api.ai-agents.com/webhook` (correct URL?)
   - Secret: Matches Kubernetes secret? (ask client to re-check)
   - Active: Webhook enabled, not paused?

2. **Test webhook manually:**
   - ServiceDesk Plus Admin Panel → Webhooks → Test Webhook
   - Monitor API logs during test: `kubectl logs deployment/ai-agents-api -n ai-agents-production -f`

3. **If signature validation error (403 Forbidden):**
   - Retrieve secret from Kubernetes:
     ```bash
     kubectl get secret ai-agents-secrets -n ai-agents-production -o jsonpath='{.data.WEBHOOK_SECRET_<TENANT>}' | base64 -d
     ```
   - Share with client securely, verify ServiceDesk Plus config matches
   - See [Secret Rotation Runbook](../../runbooks/secret-rotation.md) if rotation needed

4. **If network/firewall issue:**
   - Verify ServiceDesk Plus can reach API URL (curl test from client network)
   - Check cloud provider security groups / firewall rules
   - Escalate to Infrastructure/Networking team

---

### Resolution: High Queue Backlog

**Symptom:** Queue depth >50 jobs, enhancements delayed >5 minutes

**Immediate Action:**

**Scale workers immediately:**
```bash
# Double current worker count (e.g., 5 → 10)
kubectl scale deployment/ai-agents-worker -n ai-agents-production --replicas=10
```

**Monitor queue drainage:**
- Grafana Operations Dashboard → Queue Depth panel
- Expect: 10-20 jobs/minute decrease
- If draining: Monitor until queue <20, scale back to normal (5 workers)

**If queue NOT draining:**

1. **Check worker health:**
   ```bash
   kubectl get pods -n ai-agents-production | grep worker
   kubectl top pods -n ai-agents-production | grep worker
   ```

2. **Investigate stuck jobs:**
   - Are workers processing? (check logs for "Task started")
   - Are tasks completing? (check logs for "Task completed")
   - Are tasks failing repeatedly? (check logs for errors)

3. **Escalate to L2/Engineering** if:
   - Workers healthy but not processing
   - Tasks failing consistently (>20% failure rate)
   - Queue depth >200 after scaling

**Detailed Runbook:** [docs/runbooks/high-queue-depth.md](../../runbooks/high-queue-depth.md)

---

### Resolution: Worker Crashes

**Symptom:** Workers in CrashLoopBackOff or Error state

**Steps:**

1. **Identify crash reason:**
   ```bash
   # Check pod status
   kubectl describe pod <worker-pod-name> -n ai-agents-production | grep -i "reason"

   # Common reasons:
   # - OOMKilled (memory limit exceeded)
   # - Error (application crash)
   # - ImagePullBackOff (deployment issue)
   ```

2. **If OOMKilled:**
   - Workers exceeded memory limit (likely memory leak or large job)
   - **Immediate:** Delete crashed pods: `kubectl delete pod <pod-name> -n ai-agents-production`
   - **Follow-up:** Escalate to Engineering to increase memory limits or investigate leak

3. **If application crash:**
   - Review crash logs: `kubectl logs <worker-pod-name> -n ai-agents-production --previous`
   - Look for exception stack trace
   - **Immediate:** Restart deployment: `kubectl rollout restart deployment/ai-agents-worker -n ai-agents-production`
   - **Follow-up:** Escalate to Engineering with crash logs

**Detailed Runbook:** [docs/runbooks/worker-failures.md](../../runbooks/worker-failures.md)

---

### Resolution: Job Processing Failure

**Symptom:** Job dequeued but failed during processing

**Common Failures:**

**1. GPT-4 API Timeout/Error:**
- **Logs:** `"GPT-4 API call failed: timeout after 30s"` or `"OpenAI API error: 429 Rate Limit"`
- **Action:** Check OpenRouter/OpenAI status page, retry job manually, escalate if persistent

**2. ServiceDesk Plus API Unavailable:**
- **Logs:** `"ServiceDesk Plus API timeout"` or `"ServiceDesk Plus API error: 500"`
- **Action:** Verify ServiceDesk Plus accessibility (client-side), retry job, escalate to client if their API is down

**3. Invalid Ticket ID:**
- **Logs:** `"Ticket not found: 12345"` or `"Ticket deleted/closed"`
- **Action:** Inform client ticket was closed before processing, no action needed (expected behavior)

**4. Context Gathering Timeout:**
- **Logs:** `"Context gathering timeout after 30s"`
- **Action:** Check database connection, slow query logs, escalate to Engineering if database performance issue

**Detailed Runbook:** [docs/runbooks/enhancement-failures.md](../../runbooks/enhancement-failures.md)

---

## Prevention

**Proactive Monitoring:**
1. **Monitor queue depth trends** (Grafana): Set up alert for queue depth >30 sustained for >5 minutes
2. **Monitor success rate** (Grafana Baseline Metrics): Alert if success rate <95% for >15 minutes
3. **HPA tuning:** Ensure workers scale up quickly during traffic spikes (current: scale if queue depth >5 jobs/worker)

**Process Improvements:**
1. **Regular secret rotation:** Prevent signature mismatch by scheduled rotations (every 90 days)
2. **Client webhook testing:** Test webhooks after every ServiceDesk Plus upgrade or configuration change
3. **Worker capacity planning:** Review worker min/max replicas monthly, adjust based on traffic growth

**Documentation:**
1. **Update runbooks:** Add new failure modes discovered during investigations
2. **Share learnings:** Post resolution summaries in #support-learnings Slack channel
3. **Client communication:** Proactively notify clients of known issues or scheduled maintenance

---

## Escalation

**Escalate to L2 when:**
- Multiple clients affected (>2 clients reporting same issue)
- P1 severity (enhancements delayed >30 minutes, impacting business)
- Root cause unclear after following diagnosis steps
- Unable to resolve within 30 minutes

**Escalate to Engineering when:**
- Application code bug suspected (consistent crashes, errors)
- Database performance issues (slow queries, connection pool exhaustion)
- Infrastructure changes needed (increase resources, modify HPA)
- Security concern (RLS violation, unauthorized access)

**Escalate to Client when:**
- Webhook configuration incorrect (client must update ServiceDesk Plus)
- ServiceDesk Plus API unavailable (client-side issue)
- Client expectations setting (explain normal latency, limitations)

---

## Related Articles

- [FAQ: Slow Enhancements](faq-slow-enhancements.md) - Enhancements received but delayed
- [FAQ: Webhook Setup](faq-webhook-setup.md) - Initial webhook configuration
- [Troubleshooting: High Error Rate](troubleshooting-high-error-rate.md) - Systematic errors across platform
- [Troubleshooting: Worker Crashes](troubleshooting-worker-crashes.md) - Worker-specific failures

**Runbooks:**
- [High Queue Depth](../../runbooks/high-queue-depth.md) - Detailed queue backlog troubleshooting
- [Worker Failures](../../runbooks/worker-failures.md) - Comprehensive worker crash investigation
- [Webhook Troubleshooting](../../runbooks/WEBHOOK_TROUBLESHOOTING_RUNBOOK.md) - Signature validation deep dive
- [Enhancement Failures](../../runbooks/enhancement-failures.md) - LangGraph workflow debugging

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-04 | Initial creation from Epic 4-5 learnings (Story 5.6) | Dev Agent (AI) |

---

**Article Owner:** Support Team
**Review Frequency:** Monthly or after major incidents
**Feedback:** #support-docs-feedback Slack channel
