"""
Celery periodic task for automatic memory cleanup based on retention policy.

Runs daily at 2:00 AM UTC to delete expired memories older than
retention_days configured per agent. Ensures memory database doesn't
grow indefinitely.

Story 8.15: Memory Configuration UI - Memory Cleanup Task (Task 8.5)
"""

from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy import select

from src.database.models import Agent
from src.database.session import async_session_maker
from src.services.memory_config_service import MemoryConfigService
from src.utils.logger import logger


@shared_task(name="cleanup_expired_memories")
def cleanup_expired_memories() -> dict:
    """
    Clean up expired memories for all agents based on retention policy.

    Iterates through all agents and enforces retention policy by deleting
    memories older than retention_days. Runs as Celery Beat periodic task
    scheduled daily at 2:00 AM UTC.

    Returns:
        dict: Cleanup summary with total agents processed and memories deleted

    Raises:
        Exception: If database connection or cleanup fails
    """
    logger.info("Memory cleanup task started")

    import asyncio

    # Reason: Run async cleanup function from sync Celery task context
    result = asyncio.run(cleanup_expired_memories_async())

    logger.info(
        f"Memory cleanup completed: {result['agents_processed']} agents, "
        f"{result['total_deleted']} memories deleted"
    )

    return result


async def cleanup_expired_memories_async() -> dict:
    """
    Async implementation of memory cleanup.

    Processes all agents and enforces retention policy by calling
    MemoryConfigService.enforce_retention_policy() for each agent.

    Returns:
        dict: Cleanup summary with statistics
    """
    agents_processed = 0
    total_deleted = 0
    errors = []

    async with async_session_maker() as db:
        try:
            # Fetch all agents (no tenant filtering for scheduled task)
            stmt = select(Agent).where(Agent.status != "inactive")
            result = await db.execute(stmt)
            agents = result.scalars().all()

            logger.info(f"Processing memory cleanup for {len(agents)} agents")

            # Process each agent
            for agent in agents:
                try:
                    service = MemoryConfigService(db)

                    # Enforce retention policy for this agent
                    deleted_count = await service.enforce_retention_policy(
                        agent.id, agent.tenant_id
                    )

                    agents_processed += 1
                    total_deleted += deleted_count

                    if deleted_count > 0:
                        logger.info(
                            f"Cleaned up {deleted_count} expired memories for agent {agent.id} ({agent.name})"
                        )

                except Exception as e:
                    error_msg = f"Failed to cleanup memories for agent {agent.id}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)

        except Exception as e:
            logger.error(f"Memory cleanup task failed: {str(e)}")
            raise

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agents_processed": agents_processed,
        "total_deleted": total_deleted,
        "errors": errors,
    }


@shared_task(name="cleanup_agent_memory")
def cleanup_agent_memory(agent_id: str, tenant_id: str) -> dict:
    """
    Clean up expired memories for a specific agent (on-demand task).

    Can be triggered manually via admin UI or API for immediate cleanup
    instead of waiting for scheduled task.

    Args:
        agent_id: Agent UUID as string
        tenant_id: Tenant identifier for isolation

    Returns:
        dict: Cleanup result with deleted count

    Raises:
        Exception: If database connection or cleanup fails
    """
    import asyncio
    from uuid import UUID

    logger.info(f"On-demand memory cleanup for agent {agent_id} (tenant: {tenant_id})")

    agent_uuid = UUID(agent_id)

    # Reason: Run async cleanup function from sync Celery task context
    result = asyncio.run(cleanup_agent_memory_async(agent_uuid, tenant_id))

    logger.info(
        f"On-demand cleanup completed for agent {agent_id}: {result['deleted_count']} memories deleted"
    )

    return result


async def cleanup_agent_memory_async(agent_id, tenant_id: str) -> dict:
    """
    Async implementation of single-agent memory cleanup.

    Args:
        agent_id: Agent UUID
        tenant_id: Tenant identifier for isolation

    Returns:
        dict: Cleanup result with statistics
    """
    async with async_session_maker() as db:
        try:
            service = MemoryConfigService(db)

            # Enforce retention policy for this agent
            deleted_count = await service.enforce_retention_policy(agent_id, tenant_id)

            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent_id": str(agent_id),
                "tenant_id": tenant_id,
                "deleted_count": deleted_count,
                "success": True,
            }

        except Exception as e:
            logger.error(f"On-demand cleanup failed for agent {agent_id}: {str(e)}")
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent_id": str(agent_id),
                "tenant_id": tenant_id,
                "deleted_count": 0,
                "success": False,
                "error": str(e),
            }
