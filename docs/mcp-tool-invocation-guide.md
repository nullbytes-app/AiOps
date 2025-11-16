# MCP Tool Invocation Guide

## Overview

Story 11.1.7 implements MCP (Model Context Protocol) tool invocation in agent execution, enabling agents to call tools from MCP servers alongside OpenAPI tools. This guide covers setup, usage, and troubleshooting.

## Features

- **Unified Tool Discovery**: Agents can use both OpenAPI tools and MCP tools (tools, resources, prompts)
- **LangGraph Integration**: MCP tools are converted to LangChain-compatible tools for ReAct agent workflow
- **Multi-Server Support**: Agents can access tools from multiple MCP servers simultaneously
- **Graceful Error Handling**: Timeouts and errors in MCP tool invocation don't crash agent execution
- **Budget Enforcement**: Tenant budget limits apply to agent executions using MCP tools

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Agent Execution Flow                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  AgentExecutionService                                           │
│  - Load agent configuration                                      │
│  - Check budget                                                   │
│  - Get MCP server assignments                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┴───────────────────┐
          ▼                                       ▼
┌──────────────────────┐              ┌──────────────────────┐
│  OpenAPI Tools       │              │  MCP Tool Bridge     │
│  (Existing)          │              │  (Story 11.1.7)      │
└──────────────────────┘              └──────────────────────┘
                                                 │
                    ┌────────────────────────────┴────────────────┐
                    ▼                            ▼                 ▼
          ┌──────────────────┐       ┌──────────────────┐  ┌──────────────┐
          │  MCP Server 1    │       │  MCP Server 2    │  │  MCP Server N│
          │  (stdio)         │       │  (stdio)         │  │  (stdio)     │
          └──────────────────┘       └──────────────────┘  └──────────────┘
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
    ┌─────────┐         ┌──────────┐
    │  Tools  │         │ Resources│
    └─────────┘         └──────────┘
          ▼                   ▼
    ┌─────────┐         ┌──────────┐
    │ Prompts │         │   ...    │
    └─────────┘         └──────────┘
```

## Adding MCP Servers via Admin UI

### Accessing the MCP Servers Page

1. Navigate to the Admin UI in your browser (typically `http://localhost:8501`)
2. Select **🔌 MCP Servers** from the sidebar navigation
3. You'll see the MCP Servers management page with:
   - List of configured servers (if any)
   - **➕ Add MCP Server** button to add new servers
   - Status indicators, tool counts, and action buttons for each server

### Adding a New MCP Server (stdio)

**Example 1: Filesystem Server**

1. Click **➕ Add MCP Server**
2. Fill in the form:
   - **Server Name**: `Filesystem Server`
   - **Description**: `Provides file system access for agents`
   - **Transport Type**: Select `stdio`
   - **Command**: `npx`
   - **Arguments** (one per line):
     ```
     -y
     @modelcontextprotocol/server-filesystem
     /path/to/data
     ```
   - **Environment Variables**: (optional, leave empty for this example)
3. Click **Save**
4. The server will be created and automatic discovery will run
5. You'll see a success message: `MCP server 'Filesystem Server' created successfully`
6. The server details page will open showing discovered capabilities

**Example 2: GitHub Server**

1. Click **➕ Add MCP Server**
2. Fill in the form:
   - **Server Name**: `GitHub Integration`
   - **Description**: `GitHub API access for repository management`
   - **Transport Type**: Select `stdio`
   - **Command**: `npx`
   - **Arguments** (one per line):
     ```
     -y
     @modelcontextprotocol/server-github
     ```
   - **Environment Variables**: Click **➕ Add Environment Variable**
     - **Key**: `GITHUB_TOKEN`
     - **Value**: `ghp_xxxxxxxxxxxxx` (your GitHub Personal Access Token)
3. Click **Save**
4. Discovered tools will include: `create_issue`, `list_repos`, `get_file_contents`, etc.

**Example 3: Database Server (PostgreSQL)**

1. Click **➕ Add MCP Server**
2. Fill in the form:
   - **Server Name**: `Database Access`
   - **Description**: `PostgreSQL database query access`
   - **Transport Type**: Select `stdio`
   - **Command**: `npx`
   - **Arguments** (one per line):
     ```
     -y
     @modelcontextprotocol/server-postgres
     ```
   - **Environment Variables**: Click **➕ Add Environment Variable**
     - **Key**: `DATABASE_URL`
     - **Value**: `postgresql://user:password@localhost/dbname`
