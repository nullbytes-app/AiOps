"""
Plugin Management Page.

Displays registered plugins, configuration schemas, and connection testing.

Features (Story 7.8):
- View all registered plugins in table format (AC#3, AC#4)
- Filter plugins by status and search by name
- Expandable configuration schema view
- Plugin connection testing interface
- Integration with tenant assignment (AC#7)
"""

from typing import Any, Dict, List, Optional
import os

import httpx
import pandas as pd
import streamlit as st
from loguru import logger

# API configuration - use environment variable first, then secrets, then default
API_BASE_URL = os.getenv("API_BASE_URL", st.secrets.get("api_base_url", "http://localhost:8000"))


@st.cache_data(ttl=60)
def fetch_plugins() -> Dict[str, Any]:
    """
    Fetch all registered plugins from API.

    Returns:
        dict: Response with plugins list and count, or error dict

    Example:
        {
            "plugins": [
                {
                    "plugin_id": "servicedesk_plus",
                    "name": "ServiceDesk Plus",
                    "version": "1.0.0",
                    "status": "active",
                    "description": "ManageEngine ServiceDesk Plus plugin",
                    "tool_type": "servicedesk_plus"
                }
            ],
            "count": 1
        }
    """
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{API_BASE_URL}/api/v1/plugins/")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching plugins: {e.response.status_code} - {e.response.text}")
        return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
    except httpx.RequestError as e:
        logger.error(f"Request error fetching plugins: {str(e)}")
        return {"error": f"Connection error: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error fetching plugins: {str(e)}", exc_info=True)
        return {"error": f"Unexpected error: {str(e)}"}


@st.cache_data(ttl=300)
def fetch_plugin_details(plugin_id: str) -> Dict[str, Any]:
    """
    Fetch detailed plugin configuration schema.

    Args:
        plugin_id: Plugin identifier (e.g., "servicedesk_plus", "jira")

    Returns:
        dict: Plugin details with config schema, or error dict

    Example:
        {
            "plugin_id": "jira",
            "name": "Jira Service Management",
            "version": "1.0.0",
            "description": "Atlassian Jira plugin",
            "tool_type": "jira",
            "config_schema": {
                "plugin_id": "jira",
                "schema_fields": [
                    {
                        "field_name": "jira_url",
                        "field_type": "string",
                        "required": true,
                        "description": "Jira instance URL"
                    }
                ]
            }
        }
    """
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{API_BASE_URL}/api/v1/plugins/{plugin_id}")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP error fetching plugin details for {plugin_id}: "
            f"{e.response.status_code} - {e.response.text}"
        )
        return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
    except httpx.RequestError as e:
        logger.error(f"Request error fetching plugin details for {plugin_id}: {str(e)}")
        return {"error": f"Connection error: {str(e)}"}
    except Exception as e:
        logger.error(
            f"Unexpected error fetching plugin details for {plugin_id}: {str(e)}",
            exc_info=True,
        )
        return {"error": f"Unexpected error: {str(e)}"}


