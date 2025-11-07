"""
Add Tool - OpenAPI specification upload and MCP tool auto-generation.

Story 8.8: OpenAPI Tool Upload and Auto-Generation
Provides:
- File upload for OpenAPI/Swagger specs (.yaml, .json, .yml)
- Automatic spec validation using openapi-pydantic
- Tool metadata extraction (name, description, base URL, auth schemes)
- Dynamic auth configuration form generation
- Test connection functionality
- FastMCP automatic tool generation
- Database persistence with encrypted credentials

Architecture:
- Streamlit 1.30+ for UI
- openapi-pydantic for spec parsing/validation
- FastMCP for automatic MCP tool generation from OpenAPI specs
- httpx for connection testing
- Fernet encryption for auth credentials

Constraints:
- File size ≤ 500 lines
- Max upload size: 5MB
- All API calls use async patterns
- Multi-tenant support (tenant_id isolation)
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Optional

import streamlit as st
import yaml
from httpx import AsyncClient

# Page configuration
st.set_page_config(
    page_title="Add Tool",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Session state initialization
def init_session_state() -> None:
    """Initialize session state variables for tool upload."""
    if "uploaded_file_content" not in st.session_state:
        st.session_state.uploaded_file_content = None
    if "parsed_spec" not in st.session_state:
        st.session_state.parsed_spec = None
    if "spec_metadata" not in st.session_state:
        st.session_state.spec_metadata = None
    if "auth_config" not in st.session_state:
        st.session_state.auth_config = {}
    if "validation_errors" not in st.session_state:
        st.session_state.validation_errors = None
    if "test_connection_result" not in st.session_state:
        st.session_state.test_connection_result = None


# Helper functions
async def async_api_call(
    method: str,
    endpoint: str,
    json_data: Optional[dict[str, Any]] = None,
    timeout: int = 30,
) -> Optional[dict[str, Any]]:
    """
    Make async API call to backend endpoints.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        endpoint: API endpoint path
        json_data: Optional JSON payload for POST/PUT
        timeout: Request timeout in seconds

    Returns:
        Response JSON dict or None if error
    """
    base_url = "http://localhost:8000"
    async with AsyncClient(base_url=base_url, timeout=timeout) as client:
        try:
            response = await client.request(
                method=method,
                url=endpoint,
                json=json_data,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"API Error: {str(e)}")
            return None


def async_to_sync(coro: Any) -> Any:
    """
    Run async coroutine in sync context (Streamlit compatibility).

    Args:
        coro: Async coroutine to execute

    Returns:
        Result from coroutine execution
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def parse_uploaded_file(uploaded_file: Any) -> Optional[dict[str, Any]]:
    """
    Parse uploaded YAML or JSON file to dictionary.

    Args:
        uploaded_file: Streamlit UploadedFile object

    Returns:
        Parsed spec dict or None if parsing fails
    """
    try:
        file_content = uploaded_file.read()
        file_extension = uploaded_file.name.split(".")[-1].lower()

        if file_extension in ["yaml", "yml"]:
            spec_dict = yaml.safe_load(file_content)
        elif file_extension == "json":
            spec_dict = json.loads(file_content)
        else:
            st.error(f"Unsupported file extension: .{file_extension}")
            return None

        return spec_dict
    except yaml.YAMLError as e:
        st.error(f"YAML Parsing Error: {str(e)}")
        return None
    except json.JSONDecodeError as e:
        st.error(f"JSON Parsing Error: {str(e)}")
        return None
    except Exception as e:
        st.error(f"File Parsing Error: {str(e)}")
        return None


def validate_file_size(uploaded_file: Any, max_size_mb: int = 5) -> bool:
    """
    Validate uploaded file size.

    Args:
        uploaded_file: Streamlit UploadedFile object
        max_size_mb: Maximum file size in megabytes

    Returns:
        True if file size is valid, False otherwise
    """
    file_size_mb = uploaded_file.size / (1024 * 1024)
    if file_size_mb > max_size_mb:
        st.error(f"File too large: {file_size_mb:.2f}MB (max: {max_size_mb}MB)")
        return False
    return True


