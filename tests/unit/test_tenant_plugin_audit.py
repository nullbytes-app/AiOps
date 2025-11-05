"""
Unit tests for tenant plugin assignment audit logging (Story 7.8).

Tests cover:
- Audit logging during tenant creation with plugin assignment
- Audit logging during tenant plugin reassignment
- Audit log entry structure and content

Requirements:
- Test audit log creation for plugin operations (AC #8)
- Verify audit log contains correct user, operation, details, status
"""

import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone

from src.admin.utils.tenant_helper import create_tenant, update_tenant
from src.database.models import TenantConfig


@pytest.fixture
def tenant_data():
    """Sample tenant data for testing."""
    return {
        "name": "Test Tenant",
        "tenant_id": "test-tenant",
        "tool_type": "jira",
        "servicedesk_url": "https://test.atlassian.net",
        "api_key": "test-api-key-12345",
        "enhancement_preferences": {"ticket_history": True},
    }


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)
    return session


# ============================================================================
# Tenant Creation Audit Logging Tests (AC #8)
# ============================================================================


@pytest.mark.unit
def test_create_tenant_logs_plugin_assignment(tenant_data, mock_db_session):
    """
    Test create_tenant() logs plugin assignment to audit log.

    AC #8: All plugin management operations logged to audit_log table.
    """
    with patch("src.admin.utils.tenant_helper.get_db_session", return_value=mock_db_session):
        with patch("src.admin.utils.tenant_helper.encrypt_field", return_value="encrypted"):
            with patch("admin.utils.operations_audit.log_operation") as mock_log:
                result = create_tenant(tenant_data)

                # Verify tenant created
                assert result is not None

                # Verify audit log called
                mock_log.assert_called_once()
                call_args = mock_log.call_args[1]

                assert call_args["user"] == "admin"
                assert call_args["operation"] == "tenant_plugin_assignment"
                assert call_args["details"]["tenant_id"] == "test-tenant"
                assert call_args["details"]["tenant_name"] == "Test Tenant"
                assert call_args["details"]["plugin_id"] == "jira"
                assert call_args["details"]["action"] == "create"
                assert call_args["status"] == "success"


@pytest.mark.unit
def test_create_tenant_logs_failure_on_duplicate(tenant_data, mock_db_session):
    """
    Test create_tenant() logs failure when tenant_id already exists.

    AC #8: Log failures to audit log with error details.
    """
    from sqlalchemy.exc import IntegrityError

    with patch("src.admin.utils.tenant_helper.get_db_session", return_value=mock_db_session):
        with patch("src.admin.utils.tenant_helper.encrypt_field", return_value="encrypted"):
            # Simulate IntegrityError (duplicate key)
            mock_db_session.flush.side_effect = IntegrityError("duplicate", None, None)

            with patch("admin.utils.operations_audit.log_operation") as mock_log:
                with pytest.raises(IntegrityError):
                    create_tenant(tenant_data)

                # Verify audit log called with failure status
                mock_log.assert_called_once()
                call_args = mock_log.call_args[1]

                assert call_args["operation"] == "tenant_plugin_assignment"
                assert call_args["details"]["tenant_id"] == "test-tenant"
                assert call_args["details"]["error"] == "duplicate_tenant_id"
                assert call_args["status"] == "failure"


@pytest.mark.unit
def test_create_tenant_defaults_to_servicedesk_plus_if_no_tool_type(mock_db_session):
    """
    Test create_tenant() defaults to servicedesk_plus if tool_type not provided.

    Edge case: Backward compatibility with tenants created before multi-tool support.
    """
    tenant_data = {
        "name": "Legacy Tenant",
        "tenant_id": "legacy-tenant",
        # No tool_type provided
        "servicedesk_url": "https://legacy.servicedesk.com",
        "api_key": "legacy-key",
    }

    with patch("src.admin.utils.tenant_helper.get_db_session", return_value=mock_db_session):
        with patch("src.admin.utils.tenant_helper.encrypt_field", return_value="encrypted"):
            with patch("admin.utils.operations_audit.log_operation") as mock_log:
                result = create_tenant(tenant_data)

                # Verify tenant created with default tool_type
                tenant_call = mock_db_session.add.call_args[0][0]
                assert tenant_call.tool_type == "servicedesk_plus"

                # Verify audit log records default plugin
                call_args = mock_log.call_args[1]
                assert call_args["details"]["plugin_id"] == "servicedesk_plus"


# ============================================================================
# Tenant Update Audit Logging Tests (AC #8)
# ============================================================================


@pytest.mark.unit
def test_update_tenant_logs_plugin_reassignment(mock_db_session):
    """
    Test update_tenant() logs plugin reassignment when tool_type changes.

    AC #7: Tenant-plugin assignment interface supports reassignment.
    AC #8: Reassignment logged to audit log.
    """
    # Mock existing tenant with old plugin
    existing_tenant = MagicMock(spec=TenantConfig)
    existing_tenant.tool_type = "servicedesk_plus"

    mock_db_session.query.return_value.filter.return_value.first.return_value = (
        existing_tenant
    )

    updates = {
        "tool_type": "jira",  # Plugin changed
        "name": "Updated Tenant",
    }

    with patch("src.admin.utils.tenant_helper.get_db_session", return_value=mock_db_session):
        with patch("admin.utils.operations_audit.log_operation") as mock_log:
            result = update_tenant("test-tenant", updates)

            # Verify update succeeded
            assert result is True

            # Verify audit log called for plugin reassignment
            mock_log.assert_called_once()
            call_args = mock_log.call_args[1]

            assert call_args["user"] == "admin"
            assert call_args["operation"] == "tenant_plugin_assignment"
            assert call_args["details"]["tenant_id"] == "test-tenant"
            assert call_args["details"]["old_plugin"] == "servicedesk_plus"
            assert call_args["details"]["new_plugin"] == "jira"
            assert call_args["details"]["action"] == "reassign"
            assert call_args["status"] == "success"


