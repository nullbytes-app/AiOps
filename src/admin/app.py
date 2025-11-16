"""
AI Agents Admin UI - Main Application.

This module provides the main entrypoint for the Streamlit admin interface.
It handles navigation, authentication, and common UI elements shared across pages.

The admin UI provides operations teams with:
- System status dashboard with real-time metrics
- Tenant configuration management
- Enhancement history viewer
- System operations controls

Architecture:
- Uses Streamlit 1.44+ st.Page and st.navigation for multi-page routing
- Synchronous database access via SQLAlchemy (separate from async FastAPI layer)
- Session-based authentication with local dev fallback
- Shared database models from src/database/models.py
"""

import os
from typing import Optional

import streamlit as st
from loguru import logger

# Configure page settings (must be first Streamlit command)
st.set_page_config(
    page_title="AI Agents Admin",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/your-org/ai-agents",
        "Report a bug": "https://github.com/your-org/ai-agents/issues",
        "About": "AI Agents Admin UI - Multi-tenant AI enhancement platform",
    },
)


def check_authentication() -> bool:
    """
    Check if user is authenticated.

    In local dev mode, uses simple session state authentication.
    In production, relies on Kubernetes Ingress basic auth (users already authenticated).

    Returns:
        bool: True if authenticated, False otherwise
    """
    # Check if running behind Kubernetes Ingress with basic auth
    # In production, REMOTE_USER environment variable is set by Ingress
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        # Running in Kubernetes - assume Ingress handles auth
        st.session_state["authentication_status"] = True
        st.session_state["username"] = os.getenv("REMOTE_USER", "admin")
        return True

    # Local dev mode - check session state
    if "authentication_status" not in st.session_state:
        st.session_state["authentication_status"] = False

    return st.session_state.get("authentication_status", False)


def show_login_form() -> None:
    """
    Display login form for local development.

    In production, authentication is handled by Kubernetes Ingress basic auth.
    This form is only shown when running locally without Ingress.
    """
    st.title("🔐 AI Agents Admin Login")
    st.markdown("---")

    with st.form("login_form"):
        st.markdown("### Local Development Login")
        st.info(
            "**Production Note:** In production, authentication is handled by "
            "Kubernetes Ingress with basic auth or OAuth2-Proxy."
        )

        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        submit = st.form_submit_button("Login", type="primary")

        if submit:
            # Load credentials from secrets (local dev only)
            try:
                valid_users = st.secrets.get("credentials", {}).get("usernames", {})
                if username in valid_users and valid_users[username]["password"] == password:
                    st.session_state["authentication_status"] = True
                    st.session_state["username"] = username
                    st.session_state["name"] = valid_users[username].get("name", username)
                    st.success("✅ Login successful!")
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")
            except Exception as e:
                # If secrets.toml not configured, use default credentials for dev
                logger.warning(f"No secrets.toml configured, using default credentials: {e}")
                if username == "admin" and password == "admin":
                    st.session_state["authentication_status"] = True
                    st.session_state["username"] = "admin"
                    st.session_state["name"] = "Administrator"
                    st.warning(
                        "⚠️ Using default credentials. Configure `.streamlit/secrets.toml` "
                        "for production-grade authentication."
                    )
                    st.rerun()
                else:
                    st.error(
                        "❌ Invalid credentials. Default: username=`admin`, password=`admin`"
                    )


def show_header() -> None:
    """Display common header across all pages."""
    col1, col2 = st.columns([3, 1])

    with col1:
        st.title("🤖 AI Agents Admin UI")

    with col2:
        if st.session_state.get("authentication_status"):
            username = st.session_state.get("name", st.session_state.get("username", "User"))
            st.markdown(f"**User:** {username}")
            if st.button("Logout", key="logout_button"):
                st.session_state["authentication_status"] = False
                st.rerun()


def main() -> None:
    """
    Main application entry point.

    Handles authentication, navigation, and page routing.
    """
    # Check authentication first
    if not check_authentication():
        show_login_form()
        return

    # User is authenticated - show navigation and pages
    show_header()
    st.markdown("---")

    # Define pages for navigation using relative paths from app.py location
    # Since app.py is in src/admin/, paths are relative to that directory
    pages = [
        st.Page("pages/1_Dashboard.py", title="Dashboard", icon="📊"),
        st.Page("pages/2_Tenants.py", title="Tenant Management", icon="🏢"),
        st.Page("pages/3_Plugin_Management.py", title="Plugin Management", icon="🔌"),
        st.Page("pages/4_History.py", title="Enhancement History", icon="📜"),
        st.Page("pages/5_Agent_Management.py", title="Agent Management", icon="🤖"),
        st.Page("pages/6_LLM_Providers.py", title="LLM Providers", icon="🔑"),
        st.Page("pages/7_Operations.py", title="System Operations", icon="⚙️"),
        st.Page("pages/07_LLM_Costs.py", title="LLM Costs", icon="💰"),
        st.Page("pages/8_Workers.py", title="Worker Health", icon="👷"),
        st.Page("pages/08_Agent_Performance.py", title="Agent Performance", icon="📈"),
        st.Page("pages/9_System_Prompt_Editor.py", title="System Prompt Editor", icon="✏️"),
        st.Page("pages/10_Add_Tool.py", title="Add Tool", icon="🔧"),
        st.Page("pages/11_Execution_History.py", title="Execution History", icon="🕒"),
        st.Page("pages/12_MCP_Servers.py", title="MCP Servers", icon="🔌"),
    ]

    # Configure navigation
    pg = st.navigation(pages)
    pg.run()


if __name__ == "__main__":
    main()
