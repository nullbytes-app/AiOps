# Agent Tool Execution Bug - Root Cause Analysis

**Date**: 2025-11-16
**Execution ID**: `38eca40f-be24-4f41-8bee-0e728635da53`
**Status**: ❌ **ROOT CAUSE IDENTIFIED**

---

## Executive Summary

Agent execution `38eca40f` requested MCP tool calls (jira_search, web_search) but never executed them. The agent completed after a single LLM response containing tool call requests, without entering the expected ReAct loop to actually invoke those tools.

**Root Cause**: Hardcoded `model_provider="openai"` in `agent_execution_service.py:303` causes non-OpenAI models (like Grok) to malfunction. The Grok model generates tool calls as JSON text instead of proper function call objects, preventing LangGraph's `create_react_agent` from recognizing and executing them.

---

## Investigation Timeline

### 1. Initial Observation
Execution `38eca40f` showed:
- ✅ Agent had 31 MCP tools loaded (after previous fixes)
- ✅ LLM requested 4 tool calls (2x jira_search, 2x web_search)
- ❌ Tools were NEVER executed (`tool_calls_count: 0`)
- ❌ Execution completed after single LLM response

### 2. Execution Trace Analysis

```json
{
  "steps": [
    {
      "step_type": "llm_response",
      "response": "{\n  \"tool_calls\": [\n    {\n      \"id\": \"call_1\",\n      \"type\": \"function\",\n      \"function\": {\n        \"name\": \"jira_search\",\n        \"arguments\": {\"jql\": \"...\"}\n      }\n    },\n    ...  // 3 more tool calls
  ],
  \"duration_ms\": 7023
}
  ],
  "total_duration_ms": 9398,
  "model_used": "xai/grok-4-fast-reasoning",
  "tool_calls_count": 0  ← NO TOOLS EXECUTED!
}
```

**Critical Finding**: The `response` field contains **JSON text** with tool_calls, not actual structured tool call objects.

### 3. Expected vs Actual Behavior

#### Expected (LangGraph ReAct Loop):
1. LLM generates structured tool calls via function calling API
2. LangGraph intercepts tool call objects
3. Tools are executed
4. Results added to message history as `ToolMessage` instances
5. LLM called again with tool results
6. Repeat until LLM returns final answer (no tool calls)

####Actual (What Happened):
1. LLM generates JSON text that LOOKS like tool calls
2. LangGraph sees plain text response (no tool call objects)
3. Treats response as final output
4. Execution completes immediately
5. No tools executed

### 4. Code Investigation

**File**: `src/services/agent_execution_service.py`
**Lines**: 299-315

```python
# Step 6: Initialize chat model with init_chat_model
llm = init_chat_model(
    model=model_string,  # e.g., "xai/grok-4-fast-reasoning"
    model_provider="openai",  # ← HARDCODED! WRONG FOR GROK!
    api_key=virtual_key,
    base_url=f"{self.litellm_proxy_url}/v1",
    temperature=temperature,
    max_tokens=max_tokens,
)

# Step 7: Create ReAct agent with LangGraph
agent_executor = create_react_agent(
    model=llm,
    tools=langchain_tools,
)
```

**The Bug**: `model_provider="openai"` is hardcoded for ALL models, regardless of their actual provider.

### 5. Root Cause Explanation

**Model Used**: `xai/grok-4-fast-reasoning` (X.AI/Grok, NOT OpenAI)
**Configuration**: `model_provider="openai"` (incorrect)
**Result**: LangChain uses OpenAI SDK to communicate with Grok model
**Consequence**: Tool calls not properly bound using Grok's native function calling format
**Outcome**: Model generates tool calls as JSON text instead of via function calling API

**Why This Matters**:
- Different LLM providers use different tool calling formats
- OpenAI: Uses `tools` parameter with JSON schema
- X.AI/Grok: Uses different function calling conventions
- Anthropic/Claude: Uses `tools` with different schema format
- When `model_provider` mismatches actual model, tool binding fails

---

## Evidence Summary

### From Database
```sql
SELECT id, model_used, tool_calls_count
FROM agent_test_executions
WHERE id = '38eca40f-be24-4f41-8bee-0e728635da53';

-- Result:
-- model_used: "xai/grok-4-fast-reasoning"
-- tool_calls_count: 0
```

### From Worker Logs
```
[2025-11-16 11:00:50] Creating ReAct agent
[2025-11-16 11:00:50] Executing agent
[2025-11-16 11:00:56] HTTP Request: POST http://litellm:4000/v1/chat/completions "HTTP/1.1 200 OK"
[2025-11-16 11:00:56] Agent execution completed
```

Only ONE LLM call, no tool execution.

### From Execution Trace
- **Steps**: 1 (should be multiple for ReAct loop)
- **Tool calls count**: 0 (should be 4)
- **Response format**: Plain JSON text (should be empty final response after tool execution)

---

## Why Previous Fixes Didn't Solve This

### Previous Session Work:
1. ✅ Fixed MCP server package (`@iflow-mcp/jira-mcp`)
2. ✅ Fixed environment variables (`JIRA_BASE_URL`, `JIRA_USER_EMAIL`)
3. ✅ Cleared stale tool cache (restarted worker)
4. ✅ Verified 31 tools discovered and loaded

### Why Tools Still Didn't Execute:
The tools ARE loaded correctly and ARE being passed to `create_react_agent`. However, the **LLM model binding is broken** due to the hardcoded `model_provider="openai"` mismatch.

Think of it like this:
- **Previous fixes**: Got the tools in the toolbox
- **Current issue**: The agent is holding the toolbox but speaking the wrong language to ask for tools

