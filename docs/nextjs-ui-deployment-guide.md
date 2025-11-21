# Next.js UI Deployment Guide

## Overview

This guide covers the deployment of the Next.js UI as part of the AI Agents platform. The UI is containerized using Docker and orchestrated with docker-compose alongside the FastAPI backend and supporting services.

## Architecture

```
┌─────────────────────────────────────────────┐
│          Nginx Reverse Proxy (Port 80)      │
│  Routes: /* → Next.js, /api/* → FastAPI     │
└─────────────┬───────────────────────────────┘
              │
      ┌───────┴───────┐
      │               │
┌─────▼─────┐   ┌────▼──────┐
│ Next.js UI│   │  FastAPI  │
│ (Port 3000│   │ (Port 8000│
└───────────┘   └─────┬─────┘
                      │
              ┌───────┴────────┐
              │                │
        ┌─────▼─────┐    ┌────▼────┐
        │ PostgreSQL│    │  Redis  │
        │(Port 5433)│    │(Port 6379
        └───────────┘    └─────────┘
```

## Prerequisites

- Docker and Docker Compose installed
- Node.js 20+ (for local development)
- At least 4GB RAM available for containers
- Ports 80, 3000, 8000, 5433, 6379 available

## Quick Start

### 1. Environment Setup

```bash
# Copy environment files
cp .env.example .env
cp nextjs-ui/.env.example nextjs-ui/.env.local

# Edit .env and set required variables
vim .env
```

**Required Environment Variables:**

```bash
# Backend Configuration
AI_AGENTS_DATABASE_URL=postgresql+asyncpg://aiagents:password@postgres:5432/ai_agents
AI_AGENTS_REDIS_URL=redis://redis:6379/0

# Next.js Configuration
NEXT_PUBLIC_API_URL=http://localhost
```

### 2. Build and Start Services

```bash
# Build all services (first time or after code changes)
docker-compose build

# Start all services
docker-compose up -d

# Check service status
docker-compose ps
```

### 3. Verify Deployment

Run the validation script:

```bash
./scripts/validate-ui-backend-integration.sh
```

Expected output:
```
==========================================
Phase 1: Service Health Checks
==========================================
[✓] Backend API is reachable
[✓] OpenAPI Documentation is reachable
[✓] Next.js Frontend is reachable

==========================================
Phase 2: API Endpoint Validation
==========================================
[✓] Agents API returns valid JSON
[✓] Tools API returns valid JSON
[✓] Prompts API returns valid JSON

==========================================
Validation Summary
==========================================
Passed: 15
Failed: 0

✓ All validation checks passed!
```

## Service URLs

After successful deployment, access services at:

| Service | URL | Description |
|---------|-----|-------------|
| **Next.js UI** | http://localhost | Main application UI (via nginx) |
| **FastAPI Backend** | http://localhost/api | Backend API (via nginx) |
| **Direct Next.js** | http://localhost:3000 | Direct access to Next.js |
| **Direct FastAPI** | http://localhost:8000 | Direct access to FastAPI |
| **API Docs** | http://localhost/docs | OpenAPI/Swagger documentation |
| **Streamlit** | http://localhost:8501 | Legacy admin UI |
| **Grafana** | http://localhost:3002 | Monitoring dashboards |
| **Prometheus** | http://localhost:9091 | Metrics collection |
| **Jaeger** | http://localhost:16686 | Distributed tracing |

## Development Workflow

### Local Development (Without Docker)

1. **Start Backend Services:**
```bash
# Start only infrastructure (postgres, redis)
docker-compose up -d postgres redis

# In one terminal: Start FastAPI
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

2. **Start Next.js Dev Server:**
```bash
# In another terminal
cd nextjs-ui
npm install
npm run dev
```

3. **Access:**
- Next.js: http://localhost:3000
- FastAPI: http://localhost:8000

### With Docker (Production-like)

```bash
# Build and start everything
docker-compose up -d --build

# View logs
docker-compose logs -f nextjs-ui

# Rebuild specific service
docker-compose up -d --build nextjs-ui
```

## Deployment Steps

### Step 1: Pre-Deployment Checks

```bash
# 1. Ensure code is up to date
git pull origin main

# 2. Check environment variables
cat .env | grep NEXT_PUBLIC_API_URL

# 3. Verify Docker resources
docker system df
docker system prune -a  # If needed
```

### Step 2: Build Images

```bash
# Build all images
docker-compose build

# Or build specific services
docker-compose build nextjs-ui nginx api
```

### Step 3: Deploy

```bash
# Stop existing containers
docker-compose down

# Start services with new images
docker-compose up -d

# Wait for services to be healthy
docker-compose ps
```

### Step 4: Smoke Tests

```bash
# Run automated validation
./scripts/validate-ui-backend-integration.sh

# Manual checks
curl http://localhost/health  # Nginx
curl http://localhost:3000/api/health  # Next.js
curl http://localhost:8000/health  # FastAPI

