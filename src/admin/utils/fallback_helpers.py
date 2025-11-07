"""Fallback Chain Configuration UI Helpers - Story 8.12.

Streamlit UI components for fallback chains, triggers, and metrics (Tasks 5-8, ACs #1-8).
API helpers are in fallback_api_helpers.py to keep this under 500 lines.
"""

import asyncio
from typing import List, Dict
from datetime import datetime

import httpx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from admin.utils.provider_helpers import get_api_base, get_admin_headers
from admin.utils.fallback_api_helpers import (
    fetch_fallback_chain,
    save_fallback_chain,
    delete_fallback_chain,
    fetch_triggers,
    save_trigger,
    test_fallback,
    fetch_metrics,
)


# ============================================================================
# UI Components (Tasks 5-8, ACs #1-8)
# ============================================================================


def show_fallback_configuration_tab(providers: List[Dict]):
    """
    Display fallback chain configuration interface (AC #1, #2, #5).

    AC #1: Drag-and-drop interface to order providers (primary → fallback1 → fallback2)
    AC #2: Model-specific fallbacks (configure per model)
    AC #5: Fallback status displayed (active provider, history)
    """
    st.markdown("### Configure Fallback Chains (AC #1, #2, #5)")
    st.markdown(
        "Set up automatic fallback to backup providers when primary fails. "
        "Fallbacks are tried in order until one succeeds."
    )

    if not providers or all(not p.get("enabled") for p in providers):
        st.warning("⚠️ No enabled providers available. Create and enable providers first.")
        return

    # Collect all models from enabled providers
    all_models = {}
    enabled_providers = [p for p in providers if p.get("enabled")]

    for provider in enabled_providers:
        async def fetch_models():
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{get_api_base()}/api/llm-providers/{provider['id']}/models",
                    headers=get_admin_headers(),
                )
                return response.json() if response.status_code == 200 else []

        try:
            models = asyncio.run(fetch_models())
            for model in models:
                if model.get("enabled"):
                    model_id = model["id"]
                    model_name = model.get("display_name", model["model_name"])
                    all_models[model_id] = {"name": model_name, "provider": provider["name"]}
        except Exception:
            pass

    if not all_models:
        st.warning("⚠️ No enabled models found across providers.")
        return

    # Model selector
    col1, col2 = st.columns(2)

    with col1:
        model_id = st.selectbox(
            "Select Primary Model",
            options=list(all_models.keys()),
            format_func=lambda mid: f"{all_models[mid]['name']} ({all_models[mid]['provider']})",
            key="primary_model_select",
        )

    # Fetch current fallback chain
    current_chain = asyncio.run(fetch_fallback_chain(model_id)) if model_id else []

    with col2:
        st.metric("Current Fallbacks", len(current_chain))

    # Display current chain
    if current_chain:
        st.markdown("#### Current Fallback Chain")
        chain_display = [f"1️⃣ {all_models[model_id]['name']} (primary)"]
        for i, fallback_id in enumerate(current_chain, 1):
            if fallback_id in all_models:
                chain_display.append(f"{i+1}️⃣ {all_models[fallback_id]['name']}")
        st.write("\n".join(chain_display))
    else:
        st.info("ℹ️ No fallbacks configured for this model")

    # Fallback selection using multiselect (preserves order in Streamlit 1.30+)
    st.markdown("#### Add/Reorder Fallbacks")

    available_fallbacks = [
        mid for mid in all_models.keys() if mid != model_id
    ]

    selected_fallbacks = st.multiselect(
        "Select fallback models in order (top = tried first)",
        options=available_fallbacks,
        default=[mid for mid in available_fallbacks if mid in current_chain],
        format_func=lambda mid: f"{all_models[mid]['name']} ({all_models[mid]['provider']})",
        key="fallback_multiselect",
    )

    # Save button
    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 Save Fallback Chain", use_container_width=True, type="primary"):
            if selected_fallbacks:
                with st.spinner("Saving fallback chain..."):
                    success = asyncio.run(save_fallback_chain(model_id, selected_fallbacks))

                    if success:
                        chain_names = " → ".join([all_models[mid]["name"] for mid in selected_fallbacks])
                        st.success(f"✅ Saved! {all_models[model_id]['name']} → {chain_names}")
                        st.rerun()
                    else:
                        st.error("❌ Failed to save fallback chain")
            else:
                st.warning("⚠️ Select at least one fallback model")

    with col2:
        if st.button("🗑️ Clear Fallbacks", use_container_width=True):
            if current_chain:
                with st.spinner("Clearing fallback chain..."):
                    success = asyncio.run(delete_fallback_chain(model_id))

                    if success:
                        st.success("✅ Fallback chain cleared")
                        st.rerun()
                    else:
                        st.error("❌ Failed to clear fallback chain")

    # Display fallback status (AC #5)
    st.markdown("#### Fallback Status")

    try:
        async def fetch_model_metrics():
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{get_api_base()}/api/fallback-chains/metrics",
                    headers=get_admin_headers(),
                    params={"days": 7},
                )
                return response.json() if response.status_code == 200 else {}

        metrics_data = asyncio.run(fetch_model_metrics())
        metric_list = metrics_data.get("data", [])

        # Find metrics for selected model
        model_metrics = None
        if metric_list:
            for m in metric_list:
                # Match by model ID if available, otherwise by name
                if m.get("model_id") == model_id or m.get("model_name") == all_models[model_id]["name"]:
                    model_metrics = m
                    break

        if model_metrics:
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total Fallbacks", model_metrics.get("total_triggers", 0))

            with col2:
                total = model_metrics.get("total_triggers", 0)
                success = model_metrics.get("success_count", 0)
                rate = (success / total * 100) if total > 0 else 0
                st.metric("Success Rate", f"{rate:.1f}%")

            with col3:
                last_triggered = model_metrics.get("last_triggered_at")
                if last_triggered:
                    st.metric("Last Triggered", last_triggered[:10])
                else:
                    st.metric("Last Triggered", "Never")
        else:
            st.info("ℹ️ No fallback triggers recorded yet for this model")

    except Exception as e:
        st.warning(f"Could not load fallback status: {str(e)}")


