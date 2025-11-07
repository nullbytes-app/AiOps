"""
Helper utilities for LLM Provider management in Streamlit admin UI.

Provides reusable functions for API calls, status indicators, and data formatting.
Reduces code duplication across provider-related admin pages.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

import httpx
import streamlit as st


# ============================================================================
# Status and Formatting Helpers
# ============================================================================


def get_status_indicator(last_test_at: Optional[datetime], last_test_success: Optional[bool]) -> str:
    """
    Get status emoji based on last test timestamp and result.

    Args:
        last_test_at: Timestamp of last connection test
        last_test_success: Result of last connection test

    Returns:
        Status string with emoji indicator
    """
    if last_test_at is None:
        return "⚪ Never Tested"

    if not last_test_success:
        return "🔴 Disconnected"

    time_since_test = datetime.now() - last_test_at.replace(tzinfo=None)

    if time_since_test < timedelta(minutes=5):
        return "🟢 Connected"
    elif time_since_test < timedelta(hours=1):
        return "🟡 Warning"
    else:
        return "🔴 Disconnected"


def mask_api_key(api_key: str) -> str:
    """
    Mask API key to show only first 3 and last 3 characters.

    Args:
        api_key: Full API key

    Returns:
        Masked API key string (e.g., "sk-...xyz")
    """
    if not api_key or len(api_key) < 7:
        return "***"

    return f"{api_key[:3]}...{api_key[-3:]}"


def get_api_base() -> str:
    """Get API base URL from environment or default."""
    return os.getenv("API_BASE_URL", "http://localhost:8000")


def get_admin_headers() -> dict:
    """Get admin authentication headers."""
    return {"X-Admin-Key": os.getenv("ADMIN_API_KEY", "")}


# ============================================================================
# API Call Functions
# ============================================================================


async def fetch_providers():
    """
    Fetch all LLM providers from API.

    Returns:
        List of provider dictionaries or empty list on error
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{get_api_base()}/api/llm-providers",
                headers=get_admin_headers(),
            )
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"Failed to fetch providers: {response.status_code}")
                return []
    except Exception as e:
        st.error(f"Error fetching providers: {str(e)}")
        return []


async def create_provider_api(name: str, provider_type: str, api_base_url: str, api_key: str):
    """
    Create new provider via API.

    Args:
        name: Provider name
        provider_type: Provider type (openai, anthropic, etc.)
        api_base_url: Provider API base URL
        api_key: Provider API key (will be encrypted)

    Returns:
        Response dictionary or None on error
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{get_api_base()}/api/llm-providers",
                headers=get_admin_headers(),
                json={
                    "name": name,
                    "provider_type": provider_type,
                    "api_base_url": api_base_url,
                    "api_key": api_key,
                },
            )
            if response.status_code == 201:
                return response.json()
            else:
                st.error(f"Failed to create provider: {response.text}")
                return None
    except Exception as e:
        st.error(f"Error creating provider: {str(e)}")
        return None


async def test_connection_api(provider_id: int):
    """
    Test provider connection via API.

    Args:
        provider_id: Provider database ID

    Returns:
        Test result dictionary or None on error
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{get_api_base()}/api/llm-providers/{provider_id}/test-connection",
                headers=get_admin_headers(),
            )
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"Connection test failed: {response.text}")
                return None
    except Exception as e:
        st.error(f"Error testing connection: {str(e)}")
        return None


async def delete_provider_api(provider_id: int):
    """
    Delete provider via API (soft delete).

    Args:
        provider_id: Provider database ID

    Returns:
        True on success, False on error
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(
                f"{get_api_base()}/api/llm-providers/{provider_id}",
                headers=get_admin_headers(),
            )
            if response.status_code == 204:
                return True
            else:
                st.error(f"Failed to delete provider: {response.text}")
                return False
    except Exception as e:
        st.error(f"Error deleting provider: {str(e)}")
        return False


async def regenerate_config_api():
    """
    Regenerate litellm-config.yaml via API.

    Returns:
        Result dictionary or None on error
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{get_api_base()}/api/llm-providers/regenerate-config",
                headers=get_admin_headers(),
            )
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"Failed to regenerate config: {response.text}")
                return None
    except Exception as e:
        st.error(f"Error regenerating config: {str(e)}")
        return None


# ============================================================================
# Model Management Helpers (AC #5)
# ============================================================================


def edit_model_form(model: dict):
    """
    Inline form for editing model configuration (AC #5).

    Args:
        model: Model dictionary with current values
    """
    st.markdown("##### Edit Model Configuration")

    with st.form(key=f"edit_form_{model['id']}"):
        display_name = st.text_input(
            "Display Name",
            value=model.get("display_name", model["model_name"]),
            help="Human-readable name for this model"
        )

        col1, col2 = st.columns(2)

        with col1:
            cost_input = st.number_input(
                "Cost per 1K Input Tokens ($)",
                min_value=0.0,
                max_value=1000.0,
                value=float(model.get("cost_per_input_token") or 0.0),
                step=0.000001,
                format="%.6f",
                help="Cost in dollars per 1000 input tokens"
            )

        with col2:
            cost_output = st.number_input(
                "Cost per 1K Output Tokens ($)",
                min_value=0.0,
                max_value=1000.0,
                value=float(model.get("cost_per_output_token") or 0.0),
                step=0.000001,
                format="%.6f",
                help="Cost in dollars per 1000 output tokens"
            )

        context_window = st.number_input(
            "Context Window (tokens)",
            min_value=0,
            max_value=2000000,
            value=model.get("context_window") or 0,
            step=1000,
            help="Maximum context window size in tokens"
        )

        capabilities = st.text_area(
            "Capabilities (JSON)",
            value=model.get("capabilities", "{}"),
            height=100,
            help="JSON object describing model capabilities (e.g., vision, function calling)"
        )

        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("💾 Save Changes", use_container_width=True)
        with col2:
            cancel = st.form_submit_button("❌ Cancel", use_container_width=True)

    if cancel:
        st.rerun()

    if submit:
        # Update model via API
        import asyncio
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.put(
                f"{get_api_base()}/api/llm-models/{model['id']}",
                headers=get_admin_headers(),
                json={
                    "display_name": display_name,
                    "cost_per_input_token": cost_input if cost_input > 0 else None,
                    "cost_per_output_token": cost_output if cost_output > 0 else None,
                    "context_window": context_window if context_window > 0 else None,
                    "capabilities": capabilities if capabilities.strip() else None,
                },
            )

            if response.status_code == 200:
                st.success("✅ Model configuration updated successfully!")
                st.rerun()
            else:
                st.error(f"Failed to update model: {response.text}")
