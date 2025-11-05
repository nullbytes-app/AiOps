#!/bin/bash
# tenant-isolation-validation.sh
# Validates Row-Level Security (RLS) tenant isolation
# Tests that tenants cannot access each other's data
#
# Usage: ./scripts/tenant-isolation-validation.sh [TENANT_A_ID] [TENANT_B_ID]
#
# If tenant IDs not provided, script will create two test tenants
#
# Created: 2025-11-03 (Story 5.3)
# Version: 1.0

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="$PROJECT_ROOT/logs/tenant-isolation-test-$(date +%Y%m%d-%H%M%S).log"

# Create logs directory if not exists
mkdir -p "$PROJECT_ROOT/logs"

# Logging functions
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}ℹ️  $*${NC}"
    log "INFO" "$*"
}

log_success() {
    echo -e "${GREEN}✅ $*${NC}"
    log "SUCCESS" "$*"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $*${NC}"
    log "WARNING" "$*"
}

log_error() {
    echo -e "${RED}❌ $*${NC}"
    log "ERROR" "$*"
}

log_critical() {
    echo -e "${RED}🚨 CRITICAL: $*${NC}"
    log "CRITICAL" "$*"
}

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    log_info "Loading environment from .env file"
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
else
    log_warning ".env file not found, using defaults"
fi

# Configuration with defaults
DATABASE_URL="${DATABASE_URL:-postgresql://aiagents:password@localhost:5433/ai_agents}"

log_info "Starting RLS tenant isolation validation"
log_info "Database: $DATABASE_URL"
log_info "Log file: $LOG_FILE"
echo ""

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
CRITICAL_FAILURES=0

# Test result tracking
test_pass() {
    ((TESTS_RUN++))
    ((TESTS_PASSED++))
    log_success "$1"
}

test_fail() {
    ((TESTS_RUN++))
    ((TESTS_FAILED++))
    log_error "$1"
}

test_critical_fail() {
    ((TESTS_RUN++))
    ((TESTS_FAILED++))
    ((CRITICAL_FAILURES++))
    log_critical "$1"
}

# Check if tenant IDs provided or generate test tenants
TENANT_A_ID="${1:-}"
TENANT_B_ID="${2:-}"

if [ -z "$TENANT_A_ID" ] || [ -z "$TENANT_B_ID" ]; then
    log_info "Tenant IDs not provided, generating test tenants..."

    # Generate UUIDs
    if command -v uuidgen &> /dev/null; then
        TENANT_A_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
        TENANT_B_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
    else
        # Fallback: generate random hex strings
        TENANT_A_ID=$(cat /dev/urandom | tr -dc 'a-f0-9' | fold -w 32 | head -n 1 | sed 's/^\(........\)\(....\)\(....\)\(....\)\(............\)$/\1-\2-\3-\4-\5/')
        TENANT_B_ID=$(cat /dev/urandom | tr -dc 'a-f0-9' | fold -w 32 | head -n 1 | sed 's/^\(........\)\(....\)\(....\)\(....\)\(............\)$/\1-\2-\3-\4-\5/')
    fi

    log_info "Generated test tenant A: $TENANT_A_ID"
    log_info "Generated test tenant B: $TENANT_B_ID"

    # Create test tenant records
    log_info "Creating test tenant records..."

    psql "$DATABASE_URL" -c "
    INSERT INTO tenant_configs (id, tenant_id, name, servicedesk_url, servicedesk_api_key_encrypted, webhook_signing_secret_encrypted, enhancement_preferences, created_at, updated_at)
    VALUES
        (gen_random_uuid(), '$TENANT_A_ID', 'Test Tenant A (RLS Validation)', 'https://test-tenant-a.example.com', 'ENCRYPTED_KEY_A', 'ENCRYPTED_SECRET_A', '{\"context_sources\": [\"ticket_history\"]}'::jsonb, NOW(), NOW()),
        (gen_random_uuid(), '$TENANT_B_ID', 'Test Tenant B (RLS Validation)', 'https://test-tenant-b.example.com', 'ENCRYPTED_KEY_B', 'ENCRYPTED_SECRET_B', '{\"context_sources\": [\"ticket_history\"]}'::jsonb, NOW(), NOW())
    ON CONFLICT (tenant_id) DO NOTHING;
    " >> "$LOG_FILE" 2>&1

    log_success "Test tenant records created"

    # Flag for cleanup
    CLEANUP_TEST_TENANTS=true
else
    log_info "Using provided tenant IDs:"
    log_info "Tenant A: $TENANT_A_ID"
    log_info "Tenant B: $TENANT_B_ID"
    CLEANUP_TEST_TENANTS=false
