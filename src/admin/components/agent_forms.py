"""Agent management form dialogs for Streamlit admin UI.

This module provides dialog components for agent CRUD operations:
- Create Agent: Multi-tab form for comprehensive agent configuration
- Edit Agent: Form for updating existing agent properties
- Delete Agent: Confirmation dialog for agent deletion
- Agent Detail: Full agent properties and webhook management
"""

import json
import time

import streamlit as st
from jsonschema import Draft202012Validator, ValidationError as JSONSchemaValidationError

from src.schemas.memory import MemoryConfig

from admin.utils.agent_helpers import (
    AVAILABLE_TOOLS,
    PROMPT_TEMPLATES,
    activate_agent_async,
    async_to_sync,
    copy_to_clipboard,
    create_agent_async,
    delete_agent_async,
    fetch_agent_detail_async,
    fetch_available_models,
    fetch_available_tenants,
    fetch_prompt_templates,
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
            "tenant_id": None,  # Will be set by tenant dropdown
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

    # Use tabs to organize form (AC#3: 6-tab interface including Memory)
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["Basic Info", "LLM Config", "System Prompt", "Triggers", "Tools", "🧠 Memory"]
    )

    with tab1:
        st.subheader("Basic Information")

        # Tenant selection dropdown
        available_tenants = fetch_available_tenants()
        if not available_tenants:
            st.error("❌ No tenants available. Please create a tenant first.")
            return

        tenant_options = [t["tenant_id"] for t in available_tenants]
        tenant_display = {
            t["tenant_id"]: f"{t['name']} ({t['tenant_id']})" for t in available_tenants
        }

        # Find current tenant index (or default to 0)
        default_tenant_index = 0
        if form_data.get("tenant_id") and form_data["tenant_id"] in tenant_options:
            default_tenant_index = tenant_options.index(form_data["tenant_id"])

        selected_tenant_id = st.selectbox(
            "Tenant *",
            tenant_options,
            index=default_tenant_index,
            format_func=lambda x: tenant_display.get(x, x),
            help="Select which tenant this agent belongs to",
            key="create_agent_tenant",
        )
        form_data["tenant_id"] = selected_tenant_id

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
            key="create_agent_status",
        )

    with tab2:
        st.subheader("LLM Configuration")
        form_data["provider"] = st.selectbox(
            "LLM Provider *",
            ["litellm", "openai", "anthropic"],
            index=0,
            help="LiteLLM proxy for multi-model support",
            key="create_agent_provider",
        )
        # Fetch available models dynamically from LiteLLM (Story 9.1)
        available_models = fetch_available_models()
        model_options = [model["id"] for model in available_models]
        model_display = {m["id"]: f"{m['name']} ({m['provider']})" for m in available_models}

        # Find current model index (or default to 0)
        default_index = 0
        if form_data["model"] in model_options:
            default_index = model_options.index(form_data["model"])

        selected_model_id = st.selectbox(
            "Model *",
            model_options,
            index=default_index,
            format_func=lambda x: model_display.get(x, x),
            help="Select LLM model to use",
            key="create_agent_model",
        )
        form_data["model"] = selected_model_id
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

        # Fetch templates dynamically from API (syncs with System Prompt Editor)
        available_templates = fetch_prompt_templates()
        template_names = ["None"] + [t["name"] for t in available_templates]
        template_map = {t["name"]: t["template_text"] for t in available_templates}

        # Template selector
        template_choice = st.selectbox(
            "Load Template (optional)",
            template_names,
            help="Start with a pre-built template or write custom. Templates sync with System Prompt Editor.",
            key="create_agent_template",
        )
        if template_choice != "None" and template_choice in template_map:
            form_data["system_prompt"] = template_map[template_choice]

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
                key="create_agent_example_schema",
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
        # Unified Tool Assignment (Story 11.1.6)
        from admin.utils.tool_assignment_ui_helpers import render_unified_tool_list

        # Initialize MCP tool assignments in form_data if not present
        if "mcp_tool_assignments" not in form_data:
            form_data["mcp_tool_assignments"] = []

        # Convert legacy tool IDs to integers (OpenAPI tools use integer IDs)
        selected_openapi_ids = [
            int(tid) for tid in form_data.get("tools", []) if str(tid).isdigit()
        ]

        # Render unified tool selection UI
        # Use "create_" prefix to avoid session state conflicts with main page and edit dialog
        openapi_tool_ids, mcp_assignments = render_unified_tool_list(
            tenant_id=form_data["tenant_id"],
            selected_tool_ids=selected_openapi_ids,
            selected_mcp_tools=form_data.get("mcp_tool_assignments", []),
            key_prefix="create_",  # Unique namespace for create dialog
        )

        # Update form_data with selections
        form_data["tools"] = openapi_tool_ids
        form_data["mcp_tool_assignments"] = mcp_assignments

    with tab6:
        st.subheader("🧠 Memory Configuration")
        st.write(
            "Configure memory settings for this agent to maintain context across conversations."
        )

        # Import memory UI helpers
        from admin.utils.memory_config_ui_helpers import (
            render_memory_config_form,
            get_memory_config_defaults,
        )

        # Initialize memory config in form_data if not present
        if "memory_config" not in form_data:
            form_data["memory_config"] = get_memory_config_defaults()

        # Render memory configuration form (AC#1, AC#2, AC#3, AC#4)
        # This function handles short-term, long-term, and agentic memory configuration
        memory_form_data = render_memory_config_form(form_data["memory_config"])
        form_data["memory_config"] = MemoryConfig(
            short_term=memory_form_data["short_term"],
            long_term=memory_form_data["long_term"],
            agentic=memory_form_data["agentic"],
        )

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
                        "mcp_tool_assignments": form_data.get("mcp_tool_assignments", []),  # Story 11.1.6: Already dicts from render_unified_tool_list
                        "memory_config": (
                            form_data["memory_config"].model_dump()
                            if form_data.get("memory_config")
                            else {}
                        ),  # AC#1: Include memory configuration (convert Pydantic model to dict)
                        "triggers": [],
                    }

                    # Add webhook trigger with payload_schema if enabled (AC#7, Task 5.4)
                    if form_data["webhook_enabled"]:
                        webhook_trigger = {"trigger_type": "webhook"}
                        if form_data.get("payload_schema"):
                            webhook_trigger["payload_schema"] = form_data["payload_schema"]
                        agent_payload["triggers"].append(webhook_trigger)

                    agent = async_to_sync(create_agent_async)(agent_payload, form_data["tenant_id"])
                    if agent:
                        st.success(f"✅ Agent '{form_data['name']}' created successfully!")
                        st.info(f"**Webhook URL:** `{agent.get('webhook_url', 'N/A')}`")
                        st.session_state.refresh_trigger += 1
                        # Clear create dialog session state after successful creation
                        if "create_selected_tools" in st.session_state:
                            del st.session_state["create_selected_tools"]
                        st.session_state.show_create_form = False
                        if st.button("✅ Done"):
                            st.rerun()

    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            # Clear create dialog session state on cancel
            if "create_selected_tools" in st.session_state:
                del st.session_state["create_selected_tools"]
            st.session_state.show_create_form = False
            st.rerun()


