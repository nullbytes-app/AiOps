"""
Agent Management UI Helpers - Async API, formatting, and validation utilities.

Provides:
- Async HTTP API client functions for agent CRUD
- Sync wrappers for Streamlit context
- Status badge and datetime formatting
- Form validation logic

This module enables the main Agent Management page to stay under 500 lines.
"""

import asyncio
import os
from datetime import datetime
from typing import Optional

import httpx
import streamlit as st

# ============================================================================
# Configuration
# ============================================================================

API_BASE_URL: str = os.getenv("API_BASE_URL", "http://api:8000")  # Use 'api' service in Docker
DEFAULT_TENANT_ID: str = "default"  # TODO: Get from session/JWT in production

# Tool definitions
AVAILABLE_TOOLS = {
    "servicedesk_plus": "ServiceDesk Plus - Ticket management",
    "jira": "Jira Service Management - Issue tracking",
    "knowledge_base": "Knowledge Base - Documentation search",
    "monitoring": "Monitoring - System metrics",
    "logs": "Logs - Event and error logs",
}

# System prompt templates
PROMPT_TEMPLATES = {
    "Ticket Enhancement": """You are a helpful AI assistant specialized in enhancing support tickets.
Your role is to:
1. Analyze ticket content and context
2. Suggest improvements and additions
3. Identify relevant knowledge base articles
4. Recommend similar tickets for reference

Always maintain a professional tone and focus on clarity and completeness.""",
    "RCA Analysis": """You are an expert in Root Cause Analysis (RCA).
Your role is to:
1. Analyze incident reports and logs
2. Identify root causes systematically
3. Suggest preventive measures
4. Create actionable remediation steps

Follow the 5 Whys methodology in your analysis.""",
    "General Purpose": """You are a helpful AI assistant.
Your role is to:
1. Understand user requests
2. Provide accurate and helpful responses
3. Ask clarifying questions when needed
4. Maintain context across conversations

Be concise, professional, and solution-focused.""",
}


# ============================================================================
# Formatting Functions
# ============================================================================


def format_status_badge(status: str) -> str:
    """
    Format agent status as a colored badge.

    Args:
        status: Agent status (draft, active, suspended, inactive)

    Returns:
        str: Formatted status badge with emoji
    """
    status_map = {
        "draft": "⚪ Draft",
        "active": "🟢 Active",
        "suspended": "🟡 Suspended",
        "inactive": "🔴 Inactive",
    }
    return status_map.get(status, f"❓ {status}")


def format_datetime(dt: Optional[str]) -> str:
    """
    Convert ISO datetime string to readable format.

    Args:
        dt: ISO formatted datetime string or None

    Returns:
        str: Readable datetime (e.g., "Nov 5, 2025 2:30 PM") or "Never"
    """
    if not dt:
        return "Never"
    try:
        parsed = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        return parsed.strftime("%b %d, %Y %I:%M %p")
    except (ValueError, AttributeError):
        return dt


def copy_to_clipboard(text: str) -> None:
    """
    Copy text to clipboard with visual feedback.

    Note: Actual clipboard requires JavaScript or external library.
    For now, shows info message to user.

    Args:
        text: Text to copy
    """
    st.session_state.clipboard_copied = True
    st.session_state.clipboard_text = text
    st.info("✓ Copied to clipboard! (Copy manually if not auto-copied)")


# ============================================================================
# Form Validation
# ============================================================================


