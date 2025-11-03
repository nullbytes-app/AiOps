# Prometheus Setup Guide - AI Agents Platform

## Overview

This guide provides step-by-step instructions for deploying and configuring Prometheus server for the AI Agents Platform in both local Docker and Kubernetes production environments.

**Story:** 4.2 - Deploy Prometheus Server and Configure Scraping
**Prerequisites:** Story 4.1 (Prometheus metrics instrumentation) must be completed

### Architecture

```
┌──────────────────┐
│  Prometheus      │
│  Server          │
└────────┬─────────┘
         │ Scrapes /metrics every 15s
         │
    ┌────┴───────────────────┐
    │                        │
┌───▼──────────┐    ┌────────▼────────┐
│  FastAPI     │    │   Celery        │
│  (port 8000) │    │   Workers       │
│  /metrics    │    │   (optional)    │
└──────────────┘    └─────────────────┘
```

**Key Design Decisions:**
- **Pull-based metrics:** Prometheus scrapes `/metrics` endpoints (not push-based)
- **15-second scrape interval:** Balances data freshness vs. scrape load
- **30-day retention:** Meets NFR005 observability requirements
- **Service discovery:** Docker DNS (local) and Kubernetes API (production)

---

## Local Docker Deployment

### Prerequisites

- Docker and Docker Compose installed
- AI Agents Platform application running (`docker-compose up -d`)
- Port 9090 available on localhost

### Step 1: Verify Configuration Files

Ensure the following files exist:

**`prometheus.yml` (project root):**
```bash
cat prometheus.yml
# Should contain global scrape_interval: 15s and fastapi-app job
```

**`docker-compose.yml` (Prometheus service):**
```bash
docker-compose config | grep -A 20 prometheus
# Should show Prometheus service definition
```

### Step 2: Start Prometheus

```bash
# Start Prometheus service
docker-compose up -d prometheus

# Verify container is running
docker ps | grep prometheus
# Expected: ai-agents-prometheus container with status "Up"

# Check logs for errors
docker-compose logs prometheus
# Should show "Server is ready to receive web requests"
```

### Step 3: Access Prometheus UI

Open browser and navigate to: **http://localhost:9090**

**Expected:**
- Prometheus web interface loads
- No startup errors displayed

### Step 4: Verify Scrape Targets

1. Navigate to **Status → Targets**
2. Locate the **`fastapi-app`** job
3. Verify target status:
   - **Endpoint:** `http://api:8000/metrics`
   - **State:** UP (green indicator)
   - **Last Scrape:** Recent timestamp (updates every 15 seconds)
   - **Health:** Checkmark icon (no errors)

**Troubleshooting:**
- **Target DOWN:** Ensure FastAPI container is healthy (`docker ps`)
- **Connection refused:** Verify `/metrics` endpoint accessible (`curl http://localhost:8000/metrics`)
- **No targets:** Check `prometheus.yml` syntax (`yamllint prometheus.yml`)

### Step 5: Verify Configuration

1. Navigate to **Status → Configuration**
2. Verify settings:
   - **scrape_interval:** 15s
   - **evaluation_interval:** 15s
   - **retention:** 30d (check logs or Status → Runtime Information)

### Step 6: Test Sample Query

1. Navigate to **Graph** tab
2. Enter query: `enhancement_requests_total`
3. Click **Execute**
4. Expected: Metric data displayed (or "no data" if no requests yet)

**Trigger test request:**
```bash
curl -X POST http://localhost:8000/webhook/servicedesk \
  -H "Content-Type: application/json" \
  -d '{"ticket_id": "TEST-001", "tenant_id": "test-tenant"}'

# Wait 15 seconds (one scrape interval), then re-run query
```

### Step 7: Health Check Validation

```bash
# Test health endpoint
curl http://localhost:9090/-/healthy
# Expected: "Prometheus Server is Healthy." with 200 OK

# Test readiness endpoint
curl http://localhost:9090/-/ready
# Expected: 200 OK status
```

---

## Kubernetes Production Deployment

### Prerequisites

- `kubectl` access to target Kubernetes cluster
- Context configured: `kubectl config current-context`
- Sufficient permissions to create Deployments, Services, RBAC resources
- Port 9090 available for port-forwarding (or Ingress configured)

### Step 1: Review Kubernetes Manifests

Verify manifest files exist in `k8s/` directory:

```bash
ls k8s/prometheus-*.yaml
# Expected files:
# - k8s/prometheus-config.yaml (ConfigMap)
# - k8s/prometheus-deployment.yaml (Deployment, Service, RBAC)
```

### Step 2: Apply ConfigMap

```bash
# Create Prometheus configuration ConfigMap
kubectl apply -f k8s/prometheus-config.yaml

# Verify ConfigMap created
kubectl get configmap prometheus-config
# Expected: NAME: prometheus-config, DATA: 1
```

### Step 3: Deploy Prometheus