3. Click **Save**
4. Discovered tools will include: `query`, `list_tables`, `describe_table`, etc.

### Adding a New MCP Server (HTTP+SSE)

**Story 11.2.1** adds support for MCP Streamable HTTP transport, enabling agents to connect to remote MCP servers via HTTP with Server-Sent Events (SSE) streaming.

**Example 1: Remote MCP HTTP Server**

1. Click **➕ Add MCP Server**
2. Fill in the form:
   - **Server Name**: `Remote Analytics Server`
   - **Description**: `Cloud-based analytics and reporting tools`
   - **Transport Type**: Select `http_sse`
   - **Server URL**: `https://mcp.example.com/v1`
   - **Headers** (click **➕ Add Header** for each):
     - **Key**: `Authorization`
     - **Value**: `Bearer sk_live_xxxxxxxxxxxxx`
     - **Key**: `X-API-Key`
     - **Value**: `api_xxxxxxxxxxxxx`
3. Click **Save**
4. The server will be created and automatic discovery will run via HTTP
5. Success message: `MCP server 'Remote Analytics Server' created successfully`

**Example 2: Cloud-Based Document Processing**

1. Click **➕ Add MCP Server**
2. Fill in the form:
   - **Server Name**: `Document AI`
   - **Description**: `Cloud document processing and OCR`
   - **Transport Type**: Select `http_sse`
   - **Server URL**: `https://api.docai.example.com/mcp`
   - **Headers**:
     - **Key**: `Authorization`
     - **Value**: `Bearer YOUR_API_TOKEN`
     - **Key**: `X-Tenant-ID`
     - **Value**: `tenant_abc123`
3. Click **Save**
4. Discovered tools might include: `extract_text`, `classify_document`, `generate_summary`, etc.

**HTTP+SSE Transport Features:**

- **Remote Server Support**: Connect to MCP servers hosted anywhere via HTTPS
- **SSE Streaming**: Supports Server-Sent Events for long-running operations with incremental results
- **Event Resumability**: Automatically resumes from last event ID if connection drops (3 retries with exponential backoff)
- **Custom Headers**: Pass authentication tokens, API keys, and custom headers
- **Connection Pooling**: HTTP/2 support with connection pooling (max 100 connections, 20 keep-alive)
- **Granular Timeouts**: Connect (10s), read (60s), write (10s), pool (5s) timeouts
- **Auto-Retry**: Automatic reconnection on network errors with configurable retry logic

**When to Use HTTP+SSE vs stdio:**

- **Use http_sse** when:
  - MCP server is hosted remotely (cloud service, another datacenter)
  - Need to share MCP server across multiple instances/deployments
  - MCP server requires authentication via HTTP headers
  - Server supports SSE streaming for long operations
  - Want to scale MCP server independently from AI Ops platform

- **Use stdio** when:
  - MCP server runs locally on the same machine
  - Using npm-based MCP packages (@modelcontextprotocol/server-*)
  - Need direct process control and file system access
  - Testing/development with local MCP servers

### Viewing Server Details

1. In the server list, click **📋** (View Details) button next to any server
2. The details view shows:
   - **Server Information**: Name, transport type, status, health check timestamps
   - **Configuration**: Command, arguments, environment variable keys (values masked)
   - **Discovered Capabilities** (tabs):
     - **🔧 Tools**: List of discovered tools with names, descriptions, and input schemas
     - **📁 Resources**: List of discovered resources with URIs
     - **💬 Prompts**: List of discovered prompts with names and descriptions
   - **Raw JSON**: Expandable section with complete server data

### Editing an Existing Server

1. Click **✏️** (Edit) button next to a server OR click Edit from the details view
2. The edit form pre-populates with existing values
3. You can modify:
   - Server name (must be unique)
   - Description
   - Command, arguments, environment variables (for stdio servers)
   - **Note**: Transport type cannot be changed after creation (read-only)
4. Click **Save Changes** to update
5. Success message: `MCP server updated successfully`

### Deleting an MCP Server

1. Click **🗑️** (Delete) button next to a server
2. A confirmation warning appears:
   > ⚠️ **Confirm deletion of 'Server Name'?** This will remove the server configuration and all discovered capabilities. Agents using tools from this server will no longer function.
3. Click **Delete** button again to confirm (or click another button to cancel)
4. Success message: `MCP server 'Server Name' deleted`
5. Server is removed from the list

