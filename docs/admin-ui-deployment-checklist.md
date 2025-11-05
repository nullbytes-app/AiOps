# Admin UI Deployment Checklist

**AI Agents Enhancement Platform - Streamlit Admin Interface**

**Version:** 1.0.0
**Last Updated:** 2025-11-04
**Story:** 6.8 - Create Admin UI Documentation and Deployment Guide
**Related:** [Admin UI Guide](admin-ui-guide.md)

---

## Overview

This checklist ensures a complete and secure deployment of the Streamlit Admin UI to Kubernetes. Follow each section in order, checking off items as you complete them. Do not proceed to the next section until all items in the current section are verified.

**Estimated Time:** 2-3 hours for first deployment

---

## Pre-Deployment Checklist

Complete these tasks before building or deploying anything.

### Environment Verification

- [ ] **Kubernetes cluster accessible**
  ```bash
  kubectl version --short
  kubectl get nodes
  # All nodes should be in "Ready" status
  ```

- [ ] **Correct namespace exists**
  ```bash
  kubectl get namespace ai-agents
  # If not exists: kubectl create namespace ai-agents
  ```

- [ ] **NGINX Ingress Controller installed**
  ```bash
  kubectl get pods -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx
  # Should show running ingress controller pods
  ```

- [ ] **Database (PostgreSQL) deployed and accessible**
  ```bash
  kubectl get svc -n ai-agents postgres
  # Service should exist with ClusterIP
  ```

- [ ] **Database schema migrated to latest version**
  ```bash
  # Run from local machine with database access
  alembic current
  alembic upgrade head
  ```

### Prerequisites Verification

- [ ] **Docker installed locally (for image building)**
  ```bash
  docker --version
  # Should show Docker version 20.0+
  ```

- [ ] **kubectl configured with correct context**
  ```bash
  kubectl config current-context
  # Should show your target cluster name
  ```

- [ ] **Helm installed (if using Helm charts)**
  ```bash
  helm version
  # Optional - only if using Helm deployment
  ```

- [ ] **Git repository up to date**
  ```bash
  git pull origin main
  git status
  # Should show "nothing to commit, working tree clean"
  ```

---

## Build & Push Checklist

Build and publish Docker image for deployment.

### Docker Image Build

- [ ] **Project code is committed (no uncommitted changes)**
  ```bash
  git status
  # Verify working tree is clean
  ```

- [ ] **Build Docker image**
  ```bash
  docker build -f docker/streamlit.dockerfile -t ai-agents-streamlit:1.0.0 .
  # Build should complete successfully without errors
  ```

- [ ] **Verify image created**
  ```bash
  docker images | grep ai-agents-streamlit
  # Should show image with tag 1.0.0
  ```

- [ ] **Test image locally (optional but recommended)**
  ```bash
  docker run -it --rm -p 8501:8501 \
    -e AI_AGENTS_DATABASE_URL="postgresql://user:pass@host:5432/db" \
    ai-agents-streamlit:1.0.0
  # Open http://localhost:8501 and verify app starts
  # Press Ctrl+C to stop
  ```

### Image Push (If Using Registry)

- [ ] **Tag image for registry**
  ```bash
  docker tag ai-agents-streamlit:1.0.0 your-registry.com/ai-agents-streamlit:1.0.0
  ```

- [ ] **Authenticate to registry**
  ```bash
  docker login your-registry.com
  # Enter credentials when prompted
  ```

- [ ] **Push image to registry**
  ```bash
  docker push your-registry.com/ai-agents-streamlit:1.0.0
  # Push should complete successfully
  ```

- [ ] **Verify image in registry**
  ```bash
  # Check registry web UI or CLI
  # Image should be visible and downloadable
  ```

### Image Load (If Using Local Cluster)

**For Minikube:**

- [ ] **Load image into Minikube**
  ```bash
  minikube image load ai-agents-streamlit:1.0.0
  # Image should load successfully
  ```

**For Kind:**

- [ ] **Load image into Kind**
  ```bash
  kind load docker-image ai-agents-streamlit:1.0.0
  # Image should load successfully
  ```

**For Docker Desktop Kubernetes:**

