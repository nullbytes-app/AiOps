#!/bin/bash

##############################################################################
# Create Kubernetes namespace for tenant isolation
# Usage: ./scripts/create-tenant-namespace.sh --tenant-id=<tenant-id>
# 
# This script provisions a new Kubernetes namespace with:
# - Namespace with tenant-specific labels
# - Resource quotas (CPU 2-4 cores, Memory 4-8Gi)
# - RBAC policies (ServiceAccount, Role, RoleBinding)
# - Network policies (default deny + explicit allows)
# - Deployments and services
##############################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
TEMPLATES_DIR="$REPO_ROOT/k8s/templates"
GENERATED_DIR="$REPO_ROOT/k8s/generated"

# Logging functions
log_info() {
  echo "[INFO] $1"
}

log_error() {
  echo "[ERROR] $1" >&2
}

log_success() {
  echo "[SUCCESS] $1"
}

# Validate tenant_id parameter
validate_tenant_id() {
  local tenant_id="$1"
  if [[ ! $tenant_id =~ ^[a-z0-9-]+$ ]]; then
    log_error "Invalid tenant_id: '$tenant_id'"
    log_error "Format must be lowercase alphanumeric with hyphens: ^[a-z0-9-]+\$"
    return 1
  fi
  if [[ ${#tenant_id} -lt 3 ]]; then
    log_error "tenant_id must be at least 3 characters"
    return 1
  fi
  return 0
}

# Parse command-line arguments
parse_args() {
  while [[ $# -gt 0 ]]; do
    case $1 in
      --tenant-id=*)
        TENANT_ID="${1#*=}"
        ;;
      --help)
        show_help
        exit 0
        ;;
      *)
        log_error "Unknown option: $1"
        show_help
        exit 1
        ;;
    esac
    shift
  done

  if [[ -z "${TENANT_ID:-}" ]]; then
    log_error "Missing required parameter: --tenant-id"
    show_help
    exit 1
  fi
}

show_help() {
  cat <<EOF
Usage: $0 --tenant-id=<tenant-id>

Options:
  --tenant-id=<id>    Tenant identifier (required, lowercase alphanumeric with hyphens)
  --help              Show this help message

Examples:
  $0 --tenant-id=acme-corp
  $0 --tenant-id=test-tenant-a
EOF
}

# Substitute template variables
substitute_template() {
  local template_file="$1"
  local output_file="$2"
  local tenant_id="$3"
  
  if [[ ! -f "$template_file" ]]; then
    log_error "Template not found: $template_file"
    return 1
  fi
  
  # Create parent directory if needed
  mkdir -p "$(dirname "$output_file")"
  
  # Perform substitution
  sed "s/{{TENANT_ID}}/$tenant_id/g" "$template_file" > "$output_file"
  log_info "Generated manifest: $output_file"
}

# Generate manifests from templates
generate_manifests() {
  local tenant_id="$1"
  local output_dir="$GENERATED_DIR/$tenant_id"
  
  log_info "Generating manifests for tenant: $tenant_id"
  mkdir -p "$output_dir"
  
  # Generate all manifests
  local templates=(
    "namespace-template.yaml:namespace.yaml"
    "resourcequota-template.yaml:resourcequota.yaml"
    "serviceaccount-template.yaml:serviceaccount.yaml"
    "role-template.yaml:role.yaml"
    "rolebinding-template.yaml:rolebinding.yaml"
    "networkpolicy-deny-all-template.yaml:networkpolicy-deny-all.yaml"
    "networkpolicy-allow-ingress-nginx-template.yaml:networkpolicy-allow-ingress.yaml"
    "networkpolicy-allow-egress-template.yaml:networkpolicy-allow-egress.yaml"
  )
  
  for template_spec in "${templates[@]}"; do
    IFS=':' read -r template_file output_file <<< "$template_spec"
    substitute_template "$TEMPLATES_DIR/$template_file" "$output_dir/$output_file" "$tenant_id"
  done
  
  log_success "Manifests generated in: $output_dir"
}

# Check if namespace already exists
namespace_exists() {
  local namespace="$1"
  kubectl get namespace "$namespace" &>/dev/null
}

# Apply manifests to cluster
apply_manifests() {
  local tenant_id="$1"
  local namespace="ai-agents-$tenant_id"
  local manifest_dir="$GENERATED_DIR/$tenant_id"
  
  log_info "Applying manifests to Kubernetes cluster..."
  
  # Check cluster accessibility
  if ! kubectl cluster-info &>/dev/null; then
    log_error "Cannot access Kubernetes cluster. Ensure kubectl is configured."
    return 1
  fi
  
  # Check if namespace exists
  if namespace_exists "$namespace"; then
    log_info "Namespace '$namespace' already exists (idempotent)"
  else
    log_info "Creating namespace: $namespace"
    kubectl apply -f "$manifest_dir/namespace.yaml"
  fi
  
  # Apply resource quota (before deployments)
  log_info "Applying resource quota..."
  kubectl apply -f "$manifest_dir/resourcequota.yaml"
  
  # Apply RBAC resources
  log_info "Applying RBAC (ServiceAccount, Role, RoleBinding)..."
  kubectl apply -f "$manifest_dir/serviceaccount.yaml"
  kubectl apply -f "$manifest_dir/role.yaml"
  kubectl apply -f "$manifest_dir/rolebinding.yaml"
  
  # Apply network policies
  log_info "Applying network policies..."
  kubectl apply -f "$manifest_dir/networkpolicy-deny-all.yaml"
  kubectl apply -f "$manifest_dir/networkpolicy-allow-ingress.yaml"
  kubectl apply -f "$manifest_dir/networkpolicy-allow-egress.yaml"
  
  log_success "Manifests applied successfully"
}

# Validate namespace creation
validate_namespace() {
  local tenant_id="$1"
  local namespace="ai-agents-$tenant_id"
  
  log_info "Validating namespace provisioning..."
  
  # Check namespace exists
  if ! kubectl get namespace "$namespace" &>/dev/null; then
    log_error "Namespace not found: $namespace"
    return 1
  fi
  
  # Check labels
  local labels=$(kubectl get namespace "$namespace" -o jsonpath='{.metadata.labels}')
  log_info "Namespace labels: $labels"
  
  # Check resource quota
  if kubectl get resourcequota -n "$namespace" &>/dev/null; then
    log_success "Resource quota configured"
  fi
  
  # Check RBAC
  if kubectl get serviceaccount "sa-$tenant_id" -n "$namespace" &>/dev/null; then
    log_success "ServiceAccount created: sa-$tenant_id"
  fi
  
  # Check network policies
  local np_count=$(kubectl get networkpolicy -n "$namespace" --no-headers | wc -l)
  log_success "Network policies configured: $np_count policies"
  
  log_success "Namespace validation completed: $namespace"
}

# Main execution
main() {
  local TENANT_ID=""
  
  # Parse arguments
  parse_args "$@"
  
  # Validate tenant ID
  if ! validate_tenant_id "$TENANT_ID"; then
    exit 1
  fi
  
  log_info "Starting namespace provisioning for tenant: $TENANT_ID"
  
  # Generate manifests
  if ! generate_manifests "$TENANT_ID"; then
    log_error "Failed to generate manifests"
    exit 1
  fi
  
  # Apply manifests
  if ! apply_manifests "$TENANT_ID"; then
    log_error "Failed to apply manifests"
    exit 1
  fi
  
  # Validate
  if ! validate_namespace "$TENANT_ID"; then
    log_error "Namespace validation failed"
    exit 1
  fi
  
  log_success "Tenant namespace provisioning completed successfully"
  log_info "Namespace: ai-agents-$TENANT_ID"
  
  exit 0
}

# Run main function
main "$@"
