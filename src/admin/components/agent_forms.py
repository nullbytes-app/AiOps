"""Agent management form dialogs for Streamlit admin UI.

This module provides dialog components for agent CRUD operations:
- Create Agent: Multi-tab form for comprehensive agent configuration
- Edit Agent: Form for updating existing agent properties
- Delete Agent: Confirmation dialog for agent deletion
- Agent Detail: Full agent properties and webhook management
"""

import streamlit as st

from admin.utils.agent_helpers import (
    AVAILABLE_MODELS,
    AVAILABLE_TOOLS,
    PROMPT_TEMPLATES,
    activate_agent_async,
    async_to_sync,
    copy_to_clipboard,
    create_agent_async,
    delete_agent_async,
    fetch_agent_detail_async,
    format_datetime,
    format_status_badge,
    update_agent_async,
    validate_form_data,
)


@st.dialog("➕ Create New Agent", width="large")
def create_agent_form():
    """Modal dialog for creating a new agent.

    Implements AC#3: Create form with 5-tab interface (Basic Info, LLM Config,
    System Prompt, Triggers, Tools). Validates form data and submits to API.
    """
    st.markdown("Configure a new AI agent with comprehensive settings")

    # Initialize form state
    if "create_form_data" not in st.session_state:
        st.session_state.create_form_data = {
            "name": "",
            "description": "",
            "status": "draft",
            "provider": "litellm",
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 4096,
            "system_prompt": "",
            "webhook_enabled": True,
            "webhook_description": "",
            "tools": [],
        }

    form_data = st.session_state.create_form_data

    # Use tabs to organize form (AC#3: 5-tab interface)
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Basic Info", "LLM Config", "System Prompt", "Triggers", "Tools"]
    )

    with tab1:
        st.subheader("Basic Information")
        form_data["name"] = st.text_input(
            "Agent Name *",
            value=form_data["name"],
            placeholder="e.g., Ticket Enhancement Agent",
            help="Name of the agent (3-255 characters)",
        )
        form_data["description"] = st.text_area(
            "Description",
            value=form_data["description"],
            placeholder="Brief description of what this agent does...",
            height=80,
        )
        form_data["status"] = st.selectbox(
            "Initial Status *",
            ["draft", "active"],
            index=0,
            help="Draft agents require activation before use",
        )

    with tab2:
        st.subheader("LLM Configuration")
        form_data["provider"] = st.selectbox(
            "LLM Provider *",
            ["litellm", "openai", "anthropic"],
            index=0,
            help="LiteLLM proxy for multi-model support",
        )
        form_data["model"] = st.selectbox(
            "Model *",
            AVAILABLE_MODELS,
            index=0,
            help="Select LLM model to use",
        )
        form_data["temperature"] = st.slider(
            "Temperature *",
            min_value=0.0,
            max_value=2.0,
            value=form_data["temperature"],
            step=0.1,
            help="Higher values = more creative, lower = more deterministic",
        )
        form_data["max_tokens"] = st.number_input(
            "Max Tokens *",
            min_value=1,
            max_value=32000,
            value=form_data["max_tokens"],
            step=256,
            help="Maximum length of generated responses",
        )

    with tab3:
        st.subheader("System Prompt")

        # Template selector
        template_choice = st.selectbox(
            "Load Template (optional)",
            ["None"] + list(PROMPT_TEMPLATES.keys()),
            help="Start with a pre-built template or write custom",
        )
        if template_choice != "None":
            form_data["system_prompt"] = PROMPT_TEMPLATES[template_choice]

        form_data["system_prompt"] = st.text_area(
            "System Prompt *",
            value=form_data["system_prompt"],
            placeholder="Define agent behavior and personality...",
            height=150,
            help="Instructions that guide LLM behavior (10-32000 characters)",
        )

        # Character counter
        char_count = len(form_data["system_prompt"])
        if char_count >= 8000:
            st.warning(f"⚠️ {char_count} / 32000 characters (approaching limit)")
        else:
            st.caption(f"{char_count} / 32000 characters")

    with tab4:
        st.subheader("Triggers (Webhooks)")
        st.info(
            "Webhook URL will be auto-generated on creation. "
            "You can configure additional triggers after activation."
        )
        form_data["webhook_enabled"] = st.checkbox(
            "Enable Webhook", value=form_data["webhook_enabled"]
        )
        form_data["webhook_description"] = st.text_input(
            "Webhook Description (optional)",
            value=form_data["webhook_description"],
            placeholder="e.g., Triggered by ServiceDesk Plus tickets",
        )

    with tab5:
        st.subheader("Tools Assignment")
        st.write("Select tools this agent can access:")
        form_data["tools"] = st.multiselect(
            "Available Tools",
            list(AVAILABLE_TOOLS.keys()),
            default=form_data["tools"],
            format_func=lambda x: AVAILABLE_TOOLS.get(x, x),
            help="At least one tool must be selected",
        )

    # Form submission (AC#6,7: Validation + messages)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Create Agent", type="primary", use_container_width=True):
            is_valid, errors = validate_form_data(form_data)
            if not is_valid:
                for error in errors:
                    st.error(error)
            else:
                with st.spinner("Creating agent..."):
                    # Prepare API payload
                    agent_payload = {
                        "name": form_data["name"],
                        "description": form_data["description"] or None,
                        "status": form_data["status"],
                        "system_prompt": form_data["system_prompt"],
                        "llm_config": {
                            "provider": form_data["provider"],
                            "model": form_data["model"],
                            "temperature": form_data["temperature"],
                            "max_tokens": form_data["max_tokens"],
                        },
                        "tool_ids": form_data["tools"],
                        "triggers": (
                            [{"trigger_type": "webhook"}] if form_data["webhook_enabled"] else []
                        ),
                    }

                    agent = async_to_sync(create_agent_async)(agent_payload)
                    if agent:
                        st.success(f"✅ Agent '{form_data['name']}' created successfully!")
                        st.info(f"**Webhook URL:** `{agent.get('webhook_url', 'N/A')}`")
                        st.session_state.refresh_trigger += 1
                        st.session_state.show_create_form = False
                        if st.button("✅ Done"):
                            st.rerun()

    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            st.session_state.show_create_form = False
            st.rerun()


