# Dockerfile for Streamlit Admin UI
# Based on Python 3.12 slim image for lightweight admin interface
# Follows 2025 Docker best practices: multi-stage build, non-root user, minimal layers

FROM python:3.12-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy project files and install dependencies
COPY pyproject.toml /tmp/
COPY src/ /tmp/src/
WORKDIR /tmp
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Runtime stage
FROM python:3.12-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser src/ /app/src/
COPY --chown=appuser:appuser .streamlit/ /home/appuser/.streamlit/

# Switch to non-root user
USER appuser

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

# Set Python path (both /app and /app/src for admin.* and src.* imports)
ENV PYTHONPATH=/app:/app/src

# Run Streamlit app
CMD ["streamlit", "run", "src/admin/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
