#!/bin/bash
# Test Ticket Enhancer Agent with actual agent ID
# Agent: 00bab7b6-6335-4359-96b4-f48f3460b610
# Tenant: Test1

set -e

echo "🚀 Testing Ticket Enhancer Agent..."
echo ""
echo "Agent ID: 00bab7b6-6335-4359-96b4-f48f3460b610"
echo "Tenant: Test1"
echo ""

# Create test webhook payload (simulating Jira webhook)
PAYLOAD=$(cat <<EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%S.000+0000)",
  "webhookEvent": "jira:issue_created",
  "issue_event_type_name": "issue_created",
  "issue": {
    "id": "10003",
    "key": "KAN-3",
    "fields": {
      "summary": "Database connection timeout",
      "description": "Users experiencing timeout errors when connecting to production database",
      "issuetype": {
        "name": "Bug"
      },
      "priority": {
        "name": "High"
      },
      "status": {
        "name": "To Do"
      }
    }
  }
}
EOF
)

# Send request to webhook endpoint
echo "📤 Sending webhook request..."
echo ""

RESPONSE=$(curl -s -X POST http://localhost:3000/webhook/Test1 \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

echo "📥 Response:"
echo "$RESPONSE" | python3 -m json.tool || echo "$RESPONSE"
echo ""

# Extract execution ID if present
EXECUTION_ID=$(echo "$RESPONSE" | grep -oE '"execution_id":"[^"]+' | cut -d'"' -f4)

if [ -n "$EXECUTION_ID" ]; then
    echo "✅ Webhook accepted! Execution ID: $EXECUTION_ID"
    echo ""
    echo "📊 Monitor execution:"
    echo "   docker-compose logs worker -f | grep $EXECUTION_ID"
    echo ""
    echo "🔍 Check execution in Streamlit:"
    echo "   Navigate to Execution History page"
else
    echo "⚠️  No execution ID in response"
fi

echo ""
echo "🔄 Worker logs (last 30 lines):"
docker-compose logs worker --tail 30
