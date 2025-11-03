# Logging Infrastructure - Story 3.7

Comprehensive guide for setting up, managing, and troubleshooting the AI Agents audit logging infrastructure on Kubernetes.

---

## Architecture Overview

The logging system follows a containerized, cloud-native approach aligned with Kubernetes best practices:

```
┌─────────────────────────────────────────────────────────────────┐
│                       Kubernetes Cluster                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────┐       ┌──────────────────┐                │
│  │  API Container  │       │ Worker Container │                │
│  │  (FastAPI)      │       │  (Celery)        │                │
│  │                 │       │                  │                │
│  │ - Webhook       │       │ - Enhancement    │                │
│  │ - Logs to       │       │   Tasks          │                │
│  │   STDOUT/STDERR │       │ - Logs to        │                │
│  │ - JSON format   │       │   STDOUT/STDERR  │                │
│  │ - 90-day        │       │ - JSON format    │                │
│  │   retention     │       │                  │                │
│  └─────────────────┘       └──────────────────┘                │
│           │                         │                            │
│           └────────────┬────────────┘                            │
│                        │ (STDOUT/STDERR)                        │
│                        ▼                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │        Kubelet (Container Runtime)                      │   │
│  │  - Captures STDOUT/STDERR from containers              │   │
│  │  - Writes to /var/log/pods/                            │   │
│  │  - Buffered output                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                        │                                         │
│                        ▼                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │     Log Collector (Fluentd / Fluent Bit)               │   │
│  │  - Tails container logs                                │   │
│  │  - Parses JSON format                                  │   │
│  │  - Enriches with metadata (pod, namespace, node)       │   │
│  │  - Buffers and flushes                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                        │                                         │
│                        ▼                                         │
└─────────────────────────────────────────────────────────────────┘
                         │
       ┌─────────────────┼─────────────────┐
       │                 │                 │
       ▼                 ▼                 ▼
  ┌─────────┐    ┌────────────┐   ┌──────────────┐
  │   ES/   │    │   Grafana  │   │   S3/GCS     │
  │ Logstash│    │   Loki     │   │  (Archive)   │
  │         │    │            │   │              │
  │ (Hot    │    │ (Metrics & │   │ (Compliance) │
  │ Storage)│    │  Alerting) │   │ (90+ days)   │
  └─────────┘    └────────────┘   └──────────────┘
```

---

## Container Log Collection Strategy

### Why stdout/stderr in Containers?

1. **Cloud-native standard**: Kubernetes expects logs on stdout/stderr
2. **Decoupled logging**: Application doesn't manage files; runtime does
3. **Horizontal scaling**: Multiple instances automatically contribute
4. **Automatic rotation**: Kubelet manages log rotation
5. **Simple configuration**: No need for sidecar containers (initially)

### Log Flow

1. **Application writes to stdout/stderr**
   - Python `loguru` configured to output JSON to `sys.stderr`
   - No file writes in containerized environment
   - Single stream per container (combined stdout/stderr)

2. **Kubelet captures logs**
   - Stores in `/var/log/pods/<namespace>_<pod>_<uid>/`
   - Rotates when logs exceed size limits (10MB default)
   - Keeps 5 rotated files by default

3. **Log aggregator collects**
   - Fluentd/Fluent Bit tails the files
   - Parses JSON (one-line format)
   - Adds Kubernetes metadata

4. **Log backend stores**
   - Elasticsearch: Hot storage (current + recent)
   - S3/GCS: Cold storage (archives 90+ days)

---

## Recommended Log Aggregators

### Option 1: Fluentd (Full-Featured)

**Pros:**
- Rich plugin ecosystem
- Advanced filtering and routing
- Good for complex multi-sink scenarios
- Well-documented

**Cons:**
- Higher resource consumption (Ruby-based)
- Requires more configuration
- Slower startup time

**Installation:**
```bash
# Using Helm
helm repo add fluent https://fluent.github.io/helm-charts
helm repo update
helm install fluent-bit fluent/fluent-bit \
  --namespace logging --create-namespace
```

**Config Example:**
```yaml
[INPUT]
    Name              tail
    Path              /var/log/pods/ai-agents_*/*.log
    Parser            docker
    Tag               kube.*
    Refresh_Interval  5
    Skip_Long_Lines   On

[FILTER]
    Name    kubernetes
    Match   kube.*
    Kube_URL https://kubernetes.default.svc:443
    Labels  On
    Annotations Off

[OUTPUT]
    Name   es
    Match  *
    Host   elasticsearch.logging
    Port   9200
    Index  ai-agents-%Y.%m.%d
```

