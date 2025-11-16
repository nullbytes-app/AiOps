"""
Memory configuration API endpoints for agent memory management.

Provides REST API for memory configuration CRUD, state retrieval,
memory clearing, and history pagination with tenant isolation.

Story 8.15: Memory Configuration UI - API Layer (Task 4)
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_tenant_id
from src.database.session import get_async_session
from src.schemas.memory import (
    MemoryClearResponse,
    MemoryConfig,
    MemoryConfigResponse,
    MemoryConfigUpdate,
    MemoryHistoryResponse,
    MemoryState,
)
from src.services.memory_config_service import MemoryConfigService
from src.utils.logger import logger

# Create API router with prefix
router = APIRouter(prefix="/api/agents", tags=["memory"])


@router.get(
    "/{agent_id}/memory/config",
    response_model=MemoryConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Get agent memory configuration",
    description="Retrieve current memory configuration for specified agent with tenant isolation.",
)
async def get_memory_config(
    agent_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_async_session),
) -> MemoryConfigResponse:
    """
    Get agent memory configuration.

    Retrieves memory configuration from Agent.memory_config JSONB column
    with default values if not set.

    Args:
        agent_id: Agent UUID path parameter
        tenant_id: Tenant identifier from auth dependency
        db: Database session dependency

    Returns:
        MemoryConfigResponse: Memory configuration with timestamps

    Raises:
        HTTPException 404: If agent not found or tenant mismatch
        HTTPException 500: If database error occurs
    """
    service = MemoryConfigService(db)

    try:
        config = await service.get_memory_config(agent_id, tenant_id)

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found",
            )

        # Fetch agent updated_at timestamp
        from sqlalchemy import select
        from src.database.models import Agent

        stmt = select(Agent.created_at, Agent.updated_at).where(Agent.id == agent_id)
        result = await db.execute(stmt)
        row = result.one()

        return MemoryConfigResponse(
            agent_id=agent_id,
            config=config,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    except ValueError as e:
        logger.warning(f"GET memory config failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"GET memory config error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve memory configuration",
        )


@router.put(
    "/{agent_id}/memory/config",
    response_model=MemoryConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Update agent memory configuration",
    description="Update memory settings with validation and tenant isolation.",
)
async def update_memory_config(
    agent_id: UUID,
    config_update: MemoryConfigUpdate,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_async_session),
) -> MemoryConfigResponse:
    """
    Update agent memory configuration.

    Performs partial update of memory configuration, merging new values
    with existing settings. Validates configuration constraints.

    Args:
        agent_id: Agent UUID path parameter
        config_update: Memory configuration updates
        tenant_id: Tenant identifier from auth dependency
        db: Database session dependency

    Returns:
        MemoryConfigResponse: Updated memory configuration

    Raises:
        HTTPException 404: If agent not found or tenant mismatch
        HTTPException 422: If validation fails
        HTTPException 500: If database error occurs
    """
    service = MemoryConfigService(db)

    try:
        updated_config = await service.update_memory_config(
            agent_id, tenant_id, config_update
        )

        # Fetch updated agent timestamp
        from sqlalchemy import select
        from src.database.models import Agent

        stmt = select(Agent.created_at, Agent.updated_at).where(Agent.id == agent_id)
        result = await db.execute(stmt)
        row = result.one()

        logger.info(f"Updated memory config for agent {agent_id} (tenant: {tenant_id})")

        return MemoryConfigResponse(
            agent_id=agent_id,
            config=updated_config,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    except ValueError as e:
        logger.warning(f"PUT memory config failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"PUT memory config error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update memory configuration",
        )


@router.get(
    "/{agent_id}/memory/state",
    response_model=MemoryState,
    status_code=status.HTTP_200_OK,
    summary="Get agent memory state",
    description="Retrieve complete memory state including configuration and recent memories.",
)
async def get_memory_state(
    agent_id: UUID,
    limit_per_type: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Max memories to return per type",
    ),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_async_session),
) -> MemoryState:
    """
    Get complete memory state for agent.

    Retrieves memory configuration and recent memories across all types
    (short-term, long-term, agentic) for display in Memory tab UI.

    Args:
        agent_id: Agent UUID path parameter
        limit_per_type: Max memories per type (default: 10)
        tenant_id: Tenant identifier from auth dependency
        db: Database session dependency

    Returns:
        MemoryState: Complete memory state with configuration and memories

    Raises:
        HTTPException 404: If agent not found or tenant mismatch
        HTTPException 500: If database error occurs
    """
    service = MemoryConfigService(db)

    try:
        memory_state = await service.get_memory_state(
            agent_id, tenant_id, limit_per_type=limit_per_type
        )

        logger.info(
            f"Retrieved memory state for agent {agent_id} (tenant: {tenant_id})"
        )

        return memory_state

    except ValueError as e:
        logger.warning(f"GET memory state failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"GET memory state error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve memory state",
        )


@router.delete(
    "/{agent_id}/memory",
    response_model=MemoryClearResponse,
    status_code=status.HTTP_200_OK,
    summary="Clear agent memory",
    description="Delete agent memories with optional type filter (None = clear all types).",
)
async def clear_memory(
    agent_id: UUID,
    memory_type: Optional[str] = Query(
        default=None,
        regex="^(short_term|long_term|agentic)?$",
        description="Memory type to clear (omit to clear all types)",
    ),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_async_session),
) -> MemoryClearResponse:
    """
    Clear agent memory with optional type filter.

    Deletes memory records from agent_memory table. If memory_type is None,
    clears all memory types (short_term, long_term, agentic).

    Args:
        agent_id: Agent UUID path parameter
        memory_type: Optional memory type filter (None = clear all)
        tenant_id: Tenant identifier from auth dependency
        db: Database session dependency

    Returns:
        MemoryClearResponse: Cleared count and timestamp

    Raises:
        HTTPException 404: If agent not found or tenant mismatch
        HTTPException 500: If database error occurs
    """
    service = MemoryConfigService(db)

    try:
        cleared_count = await service.clear_memory(agent_id, tenant_id, memory_type)

        logger.info(
            f"Cleared {cleared_count} memories for agent {agent_id} "
            f"(type: {memory_type or 'all'}, tenant: {tenant_id})"
        )

        return MemoryClearResponse(
            agent_id=agent_id,
            cleared_count=cleared_count,
            memory_type=memory_type,
            cleared_at=datetime.now(timezone.utc),
        )

    except ValueError as e:
        logger.warning(f"DELETE memory failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"DELETE memory error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear memory",
        )


@router.get(
    "/{agent_id}/memory/history",
    response_model=MemoryHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get agent memory history",
    description="Retrieve paginated memory items with optional type filter.",
)
async def get_memory_history(
    agent_id: UUID,
    memory_type: Optional[str] = Query(
        default=None,
        regex="^(short_term|long_term|agentic)?$",
        description="Filter by memory type",
    ),
    page: int = Query(
        default=1,
        ge=1,
        description="Page number (1-indexed)",
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Items per page",
    ),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_async_session),
) -> MemoryHistoryResponse:
    """
    Get paginated memory history.

    Retrieves memory items with pagination and optional type filtering
    for displaying memory history in admin UI.

    Args:
        agent_id: Agent UUID path parameter
        memory_type: Optional memory type filter
        page: Page number (1-indexed)
        page_size: Items per page (max 100)
        tenant_id: Tenant identifier from auth dependency
        db: Database session dependency

    Returns:
        MemoryHistoryResponse: Paginated memory items with total count

    Raises:
        HTTPException 404: If agent not found or tenant mismatch
        HTTPException 500: If database error occurs
    """
    service = MemoryConfigService(db)

    try:
        # Calculate offset for pagination
        offset = (page - 1) * page_size

        # Retrieve memories with limit+offset
        from sqlalchemy import and_, desc, func, select
        from src.database.models import Agent, AgentMemory

        # Validate agent exists and tenant matches
        stmt = select(Agent).where(
            and_(Agent.id == agent_id, Agent.tenant_id == tenant_id)
        )
        result = await db.execute(stmt)
        agent = result.scalar_one_or_none()

        if not agent:
            raise ValueError(f"Agent {agent_id} not found for tenant {tenant_id}")

        # Build query with optional type filter
        conditions = [AgentMemory.agent_id == agent_id]
        if memory_type:
            conditions.append(AgentMemory.memory_type == memory_type)

        # Get total count
        count_stmt = select(func.count(AgentMemory.id)).where(and_(*conditions))
        count_result = await db.execute(count_stmt)
        total = count_result.scalar()

        # Get paginated memories
        stmt = (
            select(AgentMemory)
            .where(and_(*conditions))
            .order_by(desc(AgentMemory.created_at))
            .offset(offset)
            .limit(page_size)
        )

        result = await db.execute(stmt)
        memories = result.scalars().all()

        logger.info(
            f"Retrieved memory history for agent {agent_id} "
            f"(page: {page}, size: {page_size}, total: {total})"
        )

        return MemoryHistoryResponse(
            memories=[
                {
                    "id": m.id,
                    "agent_id": m.agent_id,
                    "memory_type": m.memory_type,
                    "content": m.content,
                    "embedding": m.embedding,
                    "retention_days": m.retention_days,
                    "created_at": m.created_at,
                    "updated_at": m.updated_at,
                }
                for m in memories
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    except ValueError as e:
        logger.warning(f"GET memory history failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"GET memory history error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve memory history",
        )
