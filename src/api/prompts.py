"""
Prompt versioning and template management API endpoints.

REST API for agent system prompts, prompt versioning, and template management.
Supports prompt history, reverting to previous versions, and custom template creation.
All endpoints enforce tenant isolation via tenant_id filtering.

Story 8.5: System Prompt Editor - FastAPI router for prompt management.
"""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_tenant_db, get_tenant_id
from src.schemas.agent import (
    PromptTemplateCreate,
    PromptTemplateResponse,
    PromptTestRequest,
    PromptTestResponse,
    PromptVersionDetail,
    PromptVersionResponse,
)
from src.services.prompt_service import PromptService
from src.utils.logger import logger

router = APIRouter(prefix="/api/agents", tags=["prompts"])


# ============================================================================
# Static Routes - MUST come before parameterized routes for proper matching
# ============================================================================


@router.get(
    "/prompt-templates",
    response_model=list[PromptTemplateResponse],
    summary="List Prompt Templates",
    description="Retrieves available prompt templates. "
    "Returns built-in templates for all tenants and custom templates for current tenant.",
)
async def list_prompt_templates(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    include_builtin: Annotated[bool, Query()] = True,
) -> list[PromptTemplateResponse]:
    """
    List available prompt templates.

    Args:
        include_builtin: Whether to include built-in templates (default: true)
        tenant_id: Tenant ID (auto-injected)
        db: Database session (auto-injected)

    Returns:
        List of PromptTemplateResponse objects
    """
    prompt_service = PromptService(db)
    templates = await prompt_service.get_prompt_templates(
        tenant_id, include_builtin=include_builtin
    )
    return templates


@router.post(
    "/prompt-templates",
    response_model=PromptTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Custom Prompt Template",
    description="Creates a new custom prompt template for the current tenant.",
)
async def create_prompt_template(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    template_data: Annotated[
        PromptTemplateCreate,
        Body(
            openapi_examples={
                "ticket_enhancement": {
                    "summary": "Ticket Enhancement Template",
                    "description": "Template for ticket analysis agents",
                    "value": {
                        "name": "Ticket Enhancement",
                        "description": "Template for analyzing and enriching support tickets",
                        "template_text": (
                            "You are a support ticket analyzer. "
                            "Analyze the provided ticket and enrich it with: "
                            "1. Root cause analysis\n"
                            "2. Related knowledge base articles\n"
                            "3. IP address insights\n"
                            "Tenant: {{tenant_name}}\n"
                            "Available Tools: {{tools}}\n"
                            "Current Date: {{current_date}}"
                        ),
                    },
                },
                "rca_template": {
                    "summary": "RCA Analysis Template",
                    "description": "Template for root cause analysis",
                    "value": {
                        "name": "Root Cause Analysis",
                        "description": "Systematic RCA template using 5 Whys method",
                        "template_text": (
                            "Agent: {{agent_name}}\n"
                            "Use the 5 Whys method to analyze incidents:\n"
                            "1. Why did the issue occur?\n"
                            "2. Why did that happen?\n"
                            "[Continue asking why 3 more times]\n"
                            "Tools available: {{tools}}"
                        ),
                    },
                },
            }
        ),
    ],
) -> PromptTemplateResponse:
    """
    Create a custom prompt template.

    Args:
        template_data: Template creation request
        tenant_id: Tenant ID (auto-injected)
        db: Database session (auto-injected)

    Returns:
        Created PromptTemplateResponse

    Raises:
        400: If validation fails (name too short, missing fields)
        409: If template name already exists for tenant
    """
    prompt_service = PromptService(db)
    template = await prompt_service.create_custom_template(
        tenant_id,
        template_data,
    )
    logger.info(f"Created custom template: {template.id}")
    return template


