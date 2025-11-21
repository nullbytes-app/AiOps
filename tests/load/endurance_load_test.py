"""
Endurance Load Test for AI Agents Enhancement Workflow.

Validates system stability under sustained load over extended duration.

Test Configuration:
- Users: 50 concurrent users
- Duration: 30 minutes
- Spawn Rate: 5 users/second
- Wait Time: 4-8 seconds between tasks

Objectives:
- Detect memory leaks
- Identify connection pool exhaustion
- Validate queue processing consistency
- Ensure no performance degradation over time

Performance Targets (from Story 4-8 AC-2):
- p95 latency remains <60s throughout test
- Success rate >99% maintained
- No memory growth >20% over duration
- Response times stable (no degradation)

Usage:
    # Monitor system metrics during test:
    # - Memory: kubectl top pods
    # - Connections: netstat -an | grep ESTABLISHED | wc -l
    # - Queue: Redis CLI> LLEN enhancement_queue

    # Run endurance test (30 min)
    locust -f tests/load/endurance_load_test.py --headless \
           --users 50 --spawn-rate 5 --run-time 30m \
           --host http://localhost:8000

    # Or shorter 5min test for quick validation:
    locust -f tests/load/endurance_load_test.py --headless \
           --users 50 --spawn-rate 5 --run-time 5m \
           --host http://localhost:8000
"""

import uuid
import json
import hmac
import hashlib
import random
import time
from datetime import datetime, UTC
from locust import FastHttpUser, task, between, events


