"""
Main FastAPI application entry point.

This module initializes the FastAPI application and will include
routers, middleware, and startup/shutdown event handlers in future stories.
"""

from fastapi import FastAPI

from src.config import settings

# Initialize FastAPI application
app = FastAPI(
    title="AI Agents",
    description="Multi-tenant AI enhancement platform for MSP technicians",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


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
async def health() -> dict[str, str]:
    """
    Health check endpoint.

    Returns:
        dict: Health status
    """
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower(),
    )
