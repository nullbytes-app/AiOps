"""
BYOK (Bring Your Own Key) API Helper Functions - Story 8.13.

Async API functions for BYOK operations to keep byok_helpers.py under 500 lines.
Follows the pattern from fallback_api_helpers.py.
"""

import httpx
from typing import Dict, Optional


async def get_api_base() -> str:
    """Get API base URL from environment or settings."""
    import streamlit as st

    if "api_base" in st.session_state:
        return st.session_state.api_base
    return "http://localhost:8000"


async def get_admin_headers() -> Dict[str, str]:
    """Get admin headers for API requests."""
    import streamlit as st

    admin_key = st.session_state.get("admin_key", "")
    return {"X-Admin-Key": admin_key}


async def test_provider_keys(
    tenant_id: str, openai_key: Optional[str], anthropic_key: Optional[str]
) -> Dict:
    """
    Test provider API keys via /byok/test-keys endpoint (AC#3).

    Args:
        tenant_id: Tenant identifier
        openai_key: OpenAI API key (optional)
        anthropic_key: Anthropic API key (optional)

    Returns:
        dict: Validation results with model lists
    """
    api_base = await get_api_base()
    headers = await get_admin_headers()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{api_base}/api/tenants/{tenant_id}/byok/test-keys",
            headers=headers,
            json={
                "openai_key": openai_key,
                "anthropic_key": anthropic_key,
            },
        )

        if response.status_code == 200:
            return response.json()
        else:
            return {
                "openai": {"valid": False, "models": [], "error": response.text},
                "anthropic": {"valid": False, "models": [], "error": response.text},
            }


async def enable_byok(
    tenant_id: str, openai_key: Optional[str], anthropic_key: Optional[str]
) -> Dict:
    """
    Enable BYOK mode for tenant (AC#1-4).

    Args:
        tenant_id: Tenant identifier
        openai_key: OpenAI API key (optional)
        anthropic_key: Anthropic API key (optional)

    Returns:
        dict: Success response with virtual key info
    """
    api_base = await get_api_base()
    headers = await get_admin_headers()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{api_base}/api/tenants/{tenant_id}/byok/enable",
            headers=headers,
            json={
                "openai_key": openai_key,
                "anthropic_key": anthropic_key,
            },
        )

        if response.status_code == 201:
            return response.json()
        else:
            raise Exception(f"Failed to enable BYOK: {response.text}")


async def get_byok_status(tenant_id: str) -> Dict:
    """
    Get BYOK status for tenant (AC#6).

    Args:
        tenant_id: Tenant identifier

    Returns:
        dict: BYOK status with enabled flag, providers, timestamp
    """
    api_base = await get_api_base()
    headers = await get_admin_headers()

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{api_base}/api/tenants/{tenant_id}/byok/status",
            headers=headers,
        )

        if response.status_code == 200:
            return response.json()
        else:
            return {
                "byok_enabled": False,
                "providers_configured": [],
                "enabled_at": None,
                "cost_tracking_mode": "platform",
            }


async def rotate_byok_keys(
    tenant_id: str, new_openai_key: Optional[str], new_anthropic_key: Optional[str]
) -> Dict:
    """
    Rotate BYOK tenant's provider keys (AC#7).

    Args:
        tenant_id: Tenant identifier
        new_openai_key: New OpenAI API key (optional)
        new_anthropic_key: New Anthropic API key (optional)

    Returns:
        dict: Success response with new key info
    """
    api_base = await get_api_base()
    headers = await get_admin_headers()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.put(
            f"{api_base}/api/tenants/{tenant_id}/byok/rotate-keys",
            headers=headers,
            json={
                "new_openai_key": new_openai_key,
                "new_anthropic_key": new_anthropic_key,
            },
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to rotate BYOK keys: {response.text}")


async def disable_byok(tenant_id: str) -> Dict:
    """
    Disable BYOK and revert to platform keys (AC#8).

    Args:
        tenant_id: Tenant identifier

    Returns:
        dict: Success response
    """
    api_base = await get_api_base()
    headers = await get_admin_headers()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{api_base}/api/tenants/{tenant_id}/byok/disable",
            headers=headers,
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to disable BYOK: {response.text}")
