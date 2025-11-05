#!/bin/bash
# Setup LiteLLM Environment Variables
# Story 8.1: LiteLLM Proxy Integration
# Generated: 2025-11-05
#
# This script helps generate secure random keys for LiteLLM configuration
# Run this script to create or update your .env file with LiteLLM keys

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"

echo "========================================="
echo "LiteLLM Environment Setup Script"
echo "========================================="
echo ""

# Check if .env exists
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ .env file not found"
    echo "📋 Creating .env from .env.example..."
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    echo "✅ Created .env file"
    echo ""
fi

# Generate LITELLM_MASTER_KEY if not set or is placeholder
CURRENT_MASTER_KEY=$(grep "^LITELLM_MASTER_KEY=" "$ENV_FILE" | cut -d '=' -f2- || echo "")
if [ -z "$CURRENT_MASTER_KEY" ] || [ "$CURRENT_MASTER_KEY" = "sk-1234" ]; then
    echo "🔑 Generating LITELLM_MASTER_KEY..."
    NEW_MASTER_KEY="sk-$(openssl rand -hex 16)"
    
    # Update or add LITELLM_MASTER_KEY in .env
    if grep -q "^LITELLM_MASTER_KEY=" "$ENV_FILE"; then
        # macOS sed requires backup extension argument
        sed -i.bak "s|^LITELLM_MASTER_KEY=.*|LITELLM_MASTER_KEY=$NEW_MASTER_KEY|" "$ENV_FILE"
        rm "${ENV_FILE}.bak"  # Remove backup file
    else
        echo "LITELLM_MASTER_KEY=$NEW_MASTER_KEY" >> "$ENV_FILE"
    fi
    
    echo "✅ Generated LITELLM_MASTER_KEY: $NEW_MASTER_KEY"
    echo ""
else
    echo "✓ LITELLM_MASTER_KEY already set"
    echo ""
fi

# Generate LITELLM_SALT_KEY if not set or is placeholder
CURRENT_SALT_KEY=$(grep "^LITELLM_SALT_KEY=" "$ENV_FILE" | cut -d '=' -f2- || echo "")
if [ -z "$CURRENT_SALT_KEY" ] || [[ "$CURRENT_SALT_KEY" == *"your-litellm-salt-key"* ]]; then
    echo "🔐 Generating LITELLM_SALT_KEY..."
    echo "⚠️  WARNING: This key encrypts API credentials in the database"
    echo "⚠️  CRITICAL: Back up this key securely - you CANNOT change it later"
    echo ""
    
    NEW_SALT_KEY=$(openssl rand -base64 32)
    
    # Update or add LITELLM_SALT_KEY in .env
    if grep -q "^LITELLM_SALT_KEY=" "$ENV_FILE"; then
        # macOS sed requires backup extension argument
        sed -i.bak "s|^LITELLM_SALT_KEY=.*|LITELLM_SALT_KEY=$NEW_SALT_KEY|" "$ENV_FILE"
        rm "${ENV_FILE}.bak"  # Remove backup file
    else
        echo "LITELLM_SALT_KEY=$NEW_SALT_KEY" >> "$ENV_FILE"
    fi
    
    echo "✅ Generated LITELLM_SALT_KEY: $NEW_SALT_KEY"
    echo ""
    echo "📌 IMPORTANT: Save this key in a secure vault (1Password, AWS Secrets Manager, etc.)"
    echo "📌 If you lose this key, you will need to re-setup LiteLLM completely"
    echo ""
else
    echo "✓ LITELLM_SALT_KEY already set"
    echo "⚠️  Remember: This key is IMMUTABLE - do not change it"
    echo ""
fi

# Check for required API keys
echo "========================================="
echo "API Key Configuration"
echo "========================================="
echo ""

# OpenAI API Key
OPENAI_KEY=$(grep "^OPENAI_API_KEY=" "$ENV_FILE" | cut -d '=' -f2- || echo "")
if [ -z "$OPENAI_KEY" ] || [[ "$OPENAI_KEY" == *"your-openai-api-key"* ]]; then
    echo "⚠️  OPENAI_API_KEY not set"
    echo "   Get your key from: https://platform.openai.com/account/api-keys"
    echo "   Update OPENAI_API_KEY in .env file"
    echo ""
else
    echo "✓ OPENAI_API_KEY configured"
fi

# Anthropic API Key (optional)
ANTHROPIC_KEY=$(grep "^ANTHROPIC_API_KEY=" "$ENV_FILE" | cut -d '=' -f2- || echo "")
if [ -z "$ANTHROPIC_KEY" ] || [[ "$ANTHROPIC_KEY" == *"your-anthropic-api-key"* ]]; then
    echo "ℹ️  ANTHROPIC_API_KEY not set (optional fallback provider)"
    echo "   Get your key from: https://console.anthropic.com/settings/keys"
    echo "   Update ANTHROPIC_API_KEY in .env file for fallback support"
    echo ""
else
    echo "✓ ANTHROPIC_API_KEY configured (fallback enabled)"
fi

# Azure OpenAI (optional)
AZURE_KEY=$(grep "^AZURE_API_KEY=" "$ENV_FILE" | cut -d '=' -f2- || echo "")
if [ -z "$AZURE_KEY" ] || [[ "$AZURE_KEY" == *"your-azure-openai-api-key"* ]]; then
    echo "ℹ️  AZURE_API_KEY not set (optional fallback provider)"
    echo "   Get your key from: https://portal.azure.com (Azure OpenAI Service)"
    echo "   Update AZURE_API_KEY and AZURE_API_BASE in .env file for fallback support"
    echo ""
else
    echo "✓ AZURE_API_KEY configured (fallback enabled)"
fi

echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Verify API keys in .env file"
echo "2. Start services: docker-compose up -d"
echo "3. Check LiteLLM health: curl http://localhost:4000/health"
echo "4. Test LiteLLM: See README.md for examples"
echo ""
echo "⚠️  Security reminders:"
echo "   - Never commit .env file to git"
echo "   - Back up LITELLM_SALT_KEY securely"
echo "   - Rotate LITELLM_MASTER_KEY regularly (changeable)"
echo ""
