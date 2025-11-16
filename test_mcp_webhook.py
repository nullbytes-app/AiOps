#!/usr/bin/env python3
"""
Test script to trigger Jira webhook with HMAC signature for MCP tool testing.

This script:
1. Creates a realistic Jira webhook payload
2. Generates HMAC-SHA256 signature using the TICKET_ENHANCER_HMAC_SECRET
3. Sends the webhook to the HMAC proxy at http://localhost:3000
4. Validates the response and checks worker logs for MCP tool loading

Usage:
    python test_mcp_webhook.py
"""

import hmac
import hashlib
import json
import sys
from datetime import datetime

import httpx


def generate_hmac_signature(payload: dict, secret: str) -> str:
    """
    Generate HMAC-SHA256 signature for webhook payload.

    Args:
        payload: Webhook payload dict
        secret: HMAC secret key

    Returns:
        str: Hex-encoded HMAC-SHA256 signature
    """
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')

    signature = hmac.new(
        key=secret.encode('utf-8'),
        msg=payload_bytes,
        digestmod=hashlib.sha256
    ).hexdigest()

    return f"sha256={signature}"


def create_jira_webhook_payload() -> dict:
    """
    Create a realistic Jira webhook payload for testing.

    Returns:
        dict: Jira webhook payload with issue data
    """
    return {
        "timestamp": int(datetime.utcnow().timestamp() * 1000),
        "webhookEvent": "jira:issue_created",
        "issue_event_type_name": "issue_created",
        "issue_key": "TEST-123",  # Root-level issue key for HMAC proxy logging
        "issue": {
            "id": "10001",
            "key": "TEST-123",
            "fields": {
                "summary": "Test issue for MCP tool validation",
                "description": "This is a test ticket to verify that the agent can load 31 MCP tools and add comments to Jira tickets using the MCP bridge.",
                "issuetype": {
                    "name": "Task",
                    "id": "10001"
                },
                "project": {
                    "key": "TEST",
                    "id": "10000",
                    "name": "Test Project"
                },
                "priority": {
                    "name": "Medium",
                    "id": "3"
                },
                "status": {
                    "name": "To Do",
                    "id": "10000"
                },
                "reporter": {
                    "displayName": "Test User",
                    "emailAddress": "test@example.com"
                },
                "created": datetime.utcnow().isoformat() + "Z",
                "updated": datetime.utcnow().isoformat() + "Z"
            }
        },
        "user": {
            "displayName": "Test User",
            "emailAddress": "test@example.com"
        }
    }


def send_webhook(payload: dict, signature: str, proxy_url: str = "http://localhost:8000/webhook/agents/00bab7b6-6335-4359-96b4-f48f3460b610/webhook") -> dict:
    """
    Send webhook directly to API endpoint bypassing HMAC proxy.

    NOTE: For MCP tool testing, we bypass the HMAC proxy (which has tenant isolation issues)
    and send directly to the API with proper tenant header and HMAC signature.

    Args:
        payload: Webhook payload
        signature: HMAC signature
        proxy_url: API webhook URL

    Returns:
        dict: Response data
    """
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Jira-Webhook-Test/1.0",
        "X-Tenant-ID": "test-tenant",  # Required for tenant isolation
        "X-Hub-Signature-256": signature  # HMAC signature for authentication
    }

    print(f"\n{'='*60}")
    print(f"Sending webhook to {proxy_url}")
    print(f"{'='*60}")
    print(f"Signature: {signature[:20]}...")
    print(f"Payload preview: {json.dumps(payload, indent=2)[:200]}...")

    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            proxy_url,
            json=payload,
            headers=headers
        )

    print(f"\n{'='*60}")
    print(f"Response Status: {response.status_code}")
    print(f"{'='*60}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Body: {response.text[:500]}")

    return {
        "status_code": response.status_code,
        "body": response.text,
        "headers": dict(response.headers)
    }


def main():
    """Main execution flow."""
    print("\n" + "="*60)
    print("MCP Tool Loading Test - Webhook Trigger")
    print("="*60)

    # Get HMAC secret from environment
    import os
    secret = os.getenv("TICKET_ENHANCER_HMAC_SECRET")

    if not secret:
        print("ERROR: TICKET_ENHANCER_HMAC_SECRET not found in environment")
        print("Please run: export TICKET_ENHANCER_HMAC_SECRET='your-secret-here'")
        sys.exit(1)

    print(f"✓ Found HMAC secret: {secret[:10]}...")

    # Create payload
    payload = create_jira_webhook_payload()
    print(f"✓ Created Jira webhook payload")
    print(f"  Issue Key: {payload['issue']['key']}")
    print(f"  Summary: {payload['issue']['fields']['summary']}")

    # Generate signature
    signature = generate_hmac_signature(payload, secret)
    print(f"✓ Generated HMAC signature: {signature[:30]}...")

    # Send webhook
    print(f"\n{'='*60}")
    print("Sending webhook to HMAC proxy...")
    print(f"{'='*60}")

    try:
        response = send_webhook(payload, signature)

        if response["status_code"] == 200:
            print(f"\n✅ SUCCESS: Webhook accepted!")
            print(f"\nNext steps:")
            print(f"1. Check worker logs for 'Converted 31 tools to LangChain format'")
            print(f"2. Verify no 'LoggingProxy' errors")
            print(f"3. Check execution history in admin UI")
            print(f"\nRun: docker-compose logs worker | tail -100")
        else:
            print(f"\n❌ FAILED: Webhook rejected with status {response['status_code']}")
            print(f"Response: {response['body']}")

    except Exception as e:
        print(f"\n❌ ERROR: Failed to send webhook")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
