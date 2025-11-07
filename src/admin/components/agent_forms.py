"""Agent management form dialogs for Streamlit admin UI.

This module provides dialog components for agent CRUD operations:
- Create Agent: Multi-tab form for comprehensive agent configuration
- Edit Agent: Form for updating existing agent properties
- Delete Agent: Confirmation dialog for agent deletion
- Agent Detail: Full agent properties and webhook management
"""

import json
import streamlit as st
from jsonschema import Draft202012Validator, ValidationError as JSONSchemaValidationError

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
    get_tool_usage_stats,
    get_webhook_secret_async,
    regenerate_webhook_secret_async,
    update_agent_async,
    validate_form_data,
)

# Example JSON schemas for common webhook payload patterns (AC#7, Task 5.4)
EXAMPLE_PAYLOAD_SCHEMAS = {
    "ServiceDesk Plus Ticket": {
        "type": "object",
        "properties": {
            "ticket_id": {"type": "string", "description": "Ticket ID"},
            "subject": {"type": "string", "description": "Ticket subject"},
            "description": {"type": "string", "description": "Ticket description"},
            "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
            "status": {"type": "string", "enum": ["open", "pending", "resolved", "closed"]},
        },
        "required": ["ticket_id", "subject"],
    },
    "Jira Issue": {
        "type": "object",
        "properties": {
            "issue_key": {"type": "string", "pattern": "^[A-Z]+-[0-9]+$"},
            "summary": {"type": "string"},
            "description": {"type": "string"},
            "issue_type": {"type": "string", "enum": ["Bug", "Task", "Story", "Epic"]},
            "priority": {"type": "string", "enum": ["Lowest", "Low", "Medium", "High", "Highest"]},
        },
        "required": ["issue_key", "summary"],
    },
    "Generic Event": {
        "type": "object",
        "properties": {
            "event_type": {"type": "string"},
            "timestamp": {"type": "string", "format": "date-time"},
            "data": {"type": "object"},
        },
        "required": ["event_type"],
    },
}


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
            "payload_schema": None,
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

        # Payload Schema Editor (AC#7, Task 5.4)
        if form_data["webhook_enabled"]:
            st.markdown("---")
            st.subheader("📋 Payload Schema (Optional)")
            st.caption(
                "Define JSON Schema to validate incoming webhook payloads. "
                "Leave empty to accept any JSON payload."
            )

            # Example schemas dropdown (Task 5.4c)
            example_choice = st.selectbox(
                "Load Example Schema",
                ["None"] + list(EXAMPLE_PAYLOAD_SCHEMAS.keys()),
                help="Start with a pre-built schema for common use cases",
            )
            if example_choice != "None":
                form_data["payload_schema"] = EXAMPLE_PAYLOAD_SCHEMAS[example_choice]

            # JSON Schema editor (Task 5.4b)
            schema_json = st.text_area(
                "Payload Schema (JSON Schema Draft 2020-12)",
                value=(
                    json.dumps(form_data["payload_schema"], indent=2)
                    if form_data["payload_schema"]
                    else ""
                ),
                height=200,
                placeholder='{\n  "type": "object",\n  "properties": {\n    "field": {"type": "string"}\n  },\n  "required": ["field"]\n}',
                help="JSON Schema format (Draft 2020-12). Validates webhook payload structure.",
            )

            # Validate Schema button (Task 5.4c)
            col1, col2 = st.columns([1, 3])
            with col1:
                validate_clicked = st.button("✓ Validate Schema", use_container_width=True)

            if validate_clicked:
                if schema_json.strip():
                    try:
                        # Parse JSON
                        parsed_schema = json.loads(schema_json)

                        # Validate schema format using Draft202012Validator (2025 best practice)
                        Draft202012Validator.check_schema(parsed_schema)

                        # Store valid schema
                        form_data["payload_schema"] = parsed_schema
                        st.success("✅ Schema is valid (JSON Schema Draft 2020-12)")

                    except json.JSONDecodeError as e:
                        st.error(f"❌ Invalid JSON: {e}")
                    except JSONSchemaValidationError as e:
                        st.error(f"❌ Invalid JSON Schema: {e.message}")
                else:
                    form_data["payload_schema"] = None
                    st.info("ℹ️ No schema defined - will accept any JSON payload")

            # Update schema from text area if manually edited
            if schema_json.strip():
                try:
                    form_data["payload_schema"] = json.loads(schema_json)
                except json.JSONDecodeError:
                    pass  # Keep previous valid schema until user validates

    with tab5:
        st.subheader("Tools Assignment")
        st.write("Select tools this agent can access:")

        # Get tool usage statistics (AC#6, Task 4.3)
        tool_usage = get_tool_usage_stats()

        # Initialize selected tools list
        if "selected_tools" not in st.session_state:
            st.session_state.selected_tools = form_data["tools"].copy()

        # Render tool selection with checkboxes and expandable descriptions (AC#1, AC#2)
        for tool_id, display_name in AVAILABLE_TOOLS.items():
            # Parse tool name and description
            parts = display_name.split(" - ", 1)
            tool_name = parts[0] if parts else tool_id
            tool_desc = parts[1] if len(parts) > 1 else "No description available"

            # Get usage count
            usage_count = tool_usage.get(tool_id, 0)
            usage_label = f" ({usage_count} agents)" if usage_count > 0 else ""

            # Checkbox with tool name + usage count
            is_selected = st.checkbox(
                f"🔧 {tool_name}{usage_label}",
                value=tool_id in st.session_state.selected_tools,
                key=f"create_tool_{tool_id}",
                help=tool_desc,
            )

            # Update selected_tools based on checkbox state
            if is_selected and tool_id not in st.session_state.selected_tools:
                st.session_state.selected_tools.append(tool_id)
            elif not is_selected and tool_id in st.session_state.selected_tools:
                st.session_state.selected_tools.remove(tool_id)

            # Expandable description (AC#2, Task 1.3)
            with st.expander(f"📋 Details for {tool_name}", expanded=False):
                st.markdown(f"**Description:** {tool_desc}")
                st.caption(f"**Tool ID:** `{tool_id}`")
                st.caption(f"**Currently used by:** {usage_count} agent(s)")

        # Sync selected_tools back to form_data
        form_data["tools"] = st.session_state.selected_tools.copy()

    # Form submission (AC#6,7: Validation + messages)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Create Agent", type="primary", use_container_width=True):
            # AC#7, Task 5.3: Validate with warning mode (default)
            is_valid, errors, warnings = validate_form_data(form_data, strict_tool_validation=False)

            # Display errors (blocks submission)
            if not is_valid:
                for error in errors:
                    st.error(error)
            else:
                # Display warnings (does not block submission)
                for warning in warnings:
                    st.warning(warning)
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
                        "triggers": [],
                    }

                    # Add webhook trigger with payload_schema if enabled (AC#7, Task 5.4)
                    if form_data["webhook_enabled"]:
                        webhook_trigger = {"trigger_type": "webhook"}
                        if form_data.get("payload_schema"):
                            webhook_trigger["payload_schema"] = form_data["payload_schema"]
                        agent_payload["triggers"].append(webhook_trigger)

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

        st.subheader("Tools Assignment")
        st.write("Update tools this agent can access:")

        # Get tool usage statistics (AC#6, Task 4.3)
        tool_usage = get_tool_usage_stats()

        # Initialize selected tools for edit form
        if "edit_selected_tools" not in st.session_state:
            st.session_state.edit_selected_tools = form_data["tools"].copy()

        # Render tool selection with checkboxes (AC#1, AC#2, AC#5)
        for tool_id, display_name in AVAILABLE_TOOLS.items():
            # Parse tool name and description
            parts = display_name.split(" - ", 1)
            tool_name = parts[0] if parts else tool_id
            tool_desc = parts[1] if len(parts) > 1 else "No description available"

            # Get usage count
            usage_count = tool_usage.get(tool_id, 0)
            usage_label = f" ({usage_count} agents)" if usage_count > 0 else ""

            # Show "currently assigned" state (AC#2, Task 2.3)
            is_currently_assigned = tool_id in agent.get("tool_ids", [])
            status_indicator = " ✓ Currently Assigned" if is_currently_assigned else ""

            # Checkbox with tool name + usage count + status
            is_selected = st.checkbox(
                f"🔧 {tool_name}{usage_label}{status_indicator}",
                value=tool_id in st.session_state.edit_selected_tools,
                key=f"edit_tool_{tool_id}_{agent_id}",
                help=tool_desc,
            )

            # Update selected_tools based on checkbox state (AC#5, Task 2.4)
            if is_selected and tool_id not in st.session_state.edit_selected_tools:
                st.session_state.edit_selected_tools.append(tool_id)
            elif not is_selected and tool_id in st.session_state.edit_selected_tools:
                st.session_state.edit_selected_tools.remove(tool_id)

            # Expandable description (AC#2, Task 2.1)
            with st.expander(f"📋 Details for {tool_name}", expanded=False):
                st.markdown(f"**Description:** {tool_desc}")
                st.caption(f"**Tool ID:** `{tool_id}`")
                st.caption(f"**Currently used by:** {usage_count} agent(s)")

        # Sync selected_tools back to form_data (AC#3, Task 2.2)
        form_data["tools"] = st.session_state.edit_selected_tools.copy()

        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("✅ Save Changes", type="primary")
        with col2:
            cancel = st.form_submit_button("❌ Cancel")

    if cancel:
        st.rerun()

    if submit:
        # AC#7, Task 5.3: Validate with warning mode (default)
        is_valid, errors, warnings = validate_form_data(form_data, strict_tool_validation=False)

        # Display errors (blocks submission)
        if not is_valid:
            for error in errors:
                st.error(error)
        else:
            # Display warnings (does not block submission)
            for warning in warnings:
                st.warning(warning)
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
                    "tool_ids": form_data["tools"],  # AC#3, AC#5: Include tool assignment updates
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


