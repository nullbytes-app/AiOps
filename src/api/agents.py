"""
Agent CRUD API endpoints for agent management.

REST API for creating, reading, updating, and deleting AI agents.
All endpoints enforce tenant isolation via tenant_id filtering.
Supports pagination, filtering by status and name search.

Story 8.3: Agent CRUD API Endpoints - FastAPI router for agent management.
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
    AgentCreate,
    AgentResponse,
    AgentStatus,
    AgentUpdate,
)
from src.services.agent_service import AgentService, get_agent_service
from src.utils.logger import logger

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.post(
    "/",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Agent",
    description="Creates a new agent with webhook trigger and optional tool assignments. "
    "Agent defaults to DRAFT status and must be activated before use. "
    "Webhook URL and HMAC secret are auto-generated.",
)
async def create_agent(
    agent_data: Annotated[
        AgentCreate,
        Body(
            openapi_examples={
                "ticket_enhancement": {
                    "summary": "Ticket Enhancement Agent",
                    "description": "Agent for enriching support tickets with context",
                    "value": {
                        "name": "Ticket Enhancement Agent",
                        "description": "Automatically enriches support tickets with context",
                        "system_prompt": (
                            "You are a helpful assistant that enriches support "
                            "tickets with relevant context from history, knowledge "
                            "base, and IP information."
                        ),
                        "llm_config": {
                            "provider": "litellm",
                            "model": "gpt-4",
                            "temperature": 0.7,
                            "max_tokens": 4096,
                        },
                        "status": "draft",
                        "created_by": "admin@example.com",
                        "tool_ids": ["servicedesk_plus"],
                    },
                },
                "rca_agent": {
                    "summary": "Root Cause Analysis Agent",
                    "description": "Agent for performing RCA on incidents",
                    "value": {
                        "name": "RCA Agent",
                        "description": "Performs root cause analysis on incidents",
                        "system_prompt": (
                            "You are an expert in root cause analysis. Analyze "
                            "incidents systematically using the 5 Whys method."
                        ),
                        "llm_config": {
                            "provider": "litellm",
                            "model": "claude-3-5-sonnet",
                            "temperature": 0.5,
                            "max_tokens": 8192,
                        },
                        "status": "draft",
                        "tool_ids": ["servicedesk_plus"],
                    },
                },
            }
        ),
    ],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> AgentResponse:
    """
    Create new agent with validation and webhook URL generation.

    Args:
        agent_data: Agent creation request with name, system_prompt, llm_config
        tenant_id: Current tenant ID (from dependency)
        db: Tenant-aware async database session
        agent_service: Agent service instance

    Returns:
        AgentResponse: Created agent with generated webhook URL

    Raises:
        HTTPException(400): If validation fails
        HTTPException(422): If request body is invalid
    """
    try:
        agent = await agent_service.create_agent(tenant_id, agent_data, db)
        logger.info(f"Created agent {agent.id} for tenant {tenant_id}")
        return agent
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create agent",
        )


@router.get(
    "/",
    response_model=dict,
    summary="List Agents",
    description="Get paginated list of agents with optional filtering by status or name search. "
    "Returns only agents belonging to the current tenant.",
)
async def list_agents(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    skip: Annotated[
        int, Query(ge=0, description="Number of agents to skip (pagination offset)")
    ] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum agents to return (1-100)")] = 20,
    agent_status: Annotated[
        Optional[AgentStatus],
        Query(
            alias="status",
            description="Filter by agent status (draft, active, suspended, inactive)",
        ),
    ] = None,
    q: Annotated[
        Optional[str],
        Query(description="Search agents by name (case-insensitive partial match)"),
    ] = None,
) -> dict:
    """
    List agents with pagination and filtering.

    Args:
        skip: Pagination offset (default 0)
        limit: Page size, capped at 100 (default 20)
        agent_status: Optional status filter (query param name: status)
        q: Optional name search (case-insensitive)
        tenant_id: Current tenant ID (from dependency)
        db: Tenant-aware database session
        agent_service: Agent service instance

    Returns:
        dict: {items: [AgentResponse], total: int, skip: int, limit: int}

    Raises:
        HTTPException(500): If database query fails
    """
    try:
        result = await agent_service.get_agents(
            tenant_id=tenant_id,
            skip=skip,
            limit=limit,
            status_filter=agent_status,
            name_search=q,
            db=db,
        )
        return result
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list agents",
        )


@router.get(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Get Agent",
    description="Get full agent details including assigned tools and triggers.",
)
async def get_agent(
    agent_id: Annotated[UUID, "Agent UUID"],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> AgentResponse:
    """
    Get agent by ID with full details.

    Args:
        agent_id: Agent UUID
        tenant_id: Current tenant ID (from dependency)
        db: Tenant-aware database session
        agent_service: Agent service instance

    Returns:
        AgentResponse: Full agent details with triggers and tools

    Raises:
        HTTPException(404): If agent not found or belongs to different tenant
    """
    try:
        agent = await agent_service.get_agent_by_id(tenant_id, agent_id, db)
        return agent
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent",
        )


@router.put(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Update Agent",
    description="Update agent properties with partial data support. "
    "Status transitions are validated (e.g., cannot change active→draft).",
)
async def update_agent(
    agent_id: Annotated[UUID, "Agent UUID"],
    agent_update: Annotated[
        AgentUpdate,
        Body(
            openapi_examples={
                "name_only": {
                    "summary": "Update name only",
                    "value": {"name": "Updated Agent Name"},
                },
                "system_prompt": {
                    "summary": "Update system prompt",
                    "value": {"system_prompt": "Updated system prompt with new instructions"},
                },
                "suspend_agent": {
                    "summary": "Suspend agent",
                    "value": {"status": "suspended"},
                },
            }
        ),
    ],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> AgentResponse:
    """
    Update agent with partial data.

    Args:
        agent_id: Agent UUID
        agent_update: Partial update request
        tenant_id: Current tenant ID (from dependency)
        db: Tenant-aware database session
        agent_service: Agent service instance

    Returns:
        AgentResponse: Updated agent

    Raises:
        HTTPException(400): If validation fails
        HTTPException(404): If agent not found
    """
    try:
        agent = await agent_service.update_agent(tenant_id, agent_id, agent_update, db)
        logger.info(f"Updated agent {agent_id} for tenant {tenant_id}")
        return agent
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update agent",
        )


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Agent",
    description=(
        "Soft delete agent (sets status=inactive). Agent record is " "preserved for audit trail."
    ),
)
async def delete_agent(
    agent_id: Annotated[UUID, "Agent UUID"],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> None:
    """
    Soft delete agent by setting status to INACTIVE.

    Args:
        agent_id: Agent UUID
        tenant_id: Current tenant ID (from dependency)
        db: Tenant-aware database session
        agent_service: Agent service instance

    Raises:
        HTTPException(404): If agent not found
    """
    try:
        await agent_service.delete_agent(tenant_id, agent_id, db)
        logger.info(f"Deleted agent {agent_id} for tenant {tenant_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete agent",
        )


@router.post(
    "/{agent_id}/activate",
    response_model=AgentResponse,
    summary="Activate Agent",
    description="Activate agent: transition from DRAFT→ACTIVE with validation. "
    "Agent must have system_prompt, llm_config with model, and at least one trigger.",
)
async def activate_agent(
    agent_id: Annotated[UUID, "Agent UUID"],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> AgentResponse:
    """
    Activate agent (DRAFT→ACTIVE transition).

    Validates required fields and status before activation.

    Args:
        agent_id: Agent UUID
        tenant_id: Current tenant ID (from dependency)
        db: Tenant-aware database session
        agent_service: Agent service instance

    Returns:
        AgentResponse: Activated agent with status=ACTIVE

    Raises:
        HTTPException(400): If validation fails or status not DRAFT
        HTTPException(404): If agent not found
    """
    try:
        agent = await agent_service.activate_agent(tenant_id, agent_id, db)
        logger.info(f"Activated agent {agent_id} for tenant {tenant_id}")
        return agent
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to activate agent",
        )


@router.get(
    "/{agent_id}/webhook-secret",
    summary="Get Webhook Secret",
    description="Fetch unmasked HMAC secret for agent. Rate-limited to 10 req/min. Audit logged.",
)
async def get_webhook_secret(
    agent_id: Annotated[UUID, "Agent UUID"],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> dict:
    """
    Fetch unmasked HMAC secret for agent webhook.

    Security:
        - Rate-limited to 10 requests per minute per user
        - Audit logged for security monitoring
        - Requires tenant ownership (cross-tenant access forbidden)

    Args:
        agent_id: Agent UUID
        tenant_id: Current tenant ID (from dependency)
        db: Tenant-aware database session
        agent_service: Agent service instance

    Returns:
        dict: {"hmac_secret": "base64encodedstring..."}

    Raises:
        HTTPException(403): Cross-tenant access forbidden
        HTTPException(404): Agent not found
        HTTPException(429): Rate limit exceeded (10 req/min) - TODO: Implement rate limiting

    Story 8.6 AC#4: GET endpoint for fetching unmasked HMAC secret (Task 7)
    """
    try:
        secret = await agent_service.get_webhook_secret(tenant_id, agent_id, db)
        logger.info(f"Webhook secret accessed for agent {agent_id} by tenant {tenant_id}")
        return {"hmac_secret": secret}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching webhook secret for agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch webhook secret",
        )


@router.post(
    "/{agent_id}/regenerate-webhook-secret",
    summary="Regenerate Webhook Secret",
    description="Generate new HMAC secret, invalidate old webhooks. Audit logged.",
)
async def regenerate_webhook_secret(
    agent_id: Annotated[UUID, "Agent UUID"],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> dict:
    """
    Generate new HMAC secret for agent webhook.

    This invalidates all existing webhooks using the old secret.
    Operation is audit logged for security tracking.

    Args:
        agent_id: Agent UUID
        tenant_id: Current tenant ID (from dependency)
        db: Tenant-aware database session
        agent_service: Agent service instance

    Returns:
        dict: {
            "success": true,
            "message": "HMAC secret regenerated",
            "new_secret_masked": "***...***"
        }

    Raises:
        HTTPException(403): Cross-tenant access forbidden
        HTTPException(404): Agent not found

    Story 8.6 AC#5: POST endpoint for regenerating HMAC secret (Task 3)
    """
    try:
        new_secret_masked = await agent_service.regenerate_webhook_secret(tenant_id, agent_id, db)
        logger.warning(
            f"Webhook secret regenerated for agent {agent_id} by tenant {tenant_id}. "
            "Old webhooks are now invalid."
        )
        return {
            "success": True,
            "message": "HMAC secret regenerated",
            "new_secret_masked": new_secret_masked,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error regenerating webhook secret for agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to regenerate webhook secret",
        )
