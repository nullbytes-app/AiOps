# Multi-stage Dockerfile for FastAPI application
# Stage 1: Builder - Install dependencies
FROM python:3.12-slim AS builder

# Install system dependencies required for building Python packages
# Also install Node.js for MCP stdio servers (npx)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files and source for build
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install Python dependencies (including dev dependencies for testing)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ".[dev]"

# Stage 2: Final - Runtime image
FROM python:3.12-slim

# Install runtime dependencies only
# Include Node.js for MCP stdio servers (npx command)
# Include Docker CLI for stdio MCP servers that use docker containers
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    gnupg \
    ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
# Add to docker group (GID 999 is typical, but will use host's docker group via socket)
RUN groupadd -r aiagents && useradd -r -g aiagents aiagents \
    && groupadd -f docker \
    && usermod -aG docker aiagents

# Set working directory
WORKDIR /app

# Copy installed dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=aiagents:aiagents . .

# Copy and set permissions for entrypoint script
COPY --chown=aiagents:aiagents docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Install postgresql-client for pg_isready and psql in entrypoint
USER root
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/*
USER aiagents

# Expose FastAPI port
EXPOSE 8000

# Use entrypoint script that runs migrations before starting app
# Can be overridden in docker-compose or k8s
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["--reload"]
