"""
Prompt version management service.

Handles saving, retrieving, and reverting prompt versions with full history.
Enforces multi-tenancy and immutable version history.
"""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import AgentPromptVersion
from src.schemas.agent import PromptVersionDetail, PromptVersionResponse

logger = logging.getLogger(__name__)


class PromptVersionService:
    """Service layer for prompt version management."""

    def __init__(self, db: AsyncSession):
        """Initialize version service with database session."""
        self.db = db

    async def get_prompt_versions(
        self,
        agent_id: UUID,
        tenant_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[PromptVersionResponse]:
        """
        Retrieve prompt version history for an agent.

        Args:
            agent_id: Agent UUID
            tenant_id: Tenant identifier for isolation check
            limit: Maximum number of versions (default 20, max 100)
            offset: Pagination offset (default 0)

        Returns:
            List of PromptVersionResponse ordered by created_at DESC

        Raises:
            ValueError: If agent doesn't belong to tenant
        """
        limit = min(limit, 100)

        # Verify agent belongs to tenant
        from src.database.models import Agent

        agent = await self.db.execute(
            select(Agent).where(
                and_(Agent.id == agent_id, Agent.tenant_id == tenant_id)  # type: ignore
            )
        )
        if agent.scalars().first() is None:
            raise ValueError(f"Agent {agent_id} not found for tenant {tenant_id}")

        # Fetch versions
        stmt = (
            select(AgentPromptVersion)
            .where(AgentPromptVersion.agent_id == agent_id)
            .order_by(desc(AgentPromptVersion.created_at))
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(stmt)
        versions = result.scalars().all()

        return [PromptVersionResponse.from_orm(v) for v in versions]

    async def get_prompt_version_detail(
        self,
        version_id: UUID,
        agent_id: UUID,
        tenant_id: str,
    ) -> PromptVersionDetail:
        """
        Retrieve full prompt version details including text.

        Args:
            version_id: Version UUID
            agent_id: Agent UUID (for validation)
            tenant_id: Tenant identifier for isolation check

        Returns:
            PromptVersionDetail with full prompt_text

        Raises:
            ValueError: If version not found or doesn't belong to agent/tenant
        """
        from src.database.models import Agent

        # Verify agent belongs to tenant
        agent = await self.db.execute(
            select(Agent).where(
                and_(Agent.id == agent_id, Agent.tenant_id == tenant_id)
            )
        )
        if agent.scalars().first() is None:
            raise ValueError(f"Agent {agent_id} not found for tenant {tenant_id}")

        # Fetch version
        stmt = select(AgentPromptVersion).where(
            and_(
                AgentPromptVersion.id == version_id,
                AgentPromptVersion.agent_id == agent_id,
            )
        )

        result = await self.db.execute(stmt)
        version = result.scalars().first()

        if version is None:
            raise ValueError(f"Prompt version {version_id} not found")

        return PromptVersionDetail.from_orm(version)

    async def save_prompt_version(
        self,
        agent_id: UUID,
        tenant_id: str,
        prompt_text: str,
        description: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> PromptVersionResponse:
        """
        Save a new prompt version and mark as current.

        Args:
            agent_id: Agent UUID
            tenant_id: Tenant identifier for isolation
            prompt_text: New system prompt (10-32000 chars)
            description: Optional description of changes
            created_by: User who created this version

        Returns:
            PromptVersionResponse with new version ID

        Raises:
            ValueError: If agent not found or prompt validation fails
        """
        from src.database.models import Agent

        # Validate prompt length
        if not (10 <= len(prompt_text) <= 32000):
            raise ValueError(
                f"Prompt text must be 10-32000 characters. Got {len(prompt_text)}."
            )

        # Verify agent belongs to tenant
        agent = await self.db.execute(
            select(Agent).where(
                and_(Agent.id == agent_id, Agent.tenant_id == tenant_id)
            )
        )
        agent_obj = agent.scalars().first()
        if agent_obj is None:
            raise ValueError(f"Agent {agent_id} not found for tenant {tenant_id}")

        # Mark previous versions as not current
        stmt = (
            update(AgentPromptVersion)
            .where(
                and_(
                    AgentPromptVersion.agent_id == agent_id,
                    AgentPromptVersion.is_current == True,
                )
            )
            .values(is_current=False)
        )
        await self.db.execute(stmt)

        # Create new version
        new_version = AgentPromptVersion(
            agent_id=agent_id,
            prompt_text=prompt_text,
            description=description,
            created_by=created_by,
            is_current=True,
        )
        self.db.add(new_version)

        # Update agent's system_prompt
        stmt = (
            update(Agent).where(Agent.id == agent_id).values(system_prompt=prompt_text)
        )
        await self.db.execute(stmt)

        await self.db.commit()
        await self.db.refresh(new_version)

        return PromptVersionResponse.from_orm(new_version)

    async def revert_to_version(
        self,
        version_id: UUID,
        agent_id: UUID,
        tenant_id: str,
        created_by: Optional[str] = None,
    ) -> bool:
        """
        Revert agent to a previous prompt version.

        Args:
            version_id: Version UUID to revert to
            agent_id: Agent UUID
            tenant_id: Tenant identifier
            created_by: Optional user performing revert

        Returns:
            True if revert successful

        Raises:
            ValueError: If version not found or doesn't belong to agent
        """
        from src.database.models import Agent

        # Verify agent belongs to tenant
        agent = await self.db.execute(
            select(Agent).where(
                and_(Agent.id == agent_id, Agent.tenant_id == tenant_id)
            )
        )
        agent_obj = agent.scalars().first()
        if agent_obj is None:
            raise ValueError(f"Agent {agent_id} not found for tenant {tenant_id}")

        # Fetch target version
        stmt = select(AgentPromptVersion).where(
            and_(
                AgentPromptVersion.id == version_id,
                AgentPromptVersion.agent_id == agent_id,
            )
        )
        result = await self.db.execute(stmt)
        target_version = result.scalars().first()

        if target_version is None:
            raise ValueError(f"Prompt version {version_id} not found")

        # Mark all current versions as not current
        stmt = (
            update(AgentPromptVersion)
            .where(
                and_(
                    AgentPromptVersion.agent_id == agent_id,
                    AgentPromptVersion.is_current == True,
                )
            )
            .values(is_current=False)
        )
        await self.db.execute(stmt)

        # Mark target version as current
        stmt = (
            update(AgentPromptVersion)
            .where(AgentPromptVersion.id == version_id)
            .values(is_current=True)
        )
        await self.db.execute(stmt)

        # Update agent's system_prompt
        stmt = (
            update(Agent)
            .where(Agent.id == agent_id)
            .values(system_prompt=target_version.prompt_text)
        )
        await self.db.execute(stmt)

        await self.db.commit()

        return True
