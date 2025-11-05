#!/bin/bash
# Setup script for Streamlit Admin UI basic authentication
#
# This script creates an htpasswd file and Kubernetes secret for
# NGINX Ingress basic authentication.
#
# Usage:
#   ./scripts/setup-streamlit-auth.sh [username] [password]
#
# Default credentials:
#   Username: admin
#   Password: admin (change this in production!)

set -e

# Configuration
NAMESPACE="ai-agents"
SECRET_NAME="streamlit-basic-auth"
HTPASSWD_FILE="/tmp/htpasswd"

# Get credentials from args or use defaults
USERNAME="${1:-admin}"
PASSWORD="${2:-admin}"

echo "🔐 Setting up Streamlit Admin UI Basic Authentication"
echo "=================================================="
echo ""
echo "Namespace: ${NAMESPACE}"
echo "Secret Name: ${SECRET_NAME}"
echo "Username: ${USERNAME}"
echo ""

# Check if htpasswd is installed
if ! command -v htpasswd &> /dev/null; then
    echo "❌ htpasswd command not found!"
    echo ""
    echo "Please install apache2-utils (Debian/Ubuntu) or httpd-tools (RHEL/CentOS):"
    echo "  - Ubuntu/Debian: sudo apt-get install apache2-utils"
    echo "  - RHEL/CentOS:   sudo yum install httpd-tools"
    echo "  - macOS:         brew install httpd"
    exit 1
fi

# Create htpasswd file
echo "📝 Creating htpasswd file..."
htpasswd -bc ${HTPASSWD_FILE} ${USERNAME} ${PASSWORD}

# Check if secret already exists
if kubectl get secret ${SECRET_NAME} -n ${NAMESPACE} &> /dev/null; then
    echo "⚠️  Secret '${SECRET_NAME}' already exists in namespace '${NAMESPACE}'"
    echo ""
    read -p "Do you want to delete and recreate it? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Deleting existing secret..."
        kubectl delete secret ${SECRET_NAME} -n ${NAMESPACE}
    else
        echo "❌ Aborted. Secret not modified."
        rm -f ${HTPASSWD_FILE}
        exit 0
    fi
fi

# Create Kubernetes secret
echo "🔑 Creating Kubernetes secret..."
kubectl create secret generic ${SECRET_NAME} \
    --from-file=auth=${HTPASSWD_FILE} \
    --namespace=${NAMESPACE}

# Clean up
rm -f ${HTPASSWD_FILE}

echo ""
echo "✅ Authentication setup complete!"
echo ""
echo "The Streamlit Admin UI will now require basic authentication:"
echo "  Username: ${USERNAME}"
echo "  Password: ${PASSWORD}"
echo ""
echo "To access the admin UI:"
echo "  1. Ensure /etc/hosts has: 127.0.0.1 admin.ai-agents.local"
echo "  2. Apply Kubernetes manifests: kubectl apply -f k8s/streamlit-admin-*.yaml"
echo "  3. Open browser: http://admin.ai-agents.local"
echo "  4. Enter credentials when prompted"
echo ""
echo "⚠️  IMPORTANT: Change default credentials in production!"
echo ""
