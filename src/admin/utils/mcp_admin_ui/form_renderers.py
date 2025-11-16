"""
MCP Server Form Renderers

Renders add/edit forms for MCP servers (stdio and HTTP+SSE transports).
Extracted from 12_MCP_Servers.py for maintainability (Story 12.7).

Features:
- Transport type selection (stdio, http_sse)
- Stdio fields: command, args, environment variables
- HTTP+SSE fields: URL, custom headers
- Form validation with helpful error messages
- Session state management for multi-page form flow

References:
- Story 12.7: File Size Refactoring and Code Quality
- Story 11.1.9: Admin UI for MCP Server Management
- Story 11.2.1: MCP HTTP+SSE Transport Client

Usage:
    from src.admin.utils.mcp_admin_ui import render_server_form

    # Add mode
    render_server_form(edit_mode=False)

    # Edit mode
    render_server_form(edit_mode=True)
"""

from typing import Any, Optional

import streamlit as st

from src.admin.utils.mcp_form_helpers import (
    render_http_headers_editor,
    render_http_sse_url_field,
    validate_url,
)
from src.admin.utils.mcp_ui_helpers import (
    create_mcp_server,
    fetch_mcp_server_details,
    update_mcp_server,
)


def switch_view(view: str, server_id: Optional[str] = None) -> None:
    """
    Switch between MCP admin views.

    Updates session state to trigger view transition. Clears form state
    when switching to "add" view to ensure clean form.

    Args:
        view: Target view name ("list", "add", "edit", "details")
        server_id: Optional server UUID for "edit" or "details" views
    """
    st.session_state.mcp_view = view
    st.session_state.selected_server_id = server_id
    if view == "add":
        st.session_state.env_vars = []
        st.session_state.http_headers = []
        st.session_state.test_results = None