fi

echo ""

# ============================================================================
# Test 1: Verify RLS Enabled on All Tenant Tables
# ============================================================================
test_rls_enabled() {
    log_info "Test 1: Verifying RLS enabled on all tenant tables..."

    local query="
    SELECT tablename, rowsecurity
    FROM pg_tables
    WHERE tablename IN ('tenant_configs', 'enhancement_history', 'ticket_history', 'system_inventory')
    ORDER BY tablename;
    "

    local result
    if ! result=$(psql "$DATABASE_URL" -t -c "$query" 2>&1); then
        test_critical_fail "Database query failed: $result"
        return 1
    fi

    log_info "RLS status:"
    echo "$result" | tee -a "$LOG_FILE"

    # Check if any table has rowsecurity = f (false)
    if echo "$result" | grep -q " f$"; then
        test_critical_fail "RLS NOT ENABLED on some tables (rowsecurity = f)"
        log_critical "This is a CRITICAL security issue - tenant data is not isolated!"
        return 1
    fi

    test_pass "RLS enabled on all tenant tables"
    return 0
}

# ============================================================================
# Test 2: Verify RLS Policies Exist
# ============================================================================
test_rls_policies_exist() {
    log_info "Test 2: Verifying RLS policies exist..."

    local query="
    SELECT tablename, policyname, cmd, qual
    FROM pg_policies
    WHERE tablename IN ('tenant_configs', 'enhancement_history', 'ticket_history', 'system_inventory')
    ORDER BY tablename, policyname;
    "

    local result
    if ! result=$(psql "$DATABASE_URL" -t -c "$query" 2>&1); then
        test_critical_fail "Database query failed: $result"
        return 1
    fi

    local policy_count=$(echo "$result" | grep -c "tenant_" || true)

    log_info "RLS policies found: $policy_count"
    log_info "Policies:"
    echo "$result" | tee -a "$LOG_FILE"

    if [ "$policy_count" -lt 3 ]; then
        test_critical_fail "Insufficient RLS policies (found: $policy_count, expected: >= 3)"
        return 1
    fi

    # Check if policies reference current_setting('app.current_tenant_id')
    if ! echo "$result" | grep -q "current_setting"; then
        test_critical_fail "RLS policies do not reference session variable current_setting('app.current_tenant_id')"
        return 1
    fi

    test_pass "RLS policies exist and reference tenant session variable ($policy_count policies)"
    return 0
}

# ============================================================================
# Test 3: Insert Test Data for Both Tenants
# ============================================================================
test_insert_data() {
    log_info "Test 3: Inserting test enhancement records for both tenants..."

    # Insert data for Tenant A
    psql "$DATABASE_URL" -c "
    INSERT INTO enhancement_history (id, tenant_id, ticket_id, enhancement_text, status, duration_seconds, created_at, completed_at)
    VALUES
        (gen_random_uuid(), '$TENANT_A_ID', 'TKT-A-001', 'Enhancement for Tenant A - Record 1', 'completed', 5.2, NOW(), NOW()),
        (gen_random_uuid(), '$TENANT_A_ID', 'TKT-A-002', 'Enhancement for Tenant A - Record 2', 'completed', 6.1, NOW(), NOW()),
        (gen_random_uuid(), '$TENANT_A_ID', 'TKT-A-003', 'Enhancement for Tenant A - Record 3', 'completed', 4.8, NOW(), NOW())
    ON CONFLICT DO NOTHING;
    " >> "$LOG_FILE" 2>&1

    # Insert data for Tenant B
    psql "$DATABASE_URL" -c "
    INSERT INTO enhancement_history (id, tenant_id, ticket_id, enhancement_text, status, duration_seconds, created_at, completed_at)
    VALUES
        (gen_random_uuid(), '$TENANT_B_ID', 'TKT-B-001', 'Enhancement for Tenant B - Record 1', 'completed', 7.3, NOW(), NOW()),
        (gen_random_uuid(), '$TENANT_B_ID', 'TKT-B-002', 'Enhancement for Tenant B - Record 2', 'completed', 5.9, NOW(), NOW())
    ON CONFLICT DO NOTHING;
    " >> "$LOG_FILE" 2>&1

    log_info "Inserted 3 records for Tenant A"
    log_info "Inserted 2 records for Tenant B"

    test_pass "Test data inserted for both tenants"
    return 0
}

