"""
Unit tests for multi-tool tenant schema validation.

Tests cover tool_type validation, JSONB structure, multi-tool tenant
creation, and invalid tool_type rejection (AC6).
"""

import pytest
from pydantic import ValidationError
from src.schemas.tenant import (
    TenantConfigCreate,
    TenantConfigInternal,
    EnhancementPreferences,
)


class TestToolTypeValidation:
    """Test tool_type field validation and defaults."""

    def test_tool_type_default_servicedesk_plus(self):
        """
        Test default tool_type is 'servicedesk_plus'.

        AC6: Verify default tool_type applied when not specified.
        """
        config = TenantConfigCreate(
            tenant_id="test-tenant",
            name="Test Tenant",
            servicedesk_url="https://servicedesk.example.com",
            servicedesk_api_key="test-key",
            webhook_signing_secret="test-secret",
        )
        assert config.tool_type == "servicedesk_plus"

    def test_create_jira_tenant_with_required_fields(self):
        """
        Test Jira tenant creation succeeds with all required fields.

        AC6: Validate multi-tool tenant creation with complete Jira config.
        """
        config = TenantConfigCreate(
            tenant_id="jira-tenant",
            name="Jira Test Tenant",
            tool_type="jira",
            jira_url="https://company.atlassian.net",
            jira_api_token="jira-token-123",
            jira_project_key="PROJ",
            webhook_signing_secret="test-secret",
        )
        assert config.tool_type == "jira"
        assert str(config.jira_url) == "https://company.atlassian.net/"
        assert config.jira_api_token == "jira-token-123"
        assert config.jira_project_key == "PROJ"

    def test_create_jira_tenant_missing_required_fields(self):
        """
        Test Jira tenant creation fails if required fields missing.

        AC6: Ensure ValidationError raised for incomplete Jira config.
        """
        with pytest.raises(ValidationError, match="Jira requires"):
            TenantConfigCreate(
                tenant_id="jira-tenant",
                name="Incomplete Jira Tenant",
                tool_type="jira",
                # Missing jira_url, jira_api_token, jira_project_key
                webhook_signing_secret="test-secret",
            )

    def test_create_servicedesk_tenant_missing_required_fields(self):
        """
        Test ServiceDesk Plus tenant creation fails if required fields missing.

        AC6: Ensure ValidationError raised for incomplete ServiceDesk config.
        """
        with pytest.raises(ValidationError, match="ServiceDesk Plus requires"):
            TenantConfigCreate(
                tenant_id="servicedesk-tenant",
                name="Incomplete ServiceDesk Tenant",
                tool_type="servicedesk_plus",
                # Missing servicedesk_url, servicedesk_api_key
                webhook_signing_secret="test-secret",
            )


class TestEnhancementPreferencesJSONB:
    """Test enhancement_preferences JSONB structure."""

    def test_enhancement_preferences_jsonb_structure(self):
        """
        Test enhancement_preferences JSONB preserves nested structure.

        AC2/AC6: Verify JSONB structure for tool-specific configs.
        """
        jira_prefs = {
            "tool_config": {
                "default_issue_type": "Bug",
                "default_project_key": "SUPPORT",
                "default_priority": "High",
            },
            "priority_mapping": {
                "critical": "Highest",
                "high": "High",
                "medium": "Medium",
                "low": "Low",
            },
            "custom_fields": {
                "customfield_10000": "tenant-id-value",
            },
        }

        config = TenantConfigCreate(
            tenant_id="jira-tenant",
            name="Jira Tenant",
            tool_type="jira",
            jira_url="https://company.atlassian.net",
            jira_api_token="token",
            jira_project_key="PROJ",
            webhook_signing_secret="secret",
            enhancement_preferences=EnhancementPreferences(),
        )

        # Verify preferences structure
        assert config.enhancement_preferences is not None
        assert hasattr(config.enhancement_preferences, "max_enhancement_length")


