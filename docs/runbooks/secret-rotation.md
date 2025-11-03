# Secret Rotation Runbook

This runbook explains how to safely rotate secrets in a Kubernetes production environment.

## Overview

Secrets include:
- PostgreSQL password
- Redis password  
- OpenAI API key
- Encryption key (CRITICAL - requires data migration)

## Prerequisites

- kubectl access to the Kubernetes cluster
- Updated secret value (generated via methods in secrets-setup.md)
- Application load balancer or ingress controller
- Backup of current encryption key (if rotating encryption key)

## General Secret Rotation Procedure

### 1. Generate New Secret Value

For passwords:
```bash
openssl rand -base64 32
```

For OpenAI API key:
Get new key from https://platform.openai.com/account/api-keys

For encryption key:
```bash
python -c "from src.utils.encryption import generate_encryption_key; print(generate_encryption_key())"
```

### 2. Base64 Encode Secret

```bash
echo -n "your-new-secret-value" | base64
```

Example:
```bash
$ echo -n "newPassword123456" | base64
bmV3UGFzc3dvcmQxMjM0NTY=
```

### 3. Update Kubernetes Secret

Patch the secret with the new value:

```bash
kubectl patch secret app-secrets \
  -p '{"data":{"secret-key":"<base64-encoded-value>"}}'
```

**Example: Rotating OpenAI API key**

```bash
# Get the new key from OpenAI
NEW_API_KEY="sk-proj-new-key-123456789"

# Base64 encode it
ENCODED=$(echo -n "$NEW_API_KEY" | base64)

# Patch the Kubernetes Secret
kubectl patch secret app-secrets \
  -p "{\"data\":{\"openai-api-key\":\"$ENCODED\"}}"
```

### 4. Verify Secret Updated

```bash
# View the secret (values will be base64-encoded)
kubectl get secret app-secrets -o yaml

# Decode to verify (DANGEROUS - shows unencrypted value!)
kubectl get secret app-secrets -o jsonpath='{.data.openai-api-key}' | base64 -d
```

### 5. Trigger Pod Restart

Rolling restart ensures all pods pick up the new secret:

```bash
# Restart FastAPI deployment
kubectl rollout restart deployment/api

# Restart Celery workers
kubectl rollout restart deployment/worker
```

### 6. Monitor Restart

```bash
# Watch deployment status
kubectl rollout status deployment/api
kubectl rollout status deployment/worker

# Check pods are running
kubectl get pods -l app=api
kubectl get pods -l app=worker

# Verify logs for secrets validation
kubectl logs <api-pod-name> | grep -i "secrets\|validation"
```

### 7. Validate Application

```bash
# Health check
curl http://<api-endpoint>/health

# Check logs for successful secret loading
kubectl logs <api-pod-name> | grep "Secrets loaded successfully"

# Run smoke test
kubectl exec <api-pod-name> -- curl http://localhost:8000/api/v1/health
```

## Secret-Specific Procedures

### PostgreSQL Password Rotation

**Estimated Downtime**: 2-3 minutes (rolling restart)
**Impact**: All pods will temporarily lose database connectivity

**Steps**:
1. Update PostgreSQL password in database (via pg_admin or psql)
2. Generate new 32-character password
3. Update Kubernetes Secret (see general procedure above)
4. Restart API and worker pods
5. Verify connectivity: `kubectl logs <pod> | grep "database.*healthy"`

**Rollback**:
1. Revert PostgreSQL password to previous value
2. Patch Kubernetes Secret back to old value
3. Restart pods

### Redis Password Rotation

**Estimated Downtime**: 2-3 minutes (rolling restart)
**Impact**: Cache miss for in-flight data, no data loss

**Steps**:
1. Update Redis configuration with new password
2. Generate new 32-character password
3. Update Kubernetes Secret
4. Restart API and worker pods
5. Verify connectivity: `kubectl logs <pod> | grep "redis.*healthy"`

**Rollback**:
1. Revert Redis password
2. Patch Kubernetes Secret
3. Restart pods