@st.dialog("✏️ Edit Agent", width="large")
def edit_agent_form(agent_id: str):
    """Modal dialog for editing an agent.

    Args:
        agent_id: UUID of agent to edit
    """
    # Get tenant_id with fallback mechanism
    tenant_id = st.session_state.get("selected_agent_tenant_id")

    # Fallback: Try to get from page-level selected tenant
    if not tenant_id:
        tenant_id = st.session_state.get("selected_tenant")

    # Fallback: Show helpful error if still not found
    if not tenant_id:
        st.error("❌ Please select a tenant from the dropdown at the top of the page first.")
        st.info("💡 After selecting a tenant, navigate back to Agent Management and click Edit again.")
        return

    with st.spinner("Loading agent..."):
        agent = async_to_sync(fetch_agent_detail_async)(agent_id, tenant_id)

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
            "mcp_tool_assignments": agent.get(
                "mcp_tool_assignments", []
            ),  # Story 11.1.6: Include MCP tool assignments
            "memory_config": agent.get(
                "memory_config", {}
            ),  # AC#1: Include memory config from agent
        }

    form_data = st.session_state.edit_form_data

    # Unified Tool Assignment (Story 11.1.6) - OUTSIDE form so buttons work
    st.divider()
    from admin.utils.tool_assignment_ui_helpers import render_unified_tool_list
    import json

    # Convert legacy tool IDs to integers (OpenAPI tools use integer IDs)
    selected_openapi_ids = [
        int(tid) for tid in form_data.get("tools", []) if str(tid).isdigit()
    ]

    # Render unified tool selection UI (in_form_context=False - outside form!)
    # Use "edit_" prefix to avoid key conflicts with main page tool discovery UI
    openapi_tool_ids, mcp_assignments = render_unified_tool_list(
        tenant_id=tenant_id,
        selected_tool_ids=selected_openapi_ids,
        selected_mcp_tools=form_data.get("mcp_tool_assignments", []),
        in_form_context=False,  # Buttons work outside form!
        key_prefix="edit_",  # Unique prefix for edit dialog
    )

    st.divider()
    st.subheader("📝 Agent Configuration")

    with st.form("edit_agent_form"):
        # NO HIDDEN FIELDS NEEDED!
        # We read tool selections directly from session state on form submit.
        # Session state persists across reruns, so Select All updates are preserved.
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
                key="edit_agent_provider",
            )
            form_data["temperature"] = st.slider(
                "Temperature",
                0.0,
                2.0,
                form_data["temperature"],
                step=0.1,
            )

        with col2:
            # Fetch available models dynamically from LiteLLM (Story 9.1)
            available_models = fetch_available_models()
            model_options = [model["id"] for model in available_models]
            model_display = {m["id"]: f"{m['name']} ({m['provider']})" for m in available_models}

            # Find current model index (or default to 0)
            default_index = 0
            if form_data["model"] in model_options:
                default_index = model_options.index(form_data["model"])

            form_data["model"] = st.selectbox(
                "Model *",
                model_options,
                index=default_index,
                format_func=lambda x: model_display.get(x, x),
                key="edit_agent_model",
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

        # Memory Configuration section (AC#1)
        st.divider()
        st.subheader("🧠 Memory Configuration")
        st.write("Configure agent memory settings for this agent.")

        from admin.utils.memory_config_ui_helpers import render_memory_config_form

        # Render memory configuration form for editing
        # Convert dict to MemoryConfig object if needed (fix for AttributeError: 'dict' object has no attribute 'short_term')
        try:
            current_memory_config = (
                MemoryConfig(**form_data["memory_config"]) if form_data["memory_config"] else None
            )
        except Exception:
            current_memory_config = None
        memory_form_data = render_memory_config_form(current_memory_config)
        form_data["memory_config"] = MemoryConfig(
            short_term=memory_form_data["short_term"],
            long_term=memory_form_data["long_term"],
            agentic=memory_form_data["agentic"],
        )

        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("✅ Save Changes", type="primary")
        with col2:
            cancel = st.form_submit_button("❌ Cancel")

    if cancel:
        st.rerun()

    if submit:
        # Read tool selections directly from NAMESPACED session state (edit dialog uses "edit_" prefix)
        # Session state has the live values after user clicks Select All, checkboxes, etc.
        # CRITICAL: Convert UUIDs to strings for JSON serialization
        actual_openapi_ids = [str(id) for id in st.session_state["edit_selected_tools"]["openapi"]]
        actual_mcp_keys = list(st.session_state["edit_selected_tools"]["mcp"])

        # Reconstruct MCP tool assignments from keys
        # Format: server_id_tool_name -> MCPToolAssignment(server_id="...", tool_name="...", primitive_type="tool")
        from admin.utils.tool_assignment_ui_helpers import fetch_unified_tools
        from schemas.agent import MCPToolAssignment

        all_tools = fetch_unified_tools(tenant_id)
        mcp_tools_lookup = {t.get("id"): t for t in all_tools if t.get("source_type") == "mcp"}

        actual_mcp_assignments = []
        for mcp_key in actual_mcp_keys:
            parts = mcp_key.split("_", 1)
            if len(parts) == 2:
                server_id, tool_name = parts
                # Find the tool to get primitive type
                tool = next(
                    (t for t in all_tools
                     if str(t.get("mcp_server_id")) == server_id and t.get("name") == tool_name),
                    None
                )
                if tool:
                    # Create MCPToolAssignment Pydantic model with correct field names
                    # CRITICAL: Convert UUID objects to strings for JSON serialization
                    actual_mcp_assignments.append(MCPToolAssignment(
                        id=str(tool.get("id")) if tool.get("id") else None,
                        name=tool.get("name"),
                        source_type="mcp",
                        mcp_server_id=str(tool.get("mcp_server_id")) if tool.get("mcp_server_id") else None,
                        mcp_server_name=tool.get("mcp_server_name"),
                        mcp_primitive_type=tool.get("mcp_primitive_type", "tool"),
                    ))

        # Update form_data with actual selections from hidden fields
        form_data["tools"] = actual_openapi_ids
        form_data["mcp_tool_assignments"] = actual_mcp_assignments

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
                    "tool_ids": actual_openapi_ids,  # Use actual selections from hidden fields!
                    "mcp_tool_assignments": [
                        a.model_dump(mode='json') for a in actual_mcp_assignments
                    ],  # CRITICAL: Use mode='json' to convert UUIDs to strings!
                    "memory_config": (
                        form_data["memory_config"].model_dump(mode='json')
                        if form_data.get("memory_config")
                        else {}
                    ),  # AC#1: Include memory configuration (convert Pydantic model to dict)
                }
                agent = async_to_sync(update_agent_async)(agent_id, tenant_id, updates)
                if agent:
                    st.success("✅ Agent updated successfully!")
                    st.session_state.refresh_trigger += 1
                    # Clear edit dialog session state after successful save
                    if "edit_selected_tools" in st.session_state:
                        del st.session_state["edit_selected_tools"]
                    if "edit_form_data" in st.session_state:
                        del st.session_state["edit_form_data"]
                    st.session_state.show_edit_form = False
                    if st.button("✅ Done"):
                        st.rerun()


