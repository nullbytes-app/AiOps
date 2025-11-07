"""
LLM Provider Configuration Page - Full CRUD Interface.

Implements comprehensive LLM provider management for AI Agents admin UI:
- View all providers with connection status
- Add new provider with API key encryption
- Edit existing provider (masked API key)
- Test provider connection and fetch available models
- Delete provider with confirmation (soft delete)
- Regenerate litellm-config.yaml

Story: 8.11 - Provider Configuration UI
"""

import asyncio
from datetime import datetime

import httpx
import pandas as pd
import streamlit as st
from admin.utils.db_helper import show_connection_status
from admin.utils.provider_helpers import (
    get_status_indicator,
    mask_api_key,
    get_api_base,
    get_admin_headers,
    fetch_providers,
    create_provider_api,
    test_connection_api,
    delete_provider_api,
    regenerate_config_api,
    edit_model_form,
)
from admin.utils.fallback_helpers import (
    show_fallback_configuration_tab,
    show_trigger_configuration_tab,
    show_testing_interface_tab,
    show_metrics_dashboard_tab,
)


# ============================================================================
# Dialog Functions for Add/Edit/Delete Operations
# ============================================================================


@st.dialog("➕ Add New LLM Provider", width="large")
def add_provider_dialog():
    """Modal dialog for adding a new LLM provider."""
    st.markdown("Configure a new LLM provider for the AI Agents platform")

    with st.form("add_provider_form"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input(
                "Provider Name *",
                placeholder="My OpenAI Account",
                help="Descriptive name for this provider configuration"
            )

            provider_type = st.selectbox(
                "Provider Type *",
                options=["openai", "anthropic", "azure_openai", "bedrock", "replicate", "together_ai", "custom"],
                format_func=lambda x: {
                    "openai": "OpenAI",
                    "anthropic": "Anthropic",
                    "azure_openai": "Azure OpenAI",
                    "bedrock": "AWS Bedrock",
                    "replicate": "Replicate",
                    "together_ai": "Together AI",
                    "custom": "Custom Provider",
                }[x],
                help="Select the LLM provider type"
            )

        with col2:
            # Default API base URLs by provider type
            default_urls = {
                "openai": "https://api.openai.com/v1",
                "anthropic": "https://api.anthropic.com",
                "azure_openai": "https://YOUR_RESOURCE.openai.azure.com",
                "bedrock": "https://bedrock-runtime.us-east-1.amazonaws.com",
                "replicate": "https://api.replicate.com",
                "together_ai": "https://api.together.xyz",
                "custom": "https://",
            }

            api_base_url = st.text_input(
                "API Base URL *",
                value=default_urls.get(provider_type, "https://"),
                help="Provider API endpoint URL"
            )

            api_key = st.text_input(
                "API Key *",
                type="password",
                placeholder="Enter API key (will be encrypted)",
                help="API key will be encrypted before storage using Fernet encryption"
            )

        # Validation help text
        if provider_type == "openai":
            st.info("ℹ️ OpenAI API keys start with 'sk-' and are 48-51 characters long")
        elif provider_type == "anthropic":
            st.info("ℹ️ Anthropic API keys start with 'sk-ant-'")

        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            test_conn = st.form_submit_button("🔍 Test Connection", use_container_width=True)
        with col2:
            submit = st.form_submit_button("✅ Create Provider", use_container_width=True)
        with col3:
            cancel = st.form_submit_button("❌ Cancel", use_container_width=True)

    if cancel:
        st.rerun()

    # Test connection handler
    if test_conn:
        if not all([name, provider_type, api_base_url, api_key]):
            st.error("All fields are required")
        else:
            with st.spinner(f"Testing connection to {provider_type}..."):
                # Create temporary provider to test
                result = asyncio.run(create_provider_api(name, provider_type, api_base_url, api_key))
                if result:
                    provider_id = result.get("id")
                    test_result = asyncio.run(test_connection_api(provider_id))

                    if test_result and test_result.get("success"):
                        st.success(f"✅ Connected successfully! {len(test_result.get('models', []))} models available")
                        st.json(test_result.get("models", [])[:10])  # Show first 10 models
                    else:
                        st.error(f"❌ Connection failed: {test_result.get('error', 'Unknown error')}")

                    # Delete temporary provider
                    asyncio.run(delete_provider_api(provider_id))

    # Create provider handler
    if submit:
        # Validation
        if not all([name, provider_type, api_base_url, api_key]):
            st.error("All fields are required")
            return

        # Provider-specific validation
        if provider_type == "openai" and not api_key.startswith("sk-"):
            st.error("OpenAI API keys must start with 'sk-'")
            return

        if provider_type == "anthropic" and not api_key.startswith("sk-ant-"):
            st.error("Anthropic API keys must start with 'sk-ant-'")
            return

        if not api_base_url.startswith("https://"):
            st.error("API base URL must use HTTPS")
            return

        # Create provider
        with st.spinner("Creating provider..."):
            result = asyncio.run(create_provider_api(name, provider_type, api_base_url, api_key))

            if result:
                st.success(f"✅ Provider '{name}' created successfully! ID: {result.get('id')}")
                st.info("🔄 Don't forget to test the connection and sync models")
                st.rerun()


@st.dialog("🗑️ Delete Provider", width="small")
def delete_provider_dialog(provider_id: int, provider_name: str):
    """
    Modal dialog for deleting a provider.

    Args:
        provider_id: Provider database ID
        provider_name: Provider name for confirmation
    """
    st.markdown(f"### Are you sure you want to delete **{provider_name}**?")
    st.warning("⚠️ This will soft delete the provider (set enabled=false) and disable all associated models.")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Yes, Delete", use_container_width=True, type="primary"):
            success = asyncio.run(delete_provider_api(provider_id))
            if success:
                st.success(f"Provider '{provider_name}' deleted")
                st.rerun()

    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            st.rerun()


@st.dialog("🎛️ Manage Models", width="large")
def manage_models_dialog(provider_id: int, provider_name: str):
    """
    Modal dialog for managing models (AC #4, #5).
    
    Features:
    - Enable/disable individual models via checkboxes (AC #4)
    - Edit model configuration: cost, context_window, display_name (AC #5)
    - Bulk enable/disable operations
    
    Args:
        provider_id: Provider database ID
        provider_name: Provider name for display
    """
    st.markdown(f"### Manage Models for **{provider_name}**")
    
    # Fetch models
    response = asyncio.run(get_models_api(provider_id))
    
    if response.status_code != 200:
        st.error(f"Failed to fetch models: {response.text}")
        return
    
    models = response.json()
    
    if not models:
        st.info("No models found. Click 'Sync Models' to fetch available models from provider.")
        if st.button("Close"):
            st.rerun()
        return
    
    # Bulk actions header
    st.markdown("#### Bulk Actions")
    col1, col2, col3 = st.columns([1, 1, 4])
    
    with col1:
        if st.button("✅ Enable All", use_container_width=True):
            model_ids = [m["id"] for m in models]
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{get_api_base()}/api/llm-models/bulk-enable",
                    headers=get_admin_headers(),
                    json={"model_ids": model_ids},
                )
                if response.status_code == 200:
                    st.success(f"Enabled {len(model_ids)} models")
                    st.rerun()
                else:
                    st.error(f"Failed to enable models: {response.text}")
    
    with col2:
        if st.button("❌ Disable All", use_container_width=True):
            model_ids = [m["id"] for m in models]
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{get_api_base()}/api/llm-models/bulk-disable",
                    headers=get_admin_headers(),
                    json={"model_ids": model_ids},
                )
                if response.status_code == 200:
                    st.success(f"Disabled {len(model_ids)} models")
                    st.rerun()
                else:
                    st.error(f"Failed to disable models: {response.text}")
    
    # Models table
    st.markdown("#### Models")
    
    # Create DataFrame for display
    df_data = []
    for m in models:
        df_data.append({
            "ID": m["id"],
            "Model Name": m["model_name"],
            "Display Name": m.get("display_name", m["model_name"]),
            "Enabled": "✅" if m.get("enabled") else "❌",
            "Input Cost": f"${m['cost_per_input_token']:.6f}" if m.get("cost_per_input_token") else "Not set",
            "Output Cost": f"${m['cost_per_output_token']:.6f}" if m.get("cost_per_output_token") else "Not set",
            "Context": f"{m['context_window']:,}" if m.get("context_window") else "Not set",
        })
    
    df = pd.DataFrame(df_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Model actions
    st.markdown("#### Model Actions")
    
    for model in models:
        with st.expander(f"{model['model_name']} (ID: {model['id']})"):
            col1, col2 = st.columns(2)
            
            with col1:
                # Toggle enabled/disabled
                current_status = "Enabled" if model.get("enabled") else "Disabled"
                new_status = "Disable" if model.get("enabled") else "Enable"
                
                if st.button(f"{new_status} Model", key=f"toggle_{model['id']}"):
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        response = await client.post(
                            f"{get_api_base()}/api/llm-models/{model['id']}/toggle",
                            headers=get_admin_headers(),
                        )
                        if response.status_code == 200:
                            st.success(f"Model {new_status.lower()}d")
                            st.rerun()
                        else:
                            st.error(f"Failed to toggle model: {response.text}")
            
            with col2:
                # Edit configuration button
                if st.button("✏️ Edit Configuration", key=f"edit_{model['id']}"):
                    edit_model_form(model)
    
    # Close button
    if st.button("Close", use_container_width=True):
        st.rerun()


# ============================================================================
# Helper Functions for Model Operations
# ============================================================================


async def sync_models_api(provider_id: int):
    """Sync models from provider API."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{get_api_base()}/api/llm-providers/{provider_id}/sync-models",
            headers=get_admin_headers(),
        )
        return response


async def get_models_api(provider_id: int):
    """Get models for a provider."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{get_api_base()}/api/llm-providers/{provider_id}/models",
            headers=get_admin_headers(),
        )
        return response