- [ ] **Image already available (no load needed)**
  ```bash
  # Docker Desktop uses local Docker daemon images directly
  # Verify with: docker images | grep ai-agents-streamlit
  ```

---

## Configuration Checklist

Configure secrets, environment variables, and settings.

### Secrets Configuration

- [ ] **Generate strong authentication password**
  ```bash
  # Generate random 20+ character password
  PASSWORD=$(openssl rand -base64 20)
  echo "Password: $PASSWORD"
  # Save password in password manager (do not commit to git)
  ```

- [ ] **Create authentication secret**
  ```bash
  ./scripts/setup-streamlit-auth.sh admin "$PASSWORD"
  # OR manually:
  # htpasswd -c /tmp/auth admin
  # kubectl create secret generic streamlit-basic-auth \
  #   --from-file=auth=/tmp/auth \
  #   --namespace=ai-agents
  # rm /tmp/auth
  ```

- [ ] **Verify authentication secret created**
  ```bash
  kubectl get secret streamlit-basic-auth -n ai-agents
  # Should show secret exists (not NotFound)
  ```

- [ ] **Create database credentials secret (if not exists)**
  ```bash
  kubectl create secret generic database-credentials \
    --from-literal=url='postgresql://streamlit_admin:secure-password@postgres:5432/ai_agents' \
    --namespace=ai-agents
  # Use actual database credentials
  ```

- [ ] **Verify database secret created**
  ```bash
  kubectl get secret database-credentials -n ai-agents
  ```