```bash
# Create Deployment, Service, ServiceAccount, and RBAC
kubectl apply -f k8s/prometheus-deployment.yaml

# Verify resources created
kubectl get deployment prometheus
kubectl get service prometheus
kubectl get serviceaccount prometheus
kubectl get clusterrole prometheus
kubectl get clusterrolebinding prometheus

# Expected: All resources exist
```

### Step 4: Verify Pod Status

```bash
# Check pod is running
kubectl get pods -l app=prometheus
# Expected: STATUS=Running, READY=1/1

# Check pod logs
kubectl logs -l app=prometheus --tail=50
# Should show:
# - "Server is ready to receive web requests"
# - No fatal errors
# - "Completed loading of configuration file"

# Describe pod for detailed status
kubectl describe pod -l app=prometheus
# Check Events section for issues
```

### Step 5: Access Prometheus UI

**Option A: Port-Forward (Recommended for testing)**

```bash
# Forward local port 9090 to Prometheus service
kubectl port-forward svc/prometheus 9090:9090

# Keep terminal open, open browser to http://localhost:9090
```

**Option B: LoadBalancer (Production)**

```yaml
# Edit Service type in k8s/prometheus-deployment.yaml
spec:
  type: LoadBalancer  # Changed from ClusterIP
```

```bash
# Reapply deployment
kubectl apply -f k8s/prometheus-deployment.yaml

# Get external IP
kubectl get service prometheus
# Access via EXTERNAL-IP:9090
```

**Option C: Ingress (Production with authentication)**

```yaml
# Create Ingress resource (example)
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: prometheus-ingress
  annotations:
    nginx.ingress.kubernetes.io/auth-type: basic
    nginx.ingress.kubernetes.io/auth-secret: prometheus-basic-auth
spec:
  rules:
    - host: prometheus.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: prometheus
                port:
                  number: 9090
```

### Step 6: Verify Service Discovery

1. Navigate to **Status → Targets** in Prometheus UI
2. Locate **`kubernetes-pods`** job
3. Verify discovered pods:
   - FastAPI pods should be listed (one entry per replica)
   - **Endpoint:** `http://<pod-ip>:8000/metrics`
   - **State:** UP (green indicators)
   - **Labels:** `kubernetes_pod_name`, `kubernetes_namespace`, `service=api`

**Troubleshooting:**
- **No targets discovered:** Verify FastAPI Deployment has Prometheus annotations
  ```bash
  kubectl get deployment deployment-api -o yaml | grep -A 3 "prometheus.io"
  # Expected annotations: prometheus.io/scrape, port, path
  ```
- **Pods not annotated:** Apply updated deployment (`kubectl apply -f k8s/deployment-api.yaml`)
- **Permission denied:** Verify RBAC is applied (`kubectl get clusterrolebinding prometheus`)

### Step 7: Test Service Discovery with Scaling

```bash
# Scale FastAPI deployment to 3 replicas
kubectl scale deployment deployment-api --replicas=3

# Wait 30 seconds for service discovery
sleep 30

# Check Prometheus Targets
# Expected: 3 FastAPI pod targets now visible (auto-discovered)

# Scale back to 2 replicas
kubectl scale deployment deployment-api --replicas=2
```

### Step 8: Verify Health Probes

```bash
# Check liveness probe status
kubectl describe pod -l app=prometheus | grep -A 5 "Liveness"
# Expected: Status should show successful probe checks

# Check readiness probe status
kubectl describe pod -l app=prometheus | grep -A 5 "Readiness"
# Expected: Status should show successful probe checks

# Manual health check via pod exec
kubectl exec -it deployment/prometheus -- wget -O- http://localhost:9090/-/healthy
# Expected: "Prometheus Server is Healthy."
```

### Step 9: Verify Retention Configuration

1. Navigate to **Status → Runtime Information** in Prometheus UI
2. Find **Storage** section
3. Verify **Retention:** `30d` (30 days)

**Or check via pod logs:**
```bash
kubectl logs -l app=prometheus | grep retention
# Expected: "--storage.tsdb.retention.time=30d"
```

### Step 10: Test Sample PromQL Queries

1. Navigate to **Graph** tab
2. Run test queries (see [Metrics Guide](metrics-guide.md) for full list):

```promql
# Test query 1: Check metrics are being scraped
enhancement_requests_total

# Test query 2: p95 latency
histogram_quantile(0.95, rate(enhancement_duration_seconds_bucket[5m]))

# Test query 3: Active pods
up{job="kubernetes-pods"}
```

---

## Configuration Files Explained

### prometheus.yml (Local Docker)

```yaml
global:
  scrape_interval: 15s        # Scrape targets every 15 seconds
  evaluation_interval: 15s    # Evaluate rules every 15 seconds

scrape_configs:
  - job_name: 'fastapi-app'   # Job identifier
    static_configs:
      - targets: ['api:8000'] # Docker service name (not localhost!)
        labels:               # Additional labels for metrics
          service: 'enhancement-api'
          environment: 'local'
    metrics_path: '/metrics'  # Path to metrics endpoint
    scrape_timeout: 10s       # Max time for single scrape
```

### k8s/prometheus-config.yaml (Kubernetes)

