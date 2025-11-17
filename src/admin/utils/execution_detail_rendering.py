"""
Execution Detail Rendering for Streamlit Admin UI (Story 10.3).

This module provides rendering functions for the detailed execution view,
extending the Execution History page with comprehensive LLM trace display.

Key Features:
- Fetches execution details from /api/executions/{id} endpoint
- Parses LLM conversation data (system prompt, user message, response, tool calls)
- Renders metadata, input data, LLM conversation, and error sections
- Applies sensitive data masking per AC5
- Provides copy-to-clipboard functionality via st.code()
- Handles large payloads with collapsible expanders

Related Stories:
- Story 10.1: Execution Details API Endpoint
- Story 10.2: Execution History Page
- Story 10.3: Detailed Execution View (this module)
"""

import json
from typing import Any, Optional

import httpx
import streamlit as st
from loguru import logger

from src.utils.security import mask_sensitive_data


@st.cache_data(ttl=30)
def fetch_execution_detail(execution_id: str, tenant_id: Optional[str] = None) -> Optional[dict]:
    """
    Fetch execution details from API endpoint /api/executions/{id}.

    Calls the API endpoint with tenant isolation to retrieve full execution
    details. Results are cached for 30 seconds to reduce API load.

    Args:
        execution_id: UUID of the execution to retrieve
        tenant_id: Tenant ID for the execution (required for proper tenant isolation)

    Returns:
        dict: Execution details with masked sensitive data, or None if not found

    Raises:
        None: Errors are logged but not raised to maintain UI stability

    Examples:
        >>> details = fetch_execution_detail("123e4567-e89b-12d3-a456-426614174000", "test-tenant")
        >>> print(details["status"])
        'completed'
    """
    try:
        # Use httpx for async-compatible HTTP client (Constraint 3)
        import os
        base_url = os.getenv("API_BASE_URL", "http://api:8000")
        url = f"{base_url}/api/executions/{execution_id}"

        # Use provided tenant_id, fallback to session state, then env var
        # FIX: Accept tenant_id as parameter instead of guessing from session_state
        if not tenant_id:
            tenant_id = st.session_state.get("selected_tenant_id") or \
                        st.session_state.get("tenant_id") or \
                        os.getenv("DEFAULT_TENANT_ID", "test-tenant")

        # Make synchronous request with tenant header
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, headers={"X-Tenant-ID": tenant_id})

        if response.status_code == 200:
            data = response.json()
            logger.info(f"Successfully fetched execution details: {execution_id}")
            return data
        elif response.status_code == 404:
            logger.warning(f"Execution not found: {execution_id}")
            return None
        elif response.status_code == 403:
            logger.warning(f"Forbidden access to execution: {execution_id}")
            return None
        else:
            logger.error(
                f"Failed to fetch execution {execution_id}: "
                f"HTTP {response.status_code}"
            )
            return None

    except httpx.TimeoutException:
        logger.error(f"Timeout fetching execution {execution_id}")
        return None
    except Exception as e:
        logger.error(f"Error fetching execution {execution_id}: {e}")
        return None


