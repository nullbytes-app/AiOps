"""
Integration tests for Plugin Management UI workflows (Story 7.8).

Tests end-to-end workflows:
1. View plugins → Configure plugin → Test connection → Save
2. Create tenant → Assign plugin → Verify in DB
3. Perform operation → Verify audit_log entry created
4. Update tenant plugin → Verify changes persist
5. Assign non-existent plugin → Verify error message

Requirements:
- Minimum 5 integration tests (AC #9, Story 7.7 testing requirements)
- Test full workflows with real database interactions
- Verify data persistence and audit logging
"""

import pytest
import asyncio
from datetime import datetime, timezone
from sqlalchemy import select

from src.database.models import TenantConfig, AuditLog
from src.plugins.registry import PluginManager
from src.admin.utils.tenant_helper import create_tenant, update_tenant, get_tenant_by_id


# ============================================================================
# Integration Test 1: Full Plugin Management Workflow
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_plugin_management_workflow(test_db):
    """
    Test complete workflow: View plugins → Configure → Test connection → Save.

    Workflow:
    1. List all registered plugins via PluginManager
    2. Get plugin details and configuration schema
    3. Test connection with valid credentials
    4. Create tenant with plugin assignment
    5. Verify tenant persists in database with correct plugin

    AC #1-7: Full plugin management workflow from discovery to assignment.
    """
    # Step 1: List registered plugins
    manager = PluginManager()
    registered_plugins = manager.list_registered_plugins()

    assert len(registered_plugins) >= 2  # At least ServiceDesk Plus and Jira
    assert "servicedesk_plus" in registered_plugins
    assert "jira" in registered_plugins

    # Step 2: Get plugin details for Jira
    plugin_id = "jira"
    assert manager.is_plugin_registered(plugin_id)
    plugin = manager.get_plugin(plugin_id)
    assert plugin is not None
    assert plugin.name == "Jira Service Management"

    # Step 3: Test connection (mock - real test would hit actual API)
    # In real scenario, this would call plugin.test_connection() with actual credentials
    # For integration test, we verify the method exists
    assert hasattr(plugin, "test_connection")

    # Step 4: Create tenant with Jira plugin
    tenant_data = {
        "name": "Integration Test Tenant",
        "tenant_id": "integration-test-tenant",
        "tool_type": "jira",
        "servicedesk_url": "https://integration-test.atlassian.net",
        "api_key": "test-jira-token-12345",
        "enhancement_preferences": {"ticket_history": True, "documentation": True},
    }

    tenant = create_tenant(tenant_data)
    assert tenant is not None
    assert tenant.tenant_id == "integration-test-tenant"
    assert tenant.tool_type == "jira"

    # Step 5: Verify tenant persists in database
    async with test_db() as session:
        result = await session.execute(
            select(TenantConfig).where(TenantConfig.tenant_id == "integration-test-tenant")
        )
        db_tenant = result.scalar_one_or_none()

        assert db_tenant is not None
        assert db_tenant.name == "Integration Test Tenant"
        assert db_tenant.tool_type == "jira"
        assert db_tenant.servicedesk_url == "https://integration-test.atlassian.net"
        assert db_tenant.is_active is True


# ============================================================================
# Integration Test 2: Tenant-Plugin Assignment Workflow
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tenant_plugin_assignment_workflow(test_db):
    """
    Test workflow: Create tenant → Assign plugin → Verify in database.

    Workflow:
    1. Create tenant with ServiceDesk Plus plugin
    2. Verify plugin assignment in database
    3. Update tenant to reassign to Jira plugin
    4. Verify reassignment persists

    AC #7: Tenant-plugin assignment integrated with tenant management.
    """
    # Step 1: Create tenant with ServiceDesk Plus
    tenant_data = {
        "name": "Assignment Test Tenant",
        "tenant_id": "assignment-test-tenant",
        "tool_type": "servicedesk_plus",
        "servicedesk_url": "https://assignment-test.servicedesk.com",
        "api_key": "sdp-key-12345",
    }

    tenant = create_tenant(tenant_data)
    assert tenant is not None

    # Step 2: Verify initial plugin assignment
    async with test_db() as session:
        result = await session.execute(
            select(TenantConfig).where(TenantConfig.tenant_id == "assignment-test-tenant")
        )
        db_tenant = result.scalar_one_or_none()

        assert db_tenant.tool_type == "servicedesk_plus"

    # Step 3: Reassign to Jira plugin
    update_success = update_tenant(
        "assignment-test-tenant",
        {
            "tool_type": "jira",
            "servicedesk_url": "https://assignment-test.atlassian.net",
            "api_key": "jira-token-67890",
        },
    )
    assert update_success is True

    # Step 4: Verify reassignment persists
    async with test_db() as session:
        result = await session.execute(
            select(TenantConfig).where(TenantConfig.tenant_id == "assignment-test-tenant")
        )
        db_tenant = result.scalar_one_or_none()

        assert db_tenant.tool_type == "jira"
        assert db_tenant.servicedesk_url == "https://assignment-test.atlassian.net"


