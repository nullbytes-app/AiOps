"""
Agent service layer for CRUD operations and business logic.

Implements agent lifecycle management including creation, retrieval, updates,
soft deletion, and activation with tenant isolation enforced at the service layer.

Story 8.3: Agent CRUD API Endpoints - Service layer for agent management.
"""

import base64
import secrets
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models import Agent, AgentTool, AgentTrigger
from src.schemas.agent import (
    AgentCreate,
    AgentResponse,
    AgentStatus,
    AgentUpdate,
    TriggerType,
)
from src.utils.logger import logger


class AgentService:
    """
    Service layer for agent management operations.

    Provides business logic for CRUD operations on agents with tenant isolation
    enforcement, webhook URL generation, and status transition validation.

    All methods enforce tenant_id filtering to prevent cross-tenant access.
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize agent service.

        Args:
            base_url: Base URL for webhook generation (default: http://localhost:8000)
        """
        self.base_url = base_url

    async def create_agent(
        self,
        tenant_id: str,
        agent_data: AgentCreate,
        db: AsyncSession,
    ) -> AgentResponse:
        """
        Create new agent with webhook trigger and optional tool assignments.

        Generates webhook URL and HMAC secret automatically. Creates default
        webhook trigger if agent_data.triggers is empty. Assigns tools via
        AgentTool junction table for many-to-many relationship.

        Args:
            tenant_id: Tenant identifier for isolation
            agent_data: Validated agent creation request
            db: Async database session

        Returns:
            AgentResponse: Created agent with webhook_url and relationships

        Raises:
            HTTPException(400): If validation fails or agent creation fails
        """
        try:
            # Create agent instance
            agent = Agent(
                tenant_id=tenant_id,
                name=agent_data.name,
                description=agent_data.description,
                system_prompt=agent_data.system_prompt,
                llm_config=agent_data.llm_config.model_dump(),
                status=agent_data.status,
                created_by=agent_data.created_by,
            )
            db.add(agent)
            await db.flush()  # Get agent.id before creating relationships

            # Generate webhook URL and HMAC secret
            webhook_url = f"{self.base_url}/agents/{agent.id}/webhook"
            hmac_secret = base64.b64encode(secrets.token_bytes(32)).decode("utf-8")

            # Create webhook trigger
            trigger = AgentTrigger(
                agent_id=agent.id,
                trigger_type=TriggerType.WEBHOOK,
                webhook_url=webhook_url,
                hmac_secret=hmac_secret,  # TODO: Encrypt with Fernet before storing
            )
            db.add(trigger)

            # Assign tools (many-to-many via AgentTool)
            for tool_id in agent_data.tool_ids:
                agent_tool = AgentTool(agent_id=agent.id, tool_id=tool_id)
                db.add(agent_tool)

            await db.commit()
            await db.refresh(agent, ["triggers", "tools"])

            # Build response with webhook URL
            response = AgentResponse.model_validate(agent)
            return response

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to create agent: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create agent: {str(e)}",
            )

    async def get_agents(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 20,
        status_filter: Optional[AgentStatus] = None,
        name_search: Optional[str] = None,
        db: AsyncSession | None = None,
    ) -> dict:
        """
        Get paginated list of agents with optional filters.

        Filters by tenant_id (mandatory), status (optional), and name search (optional).
        Applies pagination with offset (skip) and limit. Eager loads relationships
        to avoid N+1 queries.

        Args:
            tenant_id: Tenant identifier for isolation
            skip: Pagination offset (default 0)
            limit: Page size, capped at 100 (default 20)
            status_filter: Optional status filter
            name_search: Optional name search (case-insensitive ILIKE)
            db: Async database session

        Returns:
            dict: {items: [AgentResponse], total: int, skip: int, limit: int}

        Raises:
            HTTPException: If database query fails
        """
        try:
            # Enforce limit cap
            limit = min(limit, 100)

            # Build base query with tenant isolation
            query = select(Agent).where(Agent.tenant_id == tenant_id)  # type: ignore

            # Apply filters
            if status_filter:
                query = query.where(Agent.status == status_filter)  # type: ignore

            if name_search:
                query = query.where(Agent.name.ilike(f"%{name_search}%"))  # type: ignore

            # Count total matching agents
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await db.execute(count_query)  # type: ignore
            total = total_result.scalar() or 0

            # Apply pagination and eager load relationships
            query = (
                query.options(
                    selectinload(Agent.triggers),
                    selectinload(Agent.tools),
                )
                .offset(skip)
                .limit(limit)
            )

            result = await db.execute(query)  # type: ignore
            agents = result.scalars().unique().all()

            return {
                "items": [AgentResponse.model_validate(agent) for agent in agents],
                "total": total,
                "skip": skip,
                "limit": limit,
            }

        except Exception as e:
            logger.error(f"Failed to get agents: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve agents",
            )

    async def get_agent_by_id(
        self,
        tenant_id: str,
        agent_id: UUID,
        db: AsyncSession,
    ) -> AgentResponse:
        """
        Get agent by ID with full details including relationships.

        Args:
            tenant_id: Tenant identifier for isolation
            agent_id: Agent UUID
            db: Async database session

        Returns:
            AgentResponse: Full agent details with triggers and tools

        Raises:
            HTTPException(404): If agent not found or belongs to different tenant
        """
        try:
            query = (
                select(Agent)
                .where(
                    and_(
                        Agent.id == agent_id,  # type: ignore
                        Agent.tenant_id == tenant_id,  # type: ignore
                    )
                )
                .options(
                    selectinload(Agent.triggers),
                    selectinload(Agent.tools),
                )
            )

            result = await db.execute(query)
            agent = result.scalar_one_or_none()

            if not agent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Agent not found",
                )

            return AgentResponse.model_validate(agent)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get agent {agent_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve agent",
            )

    async def update_agent(
        self,
        tenant_id: str,
        agent_id: UUID,
        agent_update: AgentUpdate,
        db: AsyncSession,
    ) -> AgentResponse:
        """
        Update agent with partial data.

        Only updates fields present in agent_update (exclude_unset=True).
        Validates status transitions via Pydantic validator. Updates
        updated_at timestamp.

        Args:
            tenant_id: Tenant identifier for isolation
            agent_id: Agent UUID
            agent_update: Partial update request
            db: Async database session

        Returns:
            AgentResponse: Updated agent

        Raises:
            HTTPException(404): If agent not found
            HTTPException(400): If validation fails
        """
        try:
            # Fetch agent
            agent = await self.get_agent_by_id(tenant_id, agent_id, db)

            # Apply updates (only fields present in agent_update)
            update_data = agent_update.model_dump(exclude_unset=True)

            for field, value in update_data.items():
                if field == "llm_config" and value:
                    # Serialize LLMConfig to dict for JSONB storage
                    value = value.model_dump()
                setattr(agent, field, value)

            agent.updated_at = datetime.utcnow()

            await db.commit()
            await db.refresh(agent, ["triggers", "tools"])

            return AgentResponse.model_validate(agent)

        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to update agent {agent_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to update agent: {str(e)}",
            )

    async def delete_agent(
        self,
        tenant_id: str,
        agent_id: UUID,
        db: AsyncSession,
    ) -> bool:
        """
        Soft delete agent by setting status to INACTIVE.

        Preserves audit trail by keeping record in database.
        Does NOT cascade delete triggers or tools.

        Args:
            tenant_id: Tenant identifier for isolation
            agent_id: Agent UUID
            db: Async database session

        Returns:
            bool: True if deleted successfully

        Raises:
            HTTPException(404): If agent not found
        """
        try:
            # Fetch agent to verify existence and ownership
            agent = await self.get_agent_by_id(tenant_id, agent_id, db)

            # Soft delete: set status to INACTIVE
            agent.status = AgentStatus.INACTIVE
            agent.updated_at = datetime.utcnow()

            await db.commit()
            return True

        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to delete agent {agent_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete agent",
            )

    async def activate_agent(
        self,
        tenant_id: str,
        agent_id: UUID,
        db: AsyncSession,
    ) -> AgentResponse:
        """
        Activate agent: transition from DRAFT to ACTIVE with validation.

        Validates:
        1. Current status is DRAFT (only draft→active allowed)
        2. system_prompt is not empty and meets length requirements
        3. llm_config has 'model' key
        4. At least one trigger exists

        Args:
            tenant_id: Tenant identifier for isolation
            agent_id: Agent UUID
            db: Async database session

        Returns:
            AgentResponse: Activated agent with status=ACTIVE

        Raises:
            HTTPException(400): If validation fails
            HTTPException(404): If agent not found
        """
        try:
            # Fetch agent
            agent = await self.get_agent_by_id(tenant_id, agent_id, db)

            # Validate current status is DRAFT
            if agent.status != AgentStatus.DRAFT:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Agent must be in DRAFT status to activate. "
                        f"Current status: {agent.status}"
                    ),
                )

            # Validate system_prompt
            if not agent.system_prompt or len(agent.system_prompt) < 10:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="system_prompt must be at least 10 characters",
                )

            # Validate llm_config has 'model' key
            llm_config = agent.llm_config
            if not isinstance(llm_config, dict) or "model" not in llm_config:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="llm_config must have 'model' key",
                )

            # Validate at least one trigger exists
            if not agent.triggers or len(agent.triggers) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Agent must have at least one trigger before activation",
                )

            # Activate agent
            agent.status = AgentStatus.ACTIVE
            agent.updated_at = datetime.utcnow()

            await db.commit()
            await db.refresh(agent, ["triggers", "tools"])

            return AgentResponse.model_validate(agent)

        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to activate agent {agent_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to activate agent: {str(e)}",
            )


# Singleton instance for dependency injection
_agent_service: Optional[AgentService] = None


def get_agent_service() -> AgentService:
    """
    Get or create singleton AgentService instance.

    Returns:
        AgentService: Singleton service instance
    """
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service