def validate_form_data(
    form_data: dict, strict_tool_validation: bool = False
) -> tuple[bool, list[str], list[str]]:
    """
    Validate agent creation/update form data.

    Args:
        form_data: Dictionary with agent form fields
        strict_tool_validation: If True, no tools selected is an ERROR (blocks submission).
                               If False (default), no tools selected is a WARNING only.

    Returns:
        tuple: (is_valid: bool, errors: list[str], warnings: list[str])
    """
    errors = []
    warnings = []

    # Required fields
    if not form_data.get("name"):
        errors.append("❌ Agent name is required")
    elif len(form_data["name"]) < 3:
        errors.append("❌ Agent name must be at least 3 characters")

    if not form_data.get("system_prompt"):
        errors.append("❌ System prompt is required")
    elif len(form_data["system_prompt"]) < 10:
        errors.append("❌ System prompt must be at least 10 characters")

    if not form_data.get("model"):
        errors.append("❌ LLM model is required")

    # Tool validation (AC#7, Task 5.2: configurable warning or error)
    # Check BOTH OpenAPI tools AND MCP tool assignments (Story 11.1.6)
    has_openapi_tools = bool(form_data.get("tools"))
    has_mcp_tools = bool(form_data.get("mcp_tool_assignments"))

    if not has_openapi_tools and not has_mcp_tools:
        if strict_tool_validation:
            errors.append("❌ At least one tool must be selected")
        else:
            warnings.append("⚠️ No tools selected. Agent will have limited capabilities.")

    # Temperature validation
    try:
        temp = float(form_data.get("temperature", 0.7))
        if not (0.0 <= temp <= 2.0):
            errors.append("❌ Temperature must be between 0 and 2")
    except (ValueError, TypeError):
        errors.append("❌ Temperature must be a number")

    # Max tokens validation
    try:
        tokens = int(form_data.get("max_tokens", 4096))
        if not (1 <= tokens <= 32000):
            errors.append("❌ Max tokens must be between 1 and 32000")
    except (ValueError, TypeError):
        errors.append("❌ Max tokens must be an integer")

    return len(errors) == 0, errors, warnings


# ============================================================================
# Tool Usage Tracking (Story 8.7, Task 4)
# ============================================================================


@st.cache_data(ttl=60)
def get_tool_usage_stats() -> dict[str, int]:
    """
    Query database to count agents using each tool.

    Caches results for 60 seconds to reduce database load.
    Queries via API endpoint for tool usage statistics.

    Returns:
        dict: Mapping of tool_id -> agent_count
        Example: {"servicedesk_plus": 5, "jira": 3, "knowledge_base": 8}
    """
    try:
        # Get tenant_id from session state or environment (FIX: No hardcoded DEFAULT_TENANT_ID)
        tenant_id = (
            st.session_state.get("selected_agent_tenant_id")
            or st.session_state.get("tenant_id")
            or os.getenv("AI_AGENTS_DEFAULT_TENANT_ID", os.getenv("DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000001"))
        )

        # Use synchronous httpx client for cached function
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{API_BASE_URL}/api/agents/tool-usage-stats",
                headers={"X-Tenant-ID": tenant_id},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("tool_usage", {})
    except httpx.HTTPStatusError as e:
        # Silently return empty dict if tenant doesn't exist (no tenants configured yet)
        if e.response.status_code == 500 and "Invalid tenant_id" in e.response.text:
            return {}
        # Show warning for other errors
        st.warning(f"⚠️ Could not load tool usage stats: {str(e)}")
        return {}
    except httpx.HTTPError as e:
        # Gracefully fallback to empty dict on network/timeout errors
        st.warning(f"⚠️ Could not load tool usage stats: {str(e)}")
        return {}


@st.cache_data(ttl=300)
def fetch_available_models() -> list[dict[str, any]]:
    """
    Fetch available LLM models from dynamic discovery API.

    Queries /api/llm-models/available endpoint for current available models.
    Caches results for 5 minutes (300s) to minimize API calls while staying
    reasonably fresh. Falls back gracefully to sensible defaults if API unavailable.

    This replaces the hardcoded AVAILABLE_MODELS constant, enabling self-service
    model management without code deploys.

    Returns:
        list[dict]: List of model dicts with id, name, provider, max_tokens, supports_function_calling
        Example: [
            {
                "id": "gpt-4",
                "name": "GPT-4",
                "provider": "openai",
                "max_tokens": 8192,
                "supports_function_calling": True
            }
        ]

    Note:
        Gracefully returns fallback models if API unavailable.
        Falls back to: ["gpt-4", "claude-3-opus-20240229"]
    """
    try:
        # Get tenant_id from session state or environment (FIX: No hardcoded DEFAULT_TENANT_ID)
        tenant_id = (
            st.session_state.get("selected_agent_tenant_id")
            or st.session_state.get("tenant_id")
            or os.getenv("AI_AGENTS_DEFAULT_TENANT_ID", os.getenv("DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000001"))
        )

        # Use synchronous httpx client for cached function
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{API_BASE_URL}/api/llm-models/available",
                headers={"X-Tenant-ID": tenant_id},
            )
            response.raise_for_status()
            data = response.json()

            # Transform response to list of model dicts with 'id' field for st.selectbox
            if isinstance(data, list) and len(data) > 0:
                return data
            else:
                # Empty response, return fallback
                st.warning("⚠️ No models returned from API, using fallback defaults")
                return [
                    {
                        "id": "gpt-4",
                        "name": "GPT-4",
                        "provider": "openai",
                        "max_tokens": 8192,
                        "supports_function_calling": True,
                    },
                    {
                        "id": "claude-3-opus-20240229",
                        "name": "Claude 3 Opus",
                        "provider": "anthropic",
                        "max_tokens": 200000,
                        "supports_function_calling": True,
                    },
                ]
    except httpx.HTTPError as e:
        # Gracefully fallback to default models on API error
        st.warning(f"⚠️ Could not load models from API: {str(e)}")
        return [
            {
                "id": "gpt-4",
                "name": "GPT-4",
                "provider": "openai",
                "max_tokens": 8192,
                "supports_function_calling": True,
            },
            {
                "id": "claude-3-opus-20240229",
                "name": "Claude 3 Opus",
                "provider": "anthropic",
                "max_tokens": 200000,
                "supports_function_calling": True,
            },
        ]


