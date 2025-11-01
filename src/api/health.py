"""
Health check API endpoints.

This module provides health check endpoints for monitoring and
load balancer health probes. Will be expanded in Story 1.2.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """
    Health check endpoint for monitoring.

    Returns:
        dict: Health status
    """
    return {"status": "healthy", "service": "AI Agents"}


@router.get("/ready")
async def readiness_check() -> dict[str, str]:
    """
    Readiness check endpoint for Kubernetes.

    Will be expanded in future stories to check database and Redis connectivity.

    Returns:
        dict: Readiness status
    """
    return {"status": "ready"}
