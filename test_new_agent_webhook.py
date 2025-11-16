#!/usr/bin/env python3
"""
Test script for new agent webhook.
Tests the webhook endpoint with a simple "hello dude how are you" message.
"""

import hmac
import hashlib
import json
import requests
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))
from src.utils.encryption import decrypt

# Agent ID and webhook URL
AGENT_ID = "93ef8d24-1de9-4e28-b994-e0d91ba92418"
WEBHOOK_URL = f"https://aiopsapi.nullbytes.app/webhook/agents/{AGENT_ID}/webhook"

# Encrypted HMAC secret from database
ENCRYPTED_SECRET = "gAAAAABpFfE49XhRF58hcjZ-Do3TcQ2J_B-vQPIv12ZF98WNBze3q7sDpyCOoR2Wnle-tg3fIJnIsITcBKlq6it4GvF_BXjZGeRCzuP1lKU1j2d0bm9GlwQonhlt4WTxfU9WL2pzQi0p"

# Test payload with "hello dude how are you" message
payload = {
    "message": "hello dude how are you",
    "timestamp": "2025-11-14T10:00:00Z",
    "test": True
}


def generate_hmac_signature(payload_json: str, secret: str) -> str:
    """
    Generate HMAC-SHA256 signature for webhook payload.

    Args:
        payload_json: JSON string of the payload
        secret: Base64-encoded HMAC secret key

    Returns:
        Signature in format: sha256={hexdigest}
    """
    import base64

    # Decode base64 secret to bytes
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
    print("Testing New Agent Webhook")
    print("=" * 80)

    # Decrypt the HMAC secret
    try:
        hmac_secret = decrypt(ENCRYPTED_SECRET)
        print(f"✓ HMAC secret decrypted successfully")
        print(f"  Secret length: {len(hmac_secret)} chars")
    except Exception as e:
        print(f"✗ Failed to decrypt HMAC secret: {e}")
        return

    # Serialize payload to JSON
    payload_json = json.dumps(payload, sort_keys=True)
    print(f"\n✓ Payload prepared:")
    print(f"  Message: {payload['message']}")
    print(f"  Payload: {payload_json}")

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
            timeout=30
        )

        print(f"\n✓ Response received:")
        print(f"  Status Code: {response.status_code}")
        try:
            response_json = response.json()
            print(f"  Response Body: {json.dumps(response_json, indent=2)}")

            if response.status_code == 202:
                print("\n✅ SUCCESS! Agent webhook triggered successfully!")
                execution_id = response_json.get("execution_id")
                print(f"   Execution ID: {execution_id}")
                print(f"   You can track execution status using this ID")
            else:
                print(f"\n⚠️  Unexpected status code: {response.status_code}")
        except:
            print(f"  Response Text: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"\n✗ Request failed: {e}")
    except Exception as e:
        print(f"\n✗ Error: {e}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
