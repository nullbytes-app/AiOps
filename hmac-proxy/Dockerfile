FROM python:3.12-slim

LABEL maintainer="AI Ops Team"
LABEL description="HMAC Webhook Proxy for Jira Integration"

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app.py .

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:3000/health', timeout=2)"

# Run application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "3000", "--log-level", "info"]
