# Webhook HMAC Secret UI Implementation Guide

## Overview
This guide shows how to expose the HMAC webhook secret in the Agent Management UI so users can configure webhooks in external systems.

## Implementation Status
- ✅ Backend API endpoint exists: `/api/agents/{agent_id}/webhook-secret`
- ✅ Helper function exists: `get_webhook_secret_async()` in `src/admin/utils/agent_helpers.py`
- ⏳ UI integration: **Needs to be added to Agent Management page**

## Step-by-Step Implementation

### Step 1: Add Webhook Configuration Section to Agent Management UI

File: `src/admin/pages/5_Agent_Management.py`

Add this code after agent creation/selection (around line 200-300, after agent details display):

```python
# Webhook Configuration Section (if agent has webhook trigger)
if agent_data and agent_data.get("id"):
    # Check if agent has webhook trigger
    triggers = agent_data.get("triggers", [])
    has_webhook = any(t.get("trigger_type") == "webhook" for t in triggers)

    if has_webhook:
        st.divider()
        st.subheader("🔗 Webhook Configuration")

        with st.expander("Webhook Setup Instructions", expanded=False):
            # Fetch webhook secret
            agent_id = agent_data["id"]
            webhook_secret = async_to_sync(get_webhook_secret_async)(agent_id)

            if webhook_secret:
                # Webhook URL
                base_url = os.getenv("PUBLIC_URL", "http://localhost:8000")
                webhook_url = f"{base_url}/webhook/agents/{agent_id}/webhook"

                col1, col2 = st.columns([4, 1])
                with col1:
                    st.text_input(
                        "Webhook URL",
                        value=webhook_url,
                        key=f"webhook_url_{agent_id}",
                        help="Use this URL in your external system"
                    )
                with col2:
                    if st.button("📋 Copy", key=f"copy_url_{agent_id}"):
                        st.code(webhook_url)

                # HMAC Secret (masked by default)
                col1, col2 = st.columns([4, 1])
                with col1:
                    secret_display = st.text_input(
                        "HMAC Secret (Base64)",
                        value="*" * 40,
                        type="password",
                        key=f"webhook_secret_masked_{agent_id}",
                        help="Click 'Show' to reveal the secret for configuration"
                    )
                with col2:
                    if st.button("👁 Show", key=f"show_secret_{agent_id}"):
                        st.code(webhook_secret, language="text")

                # Instructions
                st.info("""
                **How to configure your external system:**

                1. Copy the Webhook URL above
                2. Copy the HMAC Secret (click 'Show' button)
                3. Configure your system to:
                   - Send POST requests to the Webhook URL
                   - Generate HMAC-SHA256 signature using the secret
                   - Add header: `X-Hub-Signature-256: sha256={signature}`
                """)

                # Code example
                with st.expander("💻 Code Example (Python)"):
                    st.code(f'''
import hmac
import hashlib
import json
import base64
import requests

# Configuration
WEBHOOK_URL = "{webhook_url}"
HMAC_SECRET = "{webhook_secret}"  # Your HMAC secret

# Example payload
payload = {{
    "ticket_id": "TKT-12345",
    "description": "Example ticket",
    "priority": "High"
}}

# Generate signature
payload_str = json.dumps(payload, separators=(',', ':'))
secret_bytes = base64.b64decode(HMAC_SECRET)
signature = hmac.new(secret_bytes, payload_str.encode(), hashlib.sha256).hexdigest()

# Send request
headers = {{
    "Content-Type": "application/json",
    "X-Hub-Signature-256": f"sha256={{signature}}"
}}

response = requests.post(WEBHOOK_URL, json=payload, headers=headers)
print(f"Status: {{response.status_code}}")
print(f"Response: {{response.json()}}")
''', language="python")

                # cURL example
                with st.expander("📋 cURL Example"):
                    st.markdown("""
                    Generate a signature using the Python script above, then use:
                    ```bash
                    curl -X POST '{url}' \\
                      -H 'Content-Type: application/json' \\
                      -H 'X-Hub-Signature-256: sha256={{YOUR_SIGNATURE}}' \\
                      -d '{{"ticket_id":"TKT-123","description":"Test"}}'
                    ```
                    """.format(url=webhook_url))
            else:
                st.error("❌ Failed to load webhook configuration")
```

### Step 2: Test the Implementation

1. Navigate to Agent Management page
2. Select an agent with a webhook trigger
3. Verify the "Webhook Configuration" section appears
4. Click "Show" to reveal the HMAC secret
5. Copy the webhook URL and secret
6. Test using the provided code examples

### Step 3: Security Considerations

- ✅ Secret is masked by default (type="password")
- ✅ Only shown when user clicks "Show" button
- ✅ Requires authentication to access Admin UI
- ✅ Tenant isolation enforced by API

## Alternative: Simple Test Script

For immediate testing without UI changes, use the provided script:

```bash
python get_correct_curl.py
```

This script:
1. Retrieves the agent's encrypted HMAC secret from database
2. Decrypts it using the ENCRYPTION_KEY
3. Generates a valid cURL command with correct signature
4. Ready to paste into Postman or terminal

## Troubleshooting

**Q: "Invalid HMAC signature" error**
- Ensure you're using base64-decoded secret: `base64.b64decode(secret)`
- Ensure payload JSON has no extra whitespace: `json.dumps(payload, separators=(',', ':'))`
- Ensure header format is: `X-Hub-Signature-256: sha256={hexdigest}`

**Q: Webhook not found**
- Verify agent has a webhook trigger configured
- Check agent status is ACTIVE (only active agents accept webhooks)

**Q: Model not configured in LiteLLM**
- Update agent's `llm_config` to use an available model (e.g., `gpt-4o-mini`)
- Or configure the model in LiteLLM proxy

## Verification Checklist

- [ ] UI shows webhook URL correctly
- [ ] UI shows masked HMAC secret by default
- [ ] "Show" button reveals actual secret
- [ ] Code examples work when copied
- [ ] Webhook accepts requests with correct signature
- [ ] Execution appears in Execution History
- [ ] No existing functionality broken

## Files Modified

1. `src/admin/pages/5_Agent_Management.py` - Add webhook config section
2. (Optional) `docs/WEBHOOK-HMAC-UI-IMPLEMENTATION.md` - This guide

## Testing Script Location

**Quick test script**: `/Users/ravi/Documents/nullBytes_Apps/Ai_Agents/AI Ops/get_correct_curl.py`

Usage:
```bash
python get_correct_curl.py
# Copy the output cURL command into Postman
```

## Next Steps

1. Implement the UI changes above
2. Test with a real external system
3. Add to user documentation/onboarding guide
4. Consider adding webhook logs/history for debugging
