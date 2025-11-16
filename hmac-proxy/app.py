"""
HMAC Webhook Proxy for Jira Integration with Dynamic Agent Routing.

This service receives webhooks from Jira (which cannot compute HMAC signatures),
computes the HMAC-SHA256 signature, and forwards the request to the AI Ops API
with the proper authentication header.

Features:
- Dynamic agent routing based on payload (agent_id or agent_name)
- Fallback to default agent if not specified
- Agent lookup and validation via AI Ops API
- Multi-agent support without restarts

Flow:
    Jira → POST /jira-webhook (no signature)
         → HMAC Proxy extracts agent identifier from payload
         → Looks up agent endpoint from AI Ops API
         → Computes HMAC signature
         → POST to agent-specific webhook with X-Hub-Signature-256 header
         → Returns response to Jira
"""

import base64
import hashlib
import hmac
import json
import os
from typing import Any, Optional

import httpx
from fastapi import FastAPI, HTTPException, Request
from loguru import logger

# Configuration
HMAC_SECRET = os.getenv("HMAC_SECRET")  # Base64-encoded secret key
API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")  # AI Ops API base URL
DEFAULT_AGENT_ID = os.getenv("DEFAULT_AGENT_ID")  # Fallback agent ID (optional)
TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", "30"))
AGENT_CACHE_TTL = int(os.getenv("AGENT_CACHE_TTL", "300"))  # Cache agents for 5 minutes

# Validate configuration
if not HMAC_SECRET:
    raise ValueError("HMAC_SECRET environment variable is required")

# Agent cache to minimize API calls
agent_cache: dict[str, dict[str, Any]] = {}

app = FastAPI(
    title="HMAC Webhook Proxy",
    description="Adds HMAC signatures to Jira webhooks before forwarding to AI Ops API",
    version="2.0.0",
)


async def lookup_agent(agent_identifier: str) -> Optional[dict[str, Any]]:
    """
    Look up agent by ID or name from AI Ops API.

    Args:
        agent_identifier: Agent UUID or agent name

    Returns:
        Agent dict with id, name, and webhook_url, or None if not found

    Raises:
        HTTPException: If API lookup fails
    """
    # Check cache first
    if agent_identifier in agent_cache:
        cached_agent = agent_cache[agent_identifier]
        logger.debug(f"Agent found in cache: {agent_identifier}")
        return cached_agent

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            # Try as UUID first
            try:
                from uuid import UUID
                UUID(agent_identifier)  # Validate UUID format
                endpoint = f"{API_BASE_URL}/api/agents/{agent_identifier}"
            except ValueError:
                # Not a UUID, search by name
                endpoint = f"{API_BASE_URL}/api/agents?name={agent_identifier}"

            logger.info(f"Looking up agent: {endpoint}")
            response = await client.get(endpoint)

            if response.status_code == 404:
                logger.warning(f"Agent not found: {agent_identifier}")
                return None

            if response.status_code != 200:
                logger.error(f"Agent lookup failed: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to lookup agent: {response.status_code}"
                )

            agent_data = response.json()

            # Handle list response (search by name)
            if isinstance(agent_data, list):
                if not agent_data:
                    logger.warning(f"No agent found with name: {agent_identifier}")
                    return None
                agent_data = agent_data[0]  # Take first match

            # Build agent info
            agent_info = {
                "id": agent_data["id"],
                "name": agent_data["name"],
                "webhook_url": f"{API_BASE_URL}/webhook/agents/{agent_data['id']}/webhook"
            }

            # Cache the result
            agent_cache[agent_identifier] = agent_info
            agent_cache[agent_info["id"]] = agent_info  # Cache by ID too
            logger.info(f"Agent cached: {agent_info['name']} ({agent_info['id']})")

            return agent_info

    except httpx.HTTPError as e:
        logger.error(f"HTTP error during agent lookup: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Agent lookup failed: {str(e)}"
        )


def compute_hmac_signature(payload_json: str, secret: str) -> str:
    """
    Compute HMAC-SHA256 signature for webhook payload.

    Args:
        payload_json: JSON string of the payload (sorted keys for consistency)
        secret: Base64-encoded HMAC secret key

    Returns:
        Signature in format: sha256={hexdigest}
    """
    try:
        # Decode base64 secret to bytes
        secret_bytes = base64.b64decode(secret)
    except Exception as e:
        logger.error(f"Failed to decode HMAC secret: {e}")
        raise ValueError("Invalid HMAC secret format") from e

    # Compute HMAC-SHA256 signature
    signature = hmac.new(
        secret_bytes, payload_json.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    return f"sha256={signature}"


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "hmac-proxy",
        "version": "2.0.0",
        "features": ["dynamic-routing", "agent-lookup", "caching"],
        "api_base_url": API_BASE_URL,
        "default_agent_id": DEFAULT_AGENT_ID or "not-configured",
        "cached_agents": len(agent_cache),
    }


