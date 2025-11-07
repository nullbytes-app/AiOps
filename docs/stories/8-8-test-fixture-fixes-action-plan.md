# Story 8.8 - Test Fixture Fixes Action Plan

**Date:** 2025-11-06
**Status:** CHANGES REQUESTED → Ready for fixes
**Estimated Total Effort:** 75 minutes
**Target:** 68/68 tests passing (100% pass rate)

---

## Current Status

- ✅ **Implementation:** 100% complete (all 8 ACs)
- ✅ **Test Coverage:** 136% (68/50 tests)
- ⚠️ **Test Pass Rate:** 75% (51/68 passing)
- 🎯 **Goal:** Fix 17 failing tests (all fixture/mocking issues)

---

## Action Items (Prioritized)

### 1. Fix Async Mocking for Connection Tests [MEDIUM]

**File:** `src/services/mcp_tool_generator.py`
**Function:** `test_openapi_connection` (lines 184-308)
**Estimated Effort:** 30 minutes
**Tests Affected:** 5 tests

**Problem:**
Function returns `None` in some error paths instead of consistent dict structure.

**Failing Tests:**
- `test_mcp_tool_generator.py::TestOpenAPIConnection::test_connection_timeout_error`
- `test_mcp_tool_generator.py::TestOpenAPIConnection::test_connection_401_unauthorized_error`
- `test_mcp_tool_generator.py::TestOpenAPIConnection::test_connection_404_not_found_error`
- `test_mcp_tool_generator.py::TestOpenAPIConnection::test_connection_500_server_error`
- `test_mcp_tool_generator.py::TestOpenAPIConnection::test_connection_connect_error`

**Error:**
```
TypeError: 'NoneType' object is not subscriptable
assert result["success"] is False
```

**Fix Required:**
Ensure `test_openapi_connection` ALWAYS returns dict with structure:
```python
{
    "success": bool,
    "error_message": str,
    "error_type": str,
    "status_code": int,  # optional
    "response_preview": str  # optional
}
```

**Implementation Steps:**
1. Open `src/services/mcp_tool_generator.py`
2. Locate `test_openapi_connection` function (around line 184)
3. Add default error dict return for all exception paths
4. Ensure all return statements include dict structure
5. Run tests: `pytest tests/unit/test_mcp_tool_generator.py::TestOpenAPIConnection -v`
6. Verify 5 tests pass

**Code Pattern to Use:**
```python
async def test_openapi_connection(...) -> dict:
    """Test connection to OpenAPI endpoint."""
    try:
        # existing logic
        return {
            "success": True,
            "status_code": response.status_code,
            "response_preview": ...
        }
    except httpx.TimeoutException as e:
        return {
            "success": False,
            "error_message": f"Connection timeout: {str(e)}",
            "error_type": "TimeoutException"
        }
    except httpx.ConnectError as e:
        return {
            "success": False,
            "error_message": f"Connection failed: {str(e)}",
            "error_type": "ConnectError"
        }
    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "error_message": f"HTTP error: {e.response.status_code}",
            "error_type": "HTTPStatusError",
            "status_code": e.response.status_code
        }
    except Exception as e:
        return {
            "success": False,
            "error_message": f"Unexpected error: {str(e)}",
            "error_type": type(e).__name__
        }
```

---

### 2. Fix Encryption Test Fixtures [MEDIUM]

**Files:** `tests/integration/test_openapi_tool_workflow.py`, `tests/conftest.py`
**Estimated Effort:** 15 minutes
**Tests Affected:** 2 tests

**Problem:**
Encryption key mismatch between test fixtures and service layer.

**Failing Tests:**
- `test_openapi_tool_workflow.py::TestDatabaseEncryption::test_encrypt_decrypt_auth_config_roundtrip`
- `test_openapi_tool_workflow.py::TestDatabaseEncryption::test_encrypt_auth_config_produces_different_ciphertexts`

**Error:**
```
cryptography.fernet.InvalidToken
```

**Fix Required:**
Ensure test fixtures use same `TENANT_ENCRYPTION_KEY` as `openapi_tool_service.py`