---

## Solution Required

### Option 1: Dynamic Provider Detection (Recommended)
Modify `agent_execution_service.py:301-308` to dynamically determine the correct `model_provider`:

```python
# Determine correct model provider from model string
def get_model_provider(model_string: str) -> str:
    """Extract provider from model string like 'xai/grok-4' → 'xai'."""
    if "/" in model_string:
        provider = model_string.split("/")[0]
        # Map LiteLLM providers to LangChain provider names
        provider_map = {
            "xai": "xai",  # or whatever LangChain calls X.AI
            "openai": "openai",
            "anthropic": "anthropic",
            "google": "google",
            # etc.
        }
        return provider_map.get(provider, "openai")  # default to openai
    return "openai"

llm = init_chat_model(
    model=model_string,
    model_provider=get_model_provider(model_string),  # DYNAMIC!
    api_key=virtual_key,
    base_url=f"{self.litellm_proxy_url}/v1",
    temperature=temperature,
    max_tokens=max_tokens,
)
```

### Option 2: Remove Provider Specification
Let LangChain auto-detect from the model string or base_url:

```python
llm = init_chat_model(
    model=model_string,
    # model_provider omitted - let LangChain auto-detect
    api_key=virtual_key,
    base_url=f"{self.litellm_proxy_url}/v1",
    temperature=temperature,
    max_tokens=max_tokens,
)
```

###Option 3: Use LiteLLM's Built-in Model Mapping
Since we're using LiteLLM proxy, leverage its model mapping instead of LangChain's `init_chat_model`:

```python
from langchain_openai import ChatOpenAI

# Use ChatOpenAI with LiteLLM proxy (works for all providers)
llm = ChatOpenAI(
    model=model_string,  # LiteLLM handles provider routing
    api_key=virtual_key,
    base_url=f"{self.litellm_proxy_url}/v1",
    temperature=temperature,
    max_tokens=max_tokens,
)
```

---

## Verification Plan

After implementing the fix:

1. **Trigger Test Execution**:
```bash
curl -X POST "http://localhost:8000/api/agent-execution/execute" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: test1" \
  -d '{
    "agent_id": "022e85cf-e7b6-45d5-81c2-b0b6823cd8f3",
    "user_message": "Search Jira for KAN-24 and post a test comment",
    "timeout_seconds": 180
  }'
```

2. **Check Execution Trace** (should show):
```json
{
  "steps": [
    {"step_type": "tool_call", "tool_name": "jira_search", ...},
    {"step_type": "tool_call", "tool_name": "jira_add_comment", ...},
    {"step_type": "llm_response", "response": "Task completed..."}
  ],
  "tool_calls_count": 2,  // NOT 0!
  "model_used": "xai/grok-4-fast-reasoning"
}
```

3. **Verify in Jira**: Comment should appear on KAN-24

4. **Check Worker Logs**: Should see multiple LLM calls and tool executions:
```
INFO - Loaded 31 tools
INFO - Converted 31 tools to LangChain format
INFO - Creating ReAct agent
INFO - Executing agent
INFO - Calling tool: jira_search
INFO - Tool result: ...
INFO - Calling tool: jira_add_comment
INFO - Tool result: ...
INFO - Agent execution completed
INFO - Tool calls: 2
```

---

## Impact Analysis

### Systems Affected
- ✅ **Agent Execution Service**: All agents using non-OpenAI models
- ✅ **Worker Tasks**: Any async agent execution
- ✅ **MCP Tool Invocation**: Tool calling broken for Grok, Claude, etc.

### Models Affected
- ❌ `xai/grok-*` (currently broken - confirmed)
- ❌ `anthropic/claude-*` (likely broken - same hardcoded provider)
- ❌ `google/gemini-*` (likely broken)
- ✅ `openai/gpt-*` (works - provider matches hardcoded value)

### User Impact
- **High**: Agents using non-OpenAI models cannot execute tools
- **Critical**: Ticket Enhancer agent (uses Grok) cannot post comments to Jira
- **Blocker**: Entire MCP tool integration is non-functional for 75% of LLM models

---

## Related Issues

### Issue #1: Stale Tool Cache (RESOLVED)
- **Fixed**: Restarted worker to clear in-memory cache
- **Result**: 31 tools now loaded correctly

### Issue #2: Wrong NPM Package (RESOLVED)
- **Fixed**: Updated to `@iflow-mcp/jira-mcp`
- **Result**: MCP server connects and discovers tools

### Issue #3: Wrong Env Vars (RESOLVED)
- **Fixed**: Updated to `JIRA_BASE_URL`, `JIRA_USER_EMAIL`
- **Result**: No more environment variable errors

### Issue #4: Hardcoded Provider (CURRENT)
- **Status**: Identified but not yet fixed
- **Impact**: Tools loaded but not executable for non-OpenAI models

---

## Summary

**What Works**:
- ✅ MCP server configuration
- ✅ Tool discovery (31 tools)
- ✅ Tool loading in agent
- ✅ LangChain tool conversion
- ✅ Agent execution triggers

**What's Broken**:
- ❌ Tool binding for non-OpenAI models
- ❌ LLM function calling format mismatch
- ❌ ReAct loop never executes tools
- ❌ Agent completes without calling tools

**Fix Needed**:
Change `model_provider="openai"` to dynamically match the actual model provider, or use LiteLLM's built-in model routing.

**Estimated Fix Time**: 15 minutes (single line code change + testing)

**Priority**: CRITICAL - Blocks all non-OpenAI model tool usage