class EnduranceTestUser(FastHttpUser):
    """
    Simulates realistic sustained user behavior over extended periods.

    Characteristics:
    - Moderate wait times (4-8s) for realistic pacing
    - Balanced task distribution
    - Connection reuse to test pool management
    - Varied payload sizes to test memory handling
    """

    wait_time = between(4, 8)  # Realistic sustained pace

    tenant_id = "load-test-tenant"
    webhook_secret = "load-test-secret-minimum-32-chars-required-here"

    # Varied descriptions for memory testing (different sizes)
    ticket_scenarios = [
        # Short descriptions
        "App crashed",
        "Login failed",
        "Page slow",
        # Medium descriptions
        "Users reporting intermittent errors when accessing the dashboard. Error occurs roughly 30% of the time.",
        "Database connection timeout after 30 seconds. Affects all queries to customer_data table.",
        # Long descriptions (stress GC and memory)
        "Detailed issue description with extensive logs:\n" + ("ERROR: Connection failed\n" * 50),
        "Performance degradation observed over 4 hour period. System starts responsive but gradually slows. " * 10,
    ]

    def on_start(self):
        """Verify system health before starting endurance test."""
        with self.client.get("/health") as resp:
            if resp.status_code != 200:
                resp.failure("System not healthy - aborting endurance test")
                self.environment.runner.quit()

    @task(10)
    def submit_varied_tickets(self):
        """
        Submit tickets with varying payload sizes.

        Purpose: Test memory handling and GC under sustained load.
        """
        ticket_id = f"END-{uuid.uuid4().hex[:8].upper()}"

        # Randomly select description size
        description = random.choice(self.ticket_scenarios)

        payload = {
            "event": "ticket_created",
            "ticket_id": ticket_id,
            "tenant_id": self.tenant_id,
            "description": description,
            "priority": random.choice(["low", "medium", "high"]),
            "created_at": datetime.now(UTC).isoformat(),
            "requester": f"endurance{random.randint(1, 100)}@test.com",
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
            name="/webhooks/servicedesk/[tenant_id]"
        ) as resp:
            if resp.status_code == 202:
                if "job_id" in resp.js:
                    resp.success()
                else:
                    resp.failure("No job_id in response")
            else:
                resp.failure(f"Webhook failed: {resp.status_code}")

    @task(5)
    def monitor_enhancement_history(self):
        """
        Regularly poll enhancement history.

        Purpose: Test connection pool handling and pagination consistency.
        """
        # Vary pagination to test different query patterns
        limit = random.choice([10, 20, 50])
        offset = random.choice([0, 10, 20])

        with self.rest(
            "GET",
            f"/enhancements/history?tenant_id={self.tenant_id}&limit={limit}&offset={offset}",
            catch_response=True,
            name="/enhancements/history"
        ) as resp:
            if resp.status_code == 200:
                if isinstance(resp.js, list):
                    # Verify pagination works correctly
                    if len(resp.js) <= limit:
                        resp.success()
                    else:
                        resp.failure(f"Pagination broken: got {len(resp.js)} items, limit was {limit}")
                else:
                    resp.failure("Invalid response format")
            else:
                resp.failure(f"History query failed: {resp.status_code}")

    @task(3)
    def check_specific_ticket_status(self):
        """
        Look up specific ticket enhancements.

        Purpose: Test query performance and index usage over time.
        """
        # Simulate looking up recent tickets
        ticket_id = f"END-{uuid.uuid4().hex[:8].upper()}"

        with self.rest(
            "GET",
            f"/enhancements/{ticket_id}",
            catch_response=True,
            name="/enhancements/[ticket_id]"
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 404:
                # Expected for random lookups
                resp.success()
            else:
                resp.failure(f"Ticket lookup failed: {resp.status_code}")

    @task(2)
    def queue_depth_monitoring(self):
        """
        Monitor queue metrics throughout test.

        Purpose: Detect queue buildup or processing stalls.
        """
        with self.client.get("/metrics") as resp:
            if resp.status_code == 200:
                # Validate metrics format hasn't degraded
                if "ai_agents" in resp.text or "queue_depth" in resp.text:
                    resp.success()
                else:
                    resp.failure("Metrics format changed or degraded")
            else:
                resp.failure(f"Metrics unavailable: {resp.status_code}")

    @task(1)
    def periodic_health_check(self):
        """
        Regular health checks to detect degradation.

        Purpose: Early detection of system issues during endurance.
        """
        with self.client.get("/health") as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Health check failed: {resp.status_code}")


# Track performance degradation over time
performance_snapshots = []


@events.request.add_listener
def track_performance_over_time(request_type, name, response_time, response_length, exception, context, **kwargs):
    """Capture response time samples every minute for degradation analysis."""
    current_time = time.time()

    # Sample every 60 seconds
    if not performance_snapshots or current_time - performance_snapshots[-1]["timestamp"] > 60:
        performance_snapshots.append({
            "created_at": current_time,
            "response_time": response_time,
            "failed": exception is not None,
            "endpoint": name
        })


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Print endurance test configuration and monitoring guidelines."""
    print("\n" + "="*80)
    print("ENDURANCE LOAD TEST - Sustained Load Stability")
    print("="*80)
    print(f"Target Host: {environment.host}")
    print(f"Users: 50 concurrent")
    print(f"Duration: 30 minutes (use --run-time flag to adjust)")
    print("\nObjectives:")
    print("  - Detect memory leaks")
    print("  - Identify connection pool exhaustion")
    print("  - Validate consistent queue processing")
    print("  - Ensure no performance degradation")
    print("\nMonitoring Checklist:")
    print("  [ ] CPU usage stable (<80%)")
    print("  [ ] Memory growth <20% over duration")
    print("  [ ] Connection pool not exhausted")
    print("  [ ] Queue depth stable (not growing)")
    print("  [ ] Response times consistent")
    print("="*80 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Analyze endurance test for performance degradation."""
    stats = environment.stats

    print("\n" + "="*80)
    print("ENDURANCE LOAD TEST - RESULTS SUMMARY")
    print("="*80)
    print(f"Total Requests: {stats.total.num_requests}")
    print(f"Total Failures: {stats.total.num_failures}")
    print(f"Success Rate: {((stats.total.num_requests - stats.total.num_failures) / stats.total.num_requests * 100):.2f}%")
    print(f"Median Response Time: {stats.total.median_response_time}ms")
    print(f"p95 Response Time: {stats.total.get_response_time_percentile(0.95)}ms")
    print(f"p99 Response Time: {stats.total.get_response_time_percentile(0.99)}ms")
    print(f"Average RPS: {stats.total.total_rps:.2f}")

    # Analyze performance degradation
    if len(performance_snapshots) >= 2:
        first_5min = [s["response_time"] for s in performance_snapshots[:5]]
        last_5min = [s["response_time"] for s in performance_snapshots[-5:]]

        if first_5min and last_5min:
            early_avg = sum(first_5min) / len(first_5min)
            late_avg = sum(last_5min) / len(last_5min)
            degradation_pct = ((late_avg - early_avg) / early_avg) * 100

            print("\nPerformance Degradation Analysis:")
            print(f"  Early avg response time (first 5 min): {early_avg:.0f}ms")
            print(f"  Late avg response time (last 5 min): {late_avg:.0f}ms")
            print(f"  Degradation: {degradation_pct:+.1f}%")

            if degradation_pct > 20:
                print("\n⚠️  WARNING: Significant performance degradation detected!")
                print("    Potential causes:")
                print("    - Memory leak (check heap growth)")
                print("    - Connection pool exhaustion")
                print("    - Database query performance degradation")
                print("    - Queue backlog building up")
            elif degradation_pct > 0:
                print("  → Minor degradation observed (acceptable)")
            else:
                print("  ✓ Performance stable or improved")

    # Validate endurance targets
    success_rate = (stats.total.num_requests - stats.total.num_failures) / stats.total.num_requests * 100
    p95_ms = stats.total.get_response_time_percentile(0.95)

    print("\nEndurance Target Validation:")
    print(f"  Success >99%: {'✓ PASS' if success_rate > 99 else '✗ FAIL'} ({success_rate:.2f}%)")
    print(f"  p95 <60s: {'✓ PASS' if p95_ms < 60000 else '✗ FAIL'} ({p95_ms:.0f}ms)")

    # Additional stability insights
    print("\nStability Metrics:")
    print(f"  Test Duration: {stats.total.last_request_timestamp - stats.total.start_time:.1f}s")
    print(f"  Total Throughput: {stats.total.num_requests} requests")
    print(f"  Failure Rate: {(stats.total.num_failures / stats.total.num_requests * 100):.3f}%")

    print("\nNext Steps:")
    print("  1. Review memory metrics: kubectl top pods")
    print("  2. Check for connection leaks: netstat -an | grep ESTABLISHED")
    print("  3. Verify queue processed all jobs: Redis LLEN enhancement_queue")
    print("  4. Review application logs for errors or warnings")

    print("="*80 + "\n")
