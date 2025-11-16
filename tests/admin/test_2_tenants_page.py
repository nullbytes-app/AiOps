"""
Unit tests for 2_Tenants.py page - Tenant Management UI.

Tests the serialization fix for load_tenants() to ensure
SQLAlchemy models are properly converted to dictionaries
for Streamlit caching.
"""

import importlib
import pickle
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from database.models import TenantConfig

# Import the module with a numeric prefix using importlib
tenants_module = importlib.import_module("admin.pages.2_Tenants")
load_tenants = tenants_module.load_tenants
show_tenant_list_table = tenants_module.show_tenant_list_table


@pytest.fixture
def mock_tenants():
    """Create mock TenantConfig objects for testing."""
    tenant1 = MagicMock(spec=TenantConfig)
    tenant1.id = 1
    tenant1.tenant_id = "test-tenant-1"
    tenant1.name = "Test Tenant 1"
    tenant1.tool_type = "servicedesk_plus"
    tenant1.servicedesk_url = "https://test1.example.com"
    tenant1.is_active = True
    tenant1.created_at = datetime(2025, 1, 1, 12, 0, 0)
    tenant1.updated_at = datetime(2025, 1, 2, 12, 0, 0)
    tenant1.enhancement_preferences = {"priority": "high"}

    tenant2 = MagicMock(spec=TenantConfig)
    tenant2.id = 2
    tenant2.tenant_id = "test-tenant-2"
    tenant2.name = "Test Tenant 2"
    tenant2.tool_type = None
    tenant2.servicedesk_url = "https://test2.example.com"
    tenant2.is_active = False
    tenant2.created_at = datetime(2025, 1, 3, 12, 0, 0)
    tenant2.updated_at = datetime(2025, 1, 4, 12, 0, 0)
    tenant2.enhancement_preferences = {}

    return [tenant1, tenant2]


def test_load_tenants_returns_serializable_data(mock_tenants):
    """Test that load_tenants returns pickle-serializable dictionaries."""
    with patch.object(tenants_module, "get_all_tenants", return_value=mock_tenants):
        # Clear cache to ensure fresh call
        load_tenants.clear()

        # Load tenants
        result = load_tenants(include_inactive=True)

        # Verify result is a list of dictionaries
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(tenant, dict) for tenant in result)

        # Verify serialization works (no exception)
        try:
            pickled = pickle.dumps(result)
            unpickled = pickle.loads(pickled)
            assert unpickled == result
        except Exception as e:
            pytest.fail(f"Failed to serialize tenant data: {e}")


def test_load_tenants_includes_all_required_fields(mock_tenants):
    """Test that all required fields are present in serialized tenants."""
    with patch.object(tenants_module, "get_all_tenants", return_value=mock_tenants):
        load_tenants.clear()
        result = load_tenants(include_inactive=True)

        # Check first tenant has all required fields
        tenant = result[0]
        required_fields = [
            "id",
            "tenant_id",
            "name",
            "tool_type",
            "servicedesk_url",
            "is_active",
            "created_at",
            "updated_at",
            "enhancement_preferences",
        ]

        for field in required_fields:
            assert field in tenant, f"Missing required field: {field}"

        # Verify values match
        assert tenant["tenant_id"] == "test-tenant-1"
        assert tenant["name"] == "Test Tenant 1"
        assert tenant["tool_type"] == "servicedesk_plus"
        assert tenant["is_active"] is True


def test_load_tenants_handles_none_values(mock_tenants):
    """Test that load_tenants handles None values properly."""
    with patch.object(tenants_module, "get_all_tenants", return_value=mock_tenants):
        load_tenants.clear()
        result = load_tenants(include_inactive=True)

        # Check second tenant with None tool_type
        tenant = result[1]
        assert tenant["tool_type"] is None
        assert tenant["is_active"] is False

        # Verify it's still serializable
        try:
            pickle.dumps(tenant)
        except Exception as e:
            pytest.fail(f"Failed to serialize tenant with None values: {e}")


def test_show_tenant_list_table_with_dict_input():
    """Test that show_tenant_list_table works with dictionary input."""
    tenants = [
        {
            "name": "Test Tenant",
            "tenant_id": "test-123",
            "tool_type": "servicedesk_plus",
            "servicedesk_url": "https://test.example.com",
            "is_active": True,
            "created_at": datetime(2025, 1, 1, 12, 0, 0),
        }
    ]

    # This should not raise an exception
    with patch("streamlit.dataframe"):
        try:
            show_tenant_list_table(tenants)
        except (KeyError, AttributeError) as e:
            pytest.fail(f"show_tenant_list_table failed with dict input: {e}")


def test_load_tenants_caching():
    """Test that load_tenants caching works with serializable data."""
    # Create a proper mock with all attributes as simple types
    mock_tenant = MagicMock(spec=TenantConfig)
    mock_tenant.id = 1
    mock_tenant.tenant_id = "test-123"
    mock_tenant.name = "Test"
    mock_tenant.tool_type = "test_type"
    mock_tenant.servicedesk_url = "https://test.com"
    mock_tenant.is_active = True
    mock_tenant.created_at = datetime(2025, 1, 1, 12, 0, 0)
    mock_tenant.updated_at = datetime(2025, 1, 1, 12, 0, 0)
    mock_tenant.enhancement_preferences = {}

    mock_tenants = [mock_tenant]

    with patch.object(tenants_module, "get_all_tenants", return_value=mock_tenants) as mock_get:
        load_tenants.clear()

        # First call
        result1 = load_tenants(include_inactive=False)
        assert mock_get.call_count == 1

        # Second call (should use cache)
        result2 = load_tenants(include_inactive=False)
        assert mock_get.call_count == 1  # Not called again

        # Results should be equal
        assert result1 == result2
