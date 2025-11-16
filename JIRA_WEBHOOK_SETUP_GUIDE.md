# 📘 Jira Webhook Setup Guide for Ticket Enhancer Agent

This guide provides step-by-step instructions for configuring Jira webhooks to trigger your Ticket Enhancer agent automatically when issues are created or updated.

## ✅ Prerequisites

Before setting up the Jira webhook, ensure you have:

1. **Active Ticket Enhancer Agent**
   - Agent status must be `ACTIVE` (not draft/suspended/inactive)
   - Agent ID: `00bab7b6-6335-4359-96b4-f48f3460b610`

2. **Webhook URL**
   ```
   https://your-domain.com/webhook/agents/00bab7b6-6335-4359-96b4-f48f3460b610/webhook
   ```
   Replace `your-domain.com` with your actual API domain (e.g., `aiops.nullbytes.app`)

3. **HMAC Secret**
   - Stored securely in database
   - Base64-encoded 32-byte key
   - Required for webhook signature validation

4. **Jira Admin Access**
   - Permission to create webhooks in your Jira instance
   - Access to Jira Administration panel

---

## 📋 Step 1: Get Your Webhook Configuration

### 1.1 Retrieve Webhook Details from Database

Connect to your database and run:

```sql
SELECT
    a.id as agent_id,
    a.name as agent_name,
    at.webhook_url,
    at.hmac_secret
FROM agents a
JOIN agent_triggers at ON a.id = at.agent_id
WHERE a.name = 'Ticket Enhancer'
  AND at.trigger_type = 'webhook'
  AND a.status = 'active';
```

**Expected Output:**
```
agent_id                              | Ticket Enhancer
webhook_url                           | http://api:8000/agents/{uuid}/webhook
hmac_secret                           | gAAAAAB... (encrypted)
```

### 1.2 Decrypt HMAC Secret

Use the provided Python script to decrypt your HMAC secret:

```python
from src.utils.encryption import decrypt

encrypted_secret = "gAAAAABpFgo48AxckgY3mpgIY..."  # From database
hmac_secret = decrypt(encrypted_secret)
print(f"HMAC Secret: {hmac_secret}")
```

**Important:** Keep this secret secure! It's used to validate webhook authenticity.

---

## 🔧 Step 2: Configure Jira Webhook

### 2.1 Access Jira Webhook Settings

1. Log in to your Jira instance as an administrator
2. Navigate to: **⚙️ Settings (gear icon) → System**
3. In the left sidebar, under "Advanced", click **WebHooks**
4. Click the **Create a WebHook** button

### 2.2 Basic Webhook Configuration

Fill in the following fields:

| Field | Value | Notes |
|-------|-------|-------|
| **Name** | `Ticket Enhancer - AI Agent` | Descriptive name for the webhook |
| **Status** | ✅ Enabled | Must be enabled for webhook to fire |
| **URL** | `https://your-domain.com/webhook/agents/00bab7b6-6335-4359-96b4-f48f3460b610/webhook` | Replace with your actual API URL |

**Example URL:**
```
https://aiops.nullbytes.app/webhook/agents/00bab7b6-6335-4359-96b4-f48f3460b610/webhook
```

### 2.3 Webhook Security Configuration

#### Add Custom Header for HMAC Signature

You'll need to add the `X-Hub-Signature-256` header with the computed HMAC signature. Since Jira doesn't natively support computed signatures, you have two options:

**Option A: Use Jira Automation (Recommended)**

1. Instead of using native webhooks, use **Jira Automation** with **Send Web Request** action
2. This allows you to compute the HMAC signature using Jira's Smart Values
3. More details in Section 3 below

**Option B: Use a Webhook Proxy**

1. Set up an intermediate webhook proxy service (e.g., Zapier, n8n, or custom Lambda)
2. Proxy receives Jira webhook → Computes HMAC → Forwards to your API
3. More complex but more flexible

**For this guide, we'll use Option A (Jira Automation).**

---

## 🤖 Step 3: Set Up Jira Automation (Recommended Method)

### 3.1 Create New Automation Rule

1. Go to: **⚙️ Settings → System → Automation**
2. Click **Create rule** (top right)
3. Choose **Custom** template
4. Click **Select** to start building

