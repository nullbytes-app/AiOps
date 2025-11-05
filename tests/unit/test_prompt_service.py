"""
Unit tests for PromptService business logic.

Tests prompt versioning, template management, and variable substitution
with focus on multi-tenancy enforcement and edge cases.

Uses pytest with pytest-asyncio markers for async testing.
Mocks database session to test logic independently of actual database.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from src.services.prompt_service import PromptService
from src.schemas.agent import (
    PromptTemplateCreate,
    PromptVersionResponse,
    PromptVersionDetail,
    PromptTemplateResponse,
)


@pytest.fixture
def mock_db():
    """Create mock async database session."""
    return AsyncMock()


@pytest.fixture
def prompt_service(mock_db):
    """Create PromptService with mocked database."""
    return PromptService(mock_db)


@pytest.fixture
def sample_agent_id():
    """Sample agent UUID."""
    return uuid4()


@pytest.fixture
def sample_tenant_id():
    """Sample tenant ID."""
    return "tenant_test_123"


@pytest.fixture
def sample_prompt_text():
    """Sample system prompt."""
    return "You are a helpful AI assistant for {{tenant_name}}. Available tools: {{tools}}"


class TestPromptVersionManagement:
    """Tests for prompt version history operations."""

    @pytest.mark.asyncio
    async def test_get_prompt_versions_success(
        self, prompt_service, sample_agent_id, sample_tenant_id, mock_db
    ):
        """Test successful retrieval of prompt version history."""
        # Arrange
        mock_version_1 = MagicMock()
        mock_version_1.id = uuid4()
        mock_version_1.created_at = datetime.utcnow()
        mock_version_1.created_by = "admin@example.com"
        mock_version_1.description = "Version 1"
        mock_version_1.is_current = False

        mock_version_2 = MagicMock()
        mock_version_2.id = uuid4()
        mock_version_2.created_at = datetime.utcnow()
        mock_version_2.created_by = "admin@example.com"
        mock_version_2.description = "Version 2"
        mock_version_2.is_current = True

        # Mock agent exists
        mock_agent = MagicMock()
        mock_agent_result = AsyncMock()
        mock_agent_result.scalars.return_value.first.return_value = mock_agent

        # Mock versions query
        mock_versions_result = AsyncMock()
        mock_versions_result.scalars.return_value.all.return_value = [
            mock_version_2,
            mock_version_1,
        ]

        mock_db.execute = AsyncMock(
            side_effect=[mock_agent_result, mock_versions_result]
        )

        # Act
        with patch.object(
            PromptVersionResponse,
            "from_orm",
            side_effect=lambda x: PromptVersionResponse(
                id=x.id,
                created_at=x.created_at,
                created_by=x.created_by,
                description=x.description,
                is_current=x.is_current,
            ),
        ):
            result = await prompt_service.get_prompt_versions(
                sample_agent_id, sample_tenant_id, limit=20, offset=0
            )

        # Assert
        assert len(result) == 2
        assert result[0].is_current == True  # Newest first
        assert result[1].is_current == False

    @pytest.mark.asyncio
    async def test_get_prompt_versions_agent_not_found(
        self, prompt_service, sample_agent_id, sample_tenant_id, mock_db
    ):
        """Test error when agent doesn't belong to tenant."""
        # Arrange
        mock_result = AsyncMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act & Assert
        with pytest.raises(ValueError, match="Agent .* not found for tenant"):
            await prompt_service.get_prompt_versions(
                sample_agent_id, sample_tenant_id
            )

    @pytest.mark.asyncio
    async def test_save_prompt_version_success(
        self,
        prompt_service,
        sample_agent_id,
        sample_tenant_id,
        sample_prompt_text,
        mock_db,
    ):
        """Test successful prompt version save with current flag update."""
        # Arrange
        mock_agent = MagicMock()
        mock_agent_result = AsyncMock()
        mock_agent_result.scalars.return_value.first.return_value = mock_agent

        mock_db.execute = AsyncMock(return_value=mock_agent_result)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Act
        with patch.object(
            PromptVersionResponse,
            "from_orm",
            return_value=PromptVersionResponse(
                id=uuid4(),
                created_at=datetime.utcnow(),
                created_by="admin",
                description="Test",
                is_current=True,
            ),
        ):
            result = await prompt_service.save_prompt_version(
                sample_agent_id,
                sample_tenant_id,
                sample_prompt_text,
                description="Updated prompt",
                created_by="admin",
            )

        # Assert
        assert result.is_current == True
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_prompt_version_invalid_length(
        self,
        prompt_service,
        sample_agent_id,
        sample_tenant_id,
    ):
        """Test error when prompt text exceeds length limits."""
        # Too short
        with pytest.raises(ValueError, match="10-32000 characters"):
            await prompt_service.save_prompt_version(
                sample_agent_id, sample_tenant_id, "short"
            )

        # Too long
        with pytest.raises(ValueError, match="10-32000 characters"):
            await prompt_service.save_prompt_version(
                sample_agent_id, sample_tenant_id, "x" * 40000
            )

    @pytest.mark.asyncio
    async def test_revert_to_version_success(
        self,
        prompt_service,
        sample_agent_id,
        sample_tenant_id,
        mock_db,
    ):
        """Test successful revert to previous version."""
        # Arrange
        version_id = uuid4()
        target_prompt = "Reverted prompt text..."

        mock_agent = MagicMock()
        mock_agent_result = AsyncMock()
        mock_agent_result.scalars.return_value.first.return_value = mock_agent

        mock_target_version = MagicMock()
        mock_target_version.prompt_text = target_prompt
        mock_version_result = AsyncMock()
        mock_version_result.scalars.return_value.first.return_value = mock_target_version

        mock_db.execute = AsyncMock(
            side_effect=[mock_agent_result, mock_version_result]
        )
        mock_db.commit = AsyncMock()

        # Act
        result = await prompt_service.revert_to_version(
            version_id, sample_agent_id, sample_tenant_id, created_by="admin"
        )

        # Assert
        assert result is True
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_revert_to_version_not_found(
        self,
        prompt_service,
        sample_agent_id,
        sample_tenant_id,
        mock_db,
    ):
        """Test error when version not found."""
        # Arrange
        version_id = uuid4()

        mock_agent = MagicMock()
        mock_agent_result = AsyncMock()
        mock_agent_result.scalars.return_value.first.return_value = mock_agent

        mock_version_result = AsyncMock()
        mock_version_result.scalars.return_value.first.return_value = None

        mock_db.execute = AsyncMock(
            side_effect=[mock_agent_result, mock_version_result]
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Prompt version .* not found"):
            await prompt_service.revert_to_version(
                version_id, sample_agent_id, sample_tenant_id
            )


class TestTemplateManagement:
    """Tests for prompt template CRUD operations."""

    @pytest.mark.asyncio
    async def test_get_prompt_templates_includes_builtin(
        self, prompt_service, sample_tenant_id, mock_db
    ):
        """Test retrieving both built-in and custom templates."""
        # Arrange
        mock_builtin = MagicMock()
        mock_builtin.is_builtin = True
        mock_builtin.name = "Built-in Template"

        mock_custom = MagicMock()
        mock_custom.is_builtin = False
        mock_custom.tenant_id = sample_tenant_id
        mock_custom.name = "Custom Template"

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [mock_builtin, mock_custom]

        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        with patch.object(
            PromptTemplateResponse,
            "from_orm",
            side_effect=lambda x: MagicMock(
                name=x.name, is_builtin=x.is_builtin, id=uuid4()
            ),
        ):
            result = await prompt_service.get_prompt_templates(
                sample_tenant_id, include_builtin=True
            )

        # Assert
        assert len(result) == 2
        assert any(t.is_builtin for t in result)
        assert any(not t.is_builtin for t in result)

    @pytest.mark.asyncio
    async def test_get_prompt_templates_custom_only(
        self, prompt_service, sample_tenant_id, mock_db
    ):
        """Test retrieving only custom templates for tenant."""
        # Arrange
        mock_custom = MagicMock()
        mock_custom.is_builtin = False
        mock_custom.tenant_id = sample_tenant_id

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [mock_custom]

        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        with patch.object(
            PromptTemplateResponse,
            "from_orm",
            return_value=MagicMock(is_builtin=False),
        ):
            result = await prompt_service.get_prompt_templates(
                sample_tenant_id, include_builtin=False
            )

        # Assert
        assert len(result) == 1
        assert all(not t.is_builtin for t in result)

    @pytest.mark.asyncio
    async def test_create_custom_template_success(
        self, prompt_service, sample_tenant_id, mock_db
    ):
        """Test successful creation of custom template."""
        # Arrange
        schema = PromptTemplateCreate(
            name="Test Template",
            description="A test template",
            template_text="You are {{agent_name}} for {{tenant_name}}",
        )

        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Act
        with patch.object(
            PromptTemplateResponse,
            "from_orm",
            return_value=PromptTemplateResponse(
                id=uuid4(),
                name="Test Template",
                description="A test template",
                template_text="You are {{agent_name}} for {{tenant_name}}",
                is_builtin=False,
                usage_count=0,
                created_by="admin",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ):
            result = await prompt_service.create_custom_template(
                sample_tenant_id, schema, created_by="admin"
            )

        # Assert
        assert result.name == "Test Template"
        assert result.is_builtin == False
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_custom_template_success(
        self, prompt_service, sample_tenant_id, mock_db
    ):
        """Test successful soft delete of custom template."""
        # Arrange
        template_id = uuid4()

        mock_template = MagicMock()
        mock_template.is_builtin = False
        mock_template.tenant_id = sample_tenant_id

        mock_result = AsyncMock()
        mock_result.scalars.return_value.first.return_value = mock_template

        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        # Act
        result = await prompt_service.delete_custom_template(template_id, sample_tenant_id)

        # Assert
        assert result is True
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_custom_template_builtin_error(
        self, prompt_service, sample_tenant_id, mock_db
    ):
        """Test error when attempting to delete built-in template."""
        # Arrange
        template_id = uuid4()

        mock_result = AsyncMock()
        mock_result.scalars.return_value.first.return_value = None  # Not found (built-in)

        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act & Assert
        with pytest.raises(ValueError, match="not found or is built-in"):
            await prompt_service.delete_custom_template(template_id, sample_tenant_id)


class TestVariableSubstitution:
    """Tests for {{variable}} substitution logic."""

    def test_substitute_variables_basic(self, prompt_service):
        """Test basic variable substitution."""
        template = "Hello {{agent_name}}, available for {{tenant_name}}"
        variables = {"agent_name": "Support Bot", "tenant_name": "Acme Corp"}

        result = PromptService.substitute_variables(template, variables)

        assert result == "Hello Support Bot, available for Acme Corp"

    def test_substitute_variables_undefined(self, prompt_service):
        """Test substitution with undefined variables."""
        template = "Agent: {{agent_name}}, Tools: {{tools}}"
        variables = {"agent_name": "Bot"}  # Missing {{tools}}

        result = PromptService.substitute_variables(template, variables)

        assert result == "Agent: Bot, Tools: [UNDEFINED: tools]"

    def test_substitute_variables_no_vars(self, prompt_service):
        """Test template with no variables."""
        template = "You are a helpful assistant"
        variables = {}

        result = PromptService.substitute_variables(template, variables)

        assert result == template

    def test_substitute_variables_multiple_same(self, prompt_service):
        """Test multiple occurrences of same variable."""
        template = "{{tenant_name}} uses {{tenant_name}} for operations"
        variables = {"tenant_name": "ACME"}

        result = PromptService.substitute_variables(template, variables)

        assert result == "ACME uses ACME for operations"

    def test_substitute_variables_all_defined(self, prompt_service):
        """Test substitution with all defined variables."""
        template = (
            "Tenant: {{tenant_name}}, Agent: {{agent_name}}, "
            "Tools: {{tools}}, Date: {{current_date}}"
        )
        variables = {
            "tenant_name": "ACME",
            "agent_name": "Support",
            "tools": "Jira, ServiceDesk",
            "current_date": "2025-11-05",
        }

        result = PromptService.substitute_variables(template, variables)

        expected = (
            "Tenant: ACME, Agent: Support, "
            "Tools: Jira, ServiceDesk, Date: 2025-11-05"
        )
        assert result == expected


class TestMultiTenancyEnforcement:
    """Tests for tenant isolation guarantees."""

    @pytest.mark.asyncio
    async def test_cross_tenant_isolation_get_versions(
        self, prompt_service, sample_agent_id, mock_db
    ):
        """Test that agents from other tenants cannot access versions."""
        # Attempt to access agent from different tenant
        wrong_tenant_id = "different_tenant"

        mock_result = AsyncMock()
        mock_result.scalars.return_value.first.return_value = None  # Agent not found for tenant

        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act & Assert
        with pytest.raises(ValueError, match="not found for tenant"):
            await prompt_service.get_prompt_versions(sample_agent_id, wrong_tenant_id)

    @pytest.mark.asyncio
    async def test_cross_tenant_isolation_templates(
        self, prompt_service, mock_db
    ):
        """Test that custom templates are tenant-scoped."""
        # Tenant A tries to update Tenant B's template
        template_id = uuid4()
        tenant_a = "tenant_a"
        tenant_b = "tenant_b"

        # Query returns None (template not found for tenant_a)
        mock_result = AsyncMock()
        mock_result.scalars.return_value.first.return_value = None

        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act & Assert
        with pytest.raises(ValueError):
            schema = PromptTemplateCreate(
                name="Test",
                description="Test",
                template_text="Test {{tenant_name}}",
            )
            await prompt_service.update_custom_template(template_id, tenant_a, schema)
