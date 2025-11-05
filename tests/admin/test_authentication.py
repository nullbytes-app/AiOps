"""
Tests for authentication logic.

Tests session state management, login/logout flows, and credential validation.
"""

import os
from unittest.mock import patch, Mock

import pytest


class TestSessionStateAuthentication:
    """Test session state-based authentication."""

    def test_session_state_initialization(self):
        """Test session state is initialized correctly."""
        from admin.app import check_authentication

        with patch.dict(os.environ, {}, clear=True):
            with patch("admin.app.st") as mock_st:
                mock_st.session_state = {}

                check_authentication()

                assert "authentication_status" in mock_st.session_state
                assert mock_st.session_state["authentication_status"] is False

    def test_session_state_persists_authentication(self):
        """Test authenticated state persists across calls."""
        from admin.app import check_authentication

        with patch.dict(os.environ, {}, clear=True):
            with patch("admin.app.st") as mock_st:
                # Simulate authenticated session
                mock_st.session_state = {"authentication_status": True, "username": "testuser"}

                result = check_authentication()

                assert result is True
                assert mock_st.session_state["authentication_status"] is True
                assert mock_st.session_state["username"] == "testuser"


class TestKubernetesAuthentication:
    """Test Kubernetes Ingress authentication detection."""

    def test_kubernetes_auth_with_service_host(self):
        """Test authentication succeeds when KUBERNETES_SERVICE_HOST is set."""
        from admin.app import check_authentication

        with patch.dict(os.environ, {"KUBERNETES_SERVICE_HOST": "10.0.0.1"}, clear=False):
            with patch("admin.app.st") as mock_st:
                mock_st.session_state = {}

                result = check_authentication()

                assert result is True
                assert mock_st.session_state["authentication_status"] is True

    def test_kubernetes_auth_with_remote_user(self):
        """Test username extracted from REMOTE_USER environment variable."""
        from admin.app import check_authentication

        with patch.dict(os.environ, {
            "KUBERNETES_SERVICE_HOST": "10.0.0.1",
            "REMOTE_USER": "operator123"
        }, clear=False):
            with patch("admin.app.st") as mock_st:
                mock_st.session_state = {}

                check_authentication()

                assert mock_st.session_state["username"] == "operator123"

    def test_kubernetes_auth_default_username(self):
        """Test default username when REMOTE_USER not set."""
        from admin.app import check_authentication

        with patch.dict(os.environ, {"KUBERNETES_SERVICE_HOST": "10.0.0.1"}, clear=False):
            with patch("admin.app.st") as mock_st:
                mock_st.session_state = {}

                check_authentication()

                assert mock_st.session_state["username"] == "admin"


class TestCredentialValidation:
    """Test credential validation logic."""

    def test_valid_credentials_from_secrets(self):
        """Test validation with correct credentials from secrets.toml."""
        from admin.app import show_login_form

        with patch("admin.app.st") as mock_st:
            mock_form = Mock()
            mock_st.form.return_value.__enter__.return_value = mock_form
            mock_st.session_state = {}

            # Simulate form submission
            mock_st.text_input.side_effect = ["alice", "secret123"]
            mock_st.form_submit_button.return_value = True

            # Mock secrets configuration
            mock_st.secrets = {
                "credentials": {
                    "usernames": {
                        "alice": {
                            "password": "secret123",
                            "name": "Alice Admin",
                            "email": "alice@example.com"
                        }
                    }
                }
            }

            mock_st.rerun = Mock()

            show_login_form()

            # Verify successful authentication
            assert mock_st.session_state["authentication_status"] is True
            assert mock_st.session_state["username"] == "alice"
            assert mock_st.session_state["name"] == "Alice Admin"
            mock_st.success.assert_called()

    def test_invalid_password(self):
        """Test validation fails with incorrect password."""
        from admin.app import show_login_form

        with patch("admin.app.st") as mock_st:
            mock_form = Mock()
            mock_st.form.return_value.__enter__.return_value = mock_form
            mock_st.session_state = {}

            mock_st.text_input.side_effect = ["alice", "wrongpass"]
            mock_st.form_submit_button.return_value = True

            mock_st.secrets = {
                "credentials": {
                    "usernames": {
                        "alice": {"password": "correctpass", "name": "Alice"}
                    }
                }
            }

            show_login_form()

            mock_st.error.assert_called()

    def test_invalid_username(self):
        """Test validation fails with nonexistent username."""
        from admin.app import show_login_form

        with patch("admin.app.st") as mock_st:
            mock_form = Mock()
            mock_st.form.return_value.__enter__.return_value = mock_form
            mock_st.session_state = {}

            mock_st.text_input.side_effect = ["bob", "anypass"]
            mock_st.form_submit_button.return_value = True

            mock_st.secrets = {
                "credentials": {
                    "usernames": {
                        "alice": {"password": "pass", "name": "Alice"}
                    }
                }
            }

            show_login_form()

            mock_st.error.assert_called()

    def test_default_credentials_when_secrets_missing(self):
        """Test fallback to default credentials when secrets.toml not configured."""
        from admin.app import show_login_form

        with patch("admin.app.st") as mock_st:
            mock_form = Mock()
            mock_st.form.return_value.__enter__.return_value = mock_form
            mock_st.session_state = {}

            mock_st.text_input.side_effect = ["admin", "admin"]
            mock_st.form_submit_button.return_value = True

            # Simulate missing secrets
            mock_st.secrets.get.side_effect = Exception("No secrets")
            mock_st.rerun = Mock()

            show_login_form()

            # Should accept default admin/admin
            assert mock_st.session_state["authentication_status"] is True
            assert mock_st.session_state["username"] == "admin"
            mock_st.warning.assert_called()  # Warning about default credentials

    def test_default_credentials_rejected_when_incorrect(self):
        """Test default credentials rejected if not exactly admin/admin."""
        from admin.app import show_login_form

        with patch("admin.app.st") as mock_st:
            mock_form = Mock()
            mock_st.form.return_value.__enter__.return_value = mock_form
            mock_st.session_state = {}

            mock_st.text_input.side_effect = ["admin", "wrongpass"]
            mock_st.form_submit_button.return_value = True

            mock_st.secrets.get.side_effect = Exception("No secrets")

            show_login_form()

            mock_st.error.assert_called()


class TestLogoutFlow:
    """Test logout functionality."""

    @patch("admin.app.st")
    def test_logout_clears_session_state(self, mock_st):
        """Test logout button clears authentication state."""
        from admin.app import show_header

        # Simulate authenticated user clicking logout
        mock_st.session_state = {
            "authentication_status": True,
            "username": "testuser",
            "name": "Test User"
        }
        mock_st.button.return_value = True  # Logout button clicked
        mock_st.rerun = Mock()

        # Create context manager mocks for columns
        col1_mock = Mock()
        col1_mock.__enter__ = Mock(return_value=col1_mock)
        col1_mock.__exit__ = Mock(return_value=False)

        col2_mock = Mock()
        col2_mock.__enter__ = Mock(return_value=col2_mock)
        col2_mock.__exit__ = Mock(return_value=False)

        mock_st.columns.return_value = [col1_mock, col2_mock]

        show_header()

        # Verify session state cleared
        assert mock_st.session_state["authentication_status"] is False
        mock_st.rerun.assert_called_once()
