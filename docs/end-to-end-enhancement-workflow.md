# End-to-End Enhancement Workflow (Story 2.11)

**Author:** Amelia (Developer Agent)
**Date:** 2025-11-02
**Epic:** 2 - AI-Powered Ticket Enhancement Pipeline
**Story:** 2.11 - End-to-End Enhancement Workflow Integration
**Status:** Implementation Complete

---

## Overview

This document describes the complete enhancement workflow from ServiceDesk Plus webhook receipt through ticket update and history recording. The workflow orchestrates five Stories (2.1, 2.8, 2.9, 2.10, 2.11) into a single coherent pipeline with distributed tracing, graceful degradation, and performance monitoring.

---

## Complete Workflow Flow

### Phase 1: Webhook Reception & Queueing (Story 2.1, 2.3)
**Component:** `src/api/webhooks.py` → `src/queue/redis_queue.py`

```
ServiceDesk Plus Webhook
    ↓ (HTTPS POST)
FastAPI Webhook Endpoint (/webhook/servicedesk)
    ↓ (Signature validation)
Webhook Validator (Story 2.2)
    ↓ (Valid request)
Redis Queue Push (Story 2.3)
    ↓ (JSON serialized job)
Job: { job_id, ticket_id, tenant_id, description, priority, timestamp, created_at }
```

**Correlation ID Generated:** `uuid.uuid4()` format (required for distributed tracing)

---

### Phase 2: Celery Task Orchestration (Story 2.11 - Main Story)
**Component:** `src/workers/tasks.py` → `enhance_ticket()` Celery task

#### 2.1 - Task Initialization
- Task receives job data from Redis queue (via Celery worker)
- Generates correlation_id (UUID4) for distributed tracing
- Loads tenant configuration from database
- Creates enhancement_history record with status='pending'

**Database Record Created:**
```python
EnhancementHistory(
    correlation_id=correlation_id,
    tenant_id=tenant_id,
    ticket_id=ticket_id,
    job_id=job_id,
    status='pending',  # pending → completed/failed
    started_at=now(),
    correlation_id_str=str(correlation_id)  # For logging
)
```

---

#### 2.2 - Context Gathering (Story 2.8 Integration)
**Component:** `src/workflows/context_gathering.py` → `execute_context_gathering()`

**Timeout:** 30 seconds (asyncio.wait_for, async timeout handling)

**Context Gathered:**
- Similar Tickets: Ranked by similarity_score (TF-IDF based)
- Knowledge Base Articles: Ranked by relevance_score
- IP Address Cross-Reference: Hostname, role, last_seen
- Errors Collection: Failed retrieval nodes with messages

**Correlation ID Propagation:** Passed through entire LangGraph state machine

**Failure Mode (AC5):**
- Timeout after 30s: Continue with empty/partial context
- Individual node failures: Gracefully skip failed nodes, record errors
- **Result:** Partial context is usable for LLM synthesis

**Example Partial Context:**
```python
{
    "similar_tickets": [...],       # Success
    "kb_articles": [],              # Failed (timeout)
    "ip_info": [...],               # Success
    "errors": [
        {"node_name": "kb_search", "message": "Timeout after 10s"}
    ]
}
```

---

#### 2.3 - LLM Synthesis (Story 2.9 Integration)
**Component:** `src/services/llm_synthesis.py` → `synthesize_enhancement()`

**Provider:** OpenRouter API Gateway (OpenAI SDK compatible)
**Model:** `gpt-4` or configured model per tenant

**Input:** WorkflowState from Story 2.8
**Output:** Markdown-formatted enhancement recommendations

**Fallback Mode (AC5 - Graceful Degradation):**
```
LLM API Call Fails (network error, rate limit, auth failure)
    ↓
Trigger: _format_context_fallback()
    ↓
Generate markdown without AI:
  ## Enhancement Context (Generated Without AI)

  ### Similar Tickets (3)
  - **TKT-11111**: Previous server slowness issue
  - **TKT-22222**: Performance degradation

  ### IP Cross-Reference (1)
  - server-prod-01 (10.0.1.100) [web-server role]

  [Plus KB articles and error details]
    ↓
Continue to Phase 2.4
```

**Correlation ID Usage:** Logged in all OpenRouter API calls for tracing

---

#### 2.4 - ServiceDesk Plus API Update (Story 2.10 Integration)
**Component:** `src/services/servicedesk_client.py` → `update_ticket_with_enhancement()`

**Operation:** Append enhancement to ticket description/notes

