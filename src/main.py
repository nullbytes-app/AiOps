"""
Main FastAPI application entry point.

This module initializes the FastAPI application and will include
routers, middleware, and startup/shutdown event handlers in future stories.
"""

import logging

from fastapi import FastAPI, HTTPException, status
from prometheus_client import make_asgi_app

from src.api import health, webhooks
from src.api.admin import tenants as admin_tenants
from src.config import is_kubernetes_env, settings
from src.cache.redis_client import check_redis_connection
from src.database.connection import check_database_connection
from src.utils.secrets import validate_secrets_at_startup

logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="AI Agents",
    description="Multi-tenant AI enhancement platform for MSP technicians",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Register routers
app.include_router(webhooks.router)
app.include_router(health.router)
app.include_router(admin_tenants.router)  # Admin tenant management endpoints

# Mount Prometheus metrics endpoint at /metrics
# Returns metrics in Prometheus text format (text/plain; version=0.0.4)
# Public endpoint - no authentication required for Prometheus scraping
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.on_event("startup")
async def startup_event() -> None:
    """
    Application startup event handler.

    Validates that all required secrets are present and properly formatted
    before the application accepts requests.

    Raises:
        EnvironmentError: If required secrets are missing or invalid
    """
    try:
        await validate_secrets_at_startup()
        env_type = "Kubernetes" if is_kubernetes_env() else "local development"
        logger.info(f"Secrets validated successfully. Running in {env_type} environment")
    except EnvironmentError as e:
        logger.error(f"Secrets validation failed: {str(e)}")
        raise


@app.get("/")
async def root() -> dict[str, str]:
    """
    Root endpoint for basic health check.

    Returns:
        dict: Simple status message
    """
    return {
        "status": "ok",
        "service": "AI Agents",
        "environment": settings.environment,
    }


@app.get("/health")
async def health() -> dict[str, str | dict]:
    """
    Health check endpoint for Docker and load balancers.

    Validates connectivity to PostgreSQL and Redis dependencies.
    Returns 503 if any dependency is unhealthy.

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
        if not db_healthy:
            health_status["status"] = "unhealthy"
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",  # nosec B104 - Required for Docker/Kubernetes deployments
        port=8000,
        reload=True,
        log_level=settings.log_level.lower(),
    )