### 3.2 Configure Trigger

**Trigger Type:** Issue created, Issue updated

1. Click **+ Add trigger**
2. Select **Issue created** from the list
3. *(Optional)* Click **+ Add trigger** again and select **Issue updated** if you want to trigger on updates too

**Filter Configuration (Optional):**
- You can add filters to only trigger for specific projects, issue types, or priorities
- Example: Only trigger for issues in project "SUPPORT" with priority "High" or "Critical"

### 3.3 Add Condition (Optional but Recommended)

To avoid triggering on every single issue, add conditions:

1. Click **+ Add condition**
2. Select **Issue fields condition**
3. Configure:
   - **Field:** Priority
   - **Condition:** equals
   - **Value:** High, Critical (select multiple)

### 3.4 Add Action: Send Web Request

This is the core step that replaces the native webhook:

1. Click **+ Add action**
2. Select **Send web request**

**Configure the Web Request:**

| Field | Value |
|-------|-------|
| **Webhook URL** | `https://your-domain.com/webhook/agents/00bab7b6-6335-4359-96b4-f48f3460b610/webhook` |
| **HTTP method** | POST |
| **Webhook body** | Custom data (JSON) |

**Custom JSON Body:**

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

**⚠️ Important:** Replace `tenant_id` with your actual tenant ID from the database.

### 3.5 Add HMAC Signature Header

**The Challenge:** Jira Automation doesn't support HMAC computation directly.

**Solution:** Use a custom script connector or middleware service:

1. **Option 1: Create a custom Jira Connect app** (for advanced users)
2. **Option 2: Use webhook proxy service** (simpler)
3. **Option 3: Temporarily disable HMAC validation** (for testing only - NOT recommended for production)

**For Production Use (Option 2 - Webhook Proxy):**

1. Deploy a simple Node.js/Python Lambda function that:
   - Receives Jira webhook
   - Computes HMAC signature
   - Forwards to your API with proper headers

**Example Lambda Function (Node.js):**

```javascript
const crypto = require('crypto');
const https = require('https');

exports.handler = async (event) => {
    const payload = JSON.parse(event.body);
    const hmacSecret = process.env.HMAC_SECRET; // Base64-encoded secret

    // Compute HMAC signature
    const secretBytes = Buffer.from(hmacSecret, 'base64');
    const payloadString = JSON.stringify(payload);
    const signature = crypto
        .createHmac('sha256', secretBytes)
        .update(payloadString)
        .digest('hex');

    // Forward to your API
    const options = {
        hostname: 'aiops.nullbytes.app',
        path: '/webhook/agents/00bab7b6-6335-4359-96b4-f48f3460b610/webhook',
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Hub-Signature-256': `sha256=${signature}`
        }
    };

    return new Promise((resolve, reject) => {
        const req = https.request(options, (res) => {
            resolve({
                statusCode: res.statusCode,
                body: 'Forwarded successfully'
            });
        });

        req.on('error', reject);
        req.write(payloadString);
        req.end();
    });
};
```

### 3.6 Test the Automation

1. Click **Turn on rule** (top right)
2. Give it a name: "Trigger Ticket Enhancer on New Issues"
3. Click **Turn it on**

4. **Create a test issue:**
   - Go to your Jira project
   - Create a new issue with High priority
   - Wait 10-30 seconds
   - Check your API logs to verify webhook was received

---

## 🧪 Step 4: Test the Webhook

### 4.1 Using the Provided Test Script

We've provided a test script that simulates a Jira webhook:

```bash
cd /path/to/your/project
source .env
python test_ticket_enhancer_webhook.py
```

**Expected Output:**
```
================================================================================
Testing Ticket Enhancer Agent Webhook
================================================================================
✓ HMAC secret decrypted successfully
✓ Payload prepared
✓ HMAC signature generated
✓ Response received:
  Status Code: 202
  Response Body: {
    "status": "queued",
    "execution_id": "1292e8bb-5bda-4745-8840-a44245f1c95e",
    "message": "Agent execution queued"
  }

✅ SUCCESS! Agent webhook triggered successfully!
```