def display_spec_preview(spec_dict: dict[str, Any]) -> None:
    """
    Display formatted OpenAPI spec preview.

    Args:
        spec_dict: Parsed OpenAPI specification dictionary
    """
    with st.expander("📄 Spec Preview", expanded=False):
        st.json(spec_dict)


def render_auth_config_form(security_schemes: dict[str, Any]) -> dict[str, Any]:
    """
    Dynamically render authentication configuration form.

    Args:
        security_schemes: Security schemes from OpenAPI spec

    Returns:
        Auth configuration dictionary
    """
    st.subheader("🔐 Authentication Configuration")

    if not security_schemes:
        st.info("No authentication schemes detected in spec.")
        return {"type": "none"}

    # If multiple schemes, let user choose
    if len(security_schemes) > 1:
        scheme_names = list(security_schemes.keys())
        selected_scheme = st.selectbox(
            "Select Authentication Method",
            options=scheme_names,
            help="Choose one authentication method to configure",
        )
        scheme = security_schemes[selected_scheme]
    else:
        selected_scheme = list(security_schemes.keys())[0]
        scheme = security_schemes[selected_scheme]
        st.info(f"**Detected Auth Type:** {selected_scheme}")

    auth_type = scheme.get("type", "").lower()
    auth_config: dict[str, Any] = {"type": auth_type, "scheme_name": selected_scheme}

    # API Key authentication
    if auth_type == "apikey":
        location = scheme.get("in", "header")
        param_name = scheme.get("name", "api_key")

        st.write(f"**Location:** {location}")
        auth_config["location"] = location
        auth_config["param_name"] = param_name

        api_key_value = st.text_input(
            f"API Key Value ({param_name})",
            type="password",
            help=f"Enter your API key (will be sent in {location})",
        )
        auth_config["value"] = api_key_value

    # HTTP authentication (Basic, Bearer)
    elif auth_type == "http":
        http_scheme = scheme.get("scheme", "").lower()
        auth_config["http_scheme"] = http_scheme

        if http_scheme == "basic":
            st.write("**Basic Authentication**")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            auth_config["username"] = username
            auth_config["password"] = password

        elif http_scheme == "bearer":
            st.write("**Bearer Token Authentication**")
            token = st.text_input("Bearer Token", type="password")
            auth_config["token"] = token

    # OAuth 2.0 authentication
    elif auth_type == "oauth2":
        st.write("**OAuth 2.0 Configuration**")
        flows = scheme.get("flows", {})
        flow_type = st.selectbox("Flow Type", options=list(flows.keys()))
        auth_config["flow_type"] = flow_type

        client_id = st.text_input("Client ID")
        client_secret = st.text_input("Client Secret", type="password")
        token_url = st.text_input("Token URL", value=flows.get(flow_type, {}).get("tokenUrl", ""))

        auth_config["client_id"] = client_id
        auth_config["client_secret"] = client_secret
        auth_config["token_url"] = token_url

        # Scopes
        available_scopes = flows.get(flow_type, {}).get("scopes", {})
        if available_scopes:
            selected_scopes = st.multiselect(
                "Scopes",
                options=list(available_scopes.keys()),
                help="Select required OAuth scopes",
            )
            auth_config["scopes"] = selected_scopes

    else:
        st.warning(f"Unsupported authentication type: {auth_type}")
        auth_config = {"type": "unsupported", "details": scheme}

    return auth_config


