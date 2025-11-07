"""
Integration tests for Agent Webhook API endpoints (Story 8.6, Task 10.2).

Tests webhook endpoint HMAC validation, payload validation, agent status checks,
tenant isolation, and secret regeneration invalidation.

These are CRITICAL tests flagged as "non-negotiable" in code review.
All 7 tests must pass before story can be marked complete.
"""

import json
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.services.webhook_service import compute_hmac_signature

client = TestClient(app)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def test_tenant_id():
    """Test tenant ID for isolation."""
    return "default"  # Use default tenant that exists in database


@pytest.fixture
def test_headers(test_tenant_id):
    """Headers with tenant ID."""
    return {
        "X-Tenant-ID": test_tenant_id,
        "Content-Type": "application/json",
    }


@pytest.fixture
def valid_agent_payload():
    """Valid agent creation payload with webhook trigger."""
    return {
        "name": "Webhook Test Agent",
        "description": "Agent for webhook integration testing",
        "system_prompt": "You are a test agent.",
        "llm_config": {
            "provider": "litellm",
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 4096,
        },
        "status": "active",  # Must be active to accept webhooks
        "created_by": "test@example.com",
        "tool_ids": ["servicedesk_plus"],
        "triggers": [
            {
                "trigger_type": "webhook",
                "payload_schema": {
                    "type": "object",
                    "properties": {
                        "ticket_id": {"type": "string"},
                        "priority": {"type": "string"},
                    },
                    "required": ["ticket_id"],
                },
            }
        ],
    }


@pytest.fixture
def draft_agent_payload(valid_agent_payload):
    """Agent payload with draft status (should reject webhooks)."""
    payload = valid_agent_payload.copy()
    payload["status"] = "draft"
    payload["name"] = "Draft Agent"
    return payload


@pytest.fixture
def created_agent(test_headers, valid_agent_payload):
    """Create an active agent with webhook trigger and return response."""
    response = client.post("/api/agents", json=valid_agent_payload, headers=test_headers)
    assert response.status_code == 201, f"Agent creation failed: {response.text}"
    return response.json()


@pytest.fixture
def draft_agent(test_headers, draft_agent_payload):
    """Create a draft agent (inactive) and return response."""
    response = client.post("/api/agents", json=draft_agent_payload, headers=test_headers)
    assert response.status_code == 201, f"Draft agent creation failed: {response.text}"
    return response.json()


@pytest.fixture
def valid_webhook_payload():
    """Valid webhook payload matching agent's schema."""
    return {"ticket_id": "T-12345", "priority": "high", "description": "Test ticket"}


@pytest.fixture
def invalid_webhook_payload():
    """Invalid webhook payload (missing required field)."""
    return {"priority": "high", "description": "Missing ticket_id"}


def get_hmac_headers(payload: dict, secret: str) -> dict:
    """
    Compute HMAC signature for payload.

    Args:
        payload: JSON payload dict
        secret: HMAC secret string (base64-encoded)

    Returns:
        dict: Headers with X-Hub-Signature-256
    """
    payload_bytes = json.dumps(payload).encode("utf-8")
    signature = compute_hmac_signature(payload_bytes, secret)
    return {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": f"sha256={signature}",
    }


# ============================================================================
# Integration Tests (Task 10.2 - ALL 7 REQUIRED TESTS)
# ============================================================================


