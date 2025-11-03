# Distributed Tracing Setup Guide

## Overview

Distributed tracing with OpenTelemetry provides end-to-end visibility into ticket enhancement workflows spanning multiple services (FastAPI webhook receiver → Redis queue → Celery workers → External APIs). This guide documents the OpenTelemetry deployment, Jaeger backend setup, configuration, and trace visualization.

**Story Reference:** Story 4.6 - Implement Distributed Tracing with OpenTelemetry

---

## Architecture

```
Complete Observability Stack:

Metrics (Story 4.1-4.2):    "What is happening?" (aggregates over time)
  → Prometheus collects CPU, memory, request count, latency histogram

Alerts (Story 4.4-4.5):     "When did something go wrong?" (firing status)
  → Prometheus alert rules fire; Alertmanager notifies Slack/PagerDuty

Traces (Story 4.6):         "Why did it happen?" (causality + timing)
  → OpenTelemetry + Jaeger shows complete request flow with bottlenecks
```

**Trace Flow Architecture:**

```
Webhook Request (FastAPI)
  ↓ [HTTP span: POST /webhook/servicedesk]
  ├─ Validate signature, extract ticket_id, tenant_id
  │
  └─ Queue enhancement job to Redis
     ↓ [custom span: job_queued]
     └─ Add trace context to job headers (traceparent)
        ↓
        └─ Celery Worker Dequeues Job
           ↓ [Celery task span: enhance_ticket]
           ├─ Context Gathering Phase
           │  ↓ [custom span: context_gathering]
           │  ├─ [child span: context.ticket_history] - Query ticket history (25s)
           │  ├─ [child span: context.documentation] - Search docs (3s)
           │  └─ [child span: context.ip_lookup] - IP cross-reference (2s)
           │
           ├─ LLM Synthesis Phase
           │  ↓ [custom span: llm.openai.completion]
           │  └─ Call OpenAI API with context (15s)
           │
           └─ Ticket Update Phase
              ↓ [custom span: api.servicedesk_plus.update_ticket]
              └─ Update ServiceDesk Plus with enhancement (14s)

TOTAL TRACE: 60 seconds (all spans within single trace_id)
BOTTLENECK IDENTIFIED: context.ticket_history = 25s (42% of total)
```

**Key Components:**

1. **OpenTelemetry SDK** - Instrumentation and span creation
   - FastAPI automatic instrumentation (HTTP spans)
   - Celery automatic instrumentation (task spans)
   - Custom spans for enhancement workflow phases

2. **Context Propagation** - Manual carrier injection for Redis queue boundary
   - Extract trace context from FastAPI request
   - Inject into Celery task headers
   - Extract in Celery worker to continue trace

3. **Span Processors**
   - BatchSpanProcessor: Batches spans for efficient export (1000 spans/batch)
   - RedactionSpanProcessor: Logs sensitive attribute detection
   - SlowTraceProcessor: Logs spans exceeding 60s threshold

4. **Exporter Wrapper** - Custom OTLP exporter that:
   - Redacts sensitive attributes (api_key, secret, token) → "[REDACTED]"
   - Tags slow spans (>60s) with slow_trace=true attribute
   - Forwards to Jaeger via OTLP (gRPC on port 4317)

5. **Jaeger Backend** - Distributed tracing backend
   - Receives traces via OTLP
   - Stores spans in memory (all-in-one) or persistent backend
   - Web UI on port 16686 for trace visualization and search

---

## Deployment

### Local Development (Docker Compose)

**Configuration Files:**
- `docker-compose.yml` - Jaeger service definition (all-in-one image)
- `.env` - Environment variables (OTEL_* configuration)
- `src/monitoring/tracing.py` - OpenTelemetry initialization

**Startup:**

```bash
# Start full stack (includes Jaeger)
docker-compose up -d

# Start only Jaeger (if other services already running)
docker-compose up -d jaeger

# Verify Jaeger is healthy
curl http://localhost:16686/

# View logs
docker-compose logs -f jaeger

# Stop Jaeger
docker-compose down jaeger
```

