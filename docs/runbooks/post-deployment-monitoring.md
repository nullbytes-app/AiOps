# Post-Deployment Monitoring Checklist

**Document Version:** 1.0
**Last Updated:** November 20, 2025
**Story:** 4-8 Testing, Deployment, and Rollout - AC-5
**Status:** ✅ ACTIVE

## Table of Contents

1. [Overview](#overview)
2. [Monitoring Timeline](#monitoring-timeline)
3. [Critical Metrics Dashboard](#critical-metrics-dashboard)
4. [Service Health Checks](#service-health-checks)
5. [Performance Monitoring](#performance-monitoring)
6. [Error Rate Analysis](#error-rate-analysis)
7. [Resource Utilization](#resource-utilization)
8. [Business Metrics](#business-metrics)
9. [Alert Response Procedures](#alert-response-procedures)
10. [Escalation Matrix](#escalation-matrix)
11. [Appendix](#appendix)

---

## Overview

### Purpose

This checklist provides comprehensive monitoring procedures to execute immediately after production deployment. It ensures early detection of issues and provides clear escalation paths.

### Scope

- **Monitoring Duration**:
  - **Intensive**: First 2 hours post-deployment (every 15 minutes)
  - **Moderate**: Hours 2-24 (every 1 hour)
  - **Normal**: After 24 hours (standard alerting)

- **Monitored Components**: API, Worker, Database, Redis, LiteLLM, HMAC Proxy, Streamlit

### Monitoring Tools

| Tool | Purpose | Access |
|------|---------|--------|
| **Grafana** | Primary dashboards | http://localhost:3002 |
| **Prometheus** | Metrics collection | http://localhost:9091 |
| **Jaeger** | Distributed tracing | http://localhost:16686 |
| **Alertmanager** | Alert routing | http://localhost:9093 |
| **Docker Logs** | Service logs | `docker-compose logs` |

---

## Monitoring Timeline

### Phase 1: Immediate Post-Deployment (0-30 minutes)

**Frequency**: Every 5 minutes

**Checklist**:

- [ ] **Deployment Completed Successfully**
  - [ ] All services show "healthy" status: `docker-compose ps`
  - [ ] Build logs show no errors
  - [ ] Database migrations completed: `alembic current`

- [ ] **Smoke Tests Passed**
  ```bash
  bash tests/smoke/production_smoke_tests.sh $API_BASE_URL
  ```
  - [ ] All critical tests passing (10/10 minimum)
  - [ ] API health check: 200 OK
  - [ ] Database/Redis connectivity verified

- [ ] **Initial Traffic Processing**
  - [ ] First requests successful (check logs)
  - [ ] No 5xx errors in first 50 requests
  - [ ] Response times normal (<500ms p95)

- [ ] **Service Startup Logs Clean**
  ```bash
  # Check for startup errors
  docker-compose logs api | grep -i error | head -20
  docker-compose logs worker | grep -i error | head -20
  ```

### Phase 2: Early Monitoring (30-120 minutes)

**Frequency**: Every 15 minutes

**Checklist**:

- [ ] **Error Rate Monitoring**
  - [ ] HTTP 5xx error rate: **<1%** of total requests
  - [ ] HTTP 4xx error rate: **<5%** of total requests
  - [ ] Celery task failure rate: **<2%**

  **Query** (Prometheus):
  ```promql
  # Error rate over last 5 minutes
  rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) * 100
  ```

- [ ] **Response Time Monitoring**
  - [ ] API p50 latency: **<200ms**
  - [ ] API p95 latency: **<500ms**
  - [ ] API p99 latency: **<1000ms**

  **Query** (Prometheus):
  ```promql
  # p95 latency
  histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
  ```

- [ ] **Database Performance**
  - [ ] Connection pool utilization: **<70%**
  - [ ] Query latency p95: **<100ms**
  - [ ] Active connections: **<50** (out of 100 max)

  ```bash
  # Check PostgreSQL connections
  docker-compose exec postgres psql -U aiagents -c \
    "SELECT count(*) FROM pg_stat_activity WHERE datname='ai_agents';"
  ```

- [ ] **Celery Worker Health**
  - [ ] Active workers: **4** (expected count)
  - [ ] Queue depth: **<100** tasks
  - [ ] Task processing rate: **Consistent** (not stalled)

  ```bash
  # Check worker status
  docker-compose exec worker celery -A src.workers.celery_app inspect active
  docker-compose exec worker celery -A src.workers.celery_app inspect stats
  ```

### Phase 3: Extended Monitoring (2-24 hours)

**Frequency**: Every 1 hour

**Checklist**:

- [ ] **Stability Verification**
  - [ ] No service restarts/crashes
  - [ ] Error rate stable and below threshold
  - [ ] Memory usage stable (no leaks detected)

- [ ] **Performance Trending**
  - [ ] Response times not degrading over time
  - [ ] Database query performance stable
  - [ ] Redis cache hit rate: **>80%**

- [ ] **Resource Consumption**
  - [ ] CPU usage: **<80%** sustained
  - [ ] Memory usage: **<80%** of allocated
  - [ ] Disk I/O: **No sustained 100% utilization**

- [ ] **Business Metrics**
  - [ ] Agent executions completing successfully
  - [ ] Webhooks being processed (if traffic exists)
  - [ ] No unusual patterns in user behavior

### Phase 4: Return to Normal (After 24 hours)

**Frequency**: Standard alerting (automated)

**Checklist**:

- [ ] **Deployment Sign-Off**
  - [ ] All monitoring metrics within normal ranges
  - [ ] No critical alerts fired in last 24 hours
  - [ ] Performance baselines established
  - [ ] Team consensus on deployment success

- [ ] **Documentation Updated**
  - [ ] Deployment recorded in change log
  - [ ] Any issues documented in post-mortem (if applicable)
  - [ ] Runbooks updated with lessons learned

---

## Critical Metrics Dashboard

### Grafana Dashboard: Production Health

Access: http://localhost:3002/dashboards

**Panels to Monitor**:

1. **API Request Rate**
   - Metric: `rate(http_requests_total[1m])`
   - Expected: Consistent with historical baseline
   - Alert: >50% drop (potential traffic issue)

2. **Error Rate Percentage**
   - Metric: `rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) * 100`
   - Expected: <1%
   - Alert: >5% for 5 minutes

3. **API Response Time (p95)**
   - Metric: `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`
   - Expected: <500ms
   - Alert: >1000ms for 5 minutes

4. **Database Connections**
   - Metric: `pg_stat_database_numbackends`
   - Expected: <50
   - Alert: >80

5. **Celery Queue Depth**
   - Metric: `celery_queue_length`
   - Expected: <100
   - Alert: >500 for 10 minutes

6. **Memory Usage**
   - Metric: `container_memory_usage_bytes / container_spec_memory_limit_bytes * 100`
   - Expected: <80%
   - Alert: >90% for 5 minutes

7. **CPU Usage**
   - Metric: `rate(container_cpu_usage_seconds_total[1m]) * 100`
   - Expected: <80%
   - Alert: >90% for 10 minutes

### Quick Dashboard Access

```bash
# Open Grafana (default credentials: admin/admin)
open http://localhost:3002

# Open Prometheus expression browser
open http://localhost:9091/graph

# Open Jaeger traces
open http://localhost:16686
```

---

## Service Health Checks

### Automated Health Checks

**API Health Endpoint**:
```bash
curl http://localhost:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "database": "connected",
#   "redis": "connected",
#   "timestamp": "2025-11-20T12:00:00Z"
# }
```

**Service Status Check**:
```bash
docker-compose ps

# Expected output: All services "Up" and "healthy"
# - ai-agents-api        Up (healthy)
# - ai-agents-worker     Up (healthy)
# - ai-agents-postgres   Up (healthy)
# - ai-agents-redis      Up (healthy)
```

### Manual Health Verification

**Database Connectivity**:
```bash
# Test database query
docker-compose exec postgres psql -U aiagents -c "SELECT 1;"

# Check RLS policies active
docker-compose exec postgres psql -U aiagents -d ai_agents -c \
  "SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname='public';"
```

**Redis Connectivity**:
```bash
# Test Redis PING
docker-compose exec redis redis-cli PING
# Expected: PONG

# Check Redis memory usage
docker-compose exec redis redis-cli INFO memory | grep used_memory_human
# Expected: <200MB for self-hosted, <20MB for Render free tier
```

**Celery Worker Status**:
```bash
# Inspect active tasks
docker-compose exec worker celery -A src.workers.celery_app inspect active

# Check worker pool
docker-compose exec worker celery -A src.workers.celery_app inspect stats
# Expected: 4 workers, all responding
```

---

## Performance Monitoring

### Response Time Analysis

**API Endpoint Latency**:
```bash
# Measure health endpoint response time
time curl -s http://localhost:8000/health > /dev/null

# Bulk test (100 requests)
ab -n 100 -c 10 http://localhost:8000/health | grep "Time per request"
```

**Prometheus Query** (p50, p95, p99):
```promql
# p50 (median)
histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))

# p95
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# p99
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
```

**Thresholds**:
- p50: <200ms ✅
- p95: <500ms ✅
- p99: <1000ms ✅
- p99: >2000ms ⚠️ **Investigate immediately**

### Database Query Performance

```sql
-- Connect to database
docker-compose exec postgres psql -U aiagents ai_agents

-- Check slow queries
SELECT query, mean_exec_time, calls, total_exec_time
FROM pg_stat_statements
WHERE mean_exec_time > 100
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check table sizes
SELECT schemaname, tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

**Alert Thresholds**:
- Mean query time >500ms: ⚠️ **Review query optimization**
- Mean query time >1000ms: 🔴 **Critical - add indexes**

### Throughput Analysis

**Requests Per Second (RPS)**:
```promql
# Current RPS
rate(http_requests_total[1m])

# Peak RPS (last hour)
max_over_time(rate(http_requests_total[1m])[1h])
```

**Celery Task Throughput**:
```promql
# Tasks processed per minute
rate(celery_task_completed_total[1m])

# Task success rate
rate(celery_task_completed_total{status="success"}[5m]) /
rate(celery_task_completed_total[5m]) * 100
```

---

## Error Rate Analysis

### HTTP Error Tracking

**4xx Errors (Client Errors)**:
```promql
# 4xx error rate
sum(rate(http_requests_total{status=~"4.."}[5m])) /
sum(rate(http_requests_total[5m])) * 100
```

**Acceptable**: <5% (many 4xx are expected, e.g., 401 unauthorized, 404 not found)

**5xx Errors (Server Errors)**:
```promql
# 5xx error rate (CRITICAL METRIC)
sum(rate(http_requests_total{status=~"5.."}[5m])) /
sum(rate(http_requests_total[5m])) * 100
```

**Thresholds**:
- <1%: ✅ Normal
- 1-5%: ⚠️ **Monitor closely, investigate if sustained**
- >5%: 🔴 **Critical - initiate rollback consideration**

### Error Log Analysis

**API Error Logs**:
```bash
# Check for errors (last 100 lines)
docker-compose logs --tail=100 api | grep -i error

# Count errors in last hour
docker-compose logs --since=1h api | grep -c -i error

# Check for critical errors
docker-compose logs --tail=500 api | grep -i "critical"
```

**Worker Error Logs**:
```bash
# Check worker errors
docker-compose logs --tail=100 worker | grep -i error

# Check task failures
docker-compose logs --tail=500 worker | grep -i "failed"
```

**Database Error Logs**:
```bash
# Check PostgreSQL logs
docker-compose logs --tail=100 postgres | grep -i error
```

### Celery Task Failures

```bash
# Inspect failed tasks
docker-compose exec worker celery -A src.workers.celery_app inspect failed

# Get task failure rate
docker-compose exec worker celery -A src.workers.celery_app inspect stats | grep -i failed
```

**Prometheus Query**:
```promql
# Task failure rate
rate(celery_task_completed_total{status="failure"}[5m]) /
rate(celery_task_completed_total[5m]) * 100
```

**Thresholds**:
- <2%: ✅ Normal (expected for retry scenarios)
- 2-10%: ⚠️ **Investigate root cause**
- >10%: 🔴 **Critical - check worker health**

---

## Resource Utilization

### Memory Monitoring

**Container Memory Usage**:
```bash
# All containers
docker stats --no-stream

# Specific service
docker stats --no-stream ai-agents-api | awk 'NR>1 {print $4}'
```

**Prometheus Query**:
```promql
# Memory usage percentage
(container_memory_usage_bytes / container_spec_memory_limit_bytes) * 100
```

**Thresholds**:
- <70%: ✅ Normal
- 70-80%: ⚠️ **Monitor for growth trend**
- 80-90%: 🔴 **Scale up resources**
- >90%: 🔴 **CRITICAL - OOM kill risk**

**Memory Leak Detection**:
```promql
# Memory growth over 6 hours (should be near 0 for stable services)
increase(container_memory_usage_bytes[6h])
```

### CPU Monitoring

**CPU Usage**:
```bash
# Current CPU usage
docker stats --no-stream | awk '{print $1, $3}'
```

**Prometheus Query**:
```promql
# CPU usage percentage
rate(container_cpu_usage_seconds_total[1m]) * 100
```

**Thresholds**:
- <60%: ✅ Optimal
- 60-80%: ✅ Normal load
- 80-90%: ⚠️ **High load, monitor**
- >90%: 🔴 **Critical - scale workers or optimize**

### Disk I/O

**Disk Usage**:
```bash
# Check disk space
df -h | grep -E '(Filesystem|/var/lib/docker)'

# Check database disk usage
docker-compose exec postgres du -sh /var/lib/postgresql/data
```

**Database Growth Rate**:
```sql
-- Database size
SELECT pg_size_pretty(pg_database_size('ai_agents'));

-- Table sizes
SELECT tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Network Monitoring

**Connection Counts**:
```bash
# Active TCP connections to API (port 8000)
netstat -an | grep :8000 | grep ESTABLISHED | wc -l

# PostgreSQL connections
docker-compose exec postgres psql -U aiagents -c \
  "SELECT count(*) FROM pg_stat_activity WHERE datname='ai_agents';"
```

---

## Business Metrics

### Agent Execution Metrics

**Successful Agent Runs**:
```sql
-- Count successful agent executions (last hour)
SELECT count(*) FROM job_queue
WHERE status = 'completed'
  AND created_at > NOW() - INTERVAL '1 hour';

-- Average execution time
SELECT AVG(EXTRACT(EPOCH FROM (updated_at - created_at))) AS avg_seconds
FROM job_queue
WHERE status = 'completed'
  AND created_at > NOW() - INTERVAL '1 hour';
```

**Failed Agent Runs**:
```sql
-- Failed executions (investigate if >5%)
SELECT count(*) FROM job_queue
WHERE status = 'failed'
  AND created_at > NOW() - INTERVAL '1 hour';
```

### Webhook Processing

**Webhook Acceptance Rate**:
```sql
-- Count webhooks processed (last hour)
SELECT count(*) FROM audit_log
WHERE event_type = 'webhook_received'
  AND created_at > NOW() - INTERVAL '1 hour';

-- Check for signature validation failures
SELECT count(*) FROM audit_log
WHERE event_type = 'webhook_validation_failed'
  AND created_at > NOW() - INTERVAL '1 hour';
```

**Prometheus Query**:
```promql
# Webhook success rate
rate(webhook_requests_total{status="success"}[5m]) /
rate(webhook_requests_total[5m]) * 100
```

### LiteLLM Proxy Metrics

**LLM Request Success Rate**:
```promql
# Check LiteLLM proxy metrics
rate(litellm_requests_total{status="success"}[5m]) /
rate(litellm_requests_total[5m]) * 100
```

**Token Usage**:
```sql
-- Check token consumption (if budget tracking enabled)
SELECT sum(tokens_used) FROM llm_usage
WHERE created_at > NOW() - INTERVAL '1 hour';
```

---

## Alert Response Procedures

### Alert Severity Levels

| Level | Response Time | Action Required |
|-------|---------------|-----------------|
| **P0 - Critical** | 5 minutes | Immediate investigation, potential rollback |
| **P1 - High** | 15 minutes | Investigate and mitigate |
| **P2 - Medium** | 1 hour | Monitor and plan fix |
| **P3 - Low** | Next business day | Track for future resolution |

### Common Alerts and Responses

#### Alert: High Error Rate

**Trigger**: 5xx error rate >5% for 5 minutes

**Response**:
1. Check API logs for error patterns:
   ```bash
   docker-compose logs --tail=200 api | grep -i "5[0-9][0-9]"
   ```
2. Verify database connectivity:
   ```bash
   docker-compose exec postgres pg_isready
   ```
3. Check Celery worker health:
   ```bash
   docker-compose exec worker celery -A src.workers.celery_app inspect ping
   ```
4. If errors persist >10 minutes: **Initiate rollback** (see [Rollback Procedures](./rollback-procedures.md))

#### Alert: High Response Time

**Trigger**: p95 latency >1000ms for 10 minutes

**Response**:
1. Check database slow queries:
   ```sql
   SELECT query, mean_exec_time FROM pg_stat_statements
   WHERE mean_exec_time > 500 ORDER BY mean_exec_time DESC LIMIT 5;
   ```
2. Check Redis connection:
   ```bash
   docker-compose exec redis redis-cli PING
   ```
3. Review CPU/memory usage:
   ```bash
   docker stats --no-stream
   ```
4. Consider scaling workers if CPU >90%

#### Alert: Worker Queue Backup

**Trigger**: Celery queue depth >500 for 10 minutes

**Response**:
1. Check worker status:
   ```bash
   docker-compose ps worker
   docker-compose logs --tail=100 worker
   ```
2. Verify workers processing tasks:
   ```bash
   docker-compose exec worker celery -A src.workers.celery_app inspect active
   ```
3. Restart workers if stalled:
   ```bash
   docker-compose restart worker
   ```
4. Scale workers if needed:
   ```bash
   docker-compose up -d --scale worker=8
   ```

#### Alert: Database Connection Pool Exhaustion

**Trigger**: Active DB connections >80

**Response**:
1. Check connection counts:
   ```sql
   SELECT count(*), state FROM pg_stat_activity GROUP BY state;
   ```
2. Kill idle connections if necessary:
   ```sql
   SELECT pg_terminate_backend(pid) FROM pg_stat_activity
   WHERE state = 'idle' AND state_change < NOW() - INTERVAL '5 minutes';
   ```
3. Restart API service to reset pool:
   ```bash
   docker-compose restart api
   ```

#### Alert: Memory Usage High

**Trigger**: Container memory >90% for 5 minutes

**Response**:
1. Identify memory-heavy container:
   ```bash
   docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}"
   ```
2. Check for memory leaks:
   ```bash
   docker-compose logs --tail=1000 api | grep -i "memory"
   ```
3. Restart service:
   ```bash
   docker-compose restart api  # or worker, as needed
   ```
4. If issue persists: **Consider rollback**

---

## Escalation Matrix

### Level 1: On-Call Engineer (0-15 minutes)

**Responsibilities**:
- Initial alert triage
- Execute standard playbooks
- Implement quick fixes (service restarts, cache clears)
- Escalate if unresolved in 15 minutes

**Contact**: Slack #engineering @oncall

### Level 2: Engineering Lead (15-30 minutes)

**Responsibilities**:
- Review incident timeline
- Make rollback decision
- Coordinate with team for investigation
- Communicate with stakeholders

**Contact**: Slack @engineering-lead, Phone (for P0)

### Level 3: CTO / Senior Leadership (30+ minutes)

**Responsibilities**:
- Approve major changes (rollback with data loss risk)
- External communication (customers, investors)
- Post-incident process improvements

**Contact**: Email cto@company.com, Phone (for P0 with customer impact)

### Escalation Flowchart

```
Alert Fired
    │
    ▼
On-Call Engineer Notified (0 min)
    │
    ├─ [Resolved] → Document in post-mortem
    │
    ├─ [Unresolved after 15 min]
    │       │
    │       ▼
    │   Engineering Lead Escalation
    │       │
    │       ├─ [Rollback Decision]
    │       │       │
    │       │       ▼
    │       │   Execute Rollback
    │       │
    │       └─ [Continue Investigation]
    │               │
    │               ├─ [Resolved]
    │               │
    │               └─ [Unresolved after 30 min / Customer Impact]
    │                       │
    │                       ▼
    │                   CTO Escalation
    │                       │
    │                       └─ [External Communication]
    │
    └─ [P0 with Data Loss Risk] → Immediate CTO notification
```

---

## Appendix

### A. Monitoring Commands Cheat Sheet

```bash
# Service health
docker-compose ps
curl http://localhost:8000/health

# Logs
docker-compose logs -f api
docker-compose logs --tail=100 worker | grep ERROR

# Metrics
curl http://localhost:8000/metrics/ | head -20

# Database
docker-compose exec postgres psql -U aiagents -c "SELECT count(*) FROM agents;"

# Redis
docker-compose exec redis redis-cli INFO memory

# Celery
docker-compose exec worker celery -A src.workers.celery_app inspect active
docker-compose exec worker celery -A src.workers.celery_app inspect stats

# Resources
docker stats --no-stream
df -h
```

### B. Prometheus Queries Reference

```promql
# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) * 100

# Latency p95
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Memory usage
(container_memory_usage_bytes / container_spec_memory_limit_bytes) * 100

# CPU usage
rate(container_cpu_usage_seconds_total[1m]) * 100

# Request rate
rate(http_requests_total[1m])

# Celery queue depth
celery_queue_length

# Database connections
pg_stat_database_numbackends
```

### C. Related Documents

- [Production Deployment Runbook](./production-deployment.md)
- [Rollback Procedures](./rollback-procedures.md)
- [OWASP Security Testing Report](../security/owasp-security-testing-report.md)
- [Database Connection Issues](./database-connection-issues.md)
- [Worker Failures Runbook](./worker-failures.md)
- [Performance Issues Runbook](./performance-issues.md)

### D. Contact Information

| Role | Slack | Phone | Availability |
|------|-------|-------|--------------|
| On-Call Engineer | @oncall | Internal | 24/7 |
| Engineering Lead | @eng-lead | Internal | Business hours |
| Database Admin | @dba | Internal | Business hours |
| DevOps Team | #devops | N/A | Business hours |

### E. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-20 | AI Agents Platform Team | Initial monitoring checklist |

---

**Document Status**: ✅ ACTIVE
**Next Review**: 2025-12-20
**Owner**: Engineering Team
**Contact**: #engineering on Slack
