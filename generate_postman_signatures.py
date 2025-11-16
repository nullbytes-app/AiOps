#!/usr/bin/env python3
"""
Generate HMAC signatures for different JSON formats for Postman testing.
"""
import base64
import hashlib
import hmac
import json

# Decrypted HMAC secret (base64 encoded)
HMAC_SECRET_BASE64 = "jz4HF9DjUHv4twGy1EkjdujxKC7gqrjkaJsMLz8gbw0="

# Test payload
PAYLOAD = {
    "ticket_id": "TKT-12345",
    "subject": "Server performance issue",
    "description": "The application server is running slow and users are experiencing timeouts",
    "priority": "high",
    "status": "open",
    "created_at": "2025-11-09T09:15:00Z"
}

def generate_signature(payload_bytes: bytes, secret_base64: str) -> str:
    """Generate HMAC-SHA256 signature."""
    secret_bytes = base64.b64decode(secret_base64)
    return hmac.new(secret_bytes, payload_bytes, hashlib.sha256).hexdigest()

print("="*80)
print("POSTMAN WEBHOOK SIGNATURE GENERATOR")
print("="*80)

# Test different JSON formats that Postman might use
formats = [
    ("Compact (no spaces)", json.dumps(PAYLOAD, separators=(',', ':'))),
    ("Pretty (space after colon)", json.dumps(PAYLOAD, separators=(',', ': '))),
    ("Standard (Python default)", json.dumps(PAYLOAD)),
    ("Indented (Postman beautify)", json.dumps(PAYLOAD, indent=2)),
]

print("\nGenerated signatures for different JSON formats:\n")

for name, payload_json in formats:
    payload_bytes = payload_json.encode('utf-8')
    signature = generate_signature(payload_bytes, HMAC_SECRET_BASE64)

    print(f"Format: {name}")
    print(f"Signature: sha256={signature}")
    print(f"Payload preview: {payload_json[:100]}...")
    print(f"Payload length: {len(payload_bytes)} bytes")
    print("-" * 80)

print("\n" + "="*80)
print("COPY THIS FOR POSTMAN:")
print("="*80)

# Show the exact format for Postman
compact_json = json.dumps(PAYLOAD, separators=(',', ':'))
compact_sig = generate_signature(compact_json.encode('utf-8'), HMAC_SECRET_BASE64)

print("\n1. Use this in the Body (Raw, Text - NOT JSON dropdown):")
print(compact_json)

print("\n2. Use this in the Headers:")
print(f"X-Hub-Signature-256: sha256={compact_sig}")

print("\n⚠️  IMPORTANT: In Postman Body tab:")
print("   - Select 'raw'")
print("   - Select 'Text' from dropdown (NOT 'JSON'!)")
print("   - This prevents Postman from reformatting your JSON")
print("\n" + "="*80)