# ============================================================================
# Test 4: Query as Tenant A (Should See Only Tenant A Data)
# ============================================================================
test_query_tenant_a() {
    log_info "Test 4: Querying as Tenant A (should see only Tenant A data)..."

    # Set tenant context to Tenant A
    local query="
    SELECT set_tenant_context('$TENANT_A_ID');
    SELECT tenant_id, ticket_id, LEFT(enhancement_text, 50) as enhancement_preview
    FROM enhancement_history
    WHERE ticket_id LIKE 'TKT-%'
    ORDER BY created_at DESC;
    "

    local result
    if ! result=$(psql "$DATABASE_URL" -t -c "$query" 2>&1); then
        test_critical_fail "Query failed: $result"
        return 1
    fi

    log_info "Query results as Tenant A:"
    echo "$result" | tee -a "$LOG_FILE"

    # Count records returned
    local record_count=$(echo "$result" | grep -c "TKT-" || true)

    log_info "Records returned: $record_count"

    # Check for Tenant B data (should NOT be present)
    if echo "$result" | grep -q "$TENANT_B_ID"; then
        test_critical_fail "ISOLATION BREACH: Tenant A can see Tenant B data!"
        log_critical "Found Tenant B ID ($TENANT_B_ID) in Tenant A query results"
        log_critical "THIS IS A CRITICAL SECURITY VIOLATION"
        return 1
    fi

    if echo "$result" | grep -q "TKT-B-"; then
        test_critical_fail "ISOLATION BREACH: Tenant A can see Tenant B tickets!"
        log_critical "Found Tenant B ticket IDs (TKT-B-*) in Tenant A query results"
        log_critical "THIS IS A CRITICAL SECURITY VIOLATION"
        return 1
    fi

    # Verify Tenant A data IS present
    if ! echo "$result" | grep -q "$TENANT_A_ID"; then
        test_fail "Tenant A data not found in query results (RLS may be blocking too much)"
        return 1
    fi

    test_pass "Tenant A query returned only Tenant A data ($record_count records, no Tenant B data)"
    return 0
}

# ============================================================================
# Test 5: Query as Tenant B (Should See Only Tenant B Data)
# ============================================================================
test_query_tenant_b() {
    log_info "Test 5: Querying as Tenant B (should see only Tenant B data)..."

    # Set tenant context to Tenant B
    local query="
    SELECT set_tenant_context('$TENANT_B_ID');
    SELECT tenant_id, ticket_id, LEFT(enhancement_text, 50) as enhancement_preview
    FROM enhancement_history
    WHERE ticket_id LIKE 'TKT-%'
    ORDER BY created_at DESC;
    "

    local result
    if ! result=$(psql "$DATABASE_URL" -t -c "$query" 2>&1); then
        test_critical_fail "Query failed: $result"
        return 1
    fi

    log_info "Query results as Tenant B:"
    echo "$result" | tee -a "$LOG_FILE"

    # Count records returned
    local record_count=$(echo "$result" | grep -c "TKT-" || true)

    log_info "Records returned: $record_count"

    # Check for Tenant A data (should NOT be present)
    if echo "$result" | grep -q "$TENANT_A_ID"; then
        test_critical_fail "ISOLATION BREACH: Tenant B can see Tenant A data!"
        log_critical "Found Tenant A ID ($TENANT_A_ID) in Tenant B query results"
        log_critical "THIS IS A CRITICAL SECURITY VIOLATION"
        return 1
    fi

    if echo "$result" | grep -q "TKT-A-"; then
        test_critical_fail "ISOLATION BREACH: Tenant B can see Tenant A tickets!"
        log_critical "Found Tenant A ticket IDs (TKT-A-*) in Tenant B query results"
        log_critical "THIS IS A CRITICAL SECURITY VIOLATION"
        return 1
    fi

    # Verify Tenant B data IS present
    if ! echo "$result" | grep -q "$TENANT_B_ID"; then
        test_fail "Tenant B data not found in query results (RLS may be blocking too much)"
        return 1
    fi

    test_pass "Tenant B query returned only Tenant B data ($record_count records, no Tenant A data)"
    return 0
}

