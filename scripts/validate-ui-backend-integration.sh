#!/bin/bash

###############################################################################
# UI-Backend Integration Validation Script
# Purpose: Validates that Next.js UI and FastAPI backend are properly integrated
# Usage: ./scripts/validate-ui-backend-integration.sh
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
TIMEOUT=5

# Test results
PASSED=0
FAILED=0

echo "=========================================="
echo "UI-Backend Integration Validation"
echo "=========================================="
echo "Backend URL: $BACKEND_URL"
echo "Frontend URL: $FRONTEND_URL"
echo ""

###############################################################################
# Helper Functions
###############################################################################

print_test() {
    echo -e "${YELLOW}[TEST]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
    ((PASSED++))
}

print_failure() {
    echo -e "${RED}[✗]${NC} $1"
    ((FAILED++))
}

check_service() {
    local url=$1
    local name=$2

    if curl -s -f --max-time $TIMEOUT "$url" > /dev/null 2>&1; then
        print_success "$name is reachable"
        return 0
    else
        print_failure "$name is NOT reachable at $url"
        return 1
    fi
}

check_json_response() {
    local url=$1
    local name=$2

    response=$(curl -s --max-time $TIMEOUT "$url")
    if echo "$response" | jq . > /dev/null 2>&1; then
        print_success "$name returns valid JSON"
        return 0
    else
        print_failure "$name does NOT return valid JSON"
        return 1
    fi
}

###############################################################################
# Phase 1: Service Health Checks
###############################################################################

echo "=========================================="
echo "Phase 1: Service Health Checks"
echo "=========================================="

print_test "Checking backend health endpoint"
check_service "$BACKEND_URL/health" "Backend API"

print_test "Checking backend OpenAPI docs"
check_service "$BACKEND_URL/docs" "OpenAPI Documentation"

print_test "Checking frontend"
check_service "$FRONTEND_URL" "Next.js Frontend"

echo ""

###############################################################################
# Phase 2: API Endpoint Validation
###############################################################################

echo "=========================================="
echo "Phase 2: API Endpoint Validation"
echo "=========================================="

print_test "Checking /api/agents endpoint"
if check_json_response "$BACKEND_URL/api/agents" "Agents API"; then
    # Additional validation: check if response is an array
    response=$(curl -s "$BACKEND_URL/api/agents")
    if echo "$response" | jq -e 'type == "array"' > /dev/null 2>&1; then
        print_success "Agents API returns array"
    else
        print_failure "Agents API does NOT return array"
    fi
fi

print_test "Checking /api/tools endpoint"
check_json_response "$BACKEND_URL/api/tools" "Tools API"

print_test "Checking /api/prompts endpoint"
check_json_response "$BACKEND_URL/api/prompts" "Prompts API"

echo ""

###############################################################################
# Phase 3: CORS Configuration
###############################################################################

echo "=========================================="
echo "Phase 3: CORS Configuration"
echo "=========================================="

print_test "Checking CORS headers from backend"
cors_headers=$(curl -s -I -X OPTIONS "$BACKEND_URL/api/agents" \
    -H "Origin: $FRONTEND_URL" \
    -H "Access-Control-Request-Method: GET" 2>&1)

if echo "$cors_headers" | grep -q "Access-Control-Allow-Origin"; then
    print_success "CORS headers present"
else
    print_failure "CORS headers NOT present - frontend may have issues"
fi

echo ""

###############################################################################
# Phase 4: Frontend Build Validation
###############################################################################

echo "=========================================="
echo "Phase 4: Frontend Build Validation"
echo "=========================================="

if [ -d "nextjs-ui" ]; then
    print_test "Checking Next.js build configuration"

    if [ -f "nextjs-ui/.env.local" ]; then
        print_success ".env.local exists"

        # Check if API URL is configured
        if grep -q "NEXT_PUBLIC_API_URL" "nextjs-ui/.env.local"; then
            print_success "NEXT_PUBLIC_API_URL configured"
        else
            print_failure "NEXT_PUBLIC_API_URL NOT configured"
        fi
    else
        print_failure ".env.local NOT found - copy from .env.example"
    fi

    if [ -f "nextjs-ui/package.json" ]; then
        print_success "package.json exists"
    else
        print_failure "package.json NOT found"
    fi
else
    print_failure "nextjs-ui directory NOT found"
fi

echo ""

###############################################################################
# Phase 5: Environment Variables Check
###############################################################################

echo "=========================================="
echo "Phase 5: Environment Variables Check"
echo "=========================================="

print_test "Checking backend environment variables"

if [ -f ".env" ]; then
    print_success ".env file exists"

    # Check critical env vars
    required_vars=("AI_AGENTS_DATABASE_URL" "REDIS_URL" "SECRET_KEY")
    for var in "${required_vars[@]}"; do
        if grep -q "^$var=" .env; then
            print_success "$var is set"
        else
            print_failure "$var is NOT set in .env"
        fi
    done
else
    print_failure ".env file NOT found"
fi

echo ""

###############################################################################
# Phase 6: Authentication Flow Test
###############################################################################

echo "=========================================="
echo "Phase 6: Authentication Flow Test"
echo "=========================================="

print_test "Testing login endpoint availability"
# Test if endpoint exists (even if auth fails)
login_response=$(curl -s -w "%{http_code}" -o /dev/null \
    -X POST "$BACKEND_URL/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"test","password":"test"}')

if [ "$login_response" = "401" ] || [ "$login_response" = "422" ] || [ "$login_response" = "200" ]; then
    print_success "Login endpoint responds (status: $login_response)"
else
    print_failure "Login endpoint error (status: $login_response)"
fi

echo ""

###############################################################################
# Phase 7: Docker Health Check (if running in containers)
###############################################################################

echo "=========================================="
echo "Phase 7: Docker Container Status"
echo "=========================================="

if command -v docker-compose &> /dev/null || command -v docker &> /dev/null; then
    print_test "Checking Docker container status"

    if docker ps | grep -q "ai-ops-api"; then
        print_success "API container is running"
    else
        print_failure "API container is NOT running"
    fi

    if docker ps | grep -q "ai-ops-nextjs-ui"; then
        print_success "Next.js UI container is running"
    else
        echo -e "${YELLOW}[!]${NC} Next.js UI container is NOT running (may not be deployed yet)"
    fi

    if docker ps | grep -q "ai-ops-postgres"; then
        print_success "PostgreSQL container is running"
    else
        print_failure "PostgreSQL container is NOT running"
    fi

    if docker ps | grep -q "ai-ops-redis"; then
        print_success "Redis container is running"
    else
        print_failure "Redis container is NOT running"
    fi
else
    echo -e "${YELLOW}[!]${NC} Docker not available - skipping container checks"
fi

echo ""

###############################################################################
# Summary
###############################################################################

echo "=========================================="
echo "Validation Summary"
echo "=========================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All validation checks passed!${NC}"
    echo "The UI and backend are properly integrated."
    exit 0
else
    echo -e "${RED}✗ Some validation checks failed.${NC}"
    echo "Please review the failures above and fix integration issues."
    exit 1
fi
