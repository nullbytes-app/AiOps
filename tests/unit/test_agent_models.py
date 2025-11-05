"""
Unit tests for Agent SQLAlchemy models.

Tests Agent, AgentTrigger, and AgentTool model instantiation, defaults,
relationships, and __repr__ methods. Does not test database operations
(covered in integration tests).
"""

import uuid
from datetime import datetime

import pytest

from src.database.models import Agent, AgentTool, AgentTrigger


class TestAgentModel:
    """Tests for Agent model instantiation and defaults."""

    def test_create_agent_model(self):
        """Test creating Agent instance with all required fields."""
        agent_id = uuid.uuid4()
        tenant_id = "tenant_123"
        name = "Test Agent"
        description = "Test description"
        status = "draft"
        system_prompt = "You are a helpful assistant"
        llm_config = {"provider": "litellm", "model": "gpt-4", "temperature": 0.7}
        created_by = "test_user"

        agent = Agent(
            id=agent_id,
            tenant_id=tenant_id,
            name=name,
            description=description,
            status=status,
            system_prompt=system_prompt,
            llm_config=llm_config,
            created_by=created_by,
        )

        assert agent.id == agent_id
        assert agent.tenant_id == tenant_id
        assert agent.name == name
        assert agent.description == description
        assert agent.status == status
        assert agent.system_prompt == system_prompt
        assert agent.llm_config == llm_config
        assert agent.created_by == created_by

    def test_agent_model_defaults(self):
        """Test Agent model default values (UUID, timestamps, llm_config)."""
        # Create agent with explicit UUID (in-memory test)
        agent_id = uuid.uuid4()
        agent = Agent(
            id=agent_id,
            tenant_id="tenant_123",
            name="Test Agent",
            status="draft",
            system_prompt="Test prompt",
        )

        # UUID is set
        assert agent.id == agent_id
        assert isinstance(agent.id, uuid.UUID)

        # llm_config defaults to None in-memory (database sets server_default='{}')
        assert agent.llm_config is None

        # Optional fields default to None
        assert agent.description is None
        assert agent.created_by is None

        # Timestamps would be set by database (server_default), not in-memory
        # These are None until persisted
        assert agent.created_at is None
        assert agent.updated_at is None

    def test_agent_repr(self):
        """Test Agent __repr__ method for debugging."""
        agent = Agent(
            id=uuid.uuid4(),
            tenant_id="tenant_123",
            name="Test Agent",
            status="active",
            system_prompt="Test prompt",
        )

        repr_str = repr(agent)
        assert "Agent" in repr_str
        assert str(agent.id) in repr_str
        assert "Test Agent" in repr_str
        assert "active" in repr_str


class TestAgentTriggerModel:
    """Tests for AgentTrigger model instantiation."""

    def test_create_agent_trigger_webhook(self):
        """Test creating AgentTrigger with webhook type."""
        trigger_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        trigger_type = "webhook"
        webhook_url = "/agents/uuid-123/webhook"
        hmac_secret = "encrypted_secret"

        trigger = AgentTrigger(
            id=trigger_id,
            agent_id=agent_id,
            trigger_type=trigger_type,
            webhook_url=webhook_url,
            hmac_secret=hmac_secret,
        )

        assert trigger.id == trigger_id
        assert trigger.agent_id == agent_id
        assert trigger.trigger_type == trigger_type
        assert trigger.webhook_url == webhook_url
        assert trigger.hmac_secret == hmac_secret
        assert trigger.schedule_cron is None
        assert trigger.payload_schema is None

    def test_create_agent_trigger_schedule(self):
        """Test creating AgentTrigger with schedule type."""
        trigger_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        trigger_type = "schedule"
        schedule_cron = "0 9 * * *"  # Daily at 9 AM

        trigger = AgentTrigger(
            id=trigger_id,
            agent_id=agent_id,
            trigger_type=trigger_type,
            schedule_cron=schedule_cron,
        )

        assert trigger.id == trigger_id
        assert trigger.agent_id == agent_id
        assert trigger.trigger_type == trigger_type
        assert trigger.schedule_cron == schedule_cron
        assert trigger.webhook_url is None
        assert trigger.hmac_secret is None

    def test_agent_trigger_relationship(self):
        """Test AgentTrigger.agent relationship (in-memory, no DB)."""
        agent = Agent(
            id=uuid.uuid4(),
            tenant_id="tenant_123",
            name="Test Agent",
            status="active",
            system_prompt="Test prompt",
        )

        trigger = AgentTrigger(
            id=uuid.uuid4(),
            agent_id=agent.id,
            trigger_type="webhook",
        )

        # Relationship is defined but requires DB session to load
        # In-memory test just verifies attribute exists
        assert hasattr(trigger, "agent")

    def test_agent_trigger_repr(self):
        """Test AgentTrigger __repr__ method for debugging."""
        agent_id = uuid.uuid4()
        trigger = AgentTrigger(
            id=uuid.uuid4(),
            agent_id=agent_id,
            trigger_type="webhook",
        )

        repr_str = repr(trigger)
        assert "AgentTrigger" in repr_str
        assert str(trigger.id) in repr_str
        assert "webhook" in repr_str
        assert str(agent_id) in repr_str


class TestAgentToolModel:
    """Tests for AgentTool junction table model."""

    def test_create_agent_tool(self):
        """Test creating AgentTool with composite primary key."""
        agent_id = uuid.uuid4()
        tool_id = "servicedesk_plus"

        agent_tool = AgentTool(
            agent_id=agent_id,
            tool_id=tool_id,
        )

        assert agent_tool.agent_id == agent_id
        assert agent_tool.tool_id == tool_id
        # Timestamp set by database, None in-memory
        assert agent_tool.created_at is None

    def test_agent_tools_relationship(self):
        """Test Agent.tools relationship (in-memory, no DB)."""
        agent = Agent(
            id=uuid.uuid4(),
            tenant_id="tenant_123",
            name="Test Agent",
            status="active",
            system_prompt="Test prompt",
        )

        tool1 = AgentTool(agent_id=agent.id, tool_id="servicedesk_plus")
        tool2 = AgentTool(agent_id=agent.id, tool_id="jira")

        # Relationship is defined but requires DB session to load
        # In-memory test just verifies attribute exists
        assert hasattr(agent, "tools")
        assert hasattr(tool1, "agent")

    def test_agent_tool_composite_pk(self):
        """Test AgentTool composite primary key uniqueness concept."""
        agent_id = uuid.uuid4()
        tool_id = "servicedesk_plus"

        tool1 = AgentTool(agent_id=agent_id, tool_id=tool_id)
        tool2 = AgentTool(agent_id=agent_id, tool_id=tool_id)

        # Both instances have same composite key (agent_id, tool_id)
        # Database would reject second insert due to PK constraint
        assert tool1.agent_id == tool2.agent_id
        assert tool1.tool_id == tool2.tool_id

    def test_agent_tool_repr(self):
        """Test AgentTool __repr__ method for debugging."""
        agent_id = uuid.uuid4()
        tool_id = "servicedesk_plus"

        agent_tool = AgentTool(agent_id=agent_id, tool_id=tool_id)

        repr_str = repr(agent_tool)
        assert "AgentTool" in repr_str
        assert str(agent_id) in repr_str
        assert tool_id in repr_str
