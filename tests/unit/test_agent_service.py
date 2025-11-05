"""
Unit tests for AgentService schema validation and initialization (Story 8.3).

These tests focus on schema validation and service initialization, which can be
tested without complex AsyncSession mocking. Full CRUD operation testing is covered
by integration tests (tests/integration/test_agent_api.py) which test the complete
workflow end-to-end with real database sessions.

Test Strategy:
- Unit: Schema validation, enum validation, service initialization
- Integration: Full CRUD operations with real AsyncSession and database
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.schemas.agent import (
    AgentCreate,
    AgentResponse,
    AgentStatus,
    AgentUpdate,
    LLMConfig,
    TriggerType,
)
from src.services.agent_service import AgentService


class TestAgentServiceInitialization:
    """Tests for AgentService initialization and configuration."""

    def test_agent_service_creation_default_base_url(self):
        """Test AgentService initialization with default base URL."""
        service = AgentService()
        assert service.base_url == "http://localhost:8000"

    def test_agent_service_creation_custom_base_url(self):
        """Test AgentService initialization with custom base URL."""
        custom_url = "https://api.production.example.com"
        service = AgentService(base_url=custom_url)
        assert service.base_url == custom_url

    def test_get_agent_service_singleton(self):
        """Test get_agent_service returns AgentService singleton."""
        from src.services.agent_service import get_agent_service

        service1 = get_agent_service()
        service2 = get_agent_service()
        assert service1 is service2


class TestAgentCreateSchema:
    """Tests for AgentCreate schema validation."""

    def test_agent_create_valid_minimal(self):
        """Test creating agent with minimal valid data."""
        agent_data = AgentCreate(
            name="Test Agent",
            system_prompt="You are helpful.",
            llm_config=LLMConfig(model="gpt-4"),
            status=AgentStatus.DRAFT,
        )
        assert agent_data.name == "Test Agent"
        assert agent_data.system_prompt == "You are helpful."
        assert agent_data.status == AgentStatus.DRAFT

    def test_agent_create_valid_full(self):
        """Test creating agent with all fields."""
        agent_data = AgentCreate(
            name="Full Agent",
            description="Complete agent configuration",
            system_prompt="You are an expert assistant.",
            llm_config=LLMConfig(
                model="claude-3-sonnet", temperature=0.7, max_tokens=4096
            ),
            status=AgentStatus.DRAFT,
            created_by="test@example.com",
            tool_ids=["servicedesk_plus", "knowledge_base"],
        )
        assert agent_data.name == "Full Agent"
        assert agent_data.description == "Complete agent configuration"
        assert len(agent_data.tool_ids) == 2
        assert agent_data.created_by == "test@example.com"

    def test_agent_create_missing_name(self):
        """Test validation fails when name is missing."""
        with pytest.raises(ValidationError) as exc_info:
            AgentCreate(
                system_prompt="You are helpful.",
                llm_config=LLMConfig(model="gpt-4"),
                status=AgentStatus.DRAFT,
            )
        assert "name" in str(exc_info.value).lower()

    def test_agent_create_missing_system_prompt(self):
        """Test validation fails when system_prompt is missing."""
        with pytest.raises(ValidationError) as exc_info:
            AgentCreate(
                name="Test Agent",
                llm_config=LLMConfig(model="gpt-4"),
                status=AgentStatus.DRAFT,
            )
        assert "system_prompt" in str(exc_info.value).lower()

    def test_agent_create_invalid_status(self):
        """Test validation fails for invalid status."""
        with pytest.raises(ValidationError):
            AgentCreate(
                name="Test Agent",
                system_prompt="You are helpful.",
                llm_config=LLMConfig(model="gpt-4"),
                status="invalid_status",  # type: ignore
            )

    def test_agent_create_short_name(self):
        """Test validation fails for very short name."""
        with pytest.raises(ValidationError):
            AgentCreate(
                name="A",  # Too short
                system_prompt="You are helpful.",
                llm_config=LLMConfig(model="gpt-4"),
                status=AgentStatus.DRAFT,
            )

    def test_agent_create_short_system_prompt(self):
        """Test validation fails for very short system_prompt."""
        with pytest.raises(ValidationError):
            AgentCreate(
                name="Test Agent",
                system_prompt="Hi",  # Too short
                llm_config=LLMConfig(model="gpt-4"),
                status=AgentStatus.DRAFT,
            )


class TestAgentUpdateSchema:
    """Tests for AgentUpdate schema validation."""

    def test_agent_update_partial_name(self):
        """Test partial update with only name."""
        agent_update = AgentUpdate(name="Updated Name")
        assert agent_update.name == "Updated Name"
        assert agent_update.description is None
        assert agent_update.status is None

    def test_agent_update_partial_status(self):
        """Test partial update with only status."""
        agent_update = AgentUpdate(status=AgentStatus.ACTIVE)
        assert agent_update.status == AgentStatus.ACTIVE
        assert agent_update.name is None

    def test_agent_update_all_fields(self):
        """Test partial update with multiple fields."""
        agent_update = AgentUpdate(
            name="Updated", description="New description", status=AgentStatus.ACTIVE
        )
        assert agent_update.name == "Updated"
        assert agent_update.description == "New description"
        assert agent_update.status == AgentStatus.ACTIVE


class TestAgentResponseSchema:
    """Tests for AgentResponse schema validation."""

    def test_agent_response_creation(self):
        """Test creating AgentResponse from dict-like object."""
        agent_data = {
            "id": uuid4(),
            "tenant_id": "tenant-123",
            "name": "Test Agent",
            "description": "Test description",
            "status": AgentStatus.DRAFT,
            "system_prompt": "You are helpful.",
            "llm_config": {"model": "gpt-4"},
            "created_at": "2025-11-05T00:00:00Z",
            "updated_at": "2025-11-05T00:00:00Z",
            "created_by": "test@example.com",
            "triggers": [],
            "tools": [],
        }
        response = AgentResponse(**agent_data)
        assert response.name == "Test Agent"
        assert response.status == AgentStatus.DRAFT
        assert response.tenant_id == "tenant-123"


class TestAgentStatusEnum:
    """Tests for AgentStatus enum."""

    def test_all_statuses_available(self):
        """Test all required agent statuses are defined."""
        assert AgentStatus.DRAFT.value == "draft"
        assert AgentStatus.ACTIVE.value == "active"
        assert AgentStatus.SUSPENDED.value == "suspended"
        assert AgentStatus.INACTIVE.value == "inactive"

    def test_status_comparison(self):
        """Test status enum comparison."""
        draft_status = AgentStatus.DRAFT
        assert draft_status == AgentStatus.DRAFT
        assert draft_status != AgentStatus.ACTIVE


class TestLLMConfig:
    """Tests for LLMConfig schema."""

    def test_llm_config_minimal(self):
        """Test creating LLMConfig with minimal fields."""
        config = LLMConfig(model="gpt-4")
        assert config.model == "gpt-4"
        assert config.temperature is None or config.temperature == 0.7  # Check default

    def test_llm_config_full(self):
        """Test creating LLMConfig with all fields."""
        config = LLMConfig(
            provider="litellm",
            model="claude-3-sonnet",
            temperature=0.5,
            max_tokens=2000,
        )
        assert config.model == "claude-3-sonnet"
        assert config.temperature == 0.5
        assert config.max_tokens == 2000

    def test_llm_config_invalid_temperature(self):
        """Test validation fails for invalid temperature."""
        with pytest.raises(ValidationError):
            LLMConfig(model="gpt-4", temperature=2.5)  # Out of range (max 2.0)

    def test_llm_config_invalid_max_tokens(self):
        """Test validation fails for invalid max_tokens."""
        with pytest.raises(ValidationError):
            LLMConfig(model="gpt-4", max_tokens=-100)  # Negative


class TestTriggerType:
    """Tests for TriggerType enum."""

    def test_trigger_type_webhook(self):
        """Test webhook trigger type."""
        assert TriggerType.WEBHOOK.value == "webhook"

    def test_trigger_type_schedule(self):
        """Test schedule trigger type."""
        assert TriggerType.SCHEDULE.value == "schedule"
