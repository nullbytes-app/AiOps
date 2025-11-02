# Kubernetes Deployment Guide

This guide provides step-by-step instructions for deploying the AI Agents platform to Kubernetes.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Detailed Deployment Steps](#detailed-deployment-steps)
4. [Secret Management](#secret-management)
5. [Scaling and Configuration](#scaling-and-configuration)
6. [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)
7. [Cleanup](#cleanup)
8. [Production Deployment](#production-deployment)

## Prerequisites

Before deploying to Kubernetes, ensure you have:

### Required Tools

- **kubectl** (v1.28+): Kubernetes command-line tool
  - Installation: https://kubernetes.io/docs/tasks/tools/
  - Verify: `kubectl version --client`

- **Docker**: Container runtime (for building custom images)
  - Installation: https://docs.docker.com/get-docker/
  - Verify: `docker --version`

### Local Kubernetes Cluster (Development)

Choose one of the following:

#### Option 1: Minikube (Recommended for macOS/Linux)

```bash
# Install minikube
brew install minikube  # macOS
# or download from https://minikube.sigs.k8s.io/docs/start/

# Start cluster
minikube start --cpus=4 --memory=8192 --disk-size=40g

# Verify
kubectl cluster-info
```

#### Option 2: Kind (Recommended for Linux)

```bash
# Install kind
brew install kind  # macOS
# or download from https://kind.sigs.k8s.io/

# Create cluster
kind create cluster --name ai-agents

# Verify
kubectl cluster-info --context kind-ai-agents
```

#### Option 3: Cloud Kubernetes (Production)

- **AWS EKS**: https://aws.amazon.com/eks/
- **Google GKE**: https://cloud.google.com/kubernetes-engine
- **Azure AKS**: https://azure.microsoft.com/en-us/products/kubernetes-service/

### Container Registry (for custom images)

For local development, Docker's local registry is sufficient. For production, use:

- Docker Hub: https://hub.docker.com/
- AWS ECR: https://aws.amazon.com/ecr/
- Google Artifact Registry: https://cloud.google.com/artifact-registry
- Azure Container Registry: https://azure.microsoft.com/en-us/products/container-registry/

## Quick Start

Deploy all components with automated validation:

```bash
# Navigate to project root
cd /path/to/ai-agents

# Run automated deployment script
./k8s/test-deployment.sh

# Expected output:
# ✓ All tests passed
# ✓ Namespace created
# ✓ ConfigMap created
# ✓ Secrets created
# ✓ PostgreSQL StatefulSet created
# ✓ Redis StatefulSet created
# ✓ API Deployment created
# ✓ Worker Deployment created
# ✓ All pods Running and Ready

# Verify deployment
kubectl get all -n ai-agents

# Access API
kubectl port-forward -n ai-agents svc/api 8000:8000
curl http://localhost:8000/api/v1/health
```

## Detailed Deployment Steps

### Step 1: Create Namespace

The namespace logically groups all AI Agents components.

```bash
kubectl apply -f k8s/namespace.yaml

# Verify
kubectl get namespaces
kubectl describe namespace ai-agents
```

### Step 2: Create Non-Sensitive Configuration (ConfigMap)

```bash
kubectl apply -f k8s/configmap.yaml -n ai-agents

# Verify
kubectl get configmap -n ai-agents
kubectl describe configmap app-config -n ai-agents
```

### Step 3: Configure Secrets

**IMPORTANT: Never commit actual secrets to git**

```bash
# Copy template
cp k8s/secrets.yaml.example k8s/secrets.yaml

# Edit with your actual values
nano k8s/secrets.yaml
# or
vi k8s/secrets.yaml

# Apply
kubectl apply -f k8s/secrets.yaml -n ai-agents

# Verify (does not show values)
kubectl get secrets -n ai-agents
```

**Encoding secrets:**

```bash
# PostgreSQL password
echo -n "your-secure-password" | base64
# Output: eW91ci1zZWN1cmUtcGFzc3dvcmQ=

# Database URL
echo -n "postgresql://postgres:password@postgresql.ai-agents.svc.cluster.local:5432/ai_agents" | base64

# Redis URL
echo -n "redis://redis.ai-agents.svc.cluster.local:6379/0" | base64

# OpenAI API Key (when available)
echo -n "sk-xxxxxxxxxxxxx" | base64
```

### Step 4: Deploy PostgreSQL

```bash
kubectl apply -f k8s/deployment-postgres.yaml -n ai-agents

# Monitor startup (may take 1-2 minutes)
kubectl get pods -n ai-agents -l app=postgresql -w
# Wait until: postgresql-0   1/1   Running

# Verify connectivity
kubectl exec -it postgresql-0 -n ai-agents -- pg_isready
# Output: accepting connections
```

### Step 5: Deploy Redis

```bash
kubectl apply -f k8s/deployment-redis.yaml -n ai-agents

# Monitor startup
kubectl get pods -n ai-agents -l app=redis -w
# Wait until: redis-0   1/1   Running

# Verify connectivity
kubectl exec -it redis-0 -n ai-agents -- redis-cli ping
# Output: PONG
```

### Step 6: Deploy API

```bash
kubectl apply -f k8s/deployment-api.yaml -n ai-agents

# Monitor deployment
kubectl get deployment -n ai-agents
kubectl describe deployment api -n ai-agents

# Watch pods reach Ready
kubectl get pods -n ai-agents -l app=api -w
# Wait until: api-xxxxx   1/1   Running
```

### Step 7: Deploy Workers

```bash
# Deploy worker deployment
kubectl apply -f k8s/deployment-worker.yaml -n ai-agents

# Deploy HPA (requires metrics-server for CPU metrics)
kubectl apply -f k8s/hpa-worker.yaml -n ai-agents

# Verify deployment
kubectl get deployment -n ai-agents
kubectl get hpa -n ai-agents
```

### Step 8: Deploy Ingress

```bash
# First, install NGINX Ingress Controller (if using minikube/kind)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.0/deploy/static/provider/kind/deploy.yaml

# Wait for ingress controller to be ready
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s

# Deploy ingress
kubectl apply -f k8s/ingress.yaml -n ai-agents

# Verify
kubectl get ingress -n ai-agents
```

## Secret Management

### Safe Secret Practices

1. **Never commit `secrets.yaml`** - Add to `.gitignore`:
   ```bash
   echo "k8s/secrets.yaml" >> .gitignore
   ```

2. **Rotate secrets regularly** - Update base64-encoded values:
   ```bash
   # Update single secret
   kubectl create secret generic app-secrets \
     --from-literal=database_url="..." \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

3. **Use Secret management tools** (Production):
   - HashiCorp Vault
   - AWS Secrets Manager
   - Google Secret Manager
   - Azure Key Vault

### Accessing Secrets from Pods

Secrets are mounted as environment variables:

```bash
# View secret in pod
kubectl exec -it api-xxxxx -n ai-agents -- env | grep DATABASE_URL

# View secret content (risky - for debugging only)
kubectl get secret app-secrets -n ai-agents -o jsonpath='{.data.database_url}' | base64 --decode
```

## Scaling and Configuration

### Adjust Resource Limits

Edit deployment files and update resource requests/limits:

```yaml
resources:
  requests:
    cpu: 250m
    memory: 512Mi
  limits:
    cpu: 500m
    memory: 1Gi
```

Then apply:

```bash
kubectl apply -f k8s/deployment-api.yaml -n ai-agents
```

### Horizontal Pod Autoscaling (HPA)

Current HPA scales workers based on CPU utilization:

```bash
# View current HPA status
kubectl get hpa worker-hpa -n ai-agents
kubectl describe hpa worker-hpa -n ai-agents

# Adjust scaling parameters
kubectl patch hpa worker-hpa -n ai-agents -p '{"spec":{"maxReplicas":15}}'

# Manual scaling (disables HPA)
kubectl scale deployment worker --replicas=5 -n ai-agents
```

### Change Replica Count

```bash
# API deployment
kubectl scale deployment api --replicas=3 -n ai-agents

# Worker deployment
kubectl scale deployment worker --replicas=4 -n ai-agents
```

### Update Configuration (ConfigMap)

```bash
# Edit ConfigMap
kubectl edit configmap app-config -n ai-agents

# Or replace entirely
kubectl apply -f k8s/configmap.yaml -n ai-agents

# Restart pods to pick up changes
kubectl rollout restart deployment api -n ai-agents
kubectl rollout restart deployment worker -n ai-agents
```

## Monitoring and Troubleshooting

### View Logs

```bash
# API logs
kubectl logs -n ai-agents deployment/api
kubectl logs -n ai-agents deployment/api --tail=100  # Last 100 lines
kubectl logs -n ai-agents deployment/api -f          # Follow logs

# Worker logs
kubectl logs -n ai-agents deployment/worker

# Specific pod
kubectl logs -n ai-agents api-xxxxx
```

### Check Pod Status

```bash
# List all pods
kubectl get pods -n ai-agents

# Detailed pod info
kubectl describe pod api-xxxxx -n ai-agents

# Pod events
kubectl describe pod api-xxxxx -n ai-agents | grep -A 20 Events:

# Check pod startup failures
kubectl get events -n ai-agents --sort-by='.lastTimestamp'
```

### Common Issues and Solutions

#### Issue: Pods stuck in Pending state

```bash
# Check why pod can't be scheduled
kubectl describe pod postgresql-0 -n ai-agents

# Common causes:
# - Not enough cluster resources
# - PersistentVolume not available
# - Image pull failures

# Solution - add resources or reduce pod count
minikube ssh  # For minikube
docker ps     # Check container status
```

#### Issue: ImagePullBackOff

```bash
# Image not found or pull error
kubectl describe pod api-xxxxx -n ai-agents

# Solution - build and tag image correctly
docker build -t ai-agents-api:latest .
# For minikube, load image into cluster
minikube image load ai-agents-api:latest
```

#### Issue: Database connection errors

```bash
# Check PostgreSQL health
kubectl exec -it postgresql-0 -n ai-agents -- pg_isready

# Check PostgreSQL logs
kubectl logs -n ai-agents postgresql-0

# Verify Secret is correct
kubectl get secret app-secrets -n ai-agents -o jsonpath='{.data.database_url}' | base64 --decode
```

#### Issue: Redis connection errors

```bash
# Check Redis health
kubectl exec -it redis-0 -n ai-agents -- redis-cli ping

# Check Redis logs
kubectl logs -n ai-agents redis-0

# Verify Redis URL in Secrets
kubectl get secret app-secrets -n ai-agents -o jsonpath='{.data.redis_url}' | base64 --decode
```

### Exec into Containers

```bash
# Bash shell in API pod
kubectl exec -it -n ai-agents deployment/api -- /bin/bash

# Python interpreter
kubectl exec -it -n ai-agents deployment/api -- python

# Run command
kubectl exec -n ai-agents deployment/api -- pip list
```

### Port Forward for Local Testing

```bash
# API (port 8000)
kubectl port-forward -n ai-agents svc/api 8000:80

# PostgreSQL (port 5432)
kubectl port-forward -n ai-agents svc/postgresql 5432:5432

# Redis (port 6379)
kubectl port-forward -n ai-agents svc/redis 6379:6379

# In another terminal:
curl http://localhost:8000/api/v1/health
psql -h localhost -U postgres -d ai_agents
redis-cli -p 6379
```

## Cleanup

### Delete All Resources

```bash
# Delete everything in namespace (including PVCs)
kubectl delete namespace ai-agents

# Or delete specific resources
kubectl delete deployment -n ai-agents --all
kubectl delete statefulset -n ai-agents --all
kubectl delete service -n ai-agents --all
kubectl delete pvc -n ai-agents --all
kubectl delete configmap -n ai-agents --all
kubectl delete secret -n ai-agents --all
```

### Stop Local Cluster

```bash
# Minikube
minikube stop
minikube delete  # Complete removal

# Kind
kind delete cluster --name ai-agents
```

## Production Deployment

### Pre-Production Checklist

- [ ] Update image tags from `latest` to specific versions
- [ ] Configure production secrets (API keys, database passwords)
- [ ] Set environment to `production` in ConfigMap
- [ ] Enable TLS/HTTPS in Ingress with certificate
- [ ] Configure DNS records pointing to ingress
- [ ] Set appropriate resource limits for production workload
- [ ] Configure monitoring (Prometheus, Grafana)
- [ ] Configure backup strategy for PostgreSQL
- [ ] Set up alerting rules
- [ ] Document runbooks for common issues
- [ ] Conduct load testing

### Recommended Production Enhancements

1. **High Availability**
   - PostgreSQL: Multi-replica setup with read replicas
   - Redis: Redis Sentinel or Cluster mode
   - API: 3+ replicas with pod disruption budgets
   - Workers: Auto-scaling based on queue depth

2. **Security**
   - Network policies to restrict pod communication
   - RBAC for fine-grained access control
   - Pod security policies
   - Secrets encryption at rest
   - Service mesh (Istio) for mTLS

3. **Operations**
   - Cluster autoscaling for dynamic capacity
   - Persistent volume backups
   - Log aggregation (ELK, Loki)
   - Centralized monitoring (Prometheus + Grafana)
   - GitOps workflow (ArgoCD, Flux)

4. **Cost Optimization**
   - Resource requests/limits tuning
   - Spot instances for workers
   - Cluster right-sizing
   - Reserved capacity discounts

### Production-Ready Resources

- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
- [Security Hardening](https://kubernetes.io/docs/concepts/security/)
- [Production Cluster Setup](https://kubernetes.io/docs/setup/production-environment/)

## References

- [Kubernetes Official Documentation](https://kubernetes.io/docs/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
- [AI Agents Architecture](./architecture.md)
- [Tech Specification](./tech-spec-epic-1.md)
- [Docker Configuration](./docker-compose.yml)