def test_plugin_connection(plugin_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test plugin connection with provided configuration.

    Args:
        plugin_id: Plugin identifier
        config: Configuration dictionary to test

    Returns:
        dict: Test result with success status and message

    Example:
        {
            "success": true,
            "message": "Connection successful"
        }
    """
    try:
        with httpx.Client(timeout=35.0) as client:  # 30s plugin timeout + 5s buffer
            response = client.post(
                f"{API_BASE_URL}/api/v1/plugins/{plugin_id}/test", json={"config": config}
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP error testing plugin connection for {plugin_id}: "
            f"{e.response.status_code} - {e.response.text}"
        )
        return {
            "success": False,
            "message": f"HTTP {e.response.status_code}: {e.response.text}",
        }
    except httpx.TimeoutException:
        logger.error(f"Timeout testing plugin connection for {plugin_id}")
        return {"success": False, "message": "Connection test timed out (30 second limit)"}
    except httpx.RequestError as e:
        logger.error(f"Request error testing plugin connection for {plugin_id}: {str(e)}")
        return {"success": False, "message": f"Connection error: {str(e)}"}
    except Exception as e:
        logger.error(
            f"Unexpected error testing plugin connection for {plugin_id}: {str(e)}",
            exc_info=True,
        )
        return {"success": False, "message": f"Unexpected error: {str(e)}"}


def display_status_badge(status: str) -> str:
    """
    Generate color-coded status badge HTML.

    Args:
        status: Plugin status (active, inactive, error)

    Returns:
        str: HTML for status badge
    """
    colors = {
        "active": "#28a745",  # Green
        "inactive": "#6c757d",  # Gray
        "error": "#dc3545",  # Red
    }
    color = colors.get(status.lower(), "#17a2b8")  # Default blue
    return f'<span style="background-color:{color};color:white;padding:2px 8px;border-radius:3px;font-size:12px;">{status.upper()}</span>'


def show() -> None:
    """
    Render the Plugin Management page.

    Implements Story 7.8 acceptance criteria:
    - AC#3: Streamlit page at src/admin/pages/03_Plugin_Management.py
    - AC#4: Display plugins in table format (name, type, version, status, description)
    - AC#5: Configuration form with dynamic field generation (via component)
    - Search/filter controls for plugin discovery
    """
    st.set_page_config(
        page_title="Plugin Management - AI Agents Admin",
        page_icon="🔌",
        layout="wide",
    )

    st.title("🔌 Plugin Management")
    st.markdown(
        "Manage ticketing tool plugins, configure connections, and assign plugins to tenants."
    )

    # Sidebar controls
    with st.sidebar:
        st.subheader("⚙️ Plugin Filters")

        # Status filter
        status_filter = st.selectbox(
            "Filter by Status",
            options=["All", "Active", "Inactive", "Error"],
            index=0,
        )

        # Search filter
        search_query = st.text_input("🔍 Search Plugins", placeholder="Enter plugin name...")

        st.markdown("---")

        # Refresh button
        if st.button("🔄 Refresh Plugin List"):
            st.cache_data.clear()
            st.rerun()

    # Fetch plugins
    with st.spinner("Loading plugins..."):
        plugins_response = fetch_plugins()

    if "error" in plugins_response:
        st.error(f"❌ Failed to load plugins: {plugins_response['error']}")
        st.info(
            "**Troubleshooting:**\n"
            "- Ensure the API server is running\n"
            "- Verify API_BASE_URL in .streamlit/secrets.toml\n"
            f"- Current API URL: {API_BASE_URL}"
        )
        return

    plugins = plugins_response.get("plugins", [])
    count = plugins_response.get("count", 0)

    if count == 0:
        st.warning(
            "⚠️ No plugins registered. Plugins should be auto-discovered at application startup."
        )
        st.info(
            "**Expected Plugins:**\n"
            "- ServiceDesk Plus (`servicedesk_plus`)\n"
            "- Jira Service Management (`jira`)\n\n"
            "Check application logs for plugin registration errors."
        )
        return

    # Apply filters
    filtered_plugins = plugins.copy()

    # Status filter
    if status_filter != "All":
        filtered_plugins = [
            p for p in filtered_plugins if p["status"].lower() == status_filter.lower()
        ]

    # Search filter
    if search_query:
        query_lower = search_query.lower()
        filtered_plugins = [
            p
            for p in filtered_plugins
            if query_lower in p["name"].lower() or query_lower in p["description"].lower()
        ]

    # Display filtered count
    st.caption(f"Showing {len(filtered_plugins)} of {count} plugins")

    # Display plugins in table format (AC#4)
    if filtered_plugins:
        # Convert to DataFrame for display
        df_data = []
        for plugin in filtered_plugins:
            df_data.append(
                {
                    "Plugin Name": plugin["name"],
                    "Type": plugin["tool_type"],
                    "Version": plugin["version"],
                    "Status": plugin["status"],
                    "Description": plugin["description"],
                }
            )

        df = pd.DataFrame(df_data)

        # Display as interactive dataframe
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Plugin Name": st.column_config.TextColumn("Plugin Name", width="medium"),
                "Type": st.column_config.TextColumn("Type", width="small"),
                "Version": st.column_config.TextColumn("Version", width="small"),
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Description": st.column_config.TextColumn("Description", width="large"),
            },
        )

        st.markdown("---")

        # Plugin details expanders (AC#4 - expandable configuration view)
        st.subheader("📋 Plugin Details")

        for plugin in filtered_plugins:
            with st.expander(f"🔌 {plugin['name']} ({plugin['tool_type']})"):
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.markdown(f"**Description:** {plugin['description']}")
                    st.markdown(f"**Version:** {plugin['version']}")
                    st.markdown(
                        f"**Status:** {display_status_badge(plugin['status'])}",
                        unsafe_allow_html=True,
                    )

                with col2:
                    st.markdown(f"**Plugin ID:** `{plugin['plugin_id']}`")
                    st.markdown(f"**Tool Type:** `{plugin['tool_type']}`")

                st.markdown("---")

                # Fetch and display configuration schema
                with st.spinner("Loading configuration schema..."):
                    details = fetch_plugin_details(plugin["plugin_id"])

                if "error" in details:
                    st.error(f"Failed to load configuration schema: {details['error']}")
                else:
                    st.markdown("#### Configuration Schema")

                    config_schema = details.get("config_schema", {})
                    schema_fields = config_schema.get("schema_fields", [])

                    if schema_fields:
                        # Display schema fields in table
                        schema_df = pd.DataFrame(schema_fields)
                        st.dataframe(
                            schema_df[
                                ["field_name", "field_type", "required", "description"]
                            ],
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "field_name": "Field Name",
                                "field_type": "Type",
                                "required": "Required",
                                "description": "Description",
                            },
                        )
                    else:
                        st.info("No configuration fields defined for this plugin.")

                    # Connection testing preview (full implementation in Task 5)
                    st.markdown("#### Test Connection")
                    st.info(
                        "ℹ️ Connection testing interface will be available after completing Task 5 "
                        "(test_connection() method implementation)."
                    )

    else:
        st.info(f"No plugins match your filters. Try adjusting the status or search query.")


# Entry point
if __name__ == "__main__":
    show()