**Key Configuration:**
- **Kubernetes Service Discovery:** `kubernetes_sd_configs` with `role: pod`
- **Annotation Filtering:** Only scrape pods with `prometheus.io/scrape=true`
- **Dynamic Port/Path:** Extract from `prometheus.io/port` and `prometheus.io/path` annotations
- **Relabel Configs:** Transform discovered labels into usable metric labels

**Relabeling Logic:**
1. Keep only pods with `prometheus.io/scrape=true` annotation
2. Extract metrics path from `prometheus.io/path` annotation (default: `/metrics`)
3. Extract port from `prometheus.io/port` annotation (required)
4. Add pod name, namespace, IP as labels for filtering

---

## Troubleshooting

### Target Shows DOWN Status

**Symptoms:**
- Prometheus UI → Status → Targets shows red "DOWN" indicator
- Error message: "context deadline exceeded" or "connection refused"

**Solutions:**
1. **Verify /metrics endpoint is accessible:**
   ```bash
   # Local Docker
   docker exec ai-agents-api curl http://localhost:8000/metrics

   # Kubernetes
   kubectl exec deployment/deployment-api -- curl http://localhost:8000/metrics
   ```

2. **Check application logs for errors:**
   ```bash
   # Local Docker
   docker-compose logs api

   # Kubernetes
   kubectl logs deployment/deployment-api
   ```

3. **Verify network connectivity:**
   ```bash
   # Local Docker: Prometheus can reach API
   docker exec prometheus wget -O- http://api:8000/metrics

   # Kubernetes: Check service
   kubectl get endpoints deployment-api
   ```

### No Targets Discovered (Kubernetes)

**Symptoms:**
- Prometheus UI → Status → Targets shows no `kubernetes-pods` targets
- Or shows targets but FastAPI pods missing

**Solutions:**
1. **Verify pod annotations:**
   ```bash
   kubectl describe pod -l app=api | grep -A 3 "Annotations"
   # Must show: prometheus.io/scrape, prometheus.io/port, prometheus.io/path
   ```

2. **Check RBAC permissions:**
   ```bash
   kubectl auth can-i get pods --as=system:serviceaccount:default:prometheus
   # Expected: yes
   ```

3. **Restart Prometheus to refresh service discovery:**
   ```bash
   kubectl rollout restart deployment prometheus
   ```

### Scrape Errors in Prometheus Logs

**Symptoms:**
- Prometheus logs show: "scrape failed" or "server returned HTTP status 500"

**Solutions:**
1. **Check metrics endpoint response:**
   ```bash
   curl -v http://localhost:8000/metrics
   # Look for HTTP status code (should be 200 OK)
   ```

2. **Verify prometheus_client is installed:**
   ```bash
   docker exec ai-agents-api pip show prometheus-client
   # Should show version >=0.19.0
   ```

3. **Test metrics endpoint manually:**
   ```bash
   docker exec ai-agents-api python -c "from prometheus_client import generate_latest; print(generate_latest())"
   ```

### High Memory Usage

**Symptoms:**
- Prometheus pod shows high memory usage (>1Gi)
- OOMKilled errors in pod events

**Solutions:**
1. **Reduce retention period (if acceptable):**
   ```yaml
   # Edit k8s/prometheus-deployment.yaml
   args:
     - '--storage.tsdb.retention.time=15d'  # Reduced from 30d
   ```

2. **Increase memory limits:**
   ```yaml
   # Edit k8s/prometheus-deployment.yaml
   resources:
     limits:
       memory: 2Gi  # Increased from 1Gi
   ```

3. **Add Persistent Volume for efficient storage:**
   ```yaml
   # Replace emptyDir with PVC
   volumes:
     - name: prometheus-data
       persistentVolumeClaim:
         claimName: prometheus-pvc
   ```

---

## Next Steps

1. **Story 4.3:** Create Grafana dashboards for real-time monitoring
2. **Story 4.4:** Configure alerting rules in Prometheus
3. **Story 4.5:** Integrate Alertmanager for alert routing

**Operational Tasks:**
- Set up backup for Prometheus data (if using PersistentVolume)
- Configure retention policies based on storage capacity
- Implement authentication for production Prometheus UI (via Ingress)
- Create operational runbooks for common troubleshooting scenarios

---

## Related Documentation

- [Metrics Guide - PromQL Queries](metrics-guide.md)
- [Architecture - Observability Section](../architecture.md#observability)
- [PRD - NFR005 (Observability Requirements)](../PRD.md#nfr005-observability)
- [Story 4.1 - Prometheus Metrics Instrumentation](../stories/4-1-implement-prometheus-metrics-instrumentation.md)

---

**Prometheus Official Documentation:**
- [Getting Started](https://prometheus.io/docs/prometheus/latest/getting_started/)
- [Configuration](https://prometheus.io/docs/prometheus/latest/configuration/configuration/)
- [Kubernetes SD](https://prometheus.io/docs/prometheus/latest/configuration/configuration/#kubernetes_sd_config)
- [Querying Basics](https://prometheus.io/docs/prometheus/latest/querying/basics/)
