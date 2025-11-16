"""
System Prompt Editor - Agent prompt configuration and versioning.

Story 8.5: System Prompt Editor UI component for managing agent system prompts.
Provides:
- Rich text editor with syntax highlighting
- Prompt templates (built-in and custom)
- Variable substitution ({{tenant_name}}, {{tools}}, {{current_date}}, {{agent_name}})
- Prompt preview mode with real-time rendering
- Character count with warnings (8000+ chars)
- Prompt version history with revert capability
- LLM test feature for prompt validation
- Custom template creation and management

Architecture:
- Streamlit 1.30+ for UI
- AsyncClient for API calls
- Session state for editor state management
- Multi-tenant support (tenant_id filtering)

Constraints:
- File size ≤ 500 lines (may split helpers if needed)
- All API calls use async patterns with proper error handling
- Enforce tenant isolation at frontend
- Use LiteLLM proxy for model testing
"""

import asyncio
import os
import re
from datetime import datetime
from typing import Optional

import streamlit as st
from httpx import AsyncClient

# Import dynamic model discovery
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.agent_helpers import fetch_available_models


# Session state initialization
def init_session_state() -> None:
    """Initialize session state variables for prompt editor."""
    if "selected_agent_id" not in st.session_state:
        st.session_state.selected_agent_id = None
    if "prompt_text" not in st.session_state:
        st.session_state.prompt_text = ""
    if "show_preview" not in st.session_state:
        st.session_state.show_preview = False
    if "preview_variables" not in st.session_state:
        st.session_state.preview_variables: dict[str, str] = {}
    if "agents_list" not in st.session_state:
        st.session_state.agents_list = []
    if "templates_list" not in st.session_state:
        st.session_state.templates_list = []
    if "selected_test_model" not in st.session_state:
        st.session_state.selected_test_model = "gpt-4"  # Default fallback


# Helper functions
def count_variables(text: str) -> dict[str, list[str] | int]:
    """Extract and count {{variable}} placeholders from prompt text."""
    pattern = r"\{\{(\w+)\}\}"
    matches = re.findall(pattern, text)
    return {"variables": matches, "count": len(matches)}


def validate_prompt_length(text: str) -> tuple[bool, int, Optional[str]]:
    """
    Validate prompt length and return status.

    Returns:
        (is_valid, char_count, warning_message)
    """
    char_count = len(text)
    warning_msg = None
    is_valid = True

    if char_count >= 12000:
        is_valid = False
        warning_msg = f"❌ Exceeds hard limit (12,000 chars). Current: {char_count}"
    elif char_count >= 10000:
        warning_msg = f"🔴 Exceeds recommended length (8,000 chars). Current: {char_count}"
    elif char_count >= 8000:
        warning_msg = f"⚠️ Approaching limit (8,000 chars). Current: {char_count}"

    return is_valid, char_count, warning_msg


async def async_api_call(
    method: str,
    endpoint: str,
    json_data: Optional[dict] = None,
    timeout: int = 30,
) -> Optional[dict]:  # type: ignore[type-arg]
    """
    Make async API call to backend endpoints.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        endpoint: API endpoint path (e.g., "/api/agents/123/prompt-versions")
        json_data: Request body for POST/PUT
        timeout: Request timeout in seconds

    Returns:
        Response JSON or None if error
    """
    base_url = os.getenv("API_BASE_URL", "http://api:8000")  # Use 'api' service in Docker

    # Get tenant_id from session state or environment (Story 8.5: tenant isolation)
    tenant_id = st.session_state.get("tenant_id") or os.getenv("AI_AGENTS_DEFAULT_TENANT_ID", os.getenv("DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000001"))

    # Headers required by API dependencies (X-Tenant-ID for tenant isolation)
    headers = {"X-Tenant-ID": tenant_id}

    try:
        async with AsyncClient(timeout=timeout, follow_redirects=True) as client:
            if method.upper() == "GET":
                response = await client.get(f"{base_url}{endpoint}", headers=headers)
            elif method.upper() == "POST":
                response = await client.post(f"{base_url}{endpoint}", json=json_data, headers=headers)
            elif method.upper() == "PUT":
                response = await client.put(f"{base_url}{endpoint}", json=json_data, headers=headers)
            elif method.upper() == "DELETE":
                response = await client.delete(f"{base_url}{endpoint}", headers=headers)
            else:
                st.error(f"Unsupported HTTP method: {method}")
                return None

            response.raise_for_status()
            return response.json()
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return None


