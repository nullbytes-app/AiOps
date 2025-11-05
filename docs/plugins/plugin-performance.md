# Plugin Performance Guide

[Plugin Docs](index.md) > How-To Guides > Performance

**Last Updated:** 2025-11-05

---

## Overview

Performance optimization strategies for plugin development, covering latency targets, connection pooling, caching, and monitoring.

---

## Expected Latencies (NFR001)

| Method | Target Latency | Notes |
|--------|---------------|-------|
| `validate_webhook()` | <100ms | HMAC computation only, no I/O |
| `get_ticket()` | <2s | Includes 1 API call + network round trip |
| `update_ticket()` | <5s | Includes retries if needed |
| `extract_metadata()` | <10ms | Pure Python, no I/O operations |

**Monitoring:** Track p50, p95, p99 latencies in production. Alert if p95 exceeds targets.

---

## Optimization Strategies

### 1. Connection Pooling

**Problem:** Creating new HTTP connections for every request is expensive

**Solution:** Reuse httpx AsyncClient with connection pooling

```python
class ServiceDeskPlusPlugin(TicketingToolPlugin):
    def __init__(self):
        # Reuse client across requests
        self._client = httpx.AsyncClient(
            limits=httpx.Limits(
                max_keepalive_connections=20,  # Keep 20 connections alive
                max_connections=100            # Max concurrent connections
            ),
            timeout=httpx.Timeout(
                connect=5.0,
                read=30.0,
                write=5.0,
                pool=5.0
            )
        )

    async def get_ticket(self, tenant_id: str, ticket_id: str) -> Dict[str, Any]:
        # Reuse pooled connection
        response = await self._client.get(url, headers=headers)
        return response.json()

    async def close(self):
        """Close client on plugin shutdown."""
        await self._client.aclose()
```

**Performance Impact:**
- Without pooling: ~200ms per request (TCP handshake + TLS)
- With pooling: ~50ms per request (reuse existing connection)

### 2. Caching Tenant Configs

**Problem:** Repeated database queries for same tenant config

**Solution:** Cache tenant configs with TTL

```python
from functools import lru_cache
from datetime import datetime, timedelta


class PluginBase:
    _config_cache = {}
    _cache_ttl = timedelta(minutes=5)

    async def _get_tenant_config_cached(
        self, tenant_id: str
    ) -> Optional[TenantConfig]:
        """Get tenant config with 5-minute cache."""

        # Check cache
        if tenant_id in self._config_cache:
            config, cached_at = self._config_cache[tenant_id]
            if datetime.now() - cached_at < self._cache_ttl:
                return config

        # Cache miss - fetch from database
        config = await self._get_tenant_config(tenant_id)
        if config:
            self._config_cache[tenant_id] = (config, datetime.now())

        return config
```

**Performance Impact:**
- Without caching: ~20ms database query per request
- With caching: ~0.1ms in-memory lookup (200x faster)

**Cache Invalidation:**
```python
def invalidate_cache(tenant_id: str):
    """Invalidate cache when tenant config changes."""
    if tenant_id in PluginBase._config_cache:
        del PluginBase._config_cache[tenant_id]
```

### 3. Parallel API Calls

**Problem:** Sequential API calls waste time

**Solution:** Use asyncio.gather for concurrent operations

```python
async def get_multiple_tickets(
    self,
    tenant_id: str,
    ticket_ids: List[str]
) -> List[Optional[Dict[str, Any]]]:
    """Retrieve multiple tickets concurrently."""

    # Create tasks
    tasks = [
        self.get_ticket(tenant_id, ticket_id)
        for ticket_id in ticket_ids
    ]

    # Execute in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle exceptions
    tickets = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Error fetching ticket: {result}")
            tickets.append(None)
        else:
            tickets.append(result)

    return tickets
```

**Performance Impact:**
- Sequential: 10 tickets × 1s = 10 seconds
- Parallel: max(10 × 1s) = 1 second (10x faster)

### 4. Request Batching

**Problem:** Multiple small API calls with overhead

**Solution:** Batch requests when API supports it

```python
async def update_tickets_batch(
    self,
    tenant_id: str,
    updates: List[Tuple[str, str]]  # [(ticket_id, content), ...]
) -> List[bool]:
    """
    Update multiple tickets in batch.

    Default implementation: Sequential calls
    Override for tools with batch APIs (e.g., Jira bulk operations)
    """
    results = []
    for ticket_id, content in updates:
        result = await self.update_ticket(tenant_id, ticket_id, content)
        results.append(result)
    return results
```

**Jira Bulk API Example:**
```python
async def update_tickets_batch(self, tenant_id: str, updates: List) -> List[bool]:
    """Use Jira bulk update API for better performance."""
    bulk_payload = {
        "issueUpdates": [
            {
                "key": ticket_id,
                "update": {"comment": [{"add": {"body": content}}]}
            }
            for ticket_id, content in updates
        ]
    }

    response = await self._client.post(
        f"{self.base_url}/rest/api/3/issue/bulk",
        json=bulk_payload
    )

    return [True] * len(updates) if response.status_code == 200 else [False] * len(updates)
```

---

## Security Optimizations

### Constant-Time Comparisons

**Critical:** Use `secrets.compare_digest()` for webhook validation

```python
# ✅ GOOD: Constant-time comparison (prevents timing attacks)
return secrets.compare_digest(expected_signature, provided_signature)

# ❌ BAD: Regular comparison (vulnerable to timing attacks)
return expected_signature == provided_signature
```

**Why:** Timing attacks can reveal signature one byte at a time by measuring response time.

### Credentials Handling

**Best Practice:** Decrypt credentials just-in-time, never store unencrypted