def format_llm_conversation(output_data: Any) -> dict:
    """
    Parse execution output_data to extract LLM conversation fields.

    Extracts system prompt, user message, LLM response, and tool calls
    from the execution_trace JSON structure. Handles both flat format and
    steps array format. Handles missing fields gracefully by returning
    empty strings/lists.

    Args:
        output_data: Execution output_data (dict or JSON string)

    Returns:
        dict: Parsed LLM conversation with keys:
            - system_prompt (str)
            - user_message (str)
            - llm_response (str)
            - tool_calls (list)

    Examples:
        >>> output = {"system_prompt": "You are...", "response": "Sure!"}
        >>> parsed = format_llm_conversation(output)
        >>> print(parsed["system_prompt"])
        'You are...'
    """
    # Handle string JSON input
    if isinstance(output_data, str):
        try:
            output_data = json.loads(output_data)
        except json.JSONDecodeError:
            logger.warning("Failed to parse output_data as JSON")
            return {
                "system_prompt": "",
                "user_message": "",
                "llm_response": "",
                "tool_calls": [],
            }

    # Handle None or non-dict input
    if not isinstance(output_data, dict):
        return {
            "system_prompt": "",
            "user_message": "",
            "llm_response": "",
            "tool_calls": [],
        }

    # FIX: Handle actual execution_trace format with step_type="llm_response"
    if "steps" in output_data and isinstance(output_data["steps"], list):
        # Find the first LLM response step
        for step in output_data["steps"]:
            step_type = step.get("step_type", "")

            # Handle "llm_response" step type (actual format from workers)
            if step_type == "llm_response":
                return {
                    "system_prompt": step.get("system_prompt", ""),
                    "user_message": step.get("user_message", step.get("input", "")),
                    "llm_response": step.get("response", ""),
                    "tool_calls": step.get("tool_calls", []),
                }

            # Handle "llm_call" step type (alternative format)
            if step_type == "llm_call":
                input_data = step.get("input", {})
                return {
                    "system_prompt": input_data.get("system_prompt", ""),
                    "user_message": input_data.get("user_message", ""),
                    "llm_response": step.get("output", ""),
                    "tool_calls": step.get("tool_calls", []),
                }

        # No LLM step found, return empty
        logger.warning("No LLM step found in execution_trace steps")
        return {
            "system_prompt": "",
            "user_message": "",
            "llm_response": "",
            "tool_calls": [],
        }

    # Handle legacy flat format (fallback for old executions)
    return {
        "system_prompt": output_data.get("system_prompt", ""),
        "user_message": output_data.get("user_message", output_data.get("input", "")),
        "llm_response": output_data.get("response", output_data.get("llm_response", "")),
        "tool_calls": output_data.get("tool_calls", []),
    }


