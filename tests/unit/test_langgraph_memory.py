"""
Unit tests for LangGraphMemoryIntegration.

Tests checkpointer creation, memory loading/saving, and LangGraph
integration patterns.

Story 8.15: Memory Configuration UI - Unit Tests (Task 9.2)
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.langgraph_memory import LangGraphMemoryIntegration


@pytest.fixture
def mock_db():
    """Fixture for mocked async database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def agent_id():
    """Fixture for sample agent ID."""
    return uuid4()


@pytest.fixture
def langgraph_integration(mock_db):
    """Fixture for LangGraphMemoryIntegration service."""
    with patch('src.services.langgraph_memory.settings') as mock_settings:
        mock_settings.database_url = "postgresql+asyncpg://test@localhost/testdb"
        return LangGraphMemoryIntegration(mock_db)


def test_get_thread_id(langgraph_integration, agent_id):
    """Test thread ID generation for agent."""
    # Act
    thread_id = langgraph_integration.get_thread_id(agent_id)

    # Assert
    assert thread_id == f"agent-{agent_id}"
    assert isinstance(thread_id, str)


def test_get_namespace(langgraph_integration, agent_id):
    """Test namespace generation for long-term memory store."""
    # Act
    namespace = langgraph_integration.get_namespace(agent_id)

    # Assert
    assert isinstance(namespace, tuple)
    assert len(namespace) == 2
    assert namespace[0] == "memories"
    assert namespace[1] == str(agent_id)


@pytest.mark.asyncio
async def test_get_checkpointer(langgraph_integration, agent_id):
    """Test PostgresSaver checkpointer creation."""
    # Arrange
    with patch('src.services.langgraph_memory.AsyncPostgresSaver') as MockSaver:
        mock_checkpointer = AsyncMock()
        mock_checkpointer.setup = AsyncMock()
        MockSaver.from_conn_string.return_value = mock_checkpointer

        # Act
        checkpointer = await langgraph_integration.get_checkpointer(agent_id)

        # Assert
        assert checkpointer == mock_checkpointer
        MockSaver.from_conn_string.assert_called_once_with(
            langgraph_integration.db_uri
        )
        mock_checkpointer.setup.assert_called_once()


@pytest.mark.asyncio
async def test_get_checkpointer_error(langgraph_integration, agent_id):
    """Test ValueError when checkpointer creation fails."""
    # Arrange
    with patch('src.services.langgraph_memory.AsyncPostgresSaver') as MockSaver:
        MockSaver.from_conn_string.side_effect = Exception("Connection failed")

        # Act & Assert
        with pytest.raises(ValueError, match="Failed to initialize checkpointer"):
            await langgraph_integration.get_checkpointer(agent_id)


@pytest.mark.asyncio
async def test_get_memory_store_placeholder(langgraph_integration, agent_id):
    """Test memory store returns None (placeholder implementation)."""
    # Act
    store = await langgraph_integration.get_memory_store(agent_id)

    # Assert
    assert store is None  # Placeholder until AsyncPostgresStore stable


@pytest.mark.asyncio
async def test_load_agent_memory_without_query(langgraph_integration, agent_id, mock_db):
    """Test loading agent memory without semantic search."""
    # Arrange
    mock_memory_service = MagicMock()
    mock_memory_service.retrieve_memory = AsyncMock(
        side_effect=[
            [],  # Long-term memories
            [],  # Agentic memories
        ]
    )

    with patch.object(
        langgraph_integration, 'memory_service', mock_memory_service
    ):
        # Act
        memory_context = await langgraph_integration.load_agent_memory(
            agent_id, "test-tenant", query_text=None
        )

        # Assert
        assert memory_context["agent_id"] == str(agent_id)
        assert memory_context["thread_id"] == f"agent-{agent_id}"
        assert memory_context["long_term"] == []
        assert memory_context["agentic"] == []


@pytest.mark.asyncio
async def test_load_agent_memory_with_query(langgraph_integration, agent_id):
    """Test loading agent memory with semantic search."""
    # Arrange
    mock_memory_item = MagicMock()
    mock_memory_item.id = uuid4()
    mock_memory_item.content = {"text": "Test memory", "source": "conversation"}
    mock_memory_item.created_at = datetime.now(timezone.utc)

    mock_memory_service = MagicMock()
    mock_memory_service.retrieve_memory = AsyncMock(
        return_value=[mock_memory_item]
    )

    with patch.object(
        langgraph_integration, 'memory_service', mock_memory_service
    ):
        # Patch EmbeddingService where it's imported in the function
        with patch('src.services.embedding_service.EmbeddingService') as MockEmbedding:
            mock_embedding_service = AsyncMock()
            mock_embedding_service.generate_embedding = AsyncMock(
                return_value='[0.1, 0.2, 0.3]'
            )
            mock_embedding_service.close = AsyncMock()
            MockEmbedding.return_value = mock_embedding_service

            # Act
            memory_context = await langgraph_integration.load_agent_memory(
                agent_id, "test-tenant", query_text="What does user prefer?"
            )

            # Assert
            assert len(memory_context["long_term"]) == 1
            assert memory_context["long_term"][0]["content"]["text"] == "Test memory"
            mock_embedding_service.generate_embedding.assert_called_once()


