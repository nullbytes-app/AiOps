"""
Agent Testing Sandbox UI Helper - Streamlit components for agent testing.

Provides reusable Streamlit components for:
- Test payload editor with JSON validation
- Test execution runner with sandbox mode
- Execution trace viewer with step-by-step details
- Token usage metrics and cost display
- Execution timing breakdown with charts
- Test result comparison feature
- Error display with syntax highlighting
"""

import asyncio
import json
import os
import time
from typing import Any, Optional
from uuid import UUID

import plotly.graph_objects as go
import streamlit as st
from pygments import highlight, lexers
from pygments.formatters import HtmlFormatter

from admin.utils.agent_helpers import async_to_sync

# API configuration
API_BASE_URL: str = os.getenv("API_BASE_URL", "http://api:8000")


# ============================================================================
# Test Interface Helper Functions
# ============================================================================


async def execute_test_async(agent_id: UUID, payload: dict, tenant_id: str) -> dict:
    """
    Execute agent test via API.

    Args:
        agent_id: Agent UUID
        payload: Test payload
        tenant_id: Tenant identifier (required)

    Returns:
        dict: Test response with execution trace, tokens, timing, errors
    """
    try:
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/agents/{agent_id}/test",
                json={"payload": payload, "trigger_type": "webhook"},
                headers={"X-Tenant-ID": tenant_id},
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"error": f"Test execution failed: {str(e)}", "success": False}


async def fetch_test_history_async(agent_id: UUID, limit: int = 10, offset: int = 0) -> dict:
    """
    Fetch test execution history.

    Args:
        agent_id: Agent UUID
        limit: Number of results
        offset: Pagination offset

    Returns:
        dict: Test history response
    """
    try:
        import httpx

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{API_BASE_URL}/api/agents/{agent_id}/test-history",
                params={"limit": limit, "offset": offset},
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"error": f"Failed to fetch history: {str(e)}", "tests": []}


async def compare_tests_async(agent_id: UUID, test_id_1: str, test_id_2: str) -> dict:
    """
    Compare two test results.

    Args:
        agent_id: Agent UUID
        test_id_1: First test ID
        test_id_2: Second test ID

    Returns:
        dict: Comparison result with diffs
    """
    try:
        import httpx

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/agents/{agent_id}/test/compare",
                json={"test_id_1": test_id_1, "test_id_2": test_id_2},
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"error": f"Comparison failed: {str(e)}", "diff": {}}


# ============================================================================
# Streamlit UI Components
# ============================================================================


def render_test_payload_editor() -> Optional[dict]:
    """
    Render JSON editor for test payload input (AC#2).

    Returns:
        Optional[dict]: Parsed payload if valid, None otherwise
    """
    st.subheader("📝 Test Payload")

    # Example payload templates
    with st.expander("📋 Example Payloads", expanded=False):
        example_payload = {
            "ticket_id": "123456",
            "subject": "Test ticket for agent",
            "description": "This is a test ticket to verify agent behavior",
            "priority": "high",
            "status": "open",
        }
        st.json(example_payload)

    # JSON editor with validation (AC#2)
    payload_text = st.text_area(
        "Enter test payload (JSON format):",
        value=json.dumps({"ticket_id": "123456", "subject": "Test ticket"}, indent=2),
        height=200,
        key="test_payload_editor",
        help="Provide a JSON object representing the webhook payload or trigger event",
    )

    # Validate JSON
    try:
        payload = json.loads(payload_text)
        st.success("✅ Valid JSON")
        return payload
    except json.JSONDecodeError as e:
        st.error(f"❌ Invalid JSON: {str(e)}")
        return None


def render_execution_trace(trace_data: dict) -> None:
    """
    Render execution trace with expandable steps (AC#4).

    Args:
        trace_data: Execution trace with steps list
    """
    st.subheader("🔍 Execution Trace")

    steps = trace_data.get("steps", [])
    if not steps:
        st.info("No execution steps recorded")
        return

    # Display total summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Steps", len(steps))
    with col2:
        total_duration_ms = trace_data.get("total_duration_ms", 0)
        st.metric("Total Duration", f"{total_duration_ms}ms")
    with col3:
        st.metric("Success", "✅" if trace_data.get("success") else "❌")

    # Expandable steps (AC#4, Task 4.4)
    for idx, step in enumerate(steps, 1):
        step_type = step.get("step_type", "unknown").upper()
        title = f"{idx}. {step_type}: {step.get('tool_name', step.get('model', 'Step'))}"
        duration = step.get("duration_ms", 0)

        with st.expander(f"{title} ({duration}ms)", expanded=False):
            # Input/Output details
            if "input" in step:
                st.markdown("**Input:**")
                st.json(step["input"])
            if "output" in step:
                st.markdown("**Output:**")
                st.json(step["output"])
            if "response" in step:
                st.markdown("**Response:**")
                st.write(step["response"])

            # Metadata
            st.caption(f"Timestamp: {step.get('timestamp', 'N/A')}")


