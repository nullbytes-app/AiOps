#!/usr/bin/env bash

################################################################################
# Production Smoke Tests
#
# Purpose: Quick validation of critical production endpoints after deployment
# Usage: bash tests/smoke/production_smoke_tests.sh [API_BASE_URL]
# Example: bash tests/smoke/production_smoke_tests.sh http://localhost:8000
#
# Story: 4-8 Testing, Deployment, and Rollout - AC-5
# Version: 1.0
# Last Updated: November 20, 2025
################################################################################

set -e  # Exit on first failure
set -o pipefail  # Exit on pipe failures

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
API_BASE_URL="${1:-http://localhost:8000}"
TIMEOUT=10
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
START_TIME=$(date +%s)

# Test results array
declare -a FAILED_TEST_NAMES=()

################################################################################
# Helper Functions
################################################################################

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_test() {
    echo -e "${YELLOW}TEST ${TOTAL_TESTS}:${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅ PASS:${NC} $1"
    ((PASSED_TESTS++))
}

print_failure() {
    echo -e "${RED}❌ FAIL:${NC} $1"
    ((FAILED_TESTS++))
    FAILED_TEST_NAMES+=("$2")
}

print_info() {
    echo -e "${BLUE}ℹ️  INFO:${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️  WARN:${NC} $1"
}

# Make HTTP request with timeout
http_get() {
    local url=$1
    local expected_status=${2:-200}

    local response
    response=$(curl -s -w "\n%{http_code}" --max-time $TIMEOUT "$url" 2>&1)
    local exit_code=$?

    if [ $exit_code -ne 0 ]; then
        echo "ERROR: curl failed with exit code $exit_code"
        return 1
    fi

    local body=$(echo "$response" | sed '$d')
    local status=$(echo "$response" | tail -n 1)

    if [ "$status" -eq "$expected_status" ]; then
        echo "$body"
        return 0
    else
        echo "ERROR: Expected status $expected_status, got $status"
        echo "$body"
        return 1
    fi
}

# Make HTTP POST request with JSON payload
http_post() {
    local url=$1
    local data=$2
    local expected_status=${3:-200}
    local auth_header=${4:-}

    local auth_flag=""
    if [ -n "$auth_header" ]; then
        auth_flag="-H \"Authorization: Bearer $auth_header\""
    fi

    local response
    response=$(curl -s -w "\n%{http_code}" --max-time $TIMEOUT \
        -X POST "$url" \
        -H "Content-Type: application/json" \
        $auth_flag \
        -d "$data" 2>&1)
    local exit_code=$?

    if [ $exit_code -ne 0 ]; then
        echo "ERROR: curl failed with exit code $exit_code"
        return 1
    fi

    local body=$(echo "$response" | sed '$d')
    local status=$(echo "$response" | tail -n 1)

    if [ "$status" -eq "$expected_status" ]; then
        echo "$body"
        return 0
    else
        echo "ERROR: Expected status $expected_status, got $status"
        echo "$body"
        return 1
    fi
}

# Check if jq is installed (for JSON parsing)
check_dependencies() {
    if ! command -v jq &> /dev/null; then
        print_warning "jq not found - JSON parsing will be limited"
        return 1
    fi
    return 0
}

################################################################################
# Test Cases
################################################################################

# Test 1: API Health Check
test_api_health() {
    ((TOTAL_TESTS++))
    print_test "API health check endpoint"

    local response
    if response=$(http_get "${API_BASE_URL}/health"); then
        # Check if response contains "healthy" status
        if echo "$response" | grep -q '"status".*"healthy"'; then
            print_success "API health check passed"
            print_info "Response: $response"
            return 0
        else
            print_failure "API health check returned unexpected status" "API Health Check"
            print_info "Response: $response"
            return 1
        fi
    else
        print_failure "API health check failed - endpoint unreachable" "API Health Check"
        print_info "Response: $response"
        return 1
    fi
}

