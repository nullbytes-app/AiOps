"""
Prompt management service for agent system prompts and templates.

Delegates to specialized services:
- PromptVersionService: Version history, reverting
- Template management: Creating, updating, deleting custom templates
- LLM testing: Testing prompts via LiteLLM proxy
- Variable substitution: Runtime variable replacement

Following 2025 async patterns and service layer architecture.
"""

import logging
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import and_, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import AgentPromptTemplate
from src.schemas.agent import (
    PromptTemplateCreate,
    PromptTemplateResponse,
    PromptTestResponse,
    PromptVersionDetail,
    PromptVersionResponse,
)
from src.services.prompt_version_service import PromptVersionService

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class PromptService:
    """
    Unified service layer for prompt management operations.

    Delegates version management to PromptVersionService.
    Handles template operations and LLM testing locally.
    All methods enforce multi-tenancy through tenant_id validation.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize prompt service with database session.

        Args:
            db: Async SQLAlchemy session
        """
        self.db = db
        self._version_service = PromptVersionService(db)

    async def get_prompt_versions(
        self,
        agent_id: UUID,
        tenant_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[PromptVersionResponse]:
        """Get prompt version history (delegates to PromptVersionService)."""
        return await self._version_service.get_prompt_versions(agent_id, tenant_id, limit, offset)

    async def get_prompt_version_detail(
        self,
        version_id: UUID,
        agent_id: UUID,
        tenant_id: str,
    ) -> PromptVersionDetail:
        """Get full prompt version details (delegates to PromptVersionService)."""
        return await self._version_service.get_prompt_version_detail(
            version_id, agent_id, tenant_id
        )

    async def save_prompt_version(
        self,
        agent_id: UUID,
        tenant_id: str,
        prompt_text: str,
        description: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> PromptVersionResponse:
        """Save new prompt version (delegates to PromptVersionService)."""
        return await self._version_service.save_prompt_version(
            agent_id, tenant_id, prompt_text, description, created_by
        )

    async def revert_to_version(
        self,
        version_id: UUID,
        agent_id: UUID,
        tenant_id: str,
        created_by: Optional[str] = None,
    ) -> bool:
        """Revert to previous version (delegates to PromptVersionService)."""
        return await self._version_service.revert_to_version(
            version_id, agent_id, tenant_id, created_by
        )

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
            .where(and_(*conditions))  # type: ignore[arg-type]
            .order_by(desc(AgentPromptTemplate.created_at))  # type: ignore[arg-type]
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
                AgentPromptTemplate.id == template_id,  # type: ignore[arg-type]
                AgentPromptTemplate.tenant_id == tenant_id,  # type: ignore[arg-type]
                AgentPromptTemplate.is_builtin == False,  # type: ignore[arg-type]
            )
        )

        result = await self.db.execute(stmt)
        template = result.scalars().first()

        if template is None:
            raise ValueError(f"Template {template_id} not found or is built-in (cannot edit)")

        # Update fields
        template.name = update_schema.name
        template.description = update_schema.description
        template.template_text = update_schema.template_text
        template.updated_at = datetime.now(timezone.utc)

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
                AgentPromptTemplate.id == template_id,  # type: ignore[arg-type]
                AgentPromptTemplate.tenant_id == tenant_id,  # type: ignore[arg-type]
                AgentPromptTemplate.is_builtin == False,  # type: ignore[arg-type]
            )
        )

        result = await self.db.execute(stmt)
        template = result.scalars().first()

        if template is None:
            raise ValueError(f"Template {template_id} not found or is built-in (cannot delete)")

        # Soft delete
        update_stmt = (
            update(AgentPromptTemplate)
            .where(AgentPromptTemplate.id == template_id)  # type: ignore[arg-type]
            .values(is_active=False)
        )
        await self.db.execute(update_stmt)

        await self.db.commit()

        return True

    async def test_prompt(
        self,
        system_prompt: str,
        user_message: str,
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> PromptTestResponse:
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
        from httpx import AsyncClient

        # LiteLLM proxy configuration
        litellm_base_url = "http://litellm-proxy:4000"  # Service name in Docker network

        start_time = time.time()
        try:
            from httpx import Limits

            async with AsyncClient(
                timeout=30.0,
                limits=Limits(max_connections=10, max_keepalive_connections=5),
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
                    tokens_used={
                        "input": input_tokens,
                        "output": output_tokens,
                    },
                    execution_time=int(execution_time * 1000),
                    cost=round(cost, 6),
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
            Template with substituted variables
        """

        def replace_var(match: re.Match[str]) -> str:
            var_name = match.group(1)
            return variables.get(var_name, f"[UNDEFINED: {var_name}]")

        return re.sub(r"\{\{(\w+)\}\}", replace_var, template_text)
