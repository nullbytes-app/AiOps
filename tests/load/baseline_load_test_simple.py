"""
Simplified Baseline Load Test - Public Endpoints Only.

Tests system stability under normal operational load using only public endpoints
that don't require authentication. Validates infrastructure performance without
webhook-specific authentication.

Test Configuration:
- Users: 10 concurrent users
- Duration: 2 minutes (shortened for quick validation)
- Spawn Rate: 2 users/second
- Wait Time: 3-7 seconds between tasks

Performance Targets (from Story 4-8 AC-2):
- p95 latency <60s for all endpoints
- Success rate >99%
- System stable under sustained load

Endpoints Tested:
- /health - Application health check
- /metrics - Prometheus metrics endpoint
- /api/v1/health - API-specific health check

Usage:
    locust -f tests/load/baseline_load_test_simple.py --headless \
           --users 10 --spawn-rate 2 --run-time 2m \
           --host http://localhost:8000
"""

from locust import FastHttpUser, task, between, events


class PublicEndpointUser(FastHttpUser):
    """
    Simulates user behavior testing public endpoints.

    Focuses on infrastructure validation without authentication complexity.
    Tests connection pooling, response times, and system stability.
    """

    wait_time = between(3, 7)  # Normal operational pace

    @task(10)
    def check_health(self):
        """
        Test main health endpoint (most frequent operation).

        Validates:
        - Application responsiveness
        - Database connectivity
        - Redis connectivity
        """
        with self.client.get("/health", catch_response=True) as resp:
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    if data.get("status") == "healthy":
                        resp.success()
                    else:
                        resp.failure(f"Unhealthy status: {data}")
                except Exception as e:
                    resp.failure(f"Invalid JSON response: {e}")
            else:
                resp.failure(f"Health check failed: {resp.status_code}")

    @task(5)
    def check_metrics(self):
        """
        Test Prometheus metrics endpoint.

        Validates:
        - Metrics collection working
        - Queue depth monitoring
        - Performance metrics available
        """
        with self.client.get("/metrics", catch_response=True) as resp:
            if resp.status_code == 200:
                # Check for expected Prometheus metrics
                if "ai_agents" in resp.text or "queue" in resp.text:
                    resp.success()
                else:
                    resp.failure("Expected metrics not found")
            else:
                resp.failure(f"Metrics unavailable: {resp.status_code}")

    @task(2)
    def check_api_health(self):
        """
        Test API-specific health endpoint.

        Validates:
        - API layer responsive
        - Health check endpoint working
        """
        with self.client.get("/api/v1/health", catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"API health check failed: {resp.status_code}")


# Event hooks for reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Print test configuration at start."""
    print("\n" + "="*80)
    print("SIMPLIFIED BASELINE LOAD TEST - Public Endpoints")
    print("="*80)
    print(f"Target Host: {environment.host}")
    print(f"Users: 10 concurrent")
    print(f"Duration: 2 minutes (shortened)")
    print(f"Endpoints: /health, /metrics, /api/v1/health")
    print(f"Performance Target: p95 <60s, success >99%")
    print("="*80 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print test summary at completion."""
    stats = environment.stats

    print("\n" + "="*80)
    print("SIMPLIFIED BASELINE LOAD TEST - RESULTS")
    print("="*80)
    print(f"Total Requests: {stats.total.num_requests}")
    print(f"Total Failures: {stats.total.num_failures}")

    if stats.total.num_requests > 0:
        success_rate = ((stats.total.num_requests - stats.total.num_failures) / stats.total.num_requests * 100)
        p95_ms = stats.total.get_response_time_percentile(0.95)

        print(f"Success Rate: {success_rate:.2f}%")
        print(f"Median Response Time: {stats.total.median_response_time}ms")
        print(f"p95 Response Time: {p95_ms:.0f}ms")
        print(f"p99 Response Time: {stats.total.get_response_time_percentile(0.99):.0f}ms")
        print(f"Requests/sec: {stats.total.total_rps:.2f}")

        print("\nPerformance Target Validation:")
        print(f"  p95 <60s (60000ms): {'✓ PASS' if p95_ms < 60000 else '✗ FAIL'} ({p95_ms:.0f}ms)")
        print(f"  Success >99%: {'✓ PASS' if success_rate > 99 else '✗ FAIL'} ({success_rate:.2f}%)")
    else:
        print("No requests completed")

    print("="*80 + "\n")
