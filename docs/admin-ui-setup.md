# Admin UI Setup Guide

**Story:** 6.1 - Set Up Streamlit Application Foundation
**Status:** Foundation Complete
**Last Updated:** 2025-11-04

## Overview

The AI Agents Admin UI provides operations teams with a web-based interface for system management without requiring kubectl access. Built with Streamlit 1.44+, it offers:

- **System Status Dashboard** (Story 6.2) - Real-time metrics and health monitoring
- **Tenant Management** (Story 6.3) - CRUD operations for tenant configurations
- **Enhancement History** (Story 6.4) - View and filter processing history
- **System Operations** (Story 6.5) - Control system operations
- **Real-Time Metrics** (Story 6.6) - Prometheus integration
- **Worker Monitoring** (Story 6.7) - Health and resource utilization

**Current Implementation (Story 6.1):**
Foundation setup with basic structure, authentication, and database connectivity. Full features coming in subsequent stories (6.2-6.7).

## Architecture

### Components

```
AI Agents Admin UI
├── Streamlit App (Python 3.12)
│   ├── Multi-page navigation
│   ├── Session-based authentication
│   └── Synchronous database access
├── Kubernetes Deployment
│   ├── Single replica (admin workload)
│   ├── 256Mi memory, 100m CPU requests
│   └── 512Mi memory, 500m CPU limits
├── NGINX Ingress
│   ├── Basic authentication (MVP)
│   ├── WebSocket support
│   └── admin.ai-agents.local routing
└── PostgreSQL Database
    ├── Shared models (TenantConfig, EnhancementHistory)
    └── Read-write access via synchronous session
```

### Authentication Strategy

**Local Development:**
- Simple session-based authentication
- Credentials in `.streamlit/secrets.toml`
- Default: username=`admin`, password=`admin`

**Production (Kubernetes):**
- NGINX Ingress basic authentication
- htpasswd-based credential storage
- Kubernetes Secret: `streamlit-basic-auth`
- Upgrade path: OAuth2-Proxy for enterprise SSO

## Local Development Setup

### Prerequisites

- Python 3.12+
- PostgreSQL 16+ running
- Virtual environment activated

### Installation

1. **Install Dependencies:**

```bash
# From project root
pip install -e ".[dev]"
```

This installs:
- `streamlit>=1.44.0` - Admin UI framework
- `psycopg2-binary>=2.9.9` - Synchronous PostgreSQL driver
- `pandas>=2.1.0` - Data manipulation
- `plotly>=5.18.0` - Interactive charts
- `pytest-mock>=3.12.0` - Testing framework

2. **Configure Database Connection:**

Set environment variable:

```bash
export AI_AGENTS_DATABASE_URL="postgresql://aiagents:password@localhost:5432/ai_agents"
```

Or add to `.env` file:

```env
AI_AGENTS_DATABASE_URL=postgresql://aiagents:password@localhost:5432/ai_agents
```

3. **Configure Authentication (Optional):**

Copy template:

```bash
cp .streamlit/secrets.toml.template .streamlit/secrets.toml
```

Edit `.streamlit/secrets.toml`:

```toml
[credentials]
[credentials.usernames]
[credentials.usernames.admin]
password = "your-secure-password"
name = "Administrator"
email = "admin@example.com"
```

**Note:** If `secrets.toml` is not configured, app uses default credentials (`admin/admin`).

### Running Locally

```bash
# From project root
streamlit run src/admin/app.py
```

The app will be available at: http://localhost:8501

**Default Login:**
- Username: `admin`
- Password: `admin`

### Verify Database Connection

After logging in, check the Dashboard page → "Database Connection Status" section.
Should display:
- ✅ Connected to PostgreSQL
- Database version
- Number of configured tenants

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (1.28+)
- kubectl configured
- NGINX Ingress Controller installed
- Namespace `ai-agents` created

### Build Docker Image

