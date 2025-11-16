#!/usr/bin/env python3
"""
Trigger Ticket Enhancer Agent via webhook with HMAC signature.
"""

import hmac
import hashlib
import json
import httpx
from datetime import datetime


# Configuration
AGENT_ID = "00bab7b6-6335-4359-96b4-f48f3460b610"
WEBHOOK_URL = f"http://localhost:8000/webhook/agents/{AGENT_ID}/webhook"
HMAC_SECRET = "/x+ww+KF3SJlISBaD2ieCqkxjzY3i368w8+4Xj7O6Ik="

# Test payload (simulating Jira webhook)
payload = {
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000+0000"),
    "webhookEvent": "jira:issue_created",
    "issue_event_type_name": "issue_created",
    "issue": {
        "id": "10003",
        "key": "KAN-3",
        "fields": {
            "summary": "Database connection timeout",
            "description": "Users experiencing timeout errors when connecting to production database",
            "issuetype": {"name": "Bug"},
            "priority": {"name": "High"},
            "status": {"name": "To Do"}
        }
    }
}


def generate_hmac_signature(payload_str: str, secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook payload."""
    signature = hmac.new(
        secret.encode('utf-8'),
        payload_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"


def main():
    print("🚀 Triggering Ticket Enhancer Agent...")
    print(f"Agent ID: {AGENT_ID}")
    print(f"Webhook URL: {WEBHOOK_URL}")
    print()

    # Serialize payload to JSON bytes (EXACTLY as httpx will send it)
    # httpx uses json.dumps with separators=(',', ': ') by default
    payload_str = json.dumps(payload, separators=(',', ': '))
    payload_bytes = payload_str.encode('utf-8')

    # Generate HMAC signature on raw bytes
    signature = generate_hmac_signature(payload_str, HMAC_SECRET)
    print(f"🔐 Generated HMAC signature: {signature[:50]}...")
    print(f"Payload length: {len(payload_bytes)} bytes")
    print()

    # Send webhook request
    headers = {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": signature
    }

    print("📤 Sending webhook request...")
    try:
        response = httpx.post(WEBHOOK_URL, json=payload, headers=headers, timeout=30.0)

        print(f"📥 Response status: {response.status_code}")
        print(f"📥 Response body:")
        print(json.dumps(response.json(), indent=2))

        if response.status_code == 202:
            execution_id = response.json().get("execution_id")
            print()
            print(f"✅ Agent execution queued successfully!")
            print(f"Execution ID: {execution_id}")
            print()
            print("📊 Monitor execution:")
            print(f"   docker-compose logs worker -f | grep {execution_id}")
            print()
            print("🔍 Check execution in Streamlit:")
            print("   Navigate to Execution History page")
        else:
            print(f"⚠️  Unexpected status code: {response.status_code}")

    except Exception as e:
        print(f"❌ Request failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
