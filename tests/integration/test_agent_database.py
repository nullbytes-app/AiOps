"""
Integration tests for Agent database operations.

Tests CRUD operations, relationships, tenant isolation, JSONB queries,
and cascade deletes. Requires running PostgreSQL database with
ai_agents schema.
"""

import uuid
from datetime import datetime

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from src.database.models import Agent, AgentTool, AgentTrigger, TenantConfig


@pytest.fixture(scope="module")
def db_session():
    """
    Create test database session.

    Uses test database URL from environment. Assumes migrations
    have been applied (alembic upgrade head).
    """
    import os

    # Use test database from environment
    db_url = os.environ.get(
        "AI_AGENTS_DATABASE_URL",
        "postgresql+psycopg2://aiagents:password@localhost:5433/ai_agents",
    )

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()


@pytest.fixture(scope="module")
def test_tenant(db_session):
    """
    Create test tenant for agent tests.

    Ensures tenant_configs has entry for foreign key constraint.
    """
    tenant = TenantConfig(
        id=uuid.uuid4(),
        tenant_id="test_tenant_agents",
        name="Test Tenant for Agents",
        servicedesk_url="https://test.example.com",
        servicedesk_api_key_encrypted="test_key",
        webhook_signing_secret_encrypted="test_secret",
        enhancement_preferences={},
    )

    # Check if tenant already exists
    existing = db_session.query(TenantConfig).filter_by(tenant_id=tenant.tenant_id).first()

    if not existing:
        db_session.add(tenant)
        db_session.commit()
        yield tenant
        # Cleanup after module tests complete
        db_session.delete(tenant)
        db_session.commit()
    else:
        yield existing


class TestAgentCRUD:
    """Tests for Agent CRUD operations."""

    def test_insert_agent(self, db_session, test_tenant):
        """Test inserting agent and querying it back."""
        agent = Agent(
            id=uuid.uuid4(),
            tenant_id=test_tenant.tenant_id,
            name="Test Insert Agent",
            description="Test description",
            status="draft",
            system_prompt="You are a test assistant",
            llm_config={"provider": "litellm", "model": "gpt-4", "temperature": 0.7},
            created_by="test_user",
        )

        db_session.add(agent)
        db_session.commit()

        # Query back
        retrieved = db_session.query(Agent).filter_by(id=agent.id).first()

        assert retrieved is not None
        assert retrieved.name == "Test Insert Agent"
        assert retrieved.tenant_id == test_tenant.tenant_id
        assert retrieved.status == "draft"
        assert retrieved.llm_config["model"] == "gpt-4"
        assert retrieved.created_at is not None  # Set by server_default
        assert retrieved.updated_at is not None

        # Cleanup
        db_session.delete(agent)
        db_session.commit()

    def test_query_agents_by_tenant(self, db_session, test_tenant):
        """Test filtering agents by tenant_id (index usage)."""
        # Create 2 agents for test tenant
        agent1 = Agent(
            tenant_id=test_tenant.tenant_id,
            name="Tenant Agent 1",
            status="active",
            system_prompt="Prompt 1",
        )
        agent2 = Agent(
            tenant_id=test_tenant.tenant_id,
            name="Tenant Agent 2",
            status="draft",
            system_prompt="Prompt 2",
        )

        db_session.add_all([agent1, agent2])
        db_session.commit()

        # Query by tenant_id
        agents = db_session.query(Agent).filter_by(tenant_id=test_tenant.tenant_id).all()

        assert len(agents) >= 2
        agent_names = [a.name for a in agents]
        assert "Tenant Agent 1" in agent_names
        assert "Tenant Agent 2" in agent_names

        # Cleanup
        db_session.delete(agent1)
        db_session.delete(agent2)
        db_session.commit()

    def test_update_agent_status(self, db_session, test_tenant):
        """Test updating agent status."""
        agent = Agent(
            tenant_id=test_tenant.tenant_id,
            name="Update Test Agent",
            status="draft",
            system_prompt="Test prompt",
        )

        db_session.add(agent)
        db_session.commit()

        # Update status
        agent.status = "active"
        db_session.commit()

        # Verify update
        retrieved = db_session.query(Agent).filter_by(id=agent.id).first()
        assert retrieved.status == "active"

        # Cleanup
        db_session.delete(agent)
        db_session.commit()

    def test_delete_agent_cascade(self, db_session, test_tenant):
        """Test CASCADE delete removes triggers and tools."""
        # Create agent with trigger and tools
        agent = Agent(
            tenant_id=test_tenant.tenant_id,
            name="Cascade Test Agent",
            status="active",
            system_prompt="Test prompt",
        )

        db_session.add(agent)
        db_session.flush()  # Get agent.id

        # Add trigger
        trigger = AgentTrigger(
            agent_id=agent.id,
            trigger_type="webhook",
            webhook_url="/test/webhook",
        )

        # Add tools
        tool1 = AgentTool(agent_id=agent.id, tool_id="servicedesk_plus")
        tool2 = AgentTool(agent_id=agent.id, tool_id="jira")

        db_session.add_all([trigger, tool1, tool2])
        db_session.commit()

        agent_id = agent.id

        # Delete agent (should CASCADE delete triggers and tools)
        db_session.delete(agent)
        db_session.commit()

        # Verify trigger deleted
        trigger_count = db_session.query(AgentTrigger).filter_by(agent_id=agent_id).count()
        assert trigger_count == 0

        # Verify tools deleted
        tool_count = db_session.query(AgentTool).filter_by(agent_id=agent_id).count()
        assert tool_count == 0


