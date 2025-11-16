"""
Unit tests for MemoryConfigService.

Tests memory configuration CRUD operations, vector similarity search,
retention policy enforcement, and tenant isolation with 80%+ coverage target.

Story 8.15: Memory Configuration UI - Unit Tests (Task 9.1)
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Agent, AgentMemory
from src.schemas.memory import MemoryConfig, MemoryConfigUpdate, MemoryItem, ShortTermMemoryConfig
from src.services.memory_config_service import MemoryConfigService


@pytest.fixture
def mock_db():
    """Fixture for mocked async database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def sample_agent():
    """Fixture for sample agent model."""
    return Agent(
        id=uuid4(),
        tenant_id="test-tenant",
        name="Test Agent",
        status="active",
        system_prompt="Test prompt",
        llm_config={},
        memory_config={
            "short_term": {
                "context_window_size": 4096,
                "conversation_history_length": 10,
            },
            "long_term": {
                "enabled": True,
                "vector_db": "postgresql_pgvector",
                "retention_days": 90,
            },
            "agentic": {
                "enabled": False,
                "retention_days": 90,
            },
        },
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_memory():
    """Fixture for sample memory model."""
    agent_id = uuid4()
    return AgentMemory(
        id=uuid4(),
        agent_id=agent_id,
        tenant_id="test-tenant",
        memory_type="long_term",
        content={"text": "User prefers concise responses", "source": "conversation"},
        embedding='[0.1, 0.2, 0.3]',  # Simplified embedding
        retention_days=90,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_get_memory_config_success(mock_db, sample_agent):
    """Test retrieving memory configuration successfully."""
    # Arrange
    service = MemoryConfigService(mock_db)

    # Mock database query
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_agent
    mock_db.execute = AsyncMock(return_value=mock_result)

    # Act
    config = await service.get_memory_config(sample_agent.id, "test-tenant")

    # Assert
    assert config is not None
    assert config.short_term.context_window_size == 4096
    assert config.long_term.enabled is True
    assert config.agentic.enabled is False


@pytest.mark.asyncio
async def test_get_memory_config_default_when_none(mock_db, sample_agent):
    """Test returning default configuration when memory_config is None."""
    # Arrange
    sample_agent.memory_config = None
    service = MemoryConfigService(mock_db)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_agent
    mock_db.execute = AsyncMock(return_value=mock_result)

    # Act
    config = await service.get_memory_config(sample_agent.id, "test-tenant")

    # Assert
    assert config is not None
    assert config.short_term.context_window_size == 4096  # Default
    assert config.long_term.enabled is True  # Default


@pytest.mark.asyncio
async def test_get_memory_config_agent_not_found(mock_db):
    """Test ValueError when agent not found."""
    # Arrange
    service = MemoryConfigService(mock_db)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    # Act & Assert
    with pytest.raises(ValueError, match="Agent .* not found"):
        await service.get_memory_config(uuid4(), "test-tenant")


@pytest.mark.asyncio
async def test_update_memory_config_success(mock_db, sample_agent):
    """Test updating memory configuration successfully."""
    # Arrange
    service = MemoryConfigService(mock_db)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_agent
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    config_update = MemoryConfigUpdate(
        short_term=ShortTermMemoryConfig(
            context_window_size=8192,
            conversation_history_length=20,
        )
    )

    # Act
    updated_config = await service.update_memory_config(
        sample_agent.id, "test-tenant", config_update
    )

    # Assert
    assert updated_config.short_term.context_window_size == 8192
    assert updated_config.short_term.conversation_history_length == 20
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_store_memory_success(mock_db, sample_agent):
    """Test storing new memory successfully."""
    # Arrange
    from datetime import datetime
    from uuid import uuid4

    service = MemoryConfigService(mock_db)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_agent
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    # Mock refresh to set the AgentMemory object with proper values
    memory_id = uuid4()
    now = datetime.now()

    async def mock_refresh(obj):
        """Mock refresh that populates object attributes."""
        obj.id = memory_id
        obj.created_at = now
        obj.updated_at = now

    mock_db.refresh = AsyncMock(side_effect=mock_refresh)

    content = {"text": "Test memory", "source": "test"}
    embedding = '[0.1, 0.2, 0.3]'

    # Act
    memory_item = await service.store_memory(
        sample_agent.id, "test-tenant", "long_term", content, embedding
    )

    # Assert
    assert memory_item.agent_id == sample_agent.id
    assert memory_item.memory_type == "long_term"
    assert memory_item.content == content
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_store_memory_invalid_type(mock_db, sample_agent):
    """Test ValueError when storing memory with invalid type."""
    # Arrange
    service = MemoryConfigService(mock_db)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_agent
    mock_db.execute = AsyncMock(return_value=mock_result)

    # Act & Assert
    with pytest.raises(ValueError, match="Invalid memory_type"):
        await service.store_memory(
            sample_agent.id, "test-tenant", "invalid_type", {"text": "test"}
        )


@pytest.mark.asyncio
async def test_store_memory_empty_content(mock_db, sample_agent):
    """Test ValueError when storing memory with empty content."""
    # Arrange
    service = MemoryConfigService(mock_db)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_agent
    mock_db.execute = AsyncMock(return_value=mock_result)

    # Act & Assert
    with pytest.raises(ValueError, match="content cannot be empty"):
        await service.store_memory(
            sample_agent.id, "test-tenant", "long_term", {}
        )


@pytest.mark.asyncio
async def test_retrieve_memory_with_embedding(mock_db, sample_agent, sample_memory):
    """Test retrieving memories with semantic search."""
    # Arrange
    service = MemoryConfigService(mock_db)

    # Mock agent validation
    mock_agent_result = MagicMock()
    mock_agent_result.scalar_one_or_none.return_value = sample_agent

    # Mock memory retrieval
    mock_memory_result = MagicMock()
    mock_memory_result.scalars.return_value.all.return_value = [sample_memory]

    mock_db.execute = AsyncMock(
        side_effect=[mock_agent_result, mock_memory_result]
    )

    query_embedding = '[0.1, 0.2, 0.3]'

    # Act
    memories = await service.retrieve_memory(
        sample_agent.id, "test-tenant", query_embedding=query_embedding, limit=5
    )

    # Assert
    assert len(memories) == 1
    assert memories[0].memory_type == "long_term"
    assert memories[0].content["text"] == "User prefers concise responses"


@pytest.mark.asyncio
async def test_retrieve_memory_without_embedding(mock_db, sample_agent, sample_memory):
    """Test retrieving recent memories without semantic search."""
    # Arrange
    service = MemoryConfigService(mock_db)

    mock_agent_result = MagicMock()
    mock_agent_result.scalar_one_or_none.return_value = sample_agent

    mock_memory_result = MagicMock()
    mock_memory_result.scalars.return_value.all.return_value = [sample_memory]

    mock_db.execute = AsyncMock(
        side_effect=[mock_agent_result, mock_memory_result]
    )

    # Act
    memories = await service.retrieve_memory(
        sample_agent.id, "test-tenant", memory_type="long_term", limit=10
    )

    # Assert
    assert len(memories) == 1
    assert memories[0].memory_type == "long_term"


@pytest.mark.asyncio
async def test_clear_memory_all_types(mock_db, sample_agent):
    """Test clearing all memory types."""
    # Arrange
    service = MemoryConfigService(mock_db)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_agent
    mock_db.execute = AsyncMock(return_value=mock_result)

    # Mock delete operation
    mock_delete_result = MagicMock()
    mock_delete_result.rowcount = 15
    mock_db.execute = AsyncMock(
        side_effect=[mock_result, mock_delete_result]
    )
    mock_db.commit = AsyncMock()

    # Act
    deleted_count = await service.clear_memory(sample_agent.id, "test-tenant")

    # Assert
    assert deleted_count == 15
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_clear_memory_specific_type(mock_db, sample_agent):
    """Test clearing specific memory type."""
    # Arrange
    service = MemoryConfigService(mock_db)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_agent

    mock_delete_result = MagicMock()
    mock_delete_result.rowcount = 5

    mock_db.execute = AsyncMock(
        side_effect=[mock_result, mock_delete_result]
    )
    mock_db.commit = AsyncMock()

    # Act
    deleted_count = await service.clear_memory(
        sample_agent.id, "test-tenant", memory_type="short_term"
    )

    # Assert
    assert deleted_count == 5


@pytest.mark.asyncio
async def test_enforce_retention_policy(mock_db, sample_agent):
    """Test retention policy enforcement."""
    # Arrange
    service = MemoryConfigService(mock_db)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_agent

    mock_delete_result = MagicMock()
    mock_delete_result.rowcount = 3

    mock_db.execute = AsyncMock(
        side_effect=[mock_result, mock_delete_result]
    )
    mock_db.commit = AsyncMock()

    # Act
    deleted_count = await service.enforce_retention_policy(
        sample_agent.id, "test-tenant"
    )

    # Assert
    assert deleted_count == 3
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_memory_state(mock_db, sample_agent):
    """Test retrieving complete memory state."""
    # Arrange
    service = MemoryConfigService(mock_db)

    # Create a memory item specific to this test
    test_memory = MemoryItem(
        id=uuid4(),
        agent_id=sample_agent.id,
        memory_type="long_term",
        content={"text": "Test memory", "source": "conversation"},
        embedding='[0.1, 0.2, 0.3]',
        retention_days=90,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    # Mock the retrieve_memory method to return appropriate values
    async def mock_retrieve_memory(agent_id, tenant_id, query_embedding=None, memory_type=None, limit=5):
        """Mock retrieve_memory that returns data based on memory_type."""
        if memory_type == "long_term":
            return [test_memory]
        return []

    # Mock get_memory_config
    async def mock_get_memory_config(agent_id, tenant_id):
        """Mock get_memory_config that returns default config."""
        from src.schemas.memory import MemoryConfig
        return MemoryConfig()

    # Patch the methods
    service.retrieve_memory = mock_retrieve_memory
    service.get_memory_config = mock_get_memory_config

    # Mock stats query for get_memory_state
    mock_stats_row = MagicMock()
    mock_stats_row.memory_type = "long_term"
    mock_stats_row.count = 1
    mock_stats_row.oldest = datetime.now(timezone.utc)
    mock_stats_row.newest = datetime.now(timezone.utc)

    mock_stats_result = MagicMock()
    mock_stats_result.all.return_value = [mock_stats_row]

    # Mock the final stats query
    mock_db.execute = AsyncMock(return_value=mock_stats_result)

    # Act
    memory_state = await service.get_memory_state(sample_agent.id, "test-tenant")

    # Assert
    assert memory_state.agent_id == sample_agent.id
    assert len(memory_state.long_term_memories) == 1
    assert memory_state.stats["total_count"] == 1


@pytest.mark.asyncio
async def test_tenant_isolation(mock_db, sample_agent):
    """Test that tenant_id is enforced for security."""
    # Arrange
    service = MemoryConfigService(mock_db)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # Agent not found for wrong tenant
    mock_db.execute = AsyncMock(return_value=mock_result)

    # Act & Assert
    with pytest.raises(ValueError, match="Agent .* not found"):
        await service.get_memory_config(sample_agent.id, "wrong-tenant")