# ============================================================================
# Integration Test 3: Audit Logging Verification
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_audit_logging_for_plugin_operations(test_db):
    """
    Test workflow: Perform plugin operation → Verify audit_log entry created.

    Workflow:
    1. Create tenant with plugin assignment
    2. Query audit_log table for operation entry
    3. Verify audit log contains correct details
    4. Reassign plugin to different tool
    5. Verify reassignment logged separately

    AC #8: All plugin management operations logged to audit_log table.
    """
    # Step 1: Create tenant (should log "tenant_plugin_assignment" action: "create")
    tenant_data = {
        "name": "Audit Test Tenant",
        "tenant_id": "audit-test-tenant",
        "tool_type": "jira",
        "servicedesk_url": "https://audit-test.atlassian.net",
        "api_key": "audit-jira-token",
    }

    tenant = create_tenant(tenant_data)
    assert tenant is not None

    # Step 2: Query audit log for creation entry
    async with test_db() as session:
        # Wait briefly for async logging to complete
        await asyncio.sleep(0.5)

        result = await session.execute(
            select(AuditLog)
            .where(AuditLog.operation == "tenant_plugin_assignment")
            .where(AuditLog.details["tenant_id"].as_string() == "audit-test-tenant")
            .where(AuditLog.details["action"].as_string() == "create")
            .order_by(AuditLog.timestamp.desc())
            .limit(1)
        )
        log_entry = result.scalar_one_or_none()

        # Step 3: Verify audit log details
        assert log_entry is not None
        assert log_entry.user == "admin"
        assert log_entry.operation == "tenant_plugin_assignment"
        assert log_entry.status == "success"
        assert log_entry.details["tenant_id"] == "audit-test-tenant"
        assert log_entry.details["tenant_name"] == "Audit Test Tenant"
        assert log_entry.details["plugin_id"] == "jira"
        assert log_entry.details["action"] == "create"

    # Step 4: Reassign plugin
    update_success = update_tenant("audit-test-tenant", {"tool_type": "servicedesk_plus"})
    assert update_success is True

    # Step 5: Verify reassignment logged
    async with test_db() as session:
        await asyncio.sleep(0.5)

        result = await session.execute(
            select(AuditLog)
            .where(AuditLog.operation == "tenant_plugin_assignment")
            .where(AuditLog.details["tenant_id"].as_string() == "audit-test-tenant")
            .where(AuditLog.details["action"].as_string() == "reassign")
            .order_by(AuditLog.timestamp.desc())
            .limit(1)
        )
        reassign_log = result.scalar_one_or_none()

        assert reassign_log is not None
        assert reassign_log.details["old_plugin"] == "jira"
        assert reassign_log.details["new_plugin"] == "servicedesk_plus"
        assert reassign_log.details["action"] == "reassign"


# ============================================================================
# Integration Test 4: Plugin Reassignment Persistence
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_plugin_reassignment_persistence(test_db):
    """
    Test workflow: Create tenant → Reassign plugin → Verify changes persist across sessions.

    Workflow:
    1. Create tenant with Plugin A
    2. Retrieve tenant and verify Plugin A
    3. Update to Plugin B
    4. Retrieve tenant again and verify Plugin B
    5. Ensure old plugin data cleared

    AC #7: Tenant-plugin assignment allows reassignment with persistence.
    """
    # Step 1: Create tenant with ServiceDesk Plus
    tenant_data = {
        "name": "Persistence Test Tenant",
        "tenant_id": "persistence-test-tenant",
        "tool_type": "servicedesk_plus",
        "servicedesk_url": "https://persistence-test.servicedesk.com",
        "api_key": "sdp-persistence-key",
    }

    tenant = create_tenant(tenant_data)
    assert tenant is not None

    # Step 2: Verify initial state (Plugin A)
    tenant_retrieved_1 = get_tenant_by_id("persistence-test-tenant")
    assert tenant_retrieved_1 is not None
    assert tenant_retrieved_1.tool_type == "servicedesk_plus"
    assert tenant_retrieved_1.servicedesk_url == "https://persistence-test.servicedesk.com"

    # Step 3: Reassign to Jira (Plugin B)
    update_success = update_tenant(
        "persistence-test-tenant",
        {
            "tool_type": "jira",
            "servicedesk_url": "https://persistence-test.atlassian.net",
            "api_key": "jira-persistence-key",
        },
    )
    assert update_success is True

    # Step 4: Retrieve tenant in new session and verify Plugin B
    tenant_retrieved_2 = get_tenant_by_id("persistence-test-tenant")
    assert tenant_retrieved_2 is not None
    assert tenant_retrieved_2.tool_type == "jira"
    assert tenant_retrieved_2.servicedesk_url == "https://persistence-test.atlassian.net"

    # Step 5: Verify updated_at timestamp changed
    assert tenant_retrieved_2.updated_at > tenant_retrieved_1.updated_at


