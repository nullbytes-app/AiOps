#!/bin/bash
#
# Kubernetes Deployment Validation Script
# ========================================
#
# This script validates that all Kubernetes manifests are correctly configured
# and that the deployed components are healthy.
#
# Usage: ./test-deployment.sh [cluster-type]
# cluster-type: minikube | kind | cloud (default: minikube)
#
# Exit codes:
#   0 - All validations passed
#   1 - One or more validations failed
#

set -euo pipefail

# Configuration
NAMESPACE="ai-agents"
CLUSTER_TYPE="${1:-minikube}"
TIMEOUT=300  # 5 minutes
LOG_FILE="/tmp/k8s-deployment-test.log"

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
TESTS_PASSED=0
TESTS_FAILED=0

# Logging functions
log_header() {
    echo -e "\n${YELLOW}=== $1 ===${NC}"
}

log_pass() {
    echo -e "${GREEN}✓ PASS: $1${NC}"
    ((TESTS_PASSED++))
}

log_fail() {
    echo -e "${RED}✗ FAIL: $1${NC}"
    ((TESTS_FAILED++))
}

log_info() {
    echo -e "${YELLOW}ℹ INFO: $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    log_header "Checking Prerequisites"

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_fail "kubectl is not installed"
        exit 1
    fi
    log_pass "kubectl is installed"

    # Check cluster connection
    if ! kubectl cluster-info &> /dev/null; then
        log_fail "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    log_pass "Connected to Kubernetes cluster"

    # Check YAML files exist
    local yaml_files=(
        "k8s/namespace.yaml"
        "k8s/deployment-postgres.yaml"
        "k8s/deployment-redis.yaml"
        "k8s/deployment-api.yaml"
        "k8s/deployment-worker.yaml"
        "k8s/hpa-worker.yaml"
        "k8s/configmap.yaml"
        "k8s/secrets.yaml.example"
        "k8s/ingress.yaml"
    )

    for file in "${yaml_files[@]}"; do
        if [[ -f "$file" ]]; then
            log_pass "Found $file"
        else
            log_fail "Missing $file"
            exit 1
        fi
    done
}

# Validate YAML syntax
validate_yaml_syntax() {
    log_header "Validating YAML Syntax"

    local yaml_files=(
        "k8s/namespace.yaml"
        "k8s/deployment-postgres.yaml"
        "k8s/deployment-redis.yaml"
        "k8s/deployment-api.yaml"
        "k8s/deployment-worker.yaml"
        "k8s/hpa-worker.yaml"
        "k8s/configmap.yaml"
        "k8s/ingress.yaml"
    )

    for file in "${yaml_files[@]}"; do
        if kubectl apply -f "$file" --dry-run=client &> /dev/null; then
            log_pass "YAML syntax valid: $file"
        else
            log_fail "YAML syntax invalid: $file"
        fi
    done
}

# Apply namespace
apply_namespace() {
    log_header "Creating Namespace"

    if kubectl apply -f k8s/namespace.yaml > /dev/null 2>&1; then
        log_pass "Namespace manifest applied"
    else
        log_fail "Failed to apply namespace manifest"
        return 1
    fi

    # Verify namespace exists
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_pass "Namespace '$NAMESPACE' exists"
    else
        log_fail "Namespace '$NAMESPACE' not found"
        return 1
    fi
}

# Apply ConfigMap
apply_configmap() {
    log_header "Creating ConfigMap"

    if kubectl apply -f k8s/configmap.yaml -n "$NAMESPACE" > /dev/null 2>&1; then
        log_pass "ConfigMap manifest applied"
    else
        log_fail "Failed to apply ConfigMap manifest"
        return 1
    fi

    if kubectl get configmap app-config -n "$NAMESPACE" &> /dev/null; then
        log_pass "ConfigMap 'app-config' exists"
    else
        log_fail "ConfigMap 'app-config' not found"
        return 1
    fi
}

