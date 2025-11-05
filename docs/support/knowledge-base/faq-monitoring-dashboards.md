# FAQ: Monitoring Dashboards

**Category:** FAQ - Observability & Monitoring
**Severity:** P3 (informational/training)
**Last Updated:** 2025-11-04
**Related Runbooks:** N/A (informational guide)

---

## Quick Answer

**Access Grafana dashboards** at http://localhost:3000 (local) or production Grafana URL. Two main dashboards: **Operations Dashboard** (real-time system health) and **Baseline Metrics Dashboard** (client satisfaction and success criteria). Default login: admin/admin (change on first use).

---

## Symptoms

**Support Team Questions:**
- "How do I access Grafana?"
- "Which dashboard should I use for incident response?"
- "What do these metrics mean?"
- "Cannot login to Grafana"

---

## Grafana Access

### Local Development
- URL: http://localhost:3000
- Default Login: admin / admin (prompted to change on first login)
- Dashboards: Grafana → Dashboards → Browse

### Production
- URL: Provided by Engineering (e.g., https://grafana.ai-agents.com)
- Login: SSO or credentials provided during onboarding
- Access: Contact Engineering if unable to login

---

## Available Dashboards

### 1. Operations Dashboard (Primary for Incident Response)

**Purpose:** Real-time system health monitoring during incidents

**Key Panels:**
1. **API Latency (p50, p95, p99):** Response time for webhook receiver
   - Target: p95 <1s, p99 <2s
   - Red: p95 >3s (investigate API timeout issues)

2. **Queue Depth:** Number of jobs waiting for workers
   - Healthy: <20 jobs
   - Elevated: 20-50 jobs (monitor, may need scaling)
   - High: >50 jobs (scale workers immediately)

3. **Worker Health:** Worker pod status and count
   - Shows: Running workers, crashed workers, CPU/memory usage
   - Red: Workers in CrashLoopBackOff (escalate)

4. **Database Connections:** Active database connections
   - Target: <80% of max_connections (100 connections)
   - Red: >80% (connection pool exhaustion, escalate)

5. **Error Rate:** Percentage of failed enhancement jobs
   - Healthy: <1% error rate
   - Warning: 1-5% (investigate errors)
   - Critical: >5% (escalate to Engineering)

6. **Success Rate:** Percentage of successful enhancements
   - Target: >95% success rate (Story 5.5 baseline)
   - Warning: <95% (quality degradation)

7. **External API Latency:** ServiceDesk Plus and OpenAI response times
   - ServiceDesk Plus target: p95 <2s
   - OpenAI target: p95 <5s
   - Use for diagnosing slow enhancements

**When to Use:**
- P0/P1 incidents (first dashboard to open)
- Daily shift handoff health checks
- Proactive monitoring (reviewing trends)

---

### 2. Baseline Metrics Dashboard (Client Satisfaction & Success Criteria)

**Purpose:** Track success criteria and client satisfaction (Story 5.5)

**Key Panels:**
1. **Average Feedback Rating:** Client technician satisfaction (1-5 scale)
   - Target: >4.0 (Story 5.5 success criterion: >4/5)
   - Warning: <4.0 (investigate quality issues)

2. **Feedback Sentiment:** Thumbs up vs thumbs down ratio
   - Target: >80% thumbs up
   - Shows: Client satisfaction trend over time

3. **Enhancement Success Rate:** Percentage of successful enhancements
   - Target: >95% (Story 5.5 success criterion)
   - Tracks: 7-day rolling average

4. **p95 Enhancement Latency:** Time from ticket received to enhancement delivered
   - Target: <60s (Story 5.5 success criterion)
   - Measures: End-to-end performance

5. **Throughput:** Enhancements processed per hour
   - Baseline: Established during 7-day collection period
   - Use for: Capacity planning, trend analysis

6. **Research Time Reduction:** Estimated time saved for technicians
   - Target: >20% reduction (Story 5.5 success criterion)
   - Calculated: From feedback and ticket resolution times

**When to Use:**
- Weekly metrics review with stakeholders
- Client quarterly business reviews (QBRs)
- Evaluating enhancement quality trends
- Capacity planning for client growth

---

## Common Prometheus Queries

### Check Queue Depth
```promql
redis_queue_length{queue="celery"}
```

### API p95 Latency
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{endpoint="/api/v1/webhooks/servicedesk-plus"}[5m]))
```

### Worker CPU Usage
```promql
avg(rate(container_cpu_usage_seconds_total{pod=~"ai-agents-worker.*"}[5m])) by (pod)
```

### Enhancement Success Rate (Last Hour)
```promql
(sum(rate(enhancement_success_total[1h])) / sum(rate(enhancement_total[1h]))) * 100
```

### Database Connection Count
```promql
pg_stat_database_numbackends{datname="ai_agents"}
```

---

## Dashboard Interpretation

### Scenario 1: "Queue Depth Spiking"
- **Panel:** Queue Depth (Operations Dashboard)
- **Symptoms:** Queue depth >50 and trending up
- **Diagnosis:** Check Worker Health panel → Are workers healthy? Check External API Latency → Are APIs slow?
- **Action:** Scale workers if healthy, investigate worker crashes if unhealthy

### Scenario 2: "Client Complaining About Slow Enhancements"
- **Panel:** p95 Enhancement Latency (Baseline Metrics Dashboard)
- **Symptoms:** p95 >60s (baseline target)
- **Diagnosis:** Check Queue Depth and External API Latency (Operations Dashboard)
- **Action:** See [FAQ: Slow Enhancements](faq-slow-enhancements.md)

### Scenario 3: "Low Feedback Ratings"
- **Panel:** Average Feedback Rating (Baseline Metrics Dashboard)
- **Symptoms:** Rating <3.5 and trending down
- **Diagnosis:** Review feedback comments via Feedback API
- **Action:** See [FAQ: Low Quality Enhancements](faq-low-quality-enhancements.md)

### Scenario 4: "High Error Rate"
- **Panel:** Error Rate (Operations Dashboard)
- **Symptoms:** Error rate >5%
- **Diagnosis:** Check Worker Health, Database Connections, External API Latency
- **Action:** See [Troubleshooting: High Error Rate](troubleshooting-high-error-rate.md)

---

## Dashboard Configuration

### Adding New Panels (Engineering Only)
- Grafana dashboards configured via k8s/grafana-dashboard-*.yaml
- Editing requires Engineering access and kubectl apply
- Request changes via #engineering-support Slack channel

### Adjusting Alert Thresholds (Engineering Only)
- Alert rules in k8s/prometheus-alert-rules.yaml
- Contact Engineering to adjust thresholds (e.g., queue depth >50 → >100)

### Creating Custom Dashboards
- Support Team Lead can create personal dashboards in Grafana
- Use existing dashboards as templates (clone and modify)
- Share useful custom dashboards with team

---

## Troubleshooting Dashboard Access

### Cannot Login to Grafana
```bash
# Reset Grafana admin password (local development only)
kubectl exec -it deployment/grafana -n monitoring -- grafana-cli admin reset-admin-password <new-password>

