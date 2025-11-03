# API Timeout

**Last Updated:** 2025-11-03
**Author:** Amelia (Developer Agent)
**Related Alerts:** None (manifests as HighLatency or low success rate)
**Severity:** High (if all requests timing out) / Medium (if intermittent)

## Quick Links

- [Symptoms](#symptoms)
- [Diagnosis](#diagnosis)
- [Resolution](#resolution)
- [Escalation](#escalation)
- [Using Distributed Tracing](#using-distributed-tracing-for-diagnosis)

---

## Overview

**When to Use This Runbook:**
- Enhancement failures with "ReadTimeout" or "ConnectTimeout" errors
- External API response times elevated (ServiceDesk Plus, OpenAI, OpenRouter)
- Worker logs showing repeated timeout-related failures and retries
- p95 latency exceeds 120 seconds consistently
- Success rate dropping with timeout-related errors

**Scope:** External API failures, timeout configuration, credential validation, circuit breaker implementation

**Prerequisites:**
- Access to external API status pages
- curl or HTTP client available in worker container
- API credentials for testing (ServiceDesk Plus, OpenAI)
- Distributed tracing (Jaeger) for detailed request analysis

---

## Symptoms

### Observable Indicators

- ✓ Enhancement failures with error message "ReadTimeout" or "ConnectTimeout"
- ✓ Worker logs showing "ConnectError" or "HTTPError" from external APIs
- ✓ p95 latency exceeds 120 seconds persistently
- ✓ ServiceDesk Plus API returning 5xx errors or slow responses
- ✓ OpenAI API returning 429 (rate limit) or 503 (service unavailable)
- ✓ Enhancement success rate declining with timeout errors
- ✓ Timeout errors concentrated at specific times (rate limit or batch processing)

### When This Runbook Does NOT Apply

- Database connectivity issues (see [Database Connection Issues Runbook](./database-connection-issues.md))
- Worker crashing (see [Worker Failures Runbook](./worker-failures.md))
- Queue backing up without timeout errors (see [High Queue Depth Runbook](./high-queue-depth.md))

---

## Diagnosis

### Step 1: Check External API Status Pages

**OpenAI Status Page:**
```bash
# Visit https://status.openai.com
# Check for:
# - Green status (OK)
# - Yellow status (Degraded Performance)
# - Red status (Service Down)

curl -s https://status.openai.com/ | grep -i "status\|incident" | head -5
```

**ServiceDesk Plus (Customer-Specific):**
```bash
# Check your ServiceDesk Plus instance status
# If hosted by vendor, check their status page
# If self-hosted, contact customer's infrastructure team

# Quick test: Try accessing SDP admin console in browser
# If slow or timeout, SDP may be having issues
```

### Step 2: Test ServiceDesk Plus API Manually

**Docker:**
```bash
# Test SDP API response time
time curl -i https://your-sdp-instance/api/v3/tickets \
  -H "Authorization: Bearer $SDP_API_KEY" \
  -H "Content-Type: application/json"

# Expected: 200 OK within 5 seconds
# Output shows time taken by "real" value
```

**Kubernetes:**
```bash
# Test from worker pod
kubectl exec -it deployment/celery-worker -- \
  time curl -i https://your-sdp-instance/api/v3/tickets \
  -H "Authorization: Bearer $SDP_API_KEY"
```

**What to Look For:**
- Response time < 2s: Normal
- Response time 2-10s: Slow but acceptable
- Response time > 10s: Timeout likely
- HTTP 5xx: Service error
- Connection timeout: Network issue or firewall block

### Step 3: Test OpenAI API Manually

**Docker:**
```bash
# Test OpenAI API
time curl -i https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Expected: 200 OK within 2 seconds
```

**Kubernetes:**
```bash
# Test from worker pod
kubectl exec -it deployment/celery-worker -- \
  time curl -i https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

**What to Look For:**
- 200 OK: API responsive
- 401 Unauthorized: Invalid API key
- 429 Too Many Requests: Rate limit exceeded
- 503 Service Unavailable: OpenAI having issues
- Network timeout: Connectivity or firewall issue

### Step 4: Review Worker Logs for Timeout Patterns

**Docker:**
```bash
# Find all timeout-related errors
docker-compose logs worker --tail=500 | grep -i "timeout\|timed out" | head -20

# Find API error patterns
docker-compose logs worker --tail=500 | grep -i "httperror\|connectionerror\|readtimeout"

# Count error frequency by API
docker-compose logs worker | grep -o "api.*timeout" | sort | uniq -c | sort -rn
```

**Kubernetes:**
```bash
# Find timeout errors across all worker pods
kubectl logs -l app=celery-worker --tail=200 | grep -i timeout | head -20
```

**What to Look For:**
- Errors concentrated at specific times (rate limiting pattern)
- Specific API consistently timing out (ServiceDesk Plus vs OpenAI)
- Timeout increasing over time (endpoint degradation)
- Specific tenant causing all timeouts (credential or quota issue)

### Step 5: Check Network Connectivity

**Docker:**
```bash
# Test basic connectivity to API hosts
docker-compose exec worker ping -c 3 api.openai.com

# Test DNS resolution
docker-compose exec worker nslookup api.openai.com

# Trace route to API (if applicable)
docker-compose exec worker traceroute api.openai.com
```

**Kubernetes:**
```bash
# Test from worker pod
kubectl exec -it deployment/celery-worker -- ping -c 3 api.openai.com

# Test DNS
kubectl exec -it deployment/celery-worker -- nslookup api.openai.com
```

**What to Look For:**
- Successful ping: Network connectivity OK
- "no route to host" or "connection refused": Network issue
- DNS lookup failures: DNS problem or domain blocked

### Step 6: Verify API Credentials Validity

**ServiceDesk Plus:**
```bash
# Test authentication with SDP
curl -i -X GET https://your-sdp-instance/api/v3/tickets \
  -H "Authorization: Bearer TEST_TOKEN_HERE" \
  -H "Content-Type: application/json"

# Compare with correct token
curl -i -X GET https://your-sdp-instance/api/v3/tickets \
  -H "Authorization: Bearer $SDP_API_KEY"

# If first fails with 401, credentials invalid or expired
```

**OpenAI:**
```bash
# Check API key validity
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# 401 = invalid/expired key
# 403 = key doesn't have required permissions
```

### Step 7: Check Distributed Traces for Timeout Spans

**Jaeger:**
1. Open http://localhost:16686
2. Search for slow traces: `slow_trace=true` and `duration > 30s`
3. Look at specific API call spans (llm.openai.completion, api.servicedesk_plus.update_ticket)
4. Check span duration - if >30s, that API is bottleneck

---

## Resolution

### If: External Service Degraded (Known Issue)

**Symptom:** API status page shows Yellow/Red, but service eventually responds

**Resolution - Implement Exponential Backoff:**

```bash
# Check if application already has retry logic
docker-compose logs worker | grep -i "retry\|backoff" | head -5

# If not, escalate to engineering to enable retry configuration:
# HTTPX timeout: 30 seconds
# Celery task retries: max_retries=3, exponential backoff
```

**Monitor Situation:**
- Wait for external service to recover
- Monitor success rate improving
- If service still down after 1 hour → escalate to vendor support

### If: Rate Limited (429 Errors from OpenAI)

**Symptom:** OpenAI API returning 429 (Too Many Requests)

**Step 1: Check Current Rate Limit**
```bash
# OpenAI rate limits depend on account tier
# Check your current quota at https://platform.openai.com/account/billing/limits

# Estimate current request rate
docker-compose logs worker --tail=1000 | grep "openai.completion" | wc -l
# Divide by time window to get req/sec
```

**Step 2: Reduce Request Rate (Short Term)**

**Option A - Increase Worker Backoff Delay:**
```bash
# Update environment variable
docker-compose up -d --force-recreate  # After updating docker-compose.yml
# environment:
#   HTTPX_TIMEOUT: 60  # Increase timeout to allow slower responses
#   CELERY_TASK_BACKOFF: 5  # Increase backoff between retries
```

**Option B - Queue Adjustment:**
```bash
# Manually reduce incoming jobs temporarily
# (Pause webhook or rate-limit at API gateway)
```

**Step 3: Request Quota Increase (Long Term)**
- Contact OpenAI support to request higher rate limit
- Provide: Current usage, projected needs, timeline

**Step 4: Implement Circuit Breaker**
- After N consecutive failures, stop calling OpenAI temporarily
- Escalate to engineering for circuit breaker implementation in application code

### If: Credentials Invalid (401/403 Errors)

**Symptom:** API returning 401 Unauthorized or 403 Forbidden

**ServiceDesk Plus - Rotate API Key:**
```bash
# 1. Generate new API key in SDP admin console
# 2. Update Kubernetes secret
kubectl create secret generic sdp-credentials \
  --from-literal=api_key=new_key_here \
  --dry-run=client -o yaml | kubectl apply -f -

# 3. Restart workers to pick up new credentials
kubectl rollout restart deployment/celery-worker

# 4. Verify new credential working
kubectl exec -it deployment/celery-worker -- \
  curl -i https://your-sdp/api/v3/tickets \
  -H "Authorization: Bearer $(kubectl get secret sdp-credentials -o jsonpath='{.data.api_key}' | base64 -d)"
```

**OpenAI - Update API Key:**
```bash
# 1. Generate new API key at https://platform.openai.com/account/api-keys
# 2. Update Kubernetes secret
kubectl create secret generic openai-credentials \
  --from-literal=api_key=new_key_here \
  --dry-run=client -o yaml | kubectl apply -f -

# 3. Restart workers
kubectl rollout restart deployment/celery-worker

# 4. Verify new key working
kubectl exec -it deployment/celery-worker -- \
  curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer new_key_here"
```

### If: Network Issue (Timeout Despite Service Responsive)

**Symptom:** API responds quickly to direct test, but worker times out

**Diagnosis:**
```bash
# Test from different network locations
# 1. From localhost: curl works fine
# 2. From worker pod: curl times out

# Possible causes:
# - Network policy blocking outbound traffic
# - Firewall blocking port 443
# - DNS resolution slow or broken from pod
```

**Resolution:**

**Check Egress Network Policies:**
```bash
# Kubernetes - verify network policies allow HTTPS
kubectl get networkpolicies -A

# If restrictive policy exists, verify API endpoints are whitelisted
# Contact platform team to add endpoints to egress whitelist
```

**Test DNS from Pod:**
```bash
# Verify DNS resolves quickly
kubectl exec -it deployment/celery-worker -- \
  time nslookup api.openai.com

# If slow (>1s), check CoreDNS pod logs
kubectl logs -l k8s-app=kube-dns -n kube-system --tail=50
```

### If: Timeout Configuration Too Aggressive

**Symptom:** Timeouts happen even with responsive APIs (>30 seconds per request)

**Current Configuration:**
```bash
# Check current timeout settings
docker-compose config | grep -i timeout
# or
kubectl get deployment celery-worker -o yaml | grep -i timeout
```

**Increase Timeout (If Justified):**

```bash
# Docker - Update docker-compose.yml
# environment:
#   HTTPX_TIMEOUT: 60  # Increase from default 30

docker-compose up -d worker

# Kubernetes - Update deployment
kubectl set env deployment/celery-worker HTTPX_TIMEOUT=60
kubectl rollout status deployment/celery-worker
```

**Verify Change:**
- Monitor success rate improving
- Check if p95 latency settles at acceptable level

---

## Escalation

### External API Down for 30+ Minutes

- **Severity:** High
- **Action:** Immediate
- **Timeline:** Page on-call engineer
- **Contact:** Vendor support for external API
- **Communicate:** Send customer notification of degraded service

### Rate Limits Consistently Hit

- **Severity:** Medium
- **Action:** Within 1 hour
- **Context:** Request quota insufficient for current demand
- **Resolution:** Contact API provider for quota increase or implement circuit breaker
- **Escalate To:** Engineering team and Product for capacity planning

### Unknown Network Issue (Firewall/Policy Block)

- **Severity:** Medium
- **Action:** Within 2 hours
- **Timeline:** Escalate to platform/DevOps team
- **Context:** Network connectivity issue preventing API access
- **Provide:** Test results (curl works locally, fails from pod) and network policies

---

## Using Distributed Tracing for Diagnosis

### When to Use Distributed Tracing

To identify exactly which API call is slow or failing:

1. Open Jaeger UI: http://localhost:16686
2. Search for slow traces and expand specific trace
3. Look at span timeline to identify bottleneck

### Jaeger Search Examples

**Find traces with OpenAI timeout:**
```
service=worker
tags.llm=openai
duration > 30s
```

**Find traces with ServiceDesk Plus timeout:**
```
service=worker
tags.api=servicedesk_plus
duration > 30s
```

**Find traces with specific error:**
```
error=true
message=timeout
```

### Interpreting Trace Spans

Each enhancement processing trace includes API spans:

- **llm.openai.completion** - Time for OpenAI API call (should be <30s)
- **api.servicedesk_plus.update_ticket** - Time for SDP API call (should be <5s)
- **api.servicedesk_plus.get_ticket** - Time for SDP API read call (should be <2s)

**If span takes 120+ seconds:** API hanging or network issue

**If span has error status:** API returned error (check span attributes for HTTP status)

---

## Fallback and Retry Configuration Examples

### HTTPX Client Retry Configuration

```python
# In worker code, HTTPX client setup:
import httpx
from httpx._models import Response

client = httpx.AsyncClient(
    timeout=30,  # 30 second timeout
    limits=httpx.Limits(max_connections=100),
    retries=3,  # Retry failed requests up to 3 times
)

# Exponential backoff in Celery task:
@app.task(max_retries=3, default_retry_delay=5)
def enhance_ticket(ticket_id):
    # Task retry delays: 5s, 10s, 20s
    try:
        # Call external APIs
        pass
    except httpx.TimeoutException:
        # Retry with exponential backoff
        raise self.retry(countdown=2**self.request.retries)
```

### Celery Task Retry Settings

```python
# In task definition:
@app.task(
    max_retries=3,
    default_retry_delay=10,
    autoretry_for=(httpx.TimeoutException, ConnectionError),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=600,  # Max 10 minutes between retries
    retry_jitter=True,  # Add jitter to prevent thundering herd
)
def enhance_ticket(ticket_id):
    # Celery will automatically retry on timeout or connection error
    pass
```

### Circuit Breaker Implementation

```python
# Simple circuit breaker pattern:
class APICircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half-open

    async def call(self, api_func):
        if self.state == 'open':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'half-open'
            else:
                raise CircuitBreakerOpenException()

        try:
            result = await api_func()
            self.failure_count = 0
            self.state = 'closed'
            return result
        except APIException as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = 'open'
            raise
```

---

## Related Documentation

- **[HighLatency Alert Runbook](../operations/alert-runbooks.md#highlatency)** - Alert-triggered latency procedures
- **[High Queue Depth Runbook](./high-queue-depth.md)** - If queue backing up due to slow API
- **[Database Connection Issues Runbook](./database-connection-issues.md)** - If database context gathering slow
- **[Distributed Tracing Setup](../operations/distributed-tracing-setup.md)** - Jaeger UI and trace analysis
- **[OpenAI API Documentation](https://platform.openai.com/docs/api-reference)** - API reference and rate limits
- **[ServiceDesk Plus API Documentation](https://www.manageengine.com/products/service-desk/help/sdp-integration-guide.html)** - API reference

---

**Status:** ✅ Complete with circuit breaker and retry configuration examples
**Test Status:** Awaiting team member validation (Task 10)
**Last Review:** 2025-11-03