### 4.2 Verify Agent Execution

Check if the agent actually processed the ticket:

```bash
# Check API logs
docker-compose logs api | grep "Agent webhook"

# Check worker logs
docker-compose logs worker | grep "execute_agent"

# Query database for execution record
psql -h localhost -p 5433 -U aiagents -d ai_agents -c \
  "SELECT * FROM agent_test_executions WHERE id = 'YOUR_EXECUTION_ID' LIMIT 1;"
```

### 4.3 Test from Jira

1. Create a test issue in Jira that matches your automation conditions
2. Verify the issue was created successfully
3. Check your API logs for incoming webhook:
   ```bash
   docker-compose logs api --tail=100 | grep "Agent webhook"
   ```

4. Look for these log entries:
   - `Agent webhook received and validated`
   - `Agent execution task enqueued to Celery`

---

## 📊 Step 5: Monitor Webhook Performance

### 5.1 Check API Metrics

View webhook metrics in your monitoring dashboard:

```bash
# Prometheus metrics endpoint
curl http://localhost:8000/metrics | grep agent_webhook
```

### 5.2 View Execution History

Access the Execution History page in your admin UI:

```
https://aiops.nullbytes.app/Execution_History
```

Filter by:
- **Agent:** Ticket Enhancer
- **Status:** queued, in_progress, completed, failed
- **Date Range:** Last 7 days

### 5.3 Check Celery Queue Status

```bash
docker-compose exec worker celery -A src.workers.celery_app inspect active
docker-compose exec worker celery -A src.workers.celery_app inspect reserved
```

---

## 🔒 Security Best Practices

### 1. HMAC Secret Management

- ✅ **DO:** Store HMAC secret encrypted in database
- ✅ **DO:** Use environment variables for encryption keys
- ✅ **DO:** Rotate secrets periodically (every 90 days)
- ❌ **DON'T:** Commit secrets to version control
- ❌ **DON'T:** Share secrets via email or chat

### 2. Network Security

- ✅ **DO:** Use HTTPS for webhook URLs (not HTTP)
- ✅ **DO:** Restrict webhook IPs if possible (Jira IP ranges)
- ✅ **DO:** Enable rate limiting on webhook endpoints
- ❌ **DON'T:** Expose webhook endpoints publicly without authentication

### 3. Payload Validation

- ✅ **DO:** Define and validate payload schema
- ✅ **DO:** Sanitize and validate all input fields
- ✅ **DO:** Log invalid payloads for security monitoring
- ❌ **DON'T:** Trust webhook data blindly

### 4. Error Handling

- ✅ **DO:** Return 202 Accepted immediately (async processing)
- ✅ **DO:** Log all webhook attempts (success and failure)
- ✅ **DO:** Implement retry logic for transient failures
- ❌ **DON'T:** Block webhook response on long-running operations

---

## 🐛 Troubleshooting

### Issue 1: "Invalid HMAC signature" Error

**Symptoms:**
```json
{
  "detail": "Invalid HMAC signature"
}
```

**Causes:**
1. HMAC secret mismatch between Jira and your API
2. Payload serialization differences
3. Secret not base64-encoded

**Solutions:**
1. Verify HMAC secret in database matches what Jira is using
2. Ensure JSON payload is serialized consistently (no extra whitespace)
3. Check that secret is base64-encoded:
   ```python
   import base64
   secret = "your_secret_here"
   print(len(base64.b64decode(secret)))  # Should be 32 bytes
   ```

### Issue 2: "Agent not found" Error

**Symptoms:**
```json
{
  "detail": "Agent not found"
}
```

**Causes:**
1. Incorrect agent UUID in webhook URL
2. Agent deleted from database
3. Cross-tenant access attempt

**Solutions:**
1. Verify agent exists and is ACTIVE:
   ```sql
   SELECT id, name, status FROM agents
   WHERE id = '00bab7b6-6335-4359-96b4-f48f3460b610';
   ```
2. Check webhook URL matches agent ID exactly
3. Ensure tenant_id in payload matches agent's tenant

### Issue 3: "Agent is draft/suspended" Error