# Production: Contact Engineering for SSO setup or password reset
```

### Dashboard Not Loading
- Check Prometheus datasource: Grafana → Configuration → Data Sources → Prometheus
- Should show: "Data source is working"
- If not: Escalate to Engineering (Prometheus may be down)

### Missing Data in Panels
- Check time range (top right): Should be "Last 6 hours" or "Last 24 hours"
- Check namespace filter (if present): Should match production namespace
- If still missing: May be metrics collection issue, escalate to Engineering

### Panels Showing "No Data"
- Verify Prometheus is scraping metrics: http://localhost:9090/targets (all targets should be "UP")
- Check time range (data may be outside selected range)
- Verify metric name in panel query (may be typo)

---

## Training Resources

**New Support Team Members:**
1. Watch recorded training session (Story 5.6) - includes Grafana walkthrough
2. Practice: Open Operations Dashboard, identify each panel's purpose
3. Simulate: Use past incident (e.g., Story 5.2 deployment issues) to practice dashboard navigation
4. Hands-on: During next incident, shadow L2 engineer observing dashboard usage

**Recommended Practice:**
- Daily: Review Operations Dashboard during shift start (health check)
- Weekly: Review Baseline Metrics Dashboard (client satisfaction trends)
- Monthly: Correlate incidents with dashboard metrics (what patterns preceded P1?)

---

## Related Articles

- [FAQ: Slow Enhancements](faq-slow-enhancements.md) - Use Operations Dashboard to diagnose
- [Troubleshooting: High Error Rate](troubleshooting-high-error-rate.md) - Error Rate panel interpretation
- [Production Support Guide](../production-support-guide.md) - System health checks using dashboards

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-04 | Initial creation (Code Review follow-up) | Dev Agent (AI) |
