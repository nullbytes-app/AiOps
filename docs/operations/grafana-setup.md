# Grafana Setup Guide for AI Agents Platform

## Overview

Grafana provides real-time visual dashboards for monitoring the AI Agents platform. It connects to a Prometheus datasource to display system health, performance metrics, and operational insights.

**Key Components:**
- **Datasource**: Prometheus (port 9090)
- **Dashboards**: "AI Agents - System Health & Performance"
- **Refresh Interval**: 30 seconds (auto-refresh)
- **Time Range**: Supports 1h, 6h, 24h, 7d lookback windows

---

## Architecture

```
FastAPI Application
        ↓
   /metrics endpoint
        ↓
   Prometheus (scrapes every 15s)
        ↓
   Grafana (queries every 30s)
        ↓
   Dashboards (visualized in UI)
```

**Data Flow:**
1. FastAPI application exposes metrics at `/metrics` endpoint (port 8000)
2. Prometheus scrapes metrics at 15-second intervals
3. Grafana queries Prometheus datasource for dashboard visualization
4. Dashboard auto-refreshes every 30 seconds

---

## Local Docker Deployment

### Prerequisites

- Docker and Docker Compose installed
- `docker-compose.yml` configured with all services
- Prometheus service running and healthy (Story 4.2 prerequisite)

### Deployment Steps

1. **Start all services:**
   ```bash
   docker-compose up -d
   ```

2. **Verify Grafana is running:**
   ```bash
   docker ps | grep grafana
   docker-compose logs grafana
   ```

3. **Access Grafana UI:**
   - URL: http://localhost:3000
   - Default credentials: admin / admin
   - **Recommended**: Change password on first login

4. **Verify service health:**
   ```bash
   curl http://localhost:3000/api/health
   ```

### Configuration Files

- **Datasource**: Mounted from `k8s/grafana-datasource.yaml`
- **Dashboard**: Mounted from `k8s/grafana-dashboard.yaml`
- **Data Persistence**: `grafana_data` named volume

### Troubleshooting Local Deployment