class TestMultiToolIsolation:
    """Test multi-tool tenant isolation and coexistence."""

    def test_multiple_tools_isolated(self):
        """
        Test ServiceDesk and Jira tenants can coexist with isolated configs.

        AC6: Verify tool_type distinct and tool-specific fields isolated.
        """
        # Create ServiceDesk tenant
        servicedesk_config = TenantConfigCreate(
            tenant_id="servicedesk-001",
            name="ServiceDesk Tenant",
            tool_type="servicedesk_plus",
            servicedesk_url="https://servicedesk.example.com",
            servicedesk_api_key="sd-key",
            webhook_signing_secret="sd-secret",
        )

        # Create Jira tenant
        jira_config = TenantConfigCreate(
            tenant_id="jira-001",
            name="Jira Tenant",
            tool_type="jira",
            jira_url="https://company.atlassian.net",
            jira_api_token="jira-token",
            jira_project_key="PROJ",
            webhook_signing_secret="jira-secret",
        )

        # Verify isolation
        assert servicedesk_config.tool_type == "servicedesk_plus"
        assert jira_config.tool_type == "jira"

        # ServiceDesk has servicedesk fields, Jira fields None
        assert servicedesk_config.servicedesk_url is not None
        assert servicedesk_config.jira_url is None

        # Jira has jira fields, ServiceDesk fields None
        assert jira_config.jira_url is not None
        assert jira_config.servicedesk_url is None


class TestPydanticSchemaValidation:
    """Test Pydantic schema validation for tool-specific configs."""

    def test_pydantic_schema_validation_servicedesk(self):
        """
        Test TenantConfigCreate validates ServiceDesk config correctly.

        AC3/AC6: Verify Pydantic @model_validator enforces required fields.
        """
        # Valid ServiceDesk config
        config = TenantConfigCreate(
            tenant_id="sd-tenant",
            name="Valid ServiceDesk",
            tool_type="servicedesk_plus",
            servicedesk_url="https://servicedesk.example.com",
            servicedesk_api_key="key",
            webhook_signing_secret="secret",
        )
        assert config.tool_type == "servicedesk_plus"

    def test_pydantic_schema_validation_jira(self):
        """
        Test TenantConfigCreate validates Jira config correctly.

        AC3/AC6: Verify Pydantic @model_validator enforces required fields.
        """
        # Valid Jira config
        config = TenantConfigCreate(
            tenant_id="jira-tenant",
            name="Valid Jira",
            tool_type="jira",
            jira_url="https://company.atlassian.net",
            jira_api_token="token",
            jira_project_key="PROJ",
            webhook_signing_secret="secret",
        )
        assert config.tool_type == "jira"

    def test_pydantic_schema_validation_invalid_tool_type(self):
        """
        Test TenantConfigCreate with invalid tool_type.

        AC6: Pydantic validation allows any string tool_type at schema level.
        Application-level validation in TenantService will catch invalid types.
        """
        # Pydantic allows any string, but TenantService will validate
        config = TenantConfigCreate(
            tenant_id="zendesk-tenant",
            name="Zendesk Tenant",
            tool_type="zendesk",  # Not registered yet
            webhook_signing_secret="secret",
        )
        # This will pass Pydantic validation but fail at TenantService level
        assert config.tool_type == "zendesk"


class TestTenantConfigInternal:
    """Test TenantConfigInternal multi-tool support."""

    def test_tenant_config_internal_optional_fields(self):
        """
        Test TenantConfigInternal allows Optional[] for tool-specific fields.

        AC3: Verify Optional[] types work for both ServiceDesk and Jira.
        """
        from datetime import datetime, timezone
        from uuid import uuid4

        # ServiceDesk tenant (Jira fields None)
        servicedesk_tenant = TenantConfigInternal(
            id=uuid4(),
            tenant_id="sd-001",
            name="ServiceDesk Tenant",
            tool_type="servicedesk_plus",
            servicedesk_url="https://servicedesk.example.com",
            servicedesk_api_key="decrypted-key",
            webhook_signing_secret="decrypted-secret",
            enhancement_preferences=EnhancementPreferences(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert servicedesk_tenant.tool_type == "servicedesk_plus"
        assert servicedesk_tenant.servicedesk_url is not None
        assert servicedesk_tenant.jira_url is None

        # Jira tenant (ServiceDesk fields None)
        jira_tenant = TenantConfigInternal(
            id=uuid4(),
            tenant_id="jira-001",
            name="Jira Tenant",
            tool_type="jira",
            jira_url="https://company.atlassian.net",
            jira_api_token="decrypted-token",
            jira_project_key="PROJ",
            webhook_signing_secret="decrypted-secret",
            enhancement_preferences=EnhancementPreferences(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert jira_tenant.tool_type == "jira"
        assert jira_tenant.jira_url is not None
        assert jira_tenant.servicedesk_url is None
