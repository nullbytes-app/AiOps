"""
Burst Load Test for AI Agents Enhancement Workflow.

Simulates sudden traffic spikes to validate system resilience and auto-scaling.

Test Configuration:
- Phase 1: Warmup (1-10 users over 30s)
- Phase 2: Burst (10-200 users in 10s)
- Phase 3: Sustain (200 users for 2 min)
- Phase 4: Cool down (200-10 users over 30s)
- Total Duration: ~4 minutes

Performance Targets (from Story 4-8 AC-2):
- System remains responsive during burst
- Queue doesn't overflow
- Auto-scaling triggers appropriately (HPA)
- Recovery time <30s after burst

Usage:
    # Ensure K8s HPA is configured for api deployment
    kubectl get hpa ai-agents-api

    # Run burst test
    locust -f tests/load/burst_load_test.py --headless \
           --users 200 --spawn-rate 20 --run-time 4m \
           --host http://localhost:8000

    # Or use custom shape for precise control:
    locust -f tests/load/burst_load_test.py --headless \
           --host http://localhost:8000
"""

import uuid
import json
import hmac
import hashlib
import random
from datetime import datetime, UTC
from locust import FastHttpUser, task, between, events, LoadTestShape


class BurstTrafficUser(FastHttpUser):
    """
    Simulates user behavior during traffic burst scenarios.

    Characteristics:
    - Minimal wait time (1-2s) during burst
    - Focus on webhook submissions (primary load driver)
    - Reduced complexity to maximize request rate
    """

    wait_time = between(1, 2)  # Aggressive during burst

    tenant_id = "load-test-tenant"
    webhook_secret = "load-test-secret-minimum-32-chars-required-here"

    @task(20)
    def rapid_ticket_submission(self):
        """
        Submit tickets rapidly during burst scenario.

        Focus: Maximum throughput to stress queue ingestion.
        """
        ticket_id = f"BURST-{uuid.uuid4().hex[:6].upper()}"

        payload = {
            "event": "ticket_created",
            "ticket_id": ticket_id,
            "tenant_id": self.tenant_id,
            "description": f"Burst test ticket - {random.randint(1, 9999)}",
            "priority": random.choice(["medium", "high"]),
            "created_at": datetime.now(UTC).isoformat(),
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
                resp.success()
            elif resp.status_code == 503:
                # Service unavailable during burst acceptable if recovers quickly
                resp.failure("Service unavailable - burst overwhelmed system")
            elif resp.status_code == 429:
                # Rate limiting is acceptable burst protection
                resp.failure("Rate limited - burst protection active")
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(1)
    def minimal_monitoring(self):
        """Lightweight health check during burst."""
        with self.client.get("/health") as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Health degraded during burst: {resp.status_code}")


class BurstLoadShape(LoadTestShape):
    """
    Custom load shape simulating traffic burst pattern.

    Phases:
    1. Warmup: 0-30s, 1→10 users
    2. Burst: 30-40s, 10→200 users (20 users/sec spawn rate)
    3. Sustain: 40-160s, 200 users constant
    4. Cool down: 160-190s, 200→10 users
    5. Recovery: 190-240s, 10 users
    """

    stages = [
        # (duration_in_seconds, users, spawn_rate)
        {"duration": 30, "users": 10, "spawn_rate": 1},      # Warmup
        {"duration": 40, "users": 200, "spawn_rate": 20},    # Burst!
        {"duration": 160, "users": 200, "spawn_rate": 0},    # Sustain
        {"duration": 190, "users": 10, "spawn_rate": 10},    # Cool down
        {"duration": 240, "users": 10, "spawn_rate": 0},     # Recovery
    ]

    def tick(self):
        """
        Return (user_count, spawn_rate) for current time.

        Returns None when test should stop.
        """
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                if stage["spawn_rate"] > 0:
                    return (stage["users"], stage["spawn_rate"])
                else:
                    # Maintain user count
                    return (stage["users"], stage["users"])

        # Test complete
        return None


# Track response times during burst phases
burst_phase_stats = {
    "warmup": [],
    "burst": [],
    "sustain": [],
    "cooldown": [],
    "recovery": []
}


@events.request.add_listener
def track_burst_phases(request_type, name, response_time, response_length, exception, context, **kwargs):
    """Track response times by burst phase for analysis."""
    run_time = context.get("start_time", 0)

    if run_time < 30:
        phase = "warmup"
    elif run_time < 40:
        phase = "burst"
    elif run_time < 160:
        phase = "sustain"
    elif run_time < 190:
        phase = "cooldown"
    else:
        phase = "recovery"

    burst_phase_stats[phase].append({
        "time": run_time,
        "response_time": response_time,
        "failed": exception is not None
    })


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Print burst test configuration."""
    print("\n" + "="*80)
    print("BURST LOAD TEST - Traffic Spike Simulation")
    print("="*80)
    print(f"Target Host: {environment.host}")
    print("Test Phases:")
    print("  1. Warmup:    0-30s   (1→10 users)")
    print("  2. BURST:    30-40s   (10→200 users, 20/sec spawn)")
    print("  3. Sustain:  40-160s  (200 users constant)")
    print("  4. Cooldown: 160-190s (200→10 users)")
    print("  5. Recovery: 190-240s (10 users)")
    print("\nExpected Behavior:")
    print("  - Queue should absorb burst without data loss")
    print("  - HPA should scale workers during sustain phase")
    print("  - System should recover within 30s after cooldown")
    print("="*80 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print burst test analysis."""
    stats = environment.stats

    print("\n" + "="*80)
    print("BURST LOAD TEST - RESULTS SUMMARY")
    print("="*80)
    print(f"Total Requests: {stats.total.num_requests}")
    print(f"Total Failures: {stats.total.num_failures}")
    print(f"Success Rate: {((stats.total.num_requests - stats.total.num_failures) / stats.total.num_requests * 100):.2f}%")
    print(f"Median Response Time: {stats.total.median_response_time}ms")
    print(f"p95 Response Time: {stats.total.get_response_time_percentile(0.95)}ms")
    print(f"p99 Response Time: {stats.total.get_response_time_percentile(0.99)}ms")
    print(f"Max Response Time: {stats.total.max_response_time}ms")

    # Analyze burst phases
    print("\nPhase-by-Phase Analysis:")
    for phase, data in burst_phase_stats.items():
        if data:
            response_times = [d["response_time"] for d in data]
            failures = sum(1 for d in data if d["failed"])
            avg_rt = sum(response_times) / len(response_times)
            max_rt = max(response_times)

            print(f"\n{phase.upper()}:")
            print(f"  Requests: {len(data)}")
            print(f"  Failures: {failures} ({failures/len(data)*100:.1f}%)")
            print(f"  Avg Response Time: {avg_rt:.0f}ms")
            print(f"  Max Response Time: {max_rt:.0f}ms")

    # Validate burst resilience
    success_rate = (stats.total.num_requests - stats.total.num_failures) / stats.total.num_requests * 100
    p95_ms = stats.total.get_response_time_percentile(0.95)

    print("\nBurst Resilience Validation:")
    print(f"  Success >99%: {'✓ PASS' if success_rate > 99 else '✗ FAIL'} ({success_rate:.2f}%)")
    print(f"  p95 <60s: {'✓ PASS' if p95_ms < 60000 else '✗ FAIL'} ({p95_ms:.0f}ms)")

    # Burst-specific insights
    burst_data = burst_phase_stats.get("burst", [])
    if burst_data:
        burst_failures = sum(1 for d in burst_data if d["failed"])
        print(f"\nBurst Phase Specific:")
        print(f"  Requests during 10s burst: {len(burst_data)}")
        print(f"  Peak throughput: {len(burst_data)/10:.1f} req/s")
        print(f"  Failures during burst: {burst_failures}")

        if burst_failures / len(burst_data) > 0.01:  # >1% failure during burst
            print("\n⚠️  WARNING: System struggled during burst phase")
            print("    Recommendations:")
            print("    - Increase queue capacity (Redis maxmemory)")
            print("    - Lower HPA scale-up threshold")
            print("    - Add connection pooling")

    print("="*80 + "\n")
