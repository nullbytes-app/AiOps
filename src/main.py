"""
Main FastAPI application entry point.

This module initializes the FastAPI application and will include
routers, middleware, and startup/shutdown event handlers in future stories.

OpenTelemetry distributed tracing is initialized before app creation
to capture all requests automatically via FastAPIInstrumentor.
"""

import logging

from fastapi import FastAPI, HTTPException, status
from prometheus_client import make_asgi_app

from src.api import health, webhooks, feedback, plugins, agents, prompts
from src.api.admin import tenants as admin_tenants
from src.config import is_kubernetes_env, settings
from src.cache.redis_client import check_redis_connection
from src.database.connection import check_database_connection
from src.utils.secrets import validate_secrets_at_startup

# Story 4.6: OpenTelemetry distributed tracing initialization
# Initialize tracer provider BEFORE creating FastAPI app
# This ensures all HTTP requests are automatically instrumented
from src.monitoring import get_tracer, init_tracer_provider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Initialize OpenTelemetry tracing infrastructure
init_tracer_provider()

logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="AI Agents",
    description="Multi-tenant AI enhancement platform for MSP technicians",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Story 4.6: Instrument FastAPI with OpenTelemetry
# Automatically creates spans for all HTTP requests with route, method, status_code
FastAPIInstrumentor.instrument_app(app)

# Register routers
app.include_router(webhooks.router)
app.include_router(health.router)
app.include_router(admin_tenants.router)  # Admin tenant management endpoints
app.include_router(feedback.router)  # Story 5.5: Enhancement feedback endpoints
app.include_router(plugins.router)  # Story 7.8: Plugin management endpoints
app.include_router(agents.router)  # Story 8.3: Agent CRUD API endpoints
app.include_router(prompts.router)  # Story 8.5: Prompt versioning and template management

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
    before the application accepts requests. Registers plugins with PluginManager
    for multi-tool support (Story 7.3).

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

    # Story 7.3: Register ServiceDesk Plus plugin
    try:
        from src.plugins import PluginManager
        from src.plugins.servicedesk_plus import ServiceDeskPlusPlugin

        manager = PluginManager()
        plugin = ServiceDeskPlusPlugin()
        manager.register_plugin("servicedesk_plus", plugin)
        logger.info("ServiceDesk Plus plugin registered successfully")
    except Exception as e:
        logger.error(f"Failed to register ServiceDesk Plus plugin: {str(e)}", exc_info=True)
        raise

    # Story 7.4: Register Jira Service Management plugin
    try:
        from src.plugins.jira import JiraServiceManagementPlugin

        jira_plugin = JiraServiceManagementPlugin()
        manager.register_plugin("jira", jira_plugin)
        logger.info("Jira Service Management plugin registered successfully")
    except Exception as e:
        logger.error(f"Failed to register Jira plugin: {str(e)}", exc_info=True)
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