@st.dialog("🗑️ Delete Agent")
def delete_agent_confirm(agent_id: str):
    """Modal dialog for confirming agent deletion.

    Args:
        agent_id: UUID of agent to delete (soft delete)
    """
    # Get tenant_id with fallback mechanism
    tenant_id = st.session_state.get("selected_agent_tenant_id")

    # Fallback: Try to get from page-level selected tenant
    if not tenant_id:
        tenant_id = st.session_state.get("selected_tenant")

    # Fallback: Show helpful error if still not found
    if not tenant_id:
        st.error("❌ Please select a tenant from the dropdown at the top of the page first.")
        st.info("💡 After selecting a tenant, navigate back to Agent Management and click Delete again.")
        return

    with st.spinner("Loading agent..."):
        agent = async_to_sync(fetch_agent_detail_async)(agent_id, tenant_id)

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
                success = async_to_sync(delete_agent_async)(agent_id, tenant_id)
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


@st.dialog("🔍 Agent Details", width="large")
def agent_detail_view(agent: dict):
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

    # Tabs for organization - including Memory and Test Agent tabs (AC#1)
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
        [
            "Configuration",
            "System Prompt",
            "Webhook",
            "Execution History",
            "Tools",
            "🧠 Memory",
            "🧪 Test Agent",
        ]
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

        # Check if agent has webhook trigger
        triggers = agent.get("triggers", [])
        has_webhook = any(t.get("trigger_type") == "webhook" for t in triggers)

        if not has_webhook:
            st.info("ℹ️ This agent does not have webhook triggers configured")
        else:
            import os

            # Webhook URL
            base_url = os.getenv("PUBLIC_URL", "http://localhost:8000")
            webhook_url = f"{base_url}/webhook/agents/{agent['id']}/webhook"

            st.markdown("**Webhook URL:**")
            col1, col2 = st.columns([4, 1])
            with col1:
                st.code(webhook_url, language="text")
            with col2:
                if st.button("📋 Copy", key="copy_webhook_url", use_container_width=True):
                    st.success("✅ Copied!")

            # HMAC Secret (masked by default)
            st.markdown("**HMAC Secret (Base64):**")
            col1, col2 = st.columns([4, 1])
            with col1:
                st.text_input(
                    "Secret",
                    value="*" * 40,
                    type="password",
                    key="webhook_secret_masked",
                    help="Click 'Show' to reveal the secret",
                    label_visibility="collapsed",
                )
            with col2:
                if st.button("👁 Show", key="view_secret", use_container_width=True):
                    secret = async_to_sync(get_webhook_secret_async)(
                        agent["id"], agent["tenant_id"]
                    )
                    if secret:
                        st.code(secret, language="text")
                    else:
                        st.warning("⚠️ No secret configured")

            # Instructions
            st.info(
                """
            **How to configure your external system:**

            1. Copy the Webhook URL above
            2. Copy the HMAC Secret (click 'Show' button)
            3. Configure your system to:
               - Send POST requests to the Webhook URL
               - Generate HMAC-SHA256 signature using the secret
               - Add header: `X-Hub-Signature-256: sha256={signature}`
            """
            )

            # Code examples
            with st.expander("💻 Code Example (Python)", expanded=False):
                # Fetch secret for code example
                secret_for_example = async_to_sync(get_webhook_secret_async)(
                    agent["id"], agent["tenant_id"]
                )
                if secret_for_example:
                    st.code(
                        f"""
import hmac
import hashlib
import json
import base64
import requests

# Configuration
WEBHOOK_URL = "{webhook_url}"
HMAC_SECRET = "{secret_for_example}"  # Your HMAC secret

# Example payload
payload = {{
    "ticket_id": "TKT-12345",
    "description": "Example ticket",
    "priority": "High"
}}

# Generate signature
payload_str = json.dumps(payload, separators=(',', ':'))
secret_bytes = base64.b64decode(HMAC_SECRET)
signature = hmac.new(secret_bytes, payload_str.encode(), hashlib.sha256).hexdigest()

# Send request
headers = {{
    "Content-Type": "application/json",
    "X-Hub-Signature-256": f"sha256={{signature}}"
}}

response = requests.post(WEBHOOK_URL, json=payload, headers=headers)
print(f"Status: {{response.status_code}}")
print(f"Response: {{response.json()}}")
""",
                        language="python",
                    )

            with st.expander("📋 cURL Example", expanded=False):
                st.markdown(
                    f"""
                Generate a signature using the Python script above, then use:
                ```bash
                curl -X POST '{webhook_url}' \\
                  -H 'Content-Type: application/json' \\
                  -H 'X-Hub-Signature-256: sha256={{YOUR_SIGNATURE}}' \\
                  -d '{{"ticket_id":"TKT-123","description":"Test"}}'
                ```
                """
                )

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
                help="Tools assigned to this agent for task execution",
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

    with tab6:
        # Memory Configuration tab (AC#1, AC#5, AC#6)
        st.subheader("🧠 Memory Management")
        st.write("View and manage this agent's memory configuration and state.")

        # Import memory UI helpers
        from admin.utils.memory_config_ui_helpers import (
            render_memory_config_form,
            render_memory_viewer,
            clear_memory_confirmation,
            render_memory_stats_summary,
        )

        # Get agent's current memory configuration
        agent_memory_config = agent.get("memory_config", {})

        # Display memory configuration summary (AC#5: View Memory button equivalent)
        st.subheader("📊 Memory Configuration")
        render_memory_stats_summary(agent_memory_config)

        # Memory viewer section (AC#5: View Memory button)
        st.subheader("👁️ View Current Memory State")
        with st.expander("Expand to view agent memory contents", expanded=False):
            render_memory_viewer(agent["id"])

        # Memory clearing section (AC#6: Clear Memory button)
        st.subheader("🗑️ Clear Memory")
        clear_memory_confirmation(agent["id"])

    with tab7:
        # Test Agent tab (AC#1, AC#2, AC#3-AC#8)
        from admin.utils.agent_test_ui_helpers import render_test_agent_tab

        render_test_agent_tab(agent["id"], agent["tenant_id"])

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
        # Only show Activate button for DRAFT agents (Bug #6 fix)
        if agent.get("status") == "draft":
            if st.button("🚀 Activate", use_container_width=True):
                success = async_to_sync(activate_agent_async)(agent["id"])
                if success:
                    st.success(f"✅ Agent '{agent['name']}' activated!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Failed to activate agent")
        else:
            # Show status badge for non-draft agents
            st.info(f"Status: {format_status_badge(agent.get('status', 'unknown'))}")