def test_webhook_endpoint_valid_signature(created_agent, valid_webhook_payload):
    """
    Test 1/7: Valid HMAC signature and payload → 202 Accepted.

    AC#6: Webhook endpoint validates HMAC signature and enqueues agent task.
    Expected: 202 Accepted with execution_id.
    """
    agent_id = created_agent["id"]
    webhook_url = created_agent.get("webhook_url")
    assert webhook_url, "Webhook URL not generated"

    # Extract HMAC secret (should be masked in response, need to fetch)
    # For test purposes, we'll use a known test secret or fetch from API
    # NOTE: In real scenario, use GET /api/agents/{id}/webhook-secret
    # For this test, we'll mock/use the creation response if available

    # Simplified: Use test client to get secret
    secret_response = client.get(f"/api/agents/{agent_id}/webhook-secret")
    assert secret_response.status_code == 200, "Failed to fetch webhook secret"
    hmac_secret = secret_response.json()["hmac_secret"]

    # Compute HMAC signature
    headers = get_hmac_headers(valid_webhook_payload, hmac_secret)

    # Send webhook request
    webhook_path = f"/webhook/agents/{agent_id}/webhook"
    response = client.post(webhook_path, json=valid_webhook_payload, headers=headers)

    # Assertions
    assert response.status_code == 202, f"Expected 202, got {response.status_code}: {response.text}"
    response_data = response.json()
    assert "execution_id" in response_data, "execution_id missing in response"
    assert response_data["status"] == "queued", "Status should be 'queued'"


def test_webhook_endpoint_invalid_signature(created_agent, valid_webhook_payload):
    """
    Test 2/7: Invalid HMAC signature → 401 Unauthorized.

    AC#6: Webhook endpoint validates HMAC signature using constant-time comparison.
    Expected: 401 Unauthorized with "Invalid HMAC signature" error.
    """
    agent_id = created_agent["id"]
    webhook_path = f"/webhook/agents/{agent_id}/webhook"

    # Use WRONG signature
    headers = {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": "sha256=invalid_signature_12345",
    }

    response = client.post(webhook_path, json=valid_webhook_payload, headers=headers)

    # Assertions
    assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
    response_data = response.json()
    assert (
        "HMAC" in response_data.get("detail", "").upper()
        or "signature" in response_data.get("detail", "").lower()
    ), f"Error message should mention HMAC/signature: {response_data}"


def test_webhook_endpoint_payload_validation_fail(created_agent, invalid_webhook_payload):
    """
    Test 3/7: Invalid payload against schema → 400 Bad Request.

    AC#7: Payload validation using JSON Schema Draft 2020-12.
    Expected: 400 Bad Request with validation error details.
    """
    agent_id = created_agent["id"]
    webhook_path = f"/webhook/agents/{agent_id}/webhook"

    # Fetch HMAC secret
    secret_response = client.get(f"/api/agents/{agent_id}/webhook-secret")
    hmac_secret = secret_response.json()["hmac_secret"]

    # Compute valid signature for INVALID payload
    headers = get_hmac_headers(invalid_webhook_payload, hmac_secret)

    response = client.post(webhook_path, json=invalid_webhook_payload, headers=headers)

    # Assertions
    assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
    response_data = response.json()
    assert (
        "validation" in response_data.get("detail", "").lower()
        or "ticket_id" in response_data.get("detail", "").lower()
    ), f"Error should mention validation failure: {response_data}"


def test_webhook_endpoint_agent_not_found(valid_webhook_payload):
    """
    Test 4/7: Non-existent agent_id → 404 Not Found.

    Expected: 404 Not Found when agent doesn't exist.
    """
    fake_agent_id = "00000000-0000-0000-0000-000000000000"
    webhook_path = f"/webhook/agents/{fake_agent_id}/webhook"

    # Use any signature (will fail at agent lookup before signature check)
    headers = {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": "sha256=dummy_signature",
    }

    response = client.post(webhook_path, json=valid_webhook_payload, headers=headers)

    # Assertions
    assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
    response_data = response.json()
    assert (
        "not found" in response_data.get("detail", "").lower()
    ), f"Error should mention 'not found': {response_data}"


def test_webhook_endpoint_agent_inactive(draft_agent, valid_webhook_payload):
    """
    Test 5/7: Agent status != ACTIVE → 403 Forbidden.

    AC#6: Only ACTIVE agents can be triggered via webhook.
    Expected: 403 Forbidden for draft/suspended agents.
    """
    agent_id = draft_agent["id"]
    webhook_path = f"/webhook/agents/{agent_id}/webhook"

    # Fetch HMAC secret
    secret_response = client.get(f"/api/agents/{agent_id}/webhook-secret")
    hmac_secret = secret_response.json()["hmac_secret"]

    # Compute valid signature
    headers = get_hmac_headers(valid_webhook_payload, hmac_secret)

    response = client.post(webhook_path, json=valid_webhook_payload, headers=headers)

    # Assertions
    assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
    response_data = response.json()
    assert (
        "active" in response_data.get("detail", "").lower()
        or "status" in response_data.get("detail", "").lower()
    ), f"Error should mention agent status: {response_data}"


