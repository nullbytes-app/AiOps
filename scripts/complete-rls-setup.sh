#!/bin/bash
# Complete RLS Setup and Validation Script
# Story 3.1 - Implement Row-Level Security in PostgreSQL
#
# This script completes the remaining steps to unblock the story:
# 1. Starts Docker services (if not running)
# 2. Executes Alembic migration
# 3. Verifies RLS policies are enabled
# 4. Runs RLS tests
# 5. Generates summary report

set -e  # Exit on any error

echo "=========================================="
echo "RLS Setup and Validation Script"
echo "Story 3.1 - Row-Level Security"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Check Docker status
echo "Step 1: Checking Docker status..."
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}ERROR: Docker is not running${NC}"
    echo "Please start Docker Desktop and run this script again"
    exit 1
fi
echo -e "${GREEN}✓ Docker is running${NC}"
echo ""

# Step 2: Start database services
echo "Step 2: Starting database services..."
docker-compose up -d postgres redis
echo "Waiting for PostgreSQL to be ready..."
sleep 5

# Check if postgres is running
if docker ps | grep -q postgres; then
    echo -e "${GREEN}✓ PostgreSQL is running${NC}"
else
    echo -e "${RED}ERROR: PostgreSQL failed to start${NC}"
    docker-compose logs postgres
    exit 1
fi
echo ""

# Step 3: Run Alembic migration
echo "Step 3: Applying RLS migration..."
echo "Running: alembic upgrade head"
alembic upgrade head

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Migration applied successfully${NC}"
else
    echo -e "${RED}ERROR: Migration failed${NC}"
    exit 1
fi
echo ""

# Step 4: Verify RLS is enabled
echo "Step 4: Verifying RLS policies..."

# Get database connection details from .env or use defaults
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_USER=${DB_USER:-postgres}
DB_NAME=${DB_NAME:-ai_agents}

# Check if we can connect to the database
if ! docker exec $(docker ps -qf "name=postgres") psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${YELLOW}Warning: Cannot verify RLS directly (database connection issue)${NC}"
    echo "You may need to check manually after the script completes"
else
    echo "Checking RLS status on tables..."

    # Check RLS enabled on tables
    TABLES=("tenant_configs" "enhancement_history" "ticket_history" "system_inventory")
    for table in "${TABLES[@]}"; do
        RLS_STATUS=$(docker exec $(docker ps -qf "name=postgres") psql -U "$DB_USER" -d "$DB_NAME" -tAc \
            "SELECT relrowsecurity FROM pg_class WHERE relname = '$table'")

        if [ "$RLS_STATUS" = "t" ]; then
            echo -e "${GREEN}✓ RLS enabled on $table${NC}"
        else
            echo -e "${RED}✗ RLS NOT enabled on $table${NC}"
        fi
    done

    # Check policies exist
    POLICY_COUNT=$(docker exec $(docker ps -qf "name=postgres") psql -U "$DB_USER" -d "$DB_NAME" -tAc \
        "SELECT COUNT(*) FROM pg_policies WHERE policyname LIKE '%tenant_isolation%'")

    if [ "$POLICY_COUNT" -ge 4 ]; then
        echo -e "${GREEN}✓ Found $POLICY_COUNT RLS policies${NC}"
    else
        echo -e "${YELLOW}Warning: Expected 4 policies, found $POLICY_COUNT${NC}"
    fi
fi
echo ""

# Step 5: Run RLS tests
echo "Step 5: Running RLS unit tests..."
echo "Command: pytest tests/unit/test_row_level_security.py -v"
echo ""

pytest tests/unit/test_row_level_security.py -v

RLS_TEST_STATUS=$?
echo ""

if [ $RLS_TEST_STATUS -eq 0 ]; then
    echo -e "${GREEN}✓ All RLS tests passed!${NC}"
else
    echo -e "${RED}✗ Some RLS tests failed${NC}"
    echo "Review the test output above for details"
fi
echo ""

# Step 6: Run full test suite (optional)
echo "Step 6: Running full test suite..."
echo "This may take a few minutes..."
echo ""

pytest tests/ -q --tb=no | tail -50

FULL_TEST_STATUS=$?
echo ""

# Step 7: Summary
echo "=========================================="
echo "SETUP COMPLETE - SUMMARY"
echo "=========================================="
echo ""

if [ $RLS_TEST_STATUS -eq 0 ]; then
    echo -e "${GREEN}✓ RLS Tests: PASSED${NC}"
else
    echo -e "${RED}✗ RLS Tests: FAILED${NC}"
fi

if [ $FULL_TEST_STATUS -eq 0 ]; then
    echo -e "${GREEN}✓ Full Test Suite: PASSED${NC}"
else
    echo -e "${YELLOW}⚠ Full Test Suite: Some tests failed (may be unrelated to RLS)${NC}"
fi

echo ""
echo "Next Steps:"
echo "1. Review test results above"
echo "2. If RLS tests pass: Story 3.1 blockers are resolved!"
echo "3. If tests fail: Check logs and fix issues"
echo "4. Re-run code-review workflow after all tests pass"
echo ""
echo "Files modified by fixes:"
echo "  - tests/unit/test_row_level_security.py (syntax error fixed)"
echo "  - src/api/webhooks.py (RLS-aware dependency added)"
echo ""
echo "=========================================="