- [ ] **Generate Fernet encryption key**
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  # Save output (32-byte base64 string)
  ```

- [ ] **Create encryption key secret**
  ```bash
  kubectl create secret generic encryption-key \
    --from-literal=fernet_key='<generated-key-from-previous-step>' \
    --namespace=ai-agents
  ```

- [ ] **Verify encryption key secret created**
  ```bash
  kubectl get secret encryption-key -n ai-agents
  ```

### Environment Variables Configuration

- [ ] **Review deployment manifest environment variables**
  ```bash
  grep -A 10 "env:" k8s/streamlit-admin-deployment.yaml
  # Verify all required env vars are present:
  # - AI_AGENTS_DATABASE_URL (from secret)
  # - KUBERNETES_NAMESPACE (value: ai-agents)
  # - FERNET_KEY (from secret)
  ```

- [ ] **Update environment variables if needed**
  ```bash
  # Edit k8s/streamlit-admin-deployment.yaml if changes required
  # Ensure all secrets reference correct secret names
  ```

### Streamlit Configuration

- [ ] **Review streamlit-admin-configmap.yaml**
  ```bash
  cat k8s/streamlit-admin-configmap.yaml
  # Verify config.toml settings:
  # - server.port = 8501
  # - server.headless = true
  # - enableXsrfProtection = true
  # - theme colors match brand (optional)
  ```

- [ ] **Update ConfigMap if needed**
  ```bash
  # Edit k8s/streamlit-admin-configmap.yaml if changes required
  ```

### Ingress Configuration

- [ ] **Review Ingress hostname**
  ```bash
  grep "host:" k8s/streamlit-admin-ingress.yaml
  # Should show: admin.ai-agents.local or your production domain
  ```

- [ ] **Update hostname for production (if needed)**
  ```bash
  # Edit k8s/streamlit-admin-ingress.yaml
  # Change host: from admin.ai-agents.local to your actual domain
  ```

- [ ] **Review Ingress annotations**
  ```bash
  grep -A 10 "annotations:" k8s/streamlit-admin-ingress.yaml
  # Verify:
  # - nginx.ingress.kubernetes.io/auth-type: basic
  # - nginx.ingress.kubernetes.io/auth-secret: streamlit-basic-auth
  # - Websocket timeout annotations present (3600+)
  ```

- [ ] **Enable TLS (production only)**
  ```bash
  # Uncomment TLS section in k8s/streamlit-admin-ingress.yaml:
  # spec:
  #   tls:
  #   - hosts:
  #     - admin.your-domain.com
  #     secretName: streamlit-admin-tls
  ```

---

## Deployment Checklist

Apply Kubernetes manifests in correct order.

### RBAC Deployment (CRITICAL - MUST BE FIRST)

- [ ] **Apply RBAC manifest**
  ```bash
  kubectl apply -f k8s/streamlit-rbac.yaml
  ```

- [ ] **Verify ServiceAccount created**
  ```bash
  kubectl get serviceaccount streamlit-admin -n ai-agents
  # Should show: streamlit-admin, 1 secrets, <age>
  ```

- [ ] **Verify Role created**
  ```bash
  kubectl get role streamlit-admin-role -n ai-agents
  # Should show role with creation timestamp
  ```

- [ ] **Verify RoleBinding created**
  ```bash
  kubectl get rolebinding streamlit-admin-rolebinding -n ai-agents
  # Should show rolebinding with creation timestamp
  ```

- [ ] **Test RBAC permissions**
  ```bash
  kubectl auth can-i list pods \
    --as=system:serviceaccount:ai-agents:streamlit-admin \
    -n ai-agents
  # Expected output: yes

  kubectl auth can-i get pods/log \
    --as=system:serviceaccount:ai-agents:streamlit-admin \
    -n ai-agents
  # Expected output: yes
  ```

### ConfigMap Deployment

- [ ] **Apply ConfigMap manifest**
  ```bash
  kubectl apply -f k8s/streamlit-admin-configmap.yaml
  ```

- [ ] **Verify ConfigMap created**
  ```bash
  kubectl get configmap streamlit-config -n ai-agents
  # Should show configmap with data entries
  ```

- [ ] **Verify ConfigMap contents**
  ```bash
  kubectl get configmap streamlit-config -n ai-agents -o yaml
  # Should show config.toml content under data section
  ```

### Deployment

- [ ] **Apply Deployment manifest**
  ```bash
  kubectl apply -f k8s/streamlit-admin-deployment.yaml
  ```

- [ ] **Verify Deployment created**
  ```bash
  kubectl get deployment streamlit-admin -n ai-agents
  # Should show: streamlit-admin, 1/1 ready, <age>
  ```

- [ ] **Verify Pod is running**
  ```bash
  kubectl get pods -n ai-agents -l app=streamlit-admin
  # Should show: streamlit-admin-xxxx, Running, 1/1 ready
  ```

- [ ] **Check Pod events for errors**
  ```bash
  kubectl describe pod -n ai-agents -l app=streamlit-admin
  # Events section should show successful image pull, container start
  # No "ImagePullBackOff", "CrashLoopBackOff", or "Error" events
  ```

- [ ] **Verify Pod logs show successful startup**
  ```bash
  kubectl logs -n ai-agents -l app=streamlit-admin --tail=50
  # Should show: "You can now view your Streamlit app in your browser."
  # No errors or stack traces
  ```

### Service Deployment

- [ ] **Apply Service manifest**
  ```bash
  kubectl apply -f k8s/streamlit-admin-service.yaml
  ```

- [ ] **Verify Service created**
  ```bash
  kubectl get svc streamlit-admin -n ai-agents
  # Should show: streamlit-admin, LoadBalancer, CLUSTER-IP, EXTERNAL-IP or <pending>, 80:XXXXX/TCP
  ```

- [ ] **Verify Service endpoints**
  ```bash
  kubectl get endpoints streamlit-admin -n ai-agents
  # Should show pod IP and port 8501
  # Example: 10.244.1.23:8501
  ```

- [ ] **Test Service connectivity (port-forward)**
  ```bash
  kubectl port-forward -n ai-agents svc/streamlit-admin 8501:80 &
  # Open browser: http://localhost:8501
  # Should show Streamlit login page
  # Press Ctrl+C to stop port-forward
  ```

### Ingress Deployment

- [ ] **Apply Ingress manifest**
  ```bash
  kubectl apply -f k8s/streamlit-admin-ingress.yaml
  ```

- [ ] **Verify Ingress created**
  ```bash
  kubectl get ingress streamlit-admin -n ai-agents
  # Should show: streamlit-admin, nginx, admin.ai-agents.local, ADDRESS, 80
  ```

- [ ] **Check Ingress status**
  ```bash
  kubectl describe ingress streamlit-admin -n ai-agents
  # Verify:
  # - Annotations include auth-type, auth-secret, websocket annotations
  # - Backend service is streamlit-admin:80
  # - Events show no errors
  ```

- [ ] **Wait for Ingress ADDRESS to be assigned**
  ```bash
  kubectl get ingress streamlit-admin -n ai-agents -w
  # Wait until ADDRESS column shows IP (may take 1-2 minutes)
  # Press Ctrl+C when ADDRESS appears
  ```

---

## Verification Checklist

Verify the deployment is working correctly.

### Basic Connectivity

- [ ] **Add hostname to /etc/hosts (local testing)**
  ```bash
  # Get Ingress address
  INGRESS_IP=$(kubectl get ingress streamlit-admin -n ai-agents -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
  echo "$INGRESS_IP  admin.ai-agents.local" | sudo tee -a /etc/hosts
  ```

- [ ] **Test DNS resolution**
  ```bash
  nslookup admin.ai-agents.local
  # Should resolve to Ingress IP or 127.0.0.1
  ```

- [ ] **Test HTTP connectivity**
  ```bash
  curl -v http://admin.ai-agents.local
  # Expected: HTTP 401 Unauthorized (auth required)
  # Should NOT show connection errors or timeouts
  ```

- [ ] **Test authenticated HTTP access**
  ```bash
  curl -u admin:yourpassword http://admin.ai-agents.local
  # Expected: HTTP 200 OK with HTML content
  ```

### Browser Access

- [ ] **Open admin UI in browser**
  ```
  Browser URL: http://admin.ai-agents.local
  ```

- [ ] **Basic auth prompt appears**
  - Browser should show authentication dialog
  - Enter username: `admin`
  - Enter password: (password from Configuration Checklist)

- [ ] **Successfully login to admin UI**
  - Dashboard page loads
  - Navigation sidebar visible on left
  - No error messages displayed

### Dashboard Page Verification

- [ ] **Database connection status shows Connected**
  - Database Connection Status section shows ✅ Connected
  - PostgreSQL version displayed
  - Number of tenants shown

- [ ] **Metrics cards display data**
  - Database Status card shows ✅
  - Active Tenants count displayed
  - Queue Depth number shown (may be 0)
  - Success Rate percentage displayed (may be N/A if no data)

- [ ] **Page auto-refreshes**
  - Wait 30 seconds
  - "Last updated" timestamp changes
  - Metrics update automatically

### Navigation and All Pages Load

- [ ] **Navigate to Tenant Management page**
  - Click "Tenants" in sidebar
  - Page loads without errors
  - Table displays (may be empty)
  - "Add Tenant" button visible

- [ ] **Navigate to Enhancement History page**
  - Click "History" in sidebar
  - Page loads without errors
  - Filter bar visible at top
  - Table displays (may be empty)

- [ ] **Navigate to System Operations page**
  - Click "Operations" in sidebar
  - Page loads without errors
  - Processing Controls section visible
  - Queue Management buttons present

- [ ] **Navigate to Real-Time Metrics page**
  - Click "Metrics" in sidebar
  - Page loads without errors
  - Charts displayed (may show "No data" if Prometheus not configured)
  - Time range selector visible

- [ ] **Navigate to Worker Monitoring page**
  - Click "Workers" in sidebar
  - Page loads without errors
  - Worker table visible (may be empty if no workers)
  - If error "Forbidden (403)" appears, RBAC issue - see Troubleshooting

### Functionality Testing

- [ ] **Test Tenant Management CRUD (if applicable)**
  - Click "Add Tenant" button
  - Fill form with test data:
    - Tenant Name: `test-client`
    - API URL: `https://test.servicedeskplus.com/api/v3`
    - API Key: `test-key-12345`
    - Webhook Secret: `test-secret-67890`
  - Click "Save"
  - Tenant appears in table with 🔒 encryption indicators
  - Edit tenant, verify form populates
  - Delete tenant, verify confirmation dialog

- [ ] **Test Worker Monitoring (if workers deployed)**
  - Navigate to Workers page
  - Worker table shows active workers
  - Click "Logs" button for a worker
  - Logs modal opens showing recent logs
  - Close logs modal

- [ ] **Test System Operations**
  - Navigate to Operations page
  - Click "Inspect Queues" button
  - Queue statistics displayed
  - Do NOT test destructive operations (Pause, Clear, Restart) in production

### Performance Verification

- [ ] **Page load times acceptable**
  - All pages load in < 3 seconds
  - No prolonged spinners or timeouts

- [ ] **Pod resource usage within limits**
  ```bash
  kubectl top pod -n ai-agents -l app=streamlit-admin
  # Memory should be < 400Mi (limit is 512Mi)
  # CPU should be < 300m (limit is 500m)
  ```

- [ ] **No errors in pod logs**
  ```bash
  kubectl logs -n ai-agents -l app=streamlit-admin --tail=100
  # Should show INFO logs, no ERRORs or WARNINGs
  ```

- [ ] **No crash restarts**
  ```bash
  kubectl get pods -n ai-agents -l app=streamlit-admin
  # RESTARTS column should show 0
  ```

---

## Security Hardening Checklist

Apply production security best practices.

### Authentication & Authorization

- [ ] **Strong password configured (20+ characters)**
  - Password stored in password manager
  - Password not shared via insecure channels (email, Slack)

- [ ] **Default credentials changed**
  - `admin`/`admin` NOT in use
  - Custom strong password from Configuration Checklist

- [ ] **OAuth2-Proxy planned (if enterprise SSO required)**
  - Roadmap item documented for Phase 2
  - Azure AD/Google Workspace/Okta configuration documented

### Network Security

- [ ] **TLS/HTTPS enabled (production)**
  ```bash
  kubectl get ingress streamlit-admin -n ai-agents -o yaml | grep -A 5 tls
  # Should show TLS configuration with secretName
  ```

- [ ] **TLS certificate valid**
  ```bash
  curl -I https://admin.your-domain.com
  # Should show HTTP 200 with valid certificate
  # Browser should show padlock icon (not insecure warning)
  ```

- [ ] **IP whitelisting configured (if required)**
  ```bash
  kubectl get ingress streamlit-admin -n ai-agents -o yaml | grep whitelist-source-range
  # Should show annotation with corporate IP ranges
  ```

- [ ] **WebSocket timeouts configured**
  ```bash
  kubectl get ingress streamlit-admin -n ai-agents -o yaml | grep timeout
  # Should show proxy-read-timeout and proxy-send-timeout (3600+)
  ```

### Secrets Management

- [ ] **All secrets in Kubernetes Secrets (not hardcoded)**
  ```bash
  kubectl get secrets -n ai-agents
  # Should show: streamlit-basic-auth, database-credentials, encryption-key
  ```

- [ ] **Secrets have proper RBAC (only admin UI pod can access)**
  ```bash
  kubectl auth can-i get secrets \
    --as=system:serviceaccount:ai-agents:streamlit-admin \
    -n ai-agents
  # Expected: yes (pod needs access to its own secrets)
  ```

- [ ] **Secret rotation schedule documented**
  - Production secrets: Rotate every 90 days
  - Development secrets: Rotate every 180 days
  - Schedule added to operations calendar

### Database Security

- [ ] **Database connection uses SSL**
  ```bash
  kubectl get secret database-credentials -n ai-agents -o yaml
  # Connection string should include sslmode=require (production)
  ```

- [ ] **Database user has minimal permissions**
  ```sql
  -- Verify grants in PostgreSQL:
  \du streamlit_admin
  -- Should NOT have SUPERUSER, CREATEDB, CREATEROLE
  ```

- [ ] **Row-Level Security (RLS) policies applied**
  ```sql
  -- Verify RLS in PostgreSQL:
  SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';
  -- tenant_config and enhancement_history should have rowsecurity = true
  ```

### Monitoring & Logging

- [ ] **Audit logging enabled**
  ```bash
  kubectl logs -n ai-agents -l app=streamlit-admin | grep -i "login\|tenant\|operation"
  # Should show user actions logged
  ```

- [ ] **Centralized logging configured (ELK/EFK)**
  - Fluentd or Filebeat deployed
  - Logs shipping to Elasticsearch
  - Kibana dashboards for admin UI logs

- [ ] **Log retention policy defined (30+ days)**
  - Elasticsearch index lifecycle management configured
  - Old logs archived or deleted per policy

- [ ] **Alerting configured for failed auth attempts**
  - Alert rule: >5 failed auth in 1 hour
  - Alert channel: Email, Slack, or PagerDuty

### Resource Management

- [ ] **Resource requests appropriate**
  ```bash
  kubectl get deployment streamlit-admin -n ai-agents -o yaml | grep -A 4 resources
  # requests.memory: 256Mi, requests.cpu: 100m (baseline)
  ```

- [ ] **Resource limits prevent OOMKilled**
  - limits.memory: 512Mi minimum (1Gi recommended)
  - limits.cpu: 500m (allows burst for chart rendering)

- [ ] **Pod anti-affinity configured (if multi-replica)**
  ```bash
  kubectl get deployment streamlit-admin -n ai-agents -o yaml | grep -A 10 affinity
  # Optional: If running >1 replica, spread across nodes
  ```

### Compliance & Backup

- [ ] **Security scan performed on Docker image**
  ```bash
  # Using Trivy (install from https://github.com/aquasecurity/trivy)
  trivy image ai-agents-streamlit:1.0.0
  # Should show zero HIGH or CRITICAL vulnerabilities
  ```

- [ ] **Vulnerability scan passed**
  - Snyk, Aqua, or similar tool run
  - No HIGH/CRITICAL issues unresolved

- [ ] **Access control policy documented**
  - Who has access to admin UI
  - Approval process for new users
  - Offboarding process documented

- [ ] **Data retention policy defined**
  - Enhancement history retention (e.g., 90 days)
  - Audit log retention (e.g., 1 year)
  - Database backup schedule (daily)

- [ ] **Disaster recovery plan documented**
  - RTO (Recovery Time Objective) defined
  - RPO (Recovery Point Objective) defined
  - Restore procedure tested

---

## Post-Deployment Checklist

Complete these tasks after deployment is verified.

### Documentation

- [ ] **Update deployment documentation**
  - Add deployment date to admin-ui-guide.md
  - Document any deviations from standard procedure
  - Note production URL and access details

- [ ] **Document secrets locations**
  - Password stored in password manager (team access)
  - Kubernetes secret names documented
  - Secret rotation reminders set (calendar/ticketing system)

- [ ] **Update runbook**
  - Add admin UI to ops runbook
  - Include rollback procedure
  - Document escalation contacts

### Team Handoff

- [ ] **Share access credentials with operations team**
  - Password manager entry shared
  - Access instructions provided
  - Training session scheduled (if needed)

- [ ] **Demonstrate admin UI features**
  - Walk through all six pages
  - Show common operations (restart workers, view logs)
  - Explain troubleshooting procedures

- [ ] **Provide support contacts**
  - Primary: DevOps lead
  - Secondary: Platform engineer
  - Escalation: Development team

### Monitoring Setup

- [ ] **Add admin UI to monitoring dashboards**
  - Grafana dashboard for pod metrics
  - Alert rules for pod health
  - Uptime monitoring (Pingdom, UptimeRobot)

- [ ] **Configure health checks**
  ```bash
  kubectl get deployment streamlit-admin -n ai-agents -o yaml | grep -A 10 livenessProbe
  # Verify liveness and readiness probes configured
  ```

- [ ] **Test alert firing**
  - Manually stop pod, verify alert fires
  - Verify notification received (email, Slack)

### Cleanup

- [ ] **Remove test data (if any)**
  - Delete test tenants created during verification
  - Clear test enhancement history records

- [ ] **Remove /etc/hosts entry (if local testing)**
  ```bash
  sudo vi /etc/hosts
  # Remove line: <IP> admin.ai-agents.local
  ```

- [ ] **Document known issues (if any)**
  - Create tickets for any non-blocking issues discovered
  - Add workarounds to runbook

---

## Rollback Procedure

If deployment fails or critical issues discovered, follow these steps:

1. **Identify the issue**
   ```bash
   kubectl get pods -n ai-agents -l app=streamlit-admin
   kubectl logs -n ai-agents -l app=streamlit-admin --tail=100
   kubectl describe pod -n ai-agents -l app=streamlit-admin
   ```

2. **Rollback deployment**
   ```bash
   # View deployment history
   kubectl rollout history deployment/streamlit-admin -n ai-agents

   # Rollback to previous version
   kubectl rollout undo deployment/streamlit-admin -n ai-agents

   # Or rollback to specific revision
   kubectl rollout undo deployment/streamlit-admin --to-revision=<revision-number> -n ai-agents
   ```

3. **Verify rollback successful**
   ```bash
   kubectl get pods -n ai-agents -l app=streamlit-admin
   kubectl logs -n ai-agents -l app=streamlit-admin --tail=50
   # Pod should be running with previous version
   ```

4. **Remove new Ingress (if Ingress caused issue)**
   ```bash
   kubectl delete ingress streamlit-admin -n ai-agents
   # Wait 1 minute for cleanup
   kubectl apply -f k8s/streamlit-admin-ingress.yaml.backup
   ```

5. **Document rollback reason**
   - Add entry to deployment log
   - Create incident ticket
   - Schedule post-mortem if critical

---

## Troubleshooting Reference

Quick reference for common issues during deployment.

| Symptom | Cause | Solution |
|---------|-------|----------|
| **Pod status: ImagePullBackOff** | Image not found in registry | Verify image name/tag in deployment.yaml, check registry authentication |
| **Pod status: CrashLoopBackOff** | Application crash on startup | Check logs: `kubectl logs -n ai-agents -l app=streamlit-admin` |
| **Pod logs: Database connection failed** | DATABASE_URL secret missing/incorrect | Verify secret exists: `kubectl get secret database-credentials -n ai-agents` |
| **Worker Monitoring page: Forbidden (403)** | RBAC not applied | Apply RBAC: `kubectl apply -f k8s/streamlit-rbac.yaml`, restart pod |
| **No basic auth prompt** | Ingress auth annotations missing | Check Ingress annotations: `kubectl describe ingress streamlit-admin -n ai-agents` |
| **401 Unauthorized with correct password** | Secret mismatch | Recreate secret: `./scripts/setup-streamlit-auth.sh admin newpassword` |
| **Ingress ADDRESS stays <pending>** | LoadBalancer not supported in cluster | Use NodePort or port-forward for local testing |
| **Connection lost/WebSocket errors** | Timeout too short | Increase proxy-read-timeout to 7200 in Ingress annotations |

For detailed troubleshooting, see [Admin UI Guide - Troubleshooting Section](admin-ui-guide.md#troubleshooting).

---

## Completion Checklist

Final verification before marking deployment complete.

- [ ] **All Pre-Deployment items checked**
- [ ] **All Build & Push items checked**
- [ ] **All Configuration items checked**
- [ ] **All Deployment items checked**
- [ ] **All Verification items checked**
- [ ] **All Security Hardening items checked**
- [ ] **All Post-Deployment items checked**

- [ ] **Deployment documented in change log**
  - Date: _______________
  - Version: _______________
  - Deployed by: _______________
  - Verified by: _______________

- [ ] **Sign-off obtained**
  - Operations Lead: _______________
  - Security Review: _______________
  - Product Owner: _______________

---

**Deployment Status:**

- [ ] ✅ **COMPLETE** - All items checked, admin UI fully functional
- [ ] ⚠️ **COMPLETE WITH ISSUES** - Deployed with known non-blocking issues documented
- [ ] ❌ **ROLLED BACK** - Deployment failed, rolled back to previous state

**Notes:**

_______________________________________________________________________________

_______________________________________________________________________________

_______________________________________________________________________________

---

**End of Deployment Checklist**

For questions or issues, contact:
- DevOps Team: devops@example.com
- Admin UI Guide: [docs/admin-ui-guide.md](admin-ui-guide.md)
- Story 6.8 Definition: [docs/stories/6-8-create-admin-ui-documentation-and-deployment-guide.md](stories/6-8-create-admin-ui-documentation-and-deployment-guide.md)
