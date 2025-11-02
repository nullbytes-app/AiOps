# Multi-stage Dockerfile for FastAPI application
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

# Copy dependency files and source for build
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install Python dependencies (including dev dependencies for testing)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ".[dev]"

# Stage 2: Final - Runtime image
FROM python:3.12-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r aiagents && useradd -r -g aiagents aiagents

# Set working directory
WORKDIR /app

# Copy installed dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=aiagents:aiagents . .

# Switch to non-root user
USER aiagents

# Expose FastAPI port
EXPOSE 8000

# Default command: Run uvicorn with hot-reload for development
# Can be overridden in docker-compose or k8s
ENTRYPOINT ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["--reload"]
