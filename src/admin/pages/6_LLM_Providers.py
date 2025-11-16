"""
LLM Provider Management Page - LiteLLM API Edition

Story 9.2: Provider Management via LiteLLM API
- Refactored to call LiteLLM /model/new, /v1/model/info, /model/delete APIs
- No database storage of provider credentials
- Single source of truth: LiteLLM proxy
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from admin.utils.db_helper import show_connection_status
from services.litellm_provider_service import LiteLLMProviderService

logger = logging.getLogger(__name__)


# ============================================================================
# Dialog Functions
# ============================================================================


@st.dialog("➕ Add LLM Model", width="large")
def add_model_dialog():
    """Modal dialog for adding a new LLM model via LiteLLM API."""
    st.markdown("Configure a new LLM model via LiteLLM proxy")

    with st.form("add_model_form"):
        col1, col2 = st.columns(2)

        with col1:
            model_name = st.text_input(
                "Model Name (LiteLLM ID) *",
                placeholder="gpt-4-production",
                help="Unique identifier for this model in LiteLLM (e.g., gpt-4-production)",
            )

            provider_type = st.selectbox(
                "Provider Type *",
                options=[
                    "openai",
                    "anthropic",
                    "azure",
                    "bedrock",
                    "vertex_ai",
                    "cohere",
                    "replicate",
                ],
                help="Select the underlying LLM provider",
            )

        with col2:
            # Underlying model name for the provider
            model_identifier = st.text_input(
                "Model Identifier *",
                placeholder="gpt-4 or claude-3-opus-20240229",
                help=f"Model name for {provider_type} (e.g., gpt-4, claude-3-opus-20240229)",
            )

            api_key = st.text_input(
                "API Key *",
                type="password",
                placeholder="Provider API key",
                help="API key will be sent directly to LiteLLM (not stored in app database)",
            )

        # Optional fields
        st.markdown("### Optional Configuration")
        col1, col2 = st.columns(2)

        with col1:
            api_base = st.text_input(
                "API Base URL",
                placeholder="https://api.example.com/v1",
                help="Custom API base URL (if different from provider default)",
            )

        with col2:
            rpm_limit = st.number_input(
                "Rate Limit (RPM)",
                min_value=1,
                max_value=10000,
                value=None,
                help="Requests per minute limit (optional)",
            )

        tags = st.text_input(
            "Tags (comma-separated)",
            placeholder="production, team-a, high-priority",
            help="Optional tags for organizing models",
        )

        description = st.text_area(
            "Description",
            placeholder="Model description for documentation",
            max_chars=500,
        )

        # Buttons
        col1, col2, col3 = st.columns([1, 1, 2])
        submit = col2.form_submit_button("✅ Add Model", use_container_width=True)
        cancel = col3.form_submit_button("❌ Cancel", use_container_width=True)

    if cancel:
        st.rerun()

    if submit:
        # Validation
        if not all([model_name, provider_type, model_identifier, api_key]):
            st.error("All required fields must be filled")
            return

        # Prepare LiteLLM params
        litellm_params = {
            "model": f"{provider_type}/{model_identifier}",
            "api_key": api_key,
        }

        if api_base:
            litellm_params["api_base"] = api_base

        if rpm_limit:
            litellm_params["rpm"] = rpm_limit

        # Prepare model_info
        model_info = {}
        if description:
            model_info["description"] = description

        if tags:
            model_info["tags"] = [t.strip() for t in tags.split(",")]

        # Call service
        with st.spinner("Adding model to LiteLLM..."):
            try:
                service = LiteLLMProviderService()
                result = asyncio.run(
                    service.add_model_to_litellm(
                        model_name=model_name,
                        litellm_params=litellm_params,
                        model_info=model_info if model_info else None,
                    )
                )

                st.success(f"✅ Model '{model_name}' added successfully!")
                logger.info(f"Added model {model_name} to LiteLLM")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to add model: {str(e)}")
                logger.error(f"Error adding model: {e}")


@st.dialog("🗑️ Delete Model", width="small")
def delete_model_dialog(model_name: str):
    """
    Modal dialog for deleting a model.

    Args:
        model_name: Model name to delete
    """
    st.markdown(f"### Delete Model: **{model_name}**?")
    st.warning(
        "⚠️ This will remove the model from LiteLLM. "
        "It will disappear from all agent configurations."
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Yes, Delete", use_container_width=True, type="primary"):
            with st.spinner("Deleting model..."):
                try:
                    service = LiteLLMProviderService()
                    result = asyncio.run(service.delete_model(model_name))
                    st.success(f"✅ Model '{model_name}' deleted")
                    logger.info(f"Deleted model {model_name} from LiteLLM")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to delete model: {str(e)}")
                    logger.error(f"Error deleting model: {e}")

    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            st.rerun()


# ============================================================================
# Helper Functions
# ============================================================================


@st.cache_data(ttl=300)  # 5-minute cache
def get_models_from_litellm() -> List[Dict[str, Any]]:
    """
    Fetch list of configured models from LiteLLM proxy.

    Returns:
        List of model dictionaries with name, provider, metadata

    Raises:
        Exception: if LiteLLM is unavailable
    """
    try:
        service = LiteLLMProviderService()
        models = asyncio.run(service.list_models())
        return models
    except Exception as e:
        logger.error(f"Failed to fetch models from LiteLLM: {e}")
        raise


def format_model_info(model: Dict[str, Any]) -> Dict[str, str]:
    """
    Format model data for display in table.

    Args:
        model: Raw model dict from LiteLLM

    Returns:
        Formatted dict for DataFrame
    """
    model_name = model.get("model_name", "Unknown")
    litellm_params = model.get("litellm_params", {})
    model_info = model.get("model_info", {})

    # Extract provider from litellm_params.model (e.g., "openai/gpt-4")
    underlying_model = litellm_params.get("model", "Unknown")
    provider = underlying_model.split("/")[0] if "/" in underlying_model else "Unknown"

    return {
        "Model Name": model_name,
        "Provider": provider.upper(),
        "Underlying Model": underlying_model,
        "Max Tokens": f"{model_info.get('max_tokens', 'N/A'):,}"
        if model_info.get("max_tokens")
        else "N/A",
        "Status": "✅ Active",
    }


# ============================================================================
# Main Page
# ============================================================================


def main():
    """Main Streamlit page for LLM provider management."""
    st.title("🔧 LLM Providers (via LiteLLM)")
    st.markdown(
        "Manage LLM models through the LiteLLM proxy. "
        "Models are stored in LiteLLM, not in the application database."
    )

    # Show database connection status
    show_connection_status()

    # Info box about LiteLLM
    st.info(
        "ℹ️ **New in Story 9.2:** Provider credentials are now managed by LiteLLM proxy. "
        "No API keys are stored in the application database. "
        "Learn more: [LiteLLM Proxy Documentation](https://docs.litellm.ai/docs/proxy)"
    )

    # Action buttons
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("➕ Add Model", use_container_width=True):
            add_model_dialog()

    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # Fetch and display models
    st.markdown("### Configured Models")

    try:
        models = get_models_from_litellm()

        if not models:
            st.info("No models configured yet. Click '➕ Add Model' to get started.")
            return

        # Format for display
        formatted_models = [format_model_info(m) for m in models]
        df = pd.DataFrame(formatted_models)

        # Display table
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Model Name": st.column_config.TextColumn("Model Name", width="medium"),
                "Provider": st.column_config.TextColumn("Provider", width="small"),
                "Underlying Model": st.column_config.TextColumn(
                    "Underlying Model", width="medium"
                ),
                "Max Tokens": st.column_config.TextColumn("Max Tokens", width="small"),
                "Status": st.column_config.TextColumn("Status", width="small"),
            },
        )

        # Model actions
        st.markdown("### Model Actions")

        for model in models:
            model_name = model.get("model_name", "Unknown")
            underlying = model.get("litellm_params", {}).get("model", "Unknown")

            with st.expander(f"{model_name} ({underlying})"):
                col1, col2, col3 = st.columns([2, 2, 2])

                with col1:
                    st.json(model.get("litellm_params", {}), expanded=False)
                    st.caption("LiteLLM Parameters")

                with col2:
                    st.json(model.get("model_info", {}), expanded=False)
                    st.caption("Model Metadata")

                with col3:
                    if st.button(
                        "🗑️ Delete Model",
                        key=f"delete_{model_name}",
                        use_container_width=True,
                    ):
                        delete_model_dialog(model_name)

    except Exception as e:
        st.error(
            f"Failed to load models from LiteLLM: {str(e)}\n\n"
            f"Make sure LiteLLM proxy is running at {st.secrets.get('LITELLM_URL', 'http://litellm:4000')}"
        )
        logger.error(f"Error loading models: {e}")


if __name__ == "__main__":
    main()