# Check logs for errors
docker-compose logs nextjs-ui | grep -i error
docker-compose logs api | grep -i error
docker-compose logs nginx | grep -i error
```

### Step 5: Post-Deployment Validation

**Critical User Journeys:**

1. **Authentication Flow:**
   - Navigate to http://localhost
   - Click "Login"
   - Enter credentials
   - Verify dashboard loads

2. **Agent Management:**
   - Navigate to "Agents" page
   - Verify agent list loads
   - Click on an agent
   - Verify agent details display

3. **Agent Execution:**
   - Select an agent
   - Click "Execute"
   - Enter test prompt
   - Verify response streams correctly

4. **Tool Assignment:**
   - Navigate to agent tools
   - Verify tool list loads
   - Assign/unassign a tool
   - Verify changes persist

## Troubleshooting

### Issue: Next.js Container Won't Start

**Symptoms:**
```bash
docker-compose ps
# Shows nextjs-ui as "Restarting" or "Exited"
```

**Solution:**
```bash
# Check logs
docker-compose logs nextjs-ui

# Common fixes:
# 1. Missing dependencies
docker-compose build --no-cache nextjs-ui

# 2. Environment variables
docker-compose exec nextjs-ui env | grep NEXT_PUBLIC

# 3. File permissions
sudo chown -R $(whoami) nextjs-ui/.next
```

### Issue: 502 Bad Gateway

**Symptoms:**
- Browser shows "502 Bad Gateway"
- Nginx logs show "upstream" errors

**Solution:**
```bash
# Check if backend services are healthy
docker-compose ps

# Check nginx configuration
docker-compose exec nginx nginx -t

# Restart nginx
docker-compose restart nginx

# Check service connectivity
docker-compose exec nginx ping nextjs-ui
docker-compose exec nginx ping api
```

### Issue: API Calls Failing with CORS Errors

**Symptoms:**
- Browser console shows CORS errors
- API requests return 403 or blocked

**Solution:**
```bash
# 1. Check API CORS configuration
docker-compose exec api env | grep FRONTEND_URL

# 2. Update src/main.py CORS origins
# Add: "http://localhost", "http://localhost:3000"

# 3. Rebuild and restart
docker-compose up -d --build api
```

### Issue: Static Assets Not Loading

**Symptoms:**
- Pages load but CSS/JS missing
- 404 errors for `/_next/static/*`

**Solution:**
```bash
# 1. Check Next.js build output
docker-compose exec nextjs-ui ls -la .next/static

# 2. Verify nginx configuration
docker-compose exec nginx cat /etc/nginx/nginx.conf | grep "_next/static"

# 3. Rebuild Next.js
docker-compose up -d --build nextjs-ui
```

## Monitoring

### Health Checks

```bash
# All services status
docker-compose ps

# Individual health checks
curl -f http://localhost/health || echo "Nginx failed"
curl -f http://localhost:3000/api/health || echo "Next.js failed"
curl -f http://localhost:8000/health || echo "API failed"
```

### Logs

```bash
# Follow all logs
docker-compose logs -f

# Specific service
docker-compose logs -f nextjs-ui
docker-compose logs -f nginx
docker-compose logs -f api

# Last 100 lines
docker-compose logs --tail=100 nextjs-ui

# Search logs
docker-compose logs nextjs-ui | grep -i error
docker-compose logs nginx | grep -i "upstream"
```

### Resource Usage

```bash
# Container stats
docker stats

# Service-specific
docker stats ai-ops-nextjs-ui ai-ops-nginx ai-agents-api
```

## Rollback Procedure

If deployment fails:

```bash
# 1. Stop new containers
docker-compose down

# 2. Revert to previous image
docker-compose up -d

# 3. If needed, restore from backup
# (Database migrations should be backward compatible)

# 4. Verify services
./scripts/validate-ui-backend-integration.sh
```

## Production Considerations

### Security

1. **Environment Variables:**
   - Use secrets management (AWS Secrets Manager, HashiCorp Vault)
   - Never commit `.env` files
   - Rotate secrets regularly

2. **HTTPS:**
   - Configure SSL/TLS in nginx
   - Use Let's Encrypt for certificates
   - Enforce HTTPS redirect

3. **Rate Limiting:**
   - Configure nginx rate limiting
   - Implement API rate limits
   - Add DDoS protection (Cloudflare)

### Performance

1. **Caching:**
   - Enable Redis caching
   - Configure nginx caching
   - Use CDN for static assets

2. **Scaling:**
   - Use docker-compose scale or Kubernetes
   - Implement load balancing
   - Configure auto-scaling

3. **Monitoring:**
   - Set up Prometheus alerts
   - Configure Grafana dashboards
   - Enable distributed tracing

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy Next.js UI

on:
  push:
    branches: [main]
    paths:
      - 'nextjs-ui/**'
      - 'docker-compose.yml'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build and Test
        run: |
          docker-compose build nextjs-ui
          docker-compose up -d
          ./scripts/validate-ui-backend-integration.sh

      - name: Deploy to Production
        run: |
          # Your deployment commands here
          ssh user@server 'cd /app && docker-compose up -d --build nextjs-ui'
```

## Support

For issues or questions:
- Check troubleshooting section
- Review logs: `docker-compose logs`
- Run validation: `./scripts/validate-ui-backend-integration.sh`
- Open GitHub issue with logs and error messages
