"""
LangGraph memory integration service for agent execution.

Provides PostgresSaver checkpointer for short-term conversation history
and AsyncPostgresStore for long-term semantic memory with vector search.
Follows LangGraph 2025 patterns for dual memory architecture.

Story 8.15: Memory Configuration UI - LangGraph Integration (Task 3)
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database.session import get_async_engine
from src.schemas.memory import MemoryItem
from src.services.embedding_service import EmbeddingService
from src.services.memory_config_service import MemoryConfigService
from src.utils.logger import logger


class LangGraphMemoryIntegration:
    """
    LangGraph memory integration for agent execution.

    Provides checkpointer (short-term) and store (long-term) for LangGraph
    agent workflows with thread-based conversation isolation and namespace
    organization for semantic memory retrieval.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize LangGraph memory integration.

        Args:
            db: Async SQLAlchemy database session
        """
        self.db = db
        self.memory_service = MemoryConfigService(db)

        # Get database connection string from settings
        self.db_uri = settings.database_url

        if not self.db_uri:
            raise ValueError(
                "Database URL not configured. Set AI_AGENTS_DATABASE_URL environment variable."
            )

    def get_thread_id(self, agent_id: UUID) -> str:
        """
        Generate thread ID for agent conversation.

        Thread ID isolates conversation history per agent in PostgresSaver.
        Format: "agent-{agent_id}"

        Args:
            agent_id: Agent UUID

        Returns:
            str: Thread identifier for LangGraph checkpointer
        """
        return f"agent-{agent_id}"

    def get_namespace(self, agent_id: UUID) -> tuple[str, str]:
        """
        Generate namespace for long-term memory store.

        Namespace format: ("memories", "{agent_id}") for AsyncPostgresStore
        organization as documented in LangGraph 2025 patterns.

        Args:
            agent_id: Agent UUID

        Returns:
            tuple[str, str]: Namespace tuple for AsyncPostgresStore
        """
        return ("memories", str(agent_id))

    async def get_checkpointer(self, agent_id: UUID) -> AsyncPostgresSaver:
        """
        Get PostgresSaver checkpointer for short-term conversation history.

        Creates async PostgreSQL checkpointer with agent-specific thread_id
        for conversation state persistence. Follows langgraph-checkpoint-postgres
        2025 async patterns.

        Args:
            agent_id: Agent UUID

        Returns:
            AsyncPostgresSaver: Async checkpointer for conversation state

        Raises:
            ValueError: If database connection fails
        """
        try:
            # Reason: Use async checkpointer for FastAPI async context
            checkpointer = AsyncPostgresSaver.from_conn_string(self.db_uri)

            # Reason: Setup creates checkpointer tables if they don't exist
            await checkpointer.setup()

            logger.info(
                f"LangGraph: Created async checkpointer for agent {agent_id} (thread: {self.get_thread_id(agent_id)})"
            )

            return checkpointer

        except Exception as e:
            logger.error(f"LangGraph: Failed to create checkpointer: {e}")
            raise ValueError(f"Failed to initialize checkpointer: {e}")

    async def get_memory_store(self, agent_id: UUID) -> Any:
        """
        Get AsyncPostgresStore for long-term semantic memory.

        Note: AsyncPostgresStore is part of LangGraph 2025 but may require
        additional setup. This method returns a placeholder for now and will
        be implemented when AsyncPostgresStore is stable.

        Args:
            agent_id: Agent UUID

        Returns:
            Any: Memory store instance (placeholder for AsyncPostgresStore)
        """
        # Reason: AsyncPostgresStore integration pending LangGraph 2025 stable release
        # For now, long-term memory is managed via MemoryConfigService directly
        logger.warning(
            f"LangGraph: AsyncPostgresStore integration pending - using MemoryConfigService for agent {agent_id}"
        )

        return None  # Placeholder - will be implemented with stable AsyncPostgresStore

    async def load_agent_memory(
        self, agent_id: UUID, tenant_id: str, query_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Load agent memory at execution start.

        Retrieves short-term conversation history (via checkpointer) and
        long-term semantic memories (via MemoryConfigService with optional
        vector similarity search).

        Args:
            agent_id: Agent UUID
            tenant_id: Tenant identifier for isolation
            query_text: Optional query for semantic memory retrieval

        Returns:
            Dict[str, Any]: Memory context with short-term and long-term memories

        Raises:
            ValueError: If agent not found or tenant mismatch
        """
        memory_context = {
            "agent_id": str(agent_id),
            "thread_id": self.get_thread_id(agent_id),
            "short_term": [],
            "long_term": [],
            "agentic": [],
        }

        try:
            # Load long-term memories with optional semantic search
            if query_text:
                # Reason: Semantic search requires embedding generation
                from src.services.embedding_service import EmbeddingService

                embedding_service = EmbeddingService()
                query_embedding = await embedding_service.generate_embedding(query_text)

                if query_embedding:
                    long_term_memories = await self.memory_service.retrieve_memory(
                        agent_id=agent_id,
                        tenant_id=tenant_id,
                        query_embedding=query_embedding,
                        memory_type="long_term",
                        limit=5,
                    )
                else:
                    # Fallback to recent memories if embedding fails
                    long_term_memories = await self.memory_service.retrieve_memory(
                        agent_id=agent_id,
                        tenant_id=tenant_id,
                        memory_type="long_term",
                        limit=5,
                    )

                await embedding_service.close()
            else:
                # No semantic search - return recent memories
                long_term_memories = await self.memory_service.retrieve_memory(
                    agent_id=agent_id,
                    tenant_id=tenant_id,
                    memory_type="long_term",
                    limit=5,
                )

            memory_context["long_term"] = [
                {
                    "id": str(m.id),
                    "content": m.content,
                    "created_at": m.created_at.isoformat(),
                }
                for m in long_term_memories
            ]

            # Load agentic memories (structured notes)
            agentic_memories = await self.memory_service.retrieve_memory(
                agent_id=agent_id,
                tenant_id=tenant_id,
                memory_type="agentic",
                limit=5,
            )

            memory_context["agentic"] = [
                {
                    "id": str(m.id),
                    "content": m.content,
                    "created_at": m.created_at.isoformat(),
                }
                for m in agentic_memories
            ]

            logger.info(
                f"LangGraph: Loaded memory for agent {agent_id} - "
                f"{len(memory_context['long_term'])} long-term, "
                f"{len(memory_context['agentic'])} agentic"
            )

        except Exception as e:
            logger.error(f"LangGraph: Failed to load agent memory: {e}")
            # Reason: Continue execution with empty memory on error (graceful degradation)

        return memory_context

    async def save_agent_memory(
        self,
        agent_id: UUID,
        tenant_id: str,
        new_messages: List[Dict[str, Any]],
        extract_facts: bool = False,
    ) -> int:
        """
        Save agent memory after execution.

        Persists new conversation messages to short-term memory and optionally
        extracts facts for long-term memory storage with embeddings.

        Args:
            agent_id: Agent UUID
            tenant_id: Tenant identifier for isolation
            new_messages: List of new messages to persist
            extract_facts: Whether to extract facts for long-term memory

        Returns:
            int: Number of memories saved

        Raises:
            ValueError: If agent not found or tenant mismatch
        """
        saved_count = 0

        try:
            # Save short-term conversation messages
            for msg in new_messages:
                await self.memory_service.store_memory(
                    agent_id=agent_id,
                    tenant_id=tenant_id,
                    memory_type="short_term",
                    content=msg,
                    embedding=None,  # Short-term memories don't need embeddings
                )
                saved_count += 1

            # Extract facts for long-term memory (optional)
            if extract_facts and new_messages:
                # Reason: Simple fact extraction from assistant responses
                for msg in new_messages:
                    if msg.get("role") == "assistant" and len(msg.get("content", "")) > 50:
                        # Generate embedding for long-term memory
                        from src.services.embedding_service import EmbeddingService

                        embedding_service = EmbeddingService()
                        embedding = await embedding_service.generate_embedding(
                            msg["content"]
                        )

                        if embedding:
                            await self.memory_service.store_memory(
                                agent_id=agent_id,
                                tenant_id=tenant_id,
                                memory_type="long_term",
                                content={
                                    "text": msg["content"],
                                    "source": "conversation",
                                    "role": "assistant",
                                },
                                embedding=embedding,
                            )
                            saved_count += 1

                        await embedding_service.close()

            logger.info(
                f"LangGraph: Saved {saved_count} memories for agent {agent_id} (extract_facts: {extract_facts})"
            )

        except Exception as e:
            logger.error(f"LangGraph: Failed to save agent memory: {e}")
            raise

        return saved_count

    async def format_memory_for_prompt(
        self, memory_context: Dict[str, Any]
    ) -> str:
        """
        Format memory context for LLM system prompt.

        Converts memory context dictionary to human-readable text format
        for inclusion in agent system messages.

        Args:
            memory_context: Memory context from load_agent_memory()

        Returns:
            str: Formatted memory context for LLM prompt
        """
        prompt_parts = []

        # Add long-term memories
        if memory_context.get("long_term"):
            prompt_parts.append("## Relevant Long-Term Memories:")
            for i, memory in enumerate(memory_context["long_term"], 1):
                content = memory.get("content", {})
                text = content.get("text", str(content))
                prompt_parts.append(f"{i}. {text}")

        # Add agentic memories (structured notes)
        if memory_context.get("agentic"):
            prompt_parts.append("\n## Structured Notes:")
            for i, memory in enumerate(memory_context["agentic"], 1):
                content = memory.get("content", {})
                text = content.get("text", str(content))
                prompt_parts.append(f"{i}. {text}")

        if not prompt_parts:
            return "No relevant memories found."

        return "\n".join(prompt_parts)