**Update Format:**
```
Original Description: "Server is running slow"

Updated Description:
"Server is running slow

---
## Enhancement Recommendations

[Content from Story 2.9 or fallback]

Generated: 2025-11-02 15:30:45 UTC | Correlation ID: 550e8400-e29b-41d4-a716-446655440000"
```

**API Retry Logic:**
- HTTP 429 (Rate Limit): Retry with exponential backoff
- HTTP 5xx (Server Error): Retry with exponential backoff
- HTTP 4xx (Client Error except 429): Fail immediately (don't retry)

**Correlation ID Logging:** All requests logged with correlation_id for audit trail

---

#### 2.5 - History Recording & Task Completion
**Component:** Database → `EnhancementHistory` table

**Status Transition:**
```
pending (created in 2.1)
    ↓ (After LLM synthesis completes)
completed (if API update succeeds)
    or
failed (if any phase fails)
```

**Final Record Update:**
```python
EnhancementHistory(
    correlation_id=correlation_id,
    # ... other fields ...
    status='completed' or 'failed',
    completed_at=now(),
    llm_provider='openrouter',
    llm_model='gpt-4',
    context_nodes_success=4,    # Number of successful context nodes
    context_nodes_failed=0,      # Number of failed nodes
    processing_time_ms=1234,     # Total execution time
    error_message=None           # Only if status='failed'
)
```

---

## Performance Requirements (AC4)

**NFR001: Response Time - Hard Limit**
- Timeout: 120 seconds (Celery hard timeout)
- Soft Limit: 100 seconds (SoftTimeLimitExceeded exception)

**Expected Performance (P95):**
- Context Gathering: ~450ms
- LLM Synthesis: ~1500ms
- API Update: ~300ms
- Database Operations: ~150ms
- **Total P95: <3 seconds** (well under 60s requirement)

**Monitoring:**
```python
# In enhance_ticket() task
start_time = time.time()
processing_time_ms = int((time.time() - start_time) * 1000)
# Logged and recorded in EnhancementHistory
```

---

## Correlation ID & Distributed Tracing (AC6)

**Format:** UUID4 format (36 chars, 4 hyphens)

**Propagation Path:**
```
1. Generated in enhance_ticket(): correlation_id = str(uuid.uuid4())
2. Stored in EnhancementHistory.correlation_id (database)
3. Passed to execute_context_gathering() (Story 2.8)
4. Passed to synthesize_enhancement() (Story 2.9)
5. Passed to update_ticket_with_enhancement() (Story 2.10)
6. Included in all log entries:
   logger.info("Processing enhancement", extra={"correlation_id": correlation_id})
```

**Log Format (Loguru):**
```json
{
  "text": "ServiceDesk API request",
  "record": {
    "time": "2025-11-02T15:30:45.123Z",
    "level": "INFO",
    "message": "ServiceDesk API request",
    "extra": {
      "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
      "ticket_id": "TKT-12345",
      "tenant_id": "test-tenant"
    }
  }
}
```

---

## Error Handling & Graceful Degradation (AC5)

### Scenario 1: Context Gathering Timeout

**Trigger:** `asyncio.TimeoutError` after 30 seconds

**Handling:**
```python
try:
    context = await asyncio.wait_for(
        execute_context_gathering(...),
        timeout=30
    )
except asyncio.TimeoutError:
    logger.warning("Context gathering timed out",
                   extra={"correlation_id": correlation_id})
    context = {"errors": [{"node_name": "context_gathering", "message": "Timeout"}]}
    # Continue to LLM synthesis with empty context
```

**Result:** Partial context (empty) is still usable for fallback formatting

---

### Scenario 2: LLM API Failure

**Trigger:** Network error, rate limit, authentication failure

**Handling:**
```python
try:
    enhancement = await synthesize_enhancement(context, correlation_id)
except Exception as exc:
    logger.error("LLM synthesis failed",
                 extra={"correlation_id": correlation_id, "error": str(exc)})
    enhancement = _format_context_fallback(context)
    # Continue to API update with fallback text
```

**Result:** Ticket still gets enhanced with fallback markdown (no AI)

---

### Scenario 3: ServiceDesk API Failure

**Trigger:** Network error, API error, rate limit

**Handling:**
```python
try:
    success = await update_ticket_with_enhancement(
        base_url, api_key, ticket_id, enhancement, correlation_id
    )
    if not success:
        raise Exception("ServiceDesk API returned false")
except Exception as exc:
    logger.error("ServiceDesk update failed",
                 extra={"correlation_id": correlation_id})
    # Update history status to 'failed'
    history.status = 'failed'
    history.error_message = str(exc)
    raise  # Task fails, can be retried
```

**Result:** Enhancement history records failure, task can be retried by Celery

---

### Scenario 4: Database Session Error

**Trigger:** Connection lost, transaction rollback

**Handling:**
```python
try:
    async with async_session_maker() as session:
        history = EnhancementHistory(...)
        session.add(history)
        await session.commit()
except Exception as exc:
    logger.error("Failed to create enhancement history",
                 extra={"correlation_id": correlation_id})
    # Continue - history recording failure doesn't block enhancement
```

**Result:** Enhancement may succeed even if history recording fails

---

## Enhancement History Lifecycle

### States:

1. **pending** - Created at task start, awaiting processing
2. **completed** - Enhancement successfully applied to ticket
3. **failed** - Enhancement processing failed (can be retried)

### Database Schema:

```sql
CREATE TABLE enhancement_history (
    id BIGSERIAL PRIMARY KEY,
    correlation_id UUID NOT NULL UNIQUE,  -- For distributed tracing
    tenant_id VARCHAR(255) NOT NULL,
    ticket_id VARCHAR(255) NOT NULL,
    job_id UUID NOT NULL,
    status VARCHAR(50) NOT NULL,  -- pending, completed, failed

    -- Timing
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    processing_time_ms INTEGER,

    -- Context
    context_nodes_success INTEGER,
    context_nodes_failed INTEGER,

    -- LLM
    llm_provider VARCHAR(100),
    llm_model VARCHAR(100),

    -- Error tracking
    error_message TEXT,

    -- Audit
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_correlation_id ON enhancement_history(correlation_id);
CREATE INDEX idx_tenant_ticket ON enhancement_history(tenant_id, ticket_id);
CREATE INDEX idx_status ON enhancement_history(status);
```

---

## Testing Strategy (AC7)

### Unit Tests (Isolated)
- `test_correlation_id_generation`: UUID4 format validation
- `test_job_data_validation`: EnhancementJob schema validation
- `test_workflow_state_structure`: WorkflowState compliance
- `test_fallback_context_formatting_standalone`: Markdown generation without AI

### Integration Tests (End-to-End)
- `test_performance_latency_calculation`: <60s requirement
- `test_partial_context_with_errors`: Graceful degradation
- Complete pipeline mock: webhook → context → LLM → API → history

### Test File Location
`tests/integration/test_end_to_end_workflow.py`

**Test Results:** All 6 tests PASSING ✓

---

## Logging & Observability

### Log Levels Used:
- `DEBUG`: Detailed context gathering steps, LLM token counts
- `INFO`: Task start/end, API calls, history recording
- `WARNING`: Timeouts, partial failures, fallback activation
- `ERROR`: Failed API calls, database errors, unrecoverable failures

### Structured Logging Example:
```python
logger.info(
    "Enhancement completed",
    extra={
        "correlation_id": correlation_id,
        "tenant_id": tenant_id,
        "ticket_id": ticket_id,
        "processing_time_ms": 1234,
        "status": "completed",
        "context_nodes": 4,
    }
)
```

### Correlation ID in Logs:
Every log entry includes `correlation_id` in `extra` dict for traceability across:
- FastAPI webhook endpoint
- Redis queue operations
- Celery task execution
- LangGraph workflow
- OpenRouter API calls
- ServiceDesk Plus API calls
- Database operations

---

## Deployment Checklist

### Pre-Deployment:
- [ ] All 6 integration tests passing
- [ ] Unit tests for all Stories (2.8, 2.9, 2.10) passing
- [ ] Code review completed
- [ ] Performance benchmarks validated (<60s requirement)
- [ ] Correlation ID propagation verified in logs

### Deployment:
- [ ] Database migrations applied (enhancement_history table)
- [ ] Celery task registered (tasks.enhance_ticket)
- [ ] Environment variables configured (OPENROUTER_API_KEY)
- [ ] Redis queue available and healthy
- [ ] Kubernetes deployment updated (if applicable)

### Post-Deployment:
- [ ] Monitor enhancement_history table for success/failure rates
- [ ] Sample 10 enhanced tickets for quality validation
- [ ] Check logs for correlation ID consistency
- [ ] Validate performance metrics (<60s P95)

---

## References

- **Story 2.1:** FastAPI Webhook Receiver
- **Story 2.2:** Webhook Signature Validation
- **Story 2.3:** Redis Queue Implementation
- **Story 2.8:** LangGraph Context Gathering
- **Story 2.9:** OpenRouter LLM Synthesis
- **Story 2.10:** ServiceDesk Plus API Client
- **Story 2.11:** This End-to-End Integration

**Architecture Document:** `docs/architecture.md`
**Tech Spec Epic 2:** `docs/tech-spec-epic-2.md`
