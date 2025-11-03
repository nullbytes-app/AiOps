# Alertmanager Setup Guide

## Overview

Alertmanager is the alert routing and notification layer that receives fired alerts from Prometheus and delivers them to configured notification channels (Slack, PagerDuty, Email). This guide documents the Alertmanager deployment, configuration, and integration with Prometheus.

**Story Reference:** Story 4.5 - Integrate Alertmanager for Alert Routing

---

## Architecture

```
Application Metrics (Story 4.1)
        ↓
Prometheus Server (Story 4.2)
        ↓
Alert Rules Fire (Story 4.4)
        ↓
Alertmanager Routes Alerts (Story 4.5) ← YOU ARE HERE
        ↓
Slack/PagerDuty/Email Notifications
```

**Alert Flow:**
1. Prometheus evaluates alert rules every 15 seconds
2. When condition is met for the `for:` duration, alert transitions to **Firing** state
3. Prometheus sends fired alert to Alertmanager via HTTP POST
4. Alertmanager receives alert and applies routing rules
5. Alertmanager groups related alerts (by `group_by` labels)
6. Alertmanager sends grouped alert to configured receivers:
   - **Critical alerts** → Slack + PagerDuty
   - **Warning alerts** → Slack only
   - **Optional:** Email (secondary channel)

---

## Deployment

### Local Development (Docker Compose)

**Configuration Files:**
- `alertmanager.yml` - Alertmanager configuration (routing, receivers, grouping)
- `prometheus.yml` - Updated with `alerting:` section to point to Alertmanager
- `docker-compose.yml` - Alertmanager service definition

**Startup:**
```bash
# Start full stack
docker-compose up -d

# Start only Alertmanager (requires Prometheus running)
docker-compose up -d alertmanager

# View logs
docker-compose logs -f alertmanager

# Health check
curl http://localhost:9093/-/healthy
```

**Ports:**
- `9093` - Alertmanager UI and API endpoint

### Production (Kubernetes)

**Configuration Files:**
- `k8s/alertmanager-deployment.yaml` - Deployment, Service, ConfigMap, Secret
- `k8s/alertmanager-secrets.template.yaml` - Secret template with placeholder values

**Deployment:**
```bash
# Create secrets with actual values (from template)
kubectl apply -f k8s/alertmanager-secrets.template.yaml

# Update secret with real credentials
kubectl patch secret alertmanager-secrets -p='{"data":{"slack-webhook-url":"'$(echo -n "ACTUAL_WEBHOOK_URL" | base64)'"}}' --type=merge

# Deploy Alertmanager
kubectl apply -f k8s/alertmanager-deployment.yaml

# Verify deployment
kubectl get pods | grep alertmanager
kubectl get svc alertmanager
kubectl logs -f deployment/alertmanager
```

---

## Configuration

### Global Settings

**File:** `alertmanager.yml` (global section)

```yaml
global:
  resolve_timeout: 5m  # Time to wait before marking alert as resolved
```

### Alert Routing Rules

**Route Tree Structure:**

```yaml
route:
  receiver: 'slack-default'        # Default receiver for alerts
  group_by: ['tenant_id', 'alertname']  # Group alerts by these labels
  group_wait: 10s      # Wait before sending notification for group
  group_interval: 15s  # Wait before sending notification about new alert in group
  repeat_interval: 4h  # How often to repeat notification for ongoing alert

  routes:
    # Critical alerts (severity=critical) → Slack + PagerDuty
    - match:
        severity: critical
      receiver: 'slack-pagerduty'
      continue: false

    # Warning alerts (severity=warning) → Slack only
    - match:
        severity: warning
      receiver: 'slack-default'
      continue: false
```

**Routing Logic:**
- Root route catches all alerts (default receiver: `slack-default`)
- Critical alerts are re-routed to `slack-pagerduty` receiver
- Warning alerts remain on default `slack-default` receiver
- `continue: false` prevents alert from matching multiple routes