### Rediscovering Server Capabilities

If you've updated an MCP server externally (e.g., added new tools), you can refresh the discovered capabilities:

1. Click **🔄** (Rediscover) button next to a server OR click Rediscover from the details view
2. A spinner appears: "Rediscovering capabilities..."
3. The system calls the MCP server to re-discover tools, resources, and prompts
4. Success message: `Capabilities rediscovered. Found X tools, Y resources, Z prompts`
5. The server details automatically refresh with updated capabilities

### Understanding Status Indicators

Servers display colored status badges:

- **🟢 Active**: Server is healthy and responding to health checks
- **🔴 Error**: Server has encountered an error (check error message in details)
- **⚪ Inactive**: Server has failed 3 consecutive health checks (circuit breaker activated)

Health checks run automatically every 30 seconds (configured in Story 11.1.8).

### Troubleshooting

**Problem: Server status shows 🔴 Error**

**Solution:**
1. Click on the server to view details
2. Check the **Error Message** field for specific error details
3. Common issues:
   - Command not found: Verify the command is installed (e.g., `npx` requires Node.js)
   - Permission denied: Check file/directory permissions
   - Invalid arguments: Verify argument syntax matches MCP server requirements
4. Click **Edit** to correct the configuration
5. Click **Rediscover** to test the fix

**Problem: Connection test fails with "Command not found"**

**Solution:**
1. Verify the command exists on the server:
   ```bash
   which npx  # Should return path to npx executable
   ```
2. If missing, install Node.js: `brew install node` (macOS) or `apt-get install nodejs npm` (Linux)
3. Try the command manually: `npx -y @modelcontextprotocol/server-filesystem /tmp`
4. Return to the admin UI and retry

**Problem: No tools discovered after server creation**

**Solution:**
1. Check the **Status** indicator - if 🔴 Error, see error message
2. Verify the MCP server package is compatible: `npx -y @modelcontextprotocol/server-<name> --help`
3. Check environment variables are set correctly (especially for servers requiring API keys)
4. Click **Rediscover** to retry discovery
5. If persistent, check application logs: `docker-compose logs api`

**Problem: Agent execution fails with "Tool not found"**

**Solution:**
1. Navigate to **Agent Management** page
2. Edit the agent configuration
3. Verify the MCP server is assigned to the agent (in tool assignment section)
4. Verify the specific tool exists in the server's discovered tools (MCP Servers → Details → Tools tab)
5. If tool was recently added, click **Rediscover** on the MCP server
6. Save the agent configuration

### Troubleshooting HTTP+SSE Transport

**Problem: HTTP server shows 🔴 Error with "Connection timeout"**

**Solution:**
1. Check if the server URL is accessible:
   ```bash
   curl -i https://mcp.example.com/v1
   ```
2. Verify firewall rules allow outbound HTTPS traffic
3. Check if the server requires specific headers (Authorization, API key)
4. Increase timeout if server is slow to respond (edit server, adjust timeout settings)
5. Check application logs: `docker-compose logs api | grep "MCP HTTP"`

**Problem: HTTP server shows "HTTP 401: Unauthorized"**

**Solution:**
1. Click **Edit** on the MCP server
2. Verify authentication headers are correct:
   - `Authorization: Bearer <token>` format for Bearer tokens
   - `X-API-Key: <key>` for API key authentication
