"""
BYOK (Bring Your Own Key) UI Helpers - Story 8.13.

Streamlit UI components for BYOK configuration, status display, key rotation,
and platform reversion (Tasks 6-9, ACs #1-8).
API helpers are in byok_api_helpers.py to keep this file under 500 lines.
"""

import asyncio
from typing import Optional, Dict

import streamlit as st

from admin.utils.byok_api_helpers import (
    test_provider_keys,
    enable_byok,
    get_byok_status,
    rotate_byok_keys,
    disable_byok,
    enable_platform_keys,
)


# ============================================================================
# Task 6: BYOK Configuration Section (AC #1, #2, #3)
# ============================================================================


def show_byok_configuration_section(tenant_id: str, tenant: Optional[Dict] = None):
    """
    Display BYOK configuration interface with mode selection and key inputs.

    AC #1: Radio buttons - "Use platform keys" (default) vs "Use own keys (BYOK)"
    AC #2: Input fields for OpenAI and Anthropic API keys (encrypted on save)
    AC #3: "Test Keys" button validates keys before enabling BYOK

    Args:
        tenant_id: Unique tenant identifier
        tenant: Optional tenant dict with litellm_virtual_key field
    """
    st.markdown("### LLM Configuration")

    # Check if tenant has virtual key
    has_virtual_key = False
    if tenant:
        has_virtual_key = tenant.get("litellm_virtual_key") is not None

    # AC #1: Mode selection with radio buttons
    col1, col2 = st.columns(2)

    with col1:
        mode = st.radio(
            "Select LLM Key Management Mode",
            options=["Use platform keys", "Use own keys (BYOK)"],
            key=f"llm_mode_{tenant_id}",
            help="Platform keys: Centralized billing. BYOK: Use your own API keys.",
        )

    with col2:
        if mode == "Use platform keys":
            if has_virtual_key:
                st.info("✅ Using platform-managed API keys for all LLM calls")
            else:
                st.warning("⚠️ Platform virtual key not configured")
        else:
            st.warning("🔑 You will provide your own OpenAI/Anthropic API keys")

    # Show "Initialize Platform Keys" button if using platform mode but no virtual key
    if mode == "Use platform keys" and not has_virtual_key:
        st.markdown("#### Initialize Platform Keys")
        st.markdown(
            "Create a platform virtual key to enable LLM functionality for this tenant."
        )

        if st.button(
            "🔑 Initialize Platform Keys",
            key=f"init_platform_{tenant_id}",
            type="primary",
        ):
            with st.spinner("Initializing platform keys..."):
                try:
                    result = asyncio.run(enable_platform_keys(tenant_id))
                    st.success("✅ Platform keys initialized successfully!")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to initialize platform keys: {str(e)}")

    # AC #2: Show input fields only in BYOK mode
    if mode == "Use own keys (BYOK)":
        st.markdown("#### Configure Your API Keys")
        st.markdown("Provide your OpenAI and/or Anthropic API keys. Keys are encrypted at rest.")

        col1, col2 = st.columns(2)

        with col1:
            openai_key = st.text_input(
                "OpenAI API Key (sk-...)",
                type="password",
                key=f"openai_key_{tenant_id}",
                help="Optional. Leave blank if not using OpenAI models.",
            )

        with col2:
            anthropic_key = st.text_input(
                "Anthropic API Key (sk-ant-...)",
                type="password",
                key=f"anthropic_key_{tenant_id}",
                help="Optional. Leave blank if not using Anthropic/Claude models.",
            )

        # Validation feedback
        if openai_key and not openai_key.startswith("sk-"):
            st.error("❌ OpenAI key must start with 'sk-'")
            openai_key = None

        if anthropic_key and not anthropic_key.startswith("sk-ant-"):
            st.error("❌ Anthropic key must start with 'sk-ant-'")
            anthropic_key = None

        if not openai_key and not anthropic_key:
            st.error("❌ Provide at least one API key (OpenAI or Anthropic)")
            return

        # AC #3: Test Keys button
        st.markdown("#### Validate Keys Before Saving")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🧪 Test Keys", key=f"test_keys_{tenant_id}"):
                with st.spinner("Testing keys with providers..."):
                    try:
                        result = asyncio.run(
                            test_provider_keys(tenant_id, openai_key, anthropic_key)
                        )

                        # Display validation results
                        st.markdown("#### Validation Results")

                        col_openai, col_anthropic = st.columns(2)

                        with col_openai:
                            openai_result = result.get("openai", {})
                            if openai_result.get("valid"):
                                st.success(
                                    f"✅ OpenAI Valid\n\n{len(openai_result.get('models', []))} models available"
                                )
                                with st.expander("View Available Models"):
                                    models = openai_result.get("models", [])
                                    st.write(", ".join(models[:5]))
                                    if len(models) > 5:
                                        st.caption(f"... and {len(models) - 5} more")
                            else:
                                st.error(
                                    f"❌ OpenAI Invalid\n\n{openai_result.get('error', 'Unknown error')}"
                                )

                        with col_anthropic:
                            anthropic_result = result.get("anthropic", {})
                            if anthropic_result.get("valid"):
                                st.success(
                                    f"✅ Anthropic Valid\n\n{len(anthropic_result.get('models', []))} models available"
                                )
                                with st.expander("View Available Models"):
                                    models = anthropic_result.get("models", [])
                                    st.write(", ".join(models[:5]))
                                    if len(models) > 5:
                                        st.caption(f"... and {len(models) - 5} more")
                            else:
                                st.error(
                                    f"❌ Anthropic Invalid\n\n{anthropic_result.get('error', 'Unknown error')}"
                                )

                        # Enable save button only if tests pass
                        st.session_state[f"keys_validated_{tenant_id}"] = openai_result.get(
                            "valid", False
                        ) or anthropic_result.get("valid", False)

                    except Exception as e:
                        st.error(f"🔴 Key validation failed: {str(e)}")

        with col2:
            if st.session_state.get(f"keys_validated_{tenant_id}", False):
                if st.button(
                    "💾 Save BYOK Configuration",
                    key=f"save_byok_{tenant_id}",
                    type="primary",
                ):
                    with st.spinner("Enabling BYOK..."):
                        try:
                            result = asyncio.run(enable_byok(tenant_id, openai_key, anthropic_key))
                            st.success("✅ BYOK enabled successfully!")
                            st.balloons()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to enable BYOK: {str(e)}")

        with col3:
            if st.button("❌ Cancel", key=f"cancel_byok_{tenant_id}"):
                st.info("Configuration cancelled")


