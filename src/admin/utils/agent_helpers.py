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
from datetime import datetime
from typing import Optional

import httpx
import streamlit as st

# ============================================================================
# Configuration
# ============================================================================

API_BASE_URL: str = "http://localhost:8000"  # Set via environment in production
DEFAULT_TENANT_ID: str = "default"  # TODO: Get from session/JWT in production

# LLM Models
AVAILABLE_MODELS = [
    "gpt-4",
    "gpt-4-turbo",
    "gpt-3.5-turbo",
    "claude-3-5-sonnet",
    "claude-3-5-sonnet-20241022",
    "claude-3-opus",
    "claude-3-haiku",
    "ollama/llama3",
    "ollama/mistral",
]

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


def validate_form_data(form_data: dict) -> tuple[bool, list[str]]:
    """
    Validate agent creation/update form data.

    Args:
        form_data: Dictionary with agent form fields

    Returns:
        tuple: (is_valid: bool, errors: list[str])
    """
    errors = []

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

    if not form_data.get("tools"):
        errors.append("❌ At least one tool must be selected")

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

    return len(errors) == 0, errors


# ============================================================================
# Async API Functions
# ============================================================================


async def fetch_agents_async(
    search: str = "", status: str = "", skip: int = 0, limit: int = 100
) -> Optional[dict]:
    """
    Fetch agents from API asynchronously.

    Args:
        search: Search query for agent name
        status: Filter by status (draft, active, suspended, inactive)
        skip: Number of records to skip (pagination)
        limit: Number of records to return (max 100)

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

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{API_BASE_URL}/api/agents",
                params=params,
                headers={"X-Tenant-ID": DEFAULT_TENANT_ID},
            )
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        st.error("⏱️ Request timed out. Please try again.")
        return None
    except httpx.HTTPError as e:
        st.error(f"❌ Failed to load agents: {str(e)}")
        return None


async def fetch_agent_detail_async(agent_id: str) -> Optional[dict]:
    """
    Fetch detailed agent information.

    Args:
        agent_id: UUID of agent to fetch

    Returns:
        dict: Agent details or None on error
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{API_BASE_URL}/api/agents/{agent_id}",
                headers={"X-Tenant-ID": DEFAULT_TENANT_ID},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        st.error(f"❌ Failed to load agent: {str(e)}")
        return None


async def create_agent_async(agent_data: dict) -> Optional[dict]:
    """
    Create new agent via API.

    Args:
        agent_data: Agent creation payload

    Returns:
        dict: Created agent details or None on error
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/agents",
                json=agent_data,
                headers={"X-Tenant-ID": DEFAULT_TENANT_ID},
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


async def update_agent_async(agent_id: str, updates: dict) -> Optional[dict]:
    """
    Update existing agent.

    Args:
        agent_id: UUID of agent to update
        updates: Fields to update

    Returns:
        dict: Updated agent details or None on error
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(
                f"{API_BASE_URL}/api/agents/{agent_id}",
                json=updates,
                headers={"X-Tenant-ID": DEFAULT_TENANT_ID},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        st.error(f"❌ Failed to update agent: {str(e)}")
        return None


async def delete_agent_async(agent_id: str) -> bool:
    """
    Delete agent (soft delete).

    Args:
        agent_id: UUID of agent to delete

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{API_BASE_URL}/api/agents/{agent_id}",
                headers={"X-Tenant-ID": DEFAULT_TENANT_ID},
            )
            response.raise_for_status()
            return True
    except httpx.HTTPError as e:
        st.error(f"❌ Failed to delete agent: {str(e)}")
        return False


async def activate_agent_async(agent_id: str) -> Optional[dict]:
    """
    Activate agent (draft → active).

    Args:
        agent_id: UUID of agent to activate

    Returns:
        dict: Updated agent or None on error
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/agents/{agent_id}/activate",
                headers={"X-Tenant-ID": DEFAULT_TENANT_ID},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        st.error(f"❌ Failed to activate agent: {str(e)}")
        return None


# ============================================================================
# Sync Wrapper
# ============================================================================


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
