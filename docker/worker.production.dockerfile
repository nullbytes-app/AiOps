# Production Dockerfile for Celery Worker
# Story 5.2: Deploy Application to Production Environment
# Shares application code with API but runs Celery worker command

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
COPY pyproject.toml README.md ./

# Install Python dependencies (production only)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Stage 2: Final - Production runtime image
FROM python:3.12-slim

# Install runtime dependencies only
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

# Copy application code
COPY --chown=aiagents:aiagents src/ ./src/
COPY --chown=aiagents:aiagents alembic.ini ./
COPY --chown=aiagents:aiagents alembic/ ./alembic/

# Create directories for temporary files and Celery runtime
RUN mkdir -p /tmp /app/.cache /var/run/celery && \
    chown -R aiagents:aiagents /tmp /app/.cache /var/run/celery

# Switch to non-root user
USER aiagents

# Expose metrics port
EXPOSE 9090

# Health check: Verify Celery worker is responsive
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD celery -A src.workers.celery_app inspect ping -d celery@$(hostname) || exit 1

# Production command: Celery worker with production settings
# --loglevel=info: Production logging
# --concurrency=4: 4 concurrent tasks per worker (matches ConfigMap)
# --max-tasks-per-child=100: Restart worker after 100 tasks (prevent memory leaks)
# --time-limit=120: Hard timeout for tasks
# --soft-time-limit=110: Soft timeout (allows graceful cleanup)
CMD ["celery", "-A", "src.workers.celery_app", "worker", \
     "--loglevel=info", \
     "--concurrency=4", \
     "--max-tasks-per-child=100", \
     "--time-limit=120", \
     "--soft-time-limit=110"]

# Build command example:
# docker build -f docker/worker.production.dockerfile -t ai-agents-worker:v1.0.0 .
#
# Tag for registry:
# docker tag ai-agents-worker:v1.0.0 <registry>/ai-agents-worker:v1.0.0
# docker tag ai-agents-worker:v1.0.0 <registry>/ai-agents-worker:latest
#
# Push to registry:
# docker push <registry>/ai-agents-worker:v1.0.0
# docker push <registry>/ai-agents-worker:latest
