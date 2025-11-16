#!/usr/bin/env python3
"""
Test Ticket Enhancer agent by directly invoking the Celery task.
Bypasses webhook HMAC validation to test core agent execution.
"""

import asyncio
import sys
import uuid
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


async def test_agent_direct():
    """Test agent execution directly via Celery task."""
    from src.workers.tasks import execute_agent
    from datetime import datetime, UTC

    print("=" * 80)
    print("Direct Agent Execution Test - Ticket Enhancer")
    print("=" * 80)
    print()

    # Agent configuration
    agent_id = "00bab7b6-6335-4359-96b4-f48f3460b610"

    # Test payload (simulating Jira webhook)
    payload = {
        "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.000+0000"),
        "webhookEvent": "jira:issue_created",
        "issue_event_type_name": "issue_created",
        "issue": {
            "id": "10004",
            "key": "KAN-4",
            "fields": {
                "summary": "API response time degradation",
                "description": "Users reporting slow API responses for search endpoint. Response times increased from 200ms to 2s.",
                "issuetype": {"name": "Bug"},
                "priority": {"name": "High"},
                "status": {"name": "To Do"}
            }
        }
    }

    print(f"Agent ID: {agent_id}")
    print(f"Test Ticket: KAN-4 - API response time degradation")
    print()

    # Queue Celery task
    print("📤 Queueing Celery task...")
    try:
        result = execute_agent.delay(
            agent_id=agent_id,
            payload=payload
        )

        print(f"✅ Task queued successfully!")
        print(f"Task ID: {result.id}")
        print()
        print("📊 Monitor execution:")
        print(f"   docker-compose logs worker -f | grep {result.id}")
        print()
        print("🔍 Check result:")
        print(f"   result.get(timeout=300)  # Wait up to 5 minutes")
        print()

        # Wait for result (optional - with timeout)
        print("⏳ Waiting for agent execution to complete (timeout: 5 minutes)...")
        try:
            task_result = result.get(timeout=300)
            print()
            print("=" * 80)
            print("EXECUTION RESULT")
            print("=" * 80)
            print(f"Status: {task_result.get('status', 'unknown')}")
            print(f"Execution ID: {task_result.get('execution_id', 'N/A')}")
            print(f"Processing Time: {task_result.get('processing_time_ms', 0)}ms")
            print()

            if task_result.get('result'):
                import json
                result_data = task_result['result']
                print(f"Result Preview:")
                print(json.dumps(result_data, indent=2)[:1000])
                print()

        except Exception as wait_error:
            print(f"⚠️  Could not wait for result: {wait_error}")
            print("Task is still running. Check logs and execution history.")

    except Exception as e:
        print(f"❌ Failed to queue task: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_agent_direct())