### OpenAI API Key Rotation

**Estimated Downtime**: Minimal (rolling restart, requests queued)
**Impact**: None - API calls can be queued during restart

**Steps**:
1. Get new API key from https://platform.openai.com/account/api-keys
2. Invalidate old key (optional, for security)
3. Update Kubernetes Secret
4. Restart API and worker pods
5. Verify logs: `kubectl logs <pod> | grep "OPENAI_API_KEY\|secrets loaded"`

**Note**: Old key can continue working during transition period for safety.

### Encryption Key Rotation (CRITICAL)

⚠️ **WARNING: Data migration required. This is complex and risky.**

**Estimated Downtime**: 30+ minutes (full data migration)
**Impact**: Tenant configs inaccessible during migration

**Prerequisite**:
- Backup of current encryption key in secure location
- Backup of database
- Test migration procedure in staging first

**Steps**:

1. **Backup current encryption key and database**
   ```bash
   # Backup key (store in password manager, not git!)
   kubectl get secret app-secrets -o jsonpath='{.data.encryption-key}' | base64 -d > encryption-key-backup.txt
   
   # Backup database (example with PostgreSQL)
   kubectl exec <postgres-pod> -- pg_dump -U postgres ai_agents > db-backup.sql
   ```

2. **Generate new encryption key**
   ```bash
   python -c "from src.utils.encryption import generate_encryption_key; print(generate_encryption_key())"
   ```

3. **Create data migration script**
   - Reencrypt all tenant configs with new key
   - Test against backup database first
   - Dry-run in staging

4. **Execution**
   - Scale down all pods (zero downtime not possible for encryption key rotation)
   - Run migration script
   - Update Kubernetes Secret with new key
   - Scale back up
   - Verify all tenant configs accessible

5. **Verification**
   - Check all tenant configs can be decrypted
   - Run integration tests
   - Monitor logs for decryption errors

6. **Rollback Plan** (if migration fails)
   - Restore database from backup
   - Keep old encryption key in Kubernetes Secret
   - Restart pods with old key
   - Investigate migration script errors

**DO NOT proceed with encryption key rotation without test in staging environment first.**

## Communication Template

Send to stakeholders before production rotation:

```
NOTICE: Scheduled Secret Rotation

Service: AI Agents
Date: [DATE]
Duration: [ESTIMATED TIME] minutes
Impact: [DESCRIBE IMPACT - API slowdown, cache miss, etc.]

We will be rotating [SECRET TYPE] to enhance security.
No action required from users.

If you experience issues, please contact [CONTACT].
```

## Monitoring During Rotation

Watch these metrics:
- Pod restart status
- API response times
- Database connection errors
- Redis connection errors
- Task queue depth (Celery)

```bash
# Monitor pod events
kubectl get events --sort-by='.lastTimestamp' | tail -20

# Monitor logs for errors
kubectl logs -f <pod-name> --tail=50

# Check metrics (if Prometheus/Grafana installed)
curl http://prometheus:9090/api/v1/query?query=up{job="kubernetes-pods"}
```

## Escalation

If issues arise during rotation:

1. **Pod fails to start**
   - Check logs: `kubectl logs <pod-name>`
   - Check events: `kubectl describe pod <pod-name>`
   - Common issue: Invalid secret format (base64 encoding error)

2. **Database connectivity lost**
   - Verify password is correct: `kubectl get secret app-secrets -o yaml`
   - Check database pod health: `kubectl describe pod <postgres-pod>`
   - Possible solutions: Revert secret, check database logs

3. **Application crashes**
   - Check logs for secret validation errors
   - Verify all 4 secrets present: `kubectl exec <pod> -- env | grep AI_AGENTS`
   - Rollback secret and investigate

## References

- docs/runbooks/secrets-setup.md - Secret generation guide
- Kubernetes Secrets Documentation: https://kubernetes.io/docs/concepts/configuration/secret/
- Secret Rotation Best Practices: https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html
