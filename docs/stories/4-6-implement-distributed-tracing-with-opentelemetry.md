# Story 4.6: Implement Distributed Tracing with OpenTelemetry

**Status:** ready-for-dev

**Story ID:** 4.6
**Epic:** 4 (Monitoring & Operations)
**Date Created:** 2025-11-03
**Story Key:** 4-6-implement-distributed-tracing-with-opentelemetry

---

## Change Log

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2025-11-03 | 1.0 | Story drafted by Scrum Master (Bob) in non-interactive mode with OpenTelemetry 2025 best practices research | Bob (Scrum Master) |

---

## Story

As a developer,
I want request traces showing end-to-end flow through FastAPI, Redis, and Celery components,
So that I can debug performance bottlenecks and failed enhancements with complete visibility into the ticket enhancement pipeline.

---

## Technical Context

Implement OpenTelemetry distributed tracing to provide end-to-end visibility into ticket enhancement workflows spanning multiple services (FastAPI webhook receiver → Redis queue → Celery workers → External APIs). This story addresses a critical observability gap: while metrics (Story 4.1-4.2) show *what* is happening and alerts (Story 4.4-4.5) notify *when* problems occur, distributed tracing reveals *why* by showing the complete request flow with timing breakdowns for each component.

**Key Implementation Components:**

1. **OpenTelemetry instrumentation** for FastAPI (automatic HTTP request tracing) and Celery (automatic task tracing)
2. **Context propagation** between FastAPI and Celery via manual carrier injection in Redis queue messages
3. **Span hierarchy** representing the enhancement flow: `webhook_received` → `job_queued` → `context_gathering` → `llm_call` → `ticket_update`
4. **Jaeger backend deployment** for trace storage and visualization (OTLP-compatible)
5. **Performance optimization** with sampling (10% of traces) and BatchSpanProcessor configuration
6. **Slow trace detection** via automatic tagging of traces exceeding 60-second threshold

**Architecture Alignment:**
- Fulfills NFR005 (Observability): "distributed tracing for debugging failed enhancements"
- Complements Story 4.1-4.2 (metrics): Traces provide causality, metrics provide aggregates
- Enhances Story 4.4-4.5 (alerting): Traces help diagnose root causes of fired alerts
- Multi-service tracing: FastAPI (Story 2.1) → Celery workers (Story 2.4) → LangGraph (Story 2.8)

**Prerequisites:**
- Story 2.11 (end-to-end enhancement workflow operational)
- Story 4.1 (Prometheus metrics instrumentation patterns established)
- Story 4.2 (Monitoring infrastructure deployment experience)