def agent_detail_view(agent: dict) -> None:
    """
    Render agent detail view modal with edit/delete actions.

    Args:
        agent (dict): The full agent object to display.
    """
    st.markdown(
        """
        <style>
        div[data-testid="stModal"] {
            max-width: 900px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Header
    st.markdown(
        f"""
        ### {agent['name']}
        {format_status_badge(agent['status'])}
        """
    )

    if agent.get("description"):
        st.info(f"📝 {agent['description']}")

    # Tabs for organization
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Configuration", "System Prompt", "Webhook", "Execution History", "Tools"]
    )

    with tab1:
        st.subheader("LLM Configuration")
        llm_config = agent.get("llm_config", {})
        properties = {
            "Provider": llm_config.get("provider", "N/A"),
            "Model": llm_config.get("model", "N/A"),
            "Temperature": llm_config.get("temperature", "N/A"),
            "Max Tokens": llm_config.get("max_tokens", "N/A"),
        }
        for key, value in properties.items():
            col1, col2 = st.columns([1, 3])
            with col1:
                st.write(f"**{key}:**")
            with col2:
                st.write(value)

    with tab2:
        st.subheader("System Prompt")
        st.code(agent.get("system_prompt", "No system prompt configured"), language="text")

    with tab3:
        st.subheader("Webhook Configuration")
        webhook_url = agent.get("webhook_url", "Not configured")
        if webhook_url != "Not configured":
            col1, col2 = st.columns([4, 1])
            with col1:
                st.code(webhook_url, language="text")
            with col2:
                if st.button("📋 Copy", key="copy_webhook_url", use_container_width=True):
                    copy_to_clipboard(webhook_url)
                    st.success("✅ Copied!")
        else:
            st.info("ℹ️ No webhook URL configured")

        # Webhook secret management
        st.markdown("**Webhook Secret:**")
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🔐 View Secret", key="view_secret", use_container_width=True):
                secret = async_to_sync(get_webhook_secret_async)(agent["id"])
                if secret:
                    st.code(secret, language="text")
                else:
                    st.warning("⚠️ No secret configured")
        with col2:
            if st.button("🔄 Regenerate Secret", key="regen_secret", use_container_width=True):
                new_secret = async_to_sync(regenerate_webhook_secret_async)(agent["id"])
                if new_secret:
                    st.success("✅ Secret regenerated!")
                    st.code(new_secret, language="text")

    with tab4:
        st.subheader("Recent Executions")
        st.info("ℹ️ Execution history display coming in Story 8.8")

    with tab5:
        # Tools (AC#4: Display with badges/chips using st.pills)
        st.subheader("Assigned Tools")
        tools = agent.get("tool_ids", [])
        if tools:
            # Use st.pills for badge/chip display (2025 Streamlit best practice)
            # AC#4, Task 3.2, Task 3.3: Show tool names with 🔧 icon
            tool_labels = [f"🔧 {AVAILABLE_TOOLS.get(tool, tool)}" for tool in tools]
            
            # Display pills (Task 3.4: descriptions on hover via help parameter)
            st.pills(
                "assigned_tools_display",
                options=tool_labels,
                selection_mode="multi",
                default=tool_labels,  # Show all as selected/active
                label_visibility="collapsed",
                help="Tools assigned to this agent for task execution"
            )
            
            # Tool descriptions in expandable section
            with st.expander("📋 Tool Details", expanded=False):
                for tool in tools:
                    display_name = AVAILABLE_TOOLS.get(tool, tool)
                    parts = display_name.split(" - ", 1)
                    tool_name = parts[0] if parts else tool
                    tool_desc = parts[1] if len(parts) > 1 else "No description available"
                    st.markdown(f"**🔧 {tool_name}**")
                    st.caption(f"{tool_desc}")
                    st.caption(f"Tool ID: `{tool}`")
                    st.markdown("---")
        else:
            # AC#4, Task 3.5: "No tools assigned" message
            st.info("ℹ️ No tools assigned")

    # Metadata
    st.markdown("---")
    st.caption(f"**Created:** {format_datetime(agent.get('created_at', 'N/A'))}")
    st.caption(f"**Last Updated:** {format_datetime(agent.get('updated_at', 'N/A'))}")
    st.caption(f"**Tenant ID:** `{agent.get('tenant_id', 'N/A')}`")
    st.caption(f"**Agent ID:** `{agent['id']}`")

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
        if st.button("🚀 Activate", use_container_width=True):
            success = async_to_sync(activate_agent_async)(agent["id"])
            if success:
                st.success(f"✅ Agent '{agent['name']}' activated!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Failed to activate agent")