@pytest.mark.asyncio
async def test_load_agent_memory_embedding_failure(langgraph_integration, agent_id):
    """Test memory loading falls back when embedding generation fails."""
    # Arrange
    mock_memory_item = MagicMock()
    mock_memory_item.id = uuid4()
    mock_memory_item.content = {"text": "Fallback memory"}
    mock_memory_item.created_at = datetime.now(timezone.utc)

    mock_memory_service = MagicMock()
    mock_memory_service.retrieve_memory = AsyncMock(
        return_value=[mock_memory_item]
    )

    with patch.object(
        langgraph_integration, 'memory_service', mock_memory_service
    ):
        with patch('src.services.langgraph_memory.EmbeddingService') as MockEmbedding:
            mock_embedding_service = AsyncMock()
            mock_embedding_service.generate_embedding = AsyncMock(
                return_value=None  # Embedding fails
            )
            mock_embedding_service.close = AsyncMock()
            MockEmbedding.return_value = mock_embedding_service

            # Act
            memory_context = await langgraph_integration.load_agent_memory(
                agent_id, "test-tenant", query_text="Query text"
            )

            # Assert - should fallback to recent memories
            assert len(memory_context["long_term"]) == 1
            mock_memory_service.retrieve_memory.assert_called()


@pytest.mark.asyncio
async def test_save_agent_memory_success(langgraph_integration, agent_id):
    """Test saving agent memory after execution."""
    # Arrange
    new_messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi! How can I help?"},
    ]

    mock_memory_service = MagicMock()
    mock_memory_service.store_memory = AsyncMock()

    with patch.object(
        langgraph_integration, 'memory_service', mock_memory_service
    ):
        # Act
        saved_count = await langgraph_integration.save_agent_memory(
            agent_id, "test-tenant", new_messages, extract_facts=False
        )

        # Assert
        assert saved_count == 2
        assert mock_memory_service.store_memory.call_count == 2


@pytest.mark.asyncio
async def test_save_agent_memory_with_fact_extraction(langgraph_integration, agent_id):
    """Test saving memory with fact extraction for long-term storage."""
    # Arrange
    new_messages = [
        {"role": "assistant", "content": "The user prefers short and concise responses with bullet points."},
    ]

    mock_memory_service = MagicMock()
    mock_memory_service.store_memory = AsyncMock()

    with patch.object(
        langgraph_integration, 'memory_service', mock_memory_service
    ):
        # Patch EmbeddingService where it's imported in the function
        with patch('src.services.embedding_service.EmbeddingService') as MockEmbedding:
            mock_embedding_service = AsyncMock()
            mock_embedding_service.generate_embedding = AsyncMock(
                return_value='[0.1, 0.2, 0.3]'
            )
            mock_embedding_service.close = AsyncMock()
            MockEmbedding.return_value = mock_embedding_service

            # Act
            saved_count = await langgraph_integration.save_agent_memory(
                agent_id, "test-tenant", new_messages, extract_facts=True
            )

            # Assert
            assert saved_count == 2  # 1 short-term + 1 long-term
            mock_embedding_service.generate_embedding.assert_called_once()


@pytest.mark.asyncio
async def test_format_memory_for_prompt_with_memories(langgraph_integration):
    """Test formatting memory context for LLM prompt."""
    # Arrange
    memory_context = {
        "long_term": [
            {
                "content": {"text": "User prefers concise responses"},
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ],
        "agentic": [
            {
                "content": {"text": "User works in healthcare industry"},
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ],
    }

    # Act
    formatted = await langgraph_integration.format_memory_for_prompt(memory_context)

    # Assert
    assert "Relevant Long-Term Memories" in formatted
    assert "Structured Notes" in formatted
    assert "User prefers concise responses" in formatted
    assert "User works in healthcare industry" in formatted


@pytest.mark.asyncio
async def test_format_memory_for_prompt_empty(langgraph_integration):
    """Test formatting empty memory context."""
    # Arrange
    memory_context = {"long_term": [], "agentic": []}

    # Act
    formatted = await langgraph_integration.format_memory_for_prompt(memory_context)

    # Assert
    assert formatted == "No relevant memories found."
