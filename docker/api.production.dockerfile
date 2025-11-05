# Production Dockerfile for FastAPI API
# Story 5.2: Deploy Application to Production Environment
# Multi-stage build optimized for production with layer caching and security hardening
# Based on FastAPI 2025 best practices: single Uvicorn process per container

# Stage 1: Builder - Install dependencies
FROM python:3.12-slim AS builder

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy ONLY dependency files first (Docker layer caching optimization)
# This layer will be cached unless pyproject.toml changes
COPY pyproject.toml README.md ./

# Install Python dependencies (production only, no dev dependencies)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Stage 2: Final - Production runtime image
FROM python:3.12-slim

# Install runtime dependencies only (minimal surface area)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security (UID 1000 matches Kubernetes runAsUser)
RUN groupadd -r -g 1000 aiagents && useradd -r -u 1000 -g aiagents aiagents

# Set working directory
WORKDIR /app

# Copy installed dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code (changes more frequently, placed after dependencies for caching)
COPY --chown=aiagents:aiagents src/ ./src/
COPY --chown=aiagents:aiagents alembic.ini ./
COPY --chown=aiagents:aiagents alembic/ ./alembic/

# Create directories for temporary files (Kubernetes readOnlyRootFilesystem support)
RUN mkdir -p /tmp /app/.cache && \
    chown -R aiagents:aiagents /tmp /app/.cache

# Switch to non-root user
USER aiagents

# Expose ports
EXPOSE 8000 9090

# Health check (Docker-level, Kubernetes probes override this)
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command: Single Uvicorn process with proxy headers
# Exec form (not shell form) for proper signal handling and graceful shutdown
# --proxy-headers: Trust X-Forwarded-* headers from nginx ingress
# --lifespan on: Enable startup and shutdown events for database connection management
CMD ["fastapi", "run", "src/main.py", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]

# Build command example:
# docker build -f docker/api.production.dockerfile -t ai-agents-api:v1.0.0 .
#
# Tag for registry:
# docker tag ai-agents-api:v1.0.0 <registry>/ai-agents-api:v1.0.0
# docker tag ai-agents-api:v1.0.0 <registry>/ai-agents-api:latest
#
# Push to registry:
# docker push <registry>/ai-agents-api:v1.0.0
# docker push <registry>/ai-agents-api:latest