# Main app
def main() -> None:
    """Main application entry point."""
    init_session_state()

    st.title("🔧 Add Tool from OpenAPI Spec")
    st.markdown(
        "Upload an OpenAPI/Swagger specification to automatically generate MCP tools."
    )

    # File upload section
    st.subheader("📤 Upload OpenAPI Specification")

    uploaded_file = st.file_uploader(
        "Choose an OpenAPI spec file",
        type=["yaml", "yml", "json"],
        accept_multiple_files=False,
        help="Supports OpenAPI 2.0 (Swagger), 3.0, and 3.1 specifications",
    )

    if uploaded_file:
        # Validate file size
        if not validate_file_size(uploaded_file, max_size_mb=5):
            return

        # Parse file
        if st.button("Parse Specification", type="primary"):
            with st.spinner("Parsing OpenAPI specification..."):
                spec_dict = parse_uploaded_file(uploaded_file)

                if spec_dict:
                    st.session_state.uploaded_file_content = spec_dict
                    st.success("✅ Spec parsed successfully!")

                    # Call backend to validate and extract metadata
                    result = async_to_sync(
                        async_api_call(
                            "POST",
                            "/api/openapi-tools/parse",
                            json_data={"spec": spec_dict},
                        )
                    )

                    if result:
                        st.session_state.parsed_spec = result.get("parsed_spec")
                        st.session_state.spec_metadata = result.get("metadata")
                        st.session_state.validation_errors = None
                    else:
                        st.session_state.validation_errors = "Failed to validate spec"

    # Display spec preview
    if st.session_state.uploaded_file_content:
        display_spec_preview(st.session_state.uploaded_file_content)

    # Display metadata and auth config form
    if st.session_state.spec_metadata:
        metadata = st.session_state.spec_metadata

        st.subheader("📋 Tool Metadata")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Tool Name", metadata.get("tool_name", "N/A"))
        with col2:
            st.metric("Spec Version", metadata.get("spec_version", "N/A"))
        with col3:
            st.metric("Total Endpoints", metadata.get("endpoint_count", 0))

        st.text_input("Base URL", value=metadata.get("base_url", ""), key="base_url_input")
        st.text_area("Description", value=metadata.get("description", ""), height=100)

        # Render auth config form
        security_schemes = metadata.get("auth_schemes", {})
        if security_schemes:
            auth_config = render_auth_config_form(security_schemes)
            st.session_state.auth_config = auth_config

            # Test connection button
            if st.button("🧪 Test Connection"):
                with st.spinner("Testing connection..."):
                    test_result = async_to_sync(
                        async_api_call(
                            "POST",
                            "/api/openapi-tools/test-connection",
                            json_data={
                                "spec": st.session_state.uploaded_file_content,
                                "auth_config": auth_config,
                            },
                        )
                    )

                    if test_result and test_result.get("success"):
                        st.success(
                            f"✅ Connection successful! Status: {test_result.get('status_code')}"
                        )
                        if test_result.get("response_preview"):
                            st.code(test_result["response_preview"])
                    else:
                        error_msg = test_result.get("error_message", "Connection failed")
                        st.error(f"❌ {error_msg}")

        # Save tool button
        st.divider()
        if st.button("💾 Save Tool", type="primary"):
            if not st.session_state.auth_config:
                st.warning("Please configure authentication first")
                return

            with st.spinner("Saving tool and generating MCP tools..."):
                save_result = async_to_sync(
                    async_api_call(
                        "POST",
                        "/api/openapi-tools",
                        json_data={
                            "tool_name": metadata.get("tool_name"),
                            "openapi_spec": st.session_state.uploaded_file_content,
                            "spec_version": metadata.get("spec_version"),
                            "base_url": st.session_state.base_url_input,
                            "auth_config": st.session_state.auth_config,
                            "tenant_id": 1,  # TODO: Get from session
                        },
                    )
                )

                if save_result:
                    st.success(
                        f"✅ Tool saved! Generated {save_result.get('tools_count', 0)} MCP tools."
                    )
                    st.balloons()
                    # Reset state
                    for key in ["uploaded_file_content", "parsed_spec", "spec_metadata", "auth_config"]:
                        st.session_state[key] = None
                else:
                    st.error("Failed to save tool")

    # Display validation errors
    if st.session_state.validation_errors:
        st.error("⚠️ Validation Errors")
        st.code(st.session_state.validation_errors)


if __name__ == "__main__":
    main()
