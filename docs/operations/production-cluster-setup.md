# Production Kubernetes Cluster Setup Guide

**Story:** 5.1 - Provision Production Kubernetes Cluster
**Status:** Implementation Complete
**Last Updated:** 2025-11-03
**Author:** Development Team (Amelia - Senior Implementation Engineer)

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Cloud Provider Selection](#cloud-provider-selection)
5. [Infrastructure Provisioning](#infrastructure-provisioning)
6. [Cluster Verification](#cluster-verification)
7. [Database Configuration](#database-configuration)
8. [Cache Configuration](#cache-configuration)
9. [Ingress and TLS Setup](#ingress-and-tls-setup)
10. [Monitoring Integration](#monitoring-integration)
11. [Security Verification](#security-verification)
12. [Troubleshooting](#troubleshooting)
13. [Recovery Procedures](#recovery-procedures)

---

## Overview

This guide documents the provisioning and operation of the AI Agents production Kubernetes cluster. The infrastructure consists of:

- **Container Orchestration:** AWS EKS (Elastic Kubernetes Service) - managed Kubernetes
- **Compute:** Auto-scaling worker nodes across 3+ availability zones (HA)
- **Storage:** Managed PostgreSQL (RDS) for persistent data
- **Caching:** Managed Redis (ElastiCache) for message queue and session data
- **Ingress:** Nginx Ingress Controller with automatic TLS via Let's Encrypt
- **Monitoring:** CloudWatch/Prometheus integration for observability

**Key Requirements Addressed:**
- AC1: Cloud Provider Cluster Provisioned with HA
- AC2: Cluster Configuration with auto-scaling, network policies, RBAC
- AC3: Managed PostgreSQL with backups, encryption, failover
- AC4: Managed Redis with persistence, replication
- AC5: Ingress Controller with TLS certificates
- AC6: Cloud Monitoring Integration
- AC7: Infrastructure as Code with Terraform

---

## Architecture

### High-Level Diagram

```
┌─────────────────────────────────────────────────────────┐
│                     AWS Region (us-east-1)               │
│                                                           │
│  ┌──────────────────────────────────────────────────┐  │
│  │          VPC (10.0.0.0/16)                       │  │
│  │                                                   │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │  │
│  │  │   AZ-1a    │  │   AZ-1b     │  │   AZ-1c    │ │  │
│  │  │            │  │             │  │            │ │  │
│  │  │ ┌────────┐ │  │ ┌────────┐ │  │ ┌────────┐ │ │  │
│  │  │ │ EKS    │ │  │ │ EKS    │ │  │ │ EKS    │ │ │  │
│  │  │ │ Node   │ │  │ │ Node   │ │  │ │ Node   │ │ │  │
│  │  │ └────────┘ │  │ └────────┘ │  │ └────────┘ │ │  │
│  │  │            │  │             │  │            │ │  │
│  │  └─────────────┘  └─────────────┘  └────────────┘ │  │
│  │         ↓                ↓                 ↓        │  │
│  │  ┌────────────────────────────────────────────┐   │  │
│  │  │   EKS Control Plane (Managed by AWS)       │   │  │
│  │  │   - API Server                             │   │  │
│  │  │   - etcd, Scheduler, Controllers           │   │  │
│  │  │   - Multi-AZ redundancy                    │   │  │
│  │  └────────────────────────────────────────────┘   │  │
│  │                                                   │  │
│  │  ┌────────────────────────────────────────────┐   │  │
│  │  │   Managed Services (Same VPC)              │   │  │
│  │  │  ┌──────────────────────────────────────┐ │   │  │
│  │  │  │ RDS PostgreSQL (Multi-AZ)            │ │   │  │
│  │  │  │ - Primary + Standby                  │ │   │  │
│  │  │  │ - Automated failover                 │ │   │  │
│  │  │  │ - 30-day backup retention            │ │   │  │
│  │  │  └──────────────────────────────────────┘ │   │  │
│  │  │  ┌──────────────────────────────────────┐ │   │  │
│  │  │  │ ElastiCache Redis (Multi-AZ)         │ │   │  │
│  │  │  │ - Primary + Replica                  │ │   │  │
│  │  │  │ - RDB persistence                    │ │   │  │
│  │  │  │ - Automatic failover                 │ │   │  │
│  │  │  └──────────────────────────────────────┘ │   │  │
│  │  └────────────────────────────────────────────┘   │  │
│  │                                                   │  │
│  │  ┌────────────────────────────────────────────┐   │  │
│  │  │   Ingress & Load Balancing                │   │  │
│  │  │  - Nginx Ingress Controller (NLB)         │   │  │
│  │  │  - cert-manager (Let's Encrypt ACME)      │   │  │
│  │  │  - TLS termination                        │   │  │
│  │  └────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │   CloudWatch Monitoring                          │  │
│  │   - Cluster logs (API, audit, controllers)       │  │
│  │   - Application logs (container output)          │  │
│  │   - 90-day retention for compliance              │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
└─────────────────────────────────────────────────────────┘
```

### Network Isolation

- **Public Subnets:** Ingress controllers, NAT gateways (1 per AZ)
- **Private Subnets:** EKS worker nodes (1 per AZ)
- **Database Subnets:** RDS instances (1 per AZ)
- **Cache Subnets:** ElastiCache instances (1 per AZ)

### Security Groups

- **Cluster SG:** EKS control plane (ingress 443, egress all)
- **Node SG:** Worker nodes (pod-to-pod 0-65535, control plane access)
- **RDS SG:** PostgreSQL (ingress 5432 from nodes, egress all)
- **Cache SG:** Redis (ingress 6379 from nodes, egress all)

---

## Prerequisites

### Required Tools

```bash
# Terraform for Infrastructure as Code
terraform version  # Should be >= 1.0

# AWS CLI for cloud operations
aws --version      # Should be >= 2.13

# kubectl for Kubernetes management
kubectl version    # Should be >= 1.28

# Helm for package management
helm version       # Should be >= 3.0
```

### AWS Account Setup

1. **IAM Permissions** - User/role must have:
   ```
   - ec2:*
   - eks:*
   - rds:*
   - elasticache:*
   - iam:*
   - cloudwatch:*
   - logs:*
   - kms:*
   ```

2. **AWS Credentials** - Configure credentials:
   ```bash
   aws configure
   # Or set environment variables:
   export AWS_ACCESS_KEY_ID=...
   export AWS_SECRET_ACCESS_KEY=...
   export AWS_DEFAULT_REGION=us-east-1
   ```

3. **VPC Capacity** - Ensure VPC has space for:
   - 3 public subnets (/24)
   - 3 private subnets (/24)
   - 3 database subnets (/24)
   - 3 cache subnets (/24)

---

## Cloud Provider Selection

### AWS EKS (Selected)

**Rationale:**
- Mature Kubernetes service (launched 2018)
- Extensive Terraform module support
- Strong ecosystem and community patterns
- Compatible with team's AWS infrastructure experience
- Managed control plane reduces operational burden

**Characteristics:**
- Automatic control plane updates and patching
- Multi-AZ control plane for HA
- Integration with AWS IAM for authentication
- VPC networking for fine-grained security
- CloudWatch integration for logging/monitoring

### Alternative Providers

For **GCP GKE:**
- Modify `main.tf`: Use `google` provider
- Use `google_container_cluster` resource
- Update variables for GCP regions/zones
- See: `terraform/aws-example.tfvars` structure

For **Azure AKS:**
- Modify `main.tf`: Use `azurerm` provider
- Use `azurerm_kubernetes_cluster` resource
- Update variables for Azure resource groups
- Consider `azure-config.tfvars`

---

## Infrastructure Provisioning

### Step 1: Clone and Prepare

```bash
# Navigate to infrastructure directory
cd infrastructure/terraform

# Copy example configuration
cp terraform.tfvars.example terraform.tfvars

# Edit with actual values
nano terraform.tfvars  # Or vim/your editor
```

### Step 2: Edit terraform.tfvars

**Critical Settings:**

```hcl
# Cluster identification
cluster_name          = "ai-agents-prod"
aws_region           = "us-east-1"

# Database credentials (use strong password!)
db_password          = "GenerateStrongPassword123!@#"
db_username          = "aiagents_admin"

# TLS certificates
letsencrypt_email    = "devops@company.com"

# Resource sizing
db_instance_class    = "db.t3.medium"    # Start here, scale up if needed
cache_node_type      = "cache.t3.small"  # Start here
node_instance_types  = ["t3.large"]      # For app pods
```

### Step 3: Initialize Terraform

```bash
# Initialize working directory (downloads providers)
terraform init

# Validate configuration
terraform validate

# Review planned changes (IMPORTANT!)
terraform plan -out=tfplan

# Display specific resources
terraform plan -out=tfplan | grep -E "aws_eks|aws_db|aws_elasticache"
```

### Step 4: Apply Infrastructure

```bash
# Apply the plan (creates all resources)
terraform apply tfplan

# This will take 15-20 minutes:
# 1. VPC and networking: 1 min
# 2. EKS cluster: 10-12 min
# 3. Node groups: 5-7 min
# 4. RDS instance: 10+ min (parallel)
# 5. ElastiCache: 5-7 min (parallel)

# Monitor progress
watch -n 10 'terraform show | grep -E "status|state"'
```

### Step 5: Capture Outputs

```bash
# Display all outputs (save for reference)
terraform output

# Save specific values
CLUSTER_ENDPOINT=$(terraform output -raw cluster_endpoint)
CLUSTER_CA=$(terraform output -raw cluster_ca_certificate)
RDS_ENDPOINT=$(terraform output -raw rds_endpoint)
REDIS_ENDPOINT=$(terraform output -raw elasticache_endpoint)

# Display instructions for next steps
terraform output next_steps
```

---

## Cluster Verification

### Step 1: Configure kubectl

```bash
# Update kubeconfig (from terraform outputs)
aws eks update-kubeconfig \
  --region us-east-1 \
  --name ai-agents-prod

# Verify connection
kubectl cluster-info

# Expected output:
# Kubernetes control plane is running at https://...
# CoreDNS is running at https://...
```

### Step 2: Verify Node Readiness

```bash
# List nodes (should show 3 Ready nodes)
kubectl get nodes

# Expected output (AC2 verification):
# NAME                            STATUS   ROLES    AGE     VERSION
# ip-10-0-1-123.ec2.internal     Ready    <none>   5m30s   v1.29.0
# ip-10-0-2-234.ec2.internal     Ready    <none>   5m45s   v1.29.0
# ip-10-0-3-45.ec2.internal      Ready    <none>   6m15s   v1.29.0

# Verify nodes span availability zones
kubectl get nodes -L topology.kubernetes.io/zone

# All three AZs should be represented (AC1 - HA requirement)
```

### Step 3: Verify Cluster Health

```bash
# System pods should be running
kubectl get pods -n kube-system

# Expected pods:
# - aws-node (CNI plugin)
# - kube-dns/coredns (DNS)
# - kube-proxy (networking)

# Check control plane logs
aws logs describe-log-groups --log-group-name-prefix /aws/eks/ai-agents-prod

# View API server logs
aws logs tail /aws/eks/ai-agents-prod/cluster --follow --max-items 10
```

### Step 4: Verify Ingress Controller

```bash
# Check ingress-nginx namespace
kubectl get pods -n ingress-nginx

# Wait for ingress controller to have external IP
kubectl get svc -n ingress-nginx -w

# Should show:
# NAME                            TYPE           CLUSTER-IP      EXTERNAL-IP
# ingress-nginx-controller        LoadBalancer   10.100.x.x      example-nlb.elb.amazonaws.com
```

### Step 5: Verify Cert-Manager

```bash
# Check cert-manager namespace
kubectl get pods -n cert-manager

# Verify ACME ClusterIssuers exist
kubectl get clusterissuer

# Should show:
# NAME                      READY   AGE
# letsencrypt-staging      True    3m
# letsencrypt-prod         True    3m
```

---

## Database Configuration

### PostgreSQL Setup (AC3)

#### Verify Connectivity

```bash
# Create test pod
kubectl run psql-test --image=postgres:16 -it --rm -- bash

# Inside pod, connect to database
psql -h <RDS_ENDPOINT> \
     -U aiagents_admin \
     -d aiagents \
     -c "SELECT version();"

# Expected output shows PostgreSQL 16.x version
```

#### Enable Row-Level Security (AC3)

```bash
# Connect to database
psql -h <RDS_ENDPOINT> -U aiagents_admin -d aiagents

# Create RLS policy table
CREATE TABLE tenants (
  tenant_id UUID PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tenant_data (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
  data JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

# Enable RLS
ALTER TABLE tenant_data ENABLE ROW LEVEL SECURITY;

# Create RLS policy
CREATE POLICY tenant_isolation ON tenant_data
  USING (tenant_id = current_setting('app.current_tenant_id')::UUID);

# Test RLS enforcement
SET app.current_tenant_id = 'tenant-1-uuid';
SELECT * FROM tenant_data;  -- Only shows tenant-1 data
```

#### Verify Backups

```bash
# Check backup configuration
aws rds describe-db-instances \
  --db-instance-identifier ai-agents-prod-postgres \
  --query 'DBInstances[0].[BackupRetentionPeriod,PreferredBackupWindow]'

# Expected: 30 days retention, scheduled backup window

# List recent backups
aws rds describe-db-snapshots \
  --db-instance-identifier ai-agents-prod-postgres \
  --query 'DBSnapshots[*].[DBSnapshotIdentifier,SnapshotCreateTime,Status]'
```

---

## Cache Configuration

### Redis Setup (AC4)

#### Verify Connectivity

```bash
# Create test pod
kubectl run redis-test --image=redis:7 -it --rm -- bash

# Inside pod, connect to cache
redis-cli -h <REDIS_ENDPOINT> \
          --pass <PASSWORD> \
          PING

# Expected: PONG response
```

#### Verify Persistence

```bash
# Check persistence configuration
aws elasticache describe-replication-groups \
  --replication-group-id ai-agents-prod-redis \
  --query 'ReplicationGroups[0].SnapshotRetentionLimit'

# Expected: 5 (days)

# Check snapshot schedule
aws elasticache describe-replication-groups \
  --replication-group-id ai-agents-prod-redis \
  --query 'ReplicationGroups[0].SnapshotWindow'

# Expected: 03:00-05:00 (UTC)
```

#### Verify Replication

```bash
# Connect to Redis
redis-cli -h <REDIS_ENDPOINT> --pass <PASSWORD>

# Check replication info
INFO replication

# Expected:
# role:primary
# connected_slaves:1
# slave0:ip=...,port=6379,state=online
```

---

## Ingress and TLS Setup

### Configure DNS

```bash
# Get ingress NLB endpoint
INGRESS_NLB=$(kubectl get svc -n ingress-nginx ingress-nginx-controller \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo "Point your domain to: $INGRESS_NLB"

# Example DNS record:
# Type: CNAME
# Name: example.com
# Value: <INGRESS_NLB>

# Verify DNS resolution
dig example.com
```

### Create Ingress Resource

```bash
# Create application ingress with TLS
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  namespace: production
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - example.com
    secretName: app-tls-cert
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: app-service
            port:
              number: 8000
EOF
```

### Verify TLS Certificate

```bash
# Wait for certificate issuance (1-2 minutes)
kubectl get certificate -n production -w

# Check certificate details
kubectl get certificate app-tls-cert -n production -o yaml

# Verify HTTPS endpoint
curl -I https://example.com

# Expected: HTTP/2 200 with valid cert
```

---

## Monitoring Integration

### CloudWatch Logs (AC6)

```bash
# Verify log groups created
aws logs describe-log-groups --log-group-name-prefix /aws/eks/

# View API server logs
aws logs tail /aws/eks/ai-agents-prod/cluster --follow

# View audit logs
aws logs tail /aws/eks/ai-agents-prod/cluster --log-stream-name audit --follow

# Create CloudWatch Insights query
aws logs start-query \
  --log-group-name /aws/eks/ai-agents-prod/cluster \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /error/'
```

### Prometheus Integration (Epic 4 Connection - AC6)

```bash
# Deploy OpenTelemetry Collector (via Terraform)
kubectl get pods -n observability

# Verify OTEL Collector metrics
kubectl port-forward -n observability \
  svc/otel-collector 8888:8888

# Access metrics: http://localhost:8888/metrics
```

---

## Security Verification

### RBAC Verification (AC2)

```bash
# Test service account permissions
kubectl auth can-i list pods --as=system:serviceaccount:production:app-sa
# Expected: yes

kubectl auth can-i delete secrets --as=system:serviceaccount:production:app-sa
# Expected: no (least privilege)

# List all role bindings
kubectl get rolebindings -A | grep production
```

### Network Policy Verification (AC2)

```bash
# Test default deny policy
kubectl run test-client --image=nginx -it --rm -- bash

# Inside pod, try to reach other pod
curl http://other-pod:8000
# Expected: connection timeout (default deny working)

# Apply allow policy
kubectl apply -f k8s/production/network-policies.yaml

# Test connectivity after explicit allow
curl http://other-pod:8000
# Expected: connection succeeds
```

### Encryption Verification (AC3, AC4)

```bash
# Verify RDS encryption
aws rds describe-db-instances \
  --db-instance-identifier ai-agents-prod-postgres \
  --query 'DBInstances[0].StorageEncrypted'
# Expected: true

# Verify ElastiCache encryption
aws elasticache describe-replication-groups \
  --replication-group-id ai-agents-prod-redis \
  --query 'ReplicationGroups[0].[AtRestEncryptionEnabled,TransitEncryptionEnabled]'
# Expected: [true, true]
```

---

## Troubleshooting

### Nodes Not Ready

```bash
# Describe nodes
kubectl describe node <node-name>

# Check node logs
aws ec2 get-console-output --instance-id <instance-id>

# Common causes:
# - Insufficient IAM permissions
# - Security group blocking traffic
# - Missing CNI plugin
```

### Pods Pending

```bash
# Describe pod
kubectl describe pod <pod-name> -n <namespace>

# Check events
kubectl get events -n <namespace> --sort-by='.lastTimestamp'

# Common causes:
# - Insufficient resources (check resource quotas)
# - Node selectors not matching
# - Persistent volume not available
```

### Database Connection Failures

```bash
# Test from pod
kubectl run psql-debug --image=postgres:16 -it --rm -- bash

# Inside pod:
psql -h <RDS_ENDPOINT> -U aiagents_admin --connection-timeout=5

# Check RDS security group
aws ec2 describe-security-groups \
  --filter Name=tag-key,Values=Purpose Name=tag-value,Values=RDS

# Verify ingress rule allows port 5432 from node security group
```

### TLS Certificate Not Issuing

```bash
# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager -f

# Check certificate status
kubectl describe certificate app-tls-cert -n production

# Check ACME order
kubectl get orders -n production

# Common causes:
# - DNS not resolving to ingress IP
# - cert-manager ClusterIssuer not ready
# - ACME challenge failing
```

---

## Recovery Procedures

### Database Failover

```bash
# Manually trigger failover (if needed)
aws rds reboot-db-instance \
  --db-instance-identifier ai-agents-prod-postgres \
  --force-failover

# Monitor failover progress
aws rds describe-db-instances \
  --db-instance-identifier ai-agents-prod-postgres \
  --query 'DBInstances[0].DBInstanceStatus'

# Failover typically takes 1-3 minutes
```

### Cache Failover

```bash
# Trigger cache failover
aws elasticache test-failover \
  --replication-group-id ai-agents-prod-redis

# Monitor failover progress
watch -n 5 'aws elasticache describe-replication-groups \
  --replication-group-id ai-agents-prod-redis \
  --query "ReplicationGroups[0].Status"'
```

### Node Recovery

```bash
# Cordon node to prevent new pods
kubectl cordon <node-name>

# Drain pods gracefully
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# Replace node via ASG
# 1. Check Auto Scaling Group:
aws autoscaling describe-auto-scaling-groups \
  --query 'AutoScalingGroups[?Tags[?Value==`ai-agents-prod`]]'

# 2. Terminate old node (ASG will replace it):
aws ec2 terminate-instances --instance-ids <instance-id>

# 3. Uncordon when new node is ready:
kubectl uncordon <node-name>
```

---

## Maintenance Schedule

### Daily Tasks

- Monitor CloudWatch logs for errors
- Check node health status
- Verify database and cache connectivity
- Review ingress certificate expiration (auto-renewal via cert-manager)

### Weekly Tasks

- Test database backup/restore procedure
- Verify cache persistence snapshots exist
- Review autoscaling metrics and adjust if needed
- Check disk usage on nodes

### Monthly Tasks

- Test disaster recovery (infrastructure recreation from IaC)
- Review security group rules
- Update Kubernetes minor versions if available
- Audit RBAC and network policies

### Quarterly Tasks

- Full cluster health assessment
- Database parameter group review
- Cache eviction policy tuning
- Load testing to verify scaling behavior

---

## Related Documentation

- [docs/operations/README.md](./README.md) - Operational procedures index
- [docs/architecture.md](../architecture.md) - System architecture
- [infrastructure/terraform/README.md](../../infrastructure/terraform/README.md) - Terraform module documentation
- [Story 4.7: Operational Runbooks](../stories/4-7-create-operational-runbooks-and-dashboards.md) - Operations patterns

---

## Change History

| Date | Version | Changes |
|------|---------|---------|
| 2025-11-03 | 1.0 | Initial production cluster setup guide created as part of Story 5.1 implementation |

---

**Status:** Ready for Production
**Validation:** All acceptance criteria (AC1-AC7) verified
**Next Step:** Deploy application to production cluster (Story 5.2)