def render_server_form(edit_mode: bool = False) -> None:
    """
    Render add or edit MCP server form.

    Displays form for creating new MCP server or editing existing one.
    Transport type selection determines which fields to show:
    - stdio: command, args, environment variables
    - http_sse: URL, custom headers

    Args:
        edit_mode: If True, loads existing server data and disables transport type change

    Session State:
        - selected_server_id: UUID of server being edited (edit mode only)
        - tenant_id: Current tenant context
        - env_vars: List of {"key": str, "value": str} dicts for stdio
        - http_headers: List of {"key": str, "value": str} dicts for HTTP+SSE
        - transport_type: Selected transport type (add mode only)

    Form Fields:
        Common:
        - name: Server name (required)
        - description: Optional server description

        Stdio:
        - command: Command to spawn server (required, e.g., "npx")
        - args: Command arguments (textarea, one per line)
        - env_vars: Environment variables (10 key-value pairs)

        HTTP+SSE:
        - url: Server URL (required, validated)
        - headers: Custom HTTP headers (10 key-value pairs)

    Validation:
        - Name required
        - Command required for stdio
        - URL required and validated for HTTP+SSE
        - Empty env/header rows ignored

    Example:
        >>> # From page main routing:
        >>> if st.session_state.mcp_view == "add":
        >>>     render_server_form(edit_mode=False)
        >>> elif st.session_state.mcp_view == "edit":
        >>>     render_server_form(edit_mode=True)
    """
    st.subheader("Edit MCP Server" if edit_mode else "Add New MCP Server")

    server_data: Optional[dict[str, Any]] = None
    if edit_mode and st.session_state.selected_server_id:
        try:
            server_data = fetch_mcp_server_details(
                st.session_state.selected_server_id, st.session_state.tenant_id
            )
            if not st.session_state.env_vars:
                st.session_state.env_vars = [
                    {"key": k, "value": v} for k, v in (server_data.get("env") or {}).items()
                ]
            if not st.session_state.http_headers:
                st.session_state.http_headers = [
                    {"key": k, "value": v} for k, v in (server_data.get("headers") or {}).items()
                ]
        except Exception as e:
            st.error(f"Failed to load server: {str(e)}")
            if st.button("← Back to List"):
                switch_view("list")
                st.rerun()
            return

    # Transport type selection OUTSIDE the form so page can rerender when changed
    if edit_mode and server_data:
        st.text_input(
            "Transport Type",
            value=server_data.get("transport_type", ""),
            disabled=True,
            help="Transport type cannot be changed after creation",
        )
        transport_type = server_data.get("transport_type", "stdio")
    else:
        # Initialize transport_type in session state if not present
        if "transport_type" not in st.session_state:
            st.session_state.transport_type = "stdio"

        transport_type = st.selectbox(
            "Transport Type *",
            options=["stdio", "http_sse"],
            index=0 if st.session_state.transport_type == "stdio" else 1,
            help="Protocol for communicating with the MCP server",
            key="transport_type_selector",
        )
        # Update session state when selection changes
        st.session_state.transport_type = transport_type

    with st.form("mcp_server_form"):
        name = st.text_input(
            "Server Name *",
            value=server_data.get("name", "") if server_data else "",
            help="Unique name for this MCP server",
        )
        description = st.text_area(
            "Description",
            value=server_data.get("description", "") if server_data else "",
            help="Optional description of what this server provides",
        )

        if transport_type == "stdio":
            command = st.text_input(
                "Command *",
                value=server_data.get("command", "") if server_data else "",
                placeholder="npx",
                help="Command to spawn the MCP server process",
            )

            args_value = (
                "\n".join(server_data.get("args", []))
                if server_data and server_data.get("args")
                else ""
            )
            args = st.text_area(
                "Arguments (one per line)",
                value=args_value,
                placeholder="-y\n@modelcontextprotocol/server-filesystem\n/path/to/data",
                help="Arguments for the command, one per line",
            )

            # Environment variables
            st.subheader("Environment Variables (Optional)")
            st.caption(
                "Add environment variables for the MCP server (e.g., API keys, database URLs). "
                "Leave unused rows empty - they will be ignored."
            )

            # Show 10 rows for environment variables
            max_env_rows = 10
            for i in range(max_env_rows):
                # Ensure we have entries in session state
                while len(st.session_state.env_vars) <= i:
                    st.session_state.env_vars.append({"key": "", "value": ""})

                col1, col2 = st.columns([2, 2])
                st.session_state.env_vars[i]["key"] = col1.text_input(
                    f"Variable {i+1} - Key",
                    value=st.session_state.env_vars[i].get("key", ""),
                    key=f"env_key_{i}",
                    label_visibility="collapsed",
                    placeholder=f"VARIABLE_{i+1}_NAME" if i < 3 else "",
                )
                st.session_state.env_vars[i]["value"] = col2.text_input(
                    f"Variable {i+1} - Value",
                    value=st.session_state.env_vars[i].get("value", ""),
                    type="password",
                    key=f"env_val_{i}",
                    label_visibility="collapsed",
                    placeholder="value" if i < 3 else "",
                )

        elif transport_type == "http_sse":
            # URL field with validation
            url = render_http_sse_url_field(server_data)

            # HTTP Headers editor
            render_http_headers_editor()

        # Form buttons
        col1, col2, col3 = st.columns([1, 1, 3])

        submitted = col1.form_submit_button(
            "Save Changes" if edit_mode else "Save",
            type="primary",
            use_container_width=True,
        )

        cancel = col2.form_submit_button("Cancel", use_container_width=True)

        if submitted:
            # Validate required fields
            if not name:
                st.error("Server name is required")
            elif transport_type == "stdio" and not command:
                st.error("Command is required for stdio transport")
            elif transport_type == "http_sse":
                url_valid, url_error = validate_url(url)
                if not url_valid:
                    st.error(url_error)
                    return
            # Build payload only if validation passes
            if (transport_type == "stdio" and name and command) or (
                transport_type == "http_sse" and name and url
            ):
                # Build payload
                payload: dict[str, Any] = {
                    "name": name,
                    "description": description or None,
                }

                if not edit_mode:
                    payload["transport_type"] = transport_type

                if transport_type == "stdio":
                    payload["command"] = command
                    payload["args"] = [arg.strip() for arg in args.split("\n") if arg.strip()]
                    payload["env"] = {
                        ev["key"]: ev["value"] for ev in st.session_state.env_vars if ev["key"]
                    }
                elif transport_type == "http_sse":
                    payload["url"] = url
                    headers_dict = {
                        h["key"]: h["value"] for h in st.session_state.http_headers if h["key"]
                    }
                    if headers_dict:
                        payload["headers"] = headers_dict

                # Save server
                try:
                    with st.spinner("Saving server..." if not edit_mode else "Updating server..."):
                        if edit_mode:
                            result = update_mcp_server(
                                st.session_state.selected_server_id,
                                payload,
                                st.session_state.tenant_id,
                            )
                            st.success(f"MCP server '{name}' updated successfully")
                        else:
                            result = create_mcp_server(payload, st.session_state.tenant_id)
                            st.success(f"MCP server '{name}' created successfully")

                        switch_view("details", result["id"])
                        st.rerun()

                except Exception as e:
                    st.error(f"Failed to save server: {str(e)}")

        if cancel:
            switch_view("list")
            st.rerun()

    # Back button (outside form)
    if st.button("← Back to List"):
        switch_view("list")
        st.rerun()