**Implementation Steps:**
1. Open `tests/integration/test_openapi_tool_workflow.py`
2. Add monkeypatch for `TENANT_ENCRYPTION_KEY` in test setup
3. Ensure consistent key across all encryption tests
4. Run tests: `pytest tests/integration/test_openapi_tool_workflow.py::TestDatabaseEncryption -v`
5. Verify 2 tests pass

**Code Pattern to Use:**
```python
import pytest
from cryptography.fernet import Fernet

@pytest.fixture
def encryption_key(monkeypatch):
    """Provide consistent encryption key for tests."""
    # Generate a test key or use a fixed one
    test_key = Fernet.generate_key()
    monkeypatch.setenv("TENANT_ENCRYPTION_KEY", test_key.decode())
    return test_key

def test_encrypt_decrypt_auth_config_roundtrip(encryption_key):
    """Test encryption/decryption roundtrip."""
    # Use encryption_key fixture
    auth_config = {"type": "api_key", "value": "test-key"}
    encrypted = encrypt_auth_config(auth_config)
    decrypted = decrypt_auth_config(encrypted)
    assert decrypted == auth_config
```

---

### 3. Fix Tenant ID Schema Consistency [MEDIUM]

**File:** `tests/unit/test_openapi_tools_api.py`
**Estimated Effort:** 20 minutes
**Tests Affected:** 8 tests

**Problem:**
Tests passing `tenant_id` as integer, but API expects string.

**Failing Tests:**
- `test_openapi_tools_api.py::TestCreateToolEndpoint::test_create_tool_success`
- `test_openapi_tools_api.py::TestCreateToolEndpoint::test_create_tool_invalid_spec_returns_400`
- `test_openapi_tools_api.py::TestCreateToolEndpoint::test_create_tool_missing_required_fields_returns_422`
- `test_openapi_tools_api.py::TestTestConnectionEndpoint::test_connection_invalid_spec_returns_400`
- `test_openapi_tools_api.py::TestListToolsEndpoint::test_list_tools_for_tenant`
- `test_openapi_tools_api.py::TestListToolsEndpoint::test_list_tools_with_status_filter`
- `test_openapi_tools_api.py::TestGetToolEndpoint::test_get_tool_by_id_success`
- `test_openapi_tools_api.py::TestGetToolEndpoint::test_get_tool_not_found_returns_404`

**Error:**
```
400 Bad Request: "Invalid tenant_id format. Must be non-empty string."
```

**Fix Options:**

**Option A: Update Test Payloads (Recommended - 20 min)**
- Update all test payloads to use `tenant_id="1"` instead of `tenant_id=1`
- Faster fix, maintains string schema consistency

**Option B: Update Schema (Alternative - 30 min)**
- Update `OpenAPIToolCreate` schema to accept int and convert to string
- More flexible but requires schema change and migration consideration

**Implementation Steps (Option A):**
1. Open `tests/unit/test_openapi_tools_api.py`
2. Find all occurrences of `tenant_id=1` (should be ~8 locations)
3. Replace with `tenant_id="1"` (string format)
4. Run tests: `pytest tests/unit/test_openapi_tools_api.py -v`
5. Verify 8 tests pass

**Search and Replace Pattern:**
```bash
# Find: tenant_id=1
# Replace: tenant_id="1"

# Or use sed:
sed -i '' 's/tenant_id=1/tenant_id="1"/g' tests/unit/test_openapi_tools_api.py
```

---

### 4. Define Missing Test Fixture [MEDIUM]

**Files:** `tests/conftest.py` or `tests/unit/test_mcp_tool_generator.py`
**Estimated Effort:** 10 minutes
**Tests Affected:** 1 test

**Problem:**
Test function expects `openapi_spec` fixture but it's not defined.

**Failing Test:**
- `test_mcp_tool_generator.py::test_openapi_connection` (ERROR)

**Error:**
```
fixture 'openapi_spec' not found
available fixtures: ..., sample_openapi_spec, ...
```

**Fix Options:**

