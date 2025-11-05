# Plugin Administration Guide

**Version:** 1.0
**Last Updated:** 2025-11-05
**Epic:** 7.8 - Create Plugin Management UI

---

## Overview

This guide explains how to manage ticketing tool plugins through the Streamlit admin UI. Plugin management enables system administrators to:

- View all installed plugins and their status
- Configure plugin credentials and connection settings
- Test plugin connectivity before deployment
- Assign plugins to tenants for ticket enhancement processing

**Who should use this guide:**
- System administrators responsible for platform configuration
- DevOps engineers onboarding new tenants
- Support teams troubleshooting integration issues

**When to use this guide:**
- Setting up the platform for the first time
- Onboarding new tenants with different ticketing tools
- Switching a tenant from one tool to another (e.g., ServiceDesk Plus → Jira)
- Troubleshooting connection failures

**Prerequisites:**
- Access to Streamlit admin UI (http://localhost:8501 or production URL)
- Plugin credentials (API keys, tokens, URLs) from ticketing tool provider
- Network connectivity to ticketing tool APIs

---

## Viewing Installed Plugins

### Access the Plugin Management Page

1. Navigate to the Streamlit admin UI in your web browser
2. Click **"Plugin Management"** in the sidebar navigation (Page 3)
3. The page displays all registered plugins in a table

### Understanding Plugin Information

The plugin table shows the following columns:

| Column | Description | Example |
|--------|-------------|---------|
| **Plugin Name** | Human-readable plugin name | "ServiceDesk Plus", "Jira Service Management" |
| **Plugin Type** | Unique identifier used in database | `servicedesk_plus`, `jira`, `zendesk` |
| **Version** | Plugin version number | "1.0.0" |
| **Status** | Operational status | "active", "inactive", "error" |
| **Description** | Brief plugin summary | "ManageEngine ServiceDesk Plus plugin" |

### Filter and Search Plugins

**Search by name:**
1. Use the search box above the table
2. Type plugin name (e.g., "Jira")
3. Results filter automatically

**Filter by status:**
1. Use the status dropdown filter
2. Select "active", "inactive", or "all"
3. Table updates to show matching plugins

### View Plugin Configuration Schema

Each plugin has an expandable section showing its configuration requirements:

1. Click the **▶** arrow next to a plugin row
2. The expander reveals configuration fields:
   - Field names (e.g., `jira_url`, `api_token`)
   - Field types (string, boolean, number)
   - Validation rules (required, min/max length, regex patterns)
   - Field descriptions

**Example - Jira Plugin Schema:**
```yaml
jira_url:
  type: string
  required: true
  pattern: ^https?://.*\.atlassian\.net.*
  description: Jira instance URL

jira_api_token:
  type: string
  required: true
  min_length: 20
  description: Jira API token (encrypted)

jira_project_key:
  type: string
  required: true
  pattern: ^[A-Z]+$
  description: Jira project key (e.g., SUPPORT)
```

---

## Configuring a Plugin

### When to Configure

Plugin configuration is typically **not** done through the admin UI directly. Instead, plugins are configured **per tenant** during tenant creation or updates. This section explains the configuration process for context.

### Configuration Fields by Plugin

**ServiceDesk Plus:**
- `servicedesk_url` - ServiceDesk Plus instance URL (e.g., https://acme.servicedesk.com)
- `api_key` - ServiceDesk Plus API key (obtained from Admin → API settings)
- `technician_key` - Technician key for API authentication

**Jira Service Management:**
- `jira_url` - Jira instance URL (e.g., https://acme.atlassian.net)
- `jira_api_token` - Jira API token (generated from Account Settings → Security → API tokens)
- `jira_project_key` - Jira project key (e.g., SUPPORT, HELP)

**Zendesk (Future):**
- `zendesk_url` - Zendesk instance URL
- `zendesk_api_token` - Zendesk API token
- `zendesk_email` - Zendesk admin email

### Obtain Plugin Credentials

**ServiceDesk Plus:**
1. Log in to ServiceDesk Plus as administrator
2. Navigate to Admin → Developer Space → API
3. Generate new API key and technician key
4. Copy keys (they won't be shown again)

**Jira:**
1. Log in to Jira Cloud
2. Navigate to Account Settings (top-right profile icon)
3. Select Security → API tokens
4. Click "Create API token"
5. Name the token (e.g., "AI Agents Integration")
6. Copy the token immediately (shown only once)

---

## Testing Plugin Connections

### Test Connection Before Saving

The admin UI provides a **"Test Connection"** button to validate plugin credentials before creating or updating a tenant. This prevents configuration errors.

**Where to test:**
- Tenant creation dialog (Add New Tenant)
- Tenant edit dialog (Update Tenant)
- Plugin Management page (if implemented in future versions)

### Test Connection Workflow

**From Tenant Creation/Edit:**
1. Fill in tenant details:
   - Tenant Name
   - Tenant ID
   - Select Plugin from dropdown
   - Enter ServiceDesk URL (or Jira URL)
   - Enter API Key (or API Token)
2. Click **"🔍 Test Connection"** button
3. Wait for test to complete (max 30 seconds)
4. Review test result:
   - ✅ **Success:** "Connection successful" - Plugin API is reachable and credentials are valid
   - ❌ **Failure:** Error message with specific issue (see Troubleshooting section)

### What the Test Validates

The connection test performs a lightweight API call to verify:

- **Network connectivity:** Can the platform reach the ticketing tool API?
- **Authentication:** Are the provided credentials valid?
- **API availability:** Is the API endpoint responding correctly?

**ServiceDesk Plus test:**
- Calls `GET /api/v3/user` to verify API key validity
- Returns user information if successful

**Jira test:**
- Calls `GET /rest/api/3/myself` to verify API token validity
- Returns authenticated user details if successful

### Test Results Interpretation

| Result | Status Code | Meaning | Action |
|--------|-------------|---------|--------|
| ✅ "Connection successful" | 200 | Credentials are valid | Proceed with tenant creation |
| ❌ "Authentication failed: Invalid API key" | 401 | API key/token is incorrect | Regenerate credentials and retry |
| ❌ "URL not reachable" | Timeout | Network issue or wrong URL | Verify URL and network connectivity |
| ❌ "Connection test timed out" | 408 | API response took >30 seconds | Check API performance or firewall rules |
| ❌ "SSL certificate error" | SSL Error | Certificate validation failed | Verify HTTPS certificate is valid |

---

## Assigning Plugins to Tenants

### Create New Tenant with Plugin

1. Navigate to **"Tenant Management"** page (Page 2)
2. Click **"➕ Add New Tenant"** button
3. Fill in tenant details:
   - **Tenant Name:** Human-readable name (e.g., "Acme Corporation")
   - **Tenant ID:** Unique identifier slug (e.g., "acme-corp")
   - **Tool Type:** Select plugin from dropdown
     - Available options: ServiceDesk Plus, Jira Service Management, etc.
     - List is dynamically populated from registered plugins
   - **ServiceDesk URL:** API endpoint URL for the selected tool
   - **API Key:** Authentication credentials (encrypted before storage)
4. Select enhancement features (optional):
   - Ticket History Search
   - Documentation Search
   - IP Lookup
   - Monitoring Data
5. Click **"🔍 Test Connection"** to validate credentials
6. If test succeeds, click **"✅ Create Tenant"**
7. Copy the generated webhook URL and configure it in your ticketing tool

**Result:**
- Tenant created with assigned plugin
- Plugin type stored in `tenant_configs.tool_type` column
- Audit log entry created: `tenant_plugin_assignment` (action: "create")

### Update Existing Tenant Plugin Assignment

**To reassign a tenant to a different plugin:**

1. Navigate to **"Tenant Management"** page
2. Locate the tenant in the table
3. Note the current **"Assigned Plugin"** column value
4. Click the tenant row to open details
5. Click **"Edit Tenant"** button (if available)
6. Select new plugin from **"Tool Type"** dropdown
7. Update connection settings for new plugin:
   - URL field name may change (e.g., `servicedesk_url` → `jira_url`)
   - API credentials will be different
8. Click **"🔍 Test Connection"** to verify new plugin credentials
9. Click **"💾 Save Changes"**
10. Confirmation dialog appears: "Changing plugin will affect ticket processing. Continue?"
11. Click **"Yes, reassign plugin"**

**Result:**
- Tenant plugin updated to new tool type
- Old credentials cleared, new credentials encrypted
- Audit log entry created: `tenant_plugin_assignment` (action: "reassign", old_plugin, new_plugin)
- Webhook URL remains the same (tenant_id unchanged)

### Verify Plugin Assignment

After assignment, verify the plugin is active:

1. View tenant details in Tenant Management page
2. Confirm **"Assigned Plugin"** column shows correct plugin name
3. Check recent operations in System Operations page
4. Review audit log for `tenant_plugin_assignment` entry

---

## Troubleshooting

### Plugin Not Appearing in List

**Symptom:** Expected plugin (e.g., Zendesk) doesn't appear in plugin dropdown.

**Possible Causes:**
1. Plugin not registered in PluginManager
2. Plugin implementation incomplete
3. Plugin disabled in configuration

**Resolution:**
1. Check registered plugins via API:
   ```bash
   curl http://localhost:8000/api/v1/plugins/
   ```
2. Verify plugin is imported in `src/main.py` and `src/workers/celery_app.py`
3. Confirm plugin class is registered:
   ```python
   # In src/plugins/zendesk/__init__.py
   from src.plugins.registry import PluginManager
   from .plugin import ZendeskPlugin

   manager = PluginManager()
   manager.register_plugin("zendesk", ZendeskPlugin)
   ```
4. Restart API server: `docker-compose restart api`
5. Refresh admin UI page

### Connection Test Failing

**Symptom:** "Test Connection" button returns error message.

**Common Errors and Solutions:**

**1. "Authentication failed: Invalid API key" (401)**
- **Cause:** API key/token is incorrect, expired, or lacks permissions
- **Solution:**
  - Regenerate API key in ticketing tool admin panel
  - Verify key was copied completely (no extra spaces)
  - Check API key has required permissions (read/write tickets)

**2. "URL not reachable" (Timeout)**
- **Cause:** Network connectivity issue or incorrect URL
- **Solution:**
  - Verify URL is correct: https://company.servicedesk.com (not http://)
  - Check DNS resolution: `nslookup company.servicedesk.com`
  - Test from container: `docker exec -it ai-agents-api curl https://company.servicedesk.com`
  - Verify firewall allows outbound HTTPS (port 443)

**3. "Connection test timed out (30 second limit exceeded)" (408)**
- **Cause:** API response too slow or hung
- **Solution:**
  - Check ticketing tool API status page for outages
  - Retry during off-peak hours
  - Contact ticketing tool support if persistent

**4. "SSL certificate error"**
- **Cause:** Self-signed certificate or expired SSL
- **Solution:**
  - Verify SSL certificate is valid: `openssl s_client -connect company.servicedesk.com:443`
  - Update to valid certificate or use HTTPS endpoint
  - Contact IT team if corporate proxy interfering

**5. "Plugin 'zendesk' does not implement test_connection() method" (501)**
- **Cause:** Plugin implementation incomplete
- **Solution:**
  - Wait for plugin developer to implement test_connection()
  - Proceed without connection test (not recommended)
  - Use plugin API documentation to manually verify credentials

### Tenant-Plugin Assignment Errors

**Symptom:** Tenant creation fails after successful connection test.

**Possible Causes:**
1. Database connection lost between test and save
2. Duplicate tenant_id in database
3. Encryption key not configured

**Resolution:**
1. Check database connectivity: `docker ps` (verify postgres container running)
2. Verify tenant_id is unique (check Tenant Management table)
3. Ensure `FERNET_KEY` environment variable set in `.env`
4. Review API logs: `docker logs ai-agents-api --tail 50`
5. Retry tenant creation with different tenant_id

### Plugin Assignment Not Persisting

**Symptom:** Plugin assignment resets to default (ServiceDesk Plus) after page refresh.

**Possible Causes:**
1. Database update not committed
2. Cache not cleared after update
3. Migration missing for `tool_type` column

**Resolution:**
1. Clear Streamlit cache: Click "Clear cache" button or refresh page (Ctrl+Shift+R)
2. Verify database schema has `tool_type` column:
   ```sql
   \d tenant_configs  -- In PostgreSQL
   ```
3. Run migrations if column missing:
   ```bash
   docker exec -it ai-agents-api alembic upgrade head
   ```
4. Check audit log for successful `tenant_plugin_assignment` entry

### Audit Logs Not Appearing

**Symptom:** Plugin operations not logged in audit_log table.

**Possible Causes:**
1. Audit logging function failing silently
2. Database table missing
3. Permissions issue

**Resolution:**
1. Verify `audit_log` table exists:
   ```sql
   SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 5;
   ```
2. Check API logs for audit logging errors: `docker logs ai-agents-api | grep "Failed to create audit log"`
3. Ensure database user has INSERT permission on audit_log table
4. Run migration if table missing:
   ```bash
   docker exec -it ai-agents-api alembic upgrade head
   ```

---

## Additional Resources

- [Plugin Architecture Overview](./plugin-architecture-overview.md) - Understand plugin system design
- [Plugin Development Guide](./plugin-development-guide.md) - Create custom plugins
- [Plugin Testing Guide](./plugin-testing-guide.md) - Test plugin implementations
- [Tenant Management Guide](../admin-ui-guide.md#tenant-management) - Complete tenant CRUD operations
- [Database Schema Documentation](../database-schema.md#tenant_configs) - tenant_configs table structure

---

## Support

For issues not covered in this guide:
1. Check [Plugin Troubleshooting Guide](./plugin-troubleshooting.md) for plugin-specific errors
2. Review API logs: `docker logs ai-agents-api --tail 100`
3. Consult audit logs for operation history
4. Contact platform support team with:
   - Error message (screenshot or text)
   - Plugin type and version
   - Tenant ID (if applicable)
   - Timestamp of issue
   - Steps to reproduce