def test_webhook_endpoint_cross_tenant_access(created_agent, valid_webhook_payload):
    """
    Test 6/7: Webhook from different tenant → 403 Forbidden.

    Multi-tenancy constraint: Enforce tenant isolation in webhook validation.
    Expected: 403 Forbidden when tenant mismatch detected.
    """
    agent_id = created_agent["id"]
    webhook_path = f"/webhook/agents/{agent_id}/webhook"

    # Fetch HMAC secret using CORRECT tenant
    secret_response = client.get(f"/api/agents/{agent_id}/webhook-secret")
    hmac_secret = secret_response.json()["hmac_secret"]

    # Compute valid signature
    headers = get_hmac_headers(valid_webhook_payload, hmac_secret)

    # Send webhook with DIFFERENT tenant header (simulating cross-tenant attack)
    headers["X-Tenant-ID"] = "different-tenant-attacker"

    response = client.post(webhook_path, json=valid_webhook_payload, headers=headers)

    # Assertions
    # NOTE: Actual behavior depends on implementation of tenant isolation
    # Expected: Either 403 Forbidden or 404 Not Found (tenant scoped query)
    assert response.status_code in [
        403,
        404,
    ], f"Expected 403 or 404 for cross-tenant access, got {response.status_code}: {response.text}"


def test_regenerate_secret_invalidates_old_webhooks(created_agent, valid_webhook_payload):
    """
    Test 7/7: Regenerating secret invalidates old HMAC signatures.

    AC#5: "Regenerate Secret" button creates new HMAC secret, invalidates old webhooks.
    Expected: Old signature fails after regeneration (401 Unauthorized).
    """
    agent_id = created_agent["id"]
    webhook_path = f"/webhook/agents/{agent_id}/webhook"

    # Step 1: Fetch original HMAC secret
    secret_response = client.get(f"/api/agents/{agent_id}/webhook-secret")
    old_hmac_secret = secret_response.json()["hmac_secret"]

    # Step 2: Compute signature with old secret
    old_headers = get_hmac_headers(valid_webhook_payload, old_hmac_secret)

    # Step 3: Verify webhook works with old secret
    response_before = client.post(webhook_path, json=valid_webhook_payload, headers=old_headers)
    assert (
        response_before.status_code == 202
    ), f"Webhook should work before regeneration, got {response_before.status_code}"

    # Step 4: Regenerate secret
    regenerate_response = client.post(f"/api/agents/{agent_id}/regenerate-webhook-secret")
    assert (
        regenerate_response.status_code == 200
    ), f"Secret regeneration failed: {regenerate_response.text}"

    # Step 5: Try using OLD signature (should fail with 401)
    response_after = client.post(webhook_path, json=valid_webhook_payload, headers=old_headers)

    # Assertions
    assert (
        response_after.status_code == 401
    ), f"Old signature should fail after regeneration, got {response_after.status_code}: {response_after.text}"
    response_data = response_after.json()
    assert (
        "HMAC" in response_data.get("detail", "").upper()
        or "signature" in response_data.get("detail", "").lower()
    ), f"Error should mention HMAC/signature: {response_data}"

    # Step 6: Verify NEW signature works
    new_secret_response = client.get(f"/api/agents/{agent_id}/webhook-secret")
    new_hmac_secret = new_secret_response.json()["hmac_secret"]
    new_headers = get_hmac_headers(valid_webhook_payload, new_hmac_secret)

    response_new = client.post(webhook_path, json=valid_webhook_payload, headers=new_headers)
    assert (
        response_new.status_code == 202
    ), f"New signature should work after regeneration, got {response_new.status_code}: {response_new.text}"