def show_trigger_configuration_tab():
    """
    Display trigger configuration interface (AC #3, #4).

    AC #3: Fallback triggers configured for 429, 500, 503, connection failures
    AC #4: Retry before fallback with 3 attempts + exponential backoff
    """
    st.markdown("### Configure Fallback Triggers (AC #3, #4)")
    st.markdown(
        "Set retry count and exponential backoff for different error types before triggering fallback."
    )

    # Fetch current configuration
    triggers_data = asyncio.run(fetch_triggers())
    current_config = triggers_data.get("triggers", {}) if triggers_data else {}

    trigger_types = [
        ("RateLimitError", "Rate Limit (429) - API rate limit exceeded"),
        ("TimeoutError", "Timeout (503) - Request timeout"),
        ("InternalServerError", "Server Error (500, 502, 504) - Server-side failures"),
        ("ConnectionError", "Connection Error - Network/connection failures"),
    ]

    # Display current configuration
    if current_config:
        st.markdown("#### Current Configuration")
        config_df = []
        for trigger_type, config in current_config.items():
            config_df.append({
                "Error Type": trigger_type,
                "Retries": config.get("retry_count", 3),
                "Backoff": config.get("backoff_factor", 2.0),
                "Enabled": "✅" if config.get("enabled", True) else "❌",
            })

        if config_df:
            df = pd.DataFrame(config_df)
            st.dataframe(df, use_container_width=True, hide_index=True)

    # Configure each trigger type
    st.markdown("#### Update Configuration")

    col1, col2 = st.columns(2)

    with col1:
        selected_trigger = st.selectbox(
            "Select Error Type",
            options=[t[0] for t in trigger_types],
            format_func=lambda x: [f for f in trigger_types if f[0] == x][0][1],
            key="trigger_type_select",
        )

    current = current_config.get(selected_trigger, {})

    with col2:
        st.info(f"Configuring: {selected_trigger}")

    col1, col2, col3 = st.columns(3)

    with col1:
        retry_count = st.number_input(
            "Retry Count",
            min_value=0,
            max_value=10,
            value=current.get("retry_count", 3),
            step=1,
            key=f"retry_{selected_trigger}",
            help="Number of retry attempts before fallback (LiteLLM 2025 default: 3)",
        )

    with col2:
        backoff_factor = st.number_input(
            "Backoff Factor",
            min_value=1.0,
            max_value=5.0,
            value=float(current.get("backoff_factor", 2.0)),
            step=0.1,
            key=f"backoff_{selected_trigger}",
            help="Exponential backoff multiplier (LiteLLM 2025 default: 2.0)",
        )

    with col3:
        enabled = st.checkbox(
            "Enabled",
            value=current.get("enabled", True),
            key=f"enabled_{selected_trigger}",
        )

    # Show backoff timing calculation
    if retry_count > 0:
        timings = []
        total = 0
        for i in range(1, retry_count + 1):
            wait_time = backoff_factor ** (i - 1)
            timings.append(f"{wait_time:.1f}s")
            total += wait_time

        st.markdown("**Retry Timing Example:**")
        st.write(f"Retries: {', '.join(timings)}")
        st.write(f"**Total wait time before fallback: {total:.1f}s**")

    # Save button
    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 Save Trigger Configuration", use_container_width=True, type="primary"):
            with st.spinner("Saving trigger configuration..."):
                success = asyncio.run(
                    save_trigger(selected_trigger, retry_count, backoff_factor, enabled)
                )

                if success:
                    st.success(f"✅ Saved trigger configuration for {selected_trigger}")
                    st.rerun()
                else:
                    st.error("❌ Failed to save trigger configuration")

    with col2:
        if st.button("↩️  Reset All to LiteLLM 2025 Defaults", use_container_width=True):
            st.info("LiteLLM 2025 defaults: 3 retries, 2.0 backoff factor")


