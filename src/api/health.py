"""
Health check API endpoints.

This module provides health check endpoints for monitoring and
load balancer health probes. Enhanced in Story 1.2 to check dependencies.
"""

from fastapi import APIRouter, HTTPException, status
from src.cache.redis_client import get_redis_client, check_redis_connection
from src.database.connection import check_database_connection

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str | dict]:
    """
    Health check endpoint for monitoring.

    Validates connectivity to PostgreSQL and Redis dependencies.
    Used by Docker health checks and load balancers.

    Returns:
        dict: Health status with dependency checks

    Raises:
        HTTPException: If any dependency is unhealthy
    """
    health_status = {
        "status": "healthy",
        "service": "AI Agents",
        "dependencies": {"database": "unknown", "redis": "unknown"},
    }

    # Check database connectivity
    try:
        db_healthy = await check_database_connection()
        health_status["dependencies"]["database"] = (
            "healthy" if db_healthy else "unhealthy"
        )
    except Exception as e:
        health_status["dependencies"]["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"

    # Check Redis connectivity
    try:
        if await check_redis_connection():
            health_status["dependencies"]["redis"] = "healthy"
        else:
            health_status["dependencies"]["redis"] = "unhealthy"
            health_status["status"] = "unhealthy"
    except Exception as e:
        health_status["dependencies"]["redis"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"

    # Return error status if any dependency is unhealthy
    if health_status["status"] == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_status,
        )

    return health_status


@router.get("/ready")
async def readiness_check() -> dict[str, str | dict]:
    """
    Readiness check endpoint for Kubernetes.

    Checks if the application is ready to accept traffic by validating
    all critical dependencies (database and Redis).

    Returns:
        dict: Readiness status with dependency checks

    Raises:
        HTTPException: If service is not ready
    """
    readiness_status = {
        "status": "ready",
        "dependencies": {"database": "unknown", "redis": "unknown"},
    }

    # Check database readiness
    try:
        db_ready = await check_database_connection()
        readiness_status["dependencies"]["database"] = (
            "ready" if db_ready else "not ready"
        )
        if not db_ready:
            readiness_status["status"] = "not ready"
    except Exception as e:
        readiness_status["dependencies"]["database"] = f"error: {str(e)}"
        readiness_status["status"] = "not ready"

    # Check Redis readiness
    try:
        if await check_redis_connection():
            readiness_status["dependencies"]["redis"] = "ready"
        else:
            readiness_status["dependencies"]["redis"] = "not ready"
            readiness_status["status"] = "not ready"
    except Exception as e:
        readiness_status["dependencies"]["redis"] = f"error: {str(e)}"
        readiness_status["status"] = "not ready"

    # Return not ready status if dependencies aren't ready
    if readiness_status["status"] == "not ready":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=readiness_status,
        )

    return readiness_status
