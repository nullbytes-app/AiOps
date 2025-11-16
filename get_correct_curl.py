#!/usr/bin/env python3
"""
Decrypt the actual HMAC secret from database and generate correct cURL command.

This script retrieves the encrypted HMAC secret from the database,
decrypts it using the ENCRYPTION_KEY, and generates a valid cURL command.
"""

import hmac
import hashlib
import json
import os
import sys
from cryptography.fernet import Fernet

# Load encryption key from environment
ENCRYPTION_KEY = "G9e1weVb1mr8UMnD4pIro9O5F_sEy2BVrQIRWi0E0WE="
BASE_URL = "http://localhost:8000"
AGENT_ID = "6125bdcf-389e-4f1d-bad2-b03357adb0c7"  # Ticker Enhancer

# Encrypted HMAC secret from database
ENCRYPTED_HMAC = "gAAAAABpD_K6NjN8qvGCy8E1zaTXxHP6Bf76YPkR2u5MGuNMD9UpyegaCxBfYkMAQ3_0SwiZIhCQ7YyFsQuvMn579JKvh0F9npGZ4zqhwq2eUVC_bzHaWDy2WswYBS-SdcYj-oOD9RLt"


def decrypt_hmac_secret(encrypted_secret: str, encryption_key: str) -> str:
    """Decrypt the HMAC secret using Fernet encryption."""
    try:
        cipher = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        plaintext = cipher.decrypt(encrypted_secret.encode("utf-8"))
        return plaintext.decode("utf-8")
    except Exception as e:
        print(f"❌ Decryption failed: {e}", file=sys.stderr)
        sys.exit(1)


def generate_curl_command(agent_id: str, payload: dict, hmac_secret: str) -> tuple:
    """Generate cURL command with HMAC signature."""
    import base64

    # Convert payload to JSON string (compact format)
    payload_str = json.dumps(payload, separators=(',', ':'))

    # IMPORTANT: The secret is base64-encoded, decode it first
    # This matches the webhook_service.py validation logic
    secret_bytes = base64.b64decode(hmac_secret)

    # Generate HMAC-SHA256 signature using the decoded secret bytes
    signature = hmac.new(
        secret_bytes,
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

    print("\n🔓 Decrypting HMAC secret from database...")
    hmac_secret = decrypt_hmac_secret(ENCRYPTED_HMAC, ENCRYPTION_KEY)
    print(f"✅ Decrypted HMAC secret: {hmac_secret[:10]}...{hmac_secret[-10:]}")

    curl_cmd, signature, payload_json = generate_curl_command(AGENT_ID, test_payload, hmac_secret)

    print("\n" + "="*90)
    print("🎯 TICKER ENHANCER AGENT - CORRECT cURL COMMAND FOR POSTMAN")
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
