"""
Unit tests for Agent Pydantic schemas.

Tests validation logic for LLMConfig, AgentCreate, AgentUpdate, AgentResponse,
AgentStatus, and TriggerType. Covers field validators, model validators,
and enum serialization.
"""

import pytest
from pydantic import ValidationError

from src.schemas.agent import (
    AgentCreate,
    AgentResponse,
    AgentStatus,
    AgentTriggerCreate,
    AgentUpdate,
    LLMConfig,
    TriggerType,
)


class TestLLMConfig:
    """Tests for LLMConfig schema validation."""

    def test_llm_config_valid(self):
        """Test valid LLM configuration parses correctly."""
        config = LLMConfig(
            provider="litellm",
            model="gpt-4",
            temperature=0.7,
            max_tokens=4096,
        )

        assert config.provider == "litellm"
        assert config.model == "gpt-4"
        assert config.temperature == 0.7
        assert config.max_tokens == 4096

    def test_llm_config_defaults(self):
        """Test LLMConfig default values."""
        config = LLMConfig(model="gpt-4")

        assert config.provider == "litellm"  # default
        assert config.temperature == 0.7  # default
        assert config.max_tokens == 4096  # default

    def test_llm_config_temperature_range(self):
        """Test temperature range validation (0.0-2.0)."""
        # Valid temperatures
        LLMConfig(model="gpt-4", temperature=0.0)  # min
        LLMConfig(model="gpt-4", temperature=1.0)  # middle
        LLMConfig(model="gpt-4", temperature=2.0)  # max

        # Invalid temperatures
        with pytest.raises(ValidationError) as exc_info:
            LLMConfig(model="gpt-4", temperature=-0.1)
        assert "greater_than_equal" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            LLMConfig(model="gpt-4", temperature=2.1)
        assert "less_than_equal" in str(exc_info.value)

    def test_llm_config_max_tokens_range(self):
        """Test max_tokens range validation (1-32000)."""
        # Valid token counts
        LLMConfig(model="gpt-4", max_tokens=1)  # min
        LLMConfig(model="gpt-4", max_tokens=16000)  # middle
        LLMConfig(model="gpt-4", max_tokens=32000)  # max

        # Invalid token counts
        with pytest.raises(ValidationError) as exc_info:
            LLMConfig(model="gpt-4", max_tokens=0)
        assert "greater_than_equal" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            LLMConfig(model="gpt-4", max_tokens=32001)
        assert "less_than_equal" in str(exc_info.value)

    def test_llm_config_invalid_model(self):
        """Test unknown model raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            LLMConfig(model="gpt-99-ultra")
        assert "Model must be one of" in str(exc_info.value)


class TestAgentTriggerCreate:
    """Tests for AgentTriggerCreate schema validation."""

    def test_webhook_trigger_valid(self):
        """Test creating valid webhook trigger."""
        trigger = AgentTriggerCreate(
            trigger_type=TriggerType.WEBHOOK,
            webhook_url="/agents/uuid-123/webhook",
            hmac_secret="encrypted_secret",
        )

        assert trigger.trigger_type == TriggerType.WEBHOOK
        assert trigger.webhook_url == "/agents/uuid-123/webhook"
        assert trigger.hmac_secret == "encrypted_secret"
        assert trigger.schedule_cron is None

    def test_schedule_trigger_valid(self):
        """Test creating valid schedule trigger with cron."""
        trigger = AgentTriggerCreate(
            trigger_type=TriggerType.SCHEDULE,
            schedule_cron="0 9 * * *",
        )

        assert trigger.trigger_type == TriggerType.SCHEDULE
        assert trigger.schedule_cron == "0 9 * * *"
        assert trigger.webhook_url is None

    def test_schedule_trigger_requires_cron(self):
        """Test schedule trigger without cron raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AgentTriggerCreate(trigger_type=TriggerType.SCHEDULE)
        assert "schedule_cron is required" in str(exc_info.value)