**Option A: Use Existing Fixture (Recommended - 5 min)**
- Replace `openapi_spec` with `sample_openapi_spec` in function signature

**Option B: Define New Fixture (Alternative - 10 min)**
- Add `openapi_spec` fixture to `conftest.py`

**Implementation Steps (Option A):**
1. Open `tests/unit/test_mcp_tool_generator.py`
2. Find `test_openapi_connection` function signature
3. Replace `openapi_spec` parameter with `sample_openapi_spec`
4. Run test: `pytest tests/unit/test_mcp_tool_generator.py::test_openapi_connection -v`
5. Verify test runs (may still fail for other reasons, but fixture error resolved)

---

### 5. Remove Async Marker from Sync Test [LOW]

**File:** `tests/unit/test_openapi_parser_service.py`
**Estimated Effort:** 2 minutes
**Tests Affected:** 1 test (warning only)

**Problem:**
Sync test incorrectly marked with `@pytest.mark.asyncio`.

**Warning:**
```
test_openapi_parser_service.py:86: PytestWarning: The test is marked with '@pytest.mark.asyncio' but it is not an async function.
```

**Fix Required:**
Remove `@pytest.mark.asyncio` decorator from `test_format_validation_errors`.

**Implementation Steps:**
1. Open `tests/unit/test_openapi_parser_service.py`
2. Go to line 86
3. Remove `@pytest.mark.asyncio` decorator
4. Run test: `pytest tests/unit/test_openapi_parser_service.py::TestErrorFormatting::test_format_validation_errors -v`
5. Verify warning is gone

---

## Execution Order

**Recommended sequence for maximum efficiency:**

1. **Start with #5 (2 min)** - Quick win, removes warning
2. **Then #4 (10 min)** - Quick fix, resolves fixture error
3. **Then #3 (20 min)** - Medium effort, fixes 8 tests
4. **Then #2 (15 min)** - Medium effort, fixes 2 tests
5. **Finally #1 (30 min)** - Largest effort, fixes 5 tests

**Total Sequential Time:** ~77 minutes

---

## Verification Steps

After each fix:
```bash
# Run specific test file
pytest tests/unit/test_openapi_parser_service.py -v
pytest tests/unit/test_mcp_tool_generator.py -v
pytest tests/integration/test_openapi_tool_workflow.py -v
pytest tests/unit/test_openapi_tools_api.py -v

# Run all Story 8.8 tests
pytest tests/unit/test_openapi_parser_service.py \
       tests/unit/test_mcp_tool_generator.py \
       tests/integration/test_openapi_tool_workflow.py \
       tests/unit/test_openapi_tools_api.py -v

# Target output
# ===== 68 passed in X.XXs =====
```

---

## Success Criteria

✅ **All 68 tests passing** (100% pass rate)
✅ **No pytest warnings**
✅ **No fixture errors**
✅ **Consistent return types in async functions**
✅ **Encryption roundtrip working**
✅ **API tests using correct schema types**

---

## Post-Fix Checklist

- [ ] Fix #5 - Remove async marker (2 min)
- [ ] Fix #4 - Define missing fixture (10 min)
- [ ] Fix #3 - Tenant ID schema (20 min)
- [ ] Fix #2 - Encryption fixtures (15 min)
- [ ] Fix #1 - Async mocking (30 min)
- [ ] Run full test suite
- [ ] Verify 68/68 tests passing
- [ ] Update story status to "review"
- [ ] Request re-review

---

## Optional: Database Migration

**File:** `alembic/versions/d286ce33df93_add_openapi_tools_table.py`
**Estimated Effort:** 10 minutes
**Status:** OPTIONAL (can defer to deployment)

**Steps:**
```bash
# Ensure database is running
docker-compose up -d postgres

# Apply migration
alembic upgrade head

# Verify
alembic current
# Should show: d286ce33df93 (head)

# Verify table exists
psql -U aiagents -d ai_agents -c "\d openapi_tools"
```

---

**Ready to start fixing? Let me know which issue you want to tackle first, or I can help with all of them!**