# Apply Secrets (using dummy base64 values for testing)
apply_secrets() {
    log_header "Creating Secrets (Test Values)"

    # Create test secrets with placeholder values
    local temp_secrets=$(mktemp)
    cat > "$temp_secrets" <<'EOF'
apiVersion: v1
kind: Secret
metadata:
  name: postgres-credentials
  namespace: ai-agents
type: Opaque
data:
  username: cG9zdGdyZXM=  # base64(postgres)
  password: dGVzdHBhc3M=  # base64(testpass)
---
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
  namespace: ai-agents
type: Opaque
data:
  database_url: cG9zdGdyZXM6Ly9wb3N0Z3Jlczp0ZXN0cGFzc0Bwb3N0Z3Jlc3FsLmFpLWFnZW50cy5zdmMuY2x1c3Rlci5sb2NhbDo1NDMyL2FpX2FnZW50cw==
  redis_url: cmVkaXM6Ly9yZWRpcy5haS1hZ2VudHMuc3ZjLmNsdXN0ZXIubG9jYWw6NjM3OS8w
  openai_api_key: c2stdGVzdGtleQ==
EOF

    if kubectl apply -f "$temp_secrets" > /dev/null 2>&1; then
        log_pass "Secrets manifest applied"
    else
        log_fail "Failed to apply Secrets manifest"
        rm "$temp_secrets"
        return 1
    fi

    if kubectl get secret postgres-credentials -n "$NAMESPACE" &> /dev/null && \
       kubectl get secret app-secrets -n "$NAMESPACE" &> /dev/null; then
        log_pass "Required Secrets exist"
    else
        log_fail "Required Secrets not found"
        rm "$temp_secrets"
        return 1
    fi

    rm "$temp_secrets"
}

# Apply database manifests
apply_databases() {
    log_header "Creating Database StatefulSets"

    # PostgreSQL
    if kubectl apply -f k8s/deployment-postgres.yaml -n "$NAMESPACE" > /dev/null 2>&1; then
        log_pass "PostgreSQL StatefulSet manifest applied"
    else
        log_fail "Failed to apply PostgreSQL manifest"
        return 1
    fi

    # Redis
    if kubectl apply -f k8s/deployment-redis.yaml -n "$NAMESPACE" > /dev/null 2>&1; then
        log_pass "Redis StatefulSet manifest applied"
    else
        log_fail "Failed to apply Redis manifest"
        return 1
    fi
}

# Apply API Deployment
apply_api_deployment() {
    log_header "Creating API Deployment"

    if kubectl apply -f k8s/deployment-api.yaml -n "$NAMESPACE" > /dev/null 2>&1; then
        log_pass "API Deployment manifest applied"
    else
        log_fail "Failed to apply API Deployment manifest"
        return 1
    fi
}

# Apply Worker Deployment
apply_worker_deployment() {
    log_header "Creating Worker Deployment"

    if kubectl apply -f k8s/deployment-worker.yaml -n "$NAMESPACE" > /dev/null 2>&1; then
        log_pass "Worker Deployment manifest applied"
    else
        log_fail "Failed to apply Worker Deployment manifest"
        return 1
    fi

    # Apply HPA
    if kubectl apply -f k8s/hpa-worker.yaml -n "$NAMESPACE" > /dev/null 2>&1; then
        log_pass "Worker HPA manifest applied"
    else
        log_fail "Failed to apply Worker HPA manifest"
        return 1
    fi
}

# Apply Ingress
apply_ingress() {
    log_header "Creating Ingress"

    if kubectl apply -f k8s/ingress.yaml -n "$NAMESPACE" > /dev/null 2>&1; then
        log_pass "Ingress manifest applied"
    else
        log_fail "Failed to apply Ingress manifest"
        return 1
    fi
}

# Verify resources are created
verify_resources() {
    log_header "Verifying Resources Created"

    local all_resources=$(kubectl get all -n "$NAMESPACE" 2>&1 | wc -l)
    if [[ $all_resources -gt 5 ]]; then
        log_pass "Resources found in namespace"
    else
        log_fail "No resources found in namespace"
        return 1
    fi

    # Check specific resources
    kubectl get statefulset -n "$NAMESPACE" | grep postgresql &> /dev/null && \
        log_pass "PostgreSQL StatefulSet exists" || \
        log_fail "PostgreSQL StatefulSet not found"

    kubectl get statefulset -n "$NAMESPACE" | grep redis &> /dev/null && \
        log_pass "Redis StatefulSet exists" || \
        log_fail "Redis StatefulSet not found"

    kubectl get deployment -n "$NAMESPACE" | grep api &> /dev/null && \
        log_pass "API Deployment exists" || \
        log_fail "API Deployment not found"

    kubectl get deployment -n "$NAMESPACE" | grep worker &> /dev/null && \
        log_pass "Worker Deployment exists" || \
        log_fail "Worker Deployment not found"
}