@st.cache_data(ttl=300)
def fetch_prompt_templates() -> list[dict[str, any]]:
    """
    Fetch available system prompt templates from the API.

    Queries /api/agents/prompt-templates endpoint for both built-in and custom templates.
    Caches results for 5 minutes (300s) to minimize API calls while staying fresh.
    Falls back gracefully to hardcoded PROMPT_TEMPLATES if API unavailable.

    This enables dynamic template management in the System Prompt Editor to be
    automatically reflected in the Agent Management creation form.

    Returns:
        list[dict]: List of template dicts with name, description, template_text, is_builtin
        Example: [
            {
                "id": "uuid",
                "name": "Ticket Enhancement",
                "description": "Enhance support tickets...",
                "template_text": "You are a helpful AI...",
                "is_builtin": True
            }
        ]

    Note:
        Gracefully returns fallback templates from PROMPT_TEMPLATES if API unavailable.
    """
    try:
        # Get tenant_id from session state or environment
        tenant_id = (
            st.session_state.get("selected_agent_tenant_id")
            or st.session_state.get("tenant_id")
            or os.getenv("AI_AGENTS_DEFAULT_TENANT_ID", os.getenv("DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000001"))
        )

        # Use synchronous httpx client for cached function
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{API_BASE_URL}/api/agents/prompt-templates",
                headers={"X-Tenant-ID": tenant_id},
            )
            response.raise_for_status()
            data = response.json()

            # API returns list[PromptTemplateResponse] directly, not paginated
            if isinstance(data, list):
                if len(data) > 0:
                    return data
                # Empty list - return fallback
                st.warning("⚠️ No templates returned from API, using fallback defaults")
                return _convert_hardcoded_templates_to_api_format()

            # Unexpected format, return fallback
            st.warning("⚠️ Unexpected API response format, using fallback defaults")
            return _convert_hardcoded_templates_to_api_format()

    except httpx.HTTPError as e:
        # Gracefully fallback to hardcoded templates on API error
        st.warning(f"⚠️ Could not load templates from API: {str(e)}")
        return _convert_hardcoded_templates_to_api_format()


def _convert_hardcoded_templates_to_api_format() -> list[dict[str, any]]:
    """
    Convert hardcoded PROMPT_TEMPLATES dict to API response format.

    Returns:
        list[dict]: Templates in API format
    """
    return [
        {
            "id": f"hardcoded-{idx}",
            "name": name,
            "description": f"Built-in template: {name}",
            "template_text": text,
            "is_builtin": True,
        }
        for idx, (name, text) in enumerate(PROMPT_TEMPLATES.items())
    ]


@st.cache_data(ttl=60)
def fetch_available_tenants() -> list[dict[str, str]]:
    """
    Fetch available tenants from the database.

    Queries tenant_configs table for all active tenants.
    Caches results for 60 seconds to minimize database load.

    Returns:
        list[dict]: List of tenant dicts with tenant_id and name
        Example: [
            {"tenant_id": "test-tenant", "name": "Test Tenant"},
            {"tenant_id": "mvp-customer-1", "name": "MVP Customer"}
        ]

    Note:
        Returns empty list if no tenants found or on error.
    """
    try:
        # Use synchronous psycopg2 connection for cached function
        import psycopg2
        from src.config import settings

        # Convert async database URL to sync version
        db_url = settings.database_url.replace("+asyncpg", "")
        db_url = db_url.replace("postgresql+asyncpg", "postgresql")

        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT tenant_id, name FROM tenant_configs WHERE is_active = true ORDER BY name"
                )
                rows = cursor.fetchall()
                tenants = [{"tenant_id": row[0], "name": row[1]} for row in rows]

                # Log for debugging
                if not tenants:
                    st.info("ℹ️ No active tenants found in database. Please create a tenant first.")

                return tenants
    except ImportError as e:
        st.error(
            f"❌ Missing psycopg2 package: {str(e)}. Install with: pip install psycopg2-binary"
        )
        return []


