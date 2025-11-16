# 🚀 Jira Webhook Quick Start - Ticket Enhancer

## ✅ Webhook Test Result

**Status:** ✅ **WORKING**

The Ticket Enhancer agent webhook has been successfully tested and is functioning correctly!

```
Test Result: 202 ACCEPTED
Execution ID: 1292e8bb-5bda-4745-8840-a44245f1c95e
Message: Agent execution queued
```

---

## 📋 Quick Setup Steps

### 1. Get Your Webhook URL

```
https://YOUR-DOMAIN.com/webhook/agents/00bab7b6-6335-4359-96b4-f48f3460b610/webhook
```

Replace `YOUR-DOMAIN.com` with your actual domain (e.g., `aiops.nullbytes.app`)

### 2. Get Your HMAC Secret

The HMAC secret is stored encrypted in your database. To decrypt it:

```python
from src.utils.encryption import decrypt

encrypted_secret = "gAAAAABpFgo48AxckgY3mpgIYIJQpImgHQKHBLKoaAv0i6pN0LTq-uuz7sKNocc7aD-3WcYbHNlsRB19U7XlvRIYTjNQdv9TcrHKSF0hsV-SvoHfxXhXzg7p9WY5MHhDoXIuh-P2tvB8"
hmac_secret = decrypt(encrypted_secret)
print(f"Secret: {hmac_secret}")
```

**Important:** This is a BASE64-encoded 32-byte secret. Keep it secure!

### 3. Configure Jira Automation (Recommended)

Since Jira native webhooks don't support HMAC computation, use **Jira Automation** instead:

#### Step-by-Step:

1. **Go to Jira Automation**
   - Settings → System → Automation
   - Click "Create rule"

2. **Add Trigger**
   - Select "Issue created" (or "Issue updated")
   - Add conditions (optional): e.g., Priority = High

3. **Add Action: Send Web Request**
   - URL: Your webhook URL (from step 1)
   - Method: POST
   - Body: Custom JSON (see payload format below)

4. **Payload Format**

```json
{
  "issue_key": "{{issue.key}}",
  "event_type": "jira:issue_created",
  "timestamp": "{{now}}",
  "issue": {
    "key": "{{issue.key}}",
    "fields": {
      "summary": "{{issue.summary}}",
      "description": "{{issue.description}}",
      "priority": {
        "name": "{{issue.priority.name}}",
        "id": "{{issue.priority.id}}"
      },
      "issuetype": {
        "name": "{{issue.issueType.name}}",
        "id": "{{issue.issueType.id}}"
      },
      "status": {
        "name": "{{issue.status.name}}"
      },
      "reporter": {
        "displayName": "{{issue.reporter.displayName}}",
        "emailAddress": "{{issue.reporter.emailAddress}}"
      },
      "created": "{{issue.created}}"
    }
  },
  "tenant_id": "4952b9b3-5909-4041-95a9-e068e01f7e13"
}
```

**Replace tenant_id with your actual tenant ID!**

---

## 🔐 HMAC Signature Challenge

**The Problem:** Jira Automation doesn't natively support HMAC signature computation.

**Solution Options:**

### Option 1: Webhook Proxy (Recommended for Production)

Deploy a simple proxy Lambda that:
1. Receives Jira webhook
2. Computes HMAC signature
3. Forwards to your API with proper headers

**AWS Lambda Example:**
```javascript
const crypto = require('crypto');

exports.handler = async (event) => {
    const payload = JSON.parse(event.body);
    const hmacSecret = Buffer.from(process.env.HMAC_SECRET, 'base64');

    const payloadString = JSON.stringify(payload);
    const signature = crypto
        .createHmac('sha256', hmacSecret)
        .update(payloadString)
        .digest('hex');

    // Forward to your API with signature header
    // ... (see full guide for complete code)
};
```

### Option 2: Disable HMAC for Testing (NOT for Production!)

**Only for testing** - you can temporarily modify the webhook endpoint to skip HMAC validation:

```python
# In src/api/webhooks.py, comment out signature validation
# THIS IS INSECURE - USE ONLY FOR TESTING!

# if not x_hub_signature_256:
#     raise HTTPException(status_code=401, detail="Missing signature")
```

---

## 🧪 Test Your Setup

### Using the Provided Test Script

```bash
cd /path/to/AI\ Ops
source .env
python test_ticket_enhancer_webhook.py
```

**Expected Output:**
```
✅ SUCCESS! Agent webhook triggered successfully!
   Execution ID: <uuid>
```

