"""
Pydantic schemas for agent memory configuration and state.

Defines request/response models for memory CRUD operations,
including configuration, state, and item schemas with validation.
"""

from datetime import datetime
from typing import Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, ConfigDict


from enum import Enum


class VectorDBType(str, Enum):
    """Vector database backend types for long-term memory."""

    POSTGRESQL_PGVECTOR = "postgresql_pgvector"
    EXTERNAL = "external"


class MemoryItem(BaseModel):
    """
    Single memory item entry.

    Represents a memory record stored in agent_memory table.
    """

    id: UUID = Field(..., description="Memory entry ID (UUID)")
    agent_id: UUID = Field(..., description="ID of agent owning this memory")
    memory_type: str = Field(
        ...,
        description="Memory type: short_term, long_term, or agentic",
        pattern="^(short_term|long_term|agentic)$",
    )
    content: dict[str, Any] = Field(..., description="Memory content (flexible structure)")
    embedding: Optional[str] = Field(
        None,
        description="Vector embedding (text format for pgvector, 1536 dims)",
    )
    retention_days: int = Field(
        default=90,
        ge=1,
        le=3650,
        description="Days to retain this memory before auto-deletion",
    )
    created_at: datetime = Field(..., description="Timestamp when memory was created")
    updated_at: datetime = Field(..., description="Timestamp when memory was last updated")

    model_config = ConfigDict(from_attributes=True)


class ShortTermMemoryConfig(BaseModel):
    """Short-term memory configuration."""

    context_window_size: int = Field(
        default=4096,
        ge=256,
        le=32768,
        description="Max tokens in context window",
    )
    conversation_history_length: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Max conversation messages to retain",
    )


class LongTermMemoryConfig(BaseModel):
    """Long-term memory configuration."""

    enabled: bool = Field(
        default=True,
        description="Enable/disable long-term memory with vector similarity search",
    )
    vector_db: str = Field(
        default="postgresql_pgvector",
        pattern="^(postgresql_pgvector|external)$",
        description="Vector database backend: postgresql_pgvector or external (future)",
    )
    retention_days: int = Field(
        default=90,
        ge=1,
        le=3650,
        description="Days to retain memories before auto-deletion",
    )


class AgenticMemoryConfig(BaseModel):
    """Agentic memory configuration."""

    enabled: bool = Field(
        default=False,
        description="Enable/disable agent-managed structured note-taking",
    )
    retention_days: int = Field(
        default=90,
        ge=1,
        le=3650,
        description="Days to retain agentic memories before auto-deletion",
    )


class MemoryConfig(BaseModel):
    """
    Complete agent memory configuration.

    Combines all three memory types (short-term, long-term, agentic)
    with their respective settings.
    """

    short_term: ShortTermMemoryConfig = Field(
        default_factory=ShortTermMemoryConfig,
        description="Short-term conversation memory settings",
    )
    long_term: LongTermMemoryConfig = Field(
        default_factory=LongTermMemoryConfig,
        description="Long-term semantic memory settings",
    )
    agentic: AgenticMemoryConfig = Field(
        default_factory=AgenticMemoryConfig,
        description="Agentic memory settings",
    )


class MemoryConfigUpdate(BaseModel):
    """
    Schema for updating agent memory configuration.

    All fields optional to support partial updates.
    """

    short_term: Optional[ShortTermMemoryConfig] = Field(
        None,
        description="Update short-term memory settings",
    )
    long_term: Optional[LongTermMemoryConfig] = Field(
        None,
        description="Update long-term memory settings",
    )
    agentic: Optional[AgenticMemoryConfig] = Field(
        None,
        description="Update agentic memory settings",
    )


class MemoryState(BaseModel):
    """
    Current memory state for an agent.

    Includes statistics and recent memory entries.
    """

    agent_id: UUID = Field(..., description="Agent ID")
    short_term_memories: list[MemoryItem] = Field(
        default_factory=list,
        description="Recent short-term conversation memories",
    )
    long_term_memories: list[MemoryItem] = Field(
        default_factory=list,
        description="Long-term semantic memories with similarity scores",
    )
    agentic_memories: list[MemoryItem] = Field(
        default_factory=list,
        description="Agent-extracted structured memories",
    )
    memory_config: MemoryConfig = Field(
        ...,
        description="Current memory configuration",
    )
    stats: dict[str, Any] = Field(
        default_factory=dict,
        description="Memory statistics (counts, oldest/newest timestamps)",
    )

    model_config = ConfigDict(from_attributes=True)


class MemoryConfigResponse(BaseModel):
    """API response for memory configuration endpoints."""

    agent_id: UUID = Field(..., description="Agent ID")
    config: MemoryConfig = Field(..., description="Memory configuration")
    updated_at: datetime = Field(..., description="Timestamp of last update")

    model_config = ConfigDict(from_attributes=True)


class MemoryClearRequest(BaseModel):
    """Request to clear agent memory."""

    memory_type: Optional[str] = Field(
        None,
        pattern="^(short_term|long_term|agentic)?$",
        description="Memory type to clear (None = all types)",
    )


class MemoryClearResponse(BaseModel):
    """Response after clearing agent memory."""

    agent_id: UUID = Field(..., description="Agent ID")
    cleared_count: int = Field(..., ge=0, description="Number of memories cleared")
    memory_type: Optional[str] = Field(
        None,
        description="Memory type cleared",
    )
    cleared_at: datetime = Field(..., description="Timestamp of clearing")


class MemoryHistoryResponse(BaseModel):
    """Paginated response for memory history retrieval."""

    agent_id: UUID = Field(..., description="Agent ID")
    memories: list[MemoryItem] = Field(
        ...,
        description="List of memory items",
    )
    total_count: int = Field(
        ...,
        ge=0,
        description="Total number of memories matching filter",
    )
    page: int = Field(
        default=1,
        ge=1,
        description="Current page number (1-indexed)",
    )
    page_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of items per page",
    )
    has_more: bool = Field(
        ...,
        description="Whether there are more pages available",
    )