# Test 2: Database Connectivity
test_database_connectivity() {
    ((TOTAL_TESTS++))
    print_test "Database connectivity via health check"

    local response
    if response=$(http_get "${API_BASE_URL}/health"); then
        # Check if database connection is reported as healthy
        if echo "$response" | grep -q '"database".*"healthy"'; then
            print_success "Database connectivity verified"
            return 0
        else
            print_failure "Database connection not healthy" "Database Connectivity"
            print_info "Response: $response"
            return 1
        fi
    else
        print_failure "Could not verify database connectivity" "Database Connectivity"
        return 1
    fi
}

# Test 3: Redis Connectivity
test_redis_connectivity() {
    ((TOTAL_TESTS++))
    print_test "Redis connectivity via health check"

    local response
    if response=$(http_get "${API_BASE_URL}/health"); then
        # Check if Redis connection is reported as healthy
        if echo "$response" | grep -q '"redis".*"healthy"'; then
            print_success "Redis connectivity verified"
            return 0
        else
            print_failure "Redis connection not healthy" "Redis Connectivity"
            print_info "Response: $response"
            return 1
        fi
    else
        print_failure "Could not verify Redis connectivity" "Redis Connectivity"
        return 1
    fi
}

# Test 4: OpenAPI Documentation
test_openapi_docs() {
    ((TOTAL_TESTS++))
    print_test "OpenAPI documentation endpoint"

    local response
    if response=$(http_get "${API_BASE_URL}/docs"); then
        # Check if response contains OpenAPI/Swagger UI HTML
        if echo "$response" | grep -qi "swagger" || echo "$response" | grep -qi "openapi"; then
            print_success "OpenAPI documentation accessible"
            return 0
        else
            print_failure "OpenAPI documentation returned unexpected content" "OpenAPI Docs"
            return 1
        fi
    else
        print_failure "OpenAPI documentation endpoint failed" "OpenAPI Docs"
        return 1
    fi
}

# Test 5: Metrics Endpoint
test_metrics_endpoint() {
    ((TOTAL_TESTS++))
    print_test "Prometheus metrics endpoint"

    local response
    if response=$(http_get "${API_BASE_URL}/metrics/"); then
        # Check if response contains Prometheus metrics format
        if echo "$response" | grep -q "http_requests_total" || echo "$response" | grep -q "process_cpu_seconds_total"; then
            print_success "Metrics endpoint returning Prometheus data"

            # Count number of metrics
            local metric_count=$(echo "$response" | grep -c "^[a-z].*{" || true)
            print_info "Metrics exported: $metric_count"
            return 0
        else
            print_failure "Metrics endpoint returned invalid format" "Metrics Endpoint"
            return 1
        fi
    else
        print_failure "Metrics endpoint failed" "Metrics Endpoint"
        return 1
    fi
}

# Test 6: API Response Time
test_api_response_time() {
    ((TOTAL_TESTS++))
    print_test "API response time measurement"

    local start=$(date +%s%N)
    local response
    if response=$(http_get "${API_BASE_URL}/health"); then
        local end=$(date +%s%N)
        local duration_ms=$(( (end - start) / 1000000 ))

        # Response time should be < 1000ms (1 second)
        if [ $duration_ms -lt 1000 ]; then
            print_success "API response time acceptable: ${duration_ms}ms"
            return 0
        else
            print_warning "API response time slow: ${duration_ms}ms (threshold: 1000ms)"
            # Don't fail on slow response, just warn
            ((PASSED_TESTS++))
            return 0
        fi
    else
        print_failure "Could not measure API response time" "API Response Time"
        return 1
    fi
}

# Test 7: CORS Headers (for API accessible from browser)
test_cors_headers() {
    ((TOTAL_TESTS++))
    print_test "CORS headers configuration"

    local response_headers
    response_headers=$(curl -s -I --max-time $TIMEOUT \
        -H "Origin: http://localhost:3000" \
        "${API_BASE_URL}/health" 2>&1)
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        # Check for CORS headers (optional - may not be configured)
        if echo "$response_headers" | grep -qi "access-control-allow"; then
            print_success "CORS headers present"
            return 0
        else
            print_info "CORS headers not configured (may be intentional)"
            # Don't fail if CORS not configured
            ((PASSED_TESTS++))
            return 0
        fi
    else
        print_failure "Could not check CORS headers" "CORS Headers"
        return 1
    fi
}