# ============================================================================
# Main Page
# ============================================================================


def main():
    """Main Streamlit page for LLM provider configuration."""
    st.title("🔧 LLM Provider Configuration")
    st.markdown("Manage API keys and available models for LLM providers")

    # Show database connection status
    show_connection_status()

    # Action buttons header
    col1, col2, col3 = st.columns([2, 2, 6])

    with col1:
        if st.button("➕ Add Provider", use_container_width=True):
            add_provider_dialog()

    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    with col3:
        if st.button("⚙️ Regenerate Config", use_container_width=True):
            with st.spinner("Regenerating litellm-config.yaml..."):
                result = asyncio.run(regenerate_config_api())

                if result:
                    st.success("✅ Config regenerated successfully!")
                    st.info(f"Backup: {result.get('backup_path')}")
                    st.warning(
                        f"⚠️ LiteLLM proxy restart required:\n\n"
                        f"```bash\n{result.get('restart_command')}\n```"
                    )

    # Fetch and display providers
    providers = asyncio.run(fetch_providers())

    if not providers:
        st.info("No providers configured yet. Click '➕ Add Provider' to get started.")
        return

    # Convert to DataFrame for display
    df_data = []
    for p in providers:
        df_data.append({
            "ID": p["id"],
            "Name": p["name"],
            "Type": p["provider_type"],
            "Status": get_status_indicator(
                datetime.fromisoformat(p["last_test_at"]) if p.get("last_test_at") else None,
                p.get("last_test_success")
            ),
            "API Key": mask_api_key(p.get("api_key_masked", "")),
            "Last Test": p.get("last_test_at", "Never")[:19] if p.get("last_test_at") else "Never",
            "Enabled": "✅" if p.get("enabled") else "❌",
        })

    df = pd.DataFrame(df_data)

    # Display provider list
    st.markdown("### Configured Providers")
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.NumberColumn("ID", width="small"),
            "Status": st.column_config.TextColumn("Status", width="small"),
        },
    )

    # Provider details expandable section
    st.markdown("### Provider Actions")

    for provider in providers:
        with st.expander(f"{provider['name']} ({provider['provider_type']})"):
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                if st.button("🔍 Test Connection", key=f"test_{provider['id']}"):
                    with st.spinner(f"Testing {provider['name']}..."):
                        result = asyncio.run(test_connection_api(provider["id"]))

                        if result and result.get("success"):
                            st.success(f"✅ Connected! {len(result.get('models', []))} models available")
                            with st.expander("Available Models"):
                                st.json(result.get("models", []))
                        else:
                            st.error(f"❌ Failed: {result.get('error', 'Unknown error')}")

            with col2:
                if st.button("🔄 Sync Models", key=f"sync_{provider['id']}"):
                    with st.spinner(f"Syncing models from {provider['name']}..."):
                        response = asyncio.run(sync_models_api(provider["id"]))
                        if response.status_code == 200:
                            result = response.json()
                            st.success(
                                f"✅ Synced {result.get('created', 0)} new models "
                                f"({result.get('skipped', 0)} already exist)"
                            )
                        else:
                            st.error(f"Failed to sync models: {response.text}")

            with col3:
                if st.button("🎛️ Manage Models", key=f"models_{provider['id']}"):
                    manage_models_dialog(provider["id"], provider["name"])

            with col4:
                if st.button("🗑️ Delete", key=f"delete_{provider['id']}"):
                    delete_provider_dialog(provider["id"], provider["name"])

            # Provider details
            st.markdown("**Provider Details:**")
            st.code(f"""
ID: {provider['id']}
Name: {provider['name']}
Type: {provider['provider_type']}
API Base URL: {provider['api_base_url']}
API Key: {mask_api_key(provider.get('api_key_masked', ''))}
Enabled: {provider.get('enabled')}
Last Test: {provider.get('last_test_at', 'Never')}
Created: {provider.get('created_at', 'Unknown')}
            """)

    # ========================================================================
    # Fallback Chain Configuration Tabs (Story 8.12)
    # ========================================================================
    st.divider()
    st.markdown("## ⛓️ Fallback Chain Configuration")

    # Create tabs for fallback management
    tab1, tab2, tab3, tab4 = st.tabs([
        "Fallback Chains",
        "Triggers",
        "Test Fallbacks",
        "Metrics"
    ])

    with tab1:
        show_fallback_configuration_tab(providers)

    with tab2:
        show_trigger_configuration_tab()

    with tab3:
        show_testing_interface_tab(providers)

    with tab4:
        show_metrics_dashboard_tab()


if __name__ == "__main__":
    # Run with async support
    asyncio.run(main())
