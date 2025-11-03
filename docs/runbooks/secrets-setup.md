# Secrets Setup Guide

This document explains how to generate, configure, and deploy secrets for the AI Agents application.

## Overview

The application uses Kubernetes Secrets for production environments and .env files for local development. Secrets include:

- **PostgreSQL Password**: Database connection credential
- **Redis Password**: Cache/broker connection credential  
- **OpenAI API Key**: LLM service access credential
- **Encryption Key**: Fernet key for encrypting sensitive tenant configurations

## Secret Generation

### PostgreSQL Password

Generate a cryptographically secure 32-character password:

```bash
openssl rand -base64 32
```

Example output:
```
X9k2jF8nP4mL7qR1vW3xC5yB2zD9eF6gH8j
```

Requirements:
- **Minimum**: 12 characters
- **Type**: Alphanumeric with special characters
- **Usage**: Database authentication (POSTGRES_PASSWORD)

### Redis Password

Generate a cryptographically secure 32-character password:

```bash
openssl rand -base64 32
```

Requirements:
- **Minimum**: 12 characters
- **Type**: Alphanumeric with special characters
- **Usage**: Redis broker authentication (REDIS_PASSWORD)

### OpenAI API Key

1. Go to [OpenAI API Keys](https://platform.openai.com/account/api-keys)
2. Create a new API key or copy existing key
3. Key format: `sk-proj-...` or `sk-...`

Requirements:
- **Non-empty**: Must have at least 20 characters
- **Type**: OpenAI service credential
- **Usage**: LLM API access (OPENAI_API_KEY)

### Encryption Key (Fernet)

Generate a Fernet encryption key using the project's encryption utility:

```bash
python -c "from src.utils.encryption import generate_encryption_key; print(generate_encryption_key())"
```

Example output:
```
gAAAAABlwXxk-k_Nz5mPqR-9jL2xF8vB3cZ1aQ_yH7mJ9dKwL-sA0pR1bC=
```

Requirements:
- **Format**: Valid Fernet key (starts with 'gAAAAAB')
- **Length**: Exactly 88 characters (base64-encoded)
- **Type**: Symmetric encryption key
- **Usage**: Tenant configuration encryption (ENCRYPTION_KEY)
- **Critical**: Loss of this key means tenant configs cannot be decrypted. Store backups in secure location.

## Kubernetes Secrets Configuration

### 1. Create k8s/secrets.yaml

Copy the example template:

```bash
cp k8s/secrets.yaml.example k8s/secrets.yaml
```

### 2. Base64 Encode Secrets

Kubernetes stores secrets in base64 encoding. Encode each secret value:

```bash
# PostgreSQL Password
echo -n "your-generated-password" | base64

# Redis Password  
echo -n "your-generated-password" | base64

# OpenAI API Key
echo -n "sk-proj-your-actual-key" | base64

# Encryption Key
echo -n "gAAAAABlwXxk..." | base64
```

### 3. Update k8s/secrets.yaml

Replace the example values with your base64-encoded secrets:

```yaml
data:
  postgres-password: <base64-encoded-password>
  redis-password: <base64-encoded-password>
  openai-api-key: <base64-encoded-api-key>
  encryption-key: <base64-encoded-fernet-key>
```

### 4. Deploy to Kubernetes

```bash
# Apply the Secret resource
kubectl apply -f k8s/secrets.yaml

# Verify creation
kubectl get secret app-secrets -o yaml

# Describe for details
kubectl describe secret app-secrets
```

### 5. Verify Pod Mounting

After deploying pods with secret mounts:

```bash
# Check environment variables in pod
kubectl exec <pod-name> -- env | grep -E "POSTGRES|REDIS|OPENAI|ENCRYPTION"

# Check logs for secret loading confirmation
kubectl logs <pod-name> | grep "Secrets loaded"
```

## Local Development (.env File)

### 1. Create .env.example

The project includes `.env.example` with placeholder values:

```bash
# Copy template for local development
cp .env.example .env
```

### 2. Fill in Local Development Secrets

Edit `.env` with your local values (NOT base64 encoded - plain text):

```env
POSTGRES_PASSWORD=your-local-dev-password
REDIS_PASSWORD=your-local-dev-password
OPENAI_API_KEY=sk-proj-your-test-key
ENCRYPTION_KEY=gAAAAABlwXxk...
```

### 3. Verify .env is Ignored

Confirm `.env` is in .gitignore:

```bash
git check-ignore .env
```

Output should be: `.env`

### 4. Application Loads Secrets Automatically

When running locally:
1. Application detects local environment (no KUBERNETES_SERVICE_HOST)
2. Loads secrets from `.env` via python-dotenv
3. Validates all required secrets present
4. Logs "Secrets loaded successfully" if valid

## Security Best Practices

### Do's ✅

- ✅ Generate passwords with cryptographically secure tools (`openssl rand`)
- ✅ Store encryption key backups in secure location (password manager, HSM)
- ✅ Rotate API keys quarterly
- ✅ Rotate passwords every 6 months
- ✅ Use RBAC to limit Secret access to authorized service accounts
- ✅ Enable encryption at rest in Kubernetes etcd
- ✅ Never log or expose secret values in application logs
- ✅ Use strong, unique secrets for each environment (dev, staging, prod)

### Don'ts ❌

- ❌ Don't use weak passwords (e.g., "password123")
- ❌ Don't commit actual secrets to git
- ❌ Don't share secrets via email or Slack
- ❌ Don't use base64 encoding for protection (it's just encoding, not encryption)
- ❌ Don't reuse the same Encryption Key across environments
- ❌ Don't manually rotate encryption keys without data migration plan
- ❌ Don't log environment variables during startup

## Troubleshooting

### Secret Not Mounted in Pod

```bash
# Check Secret exists
kubectl get secret app-secrets

# Check pod spec references correct Secret name
kubectl get deployment api-deployment -o yaml | grep -A20 "env:"

# Verify deployment updated after Secret creation
kubectl rollout restart deployment/api-deployment
```

### Application Fails to Start: "Missing OPENAI_API_KEY"

1. Verify Secret created: `kubectl get secret app-secrets`
2. Check pod environment: `kubectl exec <pod-name> -- env | grep OPENAI`
3. If empty, redeploy: `kubectl rollout restart deployment/api-deployment`
4. Check logs: `kubectl logs <pod-name>`

### Base64 Encoding Issues

```bash
# Verify base64 encoding is correct
echo "your-secret" | base64 | base64 -d  # Should output your-secret

# Decode existing Secret value to verify
kubectl get secret app-secrets -o jsonpath='{.data.postgres-password}' | base64 -d
```

## References

- [Kubernetes Secrets Documentation](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Kubernetes Secrets Best Practices](https://kubernetes.io/docs/concepts/security/secrets-good-practices/)
- [Secret Rotation Runbook](./secret-rotation.md)
- [Application Configuration](../config.md)