### Receivers (Notification Channels)

#### Slack Integration

**Configuration:**
```yaml
receivers:
  - name: 'slack-default'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/...'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
        color: '#FFA500'  # Orange for warnings
        fields:
          - title: 'Severity'
            value: '{{ .GroupLabels.severity }}'
          - title: 'Tenant'
            value: '{{ .GroupLabels.tenant_id }}'
```

**Setup Instructions:**

1. **Create Slack Incoming Webhook:**
   - Go to Slack workspace → App Directory
   - Search for "Incoming WebHooks"
   - Create New Webhook for your alert channel
   - Copy the webhook URL: `https://hooks.slack.com/services/T.../B.../...`

2. **Store Webhook URL:**
   - **Local Dev:** Add to `.env` file:
     ```
     SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
     ```
   - **Kubernetes:** Create secret with real URL:
     ```bash
     kubectl create secret generic alertmanager-secrets \
       --from-literal=slack-webhook-url="https://hooks.slack.com/services/..."
     ```

3. **Update alertmanager.yml:**
   - Change placeholder `https://hooks.slack.com/services/placeholder` to real webhook URL
   - In production, use Kubernetes Secret injection instead

#### PagerDuty Integration

**Configuration:**
```yaml
receivers:
  - name: 'slack-pagerduty'
    pagerduty_configs:
      - routing_key: 'YOUR_INTEGRATION_KEY'
        description: '{{ .GroupLabels.alertname }}'
        details:
          firing: '{{ template "pagerduty.default.instances" .Alerts.Firing }}'
          severity: 'critical'
```

**Setup Instructions:**

1. **Create PagerDuty Integration:**
   - Log in to PagerDuty account
   - Go to Service Settings → Integrations
   - Add integration for "Prometheus" (or generic webhook)
   - Copy the integration/routing key

2. **Store Integration Key:**
   - **Local Dev:** Add to `.env`:
     ```
     PAGERDUTY_INTEGRATION_KEY=your-key-here
     ```
   - **Kubernetes:** Create secret:
     ```bash
     kubectl create secret generic alertmanager-secrets \
       --from-literal=pagerduty-integration-key="your-key-here"
     ```

3. **Update alertmanager.yml:**
   - Replace placeholder with actual key

#### Email Integration (Optional)

**Configuration:**
```yaml
receivers:
  - name: 'email'
    email_configs:
      - to: 'oncall@example.com'
        from: 'alerts@ai-agents.local'
        smarthost: 'smtp.example.com:587'
        auth_username: 'your-smtp-user'
        auth_password: 'your-smtp-password'
```

**Common SMTP Servers:**
- **Gmail:** `smtp.gmail.com:587` (use App Password, not regular password)
- **SendGrid:** `smtp.sendgrid.net:587` (username: `apikey`, password: your API key)
- **Company SMTP:** Check with IT for `smarthost` and credentials

---

## Alert Rules Integration

### Available Alert Rules (from Story 4.4)

Alertmanager routes these four alert rules:

| Alert | Severity | Trigger Condition | Runbook |
|-------|----------|-------------------|---------|
| **EnhancementSuccessRateLow** | warning | Success rate < 95% | Check API credentials, restart workers |
| **QueueDepthHigh** | warning | Queue depth > 100 | Scale workers, monitor drain rate |
| **WorkerDown** | critical | 0 workers healthy | Restart immediately, check Redis |
| **HighLatency** | warning | Response time > 120s | Check external API, optimize context |

### Alert Labels

All alerts include these labels for routing and grouping:
```yaml
labels:
  severity: warning|critical  # Used for routing decisions
  tenant_id: <tenant-id>      # Used for grouping by tenant
  instance: <prometheus-instance>  # Source of metric
  alertname: <alert-name>     # Alert rule name
```

---

## Testing & Validation

### Test Local Alertmanager

