# Operational Documentation - AI Agents Platform

**Last Updated:** 2025-11-03
**Scope:** Complete operational procedures, setup guides, and troubleshooting for AI Agents monitoring and observability stack

---

## Quick Navigation by Use Case

### I Need to...

| Task | Go To |
|------|-------|
| **Diagnose a production issue** | Start with [Operational Runbooks](#operational-runbooks) or [Alert Runbooks](#alert-based-runbooks) |
| **Set up monitoring for the first time** | [Setup Guides](#setup-guides) (in order: Prometheus → Grafana → Alertmanager → Distributed Tracing) |
| **Understand how alerts work** | [Alert Configuration](#alert-configuration) |
| **View system metrics** | [Grafana Dashboards](#grafana-dashboards) - Main dashboard at http://localhost:3000 |
| **Debug a specific request end-to-end** | [Distributed Tracing Setup](#distributed-tracing-setup-story-46) |
| **Add a new metric or alert** | [Prometheus Configuration Guide](#prometheus-setup-story-42) |
| **Troubleshoot a specific component** | [Component Troubleshooting](#component-troubleshooting) |

---

## Setup Guides

Complete guides for setting up each component of the monitoring and observability stack. **Follow in order** for new environments:

### Prometheus Setup (Story 4.2)
**File:** [`prometheus-setup.md`](./prometheus-setup.md)
**Purpose:** Configures Prometheus metrics collection server
**Content:**
- Prometheus architecture and scrape configuration
- Target configuration for application, PostgreSQL, Redis
- Query syntax and common PromQL patterns
- Troubleshooting Prometheus health and scrape failures
- Performance tuning for high cardinality metrics

**Key Decisions:** Scrape interval (15s), retention (15 days)

### Grafana Setup (Story 4.3)
**File:** [`grafana-setup.md`](./grafana-setup.md)
**Purpose:** Deploys visualization dashboards for metrics
**Content:**
- Grafana datasource configuration (Prometheus integration)
- Dashboard architecture and best practices
- Panel types and visualization options
- Dashboard provisioning via ConfigMaps (Kubernetes)
- User management and access control
- Performance optimization for real-time updates

**Key Components:** Main dashboard "AI Agents Platform Monitoring", system status panels, queue/worker/latency metrics

### Alertmanager Setup (Story 4.5)
**File:** [`alertmanager-setup.md`](./alertmanager-setup.md)
**Purpose:** Routes alerts to Slack, PagerDuty, Email
**Content:**
- Alertmanager architecture and routing tree
- Slack integration with templated messages
- PagerDuty integration for critical incidents
- Email notification setup
- Alert grouping and inhibition rules
- Testing alerting pipeline
- High-availability Alertmanager deployment

**Key Decisions:** Alert grouping (by alert name, instance), routing (critical → PagerDuty, warning → Slack)

### Distributed Tracing Setup (Story 4.6)
**File:** [`distributed-tracing-setup.md`](./distributed-tracing-setup.md)
**Purpose:** Enables end-to-end request tracing with OpenTelemetry + Jaeger
**Content:**
- OpenTelemetry instrumentation of application
- Jaeger deployment and collector configuration
- Span structure (webhook → queue → context gathering → LLM → ticket update)
- Jaeger UI navigation and search syntax
- Performance impact and sampler configuration
- Trace sampling strategy (sample all in dev, 1% in prod)
- Troubleshooting missing or incomplete traces

**Key Features:** Distributed tracing across webhook → queue → workers → external APIs, cross-tenant trace correlation, slow trace detection

---

## Alert Configuration

### Prometheus Alert Rules (Story 4.4)
**File:** [`prometheus-alerting.md`](./prometheus-alerting.md)
**Purpose:** Defines alert rules and thresholds
**Content:**
- Alert rule syntax and evaluation
- Threshold definitions for 4 core alerts
- Alert grouping and severity levels
- Annotation templates including runbook URLs
- Testing alert rules locally

**Alert Rules Defined:**
- **EnhancementSuccessRateLow:** Success rate < 95% for 5 minutes
- **QueueDepthHigh:** Queue depth > 100 jobs
- **WorkerDown:** No worker processes running
- **HighLatency:** p95 latency > 120 seconds

### Alert Runbooks (Story 4.4)
**File:** [`alert-runbooks.md`](./alert-runbooks.md)
**Purpose:** Procedures for responding to the 4 automated alerts
**Content:**
- 4 alert-triggered runbooks with standardized structure
- Symptom → Common Root Causes → Troubleshooting → Resolution → Escalation
- Copy-paste ready commands and queries
- Cross-references to setup guides and operational runbooks
- Links to Grafana dashboards and Jaeger traces

**Runbooks:**
1. EnhancementSuccessRateLow → Investigate failures, check logs, restart workers
2. QueueDepthHigh → Monitor queue progress, scale workers, investigate stuck jobs
3. WorkerDown → Check worker health, restart workers, verify resource limits
4. HighLatency → Check external API health, optimize queries, review traces

---

## Operational Runbooks

**Directory:** [`docs/runbooks/`](../runbooks/)
**Purpose:** Procedures for common operational scenarios beyond alerts
**Structure:** All runbooks follow standardized format (Overview → Symptoms → Diagnosis → Resolution → Escalation)

### When to Use Operational Runbooks

- Metric elevated but **below alert threshold** (e.g., queue at 75 jobs, alert triggers at 100)
- **Post-mortem analysis** after incident resolved (e.g., reviewing worker crash patterns)
- **Procedural tasks** not triggered by alerts (e.g., onboarding new tenant)
- **Proactive investigation** before issues escalate to alerts

### Available Runbooks (Story 4.7)

| Runbook | When to Use | Read Time |
|---------|-------------|-----------|
| [High Queue Depth](../runbooks/high-queue-depth.md) | Queue depth 50-100 (pre-alert investigation) | 10 min |
| [Worker Failures](../runbooks/worker-failures.md) | Worker crashes, restarts, degradation | 12 min |
| [Database Connection Issues](../runbooks/database-connection-issues.md) | PostgreSQL connectivity or slow queries | 15 min |
| [API Timeout](../runbooks/api-timeout.md) | External API failures (ServiceDesk Plus, OpenAI) | 12 min |
| [Tenant Onboarding](../runbooks/tenant-onboarding.md) | Adding new MSP customer to production | 20 min |

**Master Index:** See [`docs/runbooks/README.md`](../runbooks/README.md) for complete index, search keywords, and quarterly review process

---

## Grafana Dashboards

### Main Monitoring Dashboard

**Accessible at:** http://localhost:3000/d/ai-agents-platform (local) or production equivalent
**Purpose:** Real-time system status and metrics overview
**Content:**
- **System Status Row:** Worker count, queue depth, success rate, p95 latency (with color-coded thresholds)
- **Queue Management Row:** Queue depth trend, jobs by status, queue age distribution
- **Enhancement Processing Row:** Success vs failure rate, processing latency distribution
- **Worker Health Row:** Worker count, CPU/memory usage, restart count
- **External API Row:** ServiceDesk Plus response time, OpenAI API latency, timeout rates

**Panel Descriptions:** Enhanced with runbook links for rapid incident response (click panel → read description → follow runbook)

### Operations Center Dashboard

**Accessible at:** http://localhost:3000/d/operations-center (Story 4.7)
**Purpose:** Quick-action dashboard for on-call incident response
**Content:**
- **System Status Overview:** 4 stat panels (workers, queue, success rate, latency) with red/yellow/green thresholds
- **Quick Actions:** Direct links to view logs, restart workers, check queue, access Jaeger
- **Runbook Index:** Central table linking to all operational runbooks
- **Recent Alerts:** Expanded alerts from Prometheus with runbook URLs

---

## Grafana Dashboards

**File:** [`grafana-setup.md`](./grafana-setup.md) - Complete dashboard architecture guide

**Production Dashboards:**
- `dashboards/ai-agents-platform.json` - Main monitoring dashboard (Story 4.3)
- `dashboards/operations-center.json` - Operations quick actions (Story 4.7)

---

## Component Troubleshooting

### Prometheus Issues

**Problem:** Prometheus UI shows "No Metrics"
→ See [`prometheus-setup.md`](./prometheus-setup.md) - "Troubleshooting" section

**Problem:** Alert rules showing state "Pending" instead of "Firing"
→ Check alert evaluation interval, review rule conditions in [`prometheus-alerting.md`](./prometheus-alerting.md)

**Problem:** Scrape targets down
→ See [`prometheus-setup.md`](./prometheus-setup.md) - "Target Health" section

### Grafana Issues

**Problem:** Dashboard panels show no data
→ Verify Prometheus datasource connected: http://localhost:3000 → Configuration → Data Sources → Prometheus (Test)

**Problem:** Panel descriptions not showing runbook links
→ Edit panel → Description → Add markdown link: `[Runbook](../runbooks/scenario.md)`

### Alertmanager Issues

**Problem:** Alerts not routing to Slack
→ See [`alertmanager-setup.md`](./alertmanager-setup.md) - "Testing Alerting Pipeline" section

**Problem:** Duplicate alerts
→ Review alert grouping rules in [`alertmanager-setup.md`](./alertmanager-setup.md) - "Grouping and Inhibition"

### Distributed Tracing Issues

**Problem:** Jaeger UI shows no traces
→ Verify OTEL_EXPORTER_OTLP_ENDPOINT configured, check Jaeger collector logs in [`distributed-tracing-setup.md`](./distributed-tracing-setup.md)

**Problem:** Traces missing spans
→ Verify instrumentation in application code, check sampler configuration

### General Troubleshooting

**I don't know what's wrong** → Check relevant operational runbook based on symptoms

**Issue is infrastructure (K8s, Docker, networking)** → Contact platform/DevOps team (out of ops runbook scope)

**Issue is application code** → File bug report with trace/logs attached, escalate to engineering

---

## File Structure and Locations

```
docs/
├── operations/                              # This directory
│   ├── README.md                            # ← You are here (central index)
│   ├── prometheus-setup.md                  # Setup guide (Story 4.2)
│   ├── grafana-setup.md                     # Setup guide (Story 4.3)
│   ├── prometheus-alerting.md               # Alert configuration (Story 4.4)
│   ├── alert-runbooks.md                    # 4 alert-driven runbooks (Story 4.4)
│   ├── alertmanager-setup.md                # Setup guide (Story 4.5)
│   ├── distributed-tracing-setup.md         # Setup guide (Story 4.6)
│   └── runbook-validation-report.md         # Testing results (Story 4.7)
│
├── runbooks/                                # Operational runbook directory (Story 4.7)
│   ├── README.md                            # Runbook index & quarterly review process
│   ├── high-queue-depth.md                  # Operational runbook
│   ├── worker-failures.md                   # Operational runbook
│   ├── database-connection-issues.md        # Operational runbook
│   ├── api-timeout.md                       # Operational runbook
│   └── tenant-onboarding.md                 # Operational runbook
│
├── architecture.md                          # System design
├── PRD.md                                   # Product requirements
├── epics.md                                 # Epic definitions
└── stories/                                 # User story files
```

---

## Key Metrics and Dashboards

### Primary Metrics

- **`enhancement_requests_total`** (counter) - Total enhancements processed
- **`enhancement_success_rate`** (gauge) - Success %
- **`enhancement_processing_duration_seconds`** (histogram) - Request latency
- **`queue_depth`** (gauge) - Number of jobs in Redis queue
- **`worker_active_count`** (gauge) - Number of active workers
- **`worker_restarts_total`** (counter) - Worker crash count

### Common Queries

```promql
# Success rate last 5 minutes
rate(enhancement_requests_total{status="success"}[5m]) / rate(enhancement_requests_total[5m])

# Queue depth trend
rate(queue_depth[5m])

# p95 latency
histogram_quantile(0.95, enhancement_processing_duration_seconds_bucket)

# Worker capacity (%)
(worker_active_count / 4) * 100
```

See [`prometheus-setup.md`](./prometheus-setup.md) for complete metric reference.

---

## External References

### Official Documentation

- **Prometheus Official Docs:** https://prometheus.io/docs/
- **Grafana Official Docs:** https://grafana.com/docs/
- **Alertmanager Official Docs:** https://prometheus.io/docs/alerting/latest/alertmanager/
- **OpenTelemetry Official Docs:** https://opentelemetry.io/docs/
- **Jaeger Official Docs:** https://www.jaegertracing.io/docs/

### Status Pages

- **OpenAI API Status:** https://status.openai.com
- **ServiceDesk Plus Docs:** [Customer's instance] /api/v3 (API reference)

### Related Internal Documentation

- **Architecture:** [`docs/architecture.md`](../architecture.md) - System design decisions
- **Database Schema:** [`docs/database-schema.md`](../database-schema.md) - PostgreSQL structure
- **API Reference:** [`docs/api.md`](../api.md) - REST endpoints

---

## Operational Checklist

### Daily Operations (If Applicable)

- [ ] Review Grafana main dashboard during business hours
- [ ] Monitor alert notifications from Slack
- [ ] Check queue depth trend (manual spot-check if not on-call)

### Weekly Operations

- [ ] Review alert history (which alerts fired, how often)
- [ ] Check distributed trace retention (are we keeping enough data?)
- [ ] Spot-check new team member familiar with at least 1 runbook

### Monthly Operations

- [ ] Review dashboards for data quality (no gaps, all panels returning data)
- [ ] Verify external API integrations still responding
- [ ] Update any documentation that changed

### Quarterly Operations

- [ ] Full runbook review and validation (see [`docs/runbooks/README.md`](../runbooks/README.md) - Quarterly Review Process)
- [ ] Update all screenshots/expected outputs in operational docs
- [ ] Identify gaps and plan new runbooks

---

## Questions or Issues?

- **General Operations Questions:** Ask in #ops-incidents Slack channel
- **Documentation Improvements:** File issue in GitHub or create PR
- **New Runbook Needed:** Create issue with symptoms and investigation steps
- **Emergency Support:** Page on-call engineer via Alertmanager/PagerDuty

---

**Last Updated:** 2025-11-03
**Next Review:** [Quarterly - TBD]
**Maintained By:** Operations Team & On-Call Engineers
