"""
Tenant Management UI Helpers for Dialog Forms.

Extracts dialog functions and complex form rendering to reduce 2_Tenants.py file size.
"""

import os
import secrets

import streamlit as st
from admin.utils.db_helper import get_db_session
from admin.utils.servicedesk_validator import validate_servicedesk_connection
from admin.utils.jira_validator import validate_jira_connection
from admin.utils.tenant_helper import (
    create_tenant,
    decrypt_field,
    get_tenant_by_id,
    mask_sensitive_field,
    soft_delete_tenant,
    update_tenant,
    validate_tenant_form,
)
from admin.utils.byok_helpers import (
    show_byok_configuration_section,
    show_byok_status_display,
    show_key_rotation_section,
    show_revert_to_platform_section,
)


def get_available_plugins():
    """Fetch available plugins from API with fallback."""
    import httpx

    API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")
    available_plugins = []
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{API_BASE_URL}/api/v1/plugins/")
            if resp.status_code == 200:
                plugins_data = resp.json()
                available_plugins = [
                    (p["tool_type"], p["name"]) for p in plugins_data.get("plugins", [])
                ]
    except:
        pass

    # Fallback if plugin API not available
    if not available_plugins:
        available_plugins = [
            ("servicedesk_plus", "ServiceDesk Plus"),
            ("jira", "Jira Service Management"),
        ]

    return available_plugins


def show_enhancement_prefs_form(default_prefs=None) -> dict:
    """Render enhancement preferences form section."""
    st.markdown("**Enhancement Features**")
    feature_list = [
        "Ticket History Search",
        "Documentation Search",
        "IP Lookup",
        "Monitoring Data",
    ]

    if default_prefs:
        default_selected = [
            f for f in feature_list
            if default_prefs.get(f.lower().replace(" ", "_"))
        ]
    else:
        default_selected = ["Ticket History Search", "Documentation Search"]

    prefs = st.multiselect(
        "Select features to enable:",
        feature_list,
        default=default_selected,
    )

    return {
        "ticket_history": "Ticket History Search" in prefs,
        "documentation": "Documentation Search" in prefs,
        "ip_lookup": "IP Lookup" in prefs,
        "monitoring": "Monitoring Data" in prefs,
    }


def show_budget_config_form(tenant=None) -> dict:
    """Render budget configuration form section."""
    st.markdown("**💰 Budget Configuration**")
    col1_budget, col2_budget = st.columns(2)

    with col1_budget:
        max_budget = st.number_input(
            "Max Monthly Budget ($)",
            min_value=0.0,
            max_value=100000.0,
            value=float(tenant.max_budget) if tenant and tenant.max_budget else 500.0,
            step=50.0,
            help="Maximum LLM spend allowed per month (default: $500)",
        )

        alert_threshold = st.slider(
            "Alert Threshold (%)",
            min_value=50,
            max_value=100,
            value=tenant.alert_threshold if tenant and tenant.alert_threshold else 80,
            help="Send notification when budget reaches this % (default: 80%)",
        )

    with col2_budget:
        grace_threshold = st.slider(
            "Grace Threshold (%)",
            min_value=100,
            max_value=150,
            value=tenant.grace_threshold if tenant and tenant.grace_threshold else 110,
            help="Block requests when budget exceeds this % (default: 110%)",
        )

        budget_options = ["30d", "60d", "90d"]
        default_index = 0
        if tenant and tenant.budget_duration in budget_options:
            default_index = budget_options.index(tenant.budget_duration)

        budget_duration = st.selectbox(
            "Budget Reset Period",
            options=budget_options,
            index=default_index,
            help="How often budget resets (default: 30 days)",
        )

    return {
        "max_budget": max_budget,
        "alert_threshold": alert_threshold,
        "grace_threshold": grace_threshold,
        "budget_duration": budget_duration,
    }


