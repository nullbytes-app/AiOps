# Tenant Namespace Provisioning Guide

## Overview

This guide covers provisioning Kubernetes namespaces for tenant isolation in the AI Agents platform. Each tenant gets a dedicated namespace with resource quotas, network policies, and RBAC restrictions.

## Architecture

### Soft Multi-Tenancy Model

- **Compute Isolation**: Each tenant in separate Kubernetes namespace
- **Data Isolation**: PostgreSQL row-level security (RLS) enforces data boundaries
- **Network Isolation**: NetworkPolicy blocks pod-to-pod communication across tenants
- **Resource Fairness**: ResourceQuotas prevent noisy neighbor problems
- **Access Control**: RBAC limits operations to authorized operators

## Prerequisites

1. Kubernetes cluster (1.28+) with NetworkPolicy support
2. kubectl CLI configured with cluster access
3. Tenant created in application database
4. DNS resolution working in cluster

## Quick Start

### Provision a Tenant Namespace

```bash
./scripts/create-tenant-namespace.sh --tenant-id=acme-corp
```

### Verify Namespace Creation

```bash
# List tenant namespaces
kubectl get ns -l app=ai-agents

# Check resource quota
kubectl describe resourcequota -n ai-agents-acme-corp

# Check RBAC
kubectl get sa,role,rolebinding -n ai-agents-acme-corp

# Check network policies
kubectl get networkpolicy -n ai-agents-acme-corp
```

## Resource Quotas

Each tenant namespace enforces:

| Resource | Request | Limit |
|----------|---------|-------|
| CPU | 2 cores | 4 cores |
| Memory | 4Gi | 8Gi |
| Storage | 20Gi | 20Gi |
| Pods | - | 10 max |

## RBAC and Access Control

### Tenant ServiceAccount

Each namespace has `sa-{tenant-id}` ServiceAccount that can only access its own namespace.

### Test Permissions

```bash
kubectl auth can-i list pods \
  --as=system:serviceaccount:ai-agents-acme-corp:sa-acme-corp \
  -n ai-agents-acme-corp
# Result: yes

kubectl auth can-i list pods \
  --as=system:serviceaccount:ai-agents-acme-corp:sa-acme-corp \
  -n ai-agents-other-corp
# Result: no
```

## Network Policies

Each namespace enforces:

1. **Default Deny Ingress**: All ingress blocked
2. **Allow Nginx**: Ingress from ingress-nginx on port 8000
3. **Allow Shared Services**:
   - PostgreSQL (port 5432)
   - Redis (port 6379)
   - DNS (port 53)
   - External APIs (ports 80, 443)

## Rollback / Delete

```bash
kubectl delete namespace ai-agents-{tenant-id}
rm -rf k8s/generated/{tenant-id}
```

## References

- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Resource Quotas](https://kubernetes.io/docs/concepts/policy/resource-quotas/)
- [RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