**Check Health:**
```bash
curl http://localhost:9093/-/healthy
# Expected output: OK
```

**Access UI:**
- http://localhost:9093 (Alerts page shows fired alerts and routing)

### Test Slack Integration

**Manual Test (requires actual Slack webhook):**

1. **Update `.env` with real Slack webhook URL**
2. **Update alertmanager.yml with webhook URL**
3. **Restart Alertmanager:**
   ```bash
   docker-compose restart alertmanager
   ```
4. **Trigger test alert (in Prometheus):**
   - Go to http://localhost:9090
   - Alerts page → Manually fire alert (if supported)
   - Or reduce metric below threshold to naturally trigger alert

5. **Verify Slack notification received within 15 seconds**

### Test Alert Routing

**Test Warning Alert (Slack only):**
1. Trigger `EnhancementSuccessRateLow` alert (warning severity)
2. Verify notification in Slack channel
3. Verify PagerDuty NOT triggered

**Test Critical Alert (Slack + PagerDuty):**
1. Trigger `WorkerDown` alert (critical severity)
2. Verify notification in Slack channel
3. Verify incident created in PagerDuty

### Test Alert Grouping

**Verify grouping prevents notification spam:**
1. Send 3 identical alerts within 1 minute
2. Expected: Receive 1 grouped notification (not 3 separate)
3. Check `group_wait: 10s` and `group_interval: 15s` behavior

---

## Troubleshooting

### Alertmanager Not Receiving Alerts from Prometheus

**Check Prometheus Configuration:**
```yaml
# In prometheus.yml, verify alerting section exists:
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - 'alertmanager:9093'
```

**Verify Prometheus sees Alertmanager:**
- Go to http://localhost:9090/status → Alerts page
- Should show "Alertmanager Targets" with alertmanager:9093
- Status should be "UP" (green)

**Check Alertmanager Logs:**
```bash
docker-compose logs alertmanager
# Look for "Completed loading configuration file" and "No errors parsing"
```

### Slack Notifications Not Received

**Verify Webhook URL:**
1. Check `.env` file has correct `SLACK_WEBHOOK_URL`
2. Test webhook directly:
   ```bash
   curl -X POST -H 'Content-type: application/json' \
     --data '{"text":"Test message"}' \
     YOUR_SLACK_WEBHOOK_URL
   ```
   Should receive message in Slack channel

**Check alertmanager.yml:**
- Verify `slack_configs:` → `api_url:` matches webhook URL
- Check routing rules match alert severity

**Check Alertmanager Logs:**
```bash
docker-compose logs alertmanager | grep -i slack
# Look for error messages
```

### PagerDuty Incidents Not Created

**Verify Integration Key:**
1. Check `.env` has `PAGERDUTY_INTEGRATION_KEY` set
2. Verify key is from PagerDuty service integrations (not API key)

**Test PagerDuty Endpoint:**
- PagerDuty API is at `https://events.pagerduty.com/v2/enqueue`
- Requires routing key and JSON payload

**Check Alertmanager Logs:**
```bash
docker-compose logs alertmanager | grep -i pagerduty
```

### Email Alerts Not Delivered

**Verify SMTP Configuration:**
```bash
# Test SMTP connection
telnet smtp.example.com 587
# Should connect without errors
```

**Check Credentials:**
- Username and password must match SMTP server requirements
- For Gmail: Use App Password (not regular password)
- For SendGrid: Username is `apikey`

**Check Alertmanager Logs:**
```bash
docker-compose logs alertmanager | grep -i smtp
```

---

## Operations

### Viewing Fired Alerts

**In Alertmanager UI:**
- Go to http://localhost:9093
- Alerts page shows all currently firing alerts
- Grouped by receiver and routing rules
- Shows alert labels, grouping key, and time fired

**In Prometheus UI:**
- Go to http://localhost:9090
- Alerts page shows alert rules and firing status
- Useful for seeing raw alert details before grouping