@st.dialog("➕ Add New Tenant", width="large")
def add_tenant_dialog():
    """Modal dialog for adding a new tenant."""
    st.markdown("Configure a new tenant for the AI Agents platform")

    with st.form("add_tenant_form"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Tenant Name *", placeholder="Acme Corporation")
            tenant_id = st.text_input(
                "Tenant ID *",
                placeholder="acme-corp",
                help="Alphanumeric and hyphens only",
            )

        with col2:
            available_plugins = get_available_plugins()
            tool_type = st.selectbox(
                "Tool Type *",
                options=[p[0] for p in available_plugins],
                format_func=lambda x: next((p[1] for p in available_plugins if p[0] == x), x),
                help="Select ticketing tool plugin",
            )
            servicedesk_url = st.text_input(
                "ServiceDesk URL *", placeholder="https://acme.servicedesk.com"
            )

        api_key = st.text_input("API Key *", type="password", placeholder="Enter API key")
        
        # Development mode: Skip connection validation
        skip_validation = st.checkbox(
            "⚠️ Skip connection validation (development only)",
            help="Enable this to create tenant without validating ServiceDesk connection. Use only for testing/development."
        )
        
        enhancement_preferences = show_enhancement_prefs_form()
        budget_config = show_budget_config_form()

        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            test_conn = st.form_submit_button("🔍 Test Connection", use_container_width=True)
        with col2:
            submit = st.form_submit_button("✅ Create Tenant", use_container_width=True)
        with col3:
            cancel = st.form_submit_button("❌ Cancel", use_container_width=True)

    if cancel:
        st.rerun()

    if test_conn:
        if not servicedesk_url or not api_key:
            st.error("❌ URL and API Key required for connection test")
        else:
            with st.spinner("Testing connection..."):
                # Use appropriate validator based on tool type
                if tool_type == "jira":
                    success, message = validate_jira_connection(servicedesk_url, api_key)
                else:
                    success, message = validate_servicedesk_connection(servicedesk_url, api_key)

                if success:
                    st.success(message)
                else:
                    st.error(message)

    if submit:
        form_data = {
            "name": name,
            "tenant_id": tenant_id,
            "tool_type": tool_type,
            "servicedesk_url": servicedesk_url,
            "api_key": api_key,
            "enhancement_preferences": enhancement_preferences,
            **budget_config,
        }

        is_valid, errors = validate_tenant_form(form_data)
        if not is_valid:
            for error in errors:
                st.error(error)
        else:
            # Skip connection validation if checkbox is enabled
            if skip_validation:
                st.warning("⚠️ Connection validation skipped (development mode)")
                conn_success = True
            else:
                with st.spinner("Testing connection..."):
                    # Use appropriate validator based on tool type
                    if tool_type == "jira":
                        conn_success, conn_message = validate_jira_connection(
                            servicedesk_url, api_key
                        )
                    else:
                        conn_success, conn_message = validate_servicedesk_connection(
                            servicedesk_url, api_key
                        )

                if not conn_success:
                    st.error(f"{conn_message}\n\n⚠️ Please fix connection issues before saving.")

            if conn_success:
                tenant = create_tenant(form_data)
                if tenant:
                    ingress_host = os.getenv("INGRESS_HOST", "localhost:8000")
                    webhook_url = (
                        f"https://{ingress_host}/webhook/servicedesk?tenant_id={tenant_id}"
                    )

                    st.success(f"✅ Tenant '{name}' created successfully!")
                    st.info(
                        f"**Webhook URL:** (copy to ServiceDesk Plus config)\n\n`{webhook_url}`"
                    )
                    st.code(webhook_url, language="text")

                    st.cache_data.clear()
                    if st.button("✅ Done"):
                        st.rerun()
                else:
                    st.error("❌ Failed to create tenant. Check logs for details.")


@st.dialog("✏️ Edit Tenant", width="large")
def edit_tenant_dialog(tenant_id: str):
    """Modal dialog for editing an existing tenant."""
    tenant = get_tenant_by_id(tenant_id)
    if not tenant:
        st.error(f"Tenant {tenant_id} not found")
        return

    st.markdown(f"Editing tenant: **{tenant.name}**")

    with st.form("edit_tenant_form"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Tenant Name *", value=tenant.name)
            servicedesk_url = st.text_input("ServiceDesk URL *", value=tenant.servicedesk_url)

        with col2:
            masked_key = mask_sensitive_field(decrypt_field(tenant.servicedesk_api_key_encrypted))
            st.text_input("Current API Key (masked)", value=masked_key, disabled=True)
            update_api_key = st.checkbox("Update API Key")

            masked_secret = mask_sensitive_field(
                decrypt_field(tenant.webhook_signing_secret_encrypted)
            )
            st.text_input("Current Webhook Secret (masked)", value=masked_secret, disabled=True)
            update_webhook_secret = st.checkbox("Update Webhook Secret")

        new_api_key = None
        if update_api_key:
            new_api_key = st.text_input("New API Key", type="password")

        new_webhook_secret = None
        if update_webhook_secret:
            new_webhook_secret = secrets.token_urlsafe(32)
            st.info(f"🔑 New webhook secret will be generated: `{new_webhook_secret[:8]}...`")

        enhancement_preferences = show_enhancement_prefs_form(tenant.enhancement_preferences)
        budget_config = show_budget_config_form(tenant)

        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("✅ Save Changes", use_container_width=True)
        with col2:
            cancel = st.form_submit_button("❌ Cancel", use_container_width=True)

    if cancel:
        st.rerun()

    if submit:
        updates = {
            "name": name,
            "servicedesk_url": servicedesk_url,
            "enhancement_preferences": enhancement_preferences,
            **budget_config,
        }

        if update_api_key and new_api_key:
            updates["api_key"] = new_api_key

        if update_webhook_secret and new_webhook_secret:
            updates["webhook_secret"] = new_webhook_secret

        form_data = {
            "name": name,
            "tenant_id": tenant_id,
            "servicedesk_url": servicedesk_url,
            "api_key": (
                new_api_key if update_api_key else "dummy"
            ),
        }
        is_valid, errors = validate_tenant_form(
            form_data, skip_duplicate_check=True
        )

        if not is_valid:
            for error in errors:
                if "API Key" not in error or update_api_key:
                    st.error(error)
        else:
            success = update_tenant(tenant_id, updates)
            if success:
                st.success(f"✅ Tenant '{name}' updated successfully!")
                st.cache_data.clear()
                if st.button("✅ Done"):
                    st.rerun()
            else:
                st.error("❌ Failed to update tenant. Check logs for details.")


@st.dialog("🗑️ Delete Tenant")
def delete_tenant_dialog(tenant_id: str):
    """Modal dialog for confirming tenant deletion."""
    tenant = get_tenant_by_id(tenant_id)
    if not tenant:
        st.error(f"Tenant {tenant_id} not found")
        return

    st.warning(
        f"**Are you sure you want to delete tenant '{tenant.name}'?**\n\n"
        f"This will mark the tenant as inactive (soft delete). Enhancement history will be preserved."
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Confirm Delete", use_container_width=True):
            success = soft_delete_tenant(tenant_id)
            if success:
                st.success(f"✅ Tenant '{tenant.name}' has been deleted (marked inactive)")
                st.cache_data.clear()
                if st.button("✅ Done"):
                    st.rerun()
            else:
                st.error("❌ Failed to delete tenant. Check logs for details.")

    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            st.rerun()


def show_tenant_byok_sections(tenant):
    """Render all BYOK-related sections for a tenant."""
    # Convert tenant object to dict for BYOK helpers
    tenant_dict = {
        "tenant_id": tenant.tenant_id,
        "litellm_virtual_key": tenant.litellm_virtual_key,
    }

    # BYOK Configuration (Story 8.13 Task 6)
    with st.expander("🔑 BYOK Configuration", expanded=False):
        show_byok_configuration_section(tenant.tenant_id, tenant=tenant_dict)

    # BYOK Status Display (Story 8.13 Task 7)
    with st.expander("📊 BYOK Status", expanded=False):
        show_byok_status_display(tenant.tenant_id)

    # Key Rotation Interface (Story 8.13 Task 8)
    with st.expander("♻️ Rotate API Keys", expanded=False):
        show_key_rotation_section(tenant.tenant_id)

    # Revert to Platform Keys (Story 8.13 Task 9)
    with st.expander("⬅️ Revert to Platform Keys", expanded=False):
        show_revert_to_platform_section(tenant.tenant_id)


@st.cache_data(ttl=60)
def fetch_tenant_spend(tenant_id: str):
    """Fetch real-time spend data from API endpoint with 1-minute cache."""
    import httpx

    API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{API_BASE_URL}/api/tenants/{tenant_id}/spend")
            if resp.status_code == 200:
                return resp.json()
            else:
                return None
    except Exception as e:
        st.error(f"Failed to fetch spend data: {str(e)}")
        return None


def show_tenant_budget_dashboard(tenant):
    """Render enhanced budget dashboard for a tenant with real-time spend data."""
    with st.expander("💰 Budget Dashboard", expanded=True):
        # Budget Configuration
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Max Budget", f"${tenant.max_budget:,.2f}")
        with col2:
            st.metric("Alert Threshold", f"{tenant.alert_threshold}%")
        with col3:
            st.metric("Grace Threshold", f"{tenant.grace_threshold}%")

        st.markdown(f"**Reset Period:** {tenant.budget_duration}")

        # Fetch real-time spend data from LiteLLM
        spend_data = fetch_tenant_spend(tenant.tenant_id)

        if spend_data is None:
            st.warning(
                "⚠️ **Budget tracking not configured**\n\n"
                "This tenant doesn't have a LiteLLM virtual key configured. "
                "Enable BYOK or platform keys to see spend data."
            )
            return

        # Extract spend information
        current_spend = spend_data.get("current_spend", 0.0)
        max_budget = spend_data.get("max_budget", tenant.max_budget)
        utilization_pct = spend_data.get("utilization_pct", 0.0)
        models_breakdown = spend_data.get("models_breakdown", [])
        last_updated = spend_data.get("last_updated", "Unknown")
        budget_reset_at = spend_data.get("budget_reset_at")

        # Determine color based on utilization
        if utilization_pct < 80:
            color = "🟢"
            status = "Within budget"
        elif utilization_pct < 100:
            color = "🟡"
            status = "Approaching limit"
        elif utilization_pct < 110:
            color = "🟠"
            status = "Over budget"
        else:
            color = "🔴"
            status = "Grace exceeded"

        # Display main spend metrics
        st.markdown(
            f"**Current Spend:** ${current_spend:,.2f} / ${max_budget:,.2f} ({utilization_pct:.1f}%) {color}"
        )

        # Progress bar
        progress_value = min(utilization_pct / 100, 1.5)  # Allow 150% for visualization
        st.progress(progress_value)

        # Alert indicators
        if utilization_pct >= 110:
            st.error(f"🚨 **Grace Period Exceeded** ({utilization_pct:.1f}%)")
        elif utilization_pct >= 100:
            st.error(f"🔴 **Budget Limit Exceeded** ({utilization_pct:.1f}%)")
        elif utilization_pct >= 80:
            st.warning(f"⚠️ **Approaching Budget Limit** ({utilization_pct:.1f}%)")

        # Model spend breakdown
        if models_breakdown:
            st.markdown("### Model Spend Breakdown")
            model_data = {
                "Model": [m["model"] for m in models_breakdown],
                "Spend": [f"${m['spend']:,.2f}" for m in models_breakdown],
                "Share": [f"{m['percentage']:.1f}%" for m in models_breakdown],
            }
            st.dataframe(model_data, hide_index=True, use_container_width=True)

        # Budget reset information
        if budget_reset_at:
            from datetime import datetime

            try:
                reset_date = datetime.fromisoformat(budget_reset_at.replace("Z", "+00:00"))
                from datetime import timezone

                days_remaining = (reset_date - datetime.now(timezone.utc)).days
                st.markdown(f"**Days Until Reset:** {max(0, days_remaining)} days")
            except:
                st.caption(f"Budget resets: {budget_reset_at}")
        else:
            st.caption("Budget reset date not set")

        # Last updated timestamp
        st.caption(f"Last updated: {last_updated}")

        # Refresh button
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🔄 Refresh", key=f"refresh_{tenant.tenant_id}"):
                st.cache_data.clear()
                st.rerun()
