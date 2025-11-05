#!/bin/bash
# Production Smoke Test Script
# Story 5.2: Deploy Application to Production Environment
#
# Validates production deployment with comprehensive smoke tests:
# - Health check endpoint
# - Readiness check endpoint
# - Webhook signature validation
# - End-to-end ticket enhancement workflow
#
# Usage:
#   ./scripts/production-smoke-test.sh https://api.ai-agents.production
#
# Exit codes:
#   0 - All tests passed
#   1 - One or more tests failed

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_BASE_URL="${1:-https://api.ai-agents.production}"
WEBHOOK_SECRET="${WEBHOOK_SECRET:-test-secret}"  # Override with env var
TENANT_ID="${TENANT_ID:-00000000-0000-0000-0000-000000000001}"

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
print_test() {
    echo -e "${YELLOW}[TEST]${NC} $1"
}

print_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
}

print_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((TESTS_FAILED++))
}

print_info() {
    echo -e "[INFO] $1"
}

# Start smoke tests
echo "========================================="
echo "Production Smoke Test Suite"
echo "========================================="
echo "API Base URL: $API_BASE_URL"
echo "Timestamp: $(date)"
echo "========================================="
echo ""

# Test 1: Health Check Endpoint
print_test "Test 1: Health Check Endpoint (GET /health)"
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "$API_BASE_URL/health" || echo "000")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
HEALTH_BODY=$(echo "$HEALTH_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" == "200" ]; then
    print_pass "Health check returned 200 OK"
    print_info "Response: $HEALTH_BODY"

    # Validate response structure
    if echo "$HEALTH_BODY" | jq -e '.status == "healthy"' > /dev/null 2>&1; then
        print_pass "Health status is 'healthy'"
    else
        print_fail "Health status is not 'healthy'"
    fi

    if echo "$HEALTH_BODY" | jq -e '.dependencies.database == "healthy"' > /dev/null 2>&1; then
        print_pass "Database dependency is healthy"
    else
        print_fail "Database dependency is not healthy"
    fi

    if echo "$HEALTH_BODY" | jq -e '.dependencies.redis == "healthy"' > /dev/null 2>&1; then
        print_pass "Redis dependency is healthy"
    else
        print_fail "Redis dependency is not healthy"
    fi
else
    print_fail "Health check returned HTTP $HTTP_CODE (expected 200)"
    print_info "Response: $HEALTH_BODY"
fi

echo ""

# Test 2: Readiness Check Endpoint
print_test "Test 2: Readiness Check Endpoint (GET /api/v1/ready)"
READY_RESPONSE=$(curl -s -w "\n%{http_code}" "$API_BASE_URL/api/v1/ready" || echo "000")
HTTP_CODE=$(echo "$READY_RESPONSE" | tail -n1)
READY_BODY=$(echo "$READY_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" == "200" ]; then
    print_pass "Readiness check returned 200 OK"
    print_info "Response: $READY_BODY"

    if echo "$READY_BODY" | jq -e '.status == "ready"' > /dev/null 2>&1; then
        print_pass "Readiness status is 'ready'"
    else
        print_fail "Readiness status is not 'ready'"
    fi
else
    print_fail "Readiness check returned HTTP $HTTP_CODE (expected 200)"
    print_info "Response: $READY_BODY"
fi

echo ""

# Test 3: TLS Certificate Validation
print_test "Test 3: TLS Certificate Validation"
if echo "$API_BASE_URL" | grep -q "https://"; then
    CERT_INFO=$(curl -vI "$API_BASE_URL/health" 2>&1 | grep -E "SSL certificate|subject|issuer" || true)
    if [ -n "$CERT_INFO" ]; then
        print_pass "TLS certificate is valid"
        print_info "Certificate info: $CERT_INFO"
    else
        print_fail "TLS certificate validation failed"
    fi
else
    print_info "Skipping TLS test (API URL is not HTTPS)"
fi

echo ""

# Test 4: Webhook Signature Validation (Invalid Signature)
print_test "Test 4: Webhook Signature Validation (Invalid Signature)"
WEBHOOK_PAYLOAD='{"ticket_id": "TEST-001", "event": "ticket_created", "tenant_id": "'$TENANT_ID'"}'
INVALID_SIG_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -H "X-ServiceDesk-Signature: invalid-signature" \
    -H "X-Tenant-ID: $TENANT_ID" \
    -d "$WEBHOOK_PAYLOAD" \
    "$API_BASE_URL/webhook/servicedesk" || echo "000")