### Option 2: Fluent Bit (Lightweight)

**Pros:**
- Minimal resource footprint (C-based)
- Fast startup
- Perfect for Kubernetes
- Easier configuration

**Cons:**
- Smaller plugin ecosystem
- Less powerful filtering
- May need multiple outputs for complex routing

**Installation:**
```bash
# Using Helm
helm repo add fluent https://fluent.github.io/helm-charts
helm repo update
helm install fluent-bit fluent/fluent-bit \
  --namespace logging --create-namespace \
  --set config.outputs.es.enabled=true \
  --set config.outputs.s3.enabled=true
```

### Option 3: Grafana Loki (Lightweight + Built-in Metrics)

**Pros:**
- Minimal storage footprint
- Index-free (label-based)
- Native Grafana integration
- Excellent for Kubernetes
- Built-in alerting

**Cons:**
- Different query syntax (LogQL vs. Kibana)
- Less mature than Elasticsearch
- Newer tool

**Installation:**
```bash
# Using Helm
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
helm install loki-stack grafana/loki-stack \
  --namespace logging --create-namespace \
  --set loki.persistence.enabled=true \
  --set loki.persistence.size=50Gi
```

**Promtail Config:**
```yaml
clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: kubernetes-pods
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_namespace]
        target_label: namespace
      - source_labels: [__meta_kubernetes_pod_name]
        target_label: pod
```

---

## Log Retention Policy

### Hot Storage (Elasticsearch / Loki)

- **Duration**: 30 days (current month + recent)
- **Retention by size**: Index-based rotation
- **Access speed**: Instant
- **Use case**: Live monitoring, debugging, real-time alerting

### Warm Storage (Optional - NFS / Object Storage)

- **Duration**: 31-60 days
- **Retention by date**: Monthly indices moved to warm tier
- **Access speed**: Slow (manual retrieval)
- **Use case**: Extended investigation window

### Cold Storage (S3 / GCS)

- **Duration**: 90+ days (compliance requirement per NFR005)
- **Retention by date**: Month-based archives
- **Access speed**: Very slow (glacier/coldline)
- **Use case**: Compliance, legal holds, historical analysis

### Deletion Policy

- **Hot tier**: Auto-delete after 30 days
- **Warm tier**: Auto-delete after 60 days
- **Cold tier**: Keep indefinitely (compliance archive)

**Automated deletion in Elasticsearch:**
```bash
# ILM (Index Lifecycle Management) policy
PUT _ilm/policy/ai-agents-policy
{
  "policy": "ai-agents-policy",
  "phases": {
    "hot": {
      "min_age": "0d",
      "actions": {
        "rollover": {
          "max_docs": 5000000,
          "max_age": "1d"
        }
      }
    },
    "warm": {
      "min_age": "1d",
      "actions": {
        "set_priority": {
          "priority": 50
        }
      }
    },
    "cold": {
      "min_age": "30d",
      "actions": {
        "set_priority": {
          "priority": 0
        }
      }
    },
    "delete": {
      "min_age": "90d",
      "actions": {
        "delete": {}
      }
    }
  }
}
```

---

## Log Volume Estimation

### Per-Request Log Size

- **Webhook received**: ~500 bytes
- **Job queued**: ~400 bytes
- **Enhancement started**: ~500 bytes
- **Context gathering (per node)**: ~300 bytes × 3 nodes = 900 bytes
- **LLM synthesis**: ~600 bytes
- **API call success**: ~400 bytes
- **API call retry**: ~350 bytes × (0-3 retries)
- **Enhancement completed**: ~600 bytes
- **Enhancement failed**: ~700 bytes

**Total per request**: ~5,000-6,000 bytes (5-6 KB)

### Cluster Volume Projections

**Assumptions:**
- 10 enhancements per minute (600/hour)
- 8 hour operational window per day
- 5KB average log size per request

**Daily volume:**
- Requests: 600/hour × 8 hours = 4,800 requests/day
- Log size: 4,800 × 5 KB = 24 MB/day

**Monthly volume:**
- 24 MB/day × 30 days = 720 MB/month

**Storage requirements:**
- Hot tier (30 days): 720 MB
- Warm tier (30 days): 720 MB
- Cold tier (90 days): 2.16 GB