def show_testing_interface_tab(providers: List[Dict]):
    """
    Display fallback testing interface (AC #7).

    Allows admins to simulate failures and verify fallback chains work.
    """
    st.markdown("### Test Fallback Chains (AC #7)")
    st.markdown(
        "Simulate provider failures to verify fallback chains work correctly. "
        "No actual LLM requests are sent - responses are mocked."
    )

    if not providers or all(not p.get("enabled") for p in providers):
        st.warning("⚠️ No enabled providers available.")
        return

    # Collect all models from enabled providers
    all_models = {}
    enabled_providers = [p for p in providers if p.get("enabled")]

    for provider in enabled_providers:
        async def fetch_models():
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{get_api_base()}/api/llm-providers/{provider['id']}/models",
                    headers=get_admin_headers(),
                )
                return response.json() if response.status_code == 200 else []

        try:
            models = asyncio.run(fetch_models())
            for model in models:
                if model.get("enabled"):
                    model_id = model["id"]
                    model_name = model.get("display_name", model["model_name"])
                    all_models[model_id] = {"name": model_name, "provider": provider["name"]}
        except Exception:
            pass

    if not all_models:
        st.warning("⚠️ No enabled models found.")
        return

    # Model selector
    col1, col2 = st.columns(2)

    with col1:
        model_id = st.selectbox(
            "Select Model to Test",
            options=list(all_models.keys()),
            format_func=lambda mid: f"{all_models[mid]['name']} ({all_models[mid]['provider']})",
            key="test_model_select",
        )

    # Failure type selector
    with col2:
        failure_type = st.selectbox(
            "Simulate Failure Type",
            options=["RateLimitError", "TimeoutError", "InternalServerError", "ConnectionError"],
            format_func=lambda x: {
                "RateLimitError": "Rate Limit (429)",
                "TimeoutError": "Timeout (503)",
                "InternalServerError": "Server Error (500)",
                "ConnectionError": "Connection Failure",
            }[x],
            key="failure_type_select",
        )

    # Test message
    st.markdown("#### Test Prompt")
    test_message = st.text_area(
        "Enter test prompt/message",
        value="Test fallback chain execution",
        height=100,
        key="test_message_area",
    )

    # Run test button
    if st.button("🧪 Run Fallback Test", use_container_width=True, type="primary"):
        with st.spinner(f"Testing fallback chain for {all_models[model_id]['name']}..."):
            result = asyncio.run(test_fallback(model_id, failure_type, test_message))

            if result:
                st.success("✅ Fallback test completed!")

                # Display test results metrics
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric(
                        "Primary Status",
                        "❌ Failed" if result.get("primary_failed") else "✅ Success",
                    )

                with col2:
                    st.metric(
                        "Fallback Status",
                        "✅ Triggered" if result.get("fallback_triggered") else "❌ Not Triggered",
                    )

                with col3:
                    st.metric(
                        "Final Result",
                        "✅ Success" if result.get("success") else "❌ Failed",
                    )

                # Display retry/fallback sequence
                if result.get("attempts"):
                    st.markdown("#### Retry Sequence")

                    for idx, attempt in enumerate(result["attempts"], 1):
                        status_icon = "✅" if attempt.get("success") else "❌"
                        model_name = attempt.get("model_name", "Unknown")
                        time_ms = attempt.get("response_time_ms", attempt.get("time_ms", 0))

                        with st.expander(
                            f"{status_icon} Attempt {idx}: {model_name} ({time_ms}ms)",
                            expanded=(idx == 1),
                        ):
                            col1, col2 = st.columns(2)

                            with col1:
                                st.write(f"**Model:** {model_name}")
                                st.write(f"**Status:** {attempt.get('status', 'Unknown')}")

                            with col2:
                                st.write(f"**Time:** {time_ms}ms")
                                if attempt.get("error"):
                                    st.write(f"**Error:** {attempt.get('error')}")

                    # Summary
                    total_time = sum(a.get("response_time_ms", a.get("time_ms", 0)) for a in result.get("attempts", []))
                    st.markdown("#### Test Summary")

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("Total Attempts", len(result.get("attempts", [])))

                    with col2:
                        st.metric("Total Time", f"{total_time}ms")

                    with col3:
                        st.metric("Final Model", result.get("final_model_name", "Failed"))

            else:
                st.error("❌ Test failed - could not complete fallback test")