def render_token_usage(token_data: dict) -> None:
    """
    Render token usage metrics with charts (AC#5).

    Args:
        token_data: Token usage stats
    """
    st.subheader("💰 Token Usage & Cost")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Input Tokens", token_data.get("input_tokens", 0))
    with col2:
        st.metric("Output Tokens", token_data.get("output_tokens", 0))
    with col3:
        st.metric("Total Tokens", token_data.get("total_tokens", 0))
    with col4:
        cost = token_data.get("estimated_cost_usd", 0)
        st.metric("Est. Cost", f"${cost:.6f}")

    # Token breakdown chart
    if token_data.get("input_tokens") or token_data.get("output_tokens"):
        fig = go.Figure(
            data=[
                go.Bar(
                    x=["Input Tokens", "Output Tokens"],
                    y=[
                        token_data.get("input_tokens", 0),
                        token_data.get("output_tokens", 0),
                    ],
                    marker=dict(color=["#1f77b4", "#ff7f0e"]),
                )
            ]
        )
        fig.update_layout(
            title="Token Distribution",
            yaxis_title="Token Count",
            showlegend=False,
            height=300,
        )
        st.plotly_chart(fig, use_container_width=True)


def render_execution_timing(timing_data: dict) -> None:
    """
    Render execution timing breakdown with chart (AC#6).

    Args:
        timing_data: Execution timing stats
    """
    st.subheader("⏱️ Execution Timing")

    total_ms = timing_data.get("total_duration_ms", 0)
    tool_latency = timing_data.get("tool_call_latency_ms", 0)
    llm_latency = timing_data.get("llm_latency_ms", 0)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Duration", f"{total_ms}ms")
    with col2:
        st.metric("Tool Calls", f"{tool_latency}ms")
    with col3:
        st.metric("LLM Requests", f"{llm_latency}ms")

    # Timing breakdown chart (Plotly horizontal bar)
    if tool_latency > 0 or llm_latency > 0:
        fig = go.Figure(
            data=[
                go.Bar(
                    y=["Timing Breakdown"],
                    x=[tool_latency],
                    name="Tool Calls",
                    orientation="h",
                    marker=dict(color="#1f77b4"),
                ),
                go.Bar(
                    y=["Timing Breakdown"],
                    x=[llm_latency],
                    name="LLM Requests",
                    orientation="h",
                    marker=dict(color="#ff7f0e"),
                ),
            ]
        )
        fig.update_layout(
            barmode="stack",
            title="Execution Timing Breakdown",
            xaxis_title="Duration (ms)",
            showlegend=True,
            height=200,
        )
        st.plotly_chart(fig, use_container_width=True)


def render_error_display(error_data: Optional[dict]) -> None:
    """
    Render error display with syntax highlighting (AC#8).

    Args:
        error_data: Error details (message, stack_trace, context)
    """
    if not error_data:
        return

    st.subheader("⚠️ Errors")

    error_message = error_data.get("message", "Unknown error")
    st.error(f"Error: {error_message}")

    # Stack trace with syntax highlighting
    stack_trace = error_data.get("stack_trace")
    if stack_trace:
        with st.expander("📋 Stack Trace", expanded=False):
            # Format stack trace with syntax highlighting
            try:
                lexer = lexers.get_lexer_by_name("python")
                formatter = HtmlFormatter(style="monokai")
                highlighted = highlight(stack_trace, lexer, formatter)
                st.markdown(highlighted, unsafe_allow_html=True)
            except Exception:
                # Fallback to plain code block
                st.code(stack_trace, language="python")

    # Additional context
    if error_data.get("context"):
        with st.expander("🔍 Error Context", expanded=False):
            st.json(error_data["context"])