3. Check if the token/key has expired (regenerate if needed)
4. Verify tenant ID or other required headers are included
5. Test authentication manually:
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" https://mcp.example.com/v1
   ```

**Problem: Discovery works but tool calls fail with timeout**

**Solution:**
1. The read timeout (60s) may be insufficient for long-running tools
2. Check if the tool supports SSE streaming (incremental results)
3. Review tool execution logs in server details
4. Consider breaking complex operations into multiple tool calls
5. Contact MCP server provider to optimize slow operations

**Problem: "Connection pool exhausted" error**

**Solution:**
1. This indicates too many concurrent requests to the same MCP server
2. Reduce number of agents using this server simultaneously
3. Check for agent loops (agent repeatedly calling same tool)
4. Consider deploying additional MCP server instances with load balancer
5. Pool limits are: 100 max connections, 20 keep-alive (configured in Story 11.2.1)

**Problem: SSE stream reconnection fails**

**Solution:**
1. Verify server supports `Last-Event-ID` header for resumption
2. Check server logs for event ID expiration (404/410 responses)
3. System auto-retries 3 times with exponential backoff (2s, 4s, 8s)
4. If consistent failures, server may not support event resumability
5. Fall back to single JSON responses (server should detect and use application/json)

## API Endpoints

### Execute Agent with MCP Tools

**Endpoint**: `POST /api/agent-execution/execute`

**Headers**:
- `X-Tenant-ID`: Tenant identifier (required)

**Request Body**:
```json
{
  "agent_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_message": "Analyze ticket #123 and suggest resolution steps",
  "context": {
    "ticket_id": 123,
    "priority": "high"
  },
  "timeout_seconds": 120
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "response": "Based on the ticket analysis...",
  "tool_calls": [
    {
      "tool_name": "read_file",
      "tool_input": {"path": "/logs/error.log"},
      "tool_output": "Error log contents...",
      "timestamp": "2025-01-09T12:34:56.789Z"
    }
  ],
  "execution_time_seconds": 2.45,
  "model_used": "openai/gpt-4o-mini",
  "error": null
}
```

**Error Responses**:
- `400 Bad Request`: Invalid request parameters
- `402 Payment Required`: Tenant budget exceeded
- `404 Not Found`: Agent not found or tenant mismatch
- `500 Internal Server Error`: Agent execution failed

### Health Check

**Endpoint**: `GET /api/agent-execution/health`

**Response** (200 OK):
```json
{
  "status": "healthy",
  "service": "agent-execution",
  "version": "1.0.0",
  "features": [
    "langgraph-react-agent",
    "mcp-tool-support",
    "budget-enforcement",
    "multi-tenant-isolation"
  ]
}
```

## Setup Guide

### 1. Create MCP Server Configuration

Use the MCP Server Management API (Story 11.1.4):

```bash
POST /api/mcp-servers
X-Tenant-ID: acme-corp

{
  "name": "filesystem",
  "description": "Access local filesystem",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"],
  "env": {},
  "status": "active"
}
```

### 2. Assign MCP Tools to Agent

Use the Agent Tool Assignment API (Story 11.1.6):

```bash
POST /api/agents/{agent_id}/assigned-mcp-tools
X-Tenant-ID: acme-corp

{
  "mcp_tool_assignments": [
    {
      "name": "read_file",
      "mcp_server_id": "550e8400-e29b-41d4-a716-446655440001",
      "mcp_primitive_type": "tool",
      "description": "Read file contents from filesystem"
    },
    {
      "name": "filesystem_resource",
      "mcp_server_id": "550e8400-e29b-41d4-a716-446655440001",
      "mcp_primitive_type": "resource",
      "description": "Access filesystem resource by URI"
    }
  ]
}
```

### 3. Execute Agent

```bash
POST /api/agent-execution/execute
X-Tenant-ID: acme-corp

{
  "agent_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_message": "Read the error log and summarize the issues",
  "timeout_seconds": 120
}
```

## MCP Tool Types

### Tools (primitive_type: "tool")

Native MCP tools exposed by the server. Automatically converted to LangChain tools using `langchain-mcp-adapters`.

**Example**:
```python
# Agent can call tool by name
"Use the read_file tool to read /logs/error.log"
```

### Resources (primitive_type: "resource")

MCP resources accessed via `session.read_resource(uri)`. Wrapped as LangChain tools.

**Example**:
```python
# Agent calls resource wrapper
"Use filesystem_resource to read resource://workspace/config.json"
```

### Prompts (primitive_type: "prompt")

MCP prompts accessed via `session.get_prompt(name, arguments)`. Wrapped as LangChain tools.

**Example**:
```python
# Agent calls prompt wrapper
"Use code_review_prompt to generate a code review checklist"
```

## Configuration

### Environment Variables

```bash
# LiteLLM Proxy (for LLM calls with budget enforcement)
LITELLM_PROXY_URL=http://litellm:4000

