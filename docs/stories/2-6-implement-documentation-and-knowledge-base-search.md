# Story 2.6: Implement Documentation and Knowledge Base Search

Status: drafted

## Story

As an enhancement agent,
I want to search knowledge base articles and documentation,
So that technicians receive relevant troubleshooting guides.

## Acceptance Criteria

1. Function created to search documentation table/external KB API for articles matching ticket keywords
2. Search uses keywords extracted from ticket description (implementation-agnostic extraction)
3. Returns top 3 relevant articles with: title, summary, URL
4. Handles KB API unavailability gracefully (returns empty list, logs warning)
5. Results cached in Redis for 1 hour (3600 seconds TTL) to reduce redundant API calls
6. API timeout set to 10 seconds; partial caching tolerates timeout gracefully
7. Unit tests with mocked KB API responses covering success, timeout, and error cases

## Tasks / Subtasks

- [ ] **Task 1: Design KB search service interface** (AC: #1, #2, #3)
  - [ ] Define function signature: `async def search_knowledge_base(tenant_id, description, kb_base_url, kb_api_key, limit=3)`
  - [ ] Document parameter meanings and return type
  - [ ] Define return type: `List[Dict]` with keys: title, summary, url
  - [ ] Create Pydantic model or dataclass for article response (optional for MVP)
  - [ ] Document assumptions about KB API interface (endpoint, auth, response format)

- [ ] **Task 2: Implement KB API client with configuration** (AC: #1, #3)
  - [ ] Create `src/services/kb_search.py` (NEW service layer)
  - [ ] Implement async HTTP client using httpx (consistent with existing codebase)
  - [ ] Load KB API configuration from tenant_configs table or environment (design decision needed)
  - [ ] Implement KB API call: GET {kb_base_url}/api/search with params: query, limit
  - [ ] Parse response JSON: extract title, summary, url fields from response
  - [ ] Truncate summaries to reasonable length (200 chars per tech-spec)
  - [ ] Log API call with correlation_id and tenant_id for debugging

- [ ] **Task 3: Implement Redis caching for KB results** (AC: #5, #6)
  - [ ] Design cache key strategy: `kb_search:{tenant_id}:{hash(description)}` (per tech-spec)
  - [ ] Implement cache check before API call: `redis_client.get(cache_key)`
  - [ ] If cache hit: log cache hit event, return cached results
  - [ ] If cache miss: proceed to API call
  - [ ] After API success: cache results with 1-hour TTL: `redis_client.setex(cache_key, 3600, json.dumps(articles))`
  - [ ] Import redis_client from `src/cache/redis_client.py`
  - [ ] Handle Redis connection errors gracefully (log, continue without cache)

- [ ] **Task 4: Implement error handling and graceful degradation** (AC: #4, #6)
  - [ ] Wrap KB API call in try/except
  - [ ] Handle `httpx.TimeoutException` (10s timeout per AC): log warning, return empty list
  - [ ] Handle `httpx.HTTPStatusError` (non-200 responses): log error, return empty list
  - [ ] Handle Redis errors (get/setex failures): log warning, continue without caching
  - [ ] All error paths must log with correlation_id and tenant_id
  - [ ] Implement exponential backoff retry logic (optional, per tech-spec 2 retries)
  - [ ] No exceptions propagated to caller; always return List[Dict] (empty if all failed)

- [ ] **Task 5: Create unit tests for KB search** (AC: #7)
  - [ ] Create `tests/unit/test_kb_search.py` (NEW)
  - [ ] Test: Valid KB API response → Returns 3 articles with title, summary, url
  - [ ] Test: Empty KB API response → Returns empty list (not an error)
  - [ ] Test: KB API timeout (10s) → Returns empty list, logs warning
  - [ ] Test: KB API returns 500 error → Returns empty list, logs error
  - [ ] Test: Cache hit → Returns cached results without calling API (verify no API call made)
  - [ ] Test: Cache miss → Calls API and caches result
  - [ ] Test: Redis unavailable → Falls back to API call without caching
  - [ ] Test: Tenant isolation → Cache keys include tenant_id (different tenants don't share cache)
  - [ ] Test: Concurrent requests for same query → Cache hit reduces API calls
  - [ ] Mock httpx.AsyncClient.get()
  - [ ] Mock redis_client.get() and redis_client.setex()
  - [ ] Use pytest-asyncio for async test execution

- [ ] **Task 6: Integration with enhancement workflow** (AC: #1, #2, #3)
  - [ ] Review Story 2.8 LangGraph workflow structure (integration point)
  - [ ] Understand how context gathering is called in enhance_ticket task (Story 2.4)
  - [ ] Document KB search as input to LangGraph node (Story 2.8 implementation detail)
  - [ ] Verify KB search results are structured as WorkflowState fields
  - [ ] Cross-reference with tech-spec-epic-2.md Section 4 KB Search Implementation

- [ ] **Task 7: Create integration test** (AC: #4, #5, #6)
  - [ ] Create `tests/integration/test_kb_search_integration.py` (NEW)
  - [ ] Set up test Redis instance (use test database)
  - [ ] Create mock KB API server or use responses library for HTTP mocking
  - [ ] Test: Search KB for "database connection issue" → Returns relevant articles from mock API
  - [ ] Test: Second search with same query → Verify cache was used (no second API call)
  - [ ] Test: Cache expiration after 1 hour → Subsequent search makes new API call
  - [ ] Test: KB API timeout behavior → Graceful degradation after 10s timeout
  - [ ] Test: Multiple tenants → Cache keys keep results isolated per tenant

- [ ] **Task 8: Error handling and logging verification** (AC: #4)
  - [ ] Verify all error paths log with structured format: tenant_id, correlation_id, error_type, error_message
  - [ ] Test KB API unavailability scenarios and verify logs
  - [ ] Test timeout scenarios and verify logs contain timing information
  - [ ] Ensure no sensitive data (API keys, URLs) logged in error messages
  - [ ] Test concurrent failures don't overwhelm logs

- [ ] **Task 9: Documentation and API contract** (AC: #1, #2, #3)
  - [ ] Document KB search API contract: Expected response schema from external KB API
  - [ ] Create example KB API response in docstring
  - [ ] Document configuration requirements: KB base URL, API key location
  - [ ] Update README.md with "Knowledge Base Integration" section
  - [ ] Document tenant configuration for KB credentials in schema or setup guide

- [ ] **Task 10: Performance and monitoring setup** (AC: #6)
  - [ ] Log KB API response time (milliseconds) for monitoring
  - [ ] Log cache hit/miss ratio per tenant (for observability)
  - [ ] Implement timeout enforcement: `async with httpx.AsyncClient(timeout=10.0):`
  - [ ] Consider adding Prometheus metrics for KB search latency (future, Epic 4)

## Dev Notes

### Architecture Alignment

This story implements **knowledge base search** for the enhancement agent's context gathering capability (Epic 2, Stories 2.5-2.7). Story 2.6 is the second context source (after Story 2.5: ticket history search), feeding documentation and troubleshooting guides to the LangGraph workflow (Story 2.8).

**Design Pattern:** Async KB API Client with Redis Caching and Graceful Degradation

**Integration Points:**
- **Input**: Ticket description (from enhance_ticket task in Story 2.4)
- **Output**: List of top 3 KB articles with title, summary, URL
- **Cache Layer**: Redis (consistent with Story 1.4 queue infrastructure)
- **Error Handling**: Timeout gracefully after 10 seconds, log warning, continue with empty results
- **Tenant Isolation**: Cache keys include tenant_id; API credentials per-tenant from tenant_configs

**Data Flow:**
```
enhance_ticket task (Story 2.4)
      │
      ├─ Extract description from ticket payload
      │
      └─ Call: search_knowledge_base(tenant_id, description, kb_config)
         │
         ├─ Check Redis cache: kb_search:{tenant_id}:{hash(description)}
         │
         ├─ If cache hit: return cached articles
         │
         ├─ If cache miss:
         │  ├─ Call KB API: GET {kb_base_url}/api/search
         │  ├─ Timeout: 10 seconds (per AC #6)
         │  ├─ Retry: Exponential backoff (optional per tech-spec)
         │  └─ Parse response: Extract title, summary, url from articles
         │
         ├─ Cache result in Redis: TTL = 1 hour (3600 seconds)
         │
         └─ Return: List[Dict] with {title, summary, url} for top 3 articles
            (or empty list on timeout/error)
```

**Sequence with Related Stories:**
1. **Story 2.5**: Ticket history search (completed) → Similar resolved tickets
2. **Story 2.6** (this): Knowledge base search → Troubleshooting documentation
3. **Story 2.7**: IP address lookup → System information
4. **Story 2.8**: LangGraph orchestration → Parallel execution of 2.5, 2.6, 2.7
5. **Story 2.9**: LLM synthesis → Analyze combined context, generate enhancement
6. **Story 2.10**: ServiceDesk Plus API → Post enhancement back to ticket

### Project Structure Notes

**New Files to Create:**
- `src/services/kb_search.py` - KB API client with Redis caching (NEW)
- `tests/unit/test_kb_search.py` - Unit tests (NEW)
- `tests/integration/test_kb_search_integration.py` - Integration tests (NEW)

**Files to Reference:**
- `src/cache/redis_client.py` - Redis client initialization (Story 1.4)
- `src/config.py` - Configuration management (KB API endpoint, timeouts)
- `src/utils/logger.py` - Structured logging with correlation_id
- `src/database/models.py` - tenant_configs table for KB credentials
- `src/workers/tasks.py` - enhance_ticket task (Story 2.4) which calls KB search
- `docs/tech-spec-epic-2.md#4-Context-Gathering-Knowledge-Base-Search` - Implementation spec

**Naming Conventions:**
- Function: `search_knowledge_base()` (verb-first, clear intent)
- Module: `kb_search.py` (concise, domain-clear)
- Cache key pattern: `kb_search:{tenant_id}:{hash(description)}` (hierarchical, includes context)
- Error messages: "KB API timeout" (clear, actionable)
- Log fields: `kb_search_latency_ms`, `cache_hit` (observability-focused)

### Learnings from Previous Story (2.5B)

**From Story 2.5B: Store Resolved Tickets Automatically (Status: review)**

**Patterns to Reuse:**
- Async function patterns: Use `async def` for I/O-bound operations
- Error handling: Graceful degradation with logging (don't crash on external API failure)
- Structured logging: Log with correlation_id, tenant_id, operation details
- Redis client usage: `from src.cache.redis_client import redis_client`
- Configuration management: Load credentials from tenant_configs table or environment
- Tenant isolation: Filter all queries/caches by tenant_id to prevent cross-tenant leakage

**Database Access Pattern (from Story 2.5B):**
- Async database session: `from src.database.session import async_session_maker`
- Query with tenant isolation: WHERE tenant_id = ? to prevent cross-tenant access
- Error handling: Catch DatabaseError, log, continue without data (graceful degradation)

**Webhook Integration Context (Story 2.5B):**
- Non-blocking pattern: Return response immediately, background processing continues
- UPSERT idempotency: Duplicate requests handled without duplication (not applicable to KB search, but useful pattern to understand)
- Logging pattern: correlation_id for request traceability across services

**Key Implementation Files to Reference:**
- `src/cache/redis_client.py` - Redis initialization from Story 1.4
- `src/services/ticket_storage_service.py` - Example service layer async function (Story 2.5B)
- `src/utils/logger.py` - Structured logging setup

**New Architectural Pattern (Story 2.6):**
- **External API Integration with Caching**: KB search demonstrates calling external KB API with Redis caching and timeout handling (pattern will be reused in Story 2.9 for OpenRouter LLM API)
- **Cache Strategy**: Redis caching for read-heavy external API calls (reduces latency, reduces cost)
- **Graceful Degradation**: Failed external APIs don't crash system; empty results acceptable for enhancement to continue (aligns with Epic 2 resilience patterns)

### Testing Strategy

**Unit Tests (test_kb_search.py):**

1. **KB API Success Path:**
   - Input: `search_knowledge_base(tenant_id="acme", description="database error")`
   - Mock `httpx.AsyncClient.get()` → returns 200 with articles
   - Expected: List[Dict] with 3 articles, each with title, summary, url
   - Verify: KB API called with correct params (query, limit), response parsed correctly

2. **KB API Timeout:**
   - Mock `httpx.AsyncClient.get()` → raises `httpx.TimeoutException`
   - Expected: Empty list returned, no exception raised
   - Verify: Log contains warning "KB API timeout"

3. **KB API Error (500):**
   - Mock `httpx.AsyncClient.get()` → returns 500
   - Expected: Empty list, no exception
   - Verify: Log contains error "KB API error: 500"

4. **Redis Cache Hit:**
   - Mock `redis_client.get()` → returns cached articles JSON
   - Expected: Cached articles returned
   - Verify: No `httpx.AsyncClient.get()` call made (API not called)

5. **Redis Cache Miss:**
   - Mock `redis_client.get()` → returns None
   - Mock `httpx.AsyncClient.get()` → returns articles
   - Expected: API called, results cached
   - Verify: `redis_client.setex()` called with 3600 TTL

6. **Tenant Isolation:**
   - Cache key should include `tenant_id`
   - Different tenants shouldn't share cache
   - Verify: `kb_search:acme:hash1` ≠ `kb_search:other:hash1`

7. **Redis Error Handling:**
   - Mock `redis_client.get()` → raises RedisError
   - Expected: Fall back to API call (log warning)
   - Verify: API called despite Redis error

**Integration Tests (test_kb_search_integration.py):**

1. **End-to-End KB Search:**
   - Setup: Test Redis instance, mock KB API server
   - Send: search_knowledge_base(tenant_id, "database connectivity")
   - Verify: Returns articles from mock KB API

2. **Cache Persistence:**
   - First search: Cache miss, API called
   - Second search (same query): Cache hit, no API call
   - Verify: Cache persists across calls

3. **Concurrent Requests:**
   - Send 5 concurrent searches for same query
   - Expected: First request hits API, others hit cache
   - Verify: Only 1 KB API call made, 4 cache hits

4. **Multi-Tenant Isolation:**
   - Search with tenant=A, query="issue1"
   - Search with tenant=B, query="issue1"
   - Expected: Separate cache entries
   - Query database: Verify tenant_id filters results

### References

- [Source: docs/tech-spec-epic-2.md#4-Context-Gathering-Knowledge-Base-Search] - Implementation specification for KB search with caching
- [Source: docs/epics.md#Story-2.6] - Story definition and acceptance criteria
- [Source: docs/stories/2-5B-store-resolved-tickets-automatically.md] - Related story, async patterns and error handling
- [Source: docs/stories/2-5-implement-ticket-history-search-context-gathering.md] - Previous context gathering story (referenced as context pattern)
- [Source: docs/architecture.md#Epic-2-Architecture] - Architecture diagram showing KB search node in LangGraph workflow
- [Source: docs/PRD.md#Functional-Requirements] - FR005: Search ticket history, FR006: Knowledge base integration, FR008: Gathering monitoring data
- [Source: src/cache/redis_client.py] - Redis client initialization (Story 1.4)
- [Source: src/config.py] - Configuration and environment variables
- [Source: src/utils/logger.py] - Structured logging patterns

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

claude-haiku-4-5-20251001 (Haiku 4.5)

### Debug Log References

### Completion Notes List

### File List

---

## Change Log

- 2025-11-02: Story drafted by Scrum Master (Bob, SM Agent)
  - Extracted requirements from tech-spec-epic-2.md section 4 (KB Search) and epics.md Story 2.6
  - Reviewed previous story 2.5B learnings: async patterns, graceful degradation, structured logging
  - Designed KB search with Redis caching (1hr TTL) per tech-spec Section 4
  - Emphasized timeout handling (10s) and graceful degradation (return empty on failure)
  - Integrated with tenant_configs table for KB API credentials (multi-tenant design)
  - Defined 10 tasks covering service implementation, caching, error handling, testing
  - Ready for Developer Agent implementation
