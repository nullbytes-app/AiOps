#!/usr/bin/env python3
"""
Generate cURL command with HMAC signature for testing Ticker Enhancer agent.

Usage:
    python test_ticker_enhancer.py

The script will output a cURL command that you can copy into Postman.
"""

import hmac
import hashlib
import json

# Configuration from .env
WEBHOOK_SECRET = "test-webhook-secret-minimum-32-chars-required-here"
BASE_URL = "http://localhost:8000"
AGENT_ID = "6125bdcf-389e-4f1d-bad2-b03357adb0c7"  # Ticker Enhancer

# Test payload - simulating a ServiceDesk ticket that needs enhancement
test_payload = {
    "ticket_id": "TKT-54321",
    "title": "App not working",
    "description": "The app crashes when I try to login",
    "priority": "Medium",
    "category": "Application",
    "reported_by": "john.doe@company.com",
    "created_at": "2025-11-09T10:30:00Z"
}

def generate_curl_command(agent_id: str, payload: dict) -> str:
    """Generate cURL command with HMAC signature."""

    # Convert payload to JSON string (compact format)
    payload_str = json.dumps(payload, separators=(',', ':'))

    # Generate HMAC-SHA256 signature
    signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload_str.encode(),
        hashlib.sha256
    ).hexdigest()

    # Format as GitHub-style header (sha256=hexdigest)
    signature_header = f"sha256={signature}"

    # Generate cURL command
    curl_command = f"""curl -X POST '{BASE_URL}/webhook/agents/{agent_id}/webhook' \\
  -H 'Content-Type: application/json' \\
  -H 'X-Hub-Signature-256: {signature_header}' \\
  -d '{payload_str}'"""

    return curl_command, signature_header, payload_str


if __name__ == "__main__":
    curl_cmd, signature, payload_json = generate_curl_command(AGENT_ID, test_payload)

    print("\n" + "="*90)
    print("🎯 TICKER ENHANCER AGENT - cURL COMMAND FOR POSTMAN")
    print("="*90)
    print("\n📋 OPTION 1: Copy this entire cURL command into Postman (Import → Raw Text):\n")
    print(curl_cmd)
    print("\n" + "="*90)
    print("\n📋 OPTION 2: Manual setup in Postman:")
    print("-"*90)
    print(f"Method:  POST")
    print(f"URL:     {BASE_URL}/webhook/agents/{AGENT_ID}/webhook")
    print(f"\nHeaders:")
    print(f"  Content-Type: application/json")
    print(f"  X-Hub-Signature-256: {signature}")
    print(f"\nBody (raw JSON):")
    print(json.dumps(test_payload, indent=2))
    print("="*90)

    print("\n✅ After sending the request:")
    print("   1. You'll receive: {\"status\": \"queued\", \"execution_id\": \"...\", \"message\": \"...\"}")
    print("   2. View in Streamlit: http://localhost:8501 → Execution History")
    print("   3. Or use API: curl http://localhost:8000/api/executions/{execution_id}")
    print("\n💡 Expected Result:")
    print("   The Ticker Enhancer agent should analyze the ticket and add more context")
    print("   to help L1 support agents better understand the issue.\n")
    print("="*90 + "\n")