# OpenTelemetry (for distributed tracing)
JAEGER_ENDPOINT=http://jaeger:4317
```

### Agent LLM Configuration

Agents use `llm_config` JSON field for model configuration:

```json
{
  "provider": "openai",
  "model": "gpt-4o-mini",
  "temperature": 0.7,
  "max_tokens": 2000
}
```

## Error Handling

### Timeout Handling

- MCP tool calls timeout after 30 seconds
- Agent execution timeouts configurable (10-600 seconds, default 120)
- Timeouts return graceful error messages instead of crashing

**Example Error**:
```json
{
  "success": false,
  "response": "",
  "tool_calls": [],
  "execution_time_seconds": 30.5,
  "model_used": "openai/gpt-4o-mini",
  "error": "MCP tool read_file timeout (>30s)"
}
```

### Budget Exceeded

When tenant budget is exceeded, execution returns 402:

```json
{
  "detail": {
    "tenant_id": "acme-corp",
    "current_spend": 550.0,
    "max_budget": 500.0,
    "grace_threshold": 110.0
  }
}
```

### Agent Not Found

When agent doesn't exist or belongs to different tenant, returns 500 with error message:

```json
{
  "detail": "Agent 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

## Monitoring

### OpenTelemetry Tracing

Agent execution automatically creates distributed traces:

- Span: `agent_execution.execute`
  - Attributes: `agent_id`, `tenant_id`, `user_message_length`, `timeout_seconds`
  - Child spans for each tool call
  - Child spans for LLM calls (via LiteLLM)

### Prometheus Metrics

Metrics exposed at `/metrics`:

- `agent_execution_duration_seconds` - Histogram of execution times
- `agent_execution_tool_calls_total` - Counter of tool invocations
- `agent_execution_errors_total` - Counter of errors by type

### Logging

Structured logs with context:

```json
{
  "level": "info",
  "message": "Agent execution completed successfully",
  "agent_id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "acme-corp",
  "execution_time_seconds": 2.45,
  "tool_calls_count": 3
}
```

## Troubleshooting

### Issue: MCP server not spawning

**Symptoms**: Agent execution fails with "MCP client initialization failed"

**Solutions**:
1. Check MCP server command is valid: `npx -y @modelcontextprotocol/server-filesystem`
2. Verify server status is "active" in database
3. Check server logs for errors: `docker logs ai-agents`

### Issue: Tool not found

**Symptoms**: Agent says "Tool X not available"

**Solutions**:
1. Verify tool is assigned to agent: `GET /api/agents/{agent_id}/assigned-mcp-tools`
2. Check MCP server exposes the tool: Use MCP inspector
3. Verify `mcp_primitive_type` matches tool type ("tool", "resource", or "prompt")

### Issue: Timeout errors

**Symptoms**: "MCP tool X timeout (>30s)"

**Solutions**:
1. Increase agent execution timeout: `"timeout_seconds": 300`
2. Optimize MCP server performance
3. Check network latency to MCP server

### Issue: Budget exceeded

**Symptoms**: 402 response "Budget exceeded"

**Solutions**:
1. Increase tenant budget: `PUT /api/admin/tenants/{tenant_id}`
2. Check current spend: `GET /api/admin/tenants/{tenant_id}/budget`
3. Review agent LLM model selection (use cheaper models for high-volume tasks)

## Best Practices

### 1. Tool Selection

- **Use MCP tools** for file system, databases, external APIs
- **Use OpenAPI tools** for your own REST APIs
- **Combine both** in a single agent for maximum flexibility

### 2. Error Handling

- Set appropriate `timeout_seconds` based on tool complexity (min 10, max 600)
- Monitor tool call failures in logs
- Implement retry logic for transient failures (via agent prompt)

### 3. Security

- MCP servers run with agent's tenant isolation
- Validate all tool inputs (MCP servers should validate)
- Use least-privilege MCP server configurations (e.g., restrict filesystem access)

### 4. Performance

- Use faster models (gpt-4o-mini) for tool-heavy workflows
- Limit number of assigned tools (agents perform better with fewer choices)
- Monitor execution time and optimize slow MCP servers

## Examples

### Example 1: File Analysis Agent

```python
# Agent Configuration
{
  "name": "Log Analyzer",
  "system_prompt": "You analyze log files and identify errors",
  "llm_config": {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "temperature": 0.3
  },
  "assigned_mcp_tools": [
    {
      "name": "read_file",
      "mcp_server_id": "...",
      "mcp_primitive_type": "tool"
    }
  ]
}

# Execution
POST /api/agent-execution/execute
{
  "agent_id": "...",
  "user_message": "Read /var/log/app.log and summarize the top 3 errors"
}
```

### Example 2: Database Query Agent

```python
# Agent Configuration
{
  "name": "DB Query Assistant",
  "system_prompt": "You help users query the database safely",
  "llm_config": {
    "provider": "openai",
    "model": "gpt-4o-mini"
  },
  "assigned_mcp_tools": [
    {
      "name": "execute_query",
      "mcp_server_id": "...",
      "mcp_primitive_type": "tool"
    },
    {
      "name": "schema_resource",
      "mcp_server_id": "...",
      "mcp_primitive_type": "resource"
    }
  ]
}

# Execution
POST /api/agent-execution/execute
{
  "agent_id": "...",
  "user_message": "Show me the top 5 customers by revenue this month"
}
```

## Connection Pooling and Performance (Story 11.2.3)

### MCP Bridge Pooling

Story 11.2.3 implements **MCP bridge pooling** to optimize agent execution performance by reusing MCP client connections within the same execution context.

**Performance Benefits:**
- **10x faster execution**: Eliminates redundant MCP client initialization overhead
- **Reduced latency**: stdio subprocess spawning happens once per execution (not per tool call)
- **HTTP connection reuse**: HTTP+SSE clients reuse persistent connections
- **Lower resource usage**: Fewer open file descriptors and processes

**How It Works:**

1. **Execution Context Isolation**: Each agent execution gets a unique `execution_context_id` (UUID)
2. **Bridge Reuse**: When an agent makes multiple MCP tool calls, the same `MCPToolBridge` instance is reused
3. **Automatic Cleanup**: Bridge is cleaned up in `finally` block after execution completes

**Architecture:**

```
┌─────────────────────────────────────────────────────────────────┐
│  Agent Execution #1 (context_id: abc-123)                       │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  1st MCP tool call  → Creates MCPToolBridge            │     │
│  │  2nd MCP tool call  → Reuses SAME bridge ✅            │     │
│  │  3rd MCP tool call  → Reuses SAME bridge ✅            │     │
│  │  finally: cleanup() → Closes all MCP server connections│     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  Agent Execution #2 (context_id: def-456)                       │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  1st MCP tool call  → Creates NEW MCPToolBridge         │   │
│  │  2nd MCP tool call  → Reuses SAME bridge ✅            │   │
│  │  finally: cleanup() → Closes all MCP server connections│   │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

**Key Implementation Details:**

- **Module-level pool**: `_mcp_bridge_pool: Dict[str, MCPToolBridge]` stores bridges by execution context ID
- **Helper methods**:
  - `_get_or_create_mcp_bridge(execution_context_id, mcp_servers)` - Get cached or create new
  - `_cleanup_mcp_bridge(execution_context_id)` - Close and remove from pool
- **Location**: `src/services/agent_execution_service.py`

**Performance Comparison:**

| Scenario | Without Pooling (11.1.7) | With Pooling (11.2.3) | Improvement |
|----------|--------------------------|------------------------|-------------|
| Agent makes 10 MCP tool calls (stdio) | 1,000-5,000ms overhead | 100-500ms overhead | **10x faster** |
| Agent makes 10 MCP tool calls (HTTP) | 500-2,000ms overhead | 50-200ms overhead | **10x faster** |
| Multiple concurrent executions | Independent (no sharing) | Isolated by context | Same isolation ✅ |

**Error Handling:**

- If `bridge.cleanup()` fails, the bridge is still removed from the pool (best effort cleanup)
- Errors are logged but don't crash agent execution
- Pool is automatically cleared on exceptions via `finally` block

**Monitoring:**

While the simplified bridge pooling approach doesn't expose dedicated metrics, you can monitor:
- Agent execution time (should decrease with pooling enabled)
- MCP server health status (POST `/api/mcp-servers/{id}/health-check`)
- Agent execution logs for "Reusing MCP bridge from pool" debug messages

**Testing:**

Integration tests validate:
- Bridge reuse within same execution context
- Isolation across concurrent executions
- Proper cleanup on normal exit and errors
- Performance improvements (reduced MCPToolBridge creation count)

See `tests/integration/test_mcp_pool_agent_execution.py` for 10 comprehensive test cases.

## References

- [Story 11.1.7: MCP Tool Invocation in Agent Execution](../docs/stories/11-1-7-mcp-tool-invocation-in-agent-execution.md)
- [Story 11.2.3: MCP Connection Pooling and Caching](../docs/stories/11-2-3-mcp-connection-pooling-and-caching.md)
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [langchain-mcp-adapters](https://github.com/rectalogic/langchain-mcp-adapters)

## Testing MCP Integration (Story 11.2.6)

### Testing Philosophy

Story 11.2.6 implements comprehensive testing infrastructure for MCP features:
- **Unit Tests**: >90% coverage for all MCP modules
- **Integration Tests**: 42 end-to-end tests with real MCP servers
- **Test Server**: Official @modelcontextprotocol/server-everything for consistent testing

### Running Tests

**All MCP Tests:**
```bash
pytest tests/unit/test_mcp_*.py tests/integration/test_mcp_*.py -v
```

**Unit Tests Only (Fast, No Dependencies):**
```bash
pytest tests/unit/test_mcp_*.py -v
# Expected: 141+ tests passing in ~5 seconds
```

**Integration Tests (Requires npx):**
```bash
# Install Node.js if needed: brew install node
pytest tests/integration/test_mcp_*.py -v
# Expected: 42 tests passing in ~10 seconds
```

**Specific Test Categories:**
```bash
# stdio transport workflow (7 tests)
pytest tests/integration/test_mcp_stdio_workflow.py -v

# Error scenarios (10 tests)
pytest tests/integration/test_mcp_error_scenarios.py -v

# All three primitives (15 tests)
pytest tests/integration/test_mcp_primitives.py -v

# Performance tests (10 tests)
pytest tests/integration/test_mcp_performance.py -v
```

### Test Server Setup

Integration tests use `@modelcontextprotocol/server-everything`, which provides all three MCP primitives for testing.

**Installation:**
```bash
npm install  # Installs test server from package.json
```

**Available Test Tools:**
- `echo` - Echo back input text
- `add` - Add two numbers
- `longRunningOperation` - Simulate long-running task
- `sampleLLM` - Mock LLM call
- `getTinyImage` - Return test image

**Test Fixtures:**

The test suite provides reusable fixtures (see `tests/integration/conftest.py`):

```python
# Use in your tests
@pytest.mark.integration
@pytest.mark.asyncio
async def test_my_mcp_feature(mcp_stdio_client):
    """Test with initialized MCP client."""
    tools = await mcp_stdio_client.list_tools()
    assert len(tools) > 0
```

**Available Fixtures:**
- `mcp_stdio_test_server_config` - Config for stdio test server
- `mcp_stdio_client` - Initialized stdio client (auto-cleanup)
- `skip_if_no_mcp_server` - Skip test if npx not available
- `mock_db_session` - Mock database session

### Writing Integration Tests

**Example: Testing Tool Invocation**

```python
import pytest

@pytest.mark.integration
@pytest.mark.usefixtures("skip_if_no_mcp_server")
@pytest.mark.asyncio
async def test_my_tool_workflow(mcp_stdio_client):
    """
    Test custom MCP tool workflow.

    Validates:
    - Tool is available
    - Tool accepts arguments
    - Result matches expectations
    """
    # List available tools
    tools = await mcp_stdio_client.list_tools()
    tool_names = {tool["name"] for tool in tools}
    assert "echo" in tool_names

    # Call tool
    result = await mcp_stdio_client.call_tool(
        "echo",
        {"message": "test input"}
    )

    # Validate result
    assert result["is_error"] is False
    assert "test input" in str(result["content"])
```

**Example: Testing Error Handling**

```python
import pytest
from src.services.mcp_stdio_client import MCPError

@pytest.mark.integration
@pytest.mark.asyncio
async def test_invalid_tool_error(mcp_stdio_client):
    """Test error handling for invalid tool name."""
    with pytest.raises(MCPError) as exc_info:
        await mcp_stdio_client.call_tool("nonexistent_tool", {})

    assert "not found" in str(exc_info.value).lower()
```

### Test Coverage Requirements

Per Story 11.2.6 AC#1:
- **Minimum Coverage**: >90% for all MCP modules
- **Current Coverage**:
  - `mcp_stdio_client.py`: 92%
  - `mcp_http_sse_client.py`: 91%
  - `mcp_health_monitor.py`: 93%
  - `mcp_server_service.py`: 94%
  - `mcp_tool_bridge.py`: 96%

**Check Coverage:**
```bash
pytest --cov=src/services/mcp_* --cov=src/api/mcp_* --cov-report=term-missing
```

### Troubleshooting Tests

**Issue: "npx: command not found"**

**Solution:**
```bash
# macOS
brew install node

# Ubuntu
sudo apt install nodejs npm

# Verify
npx --version
```

**Issue: Tests timeout**

**Solution:**
```bash
# Increase timeout for slow machines
pytest tests/integration/ --timeout=60
```

**Issue: "MCP server already running"**

**Solution:**
```bash
# Kill any hanging processes
pkill -f "server-everything"

# Rerun tests
pytest tests/integration/ -v
```

### Continuous Integration

Tests run automatically in CI/CD:

**GitHub Actions Workflow:**
```yaml
# .github/workflows/ci.yml
test-mcp-integration:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/setup-node@v3
      with:
        node-version: '18'
    - run: npm install
    - run: pytest tests/integration/test_mcp_*.py -v
```

**Expected Results:**
- Unit tests: ~5 seconds, 141+ tests passing
- Integration tests: ~10 seconds, 42 tests passing
- Total MCP test coverage: >90%

### Developer Testing Workflow

**Before Committing Code:**

1. **Run unit tests** (fast feedback):
   ```bash
   pytest tests/unit/test_mcp_*.py -v
   ```

2. **Run affected integration tests**:
   ```bash
   # If you modified stdio client
   pytest tests/integration/test_mcp_stdio_workflow.py -v

   # If you modified HTTP client
   pytest tests/integration/test_mcp_http_sse_workflow.py -v
   ```

3. **Check test coverage**:
   ```bash
   pytest --cov=src/services/mcp_stdio_client.py --cov-report=term-missing
   # Should be >90%
   ```

4. **Run full test suite** (before push):
   ```bash
   pytest tests/unit/test_mcp_*.py tests/integration/test_mcp_*.py -v
   ```

**Manual Testing:**

For manual testing with real MCP servers:

```bash
# Test with filesystem server
docker-compose exec api python -c "
from src.services.mcp_stdio_client import MCPStdioClient
from src.schemas.mcp_server import MCPServerResponse
from uuid import uuid4
from datetime import datetime, timezone
import asyncio

async def test():
    config = MCPServerResponse(
        id=uuid4(),
        tenant_id=uuid4(),
        name='test',
        description='test',
        transport_type='stdio',
        command='npx',
        args=['-y', '@modelcontextprotocol/server-filesystem', '/tmp'],
        env={},
        status='active',
        consecutive_failures=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    async with MCPStdioClient(config) as client:
        await client.initialize()
        tools = await client.list_tools()
        print(f'Found {len(tools)} tools:', [t['name'] for t in tools])

asyncio.run(test())
"
```

### Performance Benchmarks

Story 11.2.6 includes performance tests with baseline expectations:

| Metric | Threshold | Typical Value |
|--------|-----------|---------------|
| Single tool invocation | < 5s | ~0.1s |
| 10 sequential calls | < 30s | ~1.0s |
| 15 concurrent calls (3 clients) | < sequential time | ~0.23s |
| Client spawn + initialize | < 10s | ~0.17s |
| Health check | < 10s | ~0.18s |
| Capability discovery | < 15s | ~0.18s |

**Run Performance Tests:**
```bash
pytest tests/integration/test_mcp_performance.py -v -s
# -s shows performance metrics in output
```

**Example Output:**
```
Average latency per call: 0.001s
Concurrent execution: 15 calls in 0.23s (0.015s per call)
Client spawn and initialize: 0.171s
5 client lifecycles: 0.89s (0.18s per cycle)
Health check latency: 0.176s
Capability discovery: 0.177s, found 5 tools
```

### Documentation for Testing

For complete testing documentation, see:
- [tests/README.md](../tests/README.md) - Full testing guide
- [Story 11.2.6](../docs/stories/11-2-6-mcp-integration-testing-and-documentation.md) - Test requirements and acceptance criteria
- [MCP Integration Tests](../tests/integration/) - Test source code with inline documentation

## API Reference

### src/services/mcp_tool_bridge.py

Main bridge service for converting MCP primitives to LangChain tools.

**Key Methods**:
- `get_langchain_tools(mcp_tool_assignments)` - Convert assignments to LangChain tools
- `cleanup()` - Clean up MCP client resources

### src/services/agent_execution_service.py

Orchestrates agent execution with MCP tool support.

**Key Methods**:
- `execute_agent(agent_id, tenant_id, user_message, context, timeout_seconds)` - Execute agent

### src/api/agent_execution.py

REST API endpoints for agent execution.

**Endpoints**:
- `POST /api/agent-execution/execute` - Execute agent
- `GET /api/agent-execution/health` - Health check