```bash
# From project root
docker build -f docker/streamlit.dockerfile -t ai-agents-streamlit:1.0.0 .
```

### Setup Authentication

Create htpasswd secret for Ingress basic auth:

```bash
# Using the provided script (recommended)
./scripts/setup-streamlit-auth.sh admin your-secure-password

# Or manually
htpasswd -c /tmp/auth admin
kubectl create secret generic streamlit-basic-auth \
  --from-file=auth=/tmp/auth \
  --namespace=ai-agents
```

### Deploy to Kubernetes

```bash
# Apply all Streamlit admin manifests
kubectl apply -f k8s/streamlit-admin-configmap.yaml
kubectl apply -f k8s/streamlit-admin-deployment.yaml
kubectl apply -f k8s/streamlit-admin-service.yaml
kubectl apply -f k8s/streamlit-admin-ingress.yaml
```

### Verify Deployment

```bash
# Check pod status
kubectl get pods -n ai-agents -l app=streamlit-admin

# Check logs
kubectl logs -n ai-agents -l app=streamlit-admin -f

# Check ingress
kubectl get ingress -n ai-agents streamlit-admin
```

Expected output:
```
NAME               CLASS   HOSTS                      ADDRESS      PORTS   AGE
streamlit-admin    nginx   admin.ai-agents.local      localhost    80      1m
```

### Configure Local Access

Add to `/etc/hosts`:

```
127.0.0.1  admin.ai-agents.local
```

### Access the UI

Open browser: http://admin.ai-agents.local

You'll be prompted for basic authentication credentials (htpasswd).

## Configuration

### Streamlit Configuration

Stored in `.streamlit/config.toml` and mounted via ConfigMap in Kubernetes.

Key settings:

```toml
[server]
port = 8501
headless = true               # Required for production
enableXsrfProtection = true   # Security

[browser]
gatherUsageStats = false      # Privacy

[theme]
primaryColor = "#0066CC"      # Brand colors
backgroundColor = "#FFFFFF"
```

### Database Connection

**Environment Variable:** `AI_AGENTS_DATABASE_URL`

Format: `postgresql://user:password@host:port/database`

**Local:** Set in shell or `.env` file
**Kubernetes:** Mounted from Secret `database-credentials`

### Resource Limits

Current allocation (production):

| Resource | Request | Limit |
|----------|---------|-------|
| Memory   | 256Mi   | 512Mi |
| CPU      | 100m    | 500m  |

Adjust in `k8s/streamlit-admin-deployment.yaml` if needed.

## Troubleshooting

### Database Connection Failures

**Symptom:** "❌ Database connection failed" on Dashboard

**Solutions:**

1. **Check environment variable:**
   ```bash
   echo $AI_AGENTS_DATABASE_URL
   ```

2. **Test PostgreSQL connectivity:**
   ```bash
   psql $AI_AGENTS_DATABASE_URL -c "SELECT 1"
   ```

3. **Verify in Kubernetes:**
   ```bash
   kubectl exec -n ai-agents deployment/streamlit-admin -- \
     env | grep DATABASE_URL
   ```

4. **Check Secret exists:**
   ```bash
   kubectl get secret database-credentials -n ai-agents
   ```

### Authentication Not Working (Kubernetes)

**Symptom:** No basic auth prompt, or 401 Unauthorized

**Solutions:**

1. **Verify secret exists:**
   ```bash
   kubectl get secret streamlit-basic-auth -n ai-agents
   ```

2. **Check secret content:**
   ```bash
   kubectl get secret streamlit-basic-auth -n ai-agents -o yaml
   ```

   Should have `data.auth` key.

3. **Recreate secret:**
   ```bash
   ./scripts/setup-streamlit-auth.sh admin newpassword
   ```

4. **Check Ingress annotations:**
   ```bash
   kubectl describe ingress streamlit-admin -n ai-agents
   ```

   Should show:
   - `nginx.ingress.kubernetes.io/auth-type: basic`
   - `nginx.ingress.kubernetes.io/auth-secret: streamlit-basic-auth`

