# Production Deployment Runbook

**Story:** 5.2 - Deploy Application to Production Environment
**Created:** 2025-11-03
**Owner:** DevOps Team
**Status:** Active

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Pre-Deployment Checklist](#pre-deployment-checklist)
4. [Deployment Procedure](#deployment-procedure)
5. [Post-Deployment Validation](#post-deployment-validation)
6. [Rollback Procedure](#rollback-procedure)
7. [Troubleshooting](#troubleshooting)
8. [Common Issues](#common-issues)
9. [Monitoring and Alerts](#monitoring-and-alerts)

---

## Overview

This runbook provides step-by-step procedures for deploying the AI Agents platform to production, including:
- Building and pushing Docker images to container registry
- Applying Kubernetes manifests to production cluster
- Running database migrations
- Validating deployment with smoke tests
- Monitoring application health post-deployment

**Production Architecture:**
- **Kubernetes Cluster:** AWS EKS (3+ nodes, 3 availability zones)
- **Database:** PostgreSQL 17 (RDS Multi-AZ)
- **Cache/Queue:** Redis 7 (ElastiCache Multi-AZ)
- **Ingress:** nginx-ingress with Let's Encrypt TLS
- **Container Registry:** AWS ECR / GCR / ACR
- **Monitoring:** Prometheus + Grafana (from Epic 4)

---

## Prerequisites

### 1. Infrastructure Requirements (from Story 5.1)

Verify that the following infrastructure components are operational:

```bash
# Check production cluster connectivity
kubectl cluster-info --context production
kubectl get nodes -n production

# Verify namespace exists with RBAC/network policies
kubectl get namespace production
kubectl get serviceaccount app-sa -n production
kubectl get networkpolicies -n production

# Check ingress controller
kubectl get pods -n ingress-nginx
kubectl get svc -n ingress-nginx

# Verify cert-manager for TLS
kubectl get pods -n cert-manager
kubectl get clusterissuer letsencrypt-prod
```

### 2. Required Credentials

Ensure you have access to:
- **AWS/GCP/Azure credentials** (for EKS/GKE/AKS and managed services)
- **Kubernetes context** with production cluster access
- **Container registry credentials** (ECR/GCR/ACR authentication)
- **Production secrets:**
  - PostgreSQL connection string (from Terraform outputs)
  - Redis connection string (from Terraform outputs)
  - OpenAI API key
  - ServiceDesk Plus webhook secret and API credentials

### 3. Required Tools

Install and verify:
```bash
# Kubernetes CLI
kubectl version --client

# Docker (for building images)
docker --version

# AWS CLI (if using AWS)
aws --version
aws sts get-caller-identity

# jq (for JSON processing)
jq --version

# Terraform (to retrieve infrastructure outputs)
terraform version
```

---

## Pre-Deployment Checklist

- [ ] All tests passing in CI/CD (`pytest tests/` returns 0 failures)
- [ ] Production cluster operational (Story 5.1 complete)
- [ ] Database and Redis endpoints accessible
- [ ] Container registry accessible with push permissions
- [ ] Production secrets prepared (DATABASE_URL, REDIS_URL, API keys)
- [ ] DNS domain configured (api.ai-agents.production)
- [ ] Monitoring dashboards accessible (Grafana from Story 4.3)
- [ ] On-call engineer notified of deployment window
- [ ] Rollback plan reviewed and tested

---

## Deployment Procedure

### Step 1: Retrieve Infrastructure Outputs

Get database and Redis endpoints from Terraform:

```bash
cd infrastructure/terraform/

# Get all outputs
terraform output -json > /tmp/terraform-outputs.json

# Extract specific values
export DB_ENDPOINT=$(terraform output -raw db_endpoint)
export REDIS_ENDPOINT=$(terraform output -raw redis_endpoint)
export DB_PASSWORD=$(terraform output -raw db_password)  # From secrets manager

echo "Database Endpoint: $DB_ENDPOINT"
echo "Redis Endpoint: $REDIS_ENDPOINT"
```

### Step 2: Build and Push Docker Images

Build all three production images:

```bash
# Set registry and version
export REGISTRY="<YOUR_REGISTRY>"  # e.g., 123456789.dkr.ecr.us-east-1.amazonaws.com/ai-agents
export VERSION="v1.0.0"

# Authenticate to container registry
# For AWS ECR:
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $REGISTRY

# Build API image
docker build \
  -f docker/api.production.dockerfile \
  -t $REGISTRY/ai-agents-api:$VERSION \
  -t $REGISTRY/ai-agents-api:latest \
  .

# Build worker image
docker build \
  -f docker/worker.production.dockerfile \
  -t $REGISTRY/ai-agents-worker:$VERSION \
  -t $REGISTRY/ai-agents-worker:latest \
  .

# Build migrations image
docker build \
  -f docker/migrations.production.dockerfile \
  -t $REGISTRY/ai-agents-migrations:$VERSION \
  .

# Push all images
docker push $REGISTRY/ai-agents-api:$VERSION
docker push $REGISTRY/ai-agents-api:latest
docker push $REGISTRY/ai-agents-worker:$VERSION
docker push $REGISTRY/ai-agents-worker:latest
docker push $REGISTRY/ai-agents-migrations:$VERSION

# Verify images pushed successfully
docker pull $REGISTRY/ai-agents-api:$VERSION
```

**Time estimate:** 10-15 minutes

### Step 3: Create Production Secrets

Update secret templates with actual credentials:

```bash
# Create database credentials secret
kubectl create secret generic db-credentials \
  --from-literal=DATABASE_URL="postgresql+asyncpg://aiagents:${DB_PASSWORD}@${DB_ENDPOINT}:5432/aiagents?sslmode=require" \
  -n production \
  --dry-run=client -o yaml | kubectl apply -f -

# Create Redis credentials secret
kubectl create secret generic redis-credentials \
  --from-literal=REDIS_URL="rediss://${REDIS_ENDPOINT}:6379/0" \
  --from-literal=CELERY_BROKER_URL="rediss://${REDIS_ENDPOINT}:6379/0" \
  --from-literal=CELERY_RESULT_BACKEND="rediss://${REDIS_ENDPOINT}:6379/1" \
  -n production \
  --dry-run=client -o yaml | kubectl apply -f -

# Create OpenAI credentials secret
kubectl create secret generic openai-credentials \
  --from-literal=OPENAI_API_KEY="${OPENAI_API_KEY}" \
  -n production \
  --dry-run=client -o yaml | kubectl apply -f -

# Create ServiceDesk Plus credentials secret
kubectl create secret generic servicedesk-credentials \
  --from-literal=WEBHOOK_SECRET="${SERVICEDESK_WEBHOOK_SECRET}" \
  --from-literal=SERVICEDESK_API_URL="${SERVICEDESK_API_URL}" \
  --from-literal=SERVICEDESK_API_KEY="${SERVICEDESK_API_KEY}" \
  -n production \
  --dry-run=client -o yaml | kubectl apply -f -

# Verify secrets created
kubectl get secrets -n production
```

**Time estimate:** 5 minutes

### Step 4: Update Kubernetes Manifests with Image Tags

Update deployment manifests with actual registry and image tags:

```bash
# Update API deployment with registry path
sed -i "s|REPLACE_WITH_REGISTRY|${REGISTRY}|g" k8s/production/api-deployment.yaml

# Update worker deployment with registry path
sed -i "s|REPLACE_WITH_REGISTRY|${REGISTRY}|g" k8s/production/worker-deployment.yaml

# Update ingress with actual domain
sed -i "s|api.ai-agents.production|${PRODUCTION_DOMAIN}|g" k8s/production/ingress.yaml
```

### Step 5: Apply Kubernetes Manifests

Apply manifests in dependency order:

```bash
# 1. ConfigMap (non-sensitive configuration)
kubectl apply -f k8s/production/configmap.yaml

# 2. API deployment (includes init container for migrations)
kubectl apply -f k8s/production/api-deployment.yaml

# 3. API service
kubectl apply -f k8s/production/api-service.yaml

# 4. Worker deployment
kubectl apply -f k8s/production/worker-deployment.yaml

# 5. Horizontal Pod Autoscaler
kubectl apply -f k8s/production/hpa.yaml

# 6. Ingress (TLS-enabled)
kubectl apply -f k8s/production/ingress.yaml

# Verify all resources created
kubectl get all -n production
```

**Time estimate:** 5 minutes

### Step 6: Monitor Deployment Rollout

Watch pods come up and pass health checks:

```bash
# Monitor API deployment
kubectl rollout status deployment/ai-agents-api -n production --timeout=10m

# Monitor worker deployment
kubectl rollout status deployment/ai-agents-worker -n production --timeout=10m

# Check pod status
kubectl get pods -n production

# Expected output:
# NAME                              READY   STATUS    RESTARTS   AGE
# ai-agents-api-xxxxx               2/2     Running   0          2m
# ai-agents-api-yyyyy               2/2     Running   0          2m
# ai-agents-worker-xxxxx            1/1     Running   0          2m
# ai-agents-worker-yyyyy            1/1     Running   0          2m
# ai-agents-worker-zzzzz            1/1     Running   0          2m

# Check migration logs (init container)
kubectl logs deployment/ai-agents-api -n production -c migration-runner
```

**Time estimate:** 5-10 minutes (depends on image pull and startup time)

### Step 7: Configure DNS

Get ingress load balancer IP and configure DNS:

```bash
# Get load balancer IP/hostname
kubectl get ingress ai-agents-ingress -n production -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

# Or for AWS ELB (hostname instead of IP)
kubectl get ingress ai-agents-ingress -n production -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

# Create DNS A record (or CNAME for ELB):
# api.ai-agents.production → <load-balancer-ip-or-hostname>
```

Wait for DNS propagation (5-30 minutes) and verify:

```bash
dig api.ai-agents.production
```

### Step 8: Monitor TLS Certificate Provisioning

cert-manager will automatically provision Let's Encrypt certificate:

```bash
# Monitor certificate status
kubectl get certificate api-tls-cert -n production -w

# Expected output after 2-5 minutes:
# NAME            READY   SECRET          AGE
# api-tls-cert    True    api-tls-cert    3m

# Check cert-manager logs if issues
kubectl logs -n cert-manager deployment/cert-manager --tail=50
```

**Time estimate:** 2-5 minutes

---

## Post-Deployment Validation

### Step 1: Run Smoke Tests

Execute automated smoke test suite:

```bash
export API_BASE_URL="https://api.ai-agents.production"
export WEBHOOK_SECRET="${SERVICEDESK_WEBHOOK_SECRET}"
export TENANT_ID="00000000-0000-0000-0000-000000000001"

./scripts/production-smoke-test.sh $API_BASE_URL
```

Expected output:
```
=========================================
Production Smoke Test Suite
=========================================
[PASS] Health check returned 200 OK
[PASS] Readiness check returned 200 OK
[PASS] TLS certificate is valid
[PASS] Invalid signature rejected with 401 Unauthorized
[PASS] Valid webhook accepted with 202 Accepted
[PASS] Metrics endpoint returned 200 OK
[PASS] HTTP redirects to HTTPS successfully
=========================================
Smoke Test Summary
=========================================
Tests Passed: 10
Tests Failed: 0
=========================================
All smoke tests passed! ✓
```

### Step 2: Manual Validation

Verify key functionality manually:

```bash
# 1. Health check
curl -v https://api.ai-agents.production/health

# 2. Metrics endpoint (Prometheus format)
curl https://api.ai-agents.production/metrics

# 3. Check Grafana dashboards
# Open: https://grafana.ai-agents.production/dashboards
# Verify: "AI Agents API" dashboard shows metrics

# 4. Check Prometheus targets
# Open Prometheus UI and verify targets are UP:
# - ai-agents-api (2 replicas)
# - ai-agents-worker (3 replicas)
```

### Step 3: End-to-End Test (Optional)

Send a real test ticket webhook from ServiceDesk Plus:

```bash
# Trigger test webhook from ServiceDesk Plus admin console
# Or use curl with valid signature:

PAYLOAD='{"ticket_id": "TEST-001", "subject": "Test ticket", "description": "Testing production deployment", "tenant_id": "00000000-0000-0000-0000-000000000001"}'
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | awk '{print $2}')

curl -X POST https://api.ai-agents.production/webhook/servicedesk \
  -H "Content-Type: application/json" \
  -H "X-ServiceDesk-Signature: sha256=$SIGNATURE" \
  -H "X-Tenant-ID: 00000000-0000-0000-0000-000000000001" \
  -d "$PAYLOAD"

# Expected: HTTP 202 Accepted with job ID

# Verify enhancement processed:
# 1. Check worker logs: kubectl logs -n production deployment/ai-agents-worker --tail=50
# 2. Check database: Query enhancement_history table for TEST-001
# 3. Check ServiceDesk Plus: Verify enhancement comment added to ticket
```

---

## Rollback Procedure

If deployment validation fails, roll back to previous version:

### Option 1: Kubernetes Rollback (Fastest)

```bash
# Rollback API deployment
kubectl rollout undo deployment/ai-agents-api -n production

# Rollback worker deployment
kubectl rollout undo deployment/ai-agents-worker -n production

# Monitor rollback
kubectl rollout status deployment/ai-agents-api -n production
kubectl rollout status deployment/ai-agents-worker -n production

# Verify previous version running
kubectl get pods -n production -o jsonpath='{.items[*].spec.containers[*].image}' | tr ' ' '\n' | sort -u
```

**Time estimate:** 2-3 minutes

### Option 2: Redeploy Previous Version

```bash
# Update image tags to previous version
export PREVIOUS_VERSION="v0.9.0"

kubectl set image deployment/ai-agents-api ai-agents-api=$REGISTRY/ai-agents-api:$PREVIOUS_VERSION -n production
kubectl set image deployment/ai-agents-worker ai-agents-worker=$REGISTRY/ai-agents-worker:$PREVIOUS_VERSION -n production

# Monitor rollout
kubectl rollout status deployment/ai-agents-api -n production
```

### Database Migration Rollback

If database migrations caused issues:

```bash
# Connect to database
psql $DATABASE_URL

# Check current migration version
SELECT * FROM alembic_version;

# Downgrade to previous version (use Alembic revision ID)
alembic downgrade -1

# Or downgrade to specific revision
alembic downgrade <revision-id>
```

**⚠️ WARNING:** Only downgrade migrations if absolutely necessary. Coordinate with team first.

---

## Troubleshooting

### Pods Not Starting (CrashLoopBackOff)

**Symptoms:** Pods stuck in CrashLoopBackOff or ImagePullBackOff

**Diagnosis:**
```bash
# Check pod status
kubectl get pods -n production

# Check pod events
kubectl describe pod <pod-name> -n production

# Check pod logs
kubectl logs <pod-name> -n production
kubectl logs <pod-name> -n production --previous  # Previous crash logs
```

**Common Causes:**
1. **ImagePullBackOff:** Container registry authentication failed
   - Solution: Re-authenticate to registry, verify image exists
2. **Database connection failed:** DATABASE_URL incorrect or database down
   - Solution: Verify DATABASE_URL in secrets, test connectivity
3. **Redis connection failed:** REDIS_URL incorrect or Redis down
   - Solution: Verify REDIS_URL in secrets, test connectivity
4. **Migration failed:** Alembic error in init container
   - Solution: Check migration logs, verify database schema

### Health Probes Failing

**Symptoms:** Pods restarting frequently, readiness probe failures

**Diagnosis:**
```bash
# Check probe configuration
kubectl describe pod <pod-name> -n production | grep -A5 "Liveness\|Readiness"

# Test health endpoint manually
kubectl exec -it <pod-name> -n production -- curl http://localhost:8000/health
```

**Solutions:**
- Increase `initialDelaySeconds` if app needs more startup time
- Increase `timeoutSeconds` if health checks are slow
- Check database/Redis connectivity (common cause of health check failures)

### TLS Certificate Not Provisioning

**Symptoms:** cert-manager shows certificate NOT READY after 5+ minutes

**Diagnosis:**
```bash
# Check certificate status
kubectl describe certificate api-tls-cert -n production

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager --tail=100

# Check cert-manager challenges
kubectl get challenges -n production
```

**Common Causes:**
1. DNS not propagated yet (wait 30 minutes)
2. Let's Encrypt rate limits hit (use staging issuer for testing)
3. Firewall blocking HTTP-01 challenge (port 80 must be accessible)

**Solutions:**
```bash
# Delete and recreate certificate
kubectl delete certificate api-tls-cert -n production
kubectl apply -f k8s/production/ingress.yaml

# Use Let's Encrypt staging for testing
# Update ingress annotation: cert-manager.io/cluster-issuer: letsencrypt-staging
```

### High Memory/CPU Usage

**Symptoms:** Pods being OOM-killed or throttled

**Diagnosis:**
```bash
# Check resource usage
kubectl top pods -n production

# Check resource limits
kubectl describe pod <pod-name> -n production | grep -A5 "Limits\|Requests"
```

**Solutions:**
- Increase resource limits in deployment manifests
- Scale up HPA replicas to distribute load
- Investigate memory leaks (check worker logs for stuck tasks)

---

## Common Issues

### Issue: "Database migrations failed"

**Error:** Init container exits with Alembic error

**Solution:**
```bash
# Check migration logs
kubectl logs <pod-name> -n production -c migration-runner

# Common fixes:
# 1. Database not ready: Increase init container retry logic
# 2. Migration conflict: Check alembic_version table, resolve manually
# 3. Permission denied: Verify database user has DDL permissions
```

### Issue: "Webhook signature validation always fails"

**Error:** All webhooks return 401 Unauthorized

**Solution:**
```bash
# Verify WEBHOOK_SECRET matches ServiceDesk Plus configuration
kubectl get secret servicedesk-credentials -n production -o jsonpath='{.data.WEBHOOK_SECRET}' | base64 -d

# Test signature generation locally
PAYLOAD='{"test": "data"}'
echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET"

# Compare with ServiceDesk Plus webhook logs
```

### Issue: "Workers not processing tasks"

**Error:** Redis queue fills up, workers idle

**Solution:**
```bash
# Check worker logs
kubectl logs deployment/ai-agents-worker -n production --tail=100

# Check Redis connectivity
kubectl exec -it deployment/ai-agents-api -n production -- redis-cli -u $REDIS_URL ping

# Check Celery worker status
kubectl exec -it deployment/ai-agents-worker -n production -- celery -A src.workers.celery_app inspect active

# Restart workers if stuck
kubectl rollout restart deployment/ai-agents-worker -n production
```

---

## Monitoring and Alerts

### Key Metrics to Monitor (Grafana Dashboards)

1. **Application Health:**
   - API pod count (should be 2)
   - Worker pod count (should be 3-10 based on HPA)
   - Health check success rate (should be 100%)
   - Readiness probe failures

2. **Performance:**
   - Request latency (p50, p95, p99) - target p95 < 60s
   - Request rate (requests/second)
   - Error rate (errors/total requests) - target < 1%
   - Enhancement success rate

3. **Infrastructure:**
   - CPU usage (per pod and cluster-wide)
   - Memory usage (watch for memory leaks)
   - Database connection pool utilization
   - Redis queue depth

4. **Business Metrics:**
   - Webhooks received (total count)
   - Enhancements completed (success/failure)
   - Average context gathering duration
   - ServiceDesk Plus ticket update latency

### Critical Alerts (Alertmanager from Story 4.5)

Ensure these alerts are configured and routing to on-call:

1. **API Down:** No healthy API pods for 2+ minutes
2. **High Error Rate:** Error rate > 5% for 5 minutes
3. **Queue Backup:** Redis queue depth > 1000 for 10 minutes
4. **Database Connection Failures:** > 10 connection errors in 5 minutes
5. **Certificate Expiring:** TLS certificate expires in < 7 days
6. **Pod Restart Loop:** Pod restarted > 5 times in 10 minutes

### Accessing Monitoring Tools

```bash
# Grafana (dashboards)
https://grafana.ai-agents.production/

# Prometheus (metrics query)
https://prometheus.ai-agents.production/

# Alertmanager (alerts status)
https://alertmanager.ai-agents.production/

# Jaeger (distributed tracing)
https://jaeger.ai-agents.production/
```

---

## Next Steps After Successful Deployment

1. **Story 5.3:** Onboard first production client
2. **Story 5.4:** Conduct production validation testing
3. **Story 5.5:** Establish baseline metrics and success criteria
4. **Story 5.6:** Create production support documentation and handoff

---

## Document Maintenance

- **Last Updated:** 2025-11-03
- **Next Review:** After first production deployment
- **Owner:** DevOps Team
- **Feedback:** Report issues to #production-ops Slack channel
