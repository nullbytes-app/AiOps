"""
Peak Load Test for AI Agents Enhancement Workflow.

Simulates maximum expected load to validate system capacity under peak conditions.

Test Configuration:
- Users: 100 concurrent users
- Duration: 10 minutes
- Spawn Rate: 10 users/second
- Wait Time: 2-5 seconds between tasks

Performance Targets (from Story 4-8 AC-2):
- p95 latency <60s for complete enhancement workflow
- Success rate >99%
- No resource exhaustion (memory, connections, queue capacity)

Usage:
    # Start API server with production-like resources
    docker-compose up -d api redis postgres

    # Run peak load test
    locust -f tests/load/peak_load_test.py --headless \
           --users 100 --spawn-rate 10 --run-time 10m \
           --host http://localhost:8000
"""

import uuid
import json
import hmac
import hashlib
import random
from datetime import datetime, UTC
from locust import FastHttpUser, task, between, events


class PeakLoadUser(FastHttpUser):
    """
    Simulates aggressive user behavior during peak traffic periods.

    Characteristics:
    - Shorter wait times (2-5s vs 3-7s baseline)
    - Higher webhook submission rate
    - More frequent status checks
    - Realistic ticket descriptions for load testing
    """

    wait_time = between(2, 5)  # Aggressive but realistic pace

    tenant_id = "load-test-tenant"
    webhook_secret = "load-test-secret-minimum-32-chars-required-here"

    # Realistic ticket descriptions for variety
    ticket_descriptions = [
        "Database queries timing out after 30 seconds",
        "API endpoint returning 500 errors intermittently",
        "Memory leak causing gradual performance degradation",
        "Login page not responding for multiple users",
        "File upload failing for files >10MB",
        "Search functionality returning incomplete results",
        "Email notifications delayed by several hours",
        "Mobile app crashing on iOS 18 devices",
        "Payment processing stuck in pending state",
        "Reports generation taking >5 minutes",
    ]

    priorities = ["low", "medium", "high", "critical"]

    def on_start(self):
        """Verify API health before starting load."""
        with self.client.get("/health") as resp:
            if resp.status_code != 200:
                resp.failure(f"Health check failed: {resp.status_code}")
                self.environment.runner.quit()  # Stop test if API is down

    @task(15)
    def submit_high_priority_ticket(self):
        """
        Submit ticket with realistic data (higher weight for peak testing).

        Validates system handles:
        - Variable payload sizes
        - Different priority levels
        - Signature verification at scale
        """
        ticket_id = f"PEAK-{uuid.uuid4().hex[:8].upper()}"

        payload = {
            "event": "ticket_created",
            "ticket_id": ticket_id,
            "tenant_id": self.tenant_id,
            "description": random.choice(self.ticket_descriptions),
            "priority": random.choice(self.priorities),
            "created_at": datetime.now(UTC).isoformat(),
            "requester": f"user{random.randint(1, 1000)}@company.com",
            "category": random.choice(["infrastructure", "application", "security"]),
        }

        payload_str = json.dumps(payload, separators=(",", ":"))
        signature = hmac.new(
            self.webhook_secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-ServiceDesk-Signature": signature,
        }

        with self.rest(
            "POST",
            f"/webhook/servicedesk",
            json=payload,
            headers=headers,
            catch_response=True,
            name="/webhooks/servicedesk/[tenant_id]"  # Aggregate in stats
        ) as resp:
            if resp.status_code == 202:
                if resp.js and "job_id" in resp.js:
                    resp.success()
                else:
                    resp.failure("Missing job_id in 202 response")
            elif resp.status_code == 503:
                # Service unavailable acceptable under extreme load
                resp.failure("Service unavailable - may indicate capacity issue")
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(5)
    def check_enhancement_status(self):
        """Poll enhancement history more frequently during peak."""
        limit = random.choice([5, 10, 20])  # Variable page sizes

        with self.rest(
            "GET",
            f"/enhancements/history?tenant_id={self.tenant_id}&limit={limit}",
            catch_response=True,
            name="/enhancements/history"
        ) as resp:
            if resp.status_code == 200:
                if isinstance(resp.js, list) and len(resp.js) <= limit:
                    resp.success()
                else:
                    resp.failure("Invalid pagination response")
            elif resp.status_code == 429:
                # Rate limiting acceptable
                resp.failure("Rate limited")
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(2)
    def get_queue_metrics(self):
        """Monitor queue depth - critical during peak load."""
        with self.client.get(
            "/metrics",
            catch_response=True,
            name="/metrics"
        ) as resp:
            if resp.status_code == 200:
                # Check for queue depth metric
                if "ai_agents_queue_depth" in resp.text or "queue_depth" in resp.text:
                    resp.success()
                else:
                    # Metrics exist but queue metric missing
                    resp.failure("Queue metrics not exposed")
            else:
                resp.failure(f"Metrics endpoint error: {resp.status_code}")

    @task(1)
    def health_check(self):
        """Periodic health checks to detect degradation."""
        with self.client.get("/health") as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Health check degraded: {resp.status_code}")


