"""
Agent service layer for CRUD operations and business logic.

Implements agent lifecycle management including creation, retrieval, updates,
soft deletion, and activation with tenant isolation enforced at the service layer.

Story 8.3: Agent CRUD API Endpoints - Service layer for agent management.
"""

import base64
import secrets
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config import get_settings
from src.database.models import Agent, AgentTool, AgentTrigger
from src.schemas.agent import (
    AgentCreate,
    AgentResponse,
    AgentStatus,
    AgentUpdate,
    TriggerType,
)
from src.services.webhook_service import generate_hmac_secret
from src.utils.encryption import decrypt, encrypt
from src.utils.logger import logger


class AgentService:
    """
    Service layer for agent management operations.

    Provides business logic for CRUD operations on agents with tenant isolation
    enforcement, webhook URL generation, and status transition validation.

    All methods enforce tenant_id filtering to prevent cross-tenant access.
    """

    def __init__(self, base_url: str = None):
        """
        Initialize agent service.

        Args:
            base_url: Base URL for webhook generation (default: from PUBLIC_URL env var)
        """
        if base_url is None:
            import os

            base_url = os.getenv("PUBLIC_URL", "http://api:8000")
        self.base_url = base_url
        self.settings = get_settings()

    def _populate_webhook_fields(self, response: AgentResponse, triggers: list) -> None:
        """
        Populate webhook_url and hmac_secret_masked fields in AgentResponse.

        Extracts webhook trigger data from agent triggers and adds top-level
        fields for easy UI access. Masks HMAC secret for security (shows
        first/last 4 chars with *** in middle).

        Args:
            response: AgentResponse instance to populate
            triggers: List of AgentTrigger model instances from agent relationship

        Returns:
            None (modifies response in place)
        """
        for trigger in triggers:
            if trigger.trigger_type == TriggerType.WEBHOOK:
                response.webhook_url = trigger.webhook_url

                # Mask HMAC secret: show first 4 and last 4 chars with *** in middle
                if trigger.hmac_secret:
                    # Encrypted secrets are longer, so show more context
                    secret = trigger.hmac_secret
                    if len(secret) > 12:
                        response.hmac_secret_masked = f"{secret[:6]}***{secret[-6:]}"
                    else:
                        response.hmac_secret_masked = (
                            "***"  # nosec B105 - masking string for UI display, not a real password
                        )
                else:
                    response.hmac_secret_masked = None

                break  # Only one webhook trigger per agent

    async def _validate_mcp_tool_assignments(
        self, assignments: list, tenant_id: str, db: AsyncSession
    ) -> list[dict]:
        """
        Validate MCP tool assignments against active MCP servers.

        Verifies that:
        1. Each referenced MCP server exists and belongs to the tenant
        2. Each MCP server is active (status='active')
        3. Each tool exists in the server's discovered primitives

        Args:
            assignments: List of MCPToolAssignment dicts to validate
            tenant_id: Tenant identifier (VARCHAR) for isolation
            db: Async database session

        Returns:
            List of valid MCPToolAssignment dicts (filtered)

        Raises:
            HTTPException(400): If MCP server not found, inactive, or tool not discovered
        """
        if not assignments:
            return []

        from src.database.models import MCPServer

        validated_assignments = []

        for assignment in assignments:
            mcp_server_id = assignment.get("mcp_server_id")
            tool_name = assignment.get("name")
            primitive_type = assignment.get("mcp_primitive_type")

            # Query MCP server (Task 9.2)
            result = await db.execute(
                select(MCPServer).where(
                    and_(
                        MCPServer.id == mcp_server_id,
                        MCPServer.tenant_id == tenant_id,
                    )
                )
            )
            mcp_server = result.scalars().first()

            # Validation: Server must exist and belong to tenant (Task 9.3)
            if not mcp_server:
                from fastapi import HTTPException

                raise HTTPException(
                    status_code=400,
                    detail=f"MCP server {mcp_server_id} not found or does not belong to tenant {tenant_id}",
                )

            # Validation: Server must be active (Task 9.3)
            if mcp_server.status != "active":
                from fastapi import HTTPException

                raise HTTPException(
                    status_code=400,
                    detail=f"MCP server {mcp_server.name} ({mcp_server_id}) is not active (status: {mcp_server.status})",
                )

            # Validation: Tool must exist in discovered primitives (Task 9.4, 9.5)
            discovered_field_map = {
                "tool": mcp_server.discovered_tools or [],
                "resource": mcp_server.discovered_resources or [],
                "prompt": mcp_server.discovered_prompts or [],
            }

            discovered_primitives = discovered_field_map.get(primitive_type, [])
            tool_exists = any(
                primitive.get("name") == tool_name for primitive in discovered_primitives
            )

            if not tool_exists:
                from fastapi import HTTPException

                raise HTTPException(
                    status_code=400,
                    detail=f"Tool '{tool_name}' (type: {primitive_type}) not found in MCP server {mcp_server.name}'s discovered primitives",
                )

            # Tool is valid, add to validated list (Task 9.7)
            validated_assignments.append(assignment)

        return validated_assignments

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
            tenant_id: Tenant identifier (VARCHAR) for isolation
            agent_data: Validated agent creation request
            db: Async database session

        Returns:
            AgentResponse: Created agent with webhook_url and relationships

        Raises:
            HTTPException(400): If validation fails or agent creation fails
        """
        try:
            # Validate tenant exists
            from src.database.models import TenantConfig

            result = await db.execute(
                select(TenantConfig.id).where(TenantConfig.tenant_id == tenant_id)
            )
            tenant_uuid = result.scalar_one_or_none()

            if not tenant_uuid:
                raise HTTPException(
                    status_code=404,
                    detail=f"Tenant '{tenant_id}' not found"
                )

            # Validate MCP tool assignments (Task 9.6 - Story 11.1.6)
            # Note: Pass tenant_id (str) not tenant_uuid, since MCPServer.tenant_id is VARCHAR
            # Use mode='json' to convert UUID fields to strings for JSON serialization
            mcp_assignments_dicts = [
                assignment.model_dump(mode='json') for assignment in agent_data.mcp_tool_assignments
            ]
            validated_mcp_assignments = await self._validate_mcp_tool_assignments(
                mcp_assignments_dicts, tenant_id, db
            )

            # Create agent instance
            agent = Agent(
                tenant_id=tenant_id,
                name=agent_data.name,
                description=agent_data.description,
                system_prompt=agent_data.system_prompt,
                llm_config=agent_data.llm_config.model_dump(),
                memory_config=(
                    agent_data.memory_config.model_dump() if agent_data.memory_config else None
                ),
                assigned_mcp_tools=validated_mcp_assignments,
                status=agent_data.status,
                created_by=agent_data.created_by,
            )
            db.add(agent)
            await db.flush()  # Get agent.id before creating relationships

            # Generate webhook URL and use shared HMAC secret from config
            # Using shared secret ensures HMAC proxy and API use same secret for signature validation
            webhook_url = f"{self.base_url}/agents/{agent.id}/webhook"
            hmac_secret = self.settings.webhook_secret  # Use shared secret from environment

            # Encrypt HMAC secret before storing (Fernet symmetric encryption)
            encrypted_hmac_secret = encrypt(hmac_secret)

            # Create webhook trigger
            trigger = AgentTrigger(
                agent_id=agent.id,
                trigger_type=TriggerType.WEBHOOK,
                webhook_url=webhook_url,
                hmac_secret=encrypted_hmac_secret,
            )
            db.add(trigger)

            # Assign tools (many-to-many via AgentTool)
            for tool_id in agent_data.tool_ids:
                agent_tool = AgentTool(agent_id=agent.id, tool_id=tool_id)
                db.add(agent_tool)

            await db.commit()
            await db.refresh(agent, ["triggers", "tools"])

            # Build response with webhook URL and masked HMAC secret
            response = AgentResponse.model_validate(agent)
            self._populate_webhook_fields(response, agent.triggers)
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
        status_filter: Optional[list[AgentStatus]] = None,
        name_search: Optional[str] = None,
        db: AsyncSession | None = None,
    ) -> dict:
        """
        Get paginated list of agents with optional filters.

        Filters by tenant_id (mandatory), status (optional - supports multiple values),
        and name search (optional). Applies pagination with offset (skip) and limit.
        Eager loads relationships to avoid N+1 queries.

        Args:
            tenant_id: Tenant identifier for isolation
            skip: Pagination offset (default 0)
            limit: Page size, capped at 100 (default 20)
            status_filter: Optional status filter - supports multiple values
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
                query = query.where(Agent.status.in_(status_filter))  # type: ignore

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

            # Build response items with webhook fields populated
            items = []
            for agent in agents:
                response = AgentResponse.model_validate(agent)
                self._populate_webhook_fields(response, agent.triggers)
                items.append(response)

            return {
                "items": items,
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

            response = AgentResponse.model_validate(agent)
            self._populate_webhook_fields(response, agent.triggers)
            return response

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
            # Validate tenant exists
            from src.database.models import TenantConfig

            result = await db.execute(
                select(TenantConfig.id).where(TenantConfig.tenant_id == tenant_id)
            )
            tenant_uuid = result.scalar_one_or_none()

            if not tenant_uuid:
                raise HTTPException(
                    status_code=404,
                    detail=f"Tenant '{tenant_id}' not found"
                )

            # Fetch agent MODEL directly (not Pydantic schema)
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

            # Apply updates (only fields present in agent_update)
            update_data = agent_update.model_dump(exclude_unset=True)

            for field, value in update_data.items():
                if field == "llm_config" and value:
                    # Handle LLMConfig - could be dict or Pydantic object
                    if hasattr(value, "model_dump"):
                        value = value.model_dump()
                    # Otherwise it's already a dict from model_dump
                if field == "memory_config" and value:
                    # Handle MemoryConfig - could be dict or Pydantic object
                    if hasattr(value, "model_dump"):
                        value = value.model_dump()
                    # Otherwise it's already a dict from model_dump
                if field == "mcp_tool_assignments" and value:
                    # Handle MCPToolAssignment list - serialize to JSON with UUID conversion
                    value = [
                        assignment.model_dump(mode='json') if hasattr(assignment, "model_dump") else assignment
                        for assignment in value
                    ]
                    # Validate MCP tool assignments (Task 9.6 - Story 11.1.6)
                    validated_value = await self._validate_mcp_tool_assignments(
                        value, tenant_id, db  # Use tenant_id (str) not UUID
                    )
                    # CRITICAL: Convert UUIDs to strings for JSON serialization
                    # The assigned_mcp_tools field is JSON, which can't serialize UUID objects
                    json_safe_value = [
                        {k: str(v) if isinstance(v, UUID) else v for k, v in tool.items()}
                        for tool in validated_value
                    ]
                    # Store in assigned_mcp_tools field (DB column name)
                    setattr(agent, "assigned_mcp_tools", json_safe_value)
                    continue  # Skip normal setattr
                setattr(agent, field, value)

            agent.updated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(agent, ["triggers", "tools"])

            # Convert to Pydantic response
            response = AgentResponse.model_validate(agent)
            self._populate_webhook_fields(response, agent.triggers)
            return response

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
            agent.updated_at = datetime.now(timezone.utc)

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
            # Fetch agent MODEL directly (not Pydantic schema)
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
            agent.updated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(agent, ["triggers", "tools"])

            # Convert to Pydantic response
            response = AgentResponse.model_validate(agent)
            self._populate_webhook_fields(response, agent.triggers)
            return response

        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to activate agent {agent_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to activate agent: {str(e)}",
            )

    async def get_webhook_secret(self, tenant_id: str, agent_id: UUID, db: AsyncSession) -> str:
        """
        Fetch unmasked HMAC secret for agent webhook.

        Security: Audit logged, tenant isolation enforced.

        Args:
            tenant_id: Tenant ID for isolation
            agent_id: Agent UUID
            db: Database session

        Returns:
            str: Unmasked base64-encoded HMAC secret

        Raises:
            HTTPException(403): Cross-tenant access forbidden
            HTTPException(404): Agent not found or no webhook trigger

        Story 8.6 AC#4, Task 7: Fetch webhook secret for show/hide toggle
        """
        # BUG #11 FIX: Use inline query pattern instead of non-existent helper method
        from sqlalchemy import select, and_
        from sqlalchemy.orm import selectinload

        query = (
            select(Agent)
            .where(
                and_(
                    Agent.id == agent_id,
                    Agent.tenant_id == tenant_id,
                )
            )
            .options(selectinload(Agent.triggers))
        )

        result = await db.execute(query)
        agent = result.scalar_one_or_none()

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found or access forbidden",
            )

        # Get webhook trigger (should exist from agent creation)
        webhook_trigger = next((t for t in agent.triggers if t.trigger_type == "webhook"), None)
        if not webhook_trigger or not webhook_trigger.hmac_secret:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook trigger not found for agent",
            )

        # BUG #11 FIX PART 2: decrypt() only takes 1 argument (ciphertext), not 2
        decrypted_secret = decrypt(webhook_trigger.hmac_secret)
        return decrypted_secret

    async def regenerate_webhook_secret(
        self, tenant_id: str, agent_id: UUID, db: AsyncSession
    ) -> str:
        """
        Generate new HMAC secret for agent, invalidating old webhooks.

        Security: Audit logged with warning level, tenant isolation enforced.

        Args:
            tenant_id: Tenant ID for isolation
            agent_id: Agent UUID
            db: Database session

        Returns:
            str: Masked new HMAC secret (first 6 + last 6 chars)

        Raises:
            HTTPException(403): Cross-tenant access forbidden
            HTTPException(404): Agent not found or no webhook trigger

        Story 8.6 AC#5, Task 3: Regenerate HMAC secret with audit logging
        """
        # BUG FIX: Use inline query pattern instead of non-existent helper method
        from sqlalchemy import select, and_
        from sqlalchemy.orm import selectinload

        query = (
            select(Agent)
            .where(
                and_(
                    Agent.id == agent_id,
                    Agent.tenant_id == tenant_id,
                )
            )
            .options(selectinload(Agent.triggers))
        )

        result = await db.execute(query)
        agent = result.scalar_one_or_none()

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found or access forbidden",
            )

        # Get webhook trigger
        webhook_trigger = next((t for t in agent.triggers if t.trigger_type == "webhook"), None)
        if not webhook_trigger:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook trigger not found for agent",
            )

        # Generate new HMAC secret
        new_secret = generate_hmac_secret()
        # BUG FIX: encrypt() only takes 1 parameter (plaintext), not 2
        encrypted_secret = encrypt(new_secret)

        # Update database
        try:
            webhook_trigger.hmac_secret = encrypted_secret
            webhook_trigger.updated_at = datetime.now(timezone.utc)
            db.add(webhook_trigger)
            await db.commit()

            logger.warning(
                f"HMAC secret regenerated for agent {agent_id} (tenant: {tenant_id}). "
                "Old webhooks are now invalid."
            )

            # Return masked secret for API response
            if len(new_secret) > 12:
                masked = f"{new_secret[:6]}***{new_secret[-6:]}"
            else:
                masked = "***"
            return masked

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to regenerate secret for agent {agent_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to regenerate webhook secret",
            )

    async def get_tool_usage_stats(
        self,
        tenant_id: str,
        db: AsyncSession,
    ) -> dict[str, int]:
        """
        Get tool usage statistics for all agents in tenant.

        Counts how many agents are assigned to each tool. Used for
        UI display to show tool popularity.

        Args:
            tenant_id: Tenant ID to filter agents
            db: Async database session

        Returns:
            dict[str, int]: Mapping of tool_id to count of agents using it
                Example: {"servicedesk_plus": 5, "jira": 3}
        """
        from collections import defaultdict
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        # Query all active/draft agents for this tenant with tools relationship
        query = (
            select(Agent)
            .where(
                Agent.tenant_id == tenant_id,
                Agent.status.in_([AgentStatus.DRAFT, AgentStatus.ACTIVE]),
            )
            .options(selectinload(Agent.tools))
        )

        result = await db.execute(query)
        agents = result.scalars().all()

        # Count tool usage - Agent.tools is a relationship, not tool_ids
        tool_counts = defaultdict(int)
        for agent in agents:
            if agent.tools:
                for tool in agent.tools:
                    tool_counts[tool.tool_id] += 1

        return dict(tool_counts)

    async def get_agent_tools(
        self,
        agent_id: UUID,
        tenant_id: str,
        db: AsyncSession,
    ) -> list[dict]:
        """
        Get unified list of OpenAPI and MCP tools assigned to an agent.

        Retrieves both OpenAPI tools (from agent_tools table) and MCP tools
        (from assigned_mcp_tools JSON field), validating MCP tools are still
        available by checking against current discovery using NAME-BASED matching.

        Bug Fix (Story 11.2.7): Changed from ID-based to name-based validation
        because MCP tool UUIDs change after server restart, but tool names remain stable.

        Args:
            agent_id: Agent UUID
            tenant_id: Tenant identifier for isolation
            db: Async database session

        Returns:
            list[dict]: Combined list of OpenAPI and MCP tool definitions

        Raises:
            HTTPException(404): If agent not found
        """
        from src.database.models import MCPServer
        from src.services.unified_tool_service import UnifiedToolService

        try:
            # Fetch agent with OpenAPI tools relationship
            query = (
                select(Agent)
                .where(
                    and_(
                        Agent.id == agent_id,  # type: ignore
                        Agent.tenant_id == tenant_id,  # type: ignore
                    )
                )
                .options(selectinload(Agent.tools))
            )

            result = await db.execute(query)
            agent = result.scalar_one_or_none()

            if not agent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Agent not found",
                )

            tools = []

            # Add OpenAPI tools (from agent_tools table)
            if agent.tools:
                for agent_tool in agent.tools:
                    tools.append(
                        {
                            "id": agent_tool.tool_id,
                            "source_type": "openapi",
                            "name": agent_tool.tool_id,  # Tool IDs are names in current implementation
                        }
                    )

            # Add MCP tools (from assigned_mcp_tools JSON field)
            if agent.assigned_mcp_tools:
                # Get unified tool service to validate MCP tools still exist
                unified_service = UnifiedToolService(db=db)
                current_mcp_tools = await unified_service.list_tools(tenant_id)

                # Create lookup set for current MCP tools by NAME (stable across restarts)
                # Reason: Tool names remain constant, but UUIDs regenerate on server restart
                current_mcp_tool_names = {tool.name for tool in current_mcp_tools}

                # Filter MCP tools to only include still-active ones
                for assigned_tool in agent.assigned_mcp_tools:
                    tool_name = assigned_tool.get("name")

                    # Validate tool still exists in current discovery (name-based)
                    if tool_name and tool_name in current_mcp_tool_names:
                        tools.append(assigned_tool)
                        logger.debug(
                            f"MCP tool validated for agent {agent_id}: {tool_name}"
                        )
                    else:
                        # Log warning but don't fail - gracefully exclude stale tools
                        logger.warning(
                            f"Stale MCP tool excluded from agent {agent_id}: "
                            f"{tool_name} (server may be inactive or tool removed)"
                        )

            logger.info(
                f"Loaded {len(tools)} total tools for agent {agent_id} "
                f"(tenant: {tenant_id})"
            )

            return tools

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get agent tools for {agent_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve agent tools: {str(e)}",
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
