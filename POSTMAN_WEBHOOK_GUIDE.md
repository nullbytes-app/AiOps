# Postman Webhook Testing Guide

## The Problem You're Experiencing

You're getting **401 Unauthorized - Invalid HMAC Signature** because Postman automatically reformats JSON when you select the "JSON" option in the Body dropdown. This changes the payload bytes, which breaks the HMAC signature validation.

## Solution: Use "Text" Mode Instead of "JSON"

### Method 1: Import the Postman Collection (EASIEST)

1. **Import the collection**:
   ```
   File: Ticket_Enhancer_Webhook.postman_collection.json
   ```
   - In Postman, click **Import**
   - Select the file `Ticket_Enhancer_Webhook.postman_collection.json`
   - Click **Import**

2. **Use the "Compact JSON" request**:
   - Open the imported collection
   - Select "Trigger Ticket Enhancer (Compact JSON)"
   - Click **Send**
   - ✅ You should get **202 Accepted** response!

### Method 2: Manual Setup (RECOMMENDED IF IMPORT FAILS)

1. **Create new POST request**:
   ```
   URL: http://localhost:8000/webhook/agents/907cb308-6629-4426-b7e6-dfe5bbf24bc6/webhook
   Method: POST
   ```

2. **Headers tab - Add these 2 headers**:
   ```
   Content-Type: application/json
   X-Hub-Signature-256: sha256=424d4d15574814a09a9415f16e18fe55f3bc6b8d48831d42fc98590f4bbee10d
   ```

3. **Body tab - THIS IS CRITICAL**:
   - Select **raw**
   - Select **Text** from the dropdown (⚠️ NOT "JSON"!)
   - Paste this EXACT text (no modifications):
   ```json
   {"ticket_id":"TKT-12345","subject":"Server performance issue","description":"The application server is running slow and users are experiencing timeouts","priority":"high","status":"open","created_at":"2025-11-09T09:15:00Z"}
   ```

4. **Click Send** → You should get **202 Accepted**!

## Why This Works

The HMAC signature is calculated on the **exact byte representation** of the JSON payload:

- **Compact format** (no spaces): `{"ticket_id":"TKT-12345",...}`
  - Signature: `424d4d15574814a09a9415f16e18fe55f3bc6b8d48831d42fc98590f4bbee10d`

- **Pretty format** (space after colon): `{"ticket_id": "TKT-12345",...}`
  - Signature: `db2849a817082b15d74ccfdeb1db4a1dfc45aab59a88fb343779ffd3fcd73400`

- **Indented format** (Postman beautify):
  ```json
  {
    "ticket_id": "TKT-12345",
    ...
  }
  ```
  - Signature: `d160690fb109997ddbfa88ce4fa8f4883c7c9a9bb64204343d5f513f3b98f810`

When you select "JSON" in Postman's dropdown, it auto-formats your JSON which changes the bytes and invalidates the signature!

## Testing Different Payloads

If you want to test with a different payload, you need to generate a new signature:

1. **Run the signature generator**:
   ```bash
   python3 generate_postman_signatures.py
   ```

2. **Copy the signature** for your chosen format

3. **Update the header** in Postman with the new signature

## Troubleshooting

### Still getting 401?

1. **Check you're using "Text" not "JSON"** in the Body dropdown
2. **Verify no extra spaces** in the payload
3. **Check the header** format: `X-Hub-Signature-256: sha256=<hash>` (must include `sha256=` prefix)
4. **Try the Postman collection** import instead of manual setup

### Want to modify the payload?

1. Edit the payload in `generate_postman_signatures.py`
2. Run the script to get new signatures
3. Update Postman with the new payload AND new signature
4. Remember: ANY change requires a new signature!

## Quick Reference

**Working curl command** (for comparison):
```bash
./working_webhook.sh
```

**Expected response**:
```json
{
  "message": "Webhook received and queued for processing",
  "execution_id": "<uuid>"
}
```

**Status code**: `202 Accepted`