@pytest.mark.unit
def test_update_tenant_does_not_log_if_plugin_unchanged(mock_db_session):
    """
    Test update_tenant() does NOT log if tool_type not changed.

    Edge case: Only non-plugin fields updated (e.g., name, URL).
    """
    # Mock existing tenant
    existing_tenant = MagicMock(spec=TenantConfig)
    existing_tenant.tool_type = "jira"

    mock_db_session.query.return_value.filter.return_value.first.return_value = (
        existing_tenant
    )

    updates = {
        "name": "Updated Name",  # No tool_type change
        "servicedesk_url": "https://new.url.com",
    }

    with patch("src.admin.utils.tenant_helper.get_db_session", return_value=mock_db_session):
        with patch("admin.utils.operations_audit.log_operation") as mock_log:
            result = update_tenant("test-tenant", updates)

            # Verify update succeeded
            assert result is True

            # Verify audit log NOT called (plugin unchanged)
            mock_log.assert_not_called()


@pytest.mark.unit
def test_update_tenant_logs_plugin_same_value_change(mock_db_session):
    """
    Test update_tenant() does NOT log if tool_type set to same value.

    Edge case: tool_type in updates but value identical to existing.
    """
    # Mock existing tenant
    existing_tenant = MagicMock(spec=TenantConfig)
    existing_tenant.tool_type = "jira"

    mock_db_session.query.return_value.filter.return_value.first.return_value = (
        existing_tenant
    )

    updates = {
        "tool_type": "jira",  # Same as existing - no change
        "name": "Updated Name",
    }

    with patch("src.admin.utils.tenant_helper.get_db_session", return_value=mock_db_session):
        with patch("admin.utils.operations_audit.log_operation") as mock_log:
            result = update_tenant("test-tenant", updates)

            # Verify update succeeded
            assert result is True

            # Verify audit log NOT called (plugin unchanged)
            mock_log.assert_not_called()


@pytest.mark.unit
def test_update_tenant_logs_failure_on_error(mock_db_session):
    """
    Test update_tenant() logs failure when update fails.

    AC #8: Log failures to audit log.
    """
    # Mock existing tenant
    existing_tenant = MagicMock(spec=TenantConfig)
    existing_tenant.tool_type = "servicedesk_plus"

    mock_db_session.query.return_value.filter.return_value.first.return_value = (
        existing_tenant
    )

    # Simulate database error
    mock_db_session.flush.side_effect = Exception("Database connection lost")

    updates = {"tool_type": "jira"}

    with patch("src.admin.utils.tenant_helper.get_db_session", return_value=mock_db_session):
        with patch("admin.utils.operations_audit.log_operation") as mock_log:
            result = update_tenant("test-tenant", updates)

            # Verify update failed
            assert result is False

            # Verify audit log called with failure status
            mock_log.assert_called_once()
            call_args = mock_log.call_args[1]

            assert call_args["operation"] == "tenant_plugin_assignment"
            assert call_args["details"]["tenant_id"] == "test-tenant"
            assert "error" in call_args["details"]
            assert call_args["details"]["action"] == "update"
            assert call_args["status"] == "failure"


@pytest.mark.unit
def test_update_tenant_returns_false_if_tenant_not_found(mock_db_session):
    """
    Test update_tenant() returns False if tenant doesn't exist.

    Edge case: Update non-existent tenant.
    """
    # Mock no tenant found
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    updates = {"tool_type": "jira"}

    with patch("src.admin.utils.tenant_helper.get_db_session", return_value=mock_db_session):
        with patch("admin.utils.operations_audit.log_operation") as mock_log:
            result = update_tenant("non-existent-tenant", updates)

            # Verify update failed
            assert result is False

            # Verify audit log NOT called (tenant not found before operation)
            mock_log.assert_not_called()


# ============================================================================
# Audit Log Entry Structure Tests
# ============================================================================


@pytest.mark.unit
def test_audit_log_entry_has_required_fields(tenant_data, mock_db_session):
    """
    Test audit log entry contains all required fields.

    Verifies: user, operation, details (JSON), status, timestamp.
    """
    with patch("src.admin.utils.tenant_helper.get_db_session", return_value=mock_db_session):
        with patch("src.admin.utils.tenant_helper.encrypt_field", return_value="encrypted"):
            with patch("admin.utils.operations_audit.log_operation") as mock_log:
                create_tenant(tenant_data)

                # Verify audit log called
                call_args = mock_log.call_args[1]

                # Required fields
                assert "user" in call_args
                assert "operation" in call_args
                assert "details" in call_args
                assert "status" in call_args

                # Details should be a dict (JSON-serializable)
                assert isinstance(call_args["details"], dict)


@pytest.mark.unit
def test_audit_log_details_contain_plugin_info(tenant_data, mock_db_session):
    """
    Test audit log details include plugin_id for tenant operations.

    Ensures audit trail can track which plugins are assigned to tenants.
    """
    with patch("src.admin.utils.tenant_helper.get_db_session", return_value=mock_db_session):
        with patch("src.admin.utils.tenant_helper.encrypt_field", return_value="encrypted"):
            with patch("admin.utils.operations_audit.log_operation") as mock_log:
                create_tenant(tenant_data)

                call_args = mock_log.call_args[1]
                details = call_args["details"]

                # Plugin-specific fields in details
                assert "plugin_id" in details or "tool_type" in details["tenant_id"]
                assert details["action"] in ["create", "reassign", "update"]
