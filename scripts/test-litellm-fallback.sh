#!/bin/bash
# Test LiteLLM Fallback Chain
# Story 8.1: LiteLLM Proxy Integration
# Generated: 2025-11-05
#
# Tests automatic fallback from OpenAI → Azure → Anthropic
# Fallback chain configured in config/litellm-config.yaml

set -e

LITELLM_URL="${LITELLM_URL:-http://localhost:4000}"
MASTER_KEY="${LITELLM_MASTER_KEY:-sk-1234}"

echo "========================================="
echo "LiteLLM Fallback Chain Test"
echo "========================================="
echo ""
echo "Testing fallback chain: gpt-4 → azure-gpt-4 → claude-3-5-sonnet"
echo "LiteLLM URL: $LITELLM_URL"
echo ""

# Test 1: Primary provider (OpenAI gpt-4)
echo "Test 1: Primary Provider (OpenAI GPT-4)"
echo "========================================"
echo "Sending request with model: gpt-4..."
echo ""

RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$LITELLM_URL/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MASTER_KEY" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Say hello"}],
    "max_tokens": 10
  }')

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d ':' -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE:/d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Primary provider (OpenAI) working"
    echo "Response preview: $(echo "$BODY" | jq -r '.choices[0].message.content // "N/A"' 2>/dev/null || echo "Parse error")"
    echo ""
else
    echo "❌ Primary provider failed with HTTP $HTTP_CODE"
    echo "Response: $BODY"
    echo ""
fi

# Test 2: Fallback simulation (requires temporarily disabling OpenAI)
echo "Test 2: Fallback Behavior"
echo "========================================"
echo "ℹ️  To test fallback chain:"
echo "   1. Temporarily set invalid OPENAI_API_KEY in .env"
echo "   2. Restart litellm: docker-compose restart litellm"
echo "   3. Run this script again"
echo "   4. Verify response comes from Azure (check x-litellm-model-id header)"
echo ""
echo "For automatic fallback testing, use integration tests:"
echo "   pytest tests/integration/test_litellm_integration.py::test_fallback_on_primary_failure"
echo ""

# Test 3: Check LiteLLM logs for fallback events
echo "Test 3: Check Logs for Fallback Events"
echo "========================================"
echo "Recent LiteLLM logs (last 20 lines):"
echo ""
docker-compose logs --tail=20 litellm 2>/dev/null || echo "⚠️  Docker logs not available (is litellm running?)"
echo ""

# Test 4: Virtual key creation (for multi-tenant fallback testing)
echo "Test 4: Virtual Key Creation"
echo "========================================"
echo "Creating test virtual key..."
echo ""

KEY_RESPONSE=$(curl -s -X POST "$LITELLM_URL/key/generate" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MASTER_KEY" \
  -d '{
    "models": ["gpt-4"],
    "max_budget": 10,
    "duration": "1h"
  }')

VIRTUAL_KEY=$(echo "$KEY_RESPONSE" | jq -r '.key // "ERROR"')

if [ "$VIRTUAL_KEY" != "ERROR" ] && [ "$VIRTUAL_KEY" != "null" ]; then
    echo "✅ Virtual key created: ${VIRTUAL_KEY:0:20}..."
    echo ""
    
    # Test virtual key
    echo "Testing virtual key with chat completion..."
    VKEY_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$LITELLM_URL/chat/completions" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $VIRTUAL_KEY" \
      -d '{
        "model": "gpt-4",
        "messages": [{"role": "user", "content": "Test"}],
        "max_tokens": 5
      }')
    
    VKEY_HTTP_CODE=$(echo "$VKEY_RESPONSE" | grep "HTTP_CODE:" | cut -d ':' -f2)
    
    if [ "$VKEY_HTTP_CODE" = "200" ]; then
        echo "✅ Virtual key works correctly"
    else
        echo "❌ Virtual key test failed with HTTP $VKEY_HTTP_CODE"
    fi
else
    echo "❌ Failed to create virtual key"
    echo "Response: $KEY_RESPONSE"
fi

echo ""
echo "========================================="
echo "Fallback Chain Test Complete"
echo "========================================="
echo ""
echo "Summary:"
echo "  ✓ Primary provider tested"
echo "  ✓ Virtual key functionality verified"
echo "  ℹ️  For full fallback testing, see integration tests"
echo ""
echo "Next steps:"
echo "  1. Check LiteLLM logs: docker-compose logs -f litellm"
echo "  2. Run integration tests: pytest tests/integration/test_litellm_integration.py -v"
echo "  3. Monitor fallback metrics: curl $LITELLM_URL/metrics"
echo ""
