# Story 8.8A: Fix OpenAPI API Test Mocks

**Epic:** 8 - LLM Orchestration & Agent Management
**Story ID:** 8.8A
**Created:** 2025-11-06
**Type:** Technical Debt / Test Infrastructure
**Priority:** Medium
**Estimated Effort:** 30-90 minutes
**Parent Story:** 8.8 - OpenAPI Tool Upload and Auto-Generation

---

## Overview

**As a** developer maintaining the OpenAPI tool integration
**I want** all API unit tests to pass with proper mocking
**So that** we have complete test coverage and confidence in the API layer

---

## Context

Story 8.8 was completed with **88% test pass rate (60/68 tests passing)**. The 8 failing tests are all API endpoint unit tests with complex async function mocking issues. The **actual functionality works correctly** (proven by 10/10 integration tests passing), but the unit test mocking strategy needs refinement.

**Current Status:**
- ✅ All functionality implemented (8/8 ACs complete)
- ✅ Integration tests: 10/10 passing (100%)
- ✅ Parser tests: 17/17 passing (100%)
- ✅ MCP generator tests: 24/24 passing (100%)
- ✅ API creation tests: 3/3 passing (100%)
- ✅ API parse tests: 2/3 passing (67%)
- ❌ API connection tests: 0/4 passing (0%)
- ❌ API list/get tests: 0/4 passing (0%)

**Root Cause:** Complex async function mocking with FastAPI TestClient requires careful coordination between `@patch`, `AsyncMock`, and `dependency_overrides` patterns.

---

## Acceptance Criteria

### AC#1: Test Connection Endpoint Mocks Fixed
**Given** the `/api/openapi-tools/test-connection` endpoint tests
**When** running pytest on `test_connection_success_200`, `test_connection_401_unauthorized`, `test_connection_timeout_error`
**Then** all 3 tests pass with properly mocked `validate_openapi_connection` function
**And** no "coroutine was never awaited" warnings appear

### AC#2: Test Connection Invalid Spec Mock Fixed
**Given** the `test_connection_invalid_spec_returns_400` test
**When** running pytest with mocked `parse_openapi_spec` raising ValueError
**Then** the test passes and properly catches the validation error

### AC#3: List Tools Endpoint Mocks Fixed
**Given** the `/api/openapi-tools` GET endpoint tests
**When** running pytest on `test_list_tools_for_tenant` and `test_list_tools_with_status_filter`
**Then** both tests pass with properly mocked `OpenAPIToolService.get_tools` method
**And** query parameters (`tenant_id`, `status`) are correctly validated

### AC#4: Get Tool Endpoint Mock Fixed
**Given** the `/api/openapi-tools/{id}` GET endpoint tests
**When** running pytest on `test_get_tool_by_id_success` and `test_get_tool_not_found_returns_404`
**Then** both tests pass with properly mocked `OpenAPIToolService.get_tool_by_id` method

### AC#5: Parse Spec Common Issues Mock Fixed
**Given** the `/api/openapi-tools/parse` endpoint test
**When** running pytest on `test_parse_spec_with_common_issues_returns_errors`
**Then** the test passes with properly mocked `detect_common_issues` function

### AC#6: All Story 8.8 Tests Pass
**Given** all test fixes are implemented
**When** running pytest on all Story 8.8 test files
**Then** all 68 tests pass (100% pass rate)
**And** no warnings about coroutines or async issues appear

### AC#7: Testing Best Practices Documented
**Given** the refactored test code
**When** reviewing test patterns
**Then** inline comments explain the async mocking approach
**And** a test pattern guide is added to `tests/README.md` or story documentation

---

## Implementation Approach

### Option A: Convert to Integration Tests (RECOMMENDED - 30 min)

**Rationale:** Integration tests provide better real-world coverage and are easier to maintain. We already have 10 passing integration tests proving the pattern works.

**Steps:**
1. Move failing tests from `tests/unit/test_openapi_tools_api.py` to `tests/integration/test_openapi_tools_api.py`
2. Replace `TestClient` with actual HTTP calls to running FastAPI app
3. Use real database fixtures (like existing integration tests)
4. Remove complex mocking, use real service layer
5. Update test markers to `@pytest.mark.integration`

**Pros:**
- Faster implementation (~30 min)
- Better coverage (tests real behavior)
- Easier to maintain (no complex mocks)
- Follows existing integration test patterns

**Cons:**
- Slightly slower test execution
- Requires database/Redis for tests

---

### Option B: Fix Unit Test Mocking (ALTERNATIVE - 90 min)

**Rationale:** Maintains unit test isolation, but requires significant async mocking expertise.

**Known Issues to Fix:**

1. **AsyncMock with TestClient:**
   - Problem: `@patch` creates regular `MagicMock`, not `AsyncMock`
   - Solution: Use `new_callable=AsyncMock` parameter
   - Example: `@patch("...validate_openapi_connection", new_callable=AsyncMock)`

2. **Service Method Mocking:**
   - Problem: Service methods return coroutines that aren't awaited
   - Solution: Mock at service layer with proper async return values
   - Example: `mock_service.get_tools = AsyncMock(return_value=[...])`

3. **Dependency Override Conflicts:**
   - Problem: `dependency_overrides` and `@patch` may conflict
   - Solution: Use one approach consistently (prefer `dependency_overrides`)

