"""
Health check API endpoints.

This module provides health check endpoints for monitoring and
load balancer health probes. Enhanced in Story 1.2 to check dependencies.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.cache.redis_client import get_redis_client, check_redis_connection
from src.database.connection import check_database_connection
from src.database.session import get_async_session
from src.services.llm_service import LLMService
from src.utils.exceptions import TenantNotFoundException
from loguru import logger

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint for monitoring dashboard.

    Validates connectivity to PostgreSQL and Redis dependencies.
    Returns detailed component health status for API, Workers, Database, and Redis.
    Used by Docker health checks, load balancers, and dashboard monitoring.

    Returns:
        dict: Detailed health status for all components with timestamp

    Raises:
        HTTPException: If any critical dependency is unhealthy
    """
    from datetime import datetime, timezone

    # Initialize component health structure
    health_status = {
        "api": {"status": "healthy", "response_time_ms": 0},
        "workers": {"status": "healthy", "details": {"note": "Worker health check via Celery inspect not implemented"}},
        "database": {"status": "unknown"},
        "redis": {"status": "unknown"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Check database connectivity
    try:
        db_healthy = await check_database_connection()
        health_status["database"]["status"] = "healthy" if db_healthy else "down"
    except Exception as e:
        health_status["database"]["status"] = "down"
        health_status["database"]["details"] = {"error": str(e)}
        logger.error(f"Database health check failed: {e}")

    # Check Redis connectivity
    try:
        redis_healthy = await check_redis_connection()
        health_status["redis"]["status"] = "healthy" if redis_healthy else "down"
    except Exception as e:
        health_status["redis"]["status"] = "down"
        health_status["redis"]["details"] = {"error": str(e)}
        logger.error(f"Redis health check failed: {e}")

    # Determine if any critical component is down
    critical_down = any(
        health_status[comp]["status"] == "down"
        for comp in ["database", "redis"]
    )

    # Return error status if any critical dependency is down
    if critical_down:
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


@router.get("/health/litellm")
async def litellm_health_check(db: AsyncSession = Depends(get_async_session)) -> dict:
    """
    LiteLLM proxy health check endpoint (Story 8.9).

    Tests connectivity to LiteLLM proxy and validates master key.
    Used for monitoring LiteLLM integration health.

    Args:
        db: Database session for LLMService initialization

    Returns:
        dict: LiteLLM health status with proxy and master key validation

    Raises:
        HTTPException(503): If LiteLLM proxy is unavailable or master key invalid
    """
    health_status = {
        "status": "healthy",
        "proxy": "unknown",
        "master_key": "unknown",
    }

    try:
        llm_service = LLMService(db=db)

        # Test LiteLLM proxy connectivity with master key
        # Call /user/info as simple authenticated test (requires master key)
        try:
            await llm_service._call_litellm_api(
                method="GET",
                endpoint="/user/info",
                retry=False,  # Single attempt for health check
            )
            health_status["proxy"] = "connected"
            health_status["master_key"] = "valid"

        except Exception as e:
            logger.warning(f"LiteLLM health check failed: {str(e)}")
            health_status["proxy"] = "unreachable"
            health_status["master_key"] = "invalid"
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)

    except ValueError as e:
        # LiteLLM configuration missing
        health_status["status"] = "unhealthy"
        health_status["error"] = f"Configuration error: {str(e)}"

    # Return error if unhealthy
    if health_status["status"] == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_status,
        )

    return health_status


@router.get("/tenants/{tenant_id}/validate-llm-key")
async def validate_tenant_llm_key(
    tenant_id: str, db: AsyncSession = Depends(get_async_session)
) -> dict:
    """
    Validate tenant's LiteLLM virtual key (Story 8.9).

    Tests if tenant's virtual key is valid and not expired/blocked.
    Used for troubleshooting tenant LLM integration issues.

    Args:
        tenant_id: Tenant identifier
        db: Database session

    Returns:
        dict: Validation result with key status

    Raises:
        HTTPException(404): If tenant not found
        HTTPException(400): If tenant has no virtual key
    """
    try:
        llm_service = LLMService(db=db)

        # Get tenant's decrypted virtual key
        try:
            client = await llm_service.get_llm_client_for_tenant(tenant_id)
            # Extract API key from AsyncOpenAI client
            virtual_key = client.api_key
        except ValueError as e:
            # Tenant not found or no virtual key
            if "not found" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tenant '{tenant_id}' not found",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Tenant '{tenant_id}' has no virtual key configured",
                )

        # Validate the virtual key
        is_valid = await llm_service.validate_virtual_key(virtual_key)

        # Log audit entry
        await llm_service.log_audit_entry(
            operation="llm_key_validated",
            tenant_id=tenant_id,
            user="system",
            details={"valid": is_valid},
            status="success",
        )

        return {
            "tenant_id": tenant_id,
            "valid": is_valid,
            "message": "Virtual key is valid" if is_valid else "Virtual key is invalid or expired",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error validating virtual key for tenant {tenant_id}: {str(e)}",
            extra={"tenant_id": tenant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate virtual key: {str(e)}",
        )