def render_test_history_comparison(agent_id: UUID) -> None:
    """
    Render test history and comparison feature (AC#7).

    Args:
        agent_id: Agent UUID
    """
    st.subheader("📊 Test History & Comparison")

    # Fetch test history
    with st.spinner("Fetching test history..."):
        history_response = async_to_sync(fetch_test_history_async)(agent_id, limit=20)

    tests = history_response.get("tests", [])
    if not tests:
        st.info("No previous tests found")
        return

    # Display history table
    st.markdown("**Recent Tests:**")
    test_options = {f"{t['created_at'][:10]} - {t['id'][:8]}": t["id"] for t in tests}
    col1, col2 = st.columns(2)
    with col1:
        test1_display = st.selectbox("Compare Test 1:", options=list(test_options.keys()), key="test1_selector")
        test1_id = test_options[test1_display]

    with col2:
        test2_display = st.selectbox("Compare Test 2:", options=list(test_options.keys()), key="test2_selector")
        test2_id = test_options[test2_display]

    # Comparison button
    if st.button("🔄 Compare Results", use_container_width=True):
        with st.spinner("Comparing tests..."):
            comparison = async_to_sync(compare_tests_async)(agent_id, test1_id, test2_id)

        if "error" in comparison:
            st.error(f"Comparison failed: {comparison['error']}")
        else:
            st.subheader("Comparison Results")

            # Display diffs
            diff_data = comparison.get("diff", {})
            if diff_data:
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Token Difference:**")
                    token_diff = diff_data.get("token_diff", {})
                    st.json(token_diff)
                with col2:
                    st.markdown("**Timing Difference:**")
                    timing_diff = diff_data.get("timing_diff", {})
                    st.json(timing_diff)
            else:
                st.info("Tests are identical")


# ============================================================================
# Main Test Interface
# ============================================================================


def render_test_agent_tab(agent_id: UUID, tenant_id: str) -> None:
    """
    Render complete Test Agent tab (AC#1).

    Includes:
    - Payload editor (AC#2)
    - Run Test button (AC#3)
    - Execution trace (AC#4)
    - Token usage (AC#5)
    - Timing breakdown (AC#6)
    - Test history & comparison (AC#7)
    - Error display (AC#8)

    Args:
        agent_id: Agent UUID to test
        tenant_id: Tenant ID for the agent
    """
    st.subheader("🧪 Test Agent in Sandbox")
    st.markdown("Execute and verify agent behavior before activating. Tests run in dry-run mode with no side effects.")

    # Initialize session state
    if "test_results" not in st.session_state:
        st.session_state.test_results = None
    if "test_running" not in st.session_state:
        st.session_state.test_running = False

    # Payload editor (AC#2)
    payload = render_test_payload_editor()

    # Run Test button (AC#3)
    if st.button("▶️ Run Test", use_container_width=True, type="primary"):
        if payload is None:
            st.error("Please provide a valid JSON payload")
        else:
            st.session_state.test_running = True
            with st.spinner("Executing test in sandbox mode..."):
                result = async_to_sync(execute_test_async)(agent_id, payload, tenant_id)
                st.session_state.test_results = result
                st.session_state.test_running = False

    # Display results if available
    if st.session_state.test_results:
        results = st.session_state.test_results

        if "error" in results and results.get("error"):
            st.error(f"Test execution failed: {results['error']}")
        else:
            st.success("✅ Test execution completed")

            # Create tabs for different result views
            tab1, tab2, tab3, tab4, tab5 = st.tabs(
                ["Execution Trace", "Token Usage", "Timing", "History", "Errors"]
            )

            with tab1:
                # Execution trace (AC#4, Task 4.4)
                trace = results.get("execution_trace", {})
                if trace:
                    render_execution_trace(trace)
                else:
                    st.info("No execution trace available")

            with tab2:
                # Token usage (AC#5, Task 4.5)
                tokens = results.get("token_usage", {})
                if tokens:
                    render_token_usage(tokens)
                else:
                    st.info("No token usage data available")

            with tab3:
                # Execution timing (AC#6, Task 4.6)
                timing = results.get("execution_time", {})
                if timing:
                    render_execution_timing(timing)
                else:
                    st.info("No timing data available")

            with tab4:
                # Test history and comparison (AC#7, Task 4.7)
                render_test_history_comparison(agent_id)

            with tab5:
                # Error display (AC#8, Task 4.8)
                errors = results.get("errors")
                if errors:
                    render_error_display(errors)
                else:
                    st.success("✅ No errors detected")
