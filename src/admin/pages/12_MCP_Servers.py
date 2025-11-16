"""
MCP Servers Management Page

Main page for MCP server management UI. Delegates rendering to helper modules
for improved maintainability (Story 12.7).

Refactoring Note (Story 12.7):
This page was refactored to comply with 2025 Python best practices
(150-500 line sweet spot for AI code editors). Extracted modules:
- mcp_admin_ui.list_display: Server list view with actions
- mcp_admin_ui.form_renderers: Add/edit server forms
- mcp_admin_ui.detail_view: Detailed server view

References:
- Story 12.7: File Size Refactoring and Code Quality
- Story 11.1.9: Admin UI for MCP Server Management
- Story 11.2.1: MCP HTTP+SSE Transport Client
"""

import streamlit as st

from src.admin.utils.mcp_admin_ui import (
    render_server_details,
    render_server_form,
    render_server_list,
)
from src.admin.utils.mcp_ui_helpers import DEFAULT_TENANT_ID

st.set_page_config(page_title="MCP Servers", page_icon="🔌", layout="wide")
st.title("🔌 MCP Servers")
st.markdown(
    "Manage MCP servers for agent tool integration. "
    "Add stdio or HTTP+SSE servers for external tools, resources, and prompts."
)

# Session state initialization
if "tenant_id" not in st.session_state:
    st.session_state.tenant_id = DEFAULT_TENANT_ID
if "mcp_view" not in st.session_state:
    st.session_state.mcp_view = "list"
if "selected_server_id" not in st.session_state:
    st.session_state.selected_server_id = None
if "env_vars" not in st.session_state:
    st.session_state.env_vars = []
if "http_headers" not in st.session_state:
    st.session_state.http_headers = []
if "test_results" not in st.session_state:
    st.session_state.test_results = None

# Main routing (delegated to helper modules for maintainability)
if st.session_state.mcp_view == "list":
    render_server_list()
elif st.session_state.mcp_view == "add":
    render_server_form(edit_mode=False)
elif st.session_state.mcp_view == "edit":
    render_server_form(edit_mode=True)
elif st.session_state.mcp_view == "details":
    render_server_details()