**Scaling example** (100 req/hour):
- Daily: 240 MB/day
- Monthly: 7.2 GB/month
- Hot tier: 7.2 GB
- Cold tier: 21.6 GB

---

## Docker Configuration

### Dockerfile - Ensuring Unbuffered Output

```dockerfile
FROM python:3.11-slim

# Critical: Unbuffered Python output for immediate log visibility
ENV PYTHONUNBUFFERED=1

# Recommended: No bytecode caching (smaller image, faster startup)
ENV PYTHONDONTWRITEBYTECODE=1

# Logging configuration
ENV LOG_FILE_ENABLED=false
ENV LOG_LEVEL=INFO

# ... rest of Dockerfile ...
```

### Kubernetes Deployment - Disabling File Logging

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-agents-api
spec:
  template:
    spec:
      containers:
        - name: api
          image: ai-agents:latest
          imagePullPolicy: IfNotPresent
          env:
            # Disable file logging; output to stdout only
            - name: LOG_FILE_ENABLED
              value: "false"

            # Ensure unbuffered output
            - name: PYTHONUNBUFFERED
              value: "1"

            # Log level for production
            - name: LOG_LEVEL
              value: "INFO"

          # Capture logs immediately
          stdin: false
          tty: false

          # Log driver (optional - usually inherited from node)
          # Kubernetes uses default JSON file driver

          ports:
            - containerPort: 8000
              name: http

          # Resource limits ensure consistent performance
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
```

---

## Kubernetes Log Collection Setup

### DaemonSet for Fluent Bit

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: logging
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush         5
        Daemon        off
        Log_Level     info

    [INPUT]
        Name              tail
        Path              /var/log/pods/ai-agents_*/*.log
        Parser            docker
        Tag               kube.*
        Refresh_Interval  5
        Skip_Long_Lines   On
        Buffer_Chunk_Size 32k
        Buffer_Max_Size   256k

    [FILTER]
        Name    kubernetes
        Match   kube.*
        Kube_URL https://kubernetes.default.svc:443
        Kube_CA_File /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        Kube_Token_File /var/run/secrets/kubernetes.io/serviceaccount/token
        Labels  On

    [OUTPUT]
        Name   es
        Match  *
        Host   elasticsearch.logging
        Port   9200
        HTTP_User elastic
        HTTP_Passwd ${ELASTIC_PASSWORD}
        Retry_Limit 5
        Type   _doc

    [OUTPUT]
        Name   s3
        Match  archive.*
        bucket ai-agents-logs
        region us-east-1
        s3_key_format /logs/%Y/%m/%d/%H/%M/%S/$UUID.json
        total_file_size 10M
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
  namespace: logging
spec:
  selector:
    matchLabels:
      k8s-app: fluent-bit
  template:
    metadata:
      labels:
        k8s-app: fluent-bit
    spec:
      containers:
      - name: fluent-bit
        image: fluent/fluent-bit:2.0-distroless
        volumeMounts:
        - name: varlog
          mountPath: /var/log
          readOnly: true
        - name: varlibdockercontainers
          mountPath: /var/lib/docker/containers
          readOnly: true
        - name: config
          mountPath: /fluent-bit/etc
        resources:
          limits:
            memory: 256Mi
          requests:
            cpu: 100m
            memory: 128Mi
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
      - name: varlibdockercontainers
        hostPath:
          path: /var/lib/docker/containers
      - name: config
        configMap:
          name: fluent-bit-config
      serviceAccountName: fluent-bit
      tolerations:
      - key: node-role.kubernetes.io/master
        effect: NoSchedule
```

---

## Monitoring and Alerting

### Prometheus Metrics from Logs

```yaml
# Alert: High failure rate
- alert: EnhancementFailureRateHigh
  expr: |
    (count(rate(kube_pod_log_filter{status="failure"}[5m])) by (namespace)) /
    (count(rate(kube_pod_log_filter{operation=~"enhancement.*"}[5m])) by (namespace)) > 0.05
  for: 5m
  annotations:
    summary: "Enhancement failure rate > 5%"
    runbook: "docs/operations/runbooks/enhancement-failures.md"

# Alert: Missing logs from a service
- alert: MissingServiceLogs
  expr: |
    absent(rate(kube_pod_log_filter{service="worker"}[5m])) == 1
  for: 5m
  annotations:
    summary: "No logs from worker service in 5 minutes"

# Alert: High latency
- alert: EnhancementLatencyHigh
  expr: |
    histogram_quantile(0.95, duration_ms) > 60000
  for: 10m
  annotations:
    summary: "95th percentile enhancement latency > 60 seconds"
```