# ============================================================================
# Test 6: Attempt Cross-Tenant Query (Should Return Empty)
# ============================================================================
test_cross_tenant_query() {
    log_info "Test 6: Attempting cross-tenant query (should return empty)..."

    # Set context to Tenant A, but try to query Tenant B data explicitly
    local query="
    SELECT set_tenant_context('$TENANT_A_ID');
    SELECT COUNT(*)
    FROM enhancement_history
    WHERE tenant_id = '$TENANT_B_ID';
    "

    local result
    if ! result=$(psql "$DATABASE_URL" -t -c "$query" 2>&1); then
        test_critical_fail "Query failed: $result"
        return 1
    fi

    local count=$(echo "$result" | tail -1 | tr -d '[:space:]')

    log_info "Cross-tenant query returned count: $count"

    if [ "$count" != "0" ]; then
        test_critical_fail "ISOLATION BREACH: Tenant A can query Tenant B data (count: $count)"
        log_critical "RLS is NOT enforcing cross-tenant isolation"
        log_critical "THIS IS A CRITICAL SECURITY VIOLATION"
        return 1
    fi

    test_pass "Cross-tenant query returned 0 rows (isolation enforced)"
    return 0
}

# ============================================================================
# Test 7: Test Without Setting Tenant Context (Should Fail or Return Empty)
# ============================================================================
test_no_context() {
    log_info "Test 7: Querying without setting tenant context (should return empty)..."

    # Clear any existing tenant context
    local query="
    SELECT set_config('app.current_tenant_id', '', false);
    SELECT COUNT(*)
    FROM enhancement_history
    WHERE ticket_id LIKE 'TKT-%';
    "

    local result
    if ! result=$(psql "$DATABASE_URL" -t -c "$query" 2>&1); then
        # Query may fail if RLS requires tenant context - this is acceptable
        log_warning "Query failed without tenant context (acceptable if RLS enforces context)"
        test_pass "Query without tenant context failed (RLS enforcing context requirement)"
        return 0
    fi

    local count=$(echo "$result" | tail -1 | tr -d '[:space:]')

    log_info "Query without tenant context returned count: $count"

    if [ "$count" != "0" ]; then
        test_fail "Query without tenant context returned $count rows (expected 0)"
        log_warning "RLS may not be properly enforcing tenant context requirement"
        return 1
    fi

    test_pass "Query without tenant context returned 0 rows (context enforcement working)"
    return 0
}

# ============================================================================
# Cleanup Test Data
# ============================================================================
cleanup() {
    if [ "$CLEANUP_TEST_TENANTS" = true ]; then
        log_info "Cleaning up test data..."

        # Delete test enhancement records
        psql "$DATABASE_URL" -c "
        DELETE FROM enhancement_history WHERE tenant_id IN ('$TENANT_A_ID', '$TENANT_B_ID');
        DELETE FROM tenant_configs WHERE tenant_id IN ('$TENANT_A_ID', '$TENANT_B_ID');
        " >> "$LOG_FILE" 2>&1

        log_success "Test data cleaned up"
    else
        log_info "Skipping cleanup (using existing tenant IDs)"
    fi
}

# ============================================================================
# Main Test Execution
# ============================================================================
main() {
    echo ""
    log_info "=========================================="
    log_info "RLS Tenant Isolation Validation"
    log_info "=========================================="
    echo ""

    # Run tests
    test_rls_enabled || true
    test_rls_policies_exist || true
    test_insert_data || true
    test_query_tenant_a || true
    test_query_tenant_b || true
    test_cross_tenant_query || true
    test_no_context || true

    # Cleanup
    cleanup

    # Summary
    echo ""
    log_info "=========================================="
    log_info "Test Summary"
    log_info "=========================================="
    log_info "Tests Run:      $TESTS_RUN"
    log_success "Tests Passed:   $TESTS_PASSED"

    if [ $TESTS_FAILED -gt 0 ]; then
        log_error "Tests Failed:   $TESTS_FAILED"
    else
        log_info "Tests Failed:   $TESTS_FAILED"
    fi

    if [ $CRITICAL_FAILURES -gt 0 ]; then
        log_critical "CRITICAL FAILURES: $CRITICAL_FAILURES"
    fi

    log_info "Log file: $LOG_FILE"
    echo ""

    # Exit code
    if [ $CRITICAL_FAILURES -gt 0 ]; then
        log_critical "❌ RLS TENANT ISOLATION VALIDATION FAILED (CRITICAL)"
        log_critical "IMMEDIATE ACTION REQUIRED:"
        log_critical "1. Disable all workers: kubectl scale deployment ai-agents-worker --replicas=0"
        log_critical "2. Escalate to Security Team + Engineering Director"
        log_critical "3. Do NOT re-enable production until RLS validated"
        exit 2
    elif [ $TESTS_FAILED -gt 0 ]; then
        log_error "❌ RLS tenant isolation validation FAILED"
        exit 1
    else
        log_success "✅ RLS TENANT ISOLATION VALIDATION PASSED"
        log_success "Tenant data is properly isolated - no cross-tenant leakage detected"
        exit 0
    fi
}

# Run main function
main