class TestAgentCreate:
    """Tests for AgentCreate schema validation."""

    def test_agent_create_valid(self):
        """Test creating valid agent with all required fields."""
        agent = AgentCreate(
            name="Test Agent",
            description="Test description",
            system_prompt="You are a helpful assistant for ticket enhancement.",
            llm_config=LLMConfig(model="gpt-4"),
            status=AgentStatus.DRAFT,
            triggers=[
                AgentTriggerCreate(
                    trigger_type=TriggerType.WEBHOOK,
                    webhook_url="/agents/uuid/webhook",
                )
            ],
            tool_ids=["servicedesk_plus"],
        )

        assert agent.name == "Test Agent"
        assert agent.description == "Test description"
        assert len(agent.system_prompt) > 10
        assert agent.llm_config.model == "gpt-4"
        assert agent.status == AgentStatus.DRAFT
        assert len(agent.triggers) == 1
        assert len(agent.tool_ids) == 1

    def test_agent_create_defaults(self):
        """Test AgentCreate default values."""
        agent = AgentCreate(
            name="Test Agent",
            system_prompt="Test prompt for agent",
            llm_config=LLMConfig(model="gpt-4"),
        )

        assert agent.status == AgentStatus.DRAFT  # default
        assert agent.description is None  # optional
        assert agent.created_by is None  # optional
        assert agent.triggers == []  # default empty list
        assert agent.tool_ids == []  # default empty list

    def test_agent_create_missing_name(self):
        """Test missing name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AgentCreate(
                system_prompt="Test prompt",
                llm_config=LLMConfig(model="gpt-4"),
            )
        assert "name" in str(exc_info.value)

    def test_agent_create_invalid_prompt_length(self):
        """Test prompt too short or too long raises ValidationError."""
        # Prompt too short (<10 chars)
        with pytest.raises(ValidationError) as exc_info:
            AgentCreate(
                name="Test Agent",
                system_prompt="Short",  # Only 5 chars
                llm_config=LLMConfig(model="gpt-4"),
            )
        assert "at least 10 characters" in str(exc_info.value)

        # Prompt too long (>32000 chars)
        with pytest.raises(ValidationError) as exc_info:
            AgentCreate(
                name="Test Agent",
                system_prompt="A" * 32001,  # 32001 chars
                llm_config=LLMConfig(model="gpt-4"),
            )
        assert "at most 32000 characters" in str(exc_info.value)

    def test_agent_create_with_triggers(self):
        """Test creating agent with webhook and schedule triggers."""
        agent = AgentCreate(
            name="Multi-Trigger Agent",
            system_prompt="Test agent with multiple triggers",
            llm_config=LLMConfig(model="gpt-4"),
            triggers=[
                AgentTriggerCreate(
                    trigger_type=TriggerType.WEBHOOK,
                    webhook_url="/agents/uuid/webhook",
                ),
                AgentTriggerCreate(
                    trigger_type=TriggerType.SCHEDULE,
                    schedule_cron="0 * * * *",
                ),
            ],
        )

        assert len(agent.triggers) == 2
        assert agent.triggers[0].trigger_type == TriggerType.WEBHOOK
        assert agent.triggers[1].trigger_type == TriggerType.SCHEDULE

    def test_active_agent_requires_trigger(self):
        """Test active agent without triggers raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AgentCreate(
                name="Test Agent",
                system_prompt="Test prompt for active agent",
                llm_config=LLMConfig(model="gpt-4"),
                status=AgentStatus.ACTIVE,
                triggers=[],  # No triggers
            )
        assert "Active agents must have at least one trigger" in str(exc_info.value)


class TestAgentUpdate:
    """Tests for AgentUpdate schema validation."""

    def test_agent_update_partial(self):
        """Test partial update with subset of fields."""
        update = AgentUpdate(name="Updated Name", status=AgentStatus.ACTIVE)

        assert update.name == "Updated Name"
        assert update.status == AgentStatus.ACTIVE
        # Other fields not provided (partial update)
        assert update.description is None
        assert update.system_prompt is None
        assert update.llm_config is None

    def test_agent_update_empty(self):
        """Test empty update allowed (no-op)."""
        update = AgentUpdate()

        assert update.name is None
        assert update.description is None
        assert update.system_prompt is None
        assert update.llm_config is None
        assert update.status is None

    def test_agent_update_invalid_status_transition(self):
        """Test transition to draft status is blocked."""
        with pytest.raises(ValidationError) as exc_info:
            AgentUpdate(status=AgentStatus.DRAFT)
        assert "Cannot transition agent status to 'draft'" in str(exc_info.value)


class TestAgentResponse:
    """Tests for AgentResponse schema validation and ORM mode."""

    def test_agent_response_creation(self):
        """Test creating AgentResponse with all fields."""
        from datetime import datetime, timezone
        from uuid import uuid4

        response = AgentResponse(
            id=uuid4(),
            tenant_id="tenant_123",
            name="Test Agent",
            description="Test description",
            status=AgentStatus.ACTIVE,
            system_prompt="Test prompt",
            llm_config={"provider": "litellm", "model": "gpt-4"},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="admin@example.com",
            triggers=[{"trigger_type": "webhook", "webhook_url": "/webhook"}],
            tool_ids=["servicedesk_plus"],
        )

        assert response.tenant_id == "tenant_123"
        assert response.name == "Test Agent"
        assert response.status == AgentStatus.ACTIVE
        assert response.llm_config["model"] == "gpt-4"
        assert len(response.triggers) == 1
        assert len(response.tool_ids) == 1

    def test_agent_response_from_attributes(self):
        """Test AgentResponse from_attributes config for ORM mode."""
        # Verify from_attributes is set in model_config
        assert AgentResponse.model_config.get("from_attributes") is True


class TestAgentStatus:
    """Tests for AgentStatus enum."""

    def test_agent_status_values(self):
        """Test all AgentStatus enum values."""
        assert AgentStatus.DRAFT.value == "draft"
        assert AgentStatus.ACTIVE.value == "active"
        assert AgentStatus.SUSPENDED.value == "suspended"
        assert AgentStatus.INACTIVE.value == "inactive"

    def test_agent_status_json_serialization(self):
        """Test enum serializes to JSON string."""
        import json

        agent = AgentCreate(
            name="Test",
            system_prompt="Test prompt",
            llm_config=LLMConfig(model="gpt-4"),
            status=AgentStatus.DRAFT,
        )

        # Pydantic model_dump() converts enum to value
        agent_dict = agent.model_dump()
        assert agent_dict["status"] == "draft"

        # JSON serialization works
        json_str = json.dumps(agent_dict)
        assert '"status": "draft"' in json_str


class TestTriggerType:
    """Tests for TriggerType enum."""

    def test_trigger_type_values(self):
        """Test all TriggerType enum values."""
        assert TriggerType.WEBHOOK.value == "webhook"
        assert TriggerType.SCHEDULE.value == "schedule"

    def test_trigger_type_in_schema(self):
        """Test TriggerType enum used in schema."""
        trigger = AgentTriggerCreate(
            trigger_type=TriggerType.WEBHOOK,
            webhook_url="/webhook",
        )

        assert trigger.trigger_type == TriggerType.WEBHOOK
        assert trigger.trigger_type.value == "webhook"