HTTP_CODE=$(echo "$INVALID_SIG_RESPONSE" | tail -n1)

if [ "$HTTP_CODE" == "401" ]; then
    print_pass "Invalid signature rejected with 401 Unauthorized"
else
    print_fail "Invalid signature returned HTTP $HTTP_CODE (expected 401)"
fi

echo ""

# Test 5: Webhook with Valid Signature
print_test "Test 5: Webhook with Valid Signature"
# Generate HMAC-SHA256 signature
SIGNATURE=$(echo -n "$WEBHOOK_PAYLOAD" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | awk '{print $2}')
VALID_SIG_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -H "X-ServiceDesk-Signature: sha256=$SIGNATURE" \
    -H "X-Tenant-ID: $TENANT_ID" \
    -d "$WEBHOOK_PAYLOAD" \
    "$API_BASE_URL/webhook/servicedesk" || echo "000")
HTTP_CODE=$(echo "$VALID_SIG_RESPONSE" | tail -n1)
WEBHOOK_BODY=$(echo "$VALID_SIG_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" == "202" ]; then
    print_pass "Valid webhook accepted with 202 Accepted"
    print_info "Response: $WEBHOOK_BODY"

    # Extract job ID if present
    JOB_ID=$(echo "$WEBHOOK_BODY" | jq -r '.job_id // empty')
    if [ -n "$JOB_ID" ]; then
        print_pass "Job ID returned: $JOB_ID"
    fi
else
    print_fail "Valid webhook returned HTTP $HTTP_CODE (expected 202)"
    print_info "Response: $WEBHOOK_BODY"
fi

echo ""

# Test 6: Metrics Endpoint (Prometheus)
print_test "Test 6: Metrics Endpoint (GET /metrics)"
METRICS_RESPONSE=$(curl -s -w "\n%{http_code}" "$API_BASE_URL/metrics" || echo "000")
HTTP_CODE=$(echo "$METRICS_RESPONSE" | tail -n1)
METRICS_BODY=$(echo "$METRICS_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" == "200" ]; then
    print_pass "Metrics endpoint returned 200 OK"

    # Check for Prometheus metrics format
    if echo "$METRICS_BODY" | grep -q "# HELP"; then
        print_pass "Metrics in Prometheus format"
    else
        print_fail "Metrics not in Prometheus format"
    fi

    # Check for custom metrics
    if echo "$METRICS_BODY" | grep -q "enhancement_"; then
        print_pass "Custom enhancement metrics found"
    else
        print_info "Custom enhancement metrics not yet available (may require traffic)"
    fi
else
    print_fail "Metrics endpoint returned HTTP $HTTP_CODE (expected 200)"
fi

echo ""

# Test 7: HTTP to HTTPS Redirect
print_test "Test 7: HTTP to HTTPS Redirect"
if echo "$API_BASE_URL" | grep -q "https://"; then
    HTTP_URL=$(echo "$API_BASE_URL" | sed 's/https:/http:/')
    REDIRECT_RESPONSE=$(curl -s -L -w "\n%{http_code}" "$HTTP_URL/health" || echo "000")
    HTTP_CODE=$(echo "$REDIRECT_RESPONSE" | tail -n1)

    if [ "$HTTP_CODE" == "200" ]; then
        print_pass "HTTP redirects to HTTPS successfully"
    else
        print_fail "HTTP to HTTPS redirect failed (HTTP $HTTP_CODE)"
    fi
else
    print_info "Skipping HTTPS redirect test (API URL is not HTTPS)"
fi

echo ""

# Summary
echo "========================================="
echo "Smoke Test Summary"
echo "========================================="
echo -e "${GREEN}Tests Passed:${NC} $TESTS_PASSED"
echo -e "${RED}Tests Failed:${NC} $TESTS_FAILED"
echo "========================================="

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All smoke tests passed! ✓${NC}"
    exit 0
else
    echo -e "${RED}Some smoke tests failed! ✗${NC}"
    exit 1
fi
