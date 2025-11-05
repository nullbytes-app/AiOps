"""
Prompt management service for agent system prompts and templates.

Provides business logic for:
- Saving and retrieving prompt versions with history
- Reverting to previous prompt versions
- Creating, updating, and deleting custom prompt templates
- Enforcing multi-tenancy and soft deletes
- Template-to-prompt substitution with runtime variables

Following 2025 async patterns and service layer architecture.
"""

import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import AgentPromptTemplate, AgentPromptVersion
from src.schemas.agent import (
    PromptTemplateCreate,
    PromptTemplateResponse,
    PromptVersionDetail,
    PromptVersionResponse,
)


class PromptService:
    """
    Service layer for prompt management operations.

    All methods enforce multi-tenancy through tenant_id validation.
    Prompt versions are immutable (insert-only), versions are soft-deleted via is_active flag.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize prompt service with database session.

        Args:
            db: Async SQLAlchemy session
        """
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

        Ordered by created_at DESC (newest first). Does not include full prompt_text
        to reduce response size (use get_prompt_version_detail for full text).

        Args:
            agent_id: Agent UUID
            tenant_id: Tenant identifier for isolation check
            limit: Maximum number of versions (default 20, max 100)
            offset: Pagination offset (default 0)

        Returns:
            List of PromptVersionResponse (without full text)

        Raises:
            ValueError: If agent doesn't belong to tenant
        """
        limit = min(limit, 100)  # Enforce max limit

        # Verify agent belongs to tenant (will raise 404 in API layer)
        from src.database.models import Agent

        agent = await self.db.execute(
            select(Agent).where(
                and_(Agent.id == agent_id, Agent.tenant_id == tenant_id)
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

        Sets is_current=true for this version and is_current=false for all previous versions.
        Also updates agents.system_prompt to the new text.

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
            update(Agent)
            .where(Agent.id == agent_id)
            .values(system_prompt=prompt_text)
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

        Marks the target version as current and all others as not current.
        Optionally creates a new version entry to track the revert action.

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

    async def get_prompt_templates(
        self,
        tenant_id: str,
        include_builtin: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PromptTemplateResponse]:
        """
        Retrieve prompt templates for a tenant.

        Returns both built-in templates (shared across all tenants) and
        custom templates created by this tenant.

        Args:
            tenant_id: Tenant identifier
            include_builtin: Whether to include built-in templates (default True)
            limit: Maximum templates to return (default 100, max 500)
            offset: Pagination offset

        Returns:
            List of PromptTemplateResponse
        """
        limit = min(limit, 500)

        conditions = [AgentPromptTemplate.is_active == True]

        if include_builtin:
            # Include both built-in (is_builtin=true) and custom (tenant_id=this tenant)
            conditions.append(
                (AgentPromptTemplate.is_builtin == True)
                | (AgentPromptTemplate.tenant_id == tenant_id)
            )
        else:
            # Only custom templates for this tenant
            conditions.append(
                (AgentPromptTemplate.is_builtin == False)
                & (AgentPromptTemplate.tenant_id == tenant_id)
            )

        stmt = (
            select(AgentPromptTemplate)
            .where(and_(*conditions))
            .order_by(desc(AgentPromptTemplate.created_at))
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(stmt)
        templates = result.scalars().all()

        return [PromptTemplateResponse.from_orm(t) for t in templates]

    async def create_custom_template(
        self,
        tenant_id: str,
        create_schema: PromptTemplateCreate,
        created_by: Optional[str] = None,
    ) -> PromptTemplateResponse:
        """
        Create a custom prompt template for a tenant.

        Args:
            tenant_id: Tenant identifier
            create_schema: Template creation payload
            created_by: Optional user who created template

        Returns:
            PromptTemplateResponse with new template ID

        Raises:
            ValueError: If template validation fails
        """
        # Template creation schema already validates name, description, template_text
        # and variable substitution

        new_template = AgentPromptTemplate(
            tenant_id=tenant_id,
            name=create_schema.name,
            description=create_schema.description,
            template_text=create_schema.template_text,
            is_builtin=False,
            is_active=True,
            created_by=created_by,
        )

        self.db.add(new_template)
        await self.db.commit()
        await self.db.refresh(new_template)

        return PromptTemplateResponse.from_orm(new_template)

    async def update_custom_template(
        self,
        template_id: UUID,
        tenant_id: str,
        update_schema: PromptTemplateCreate,
    ) -> PromptTemplateResponse:
        """
        Update a custom prompt template.

        Only allows updating custom templates (is_builtin=false) owned by this tenant.

        Args:
            template_id: Template UUID
            tenant_id: Tenant identifier for ownership check
            update_schema: Updated template payload

        Returns:
            PromptTemplateResponse with updated template

        Raises:
            ValueError: If template not found or is built-in
        """
        # Fetch template
        stmt = select(AgentPromptTemplate).where(
            and_(
                AgentPromptTemplate.id == template_id,
                AgentPromptTemplate.tenant_id == tenant_id,
                AgentPromptTemplate.is_builtin == False,
            )
        )

        result = await self.db.execute(stmt)
        template = result.scalars().first()

        if template is None:
            raise ValueError(
                f"Template {template_id} not found or is built-in (cannot edit)"
            )

        # Update fields
        template.name = update_schema.name
        template.description = update_schema.description
        template.template_text = update_schema.template_text
        template.updated_at = datetime.utcnow()

        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)

        return PromptTemplateResponse.from_orm(template)

    async def delete_custom_template(
        self,
        template_id: UUID,
        tenant_id: str,
    ) -> bool:
        """
        Soft delete a custom prompt template.

        Sets is_active=false to preserve history. Only allows deleting custom
        templates owned by this tenant.

        Args:
            template_id: Template UUID
            tenant_id: Tenant identifier for ownership

        Returns:
            True if delete successful

        Raises:
            ValueError: If template not found or is built-in
        """
        # Fetch template
        stmt = select(AgentPromptTemplate).where(
            and_(
                AgentPromptTemplate.id == template_id,
                AgentPromptTemplate.tenant_id == tenant_id,
                AgentPromptTemplate.is_builtin == False,
            )
        )

        result = await self.db.execute(stmt)
        template = result.scalars().first()

        if template is None:
            raise ValueError(
                f"Template {template_id} not found or is built-in (cannot delete)"
            )

        # Soft delete
        stmt = (
            update(AgentPromptTemplate)
            .where(AgentPromptTemplate.id == template_id)
            .values(is_active=False)
        )
        await self.db.execute(stmt)

        await self.db.commit()

        return True

    async def test_prompt(
        self,
        system_prompt: str,
        user_message: str,
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> "PromptTestResponse":
        """
        Test a system prompt by calling LiteLLM proxy.

        Args:
            system_prompt: The system prompt to test
            user_message: Sample user message to send to the LLM
            model: LLM model name (default: gpt-4)
            temperature: Temperature for generation (default: 0.7)
            max_tokens: Max output tokens (default: 1000)

        Returns:
            PromptTestResponse with LLM response and metadata

        Raises:
            TimeoutError: If request exceeds 30 seconds
            Exception: If LiteLLM proxy is unavailable
        """
        import asyncio
        import time
        from datetime import datetime
        from httpx import AsyncClient

        # Import PromptTestResponse
        from src.schemas.agent import PromptTestResponse, TokenCount

        # LiteLLM proxy configuration
        litellm_base_url = "http://litellm-proxy:4000"  # Service name in Docker network

        start_time = time.time()
        try:
            async with AsyncClient(
                timeout=30.0,
                limits=AsyncClient.Limits(max_connections=10, max_keepalive_connections=5),
            ) as client:
                response = await client.post(
                    f"{litellm_base_url}/chat/completions",
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_message},
                        ],
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                
                # Parse response
                result = response.json()
                completion = result.get("choices", [{}])[0].get("message", {})
                usage = result.get("usage", {})
                
                execution_time = time.time() - start_time

                # Estimate cost (simplified - would need real pricing)
                # Cost estimate: $0.0001 per 1K input tokens, $0.0003 per 1K output tokens
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)
                cost = (input_tokens / 1000 * 0.0001) + (output_tokens / 1000 * 0.0003)

                return PromptTestResponse(
                    text=completion.get("content", ""),
                    tokens_used=TokenCount(
                        input=input_tokens,
                        output=output_tokens,
                    ),
                    execution_time_ms=int(execution_time * 1000),
                    cost_estimate=round(cost, 6),
                    tested_at=datetime.utcnow().isoformat(),
                )

        except asyncio.TimeoutError:
            raise TimeoutError("LLM request timeout after 30 seconds")
        except Exception as e:
            logger.error(f"LLM test failed: {str(e)}")
            raise

    @staticmethod
    def substitute_variables(
        template_text: str,
        variables: dict[str, str],
    ) -> str:
        """
        Substitute {{variable}} placeholders in prompt template.

        Variables not found in the provided dict are replaced with "[UNDEFINED: var_name]".

        Supported variables (enforced by PromptTemplateCreate validator):
        - {{tenant_name}}: Tenant name
        - {{tools}}: Comma-separated list of assigned tools
        - {{current_date}}: Current date (YYYY-MM-DD)
        - {{agent_name}}: Agent name

        Args:
            template_text: Template with {{variable}} placeholders
            variables: Dict mapping variable names to values

        Returns:
            str: Template with substituted variables
        """

        def replace_var(match):
            var_name = match.group(1)
            return variables.get(var_name, f"[UNDEFINED: {var_name}]")

        return re.sub(r"\{\{(\w+)\}\}", replace_var, template_text)