```python
# ✅ GOOD: Decrypt only when needed
async def get_ticket(self, tenant_id: str, ticket_id: str):
    config = await self._get_tenant_config(tenant_id)
    api_key = decrypt_value(config.api_key_encrypted)  # Decrypt JIT
    response = await client.get(url, headers={"API-KEY": api_key})
    # api_key goes out of scope immediately

# ❌ BAD: Store decrypted credential as instance variable
class Plugin:
    def __init__(self, api_key: str):
        self.api_key = api_key  # Stored unencrypted in memory
```

---

## Monitoring and Metrics

### Prometheus Metrics

**File:** `src/plugins/metrics.py`

```python
from prometheus_client import Counter, Histogram

# Webhook validation metrics
webhook_validation_total = Counter(
    'plugin_webhook_validation_total',
    'Total webhook validations',
    ['tool_type', 'result']  # result: success/failure
)

webhook_validation_duration = Histogram(
    'plugin_webhook_validation_duration_seconds',
    'Webhook validation duration',
    ['tool_type']
)

# API call metrics
api_call_total = Counter(
    'plugin_api_call_total',
    'Total API calls',
    ['tool_type', 'method', 'result']  # method: get_ticket/update_ticket
)

api_call_duration = Histogram(
    'plugin_api_call_duration_seconds',
    'API call duration',
    ['tool_type', 'method'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]  # Custom buckets for SLA monitoring
)
```

### Usage in Plugin

```python
async def validate_webhook(self, payload, signature) -> bool:
    with webhook_validation_duration.labels(tool_type='servicedesk_plus').time():
        is_valid = await self._validate_signature(payload, signature)

    webhook_validation_total.labels(
        tool_type='servicedesk_plus',
        result='success' if is_valid else 'failure'
    ).inc()

    return is_valid
```

### Grafana Dashboard Queries

```promql
# p95 webhook validation latency
histogram_quantile(0.95, sum(rate(plugin_webhook_validation_duration_seconds_bucket[5m])) by (le, tool_type))

# API call success rate
sum(rate(plugin_api_call_total{result="success"}[5m])) / sum(rate(plugin_api_call_total[5m])) * 100

# Average API call duration by method
avg(rate(plugin_api_call_duration_seconds_sum[5m])) by (method)
```

---

## Profiling and Benchmarking

### Python Profiler

```bash
# Profile plugin execution
python -m cProfile -o plugin.prof -m pytest tests/unit/test_servicedesk_plugin.py

# View results
python -m pstats plugin.prof
```

### pytest-benchmark

```python
import pytest


def test_extract_metadata_performance(benchmark):
    """Benchmark metadata extraction (target: <10ms)."""
    plugin = ServiceDeskPlusPlugin()
    payload = {...}  # Sample payload

    result = benchmark(plugin.extract_metadata, payload)
    assert result.tenant_id == "tenant-001"

# Run with:
# pytest tests/benchmark/ --benchmark-only
```

### Memory Profiling

```python
from memory_profiler import profile


@profile
async def get_ticket(self, tenant_id: str, ticket_id: str):
    # Function will show line-by-line memory usage
    ...
```

---

## Performance Testing

### Load Testing with Locust

```python
from locust import HttpUser, task, between


class PluginLoadTest(HttpUser):
    wait_time = between(1, 2)

    @task
    def webhook_validation(self):
        payload = {...}
        self.client.post(
            "/webhook",
            json=payload,
            headers={"X-ServiceDesk-Signature": "sha256=..."}
        )
```

**Run:**
```bash
locust -f tests/load/test_plugin_load.py --host=http://localhost:8000
```

**Targets:**
- 1000 requests/second sustained
- p95 latency <2s
- Zero errors under normal load

---

## Common Performance Issues

### Issue 1: N+1 Database Queries

**Problem:**
```python
# BAD: 100 database queries
for tenant_id in tenant_ids:
    config = await get_tenant_config(tenant_id)
    process(config)
```

**Solution:**
```python
# GOOD: 1 database query
configs = await get_tenant_configs_batch(tenant_ids)
for config in configs:
    process(config)
```

### Issue 2: Blocking I/O in Async Code

**Problem:**
```python
# BAD: Blocking file I/O
def extract_metadata(self, payload):
    with open("mapping.json") as f:  # Blocks event loop
        mapping = json.load(f)
```

**Solution:**
```python
# GOOD: Load once at startup
class Plugin:
    def __init__(self):
        with open("mapping.json") as f:
            self._mapping = json.load(f)

    def extract_metadata(self, payload):
        priority = self._mapping.get(payload["priority"])
```

### Issue 3: Inefficient JSON Serialization

**Problem:**
```python
# BAD: Large payload with pretty printing
json.dumps(payload, indent=2)  # Slower, larger size
```

**Solution:**
```python
# GOOD: Compact JSON for signatures
json.dumps(payload, separators=(',', ':'))  # Faster, smaller
```

---

## Performance Checklist

- [ ] Connection pooling enabled (max_keepalive_connections=20)
- [ ] Tenant configs cached (5-minute TTL)
- [ ] Parallel API calls used where possible
- [ ] Constant-time comparisons for security
- [ ] Prometheus metrics instrumented
- [ ] p95 latency meets NFR001 targets
- [ ] Load testing passed (1000 req/s)
- [ ] No blocking I/O in async code
- [ ] Efficient JSON serialization used
- [ ] Memory leaks checked (no unbounded caches)

---

## See Also

- [Plugin Error Handling Guide](plugin-error-handling.md)
- [Plugin Interface Reference](plugin-interface-reference.md)
- [httpx Documentation](https://www.python-httpx.org/)
- [Prometheus Python Client](https://github.com/prometheus/client_python)