**Steps:**
1. Review working integration tests for async patterns
2. Apply `new_callable=AsyncMock` to all async function patches
3. Fix service method mocking with `AsyncMock(return_value=...)`
4. Ensure `dependency_overrides` properly configured for all tests
5. Run each test individually to debug async warnings
6. Document patterns in inline comments

**Pros:**
- Maintains unit test isolation
- Faster test execution
- No database/Redis dependency

**Cons:**
- Time-intensive (~90 min)
- Complex async mocking patterns
- Higher maintenance burden

---

## Files to Modify

### Primary Files:
- `tests/unit/test_openapi_tools_api.py` (lines 248-505) - OR move to integration
- `tests/integration/test_openapi_tools_api.py` (NEW - if Option A)
- `tests/README.md` (NEW section on async mocking patterns)

### Reference Files (for patterns):
- `tests/integration/test_openapi_tool_workflow.py` (working async patterns)
- `tests/unit/test_mcp_tool_generator.py` (working AsyncMock examples)

---

## Task Breakdown

### Option A Tasks (Recommended):
- [ ] **Task 1:** Create `tests/integration/test_openapi_tools_api.py` (10 min)
- [ ] **Task 2:** Copy 8 failing tests to integration file (5 min)
- [ ] **Task 3:** Convert mocks to real service calls with database fixtures (10 min)
- [ ] **Task 4:** Run tests and fix any database fixture issues (5 min)
- [ ] **Task 5:** Document pattern in `tests/README.md` (5 min)
- [ ] **Task 6:** Verify all 68 tests pass (5 min)

**Total: ~30 minutes**

### Option B Tasks (Alternative):
- [ ] **Task 1:** Add `new_callable=AsyncMock` to test_connection patches (15 min)
- [ ] **Task 2:** Fix service method mocking for list/get tests (20 min)
- [ ] **Task 3:** Debug and fix parse_spec common issues mock (15 min)
- [ ] **Task 4:** Resolve dependency override conflicts (20 min)
- [ ] **Task 5:** Run each test individually to debug warnings (15 min)
- [ ] **Task 6:** Document async mocking patterns in comments (5 min)
- [ ] **Task 7:** Create `tests/README.md` guide section (10 min)

**Total: ~90 minutes**

---

## Definition of Done

- [ ] All 68 Story 8.8 tests pass (100% pass rate)
- [ ] No pytest warnings about coroutines or async issues
- [ ] Test execution time remains reasonable (<5 seconds for integration, <1 second for unit)
- [ ] Test patterns documented in `tests/README.md` or inline comments
- [ ] Code review approval obtained
- [ ] Tests run successfully in CI/CD pipeline

---

## Technical Notes

### Working Async Mock Pattern (from test_mcp_tool_generator.py):
```python
# Example of working AsyncMock with httpx
@pytest.mark.asyncio
async def test_connection_success(httpx_mock):
    httpx_mock.add_response(json={"status": "ok"}, status_code=200)
    result = await validate_openapi_connection(spec, auth_config, base_url)
    assert result["success"] is True
```

### Working Integration Test Pattern (from test_openapi_tool_workflow.py):
```python
@pytest.mark.asyncio
async def test_full_workflow(db_session):
    """Test with real database and services."""
    service = OpenAPIToolService(db_session)
    tool, count = await service.create_tool(tool_data)
    assert tool.id is not None
```

### Dependency Override Pattern (currently in test file):
```python
@pytest.fixture
def app(mock_db):
    """FastAPI test app with dependency overrides."""
    from src.api.dependencies import get_tenant_db

    app = FastAPI()
    app.include_router(router)

    async def override_get_tenant_db():
        yield mock_db

    app.dependency_overrides[get_tenant_db] = override_get_tenant_db
    return app
```

---

## Success Metrics

- **Primary:** Test pass rate: 60/68 (88%) → 68/68 (100%)
- **Secondary:** Zero pytest warnings
- **Tertiary:** Test execution time <5 seconds total for Story 8.8 tests

---

## Dependencies

- **Blocked By:** None (can start immediately)
- **Blocks:** None (technical debt cleanup)
- **Related:** Story 8.8 (parent)

---

## Rollback Plan

If Option A (integration tests) causes issues:
1. Keep both unit and integration versions
2. Mark failing unit tests with `@pytest.mark.skip(reason="Complex async mocking - covered by integration tests")`
3. Document decision in story notes

If Option B (unit test fixes) proves too complex:
1. Revert to original unit test code
2. Switch to Option A approach
3. Document decision and time spent

---

## References

- Parent Story: `docs/stories/8-8-openapi-tool-upload-and-auto-generation.md`
- Test Infrastructure: `tests/conftest.py`
- Working Async Patterns: `tests/unit/test_mcp_tool_generator.py:184-308`
- Working Integration Patterns: `tests/integration/test_openapi_tool_workflow.py`
- pytest-asyncio Docs: https://pytest-asyncio.readthedocs.io/
- FastAPI Testing Docs: https://fastapi.tiangolo.com/tutorial/testing/

---

## Story Status

**Status:** Backlog
**Priority:** Medium (not blocking, but improves test coverage confidence)
**Assigned To:** TBD
**Target Sprint:** Next available capacity
**Estimated Effort:** 30 min (Option A) or 90 min (Option B)
