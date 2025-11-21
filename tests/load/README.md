# Load Testing Suite for AI Agents Enhancement Workflow

Comprehensive Locust-based load testing scenarios for Story 4-8 AC-2.

## Overview

This suite validates system performance under various load conditions:

1. **Baseline** - Normal operational load (10 users, 5 min)
2. **Peak** - Maximum expected load (100 users, 10 min)
3. **Burst** - Sudden traffic spikes (1→200→10 users, 4 min)
4. **Endurance** - Sustained load stability (50 users, 30 min)

## Performance Targets

From Story 4-8 Acceptance Criteria:
- **p95 latency**: <60s for complete enhancement workflow
- **Success rate**: >99%
- **Queue processing**: Adequate for expected load
- **System stability**: No degradation over time

## Prerequisites

### 1. Install Locust

```bash
pip install locust>=2.20.0
# Or using uv:
uv pip install locust
```

### 2. Start System Under Test

```bash
# Local development
docker-compose up -d api redis postgres

# Or Kubernetes staging
kubectl port-forward svc/ai-agents-api 8000:8000
```

### 3. Create Test Tenant

The load tests use `tenant_id="load-test-tenant"`. Create it:

```sql
-- Connect to database
psql $AI_AGENTS_DATABASE_URL

-- Create test tenant
INSERT INTO tenant_configs (
    tenant_id, name, servicedesk_url,
    servicedesk_api_key_encrypted,
    webhook_signing_secret_encrypted,
    tool_type
) VALUES (
    'load-test-tenant',
    'Load Test Tenant',
    'https://loadtest.servicedesk.local',
    'encrypted_test_key',
    'encrypted_test_secret',
    'servicedesk_plus'
);
```

## Running Load Tests

### Individual Tests

#### Baseline (5 minutes)
```bash
locust -f tests/load/baseline_load_test.py --headless \
       --users 10 --spawn-rate 2 --run-time 5m \
       --host http://localhost:8000
```

#### Peak (10 minutes)
```bash
locust -f tests/load/peak_load_test.py --headless \
       --users 100 --spawn-rate 10 --run-time 10m \
       --host http://localhost:8000
```

#### Burst (4 minutes with custom shape)
```bash
locust -f tests/load/burst_load_test.py --headless \
       --host http://localhost:8000
```

#### Endurance (30 minutes)
```bash
locust -f tests/load/endurance_load_test.py --headless \
       --users 50 --spawn-rate 5 --run-time 30m \
       --host http://localhost:8000
```

### Web UI Mode (Interactive)

For real-time monitoring and manual control:

```bash
locust -f tests/load/baseline_load_test.py \
       --host http://localhost:8000

# Open browser: http://localhost:8089
```

### Full Test Suite

Run all tests sequentially:

```bash
./tests/load/run_all_load_tests.sh
```

## Monitoring During Tests

### 1. Application Metrics

```bash
# Watch Prometheus metrics
watch -n 2 'curl -s http://localhost:8000/metrics | grep queue_depth'

# Watch API health
watch -n 2 'curl -s http://localhost:8000/health | jq'
```

### 2. Infrastructure Metrics

```bash
# Kubernetes pods
watch kubectl top pods

# Docker containers
watch docker stats

# Queue depth (Redis)
watch 'redis-cli LLEN enhancement_queue'
```

### 3. Database Connections

```bash
# PostgreSQL connections
watch 'psql $AI_AGENTS_DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity"'
```

## Interpreting Results

### Success Criteria

✅ **PASS** if ALL of the following:
- Success rate >99%
- p95 latency <60s (60000ms)
- No errors in application logs
- Queue processed all jobs

⚠️ **WARNING** if ANY of:
- Success rate 95-99%
- p95 latency 60-90s
- Temporary queue buildup (recovered)

❌ **FAIL** if ANY of:
- Success rate <95%
- p95 latency >90s
- System crashes or becomes unresponsive
- Data loss or corruption

### Common Issues

#### High Latency (p95 >60s)

**Symptoms**: Slow response times under load

**Causes**:
- Database connection pool exhausted
- LLM API rate limiting
- Queue worker CPU bound

**Solutions**:
```bash
# Increase connection pool
export DATABASE_POOL_SIZE=20

# Scale workers horizontally
kubectl scale deployment celery-worker --replicas=5

# Add caching
export REDIS_CACHE_TTL=300
```

#### Low Success Rate (<99%)

**Symptoms**: Requests failing under load

**Causes**:
- Timeouts (default 30s may be too short)
- Memory pressure causing OOM kills
- Rate limiting (429 responses)

**Solutions**:
```python
# Increase request timeout
CLIENT_TIMEOUT = 60

# Add memory limits to K8s
resources:
  limits:
    memory: "2Gi"

# Implement circuit breaker
```

#### Queue Buildup

**Symptoms**: `LLEN enhancement_queue` growing continuously

**Causes**:
- Worker processing slower than webhook ingestion
- Workers stuck or crashed
- Insufficient worker capacity

**Solutions**:
```bash
# Check worker logs
kubectl logs -l app=celery-worker --tail=50

# Scale workers
kubectl scale deployment celery-worker --replicas=10

# Verify worker health
celery -A src.workers.celery_app inspect active
```

## Load Test Best Practices

### 1. Warmup Phase

Always include warmup to:
- Fill connection pools
- Prime caches
- Allow auto-scaling to stabilize

```python
# Good: Gradual ramp-up
wait_time = between(5, 10)  # Start slow
```

### 2. Realistic Patterns

Match production behavior:
- Use actual ticket descriptions
- Vary payload sizes
- Include monitoring tasks (not just writes)

### 3. Clean Data Between Tests

```bash
# Clear Redis queue
redis-cli FLUSHDB

# Truncate test data
psql $AI_AGENTS_DATABASE_URL -c \
  "DELETE FROM enhancement_history WHERE tenant_id='load-test-tenant'"
```

### 4. Monitor System Resources

Set up alerts:
```bash
# CPU >80%
# Memory >90%
# Queue depth >1000
# Connection pool >90%
```

## Troubleshooting

### Locust Won't Start

```bash
# Check Python version (3.9+)
python --version

# Reinstall Locust
pip install --upgrade locust

# Verify imports
python -c "from locust import FastHttpUser; print('OK')"
```

### Connection Refused

```bash
# Verify API is running
curl http://localhost:8000/health

# Check port forwarding
lsof -i :8000

# Test direct connection
telnet localhost 8000
```

### High Failure Rate

```bash
# Check API logs
docker-compose logs api --tail=100

# Verify database connection
docker-compose exec postgres psql -U aiagents -c "SELECT 1"

# Test endpoint manually
curl -X POST http://localhost:8000/webhooks/servicedesk/load-test-tenant \
  -H "Content-Type: application/json" \
  -d '{"ticket_id": "TEST-123", ...}'
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Load Tests

on:
  schedule:
    - cron: '0 2 * * *'  # Nightly

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Start services
        run: docker-compose up -d
      - name: Run baseline test
        run: |
          pip install locust
          locust -f tests/load/baseline_load_test.py --headless \
                 --users 10 --spawn-rate 2 --run-time 5m \
                 --host http://localhost:8000 \
                 --html reports/baseline_results.html
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: load-test-results
          path: reports/
```

## References

- [Locust Documentation](https://docs.locust.io/)
- [FastAPI Performance Testing](https://fastapi.tiangolo.com/advanced/testing/)
- [Story 4-8: Testing & Deployment](docs/sprint-artifacts/4-8-testing-deployment-and-rollout.md)