# Track queue depth over time
queue_depth_samples = []


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, context, **kwargs):
    """Track metrics endpoint responses for queue depth analysis."""
    if name == "/metrics" and not exception:
        # Parse queue depth from Prometheus metrics
        # This is a simplified example - real implementation would parse metrics format
        queue_depth_samples.append(response_time)


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Print peak test configuration."""
    print("\n" + "="*80)
    print("PEAK LOAD TEST - Maximum Expected Load")
    print("="*80)
    print(f"Target Host: {environment.host}")
    print(f"Expected Users: 100")
    print(f"Duration: 10 minutes")
    print(f"Performance Target: p95 <60s, success >99%")
    print(f"WARNING: This test will stress system resources significantly")
    print("="*80 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print detailed peak test results."""
    stats = environment.stats

    print("\n" + "="*80)
    print("PEAK LOAD TEST - RESULTS SUMMARY")
    print("="*80)
    print(f"Total Requests: {stats.total.num_requests}")
    print(f"Total Failures: {stats.total.num_failures}")
    print(f"Success Rate: {((stats.total.num_requests - stats.total.num_failures) / stats.total.num_requests * 100):.2f}%")
    print(f"Median Response Time: {stats.total.median_response_time}ms")
    print(f"p50 Response Time: {stats.total.get_response_time_percentile(0.50)}ms")
    print(f"p95 Response Time: {stats.total.get_response_time_percentile(0.95)}ms")
    print(f"p99 Response Time: {stats.total.get_response_time_percentile(0.99)}ms")
    print(f"Max Response Time: {stats.total.max_response_time}ms")
    print(f"Requests/sec: {stats.total.total_rps:.2f}")

    # Validate performance targets
    p95_ms = stats.total.get_response_time_percentile(0.95)
    success_rate = (stats.total.num_requests - stats.total.num_failures) / stats.total.num_requests * 100

    print("\nPerformance Target Validation:")
    print(f"  p95 <60s (60000ms): {'✓ PASS' if p95_ms < 60000 else '✗ FAIL'} ({p95_ms:.0f}ms)")
    print(f"  Success >99%: {'✓ PASS' if success_rate > 99 else '✗ FAIL'} ({success_rate:.2f}%)")

    # Additional peak load insights
    print("\nPeak Load Analysis:")
    print(f"  Concurrent Users: 100")
    print(f"  Peak RPS: {stats.total.total_rps:.2f}")
    print(f"  Average Latency: {stats.total.avg_response_time:.0f}ms")

    if p95_ms > 60000 or success_rate < 99:
        print("\n⚠️  CAPACITY WARNING: System failed to meet targets under peak load")
        print("    Consider: Horizontal scaling, caching, queue optimization")

    print("="*80 + "\n")