@app.post("/jira-webhook")
async def proxy_jira_webhook(request: Request) -> dict[str, Any]:
    """
    Receive Jira webhook, dynamically route to appropriate agent, compute HMAC signature,
    and forward to AI Ops API.

    Routing Logic:
    1. Check payload for 'agent_id' or 'agent_name' field
    2. If not found, use DEFAULT_AGENT_ID (if configured)
    3. Look up agent endpoint via AI Ops API
    4. Compute HMAC signature and forward

    Args:
        request: FastAPI request object containing Jira webhook payload

    Returns:
        Response from AI Ops API

    Raises:
        HTTPException: If proxy operation fails or agent not found
    """
    try:
        # 1. Parse incoming Jira webhook payload
        payload = await request.json()
        issue_key = payload.get('issue_key', 'unknown')
        logger.info(f"Received Jira webhook: {issue_key}")

        # 2. Extract agent identifier from payload (or use default)
        agent_identifier = (
            payload.get('agent_id') or
            payload.get('agent_name') or
            DEFAULT_AGENT_ID
        )

        if not agent_identifier:
            logger.error("No agent identifier in payload and no default configured")
            raise HTTPException(
                status_code=400,
                detail="Missing agent_id or agent_name in payload, and no DEFAULT_AGENT_ID configured"
            )

        logger.info(f"Routing to agent: {agent_identifier}")

        # 3. Look up agent endpoint
        agent = await lookup_agent(agent_identifier)

        if not agent:
            logger.error(f"Agent not found: {agent_identifier}")
            raise HTTPException(
                status_code=404,
                detail=f"Agent not found: {agent_identifier}"
            )

        target_url = agent["webhook_url"]
        logger.info(f"Agent resolved: {agent['name']} -> {target_url}")

        # 4. Serialize payload with sorted keys for consistent signature
        payload_json = json.dumps(payload, sort_keys=True)

        # 5. Compute HMAC-SHA256 signature
        signature = compute_hmac_signature(payload_json, HMAC_SECRET)
        logger.debug(f"Computed HMAC signature: {signature[:20]}...")

        # 6. Forward to AI Ops API with signature header
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            logger.info(f"Forwarding to: {target_url}")

            response = await client.post(
                target_url,
                content=payload_json,  # Use same serialized payload
                headers={
                    "Content-Type": "application/json",
                    "X-Hub-Signature-256": signature,
                },
            )

            # Log response
            logger.info(
                f"AI Ops API response: {response.status_code} - {response.text[:100]}"
            )

            # 7. Return AI Ops API response to Jira
            if response.status_code >= 400:
                logger.error(f"AI Ops API error: {response.status_code} - {response.text}")

            return response.json()

    except httpx.TimeoutException:
        logger.error(f"Timeout forwarding webhook")
        raise HTTPException(
            status_code=504,
            detail=f"Timeout forwarding webhook to AI Ops API (>{TIMEOUT_SECONDS}s)",
        )

    except httpx.HTTPError as e:
        logger.error(f"HTTP error forwarding webhook: {e}")
        raise HTTPException(
            status_code=502, detail=f"Failed to forward webhook: {str(e)}"
        )

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    except Exception as e:
        logger.error(f"Unexpected error in proxy: {e}")
        raise HTTPException(
            status_code=500, detail=f"Proxy error: {str(e)}"
        )


@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint with service information."""
    return {
        "service": "HMAC Webhook Proxy",
        "version": "2.0.0",
        "features": ["dynamic-routing", "agent-lookup", "caching"],
        "endpoints": {
            "health": "/health (GET)",
            "webhook": "/jira-webhook (POST)",
        },
        "routing": {
            "payload_fields": ["agent_id", "agent_name"],
            "fallback": DEFAULT_AGENT_ID or "not-configured",
        },
        "cached_agents": len(agent_cache),
    }


@app.post("/cache/clear")
async def clear_cache() -> dict[str, str]:
    """Clear the agent cache (useful for testing or after agent updates)."""
    agent_cache.clear()
    logger.info("Agent cache cleared")
    return {"status": "cache_cleared", "message": "All cached agents have been removed"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=3000, log_level="info")