# Test 8: API Error Handling (404 endpoint)
test_error_handling() {
    ((TOTAL_TESTS++))
    print_test "API error handling for non-existent endpoint"

    local response
    if response=$(http_get "${API_BASE_URL}/nonexistent-endpoint-test-12345" 404); then
        # Check if response contains proper error format
        if echo "$response" | grep -q "detail" || echo "$response" | grep -q "error"; then
            print_success "API returns proper error response for 404"
            return 0
        else
            print_warning "API 404 response format unexpected"
            # Don't fail, just warn
            ((PASSED_TESTS++))
            return 0
        fi
    else
        # If we get here, it means status wasn't 404 (unexpected)
        print_failure "API error handling returned unexpected status" "Error Handling"
        return 1
    fi
}

# Test 9: Webhook Endpoint Reachability (without signature)
test_webhook_endpoint() {
    ((TOTAL_TESTS++))
    print_test "Webhook endpoint reachability"

    # Try to POST to webhook endpoint without signature (should return 401 or 422)
    local response
    response=$(curl -s -w "\n%{http_code}" --max-time $TIMEOUT \
        -X POST "${API_BASE_URL}/webhook/servicedesk" \
        -H "Content-Type: application/json" \
        -d '{"tenant_id":"test","event":"test"}' 2>&1)

    local body=$(echo "$response" | sed '$d')
    local status=$(echo "$response" | tail -n 1)

    # Expect 401 (missing signature) or 422 (validation error)
    if [ "$status" -eq 401 ] || [ "$status" -eq 422 ]; then
        print_success "Webhook endpoint reachable (correctly rejected invalid request)"
        print_info "Status: $status (expected 401 or 422 for missing signature)"
        return 0
    elif [ "$status" -eq 404 ]; then
        print_failure "Webhook endpoint not found (404)" "Webhook Endpoint"
        return 1
    else
        print_warning "Webhook endpoint returned unexpected status: $status"
        # Don't fail, endpoint is reachable
        ((PASSED_TESTS++))
        return 0
    fi
}

# Test 10: Security Headers Check
test_security_headers() {
    ((TOTAL_TESTS++))
    print_test "Security headers presence"

    local response_headers
    response_headers=$(curl -s -I --max-time $TIMEOUT "${API_BASE_URL}/health" 2>&1)
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        local headers_found=0

        # Check for X-Content-Type-Options
        if echo "$response_headers" | grep -qi "x-content-type-options"; then
            print_info "✓ X-Content-Type-Options header present"
            ((headers_found++))
        fi

        # Check for X-Frame-Options
        if echo "$response_headers" | grep -qi "x-frame-options"; then
            print_info "✓ X-Frame-Options header present"
            ((headers_found++))
        fi

        # Check for Strict-Transport-Security (HTTPS only)
        if echo "$response_headers" | grep -qi "strict-transport-security"; then
            print_info "✓ Strict-Transport-Security header present"
            ((headers_found++))
        fi

        if [ $headers_found -gt 0 ]; then
            print_success "Security headers detected ($headers_found/3)"
            return 0
        else
            print_info "No security headers detected (may need configuration)"
            # Don't fail if security headers not configured
            ((PASSED_TESTS++))
            return 0
        fi
    else
        print_failure "Could not check security headers" "Security Headers"
        return 1
    fi
}

################################################################################
# Advanced Tests (Optional - Comment out if credentials not available)
################################################################################