**2025 OpenTelemetry Best Practices Applied:**
- **Celery worker initialization:** Use `worker_process_init` signal to initialize tracer provider after fork (avoids threading issues with BatchSpanProcessor)
- **FastAPI-Celery context propagation:** Manual carrier injection required (automatic propagation doesn't work across Redis queue boundary)
- **Jaeger OTLP support:** Jaeger natively receives OTLP on ports 4317 (gRPC) and 4318 (HTTP) as of 2024+
- **Performance overhead:** BatchSpanProcessor with optimized settings keeps overhead <2% (well below 5% requirement)
- **Security:** Custom span processors redact sensitive data (API keys, ticket content) before export

---

## Requirements Context Summary

**From epics.md (Story 4.6 - Lines 900-915):**

Distributed tracing acceptance criteria:
1. **Instrumentation:** OpenTelemetry added to FastAPI and Celery applications
2. **Span coverage:** Traces include spans for webhook_received, job_queued, context_gathering, llm_call, ticket_update
3. **Context propagation:** Trace context flows across service boundaries (FastAPI → Redis → Celery)
4. **Backend:** Traces exported to Jaeger or similar OTLP-compatible backend
5. **Visualization:** Sample trace viewable in Jaeger UI showing complete enhancement flow from webhook to ticket update
6. **Slow trace detection:** Traces exceeding 60 seconds automatically flagged/tagged
7. **Performance:** Tracing overhead remains below 5% (CPU/memory impact)

**From PRD.md (NFR005):**
- "System shall provide real-time visibility into agent operations through... distributed tracing for debugging failed enhancements"

**From Architecture.md:**
- OpenTelemetry listed under "Observability" as future component
- Multi-service architecture requiring cross-process trace correlation

**OpenTelemetry 2025 Research Findings:**

**Supported Libraries (OpenTelemetry Registry):**
- FastAPI: Automatic instrumentation via `opentelemetry-instrumentation-fastapi`
- Celery: Automatic instrumentation via `opentelemetry-instrumentation-celery`
- HTTPX: Automatic HTTP client tracing for external API calls
- Redis: Optional broker instrumentation via `opentelemetry-instrumentation-redis`

**Celery Worker Initialization (Critical):**
```python
from celery.signals import worker_process_init

@worker_process_init.connect(weak=False)
def init_celery_tracing(*args, **kwargs):
    # Initialize tracer provider AFTER worker fork
    # Prevents BatchSpanProcessor threading issues
```

**Context Propagation Challenge:**
- FastAPI and Celery instrumentors create separate trace trees by default
- Manual propagation needed: Extract context from FastAPI request → Inject into Celery task headers
- Use `TraceContextTextMapPropagator` to serialize/deserialize trace context

**Jaeger Deployment (Docker):**
```bash
docker run --rm \
  -p 16686:16686 \  # Jaeger UI
  -p 4317:4317 \    # OTLP gRPC
  -p 4318:4318 \    # OTLP HTTP
  jaegertracing/all-in-one:latest
```

**Performance Optimization:**
- Sampling: TraceIdRatioBased(0.1) for 10% trace sampling
- BatchSpanProcessor: max_queue_size=2048, schedule_delay_millis=5000, max_export_batch_size=512
- Measured overhead: <2% CPU/memory impact with proper configuration

**Span Naming Conventions:**
- HTTP spans: `GET /webhook/servicedesk` (automatic from FastAPIInstrumentor)
- Celery task spans: `celery.task.enhance_ticket` (automatic from CeleryInstrumentor)
- Custom spans: `context_gathering.ticket_history`, `llm.openai.completion`, `api.servicedesk_plus.update_ticket`

**Security Considerations:**
- Redact sensitive span attributes: API keys, webhook secrets, full ticket descriptions
- Use custom span processor to filter before export
- Jaeger UI access control via network policies or authentication proxy

---

## Project Structure Alignment and Lessons Learned

### Learnings from Previous Story (4.5 - Alertmanager Integration)

**From Story 4.5 (Status: done, Code Review: APPROVED):**

Story 4.5 successfully implemented Alertmanager for alert routing to Slack/PagerDuty/Email channels. Key learnings:

**Infrastructure Patterns:**
- **Docker Compose deployment:** Added service with health checks, volume mounts, and environment variable injection
- **Kubernetes deployment:** Created Deployment + Service + ConfigMap + Secret manifests following established patterns
- **Configuration management:** YAML config file + secrets template with placeholder values (no hardcoded credentials)
- **Documentation:** Comprehensive operational guide (698 lines) with architecture, setup, troubleshooting, and runbooks

**Integration Testing:**
- 33 integration tests created covering configuration validation, health checks, routing rules, and notification delivery
- All tests passing with mocked external services (Slack, PagerDuty, SMTP)
- Test framework pattern: Use `pytest` with fixture-based setup for service dependencies

**Files Created in Story 4.5:**
- `alertmanager.yml` - Configuration file (149 lines with receivers, routing, grouping)
- `k8s/alertmanager-deployment.yaml` - Kubernetes manifests
- `k8s/alertmanager-secrets.template.yaml` - Secrets template
- `docs/operations/alertmanager-setup.md` - Operational documentation
- `tests/integration/test_alertmanager_integration.py` - Integration test suite

**For Story 4.6 Implementation:**

**Reuse Monitoring Infrastructure Patterns:**
- Follow same deployment approach: Docker Compose service + Kubernetes manifests
- Use ConfigMap for OpenTelemetry configuration (like alertmanager.yml)
- Create comprehensive operational documentation (following alertmanager-setup.md structure)
- Build integration test suite using pytest patterns from Story 4.5

**Expected File Structure:**
- **Docker Compose:** Add Jaeger service to `docker-compose.yml` with OTLP ports exposed
- **Kubernetes:** Create `k8s/jaeger-deployment.yaml` for production trace backend
- **Application Code:**
  - `src/observability/tracing.py` - OpenTelemetry initialization and configuration
  - `src/observability/span_processors.py` - Custom processors for data redaction
- **Configuration:** `otel-config.yaml` or environment variables for exporter settings
- **Documentation:** `docs/operations/distributed-tracing-setup.md` following Story 4.5 documentation patterns
- **Tests:** `tests/integration/test_distributed_tracing.py` with trace validation

**Project Structure Alignment:**

Based on existing codebase structure (from unified-project-structure if it exists) and established patterns:

- **Observability module:** Create `src/observability/` for tracing infrastructure (separate from metrics in `src/metrics/`)
- **FastAPI instrumentation:** Add to existing FastAPI app initialization (likely in `src/main.py` or `src/app.py`)
- **Celery instrumentation:** Add to Celery worker initialization (likely in `src/worker.py` or `src/tasks/__init__.py`)
- **Deployment:** Jaeger manifests in `k8s/` directory alongside Prometheus and Alertmanager
- **Testing:** Integration tests in `tests/integration/` following pytest conventions

**Technical Debt to Address:**
- Story 4.5 noted E2E testing blocked on credentials - Story 4.6 should use mocked backends for E2E trace testing (no external service dependencies)

---

## Acceptance Criteria

1. **OpenTelemetry instrumentation - FastAPI:** `opentelemetry-instrumentation-fastapi` installed and configured; HTTP requests to webhook endpoint automatically generate spans with route, method, status code attributes
2. **OpenTelemetry instrumentation - Celery:** `opentelemetry-instrumentation-celery` installed; Celery task execution automatically generates spans with task name, queue, status, exception (if any)
3. **Trace context propagation:** Trace context flows from FastAPI request → Redis queue → Celery task; single trace ID spans all components (manual carrier injection implemented)
4. **Span coverage - webhook_received:** FastAPI span captures webhook request details (tenant_id, ticket_id, priority) as span attributes
5. **Span coverage - job_queued:** Custom span records Redis queue operation with queue name and job ID
6. **Span coverage - context_gathering:** Custom span(s) capture context gathering operations (ticket history search, doc search, IP lookup) with result counts
7. **Span coverage - llm_call:** Custom span captures OpenAI/OpenRouter API call with model name, token count, latency
8. **Span coverage - ticket_update:** Custom span captures ServiceDesk Plus ticket update API call with success/failure status
9. **Jaeger backend deployment:** Jaeger deployed as Docker Compose service (local dev) and Kubernetes Deployment (production); OTLP receiver enabled on ports 4317 (gRPC) and 4318 (HTTP)
10. **Trace export configuration:** Application configured to export traces via OTLP exporter to Jaeger endpoint; BatchSpanProcessor configured with production settings (max_queue_size=2048, schedule_delay_millis=5000)
11. **Sample trace visualization:** Trigger test ticket enhancement → verify complete trace visible in Jaeger UI (http://localhost:16686) showing all spans from webhook to ticket update with correct parent-child relationships
12. **Slow trace detection:** Traces exceeding 60-second duration automatically tagged with `slow_trace=true` attribute; Jaeger query can filter slow traces
13. **Performance overhead:** Measure CPU/memory overhead with tracing enabled vs disabled; verify <5% increase (target: <2%)
14. **Security - data redaction:** Custom span processor redacts sensitive attributes (API keys, webhook secrets, full ticket content) before export
15. **Configuration documentation:** Document OpenTelemetry configuration including exporter settings, sampling configuration, span processor configuration, and Jaeger UI access
16. **Testing:** Integration tests verify trace generation, context propagation, and span attributes; tests use in-memory span exporter (no external Jaeger dependency for tests)

---

## Tasks / Subtasks

### Task 1: Install OpenTelemetry Dependencies
- [ ] **Install core OpenTelemetry packages:**
  - [ ] Subtask 1.1: Add to `requirements.txt`: `opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation`
  - [ ] Subtask 1.2: Add instrumentation packages: `opentelemetry-instrumentation-fastapi opentelemetry-instrumentation-celery opentelemetry-instrumentation-httpx opentelemetry-instrumentation-redis`
  - [ ] Subtask 1.3: Add OTLP exporter: `opentelemetry-exporter-otlp-proto-grpc` (for production Jaeger export)
  - [ ] Subtask 1.4: Run `pip install -r requirements.txt` to install all dependencies
  - [ ] Subtask 1.5: Verify installation: `python -c "import opentelemetry; print(opentelemetry.__version__)"`

### Task 2: Deploy Jaeger Backend
- [ ] **Docker Compose deployment (local development):**
  - [ ] Subtask 2.1: Add Jaeger service to `docker-compose.yml` with image `jaegertracing/all-in-one:latest`
  - [ ] Subtask 2.2: Expose ports: 16686 (UI), 4317 (OTLP gRPC), 4318 (OTLP HTTP)
  - [ ] Subtask 2.3: Add health check: `http://localhost:16686/` returns 200 OK
  - [ ] Subtask 2.4: Test: `docker-compose up jaeger` starts successfully, UI accessible at http://localhost:16686
- [ ] **Kubernetes deployment (production):**
  - [ ] Subtask 2.5: Create `k8s/jaeger-deployment.yaml` with Deployment resource (image: jaegertracing/all-in-one:latest)
  - [ ] Subtask 2.6: Configure resource limits (CPU: 200m request, 1000m limit; Memory: 512Mi request, 2Gi limit)
  - [ ] Subtask 2.7: Create Kubernetes Service exposing ports 16686, 4317, 4318
  - [ ] Subtask 2.8: Add liveness and readiness probes pointing to `/` endpoint
  - [ ] Subtask 2.9: (Optional) Create PersistentVolumeClaim for trace storage if persistence needed

### Task 3: Create OpenTelemetry Tracing Infrastructure
- [ ] **Create tracing initialization module:**
  - [ ] Subtask 3.1: Create `src/observability/tracing.py` module
  - [ ] Subtask 3.2: Implement `init_tracer_provider()` function:
    - [ ] Subtask 3.2a: Create Resource with service.name, service.version, deployment.environment attributes
    - [ ] Subtask 3.2b: Configure BatchSpanProcessor with OTLP exporter (endpoint from env var `OTEL_EXPORTER_OTLP_ENDPOINT`)
    - [ ] Subtask 3.2c: Add custom RedactionSpanProcessor (implemented in next subtask)
    - [ ] Subtask 3.2d: Set tracer provider globally via `trace.set_tracer_provider()`
  - [ ] Subtask 3.3: Implement `RedactionSpanProcessor` in `src/observability/span_processors.py`:
    - [ ] Subtask 3.3a: Redact span attributes containing: `api_key`, `secret`, `password`, `token`
    - [ ] Subtask 3.3b: Truncate `ticket.description` attribute to first 100 characters
    - [ ] Subtask 3.3c: Remove full webhook payload from span attributes
  - [ ] Subtask 3.4: Implement `get_tracer(name: str)` helper function for creating named tracers
  - [ ] Subtask 3.5: Add configuration via environment variables:
    - [ ] `OTEL_EXPORTER_OTLP_ENDPOINT` (default: http://jaeger:4317)
    - [ ] `OTEL_SERVICE_NAME` (default: ai-agents-enhancement)
    - [ ] `OTEL_TRACES_SAMPLER` (default: traceidratio)
    - [ ] `OTEL_TRACES_SAMPLER_ARG` (default: 0.1 for 10% sampling)

### Task 4: Instrument FastAPI Application
- [ ] **Enable FastAPI automatic instrumentation:**
  - [ ] Subtask 4.1: Import `FastAPIInstrumentor` in main FastAPI app file (e.g., `src/main.py`)
  - [ ] Subtask 4.2: Call `init_tracer_provider()` BEFORE creating FastAPI app instance
  - [ ] Subtask 4.3: Instrument FastAPI app: `FastAPIInstrumentor.instrument_app(app)`
  - [ ] Subtask 4.4: Verify automatic span creation: Start server, send test request, check logs for span export
  - [ ] Subtask 4.5: Add custom span attributes to webhook endpoint:
    - [ ] Subtask 4.5a: Extract `tenant_id`, `ticket_id`, `priority` from webhook payload
    - [ ] Subtask 4.5b: Add as span attributes using `span.set_attribute("ticket.id", ticket_id)`
    - [ ] Subtask 4.5c: Add span event for validation errors (if signature validation fails)

### Task 5: Instrument Celery Workers
- [ ] **Enable Celery automatic instrumentation with worker_process_init:**
  - [ ] Subtask 5.1: Import `worker_process_init` signal from `celery.signals` in Celery app file (e.g., `src/worker.py`)
  - [ ] Subtask 5.2: Create signal handler decorated with `@worker_process_init.connect(weak=False)`:
    - [ ] Subtask 5.2a: Call `init_tracer_provider()` inside signal handler
    - [ ] Subtask 5.2b: Instrument Celery: `CeleryInstrumentor().instrument()`
  - [ ] Subtask 5.3: Verify instrumentation: Start Celery worker, trigger test task, check logs for span export
  - [ ] Subtask 5.4: Add custom task attributes:
    - [ ] Subtask 5.4a: Add `tenant_id` to all enhancement task spans
    - [ ] Subtask 5.4b: Add `ticket_id` to task spans
    - [ ] Subtask 5.4c: Add `enhancement.status` (success/failure) as span attribute

### Task 6: Implement Context Propagation (FastAPI → Celery)
- [ ] **Manual carrier injection for trace context:**
  - [ ] Subtask 6.1: In FastAPI webhook handler, extract current trace context:
    ```python
    from opentelemetry import trace
    from opentelemetry.propagate import inject

    carrier = {}
    inject(carrier)  # Injects current trace context into carrier dict
    ```
  - [ ] Subtask 6.2: Pass carrier as headers to Celery task:
    ```python
    enhance_ticket.apply_async(
        args=[ticket_data],
        headers={"traceparent": carrier.get("traceparent")}
    )
    ```
  - [ ] Subtask 6.3: In Celery task, extract context from headers:
    ```python
    from opentelemetry.propagate import extract

    context = extract(task.request.headers)
    with trace.get_tracer(__name__).start_as_current_span("enhance_ticket", context=context):
        # Task logic here
    ```
  - [ ] Subtask 6.4: Verify context propagation: Trigger webhook → check Jaeger UI → verify single trace ID for FastAPI + Celery spans

### Task 7: Add Custom Spans for Enhancement Workflow
- [ ] **Create custom spans for each enhancement phase:**
  - [ ] Subtask 7.1: **job_queued span:** In FastAPI handler, create span around Redis queue push:
    ```python
    with tracer.start_as_current_span("job_queued") as span:
        span.set_attribute("queue.name", "enhancement_queue")
        span.set_attribute("job.id", job_id)
        # Push to Redis queue
    ```
  - [ ] Subtask 7.2: **context_gathering span:** In Celery task, wrap context gathering:
    ```python
    with tracer.start_as_current_span("context_gathering") as span:
        # Child spans for each context source:
        with tracer.start_as_current_span("context.ticket_history") as child:
            results = search_ticket_history(ticket_id)
            child.set_attribute("results.count", len(results))
    ```
  - [ ] Subtask 7.3: **llm_call span:** Wrap OpenAI API call:
    ```python
    with tracer.start_as_current_span("llm.openai.completion") as span:
        span.set_attribute("llm.model", model_name)
        response = openai_client.chat.completions.create(...)
        span.set_attribute("llm.tokens.prompt", response.usage.prompt_tokens)
        span.set_attribute("llm.tokens.completion", response.usage.completion_tokens)
    ```
  - [ ] Subtask 7.4: **ticket_update span:** Wrap ServiceDesk Plus API call:
    ```python
    with tracer.start_as_current_span("api.servicedesk_plus.update_ticket") as span:
        span.set_attribute("api.endpoint", "/api/v3/tickets/{ticket_id}")
        response = httpx_client.put(url, json=payload)
        span.set_attribute("api.status_code", response.status_code)
    ```

### Task 8: Implement Slow Trace Detection
- [ ] **Add slow trace tagging:**
  - [ ] Subtask 8.1: Create custom span processor in `src/observability/span_processors.py`:
    ```python
    class SlowTraceProcessor(SpanProcessor):
        def on_end(self, span):
            duration_ms = (span.end_time - span.start_time) / 1_000_000
            if duration_ms > 60_000:  # 60 seconds
                span.set_attribute("slow_trace", True)
                span.set_attribute("duration_ms", duration_ms)
    ```
  - [ ] Subtask 8.2: Add SlowTraceProcessor to tracer provider in `init_tracer_provider()`
  - [ ] Subtask 8.3: Test: Trigger slow enhancement (add sleep in task) → verify Jaeger shows `slow_trace=true` tag
  - [ ] Subtask 8.4: Document Jaeger query for slow traces: `slow_trace=true` in tag filter

### Task 9: Performance Testing and Optimization
- [ ] **Measure tracing overhead:**
  - [ ] Subtask 9.1: Baseline measurement: Run load test with tracing DISABLED, measure CPU/memory
  - [ ] Subtask 9.2: Tracing enabled measurement: Run same load test with tracing ENABLED, measure CPU/memory
  - [ ] Subtask 9.3: Calculate overhead percentage: (tracing_enabled - baseline) / baseline * 100
  - [ ] Subtask 9.4: Verify overhead <5% (target: <2%)
  - [ ] Subtask 9.5: If overhead too high, optimize:
    - [ ] Reduce sampling rate (e.g., 0.05 for 5% instead of 10%)
    - [ ] Increase BatchSpanProcessor schedule_delay_millis (reduce export frequency)
    - [ ] Remove non-essential custom span attributes

### Task 10: Integration Testing
- [ ] **Create integration test suite:**
  - [ ] Subtask 10.1: Create `tests/integration/test_distributed_tracing.py`
  - [ ] Subtask 10.2: Test: Verify FastAPI instrumentation creates HTTP spans with correct attributes
  - [ ] Subtask 10.3: Test: Verify Celery instrumentation creates task spans with correct attributes
  - [ ] Subtask 10.4: Test: Verify context propagation - single trace ID across FastAPI + Celery
  - [ ] Subtask 10.5: Test: Verify custom spans created (job_queued, context_gathering, llm_call, ticket_update)
  - [ ] Subtask 10.6: Test: Verify RedactionSpanProcessor removes sensitive attributes
  - [ ] Subtask 10.7: Test: Verify SlowTraceProcessor tags slow traces
  - [ ] Subtask 10.8: Use in-memory span exporter for tests (no external Jaeger dependency):
    ```python
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    span_exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    ```
  - [ ] Subtask 10.9: Run full test suite: `pytest tests/integration/test_distributed_tracing.py -v`
  - [ ] Subtask 10.10: Verify all tests passing

### Task 11: End-to-End Trace Validation
- [ ] **Verify complete trace in Jaeger UI:**
  - [ ] Subtask 11.1: Start all services (docker-compose up: fastapi, celery, redis, jaeger)
  - [ ] Subtask 11.2: Send test webhook to `/webhook/servicedesk` endpoint
  - [ ] Subtask 11.3: Wait for enhancement to complete (check Celery logs)
  - [ ] Subtask 11.4: Open Jaeger UI (http://localhost:16686)
  - [ ] Subtask 11.5: Search for service "ai-agents-enhancement"
  - [ ] Subtask 11.6: Verify trace contains spans:
    - [ ] HTTP span: `POST /webhook/servicedesk`
    - [ ] Custom span: `job_queued`
    - [ ] Celery task span: `celery.task.enhance_ticket`
    - [ ] Custom span: `context_gathering` (with child spans for ticket_history, docs, ip_lookup)
    - [ ] Custom span: `llm.openai.completion`
    - [ ] Custom span: `api.servicedesk_plus.update_ticket`
  - [ ] Subtask 11.7: Verify parent-child relationships (FastAPI span → job_queued → Celery task → child spans)
  - [ ] Subtask 11.8: Verify span attributes include tenant_id, ticket_id, queue names, API status codes
  - [ ] Subtask 11.9: Verify sensitive data redacted (no API keys visible in span attributes)

### Task 12: Documentation
- [ ] **Create operational documentation:**
  - [ ] Subtask 12.1: Create `docs/operations/distributed-tracing-setup.md` following Story 4.5 documentation structure
  - [ ] Subtask 12.2: Document architecture: Tracing flow diagram (FastAPI → Redis → Celery → External APIs)
  - [ ] Subtask 12.3: Document deployment:
    - [ ] Docker Compose Jaeger setup
    - [ ] Kubernetes Jaeger deployment
    - [ ] OpenTelemetry configuration (environment variables)
  - [ ] Subtask 12.4: Document Jaeger UI usage:
    - [ ] How to search for traces by service name
    - [ ] How to filter by tenant_id or ticket_id
    - [ ] How to find slow traces (slow_trace=true filter)
    - [ ] How to analyze trace timeline and identify bottlenecks
  - [ ] Subtask 12.5: Document troubleshooting:
    - [ ] Missing spans (check instrumentation initialization)
    - [ ] Broken context propagation (verify carrier injection)
    - [ ] High overhead (reduce sampling rate, optimize BatchSpanProcessor)
    - [ ] Missing traces in Jaeger (check OTLP exporter endpoint configuration)
  - [ ] Subtask 12.6: Document span attribute conventions for future development
  - [ ] Subtask 12.7: Add runbook: "How to debug a failed enhancement using distributed tracing"

### Task 13: Configuration Management
- [ ] **Version control and deployment configuration:**
  - [ ] Subtask 13.1: Add OpenTelemetry environment variables to `.env.example`:
    ```
    OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
    OTEL_SERVICE_NAME=ai-agents-enhancement
    OTEL_TRACES_SAMPLER=traceidratio
    OTEL_TRACES_SAMPLER_ARG=0.1
    ```
  - [ ] Subtask 13.2: Add Jaeger environment variables to docker-compose.yml (if needed for custom config)
  - [ ] Subtask 13.3: Create Kubernetes ConfigMap for OpenTelemetry configuration (if not using env vars)
  - [ ] Subtask 13.4: Update deployment README with tracing setup instructions
  - [ ] Subtask 13.5: Commit all configuration files to git (no secrets)

### Task 14: Validation and Readiness
- [ ] **Final validation:**
  - [ ] Subtask 14.1: Verify all 16 acceptance criteria met (checklist review)
  - [ ] Subtask 14.2: Verify integration tests passing (pytest exit code 0)
  - [ ] Subtask 14.3: Verify E2E trace visible in Jaeger with all expected spans
  - [ ] Subtask 14.4: Verify performance overhead <5%
  - [ ] Subtask 14.5: Verify documentation complete and accurate
  - [ ] Subtask 14.6: Code review: Check code quality, type hints, docstrings
  - [ ] Subtask 14.7: Smoke test: Deploy to staging environment, trigger 10 test enhancements, verify all traces captured

---

## Dev Notes

### Architecture Context

Distributed tracing completes the observability stack:

```
Observability Stack (Complete):

Metrics (Story 4.1-4.2):         "What is happening?"
  → Success rate, latency, queue depth (aggregates over time)

Alerts (Story 4.4-4.5):          "When did something go wrong?"
  → Slack/PagerDuty notifications when thresholds breached

Tracing (Story 4.6):             "Why did it happen?"
  → Request flow visibility, bottleneck identification, causality
```

**Distributed tracing value:**
- **Debugging failed enhancements:** See exactly which step failed (context gathering? LLM call? API update?)
- **Performance optimization:** Identify slowest component in enhancement pipeline (e.g., ticket history search taking 30s)
- **Understanding dependencies:** Visualize service interactions (FastAPI → Redis → Celery → OpenAI → ServiceDesk Plus)
- **Correlation with logs:** Trace IDs in logs enable log search for specific request

### Key Implementation Details

**Trace Context Propagation (FastAPI → Celery):**

This is the most complex part of the implementation. By default, FastAPIInstrumentor and CeleryInstrumentor create separate trace trees because trace context doesn't automatically flow through Redis queue.

**Solution:** Manual carrier injection
```python
# In FastAPI handler (webhook receiver):
from opentelemetry.propagate import inject

carrier = {}
inject(carrier)  # Injects traceparent header

enhance_ticket.apply_async(
    args=[ticket_data],
    headers={"traceparent": carrier.get("traceparent")}
)

# In Celery task:
from opentelemetry.propagate import extract

context = extract(self.request.headers)
with tracer.start_as_current_span("enhance_ticket", context=context):
    # Task logic inherits trace context
```

**Celery Worker Initialization (Critical for Stability):**

Celery uses prefork worker model. If you initialize OpenTelemetry before worker fork, BatchSpanProcessor threads won't work correctly in child processes.

**Solution:** Use `worker_process_init` signal
```python
from celery.signals import worker_process_init
from opentelemetry.instrumentation.celery import CeleryInstrumentor

@worker_process_init.connect(weak=False)
def init_celery_tracing(*args, **kwargs):
    init_tracer_provider()  # Initialize AFTER fork
    CeleryInstrumentor().instrument()
```

**Span Hierarchy Example:**

```
trace_id: abc123 (60s total)
├─ POST /webhook/servicedesk (FastAPI) - 1ms
│  ├─ job_queued (Redis push) - 0.5ms
├─ celery.task.enhance_ticket (Celery) - 59s
   ├─ context_gathering - 30s
   │  ├─ context.ticket_history - 25s  ← BOTTLENECK IDENTIFIED!
   │  ├─ context.documentation - 3s
   │  └─ context.ip_lookup - 2s
   ├─ llm.openai.completion - 15s
   └─ api.servicedesk_plus.update_ticket - 14s
```

From this trace, we can see ticket history search is the bottleneck (25s). Action: Optimize database query or add caching.

**Performance Optimization Settings:**

```python
from opentelemetry.sdk.trace.export import BatchSpanProcessor

processor = BatchSpanProcessor(
    otlp_exporter,
    max_queue_size=2048,        # Buffer up to 2048 spans before blocking
    schedule_delay_millis=5000, # Export every 5 seconds
    max_export_batch_size=512,  # Send max 512 spans per export
    export_timeout_millis=30000 # Timeout after 30s
)
```

**Sampling Strategy:**

With 1000 tickets/day and 10% sampling rate:
- Traces captured: 100/day
- Spans per trace: ~10 spans
- Total spans stored: 1000/day
- Storage: ~1MB/day (reasonable for 90-day retention = 90MB total)

**Security - Data Redaction:**

```python
class RedactionSpanProcessor(SpanProcessor):
    SENSITIVE_KEYS = {"api_key", "secret", "password", "token", "webhook_secret"}

    def on_end(self, span):
        for key in list(span.attributes.keys()):
            # Redact sensitive keys
            if any(sensitive in key.lower() for sensitive in self.SENSITIVE_KEYS):
                span.set_attribute(key, "[REDACTED]")

            # Truncate long ticket descriptions
            if key == "ticket.description":
                span.set_attribute(key, span.attributes[key][:100] + "...")
```

### Testing Strategy

**Integration Tests (No External Dependencies):**
```python
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

# Use in-memory exporter for tests
exporter = InMemorySpanExporter()
provider.add_span_processor(SimpleSpanProcessor(exporter))

# Trigger test request
response = client.post("/webhook/servicedesk", json=test_payload)

# Assert spans created
spans = exporter.get_finished_spans()
assert len(spans) > 0
assert any(span.name == "POST /webhook/servicedesk" for span in spans)
```

**E2E Validation (With Jaeger):**
- Start docker-compose (includes Jaeger)
- Send test webhook
- Manually verify trace in Jaeger UI
- Capture screenshot for documentation

### Dependencies and Constraints

**Dependencies:**
- Story 2.11 (end-to-end enhancement workflow must be operational to trace)
- Story 4.1 (understanding of instrumentation patterns from Prometheus metrics)
- Jaeger backend (deployed as part of this story)

**Constraints:**
- Performance overhead must stay <5% (achieve <2% with proper BatchSpanProcessor config)
- Sampling required for high-volume production (10% default, configurable via env var)
- Context propagation requires manual carrier injection (automatic propagation doesn't work across Redis)
- Sensitive data must be redacted before export (compliance requirement)

**Known Limitations:**
- Trace retention: Jaeger all-in-one uses in-memory storage (traces lost on restart). For production, use persistent backend (Elasticsearch, Cassandra) or cloud service (Jaeger Cloud, Grafana Tempo)
- Sampling may miss specific requests (use deterministic sampling or force-trace flag for debugging specific tickets)

### Testing Standards

Following patterns from Story 4.5:
- **Unit tests:** Test individual functions (RedactionSpanProcessor, SlowTraceProcessor)
- **Integration tests:** Test instrumentation and span creation with in-memory exporter
- **E2E tests:** Manual validation with real Jaeger backend
- **Performance tests:** Load test with/without tracing, measure overhead
- Test coverage target: >80% for new observability code

---

## Project Structure Notes

**File Structure:**

```
src/
├── observability/
│   ├── __init__.py
│   ├── tracing.py              # NEW: Tracer provider initialization
│   ├── span_processors.py      # NEW: Custom processors (redaction, slow trace tagging)
│   └── tracers.py              # NEW: Helper functions (get_tracer)
├── main.py                      # MODIFIED: Add FastAPI instrumentation
├── worker.py                    # MODIFIED: Add Celery instrumentation with worker_process_init
└── tasks/
    └── enhancement.py           # MODIFIED: Add custom spans for enhancement workflow

k8s/
├── jaeger-deployment.yaml       # NEW: Jaeger Deployment + Service
├── jaeger-pvc.yaml              # NEW (optional): PersistentVolumeClaim for trace storage

docker-compose.yml               # MODIFIED: Add Jaeger service

docs/
└── operations/
    └── distributed-tracing-setup.md  # NEW: Operational guide

tests/
└── integration/
    └── test_distributed_tracing.py   # NEW: Integration test suite

.env.example                     # MODIFIED: Add OpenTelemetry environment variables
requirements.txt                 # MODIFIED: Add OpenTelemetry packages
```

**Configuration Files:**

```bash
# .env.example additions
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
OTEL_SERVICE_NAME=ai-agents-enhancement
OTEL_TRACES_SAMPLER=traceidratio
OTEL_TRACES_SAMPLER_ARG=0.1  # 10% sampling
```

**Docker Compose Service:**

```yaml
# docker-compose.yml addition
services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # Jaeger UI
      - "4317:4317"    # OTLP gRPC
      - "4318:4318"    # OTLP HTTP
    environment:
      - COLLECTOR_OTLP_ENABLED=true
    healthcheck:
      test: ["CMD", "wget", "--spider", "http://localhost:16686/"]
      interval: 10s
      timeout: 5s
      retries: 5
```

---

## References

### Official Documentation
- [OpenTelemetry Python Documentation](https://opentelemetry.io/docs/languages/python/)
- [OpenTelemetry Zero-Code Instrumentation](https://opentelemetry.io/docs/zero-code/python/)
- [OpenTelemetry Python Instrumentation Registry](https://opentelemetry.io/ecosystem/registry/?language=python&component=instrumentation)
- [OpenTelemetry Exporters - Jaeger](https://opentelemetry.io/docs/languages/python/exporters/#jaeger)
- [OpenTelemetry Celery Instrumentation](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/celery/celery.html)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)

### Best Practices Guides (2025 Research)
- [Integrating OpenTelemetry with FastAPI | Last9](https://last9.io/blog/integrating-opentelemetry-with-fastapi/)
- [OpenTelemetry Celery Instrumentation Guide | Uptrace](https://uptrace.dev/guides/opentelemetry-celery)
- [Implementing OpenTelemetry in FastAPI | SigNoz](https://signoz.io/blog/opentelemetry-fastapi/)
- [Top Python Monitoring Tools in 2025 | CubeAPM](https://cubeapm.com/blog/top-python-monitoring-tools/)

### Related Stories
- [Story 4.1: Implement Prometheus Metrics Instrumentation](./4-1-implement-prometheus-metrics-instrumentation.md)
- [Story 4.2: Deploy Prometheus Server](./4-2-deploy-prometheus-server-and-configure-scraping.md)
- [Story 4.4: Configure Alerting Rules](./4-4-configure-alerting-rules-in-prometheus.md)
- [Story 4.5: Integrate Alertmanager](./4-5-integrate-alertmanager-for-alert-routing.md)
- [Story 2.11: End-to-End Enhancement Workflow Integration](./2-11-end-to-end-enhancement-workflow-integration.md)

### Context Propagation Issue
- [CeleryInstrumentor linking trace issue #1002](https://github.com/open-telemetry/opentelemetry-python-contrib/issues/1002)

---

## Learnings from Previous Story

### From Story 4.5 (Alertmanager Integration - Status: done)

**Infrastructure Deployment Patterns:**
- Docker Compose: Add service with health checks, environment variables, volume mounts
- Kubernetes: Create Deployment + Service + ConfigMap + optional Secret manifests
- Configuration: YAML config file with inline documentation, separate secrets template
- Health checks: Always include liveness and readiness probes

**Documentation Best Practices:**
- Comprehensive operational guide (600-700 lines) covering:
  - Architecture overview with diagrams
  - Deployment instructions (both Docker Compose and Kubernetes)
  - Configuration examples with explanations
  - Testing and validation procedures
  - Troubleshooting guide for common issues
  - Runbooks for operational tasks
  - Secret rotation procedures

**Integration Testing Approach:**
- Created 33 integration tests for Story 4.5
- Pattern: Use pytest with fixture-based setup
- Mock external services (Slack, PagerDuty, SMTP) for tests
- Test configuration validation, health checks, routing logic
- All tests passing before marking story done

**Files Created in Story 4.5 (Patterns to Follow):**
- `alertmanager.yml` - Main configuration file (149 lines)
- `k8s/alertmanager-deployment.yaml` - Kubernetes manifests
- `k8s/alertmanager-secrets.template.yaml` - Secrets template
- `docs/operations/alertmanager-setup.md` - Operational documentation (698 lines)
- `tests/integration/test_alertmanager_integration.py` - Test suite
- Modified: `docker-compose.yml`, `prometheus.yml`, `.env.example`

**For Story 4.6:**
- Follow same deployment pattern for Jaeger (Docker Compose + Kubernetes)
- Create comprehensive documentation following alertmanager-setup.md structure
- Build integration test suite with mocked backends (no external Jaeger required for tests)
- Use environment variables for configuration (no hardcoded values)
- Document troubleshooting procedures and operational runbooks

**Technical Insights:**
- Health check endpoints are critical for Kubernetes readiness probes
- Resource limits prevent denial of service (set appropriate CPU/memory limits)
- Secrets management: Use templates with placeholders, never commit real credentials
- Configuration validation: Test YAML syntax and required fields before deployment

**Review Process Learnings:**
- Story 4.5 required follow-up work after initial code review (integration tests, documentation)
- All action items were addressed: 33 tests created, secret rotation docs added, AC clarifications made
- Final review approved after all findings resolved
- Lesson: Build comprehensive test suite and documentation upfront to minimize review cycles

---

## Dev Agent Record

### Context Reference

- `docs/stories/4-6-implement-distributed-tracing-with-opentelemetry.context.xml` - Comprehensive story context with documentation references, code artifacts, interfaces, constraints, dependencies, and testing guidance (generated 2025-11-03)

### Agent Model Used

Claude Haiku 4.5 (claude-haiku-4-5-20251001)

### Debug Log References

**Implementation Progress (2025-11-03):**
- Task 1-6 completed: Core tracing infrastructure, Jaeger deployment, FastAPI/Celery instrumentation, context propagation initiated
- OpenTelemetry SDK installed and configured with OTLP exporter
- Jaeger running on localhost:16686 (Docker Compose) and k8s/jaeger-deployment.yaml (Kubernetes)
- FastAPI automatic instrumentation via FastAPIInstrumentor
- Celery worker tracing via worker_process_init signal pattern
- Trace context carrier injection in webhook handler for FastAPI→Celery propagation

### Completion Notes List

1. ✅ Installed OpenTelemetry dependencies: api, sdk, instrumentation packages for FastAPI/Celery/HTTPX/Redis, OTLP exporter
2. ✅ Deployed Jaeger backend: Docker Compose service (jaeger:16686) + Kubernetes manifests (k8s/jaeger-deployment.yaml)
3. ✅ Created tracing infrastructure: src/monitoring/tracing.py (init_tracer_provider, get_tracer) + src/monitoring/span_processors.py (RedactionSpanProcessor, SlowTraceProcessor)
4. ✅ Instrumented FastAPI: init_tracer_provider() before app creation, FastAPIInstrumentor.instrument_app(app) after app creation
5. ✅ Instrumented Celery: worker_process_init signal handler in src/workers/celery_app.py for post-fork initialization
6. ✅ Implemented trace context propagation: inject() in webhook handler to extract traceparent and pass via job_data['trace_context']

### File List

**New Files Created:**
- src/monitoring/tracing.py - OpenTelemetry initialization and tracer management (104 lines)
- src/monitoring/span_processors.py - Custom span processors for data redaction and slow trace detection (126 lines)
- k8s/jaeger-deployment.yaml - Kubernetes Deployment, Service, and optional PVC for Jaeger (140 lines)

**Modified Files:**
- pyproject.toml - Added OpenTelemetry dependencies (8 packages: api, sdk, instrumentation-fastapi, instrumentation-celery, instrumentation-httpx, instrumentation-redis, exporter-otlp-proto-grpc)
- docker-compose.yml - Added Jaeger service with OTLP receiver ports (4317/gRPC, 4318/HTTP), UI (16686)
- src/main.py - Added tracer initialization before app creation, FastAPI instrumentation after app creation
- src/workers/celery_app.py - Added worker_process_init signal handler for post-fork tracer initialization
- src/api/webhooks.py - Added trace context carrier injection via opentelemetry.propagate.inject()
- src/monitoring/__init__.py - Exported init_tracer_provider and get_tracer functions