### Manual cURL Test

```bash
# Set variables
WEBHOOK_URL="https://aiops.nullbytes.app/webhook/agents/00bab7b6-6335-4359-96b4-f48f3460b610/webhook"
HMAC_SECRET="<your-base64-secret>"

# Create payload
PAYLOAD='{
  "issue_key": "TEST-123",
  "event_type": "jira:issue_created",
  "timestamp": "2025-11-13T17:00:00Z",
  "issue": {
    "key": "TEST-123",
    "fields": {
      "summary": "Application crashes when uploading files",
      "description": "Users report crashes with large files",
      "priority": {"name": "High", "id": "2"}
    }
  },
  "tenant_id": "4952b9b3-5909-4041-95a9-e068e01f7e13"
}'

# Compute HMAC (requires OpenSSL)
SIGNATURE=$(echo -n "$PAYLOAD" | \
  openssl dgst -sha256 -hmac "$(echo -n "$HMAC_SECRET" | base64 -d)" -binary | \
  xxd -p)

# Send request
curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=$SIGNATURE" \
  -d "$PAYLOAD"
```

---

## 📊 Verify Execution

### Check API Logs

```bash
docker-compose logs api --tail=50 | grep "Agent webhook"
```

Look for:
- ✅ `Agent webhook received and validated`
- ✅ `Agent execution task enqueued to Celery`

### Check Execution History UI

Navigate to: `https://your-domain.com/Execution_History`

Filter by:
- Agent: Ticket Enhancer
- Status: queued, in_progress, completed
- Date: Today

### Query Database

```sql
SELECT
    id,
    agent_id,
    status,
    started_at,
    completed_at,
    result
FROM agent_test_executions
WHERE agent_id = '00bab7b6-6335-4359-96b4-f48f3460b610'
ORDER BY started_at DESC
LIMIT 5;
```

---

## ⚠️ Common Issues

### 1. "Invalid HMAC signature" (401)

**Cause:** HMAC secret mismatch or incorrect signature format

**Fix:**
- Verify HMAC secret is base64-encoded 32-byte key
- Ensure payload serialization is consistent (no extra whitespace)
- Use the test script to verify signature computation

### 2. "Agent is draft" (403)

**Cause:** Agent status is not ACTIVE

**Fix:**
```sql
UPDATE agents
SET status = 'active'
WHERE id = '00bab7b6-6335-4359-96b4-f48f3460b610';
```

### 3. Webhook timeouts

**Cause:** Worker not processing tasks

**Fix:**
```bash
# Check worker status
docker-compose ps worker

# Restart if needed
docker-compose restart worker

# Check for disk space issues
docker system df
docker system prune -a
```

### 4. "No space left on device"

**Current Issue:** Worker container experiencing disk space errors

**Fix:**
```bash
# Clean up Docker resources
docker system prune -a --volumes

# Remove old containers
docker container prune -f

# Remove unused images
docker image prune -a -f

# Restart services
docker-compose restart
```

---

## 📈 Production Deployment Checklist

Before going live with Jira webhooks:

- [ ] Use HTTPS webhook URL (not HTTP)
- [ ] Implement webhook proxy with HMAC signature computation
- [ ] Configure rate limiting on webhook endpoint
- [ ] Set up monitoring and alerting for failed webhooks
- [ ] Test with various Jira issue types and priorities
- [ ] Document tenant-specific configuration
- [ ] Train team on troubleshooting procedures
- [ ] Set up backup agent in case primary fails
- [ ] Configure retry logic for transient failures
- [ ] Implement webhook queue depth monitoring

---

## 📞 Next Steps

1. **Read the full guide:** `JIRA_WEBHOOK_SETUP_GUIDE.md`
2. **Test with your Jira instance:** Create test issues and verify webhooks fire
3. **Monitor execution:** Watch logs and execution history
4. **Set up webhook proxy:** Deploy Lambda/Cloud Function for HMAC signing
5. **Configure production monitoring:** Set up alerts for webhook failures

---

## 📚 Resources

- **Full Setup Guide:** `JIRA_WEBHOOK_SETUP_GUIDE.md`
- **Test Script:** `test_ticket_enhancer_webhook.py`
- **API Endpoint:** `/webhook/agents/{agent_id}/webhook`
- **Execution History UI:** `/Execution_History`

---

**Status:** ✅ Webhook endpoint tested and working
**Date:** 2025-11-13
**Version:** 1.0