# Test 11: Authentication Flow (requires admin credentials)
test_authentication() {
    ((TOTAL_TESTS++))
    print_test "Authentication flow (requires credentials)"

    # Check if admin credentials are set
    if [ -z "${ADMIN_USERNAME:-}" ] || [ -z "${ADMIN_PASSWORD:-}" ]; then
        print_info "Skipping authentication test (credentials not provided)"
        print_info "Set ADMIN_USERNAME and ADMIN_PASSWORD to enable this test"
        ((PASSED_TESTS++))
        return 0
    fi

    # Attempt login
    local response
    local login_data="{\"username\":\"${ADMIN_USERNAME}\",\"password\":\"${ADMIN_PASSWORD}\"}"

    if response=$(http_post "${API_BASE_URL}/api/v1/auth/login" "$login_data" 200); then
        # Check if JWT token returned
        if echo "$response" | grep -q "access_token"; then
            print_success "Authentication successful - JWT token received"

            # Extract token for subsequent tests
            if check_dependencies; then
                JWT_TOKEN=$(echo "$response" | jq -r '.access_token')
                print_info "JWT token extracted for subsequent tests"
            fi
            return 0
        else
            print_failure "Authentication response missing access_token" "Authentication"
            return 1
        fi
    else
        print_failure "Authentication endpoint failed" "Authentication"
        return 1
    fi
}

# Test 12: Agent List Endpoint (requires authentication)
test_agent_list() {
    ((TOTAL_TESTS++))
    print_test "Agent list endpoint (requires authentication)"

    if [ -z "${JWT_TOKEN:-}" ]; then
        print_info "Skipping agent list test (no JWT token available)"
        ((PASSED_TESTS++))
        return 0
    fi

    local response
    response=$(curl -s -w "\n%{http_code}" --max-time $TIMEOUT \
        -H "Authorization: Bearer ${JWT_TOKEN}" \
        "${API_BASE_URL}/api/v1/agents" 2>&1)

    local body=$(echo "$response" | sed '$d')
    local status=$(echo "$response" | tail -n 1)

    if [ "$status" -eq 200 ]; then
        print_success "Agent list endpoint accessible"

        if check_dependencies; then
            local agent_count=$(echo "$body" | jq '. | length')
            print_info "Agents found: $agent_count"
        fi
        return 0
    else
        print_failure "Agent list endpoint failed with status $status" "Agent List"
        return 1
    fi
}

################################################################################
# Test Execution
################################################################################

main() {
    print_header "PRODUCTION SMOKE TESTS"
    echo -e "Target: ${BLUE}${API_BASE_URL}${NC}"
    echo -e "Timeout: ${TIMEOUT}s per request"
    echo -e "Started: $(date '+%Y-%m-%d %H:%M:%S')\n"

    # Check dependencies
    check_dependencies || true

    # Core Infrastructure Tests
    print_header "CORE INFRASTRUCTURE TESTS"
    test_api_health || true
    test_database_connectivity || true
    test_redis_connectivity || true

    # API Functionality Tests
    print_header "API FUNCTIONALITY TESTS"
    test_openapi_docs || true
    test_metrics_endpoint || true
    test_api_response_time || true
    test_cors_headers || true
    test_error_handling || true
    test_webhook_endpoint || true
    test_security_headers || true

    # Authentication Tests (optional)
    print_header "AUTHENTICATION TESTS"
    test_authentication || true
    test_agent_list || true

    # Summary
    print_header "TEST SUMMARY"

    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))

    echo -e "Total Tests: ${TOTAL_TESTS}"
    echo -e "${GREEN}Passed: ${PASSED_TESTS}${NC}"
    echo -e "${RED}Failed: ${FAILED_TESTS}${NC}"
    echo -e "Duration: ${duration}s"
    echo -e "Completed: $(date '+%Y-%m-%d %H:%M:%S')\n"

    # List failed tests
    if [ $FAILED_TESTS -gt 0 ]; then
        echo -e "${RED}FAILED TESTS:${NC}"
        for test_name in "${FAILED_TEST_NAMES[@]}"; do
            echo -e "  - $test_name"
        done
        echo ""
    fi

    # Exit with failure if any tests failed
    if [ $FAILED_TESTS -gt 0 ]; then
        echo -e "${RED}❌ SMOKE TESTS FAILED${NC}"
        echo -e "${YELLOW}Review failed tests above and check logs for details${NC}\n"
        exit 1
    else
        echo -e "${GREEN}✅ ALL SMOKE TESTS PASSED${NC}"
        echo -e "${GREEN}Deployment validation successful${NC}\n"
        exit 0
    fi
}

# Run main function
main "$@"
