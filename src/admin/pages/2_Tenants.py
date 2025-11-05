"""
Tenant Management Page - Full CRUD Interface.

Implements comprehensive tenant management for AI Agents admin UI:
- View all tenants with search/filter
- Add new tenant with validation and connection testing
- Edit existing tenant (masked sensitive fields)
- Delete tenant with confirmation (soft delete)
- Display webhook URL after creation

Story: 6.3 - Create Tenant Management Interface
"""

import os
import secrets

import pandas as pd
import streamlit as st
from admin.utils.db_helper import get_db_session, show_connection_status
from admin.utils.servicedesk_validator import validate_servicedesk_connection
from admin.utils.tenant_helper import (
    create_tenant,
    decrypt_field,
    get_all_tenants,
    get_tenant_by_id,
    mask_sensitive_field,
    soft_delete_tenant,
    update_tenant,
    validate_tenant_form,
)
from database.models import TenantConfig


# ============================================================================
# Dialog Functions for Add/Edit/Delete Operations
# ============================================================================


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
            # Story 7.8: Plugin assignment - Fetch available plugins
            import httpx

            API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
            available_plugins = []
            try:
                with httpx.Client(timeout=5.0) as client:
                    resp = client.get(f"{API_BASE_URL}/api/v1/plugins/")
                    if resp.status_code == 200:
                        plugins_data = resp.json()
                        available_plugins = [(p["tool_type"], p["name"]) for p in plugins_data.get("plugins", [])]
            except:
                # Fallback if plugin API not available
                available_plugins = [("servicedesk_plus", "ServiceDesk Plus"), ("jira", "Jira Service Management")]

            tool_type = st.selectbox(
                "Tool Type *",
                options=[p[0] for p in available_plugins],
                format_func=lambda x: next((p[1] for p in available_plugins if p[0] == x), x),
                help="Select ticketing tool plugin"
            )
            servicedesk_url = st.text_input(
                "ServiceDesk URL *", placeholder="https://acme.servicedesk.com"
            )

        api_key = st.text_input("API Key *", type="password", placeholder="Enter API key")

        # Enhancement preferences
        st.markdown("**Enhancement Features**")
        prefs = st.multiselect(
            "Select features to enable:",
            [
                "Ticket History Search",
                "Documentation Search",
                "IP Lookup",
                "Monitoring Data",
            ],
            default=["Ticket History Search", "Documentation Search"],
        )

        enhancement_preferences = {
            "ticket_history": "Ticket History Search" in prefs,
            "documentation": "Documentation Search" in prefs,
            "ip_lookup": "IP Lookup" in prefs,
            "monitoring": "Monitoring Data" in prefs,
        }

        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            test_conn = st.form_submit_button("🔍 Test Connection", use_container_width=True)
        with col2:
            submit = st.form_submit_button("✅ Create Tenant", use_container_width=True)
        with col3:
            cancel = st.form_submit_button("❌ Cancel", use_container_width=True)

    if cancel:
        st.rerun()

    # Test connection (separate from submit)
    if test_conn:
        if not servicedesk_url or not api_key:
            st.error("❌ ServiceDesk URL and API Key required for connection test")
        else:
            with st.spinner("Testing connection..."):
                success, message = validate_servicedesk_connection(servicedesk_url, api_key)
                if success:
                    st.success(message)
                else:
                    st.error(message)

    # Create tenant
    if submit:
        form_data = {
            "name": name,
            "tenant_id": tenant_id,
            "tool_type": tool_type,  # Story 7.8: Include tool_type for plugin assignment
            "servicedesk_url": servicedesk_url,
            "api_key": api_key,
            "enhancement_preferences": enhancement_preferences,
        }

        # Validate form
        is_valid, errors = validate_tenant_form(form_data)
        if not is_valid:
            for error in errors:
                st.error(error)
        else:
            # Test connection before saving
            with st.spinner("Testing connection..."):
                conn_success, conn_message = test_servicedesk_connection(
                    servicedesk_url, api_key
                )

            if not conn_success:
                st.error(f"{conn_message}\n\n⚠️ Please fix connection issues before saving.")
            else:
                # Create tenant
                tenant = create_tenant(form_data)
                if tenant:
                    # Generate webhook URL
                    ingress_host = os.getenv("INGRESS_HOST", "localhost:8000")
                    webhook_url = (
                        f"https://{ingress_host}/webhook/servicedesk?tenant_id={tenant_id}"
                    )

                    st.success(f"✅ Tenant '{name}' created successfully!")
                    st.info(f"**Webhook URL:** (copy to ServiceDesk Plus config)\n\n`{webhook_url}`")
                    st.code(webhook_url, language="text")

                    # Clear cache and close dialog
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
            # Show masked API key
            masked_key = mask_sensitive_field(decrypt_field(tenant.servicedesk_api_key_encrypted))
            st.text_input("Current API Key (masked)", value=masked_key, disabled=True)
            update_api_key = st.checkbox("Update API Key")

            # Show masked webhook secret
            masked_secret = mask_sensitive_field(decrypt_field(tenant.webhook_signing_secret_encrypted))
            st.text_input("Current Webhook Secret (masked)", value=masked_secret, disabled=True)
            update_webhook_secret = st.checkbox("Update Webhook Secret")

        new_api_key = None
        if update_api_key:
            new_api_key = st.text_input("New API Key", type="password")

        new_webhook_secret = None
        if update_webhook_secret:
            # Auto-generate new webhook secret
            new_webhook_secret = secrets.token_urlsafe(32)
            st.info(f"🔑 New webhook secret will be generated: `{new_webhook_secret[:8]}...`")

        # Enhancement preferences
        st.markdown("**Enhancement Features**")
        prefs = tenant.enhancement_preferences
        selected_prefs = st.multiselect(
            "Select features to enable:",
            [
                "Ticket History Search",
                "Documentation Search",
                "IP Lookup",
                "Monitoring Data",
            ],
            default=[
                p
                for p in [
                    "Ticket History Search" if prefs.get("ticket_history") else None,
                    "Documentation Search" if prefs.get("documentation") else None,
                    "IP Lookup" if prefs.get("ip_lookup") else None,
                    "Monitoring Data" if prefs.get("monitoring") else None,
                ]
                if p
            ],
        )

        enhancement_preferences = {
            "ticket_history": "Ticket History Search" in selected_prefs,
            "documentation": "Documentation Search" in selected_prefs,
            "ip_lookup": "IP Lookup" in selected_prefs,
            "monitoring": "Monitoring Data" in selected_prefs,
        }

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
        }

        if update_api_key and new_api_key:
            updates["api_key"] = new_api_key

        if update_webhook_secret and new_webhook_secret:
            updates["webhook_secret"] = new_webhook_secret

        # Validate
        form_data = {
            "name": name,
            "tenant_id": tenant_id,
            "servicedesk_url": servicedesk_url,
            "api_key": new_api_key if update_api_key else "dummy",  # Skip api_key validation if not updating
        }
        is_valid, errors = validate_tenant_form(
            form_data, skip_duplicate_check=True
        )  # Skip duplicate check for edit

        if not is_valid:
            for error in errors:
                if "API Key" not in error or update_api_key:  # Only show api_key error if updating
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