**Symptoms:**
```json
{
  "detail": "Agent is draft, only ACTIVE agents can be triggered"
}
```

**Solution:**
Activate the agent:
```sql
UPDATE agents
SET status = 'active'
WHERE id = '00bab7b6-6335-4359-96b4-f48f3460b610';
```

### Issue 4: Webhook Timeouts

**Symptoms:**
- Jira reports webhook timeout errors
- Webhook succeeds but takes > 10 seconds

**Causes:**
1. Database connection pool exhausted
2. Worker queue backed up
3. Network latency

**Solutions:**
1. Scale up worker replicas:
   ```yaml
   # docker-compose.yml
   worker:
     deploy:
       replicas: 3
   ```

2. Increase Redis queue size:
   ```python
   # config.py
   REDIS_MAX_CONNECTIONS = 50
   ```

3. Monitor queue depth:
   ```bash
   redis-cli LLEN enhancement_queue
   ```

### Issue 5: Webhook Received but Not Processed

**Symptoms:**
- API returns 202 Accepted
- No agent execution occurs
- Worker logs show no activity

**Causes:**
1. Worker not running
2. Celery queue connection issues
3. Worker disk space full

**Solutions:**
1. Check worker status:
   ```bash
   docker-compose ps worker
   ```

2. Restart worker:
   ```bash
   docker-compose restart worker
   ```

3. Check worker logs:
   ```bash
   docker-compose logs worker --tail=100
   ```

4. Verify Redis connectivity:
   ```bash
   docker-compose exec worker redis-cli ping
   ```

---

## 📚 Additional Resources

### API Documentation
- Webhook Endpoint: `/webhook/agents/{agent_id}/webhook`
- Method: `POST`
- Headers Required: `X-Hub-Signature-256`, `Content-Type: application/json`
- Response: `202 Accepted` with execution_id

### Database Schema
```sql
-- Agents table
CREATE TABLE agents (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(100),
    name VARCHAR(255),
    status VARCHAR(20),
    -- ... other fields
);

-- Agent triggers table
CREATE TABLE agent_triggers (
    id UUID PRIMARY KEY,
    agent_id UUID REFERENCES agents(id),
    trigger_type VARCHAR(50),  -- 'webhook' or 'schedule'
    webhook_url VARCHAR(500),
    hmac_secret TEXT,  -- Encrypted
    payload_schema JSONB
);
```

### Example cURL Request

```bash
#!/bin/bash

AGENT_ID="00bab7b6-6335-4359-96b4-f48f3460b610"
WEBHOOK_URL="https://aiops.nullbytes.app/webhook/agents/$AGENT_ID/webhook"
HMAC_SECRET="your_base64_secret"

PAYLOAD='{
  "issue_key": "TEST-123",
  "event_type": "jira:issue_created",
  "timestamp": "2025-11-13T17:00:00Z",
  "issue": {
    "fields": {
      "summary": "Test issue",
      "description": "Test description",
      "priority": {"name": "High"}
    }
  },
  "tenant_id": "4952b9b3-5909-4041-95a9-e068e01f7e13"
}'

# Compute HMAC signature
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$(echo -n "$HMAC_SECRET" | base64 -d)" -binary | xxd -p)

# Send request
curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=$SIGNATURE" \
  -d "$PAYLOAD"
```

---

## ✅ Checklist: Production Readiness

Before deploying to production, verify:

- [ ] HMAC secrets are stored encrypted
- [ ] Webhook URLs use HTTPS (not HTTP)
- [ ] Agent status is ACTIVE
- [ ] Rate limiting is configured
- [ ] Monitoring and alerting are set up
- [ ] Worker auto-scaling is configured
- [ ] Backup and disaster recovery plans are in place
- [ ] Security audit has been performed
- [ ] Load testing has been completed
- [ ] Documentation is up to date

---

## 📞 Support

For issues or questions:

1. Check the troubleshooting section above
2. Review API logs: `docker-compose logs api`
3. Review worker logs: `docker-compose logs worker`
4. Check GitHub issues: [Your Repository URL]
5. Contact support: [Your Support Email]

---

**Last Updated:** 2025-11-13
**Version:** 1.0
**Author:** AI Ops Platform Team