def show_metrics_dashboard_tab():
    """
    Display fallback metrics dashboard (AC #8).

    Shows fallback performance metrics with Plotly charts and CSV export.
    """
    st.markdown("### Fallback Metrics Dashboard (AC #8)")
    st.markdown("Track fallback chain performance, trigger statistics, and success rates.")

    col1, col2 = st.columns(2)

    with col1:
        days = st.selectbox(
            "Time Range",
            options=[1, 7, 30],
            format_func=lambda x: {1: "Last 24 Hours", 7: "Last 7 Days", 30: "Last 30 Days"}[x],
            key="metrics_time_range",
        )

    # Fetch metrics
    metrics_data = asyncio.run(fetch_metrics(days=days))

    if not metrics_data or not metrics_data.get("data"):
        st.info("📊 No fallback metrics recorded yet. Configure and use fallback chains to see data.")
        return

    # Build DataFrame
    metrics_list = metrics_data.get("data", [])
    df_metrics = []

    for metric in metrics_list:
        total = metric.get("total_triggers", 0)
        success = metric.get("success_count", 0)
        success_rate = (success / total * 100) if total > 0 else 0

        df_metrics.append({
            "Model": metric.get("model_name", "Unknown"),
            "Total Triggers": total,
            "Success": success,
            "Failures": metric.get("failure_count", 0),
            "Success Rate %": success_rate,
            "Last Triggered": metric.get("last_triggered_at", "Never")[:10],
        })

    df = pd.DataFrame(df_metrics)

    # Summary metrics
    st.markdown("#### Summary Statistics")
    col1, col2, col3, col4 = st.columns(4)

    total_triggers = df["Total Triggers"].sum()
    total_success = df["Success"].sum()
    overall_rate = (total_success / total_triggers * 100) if total_triggers > 0 else 0

    with col1:
        st.metric("Total Fallback Triggers", int(total_triggers))

    with col2:
        st.metric("Overall Success Rate", f"{overall_rate:.1f}%")

    with col3:
        st.metric("Successful Fallbacks", int(total_success))

    with col4:
        st.metric("Models Tracked", len(df))

    # Detailed metrics table
    st.markdown("#### Per-Model Metrics")
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Plotly Charts
    st.markdown("#### Visualizations")

    # Chart 1: Fallback Trigger Count by Model
    if len(df) > 0:
        fig1 = go.Figure(
            data=[
                go.Bar(
                    x=df["Model"],
                    y=df["Total Triggers"],
                    marker_color="rgba(99, 110, 250, 0.8)",
                    name="Trigger Count",
                )
            ]
        )
        fig1.update_layout(
            title="Fallback Trigger Count by Model",
            xaxis_title="Model",
            yaxis_title="Number of Triggers",
            height=400,
            showlegend=False,
        )
        st.plotly_chart(fig1, use_container_width=True)

    # Chart 2: Success Rate by Model
    if len(df) > 0:
        fig2 = go.Figure(
            data=[
                go.Bar(
                    x=df["Model"],
                    y=df["Success Rate %"],
                    marker_color="rgba(0, 204, 102, 0.8)",
                    name="Success Rate",
                )
            ]
        )
        fig2.update_layout(
            title="Success Rate by Model (%)",
            xaxis_title="Model",
            yaxis_title="Success Rate (%)",
            height=400,
            showlegend=False,
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Chart 3: Success vs Failures
    if len(df) > 0:
        fig3 = go.Figure(
            data=[
                go.Bar(name="Success", x=df["Model"], y=df["Success"], marker_color="rgba(0, 200, 100, 0.8)"),
                go.Bar(
                    name="Failures",
                    x=df["Model"],
                    y=df["Failures"],
                    marker_color="rgba(255, 100, 100, 0.8)",
                ),
            ]
        )
        fig3.update_layout(
            title="Success vs Failure by Model",
            xaxis_title="Model",
            yaxis_title="Count",
            barmode="group",
            height=400,
        )
        st.plotly_chart(fig3, use_container_width=True)

    # CSV Export
    st.markdown("#### Export Data")
    csv_data = df.to_csv(index=False)

    st.download_button(
        label="📥 Download Metrics as CSV",
        data=csv_data,
        file_name=f"fallback_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True,
    )
