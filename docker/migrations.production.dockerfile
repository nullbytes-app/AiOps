# Production Dockerfile for Database Migration Runner
# Story 5.2: Deploy Application to Production Environment
# Minimal image for Alembic migrations (used in init containers)

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

# Copy ONLY dependency files first
COPY pyproject.toml README.md ./

# Install minimal dependencies for migrations (Alembic, asyncpg, SQLAlchemy)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir alembic asyncpg sqlalchemy python-dotenv

# Stage 2: Final - Minimal runtime image
FROM python:3.12-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r -g 1000 aiagents && useradd -r -u 1000 -g aiagents aiagents

# Set working directory
WORKDIR /app

# Copy installed dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy ONLY migration-related files (minimal attack surface)
COPY --chown=aiagents:aiagents alembic.ini ./
COPY --chown=aiagents:aiagents alembic/ ./alembic/

# Copy minimal src code needed for models (Alembic env.py imports them)
COPY --chown=aiagents:aiagents src/__init__.py ./src/
COPY --chown=aiagents:aiagents src/config.py ./src/
COPY --chown=aiagents:aiagents src/models/ ./src/models/

# Switch to non-root user
USER aiagents

# Database health check script
RUN echo '#!/bin/sh\n\
set -e\n\
echo "Checking database connectivity..."\n\
for i in $(seq 1 30); do\n\
    if python -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect('"'"'${DATABASE_URL}'"'"'))"; then\n\
        echo "Database connection successful"\n\
        exit 0\n\
    fi\n\
    echo "Waiting for database... (attempt $i/30)"\n\
    sleep 2\n\
done\n\
echo "ERROR: Database not available after 30 attempts"\n\
exit 1\n\
' > /app/wait-for-db.sh && chmod +x /app/wait-for-db.sh

# Default command: Run migrations
# Init containers in Kubernetes will override this with health check + migration
CMD ["alembic", "upgrade", "head"]

# Usage in Kubernetes init container:
# command: ["/bin/sh", "-c"]
# args:
#   - |
#     /app/wait-for-db.sh
#     echo "Running Alembic migrations..."
#     alembic upgrade head
#     echo "Migrations complete"
#
# Build command example:
# docker build -f docker/migrations.production.dockerfile -t ai-agents-migrations:v1.0.0 .
#
# Tag for registry:
# docker tag ai-agents-migrations:v1.0.0 <registry>/ai-agents-migrations:v1.0.0
#
# Push to registry:
# docker push <registry>/ai-agents-migrations:v1.0.0