### Managing Alert Silence

**Temporarily Silence Alert (in Alertmanager UI):**
1. Go to http://localhost:9093
2. Find alert in list
3. Click "Silence" button
4. Set duration and reason
5. Silenced alerts won't send notifications

### Reloading Configuration

**Without Downtime:**

```bash
# Local Docker
docker-compose restart alertmanager

# Kubernetes
kubectl rollout restart deployment/alertmanager
```

**After Configuration Change:**
1. Update alertmanager.yml or alertmanager-secrets
2. Reload Alertmanager using above commands
3. Verify health check: `curl http://localhost:9093/-/healthy`

---

## Performance & Scaling

### Resource Limits

**Current Settings (Kubernetes):**
```yaml
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 256Mi
```

**When to Scale:**
- If processing > 1000 alerts/second, increase resource limits
- For high availability, increase replicas to 3
- Use PersistentVolumeClaim for data persistence (currently emptyDir)

### Alert Delivery Latency

**Expected Timeline:**
- Prometheus evaluation: ~15s (scrape + rule evaluation intervals)
- Alert → Alertmanager: < 1s
- Alertmanager processing: < 1s
- Webhook delivery: < 2s
- **Total: ~15-20 seconds** (dominated by Prometheus evaluation)

**Grouping Impact:**
- `group_wait: 10s` - delays notification by up to 10s to batch similar alerts
- `group_interval: 15s` - delays new alerts in group by 15s
- Trade-off: Lower notification count vs. higher latency

---

## Runbooks

### Troubleshooting High Latency Alert

**When `HighLatency` alert fires:**

1. **Check OpenRouter API status:**
   - Prometheus dashboard → Graph tab
   - Query: `rate(enhancement_duration_seconds_sum[5m]) / rate(enhancement_duration_seconds_count[5m])`
   - Threshold: > 120 seconds

2. **Investigate Root Cause:**
   - Check OpenRouter API status page
   - Verify network connectivity to OpenRouter
   - Check context gathering (query database, external APIs)

3. **Resolution Steps:**
   - Increase LLM timeout: `AI_AGENTS_LLM_TIMEOUT_SECONDS=60`
   - Optimize context queries (add indexes to database)
   - Consider caching context for frequently accessed documents

4. **Escalation:**
   - If latency persists > 5 minutes, page on-call engineer
   - Consider reducing batch size or implementing rate limiting

### Troubleshooting Queue Depth High

**When `QueueDepthHigh` alert fires:**

1. **Check Queue Depth Metric:**
   - Prometheus: `enhancement_queue_depth`
   - Threshold: > 100 jobs queued

2. **Scale Workers:**
   ```bash
   # Kubernetes
   kubectl scale deployment ai-agents-worker --replicas=8

   # Docker Compose (manual restart with more concurrency)
   # Update docker-compose.yml: celery concurrency
   ```

3. **Monitor Drain Rate:**
   - Query: `rate(enhancement_requests_total[1m])`
   - Should exceed job submission rate

4. **If Scaling Doesn't Help:**
   - Check worker logs for errors
   - Verify Redis connection (queue broker)
   - Check database for locks or timeouts

### Troubleshooting Worker Down

**When `WorkerDown` alert fires (CRITICAL):**

1. **Immediate Actions:**
   - Check worker pod status:
     ```bash
     kubectl get pods | grep worker
     ```
   - Check worker logs:
     ```bash
     kubectl logs -l app=worker --tail=50
     ```

2. **Restart Workers:**
   ```bash
   # Kubernetes
   kubectl rollout restart deployment/ai-agents-worker

   # Docker Compose
   docker-compose restart worker
   ```

3. **Verify Redis Connectivity:**
   ```bash
   # From worker pod
   redis-cli -h redis ping
   # Should return PONG
   ```

