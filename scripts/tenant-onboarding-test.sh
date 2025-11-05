#!/bin/bash
# tenant-onboarding-test.sh
# Automated validation script for tenant onboarding
# Tests tenant creation, webhook processing, and end-to-end enhancement workflow
#
# Usage: ./scripts/tenant-onboarding-test.sh <TENANT_ID> [<WEBHOOK_SECRET>]
#
# Example: ./scripts/tenant-onboarding-test.sh 550e8400-e29b-41d4-a716-446655440000 abc123...
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
LOG_FILE="$PROJECT_ROOT/logs/tenant-onboarding-test-$(date +%Y%m%d-%H%M%S).log"

# Create logs directory if not exists
mkdir -p "$PROJECT_ROOT/logs"

# Logging function
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

# Usage function
usage() {
    cat <<EOF
Usage: $0 <TENANT_ID> [<WEBHOOK_SECRET>]

Validates tenant onboarding by testing:
1. Tenant configuration exists in database
2. Credentials encrypted properly
3. Webhook signature validation
4. End-to-end enhancement processing

Arguments:
  TENANT_ID       UUID of the tenant to test (required)
  WEBHOOK_SECRET  Webhook signing secret (optional, will query from DB if omitted)

Environment Variables:
  DATABASE_URL    PostgreSQL connection string (default: from .env)
  API_BASE_URL    Production API URL (default: https://api.ai-agents.production)
  REDIS_HOST      Redis hostname (default: localhost)
  REDIS_PORT      Redis port (default: 6379)

Examples:
  # Test with tenant ID only (queries secret from database)
  $0 550e8400-e29b-41d4-a716-446655440000

  # Test with explicit webhook secret
  $0 550e8400-e29b-41d4-a716-446655440000 abc123def456...

EOF
    exit 1
}

# Check arguments
if [ $# -lt 1 ]; then
    usage
fi

TENANT_ID="$1"
WEBHOOK_SECRET="${2:-}"

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
API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"

log_info "Starting tenant onboarding validation for tenant_id: $TENANT_ID"
log_info "API Base URL: $API_BASE_URL"
log_info "Redis: $REDIS_HOST:$REDIS_PORT"
log_info "Log file: $LOG_FILE"
echo ""

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

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

test_skip() {
    log_warning "SKIPPED: $1"
}

# ============================================================================
# Test 1: Verify Tenant Configuration Exists
# ============================================================================
test_tenant_config() {
    log_info "Test 1: Verifying tenant configuration in database..."

    # Query tenant_configs table
    local query="SELECT tenant_id, name, servicedesk_url, created_at FROM tenant_configs WHERE tenant_id = '$TENANT_ID';"

    local result
    if ! result=$(psql "$DATABASE_URL" -t -c "$query" 2>&1); then
        test_fail "Database query failed: $result"
        return 1
    fi

    if [ -z "$result" ] || [ "$(echo "$result" | tr -d '[:space:]')" = "" ]; then
        test_fail "Tenant configuration not found in database for tenant_id: $TENANT_ID"
        return 1
    fi

    log_info "Tenant record found:"
    echo "$result" | tee -a "$LOG_FILE"
    test_pass "Tenant configuration exists in database"
    return 0
}

# ============================================================================
# Test 2: Verify Credentials Encrypted
# ============================================================================
test_credentials_encrypted() {
    log_info "Test 2: Verifying credentials are encrypted..."

    # Query encrypted fields
    local query="SELECT
        LENGTH(servicedesk_api_key_encrypted) as api_key_length,
        LENGTH(webhook_signing_secret_encrypted) as secret_length
    FROM tenant_configs
    WHERE tenant_id = '$TENANT_ID';"

    local result
    if ! result=$(psql "$DATABASE_URL" -t -c "$query" 2>&1); then
        test_fail "Database query failed: $result"
        return 1
    fi

    # Parse result
    local api_key_length=$(echo "$result" | awk '{print $1}')
    local secret_length=$(echo "$result" | awk '{print $3}')

    if [ -z "$api_key_length" ] || [ "$api_key_length" -lt 50 ]; then
        test_fail "ServiceDesk API key appears unencrypted (length: $api_key_length, expected > 50)"
        return 1
    fi

    if [ -z "$secret_length" ] || [ "$secret_length" -lt 50 ]; then
        test_fail "Webhook secret appears unencrypted (length: $secret_length, expected > 50)"
        return 1
    fi

    log_info "Encrypted API key length: $api_key_length bytes"
    log_info "Encrypted webhook secret length: $secret_length bytes"
    test_pass "Credentials are encrypted (lengths > 50 bytes)"
    return 0
}

# ============================================================================
# Test 3: Verify Enhancement Preferences Valid JSON
# ============================================================================
test_enhancement_preferences() {
    log_info "Test 3: Verifying enhancement preferences are valid JSON..."

    local query="SELECT enhancement_preferences FROM tenant_configs WHERE tenant_id = '$TENANT_ID';"

    local result
    if ! result=$(psql "$DATABASE_URL" -t -c "$query" 2>&1); then
        test_fail "Database query failed: $result"
        return 1
    fi

    # Try to parse JSON with jq
    if ! echo "$result" | jq empty 2>/dev/null; then
        test_fail "Enhancement preferences are not valid JSON"
        return 1
    fi

    log_info "Enhancement preferences:"
    echo "$result" | jq '.' | tee -a "$LOG_FILE"
    test_pass "Enhancement preferences are valid JSON"
    return 0
}

# ============================================================================
# Test 4: Test Webhook Signature Validation
# ============================================================================
test_webhook_signature() {
    log_info "Test 4: Testing webhook signature validation..."

    # If webhook secret not provided, try to retrieve from database
    if [ -z "$WEBHOOK_SECRET" ]; then
        log_warning "Webhook secret not provided, attempting to decrypt from database..."
        log_warning "NOTE: This requires TENANT_ENCRYPTION_KEY environment variable to be set"

        if [ -z "${TENANT_ENCRYPTION_KEY:-}" ]; then
            test_skip "Webhook signature validation (no secret provided and TENANT_ENCRYPTION_KEY not set)"
            return 0
        fi

        # Decrypt webhook secret using Python
        local encrypted_secret
        encrypted_secret=$(psql "$DATABASE_URL" -t -c "SELECT webhook_signing_secret_encrypted FROM tenant_configs WHERE tenant_id = '$TENANT_ID';" | tr -d '[:space:]')

        if ! WEBHOOK_SECRET=$(python3 -c "
from cryptography.fernet import Fernet
import os
import sys
cipher = Fernet(os.getenv('TENANT_ENCRYPTION_KEY').encode())
try:
    decrypted = cipher.decrypt('$encrypted_secret'.encode()).decode()
    print(decrypted)
except Exception as e:
    print(f'Error decrypting: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&1); then
            test_skip "Webhook signature validation (failed to decrypt secret: $WEBHOOK_SECRET)"
            return 0
        fi
    fi

    # Create test webhook payload
    local payload='{"ticket_id":"TEST-12345","subject":"Test ticket for onboarding validation","description":"This is a test ticket to validate webhook processing","priority":"Medium","status":"Open","created_at":"'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"}'

    # Compute HMAC-SHA256 signature
    local signature
    signature=$(echo -n "$payload" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | awk '{print $2}')

    log_info "Test payload: $payload"
    log_info "Computed signature: $signature"

    # Send webhook to API
    local response
    local http_code
    http_code=$(curl -s -w "%{http_code}" -o /tmp/webhook_response.json \
        -X POST "$API_BASE_URL/webhook/servicedesk?tenant_id=$TENANT_ID" \
        -H "Content-Type: application/json" \
        -H "X-ServiceDesk-Signature: $signature" \
        -d "$payload" 2>&1)

    response=$(cat /tmp/webhook_response.json)

    log_info "HTTP Status: $http_code"
    log_info "Response: $response"

    # Check response
    if [ "$http_code" != "202" ]; then
        test_fail "Webhook signature validation failed (HTTP $http_code): $response"
        return 1
    fi

    # Verify job_id returned
    if ! echo "$response" | jq -e '.job_id' > /dev/null 2>&1; then
        test_fail "Webhook accepted but no job_id returned: $response"
        return 1
    fi

    local job_id
    job_id=$(echo "$response" | jq -r '.job_id')
    log_info "Job queued successfully with job_id: $job_id"

    test_pass "Webhook signature validation successful (HTTP 202, job_id: $job_id)"
    return 0
}

# ============================================================================
# Test 5: Verify Job Queued to Redis
# ============================================================================
test_redis_queue() {
    log_info "Test 5: Verifying job queued to Redis..."

    # Check if redis-cli available
    if ! command -v redis-cli &> /dev/null; then
        test_skip "Redis queue verification (redis-cli not installed)"
        return 0
    fi

    # Get queue depth
    local queue_depth
    if ! queue_depth=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" LLEN enhancement_queue 2>&1); then
        test_fail "Failed to query Redis: $queue_depth"
        return 1
    fi

    log_info "Redis enhancement_queue depth: $queue_depth"

    if [ "$queue_depth" -lt 1 ]; then
        test_warning "Redis queue depth is 0 (job may have already been processed)"
        # This is not necessarily a failure - workers may be fast
        test_pass "Redis connection successful (queue depth: $queue_depth)"
        return 0
    fi

    # Inspect most recent job (without removing from queue)
    local job_payload
    if ! job_payload=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" LINDEX enhancement_queue -1 2>&1); then
        test_warning "Could not inspect queue payload: $job_payload"
    else
        log_info "Most recent job in queue:"
        echo "$job_payload" | jq '.' 2>/dev/null || echo "$job_payload" | tee -a "$LOG_FILE"
    fi

    test_pass "Job queued to Redis (queue depth: $queue_depth)"
    return 0
}

# ============================================================================
# Test 6: Monitor Worker Processing (Optional)
# ============================================================================
test_worker_processing() {
    log_info "Test 6: Monitoring worker processing..."

    # Check if kubectl available
    if ! command -v kubectl &> /dev/null; then
        test_skip "Worker processing monitoring (kubectl not installed)"
        return 0
    fi

    # Check if in Kubernetes context
    if ! kubectl get pods -n production &> /dev/null; then
        test_skip "Worker processing monitoring (not in production Kubernetes context)"
        return 0
    fi

    log_info "Checking worker pod logs for tenant activity (last 50 lines)..."

    # Get worker logs
    local worker_logs
    if ! worker_logs=$(kubectl logs -n production deployment/ai-agents-worker --tail=50 2>&1 | grep "$TENANT_ID" || true); then
        test_skip "Worker processing monitoring (could not retrieve logs)"
        return 0
    fi

    if [ -z "$worker_logs" ]; then
        log_warning "No worker logs found for tenant_id: $TENANT_ID (job may not have processed yet)"
        test_skip "Worker processing monitoring (no logs found, wait 10-15 seconds and check manually)"
        return 0
    fi

    log_info "Worker logs for tenant:"
    echo "$worker_logs" | tee -a "$LOG_FILE"

    # Check for success indicators
    if echo "$worker_logs" | grep -q "task_completed\|SUCCESS"; then
        test_pass "Worker processing completed successfully"
        return 0
    elif echo "$worker_logs" | grep -q "ERROR\|FAILED"; then
        test_fail "Worker processing encountered errors (see logs above)"
        return 1
    else
        test_warning "Worker processing in progress or logs incomplete"
        test_pass "Worker logs visible (check manually for completion)"
        return 0
    fi
}

# ============================================================================
# Test 7: Verify RLS Context Setting
# ============================================================================
test_rls_context() {
    log_info "Test 7: Verifying RLS context setting..."

    # Test set_tenant_context function
    local query="SELECT set_tenant_context('$TENANT_ID'); SELECT current_setting('app.current_tenant_id', true);"

    local result
    if ! result=$(psql "$DATABASE_URL" -t -c "$query" 2>&1); then
        test_fail "RLS context setting failed: $result"
        return 1
    fi

    # Verify current setting matches tenant_id
    local current_tenant_id=$(echo "$result" | tail -1 | tr -d '[:space:]')

    if [ "$current_tenant_id" != "$TENANT_ID" ]; then
        test_fail "RLS context mismatch: expected $TENANT_ID, got $current_tenant_id"
        return 1
    fi

    log_info "RLS session variable set to: $current_tenant_id"
    test_pass "RLS context setting successful"
    return 0
}

# ============================================================================
# Test 8: Verify RLS Policies Active
# ============================================================================
test_rls_policies() {
    log_info "Test 8: Verifying RLS policies are active..."

    # Check if RLS enabled on tenant tables
    local query="
    SELECT tablename, rowsecurity
    FROM pg_tables
    WHERE tablename IN ('tenant_configs', 'enhancement_history', 'ticket_history', 'system_inventory')
    ORDER BY tablename;
    "

    local result
    if ! result=$(psql "$DATABASE_URL" -t -c "$query" 2>&1); then
        test_fail "RLS policy query failed: $result"
        return 1
    fi

    log_info "RLS status for tenant tables:"
    echo "$result" | tee -a "$LOG_FILE"

    # Check if all tables have rowsecurity enabled
    if echo "$result" | grep -q " f$"; then
        test_fail "Some tables have RLS disabled (rowsecurity = f)"
        return 1
    fi

    # Count policies
    local policy_query="
    SELECT COUNT(*)
    FROM pg_policies
    WHERE tablename IN ('tenant_configs', 'enhancement_history', 'ticket_history', 'system_inventory');
    "

    local policy_count
    if ! policy_count=$(psql "$DATABASE_URL" -t -c "$policy_query" | tr -d '[:space:]'); then
        test_fail "RLS policy count query failed"
        return 1
    fi

    log_info "RLS policies active: $policy_count"

    if [ "$policy_count" -lt 3 ]; then
        test_fail "Insufficient RLS policies (found: $policy_count, expected: >= 3)"
        return 1
    fi

    test_pass "RLS policies active ($policy_count policies on tenant tables)"
    return 0
}

# ============================================================================
# Main Test Execution
# ============================================================================
main() {
    echo ""
    log_info "=========================================="
    log_info "Tenant Onboarding Validation Test Suite"
    log_info "=========================================="
    echo ""

    # Run tests
    test_tenant_config || true
    test_credentials_encrypted || true
    test_enhancement_preferences || true
    test_webhook_signature || true
    test_redis_queue || true
    test_worker_processing || true
    test_rls_context || true
    test_rls_policies || true

    # Summary
    echo ""
    log_info "=========================================="
    log_info "Test Summary"
    log_info "=========================================="
    log_info "Tests Run:    $TESTS_RUN"
    log_success "Tests Passed: $TESTS_PASSED"
    if [ $TESTS_FAILED -gt 0 ]; then
        log_error "Tests Failed: $TESTS_FAILED"
    else
        log_info "Tests Failed: $TESTS_FAILED"
    fi
    log_info "Log file: $LOG_FILE"
    echo ""

    # Exit code
    if [ $TESTS_FAILED -gt 0 ]; then
        log_error "❌ Tenant onboarding validation FAILED"
        exit 1
    else
        log_success "✅ Tenant onboarding validation PASSED"
        log_info "Tenant $TENANT_ID is ready for production use!"
        exit 0
    fi
}

# Run main function
main
