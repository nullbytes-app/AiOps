"""Fallback Chain API Helper Functions - Story 8.12.

Low-level async API functions for communicating with fallback chain endpoints.
Separated to keep fallback_helpers.py under 500 lines.
"""

import asyncio
from typing import Optional, List, Dict

import httpx

from admin.utils.provider_helpers import get_api_base, get_admin_headers


async def fetch_fallback_chain(model_id: int) -> List[int]:
    """Fetch configured fallback chain for a model."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{get_api_base()}/api/fallback-chains/models/{model_id}/chain",
                headers=get_admin_headers(),
            )
            if response.status_code == 200:
                return response.json()
            return []
    except Exception:
        return []


async def save_fallback_chain(
    model_id: int,
    fallback_model_ids: List[int],
) -> bool:
    """Save fallback chain configuration."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{get_api_base()}/api/fallback-chains/models/{model_id}/chain",
                json={"fallback_model_ids": fallback_model_ids},
                headers=get_admin_headers(),
            )
            return response.status_code == 201
    except Exception:
        return False


async def delete_fallback_chain(model_id: int) -> bool:
    """Delete fallback chain for a model."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(
                f"{get_api_base()}/api/fallback-chains/models/{model_id}/chain",
                headers=get_admin_headers(),
            )
            return response.status_code == 204
    except Exception:
        return False


async def fetch_triggers() -> Dict:
    """Fetch current trigger configuration."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{get_api_base()}/api/fallback-chains/triggers",
                headers=get_admin_headers(),
            )
            if response.status_code == 200:
                return response.json()
            return {}
    except Exception:
        return {}


async def save_trigger(
    trigger_type: str,
    retry_count: int,
    backoff_factor: float,
    enabled: bool = True,
) -> bool:
    """Save trigger configuration for a specific error type."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{get_api_base()}/api/fallback-chains/triggers",
                json={
                    "trigger_type": trigger_type,
                    "retry_count": retry_count,
                    "backoff_factor": backoff_factor,
                    "enabled": enabled,
                },
                headers=get_admin_headers(),
            )
            return response.status_code == 201
    except Exception:
        return False


async def test_fallback(
    model_id: int,
    failure_type: str,
    test_message: str,
) -> Optional[Dict]:
    """Test fallback chain with simulated failure."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{get_api_base()}/api/fallback-chains/models/{model_id}/test",
                json={
                    "failure_type": failure_type,
                    "test_message": test_message,
                },
                headers=get_admin_headers(),
            )
            if response.status_code == 200:
                return response.json()
            return None
    except Exception:
        return None


async def fetch_metrics(days: int = 7) -> Dict:
    """Fetch fallback metrics."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{get_api_base()}/api/fallback-chains/metrics",
                headers=get_admin_headers(),
                params={"days": days},
            )
            if response.status_code == 200:
                return response.json()
            return {}
    except Exception:
        return {}