@st.cache_data(ttl=60)
def fetch_available_tenants_with_ids() -> list[dict[str, str]]:
    """
    Fetch available tenants including UUID primary key and VARCHAR tenant_id.

    Returns a list of dicts with keys: id (UUID as text), tenant_id (VARCHAR), name.
    
    IMPORTANT: MCP Server APIs expect VARCHAR tenant_id in X-Tenant-ID header,
    NOT the UUID id! The get_tenant_id() dependency reads the header and passes
    it to get_tenant_uuid() which does: WHERE tenant_id == header_value.
    """
    try:
        import psycopg2
        from src.config import settings

        db_url = settings.database_url.replace("+asyncpg", "")
        db_url = db_url.replace("postgresql+asyncpg", "postgresql")

        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id::text, tenant_id, name
                    FROM tenant_configs
                    WHERE is_active = true
                    ORDER BY name
                    """
                )
                rows = cursor.fetchall()
                return [{"id": row[0], "tenant_id": row[1], "name": row[2]} for row in rows]
    except Exception as e:
        # Keep failure quiet and return empty list; the caller can show UI guidance
        try:
            import streamlit as st

            st.error(f"❌ Failed to load tenants: {str(e)}")
        except Exception:
            pass
        return []
    except Exception as e:
        st.error(f"❌ Database connection error: {str(e)}")
        # Show more diagnostic info in expander
        with st.expander("🔍 Diagnostic Information"):
            st.code(f"Error type: {type(e).__name__}\\nError details: {str(e)}")
        return []


# ============================================================================
# MCP Tool Metadata Integration (Story 8.7, Task 6 - Optional Enhancement)
# ============================================================================


@st.cache_data(ttl=300)
async def fetch_mcp_tool_metadata() -> dict[str, dict]:
    """
    Fetch tool schemas and descriptions from MCP servers (optional enhancement).

    Queries plugin registry for registered tools and their metadata.
    Falls back gracefully to AVAILABLE_TOOLS dict if MCP unavailable.

    Caches results for 5 minutes (300s) to avoid repeated server calls.

    Returns:
        dict: Mapping of tool_id -> {name, description, operations}
        Example: {
            "servicedesk_plus": {
                "name": "ServiceDesk Plus",
                "description": "Ticket management and ITSM",
                "operations": ["create_ticket", "update_ticket", "search_tickets"]
            }
        }
    """
    try:
        # Get tenant_id from session state or environment (FIX: No hardcoded DEFAULT_TENANT_ID)
        tenant_id = (
            st.session_state.get("selected_agent_tenant_id")
            or st.session_state.get("tenant_id")
            or os.getenv("AI_AGENTS_DEFAULT_TENANT_ID", os.getenv("DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000001"))
        )

        # Attempt to query plugin registry for MCP tool metadata
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{API_BASE_URL}/api/plugins/metadata",
                headers={"X-Tenant-ID": tenant_id},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("tools", {})
    except (httpx.HTTPError, httpx.TimeoutException):
        # Gracefully fallback to static AVAILABLE_TOOLS dict (C10)
        # Convert AVAILABLE_TOOLS format to metadata format
        fallback_metadata = {}
        for tool_id, display_name in AVAILABLE_TOOLS.items():
            parts = display_name.split(" - ", 1)
            fallback_metadata[tool_id] = {
                "name": parts[0] if parts else tool_id,
                "description": parts[1] if len(parts) > 1 else "No description available",
                "operations": [],  # No operation metadata in fallback mode
            }
        return fallback_metadata


# ============================================================================
# Async API Functions
# ============================================================================


async def fetch_agents_async(
    search: str = "", status: str = "", skip: int = 0, limit: int = 100, tenant_id: str = None
) -> Optional[dict]:
    """
    Fetch agents from API asynchronously.

    Args:
        search: Search query for agent name
        status: Filter by status (draft, active, suspended, inactive)
        skip: Number of records to skip (pagination)
        limit: Number of records to return (max 100)
        tenant_id: Tenant identifier to fetch agents for (if None, uses DEFAULT_TENANT_ID)

    Returns:
        dict: Response with agent list or None on error
    """
    try:
        params = {
            "skip": skip,
            "limit": limit,
        }
        if search:
            params["q"] = search
        if status and status != "All":
            params["status"] = status.lower()

        # Use provided tenant_id or fallback to DEFAULT_TENANT_ID
        selected_tenant = tenant_id if tenant_id else DEFAULT_TENANT_ID

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(
                f"{API_BASE_URL}/api/agents/",
                params=params,
                headers={"X-Tenant-ID": selected_tenant},
            )
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        st.error("⏱️ Request timed out. Please try again.")
        return None
    except httpx.HTTPStatusError as e:
        # Handle invalid tenant error
        if e.response.status_code == 400 or e.response.status_code == 500:
            error_detail = e.response.json().get("detail", str(e))
            if (
                "Invalid tenant_id" in error_detail
                or "Failed to set tenant context" in error_detail
            ):
                st.warning(
                    "⚠️ No tenant configured. Please create a tenant first in the "
                    "**Tenant Management** page before managing agents."
                )
                return {"items": [], "total": 0, "skip": skip, "limit": limit}
        st.error(f"❌ Failed to load agents: {str(e)}")
        return None
    except httpx.HTTPError as e:
        st.error(f"❌ Failed to load agents: {str(e)}")
        return None


async def fetch_agent_detail_async(agent_id: str, tenant_id: str) -> Optional[dict]:
    """
    Fetch detailed agent information.

    Args:
        agent_id: UUID of agent to fetch
        tenant_id: Tenant ID for the agent

    Returns:
        dict: Agent details or None on error
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{API_BASE_URL}/api/agents/{agent_id}",
                headers={"X-Tenant-ID": tenant_id},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        st.error(f"❌ Failed to load agent: {str(e)}")
        return None


