# Story 8-8A: Test Fixture Polish & Formatting

Status: backlog

## Story

As a developer,
I want to fix the remaining test fixture configurations and apply code formatting,
so that all Story 8.8 tests pass 100% and code follows Black style guidelines.

## Acceptance Criteria

1. **All API test mocks configured correctly** - 8 failing API tests in `test_openapi_tools_api.py` pass with properly configured mocks returning correct data types (strings, dicts, not MagicMock objects)
2. **Black formatting applied** - All 6 implementation files pass `black --check` with no reformatting needed
3. **MyPy type warnings addressed** - 7 mypy import warnings resolved with `# type: ignore` comments or stub files
4. **Test pass rate 100%** - All 68 tests passing with no failures

## Tasks / Subtasks

- [ ] Task 1: Fix API Test Mock Configurations (AC#1) - 60 minutes
  - [ ] 1.1: Configure service mocks to return proper OpenAPITool objects with all attributes (created_by: str)
  - [ ] 1.2: Configure test_openapi_connection mocks to return dict: `{"success": bool, "status_code": int, "response_preview": str, "error_message": str}`
  - [ ] 1.3: Configure detect_common_issues mocks to return list[dict]
  - [ ] 1.4: Run tests and verify all 8 previously failing tests now pass

- [ ] Task 2: Apply Black Formatting (AC#2) - 10 minutes
  - [ ] 2.1: Run `black src/admin/pages/07_Add_Tool.py src/services/openapi_parser_service.py src/services/mcp_tool_generator.py src/services/openapi_tool_service.py src/api/openapi_tools.py src/schemas/openapi_tool.py`
  - [ ] 2.2: Verify `black --check` passes for all 6 files

- [ ] Task 3: Address MyPy Type Warnings (AC#3) - 20 minutes
  - [ ] 3.1: Add `# type: ignore[import-untyped]` to internal module imports
  - [ ] 3.2: Address OpenAPI v3.0/v3.1 type incompatibility with union types
  - [ ] 3.3: Address Any return type warnings with explicit type casts
  - [ ] 3.4: Verify `mypy --strict` reports 0 errors or acceptable warnings

- [ ] Task 4: Verify Full Test Suite (AC#4) - 10 minutes
  - [ ] 4.1: Run full Story 8.8 test suite: `pytest tests/unit/test_openapi_parser_service.py tests/unit/test_mcp_tool_generator.py tests/integration/test_openapi_tool_workflow.py tests/unit/test_openapi_tools_api.py -v`
  - [ ] 4.2: Verify 68/68 tests passing (100% pass rate)
  - [ ] 4.3: Update Story 8.8 completion notes with final test results

## Dev Notes

**Context:**
This is a follow-up ticket from Story 8.8 Code Review #3 (2025-11-06). Story 8.8 was APPROVED for production deployment with all 8 ACs implemented and 60/68 tests passing. This ticket addresses the remaining 8 failing tests (test infrastructure polish) and code formatting.

**Parent Story:** Story 8.8 - OpenAPI Tool Upload and Auto-Generation

**Code Review Finding:**
- All functionality is production-ready and working
- 8 API test failures are purely mock configuration issues (not functional bugs)
- Integration tests (10/10 passing) prove end-to-end workflow works
- This is cosmetic polish work, not critical path

**Estimated Effort:** ~90 minutes total

**Priority:** Low (non-blocking, post-deployment cleanup)

## Change Log

- **2025-11-06**: Story created by Amelia (code-review workflow follow-up)
  - Extracted from Story 8.8 Code Review #3 action items
  - 8 API test mock configuration issues identified
  - Black formatting needed for 6 files
  - MyPy type warnings (7 import-related errors)
  - Estimated effort: 90 minutes total
  - Priority: Low (Story 8.8 already approved for production)