@st.dialog("✏️ Edit Agent", width="large")
def edit_agent_form(agent_id: str):
    """Modal dialog for editing an agent.

    Args:
        agent_id: UUID of agent to edit
    """
    with st.spinner("Loading agent..."):
        agent = async_to_sync(fetch_agent_detail_async)(agent_id)

    if not agent:
        st.error("Failed to load agent")
        return

    st.markdown(f"Editing agent: **{agent.get('name')}**")

    if "edit_form_data" not in st.session_state:
        llm_config = agent.get("llm_config", {})
        st.session_state.edit_form_data = {
            "name": agent.get("name", ""),
            "description": agent.get("description", ""),
            "system_prompt": agent.get("system_prompt", ""),
            "provider": llm_config.get("provider", "litellm"),
            "model": llm_config.get("model", "gpt-4"),
            "temperature": llm_config.get("temperature", 0.7),
            "max_tokens": llm_config.get("max_tokens", 4096),
            "tools": agent.get("tool_ids", []),
        }

    form_data = st.session_state.edit_form_data

    with st.form("edit_agent_form"):
        col1, col2 = st.columns(2)
        with col1:
            form_data["name"] = st.text_input("Agent Name *", value=form_data["name"])
            form_data["provider"] = st.selectbox(
                "LLM Provider",
                ["litellm", "openai", "anthropic"],
                index=[
                    "litellm",
                    "openai",
                    "anthropic",
                ].index(form_data["provider"]),
            )
            form_data["temperature"] = st.slider(
                "Temperature",
                0.0,
                2.0,
                form_data["temperature"],
                step=0.1,
            )

        with col2:
            form_data["model"] = st.selectbox(
                "Model *",
                AVAILABLE_MODELS,
                index=(
                    AVAILABLE_MODELS.index(form_data["model"])
                    if form_data["model"] in AVAILABLE_MODELS
                    else 0
                ),
            )
            form_data["max_tokens"] = st.number_input(
                "Max Tokens *",
                min_value=1,
                max_value=32000,
                value=form_data["max_tokens"],
                step=256,
            )

        form_data["description"] = st.text_area(
            "Description",
            value=form_data["description"],
            height=80,
        )
        form_data["system_prompt"] = st.text_area(
            "System Prompt *",
            value=form_data["system_prompt"],
            height=120,
        )

        form_data["tools"] = st.multiselect(
            "Tools",
            list(AVAILABLE_TOOLS.keys()),
            default=form_data["tools"],
            format_func=lambda x: AVAILABLE_TOOLS.get(x, x),
        )

        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("✅ Save Changes", type="primary")
        with col2:
            cancel = st.form_submit_button("❌ Cancel")

    if cancel:
        st.rerun()

    if submit:
        is_valid, errors = validate_form_data(form_data)
        if not is_valid:
            for error in errors:
                st.error(error)
        else:
            with st.spinner("Updating agent..."):
                updates = {
                    "name": form_data["name"],
                    "description": form_data["description"] or None,
                    "system_prompt": form_data["system_prompt"],
                    "llm_config": {
                        "provider": form_data["provider"],
                        "model": form_data["model"],
                        "temperature": form_data["temperature"],
                        "max_tokens": form_data["max_tokens"],
                    },
                }
                agent = async_to_sync(update_agent_async)(agent_id, updates)
                if agent:
                    st.success("✅ Agent updated successfully!")
                    st.session_state.refresh_trigger += 1
                    st.session_state.show_edit_form = False
                    if st.button("✅ Done"):
                        st.rerun()


