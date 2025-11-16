#!/usr/bin/env python3
"""
Test script for Ticket Enhancer agent webhook.

Tests the agent webhook endpoint with a sample Jira-like ticket payload.
"""

import hmac
import hashlib
import json
import requests
from src.utils.encryption import decrypt

# Ticket Enhancer Agent ID
AGENT_ID = "00bab7b6-6335-4359-96b4-f48f3460b610"

# Webhook URL (localhost for testing)
WEBHOOK_URL = f"http://localhost:8000/webhook/agents/{AGENT_ID}/webhook"

# Encrypted HMAC secret from database
ENCRYPTED_SECRET = "gAAAAABpFgo48AxckgY3mpgIYIJQpImgHQKHBLKoaAv0i6pN0LTq-uuz7sKNocc7aD-3WcYbHNlsRB19U7XlvRIYTjNQdv9TcrHKSF0hsV-SvoHfxXhXzg7p9WY5MHhDoXIuh-P2tvB8"

# Sample Jira-like ticket payload
payload = {
    "issue_key": "SUPPORT-12345",
    "event_type": "jira:issue_created",
    "timestamp": "2025-11-13T16:55:00Z",
    "issue": {
        "key": "SUPPORT-12345",
        "fields": {
            "summary": "Application crashes when uploading large files",
            "description": "Users are reporting that the application crashes when they try to upload files larger than 50MB. The error message shown is 'Connection timeout'. This happens consistently on both web and mobile app versions. Priority: High. Affected users: 25+",
            "priority": {
                "name": "High",
                "id": "2"
            },
            "issuetype": {
                "name": "Bug",
                "id": "1"
            },
            "status": {
                "name": "Open"
            },
            "reporter": {
                "displayName": "John Smith",
                "emailAddress": "john.smith@company.com"
            },
            "created": "2025-11-13T16:55:00+0000"
        }
    },
    "tenant_id": "4952b9b3-5909-4041-95a9-e068e01f7e13"
}


def generate_hmac_signature(payload_json: str, secret: str) -> str:
    """
    Generate HMAC-SHA256 signature for webhook payload.

    The secret is expected to be base64-encoded (as stored in the database).
    This function decodes it, computes HMAC, and returns the signature.

    Args:
        payload_json: JSON string of the payload
        secret: Base64-encoded HMAC secret key

    Returns:
        Signature in format: sha256={hexdigest}
    """
    import base64

    # Decode base64 secret to bytes (matching webhook_service.py logic)
    try:
        secret_bytes = base64.b64decode(secret)
    except Exception as e:
        print(f"Error decoding secret: {e}")
        # Try using secret as-is if not base64-encoded
        secret_bytes = secret.encode('utf-8')

    signature = hmac.new(
        secret_bytes,
        payload_json.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"


def main():
    print("=" * 80)
    print("Testing Ticket Enhancer Agent Webhook")
    print("=" * 80)

    # Decrypt the HMAC secret
    try:
        hmac_secret = decrypt(ENCRYPTED_SECRET)
        print(f"✓ HMAC secret decrypted successfully")
        print(f"  Secret length: {len(hmac_secret)} chars")
        print(f"  Secret (first 10 chars): {hmac_secret[:10]}...")

        # Check if it's base64-encoded
        import base64
        try:
            decoded = base64.b64decode(hmac_secret)
            print(f"  Secret is base64-encoded (decoded to {len(decoded)} bytes)")
        except Exception:
            print(f"  Secret is NOT base64-encoded (plain text)")
    except Exception as e:
        print(f"✗ Failed to decrypt HMAC secret: {e}")
        return

    # Serialize payload to JSON
    payload_json = json.dumps(payload, sort_keys=True)
    print(f"\n✓ Payload prepared:")
    print(f"  Issue Key: {payload['issue_key']}")
    print(f"  Summary: {payload['issue']['fields']['summary']}")
    print(f"  Priority: {payload['issue']['fields']['priority']['name']}")

    # Generate HMAC signature
    signature = generate_hmac_signature(payload_json, hmac_secret)
    print(f"\n✓ HMAC signature generated:")
    print(f"  Signature: {signature[:50]}...")

    # Prepare request headers
    headers = {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": signature,
    }

    # Send webhook request
    print(f"\n→ Sending webhook request to: {WEBHOOK_URL}")
    try:
        response = requests.post(
            WEBHOOK_URL,
            headers=headers,
            data=payload_json,
            timeout=10
        )

        print(f"\n✓ Response received:")
        print(f"  Status Code: {response.status_code}")
        print(f"  Response Body: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 202:
            print("\n✅ SUCCESS! Agent webhook triggered successfully!")
            execution_id = response.json().get("execution_id")
            print(f"   Execution ID: {execution_id}")
            print(f"   You can track execution status using this ID")
        else:
            print(f"\n⚠️  Unexpected status code: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"\n✗ Request failed: {e}")
    except Exception as e:
        print(f"\n✗ Error: {e}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