### Pod Crashes or Restarts

**Check logs:**

```bash
kubectl logs -n ai-agents -l app=streamlit-admin --tail=100
```

**Common issues:**

1. **Import errors:** Ensure all dependencies installed in Docker image
2. **Memory limit:** Increase resource limits if OOMKilled
3. **Database connection:** Verify `AI_AGENTS_DATABASE_URL` is set

### WebSocket Connection Issues

**Symptom:** "Connection lost" or frequent reconnections

**Solution:**

Ingress has WebSocket timeout annotations:

```yaml
nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"
nginx.ingress.kubernetes.io/websocket-services: streamlit-admin
```

If issues persist, increase timeout values.

### Port Conflicts (Local Dev)

**Symptom:** "Address already in use" on port 8501

**Solution:**

```bash
# Find process using port 8501
lsof -i :8501

# Kill process
kill -9 <PID>

# Or use different port
streamlit run src/admin/app.py --server.port=8502
```

## Security Considerations

### Local Development

- **Default credentials:** Change from `admin/admin` in `.streamlit/secrets.toml`
- **Database URL:** Never commit `.env` or `secrets.toml` to git (git-ignored)
- **HTTPS:** Not required for local dev

### Production

- **Basic auth credentials:** Use strong passwords (20+ characters)
- **Upgrade to OAuth2-Proxy:** Recommended for enterprise deployments
- **TLS/HTTPS:** Enable cert-manager for production (commented in ingress.yaml)
- **Secret rotation:** Regularly rotate database credentials and auth passwords
- **Network policies:** Restrict admin UI access to internal networks only
- **Audit logging:** Monitor access logs in NGINX Ingress

### Future Enhancements (Post-MVP)

Story 6.8 will add:
- OAuth2-Proxy integration for SSO (Azure AD, Google, GitHub)
- Role-based access control (RBAC)
- Audit logging for admin actions
- TLS certificate automation

## Next Steps

**Immediate (Story 6.1 Complete):**
- ✅ Foundation setup complete
- ✅ Authentication working
- ✅ Database connectivity verified
- ✅ Kubernetes deployment functional

**Coming Soon:**

- **Story 6.2:** System Status Dashboard with real-time metrics
- **Story 6.3:** Tenant Management CRUD interface
- **Story 6.4:** Enhancement History viewer with filters
- **Story 6.5:** System Operations controls (pause/resume, queue management)
- **Story 6.6:** Real-time metrics display (Prometheus integration)
- **Story 6.7:** Worker health and resource monitoring
- **Story 6.8:** Comprehensive documentation and deployment guide

## Support

For issues or questions:

1. Check [Troubleshooting](#troubleshooting) section above
2. Review Streamlit logs: `kubectl logs -n ai-agents -l app=streamlit-admin`
3. Verify database connectivity
4. Check NGINX Ingress logs: `kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx`
5. Consult Streamlit documentation: https://docs.streamlit.io

## References

- [Streamlit 1.44 Release Notes](https://docs.streamlit.io/develop/quick-references/release-notes/2025#version-1-44-0)
- [Streamlit Multi-Page Apps](https://docs.streamlit.io/develop/concepts/multipage-apps/overview)
- [Kubernetes Deployment Guide](https://docs.streamlit.io/deploy/tutorials/kubernetes)
- [NGINX Ingress Basic Auth](https://kubernetes.github.io/ingress-nginx/examples/auth/basic/)
- Story 6.1 Definition: `docs/stories/6-1-set-up-streamlit-application-foundation.md`
- PRD Requirements: `docs/PRD.md#Admin-UI-Configuration-Management` (FR026-FR033)
- Architecture Decisions: `docs/architecture.md#ADR-009-Streamlit-for-Admin-UI`