@router.put(
    "/prompt-templates/{template_id}",
    response_model=PromptTemplateResponse,
    summary="Update Custom Prompt Template",
    description="Updates an existing custom prompt template. Built-in templates are read-only.",
)
async def update_prompt_template(
    template_id: UUID,
    template_data: PromptTemplateCreate,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
) -> PromptTemplateResponse:
    """
    Update a custom prompt template.

    Args:
        template_id: The template UUID
        template_data: Updated template data
        tenant_id: Tenant ID (auto-injected)
        db: Database session (auto-injected)

    Returns:
        Updated PromptTemplateResponse

    Raises:
        403: If template is built-in or belongs to another tenant
        404: If template not found
    """
    prompt_service = PromptService(db)
    template = await prompt_service.update_custom_template(
        template_id,
        tenant_id,
        template_data,
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    logger.info(f"Updated template: {template_id}")
    return template


@router.delete(
    "/prompt-templates/{template_id}",
    response_model=dict,
    summary="Delete Custom Prompt Template",
    description="Soft-deletes a custom template (marks as inactive). Built-in templates cannot be deleted.",
)
async def delete_prompt_template(
    template_id: UUID,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
) -> dict[str, bool | str]:
    """
    Delete a custom prompt template.

    Args:
        template_id: The template UUID
        tenant_id: Tenant ID (auto-injected)
        db: Database session (auto-injected)

    Returns:
        {"success": true, "message": "Template deleted"}

    Raises:
        403: If template is built-in or belongs to another tenant
        404: If template not found
    """
    prompt_service = PromptService(db)
    success = await prompt_service.delete_custom_template(template_id, tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found or is built-in")
    logger.info(f"Deleted template: {template_id}")
    return {"success": True, "message": "Template deleted"}


@router.post(
    "/prompt-test",
    response_model=PromptTestResponse,
    summary="Test System Prompt with LLM",
    description="Tests a system prompt by sending a sample message to the LLM "
    "through the LiteLLM proxy.",
)
async def test_prompt(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    request: Annotated[
        PromptTestRequest,
        Body(
            openapi_examples={
                "basic_test": {
                    "summary": "Test prompt with sample input",
                    "description": "Test a ticket enhancement prompt",
                    "value": {
                        "system_prompt": (
                            "You are a support ticket analyzer. "
                            "Analyze tickets and provide recommendations."
                        ),
                        "user_message": (
                            "Ticket: TKT-001\n"
                            "Customer: John Doe\n"
                            "Issue: Password reset not working\n"
                            "Priority: High"
                        ),
                        "model": "gpt-4",
                        "temperature": 0.7,
                        "max_tokens": 1000,
                    },
                }
            }
        ),
    ],
) -> PromptTestResponse:
    """
    Test a system prompt via LiteLLM proxy.

    Args:
        request: Test request with system_prompt, user_message, model config
        tenant_id: Tenant ID (auto-injected)
        db: Database session (auto-injected)

    Returns:
        PromptTestResponse with LLM response and metadata

    Raises:
        400: If validation fails
        503: If LiteLLM proxy is unavailable
        504: If request times out (>30s)
    """
    prompt_service = PromptService(db)
    try:
        result = await prompt_service.test_prompt(
            system_prompt=request.system_prompt,
            user_message=request.user_message,
            model=request.model,
            temperature=request.temperature or 0.7,
            max_tokens=request.max_tokens or 1000,
        )
        logger.info(
            f"Prompt test completed for tenant {tenant_id}: "
            f"{result.tokens_used['input']} input tokens, "
            f"{result.tokens_used['output']} output tokens"
        )
        return result
    except TimeoutError:
        raise HTTPException(status_code=504, detail="LLM request timeout (>30s)")
    except Exception as e:
        logger.error(f"Prompt test failed: {str(e)}")
        raise HTTPException(status_code=503, detail="LLM service unavailable")


# ============================================================================
# Parameterized Routes - Come after static routes
# ============================================================================


@router.get(
    "/{agent_id}/prompt-versions",
    response_model=list[PromptVersionResponse],
    summary="Get Prompt Version History",
    description="Retrieves version history for an agent's system prompt. "
    "Includes metadata for each version but not the full prompt text.",
)
async def get_prompt_versions(
    agent_id: UUID,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PromptVersionResponse]:
    """
    Get prompt version history for an agent.

    Args:
        agent_id: The agent UUID
        limit: Maximum number of versions to return (default: 20, max: 100)
        offset: Number of versions to skip for pagination
        tenant_id: Tenant ID (auto-injected from session)
        db: Database session (auto-injected)

    Returns:
        List of PromptVersionResponse objects ordered by created_at DESC

    Raises:
        404: If agent not found or doesn't belong to tenant
        403: If accessing another tenant's agent
    """
    prompt_service = PromptService(db)
    versions = await prompt_service.get_prompt_versions(
        agent_id, tenant_id, limit=limit, offset=offset
    )
    if not versions:
        logger.warning(f"No prompt versions found for agent {agent_id}")
    return versions


@router.get(
    "/{agent_id}/prompt-versions/{version_id}",
    response_model=PromptVersionDetail,
    summary="Get Prompt Version Detail",
    description="Retrieves full prompt text for a specific version.",
)
async def get_prompt_version_detail(
    agent_id: UUID,
    version_id: UUID,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
) -> PromptVersionDetail:
    """
    Get detailed prompt version with full text.

    Args:
        agent_id: The agent UUID
        version_id: The version UUID
        tenant_id: Tenant ID (auto-injected)
        db: Database session (auto-injected)

    Returns:
        PromptVersionDetail with full prompt_text

    Raises:
        404: If version not found
        403: If accessing another tenant's agent
    """
    prompt_service = PromptService(db)
    version = await prompt_service.get_prompt_version_detail(version_id, agent_id, tenant_id)
    if not version:
        raise HTTPException(status_code=404, detail="Prompt version not found")
    return version


@router.post(
    "/{agent_id}/prompt-versions/revert",
    response_model=dict,
    summary="Revert to Previous Prompt Version",
    description="Reverts agent's system prompt to a previous version.",
)
async def revert_prompt_version(
    agent_id: UUID,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    request_body: Annotated[
        dict[str, str],
        Body(
            openapi_examples={
                "revert_example": {
                    "summary": "Revert to previous version",
                    "description": "Revert to version created 1 day ago",
                    "value": {"version_id": "550e8400-e29b-41d4-a716-446655440000"},
                }
            }
        ),
    ] = {},
) -> dict[str, str]:
    """
    Revert to a previous prompt version.

    Args:
        agent_id: The agent UUID
        request_body: {"version_id": "UUID of version to revert to"}
        tenant_id: Tenant ID (auto-injected)
        db: Database session (auto-injected)

    Returns:
        {"success": true, "message": "Reverted to version from..."}

    Raises:
        400: If version_id not provided or invalid
        404: If version not found
        403: If accessing another tenant's agent
    """
    version_id_str = request_body.get("version_id")
    if not version_id_str:
        raise HTTPException(status_code=400, detail="version_id required")

    try:
        version_id = UUID(version_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid version_id format")

    prompt_service = PromptService(db)
    success = await prompt_service.revert_to_version(version_id, agent_id, tenant_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to revert prompt version")

    logger.info(f"Reverted prompt for agent {agent_id} to version {version_id}")
    return {
        "success": "true",
        "message": "Successfully reverted to previous version",
    }