| Issue | Solution |
|-------|----------|
| Grafana container won't start | Check `docker-compose logs grafana` for errors; verify Prometheus is healthy |
| Cannot access http://localhost:3000 | Verify port 3000 is not in use; check container status with `docker ps` |
| "Data source is down" in UI | Verify Prometheus service is running; check network connectivity between containers |
| Dashboard shows "No data" | Verify metrics are being scraped (check Prometheus at http://localhost:9090); wait 1-2 minutes for data collection |

---

## Kubernetes Production Deployment

### Prerequisites

- kubectl configured with cluster access
- Prometheus deployed (Story 4.2 prerequisite)
- YAML manifests: `k8s/grafana-datasource.yaml`, `k8s/grafana-dashboard.yaml`, `k8s/grafana-deployment.yaml`

### Deployment Steps

1. **Create datasource ConfigMap:**
   ```bash
   kubectl apply -f k8s/grafana-datasource.yaml
   ```

2. **Create dashboard ConfigMap:**
   ```bash
   kubectl apply -f k8s/grafana-dashboard.yaml
   ```

3. **Deploy Grafana (Deployment + Service):**
   ```bash
   kubectl apply -f k8s/grafana-deployment.yaml
   ```

4. **Verify deployment:**
   ```bash
   kubectl get deployment grafana
   kubectl get pods -l app=grafana
   kubectl get service grafana
   kubectl get configmap | grep grafana
   ```

5. **Access Grafana via port-forward:**
   ```bash
   kubectl port-forward svc/grafana 3000:3000
   ```
   Then navigate to: http://localhost:3000

6. **Check pod logs:**
   ```bash
   kubectl logs -l app=grafana -f
   ```

### Production Configuration

- **Image**: grafana/grafana:latest (pin to specific version for production)
- **Replicas**: 1 (consider increasing for HA)
- **Resource Limits**: CPU 200m, Memory 512Mi
- **Health Probes**: Liveness and readiness probes configured
- **Data Persistence**: emptyDir (ephemeral; use PersistentVolume for production)

### Ingress Setup (Optional for External Access)

For external access in production, configure Kubernetes Ingress:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: grafana-ingress
spec:
  rules:
  - host: grafana.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: grafana
            port:
              number: 3000
```

Then apply: `kubectl apply -f grafana-ingress.yaml`

### Troubleshooting Kubernetes Deployment

| Issue | Solution |
|-------|----------|
| Pod in CrashLoopBackOff | Check pod logs: `kubectl logs <pod-name>` |
| ConfigMaps not auto-provisioning | Verify volume mounts in Deployment spec; check provisioning directory permissions |
| Port-forward fails | Verify pod is running: `kubectl get pod <pod-name>` |
| Datasource shows "Service Unavailable" | Verify Prometheus Service is discoverable: `kubectl get service prometheus` |

---

## Dashboard Guide

### Main Dashboard: "AI Agents - System Health & Performance"

The main dashboard provides at-a-glance visibility into platform health with 5 key panels.

#### Panel 1: Enhancement Success Rate (Gauge)

- **Metric**: `enhancement_success_rate`
- **Visualization**: Gauge (0-100%)
- **Thresholds**:
  - Red: < 90% (Alert condition)
  - Yellow: 90-95% (Warning)
  - Green: ≥ 95% (Healthy)
- **Interpretation**: Percentage of successfully processed enhancement requests. Values above 95% indicate healthy system operation.

#### Panel 2: Pending Enhancement Jobs in Queue (Time Series)

- **Metric**: `queue_depth`
- **Visualization**: Line chart with area fill
- **Y-Axis**: Number of jobs in Redis queue
- **Threshold Line**: 100 jobs (SLA reference)
- **Interpretation**: Shows queue depth over time. Sustained high values (>100) indicate processing backlog and may require worker scaling.

#### Panel 3: p95 Enhancement Processing Latency (Time Series)

- **Metric**: `histogram_quantile(0.95, rate(enhancement_duration_seconds_bucket[5m]))`
- **Visualization**: Line chart
- **Y-Axis**: Latency in seconds
- **Target Line**: 120 seconds (SLA reference)
- **Interpretation**: The 95th percentile latency indicates when slowest requests complete. Values above 120s suggest performance degradation.

#### Panel 4: Error Rate by Tenant (Table)

- **Metric**: `rate(enhancement_requests_total{status="failure"}[5m]) / rate(enhancement_requests_total[5m]) * 100`
- **Visualization**: Table with sortable columns
- **Columns**: Tenant, Error Rate (%)
- **Color Coding**:
  - Green: < 1% error rate (healthy)
  - Yellow: 1-5% error rate (warning)
  - Red: > 5% error rate (critical)
- **Interpretation**: Shows which tenants are experiencing issues. High error rates for specific tenants may indicate tenant-specific configuration problems or data quality issues.

#### Panel 5: Active Celery Workers (Stat)

- **Metric**: `worker_active_count`
- **Visualization**: Large number display (Stat panel)
- **Color**: Green (≥ 1 worker), Red (0 workers)
- **Interpretation**: Count of active Celery workers. Zero workers indicate workers are down and no tasks will be processed.

### Dashboard Interactions

#### Time Range Selector

Located in the dashboard header (top-right):

- **Quick Select Options**:
  - Last 1 hour (default)
  - Last 6 hours
  - Last 24 hours
  - Last 7 days
- **Custom Range**: Click calendar icon for custom date/time selection
- **Effect**: All panels update to show data within selected time range

#### Auto-Refresh Indicator

Located in dashboard header:

- **Default**: 30 seconds
- **Control**: Click dropdown to change interval (10s, 1m, 5m, etc.)
- **Persistence**: Selection saved across page reloads

#### Per-Tenant Filtering (Future Enhancement)

Error Rate by Tenant panel demonstrates filtering capability. Future dashboards can add tenant-specific views using dashboard variables.

---

## Configuration Files

### Datasource Configuration (k8s/grafana-datasource.yaml)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasource
data:
  prometheus.yaml: |
    apiVersion: 1
    datasources:
      - name: Prometheus
        type: prometheus
        url: http://prometheus:9090
        access: proxy
        isDefault: true
```

**Key Fields:**
- `url`: Internal Kubernetes service name (`http://prometheus:9090`)
- `access: proxy`: Grafana queries Prometheus on behalf of client
- `isDefault: true`: This datasource used by default in all panels

### Dashboard Configuration (k8s/grafana-dashboard.yaml)

The dashboard JSON defines all panels, queries, visualizations, and refresh settings. Key properties:

```json
{
  "title": "AI Agents - System Health & Performance",
  "refresh": "30s",
  "panels": [
    {
      "title": "Success Rate",
      "targets": [{"expr": "enhancement_success_rate"}],
      "type": "gauge"
    },
    ...
  ]
}
```

**Auto-Provisioning**: ConfigMap mounted to `/etc/grafana/provisioning/dashboards/` enables auto-provisioning on Grafana startup.

### Environment Variables (docker-compose.yml)

```yaml
environment:
  GF_SECURITY_ADMIN_USER: admin
  GF_SECURITY_ADMIN_PASSWORD: admin
  GF_PATHS_PROVISIONING: /etc/grafana/provisioning
  GF_SERVER_ROOT_URL: "http://localhost:3000"
```

**Important for Production:**
- `GF_SECURITY_ADMIN_PASSWORD`: Change from default "admin" immediately
- `GF_SERVER_ROOT_URL`: Update to match actual Grafana URL (e.g., https://grafana.example.com)
- Additional options: See [Grafana Environment Variables](https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/#override-configuration-with-environment-variables)

---

## Performance Optimization

### Query Optimization

Use range vectors instead of instant queries for better performance:

**Recommended:**
```promql
rate(enhancement_requests_total[5m])  # Returns time series over 5m window
```

**Avoid:**
```promql
enhancement_requests_total  # Instant query, less useful for trends
```

### Recording Rules (Future Enhancement - Story 4.4)

Pre-compute complex queries with Prometheus recording rules:

```yaml
- name: ai_agents_rules
  interval: 30s
  rules:
  - record: ai_agents:enhancement_success_rate:5m
    expr: rate(enhancement_requests_total{status="success"}[5m]) / rate(enhancement_requests_total[5m]) * 100
```

Then query the pre-computed metric: `ai_agents:enhancement_success_rate:5m`

### Dashboard Cloning

Create custom dashboards by cloning the main dashboard:
1. Open main dashboard
2. Click settings (gear icon)
3. Click "Save as" → Enter new name
4. Customize panels as needed

---

## Authentication & Security

### Local Docker

- **Default Credentials**: admin / admin
- **Recommended Action**: Change password on first login
- **Access Control**: Localhost-only by default

### Kubernetes Production

- **Admin User**: Created from environment variables
- **Recommended**:
  - Change default password immediately
  - Use Ingress with authentication (OAuth, LDAP, SAML)
  - Implement RBAC for multi-user access
- **Datasource Security**: Prometheus URL configured with internal Kubernetes DNS name (no external exposure)

### Sensitive Data Handling

- Dashboard JSON doesn't include sensitive data (metrics are aggregated)
- Prometheus scrape auth credentials (if needed) stored in Kubernetes secrets
- Grafana admin password stored in deployment environment variables or secrets manager

---

## Troubleshooting

### Common Issues

#### Datasource Shows "Data Source is Down"

**Cause**: Grafana cannot reach Prometheus

**Solutions**:
1. Verify Prometheus is running:
   - Local Docker: `docker ps | grep prometheus`
   - Kubernetes: `kubectl get pod -l app=prometheus`

2. Check network connectivity:
   - Docker: Ping Prometheus from Grafana container: `docker exec ai-agents-grafana ping prometheus`
   - Kubernetes: Verify service exists: `kubectl get service prometheus`

3. Check Prometheus health endpoint:
   - Local: `curl http://localhost:9090/-/healthy`
   - Kubernetes: `curl http://prometheus:9090/-/healthy` (from inside pod)

#### Dashboard Panels Show No Data

**Cause**: Prometheus has not collected metrics yet

**Solutions**:
1. Wait 1-2 minutes for initial metrics collection
2. Verify `/metrics` endpoint is accessible: `curl http://localhost:8000/metrics` (local)
3. Check Prometheus targets: http://localhost:9090 → Status → Targets
4. Verify FastAPI application is running and exposing metrics

#### Login Fails with "Invalid credentials"

**Cause**: Incorrect admin password

**Solutions**:
1. Check environment variables:
   - Docker: `docker-compose config | grep GF_SECURITY`
   - Kubernetes: `kubectl get deployment grafana -o yaml | grep GF_SECURITY`

2. Reset admin password:
   - Docker: `docker exec ai-agents-grafana grafana-cli admin reset-admin-password <newpassword>`
   - Kubernetes: `kubectl exec <pod-name> -- grafana-cli admin reset-admin-password <newpassword>`

#### Port-Forward Connection Fails (Kubernetes)

**Cause**: Port 3000 in use or pod not running

**Solutions**:
1. Verify pod is running: `kubectl get pod -l app=grafana`
2. Use different local port: `kubectl port-forward svc/grafana 3001:3000`
3. Check pod logs: `kubectl logs -l app=grafana`

---

## Integration with Alerting (Story 4.4)

Grafana dashboards can be linked to Prometheus alerting rules:

1. Create alert rule in Prometheus (Story 4.4)
2. Dashboard panels can reference the same metrics
3. Alerts fire when thresholds are exceeded
4. Use AlertManager (Story 4.5) to route notifications

**Example Alert Rule:**
```yaml
- alert: HighErrorRate
  expr: rate(enhancement_requests_total{status="failure"}[5m]) > 0.05
  annotations:
    summary: "High error rate detected ({{ $value }}%)"
```

Panel visualization + alert rules = complete observability stack.

---

## Next Steps

### Immediate (After Story 4.3)
- Change default admin password
- Test dashboard with sample data
- Verify all panels display correct metrics
- Document tenant-specific dashboard customization

### Story 4.4: Alerting Rules
- Create Prometheus alert rules for critical thresholds
- Reference dashboard panels in alert annotations
- Implement alert condition testing

### Story 4.5: Alert Routing
- Configure Alertmanager for multi-channel notifications
- Integrate with Slack, PagerDuty, email
- Test end-to-end alert flow

### Story 4.6: Distributed Tracing
- Integrate OpenTelemetry for request tracing
- Correlate traces with metrics on dashboard
- Enhanced observability for performance debugging

---

## References

- [Grafana Official Documentation](https://grafana.com/docs/grafana/latest/)
- [Prometheus Datasource Configuration](https://grafana.com/docs/grafana/latest/datasources/prometheus/)
- [Dashboard Provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/)
- [PromQL Query Language](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- Story 4.1: Prometheus Metrics Instrumentation - `/docs/operations/metrics-guide.md`
- Story 4.2: Prometheus Server Deployment - `/docs/operations/prometheus-setup.md`