class TestAgentRelationships:
    """Tests for Agent relationships (triggers, tools)."""

    def test_agent_trigger_relationship(self, db_session, test_tenant):
        """Test agent.triggers relationship loading."""
        agent = Agent(
            tenant_id=test_tenant.tenant_id,
            name="Relationship Test Agent",
            status="active",
            system_prompt="Test prompt",
        )

        db_session.add(agent)
        db_session.flush()

        # Add 2 triggers
        trigger1 = AgentTrigger(
            agent_id=agent.id,
            trigger_type="webhook",
            webhook_url="/webhook",
        )
        trigger2 = AgentTrigger(
            agent_id=agent.id,
            trigger_type="schedule",
            schedule_cron="0 9 * * *",
        )

        db_session.add_all([trigger1, trigger2])
        db_session.commit()

        # Reload agent and access relationship
        agent = db_session.query(Agent).filter_by(id=agent.id).first()
        triggers = agent.triggers

        assert len(triggers) == 2
        trigger_types = [t.trigger_type for t in triggers]
        assert "webhook" in trigger_types
        assert "schedule" in trigger_types

        # Cleanup
        db_session.delete(agent)  # CASCADE deletes triggers
        db_session.commit()

    def test_agent_tools_relationship(self, db_session, test_tenant):
        """Test agent.tools relationship loading."""
        agent = Agent(
            tenant_id=test_tenant.tenant_id,
            name="Tools Test Agent",
            status="active",
            system_prompt="Test prompt",
        )

        db_session.add(agent)
        db_session.flush()

        # Add 3 tools
        tool1 = AgentTool(agent_id=agent.id, tool_id="servicedesk_plus")
        tool2 = AgentTool(agent_id=agent.id, tool_id="jira")
        tool3 = AgentTool(agent_id=agent.id, tool_id="zendesk")

        db_session.add_all([tool1, tool2, tool3])
        db_session.commit()

        # Reload agent and access relationship
        agent = db_session.query(Agent).filter_by(id=agent.id).first()
        tools = agent.tools

        assert len(tools) == 3
        tool_ids = [t.tool_id for t in tools]
        assert "servicedesk_plus" in tool_ids
        assert "jira" in tool_ids
        assert "zendesk" in tool_ids

        # Cleanup
        db_session.delete(agent)  # CASCADE deletes tools
        db_session.commit()


class TestJSONBOperations:
    """Tests for JSONB llm_config operations."""

    def test_jsonb_insert(self, db_session, test_tenant):
        """Test inserting agent with complex llm_config."""
        agent = Agent(
            tenant_id=test_tenant.tenant_id,
            name="JSONB Test Agent",
            status="draft",
            system_prompt="Test prompt",
            llm_config={
                "provider": "litellm",
                "model": "claude-3-5-sonnet",
                "temperature": 0.8,
                "max_tokens": 8192,
                "top_p": 1.0,
                "frequency_penalty": 0.0,
            },
        )

        db_session.add(agent)
        db_session.commit()

        # Query back and verify JSONB
        retrieved = db_session.query(Agent).filter_by(id=agent.id).first()
        assert retrieved.llm_config["model"] == "claude-3-5-sonnet"
        assert retrieved.llm_config["temperature"] == 0.8
        assert retrieved.llm_config["max_tokens"] == 8192

        # Cleanup
        db_session.delete(agent)
        db_session.commit()

    def test_jsonb_query(self, db_session, test_tenant):
        """Test querying agents by JSONB field (model=gpt-4)."""
        # Create agent with gpt-4
        agent_gpt4 = Agent(
            tenant_id=test_tenant.tenant_id,
            name="GPT-4 Agent",
            status="active",
            system_prompt="Test prompt",
            llm_config={"model": "gpt-4"},
        )

        # Create agent with claude
        agent_claude = Agent(
            tenant_id=test_tenant.tenant_id,
            name="Claude Agent",
            status="active",
            system_prompt="Test prompt",
            llm_config={"model": "claude-3-5-sonnet"},
        )

        db_session.add_all([agent_gpt4, agent_claude])
        db_session.commit()

        # Query agents using gpt-4 (JSONB operator)
        gpt4_agents = (
            db_session.query(Agent).filter(Agent.llm_config["model"].astext == "gpt-4").all()
        )

        assert len(gpt4_agents) >= 1
        assert "GPT-4 Agent" in [a.name for a in gpt4_agents]

        # Cleanup
        db_session.delete(agent_gpt4)
        db_session.delete(agent_claude)
        db_session.commit()