# ============================================================================
# Main Page Function
# ============================================================================


@st.cache_data(ttl=60)
def load_tenants(include_inactive: bool):
    """Load tenants with caching."""
    return get_all_tenants(include_inactive=include_inactive)


def show() -> None:
    """Render the Tenant Management page with full CRUD operations."""
    st.set_page_config(
        page_title="Tenants - AI Agents Admin",
        page_icon="🏢",
        layout="wide",
    )

    st.title("🏢 Tenant Management")
    st.markdown("---")

    # Database connection check
    with st.sidebar:
        st.subheader("Connection Status")
        show_connection_status()

    # Filter controls
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        search_term = st.text_input("🔍 Search tenants", placeholder="Search by name or ID...")
    with col2:
        status_filter = st.selectbox("Filter by status", ["Active", "Inactive", "All"])
    with col3:
        if st.button("➕ Add Tenant", use_container_width=True):
            add_tenant_dialog()

    # Load tenants
    include_inactive = status_filter in ["Inactive", "All"]
    tenants = load_tenants(include_inactive)

    # Apply search filter
    if search_term:
        tenants = [
            t
            for t in tenants
            if search_term.lower() in t.name.lower() or search_term.lower() in t.tenant_id.lower()
        ]

    # Apply status filter
    if status_filter == "Active":
        tenants = [t for t in tenants if t.is_active]
    elif status_filter == "Inactive":
        tenants = [t for t in tenants if not t.is_active]

    # Display tenants
    st.subheader(f"📋 Tenants ({len(tenants)} found)")

    if not tenants:
        st.info("No tenants found. Click 'Add Tenant' to create your first tenant configuration.")
    else:
        # Create dataframe for display
        tenant_data = []
        for t in tenants:
            # Story 7.8: Add plugin assignment column
            plugin_name = "ServiceDesk Plus" if t.tool_type == "servicedesk_plus" else t.tool_type.replace("_", " ").title() if t.tool_type else "Not assigned"
            tenant_data.append(
                {
                    "Name": t.name,
                    "Tenant ID": t.tenant_id,
                    "Assigned Plugin": plugin_name,
                    "ServiceDesk URL": t.servicedesk_url,
                    "Status": "✅ Active" if t.is_active else "❌ Inactive",
                    "Created": t.created_at.strftime("%Y-%m-%d"),
                }
            )

        df = pd.DataFrame(tenant_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Tenant detail view
        st.markdown("### Tenant Details & Actions")
        selected_tenant = st.selectbox(
            "Select tenant to view/manage:",
            options=[t.tenant_id for t in tenants],
            format_func=lambda tid: next(t.name for t in tenants if t.tenant_id == tid),
        )

        if selected_tenant:
            tenant = next(t for t in tenants if t.tenant_id == selected_tenant)

            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown(f"**Name:** {tenant.name}")
                st.markdown(f"**Tenant ID:** `{tenant.tenant_id}`")
                # Story 7.8: Display assigned plugin
                plugin_name = "ServiceDesk Plus" if tenant.tool_type == "servicedesk_plus" else tenant.tool_type.replace("_", " ").title() if tenant.tool_type else "Not assigned"
                st.markdown(f"**Assigned Plugin:** {plugin_name}")
                st.markdown(f"**ServiceDesk URL:** {tenant.servicedesk_url}")
                st.markdown(f"**Status:** {'✅ Active' if tenant.is_active else '❌ Inactive'}")
                st.markdown(f"**Created:** {tenant.created_at}")
                st.markdown(f"**Updated:** {tenant.updated_at}")

                with st.expander("Enhancement Preferences"):
                    st.json(tenant.enhancement_preferences)

            with col2:
                st.markdown("**Actions:**")
                if st.button("✏️ Edit Tenant", key=f"edit_{tenant.tenant_id}", use_container_width=True):
                    edit_tenant_dialog(tenant.tenant_id)

                if tenant.is_active:
                    if st.button(
                        "🗑️ Delete Tenant",
                        key=f"delete_{tenant.tenant_id}",
                        use_container_width=True,
                    ):
                        delete_tenant_dialog(tenant.tenant_id)


if __name__ == "__main__":
    show()
