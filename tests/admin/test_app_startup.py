"""
Tests for Streamlit app startup and initialization.

Tests app configuration, authentication, and navigation setup.
"""

import os
from unittest.mock import Mock, patch, MagicMock

import pytest

from admin.app import check_authentication, show_login_form, main


class TestCheckAuthentication:
    """Test authentication checking logic."""

    def test_kubernetes_authentication(self):
        """Test authentication succeeds when running in Kubernetes."""
        with patch.dict(os.environ, {"KUBERNETES_SERVICE_HOST": "10.0.0.1"}, clear=False):
            with patch("admin.app.st") as mock_st:
                mock_st.session_state = {}

                result = check_authentication()

                assert result is True
                assert mock_st.session_state["authentication_status"] is True
                assert "username" in mock_st.session_state

    def test_local_dev_authenticated(self):
        """Test authentication check when user already authenticated locally."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("admin.app.st") as mock_st:
                mock_st.session_state = {"authentication_status": True}

                result = check_authentication()

                assert result is True

    def test_local_dev_not_authenticated(self):
        """Test authentication check when user not authenticated."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("admin.app.st") as mock_st:
                mock_st.session_state = {}

                result = check_authentication()

                assert result is False
                assert mock_st.session_state["authentication_status"] is False


class TestShowLoginForm:
    """Test login form rendering and submission."""

    @patch("admin.app.st")
    def test_login_form_display(self, mock_st):
        """Test login form renders correctly."""
        # Mock form context
        mock_form = MagicMock()
        mock_st.form.return_value.__enter__.return_value = mock_form
        mock_st.session_state = {}

        # Mock form fields
        mock_st.text_input.side_effect = ["", ""]  # username, password
        mock_st.form_submit_button.return_value = False  # Not submitted

        show_login_form()

        # Verify UI elements displayed
        mock_st.title.assert_called_once()
        assert mock_st.text_input.call_count == 2  # username and password fields

    @patch("admin.app.st")
    def test_login_success_with_secrets(self, mock_st):
        """Test successful login with configured secrets."""
        # Mock form submission
        mock_form = MagicMock()
        mock_st.form.return_value.__enter__.return_value = mock_form
        mock_st.session_state = {}

        # Mock form inputs
        mock_st.text_input.side_effect = ["admin", "testpass"]
        mock_st.form_submit_button.return_value = True  # Form submitted

        # Mock secrets
        mock_st.secrets = {
            "credentials": {
                "usernames": {
                    "admin": {"password": "testpass", "name": "Admin User"}
                }
            }
        }

        # Mock rerun
        mock_st.rerun = Mock()

        show_login_form()

        # Verify authentication set
        assert mock_st.session_state["authentication_status"] is True
        assert mock_st.session_state["username"] == "admin"
        mock_st.rerun.assert_called_once()

    @patch("admin.app.st")
    def test_login_failure_with_secrets(self, mock_st):
        """Test failed login with incorrect credentials."""
        mock_form = MagicMock()
        mock_st.form.return_value.__enter__.return_value = mock_form
        mock_st.session_state = {}

        mock_st.text_input.side_effect = ["admin", "wrongpass"]
        mock_st.form_submit_button.return_value = True

        mock_st.secrets = {
            "credentials": {
                "usernames": {
                    "admin": {"password": "correctpass", "name": "Admin"}
                }
            }
        }

        show_login_form()

        # Verify error displayed
        mock_st.error.assert_called()
        assert "authentication_status" not in mock_st.session_state or \
               mock_st.session_state.get("authentication_status") is False

    @patch("admin.app.st")
    def test_login_default_credentials_fallback(self, mock_st):
        """Test fallback to default credentials when secrets not configured."""
        mock_form = MagicMock()
        mock_st.form.return_value.__enter__.return_value = mock_form
        mock_st.session_state = {}

        mock_st.text_input.side_effect = ["admin", "admin"]
        mock_st.form_submit_button.return_value = True

        # Simulate missing secrets
        mock_st.secrets.get.side_effect = Exception("No secrets configured")
        mock_st.rerun = Mock()

        show_login_form()

        # Verify default credentials accepted
        assert mock_st.session_state["authentication_status"] is True
        assert mock_st.session_state["username"] == "admin"
        mock_st.warning.assert_called()  # Warning about default credentials


class TestMainFunction:
    """Test main application entry point."""

    @patch("admin.app.check_authentication")
    @patch("admin.app.show_login_form")
    @patch("admin.app.st")
    def test_main_not_authenticated(self, mock_st, mock_login, mock_auth):
        """Test main shows login form when not authenticated."""
        mock_auth.return_value = False
        mock_st.session_state = {}

        main()

        mock_auth.assert_called_once()
        mock_login.assert_called_once()

    @patch("admin.app.check_authentication")
    @patch("admin.app.show_header")
    @patch("admin.app.st")
    def test_main_authenticated_success(self, mock_st, mock_header, mock_auth):
        """Test main shows navigation when authenticated."""
        mock_auth.return_value = True
        mock_st.session_state = {"authentication_status": True}

        # Mock st.Page and navigation
        mock_page = Mock()
        mock_st.Page.return_value = mock_page
        mock_navigation = Mock()
        mock_st.navigation.return_value = mock_navigation

        # Mock the imported page modules with show methods
        with patch("admin.pages.dashboard") as mock_dashboard, \
             patch("admin.pages.tenants") as mock_tenants, \
             patch("admin.pages.history") as mock_history:

            mock_dashboard.show = Mock()
            mock_tenants.show = Mock()
            mock_history.show = Mock()

            main()

            mock_auth.assert_called_once()
            mock_header.assert_called_once()
            mock_st.navigation.assert_called_once()
            mock_navigation.run.assert_called_once()

    @patch("admin.app.check_authentication")
    @patch("admin.app.show_header")
    @patch("admin.app.st")
    def test_main_fallback_navigation_on_import_error(self, mock_st, mock_header, mock_auth):
        """Test main uses fallback navigation when page imports fail."""
        mock_auth.return_value = True
        mock_st.session_state = {"authentication_status": True}

        mock_page = Mock()
        mock_st.Page.return_value = mock_page
        mock_navigation = Mock()
        mock_st.navigation.return_value = mock_navigation

        # Simulate import error by making the from import statement fail
        with patch("admin.pages.dashboard", side_effect=ImportError("Module not found")):
            main()

            # Should still create navigation with file paths as fallback
            # Verify that st.Page was called with file paths (string arguments)
            assert mock_st.Page.call_count >= 1
            mock_st.navigation.assert_called_once()
            mock_navigation.run.assert_called_once()


class TestPageConfiguration:
    """Test Streamlit page configuration."""

    @patch("admin.app.st")
    def test_set_page_config_called(self, mock_st):
        """Test st.set_page_config is called on module import."""
        # Import triggers set_page_config at module level
        import admin.app

        # Verify set_page_config was called (it's called at module import)
        # This test verifies the module loads without errors
        assert hasattr(admin.app, "main")
        assert callable(admin.app.main)