async def create_agent_async(agent_data: dict, tenant_id: str) -> Optional[dict]:
    """
    Create new agent via API.

    Args:
        agent_data: Agent creation payload
        tenant_id: Tenant identifier to create agent for

    Returns:
        dict: Created agent details or None on error
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/agents/",
                json=agent_data,
                headers={"X-Tenant-ID": tenant_id},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 400:
            try:
                error_detail = e.response.json().get("detail", str(e))
                st.error(f"❌ Validation error: {error_detail}")
            except:
                st.error(f"❌ Invalid request: {str(e)}")
        else:
            st.error(f"❌ Failed to create agent (HTTP {e.response.status_code})")
        return None
    except httpx.HTTPError as e:
        st.error(f"❌ Failed to create agent: {str(e)}")
        return None


async def update_agent_async(agent_id: str, tenant_id: str, updates: dict) -> Optional[dict]:
    """
    Update existing agent.

    Args:
        agent_id: UUID of agent to update
        tenant_id: Tenant ID for the agent
        updates: Fields to update

    Returns:
        dict: Updated agent details or None on error
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(
                f"{API_BASE_URL}/api/agents/{agent_id}",
                json=updates,
                headers={"X-Tenant-ID": tenant_id},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        st.error(f"❌ Failed to update agent: {str(e)}")
        return None


async def delete_agent_async(agent_id: str, tenant_id: str) -> bool:
    """
    Delete agent (soft delete).

    Args:
        agent_id: UUID of agent to delete
        tenant_id: Tenant ID for the agent

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{API_BASE_URL}/api/agents/{agent_id}",
                headers={"X-Tenant-ID": tenant_id},
            )
            response.raise_for_status()
            return True
    except httpx.HTTPError as e:
        st.error(f"❌ Failed to delete agent: {str(e)}")
        return False


async def activate_agent_async(agent_id: str, tenant_id: str) -> Optional[dict]:
    """
    Activate agent (draft → active).

    Args:
        agent_id: UUID of agent to activate
        tenant_id: Tenant ID for the agent

    Returns:
        dict: Updated agent or None on error
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/agents/{agent_id}/activate",
                headers={"X-Tenant-ID": tenant_id},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        st.error(f"❌ Failed to activate agent: {str(e)}")
        return None


async def get_webhook_secret_async(agent_id: str, tenant_id: str) -> Optional[str]:
    """
    Fetch unmasked HMAC secret for agent webhook.

    Args:
        agent_id: UUID of agent
        tenant_id: Tenant ID for the agent

    Returns:
        str: Unmasked HMAC secret or None on error
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{API_BASE_URL}/api/agents/{agent_id}/webhook-secret",
                headers={
                    "X-Tenant-ID": tenant_id
                },  # FIX: Use actual tenant_id, not DEFAULT_TENANT_ID
            )
            response.raise_for_status()
            data = response.json()
            return data.get("hmac_secret")
    except httpx.HTTPError as e:
        st.error(f"❌ Failed to fetch webhook secret: {str(e)}")
        return None


async def regenerate_webhook_secret_async(agent_id: str, tenant_id: str) -> Optional[dict]:
    """
    Regenerate HMAC secret for agent webhook (invalidates old webhooks).

    Args:
        agent_id: UUID of agent
        tenant_id: Tenant ID for the agent

    Returns:
        dict: Response with new_secret_masked or None on error
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/agents/{agent_id}/regenerate-webhook-secret",
                headers={"X-Tenant-ID": tenant_id},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        st.error(f"❌ Failed to regenerate webhook secret: {str(e)}")
        return None


# ============================================================================
# Sync Wrapper
# ============================================================================


# ============================================================================
# Webhook Testing (AC#8, Task 6.2)
# ============================================================================


async def send_test_webhook_async(
    webhook_url: str, agent_id: str, tenant_id: str, payload: dict
) -> Optional[dict]:
    """
    Send test webhook request with auto-computed HMAC signature.

    Uses httpx.AsyncClient with 2025 best practices (granular timeouts,
    proper error handling). Auto-fetches HMAC secret and computes signature.

    Args:
        webhook_url: Agent's webhook URL
        agent_id: Agent UUID
        tenant_id: Tenant ID for the agent
        payload: JSON payload to send

    Returns:
        dict: {"status_code": int, "response": dict, "execution_id": str | None}
        None if network error occurs
    """
    import json
    from services.webhook_service import compute_hmac_signature

    try:
        # Fetch agent's HMAC secret (FIX: Pass tenant_id)
        secret_response = await get_webhook_secret_async(agent_id, tenant_id)
        if not secret_response:
            return {
                "status_code": 500,
                "response": {"error": "Failed to fetch HMAC secret"},
                "execution_id": None,
            }

        hmac_secret = secret_response

        # Convert payload to JSON bytes
        payload_json = json.dumps(payload)
        payload_bytes = payload_json.encode("utf-8")

        # Compute HMAC-SHA256 signature (Task 6.2c)
        signature = compute_hmac_signature(payload_bytes, hmac_secret)

        # Prepare headers (Task 6.2d)
        headers = {
            "Content-Type": "application/json",
            "X-Hub-Signature-256": f"sha256={signature}",
        }

        # Configure granular timeouts (2025 httpx best practice from Context7 MCP)
        timeout = httpx.Timeout(
            connect=5.0,  # Time to establish connection
            read=30.0,  # Time to read response (agent execution may take time)
            write=5.0,  # Time to send request data
            pool=5.0,  # Time to acquire connection from pool
        )

        # Send POST request (Task 6.2e)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(webhook_url, content=payload_json, headers=headers)

            # Parse response
            try:
                response_data = response.json()
            except Exception:
                response_data = {"detail": response.text}

            # Extract execution ID if present (Task 6.2f, 6.3a)
            execution_id = response_data.get("execution_id")

            return {
                "status_code": response.status_code,
                "response": response_data,
                "execution_id": execution_id,
            }

    except httpx.ConnectTimeout:
        return {
            "status_code": 0,
            "response": {"error": "Connection timeout - webhook endpoint unreachable"},
            "execution_id": None,
        }
    except httpx.ReadTimeout:
        return {
            "status_code": 0,
            "response": {"error": "Read timeout - agent execution taking too long"},
            "execution_id": None,
        }
    except httpx.TimeoutException as e:
        return {
            "status_code": 0,
            "response": {"error": f"Timeout: {str(e)}"},
            "execution_id": None,
        }
    except httpx.HTTPError as e:
        return {
            "status_code": 0,
            "response": {"error": f"HTTP error: {str(e)}"},
            "execution_id": None,
        }
    except Exception as e:
        return {
            "status_code": 0,
            "response": {"error": f"Unexpected error: {str(e)}"},
            "execution_id": None,
        }


def async_to_sync(async_func):
    """
    Wrapper to run async function synchronously in Streamlit context.

    Args:
        async_func: Async function to wrap

    Returns:
        function: Synchronous wrapper
    """

    def sync_wrapper(*args, **kwargs):
        return asyncio.run(async_func(*args, **kwargs))

    return sync_wrapper
