"""
Main FastAPI application entry point.

This module initializes the FastAPI application and will include
routers, middleware, and startup/shutdown event handlers in future stories.
"""

from fastapi import FastAPI, HTTPException, status

from src.api import health, webhooks
from src.api.admin import tenants as admin_tenants
from src.config import settings
from src.cache.redis_client import check_redis_connection
from src.database.connection import check_database_connection

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
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower(),
    )