# ============================================================================
# Task 7: BYOK Status Display (AC #6)
# ============================================================================


def show_byok_status_display(tenant_id: str):
    """
    Display BYOK status and configuration information.

    AC #6: Show BYOK enabled/disabled status, providers configured, cost tracking mode

    Args:
        tenant_id: Unique tenant identifier
    """
    try:
        status = asyncio.run(get_byok_status(tenant_id))
    except Exception as e:
        st.error(f"Failed to load BYOK status: {str(e)}")
        return

    # Display status overview
    col1, col2, col3 = st.columns(3)

    with col1:
        if status.get("byok_enabled"):
            st.metric(
                "BYOK Status",
                "Enabled",
                delta="🔑 Using own keys",
                delta_color="off",
            )
        else:
            st.metric(
                "BYOK Status",
                "Disabled",
                delta="📦 Using platform keys",
                delta_color="off",
            )

    with col2:
        providers = status.get("providers_configured", [])
        if providers:
            st.metric(
                "Providers Configured",
                len(providers),
                delta=", ".join(providers),
                delta_color="off",
            )
        else:
            st.metric("Providers Configured", "0", delta="None", delta_color="off")

    with col3:
        tracking_mode = status.get("cost_tracking_mode", "platform")
        if tracking_mode == "byok":
            st.metric(
                "Cost Tracking",
                "N/A",
                delta="🔑 Using own keys",
                delta_color="off",
            )
        else:
            st.metric(
                "Cost Tracking",
                "Active",
                delta="📊 Platform tracked",
                delta_color="off",
            )

    # Display detailed status
    if status.get("byok_enabled"):
        st.markdown("#### BYOK Configuration Details")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Enabled Providers")
            for provider in status.get("providers_configured", []):
                st.caption(f"✅ {provider.capitalize()}")

        with col2:
            if status.get("enabled_at"):
                st.subheader("Configuration Date")
                st.caption(status.get("enabled_at"))


# ============================================================================
# Task 8: Key Rotation Interface (AC #7)
# ============================================================================


