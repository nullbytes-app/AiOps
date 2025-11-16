"""
Memory configuration service layer for agent memory CRUD operations.

Implements memory management including configuration, storage, retrieval,
vector similarity search, and retention policy enforcement. Follows async
patterns with tenant isolation and OpenAI API integration for embeddings.

Story 8.15: Memory Configuration UI - Service layer (Task 2)
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, delete, desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Agent, AgentMemory
from src.schemas.memory import (
    MemoryConfig,
    MemoryConfigUpdate,
    MemoryItem,
    MemoryState,
)
from src.utils.logger import logger


class MemoryConfigService:
    """
    Service layer for agent memory configuration and management.

    Provides business logic for memory CRUD operations with tenant isolation,
    vector similarity search, and retention policy enforcement.

    All methods enforce agent ownership validation to prevent unauthorized access.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize memory config service.

        Args:
            db: Async SQLAlchemy database session
        """
        self.db = db

    async def get_memory_config(
        self, agent_id: UUID, tenant_id: str
    ) -> Optional[MemoryConfig]:
        """
        Get agent memory configuration.

        Retrieves memory configuration from agent.memory_config JSONB column.
        Returns default configuration if not set.

        Args:
            agent_id: Agent UUID
            tenant_id: Tenant identifier for isolation

        Returns:
            Optional[MemoryConfig]: Memory configuration or None if agent not found

        Raises:
            ValueError: If agent not found or tenant mismatch
        """
        # Reason: Enforce tenant isolation by checking both agent_id and tenant_id
        stmt = select(Agent).where(
            and_(Agent.id == agent_id, Agent.tenant_id == tenant_id)
        )
        result = await self.db.execute(stmt)
        agent = result.scalar_one_or_none()

        if not agent:
            raise ValueError(f"Agent {agent_id} not found for tenant {tenant_id}")

        # Reason: Return default configuration if memory_config is None
        if agent.memory_config is None:
            return MemoryConfig()

        return MemoryConfig(**agent.memory_config)

    async def update_memory_config(
        self,
        agent_id: UUID,
        tenant_id: str,
        config_update: MemoryConfigUpdate,
    ) -> MemoryConfig:
        """
        Update agent memory configuration with validation.

        Performs partial update of memory configuration, merging new values
        with existing configuration. Updates Agent.memory_config JSONB column.

        Args:
            agent_id: Agent UUID
            tenant_id: Tenant identifier for isolation
            config_update: Memory configuration updates

        Returns:
            MemoryConfig: Updated memory configuration

        Raises:
            ValueError: If agent not found or tenant mismatch
        """
        # Fetch current agent with tenant isolation
        stmt = select(Agent).where(
            and_(Agent.id == agent_id, Agent.tenant_id == tenant_id)
        )
        result = await self.db.execute(stmt)
        agent = result.scalar_one_or_none()

        if not agent:
            raise ValueError(f"Agent {agent_id} not found for tenant {tenant_id}")

        # Get current config or initialize default
        current_config = (
            MemoryConfig(**agent.memory_config)
            if agent.memory_config
            else MemoryConfig()
        )

        # Reason: Merge update with current config (partial update support)
        if config_update.short_term:
            current_config.short_term = config_update.short_term
        if config_update.long_term:
            current_config.long_term = config_update.long_term
        if config_update.agentic:
            current_config.agentic = config_update.agentic

        # Update agent memory_config column
        agent.memory_config = current_config.model_dump()
        agent.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(agent)

        logger.info(
            f"Updated memory config for agent {agent_id} (tenant: {tenant_id})"
        )

        return current_config

    async def store_memory(
        self,
        agent_id: UUID,
        tenant_id: str,
        memory_type: str,
        content: Dict,
        embedding: Optional[str] = None,
    ) -> MemoryItem:
        """
        Store new memory with optional embedding.

        Creates new memory record in agent_memory table. Embedding generation
        is handled by EmbeddingService (Task 7) before calling this method.

        Args:
            agent_id: Agent UUID
            tenant_id: Tenant identifier for isolation
            memory_type: Memory type (short_term, long_term, agentic)
            content: Memory content (flexible JSONB)
            embedding: Optional vector embedding (text format, 1536 dims)

        Returns:
            MemoryItem: Created memory item

        Raises:
            ValueError: If agent not found, invalid memory_type, or content empty
        """
        # Validate agent exists and tenant matches
        stmt = select(Agent).where(
            and_(Agent.id == agent_id, Agent.tenant_id == tenant_id)
        )
        result = await self.db.execute(stmt)
        agent = result.scalar_one_or_none()

        if not agent:
            raise ValueError(f"Agent {agent_id} not found for tenant {tenant_id}")

        # Validate memory type
        if memory_type not in ["short_term", "long_term", "agentic"]:
            raise ValueError(
                f"Invalid memory_type: {memory_type}. Must be short_term, long_term, or agentic"
            )

        # Validate content not empty
        if not content:
            raise ValueError("Memory content cannot be empty")

        # Get retention days from agent memory config
        config = await self.get_memory_config(agent_id, tenant_id)
        if memory_type == "short_term":
            retention_days = 7  # Reason: Short-term memories expire quickly
        elif memory_type == "long_term":
            retention_days = config.long_term.retention_days
        else:  # agentic
            retention_days = config.agentic.retention_days

        # Create new memory record
        memory = AgentMemory(
            agent_id=agent_id,
            tenant_id=tenant_id,
            memory_type=memory_type,
            content=content,
            embedding=embedding,
            retention_days=retention_days,
        )

        self.db.add(memory)
        await self.db.commit()
        await self.db.refresh(memory)

        logger.info(
            f"Stored {memory_type} memory for agent {agent_id} (tenant: {tenant_id})"
        )

        return MemoryItem(
            id=memory.id,
            agent_id=memory.agent_id,
            memory_type=memory.memory_type,
            content=memory.content,
            embedding=memory.embedding,
            retention_days=memory.retention_days,
            created_at=memory.created_at,
            updated_at=memory.updated_at,
        )

    async def retrieve_memory(
        self,
        agent_id: UUID,
        tenant_id: str,
        query_embedding: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 5,
    ) -> List[MemoryItem]:
        """
        Retrieve memories with optional vector similarity search.

        If query_embedding is provided, performs pgvector cosine similarity search.
        Otherwise, returns most recent memories by created_at DESC.

        Args:
            agent_id: Agent UUID
            tenant_id: Tenant identifier for isolation
            query_embedding: Optional query embedding for similarity search
            memory_type: Optional filter by memory type
            limit: Maximum number of results (default: 5)

        Returns:
            List[MemoryItem]: List of matching memories

        Raises:
            ValueError: If agent not found or tenant mismatch
        """
        # Validate agent exists and tenant matches
        stmt = select(Agent).where(
            and_(Agent.id == agent_id, Agent.tenant_id == tenant_id)
        )
        result = await self.db.execute(stmt)
        agent = result.scalar_one_or_none()

        if not agent:
            raise ValueError(f"Agent {agent_id} not found for tenant {tenant_id}")

        # Build base query
        conditions = [AgentMemory.agent_id == agent_id]

        if memory_type:
            conditions.append(AgentMemory.memory_type == memory_type)

        # Reason: Use vector similarity search if query embedding provided
        if query_embedding:
            # pgvector cosine similarity search using <-> operator
            # Note: Requires pgvector extension and vector index created
            stmt = (
                select(AgentMemory)
                .where(and_(*conditions))
                .where(AgentMemory.embedding.isnot(None))
                .order_by(
                    text(f"embedding <-> '{query_embedding}'::vector")
                )  # Cosine distance
                .limit(limit)
            )
        else:
            # Fallback: Return most recent memories
            stmt = (
                select(AgentMemory)
                .where(and_(*conditions))
                .order_by(desc(AgentMemory.created_at))
                .limit(limit)
            )

        result = await self.db.execute(stmt)
        memories = result.scalars().all()

        logger.info(
            f"Retrieved {len(memories)} memories for agent {agent_id} (type: {memory_type}, semantic: {bool(query_embedding)})"
        )

        return [
            MemoryItem(
                id=m.id,
                agent_id=m.agent_id,
                memory_type=m.memory_type,
                content=m.content,
                embedding=m.embedding,
                retention_days=m.retention_days,
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
            for m in memories
        ]

    async def clear_memory(
        self,
        agent_id: UUID,
        tenant_id: str,
        memory_type: Optional[str] = None,
    ) -> int:
        """
        Clear agent memory with optional type filter.

        Deletes memory records from agent_memory table. If memory_type is None,
        clears all memory types (short_term, long_term, agentic).

        Args:
            agent_id: Agent UUID
            tenant_id: Tenant identifier for isolation
            memory_type: Optional memory type filter (None = clear all)

        Returns:
            int: Number of memories deleted

        Raises:
            ValueError: If agent not found or tenant mismatch
        """
        # Validate agent exists and tenant matches
        stmt = select(Agent).where(
            and_(Agent.id == agent_id, Agent.tenant_id == tenant_id)
        )
        result = await self.db.execute(stmt)
        agent = result.scalar_one_or_none()

        if not agent:
            raise ValueError(f"Agent {agent_id} not found for tenant {tenant_id}")

        # Build delete statement
        conditions = [AgentMemory.agent_id == agent_id]

        if memory_type:
            conditions.append(AgentMemory.memory_type == memory_type)

        stmt = delete(AgentMemory).where(and_(*conditions))

        result = await self.db.execute(stmt)
        await self.db.commit()

        deleted_count = result.rowcount

        logger.info(
            f"Cleared {deleted_count} memories for agent {agent_id} (type: {memory_type or 'all'})"
        )

        return deleted_count

    async def enforce_retention_policy(self, agent_id: UUID, tenant_id: str) -> int:
        """
        Enforce retention policy by deleting expired memories.

        Deletes memories older than retention_days based on created_at timestamp.
        Respects per-memory retention_days setting.

        Args:
            agent_id: Agent UUID
            tenant_id: Tenant identifier for isolation

        Returns:
            int: Number of memories deleted

        Raises:
            ValueError: If agent not found or tenant mismatch
        """
        # Validate agent exists and tenant matches
        stmt = select(Agent).where(
            and_(Agent.id == agent_id, Agent.tenant_id == tenant_id)
        )
        result = await self.db.execute(stmt)
        agent = result.scalar_one_or_none()

        if not agent:
            raise ValueError(f"Agent {agent_id} not found for tenant {tenant_id}")

        # Reason: Delete memories where created_at + retention_days < now
        # Use PostgreSQL interval arithmetic for timestamp comparison
        stmt = delete(AgentMemory).where(
            and_(
                AgentMemory.agent_id == agent_id,
                text(
                    "created_at + make_interval(days => retention_days) < NOW()"
                ),  # PostgreSQL interval arithmetic
            )
        )

        result = await self.db.execute(stmt)
        await self.db.commit()

        deleted_count = result.rowcount

        if deleted_count > 0:
            logger.info(
                f"Retention policy: Deleted {deleted_count} expired memories for agent {agent_id}"
            )

        return deleted_count

    async def get_memory_state(
        self, agent_id: UUID, tenant_id: str, limit_per_type: int = 10
    ) -> MemoryState:
        """
        Get complete memory state for an agent.

        Retrieves memory configuration and recent memories across all types
        for display in Memory tab UI.

        Args:
            agent_id: Agent UUID
            tenant_id: Tenant identifier for isolation
            limit_per_type: Max memories to return per type (default: 10)

        Returns:
            MemoryState: Complete memory state

        Raises:
            ValueError: If agent not found or tenant mismatch
        """
        # Get memory configuration
        config = await self.get_memory_config(agent_id, tenant_id)

        # Retrieve memories for each type
        short_term = await self.retrieve_memory(
            agent_id, tenant_id, memory_type="short_term", limit=limit_per_type
        )
        long_term = await self.retrieve_memory(
            agent_id, tenant_id, memory_type="long_term", limit=limit_per_type
        )
        agentic = await self.retrieve_memory(
            agent_id, tenant_id, memory_type="agentic", limit=limit_per_type
        )

        # Calculate statistics
        stmt = (
            select(
                AgentMemory.memory_type,
                func.count(AgentMemory.id).label("count"),
                func.min(AgentMemory.created_at).label("oldest"),
                func.max(AgentMemory.created_at).label("newest"),
            )
            .where(AgentMemory.agent_id == agent_id)
            .group_by(AgentMemory.memory_type)
        )

        result = await self.db.execute(stmt)
        stats_rows = result.all()

        stats = {
            "by_type": {
                row.memory_type: {
                    "count": row.count,
                    "oldest": row.oldest.isoformat() if row.oldest else None,
                    "newest": row.newest.isoformat() if row.newest else None,
                }
                for row in stats_rows
            },
            "total_count": sum(row.count for row in stats_rows),
        }

        return MemoryState(
            agent_id=agent_id,
            short_term_memories=short_term,
            long_term_memories=long_term,
            agentic_memories=agentic,
            memory_config=config,
            stats=stats,
        )