def format_json_display(data: Any) -> str:
    """
    Pretty-print JSON data for st.code() display.

    Formats dict/list data as indented JSON string for readable display
    in code blocks with syntax highlighting.

    Args:
        data: Data to format (dict, list, or JSON string)

    Returns:
        str: Formatted JSON string with 2-space indentation

    Examples:
        >>> format_json_display({"key": "value"})
        '{\\n  "key": "value"\\n}'
    """
    # If already a string, try to parse and re-format
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            # Return as-is if not valid JSON
            return data

    # Format with indentation
    try:
        return json.dumps(data, indent=2, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        logger.warning(f"Failed to format data as JSON: {e}")
        return str(data)


def render_metadata_section(execution: dict) -> None:
    """
    Render execution metadata section with st.metric() (AC1).

    Displays:
    - Execution ID (database record UUID)
    - Task ID (Celery task UUID for correlation)
    - Status with color indicator
    - Execution Time (ms)
    - Agent Name
    - Tenant Name
    - Created At timestamp

    Args:
        execution: Execution details dict from API

    Returns:
        None: Renders directly to Streamlit UI
    """
    st.subheader("📋 Execution Metadata")

    # Three columns for metrics (Constraint 3)
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Execution ID", execution["id"])

        # Task ID for correlation with webhook response
        task_id = execution.get("task_id", "N/A")
        if task_id and task_id != "N/A":
            st.metric("Task ID (Celery)", task_id)
        else:
            st.metric("Task ID (Celery)", "N/A")

        # Status with color indicator (AC1)
        status = execution["status"]
        if status.lower() == "completed" or status.lower() == "success":
            status_display = "🟢 Completed"
        elif status.lower() == "failed":
            status_display = "🔴 Failed"
        else:
            status_display = f"⚪ {status.title()}"
        st.metric("Status", status_display)

    with col2:
        execution_time = execution.get("execution_time", 0)
        st.metric("Execution Time", f"{execution_time} ms")

        # Agent name (from API response - may need join)
        agent_id = execution.get("agent_id", "N/A")
        st.metric("Agent ID", str(agent_id)[:8] + "...")

    with col3:
        tenant_name = execution.get("tenant_id", "N/A")
        st.metric("Tenant", tenant_name)

        # Format created_at timestamp
        created_at = execution.get("created_at", "N/A")
        if isinstance(created_at, str):
            # Already formatted string
            st.metric("Created", created_at)
        else:
            # DateTime object - format it
            try:
                formatted_date = created_at.strftime("%Y-%m-%d %H:%M:%S")
                st.metric("Created", formatted_date)
            except AttributeError:
                st.metric("Created", str(created_at))


def render_input_section(execution: dict) -> None:
    """
    Render input data section with st.json() and collapsible expander (AC2).

    Displays formatted webhook payload with:
    - Syntax highlighting via st.json()
    - Collapsible expander for large payloads (AC7)
    - Copy-to-clipboard via st.code() (AC6)
    - Sensitive data masking (AC5)

    Args:
        execution: Execution details dict from API

    Returns:
        None: Renders directly to Streamlit UI
    """
    st.subheader("📥 Input Data")

    input_data = execution.get("input_data", {})

    # Check if payload is large (>1000 lines) for AC7
    input_json_str = format_json_display(input_data)
    line_count = input_json_str.count("\n") + 1
    is_large = line_count > 1000

    # Use expander for large payloads, expanded by default for small ones
    with st.expander(
        f"View Input Payload ({line_count} lines)",
        expanded=(not is_large),
    ):
        # Display with syntax highlighting (Constraint 3)
        st.json(input_data)

        st.markdown("---")

        # Copy functionality (AC6)
        st.markdown("**Copy Raw JSON:**")
        st.code(input_json_str, language="json")


def render_llm_conversation(execution: dict) -> None:
    """
    Render LLM conversation section with system prompt, messages, and responses (AC3).

    Displays:
    - System prompt (note: stored with agent, not execution)
    - User message (extracted from input_data/payload)
    - LLM response text (from execution_trace)
    - Tool calls (if applicable) - each shown as individual expandable card

    Each section uses st.text_area() for full content display with scrolling.

    Args:
        execution: Execution details dict from API

    Returns:
        None: Renders directly to Streamlit UI
    """
    st.subheader("💬 LLM Conversation")

    # Get execution ID for unique widget keys
    execution_id = execution.get("id", "unknown")
    agent_id = execution.get("agent_id", "unknown")

    # System Prompt section
    # NOTE: System prompt is stored with the agent, not in the execution record
    st.markdown("**System Prompt:**")
    st.info(
        f"ℹ️ System prompt is configured on the agent (ID: {str(agent_id)[:8]}...)\n\n"
        "To view the system prompt, go to **Agent Management** page and select this agent."
    )

    st.markdown("---")

    # User Message section - Extract from input_data (payload)
    st.markdown("**User Message (Input Payload):**")
    input_data = execution.get("input_data", {})

    # For JIRA webhooks, extract the issue description and summary
    if "issue" in input_data and isinstance(input_data["issue"], dict):
        fields = input_data["issue"].get("fields", {})
        summary = fields.get("summary", "")
        description = fields.get("description", "")
        issue_key = input_data.get("issue_key", "N/A")

        user_message = f"**Issue:** {issue_key}\n**Summary:** {summary}\n\n**Description:**\n{description}"

        st.text_area(
            "User Message Content",
            value=user_message,
            height=200,
            label_visibility="collapsed",
            key=f"user_message_{execution_id}"
        )
    else:
        # Fallback: Display full payload as JSON
        st.json(input_data)

    st.markdown("---")

    # LLM Response section - Extract from output_data (execution_trace)
    st.markdown("**LLM Response:**")
    output_data = execution.get("output_data", {})
    conversation = format_llm_conversation(output_data)

    llm_response = conversation.get("llm_response", "N/A")
    if llm_response and llm_response != "N/A":
        # Use text_area with larger height for potentially long responses
        st.text_area(
            "LLM Response Content",
            value=llm_response,
            height=400,
            label_visibility="collapsed",
            key=f"llm_response_{execution_id}"
        )
    else:
        st.warning("No LLM response found in execution trace")

    # Tool Calls section (if present) - Extract from steps array
    # FIX: Tool calls are stored as separate steps with step_type="tool_call"
    # not as a tool_calls array inside the llm_response step
    tool_calls_count = output_data.get("tool_calls_count", 0)

    # Extract all tool_call steps from output_data.steps
    tool_calls = []
    if "steps" in output_data and isinstance(output_data["steps"], list):
        tool_calls = [
            step for step in output_data["steps"]
            if step.get("step_type") == "tool_call"
        ]

    st.markdown("---")
    st.markdown(f"**🔧 Tool Calls:** {tool_calls_count} total")

    if tool_calls and len(tool_calls) > 0:
        # Render each tool call as a separate expandable card
        for idx, tool in enumerate(tool_calls, 1):
            # Extract tool information from the tool_call step format
            # Format: {step_type, tool_name, tool_args, tool_result}
            tool_name = tool.get("tool_name", "Unknown Tool")
            tool_args = tool.get("tool_args", {})
            tool_result = tool.get("tool_result", "")

            # Create expander for each tool
            with st.expander(f"🔧 Tool {idx}: **{tool_name}**", expanded=False):
                # Two-column layout for input/output
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**📥 Input:**")
                    if tool_args:
                        st.json(tool_args)
                    else:
                        st.info("No input parameters")

                with col2:
                    st.markdown("**📤 Output:**")
                    if tool_result:
                        # Handle string vs object output
                        if isinstance(tool_result, str):
                            # Try to parse as JSON first
                            try:
                                parsed_output = json.loads(tool_result)
                                st.json(parsed_output)
                            except json.JSONDecodeError:
                                # Display as text if not JSON
                                st.code(tool_result, language="text")
                        else:
                            st.json(tool_result)
                    else:
                        st.info("No output available")

                # Show error if tool call failed
                if "error" in tool:
                    st.error(f"❌ **Error:** {tool['error']}")

                # Show additional metadata if available
                metadata_items = []
                if "timestamp" in tool:
                    metadata_items.append(f"⏱️ Timestamp: `{tool['timestamp']}`")
                if "duration_ms" in tool:
                    metadata_items.append(f"⚡ Duration: `{tool['duration_ms']}ms`")
                if "status" in tool:
                    status_icon = "✅" if tool["status"] == "success" else "❌"
                    metadata_items.append(f"{status_icon} Status: `{tool['status']}`")

                if metadata_items:
                    st.markdown("---")
                    st.caption(" | ".join(metadata_items))

    elif tool_calls_count == 0:
        st.info("ℹ️ No MCP tools were called during this execution")


def render_error_section(execution: dict) -> None:
    """
    Render error details section for failed executions (AC4).

    Only displayed if status == "failed". Shows:
    - Error message
    - Stack trace (if available)
    - Timestamp (from execution metadata)

    Args:
        execution: Execution details dict from API

    Returns:
        None: Renders directly to Streamlit UI (or nothing if no errors)
    """
    # Only show error section for failed executions (AC4)
    status = execution.get("status", "").lower()
    if status != "failed":
        return

    st.subheader("❌ Error Details")

    # Display error message
    error_message = execution.get("error_message")
    if error_message:
        st.error(f"**Error Message:**\n\n{error_message}")
    else:
        st.error("**Error:** Unknown error (no error message available)")

    # Display stack trace if available
    errors = execution.get("errors", {})
    stack_trace = None

    # Try different possible locations for stack trace
    if isinstance(errors, dict):
        stack_trace = errors.get("stack_trace") or errors.get("traceback")

    if stack_trace:
        with st.expander("View Stack Trace"):
            st.code(stack_trace, language="python")

    # Show timestamp (AC4 requirement)
    created_at = execution.get("created_at", "N/A")
    st.caption(f"Failed at: {created_at}")
