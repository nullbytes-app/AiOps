"""
Tenant Management Page - Full CRUD Interface.

Implements comprehensive tenant management for AI Agents admin UI:
- View all tenants with search/filter
- Add new tenant with validation and connection testing
- Edit existing tenant (masked sensitive fields)
- Delete tenant with confirmation (soft delete)
- Display webhook URL after creation

Story: 6.3 - Create Tenant Management Interface
Story: 8.13 - BYOK (Bring Your Own Key) Configuration
"""

import pandas as pd
import streamlit as st
from admin.utils.db_helper import get_db_session, show_connection_status
from admin.utils.tenant_helper import get_all_tenants, get_tenant_by_id
from admin.pages._2_tenants_ui_helpers import (
    add_tenant_dialog,
    delete_tenant_dialog,
    edit_tenant_dialog,
    show_tenant_budget_dashboard,
    show_tenant_byok_sections,
)


@st.cache_data(ttl=60)
def load_tenants(include_inactive: bool):
    """Load tenants with caching.
    
    Returns serializable tenant data for Streamlit caching.
    Excludes sensitive encrypted fields for list view.
    """
    tenants = get_all_tenants(include_inactive=include_inactive)
    
    # Convert SQLAlchemy models to dictionaries for serialization
    serializable_tenants = []
    for tenant in tenants:
        tenant_dict = {
            "id": tenant.id,
            "tenant_id": tenant.tenant_id,
            "name": tenant.name,
            "tool_type": tenant.tool_type,
            "servicedesk_url": tenant.servicedesk_url,
            "is_active": tenant.is_active,
            "created_at": tenant.created_at,
            "updated_at": tenant.updated_at,
            "enhancement_preferences": tenant.enhancement_preferences,
        }
        serializable_tenants.append(tenant_dict)
    
    return serializable_tenants


def show_tenant_list_table(tenants):
    """Render tenants as a DataFrame table.
    
    Args:
        tenants: List of tenant dictionaries from load_tenants()
    """
    tenant_data = []
    for t in tenants:
        tool_type = t.get("tool_type")
        plugin_name = (
            "ServiceDesk Plus"
            if tool_type == "servicedesk_plus"
            else tool_type.replace("_", " ").title() if tool_type else "Not assigned"
        )
        tenant_data.append(
            {
                "Name": t["name"],
                "Tenant ID": t["tenant_id"],
                "Assigned Plugin": plugin_name,
                "ServiceDesk URL": t.get("servicedesk_url", ""),
                "Status": "✅ Active" if t["is_active"] else "❌ Inactive",
                "Created": t["created_at"].strftime("%Y-%m-%d"),
            }
        )

    df = pd.DataFrame(tenant_data)
    st.dataframe(df, use_container_width=True, hide_index=True)


def show_tenant_detail_view(tenants):
    """Render detailed view of selected tenant with actions.
    
    Args:
        tenants: List of tenant dictionaries from load_tenants()
    """
    st.markdown("### Tenant Details & Actions")
    selected_tenant = st.selectbox(
        "Select tenant to view/manage:",
        options=[t["tenant_id"] for t in tenants],
        format_func=lambda tid: next(t["name"] for t in tenants if t["tenant_id"] == tid),
    )

    if selected_tenant:
        # Get the full tenant object from database for detail view
        # This ensures compatibility with budget dashboard and BYOK sections
        tenant = get_tenant_by_id(selected_tenant)
        
        if not tenant:
            st.error("Failed to load tenant details")
            return

        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"**Name:** {tenant.name}")
            st.markdown(f"**Tenant ID:** `{tenant.tenant_id}`")
            tool_type = tenant.tool_type
            plugin_name = (
                "ServiceDesk Plus"
                if tool_type == "servicedesk_plus"
                else (
                    tool_type.replace("_", " ").title()
                    if tool_type
                    else "Not assigned"
                )
            )
            st.markdown(f"**Assigned Plugin:** {plugin_name}")
            st.markdown(f"**ServiceDesk URL:** {tenant.servicedesk_url}")
            st.markdown(f"**Status:** {'✅ Active' if tenant.is_active else '❌ Inactive'}")
            st.markdown(f"**Created:** {tenant.created_at}")
            st.markdown(f"**Updated:** {tenant.updated_at}")

            with st.expander("Enhancement Preferences"):
                st.json(tenant.enhancement_preferences)

            show_tenant_budget_dashboard(tenant)
            show_tenant_byok_sections(tenant)

        with col2:
            st.markdown("**Actions:**")
            if st.button(
                "✏️ Edit Tenant", key=f"edit_{tenant.tenant_id}", use_container_width=True
            ):
                edit_tenant_dialog(tenant.tenant_id)

            if tenant.is_active:
                if st.button(
                    "🗑️ Delete Tenant",
                    key=f"delete_{tenant.tenant_id}",
                    use_container_width=True,
                ):
                    delete_tenant_dialog(tenant.tenant_id)


def show() -> None:
    """Render the Tenant Management page with full CRUD operations."""
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
            if search_term.lower() in t["name"].lower() or search_term.lower() in t["tenant_id"].lower()
        ]

    # Apply status filter
    if status_filter == "Active":
        tenants = [t for t in tenants if t["is_active"]]
    elif status_filter == "Inactive":
        tenants = [t for t in tenants if not t["is_active"]]

    # Display tenants
    st.subheader(f"📋 Tenants ({len(tenants)} found)")

    if not tenants:
        st.info("No tenants found. Click 'Add Tenant' to create your first tenant configuration.")
    else:
        show_tenant_list_table(tenants)
        show_tenant_detail_view(tenants)


if __name__ == "__main__":
    show()