---

## Compliance and Security

### Data Sensitivity

- **Redacted**: API keys, passwords, SSN, PII (emails, credit cards)
- **Not redacted**: Tenant ID, ticket ID, timestamps, operations
- **Verified by**: `SensitiveDataFilter` in `src/utils/logger.py`

### Audit Trail

- **Retention**: 90 days minimum (NFR005)
- **Immutability**: Archive to cold storage (S3 Glacier)
- **Access control**: RBAC on Elasticsearch/Loki queries
- **Encryption**: TLS for transit, encryption at rest recommended

### Compliance Reporting

```bash
# Generate compliance report for a month
MONTH="2025-11"
kubectl logs -n ai-agents -l app=ai-agents --since=$MONTH-01 --until=$MONTH-30 | \
  jq -s '{
    total_events: length,
    date_range: "'"$MONTH"'",
    operations: group_by(.operation) | map({op: .[0].operation, count: length}),
    error_rate: (map(select(.status=="failure")) | length) / length,
    tenants: group_by(.tenant_id) | length,
    redaction_check: (map(.message) | map(select(test("API_KEY|password|Bearer"))) | length) +
                     " unredacted secrets found (should be 0)"
  }' > compliance-report-$MONTH.json
```

---

## Troubleshooting

### Issue: No logs appearing in aggregator

**Steps:**
1. Check `PYTHONUNBUFFERED=1` in Docker environment
2. Check `LOG_FILE_ENABLED=false` in Pod env
3. Verify Fluent Bit/Fluentd DaemonSet is running on all nodes
4. Check log collector configuration: `kubectl logs -n logging -l app=fluent-bit`
5. Verify output sink accessibility (ES, Loki, S3)

### Issue: Logs showing \`[REDACTED]\` incorrectly

**Steps:**
1. Review `SensitiveDataFilter` regex patterns
2. Check for false positives in patterns
3. Test patterns against sample data
4. File issue if legitimate data is redacted

### Issue: High disk usage from logs

**Steps:**
1. Check Kubelet log rotation settings: `/etc/docker/daemon.json`
2. Reduce log level to WARNING in non-prod environments
3. Increase log aggregator buffer flush frequency
4. Verify cold storage archival is working

### Issue: Latency spike in log processing

**Steps:**
1. Check Fluent Bit buffer usage: `kubectl top pods -n logging`
2. Increase Fluent Bit buffer sizes (at cost of memory)
3. Verify Elasticsearch cluster health
4. Check network connectivity between nodes and aggregator

---

## Migration Guide

### From Local File Logging to Cloud Logging

1. **Phase 1**: Keep file logging + add stdout
   ```bash
   LOG_FILE_ENABLED=true
   # (also outputs to stdout)
   ```

2. **Phase 2**: Verify logs are flowing to aggregator
   ```bash
   kubectl logs -n ai-agents -l app=ai-agents | head -20
   ```

3. **Phase 3**: Disable file logging
   ```bash
   LOG_FILE_ENABLED=false
   ```

4. **Phase 4**: Monitor disk usage for 1 week
   - Verify no logs are stored on container filesystem
   - Confirm all logs are in aggregator

---

## Performance Considerations

| Component | CPU | Memory | Network | Storage |
|-----------|-----|--------|---------|---------|
| Fluent Bit (per node) | 100m | 128-256Mi | ~1 Mbps | None (streaming) |
| Elasticsearch (cluster) | 500m | 2-4Gi | Varies | 10 GB/day (3 replicas) |
| Loki (single node) | 200m | 512Mi | ~2 Mbps | 1 GB/day |
| Prometheus (metrics) | 200m | 512Mi | Minimal | 50 GB/30d (typical) |

---

## References

- [Kubernetes Logging](https://kubernetes.io/docs/concepts/cluster-administration/logging/)
- [Fluent Bit Documentation](https://docs.fluentbit.io/manual/)
- [Grafana Loki Docs](https://grafana.com/docs/loki/)
- [Elasticsearch Log Management](https://www.elastic.co/guide/en/kibana/)
- [Loguru Python Library](https://loguru.readthedocs.io/)