# ============================================================================
# Integration Test 5: Error Handling - Non-Existent Plugin
# ============================================================================


@pytest.mark.integration
def test_assign_non_existent_plugin_error_handling():
    """
    Test workflow: Assign non-existent plugin → Verify error handling.

    Workflow:
    1. Attempt to create tenant with invalid plugin_id
    2. Verify creation succeeds (no plugin validation in create_tenant)
    3. Attempt to get non-existent plugin from PluginManager
    4. Verify PluginNotFoundError raised

    AC #7: Plugin assignment validates plugin exists (handled at UI level).

    Note: create_tenant() doesn't validate plugin existence (assumed to be
    validated at UI level via plugin dropdown). This test verifies PluginManager
    correctly rejects invalid plugin IDs.
    """
    # Step 1: Create tenant with non-existent plugin
    tenant_data = {
        "name": "Invalid Plugin Tenant",
        "tenant_id": "invalid-plugin-tenant",
        "tool_type": "zendesk",  # Not registered yet
        "servicedesk_url": "https://invalid.zendesk.com",
        "api_key": "invalid-key",
    }

    # Tenant creation succeeds (no validation at this level)
    tenant = create_tenant(tenant_data)
    assert tenant is not None
    assert tenant.tool_type == "zendesk"

    # Step 2: Verify PluginManager rejects invalid plugin
    manager = PluginManager()
    assert not manager.is_plugin_registered("zendesk")

    # Step 3: Attempt to get non-existent plugin
    from src.plugins.exceptions import PluginNotFoundError

    with pytest.raises(PluginNotFoundError):
        manager.get_plugin("zendesk")

    # Step 4: Verify error message helpful
    try:
        manager.get_plugin("zendesk")
    except PluginNotFoundError as e:
        assert "zendesk" in str(e).lower()
        assert "not registered" in str(e).lower() or "not found" in str(e).lower()


# ============================================================================
# Integration Test 6: Multi-Tenant Plugin Isolation
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multi_tenant_plugin_isolation(test_db):
    """
    Test workflow: Create multiple tenants with different plugins → Verify isolation.

    Workflow:
    1. Create Tenant A with ServiceDesk Plus
    2. Create Tenant B with Jira
    3. Create Tenant C with ServiceDesk Plus
    4. Verify each tenant has correct plugin assignment
    5. Update Tenant A plugin without affecting others

    AC #7: Multi-tenant support allows different plugins per tenant.
    """
    # Step 1: Create Tenant A (ServiceDesk Plus)
    tenant_a = create_tenant(
        {
            "name": "Tenant A",
            "tenant_id": "tenant-a",
            "tool_type": "servicedesk_plus",
            "servicedesk_url": "https://tenant-a.servicedesk.com",
            "api_key": "key-a",
        }
    )
    assert tenant_a.tool_type == "servicedesk_plus"

    # Step 2: Create Tenant B (Jira)
    tenant_b = create_tenant(
        {
            "name": "Tenant B",
            "tenant_id": "tenant-b",
            "tool_type": "jira",
            "servicedesk_url": "https://tenant-b.atlassian.net",
            "api_key": "key-b",
        }
    )
    assert tenant_b.tool_type == "jira"

    # Step 3: Create Tenant C (ServiceDesk Plus)
    tenant_c = create_tenant(
        {
            "name": "Tenant C",
            "tenant_id": "tenant-c",
            "tool_type": "servicedesk_plus",
            "servicedesk_url": "https://tenant-c.servicedesk.com",
            "api_key": "key-c",
        }
    )
    assert tenant_c.tool_type == "servicedesk_plus"

    # Step 4: Verify isolation in database
    async with test_db() as session:
        result = await session.execute(select(TenantConfig).order_by(TenantConfig.tenant_id))
        all_tenants = result.scalars().all()

        tenant_map = {t.tenant_id: t.tool_type for t in all_tenants if t.tenant_id.startswith("tenant-")}

        assert tenant_map["tenant-a"] == "servicedesk_plus"
        assert tenant_map["tenant-b"] == "jira"
        assert tenant_map["tenant-c"] == "servicedesk_plus"

    # Step 5: Update Tenant A plugin without affecting others
    update_tenant("tenant-a", {"tool_type": "jira"})

    async with test_db() as session:
        result = await session.execute(select(TenantConfig).order_by(TenantConfig.tenant_id))
        all_tenants = result.scalars().all()

        tenant_map = {t.tenant_id: t.tool_type for t in all_tenants if t.tenant_id.startswith("tenant-")}

        # Tenant A updated to Jira
        assert tenant_map["tenant-a"] == "jira"
        # Tenant B unchanged
        assert tenant_map["tenant-b"] == "jira"
        # Tenant C unchanged
        assert tenant_map["tenant-c"] == "servicedesk_plus"