def show_key_rotation_section(tenant_id: str):
    """
    Display key rotation interface with modal form and confirmation.

    AC #7: Rotation form, new key inputs, confirmation dialog, audit logging

    Args:
        tenant_id: Unique tenant identifier
    """
    # Check if BYOK is enabled first
    try:
        status = asyncio.run(get_byok_status(tenant_id))
        if not status.get("byok_enabled"):
            st.info("ℹ️ Key rotation only available when BYOK is enabled")
            return
    except Exception:
        st.warning("Unable to check BYOK status")
        return

    st.markdown("### Rotate API Keys")
    st.markdown("Update your OpenAI and/or Anthropic API keys without disabling BYOK.")

    col1, col2 = st.columns(2)

    with col1:
        new_openai_key = st.text_input(
            "New OpenAI API Key (optional)",
            type="password",
            key=f"new_openai_key_{tenant_id}",
            help="Leave blank to keep current OpenAI key",
        )

        if new_openai_key and not new_openai_key.startswith("sk-"):
            st.error("❌ OpenAI key must start with 'sk-'")
            new_openai_key = None

    with col2:
        new_anthropic_key = st.text_input(
            "New Anthropic API Key (optional)",
            type="password",
            key=f"new_anthropic_key_{tenant_id}",
            help="Leave blank to keep current Anthropic key",
        )

        if new_anthropic_key and not new_anthropic_key.startswith("sk-ant-"):
            st.error("❌ Anthropic key must start with 'sk-ant-'")
            new_anthropic_key = None

    if not new_openai_key and not new_anthropic_key:
        st.warning("⚠️ Provide at least one new key to rotate")
        return

    # Test new keys before rotation
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🧪 Test New Keys", key=f"test_rotate_{tenant_id}"):
            with st.spinner("Testing new keys..."):
                try:
                    result = asyncio.run(
                        test_provider_keys(tenant_id, new_openai_key, new_anthropic_key)
                    )

                    openai_valid = result.get("openai", {}).get("valid", False)
                    anthropic_valid = result.get("anthropic", {}).get("valid", False)

                    if openai_valid or anthropic_valid:
                        st.success("✅ New keys are valid")
                        st.session_state[f"rotation_validated_{tenant_id}"] = True
                    else:
                        st.error("❌ One or more keys failed validation")

                except Exception as e:
                    st.error(f"Key validation failed: {str(e)}")

    with col2:
        if st.session_state.get(f"rotation_validated_{tenant_id}", False):
            if st.button(
                "♻️ Confirm Rotation",
                key=f"confirm_rotate_{tenant_id}",
                type="primary",
            ):
                # Confirmation dialog
                st.warning("⚠️ Key rotation will immediately switch to new keys")
                if st.checkbox(
                    "I understand this will immediately use new keys",
                    key=f"rotation_confirm_{tenant_id}",
                ):
                    with st.spinner("Rotating keys..."):
                        try:
                            result = asyncio.run(
                                rotate_byok_keys(tenant_id, new_openai_key, new_anthropic_key)
                            )
                            st.success("✅ Keys rotated successfully!")
                            st.balloons()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Key rotation failed: {str(e)}")

    with col3:
        if st.button("❌ Cancel", key=f"cancel_rotate_{tenant_id}"):
            st.session_state[f"rotation_validated_{tenant_id}"] = False
            st.info("Rotation cancelled")


# ============================================================================
# Task 9: Revert to Platform Keys (AC #8)
# ============================================================================


def show_revert_to_platform_section(tenant_id: str):
    """
    Display revert to platform keys interface with confirmation.

    AC #8: Confirmation dialog, warning message, cleanup of BYOK configuration

    Args:
        tenant_id: Unique tenant identifier
    """
    # Check if BYOK is enabled first
    try:
        status = asyncio.run(get_byok_status(tenant_id))
        if not status.get("byok_enabled"):
            st.info("ℹ️ BYOK is not currently enabled for this tenant")
            return
    except Exception:
        st.warning("Unable to check BYOK status")
        return

    st.markdown("### Revert to Platform Keys")
    st.markdown(
        "Disable BYOK and switch back to platform-managed API keys. "
        "This will clear your stored API keys."
    )

    # Warning box
    with st.container(border=True):
        st.warning(
            "⚠️ **Important:** Reverting to platform keys will:\n"
            "- Disable BYOK mode\n"
            "- Delete your stored API keys from our system\n"
            "- Switch all agents to platform-managed keys\n"
            "- Resume cost tracking in platform dashboard\n\n"
            "This action cannot be undone easily."
        )

    # Confirmation checkbox
    col1, col2 = st.columns(2)

    with col1:
        confirmed = st.checkbox(
            "I understand this will disable BYOK and delete my stored keys",
            key=f"revert_confirm_{tenant_id}",
        )

    with col2:
        if confirmed:
            if st.button(
                "🔄 Revert to Platform Keys",
                key=f"confirm_revert_{tenant_id}",
                type="secondary",
            ):
                with st.spinner("Reverting to platform keys..."):
                    try:
                        result = asyncio.run(disable_byok(tenant_id))
                        st.success("✅ Successfully reverted to platform keys!")
                        st.info(
                            "All agents now using platform-managed API keys. "
                            "Cost tracking resumed."
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"Reversion failed: {str(e)}")
        else:
            st.button(
                "🔄 Revert to Platform Keys",
                key=f"revert_disabled_{tenant_id}",
                disabled=True,
                help="Check the confirmation box to enable",
            )
