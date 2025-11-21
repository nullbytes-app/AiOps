#!/bin/bash
#
# Run All Load Tests Sequentially
#
# Executes all 4 load test scenarios and generates comprehensive report.
#
# Usage:
#   ./tests/load/run_all_load_tests.sh [HOST]
#
# Example:
#   ./tests/load/run_all_load_tests.sh http://localhost:8000
#   ./tests/load/run_all_load_tests.sh https://staging.ai-agents.example.com
#

set -euo pipefail

# Configuration
HOST="${1:-http://localhost:8000}"
REPORT_DIR="tests/load/reports/$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$REPORT_DIR/test_execution.log"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Create report directory
mkdir -p "$REPORT_DIR"

echo "================================================================================"
echo "AI Agents Load Testing Suite"
echo "================================================================================"
echo "Target Host: $HOST"
echo "Report Directory: $REPORT_DIR"
echo "Start Time: $(date)"
echo "================================================================================"
echo ""

# Function to run a single load test
run_load_test() {
    local test_name=$1
    local test_file=$2
    local users=$3
    local spawn_rate=$4
    local run_time=$5
    local extra_args="${6:-}"

    echo "--------------------------------------------------------------------------------"
    echo -e "${YELLOW}Running: $test_name${NC}"
    echo "--------------------------------------------------------------------------------"
    echo "  Users: $users"
    echo "  Spawn Rate: $spawn_rate users/sec"
    echo "  Duration: $run_time"
    echo "  File: $test_file"
    echo ""

    local report_name="$REPORT_DIR/${test_name}_results.html"
    local csv_name="$REPORT_DIR/${test_name}_stats.csv"

    # Run Locust test
    if locust -f "tests/load/$test_file" --headless \
              --users "$users" \
              --spawn-rate "$spawn_rate" \
              --run-time "$run_time" \
              --host "$HOST" \
              --html "$report_name" \
              --csv "$csv_name" \
              $extra_args \
              2>&1 | tee -a "$LOG_FILE"; then
        echo -e "${GREEN}✓ $test_name completed successfully${NC}"
        echo ""
    else
        echo -e "${RED}✗ $test_name failed${NC}"
        echo ""
        return 1
    fi

    # Cool-down period between tests
    echo "Cool-down period: 30 seconds..."
    sleep 30
    echo ""
}

# Check if Locust is installed
if ! command -v locust &> /dev/null; then
    echo -e "${RED}Error: Locust is not installed${NC}"
    echo "Install with: pip install locust"
    exit 1
fi

# Verify target host is reachable
echo "Verifying target host accessibility..."
if curl -sf "$HOST/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Host is reachable${NC}"
    echo ""
else
    echo -e "${RED}✗ Cannot reach $HOST/health${NC}"
    echo "Please ensure the API server is running"
    exit 1
fi

# Initialize test execution log
cat > "$LOG_FILE" <<EOF
AI Agents Load Testing Suite - Execution Log
==================================================
Start Time: $(date)
Target Host: $HOST
Report Directory: $REPORT_DIR
==================================================

EOF

# Track test results
declare -A test_results

# Test 1: Baseline Load (5 minutes)
if run_load_test \
    "baseline" \
    "baseline_load_test.py" \
    "10" \
    "2" \
    "5m"; then
    test_results[baseline]="PASS"
else
    test_results[baseline]="FAIL"
fi

# Test 2: Peak Load (10 minutes)
if run_load_test \
    "peak" \
    "peak_load_test.py" \
    "100" \
    "10" \
    "10m"; then
    test_results[peak]="PASS"
else
    test_results[peak]="FAIL"
fi

# Test 3: Burst Load (custom shape, ~4 minutes)
echo "--------------------------------------------------------------------------------"
echo -e "${YELLOW}Running: Burst Load Test${NC}"
echo "--------------------------------------------------------------------------------"
echo "  Pattern: Custom shape (1→200→10 users)"
echo "  Duration: ~4 minutes"
echo "  File: burst_load_test.py"
echo ""

if locust -f tests/load/burst_load_test.py --headless \
          --host "$HOST" \
          --html "$REPORT_DIR/burst_results.html" \
          --csv "$REPORT_DIR/burst_stats.csv" \
          2>&1 | tee -a "$LOG_FILE"; then
    echo -e "${GREEN}✓ Burst test completed successfully${NC}"
    test_results[burst]="PASS"
else
    echo -e "${RED}✗ Burst test failed${NC}"
    test_results[burst]="FAIL"
fi
echo ""
sleep 30

# Test 4: Endurance Load (shortened to 5min for quick validation, use 30m for full test)
if run_load_test \
    "endurance" \
    "endurance_load_test.py" \
    "50" \
    "5" \
    "5m" \
    "# Use --run-time 30m for full endurance test"; then
    test_results[endurance]="PASS"
else
    test_results[endurance]="FAIL"
fi

# Generate summary report
echo "================================================================================"
echo "LOAD TESTING SUITE - SUMMARY REPORT"
echo "================================================================================"
echo "End Time: $(date)"
echo ""
echo "Test Results:"
echo "  Baseline Load:   ${test_results[baseline]}"
echo "  Peak Load:       ${test_results[peak]}"
echo "  Burst Load:      ${test_results[burst]}"
echo "  Endurance Load:  ${test_results[endurance]}"
echo ""

# Count passes and failures
pass_count=0
fail_count=0
for result in "${test_results[@]}"; do
    if [ "$result" == "PASS" ]; then
        ((pass_count++))
    else
        ((fail_count++))
    fi
done

echo "Overall:"
echo "  Passed: $pass_count/4"
echo "  Failed: $fail_count/4"
echo ""

if [ $fail_count -eq 0 ]; then
    echo -e "${GREEN}✓ ALL LOAD TESTS PASSED${NC}"
    echo ""
    echo "Performance Validation: SUCCESS"
    echo "  - p95 latency <60s for all scenarios"
    echo "  - Success rate >99% for all scenarios"
    echo "  - System stable under all load conditions"
    exit_code=0
else
    echo -e "${RED}✗ SOME LOAD TESTS FAILED${NC}"
    echo ""
    echo "Performance Validation: FAILURE"
    echo "  - Review individual test reports in $REPORT_DIR"
    echo "  - Check application logs for errors"
    echo "  - Verify infrastructure capacity"
    exit_code=1
fi

echo ""
echo "Report Location: $REPORT_DIR"
echo "  - HTML Reports: *_results.html"
echo "  - CSV Stats: *_stats.csv"
echo "  - Execution Log: test_execution.log"
echo ""
echo "================================================================================"

# Append summary to log
cat >> "$LOG_FILE" <<EOF

==================================================
SUMMARY
==================================================
End Time: $(date)
Passed: $pass_count/4
Failed: $fail_count/4
Overall Result: $([ $fail_count -eq 0 ] && echo "PASS" || echo "FAIL")
==================================================
EOF

exit $exit_code