@st.dialog("🗑️ Delete Agent")
def delete_agent_confirm(agent_id: str):
    """Modal dialog for confirming agent deletion.

    Args:
        agent_id: UUID of agent to delete (soft delete)
    """
    with st.spinner("Loading agent..."):
        agent = async_to_sync(fetch_agent_detail_async)(agent_id)

    if not agent:
        st.error("Failed to load agent")
        return

    st.warning(
        f"**Are you sure you want to delete '{agent.get('name')}'?**\n\n"
        f"This will mark the agent as inactive (soft delete). "
        f"The agent will be preserved in history."
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Confirm Delete", use_container_width=True):
            with st.spinner("Deleting agent..."):
                success = async_to_sync(delete_agent_async)(agent_id)
                if success:
                    st.success(
                        f"✅ Agent '{agent.get('name')}' has been deleted " f"(marked inactive)"
                    )
                    st.session_state.refresh_trigger += 1
                    st.session_state.show_delete_form = False
                    if st.button("✅ Done"):
                        st.rerun()
    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            st.rerun()


@st.dialog("🤖 Agent Details")
def agent_detail_view(agent_id: str):
    """Modal dialog showing full agent details.

    Implements AC#4: Agent detail view with properties, webhook URL,
    copy button, and edit/delete action buttons.

    Args:
        agent_id: UUID of agent to display
    """
    with st.spinner("Loading agent..."):
        agent = async_to_sync(fetch_agent_detail_async)(agent_id)

    if not agent:
        st.error("Failed to load agent")
        return

    st.markdown(f"### {agent.get('name')}")

    # Basic info
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**Status:** {format_status_badge(agent.get('status'))}")
    with col2:
        st.write(f"**Created:** {format_datetime(agent.get('created_at'))}")
    with col3:
        st.write(f"**Tools:** {len(agent.get('tool_ids', []))}")

    # Webhook section (AC#4)
    st.subheader("Webhook")
    webhook_url = agent.get("webhook_url", "N/A")
    col1, col2 = st.columns([4, 1])
    with col1:
        st.code(webhook_url, language="text")
    with col2:
        if st.button("📋 Copy"):
            copy_to_clipboard(webhook_url)

    # Properties table
    st.subheader("Properties")
    properties = {
        "Name": agent.get("name"),
        "Description": agent.get("description", "N/A"),
        "Status": agent.get("status"),
        "System Prompt": agent.get("system_prompt", "")[:100] + "...",
        "LLM Model": agent.get("llm_config", {}).get("model", "N/A"),
        "Temperature": agent.get("llm_config", {}).get("temperature", "N/A"),
        "Max Tokens": agent.get("llm_config", {}).get("max_tokens", "N/A"),
    }

    for key, value in properties.items():
        col1, col2 = st.columns([1, 3])
        with col1:
            st.write(f"**{key}:**")
        with col2:
            st.write(value)

    # Tools
    st.subheader("Assigned Tools")
    tools = agent.get("tool_ids", [])
    if tools:
        cols = st.columns(min(3, len(tools)))
        for idx, tool in enumerate(tools):
            with cols[idx % 3]:
                st.write(f"🔧 {AVAILABLE_TOOLS.get(tool, tool)}")
    else:
        st.info("No tools assigned")

    # Action buttons
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✏️ Edit", use_container_width=True):
            st.session_state.show_edit_form = True
            st.rerun()
    with col2:
        if st.button("🗑️ Delete", use_container_width=True):
            st.session_state.show_delete_form = True
            st.rerun()
    with col3:
        if st.button("❌ Close", use_container_width=True):
            st.rerun()