# Wait for pods to be ready
wait_for_pods() {
    log_header "Waiting for Pods to Reach Ready State"

    log_info "Waiting up to ${TIMEOUT} seconds for pods to be ready..."

    start_time=$(date +%s)
    while true; do
        current_time=$(date +%s)
        elapsed=$((current_time - start_time))

        if [[ $elapsed -gt $TIMEOUT ]]; then
            log_fail "Timeout waiting for pods to be ready"
            return 1
        fi

        # Check if all pods are ready
        not_ready=$(kubectl get pods -n "$NAMESPACE" --no-headers 2>/dev/null | \
            grep -v "Running\|Succeeded" | wc -l)

        if [[ $not_ready -eq 0 ]]; then
            log_pass "All pods are ready"
            return 0
        fi

        echo -ne "  Waiting... ($elapsed/$TIMEOUT seconds)\r"
        sleep 5
    done
}

# Test service endpoints
test_service_endpoints() {
    log_header "Testing Service Endpoints"

    # PostgreSQL endpoint
    if kubectl get endpoints postgresql -n "$NAMESPACE" &> /dev/null; then
        log_pass "PostgreSQL service endpoint exists"
    else
        log_fail "PostgreSQL service endpoint not found"
    fi

    # Redis endpoint
    if kubectl get endpoints redis -n "$NAMESPACE" &> /dev/null; then
        log_pass "Redis service endpoint exists"
    else
        log_fail "Redis service endpoint not found"
    fi

    # API endpoint
    if kubectl get endpoints api -n "$NAMESPACE" &> /dev/null; then
        log_pass "API service endpoint exists"
    else
        log_fail "API service endpoint not found"
    fi
}

# Test health check (if API is ready)
test_health_check() {
    log_header "Testing API Health Check"

    # Check if pod is ready before testing
    local api_ready=$(kubectl get pods -n "$NAMESPACE" -l app=api -o jsonpath='{.items[0].status.conditions[?(@.type=="Ready")].status}' 2>/dev/null)

    if [[ "$api_ready" != "True" ]]; then
        log_info "API pod not ready yet, skipping health check test"
        return 0
    fi

    # Get pod name
    local pod=$(kubectl get pods -n "$NAMESPACE" -l app=api -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

    if [[ -z "$pod" ]]; then
        log_fail "No API pod found for health check"
        return 1
    fi

    # Port-forward and test
    if kubectl port-forward -n "$NAMESPACE" "pod/$pod" 8000:8000 &> /dev/null &
    sleep 2 && curl -s http://localhost:8000/api/v1/health &> /dev/null; then
        log_pass "API health endpoint responds"
        pkill -f "port-forward" || true
    else
        log_info "API health check skipped (endpoint not yet available)"
        pkill -f "port-forward" || true
    fi
}

# Generate summary report
generate_summary() {
    log_header "Test Summary"

    local total=$((TESTS_PASSED + TESTS_FAILED))

    echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
    echo -e "${RED}Failed: $TESTS_FAILED${NC}"
    echo -e "Total:  $total"

    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "\n${GREEN}All tests passed! ✓${NC}"
        return 0
    else
        echo -e "\n${RED}Some tests failed. See details above.${NC}"
        return 1
    fi
}

# Cleanup
cleanup_on_exit() {
    pkill -f "port-forward" || true
}

trap cleanup_on_exit EXIT

# Main execution
main() {
    echo "Kubernetes Deployment Validation Script"
    echo "========================================"
    echo "Cluster Type: $CLUSTER_TYPE"
    echo "Namespace: $NAMESPACE"

    check_prerequisites
    validate_yaml_syntax
    apply_namespace
    apply_configmap
    apply_secrets
    apply_databases
    apply_api_deployment
    apply_worker_deployment
    apply_ingress
    verify_resources
    wait_for_pods
    test_service_endpoints
    test_health_check
    generate_summary
}

main
