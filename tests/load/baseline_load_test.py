"""
Baseline Load Test for AI Agents Enhancement Workflow.

Simulates normal operational load to establish performance baselines.

Test Configuration:
- Users: 10 concurrent users
- Duration: 5 minutes
- Spawn Rate: 2 users/second
- Wait Time: 3-7 seconds between tasks

Performance Targets (from Story 4-8 AC-2):
- p95 latency <60s for complete enhancement workflow
- Success rate >99%
- Queue processing adequate for expected load

Usage:
    # Start API server first
    docker-compose up -d api

    # Run baseline test
    locust -f tests/load/baseline_load_test.py --headless \
           --users 10 --spawn-rate 2 --run-time 5m \
           --host http://localhost:8000
"""

import uuid
import json
import hmac
import hashlib
from datetime import datetime, UTC
from locust import FastHttpUser, task, between, events


class TicketEnhancementUser(FastHttpUser):
    """
    Simulates typical user behavior for ticket enhancement workflow.

    Workflow: Webhook → Queue → Context Gathering → LLM Synthesis → Ticket Update
    """

    wait_time = between(3, 7)  # Normal operational pace

    # Test tenant configuration (must exist in database)
    tenant_id = "load-test-tenant"
    webhook_secret = "load-test-secret-minimum-32-chars-required-here"

    def on_start(self):
        """Initialize test user - verify API is reachable."""
        with self.client.get("/health", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"Health check failed: {resp.status_code}")

    @task(10)
    def submit_ticket_for_enhancement(self):
        """
        Submit ticket via webhook for enhancement (most common operation).

        Validates:
        - Webhook signature verification
        - Job queued to Redis
        - 202 Accepted response
        - Job ID returned
        """
        ticket_id = f"TKT-LOAD-{uuid.uuid4().hex[:8]}"

        payload = {
            "event": "ticket_created",
            "ticket_id": ticket_id,
            "tenant_id": self.tenant_id,
            "description": "Load test: Server experiencing intermittent timeouts",
            "priority": "medium",
            "created_at": datetime.now(UTC).isoformat(),
        }

        # Generate HMAC signature (as ServiceDesk Plus would)
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
            headers=headers
        ) as resp:
            if resp.status_code == 202:
                if "job_id" in resp.js:
                    resp.success()
                else:
                    resp.failure("No job_id in response")
            elif resp.status_code == 401:
                resp.failure("Authentication failed - check webhook secret")
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(3)
    def check_enhancement_status(self):
        """
        Check enhancement history status (periodic monitoring operation).

        Validates:
        - Tenant filtering works correctly
        - Response time acceptable
        - Data format correct
        """
        with self.rest(
            "GET",
            f"/enhancements/history?tenant_id={self.tenant_id}&limit=10"
        ) as resp:
            if resp.status_code == 200:
                if isinstance(resp.js, list):
                    resp.success()
                else:
                    resp.failure(f"Unexpected response format: {type(resp.js)}")
            else:
                resp.failure(f"Status check failed: {resp.status_code}")

    @task(1)
    def get_queue_depth(self):
        """
        Monitor queue depth for capacity planning (infrequent operation).

        Validates:
        - Metrics endpoint accessible
        - Queue depth data available
        """
        with self.client.get("/metrics", catch_response=True) as resp:
            if resp.status_code == 200:
                # Prometheus metrics format expected
                if "queue_depth" in resp.text or "ai_agents" in resp.text:
                    resp.success()
                else:
                    resp.failure("Expected metrics not found in response")
            else:
                resp.failure(f"Metrics unavailable: {resp.status_code}")


# Event hooks for custom reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Print test configuration at start."""
    print("\n" + "="*80)
    print("BASELINE LOAD TEST - Normal Operational Load")
    print("="*80)
    print(f"Target Host: {environment.host}")
    print(f"Expected Users: 10")
    print(f"Duration: 5 minutes")
    print(f"Performance Target: p95 <60s, success >99%")
    print("="*80 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print test summary at completion."""
    stats = environment.stats

    print("\n" + "="*80)
    print("BASELINE LOAD TEST - RESULTS SUMMARY")
    print("="*80)
    print(f"Total Requests: {stats.total.num_requests}")
    print(f"Total Failures: {stats.total.num_failures}")
    print(f"Success Rate: {((stats.total.num_requests - stats.total.num_failures) / stats.total.num_requests * 100):.2f}%")
    print(f"Median Response Time: {stats.total.median_response_time}ms")
    print(f"p95 Response Time: {stats.total.get_response_time_percentile(0.95)}ms")
    print(f"p99 Response Time: {stats.total.get_response_time_percentile(0.99)}ms")
    print(f"Requests/sec: {stats.total.total_rps:.2f}")

    # Validate performance targets
    p95_ms = stats.total.get_response_time_percentile(0.95)
    success_rate = (stats.total.num_requests - stats.total.num_failures) / stats.total.num_requests * 100

    print("\nPerformance Target Validation:")
    print(f"  p95 <60s (60000ms): {'✓ PASS' if p95_ms < 60000 else '✗ FAIL'} ({p95_ms:.0f}ms)")
    print(f"  Success >99%: {'✓ PASS' if success_rate > 99 else '✗ FAIL'} ({success_rate:.2f}%)")
    print("="*80 + "\n")