def substitute_variables(template_text: str, variables: dict[str, str]) -> str:
    """Substitute {{variable}} placeholders with provided values."""

    def replace_var(match: re.Match) -> str:  # type: ignore[name-defined]
        var_name = match.group(1)
        return variables.get(var_name, f"[UNDEFINED: {var_name}]")

    return re.sub(r"\{\{(\w+)\}\}", replace_var, template_text)


# Main UI
def main() -> None:
    """Main System Prompt Editor interface."""
    init_session_state()

    st.title("✏️ System Prompt Editor")
    st.markdown(
        "Configure and manage system prompts for your AI agents. "
        "Save versions, use templates, and test prompts before deployment."
    )

    # Sidebar: Agent selection
    with st.sidebar:
        st.header("📌 Agent Selection")

        # Load agents via GET /api/agents?status=active,draft&limit=100
        if not st.session_state.agents_list:
            with st.spinner("Loading agents..."):
                agents_data = asyncio.run(
                    async_api_call("GET", "/api/agents?status=active,draft&limit=100")
                )
                if agents_data and "data" in agents_data:
                    st.session_state.agents_list = agents_data["data"]

        agents = st.session_state.agents_list or []
        agent_names = [a.get("name", "Unknown") for a in agents]
        agent_ids = {a.get("name"): a.get("id") for a in agents}

        agent_name = st.selectbox(
            "Select Agent",
            options=agent_names if agent_names else ["(No agents available)"],
            key="agent_selector",
        )

        if agent_name and agent_name in agent_ids:
            agent_id = agent_ids[agent_name]
            st.session_state.selected_agent_id = agent_id

            st.divider()

            # Agent context display
            agent = next((a for a in agents if a.get("id") == agent_id), None)
            if agent:
                st.subheader("Agent Context")
                st.metric("Status", agent.get("status", "Unknown").title())
                st.metric("Model", agent.get("llm_config", {}).get("model", "gpt-4"))
                st.metric("Last Modified", agent.get("updated_at", "Never")[:10])

        st.divider()

        # Templates section
        st.subheader("📚 Templates")
        if st.button("🔄 Reload Templates"):
            st.session_state.templates_list = []

        # Load templates via GET /api/agents/prompt-templates
        if not st.session_state.templates_list:
            with st.spinner("Loading templates..."):
                templates_data = asyncio.run(async_api_call("GET", "/api/agents/prompt-templates"))
                # API returns list[PromptTemplateResponse] directly, not paginated
                if templates_data and isinstance(templates_data, list):
                    st.session_state.templates_list = templates_data

        templates = st.session_state.templates_list or []
        if templates:
            selected_template = st.selectbox(
                "Choose Template",
                options=[t.get("name") for t in templates],
                key="template_selector",
            )

            if selected_template:
                template = next((t for t in templates if t.get("name") == selected_template), None)
                if st.button("📥 Load Template", key="load_template_btn"):
                    st.session_state.prompt_text = template.get("template_text", "")
                    st.success(f"Loaded template: {selected_template}")
                    st.rerun()

            # Show template description
            if template:
                with st.expander("📖 Template Info"):
                    st.write(f"**Description:** {template.get('description', 'N/A')}")
                    if template.get("is_builtin"):
                        st.badge("🔹 Built-in")
                    else:
                        st.badge("⭐ Custom")
        else:
            st.info("No templates loaded yet")

    # Main content area: Two-column layout
    col_editor, col_preview = st.columns([1, 1], gap="medium")

    with col_editor:
        st.subheader("Prompt Editor")

        # Text area for prompt editing
        prompt_text = st.text_area(
            "System Prompt",
            value=st.session_state.prompt_text,
            height=300,
            help="Enter your system prompt. Use {{variable}} for dynamic substitution.",
        )
        st.session_state.prompt_text = prompt_text

        # Character count and warnings
        is_valid, char_count, warning = validate_prompt_length(prompt_text)

        col1, col2 = st.columns([2, 1])
        with col1:
            if warning:
                if is_valid:
                    st.warning(warning)
                else:
                    st.error(warning)
        with col2:
            st.metric("Characters", f"{char_count} / 12000")

        # Variable analysis
        var_info = count_variables(prompt_text)
        if var_info["count"] > 0:
            st.info(
                f"Found {var_info['count']} variable(s): {', '.join(set(var_info['variables']))}"
            )

        # Action buttons
        col_save, col_preview_btn, col_test = st.columns(3)

        with col_save:
            if st.button(
                "💾 Save Prompt", disabled=not is_valid or not st.session_state.selected_agent_id
            ):
                with st.spinner("Saving prompt..."):
                    result = asyncio.run(
                        async_api_call(
                            "POST",
                            f"/api/agents/{st.session_state.selected_agent_id}/prompt-versions",
                            json_data={
                                "prompt_text": prompt_text,
                                "description": "Updated via editor",
                            },
                        )
                    )
                    if result:
                        st.success("✅ Prompt saved successfully!")
                    else:
                        st.error("❌ Failed to save prompt")

        with col_preview_btn:
            st.session_state.show_preview = st.button("👁️ Preview", st.session_state.show_preview)

        with col_test:
            if st.button("🧪 Test Prompt"):
                if st.session_state.selected_agent_id:
                    with st.spinner("Testing prompt with LLM (may take 10-30 seconds)..."):
                        result = asyncio.run(
                            async_api_call(
                                "POST",
                                "/api/llm/test",
                                json_data={
                                    "system_prompt": prompt_text,
                                    "user_message": "Ticket ID: TKT-001\nDescription: Password reset not working\nPriority: High",
                                    "model": st.session_state.selected_test_model,
                                },
                            )
                        )
                        if result:
                            st.session_state.test_result = result
                            st.rerun()
                        else:
                            st.error("❌ Test failed")
                else:
                    st.warning("⚠️ Select an agent first")

        # Model selection for testing (new - Task 3.3)
        st.divider()
        st.subheader("🧪 Test Configuration")
        col_model, col_spacer = st.columns([1, 2])
        with col_model:
            # Fetch available models dynamically
            available_models = fetch_available_models()
            model_options = [m.get("id") for m in available_models] if available_models else ["gpt-4"]
            model_display = [f"{m.get('name')} ({m.get('provider')})" for m in available_models] if available_models else ["GPT-4"]

            selected_idx = 0
            if st.session_state.selected_test_model in model_options:
                selected_idx = model_options.index(st.session_state.selected_test_model)

            st.session_state.selected_test_model = st.selectbox(
                "Test Model",
                options=model_options,
                format_func=lambda x: model_display[model_options.index(x)] if x in model_options else x,
                index=selected_idx,
                help="Select the LLM model to use for testing prompts",
            )

    with col_preview:
        if st.session_state.show_preview:
            st.subheader("Preview (Live)")

            # Variable substitution for preview
            preview_vars = {
                "tenant_name": "Acme Corp",
                "tools": "ServiceDesk Plus, Jira",
                "current_date": datetime.now().strftime("%Y-%m-%d"),
                "agent_name": "Ticket Enhancement Agent",
            }

            rendered_prompt = substitute_variables(prompt_text, preview_vars)

            st.markdown(rendered_prompt)

            # Variable reference table
            st.subheader("Variables Used")
            var_data = {
                "{{tenant_name}}": preview_vars["tenant_name"],
                "{{tools}}": preview_vars["tools"],
                "{{current_date}}": preview_vars["current_date"],
                "{{agent_name}}": preview_vars["agent_name"],
            }

            for var, value in var_data.items():
                col_var, col_val = st.columns([1, 2])
                with col_var:
                    st.code(var)
                with col_val:
                    st.text_input("", value=value, disabled=True, key=f"var_{var}")

    # Tabs for additional features
    st.divider()
    tab_history, tab_templates, tab_test_result = st.tabs(
        ["📜 Version History", "🎨 Templates", "🧪 Test Result"]
    )

    with tab_history:
        st.subheader("Prompt Version History")

        if st.session_state.selected_agent_id:
            if st.button("🔄 Reload History", key="reload_history"):
                st.session_state.pop("version_history", None)

            # Load version history via GET /api/agents/{agent_id}/prompt-versions
            if "version_history" not in st.session_state:
                with st.spinner("Loading version history..."):
                    versions_data = asyncio.run(
                        async_api_call(
                            "GET",
                            f"/api/agents/{st.session_state.selected_agent_id}/prompt-versions?limit=20&offset=0",
                        )
                    )
                    if versions_data and "data" in versions_data:
                        st.session_state.version_history = versions_data["data"]
                    else:
                        st.session_state.version_history = []

            versions = st.session_state.get("version_history", [])
            if versions:
                for idx, version in enumerate(versions):
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.markdown(
                                f"**Version {len(versions) - idx}** ({version.get('created_at', 'N/A')[:10]})\n"
                                f"*{version.get('description', 'No description')}*"
                            )
                        with col2:
                            if st.button("👁️ View", key=f"view_ver_{version.get('id')}"):
                                st.session_state.prompt_text = version.get("prompt_text", "")
                                st.rerun()
                        with col3:
                            if st.button("↩️ Revert", key=f"revert_ver_{version.get('id')}"):
                                with st.spinner("Reverting..."):
                                    revert_result = asyncio.run(
                                        async_api_call(
                                            "POST",
                                            f"/api/agents/{st.session_state.selected_agent_id}/prompt-versions/revert",
                                            json_data={"version_id": version.get("id")},
                                        )
                                    )
                                    if revert_result:
                                        st.success(f"✅ Reverted to version {len(versions) - idx}")
                                        st.session_state.prompt_text = version.get(
                                            "prompt_text", ""
                                        )
                                        st.rerun()
                                    else:
                                        st.error("❌ Revert failed")
            else:
                st.info("No version history yet. Save a prompt to create the first version.")
        else:
            st.warning("Select an agent to view version history")

    with tab_templates:
        st.subheader("Template Management")

        col_list, col_create = st.columns([2, 1])
        with col_create:
            if st.button("➕ Create New Template", key="create_template_btn"):
                st.session_state.show_template_form = not st.session_state.get(
                    "show_template_form", False
                )
                st.rerun()

        # Template creation form
        if st.session_state.get("show_template_form", False):
            st.subheader("Create Custom Template")
            with st.form("create_template_form"):
                template_name = st.text_input("Template Name", placeholder="e.g., Custom RCA")
                template_desc = st.text_area(
                    "Description", placeholder="What is this template for?"
                )
                template_text = st.text_area(
                    "Template Text", height=200, placeholder="Enter prompt template..."
                )

                if st.form_submit_button("💾 Save Template"):
                    if template_name and template_text:
                        with st.spinner("Creating template..."):
                            result = asyncio.run(
                                async_api_call(
                                    "POST",
                                    "/api/agents/prompt-templates",
                                    json_data={
                                        "name": template_name,
                                        "description": template_desc,
                                        "template_text": template_text,
                                    },
                                )
                            )
                            if result:
                                st.success("✅ Template created!")
                                st.session_state.templates_list = []  # Refresh template list
                                st.session_state.show_template_form = False
                                st.rerun()
                            else:
                                st.error("❌ Failed to create template")
                    else:
                        st.error("Name and text are required")

        # List existing templates
        st.subheader("Custom Templates")
        custom_templates = [t for t in st.session_state.templates_list if not t.get("is_builtin")]
        if custom_templates:
            for template in custom_templates:
                with st.container(border=True):
                    st.write(f"**{template.get('name')}**")
                    st.caption(template.get("description", "No description"))
                    col_edit, col_delete = st.columns(2)
                    with col_edit:
                        if st.button("✏️ Edit", key=f"edit_tmpl_{template.get('id')}"):
                            st.info("Edit functionality coming in next iteration")
                    with col_delete:
                        if st.button("🗑️ Delete", key=f"delete_tmpl_{template.get('id')}"):
                            with st.spinner("Deleting..."):
                                result = asyncio.run(
                                    async_api_call(
                                        "DELETE",
                                        f"/api/agents/prompt-templates/{template.get('id')}",
                                    )
                                )
                                if result:
                                    st.success("✅ Template deleted")
                                    st.session_state.templates_list = []
                                    st.rerun()
                                else:
                                    st.error("❌ Delete failed")
        else:
            st.info("No custom templates yet")

    with tab_test_result:
        st.subheader("Test Prompt Result")
        if "test_result" in st.session_state and st.session_state.test_result:
            result = st.session_state.test_result

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Input Tokens", result.get("tokens_used", {}).get("input", 0))
            with col2:
                st.metric("Output Tokens", result.get("tokens_used", {}).get("output", 0))
            with col3:
                st.metric("Exec Time", f"{result.get('execution_time', 0):.2f}s")

            st.subheader("LLM Response")
            st.markdown(result.get("text", "No response"))

            if st.button("📋 Copy Response", key="copy_test"):
                st.write("(Copy functionality - implement clipboard)")
        else:
            st.info("Run a test to see results here")


if __name__ == "__main__":
    main()
