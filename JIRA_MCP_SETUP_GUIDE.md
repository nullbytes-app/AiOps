# 🔌 Jira MCP Server Setup Guide

Complete walkthrough for registering and using the Jira MCP server in your AI Agents platform.

---

## 📋 Prerequisites

Before starting, you need:
- ✅ Jira Cloud account (https://your-company.atlassian.net)
- ✅ Admin access to your AI Agents platform
- ✅ Docker and docker-compose installed

---

## Step 1: Get Your Jira API Token

### 1.1 Generate API Token

1. Go to **https://id.atlassian.com**
2. Log in with your Atlassian account
3. Click **Security** in the left sidebar
4. Click **Create and manage API tokens**
5. Click **Create API token**
6. Give it a label: `AI Agents MCP Server`
7. Click **Create**
8. **Copy the token immediately** (you won't see it again!)

### 1.2 Get Your Jira Base URL

Your Jira base URL format: `https://your-company.atlassian.net`

**Example:**
- If you access Jira at: `https://acme-corp.atlassian.net/jira/software/projects/PROJ`
- Your base URL is: `https://acme-corp.atlassian.net`

---

## Step 2: Configure `.env` File

Edit your `.env` file and update these values:

```bash
# Open .env in your editor
vim .env
# or
nano .env
# or
code .env
```

Find the Jira section and replace with **your actual credentials**:

```bash
# Jira MCP Server Configuration
JIRA_BASE_URL=https://acme-corp.atlassian.net  # ← YOUR Jira URL
JIRA_EMAIL=john.smith@acme-corp.com            # ← YOUR email
JIRA_API_TOKEN=ATATT3xFfGF0T...                # ← YOUR API token
JIRA_MCP_LOG_LEVEL=INFO
```

**Save the file** after editing.

---

## Step 3: Start the Jira MCP Server

Run this command from your project directory:

```bash
docker-compose up -d jira-mcp
```

### Verify it's running:

```bash
# Check logs
docker logs jira-mcp-server

# Check health
curl http://localhost:3001/health

# Expected output: {"status": "ok"}
```

If you see errors about missing credentials, double-check your `.env` file.

---

## Step 4: Register MCP Server in Admin UI

### 4.1 Access Admin UI

Open your browser and go to:
```
http://localhost:8501
```

### 4.2 Navigate to MCP Servers Page

1. In the left sidebar, scroll down to **🔌 MCP Servers**
2. Click on it

You'll see the MCP Servers management page.

### 4.3 Add New Server

Click the **➕ Add Server** button (top right)

### 4.4 Fill in the Form

**Server Configuration:**

| Field | Value | Notes |
|-------|-------|-------|
| **Server Name** | `Jira Cloud MCP` | Friendly name |
| **Description** | `Jira Service Management integration` | Optional |
| **Transport Type** | ● **HTTP+SSE** | Select radio button |
| **Base URL** | `http://jira-mcp-server:3001` | Docker service name |

**Important:**
- ✅ Use `http://jira-mcp-server:3001` (docker service name)
- ❌ Don't use `http://localhost:3001` (won't work from container)

### 4.5 Test Connection

Click the **🔍 Test Connection** button

You should see:
```
✅ Connection successful!
Tools discovered: 20+
```

**If you see an error:**
- Check docker logs: `docker logs jira-mcp-server`
- Verify `.env` has correct Jira credentials
- Restart service: `docker-compose restart jira-mcp`

### 4.6 Save Server

Click **💾 Save Server**

The system will:
1. Save configuration to database
2. Discover all available Jira tools
3. Mark status as "active" ✅

---

## Step 5: Verify Tools Were Discovered

On the MCP Servers list page, you should see:

```
┌──────────────────────────────────────────────────────┐
│ Jira Cloud MCP                          [Active ✅]  │
│ http://jira-mcp-server:3001                          │
│ Tools: 20+ | Resources: 0 | Prompts: 0               │
│ [View Details] [Edit] [Test] [Delete]                │
└──────────────────────────────────────────────────────┘
```

### View Tool Details

Click **[View Details]** to see all discovered tools:

**Key tools you'll use:**
- ✅ `jira_add_comment` - Post comments to issues
- ✅ `jira_get_issue` - Retrieve issue details
- ✅ `jira_search_issues` - Search using JQL
- ✅ `jira_create_issue` - Create new issues
- ✅ `jira_update_issue` - Update issue fields
- ✅ `jira_transition_issue` - Change issue status
- And 14+ more tools for boards, projects, time tracking, etc.

---

## Step 6: Assign Tools to Your Agent

### 6.1 Navigate to Agent Management

1. Click **👥 Agent Management** in the left sidebar
2. Find your **Ticket Enhancer** agent
3. Click **[Edit]**

### 6.2 Assign Jira Tools

Scroll to **Assigned Tools** section

**For Ticket Enhancement, assign these tools:**
- ✅ `jira_add_comment` (REQUIRED - to post enhancement back to Jira)
- ✅ `jira_get_issue` (OPTIONAL - to fetch additional issue details)
- ✅ `jira_search_issues` (OPTIONAL - to find similar tickets)

Click **Add Tool** → Select tools → **Save**

---

## Step 7: Update Agent System Prompt

Update your Ticket Enhancer agent's system prompt to use the Jira tools:

```markdown
You are an AI Ticket Enhancement Agent for technical support.

When you receive a Jira ticket via webhook:

1. **Analyze the ticket thoroughly:**
   - Identify the core issue and severity
   - Determine potential root causes
   - Suggest actionable remediation steps
   - Search for similar resolved tickets if relevant (using jira_search_issues)

2. **Format your analysis clearly:**
   - Use markdown for readability
   - Include sections: Summary, Root Cause, Recommendations, Similar Issues
   - Be concise but comprehensive

3. **Post your analysis back to Jira:**
   - Use the `jira_add_comment` tool to post your findings
   - The comment should appear on the original issue (issue_key provided in payload)
   - Format: Professional, actionable, and helpful for human agents

**Important:** Always post your analysis as a comment so the support team can see your recommendations immediately.

**Input Format:**
You'll receive webhook payloads containing:
- issue_key: Jira issue ID (e.g., "SUPPORT-12345")
- tenant_id: Tenant identifier
- issue: Full issue details (summary, description, priority, etc.)

**Your workflow:**
1. Extract issue_key from payload
2. Analyze the issue details
3. Call jira_add_comment(issue_key, your_formatted_analysis)
```

---

## Step 8: Test End-to-End

### 8.1 Trigger Webhook

Use your test script:

```bash
python test_ticket_enhancer_webhook.py
```

### 8.2 Monitor Execution

1. **Check Celery Logs:**
   ```bash
   docker logs -f ai-agents-worker
   ```

2. **Look for:**
   - ✅ "Agent execution started"
   - ✅ "Tool call: jira_add_comment"
   - ✅ "Successfully posted comment to Jira"

### 8.3 Verify in Jira

1. Open the test ticket in Jira (e.g., SUPPORT-12345)
2. Scroll to **Activity** / **Comments** section
3. You should see a comment from your Jira bot account with the AI analysis!

---

## 🎯 Success Checklist

- [ ] Jira API token generated
- [ ] `.env` file configured with credentials
- [ ] `docker-compose up -d jira-mcp` started successfully
- [ ] `curl http://localhost:3001/health` returns `{"status": "ok"}`
- [ ] MCP server registered in Admin UI (http://localhost:8501)
- [ ] Connection test passed ✅
- [ ] 20+ tools discovered
- [ ] Tools assigned to Ticket Enhancer agent
- [ ] System prompt updated
- [ ] End-to-end test successful
- [ ] Comment appears in Jira ticket

---

## 🐛 Troubleshooting

### Issue: "Connection failed" when testing

**Solution:**
```bash
# Check MCP server logs
docker logs jira-mcp-server

# Common errors:
# - "Invalid API token" → Regenerate token at id.atlassian.com
# - "Authentication failed" → Check JIRA_EMAIL matches token owner
# - "Connection refused" → Make sure service is running
```

### Issue: Tools not discovered

**Solution:**
```bash
# Restart MCP server
docker-compose restart jira-mcp

# Wait 10 seconds, then click "Refresh" in Admin UI
```

### Issue: Agent doesn't call jira_add_comment

**Solution:**
1. Check tool is assigned to agent (Agent Management page)
2. Verify system prompt instructs agent to use the tool
3. Check agent execution logs for errors

### Issue: "403 Forbidden" from Jira API

**Solution:**
- Verify API token user has permission to comment on issues
- Check Jira project permissions

---

## 📚 Additional Resources

- **Jira REST API Docs:** https://developer.atlassian.com/cloud/jira/platform/rest/v3/
- **MCP Specification:** https://modelcontextprotocol.io/specification
- **Jira MCP Server (OrenGrinker):** https://github.com/OrenGrinker/jira-mcp-server

---

## 🔐 Security Notes

- ✅ API tokens are encrypted in database
- ✅ Credentials never logged
- ✅ MCP server isolated in Docker network
- ⚠️ **Never commit `.env` file** to git
- ⚠️ **Rotate API tokens regularly** (every 90 days recommended)

---

## 🚀 Next Steps

Once Jira integration is working:

1. **Add more MCP servers:**
   - Slack MCP (notifications)
   - GitHub MCP (code issues)
   - Salesforce MCP (customer context)

2. **Enhance prompts:**
   - Add domain-specific knowledge
   - Fine-tune analysis format
   - Add SLA tracking

3. **Scale:**
   - Move to Kubernetes for auto-scaling
   - Add monitoring/alerting
   - Implement multi-tenant isolation

---

**Questions? Issues?**
- Check logs: `docker logs jira-mcp-server`
- Test locally: `curl http://localhost:3001/health`
- Verify credentials in `.env`