**Ports:**
- `16686` - Jaeger UI (http://localhost:16686)
- `4317` - OTLP gRPC receiver (traces exported here from application)
- `4318` - OTLP HTTP receiver (alternative to gRPC)
- `6831` - Jaeger agent (UDP, for agent-based trace submission)
- `6832` - Jaeger agent (UDP compact format)

**Health Check:**

```bash
# Jaeger UI endpoint
curl -s http://localhost:16686/ | head -20

# Expected: HTML response with Jaeger UI
```

### Production (Kubernetes)

**Configuration Files:**
- `k8s/jaeger-deployment.yaml` - Deployment, Service, optional PVC
- `.env` (production) - OTEL_EXPORTER_OTLP_ENDPOINT should point to Jaeger service

**Deployment:**

```bash
# Deploy Jaeger to Kubernetes
kubectl apply -f k8s/jaeger-deployment.yaml

# Verify deployment
kubectl get pods | grep jaeger
kubectl get svc jaeger

# View logs
kubectl logs -f deployment/jaeger

# Check service connectivity
kubectl port-forward svc/jaeger 16686:16686
# Then access: http://localhost:16686
```

**Kubernetes Manifest Highlights:**

```yaml
# k8s/jaeger-deployment.yaml includes:
- Deployment: Jaeger all-in-one container
  - Resource limits: CPU 200m request / 1000m limit
  - Memory: 512Mi request / 2Gi limit
  - Liveness probe: HTTP GET / every 10s
  - Readiness probe: HTTP GET / every 10s

- Service: Exposes Jaeger ports
  - Type: ClusterIP (internal only, more secure)
  - Ports: 16686 (UI), 4317 (OTLP gRPC), 4318 (OTLP HTTP)

- PersistentVolumeClaim (optional): For trace persistence
  - Default: In-memory storage (traces lost on restart)
  - For production: Add PVC + Elasticsearch/Cassandra backend
```

**Production Considerations:**

1. **Persistent Storage**
   - All-in-one image uses in-memory storage (traces lost on pod restart)
   - For production: Use Jaeger with persistent backend:
     - **Elasticsearch**: Recommended for 100M+ spans/day
     - **Cassandra**: Recommended for large-scale deployments
     - **GCS/S3**: Cloud-native option via Jaeger operator

2. **Access Control**
   - Jaeger UI exposed via ClusterIP service (internal only)
   - For external access: Use Ingress with authentication
   - Example: Add OAuth2 proxy in front of Jaeger UI

3. **Trace Retention**
   - All-in-one: 72-hour default retention
   - Elasticsearch: Configure index retention per needs
   - Monitor storage usage: Jaeger can consume significant disk space

4. **Performance Optimization**
   - Sampling rate in production: 0.01-0.1 (1-10% of traces)
   - BatchSpanProcessor: queue_size=2048, batch_size=512 (configured in code)
   - Monitor OTLP exporter latency to Jaeger

---

## Configuration

### Environment Variables

**File:** `.env` (or Kubernetes ConfigMap/Secret)

```bash
# OpenTelemetry Configuration
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317    # Jaeger collector (gRPC)
OTEL_SERVICE_NAME=ai-agents-enhancement           # Service name in traces
OTEL_TRACES_SAMPLER=traceidratio                  # Sampling strategy
OTEL_TRACES_SAMPLER_ARG=0.1                       # 10% sampling (100 traces/day for 1000 tickets)
DEPLOYMENT_ENV=production                         # Environment tag for traces
```

**Configuration Details:**

| Variable | Default | Purpose | Notes |
|----------|---------|---------|-------|
| OTEL_EXPORTER_OTLP_ENDPOINT | http://jaeger:4317 | Jaeger collector address | Must be reachable from application |
| OTEL_SERVICE_NAME | ai-agents-enhancement | Service identifier in traces | Appears in Jaeger service list |
| OTEL_TRACES_SAMPLER | traceidratio | Sampling strategy | traceidratio = percentage-based sampling |
| OTEL_TRACES_SAMPLER_ARG | 0.1 | Sampling rate (0.0-1.0) | 0.1 = 10% of traces sampled |
| DEPLOYMENT_ENV | development | Environment tag | Appears as attribute in spans |

**Sampling Calculation Example:**

```
Tickets per day:           1000
Sampling rate:             10% (0.1)
Traces captured:           100/day
Spans per trace (average): ~10 spans
Total spans:              1000/day
Storage per day:          ~1MB (12 bytes per span metadata)
90-day retention:         90MB (reasonable for Jaeger all-in-one)
```

### Application Configuration

**File:** `src/monitoring/tracing.py`

```python
def init_tracer_provider() -> TracerProvider:
    """Initialize OpenTelemetry tracer provider."""
    # Load configuration from environment
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4317")
    service_name = os.getenv("OTEL_SERVICE_NAME", "ai-agents-enhancement")

    # Create resource with service metadata
    resource = Resource(attributes={
        "service.name": service_name,
        "service.version": "0.1.0",
        "deployment.environment": os.getenv("DEPLOYMENT_ENV", "development"),
    })

    # Create tracer provider with OTLP exporter
    tracer_provider = TracerProvider(resource=resource)
    otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)

    # Wrap with redaction + slow trace detection (AC12 & AC14)
    wrapped_exporter = RedactionAndSlowTraceExporter(otlp_exporter)

    # Add batch span processor for efficient export
    batch_processor = BatchSpanProcessor(
        wrapped_exporter,
        max_queue_size=2048,        # Buffer 2048 spans
        schedule_delay_millis=5000, # Export every 5 seconds
        max_export_batch_size=512,  # Max 512 spans per batch
    )
    tracer_provider.add_span_processor(batch_processor)

    # Set as global and return
    trace.set_tracer_provider(tracer_provider)
    return tracer_provider
```

**Instrumentation Integration Points:**

1. **FastAPI** (src/main.py startup):
   ```python
   init_tracer_provider()  # Initialize BEFORE creating app
   app = FastAPI()
   FastAPIInstrumentor.instrument_app(app)  # Instrument AFTER creating app
   ```

2. **Celery** (src/workers/celery_app.py):
   ```python
   @worker_process_init.connect(weak=False)
   def init_celery_tracing(*args, **kwargs):
       init_tracer_provider()  # Initialize AFTER worker fork
       CeleryInstrumentor().instrument()
   ```

3. **Context Propagation** (src/api/webhooks.py + src/workers/tasks.py):
   ```python
   # In FastAPI handler: Extract and inject trace context
   from opentelemetry.propagate import inject
   carrier = {}
   inject(carrier)
   enhance_ticket.apply_async(args=[...], headers={"traceparent": carrier.get("traceparent")})

   # In Celery task: Extract context
   from opentelemetry.propagate import extract
   context = extract(self.request.headers)
   with tracer.start_as_current_span("enhance_ticket", context=context):
       # Task logic continues trace
   ```

---

## Jaeger UI Usage

### Accessing the UI

**Local Development:**
```bash
# UI automatically available at:
http://localhost:16686

# If accessing from Docker container hostname:
# Change OTEL_EXPORTER_OTLP_ENDPOINT in .env to use container DNS:
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317  # ✓ Correct (container networking)
```

**Production (Kubernetes):**
```bash
# Port-forward to access UI
kubectl port-forward svc/jaeger 16686:16686

# Then access: http://localhost:16686
```

### Searching for Traces

**By Service Name:**
1. Open http://localhost:16686
2. Service dropdown: Select `ai-agents-enhancement`
3. Click "Find Traces"
4. View list of traces with trace ID, operation, duration, error status

**By Trace ID:**
1. If you have a trace ID from logs (e.g., `abc123def456`)
2. Click "Search" → "Advanced"
3. Enter Trace ID: `abc123def456`
4. Click "Find Traces"

**By Tenant/Ticket ID (Tag Search):**
1. Traces have custom attributes set by application
2. Search by custom attributes (AC4-AC8 span coverage):
   ```
   tenant.id = "tenant-123"
   ticket.id = "TICKET-456"
   enhancement.status = "success"
   queue.name = "enhancements"
   ```
3. Example search in UI:
   - Click "Advanced" tab
   - Enter tag: `ticket.id`
   - Enter value: `TICKET-456`
   - Click "Find Traces"

**Filtering for Slow Traces:**
1. Slow traces (>60s) are tagged with `slow_trace=true`
2. Search filter:
   - Tag: `slow_trace`
   - Value: `true`
   - Click "Find Traces"
3. Results show all enhancement jobs that took > 60 seconds
4. Click on a trace to identify bottleneck (example: context_gathering = 25s)

### Analyzing a Trace

**Trace Details View:**

```
Trace ID: abc123def456
Service: ai-agents-enhancement
Duration: 60.234 ms
Spans: 8

Span Timeline (click to expand):
├─ POST /webhook/servicedesk (FastAPI HTTP) [0.0-1.0 ms]
│  └─ job_queued (custom span) [0.5-0.6 ms]
├─ enhance_ticket (Celery task) [1.0-60.0 ms]
│  ├─ context_gathering [1.0-31.0 ms] ← BOTTLENECK
│  │  ├─ context.ticket_history [1.0-26.0 ms]
│  │  ├─ context.documentation [26.0-29.0 ms]
│  │  └─ context.ip_lookup [29.0-31.0 ms]
│  ├─ llm.openai.completion [31.0-46.0 ms]
│  └─ api.servicedesk_plus.update_ticket [46.0-60.0 ms]
```

**Key Metrics:**
- **Self Time** - Time span spent NOT in child spans (e.g., context_gathering = 31ms - 26ms = 5ms overhead)
- **Duration** - Total time including all child spans
- **Bottleneck** - Span with highest duration relative to total (context_gathering = 31s out of 60s = 52%)

**Span Attributes Tab:**
```
Attributes for: context_gathering span
- operation: "context_gathering"
- tenant.id: "tenant-123"
- ticket.id: "TICKET-456"
- result.ticket_history.count: 42
- result.docs.count: 18
- result.ip_lookup: "found"
- slow_trace: false (parent trace is not slow, but this span takes 31s)
- status.code: 0 (success)
```

**Note:** Sensitive attributes are redacted (AC14):
- `api_key` → `[REDACTED]`
- `webhook_secret` → `[REDACTED]`
- `password` → `[REDACTED]`

### Key Insights from Traces

**Finding Performance Bottlenecks:**

```
Trace analysis example:
- Total time: 60 seconds
- Breakdown:
  - context_gathering: 30 seconds (50%)
  - llm_call: 15 seconds (25%)
  - ticket_update: 14 seconds (23%)

Action: Optimize context_gathering (database query likely slow)
Solution: Add database index on ticket_history query, or implement caching
```

**Debugging Failed Enhancements:**

```
Trace shows enhancement failure:
- Span: api.servicedesk_plus.update_ticket
- Attributes: status.code = 403 (Forbidden)
- Error: span.status = "ERROR"
- Error event: "API authentication failed: invalid credentials"

Action: Check ServiceDesk Plus API credentials in secrets
```

**Monitoring Error Rates:**

1. Click "Service Performance" in Jaeger UI
2. Metric: "Error %" - percentage of traces with errors
3. If error rate spikes: Investigate error spans and their attributes
4. Correlate with Prometheus alerts (Story 4.4-4.5)

---

## Security Considerations

### Data Redaction (AC14)

**Sensitive Attributes Redacted:**
- `api_key` → `[REDACTED]`
- `secret` → `[REDACTED]`
- `password` → `[REDACTED]`
- `token` → `[REDACTED]`
- `webhook_secret` → `[REDACTED]`
- `authorization` → `[REDACTED]`
- `credential` → `[REDACTED]`

**Implementation:**
- `RedactionAndSlowTraceExporter` (src/monitoring/span_processors.py:154-299)
- Redaction happens at export time (before transmission to Jaeger)
- Sensitive keys are replaced with `[REDACTED]` string
- No sensitive data appears in Jaeger UI

**Verification:**
```bash
# Check that sensitive data is redacted in Jaeger UI:
1. Open trace in Jaeger
2. Click on a span (e.g., api.servicedesk_plus.update_ticket)
3. Attributes tab: Look for api_key attribute
4. Should show: api_key: "[REDACTED]" (not the actual key)
```

### Access Control

**Local Development:**
- Jaeger UI exposed on `localhost:16686`
- Only accessible from local machine or Docker network
- No authentication required (acceptable for development)

**Production (Kubernetes):**
- Jaeger Service: `ClusterIP` type (internal only, secure)
- For external access: Use Ingress + Authentication proxy
- Example nginx-oauth2-proxy configuration:
  ```yaml
  # nginx ingress with OAuth2 proxy
  # Requires: OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET
  # Users must authenticate before accessing Jaeger UI
  ```

### Network Security

**Jaeger OTLP Receiver:**
- Default: Listens on all interfaces (0.0.0.0:4317)
- Production: Restrict to application pod namespace
- Recommendation:
  ```yaml
  # k8s/jaeger-deployment.yaml
  spec:
    containers:
    - ports:
      - name: otlp-grpc
        containerPort: 4317
        # Network policy: Only allow from application pods
  ```

**Trace Data Storage:**
- Jaeger all-in-one: In-memory (ephemeral, pod restart = data loss)
- Production: Use persistent backend (Elasticsearch, Cassandra) with encryption at rest
- Backup: Regularly backup Elasticsearch indices containing trace data

---

## Troubleshooting

### Problem: No Traces Appearing in Jaeger UI

**Symptoms:**
- Jaeger UI accessible (http://localhost:16686)
- But no traces visible when searching for service

**Root Causes and Solutions:**

1. **Jaeger Not Receiving Traces**
   - Check OTLP exporter endpoint configuration:
     ```bash
     # Verify OTEL_EXPORTER_OTLP_ENDPOINT is correct
     echo $OTEL_EXPORTER_OTLP_ENDPOINT  # Should output: http://jaeger:4317
     ```
   - Check network connectivity:
     ```bash
     # From application container, test Jaeger connectivity
     docker exec <app-container> curl http://jaeger:4317/readiness
     # Expected: 200 OK response
     ```
   - Check Jaeger logs:
     ```bash
     docker-compose logs jaeger | grep -i error
     ```

2. **Instrumentation Not Initialized**
   - Verify `init_tracer_provider()` called in `src/main.py` startup:
     ```python
     @app.on_event("startup")
     def startup():
         init_tracer_provider()  # MUST be called before creating FastAPI app
     ```
   - Verify FastAPI instrumentation:
     ```python
     FastAPIInstrumentor.instrument_app(app)
     ```

3. **Sampling Rate Too Low**
   - Default: 10% of traces sampled
   - If OTEL_TRACES_SAMPLER_ARG=0.01 (1%), only 1 out of 100 requests traced
   - Increase for testing:
     ```bash
     export OTEL_TRACES_SAMPLER_ARG=1.0  # 100% sampling (temporary)
     # Run test request
     # Restart application after testing
     ```

4. **Trace Context Not Propagating**
   - Check that trace context carrier injection is working:
     ```bash
     # In logs, verify trace ID is consistent across FastAPI → Celery
     grep "trace_id=abc123" application.log  # Should see same ID in multiple logs
     ```

**Solution Checklist:**
```
□ Verify OTEL_EXPORTER_OTLP_ENDPOINT set correctly
□ Verify Jaeger running: docker-compose ps | grep jaeger
□ Test Jaeger connectivity: curl http://localhost:16686/
□ Check application logs for OTLP exporter errors
□ Increase sampling rate to 100% for testing: OTEL_TRACES_SAMPLER_ARG=1.0
□ Trigger test request (webhook to /webhook/servicedesk)
□ Wait 5 seconds for batch export
□ Refresh Jaeger UI and search for service
```

---

### Problem: Traces Not Complete or Missing Spans

**Symptoms:**
- Traces appear in Jaeger, but missing expected spans
- Example: Context gathering span not appearing

**Root Causes:**

1. **Span Not Created** - Code doesn't have custom span wrapper
   - Solution: Verify custom spans implemented (Tasks 7-8)
   - Example: `src/workers/tasks.py` should have:
     ```python
     with tracer.start_as_current_span("context_gathering"):
         # Context gathering logic
     ```

2. **Trace Sampling Excluded Span** - Span's parent trace was not sampled
   - Solution: All spans in a sampled trace should appear
   - If span missing: Check if parent trace is sampled (OTEL_TRACES_SAMPLER_ARG)

3. **Span Export Failed** - Span created but export to Jaeger failed
   - Solution: Check application logs for export errors:
     ```bash
     docker-compose logs app | grep -i "otlp\|export\|error"
     ```

4. **Trace Not Yet Exported** - Spans in memory, waiting for batch export
   - Solution: Wait 5+ seconds (BatchSpanProcessor.schedule_delay_millis = 5000)
   - Or force flush (not applicable in production, only testing)

**Solution Checklist:**
```
□ Verify custom spans implemented in code (context_gathering, llm_call, etc.)
□ Check OTEL_TRACES_SAMPLER_ARG: increase to 1.0 for 100% sampling
□ Check application logs for OTLP export errors
□ Wait 5 seconds after test request (batch export delay)
□ Verify span attributes in Jaeger UI (click span to see details)
□ If still missing: Check if span exception occurred (span.status = ERROR)
```

---

### Problem: Sensitive Data Visible in Jaeger

**Symptoms:**
- Traces show unredacted sensitive data (API keys, secrets)
- Example: `api_key: "sk-1234567890abcdef"` visible in span attributes

**Root Cause:**
- RedactionAndSlowTraceExporter not properly redacting before export
- Sensitive attribute key patterns not matching actual attribute names

**Solution:**

1. **Verify Redaction is Enabled**
   - Check `src/monitoring/tracing.py`:
     ```python
     wrapped_exporter = RedactionAndSlowTraceExporter(otlp_exporter)
     batch_processor = BatchSpanProcessor(wrapped_exporter, ...)
     ```

2. **Update Sensitive Keys List** if needed
   - File: `src/monitoring/span_processors.py` line 180-188
   - Add any custom attribute names containing sensitive data:
     ```python
     self.SENSITIVE_KEYS = {
         "api_key",
         "secret",
         "password",
         "token",
         "webhook_secret",
         "custom_secret_field",  # Add if needed
     }
     ```

3. **Verify Redaction in Logs**
   - Application logs should show redaction happening:
     ```
     DEBUG: Span context_gathering: redacted 1 keys, slow_trace=false
     ```
   - If not appearing: Check log level (should be DEBUG minimum)

4. **Test Redaction**
   - Send test webhook with API key in attributes
   - Check Jaeger UI: attribute should show `[REDACTED]`
   - If not working: Check if attribute key pattern matches SENSITIVE_KEYS

**Solution Checklist:**
```
□ Verify wrapped_exporter used in BatchSpanProcessor
□ Check SENSITIVE_KEYS includes actual attribute names in code
□ Enable DEBUG logging and check redaction messages
□ Trigger test request and verify redaction in Jaeger UI
□ If still leaking: Add custom attribute names to SENSITIVE_KEYS
```

---

### Problem: High Latency in Tracing/Export

**Symptoms:**
- Application requests slower than expected
- OTLP exporter taking long time to export spans
- Batch processor queue filling up

**Root Causes:**

1. **Jaeger Unreachable** - OTLP exporter waits for timeout
   - Check network: `curl http://jaeger:4317/readiness`
   - Check endpoint configuration: `echo $OTEL_EXPORTER_OTLP_ENDPOINT`

2. **BatchSpanProcessor Settings Too Conservative**
   - Current: max_queue_size=2048, schedule_delay_millis=5000
   - For high-throughput: Consider adjusting:
     - schedule_delay_millis: Reduce to 1000ms for faster export
     - max_queue_size: Increase if queue filling up
     - max_export_batch_size: Increase to 1024 for larger batches

3. **Sampling Rate Too High** - Too many spans being exported
   - Current: 10% sampling (0.1)
   - Reduce for production: 0.01-0.05 (1-5%)

**Solution:**

```python
# src/monitoring/tracing.py - Adjust batch processor settings
batch_processor = BatchSpanProcessor(
    wrapped_exporter,
    max_queue_size=4096,         # Increase from 2048
    schedule_delay_millis=1000,  # Decrease from 5000 (export faster)
    max_export_batch_size=1024,  # Increase from 512 (larger batches)
    export_timeout_millis=30000,
)

# .env - Reduce sampling rate
OTEL_TRACES_SAMPLER_ARG=0.05  # 5% instead of 10%
```

**Verification:**
- Monitor export latency in application metrics (if instrumented)
- Check Jaeger UI response time improving
- Monitor Jaeger CPU/memory usage increasing (more traces)

---

## Operational Runbooks

### Debugging a Failed Ticket Enhancement

**Scenario:** Customer reports enhancement didn't apply to ticket

**Steps:**

1. **Get Ticket ID from Customer**
   - Example: `TICKET-456`

2. **Find Trace in Jaeger**
   ```
   Jaeger UI → Search
   Service: ai-agents-enhancement
   Operation: POST /webhook/servicedesk (or any)
   Advanced → Tag: ticket.id = TICKET-456
   Click "Find Traces"
   ```

3. **Examine Trace**
   - Click on trace in results
   - Look for ERROR status (red X on span)
   - Identify which span failed

4. **Analyze Error Span**
   - Click on error span (e.g., `api.servicedesk_plus.update_ticket`)
   - Expand "Tags" section → Look for:
     - `status.code` - HTTP response code (403, 500, etc.)
     - `error.message` - Error description
     - `http.status_code` - Actual HTTP code

5. **Common Failure Points**

   **Context Gathering Failed (30s timeout)**
   - Span: `context_gathering`
   - Status: ERROR, Duration: ~30s
   - Error: "Timeout waiting for ticket history"
   - Action: Check ticket history search performance (may need database index)

   **LLM Call Failed (API error)**
   - Span: `llm.openai.completion`
   - Status: ERROR, Duration: varies
   - Error: "429 Too Many Requests" or "Invalid API key"
   - Action: Check OpenAI API quota or key rotation schedule

   **Ticket Update Failed (Auth error)**
   - Span: `api.servicedesk_plus.update_ticket`
   - Status: ERROR, Duration: <1s
   - Error: "403 Forbidden" or "401 Unauthorized"
   - Action: Check ServiceDesk Plus API credentials in Kubernetes secret

6. **Correlate with Logs**
   - Use trace ID to find related logs:
     ```bash
     # Extract trace_id from Jaeger (top of trace details)
     trace_id="abc123def456"

     # Search logs
     kubectl logs -n default -l app=ai-agents -c app --grep="$trace_id" | tail -100
     ```

7. **Resolution**
   - Based on error cause, fix configuration or code
   - Retest: Trigger new webhook, verify trace succeeds

---

### Monitoring Slow Enhancements

**Scenario:** Alert fires for enhancement taking > 60 seconds

**Steps:**

1. **Find Slow Traces in Jaeger**
   ```
   Service: ai-agents-enhancement
   Advanced → Tag: slow_trace = true
   Click "Find Traces"
   ```

2. **Analyze Slow Trace**
   - Sort spans by duration
   - Identify slowest span (likely bottleneck)
   - Example results:
     - context_gathering: 45s (75% of total)
     - llm_call: 10s
     - ticket_update: 5s

3. **Optimize Bottleneck**
   - If context_gathering slow:
     - Add database index on ticket_history query
     - Implement caching for frequently accessed docs
     - Parallelize independent context gathering (ticket + docs + IP)
   - If llm_call slow:
     - Check OpenAI API performance (may be network latency)
     - Consider batch requests if multiple tickets
   - If ticket_update slow:
     - Check ServiceDesk Plus API latency
     - May need connection pooling

4. **Test Optimization**
   - Deploy fix
   - Send test webhook
   - Verify new trace has reduced duration
   - Check `slow_trace=false` attribute in new trace

5. **Update Alerts**
   - If slow enhancement is now normal (e.g., data has grown):
     - Consider increasing threshold (Story 4.4)
     - Or adjusting alert frequency

---

### Jaeger Storage Cleanup (Production)

**Scenario:** Jaeger storage growing too large (Elasticsearch backend)

**Steps:**

1. **Check Storage Usage**
   ```bash
   # Connect to Elasticsearch
   kubectl port-forward svc/elasticsearch 9200:9200

   # List indices
   curl http://localhost:9200/_cat/indices?v | grep jaeger

   # Get index size
   curl http://localhost:9200/_cat/indices/jaeger-2025-11-03?v
   ```

2. **Delete Old Traces**
   ```bash
   # Delete indices older than 30 days (example)
   THIRTY_DAYS_AGO=$(date -d "30 days ago" +%Y-%m-%d)

   curl -X DELETE http://localhost:9200/jaeger-${THIRTY_DAYS_AGO}-*
   ```

3. **Configure Automatic Cleanup**
   - Use Elasticsearch Index Lifecycle Management (ILM)
   - Set retention: delete indices after 30 days
   - Configure in Jaeger deployment documentation

---

## Performance Tuning

### Sampling Strategy

**Purpose:** Balance trace volume vs. storage/cost

```
Sampling Rate Table:
┌──────────┬────────────┬──────────────┬──────────┐
│ Rate     │ Traces/day │ Spans/day    │ Storage  │
├──────────┼────────────┼──────────────┼──────────┤
│ 1% (0.01)│ 10         │ 100          │ 100KB    │ ← Development
│ 5% (0.05)│ 50         │ 500          │ 500KB    │
│ 10% (0.1)│ 100        │ 1,000        │ 1MB      │ ← Current (recommended)
│ 50% (0.5)│ 500        │ 5,000        │ 5MB      │
│ 100% (1) │ 1,000      │ 10,000       │ 10MB     │ ← High visibility
└──────────┴────────────┴──────────────┴──────────┘

For 1000 tickets/day:
- At 10% sampling: 100 traces/day, ~1MB/day, 90MB/month
- At 1% sampling: 10 traces/day, ~100KB/day, 9MB/month
```

**Recommendation:**
- **Development/Testing:** 100% (OTEL_TRACES_SAMPLER_ARG=1.0)
- **Staging:** 50% (OTEL_TRACES_SAMPLER_ARG=0.5)
- **Production:** 10% (OTEL_TRACES_SAMPLER_ARG=0.1)
- **High-traffic:** 1-5% (OTEL_TRACES_SAMPLER_ARG=0.01-0.05)

### BatchSpanProcessor Tuning

**Current Settings:**
```python
BatchSpanProcessor(
    exporter,
    max_queue_size=2048,        # Max spans buffered before blocking
    schedule_delay_millis=5000, # Export every 5 seconds
    max_export_batch_size=512,  # Max spans per batch
    export_timeout_millis=30000,# Timeout for export operation
)
```

**Tuning Scenarios:**

1. **High Latency Sensitivity (Need fast export)**
   ```python
   schedule_delay_millis=500,  # Export every 0.5 seconds
   max_export_batch_size=128,  # Smaller batches for faster export
   ```

2. **High Throughput (Many spans/second)**
   ```python
   max_queue_size=8192,        # Increase buffer
   max_export_batch_size=2048, # Larger batches
   schedule_delay_millis=10000,# Less frequent export
   ```

3. **Resource-Constrained (Low memory)**
   ```python
   max_queue_size=512,         # Smaller buffer
   max_export_batch_size=128,  # Smaller batches
   schedule_delay_millis=1000, # Faster export
   ```

---

## Testing & Validation

### Verifying Tracing is Working

```bash
#!/bin/bash
# test_tracing.sh - End-to-end tracing validation

# 1. Check Jaeger is running
echo "Step 1: Verify Jaeger running..."
curl -s http://localhost:16686/ > /dev/null && echo "✓ Jaeger UI accessible" || echo "✗ Jaeger not running"

# 2. Send test webhook
echo "Step 2: Trigger test enhancement..."
curl -X POST http://localhost:8000/webhook/servicedesk \
  -H "Content-Type: application/json" \
  -H "X-Signature: test" \
  -d '{"ticket_id": "TEST-001", "summary": "Test enhancement"}'

# 3. Wait for processing
echo "Step 3: Waiting for trace export (5 seconds)..."
sleep 5

# 4. Check Jaeger for trace
echo "Step 4: Verify trace in Jaeger..."
# Manual: Open http://localhost:16686, search for service

echo ""
echo "✓ Test complete. Check Jaeger UI for trace with:"
echo "  Service: ai-agents-enhancement"
echo "  Operation: POST /webhook/servicedesk"
echo "  Look for custom spans: job_queued, context_gathering, llm.openai.completion, etc."
```

---

## References & Documentation

**OpenTelemetry:**
- [OpenTelemetry Python Documentation](https://opentelemetry.io/docs/languages/python/)
- [OpenTelemetry Instrumentation Registry](https://opentelemetry.io/ecosystem/registry/?language=python)

**Jaeger:**
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [Jaeger Sampling](https://www.jaegertracing.io/docs/latest/sampling/)

**Integration Guides:**
- [OpenTelemetry + FastAPI](https://last9.io/blog/integrating-opentelemetry-with-fastapi/)
- [OpenTelemetry + Celery](https://uptrace.dev/guides/opentelemetry-celery)

**Related Stories:**
- Story 4.1: Prometheus Metrics Instrumentation
- Story 4.2: Prometheus Server Deployment
- Story 4.4: Prometheus Alerting Rules
- Story 4.5: Alertmanager Integration

---

**Last Updated:** 2025-11-03
**Author:** Ravi (Developer Agent)
**Status:** Complete (AC15 - Operational Documentation)
