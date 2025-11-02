"""
Tenant Context Management for Row-Level Security (RLS).

This module provides utilities for setting PostgreSQL session variables that control
Row-Level Security policies. The tenant context must be set before any database
queries on tenant-scoped tables.

Story: 3.1 - Implement Row-Level Security in PostgreSQL
AC: 2, 3
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def set_db_tenant_context(session: AsyncSession, tenant_id: str) -> None:
    """
    Set PostgreSQL RLS tenant context for the current database session.

    This function calls the database's set_tenant_context() function which:
    1. Validates the tenant_id exists in tenant_configs
    2. Sets the session variable app.current_tenant_id
    3. Applies RLS policies based on this tenant_id

    Args:
        session: Active SQLAlchemy async database session
        tenant_id: Tenant identifier to set as context (must exist in tenant_configs)

    Raises:
        sqlalchemy.exc.DBAPIError: If tenant_id is invalid or doesn't exist
        sqlalchemy.exc.DatabaseError: If session variable cannot be set

    Example:
        async with get_async_session() as session:
            await set_db_tenant_context(session, "acme-corp")
            # All subsequent queries in this session will be filtered by tenant_id
            results = await session.execute(select(EnhancementHistory))

    Note:
        - Session variable is session-scoped, automatically cleared when session closes
        - Must be called before any queries on RLS-protected tables
        - Superusers and roles with BYPASSRLS attribute bypass this filtering
    """
    await session.execute(
        text("SELECT set_tenant_context(:tenant_id)"),
        {"tenant_id": tenant_id}
    )


async def clear_tenant_context(session: AsyncSession) -> None:
    """
    Clear the tenant context from the current database session.

    This is typically not needed as the session variable is automatically cleared
    when the session closes, but can be used for explicit cleanup in long-running
    sessions or testing scenarios.

    Args:
        session: Active SQLAlchemy async database session

    Example:
        async with get_async_session() as session:
            await set_db_tenant_context(session, "acme-corp")
            # ... perform operations ...
            await clear_tenant_context(session)
    """
    await session.execute(
        text("SELECT set_config('app.current_tenant_id', '', false)")
    )