4. **Check Resource Constraints:**
   - Worker may be OOMKilled (out of memory)
   - Verify resource limits in deployment
   - Check node resources (CPU, memory available)

5. **Escalation:**
   - If workers repeatedly fail, page on-call engineer
   - Consider increasing resource limits or worker count

---

## Secret Rotation and Credential Management

### Rotating Slack Webhook URL

**Docker Compose Local Development:**

1. **Generate new Slack webhook:**
   - Go to Slack workspace → Settings → Apps & Integrations
   - Manage app for your Slack channel
   - Regenerate the webhook URL

2. **Update local alertmanager.yml:**
   ```bash
   # Edit alertmanager.yml and replace api_url
   vi alertmanager.yml
   # Update the Slack receiver api_url with the new webhook URL
   ```

3. **Restart Alertmanager:**
   ```bash
   docker-compose restart alertmanager
   ```

4. **Verify:**
   ```bash
   curl http://localhost:9093/-/healthy
   ```

**Kubernetes Production:**

1. **Update Kubernetes secret (no pod restart needed):**
   ```bash
   # Create new secret with updated webhook URL
   kubectl create secret generic alertmanager-slack-webhook \
     --from-literal=url="https://hooks.slack.com/services/..." \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

2. **Reload Alertmanager configuration:**
   ```bash
   # Trigger pod restart to load new secret
   kubectl rollout restart deployment/alertmanager

   # Verify new pods are running
   kubectl get pods | grep alertmanager
   ```

3. **Verify connectivity:**
   ```bash
   kubectl logs -f deployment/alertmanager | grep -i "config"
   ```

### Rotating PagerDuty Integration Key

**Docker Compose:**

1. **Get new integration key from PagerDuty:**
   - Service → Integrations → Create Integration
   - Copy the routing key

2. **Update alertmanager.yml:**
   ```bash
   vi alertmanager.yml
   # Update the PagerDuty receiver routing_key
   ```

3. **Restart:**
   ```bash
   docker-compose restart alertmanager
   ```

**Kubernetes:**

1. **Update secret:**
   ```bash
   kubectl create secret generic alertmanager-pagerduty-key \
     --from-literal=routing-key="..." \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

2. **Restart pods:**
   ```bash
   kubectl rollout restart deployment/alertmanager
   ```

### Rotating SMTP Credentials

**Docker Compose:**

1. **Update alertmanager.yml:**
   ```bash
   vi alertmanager.yml
   # Update email section: smtp_auth_username, smtp_auth_password
   ```

2. **Restart:**
   ```bash
   docker-compose restart alertmanager
   ```

**Kubernetes:**

1. **Update secret:**
   ```bash
   kubectl create secret generic alertmanager-smtp-credentials \
     --from-literal=username="new-user" \
     --from-literal=password="new-password" \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

2. **Restart:**
   ```bash
   kubectl rollout restart deployment/alertmanager
   ```

### Best Practices for Secret Rotation

- **Frequency:** Rotate credentials every 90 days (or immediately if compromised)
- **No downtime:** Kubernetes secrets can be updated without service interruption
- **Testing:** Test notification delivery after rotation using a test alert
- **Backup:** Keep old credentials for 24 hours in case rollback is needed
- **Documentation:** Log credential rotation events with timestamps for audit trail
- **Never commit secrets:** Use `.env` files and Kubernetes Secrets, never commit to git

---

## References

- [Alertmanager Official Docs](https://prometheus.io/docs/alerting/latest/overview/)
- [Alertmanager Configuration](https://prometheus.io/docs/alerting/latest/configuration/)
- [Slack Integration](https://prometheus.io/docs/alerting/latest/configuration/#slack_config)
- [PagerDuty Integration](https://prometheus.io/docs/alerting/latest/configuration/#pagerduty_config)
- [Story 4.4: Alert Rules Configuration](./prometheus-alert-rules.md)
- [Story 4.2: Prometheus Deployment](./prometheus-setup.md)

